"""Qualify fixed imports with one observed, denied urllib3 IPv6 capability probe.

This is a different gate from the frozen strict R167 import probe. Its exact
guard still denies every bind. One source-pinned import-time attempt may be
classified only after the real socket is closed and HAS_IPV6 is False. All
other denials fail qualification. No service, store, provider or model starts.
Execute only as hash-verified in-memory source with the ordinary lab actor.
The frozen v1 probe, installed inputs and installation receipt are not changed.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import os
from pathlib import Path
import re
import socket
import stat
import sys
import sysconfig
import tempfile
import threading
import traceback
import types

COMPILE_NAME = '<reviewed-r167-import-qualification>'
SUPPORT = '/opt/alaz-r167a1-input/qa/r167a1_import_probe.py'
SUPPORT_SHA = '9261a63ab741cefe0df32296cdced122e29e420278075bb8a5f295de2b826bab'
INSTALLER = '/opt/alaz-r167a1-input/scripts/install_service_candidate.py'
INSTALLER_SHA = 'bc014b7e4f9ac2a0c6d170e80501eee5e458d526a2b21c4f076bfa4f590de30a'
CANDIDATE = '/opt/alaz-r167a1-input/candidate'
CONNECTION_NAME = 'urllib3/util/connection.py'
CONNECTION_PATH = '/opt/alaz-r167a1/dependencies/' + CONNECTION_NAME
CONNECTION_SHA = '2633bbdb69731e5ccb5cf4e4afd65605d86c7979cc5633126f50c92d5ad74a74'
CONNECTION_BYTES = 4444
METADATA_NAME = 'urllib3-2.8.0.dist-info/METADATA'
METADATA_SHA = '10898c620e8007c030e07fa5622b68358a43010025dfbd78a1cb797699de2bb4'
SOURCE_LIMIT = 64 * 1024


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def stamp(info):
    return (info.st_dev, info.st_ino, info.st_mode, info.st_uid, info.st_gid,
            info.st_nlink, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def source_identity(expected):
    """Bind these executing source bytes to the operator's external transport pin."""
    require(type(expected) is str and re.fullmatch('[a-f0-9]{64}', expected),
            'qualification_source_pin')
    raw = globals().get('__reviewed_source_bytes__')
    require(type(raw) is bytes and 0 < len(raw) <= SOURCE_LIMIT and sha(raw) == expected,
            'qualification_transported_source_identity')
    require('__file__' not in globals() and main.__code__.co_filename == COMPILE_NAME,
            'qualification_in_memory_source_mode')
    return {'mode': 'hash_verified_in_memory', 'sha256': sha(raw), 'bytes': len(raw),
            'compileFilename': COMPILE_NAME, 'fileBackedIdentityClaimed': False}


def load_support():
    """Load only the unchanged, previously reviewed v1 helper definitions."""
    path = Path(SUPPORT)
    require(path.resolve(strict=True) == path, 'qualification_support_canonical_path')
    for parent in path.parents:
        info = parent.lstat()
        require(stat.S_ISDIR(info.st_mode) and info.st_uid == info.st_gid == 0
                and not info.st_mode & 0o022, 'qualification_support_ancestry')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC)
    try:
        info = os.fstat(fd)
        require(stat.S_ISREG(info.st_mode) and info.st_uid == info.st_gid == 0
                and info.st_nlink == 1 and not info.st_mode & 0o022
                and 0 < info.st_size <= SOURCE_LIMIT, 'qualification_support_metadata')
        with os.fdopen(fd, 'rb', closefd=False) as stream:
            raw = stream.read(SOURCE_LIMIT + 1)
        require(len(raw) == info.st_size and sha(raw) == SUPPORT_SHA
                and stamp(info) == stamp(os.fstat(fd)) == stamp(path.lstat()),
                'qualification_support_bytes')
    finally:
        os.close(fd)
    module = types.ModuleType('_r167_frozen_import_support')
    module.__file__ = str(path)
    sys.modules[module.__name__] = module
    exec(compile(raw, str(path), 'exec'), module.__dict__)
    return module


class DeniedIPv6Observation:
    """Observe one exact caller, then delegate denial to the unchanged v1 guard."""

    def __init__(self, frozen_guard, active, denied, phase, modules):
        self.frozen_guard, self.active, self.denied = frozen_guard, active, denied
        self.phase, self.modules = phase, frozenset(modules)
        self.observations, self.held = [], []

    def observe(self, args, caller):
        module = sys.modules.get('urllib3.util.connection')
        original = getattr(module, '_has_ipv6', None) if module is not None else None
        shape = type(args) is tuple and len(args) == 2
        sock, address = args if shape else (None, None)
        address_ok = (type(address) is tuple and len(address) == 2
                      and type(address[0]) is str and address[0] == '::1'
                      and type(address[1]) is int and address[1] == 0)
        socket_ok = (type(sock) is socket.socket and sock.family == socket.AF_INET6
                     and sock.type == socket.SOCK_STREAM and sock.proto == 0
                     and sock.fileno() >= 0)
        parent = caller.f_back
        checks = {
            'firstBindObservation': not self.observations and not self.held,
            'fixedImportPhase': self.phase[0] in ('SOURCE_QUALIFICATION', 'NATIVE_TYPES')
                or self.phase[0] in {'FIXED_IMPORT:' + name for name in self.modules},
            'moduleIdentity': module is not None and getattr(module, '__file__', None) == CONNECTION_PATH,
            'originalCallable': type(original) is types.FunctionType
                and original.__name__ == '_has_ipv6' and original.__module__ == 'urllib3.util.connection',
            'callableCodeIdentity': type(original) is types.FunctionType
                and caller.f_code is original.__code__,
            'callerSource': caller.f_code.co_filename == CONNECTION_PATH
                and caller.f_code.co_name == '_has_ipv6' and caller.f_code.co_firstlineno == 114
                and caller.f_lineno == 127,
            'callerGlobals': module is not None and caller.f_globals is vars(module),
            'callerLocals': caller.f_locals.get('host') == '::1'
                and caller.f_locals.get('sock') is sock and caller.f_locals.get('has_ipv6') is False,
            'moduleImportCallsite': parent is not None and module is not None
                and parent.f_globals is vars(module) and parent.f_code.co_filename == CONNECTION_PATH
                and parent.f_code.co_name == '<module>' and parent.f_lineno == 137,
            'argumentShape': shape, 'exactLoopbackEphemeralAddress': address_ok,
            'exactOpenIPv6StreamSocket': socket_ok,
        }
        sources = []
        frame = caller
        for _ in range(24):
            if frame is None:
                break
            sources.append({'file': frame.f_code.co_filename[:320],
                            'function': frame.f_code.co_name[:96], 'line': frame.f_lineno})
            frame = frame.f_back
        row = {'event': 'socket.bind', 'phase': self.phase[0], 'checks': checks,
               'qualifiedOrigin': all(checks.values()), 'guardDenied': False,
               'source': {'file': CONNECTION_PATH, 'sha256': CONNECTION_SHA,
                          'function': '_has_ipv6', 'functionFirstLine': 114, 'bindLine': 127},
               'address': ['::1', 0] if address_ok else None,
               'socketDescriptorAtAttempt': sock.fileno() if type(sock) is socket.socket else None,
               'stack': sources, 'bindPerformed': None, 'socketClosed': False,
               'hasIPv6AfterImports': None}
        return row, (sock, original, caller.f_code, module)

    def __call__(self, event, args):
        if not self.active[0] or event != 'socket.bind':
            return self.frozen_guard(event, args)
        try:
            row, held = self.observe(args, sys._getframe(1))
        except Exception as exc:
            row, held = {'event': event, 'phase': self.phase[0], 'qualifiedOrigin': False,
                         'observationError': type(exc).__name__, 'guardDenied': False}, None
        if len(self.observations) < 16:
            self.observations.append(row)
        try:
            self.frozen_guard(event, args)
        except PermissionError:
            row.update(guardDenied=True, bindPerformed=False)
            if row['qualifiedOrigin'] and held is not None:
                self.held.append(held)
            raise
        # The exact frozen guard is expected to raise. Never allow a bind if
        # a future programming error breaks that expectation.
        row['guardUnexpectedlyReturned'] = True
        raise PermissionError('qualification_bind_remains_denied')

    def verify_closed(self):
        require(self.denied == ['socket.bind'] and len(self.observations) == len(self.held) == 1,
                'qualification_unclassified_or_duplicate_denial')
        row = self.observations[0]
        sock, original, code, module = self.held[0]
        current = sys.modules.get('urllib3.util.connection')
        stable = (current is module and getattr(current, '__file__', None) == CONNECTION_PATH
                  and getattr(current, '_has_ipv6', None) is original and original.__code__ is code)
        closed = sock.fileno() == -1
        false_result = current is not None and getattr(current, 'HAS_IPV6', None) is False
        row.update(socketClosed=closed, hasIPv6AfterImports=False if false_result else None,
                   callableIdentityUnchangedAfterImports=stable)
        require(row['qualifiedOrigin'] is True and row['guardDenied'] is True
                and row['bindPerformed'] is False and stable and closed and false_result,
                'qualification_optional_probe_not_closed_or_not_false')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--expected-probe-sha256', required=True)
    parser.add_argument('--expected-receipt-sha256', required=True)
    args = parser.parse_args()
    report = {'schema': 1, 'kind': 'R167A1_QUALIFIED_FIXED_SERVICE_IMPORTS',
              'result': 'NOT_ACCEPTED_QUALIFIED_IMPORTS', 'stage': 'PREFLIGHT',
              'acceptancePolicy': 'fixed_imports_with_one_denied_pinned_urllib3_ipv6_capability_probe',
              'frozenStrictProbeSha256': SUPPORT_SHA, 'frozenGuardUsed': False,
              'isolated': sys.flags.isolated, 'noSite': sys.flags.no_site,
              'strictZeroDeniedEventsPolicySatisfied': False,
              'installedTreeWritten': False, 'frozenInstallationInputsWritten': False,
              'serviceObjectsConstructedByProbe': False, 'serviceReadinessAccepted': False,
              'nativeRuntimeAccepted': False, 'providerDependencyCompletenessAccepted': False,
              'kernelAcceptance': False, 'realModelCalls': 0, 'nodeExecuted': False,
              'runtimeVersionsReexecuted': False, 'sharedLibraryClosureAccepted': False,
              'osConfinementTested': False, 'auditGuardIsHostileCodeSandbox': False}
    active, phase, denied = [False], ['PREFLIGHT'], []
    temporary = observer = None
    try:
        report['sourceIdentity'] = source_identity(args.expected_probe_sha256)
        helper = load_support()
        helper.actor()
        require(sys.flags.no_site == 1, 'qualification_site_startup_disabled_required')
        require(re.fullmatch('[a-f0-9]{64}', args.expected_receipt_sha256), 'qualification_receipt_pin')
        installer = helper.load_installer(INSTALLER, INSTALLER_SHA)
        p = installer._legacy()
        prepared = installer._verifier().verify_files(Path(CANDIDATE) / 'manifest.json',
            Path(CANDIDATE) / 'service-source.tar', expected_manifest_sha256=helper.MANIFEST,
            expected_archive_sha256=helper.ARCHIVE, expected_harness_commit=helper.HARNESS,
            expected_native_feature=helper.NATIVE)
        require(len(prepared.source) == 878 and len(prepared.dependencies) == 1162,
                'qualification_inventory_counts')
        require(prepared.dependencies.get(CONNECTION_NAME) == CONNECTION_SHA
                and prepared.dependencies.get(METADATA_NAME) == METADATA_SHA,
                'qualification_urllib3_inventory_pins')
        before_receipt, before_binaries = helper.installed_bytes(installer, prepared, args.expected_receipt_sha256)
        raw, _ = p._read_path(CONNECTION_PATH, SOURCE_LIMIT, trusted=True)
        require(len(raw) == CONNECTION_BYTES and sha(raw) == CONNECTION_SHA,
                'qualification_urllib3_source_pin')
        metadata, _ = p._read_path(str(Path(helper.DESTINATION) / 'dependencies' / METADATA_NAME),
                                   SOURCE_LIMIT, trusted=True)
        require(sha(metadata) == METADATA_SHA and b'\nName: urllib3\n' in metadata
                and b'\nVersion: 2.8.0\n' in metadata, 'qualification_urllib3_version_pin')
        require(not any(name == 'urllib3' or name.startswith('urllib3.') for name in sys.modules),
                'qualification_urllib3_already_imported')
        report.update(installation=helper.DESTINATION, harnessCommit=helper.HARNESS,
                      nativeFeature=helper.NATIVE, sourceManifestSha256=helper.MANIFEST,
                      archiveSha256=helper.ARCHIVE, sourceFileCount=878, dependencyFileCount=1162,
                      installationReceiptSha256=args.expected_receipt_sha256,
                      urllib3Version='2.8.0', urllib3ConnectionSha256=CONNECTION_SHA,
                      urllib3MetadataSha256=METADATA_SHA)
        tools = {SUPPORT: SUPPORT_SHA}
        for module in tuple(sys.modules.values()):
            filename = getattr(module, '__file__', None)
            if filename and Path(filename).resolve().parent == Path(INSTALLER).parent:
                path = Path(filename).resolve()
                content, _ = p._read_path(str(path), helper.SOURCE_LIMIT, trusted=True)
                tools[str(path)] = sha(content)
        stdlib_roots = tuple(sorted({Path(value).resolve() for value in (
            sysconfig.get_path('stdlib'), sysconfig.get_path('platstdlib'),
            sysconfig.get_config_var('DESTSHARED')) if value}))
        threads_before = {thread.ident for thread in threading.enumerate()}
        temporary = tempfile.TemporaryDirectory(prefix='alaz-r167a1-qualified-import-')
        root = Path(temporary.name).resolve()
        home, temp = root / 'home', root / 'tmp'
        home.mkdir(mode=0o700)
        temp.mkdir(mode=0o700)
        os.environ.clear()
        os.environ.update(PATH='/usr/bin:/bin', HOME=str(home), HERMES_HOME=str(home),
            USERPROFILE=str(home), APPDATA=str(home), LOCALAPPDATA=str(home),
            TMPDIR=str(temp), TMP=str(temp), TEMP=str(temp), LANG='C.UTF-8', TZ='UTC',
            WSL_DISTRO_NAME=helper.LAB)
        os.chdir(home)
        install_root = Path(helper.DESTINATION)
        sys.path[:] = [str(install_root / 'packages/claw-hermes'), str(install_root / 'native'),
                       str(install_root / 'dependencies'), *map(str, stdlib_roots)]
        observer = DeniedIPv6Observation(helper.effect_guard(root, denied, active),
                                        active, denied, phase, helper.MODULES)
        report['deniedEvents'] = denied
        report['blockedCapabilityObservations'] = observer.observations
        report['completedFixedImports'] = []
        sys.addaudithook(observer)
        report['frozenGuardUsed'] = True
        active[0] = True
        report['stage'] = 'IMPORT'
        phase[0] = 'SOURCE_QUALIFICATION'
        import gateway_service_sources as sources
        import gateway_prepared_consumer as consumer
        selection = sources.load_selection()
        proof = consumer.qualify_sources(local_admission=True, canonical_api=True,
                                         finite_turn=True, service_selection=selection)
        require(selection.native_feature == helper.NATIVE and len(proof[1]) == 760,
                'qualification_native_selection')
        phase[0] = 'NATIVE_TYPES'
        require(len(consumer.native_types()) == 7, 'qualification_native_type_exports')
        for name in helper.MODULES:
            phase[0] = 'FIXED_IMPORT:' + name
            importlib.import_module(name)
            report['completedFixedImports'].append(name)
        phase[0] = 'VERIFY'
        consumer.verify_imports(proof)
        require({thread.ident for thread in threading.enumerate()} == threads_before,
                'qualification_live_thread_created')
        origins = helper.imported_origins(installer, prepared, tools, stdlib_roots)
        after_receipt, after_binaries = helper.installed_bytes(installer, prepared, args.expected_receipt_sha256)
        require(installer.canonical(before_receipt) == installer.canonical(after_receipt)
                and before_binaries == after_binaries, 'qualification_installed_inputs_changed')
        report.update(sourceAndDependencyBytesReadBackBeforeAndAfter=True,
                      runtimeBinaryBytesReadBackBeforeAndAfter=True,
                      importedOrigins=origins, nativeImportedFileCount=len(origins['native']),
                      dependencyImportedFileCount=len(origins['dependencies']))
        observer.verify_closed()
        report.update(result='PASS_FIXED_IMPORTS_WITH_DENIED_IPV6_PROBE', stage='COMPLETE',
                      guardRemainsActiveThroughProcessExit=True,
                      qualifiedBlockedProbeCount=1, unclassifiedDeniedEvents=[],
                      pythonVersion=sys.version, uid=list(os.getresuid()), gid=list(os.getresgid()),
                      temporaryFilesCreated=sorted(path.relative_to(root).as_posix()
                          for path in root.rglob('*') if path.is_file()))
    except BaseException as exc:
        report.update(error={'type': type(exc).__name__, 'reason': str(exc)[:1000],
                             'traceback': traceback.format_exc()[-6000:]})
    finally:
        phase[0] = 'CLEANUP'
        os.chdir('/')
        if temporary is not None:
            try:
                temporary.cleanup()
                report['ownedTemporaryHomeRemoved'] = not Path(temporary.name).exists()
            except OSError as exc:
                report.update(result='NOT_ACCEPTED_QUALIFIED_IMPORTS', ownedTemporaryHomeRemoved=False,
                              ownedTemporaryCleanupError=type(exc).__name__)
        if report['result'] == 'PASS_FIXED_IMPORTS_WITH_DENIED_IPV6_PROBE':
            try:
                observer.verify_closed()
            except (OSError, ValueError) as exc:
                report.update(result='NOT_ACCEPTED_QUALIFIED_IMPORTS',
                              finalDenialCheckError=type(exc).__name__)
        phase[0] = 'PROCESS_EXIT'
    print(json.dumps(report, sort_keys=True), flush=True)
    return 0 if report['result'] == 'PASS_FIXED_IMPORTS_WITH_DENIED_IPV6_PROBE' else 2


if __name__ == '__main__':
    raise SystemExit(main())
