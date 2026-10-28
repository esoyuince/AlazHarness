"""QA contracts and actual local pipes/socket faults; no installed lab acceptance."""
import copy
import builtins
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path, PurePosixPath
import socket
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'packages/claw-hermes'))


def load(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


qa = load('r168_controller_qa_tests', 'scripts/qa/r168a1_linux_accept.py')
child = load('r168_seed_child_qa_tests', 'scripts/qa/r168a1_seed_child.py')
transport = load('r168_transport_qa_tests', 'scripts/qa/r168a1_linux_transport.py')
seed = load('r168_seed_input_qa_tests', 'scripts/qa/r168a1_service_seed.py')


def seed_contract(attempt='normal-01'):
    base = '/srv/alaz-r168a1-' + attempt
    token = '1' * 32
    return {'protocol': child.PROTOCOL, 'attemptId': attempt,
        'controller': {'pid': 11, 'startTicks': 12}, 'worker': {'pid': 13, 'startTicks': 14},
        'scope': {'path': '/sys/fs/cgroup/alaz-r168a1-' + attempt + '/volume-' + token,
                  'device': 1, 'inode': 2}, 'namespace': {'fd': 5, 'inode': 6},
        'image': {'path': base + '/images/state.ext4', 'device': 1, 'inode': 2,
                  'size': 64 * 1024 * 1024, 'uid': 0, 'gid': 0, 'parent_device': 1, 'parent_inode': 3},
        'token': token, 'fence': {'path': base + '/images/state.ext4.volume-owner.json', 'sha256': '2' * 64},
        'mountpoint': base + '/mount', 'profile': base + '/mount/profile', 'loopNumber': 3,
        'principal': dict(qa.PRINCIPAL),
        'installation': {'path': child.INSTALLATION, 'receiptSha256': qa.RECEIPT_SHA},
        'bootstrap': {'path': child.BOOTSTRAP, 'sha256': '3' * 64},
        'childSha256': '4' * 64, 'configSha256': '5' * 64, 'seedInstanceId': 'seed-01'}


class ConfigurationTests(unittest.TestCase):
    def test_bootstrap_refusal_keeps_original_probe_bytes_and_terminal_identity(self):
        from types import SimpleNamespace
        c = qa.Controller('normal-01', 'normal')
        process = SimpleNamespace(pid=17, returncode=2, poll=lambda: 2)
        output = qa.canonical({'result': 'NOT_ACCEPTED', 'reason': 'bootstrap_observation_changed'})
        def observed(attempt, seconds):
            self.assertIs(attempt['process'], process)
            attempt.update(pipesComplete=True, exitCode=2,
                           buffers={'stdout': bytearray(output), 'stderr': bytearray()})
            return output, b''
        manifest = {'files': {qa.PROBE: {'sha256': '1' * 64},
                              qa.CONTRACT: {'sha256': '2' * 64}}}
        with patch.object(qa.subprocess, 'Popen', return_value=process), \
                patch.object(qa, 'start_ticks', return_value=99), \
                patch.object(qa, 'collect', side_effect=observed):
            with self.assertRaisesRegex(qa.AcceptanceRejected, 'qa_bootstrap_refused'):
                c.bootstrap_probe(manifest)
            report = c.failure_snapshot()
        self.assertFalse(report['effectsAttempted'])
        self.assertEqual(len(report['bootstrap']), 1)
        probe = report['bootstrap'][0]
        self.assertEqual((probe['pid'], probe['startTicks'], probe['exitCode']), (17, 99, 2))
        self.assertTrue(probe['pipesComplete'])
        self.assertEqual(probe['stdout'], {'bytes': len(output), 'sha256': qa.digest(output),
            'base64': qa.base64.b64encode(output).decode('ascii')})
        self.assertEqual(probe['stderr']['bytes'], 0)

    def document(self):
        return qa.configuration({'socketPath': '/run/alaz-r168a1-normal-01/broker/egress.sock',
                                 'brokerId': '1' * 32, 'routeFingerprint': '2' * 64},
                                PurePosixPath('/srv/alaz-r168a1-normal-01/canary.txt'), '3' * 64)

    def test_zero_capacity_config_accepted_by_real_factory_and_seed_codec(self):
        import gateway_service_factory as factory
        document = self.document()
        raw = qa.config_bytes(document)
        self.assertFalse(raw.endswith(b'\n'))
        self.assertEqual(seed.config_document(raw), document)
        checked = factory.validate_settings(document)
        for key in ('max_provider_calls', 'max_tool_calls', 'total_token_limit', 'total_cost_microusd'):
            self.assertEqual(checked.execution['policy'][key], 0)
            self.assertIs(type(checked.execution['policy'][key]), int)
        self.assertEqual(checked.policy.max_issued, 1)

    def test_framed_config_is_rejected_without_relaxing_product_codec(self):
        with self.assertRaisesRegex(seed.SeedRejected, 'seed_config_noncanonical'):
            seed.config_document(qa.canonical(self.document()))

    def test_config_credentials_are_distinct_and_only_local_provider_route(self):
        d = self.document()
        e = d['plugins']['entries']['alaz-host-gate']['settings']['execution']
        self.assertEqual(len({e['provider_bearer'], e['provider_broker']['signing_key'],
                              d['platforms']['api_server']['extra']['key']}), 3)
        self.assertEqual(d['model']['api_key'], e['provider_bearer'])
        self.assertEqual(d['model']['base_url'], 'http://127.0.0.1:45568/alaz/provider/v1')

    def test_attempt_paths_reject_traversal_alias_and_mode_conflict(self):
        for attempt, mode in (('../normal-01', 'normal'), ('normal-001', 'normal'),
                               ('normal-01', 'lostreply'), ('normal-01/child', 'normal')):
            with self.subTest(attempt=attempt, mode=mode), self.assertRaises(qa.AcceptanceRejected):
                qa.Controller(attempt, mode)


class SeedBoundaryTests(unittest.TestCase):
    def test_exact_roundtrip_binds_attempt_and_new_input_hashes(self):
        value = seed_contract()
        self.assertEqual(child.decode_contract(child.encode_contract(value)), value)
        for name in ('configSha256', 'childSha256', 'attemptId'):
            bad = copy.deepcopy(value)
            del bad[name]
            with self.subTest(missing=name), self.assertRaises(child.SeedRejected):
                child.encode_contract(bad)

    def test_foreign_profile_scope_and_old_receipt_rejected(self):
        value = seed_contract()
        cases = [dict(value, profile='/srv/alaz-r168a1-lostreply-01/mount/profile'),
                 dict(value, configSha256='x' * 64),
                 dict(value, attemptId='../normal-01')]
        old = copy.deepcopy(value)
        old['installation']['receiptSha256'] = 'a4bcc0f27d29f27f08c55d3a65eaa102a503a7da12d4672253f0245fd5d4f845'
        cases.append(old)
        for case in cases:
            with self.subTest(case=case), self.assertRaises(child.SeedRejected):
                child.encode_contract(case)

    def test_producer_argv_preserves_parent_namespace_and_source_pins(self):
        value = child.validate_contract(seed_contract())
        command = child.producer_command(value, child.CreatedProfile(7, 8))
        self.assertEqual(command[:4], [qa.PYTHON, '-I', '-S', '-B'])
        args = dict(zip(command[5::2], command[6::2]))
        self.assertEqual(args['--parent-start-ticks'], '12')
        self.assertEqual(args['--expected-mount-namespace-inode'], '6')
        self.assertEqual(args['--expected-seed-sha256'], '3' * 64)
        self.assertEqual(args['--expected-config-sha256'], '5' * 64)
        self.assertEqual(args['--config-file'], '/srv/alaz-r168a1-normal-01/seed-config.json')


_DIAGNOSTIC_TEMPLATE = (
    '%s: linked SQLite %s (interpreter %s) is vulnerable to the WAL-reset corruption bug '
    '(https://sqlite.org/wal.html#walresetbug) — %s. Upgrade to SQLite 3.51.3+ '
    '(or backports 3.50.7 / 3.44.6); %s. See ' + chr(96) + 'hermes doctor' + chr(96) +
    '. This warning fires once per process per database.')
_DIAGNOSTIC_ACTION = 'using journal_mode=DELETE instead of enabling WAL'
_DIAGNOSTIC_LABELS = ('state.db', 'runs_idempotency.db', 'response_store.db')


def diagnostic_sources():
    """Explicit AST-only fixtures; none is a native program used by the lab."""
    wal = (
        "raise AssertionError('synthetic native source must not execute')\n"
        "_WAL_RESET_BUG_ACTIONS = {'delete': " + repr(_DIAGNOSTIC_ACTION) + "}\n"
        "_ONCE_LOGS = {'wal_reset_bug': (lock, seen, logging.WARNING, " +
        repr(_DIAGNOSTIC_TEMPLATE) + ")}\n"
        "def _log_wal_reset_bug_once():\n"
        "    _log_once('wal_reset_bug', db_label, sqlite3.sqlite_version, "
        "sys.executable, action, _wal_reset_repair_hint)\n"
        "def _wal_reset_repair_hint():\n"
        '    return f"Hermes-managed installs can repair the embedded runtime with ' +
        chr(96) + '{cmd}' + chr(96) + '"\n')
    return {
        'native/hermes_state_wal.py': wal.encode('utf-8'),
        'native/hermes_state.py':
            b"def constructor():\n    apply_wal_with_fallback(conn, db_label='state.db')\n",
        'native/gateway/platforms/api_server_run_idempotency.py':
            b"def constructor():\n    apply_wal_with_fallback(conn, db_label='runs_idempotency.db')\n",
        'native/gateway/platforms/api_server_response_store.py':
            b"def constructor():\n    apply_wal_with_fallback(conn, db_label='response_store.db')\n",
    }


def diagnostic_wire(document):
    return json.dumps(document, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=True, allow_nan=False).encode('ascii')


def diagnostic_seed():
    """Synthetic producer proof for the pure classifier, not service acceptance."""
    home = '/srv/alaz-r168a1-normal-99/mount/profile'
    identities = [[9, 101], [9, 102], [9, 103]]
    handoff = {
        'protocol': 'alaz-service-startup-v1',
        'state': {'epoch': 1, 'journal_mode': 'delete', 'instance_id': 'fixture-seed',
                  'state_identity': identities[0], 'replay_identity': identities[1]},
        'response': {'response_identity': identities[2]},
        'service': {'epoch': 1, 'instance_id': 'fixture-seed', 'home': home,
                    'database_identities': identities},
    }
    raw = diagnostic_wire(handoff)
    return {
        'kind': 'R168A1_TASK_FREE_SERVICE_SEED', 'result': 'PASS',
        'state': 'SERVICE_SEED_CREATED', 'phase': 'COMPLETE',
        'ownerState': 'CLOSED', 'consumerState': 'DETACHED',
        'allThreeConnectionsPhysicallyClosed': True, 'profileLeaseReleasedNormally': True,
        'serviceCapturedWhileLeaseHeld': True, 'normalLoopShutdown': True,
        'zeroExecutionCapacity': True, 'sourceAndDependencyBytesReadBackBeforeAndAfter': True,
        'runtimeBinaryBytesReadBackBeforeAndAfter': True,
        'apiAdmissionPublished': False, 'providerExchangePerformed': False,
        'serviceAccepted': False, 'kernelAccepted': False, 'fullD3BAccepted': False,
        'automaticCleanup': False, 'automaticRetry': False,
        'executedTasks': 0, 'realModelCalls': 0, 'listenersCreated': 0,
        'outstandingAsyncTasks': 0, 'outstandingThreads': 0,
        'completedChecks': ['preflight', 'response_preflight', 'before_epoch',
                            'response_before_epoch', 'after_epoch', 'response_after_epoch'],
        'installationReceiptSha256': qa._SEED_DIAG_RECEIPT_SHA,
        'harnessCommit': qa._SEED_DIAG_HARNESS, 'nativeFeature': qa._SEED_DIAG_NATIVE,
        'sourceFileCount': 878, 'dependencyFileCount': 1162, 'qualifiedNativeSourceCount': 760,
        'sourceIdentity': {'sha256': qa._SEED_DIAG_SEED_SHA},
        'runtimeBinaries': {'python': {'path': '/usr/bin/python3.12',
                                       'sha256': qa._SEED_DIAG_PYTHON_SHA}},
        'home': home, 'instanceId': 'fixture-seed', 'previousEpoch': 1,
        'databaseIdentities': identities, 'handoff': raw.decode('ascii'),
        'handoffSha256': hashlib.sha256(raw).hexdigest(),
    }


class SeedDiagnosticTests(unittest.TestCase):
    def setUp(self):
        self.sources = diagnostic_sources()
        # Hash substitution is an explicit, restored test fixture. The runtime
        # API has no pin override and production constants remain unchanged.
        pins = {name: hashlib.sha256(raw).hexdigest() for name, raw in self.sources.items()}
        fixture = patch.object(qa, '_SEED_DIAG_SOURCE_PINS', pins)
        fixture.start()
        self.addCleanup(fixture.stop)
        self.seed = diagnostic_seed()
        hint = ('Hermes-managed installs can repair the embedded runtime with ' +
                chr(96) + 'hermes update' + chr(96))
        self.stderr = ''.join(
            _DIAGNOSTIC_TEMPLATE % (name, '3.45.1', '/usr/bin/python3.12',
                                    _DIAGNOSTIC_ACTION, hint) + '\n'
            for name in _DIAGNOSTIC_LABELS).encode('utf-8')

    def invoke(self, stderr=None, seed_result=None, sources=None, **changed):
        arguments = {'archive_sha256': qa._SEED_DIAG_ARCHIVE_SHA,
                     'sqlite_version': (3, 45, 1), 'interpreter': '/usr/bin/python3.12',
                     'exit_code': 0, 'pipes_complete': True}
        arguments.update(changed)
        return qa.classify_seed_diagnostics(
            self.stderr if stderr is None else stderr,
            self.seed if seed_result is None else seed_result,
            self.sources if sources is None else sources, **arguments)

    @staticmethod
    def altered_handoff(seed_result, change):
        result = copy.deepcopy(seed_result)
        value = json.loads(result['handoff'])
        change(value)
        raw = diagnostic_wire(value)
        result['handoff'] = raw.decode('ascii')
        result['handoffSha256'] = hashlib.sha256(raw).hexdigest()
        return result

    def test_exact_three_lines_produce_separate_scoped_receipt(self):
        before = copy.deepcopy(self.seed)
        expected, derivation = qa._seed_diag_expected_stderr(
            self.sources, sqlite_version=(3, 45, 1), interpreter='/usr/bin/python3.12')
        self.assertEqual(expected, self.stderr)
        self.assertEqual(len(expected), 1265)
        self.assertEqual(expected.count(b'\n'), 3)
        receipt = self.invoke()
        self.assertEqual(receipt['classification'], 'EXACT_PINNED_NATIVE_DELETE_WARNINGS')
        self.assertTrue(receipt['qualified'])
        self.assertEqual(receipt['stderrSha256'], hashlib.sha256(self.stderr).hexdigest())
        self.assertEqual(receipt['databaseLabelsInOrder'], list(_DIAGNOSTIC_LABELS))
        self.assertEqual(receipt['declaredJournalMode'], 'delete')
        self.assertEqual(receipt['sqliteVersionObservedByCaller'], [3, 45, 1])
        self.assertEqual(derivation['repairCommand'], 'hermes update')
        for name in ('priorUnknownReclassified', 'serviceAccepted', 'kernelAccepted',
                     'fullSharedLibraryClosureAccepted', 'liveDatabaseOpenedByClassifier',
                     'installedHandoffCodecRunByClassifier', 'nativeSourceExecutedByClassifier',
                     'automaticCleanup', 'automaticRetry'):
            self.assertIs(receipt[name], False, name)
        self.assertEqual(self.seed, before)
        self.assertNotIn('diagnostics', self.seed)

    def test_missing_extra_reordered_duplicate_and_truncated_bytes_are_refused(self):
        rows = self.stderr.splitlines(keepends=True)
        alternatives = [b'', self.stderr[:-1], self.stderr[:100], self.stderr + b'extra\n',
            b'prefix\n' + self.stderr, b''.join(rows[:2]), b''.join(reversed(rows)),
            rows[0] + rows[0] + rows[2], self.stderr.replace(b'\n', b'\r\n'), b'x' * 4097]
        for raw in alternatives:
            with self.subTest(size=len(raw)), self.assertRaises(qa.AcceptanceRejected):
                self.invoke(stderr=raw)

    def test_warning_database_version_interpreter_action_and_hint_are_exact(self):
        for before, after in ((b'state.db:', b'foreign.db:'), (b'3.45.1', b'3.45.2'),
            (b'/usr/bin/python3.12', b'/tmp/python3.12'),
            (b'using journal_mode=DELETE instead of enabling WAL', b'leaving WAL in place'),
            (b'hermes update', b'hermes alternate-update')):
            with self.subTest(before=before), self.assertRaisesRegex(
                    qa.AcceptanceRejected, 'diagnostic_unexpected_stderr'):
                self.invoke(stderr=self.stderr.replace(before, after))

    def test_source_hash_inventory_and_archive_pin_are_mandatory(self):
        for name in self.sources:
            changed = dict(self.sources)
            changed[name] += b'\n# Changed after fixture pinning.\n'
            with self.subTest(name=name), self.assertRaisesRegex(
                    qa.AcceptanceRejected, 'diagnostic_source_pin'):
                self.invoke(sources=changed)
        for changed in ({}, {**self.sources, 'native/foreign.py': b'pass\n'}):
            with self.assertRaisesRegex(qa.AcceptanceRejected, 'diagnostic_source_inventory'):
                self.invoke(sources=changed)
        with self.assertRaisesRegex(qa.AcceptanceRejected, 'diagnostic_archive_pin'):
            self.invoke(archive_sha256='0' * 64)
        with self.assertRaises(TypeError):
            self.invoke(source_pins=dict(qa._SEED_DIAG_SOURCE_PINS))

    def test_terminal_and_runtime_observations_reject_weak_equality(self):
        for changed in ({'exit_code': False}, {'exit_code': 2}, {'pipes_complete': 1},
                        {'pipes_complete': False}, {'sqlite_version': (3, 45, True)},
                        {'sqlite_version': [3, 45, 1]}, {'sqlite_version': (3, 51, 3)},
                        {'interpreter': '/usr/bin/python3'}):
            with self.subTest(changed=changed), self.assertRaises(qa.AcceptanceRejected):
                self.invoke(**changed)

    def test_exact_warning_text_cannot_replace_successful_seed_proof(self):
        for key, value in (
            ('result', 'NOT_ACCEPTED'), ('phase', 'CLOSE_OWNER'), ('ownerState', 'OPEN'),
            ('consumerState', 'ATTACHED'), ('allThreeConnectionsPhysicallyClosed', False),
            ('normalLoopShutdown', False), ('profileLeaseReleasedNormally', False),
            ('serviceCapturedWhileLeaseHeld', False), ('zeroExecutionCapacity', False),
            ('sourceAndDependencyBytesReadBackBeforeAndAfter', False),
            ('runtimeBinaryBytesReadBackBeforeAndAfter', False), ('executedTasks', 1),
            ('executedTasks', False), ('realModelCalls', 1), ('serviceAccepted', True),
            ('providerExchangePerformed', True), ('automaticCleanup', True),
            ('completedChecks', ['preflight']), ('sourceFileCount', 877),
            ('dependencyFileCount', 1161), ('qualifiedNativeSourceCount', 759),
            ('installationReceiptSha256', '0' * 64), ('harnessCommit', '0' * 40),
            ('nativeFeature', '0' * 40)):
            changed = copy.deepcopy(self.seed)
            changed[key] = value
            with self.subTest(key=key, value=value), self.assertRaises(qa.AcceptanceRejected):
                self.invoke(seed_result=changed)

    def test_producer_and_runtime_source_pins_are_mandatory(self):
        changed = copy.deepcopy(self.seed)
        changed['sourceIdentity']['sha256'] = '0' * 64
        with self.assertRaisesRegex(qa.AcceptanceRejected, 'diagnostic_seed_producer_pin'):
            self.invoke(seed_result=changed)
        for key, value in (('path', '/tmp/python3.12'), ('sha256', '0' * 64)):
            changed = copy.deepcopy(self.seed)
            changed['runtimeBinaries']['python'][key] = value
            with self.subTest(key=key), self.assertRaisesRegex(
                    qa.AcceptanceRejected, 'diagnostic_seed_runtime_pin'):
                self.invoke(seed_result=changed)

    def test_rehashed_non_delete_handoff_is_refused(self):
        for mode in ('wal', 'unknown', 'truncate', 'persist', None):
            changed = self.altered_handoff(self.seed,
                lambda value: value['state'].__setitem__('journal_mode', mode))
            with self.subTest(mode=mode), self.assertRaisesRegex(
                    qa.AcceptanceRejected, 'diagnostic_handoff_delete'):
                self.invoke(seed_result=changed)

    def test_handoff_hash_identity_epoch_and_canonical_bytes_remain_bound(self):
        changed = copy.deepcopy(self.seed)
        changed['handoffSha256'] = '0' * 64
        with self.assertRaisesRegex(qa.AcceptanceRejected, 'diagnostic_handoff_hash'):
            self.invoke(seed_result=changed)
        for member, key, value, reason in (
            ('state', 'epoch', True, 'diagnostic_handoff_delete'),
            ('service', 'home', '/srv/foreign', 'diagnostic_handoff_delete'),
            ('response', 'response_identity', [9, 999], 'diagnostic_handoff_identities'),
            ('state', 'state_identity', [True, 101], 'diagnostic_handoff_identities')):
            changed = self.altered_handoff(self.seed,
                lambda doc: doc[member].__setitem__(key, value))
            with self.subTest(member=member, key=key), self.assertRaisesRegex(
                    qa.AcceptanceRejected, reason):
                self.invoke(seed_result=changed)
        changed = copy.deepcopy(self.seed)
        raw = changed['handoff'].encode('ascii') + b'\n'
        changed.update(handoff=raw.decode('ascii'), handoffSha256=hashlib.sha256(raw).hexdigest())
        with self.assertRaisesRegex(qa.AcceptanceRejected, 'diagnostic_handoff_format'):
            self.invoke(seed_result=changed)

    def test_hash_pinned_but_wrong_ast_emitter_and_callsite_are_refused(self):
        name = 'native/hermes_state_wal.py'
        alternatives = [
            (name, b'logging.WARNING', b'logging.ERROR', 'source_warning_format'),
            (name, b'sys.executable, action', b'action, sys.executable', 'source_argument_order'),
            (name, b'{cmd}', b'{command}', 'source_repair_hint_shape'),
            ('native/hermes_state.py', b"'state.db'", b"'foreign.db'", 'constructor_label'),
        ]
        for path, old, new, reason in alternatives:
            sources = dict(self.sources)
            self.assertIn(old, sources[path])
            sources[path] = sources[path].replace(old, new)
            pins = {n: hashlib.sha256(raw).hexdigest() for n, raw in sources.items()}
            with self.subTest(path=path, reason=reason), \
                    patch.object(qa, '_SEED_DIAG_SOURCE_PINS', pins), \
                    self.assertRaisesRegex(qa.AcceptanceRejected, reason):
                self.invoke(sources=sources)

    def test_source_is_never_executed_and_classification_has_no_io(self):
        # Even the valid source fixture raises if executed. These explicit
        # prohibitions also catch an accidental file/database/child side effect.
        with patch.object(builtins, 'exec', side_effect=AssertionError('unexpected exec')), \
                patch.object(builtins, 'open', side_effect=AssertionError('unexpected file I/O')), \
                patch.object(qa.subprocess, 'Popen', side_effect=AssertionError('unexpected child')), \
                patch.object(seed.sqlite3, 'connect', side_effect=AssertionError('unexpected DB')):
            self.assertTrue(self.invoke()['qualified'])

    def test_snapshot_keeps_raw_stderr_and_separate_diagnostic_receipt(self):
        from types import SimpleNamespace
        c = qa.Controller('normal-99', 'normal')
        receipt = self.invoke()
        process = SimpleNamespace(pid=55, poll=lambda: 0)
        c.seed = {'phase': 'COMPLETE', 'process': process, 'startTicks': 66,
                  'diagnostics': receipt, 'pipesComplete': True,
                  'buffers': {'stdout': bytearray(qa.canonical(self.seed)),
                              'stderr': bytearray(self.stderr)}}
        c.seed_result = self.seed
        before = copy.deepcopy(self.seed)
        with patch.object(qa, 'start_ticks', return_value=77):
            report = c.snapshot()
        self.assertIs(report['seed']['diagnostics'], receipt)
        self.assertEqual(report['seed']['stderr'], {
            'bytes': 1265, 'sha256': hashlib.sha256(self.stderr).hexdigest(),
            'base64': qa.base64.b64encode(self.stderr).decode('ascii')})
        self.assertEqual(c.seed_result, before)
        self.assertNotIn('diagnostics', c.seed_result)


@unittest.skipUnless(sys.platform == 'linux', 'actual POSIX pipes and Unix sockets')
class PipeAndReplyTests(unittest.TestCase):
    def process(self, text):
        p = subprocess.Popen([sys.executable, '-I', '-S', '-B', '-c', text],
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.addCleanup(self.cleanup, p)
        return p

    @staticmethod
    def cleanup(p):
        # Explicit teardown of disposable test-only processes, never product owners.
        if p.poll() is None:
            p.terminate()
        p.wait(timeout=5)
        for name in ('stdout', 'stderr'):
            if not getattr(p, name).closed:
                getattr(p, name).close()

    def test_real_pipe_capture_requires_exit_and_both_eofs(self):
        p = self.process("import os;os.write(1,b'complete\\n');os.write(2,b'diagnostic\\n')")
        owned = {'process': p}
        out, err = qa.collect(owned, 5, 64)
        self.assertEqual((out, err), (b'complete\n', b'diagnostic\n'))
        self.assertTrue(owned['pipesComplete'])
        self.assertEqual(owned['exitCode'], 0)

    def test_timeout_preserves_same_live_process_and_pipes(self):
        p = self.process('import time;time.sleep(30)')
        owned = {'process': p}
        with self.assertRaisesRegex(qa.AcceptanceRejected, 'timeout_unknown'):
            qa.collect(owned, .03, 64)
        self.assertIs(owned['process'], p)
        self.assertIsNone(p.poll())
        self.assertFalse(p.stdout.closed)
        self.assertFalse(p.stderr.closed)
        self.assertFalse(owned.get('pipesComplete', False))

    def test_output_overflow_preserves_owned_child_without_cleanup(self):
        p = self.process("import os,time;os.write(1,b'x'*65);time.sleep(30)")
        owned = {'process': p}
        with self.assertRaisesRegex(qa.AcceptanceRejected, 'overflow_unknown'):
            qa.collect(owned, 5, 64)
        self.assertIs(owned['process'], p)
        self.assertIsNone(p.poll())
        self.assertEqual(len(owned['buffers']['stdout']), 65)

    def test_partial_report_does_not_require_nonexistent_capture_member(self):
        from types import SimpleNamespace
        c = qa.Controller('normal-01', 'normal')
        p = self.process('pass')
        p.wait(timeout=5)
        channel = SimpleNamespace(status=lambda: {'state': 'COMPLETED'},
            stdout_eof=True, stderr_eof=True, stdin_closed=True, final_frame={'state': 'CLOSED'},
            stderr_tail=bytearray(b'log'), stderr_bytes=3)
        child_owner = SimpleNamespace(phase='COMPLETED', process=p, channel=channel, start_ticks=1)
        c.volume = SimpleNamespace(_service_child=child_owner, stage='CLOSED', worker=None,
                                   scope=Path('/scope'), fence=Path('/fence'))
        with patch.object(qa, 'start_ticks', return_value=1):
            report = c.snapshot()
        self.assertTrue(report['service']['stdoutEof'])
        self.assertTrue(report['service']['stderrTailIsComplete'])
        self.assertEqual(report['service']['channel'], {'state': 'COMPLETED'})

    def test_faulty_snapshot_still_preserves_minimal_failure_diagnostic(self):
        c = qa.Controller('normal-01', 'normal')
        c.effects = True
        with patch.object(c, 'snapshot', side_effect=AttributeError('private')):
            result = c.failure_snapshot()
        self.assertEqual(result['snapshotUnavailable'], 'AttributeError')
        self.assertTrue(result['effectsAttempted'])
        self.assertNotIn('private', str(result))

    @unittest.skipUnless(hasattr(os, 'getuid') and os.getuid() == 0, 'peer requires root actor')
    def test_actual_unix_close_request_queued_once_and_reply_socket_gone(self):
        with tempfile.TemporaryDirectory(prefix='r168-sock-') as folder:
            c = qa.Controller('lostreply-01', 'lostreply')
            c.run = Path(folder)
            (c.run / 'control').mkdir()
            path = str(c.run / 'control/service.sock')
            owner = {'pid': os.getpid(), 'startTicks': 33, 'token': 'a' * 32}
            request = {'protocol': 'alaz-supervisor-control-v1', 'command': 'close',
                       'expectedOwner': owner, 'requestId': 'b' * 32, 'serviceId': 'c' * 32}
            raw = qa.canonical({'socketPath': path, 'request': request})
            with socket.socket(socket.AF_UNIX) as server:
                try:
                    server.bind(path)
                except PermissionError:
                    self.skipTest('execution sandbox refuses AF_UNIX bind; requires lab/CI kernel')
                server.listen(1)
                with patch.object(sys, 'stdin', type('Input', (), {'buffer': io.BytesIO(raw)})()), \
                        patch.object(os, 'getppid', return_value=os.getpid()), \
                        patch.object(qa, 'start_ticks', return_value=33):
                    result = qa.drop_reply_client(c)
                conn, _ = server.accept()
                with conn:
                    received = b''
                    while True:
                        part = conn.recv(4096)
                        if not part:
                            break
                        received += part
                    self.assertEqual(received, qa.canonical(request))
                    with self.assertRaises(BrokenPipeError):
                        conn.sendall(b'reply\n')
                self.assertTrue(result['sentOnce'])
                self.assertFalse(result['responseRead'])


class TransportTests(unittest.TestCase):
    def intent(self):
        return {'kind': 'R168A1_SERVICE_ACCEPT_INTENT', 'lab': transport.LAB,
            'inputRoot': '/opt/alaz-r168a1-qa-01', 'stateRoot': '/srv/alaz-r168a1-normal-01',
            'attemptId': 'normal-01', 'mode': 'normal', 'stageMode': 'fresh',
            'manifestSha256': '1' * 64, 'bundleSha256': '2' * 64, 'bundleBytes': 123,
            'transportSha256': '3' * 64, 'hostRunnerSha256': '4' * 64,
            'sourceFiles': {name: {'sha256': '5' * 64, 'size': 1} for name in transport.FILES},
            'baseCommit': '9440a2251d26db88b5f08a0e0292e73f4fbb6e57',
            'parentSealSha256': '65693d5e1453da650422d63b30b29e5b3ed291aad753b527ed24985e08456cd8'}

    def test_transport_accepts_only_named_new_scope(self):
        self.assertEqual(transport.validate_intent(self.intent()), self.intent())
        for key, value in (('stageMode', 'auto'), ('inputRoot', '/opt/alaz-r167a1'),
                           ('stateRoot', '/srv/foreign'), ('mode', 'lostreply'),
                           ('bundleBytes', True), ('baseCommit', 'a' * 40)):
            bad = self.intent()
            bad[key] = value
            with self.subTest(key=key), self.assertRaises(transport.TransportRejected):
                transport.validate_intent(bad)

    def test_unknown_custody_requires_same_live_original_pid_start(self):
        from types import SimpleNamespace
        intent = self.intent()
        identity = {'pid': 22, 'startTicks': 33}
        process = SimpleNamespace(pid=22, poll=lambda: None)
        report = {'kind': 'R168A1_REAL_SERVICE_LIFECYCLE', 'result': 'NOT_ACCEPTED',
            'attemptId': 'normal-01', 'mode': 'normal', 'state': 'OUTCOME_UNKNOWN',
            'partialStatePreserved': True, 'normalCloseClaimed': False,
            'automaticRetry': False, 'automaticCleanup': False, 'productionReady': False,
            'custody': {'state': 'RETAINED_CONTROLLER', **identity}}
        with patch.object(transport, 'process_identity', return_value=identity):
            result = transport.classify(process, identity, b'', transport.canonical(report), intent)
        self.assertTrue(result['verifiedLiveCustody'])
        with patch.object(transport, 'process_identity', return_value={'pid': 22, 'startTicks': 34}), \
                self.assertRaisesRegex(transport.TransportRejected, 'custody_not_live'):
            transport.classify(process, identity, b'', transport.canonical(report), intent)
        for key, value in (('state', 'REFUSED'), ('automaticRetry', True),
                           ('normalCloseClaimed', True), ('partialStatePreserved', False)):
            changed = dict(report, **{key: value})
            with self.subTest(key=key), self.assertRaisesRegex(transport.TransportRejected, 'retained_scope'):
                transport.classify(process, identity, b'', transport.canonical(changed), intent)


if __name__ == '__main__':
    unittest.main()
