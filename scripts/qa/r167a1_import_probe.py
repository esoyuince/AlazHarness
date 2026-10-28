"""Ordinary-user, fixed P2 service import qualification of a pinned installation.

The installed tree and runtime binaries are read back before and after imports.
Only a fresh owned temporary home may be written. No service constructor,
configuration loader, store, task, Node process or model is invoked by this
probe. Python audit hooks constrain cooperative import effects; they are not
an operating-system sandbox. Provider/plugin completeness remains unaccepted.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import os
from pathlib import Path
import platform
import re
import stat
import sys
import sysconfig
import tempfile
import threading
import traceback
import types

LAB = 'AlazHarness-D3B-P71C'
PYTHON = '/usr/bin/python3.12'
HARNESS = '1600eba430562795b9114209d1168bfa0d6ea5fd'
NATIVE = '5e3635c2cdfc2161fd20c089618bd7f2a7c12f2d'
MANIFEST = 'a3fde8b0ac808c375c4ecd0eab9f26938828b0d01cd4632ffa4234e47de38af8'
ARCHIVE = '43fc186b8f21e4f39e34364ae100c82e520317d6b06c8a100b29f3b26adcd56a'
DESTINATION = '/opt/alaz-r167a1'
SOURCE_LIMIT = 2 * 1024 * 1024
MODULES = (
    'gateway.platforms.api_server_borrowed_transport',
    'gateway.platforms.api_server_prepared',
    'gateway.platforms.api_server_metrics',
    'gateway.platforms.api_server_authority_runs',
    'hermes_cli.config', 'hermes_cli.plugins', 'agent.secret_sources.command',
    'gateway_service_factory', 'gateway_service_runtime', 'gateway_service_launch',
    'gateway_service_control', 'gateway_supervised_service',
    'service_control_server', 'service_task_http', 'service_task_server',
)


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def stamp(info):
    return (info.st_dev, info.st_ino, info.st_mode, info.st_uid, info.st_gid,
            info.st_nlink, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def load_installer(filename, expected_sha256):
    """Load reviewed tool bytes only; no candidate module is imported here."""
    require(re.fullmatch('[a-f0-9]{64}', expected_sha256) is not None,
            'import_installer_pin')
    path = Path(filename)
    require(path.is_absolute() and path.resolve(strict=True) == path
            and path.name == 'install_service_candidate.py', 'import_installer_path')
    for parent in path.parents:
        info = parent.lstat()
        require(stat.S_ISDIR(info.st_mode) and info.st_uid == info.st_gid == 0
                and not info.st_mode & 0o022, 'import_installer_ancestry')
    fd = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        info = os.fstat(fd)
        require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1
                and info.st_uid == info.st_gid == 0 and not info.st_mode & 0o022
                and 0 < info.st_size <= SOURCE_LIMIT, 'import_installer_metadata')
        with os.fdopen(fd, 'rb', closefd=False) as stream:
            raw = stream.read(SOURCE_LIMIT + 1)
        require(len(raw) == info.st_size and sha(raw) == expected_sha256
                and stamp(info) == stamp(os.fstat(fd)) == stamp(path.lstat()),
                'import_installer_bytes')
    finally:
        os.close(fd)
    module = types.ModuleType('_r167_reviewed_install_tool')
    module.__file__ = str(path)
    sys.modules[module.__name__] = module
    exec(compile(raw, str(path), 'exec'), module.__dict__)
    return module


def actor():
    require(os.environ.get('WSL_DISTRO_NAME') == LAB
            and Path('/etc/alaz-p71c-lab-id').read_text().strip() == LAB,
            'import_wrong_lab')
    require(sys.platform == 'linux' and platform.machine() == 'x86_64'
            and sys.version_info[:2] == (3, 12) and sys.executable == PYTHON
            and sys.flags.isolated == 1 and sys.dont_write_bytecode
            and not sys.flags.optimize, 'import_python_actor')
    require(os.getresuid() == (23001,) * 3 and os.getresgid() == (23003,) * 3,
            'import_ordinary_actor')
    require(not Path('/mnt/c/Windows').exists(), 'import_windows_mount_present')


def runtime_bytes(installer, runtimes):
    """Rehash executable files; do not re-execute historical version probes."""
    require(type(runtimes) is dict and set(runtimes) == {'python', 'node'},
            'import_runtime_fields')
    p = installer._legacy()
    result = {}
    for kind in ('python', 'node'):
        row = runtimes[kind]
        require(type(row) is dict and set(row) == {
            'path', 'sha256', 'bytes', 'device', 'inode', 'uid', 'gid', 'mode',
            'version', 'versionTuple', 'observedVersion', 'versionStdoutSha256'},
            'import_runtime_record_fields')
        path = p._absolute(row['path'])
        parent = p._directory(path.parent, trusted=True)
        fd = None
        try:
            fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC
                         | os.O_NONBLOCK, dir_fd=parent)
            digest, info = installer._binary_digest(fd)
            actual = {'path': str(path), 'sha256': digest, 'bytes': info.st_size,
                      'device': info.st_dev, 'inode': info.st_ino, 'uid': info.st_uid,
                      'gid': info.st_gid, 'mode': stat.S_IMODE(info.st_mode)}
            require(all(type(row[k]) is type(v) and row[k] == v
                        for k, v in actual.items()), 'import_runtime_bytes_changed')
            current_parent = p._directory(path.parent, trusted=True)
            try:
                require(stamp(info) == stamp(os.stat(path.name, dir_fd=current_parent,
                                                     follow_symlinks=False)),
                        'import_runtime_path_changed')
            finally:
                os.close(current_parent)
            observed = (row['observedVersion'] + '\n').encode('ascii')
            version = installer._parse_runtime_version(kind, observed)
            require(installer.canonical({key: row[key] for key in version})
                    == installer.canonical(version), 'import_runtime_version_record')
            if kind == 'python':
                require(str(path) == PYTHON and row['versionTuple'] == list(sys.version_info[:3])
                        and (info.st_dev, info.st_ino) ==
                        (Path('/proc/self/exe').stat().st_dev, Path('/proc/self/exe').stat().st_ino),
                        'import_running_python_identity')
            result[kind] = actual
        finally:
            if fd is not None:
                os.close(fd)
            os.close(parent)
    return result


def installed_bytes(installer, prepared, expected_receipt):
    p = installer._legacy()
    fd = p._directory(DESTINATION, trusted=True)
    try:
        info = os.fstat(fd)
        require(stat.S_IMODE(info.st_mode) == 0o755, 'import_installation_mode')
        raw, _ = p._read_at(fd, installer.RECEIPT, SOURCE_LIMIT, trusted=True)
        require(sha(raw) == expected_receipt, 'import_installation_receipt_pin')
        receipt = installer._verifier()._builder().unique_json(raw)
        depfd = p._directory(Path(DESTINATION) / 'dependencies', trusted=True)
        try:
            dependencies = p._tree(depfd, prepared.dependencies, trusted=True)
        finally:
            os.close(depfd)
        expected = installer._receipt(prepared, dependencies, receipt['runtimes'],
                                      p._absolute(DESTINATION), info)
        installer._verify_receipt(raw, expected)
        files, modes = installer._installation_files(prepared, dependencies)
        files[installer.RECEIPT], modes[installer.RECEIPT] = raw, 0o644
        p._tree(fd, {name: sha(data) for name, data in files.items()}, trusted=True,
                modes=modes, total_limit=p.DEPENDENCY_TOTAL_LIMIT + p._builder().MAX_TOTAL + SOURCE_LIMIT)
        binaries = runtime_bytes(installer, receipt['runtimes'])
        return receipt, binaries
    finally:
        os.close(fd)


def effect_guard(root, denied, active):
    def owned(raw, dir_fd=None):
        if isinstance(raw, int):
            path = Path(os.readlink('/proc/self/fd/' + str(raw)))
        else:
            path = Path(os.fsdecode(raw))
            if not path.is_absolute():
                base = Path.cwd() if dir_fd in (None, -1) else Path(os.readlink('/proc/self/fd/' + str(dir_fd)))
                path = base / path
        return path.resolve().is_relative_to(root)

    def reject(event):
        denied.append(event)
        raise PermissionError('r167_import_effect_refused')

    def audit(event, args):
        if not active[0]:
            return
        if event in {'socket.connect', 'socket.connect_ex', 'socket.bind', 'socket.getaddrinfo',
                     'socket.sendto', 'subprocess.Popen', 'os.system', 'os.exec',
                     'os.posix_spawn', 'os.fork', 'os.forkpty', 'sqlite3.connect'}:
            reject(event)
        if event == 'open':
            mode, flags = args[1:3]
            write = (isinstance(mode, str) and any(c in mode for c in 'wax+')) or (
                isinstance(flags, int) and bool(flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT
                                                        | os.O_TRUNC | os.O_APPEND)))
            if write and not owned(args[0]):
                reject('write_outside_owned_import_home')
        elif event in {'os.mkdir', 'os.chmod'} and not owned(args[0], args[2]):
            reject(event + '_outside_owned_import_home')
        elif event in {'os.remove', 'os.rmdir'} and not owned(args[0], args[1]):
            reject(event + '_outside_owned_import_home')
        elif event in {'os.utime', 'os.chown'} and not owned(args[0], args[3]):
            reject(event + '_outside_owned_import_home')
        elif event in {'os.setxattr', 'os.removexattr'} and not owned(args[0]):
            reject(event + '_outside_owned_import_home')
        elif event == 'os.rename' and not (owned(args[0], args[2]) and owned(args[1], args[3])):
            reject('rename_outside_owned_import_home')
        elif event == 'os.link' and not (owned(args[0], args[2]) and owned(args[1], args[3])):
            reject('link_outside_owned_import_home')
        elif event == 'os.symlink' and not owned(args[1], args[2]):
            reject('symlink_outside_owned_import_home')
        elif event == 'os.truncate' and not owned(args[0]):
            reject('truncate_outside_owned_import_home')
    return audit


def imported_origins(installer, prepared, tools, stdlib_roots):
    p = installer._legacy()
    root = Path(DESTINATION)
    native, dependencies = root / 'native', root / 'dependencies'
    result = {'native': {}, 'harness': {}, 'dependencies': {}, 'stdlib': {}, 'reviewedTools': {}}
    for module in tuple(sys.modules.values()):
        filename = getattr(module, '__file__', None)
        if not filename or filename.startswith('<'):
            continue
        path = Path(filename).resolve(strict=True)
        if not path.is_file():
            continue
        raw, _ = p._read_path(str(path), p.DEPENDENCY_FILE_LIMIT, trusted=True)
        digest = sha(raw)
        if path.is_relative_to(native):
            name = path.relative_to(native).as_posix()
            require(name.endswith('.py') and sha(prepared.source['native/' + name]) == digest,
                    'import_unqualified_native_origin')
            result['native'][name] = digest
        elif path.is_relative_to(dependencies):
            name = path.relative_to(dependencies).as_posix()
            require(prepared.dependencies.get(name) == digest, 'import_unqualified_dependency_origin')
            result['dependencies'][name] = digest
        elif path.is_relative_to(root):
            name = path.relative_to(root).as_posix()
            require(name in prepared.source and sha(prepared.source[name]) == digest,
                    'import_unqualified_harness_origin')
            result['harness'][name] = digest
        elif str(path) in tools:
            require(tools[str(path)] == digest, 'import_reviewed_tool_changed')
            result['reviewedTools'][str(path)] = digest
        else:
            require(not {'site-packages', 'dist-packages'}.intersection(path.parts)
                    and any(path.is_relative_to(base) for base in stdlib_roots),
                    'import_ambient_package_origin')
            result['stdlib'][str(path)] = digest
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--installer', required=True)
    parser.add_argument('--expected-installer-sha256', required=True)
    parser.add_argument('--candidate-directory', required=True)
    parser.add_argument('--expected-receipt-sha256', required=True)
    args = parser.parse_args()
    report = {'schema': 1, 'kind': 'R167A1_FIXED_SERVICE_IMPORT_PROBE',
              'result': 'NOT_ACCEPTED_IMPORT_PREFLIGHT', 'stage': 'PREFLIGHT',
              'installation': DESTINATION, 'harnessCommit': HARNESS, 'nativeFeature': NATIVE,
              'sourceManifestSha256': MANIFEST, 'archiveSha256': ARCHIVE,
              'serviceObjectsConstructedByProbe': False, 'serviceReadinessAccepted': False,
              'nativeRuntimeAccepted': False, 'kernelAcceptance': False,
              'providerDependencyCompletenessAccepted': False, 'realModelCalls': 0,
              'nodeExecuted': False, 'runtimeVersionsReexecuted': False,
              'sharedLibraryClosureAccepted': False, 'osConfinementTested': False,
              'auditGuardIsHostileCodeSandbox': False, 'installedTreeWritten': False}
    active = [False]
    temporary = None
    try:
        actor()
        require(re.fullmatch('[a-f0-9]{64}', args.expected_receipt_sha256) is not None,
                'import_receipt_pin')
        installer = load_installer(args.installer, args.expected_installer_sha256)
        p = installer._legacy()
        candidate = p._absolute(args.candidate_directory)
        prepared = installer._verifier().verify_files(candidate / 'manifest.json',
            candidate / 'service-source.tar', expected_manifest_sha256=MANIFEST,
            expected_archive_sha256=ARCHIVE, expected_harness_commit=HARNESS,
            expected_native_feature=NATIVE)
        require(len(prepared.source) == 878 and len(prepared.dependencies) == 1162,
                'import_expected_inventory')
        before_receipt, before_binaries = installed_bytes(installer, prepared, args.expected_receipt_sha256)
        tools = {}
        for module in tuple(sys.modules.values()):
            filename = getattr(module, '__file__', None)
            if filename and Path(filename).resolve().parent == Path(args.installer).parent:
                raw, _ = p._read_path(str(Path(filename).resolve()), SOURCE_LIMIT, trusted=True)
                tools[str(Path(filename).resolve())] = sha(raw)
        if '__file__' in globals():
            own_path = Path(__file__).resolve(strict=True)
            own_raw, _ = p._read_path(str(own_path), SOURCE_LIMIT, trusted=True)
            tools[str(own_path)] = sha(own_raw)
            report['probeSha256'] = sha(own_raw)
        stdlib_roots = tuple(sorted({Path(value).resolve() for value in (
            sysconfig.get_path('stdlib'), sysconfig.get_path('platstdlib'),
            sysconfig.get_config_var('DESTSHARED')) if value}))
        threads_before = {thread.ident for thread in threading.enumerate()}
        temporary = tempfile.TemporaryDirectory(prefix='alaz-r167a1-import-')
        root = Path(temporary.name).resolve()
        home, temp = root / 'home', root / 'tmp'
        home.mkdir(mode=0o700)
        temp.mkdir(mode=0o700)
        os.environ.clear()
        os.environ.update(PATH='/usr/bin:/bin', HOME=str(home), HERMES_HOME=str(home),
            USERPROFILE=str(home), APPDATA=str(home), LOCALAPPDATA=str(home),
            TMPDIR=str(temp), TMP=str(temp), TEMP=str(temp), LANG='C.UTF-8', TZ='UTC',
            WSL_DISTRO_NAME=LAB)
        os.chdir(home)
        install_root = Path(DESTINATION)
        sys.path[:] = [str(install_root / 'packages/claw-hermes'), str(install_root / 'native'),
                       str(install_root / 'dependencies'), *map(str, stdlib_roots)]
        denied = []
        report['deniedEvents'] = denied
        report['completedFixedImports'] = []
        sys.addaudithook(effect_guard(root, denied, active))
        active[0] = True
        report['stage'] = 'IMPORT'
        import gateway_service_sources as sources
        import gateway_prepared_consumer as consumer
        selection = sources.load_selection()
        proof = consumer.qualify_sources(local_admission=True, canonical_api=True,
                                         finite_turn=True, service_selection=selection)
        require(selection.native_feature == NATIVE and len(proof[1]) == 760,
                'import_native_selection')
        require(len(consumer.native_types()) == 7, 'import_native_type_exports')
        completed = []
        for name in MODULES:
            importlib.import_module(name)
            completed.append(name)
            report['completedFixedImports'].append(name)
        consumer.verify_imports(proof)
        require(not denied, 'import_forbidden_effect_attempted')
        require({thread.ident for thread in threading.enumerate()} == threads_before,
                'import_live_thread_created')
        origins = imported_origins(installer, prepared, tools, stdlib_roots)
        after_receipt, after_binaries = installed_bytes(installer, prepared, args.expected_receipt_sha256)
        require(installer.canonical(before_receipt) == installer.canonical(after_receipt)
                and before_binaries == after_binaries, 'import_installed_inputs_changed')
        report.update(result='PASS_FIXED_SERVICE_IMPORTS_ONLY', stage='COMPLETE',
            installationReceiptSha256=args.expected_receipt_sha256,
            installerSha256=args.expected_installer_sha256,
            sourceFileCount=len(prepared.source), dependencyFileCount=len(prepared.dependencies),
            sourceAndDependencyBytesReadBackBeforeAndAfter=True,
            runtimeBinaryBytesReadBackBeforeAndAfter=True,
            completedFixedImports=completed, importedOrigins=origins,
            nativeImportedFileCount=len(origins['native']),
            dependencyImportedFileCount=len(origins['dependencies']),
            deniedEvents=denied, pythonVersion=sys.version,
            uid=list(os.getresuid()), gid=list(os.getresgid()),
            temporaryFilesCreated=sorted(path.relative_to(root).as_posix()
                for path in root.rglob('*') if path.is_file()))
    except BaseException as exc:
        report.update(error={'type': type(exc).__name__,
            'reason': str(exc)[:1000], 'traceback': traceback.format_exc()[-6000:]})
    finally:
        os.chdir('/')
        if temporary is not None:
            try:
                temporary.cleanup()
                report['ownedTemporaryHomeRemoved'] = not Path(temporary.name).exists()
            except OSError as exc:
                report.update(result='NOT_ACCEPTED_IMPORT_PREFLIGHT',
                              ownedTemporaryHomeRemoved=False,
                              ownedTemporaryCleanupError=type(exc).__name__)
    print(json.dumps(report, sort_keys=True), flush=True)
    return 0 if report['result'] == 'PASS_FIXED_SERVICE_IMPORTS_ONLY' else 2


if __name__ == '__main__':
    raise SystemExit(main())
