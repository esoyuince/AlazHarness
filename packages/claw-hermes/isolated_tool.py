"""HYB-005D: one-shot, credential-free Linux Docker tool execution.

Trusted operator adapter, NOT an agent-facing permission API. Only staged files
enter the container. No host secrets, state DB, Docker socket or network enters.
The native Hermes dispatch/ledger is unchanged; integration is a separate gate.
"""
from __future__ import annotations
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import threading
import time
import uuid

IMAGE = re.compile(r'sha256:[a-f0-9]{64}\Z')
IDENTITY = re.compile(r'[a-f0-9]{64}\Z')
OWNER_LABEL = 'org.alaz.harness.isolation-owner'
FIXED_ENV = ('HOME=/tmp', 'LANG=C.UTF-8', 'PATH=/usr/bin:/bin')
TMPFS = 'rw,noexec,nosuid,nodev,size=16777216,mode=1777'


class IsolationError(RuntimeError):
    """Bounded machine reason; no Docker diagnostics or credentials."""


def require(value, reason):
    if not value:
        raise IsolationError(reason)


def _integer(value, low, high, reason):
    require(type(value) is int and low <= value <= high, reason)
    return value


def checked_capsule(root: Path, capsule: Path) -> tuple[Path, str]:
    """Validate a dedicated operator-staged directory, never a general host mount.

    Capsule mutation by another privileged host process is outside this contract.
    The sandbox itself cannot modify the capsule's read-only mount.
    """
    root, capsule = Path(root), Path(capsule)
    require(root.is_absolute() and capsule.is_absolute(), 'absolute_capsule_required')
    for target in (root, capsule):
        require(not any(p.is_symlink() for p in [target, *target.parents]), 'symlink_capsule')
    base, actual = root.resolve(), capsule.resolve()
    require(actual != base and actual.is_relative_to(base), 'capsule_outside_root')
    require(base != Path('/') and actual.is_dir(), 'missing_capsule')
    require(not any(ch in str(actual) for ch in '\n\r\x00'), 'unsupported_capsule_path')
    manifest = []
    total = 0
    for p in sorted(actual.rglob('*')):
        require(not p.is_symlink(), 'symlink_capsule')
        require(p.is_file() or p.is_dir(), 'special_capsule_entry')
        if not p.is_file():
            continue
        st = p.stat()
        require(st.st_nlink == 1, 'hardlinked_capsule_entry')
        require(st.st_size <= 1048576, 'capsule_too_large')
        total += st.st_size
        require(total <= 2097152 and len(manifest) < 32, 'capsule_too_large')
        manifest.append((p.relative_to(actual).as_posix(), hashlib.sha256(p.read_bytes()).hexdigest()))
    require(any(name == 'program.py' for name, _ in manifest), 'program_missing')
    return actual, hashlib.sha256(json.dumps(manifest, separators=(',', ':')).encode()).hexdigest()


@dataclass(frozen=True)
class ToolSandboxPolicy:
    """Pin an already installed, operator-reviewed Linux image by content ID."""
    image: str
    timeout_seconds: int = 10
    output_limit_bytes: int = 65536
    memory_bytes: int = 134217728
    pids_limit: int = 32

    def __post_init__(self):
        require(type(self.image) is str and bool(IMAGE.fullmatch(self.image)), 'pinned_image_required')
        _integer(self.timeout_seconds, 1, 30, 'invalid_timeout')
        _integer(self.output_limit_bytes, 1024, 262144, 'invalid_output_limit')
        _integer(self.memory_bytes, 67108864, 536870912, 'invalid_memory')
        _integer(self.pids_limit, 8, 64, 'invalid_pids_limit')


def create_arguments(policy: ToolSandboxPolicy, capsule: Path, owner: str) -> list[str]:
    require(type(policy) is ToolSandboxPolicy, 'trusted_policy_required')
    require(type(owner) is str and re.fullmatch('[a-f0-9]{32}', owner), 'invalid_owner')
    source = str(capsule)
    require(source.startswith('/') and not any(c in source for c in ',:\n\r\x00'), 'unsupported_capsule_path')
    return [
        'create', '--pull=never', '--name=alaz-isolated-' + owner,
        '--label=' + OWNER_LABEL + '=' + owner,
        '--network=none', '--read-only', '--cap-drop=ALL',
        '--security-opt=no-new-privileges', '--user=65534:65534',
        '--pids-limit=' + str(policy.pids_limit), '--memory=' + str(policy.memory_bytes),
        '--memory-swap=' + str(policy.memory_bytes), '--cpus=0.5',
        '--ipc=none', '--cgroupns=private', '--init', '--restart=no',
        '--log-driver=none', '--stop-timeout=2', '--no-healthcheck',
        '--tmpfs=/tmp:' + TMPFS,
        '--mount=type=bind,source=' + source + ',target=/workspace,readonly,bind-propagation=rprivate',
        '--workdir=/workspace', '--entrypoint=/usr/bin/env',
        policy.image, '-i', *FIXED_ENV, '/usr/bin/python3', '-I', '-B', '/workspace/program.py',
    ]


def validate_container(raw: dict, *, policy: ToolSandboxPolicy, capsule: Path,
                       owner: str, container_id: str) -> dict:
    """Check Docker's actual create/inspect response BEFORE starting the process."""
    try:
        require(type(raw) is dict and raw['Id'] == container_id and IDENTITY.fullmatch(container_id), 'container_identity_mismatch')
        cfg, host = raw['Config'], raw['HostConfig']
        require(raw['Image'] == policy.image, 'container_image_changed')
        require(raw['Name'] == '/alaz-isolated-' + owner and cfg['Labels'].get(OWNER_LABEL) == owner,
                'container_ownership_mismatch')
        require(cfg['User'] == '65534:65534' and cfg['WorkingDir'] == '/workspace', 'container_user_or_workdir')
        require(cfg['Entrypoint'] == ['/usr/bin/env'], 'container_entrypoint')
        require(cfg['Cmd'] == ['-i', *FIXED_ENV, '/usr/bin/python3', '-I', '-B', '/workspace/program.py'], 'container_command')
        require(host['NetworkMode'] == 'none' and host['ReadonlyRootfs'] is True, 'container_network_or_root')
        require(host['Privileged'] is False and set(host['CapDrop']) == {'ALL'} and not host.get('CapAdd'), 'container_capabilities')
        require(host.get('SecurityOpt') in (['no-new-privileges'], ['no-new-privileges=true']), 'container_security_options')
        require(host['PidsLimit'] == policy.pids_limit and host['Memory'] == policy.memory_bytes
                and host['MemorySwap'] == policy.memory_bytes and host['NanoCpus'] == 500000000,
                'container_resource_limits')
        require(host['IpcMode'] == 'none' and host.get('PidMode', '') == '' and host['CgroupnsMode'] == 'private', 'container_namespaces')
        require(host['Init'] is True and host['RestartPolicy']['Name'] == 'no', 'container_lifecycle_options')
        require(host['LogConfig']['Type'] == 'none' and host['Tmpfs'] == {'/tmp': TMPFS}, 'container_logs_or_tmpfs')
        for field in ('Binds', 'VolumesFrom', 'Devices', 'DeviceRequests', 'DeviceCgroupRules', 'GroupAdd', 'Links', 'ExtraHosts', 'PortBindings'):
            require(not host.get(field), 'unexpected_container_exposure')
        require(not host.get('PublishAllPorts') and not cfg.get('Volumes') and not cfg.get('ExposedPorts'), 'unexpected_image_exposure')
        mounts = raw['Mounts']
        require(len(mounts) == 1, 'unexpected_mounts')
        mount = mounts[0]
        require(mount['Type'] == 'bind' and mount['Source'] == str(capsule) and mount['Destination'] == '/workspace'
                and mount['RW'] is False and mount['Propagation'] == 'rprivate', 'unexpected_mounts')
        require(set(raw['NetworkSettings']['Networks']) <= {'none'}, 'unexpected_network_attachment')
        return {'containerId': container_id, 'network': 'none', 'rootReadOnly': True,
                'user': '65534:65534', 'capabilitiesDropped': ['ALL'], 'noNewPrivileges': True,
                'onlyCapsuleMounted': True, 'memoryBytes': policy.memory_bytes, 'pidsLimit': policy.pids_limit}
    except (KeyError, TypeError, AttributeError):
        raise IsolationError('malformed_container_inspection') from None


class IsolatedToolRunner:
    """One-shot lifecycle. A failed/uncertain operation is never retried.

    The daemon and host OS admin remain trusted. This is a Docker/Linux tool
    boundary, not VM isolation, universal provider fencing or a permission grant.
    """
    def __init__(self, *, root: Path, capsule: Path, receipt_dir: Path,
                 policy: ToolSandboxPolicy, use_sudo: bool = False):
        require(type(policy) is ToolSandboxPolicy and type(use_sudo) is bool, 'trusted_policy_required')
        self.root = Path(root)
        self.capsule, self.capsule_hash = checked_capsule(self.root, Path(capsule))
        self.receipt_dir = Path(receipt_dir)
        require(self.receipt_dir.is_absolute() and not self.receipt_dir.exists(), 'fresh_receipt_directory_required')
        require(not self.receipt_dir.is_relative_to(self.capsule), 'receipt_inside_capsule')
        self.policy, self.use_sudo = policy, use_sudo
        self.owner, self.cid, self.used = uuid.uuid4().hex, None, False
        self._base = None

    def _write_receipt(self, name, value):
        target = self.receipt_dir / name
        tmp = target.with_suffix('.tmp')
        tmp.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')
        tmp.replace(target)

    def _docker(self, arguments, *, timeout=10, allow_failure=False):
        try:
            p = subprocess.run([*self._base, *arguments], env=self._env, stdin=subprocess.DEVNULL,
                               capture_output=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            raise IsolationError('docker_operation_outcome_unknown') from None
        except OSError:
            raise IsolationError('docker_unavailable') from None
        require(len(p.stdout) <= 1048576 and len(p.stderr) <= 65536, 'docker_response_too_large')
        if not allow_failure:
            require(p.returncode == 0, 'docker_operation_failed')
        return p

    def _inspect(self, ident):
        p = self._docker(['inspect', '--type=container', ident])
        try:
            data = json.loads(p.stdout)
            require(type(data) is list and len(data) == 1, 'malformed_container_inspection')
            return data[0]
        except (ValueError, TypeError, IndexError):
            raise IsolationError('malformed_container_inspection') from None

    def _owned(self, raw):
        require(type(raw) is dict, 'malformed_container_inspection')
        require(type(raw.get('Id')) is str and IDENTITY.fullmatch(raw['Id']), 'container_identity_mismatch')
        require(raw.get('Name') == '/alaz-isolated-' + self.owner
                and raw.get('Config', {}).get('Labels', {}).get(OWNER_LABEL) == self.owner,
                'container_ownership_mismatch')
        if self.cid:
            require(raw['Id'] == self.cid, 'container_identity_mismatch')
        self.cid = raw['Id']
        return raw

    def _close(self):
        raw = self._owned(self._inspect(self.cid or 'alaz-isolated-' + self.owner))
        never_started = raw['State']['Status'] == 'created'
        was_running = raw['State']['Running'] is True
        if raw['State']['Running']:
            self._docker(['kill', self.cid], allow_failure=True)
        if not never_started:
            self._docker(['wait', self.cid], timeout=10)
        raw = self._owned(self._inspect(self.cid))
        require(raw['State']['Running'] is False and raw['State']['Pid'] == 0, 'container_exit_unconfirmed')
        exit_info = {'containerId': self.cid, 'exited': True, 'exitCode': raw['State']['ExitCode'],
                     'oomKilled': raw['State'].get('OOMKilled'), 'neverStarted': never_started,
                     'runningBeforeCleanup': was_running, 'removed': False}
        self._write_receipt('exit.json', exit_info)
        self._docker(['rm', self.cid])
        # Exact ID query; never prune a name prefix or delete an unrelated object.
        listed = self._docker(['ps', '-aq', '--no-trunc', '--filter=id=' + self.cid])
        require(not listed.stdout.strip(), 'container_removal_unconfirmed')
        exit_info['removed'] = True
        self._write_receipt('exit.json', exit_info)
        return exit_info

    def run(self, *, cancel_event: threading.Event | None = None) -> dict:
        require(not self.used, 'runner_already_used')
        self.used = True
        require(os.name == 'posix' and Path('/proc/self/ns/net').exists(), 'linux_backend_required')
        require(checked_capsule(self.root, self.capsule)[1] == self.capsule_hash, 'capsule_changed')
        self.receipt_dir.mkdir(parents=True, exist_ok=False)
        (self.receipt_dir / 'docker-config').mkdir()
        (self.receipt_dir / 'home').mkdir()
        self._env = {'PATH': '/usr/bin:/bin', 'HOME': str(self.receipt_dir / 'home'), 'LANG': 'C.UTF-8'}
        self._base = (['/usr/bin/sudo', '-n'] if self.use_sudo else []) + [
            '/usr/bin/docker', '--host=unix:///var/run/docker.sock', '--config', str(self.receipt_dir / 'docker-config')]
        self._write_receipt('ownership.json', {'owner': self.owner, 'name': 'alaz-isolated-' + self.owner,
                                               'image': self.policy.image, 'capsuleDigest': self.capsule_hash,
                                               'automaticRetry': False})
        answer = {'version': 1, 'result': 'NOT_RUN', 'errors': [], 'automaticRetry': False,
                  'providerCallsByRunner': 0, 'hostSecretsForwarded': False,
                  'fullHermesIntegration': False}
        created = False
        create_attempted = False
        attached = None
        chunks = {'stdout': bytearray(), 'stderr': bytearray()}
        sizes = {'stdout': 0, 'stderr': 0}
        reader_errors = []
        overflow = threading.Event()
        threads = []
        try:
            require(cancel_event is None or not cancel_event.is_set(), 'cancelled_before_create')
            # No pulls, builds, aliases or inherited Docker context/registry credentials.
            image = json.loads(self._docker(['image', 'inspect', self.policy.image]).stdout)[0]
            require(image['Id'] == self.policy.image and image['Os'] == 'linux', 'image_not_qualified')
            require(not image['Config'].get('Volumes') and not image['Config'].get('ExposedPorts'), 'unexpected_image_exposure')
            # Fresh random name; Docker rejects any collision. No adopt/restart of old work.
            args = create_arguments(self.policy, self.capsule, self.owner)
            self._write_receipt('plan.json', {'arguments': args, 'environmentNames': sorted(self._env), 'image': self.policy.image})
            create_attempted = True
            create = self._docker(args)
            cid = create.stdout.decode('ascii').strip()
            require(bool(IDENTITY.fullmatch(cid)), 'invalid_create_receipt')
            self.cid, created = cid, True
            raw = self._owned(self._inspect(cid))
            require(raw['State']['Status'] == 'created' and raw['State']['Running'] is False, 'container_started_before_validation')
            checked = validate_container(raw, policy=self.policy, capsule=self.capsule, owner=self.owner, container_id=cid)
            self._write_receipt('prestart-validation.json', checked)
            require(checked_capsule(self.root, self.capsule)[1] == self.capsule_hash, 'capsule_changed')
            require(cancel_event is None or not cancel_event.is_set(), 'cancelled_before_start')
            attached = subprocess.Popen([*self._base, 'start', '--attach', cid], env=self._env,
                                        stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            def read(pipe, key):
                try:
                    while True:
                        piece = pipe.read(4096)
                        if not piece:
                            break
                        sizes[key] += len(piece)
                        left = self.policy.output_limit_bytes - len(chunks[key])
                        chunks[key].extend(piece[:max(0, left)])
                        if sizes[key] > self.policy.output_limit_bytes:
                            overflow.set()
                except Exception:
                    reader_errors.append(key)
                finally:
                    pipe.close()
            for key in chunks:
                th = threading.Thread(target=read, args=(getattr(attached, key), key), daemon=True)
                th.start(); threads.append(th)
            deadline = time.monotonic() + self.policy.timeout_seconds
            reason = None
            while attached.poll() is None:
                if overflow.is_set(): reason = 'output_limit'; break
                if cancel_event is not None and cancel_event.is_set(): reason = 'cancelled'; break
                if time.monotonic() >= deadline: reason = 'timeout'; break
                time.sleep(.02)
            # Docker state, not an echoed child assertion, proves termination.
            answer['exit'] = self._close()
            created = False
            try:
                attached.wait(timeout=5)
            except subprocess.TimeoutExpired:
                attached.kill(); attached.wait(timeout=5)
                reason = reason or 'attach_exit_unconfirmed'
            for th in threads: th.join(timeout=5)
            require(not any(th.is_alive() for th in threads) and not reader_errors, 'output_reader_unconfirmed')
            if overflow.is_set(): reason = reason or 'output_limit'
            # A created container has not run, even though Docker's default exit
            # field is zero. Losing the attach client is not tool-success proof.
            if answer['exit']['neverStarted']:
                answer['result'] = 'refused'
                answer['errors'].append('container_never_started')
            elif reason == 'attach_exit_unconfirmed' or (reason is None and
                    (answer['exit']['runningBeforeCleanup'] or attached.returncode != answer['exit']['exitCode'])):
                answer['result'] = 'unknown'
                answer['errors'].append('attachment_outcome_unconfirmed')
            else:
                answer['result'] = reason or ('completed' if answer['exit']['exitCode'] == 0 else 'tool_failed')
            answer['stdout'] = bytes(chunks['stdout']).decode('utf-8', 'replace')
            answer['stderr'] = bytes(chunks['stderr']).decode('utf-8', 'replace')
            answer['outputBytes'] = dict(sizes)
            answer['outputTruncated'] = overflow.is_set()
        except (IsolationError, OSError, ValueError, KeyError, TypeError, IndexError) as exc:
            answer['result'] = 'refused'
            answer['errors'].append(str(exc) if isinstance(exc, IsolationError) else 'isolation_backend_error')
        finally:
            if create_attempted and not created and self.cid is None:
                # A lost create acknowledgement may leave our own container. Never
                # replay create/start. Resolve our exact random name+label instead.
                try:
                    raw = self._owned(self._inspect('alaz-isolated-' + self.owner))
                    created = True
                except IsolationError:
                    answer['errors'].append('create_cleanup_unconfirmed')
            if created:
                try: answer['exit'] = self._close()
                except (IsolationError, KeyError, TypeError): answer['errors'].append('cleanup_unconfirmed')
            if attached is not None and attached.poll() is None:
                attached.kill(); attached.wait(timeout=5)
            for th in threads: th.join(timeout=1)
            if any(e.endswith('cleanup_unconfirmed') for e in answer['errors']):
                answer['result'] = 'unknown'
            try:
                answer['capsuleUnchanged'] = checked_capsule(self.root, self.capsule)[1] == self.capsule_hash
            except (IsolationError, OSError):
                answer['capsuleUnchanged'] = False
            if not answer['capsuleUnchanged']:
                answer['errors'].append('capsule_changed')
                answer['result'] = 'unknown'
            # Tool stdout/stderr are untrusted. Only publish selected sanitized test receipts.
            self._write_receipt('result.json', answer)
        return answer
