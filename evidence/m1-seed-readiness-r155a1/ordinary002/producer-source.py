"""Bootstrap one fresh retained profile through the original pinned native APIs.

This fixed provisioner consumes the R154 verified installation. It does not
publish API admission, submit work, register the complete tool graph, call a
provider, create a mount, or grant projected execution authority. A caller must
own any namespace/cgroup enrollment and the seed process. Partial state remains
on every failure; this program has no repair, reuse, retry, or cleanup command.
"""
from __future__ import annotations

import argparse
import asyncio
import contextlib
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import platform
import re
import sqlite3
import stat
import sys
import threading
import time
import types

INSTALLATION = Path('/opt/alaz-r154a1')
INPUT = Path('/opt/alaz-r154a1-input')
DEPENDENCIES = Path('/opt/alaz-f126c1a6/dependencies')
PYTHON = '/usr/bin/python3.12'
INSTALLER_SHA256 = 'a56782d4e09bed38983c387d4b882e3db3866409e8e96e1f092d36517fc53525'
RECEIPT_SHA256 = '137cbe59427813b50f8c8581a7dbc3b81db9e514e2e57784cee91baa4cc17ae2'
NATIVE_FEATURE = 'd1516731308de8e87130dc68124e69aad35d6911'
PINS = {
    'expected_manifest_sha256': '182b9d0198e4c7f39bd28e194bfe7fc6cfca844ed4a653e9d209b0db8d77eef9',
    'expected_archive_sha256': 'e036fba503130b3b259ec727439089c8fa3d88408359618fa5c7df77a6b5513b',
    'expected_harness_commit': 'e03f7fd4e47fea6a58b749564ab350aeb4237a26',
    'expected_python_sha256': 'e50d468e8b0adfb05733f5b87b3cff34829c4a8c1aea50c865aa8bdfe4bb150f',
}
MAX_RESULT = 32768
MAX_SOURCE = 4 * 1024 * 1024
MAX_DISCOVERY = 262144
MAX_CANDIDATES = 1024
MAX_ELAPSED_MILLIS = 35000  # The supervisor independently owns the process deadline.
HELPERS = ('run_store_preopen.py', 'run_response_preopen.py')
FORBIDDEN_NATIVE_CALLS = frozenset((
    'run_api_turn', 'execute_finite_admission', 'run_conversation',
    '_build_fresh_agent', 'commit_and_publish', 'settle_session_input',
))


class BootstrapRejected(ValueError):
    pass


def require(value, reason):
    if not value:
        raise BootstrapRejected(reason)


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'),
                       ensure_ascii=True, allow_nan=False) + '\n').encode('ascii')


def decimal(value):
    require(type(value) is str and re.fullmatch('[1-9][0-9]{0,19}', value) is not None,
            'bootstrap_decimal')
    result = int(value)
    require(result < 2**64, 'bootstrap_decimal')
    return result


def canonical_home(value):
    require(type(value) is str and 1 < len(value) <= 4096 and '\x00' not in value
            and '\\' not in value and not value.startswith('//'), 'bootstrap_home_path')
    path = PurePosixPath(value)
    require(path.is_absolute() and str(path) == value and '..' not in path.parts
            and '.' not in value.split('/'), 'bootstrap_home_path')
    return Path(value)


def validate_arguments(args):
    home = canonical_home(args.home)
    require(type(args.instance_id) is str
            and re.fullmatch('[A-Za-z0-9._-]{1,128}', args.instance_id) is not None,
            'bootstrap_instance_id')
    for name in ('gateway_uid', 'socket_group_gid', 'parent_pid'):
        value = getattr(args, name)
        require(type(value) is int and 0 < value < 2**31, 'bootstrap_actor_argument')
    for name in ('expected_profile_device', 'expected_profile_inode'):
        value = getattr(args, name)
        require(type(value) is int and 0 < value < 2**64, 'bootstrap_profile_argument')
    require(not any(home == p or p in home.parents
                    for p in (INSTALLATION, INPUT, DEPENDENCIES)), 'bootstrap_home_in_installation')
    return home


def validate_actor(args):
    require(sys.platform == 'linux' and platform.machine() == 'x86_64'
            and platform.python_implementation() == 'CPython'
            and sys.version_info[:2] == (3, 12) and sys.executable == PYTHON,
            'bootstrap_interpreter')
    require(sys.flags.isolated == 1 and sys.dont_write_bytecode and not sys.flags.optimize,
            'bootstrap_interpreter_flags')
    require(os.getresuid() == (args.gateway_uid,) * 3
            and os.getresgid() == (args.socket_group_gid,) * 3
            and set(os.getgroups()) <= {args.socket_group_gid}
            and os.getppid() == args.parent_pid and os.getpid() != args.parent_pid,
            'bootstrap_actor')
    require(threading.current_thread() is threading.main_thread()
            and threading.active_count() == 1 and sys.getprofile() is None,
            'bootstrap_fresh_process')
    forbidden = ('gateway', 'hermes_', 'hermes_cli', 'tools', 'agent', 'run_agent', 'model_tools')
    require(not any(name == prefix or name.startswith(prefix + '.')
                    or (prefix.endswith('_') and name.startswith(prefix))
                    for name in sys.modules for prefix in forbidden), 'bootstrap_native_already_imported')


def home_identity(home, args, *, fresh):
    require(home.resolve(strict=True) == home
            and not any(p.is_symlink() for p in (home, *home.parents)), 'bootstrap_home_alias')
    fd = os.open(home, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        info = os.fstat(fd)
        require(stat.S_ISDIR(info.st_mode) and stat.S_IMODE(info.st_mode) == 0o700
                and (info.st_uid, info.st_gid) == (args.gateway_uid, args.socket_group_gid)
                and (info.st_dev, info.st_ino) == (args.expected_profile_device, args.expected_profile_inode),
                'bootstrap_home_identity')
        if fresh:
            require(not os.listdir(fd), 'bootstrap_home_not_empty')
        after = home.lstat()
        require((after.st_dev, after.st_ino, after.st_mode, after.st_uid, after.st_gid)
                == (info.st_dev, info.st_ino, info.st_mode, info.st_uid, info.st_gid),
                'bootstrap_home_changed')
        return (info.st_dev, info.st_ino)
    finally:
        os.close(fd)


def _trusted_installer_bytes(path):
    require(path.is_absolute() and path.resolve(strict=True) == path
            and not any(p.is_symlink() for p in (path, *path.parents)), 'bootstrap_installer_alias')
    for parent in path.parents:
        info = parent.lstat()
        require(stat.S_ISDIR(info.st_mode) and info.st_uid == info.st_gid == 0
                and not info.st_mode & 0o022, 'bootstrap_installer_ancestry')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC)
    try:
        before = os.fstat(fd)
        require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1
                and before.st_uid == before.st_gid == 0 and not before.st_mode & 0o022
                and 0 < before.st_size <= MAX_SOURCE, 'bootstrap_installer_file')
        with os.fdopen(fd, 'rb', closefd=False) as stream:
            raw = stream.read(MAX_SOURCE + 1)
        after = os.fstat(fd)
        stamp = lambda x: (x.st_dev, x.st_ino, x.st_mode, x.st_uid, x.st_gid,
                           x.st_nlink, x.st_size, x.st_mtime_ns, x.st_ctime_ns)
        require(len(raw) == before.st_size and stamp(before) == stamp(after),
                'bootstrap_installer_changed')
    finally:
        os.close(fd)
    require(hashlib.sha256(raw).hexdigest() == INSTALLER_SHA256, 'bootstrap_installer_digest')
    return raw


def verify_installation():
    path = INPUT / 'scripts/install_projected_candidate.py'
    raw = _trusted_installer_bytes(path)
    name = '_alaz_r155_verified_installer'
    require(name not in sys.modules, 'bootstrap_verifier_already_loaded')
    module = types.ModuleType(name)
    module.__file__ = str(path)
    sys.modules[name] = module
    exec(compile(raw, str(path), 'exec'), module.__dict__)
    result = module.verify_installed(INPUT / 'candidate', INSTALLATION, DEPENDENCIES, **PINS)
    require(result['receiptSha256'] == RECEIPT_SHA256 and result['verifiedInstalledBytesNow'] is True
            and result['installed'] is True and result['sourceAndDependenciesReadBack'] is True
            and result['rootControlledAncestryVerified'] is True
            and result['sourceFileCount'] == 834 and result['dependencyFileCount'] == 1162
            and result['harnessCommit'] == PINS['expected_harness_commit']
            and result['nativeFeature'] == NATIVE_FEATURE
            and result['destination'] == str(INSTALLATION), 'bootstrap_installation_identity')
    return result


def configure_environment(home):
    # This is a fresh child environment. No credential/provider values survive.
    # HOME is intentionally omitted; native APIs must resolve HERMES_HOME exactly.
    os.environ.clear()
    os.environ.update(PATH='/usr/bin:/bin', LANG='C.UTF-8', LC_ALL='C.UTF-8', TZ='UTC',
                      HERMES_HOME=str(home), TMPDIR=str(home))


class OfflineBoundary:
    """Operational tripwire for this fixed, trusted bootstrap, not a sandbox."""
    def __init__(self, home, progress):
        self.home = home
        self.progress = progress
        self.native_prefix = str(INSTALLATION / 'native') + os.sep
        self.helpers = []
        self.sqlite_opens = []
        self.denied = []
        self.native_work_attempts = []

    def reject(self, reason):
        if len(self.denied) < 16:
            self.denied.append({'phase': self.progress['phase'], 'reason': reason})
        raise BootstrapRejected(reason)

    def writable(self, value):
        if type(value) is int and value >= 0:
            return True  # Existing stdio/owned descriptors; never discovered targets.
        try:
            raw = os.fsdecode(value)
            path = Path(raw)
            return (path.is_absolute() and str(path) == raw and '..' not in path.parts
                    and path.resolve(strict=False) == path
                    and (path == self.home or self.home in path.parents))
        except (OSError, RuntimeError, TypeError, ValueError):
            return False

    def __call__(self, event, args):
        if event == 'subprocess.Popen':
            executable, argv, cwd, env = args
            index = len(self.helpers)
            expected = ([PYTHON, '-I', '-B', str(INSTALLATION / 'scripts' / HELPERS[index])]
                        if index < len(HELPERS) else None)
            if not (self.progress['phase'] == 'START_OWNER' and isinstance(argv, (list, tuple))
                    and list(argv) == expected and executable == PYTHON
                    and str(cwd) == str(INSTALLATION)
                    and env == {'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8', 'HOME': '/'}):
                self.reject('bootstrap_process_forbidden')
            self.helpers.append({'phase': self.progress['phase'], 'script': HELPERS[index]})
        elif event in ('socket.connect', 'socket.bind', 'socket.getaddrinfo', 'socket.gethostbyname',
                       'socket.gethostbyaddr', 'socket.getnameinfo', 'socket.sendto',
                       'socket.sendmsg', 'os.system', 'os.posix_spawn',
                       'os.exec', 'os.fork', 'os.forkpty'):
            self.reject('bootstrap_network_or_process_forbidden')
        elif event == 'sqlite3.connect':
            path = str(args[0])
            allowed = {str(self.home / name) for name in ('state.db', 'runs_idempotency.db', 'response_store.db')}
            if path not in allowed:
                self.reject('bootstrap_database_path_forbidden')
            self.sqlite_opens.append({'phase': self.progress['phase'], 'path': path})
        elif event == 'open':
            path, mode, flags = args
            write = bool(flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND))
            if write and not self.writable(path):
                self.reject('bootstrap_write_outside_profile')
        elif event in ('os.mkdir', 'os.remove', 'os.rmdir', 'os.chmod'):
            if not self.writable(args[0]):
                self.reject('bootstrap_mutation_outside_profile')
        elif event in ('os.rename', 'os.link', 'os.symlink'):
            if not self.writable(args[0]) or not self.writable(args[1]):
                self.reject('bootstrap_mutation_outside_profile')

    def profile(self, frame, event, arg):
        if event != 'call':
            return
        file = frame.f_code.co_filename
        if not file.startswith(self.native_prefix):
            return
        name = frame.f_code.co_name
        if name in FORBIDDEN_NATIVE_CALLS or frame.f_code.co_qualname == 'AIAgent.__init__':
            if len(self.native_work_attempts) < 16:
                self.native_work_attempts.append(name)
            self.reject('bootstrap_native_work_forbidden')


def source_discovery_rows(proof, registry):
    native, hashes = proof
    require(type(hashes) is dict and native.resolve(strict=True) == native, 'bootstrap_source_proof')
    selected = {}
    for name, digest in hashes.items():
        path = PurePosixPath(name)
        parts = path.parts
        candidate = len(parts) == 2 and parts[0] == 'tools' and path.suffix == '.py'
        candidate = candidate or (len(parts) == 3 and parts[0] == 'tools' and parts[2] == 'tool.py'
                                  and str(PurePosixPath(*parts[:2]) / '__init__.py') in hashes)
        if candidate and path.name not in ('__init__.py', 'registry.py', 'mcp_tool.py'):
            selected[native / path] = digest
    require(0 < len(selected) <= MAX_CANDIDATES, 'bootstrap_discovery_count')
    candidates = registry._tool_module_candidates(native / 'tools')
    actual = [p for p in candidates if p.name not in ('__init__.py', 'registry.py', 'mcp_tool.py')
              and (p.parent == native / 'tools' or (p.parent / '__init__.py').is_file())]
    require(len(actual) == len(set(actual)) and set(actual) == set(selected),
            'bootstrap_discovery_candidates_changed')
    result = {}
    for path, digest in sorted(selected.items()):
        info = path.lstat()
        require(path.resolve(strict=True) == path and stat.S_ISREG(info.st_mode)
                and info.st_nlink == 1 and 0 <= info.st_size <= MAX_SOURCE
                and 0 <= info.st_mtime_ns < 2**63, 'bootstrap_tool_source_file')
        raw = path.read_bytes()
        require(len(raw) == info.st_size and hashlib.sha256(raw).hexdigest() == digest,
                'bootstrap_tool_source_changed')
        registers = registry._module_registers_tools(path)
        after = path.stat()
        require(type(registers) is bool and (after.st_dev, after.st_ino, after.st_size,
                after.st_mtime_ns, after.st_ctime_ns) == (info.st_dev, info.st_ino, info.st_size,
                info.st_mtime_ns, info.st_ctime_ns), 'bootstrap_tool_source_changed')
        result[str(path)] = [info.st_mtime_ns, info.st_size, registers]
    require(len(canonical(result)) <= MAX_DISCOVERY, 'bootstrap_discovery_size')
    return result


def initialize_auxiliaries(home, consumer, instance_id):
    import hermes_constants
    import hermes_cli.auth as auth
    import hermes_cli.active_sessions as active
    import gateway.platforms.base as base
    import tools.registry as registry
    from agent.safe_worker_policy import safe_worker_enabled
    from gateway_prepared_consumer import verify_imports
    require(not safe_worker_enabled(), 'bootstrap_safe_worker_incompatible')
    require(Path(hermes_constants.get_hermes_home()) == home
            and hermes_constants.get_hermes_home_override() is None,
            'bootstrap_native_home_changed')
    require(base.DOCUMENT_CACHE_DIR == base._CACHE_DIR_IMPORT_DEFAULTS['DOCUMENT_CACHE_DIR']
            and Path(base.DOCUMENT_CACHE_DIR) == home / 'cache/documents'
            and not (home / 'document_cache').exists(), 'bootstrap_document_cache_redirected')
    with auth._auth_store_lock(timeout_seconds=2.0, target_path=home / 'auth.json'):
        require(not (home / 'auth.json').exists(), 'bootstrap_unexpected_auth_store')
    require(base.get_document_cache_dir() == home / 'cache/documents',
            'bootstrap_document_cache_redirected')
    with active.active_session_liveness_guard(instance_id, registry_home=home,
                                               own_live_lease_ids=None) as is_active:
        require(is_active is False, 'bootstrap_active_session_present')
    require(active.active_session_registry_snapshot(registry_home=home, strict=True) == [],
            'bootstrap_active_sessions_present')
    require(registry._discovery_cache_path() == home / 'cache/tool_discovery_cache.json',
            'bootstrap_discovery_redirected')
    rows = source_discovery_rows(consumer._source_proof, registry)
    registry._save_discovery_cache(rows)
    cache = home / 'cache/tool_discovery_cache.json'
    require(cache.is_file() and not cache.is_symlink() and cache.stat().st_size <= MAX_DISCOVERY,
            'bootstrap_discovery_write_missing')
    raw = cache.read_bytes()
    from gateway_retained_profile import _json
    require(_json(raw) == rows, 'bootstrap_discovery_write_changed')
    verify_imports(consumer._source_proof)
    return {'sourceDerivedCacheEntries': len(rows),
            'sourceDerivedCacheSha256': hashlib.sha256(raw).hexdigest(),
            'completeToolRegistrationPerformed': False, 'activeSessionEntries': 0}


def physically_closed(connections):
    for connection in connections:
        try:
            connection.execute('SELECT 1')
        except sqlite3.ProgrammingError:
            continue
        raise BootstrapRejected('bootstrap_connection_not_physically_closed')


async def native_lifecycle(home, args, progress, boundary):
    from gateway.runtime_ownership import process_ownership
    from hermes_state import SessionDB
    from gateway.platforms.api_server_run_idempotency import RunIdempotencyStore
    from gateway.platforms.api_server_response_store import ResponseStore
    from gateway.config import GatewayConfig, PlatformConfig
    import gateway_store_startup as startup
    import gateway_retained_profile as retained
    import gateway_retained_handoff as handoff
    import gateway_profile_lease as lease
    import gateway_storage_mounts as mounts
    import gateway_native_layout as layout
    import hermes_state_registry as registry
    from agent.safe_worker_policy import safe_worker_enabled
    from gateway_prepared_consumer import verify_imports
    require(not safe_worker_enabled(), 'bootstrap_safe_worker_incompatible')
    require(not process_ownership.homes and registry.stats()['total_refcounts'] == 0,
            'bootstrap_existing_native_owner')
    selected = mounts.select_mount(mounts.parse_mountinfo(mounts._read_mountinfo()), str(home))
    mount = mounts.ExpectedMount(selected.mount_id, selected.device, selected.root,
                                 selected.mount_point, selected.filesystem)
    require(mount.filesystem == 'ext4', 'bootstrap_ext4_required')
    # The qualified native imports initialize the original cold scaffold
    # (SOUL.md and its empty standard directories). Freshness was established
    # twice before native imports. Recheck identity here; the unchanged native
    # layout inspector below validates the complete scaffold and three stores.
    home_identity(home, args, fresh=False)
    require(not boundary.sqlite_opens and not boundary.helpers, 'bootstrap_import_opened_store_or_helper')

    def identity(name):
        info = (home / name).stat()
        return info.st_dev, info.st_ino

    progress.update(phase='CREATE_COLD_STORES', nativeEffectsAttempted=True)
    lock = os.open(home / 'gateway.lock', os.O_CREAT | os.O_EXCL | os.O_WRONLY
                   | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
    os.close(lock)
    process_ownership.reserve([home])
    state = SessionDB(home / 'state.db')
    replay = RunIdempotencyStore(str(home / 'runs_idempotency.db'))
    response = ResponseStore(db_path=str(home / 'response_store.db'), canonical_state=state,
                             max_size=100, max_identities=1000)
    seed_connections = (state._conn, replay._conn, response._conn)
    expected = startup.live.PreparedStoreExpectation(
        startup.live.NATIVE_PIN, startup.live.schema_digest(state._conn),
        startup.live.schema_digest(replay._conn),
        state._conn.execute("SELECT value FROM state_meta WHERE key='store_instance_id'").fetchone()[0],
        state._conn.execute('PRAGMA application_id').fetchone()[0],
        identity('state.db'), identity('runs_idempotency.db'), 0, None)
    response_expected = startup.response_preopen.PreparedResponseExpectation(
        startup.response_preopen.NATIVE_FEATURE, startup.response_preopen.SCHEMA_SHA256,
        identity('response_store.db'))
    require(startup.live.schema_digest(response._conn) == response_expected.schema_sha256,
            'bootstrap_response_schema')
    for store in (response, replay, state):
        store.close()
    physically_closed(seed_connections)
    process_ownership.close()
    require(not process_ownership.homes and registry.stats()['total_refcounts'] == 0,
            'bootstrap_cold_seed_not_released')

    progress['phase'] = 'RESERVE_PROFILE'
    held = lease.reserve_profile(home, mount)
    require(held.check()['state'] == 'NATIVE_PROFILE_RESERVED', 'bootstrap_profile_lease')
    layout.inspect_profile(home, uid=args.gateway_uid, gid=args.socket_group_gid,
                           device=args.expected_profile_device, include_response=True)
    owner = startup.NativeStoreStartup(held, mount, expected, instance_id=args.instance_id,
                                       response_expected=response_expected, prepared_layout=True)
    progress['phase'] = 'START_OWNER'
    started = owner.start()
    require(owner.expectation.epoch == 1 and len(started['completedChecks']) == 6,
            'bootstrap_cold_start')
    require([item['script'] for item in boundary.helpers] == list(HELPERS),
            'bootstrap_cold_helper_count')
    connections = (owner.state_store._conn, owner.replay_store._conn, owner.response_store._conn)
    progress['phase'] = 'PREPARE_CONSUMER'
    consumer = await owner.prepare_runtime(
        GatewayConfig(multiplex_profiles=False, write_sessions_json=False),
        PlatformConfig(extra={'key': 'r155-local-disabled-api', 'model_name': 'r155-no-model'}),
        local_admission=True, canonical_api=True, finite_turn=True)
    prepared = consumer.check()
    require(prepared['nativeAdmissionState'] == 'PREPARED'
            and prepared['canonicalApiPublicationState'] == 'NEW'
            and all(a is b for a, b in zip(consumer._connections, connections)),
            'bootstrap_consumer_not_idle')
    require(connections[0].execute('SELECT COUNT(*) FROM session_admissions').fetchone()[0] == 0,
            'bootstrap_admission_rows_present')
    progress['phase'] = 'INITIALIZE_AUXILIARIES'
    auxiliary = initialize_auxiliaries(home, consumer, args.instance_id)
    progress['phase'] = 'DETACH_CONSUMER'
    await consumer.detach()
    consumer.assert_store_closeable(owner)
    require(not [t for t in asyncio.all_tasks() if t is not asyncio.current_task() and not t.done()],
            'bootstrap_pending_async_work')
    progress['phase'] = 'CLOSE_OWNER'
    expectation = owner.expectation
    owner.close()
    physically_closed(connections)
    require(owner._stage == 'CLOSED' and consumer._stage == 'DETACHED'
            and held.check()['state'] == 'NATIVE_PROFILE_RESERVED', 'bootstrap_close_or_lease')
    progress['phase'] = 'CAPTURE_RETAINED'
    receipt = retained.capture(owner)
    progress['phase'] = 'ENCODE_HANDOFF'
    record = handoff.RetainedStartup(expectation, response_expected, receipt)
    wire = handoff.encode(record, expected_home=str(home))
    require(handoff.decode(wire, expected_home=str(home)) == record, 'bootstrap_handoff_roundtrip')
    verify_imports(consumer._source_proof)
    progress['phase'] = 'RELEASE_PROFILE'
    held.finish()
    require(not process_ownership.homes and registry.stats()['total_refcounts'] == 0,
            'bootstrap_lease_or_registry_retained')
    home_identity(home, args, fresh=False)
    require(not boundary.native_work_attempts and not boundary.denied, 'bootstrap_forbidden_effect')
    return {
        'handoff': wire.decode('ascii'), 'handoffSha256': hashlib.sha256(wire).hexdigest(),
        'previousEpoch': expectation.epoch, 'instanceId': args.instance_id,
        'profileIdentity': list(receipt.home_identity),
        'databaseIdentities': [list(v) for v in receipt.database_identities],
        'completedChecks': started['completedChecks'], 'allThreeConnectionsPhysicallyClosed': True,
        'ownerState': owner._stage, 'consumerState': consumer._stage,
        'profileLeaseReleasedNormally': True, 'retainedCapturedWhileLeaseHeld': True,
        'mount': {'mount_id': mount.mount_id, 'device': list(mount.device), 'root': mount.root,
                  'mount_point': mount.mount_point, 'filesystem': mount.filesystem},
        'auxiliaryInitialization': auxiliary, 'coldHelperCalls': boundary.helpers,
        'sqliteOpenCount': len(boundary.sqlite_opens),
        'qualifiedNativeSourceCount': len(consumer._source_proof[1]),
    }


def bootstrap(args, progress):
    started = time.monotonic()
    home = validate_arguments(args)
    validate_actor(args)
    os.umask(0o077)
    home_identity(home, args, fresh=True)
    progress['phase'] = 'VERIFY_INSTALLATION'
    installed = verify_installation()
    verified_at = time.monotonic()
    home_identity(home, args, fresh=True)
    configure_environment(home)
    boundary = OfflineBoundary(home, progress)
    sys.addaudithook(boundary)
    sys.setprofile(boundary.profile)
    threading.setprofile(boundary.profile)
    sys.path[:0] = [str(INSTALLATION / 'packages/claw-hermes'), str(INSTALLATION / 'native'),
                    str(INSTALLATION / 'dependencies')]
    progress.update(phase='NATIVE_IMPORTS', nativeEffectsAttempted=True)
    # Native diagnostics cannot become a second stdout protocol frame.
    try:
        with contextlib.redirect_stdout(sys.stderr):
            result = asyncio.run(native_lifecycle(home, args, progress, boundary))
    finally:
        # Observers must not outlive the native invocation into interpreter
        # teardown. The irreversible audit hook remains active on all paths.
        sys.setprofile(None)
        threading.setprofile(None)
    progress['phase'] = 'CHECK_EXECUTOR_SHUTDOWN'
    require(threading.active_count() == 1 and os.getppid() == args.parent_pid,
            'bootstrap_thread_or_parent_changed')
    home_identity(home, args, fresh=False)
    finished = time.monotonic()
    require((finished - started) * 1000 < MAX_ELAPSED_MILLIS, 'bootstrap_elapsed_budget')
    result.update(
        kind='R155A1_TASK_FREE_RETAINED_SEED', result='PASS', state='RETAINED_SEED_CREATED',
        phase='COMPLETE',
        installationReceiptSha256=installed['receiptSha256'],
        harnessCommit=installed['harnessCommit'], nativeFeature=installed['nativeFeature'],
        home=str(home), pid=os.getpid(), parentPid=os.getppid(),
        startTicks=int(Path('/proc/self/stat').read_text().rsplit(')', 1)[1].split()[19]),
        gatewayUid=args.gateway_uid, socketGroupGid=args.socket_group_gid,
        supplementaryGroups=os.getgroups(), resUid=list(os.getresuid()), resGid=list(os.getresgid()),
        mountNamespaceInode=Path('/proc/self/ns/mnt').stat().st_ino,
        mountNamespace=os.readlink('/proc/self/ns/mnt'),
        verificationMillis=int((verified_at - started) * 1000),
        nativeMillis=int((finished - verified_at) * 1000),
        totalMillis=int((finished - started) * 1000),
        normalLoopShutdown=True, outstandingAsyncTasks=0, outstandingThreads=0,
        executedTasks=0, realModelCalls=0, listenersCreated=0, apiAdmissionPublished=False,
        projectedReadinessAccepted=False, fullD3BAccepted=False,
        automaticCleanup=False, automaticRetry=False,
    )
    progress['phase'] = 'COMPLETE'
    require(len(canonical(result)) <= MAX_RESULT, 'bootstrap_result_size')
    return result


def main(argv=None):
    started = time.monotonic()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--home', required=True)
    parser.add_argument('--instance-id', required=True)
    for name in ('expected-profile-device', 'expected-profile-inode', 'gateway-uid',
                 'socket-group-gid', 'parent-pid'):
        parser.add_argument('--' + name, type=decimal, required=True)
    args = parser.parse_args(argv)
    progress = {'phase': 'ARGUMENTS', 'nativeEffectsAttempted': False}
    try:
        result = bootstrap(args, progress)
    except BaseException as exc:
        code = str(exc) if type(exc) is BootstrapRejected else 'bootstrap_operation_failed'
        if not re.fullmatch('[a-z_]{1,100}', code):
            code = 'bootstrap_operation_failed'
        failure = {'kind': 'R155A1_TASK_FREE_RETAINED_SEED', 'result': 'NOT_ACCEPTED',
                   'state': 'SEED_OUTCOME_UNKNOWN' if progress['nativeEffectsAttempted'] else 'REFUSED',
                   **progress, 'reason': code, 'reasonType': type(exc).__name__,
                   'totalMillis': int((time.monotonic() - started) * 1000),
                   'partialStatePreserved': True, 'automaticCleanup': False, 'automaticRetry': False,
                   'projectedReadinessAccepted': False, 'fullD3BAccepted': False}
        sys.stderr.buffer.write(canonical(failure)); sys.stderr.buffer.flush()
        return 2
    sys.stdout.buffer.write(canonical(result)); sys.stdout.buffer.flush()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
