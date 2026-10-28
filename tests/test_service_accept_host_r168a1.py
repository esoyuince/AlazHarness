"""Bounded synthetic host-runner checks; never execute Git, WSL, or native code."""
from __future__ import annotations

import base64
import copy
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import stat
import subprocess
import tempfile
import threading
import time
import types
import unittest
from unittest import mock
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('r168_host_accept_under_test',
    ROOT / 'scripts/qa/r168a1_accept.py')
HOST = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(HOST)


def sources():
    return {name: (HOST.canonical({'protocol': 'alaz-r168a1-os-bootstrap-contract-v2'})
                   if name.endswith('.json') else b'# Declared synthetic QA source.\npass\n')
            for name in HOST.SOURCES}


def prepared(mode='normal', stage_mode='fresh'):
    return HOST.prepared_files(
        HOST.attempt_parameters(mode + '-01', mode, '01', stage_mode),
        sources(), b'# Declared synthetic transport.\npass\n', b'# Declared synthetic host.\n',
        b'{"synthetic":"baseline"}\n', b'{"synthetic":"parent"}\n')


def stream_row(raw):
    return {'bytes': len(raw), 'sha256': HOST.sha(raw),
            'base64': base64.b64encode(raw).decode('ascii')}


TRUE_FIELDS = ('taskFreeLifecycleAccepted', 'realBrokerPingAccepted', 'serviceStarted',
    'sameOriginalSupervisor', 'sameOriginalServiceChild', 'allOwnedChildrenTerminal',
    'hostMountNamespaceUnchanged', 'hostMountTableUnchanged', 'installedSourcesAndRuntimesUnchanged')
FALSE_FIELDS = ('taskExecutionAccepted', 'restartAccepted', 'fullD3BAccepted', 'm1Accepted',
                'productionReady', 'automaticCleanup', 'automaticRetry')
ZERO_FIELDS = ('executedTasks', 'realModelCalls', 'providerBudget', 'toolBudget')


def transport_fixture(intent, kind='positive'):
    caller = {'kind': 'R168A1_REAL_SERVICE_LIFECYCLE', 'attemptId': intent['attemptId'],
              'mode': intent['mode'], 'manifestSha256': intent['manifestSha256']}
    result = {'kind': 'R168A1_ROOT_TRANSPORT', 'phase': 'OBSERVED',
        'intentSha256': HOST.sha(HOST.canonical(intent)), 'manifestSha256': intent['manifestSha256'],
        'attemptId': intent['attemptId'], 'mode': intent['mode'], 'stageMode': intent['stageMode'],
        'rootUsed': True, 'automaticRetry': False, 'automaticCleanup': False,
        'pipesComplete': True, 'callerPid': 714, 'callerStartTicks': 91234}
    if kind == 'positive':
        caller.update(result='PASS', state='REAL_SERVICE_LIFECYCLE_CLOSED',
            sourceFiles=878, dependencyFiles=1162,
            observations={'controller': {'pid': 714, 'startTicks': 91234}},
            installationReceiptSha256='0ba26bfbae1a216a595baf6fb935ed18f399bcfd0ecf29aa9c14bf61bd04232f',
            lostReply=None if intent['mode'] == 'normal' else {'synthetic': 'lost reply'})
        caller.update({name: True for name in TRUE_FIELDS})
        caller.update({name: False for name in FALSE_FIELDS})
        caller.update({name: 0 for name in ZERO_FIELDS})
        result.update(result='PASS', state='CALLER_TERMINAL_ACCEPTED',
                      callerTerminalObserved=True, callerExitCode=0)
        out, err = HOST.canonical(caller), b''
    else:
        caller.update(result='NOT_ACCEPTED', automaticRetry=False, automaticCleanup=False,
                      productionReady=False)
        result.update(result='NOT_ACCEPTED')
        if kind == 'retained':
            custody = {'state': 'RETAINED_CONTROLLER', 'pid': 714, 'startTicks': 91234}
            caller.update(state='OUTCOME_UNKNOWN', custody=custody,
                          partialStatePreserved=True, normalCloseClaimed=False)
            result.update(state='CALLER_RETAINED_OUTCOME_UNKNOWN', custody=custody,
                          callerTerminalObserved=False, verifiedLiveCustody=True)
        else:
            caller['state'] = 'REFUSED'
            result.update(state='CALLER_TERMINAL_REFUSED', callerTerminalObserved=True, callerExitCode=2)
        out, err = b'', HOST.canonical(caller)
    result.update(caller=caller, stdout=stream_row(out), stderr=stream_row(err))
    return result


def reframe(report):
    if report['state'] == 'CALLER_TERMINAL_ACCEPTED':
        report['stdout'] = stream_row(HOST.canonical(report['caller']))
    else:
        report['stderr'] = stream_row(HOST.canonical(report['caller']))
    return HOST.canonical(report)


class FormatAndFileTests(unittest.TestCase):
    def test_manifest_and_stored_zip_are_deterministic_and_exact(self):
        files, intent, receipt = prepared()
        self.assertEqual((files, intent, receipt), prepared())
        self.assertEqual(set(intent), {'kind', 'lab', 'inputRoot', 'stateRoot', 'attemptId', 'mode',
            'stageMode', 'manifestSha256', 'bundleSha256', 'bundleBytes', 'transportSha256',
            'hostRunnerSha256', 'sourceFiles', 'baseCommit', 'parentSealSha256'})
        self.assertEqual(intent['baseCommit'], HOST.BASE_COMMIT)
        self.assertEqual(intent['parentSealSha256'], HOST.PARENT_SEAL_SHA)
        self.assertEqual(intent['bundleSha256'], HOST.sha(files['bundle.zip']))
        self.assertEqual(intent['bundleBytes'], len(files['bundle.zip']))
        self.assertEqual(receipt['intentSha256'], HOST.sha(files['intent.json']))
        with zipfile.ZipFile(io.BytesIO(files['bundle.zip'])) as archive:
            self.assertEqual(set(archive.namelist()), set(HOST.SOURCES) | {'manifest.json'})
            for item in archive.infolist():
                self.assertEqual(item.compress_type, zipfile.ZIP_STORED)
                self.assertEqual(item.date_time, (1980, 1, 1, 0, 0, 0))
                self.assertEqual(item.external_attr >> 16, 0o100644)
            self.assertEqual(archive.read('manifest.json'), files['manifest.json'])
        manifest = HOST.parse(files['manifest.json'])
        self.assertEqual(manifest, {'protocol': 'alaz-r168a1-input-v1', 'files': intent['sourceFiles']})
        for name, row in manifest['files'].items():
            self.assertEqual(row, {'sha256': HOST.sha(files['sources/' + name]),
                                   'size': len(files['sources/' + name])})

    def test_bundle_rejects_wrong_inventory_and_bounds(self):
        for mutation in ('missing', 'extra', 'empty', 'large', 'total'):
            with self.subTest(mutation=mutation):
                value = sources()
                name = sorted(value)[0]
                if mutation == 'missing':
                    value.pop(name)
                elif mutation == 'extra':
                    value['../outside.py'] = b'pass\n'
                elif mutation == 'empty':
                    value[name] = b''
                elif mutation == 'large':
                    value[name] = b'x' * (HOST.MAX_SOURCE + 1)
                else:
                    value = {name: b'x' * HOST.MAX_SOURCE for name in value}
                with self.assertRaises(HOST.RunnerRejected):
                    HOST.make_bundle(value, b'{}\n')

    def test_attempt_paths_and_modes_are_narrow(self):
        self.assertEqual(HOST.attempt_parameters('lostreply-02', 'lostreply', '07', 'reuse'),
            {'attemptId': 'lostreply-02', 'mode': 'lostreply', 'stageMode': 'reuse',
             'inputRoot': '/opt/alaz-r168a1-qa-07', 'stateRoot': '/srv/alaz-r168a1-lostreply-02'})
        for args in (('../normal-01', 'normal', '01', 'fresh'), ('normal-01', 'lostreply', '01', 'fresh'),
                     ('normal-001', 'normal', '01', 'fresh'), ('normal-01', 'normal', '../', 'fresh'),
                     ('normal-01', 'normal', '01', 'replace')):
            with self.subTest(args=args), self.assertRaises(HOST.RunnerRejected):
                HOST.attempt_parameters(*args)

    def test_json_rejects_duplicate_noncanonical_nan_and_large_integer(self):
        for raw in (b'{"a":1,"a":2}\n', b'{ "a":1}\n', b'{"a":NaN}\n',
                    b'{"a":123456789012345678901}\n', b'{"a":1}', b'\xff'):
            with self.subTest(raw=raw), self.assertRaises(HOST.RunnerRejected):
                HOST.parse(raw)

    def test_open_verified_keeps_verified_handle_at_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'bundle.zip'
            path.write_bytes(b'reviewed')
            stream, raw = HOST.open_verified(path, 10, expected=HOST.sha(b'reviewed'))
            try:
                self.assertEqual(raw, b'reviewed')
                self.assertEqual(stream.tell(), 0)
                self.assertEqual(stream.read(), raw)
            finally:
                stream.close()
            with self.assertRaises(HOST.RunnerRejected):
                HOST.open_verified(path, 10, expected='0' * 64)

    def test_rejects_hardlinked_and_empty_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'input'
            path.write_bytes(b'x')
            os.link(path, Path(tmp) / 'alias')
            with self.assertRaises(HOST.RunnerRejected):
                HOST.open_verified(path, 10)
            empty = Path(tmp) / 'empty'
            empty.write_bytes(b'')
            with self.assertRaises(HOST.RunnerRejected):
                HOST.open_verified(empty, 10)
            stream, raw = HOST.open_verified(empty, 10, empty=True)
            stream.close()
            self.assertEqual(raw, b'')

    def test_alias_detection_rejects_symlink_observation(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'input'
            path.write_bytes(b'x')
            with mock.patch.object(Path, 'is_symlink', return_value=True):
                with self.assertRaises(HOST.RunnerRejected):
                    HOST.open_verified(path, 10)

    def test_exclusive_write_flushes_fsyncs_and_never_overwrites(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'execution-start.json'
            with mock.patch.object(HOST.os, 'fsync', wraps=os.fsync) as sync:
                HOST.put(path, b'first\n')
                self.assertEqual(sync.call_count, 1)
            with self.assertRaises(FileExistsError):
                HOST.put(path, b'second\n')
            self.assertEqual(path.read_bytes(), b'first\n')

    def test_cross_windows_ctime_does_not_hide_stable_view_changes(self):
        row = dict(st_dev=1, st_ino=2, st_mode=0o100600, st_size=10, st_mtime_ns=20,
                   st_nlink=1, st_birthtime_ns=10, st_ctime_ns=30)
        first = types.SimpleNamespace(**row)
        other = types.SimpleNamespace(**{**row, 'st_ctime_ns': 10})
        with mock.patch.object(HOST.sys, 'platform', 'win32'):
            self.assertEqual(HOST.cross_stamp(first), HOST.cross_stamp(other))
            self.assertNotEqual(HOST.stamp(first), HOST.stamp(other))
        with mock.patch.object(HOST.sys, 'platform', 'linux'):
            self.assertNotEqual(HOST.cross_stamp(first), HOST.cross_stamp(other))

    def test_windows_command_size_is_utf16_bounded(self):
        files, intent, _ = prepared()
        command = HOST.command_for(files, intent)
        self.assertEqual(command[:12], ['wsl.exe', '--distribution', HOST.LAB, '--user', 'root',
                         '--cd', '/', '--exec', '/usr/bin/python3.12', '-I', '-S', '-B'])
        self.assertEqual(command[-1], HOST.canonical(intent).decode('ascii')[:-1])
        too_long = dict(files, **{'transport.py': ('# ' + '\U0001f642' * 18000).encode('utf-8')})
        with self.assertRaises(HOST.RunnerRejected):
            HOST.command_for(too_long, intent)


class StreamAndClassificationTests(unittest.TestCase):
    def test_bounded_reader_drains_without_retaining_overflow(self):
        pipe = HOST.BoundedPipe(io.BytesIO(b'x' * 90))
        with mock.patch.object(HOST, 'MAX_OUTPUT', 32):
            self.assertEqual(pipe.read(), b'x' * 32)
        self.assertEqual(pipe.snapshot(), (b'x' * 32, True, True, None))
        self.assertEqual(pipe.raw.tell(), 90)

    def test_read_error_and_eof_are_distinct(self):
        class Broken:
            def read(self, size):
                raise OSError('synthetic')
        pipe = HOST.BoundedPipe(Broken())
        pipe.read()
        self.assertEqual(pipe.snapshot(), (b'', False, False, 'OSError'))

    def test_communication_invokes_once_without_input(self):
        class Process:
            returncode = None
            def communicate(self, **kwargs):
                self.kwargs = kwargs
                self.returncode = 0
        process = Process()
        observation = {}
        HOST.communicate_bounded(process, observation, time.monotonic(), seconds=1)
        self.assertEqual(process.kwargs, {'timeout': 1})
        self.assertFalse(observation['worker'].is_alive())

    def test_communication_deadline_does_not_signal_or_retry(self):
        event = threading.Event()
        class Process:
            returncode = None
            calls = 0
            def communicate(self, **kwargs):
                self.calls += 1
                event.wait(2)
                self.returncode = 0
        process, observation = Process(), {}
        try:
            with self.assertRaisesRegex(HOST.RunnerRejected, 'deadline_unknown'):
                HOST.communicate_bounded(process, observation, time.monotonic(), seconds=0.01)
            self.assertEqual(process.calls, 1)
            self.assertTrue(observation['worker'].is_alive())
        finally:
            event.set()
            observation['worker'].join(2)

    def test_output_rows_bind_all_bytes(self):
        self.assertEqual(HOST.output_row(stream_row(b'abc')), b'abc')
        for change in ({'bytes': True}, {'bytes': 2}, {'sha256': '0' * 64},
                       {'base64': 'YQ==\n'}, {'base64': '!!!!'}, {'extra': 1}):
            with self.subTest(change=change), self.assertRaises(HOST.RunnerRejected):
                HOST.output_row({**stream_row(b'abc'), **change})

    def test_positive_closure_is_scope_limited(self):
        _, intent, _ = prepared()
        report = transport_fixture(intent)
        value = HOST.transport_result(HOST.canonical(report), b'', 0, intent)
        self.assertEqual(value['result'], 'PASS')
        self.assertTrue(value['taskFreeLifecycleAccepted'])
        self.assertFalse(value['ownedCallerMayBeRunning'])
        self.assertFalse(value['continuingLiveCustodyVerified'])

    def test_positive_rejects_missing_identity_stream_or_scope(self):
        _, intent, _ = prepared()
        changes = [('manifestSha256', '0' * 64), ('callerTerminalObserved', False),
                   ('pipesComplete', False), ('callerExitCode', False), ('mode', 'lostreply'),
                   ('stageMode', 'reuse'), ('rootUsed', 1)]
        for key, value in changes:
            report = transport_fixture(intent)
            report[key] = value
            with self.subTest(key=key), self.assertRaises(HOST.RunnerRejected):
                HOST.transport_result(HOST.canonical(report), b'', 0, intent)
        for key in TRUE_FIELDS + FALSE_FIELDS + ZERO_FIELDS:
            report = transport_fixture(intent)
            report['caller'][key] = False if key in TRUE_FIELDS + ZERO_FIELDS else True
            with self.subTest(key=key), self.assertRaises(HOST.RunnerRejected):
                HOST.transport_result(reframe(report), b'', 0, intent)
        report = transport_fixture(intent)
        report['caller']['lostReply'] = {'synthetic': True}
        with self.assertRaises(HOST.RunnerRejected):
            HOST.transport_result(reframe(report), b'', 0, intent)

    def test_report_and_actual_stream_must_agree(self):
        _, intent, _ = prepared()
        report = transport_fixture(intent)
        report['caller']['realModelCalls'] = 1
        with self.assertRaisesRegex(HOST.RunnerRejected, 'caller_identity'):
            HOST.transport_result(HOST.canonical(report), b'', 0, intent)
        report = transport_fixture(intent)
        with self.assertRaises(HOST.RunnerRejected):
            HOST.transport_result(HOST.canonical(report), b'unexpected', 0, intent)

    def test_original_controller_requires_exact_typed_identity(self):
        _, intent, _ = prepared()
        for value in (None, {}, {'pid': 715, 'startTicks': 91234},
                      {'pid': 714, 'startTicks': True},
                      {'pid': 714, 'startTicks': 91234, 'extra': 1}):
            report = transport_fixture(intent)
            report['caller']['observations']['controller'] = value
            with self.subTest(value=value), self.assertRaisesRegex(HOST.RunnerRejected, 'original_caller_binding'):
                HOST.transport_result(reframe(report), b'', 0, intent)
        report = transport_fixture(intent)
        report['caller']['observations'] = None
        with self.assertRaisesRegex(HOST.RunnerRejected, 'original_caller_binding'):
            HOST.transport_result(reframe(report), b'', 0, intent)

    def test_retained_custody_stays_unknown_and_is_not_current_liveness(self):
        _, intent, _ = prepared()
        report = transport_fixture(intent, 'retained')
        value = HOST.transport_result(HOST.canonical(report), b'', 2, intent)
        self.assertEqual(value['result'], 'UNKNOWN')
        self.assertTrue(value['liveCustodyObservedByTransport'])
        self.assertFalse(value['continuingLiveCustodyVerified'])
        self.assertTrue(value['ownedCallerMayBeRunning'])
        for key in ('pid', 'startTicks'):
            changed = copy.deepcopy(report)
            changed['custody'][key] += 1
            with self.subTest(key=key), self.assertRaises(HOST.RunnerRejected):
                HOST.transport_result(reframe(changed), b'', 2, intent)

    def test_terminal_refusal_and_transport_unknown_remain_unaccepted(self):
        _, intent, _ = prepared()
        report = transport_fixture(intent, 'refused')
        result = HOST.transport_result(HOST.canonical(report), b'', 2, intent)
        self.assertEqual(result['result'], 'NOT_ACCEPTED')
        self.assertFalse(result['ownedCallerMayBeRunning'])
        report = {'kind': 'R168A1_ROOT_TRANSPORT', 'result': 'NOT_ACCEPTED',
                  'state': 'TRANSPORT_REFUSED', 'rootUsed': True,
                  'partialStatePreserved': True, 'automaticRetry': False, 'automaticCleanup': False}
        result = HOST.transport_result(HOST.canonical(report), b'', 2, intent)
        self.assertEqual(result['result'], 'UNKNOWN')
        self.assertTrue(result['ownedCallerMayBeRunning'])


class ProtectionTests(unittest.TestCase):
    def test_owned_files_gate_includes_only_declared_status_archive(self):
        for name in ('status.md', 'docs/status-history/r168-parent.md',
                     'docs/P2-SERVICE-LIFECYCLE-R168A1-REPORT.md', 'scripts/qa/r168a1_focus.py',
                     'tests/test_service_accept_host_r168a1.py',
                     'evidence/p2-service-lifecycle-r168a1/result.json'):
            self.assertTrue(HOST.allowed_current_change(name), name)
        for name in ('src/product.py', 'scripts/qa/r167a1_import_probe.py',
                     'docs/status-history/other.md', 'tests/test_service_seed.py'):
            self.assertFalse(HOST.allowed_current_change(name), name)

    def test_protection_checks_untracked_and_all_baseline_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repositories = [{'path': str(root / ('repo' + str(i))), 'head': 'h' + str(i),
                             'branch': 'b' + str(i), 'status': ''} for i in range(20)]
            hashes = {'root-' + str(i): HOST.sha(('bytes' + str(i)).encode()) for i in range(33)}
            baseline = {'worktree': str(root), 'protectedRepositories': repositories,
                        'rootChangedFileHashes': hashes}
            calls = []
            untracked = ['scripts/qa/r168a1_new.py\n']
            def git(directory, *args):
                calls.append((str(directory), args))
                if Path(directory) == root:
                    if args[0] == 'rev-parse':
                        return HOST.BASE_COMMIT + '\n'
                    if args[0] == 'branch':
                        return HOST.BRANCH + '\n'
                    if args[0] == 'diff':
                        return 'status.md\n'
                    if args[0] == 'ls-files':
                        return untracked[0]
                row = next(row for row in repositories if row['path'] == str(directory))
                return row['head'] + '\n' if args[0] == 'rev-parse' else (
                    row['branch'] + '\n' if args[0] == 'branch' else row['status'])
            def read(path, *args, **kwargs):
                return ('bytes' + path.name.removeprefix('root-')).encode()
            with mock.patch.object(HOST, 'ROOT', root), \
                 mock.patch.object(HOST, 'path_without_alias', side_effect=lambda p, **k: Path(p)), \
                 mock.patch.object(HOST, 'git_read', side_effect=git), \
                 mock.patch.object(HOST, 'read_file', side_effect=read):
                proof = HOST.protection_snapshot(baseline)
                self.assertEqual(proof['protectedRepositoryCount'], 20)
                self.assertEqual(proof['rootChangedFileCount'], 33)
                self.assertIn((str(root), ('ls-files', '--others', '--exclude-standard')), calls)
                untracked[0] = 'foreign-source.py\n'
                with self.assertRaisesRegex(HOST.RunnerRejected, 'existing_source_changed'):
                    HOST.protection_snapshot(baseline)
                untracked[0] = ''
                hashes['root-0'] = '0' * 64
                with self.assertRaisesRegex(HOST.RunnerRejected, 'root_file_changed'):
                    HOST.protection_snapshot(baseline)


class SyntheticProcess:
    """Declared Windows-communicate port; no subprocess is created."""
    def __init__(self, out, err, exit_code, stdin, timeout=False):
        self.stdout, self.stderr = io.BytesIO(out), io.BytesIO(err)
        self.returncode, self.pid = None, 8123
        self.exit_code, self.received_stdin, self.timeout = exit_code, stdin, timeout
        self.calls, self.received_bytes = 0, None

    def communicate(self, **kwargs):
        self.calls += 1
        if set(kwargs) != {'timeout'}:
            raise AssertionError('Only timeout may be passed to communicate')
        if self.timeout:
            raise subprocess.TimeoutExpired('declared fixture', kwargs['timeout'])
        self.received_bytes = self.received_stdin.read()
        self.stdout.read()
        self.stderr.read()
        self.returncode = self.exit_code

    def kill(self):
        raise AssertionError('Never signal a process')

    terminate = kill

    def wait(self, *args, **kwargs):
        raise AssertionError('Never second-wait a process')


class ApplyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / 'scratch/r168-service').mkdir(parents=True)
        self.sources = sources()
        self.transport, self.host = b'# transport\npass\n', b'# host\n'
        self.before = {'synthetic': 'unchanged protection'}
        self.patchers = [
            mock.patch.object(HOST, 'ROOT', self.root),
            mock.patch.object(HOST, 'host_actor'),
            mock.patch.object(HOST, 'baseline_inputs', return_value=({}, b'baseline\n', b'seal\n')),
            mock.patch.object(HOST, 'protection_snapshot', return_value=self.before),
            mock.patch.object(HOST, 'current_inputs',
                              return_value=(self.sources, self.transport, self.host)),
            mock.patch.object(HOST, '_PENDING', []),
        ]
        self.mocks = [patcher.start() for patcher in self.patchers]
        receipt = HOST.prepare('normal-01', 'normal', '01', 'fresh')
        self.intent_sha = receipt['intentSha256']
        self.directory = self.root / 'scratch/r168-service/normal-01'
        self.intent = HOST.parse((self.directory / 'intent.json').read_bytes())
        self.processes = []

    def tearDown(self):
        # Only declared synthetic objects/temp paths are released by tests.
        for row in HOST._PENDING:
            if len(row) == 4:
                row[3].close()
        for patcher in reversed(self.patchers):
            patcher.stop()
        self.tmp.cleanup()

    def invoke(self, *, kind='positive', timeout=False, fail_spawn=False):
        report = transport_fixture(self.intent, kind)
        out = HOST.canonical(report)
        def spawn(command, **kwargs):
            self.assertEqual((self.directory / 'execution-start.json').is_file(), True)
            self.assertNotEqual(kwargs['stdin'], subprocess.PIPE)
            self.assertEqual(kwargs['stdin'].tell(), 0)
            self.assertEqual(HOST.sha(kwargs['stdin'].read()), self.intent['bundleSha256'])
            kwargs['stdin'].seek(0)
            if fail_spawn:
                raise OSError('declared spawn failure')
            process = SyntheticProcess(out, b'', 0 if kind == 'positive' else 2,
                                       kwargs['stdin'], timeout)
            self.processes.append(process)
            return process
        with mock.patch.object(HOST.subprocess, 'Popen', side_effect=spawn):
            return HOST.apply('normal-01', 'normal', '01', 'fresh', self.intent_sha)

    def test_complete_apply_uses_held_file_and_persists_exact_result(self):
        bundle = (self.directory / 'bundle.zip').read_bytes()
        result = self.invoke()
        self.assertEqual(result['result'], 'PASS')
        self.assertTrue(result['protectedWorkspacesUnchanged'])
        self.assertTrue(result['frozenInputsUnchanged'])
        self.assertTrue(result['evidenceWriteComplete'])
        self.assertFalse(result['hostTransportMayBeRunning'])
        self.assertEqual(self.processes[0].received_bytes, bundle)
        self.assertEqual(self.processes[0].calls, 1)
        self.assertTrue(self.processes[0].received_stdin.closed)
        self.assertEqual(HOST.parse((self.directory / 'result.json').read_bytes()), result)
        self.assertEqual(result['stdoutSha256'], HOST.sha((self.directory / 'stdout.txt').read_bytes()))
        self.assertEqual((self.directory / 'stderr.txt').read_bytes(), b'')
        with self.assertRaisesRegex(HOST.RunnerRejected, 'no_replay'):
            HOST.load_prepared('normal-01', 'normal', '01', 'fresh', self.intent_sha)

    def test_timeout_preserves_marker_references_and_never_replays(self):
        result = self.invoke(timeout=True)
        self.assertEqual(result['result'], 'UNKNOWN')
        self.assertTrue(result['hostTransportMayBeRunning'])
        self.assertFalse(result['transportTerminalObserved'])
        self.assertFalse(result['taskFreeLifecycleAccepted'])
        self.assertEqual(self.processes[0].calls, 1)
        self.assertEqual(len(HOST._PENDING), 1)
        self.assertFalse(self.processes[0].received_stdin.closed)
        self.assertTrue((self.directory / 'execution-start.json').is_file())
        with self.assertRaisesRegex(HOST.RunnerRejected, 'no_replay'):
            HOST.load_prepared('normal-01', 'normal', '01', 'fresh', self.intent_sha)

    def test_spawn_failure_is_after_marker_and_unknown(self):
        result = self.invoke(fail_spawn=True)
        self.assertEqual(result['result'], 'UNKNOWN')
        self.assertFalse(result['transportTerminalObserved'])
        self.assertEqual(len(HOST._PENDING), 1)
        self.assertTrue((self.directory / 'execution-start.json').is_file())

    def test_retained_linux_caller_is_observed_but_not_claimed_alive_now(self):
        result = self.invoke(kind='retained')
        self.assertEqual(result['result'], 'UNKNOWN')
        self.assertTrue(result['transportTerminalObserved'])
        self.assertTrue(result['liveCustodyObservedByTransport'])
        self.assertFalse(result['continuingLiveCustodyVerified'])
        self.assertFalse(result['taskFreeLifecycleAccepted'])
        self.assertFalse(result['hostTransportMayBeRunning'])

    def test_post_protection_failure_cannot_keep_overall_pass(self):
        self.mocks[3].side_effect = [self.before, HOST.RunnerRejected('synthetic drift')]
        result = self.invoke()
        self.assertEqual(result['result'], 'UNKNOWN')
        self.assertEqual(result['transport']['result'], 'PASS')
        self.assertFalse(result['taskFreeLifecycleAccepted'])
        self.assertFalse(result['protectedWorkspacesUnchanged'])
        self.assertTrue(result['evidenceWriteComplete'])

    def test_post_source_change_cannot_keep_overall_pass(self):
        self.mocks[4].side_effect = [
            (self.sources, self.transport, self.host),
            (self.sources, self.transport + b'# changed\n', self.host)]
        result = self.invoke()
        self.assertEqual(result['result'], 'UNKNOWN')
        self.assertEqual(result['transport']['result'], 'PASS')
        self.assertTrue(result['protectedWorkspacesUnchanged'])
        self.assertFalse(result['frozenInputsUnchanged'])

    def test_output_write_failure_cannot_keep_overall_pass(self):
        actual_put = HOST.put
        def put(path, raw):
            if path.name == 'stdout.txt':
                raise OSError('declared evidence failure')
            return actual_put(path, raw)
        with mock.patch.object(HOST, 'put', side_effect=put):
            result = self.invoke()
        self.assertEqual(result['result'], 'UNKNOWN')
        self.assertEqual(result['transport']['result'], 'PASS')
        self.assertFalse(result['evidenceWriteComplete'])
        self.assertFalse(result['taskFreeLifecycleAccepted'])
        self.assertTrue((self.directory / 'execution-start.json').is_file())

    def test_frozen_change_and_source_change_refuse_before_start(self):
        path = self.directory / 'sources/scripts/qa/r168a1_service_seed.py'
        original = path.read_bytes()
        path.write_bytes(original + b'# changed\n')
        with self.assertRaisesRegex(HOST.RunnerRejected, 'frozen_bytes_changed'):
            HOST.load_prepared('normal-01', 'normal', '01', 'fresh', self.intent_sha)
        self.assertFalse((self.directory / 'execution-start.json').exists())
        path.write_bytes(original)
        self.sources['scripts/qa/r168a1_service_seed.py'] += b'# live changed\n'
        with self.assertRaisesRegex(HOST.RunnerRejected, 'expected_intent_changed'):
            HOST.load_prepared('normal-01', 'normal', '01', 'fresh', self.intent_sha)
        self.assertFalse((self.directory / 'execution-start.json').exists())


if __name__ == '__main__':
    unittest.main()
