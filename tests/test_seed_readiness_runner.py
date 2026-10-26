"""Owned host contracts only: every PASS below is a labelled synthetic double.

No WSL/root/native process is launched. Prepared evidence exists only inside
TemporaryDirectory fixtures with patched repository, source pins and HEAD.
"""
from __future__ import annotations

import base64
from copy import deepcopy
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
import zipfile

SOURCE = Path(__file__).resolve().parents[1] / 'scripts/qa/r155a1_accept.py'
SPEC = importlib.util.spec_from_file_location('owned_seed_readiness_runner', SOURCE)
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


def seed_double(home='/tmp/alaz-r155a1-ordinary001/profile', instance='r155a1-ordinary001'):
    """Typed synthetic records; no native schema, receipt or kernel acceptance."""
    identities = [[1801, 21], [1801, 22], [1801, 23]]
    retained = {'native_feature': runner.NATIVE, 'home': home, 'home_identity': [1801, 20],
                'database_identities': identities, 'epoch': 1, 'instance_id': instance,
                'discovery_sha256': 'a' * 64}
    wire = runner.canonical({'protocol': 'alaz-retained-startup-v1', 'retained': retained,
        'state': {'journal_mode': 'delete', 'epoch': 1, 'instance_id': instance,
                  'state_identity': identities[0], 'replay_identity': identities[1]},
        'response': {'response_identity': identities[2]}})[:-1].decode('ascii')
    return {'kind': 'R155A1_TASK_FREE_RETAINED_SEED', 'result': 'PASS',
        'state': 'RETAINED_SEED_CREATED', 'phase': 'COMPLETE', 'home': home,
        'pid': 123, 'parentPid': 100, 'startTicks': 456, 'gatewayUid': 23001,
        'socketGroupGid': 23003, 'supplementaryGroups': [23003], 'resUid': [23001] * 3,
        'resGid': [23003] * 3, 'mountNamespaceInode': 789, 'mountNamespace': 'mnt:[789]',
        'profileIdentity': [1801, 20], 'databaseIdentities': identities,
        'mount': {'mount_id': 10, 'device': [7, 9], 'root': '/', 'mount_point': '/',
                  'filesystem': 'ext4'}, 'handoff': wire, 'handoffSha256': runner.sha(wire.encode()),
        'previousEpoch': 1, 'instanceId': instance, 'ownerState': 'CLOSED', 'consumerState': 'DETACHED',
        'allThreeConnectionsPhysicallyClosed': True, 'profileLeaseReleasedNormally': True,
        'retainedCapturedWhileLeaseHeld': True, 'normalLoopShutdown': True,
        'outstandingAsyncTasks': 0, 'outstandingThreads': 0, 'completedChecks': list(runner.CHECKS),
        'coldHelperCalls': [{'phase': 'START_OWNER', 'script': name}
                           for name in ('run_store_preopen.py', 'run_response_preopen.py')],
        'sqliteOpenCount': 7, 'qualifiedNativeSourceCount': 500,
        'auxiliaryInitialization': {'sourceDerivedCacheEntries': 75,
            'sourceDerivedCacheSha256': 'a' * 64, 'completeToolRegistrationPerformed': False,
            'activeSessionEntries': 0,
            'blockedIpv6CapabilityProbe': {'count': 1, 'socketClosed': True, 'bindPerformed': False}},
        'executedTasks': 0, 'realModelCalls': 0, 'listenersCreated': 0, 'apiAdmissionPublished': False,
        'installationReceiptSha256': runner.RECEIPT_SHA, 'harnessCommit': runner.HARNESS,
        'nativeFeature': runner.NATIVE, 'verificationMillis': 1000, 'nativeMillis': 2000,
        'totalMillis': 3000, 'projectedReadinessAccepted': False, 'fullD3BAccepted': False,
        'automaticCleanup': False, 'automaticRetry': False}


def raw_row(raw):
    return {'bytes': len(raw), 'sha256': runner.sha(raw), 'base64': base64.b64encode(raw).decode('ascii')}


def caller_double(intent):
    seed = seed_double('/srv/alaz-r155a1/mount/profile', 'r155a1-seed')
    seed['supplementaryGroups'] = []
    value = {'kind': 'R155A1_SAME_IMAGE_SEED_READINESS', 'result': 'PASS',
        'state': 'SAME_IMAGE_SEED_READINESS_CLOSED', 'manifestSha256': intent['manifestSha256'],
        'seedResult': seed, 'readiness': {'state': 'SUPERVISED_PROJECTED_OWNER_CLOSED',
            'childExited': True, 'volumeMayClose': True, 'observedAfterUnknown': False,
            'finiteWorkExecuted': False, 'fullD3BAccepted': False,
            'owner': {'epoch': 2, 'completedChecks': list(runner.CHECKS)}},
        'closure': {'finish': {'state': 'CLOSED', 'ownedUsersGone': True, 'loopAttachmentGone': True,
                              'fenceRemovedAfterCleanup': True, 'leaseReleasedLast': True}},
        'executedTasks': 0, 'realModelCalls': 0}
    for name in ('projectedReadinessAccepted', 'sameImageSeedAndReadiness', 'sameOriginalSupervisor',
                 'allOwnedChildrenTerminal', 'hostMountNamespaceUnchanged', 'hostMountTableUnchanged',
                 'brokerMetadataFixtureOnly'):
        value[name] = True
    for name in ('realBrokerExchangeAccepted', 'serviceStarted', 'runtimeAdmissionAuthorized',
                 'finiteWorkExecuted', 'fullD3BAccepted', 'm1Accepted', 'productionReady',
                 'automaticCleanup', 'automaticRetry'):
        value[name] = False
    return value


def transport_double(intent, *, retained=False, caller=None):
    value = {'kind': 'R155A1_ROOT_TRANSPORT', 'rootUsed': True, 'automaticRetry': False,
        'automaticCleanup': False, 'phase': 'OBSERVED', 'pipesComplete': True,
        'intentSha256': runner.sha(runner.canonical(intent)), 'manifestSha256': intent['manifestSha256'],
        'callerPid': 50, 'callerStartTicks': 70}
    if retained:
        custody = {'state': 'RETAINED_CONTROLLER', 'pid': 50, 'startTicks': 70}
        caller = {'kind': 'R155A1_SAME_IMAGE_SEED_READINESS', 'result': 'NOT_ACCEPTED',
                  'state': 'OUTCOME_UNKNOWN', 'custody': custody}
        value.update(result='NOT_ACCEPTED', state='CALLER_RETAINED_OUTCOME_UNKNOWN',
                     callerTerminalObserved=False, verifiedLiveCustody=True, custody=custody,
                     caller=caller, stdout=raw_row(b''), stderr=raw_row(runner.canonical(caller)))
    else:
        caller = caller if caller is not None else caller_double(intent)
        value.update(result='PASS', state='CALLER_TERMINAL_ACCEPTED', callerTerminalObserved=True,
                     callerExitCode=0, caller=caller, stdout=raw_row(runner.canonical(caller)),
                     stderr=raw_row(b''))
    return value


class OwnedProcess:
    """Exercises Windows-style communicate reader calls without any subprocess."""
    pid = 999

    def __init__(self, out, err=b'', *, exit_code=0, timeout=False):
        self.stdout, self.stderr = io.BytesIO(out), io.BytesIO(err)
        self.returncode = exit_code
        self.timeout = timeout
        self.calls = []
        self.kill = Mock(side_effect=AssertionError('kill forbidden'))
        self.terminate = Mock(side_effect=AssertionError('terminate forbidden'))
        self.wait = Mock(side_effect=AssertionError('extra wait forbidden'))

    def communicate(self, raw, timeout):
        self.calls.append((raw, timeout))
        out, err = self.stdout.read(), self.stderr.read()
        if self.timeout:
            self.returncode = None
            raise subprocess.TimeoutExpired('owned-wsl-double', timeout, output=out, stderr=err)
        return out, err


class FixtureCase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='owned-r155-host-tests-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.evidence_base = self.root / 'evidence/m1-seed-readiness-r155a1'
        self.evidence_base.mkdir(parents=True)
        self.ordinary = self.evidence_base / 'ordinary001'
        self.ordinary.mkdir()
        self.evidence = self.evidence_base / 'accept001'
        self.producer = b'# OWNED producer double; never a native program.\n'
        self.caller = b'# OWNED caller double; never a root program.\n'
        self.child = b'# OWNED child double\n'
        self.transport = b'# OWNED transport double; never executed.\n'
        self.linux = b'# OWNED ordinary Linux runner double; never executed.\n'
        self.driver = ('PRODUCER_SHA = ' + repr(runner.sha(self.producer))
                       + '\nLINUX = ' + repr('\n' + self.linux.decode()) + '.lstrip()\n').encode()
        for name, raw in {runner.SEED: self.producer, runner.CALLER: self.caller,
                          runner.CHILD: self.child, runner.TRANSPORT: self.transport,
                          runner.ORDINARY_DRIVER: self.driver,
                          'scripts/qa/r155a1_accept.py': SOURCE.read_bytes()}.items():
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
        self.patches = [
            patch.object(runner, 'ROOT', self.root),
            patch.object(runner, 'SELF', self.root / 'scripts/qa/r155a1_accept.py'),
            patch.object(runner, 'REVIEWED_TRANSPORT_SHA', runner.sha(self.transport)),
            patch.object(runner, 'REVIEWED_CALLER_SHA', runner.sha(self.caller)),
            patch.object(runner, 'REVIEWED_CHILD_SHA', runner.sha(self.child)),
            patch.object(runner, 'current_head', return_value=runner.BASE_COMMIT),
            patch.object(runner, 'host_actor'),
            patch.object(runner, '_PENDING', []),
        ]
        for item in self.patches:
            item.start()
            self.addCleanup(item.stop)
        self.write_ordinary()

    def write_ordinary(self, *, seed=None, change_proof=None, change_result=None, change_start=None):
        seed = seed if seed is not None else seed_double()
        producer_out, producer_err = runner.canonical(seed), b'OWNED diagnostic double\n'
        proof = {'kind': 'R155A1_ORDINARY_NATIVE_SEED_PROOF', 'result': 'PASS', 'rootUsed': False,
            'projectedReadinessAccepted': False, 'sameImageReadinessAccepted': False,
            'fullD3BAccepted': False, 'automaticCleanup': False, 'automaticRetry': False,
            'nativeAccepted': True, 'phase': 'COMPLETE', 'path': '/tmp/alaz-r155a1-ordinary001',
            'sourceSha256': runner.sha(self.producer), 'sqliteVersion': '3.45.1',
            'sqliteVersionInfo': [3, 45, 1], 'controllerPid': 100, 'supplementaryGroups': [23003],
            'nativeProcessAttempted': True, 'producerPid': 123, 'producerExitCode': 0,
            'producerTerminalObserved': True, 'elapsedMillis': 4000,
            'producerStdoutSha256': runner.sha(producer_out), 'producerStderrSha256': runner.sha(producer_err),
            'producerStdoutBytes': len(producer_out), 'producerStderrBytes': len(producer_err),
            'producerStdoutBase64': base64.b64encode(producer_out).decode(),
            'producerStderrBase64': base64.b64encode(producer_err).decode(), 'seed': seed,
            'realModelCalls': 0, 'executedTasks': 0, 'physicalDatabaseCloseAccepted': True}
        if change_proof:
            change_proof(proof)
        out, err = runner.canonical(proof), b''
        result = {'result': 'PASS', 'exitCode': 0, 'rootRequested': False,
            'stdoutSha256': runner.sha(out), 'stderrSha256': runner.sha(err),
            'producerSha256': runner.sha(self.producer), 'automaticRetry': False,
            'automaticCleanup': False, 'proof': proof}
        if change_result:
            change_result(result)
        start = {'state': 'EXECUTION_STARTED_NO_REPLAY', 'attempt': 'ordinary001',
            'startedUtc': '2026-10-25T00:00:00+00:00', 'producerSha256': runner.sha(self.producer),
            'linuxRunnerSha256': runner.sha(self.linux), 'rootRequested': False, 'lab': runner.LAB}
        if change_start:
            change_start(start)
        files = {'result.json': runner.pretty(result), 'producer-source.py': self.producer,
                 'linux-runner.py': self.linux, 'execution-start.json': runner.pretty(start),
                 'stdout.txt': out, 'stderr.txt': err}
        for name, raw in files.items():
            (self.ordinary / name).write_bytes(raw)

    def prepare(self):
        result = runner.prepare(self.evidence, self.ordinary)
        self.intent = runner.parse((self.evidence / 'intent.json').read_bytes(), 16384)
        self.intent_sha = result['intentSha256']
        return result

    def apply_with(self, process):
        def spawn(command, **kwargs):
            marker = runner.parse((self.evidence / 'execution-start.json').read_bytes(), 8192)
            self.assertEqual(marker['state'], 'EXECUTION_STARTED_NO_REPLAY')
            self.assertEqual(marker['intentSha256'], self.intent_sha)
            self.assertEqual(command[:12], ['wsl.exe', '--distribution', runner.LAB, '--user',
                'root', '--cd', '/', '--exec', '/usr/bin/python3.12', '-I', '-B', '-c'])
            self.assertEqual(command[12], self.transport.decode())
            self.assertEqual(command[13], runner.canonical(self.intent).decode()[:-1])
            self.assertTrue(kwargs['close_fds'])
            return process
        with patch.object(runner.subprocess, 'Popen', side_effect=spawn) as popen:
            result = runner.apply(self.evidence, self.intent_sha)
        self.assertEqual(popen.call_count, 1)
        self.assertEqual(len(process.calls), 1)
        self.assertEqual(process.calls[0][1], 240)
        self.assertEqual(runner.sha(process.calls[0][0]), self.intent['bundleSha256'])
        process.kill.assert_not_called()
        process.terminate.assert_not_called()
        process.wait.assert_not_called()
        return result


class PreparationTests(FixtureCase):
    def test_prepare_requires_complete_proof_and_freezes_text_only_without_process(self):
        with patch.object(runner.subprocess, 'Popen') as process:
            receipt = self.prepare()
        process.assert_not_called()
        self.assertEqual(receipt['result'], 'PREPARED')
        self.assertFalse(receipt['rootRequested'])
        self.assertFalse((self.evidence / 'execution-start.json').exists())
        binding_raw = (self.evidence / 'ordinary-proof.json').read_bytes()
        binding = runner.parse(binding_raw, 8192)
        self.assertEqual(self.intent['ordinaryProofSha256'], runner.sha(binding_raw))
        self.assertEqual(set(binding['files']), runner.PROOF_FILES)
        encoded = (self.evidence / 'bundle.zip.b64').read_bytes()
        bundle = base64.b64decode(encoded[:-1], validate=True)
        self.assertEqual(encoded, base64.b64encode(bundle) + b'\n')
        self.assertEqual(runner.sha(bundle), self.intent['bundleSha256'])
        with zipfile.ZipFile(io.BytesIO(bundle)) as archive:
            self.assertEqual(set(archive.namelist()), runner.SOURCES | {'manifest.json'})
            self.assertTrue(all(item.compress_type == zipfile.ZIP_STORED for item in archive.infolist()))
        for path in self.evidence.rglob('*'):
            if path.is_file():
                raw = path.read_bytes()
                self.assertNotIn(b'\0', raw)
                self.assertLessEqual(len(raw), 2 * 1024 * 1024)

    def test_ordinary_refusal_root_or_nonterminal_claim_leaves_evidence_absent(self):
        for kind in ('refusal', 'root', 'exit', 'native', 'terminal', 'scope'):
            with self.subTest(kind=kind):
                changes = {
                    'refusal': lambda x: x.update(result='NOT_ACCEPTED'),
                    'root': lambda x: x.update(rootRequested=True),
                    'exit': lambda x: x.update(exitCode=False),
                }
                proof_changes = {
                    'native': lambda x: x.update(nativeAccepted=False),
                    'terminal': lambda x: x.update(producerTerminalObserved=False),
                    'scope': lambda x: x.update(realModelCalls=1),
                }
                self.write_ordinary(change_result=changes.get(kind), change_proof=proof_changes.get(kind))
                with patch.object(runner.subprocess, 'Popen') as process:
                    with self.assertRaises(runner.RunnerRejected):
                        runner.prepare(self.evidence, self.ordinary)
                process.assert_not_called()
                self.assertFalse(self.evidence.exists())

    def test_frozen_producer_runner_start_or_raw_hash_change_refuses_preparation(self):
        for name in ('producer-source.py', 'linux-runner.py', 'execution-start.json', 'stdout.txt', 'stderr.txt'):
            with self.subTest(name=name):
                self.write_ordinary()
                path = self.ordinary / name
                path.write_bytes(path.read_bytes() + b'changed')
                with self.assertRaises((runner.RunnerRejected, ValueError)):
                    runner.prepare(self.evidence, self.ordinary)
                self.assertFalse(self.evidence.exists())

    def test_seed_scope_and_physical_close_cannot_be_faked_by_outer_pass(self):
        for name, value in (('ownerState', 'OPEN'), ('normalLoopShutdown', False),
                            ('executedTasks', 1), ('apiAdmissionPublished', True),
                            ('previousEpoch', True), ('pid', 124)):
            with self.subTest(name=name):
                seed = seed_double()
                seed[name] = value
                self.write_ordinary(seed=seed)
                with self.assertRaises(runner.RunnerRejected):
                    runner.prepare(self.evidence, self.ordinary)
                self.assertFalse(self.evidence.exists())

    def test_current_head_and_fresh_evidence_are_required(self):
        with patch.object(runner, 'current_head', side_effect=runner.RunnerRejected('changed_head')):
            with self.assertRaises(runner.RunnerRejected):
                runner.prepare(self.evidence, self.ordinary)
        self.assertFalse(self.evidence.exists())
        self.prepare()
        with self.assertRaises(runner.RunnerRejected):
            runner.prepare(self.evidence, self.ordinary)

    def test_unreviewed_child_source_blocks_prepare_before_evidence_creation(self):
        (self.root / runner.CHILD).write_bytes(self.child + b'# changed owned child\n')
        with patch.object(runner.subprocess, 'Popen') as process:
            with self.assertRaisesRegex(runner.RunnerRejected, 'reviewed_sources_changed'):
                runner.prepare(self.evidence, self.ordinary)
        process.assert_not_called()
        self.assertFalse(self.evidence.exists())

    def test_blocked_probe_requires_exact_count_closed_socket_and_no_bind(self):
        for key, bad in (('count', True), ('count', 0), ('count', 2),
                         ('socketClosed', False), ('socketClosed', 1),
                         ('bindPerformed', True), ('bindPerformed', 0)):
            with self.subTest(key=key, bad=bad):
                seed = seed_double()
                seed['auxiliaryInitialization']['blockedIpv6CapabilityProbe'][key] = bad
                self.write_ordinary(seed=seed)
                with self.assertRaises(runner.RunnerRejected):
                    runner.prepare(self.evidence, self.ordinary)
                self.assertFalse(self.evidence.exists())


class ApplyTests(FixtureCase):
    def test_apply_single_fixed_launch_with_exclusive_marker_and_exact_bundle(self):
        self.prepare()
        process = OwnedProcess(runner.canonical(transport_double(self.intent)))
        result = self.apply_with(process)
        self.assertEqual(result['result'], 'PASS')
        self.assertTrue(result['projectedReadinessAccepted'])
        self.assertFalse(result['fullD3BAccepted'])
        self.assertFalse(result['productionReady'])
        self.assertEqual((self.evidence / 'stdout.txt').read_bytes(),
                         runner.canonical(transport_double(self.intent)))
        self.assertEqual(result['stdoutSha256'], runner.sha((self.evidence / 'stdout.txt').read_bytes()))
        with patch.object(runner.subprocess, 'Popen') as second:
            with self.assertRaisesRegex(runner.RunnerRejected, 'no_replay'):
                runner.apply(self.evidence, self.intent_sha)
        second.assert_not_called()

    def test_wrong_expected_intent_prevents_execution_marker(self):
        self.prepare()
        with patch.object(runner.subprocess, 'Popen') as process:
            with self.assertRaises(runner.RunnerRejected):
                runner.apply(self.evidence, '0' * 64)
        process.assert_not_called()
        self.assertFalse((self.evidence / 'execution-start.json').exists())

    def test_apply_revalidates_original_proof_and_current_host_source(self):
        self.prepare()
        original = self.ordinary / 'execution-start.json'
        before = original.read_bytes()
        changed = runner.parse(before, 8192, form='pretty')
        changed['startedUtc'] = '2026-10-25T00:01:00+00:00'
        original.write_bytes(runner.pretty(changed))
        with patch.object(runner.subprocess, 'Popen') as process:
            with self.assertRaises(runner.RunnerRejected):
                runner.apply(self.evidence, self.intent_sha)
        process.assert_not_called()
        self.assertFalse((self.evidence / 'execution-start.json').exists())
        original.write_bytes(before)
        runner.SELF.write_bytes(runner.SELF.read_bytes() + b'\n# owned changed self\n')
        with patch.object(runner.subprocess, 'Popen') as process:
            with self.assertRaises(runner.RunnerRejected):
                runner.apply(self.evidence, self.intent_sha)
        process.assert_not_called()
        self.assertFalse((self.evidence / 'execution-start.json').exists())

    def test_frozen_bundle_tamper_prevents_marker_and_spawn(self):
        self.prepare()
        frozen = self.evidence / 'bundle.zip.b64'
        frozen.write_bytes(frozen.read_bytes() + b'\n')
        with patch.object(runner.subprocess, 'Popen') as process:
            with self.assertRaises(runner.RunnerRejected):
                runner.apply(self.evidence, self.intent_sha)
        process.assert_not_called()
        self.assertFalse((self.evidence / 'execution-start.json').exists())

    def test_current_child_change_blocks_apply_before_execution_marker(self):
        self.prepare()
        (self.root / runner.CHILD).write_bytes(self.child + b'# changed after prepare\n')
        with patch.object(runner.subprocess, 'Popen') as process:
            with self.assertRaisesRegex(runner.RunnerRejected, 'reviewed_sources_changed'):
                runner.apply(self.evidence, self.intent_sha)
        process.assert_not_called()
        self.assertFalse((self.evidence / 'execution-start.json').exists())

    def test_blocked_stdin_worker_times_out_without_close_kill_or_second_invocation(self):
        self.prepare()
        entered, release = threading.Event(), threading.Event()
        process = OwnedProcess(b'', b'')
        raw_out, raw_err = process.stdout, process.stderr
        process.returncode = None
        calls = []
        def blocked_writer(raw, timeout):
            calls.append((raw, timeout))
            entered.set()
            release.wait()  # Owned fixture only; released by the test's finally.
            process.returncode = 0
            return b'', b''
        process.communicate = blocked_writer
        try:
            began = time.monotonic()
            with patch.object(runner.subprocess, 'Popen', return_value=process) as popen, \
                    patch.object(runner, 'COMMUNICATION_SECONDS', 0.03):
                result = runner.apply(self.evidence, self.intent_sha)
            self.assertLess(time.monotonic() - began, 1.0)
            self.assertTrue(entered.is_set())
            self.assertEqual(popen.call_count, 1)
            self.assertEqual(len(calls), 1)
            self.assertEqual(result['result'], 'UNKNOWN')
            self.assertEqual(result['reason'], 'runner_communication_deadline_unknown')
            self.assertFalse(result['transportTerminalObserved'])
            self.assertFalse(result['communicationCompletedWithinDeadline'])
            self.assertFalse(raw_out.closed)
            self.assertFalse(raw_err.closed)
            self.assertEqual(len(runner._PENDING), 1)
            kept_process, kept_readers, kept_communication = runner._PENDING[0]
            self.assertIs(kept_process, process)
            self.assertEqual(kept_readers, [process.stdout, process.stderr])
            self.assertTrue(kept_communication['worker'].daemon)
            self.assertTrue(kept_communication['worker'].is_alive())
            process.kill.assert_not_called()
            process.terminate.assert_not_called()
            process.wait.assert_not_called()
            with patch.object(runner.subprocess, 'Popen') as replay:
                with self.assertRaisesRegex(runner.RunnerRejected, 'no_replay'):
                    runner.apply(self.evidence, self.intent_sha)
            replay.assert_not_called()
        finally:
            release.set()  # Owned fixture teardown; no application process exists.
            if runner._PENDING:
                runner._PENDING[0][2]['worker'].join(timeout=1)

    def test_timeout_is_unknown_preserves_prefix_and_never_retries(self):
        self.prepare()
        process = OwnedProcess(b'owned partial stdout', b'owned partial stderr', timeout=True)
        result = self.apply_with(process)
        self.assertEqual(result['result'], 'UNKNOWN')
        self.assertFalse(result['transportTerminalObserved'])
        self.assertFalse(result['continuingLiveCustodyVerified'])
        self.assertEqual((self.evidence / 'stdout.txt').read_bytes(), b'owned partial stdout')
        self.assertTrue((self.evidence / 'execution-start.json').exists())
        with patch.object(runner.subprocess, 'Popen') as second:
            with self.assertRaises(runner.RunnerRejected):
                runner.apply(self.evidence, self.intent_sha)
        second.assert_not_called()

    def test_spawn_exception_is_unknown_after_marker_without_retry(self):
        self.prepare()
        with patch.object(runner.subprocess, 'Popen', side_effect=OSError('owned failure')) as process:
            result = runner.apply(self.evidence, self.intent_sha)
        self.assertEqual(process.call_count, 1)
        self.assertEqual(result['result'], 'UNKNOWN')
        self.assertTrue((self.evidence / 'execution-start.json').exists())
        self.assertEqual((self.evidence / 'stdout.txt').read_bytes(), b'')

    def test_retained_custody_is_only_an_observation_before_transport_exit(self):
        self.prepare()
        process = OwnedProcess(runner.canonical(transport_double(self.intent, retained=True)), exit_code=2)
        result = self.apply_with(process)
        self.assertEqual(result['result'], 'UNKNOWN')
        self.assertFalse(result['continuingLiveCustodyVerified'])
        self.assertEqual(result['custodyObservedBeforeTransportExit']['pid'], 50)
        self.assertFalse(result['projectedReadinessAccepted'])

    def test_transport_or_caller_provenance_and_scope_failure_cannot_pass(self):
        self.prepare()
        for fault in ('intent', 'manifest', 'caller_manifest', 'work', 'close'):
            with self.subTest(fault=fault):
                caller = caller_double(self.intent)
                if fault == 'caller_manifest':
                    caller['manifestSha256'] = '0' * 64
                if fault == 'work':
                    caller['realModelCalls'] = 1
                if fault == 'close':
                    caller['closure']['finish']['leaseReleasedLast'] = False
                value = transport_double(self.intent, caller=caller)
                if fault == 'intent':
                    value['intentSha256'] = '0' * 64
                if fault == 'manifest':
                    value['manifestSha256'] = '0' * 64
                with self.assertRaises(runner.RunnerRejected):
                    runner.transport_result(runner.canonical(value), b'', 0, self.intent)

    def test_capture_overflow_is_bounded_and_not_accepted(self):
        self.prepare()
        process = OwnedProcess(b'x' * (runner.MAX_OUTPUT + 1))
        result = self.apply_with(process)
        self.assertEqual(result['result'], 'UNKNOWN')
        self.assertTrue(result['stdoutOverflow'])
        self.assertEqual((self.evidence / 'stdout.txt').stat().st_size, runner.MAX_OUTPUT)

    def test_receipt_write_failure_cannot_leave_host_acceptance_true(self):
        self.prepare()
        process = OwnedProcess(runner.canonical(transport_double(self.intent)))
        original_put = runner.put
        def fail_receipt(path, raw):
            if Path(path).name == 'result.json':
                raise OSError('owned evidence failure')
            return original_put(path, raw)
        with patch.object(runner, 'put', side_effect=fail_receipt):
            result = self.apply_with(process)
        self.assertEqual(result['result'], 'UNKNOWN')
        self.assertFalse(result['projectedReadinessAccepted'])
        self.assertFalse(result['evidenceWriteComplete'])
        self.assertTrue((self.evidence / 'execution-start.json').exists())


class FileObservationTests(unittest.TestCase):
    """Exercise actual owned-file reads with controlled path/descriptor metadata."""
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='owned-r155-stat-tests-')
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name).resolve() / 'owned-source.py'
        self.raw = b'# owned byte fixture\n'
        self.path.write_bytes(self.raw)
        actual = self.path.stat()
        self.base = {name: getattr(actual, name) for name in
                     ('st_dev', 'st_ino', 'st_mode', 'st_size', 'st_mtime_ns', 'st_nlink')}
        self.base.update(st_ctime_ns=100, st_birthtime_ns=100, st_mtime_ns=200)

    def info(self, **changes):
        return SimpleNamespace(**{**self.base, **changes})

    def read_observed(self, platform, *, before=None, opened=None, after=None, last=None):
        before = before or self.info()
        opened = opened or self.info(st_ctime_ns=200)
        after = after or self.info(st_ctime_ns=200)
        last = last or self.info()
        with patch.object(runner, 'path_without_alias', return_value=self.path), \
                patch.object(runner.sys, 'platform', platform), \
                patch.object(type(self.path), 'lstat', side_effect=[before, last]), \
                patch.object(runner.os, 'fstat', side_effect=[opened, after]):
            return runner.read_file(self.path)

    def test_windows_cross_view_ctime_difference_is_allowed_only_when_both_views_stay_stable(self):
        self.assertEqual(self.read_observed('win32'), self.raw)

    def test_nonwindows_still_requires_equal_cross_view_ctime(self):
        with self.assertRaisesRegex(runner.RunnerRejected, 'file_changed'):
            self.read_observed('linux')
        self.assertEqual(self.read_observed('linux', opened=self.info(), after=self.info()), self.raw)

    def test_windows_descriptor_metadata_changes_remain_rejected(self):
        for change in ({'st_ctime_ns': 201}, {'st_birthtime_ns': 101},
                       {'st_mtime_ns': 201}, {'st_nlink': 2}, {'st_ino': self.base['st_ino'] + 1}):
            with self.subTest(change=change), self.assertRaisesRegex(runner.RunnerRejected, 'file_changed'):
                self.read_observed('win32', after=self.info(**{'st_ctime_ns': 200, **change}))

    def test_windows_path_metadata_changes_remain_rejected(self):
        for change in ({'st_ctime_ns': 101}, {'st_birthtime_ns': 101},
                       {'st_mtime_ns': 201}, {'st_nlink': 2}):
            with self.subTest(change=change), self.assertRaisesRegex(runner.RunnerRejected, 'file_changed'):
                self.read_observed('win32', last=self.info(**change))

    def test_windows_cross_view_identity_and_birthtime_must_still_match(self):
        for change in ({'st_birthtime_ns': 101}, {'st_mtime_ns': 201},
                       {'st_nlink': 2}, {'st_ino': self.base['st_ino'] + 1}):
            opened = self.info(**{'st_ctime_ns': 200, **change})
            with self.subTest(change=change), self.assertRaisesRegex(runner.RunnerRejected, 'file_changed'):
                self.read_observed('win32', opened=opened, after=opened)


class ParserAndCaptureTests(unittest.TestCase):
    def test_json_and_base64_have_one_exact_encoding(self):
        for raw in (b'{}\n{}\n', b'{"x":1,"x":2}\n', b'{"x":NaN}\n', b'{"x":1.0}\n', b'{}\r\n'):
            with self.subTest(raw=raw), self.assertRaises(runner.RunnerRejected):
                runner.parse(raw, 8192)
        for value in ('YQ==\n', 'YQ=', '!'):
            with self.subTest(value=value), self.assertRaises(runner.RunnerRejected):
                runner.b64(value, 10)

    def test_capture_reader_retains_only_bound_and_drains_to_eof(self):
        raw = io.BytesIO(b'a' * 100)
        reader = runner.BoundedPipe(raw)
        with patch.object(runner, 'MAX_OUTPUT', 32):
            self.assertEqual(reader.read(), b'a' * 32)
        data, complete, overflow, error = reader.snapshot()
        self.assertEqual(len(data), 32)
        self.assertTrue(complete)
        self.assertTrue(overflow)
        self.assertIsNone(error)
        self.assertEqual(raw.tell(), 100)

    def test_ordinary_literals_are_read_without_executing_source(self):
        raw = b'raise RuntimeError("must never run")\nPRODUCER_SHA = "fixed"\nLINUX = "\\nowned\\n".lstrip()\n'
        self.assertEqual(runner.ordinary_literals(raw), ('fixed', b'owned\n'))

    @unittest.skipUnless(sys.platform == 'win32', 'Owned Windows stdio fixture; no WSL or native program')
    def test_actual_windows_three_pipe_communication_with_owned_finite_child(self):
        # Root may run this on Windows during source verification. The only
        # child is an isolated Python stdio fixture, with no file/site access.
        code = ('import hashlib,sys\n'
                'data=sys.stdin.buffer.read()\n'
                'sys.stdout.buffer.write(hashlib.sha256(data).hexdigest().encode()+b"\\n")\n'
                'sys.stderr.buffer.write(b"owned-windows-stdio-fixture\\n")\n')
        payload = b'owned-input-larger-than-one-pipe-buffer\n' * 4096
        process = subprocess.Popen([sys.executable, '-I', '-B', '-c', code],
                                   stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, close_fds=True, bufsize=0)
        returned_at = time.monotonic()
        readers = [runner.BoundedPipe(process.stdout), runner.BoundedPipe(process.stderr)]
        process.stdout, process.stderr = readers
        observation = {}
        try:
            runner.communicate_bounded(process, payload, observation, returned_at)
            self.assertEqual(process.returncode, 0)
            self.assertEqual(readers[0].snapshot(), ((runner.sha(payload) + '\n').encode(), True, False, None))
            self.assertEqual(readers[1].snapshot(), (b'owned-windows-stdio-fixture\n', True, False, None))
        except BaseException:
            runner._PENDING.append((process, readers, observation))
            raise


if __name__ == '__main__':
    unittest.main()
