"""Install and independently read back one explicitly pinned P2 source candidate.

Only the selected, hash-verified Python/Node executables are run, with builtin
version arguments and a clean environment. Candidate and dependency code is not
executed. Source installation is not service, kernel or model acceptance.
Existing destinations and failed staging trees are never replaced or removed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import selectors
import signal
import stat
import subprocess
import sys
import time
import types
import uuid
from functools import lru_cache

VERIFIER_SHA256 = 'ddd8fb60dc030c36c0aefcf2790c788d012dc13e39e37f1a14f5bcd0725e3288'
PYTHON = '/usr/bin/python3.12'
RECEIPT = '.alaz-service-installation.json'
MANIFEST_LIMIT = 2 * 1024 * 1024
BINARY_LIMIT = 256 * 1024 * 1024
PROBE_LIMIT = 4096
PROBE_TIMEOUT = 10.0
PROBE_ENV = {'PATH': '/usr/bin:/bin', 'LANG': 'C', 'LC_ALL': 'C'}


class InstallationRejected(ValueError):
    def __init__(self, reason, *, partial_path=None):
        super().__init__(reason)
        self.partial_path = partial_path


def require(ok, reason):
    if not ok:
        raise InstallationRejected(reason)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=True,
                       allow_nan=False) + '\n').encode('ascii')


@lru_cache(maxsize=1)
def _verifier():
    """Load only the exact reviewed sibling bytes, including its pinned chain."""
    path = Path(__file__).absolute().with_name('verify_service_candidate.py')
    require(not any(p.is_symlink() for p in (path, *path.parents)),
            'service_install_verifier_symlink')
    flags = os.O_RDONLY | getattr(os, 'O_CLOEXEC', 0) | getattr(os, 'O_NOFOLLOW', 0)
    fd = os.open(path, flags)
    try:
        before = os.fstat(fd)
        require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1
                and 0 < before.st_size <= MANIFEST_LIMIT,
                'service_install_verifier_file')
        with os.fdopen(fd, 'rb', closefd=False) as stream:
            raw = stream.read(MANIFEST_LIMIT + 1)
        after = os.fstat(fd)
        stamp = lambda s: (s.st_dev, s.st_ino, s.st_mode, s.st_uid, s.st_gid,
                           s.st_nlink, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
        require(len(raw) == before.st_size and stamp(before) == stamp(after)
                and digest(raw) == VERIFIER_SHA256, 'service_install_verifier_changed')
    finally:
        os.close(fd)
    name = '_alaz_install_reviewed_service_verifier_' + VERIFIER_SHA256
    module = types.ModuleType(name)
    module.__file__ = str(path)
    sys.modules[name] = module
    try:
        exec(compile(raw, str(path), 'exec'), module.__dict__)
        module._builder()  # Validate the complete existing pinned helper chain.
    except BaseException:
        sys.modules.pop(name, None)
        raise
    return module


def _legacy():
    return _verifier()._builder()._legacy()


def prepare_bytes(manifest_raw, archive_raw, **pins):
    """Pure four-pin candidate verification; never runtime or install acceptance."""
    return _verifier().prepare_bytes(manifest_raw, archive_raw, **pins)


def _platform():
    require(sys.platform == 'linux' and platform.machine() == 'x86_64',
            'service_install_linux_x86_64_required')


def _actor():
    # Preserve the original fixed CPython3.12/-I/-B/root/initial-userns contract.
    _legacy()._actor()


def _parse_runtime_version(kind, stdout):
    require(kind in ('python', 'node') and type(stdout) is bytes
            and 0 < len(stdout) <= 128, 'service_runtime_version_output')
    pattern = (rb'Python (3)\.(12)\.(0|[1-9][0-9]*)\n' if kind == 'python'
               else rb'v(24)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\n')
    match = re.fullmatch(pattern, stdout)
    require(match is not None, 'service_runtime_version_requirement')
    parts = [int(value) for value in match.groups()]
    return {'version': '.'.join(str(value) for value in parts),
            'versionTuple': parts, 'observedVersion': stdout.decode('ascii').rstrip('\n'),
            'versionStdoutSha256': digest(stdout)}


def _stop_probe(process):
    """Terminate only this owned session; never claim an unconfirmed stop."""
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    try:
        process.wait(timeout=2)
    except subprocess.TimeoutExpired as exc:
        raise InstallationRejected('service_runtime_probe_termination_unconfirmed') from exc


def _capture_bounded(command, *, pass_fds=(), env=None,
                     timeout=PROBE_TIMEOUT, limit=PROBE_LIMIT):
    """Capture an owned version process within a combined byte and time bound."""
    _platform()
    require(type(command) is list and command and all(type(s) is str for s in command)
            and type(limit) is int and 0 < limit <= PROBE_LIMIT
            and type(timeout) in (int, float) and 0 < timeout <= PROBE_TIMEOUT,
            'service_runtime_probe_arguments')
    process = subprocess.Popen(command, stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd='/',
        env=dict(PROBE_ENV if env is None else env), close_fds=True,
        pass_fds=pass_fds, start_new_session=True)
    selector = None
    try:
        streams = {'stdout': bytearray(), 'stderr': bytearray()}
        deadline = time.monotonic() + timeout
        selector = selectors.DefaultSelector()
        for key, pipe in (('stdout', process.stdout), ('stderr', process.stderr)):
            os.set_blocking(pipe.fileno(), False)
            selector.register(pipe, selectors.EVENT_READ, key)
        while selector.get_map():
            remaining = deadline - time.monotonic()
            require(remaining > 0, 'service_runtime_probe_timeout')
            for key, _ in selector.select(min(remaining, 0.1)):
                total = sum(len(value) for value in streams.values())
                try:
                    chunk = os.read(key.fd, min(65536, limit - total + 1))
                except BlockingIOError:
                    continue
                if not chunk:
                    selector.unregister(key.fileobj)
                    continue
                streams[key.data].extend(chunk)
                require(sum(len(value) for value in streams.values()) <= limit,
                        'service_runtime_probe_output_limit')
        remaining = deadline - time.monotonic()
        require(remaining > 0, 'service_runtime_probe_timeout')
        try:
            code = process.wait(timeout=remaining)
        except subprocess.TimeoutExpired as exc:
            raise InstallationRejected('service_runtime_probe_timeout') from exc
        return subprocess.CompletedProcess(command, code, bytes(streams['stdout']),
                                           bytes(streams['stderr']))
    except BaseException:
        _stop_probe(process)
        raise
    finally:
        if selector is not None:
            selector.close()
        process.stdout.close()
        process.stderr.close()


def _binary_digest(fd):
    p = _legacy()
    info = os.fstat(fd)
    p._trusted(info, False)
    require(64 <= info.st_size <= BINARY_LIMIT and info.st_mode & 0o111
            and not info.st_mode & 0o7000, 'service_runtime_executable_metadata')
    os.lseek(fd, 0, os.SEEK_SET)
    hashed = hashlib.sha256()
    size = 0
    header = b''
    while True:
        part = os.read(fd, min(1024 * 1024, BINARY_LIMIT - size + 1))
        if not part:
            break
        if not header:
            header = part[:64]
        size += len(part)
        require(size <= BINARY_LIMIT, 'service_runtime_executable_limit')
        hashed.update(part)
    require(size == info.st_size and p._stamp(info) == p._stamp(os.fstat(fd)),
            'service_runtime_executable_changed')
    require(header[:6] == b'\x7fELF\x02\x01' and header[18:20] == b'\x3e\x00'
            and header[16:18] in (b'\x02\x00', b'\x03\x00'),
            'service_runtime_linux_x86_64_elf_required')
    return hashed.hexdigest(), info


def _runtime_readback(path, expected_sha256, kind):
    """Verify root-controlled executable bytes, then probe that held descriptor."""
    _platform()
    p = _legacy()
    p._hex(expected_sha256, 64, 'service_runtime_external_pin')
    require(kind in ('python', 'node'), 'service_runtime_kind')
    path = p._absolute(path)
    parent = p._directory(path.parent, trusted=True)
    fd = None
    try:
        fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC
                     | os.O_NONBLOCK, dir_fd=parent)
        actual, before = _binary_digest(fd)
        require(actual == expected_sha256, 'service_runtime_executable_digest')
        command = ['/proc/self/fd/' + str(fd)]
        command += ['-I', '-S', '-B', '--version'] if kind == 'python' else ['--version']
        result = _capture_bounded(command, pass_fds=(fd,), env=PROBE_ENV,
                                  timeout=PROBE_TIMEOUT, limit=PROBE_LIMIT)
        require(result.returncode == 0 and result.stderr == b'',
                'service_runtime_version_process')
        version = _parse_runtime_version(kind, result.stdout)
        after_digest, after = _binary_digest(fd)
        require(after_digest == actual and p._stamp(before) == p._stamp(after),
                'service_runtime_executable_changed')
        # Re-walk the canonical name rather than trusting only the old parent FD.
        current_parent = p._directory(path.parent, trusted=True)
        try:
            current = os.stat(path.name, dir_fd=current_parent, follow_symlinks=False)
            require(p._stamp(current) == p._stamp(before),
                    'service_runtime_executable_path_changed')
        finally:
            os.close(current_parent)
        return {'path': str(path), 'sha256': actual, 'bytes': before.st_size,
            'device': before.st_dev, 'inode': before.st_ino,
            'uid': before.st_uid, 'gid': before.st_gid,
            'mode': stat.S_IMODE(before.st_mode), **version}
    finally:
        if fd is not None:
            os.close(fd)
        os.close(parent)


def _runtimes(*, expected_python_sha256, node_path, expected_node_sha256):
    p = _legacy()
    p._hex(expected_python_sha256, 64, 'service_runtime_python_pin')
    p._hex(expected_node_sha256, 64, 'service_runtime_node_pin')
    p._absolute(node_path)
    return {'python': _runtime_readback(PYTHON, expected_python_sha256, 'python'),
            'node': _runtime_readback(node_path, expected_node_sha256, 'node')}


def preflight(candidate_directory, dependencies, *, expected_manifest_sha256,
              expected_archive_sha256, expected_harness_commit, expected_native_feature,
              expected_python_sha256, node_path, expected_node_sha256):
    p = _legacy()
    b = _verifier()._builder()
    candidate_directory = p._absolute(candidate_directory)
    prepared = _verifier().verify_files(candidate_directory / 'manifest.json',
        candidate_directory / b.ARCHIVE, expected_manifest_sha256=expected_manifest_sha256,
        expected_archive_sha256=expected_archive_sha256,
        expected_harness_commit=expected_harness_commit,
        expected_native_feature=expected_native_feature)
    _platform()
    fd = p._directory(dependencies, trusted=True)
    try:
        dependency_bytes = p._tree(fd, prepared.dependencies, trusted=True)
    finally:
        os.close(fd)
    runtimes = _runtimes(expected_python_sha256=expected_python_sha256,
                        node_path=node_path, expected_node_sha256=expected_node_sha256)
    return prepared, dependency_bytes, runtimes


def _installation_files(prepared, dependency_bytes):
    p = _legacy()
    require(type(dependency_bytes) is dict
            and set(dependency_bytes) == set(prepared.dependencies)
            and all(type(data) is bytes and digest(data) == prepared.dependencies[name]
                    for name, data in dependency_bytes.items()),
            'service_install_dependency_bytes')
    files, modes = dict(prepared.source), dict(prepared.source_modes)
    dependencies = {'dependencies/' + name: data for name, data in dependency_bytes.items()}
    require(not set(files).intersection(dependencies), 'service_install_namespace_collision')
    files.update(dependencies)
    modes.update({name: 0o644 for name in dependencies})
    p._namespace(files)
    return files, modes


def _receipt(prepared, dependency_bytes, runtimes, destination, info):
    return {'schemaVersion': 1, 'kind': 'VERIFIED_SERVICE_INSTALLATION',
        'destination': str(destination), 'sourceManifestSha256': prepared.manifest_sha256,
        'archiveSha256': prepared.archive_sha256, 'harnessCommit': prepared.harness_commit,
        'nativeFeature': prepared.native_feature, 'sourceFileCount': len(prepared.source),
        'dependencyFileCount': len(dependency_bytes),
        'dependencyInventorySha256': prepared.dependency_inventory_sha256,
        'runtimes': runtimes, 'rootDevice': info.st_dev, 'rootInode': info.st_ino,
        'sourceAndDependenciesReadBack': True, 'runtimeExecutableBytesVerified': True,
        'runtimeVersionReadback': True, 'rootControlledAncestryVerified': True,
        'installed': True, 'executionAuthorized': False,
        'dependenciesAcceptedForService': False, 'serviceReadinessAccepted': False,
        'nativeRuntimeAccepted': False, 'kernelAcceptance': False,
        'realModelAcceptance': False, 'realModelCalls': 0}


def _verify_receipt(raw, expected):
    actual = _verifier()._builder().unique_json(raw)
    require(canonical(actual) == canonical(expected), 'service_install_receipt_identity')


def _reread_runtimes(pins, expected):
    actual = _runtimes(expected_python_sha256=pins['expected_python_sha256'],
        node_path=pins['node_path'], expected_node_sha256=pins['expected_node_sha256'])
    require(canonical(actual) == canonical(expected), 'service_install_runtimes_changed')


def install(candidate_directory, destination, dependencies, **pins):
    _actor()
    p = _legacy()
    destination = p._absolute(destination)
    require(destination.name and destination.parent != destination,
            'service_install_destination_root_refused')
    prepared, dependency_bytes, runtimes = preflight(candidate_directory, dependencies, **pins)
    parent = p._directory(destination.parent, trusted=True)
    stage = '.' + destination.name + '.partial-' + uuid.uuid4().hex
    partial = str(destination.parent / stage)
    created = published = False
    root = None
    try:
        p._absent(parent, destination.name)
        os.mkdir(stage, 0o700, dir_fd=parent)
        created = True
        root = os.open(stage, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
                       dir_fd=parent)
        p._trusted(os.fstat(root), True)
        files, modes = _installation_files(prepared, dependency_bytes)
        p._materialize(root, files, modes)
        p._tree(root, {name: digest(data) for name, data in files.items()}, trusted=True,
                modes=modes, total_limit=p.DEPENDENCY_TOTAL_LIMIT + _verifier()._builder().MAX_TOTAL)
        dependency_fd = p._directory(dependencies, trusted=True)
        try:
            p._tree(dependency_fd, prepared.dependencies, trusted=True)
        finally:
            os.close(dependency_fd)
        _reread_runtimes(pins, runtimes)
        receipt = _receipt(prepared, dependency_bytes, runtimes, destination, os.fstat(root))
        receipt_raw = canonical(receipt)
        os.fchmod(root, 0o755)
        os.fsync(root)
        p._rename_noreplace(parent, stage, destination.name)
        published = True
        os.fsync(parent)
        pending = RECEIPT + '.pending'
        p._write_at(root, pending, receipt_raw, 0o644)
        readback, _ = p._read_at(root, pending, MANIFEST_LIMIT, trusted=True)
        require(readback == receipt_raw, 'service_install_receipt_readback')
        os.fsync(root)
        p._rename_noreplace(root, pending, RECEIPT)
        os.fsync(root)
        return {**receipt, 'receiptSha256': digest(receipt_raw)}
    except BaseException as exc:
        if isinstance(exc, (KeyboardInterrupt, SystemExit)):
            raise
        reason = str(exc) if isinstance(exc, ValueError) else 'service_install_local_io_failed'
        raise InstallationRejected(reason,
            partial_path=(str(destination) if published else partial) if created else None) from exc
    finally:
        if root is not None:
            os.close(root)
        os.close(parent)


def verify_installed(candidate_directory, destination, dependencies, **pins):
    """Read back every installed byte and both runtime identities as any reader."""
    prepared, dependency_bytes, runtimes = preflight(candidate_directory, dependencies, **pins)
    p = _legacy()
    destination = p._absolute(destination)
    fd = p._directory(destination, trusted=True)
    try:
        info = os.fstat(fd)
        require(stat.S_IMODE(info.st_mode) == 0o755, 'service_install_root_mode')
        raw, _ = p._read_at(fd, RECEIPT, MANIFEST_LIMIT, trusted=True)
        expected = _receipt(prepared, dependency_bytes, runtimes, destination, info)
        _verify_receipt(raw, expected)
        files, modes = _installation_files(prepared, dependency_bytes)
        files[RECEIPT], modes[RECEIPT] = raw, 0o644
        p._tree(fd, {name: digest(data) for name, data in files.items()}, trusted=True,
                modes=modes, total_limit=p.DEPENDENCY_TOTAL_LIMIT
                + _verifier()._builder().MAX_TOTAL + MANIFEST_LIMIT)
        _reread_runtimes(pins, runtimes)
        return {**expected, 'receiptSha256': digest(raw), 'verifiedInstalledBytesNow': True}
    finally:
        os.close(fd)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate-directory', required=True)
    parser.add_argument('--destination', required=True)
    parser.add_argument('--dependencies', required=True)
    parser.add_argument('--node-path', required=True)
    for name in ('manifest-sha256', 'archive-sha256', 'harness-commit', 'native-feature',
                 'python-sha256', 'node-sha256'):
        parser.add_argument('--expected-' + name, required=True)
    actions = parser.add_mutually_exclusive_group()
    actions.add_argument('--verify-only', action='store_true')
    actions.add_argument('--verify-installed', action='store_true')
    args = parser.parse_args()
    pins = {name: getattr(args, name) for name in ('expected_manifest_sha256',
        'expected_archive_sha256', 'expected_harness_commit', 'expected_native_feature',
        'expected_python_sha256', 'node_path', 'expected_node_sha256')}
    try:
        if args.verify_only:
            prepared, deps, runtimes = preflight(args.candidate_directory, args.dependencies, **pins)
            p = _legacy()
            destination = p._absolute(args.destination)
            require(destination.name and destination.parent != destination,
                    'service_install_destination_root_refused')
            fd = p._directory(destination.parent, trusted=True)
            try:
                p._absent(fd, destination.name)
            finally:
                os.close(fd)
            result = {'kind': 'VERIFIED_SERVICE_INSTALLATION_INPUTS',
                'harnessCommit': prepared.harness_commit, 'nativeFeature': prepared.native_feature,
                'sourceManifestSha256': prepared.manifest_sha256,
                'archiveSha256': prepared.archive_sha256, 'sourceFileCount': len(prepared.source),
                'dependencyFileCount': len(deps), 'runtimes': runtimes,
                'runtimeExecutableBytesVerified': True, 'runtimeVersionReadback': True,
                'installed': False, 'executionAuthorized': False,
                'dependenciesAcceptedForService': False, 'serviceReadinessAccepted': False,
                'kernelAcceptance': False, 'realModelAcceptance': False, 'realModelCalls': 0}
        elif args.verify_installed:
            result = verify_installed(args.candidate_directory, args.destination, args.dependencies, **pins)
        else:
            result = install(args.candidate_directory, args.destination, args.dependencies, **pins)
    except (OSError, ValueError) as exc:
        print(json.dumps({'result': 'REFUSED', 'reasonType': type(exc).__name__,
            'reason': str(exc) if isinstance(exc, ValueError) else 'service_install_local_io_failed',
            'partialPath': getattr(exc, 'partial_path', None), 'installed': False,
            'executionAuthorized': False, 'serviceReadinessAccepted': False,
            'kernelAcceptance': False, 'realModelAcceptance': False,
            'realModelCalls': 0}), file=sys.stderr)
        return 2
    print(json.dumps({'result': 'PASS', **result}, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
