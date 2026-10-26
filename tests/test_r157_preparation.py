"""Owned R157 preparation contracts; no Git, WSL, root or native process runs.

Original receipt/proof inputs are authenticated tracked bytes, read only. Each
test works in a disposable copy. The 838-entry source-shape fixture below is
explicitly not a candidate: only its inventory and three helper bytes are real.
The full-candidate verifier seam is doubled only in publication-unit tests.
"""
from __future__ import annotations

import ast
import base64
from copy import deepcopy
import importlib.util
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import Mock, patch
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('owned_r157_preparation', ROOT / 'scripts/qa/r157a1_prepare.py')
prepare = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(prepare)
INSTALLATION = 'evidence/m1-finite-product-r156a1/installation'
DEPENDENCY_RECORD = 'evidence/d3b-confined-consumer-f126c1/native-006-result.json'
HOST = 'scripts/qa/r157a1_accept.py'
CALLER = 'scripts/qa/r157a1_linux_accept.py'
CHILD = 'scripts/qa/r157a1_seed_child.py'
TRANSPORT = 'scripts/qa/r157a1_linux_transport.py'
HELPERS = tuple('packages/claw-hermes/' + name + '.py' for name in (
    'state_image_lease', 'state_volume_supervisor', 'gateway_storage_mounts'))


class OwnedPreparationFixture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.binding_raw = (ROOT / INSTALLATION / 'installation-binding.json').read_bytes()
        cls.receipt_raw = (ROOT / INSTALLATION / 'installation-receipt.json').read_bytes()
        assert prepare.sha(cls.binding_raw) == prepare.BINDING_SHA
        assert prepare.sha(cls.receipt_raw) == prepare.RECEIPT_SHA
        record = json.loads((ROOT / DEPENDENCY_RECORD).read_bytes())
        assert type(record['nativeExitCode']) is int and record['nativeExitCode'] == 0
        assert record['sourceBytesUnchanged'] is True
        assert record['installedBytesMatchPriorAcceptedTarget'] is True
        dependencies = {name.removeprefix('dependencies/'): digest
                        for name, digest in record['sources'].items() if name.startswith('dependencies/')}
        assert len(dependencies) == 1162
        cls.inventory_raw = prepare.canonical(dependencies)
        assert prepare.sha(cls.inventory_raw) == prepare.DEPENDENCY_INVENTORY_SHA

    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='owned-r157-preparation-')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        names = [prepare.HELPER, *prepare.TEMPLATES, prepare.PRODUCER, prepare.ORDINARY_DRIVER,
                 *HELPERS, 'scripts/build_projected_candidate.py', 'scripts/install_projected_candidate.py']
        names += [prepare.ORIGINAL_PROOF + '/' + name for name in prepare.ORIGINAL_PROOF_ROWS]
        for name in names:
            target = self.root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, target)
        self.binding_path = self.root / 'original-installation-binding.json'
        self.receipt_path = self.root / 'original-installation-receipt.json'
        self.binding_path.write_bytes(self.binding_raw)
        self.receipt_path.write_bytes(self.receipt_raw)
        self.sources = {'accepted-dependencies.json': self.inventory_raw,
                        **{name: (self.root / name).read_bytes() for name in HELPERS}}
        for index in range(prepare.SOURCE_COUNT - len(self.sources)):
            self.sources[f'tests/owned-source-shape-{index:04d}.py'] = b''
        self.ordinary = self.root / prepare.ORIGINAL_PROOF
        self.evidence = self.root / prepare.EVIDENCE / 'readiness001'
        self.output = self.root / 'scratch/r157-preparation/owned-source001'
        self.process_guard = patch.object(subprocess, 'Popen', side_effect=AssertionError('process forbidden'))
        self.process_guard.start()
        self.addCleanup(self.process_guard.stop)

    def render(self):
        return prepare.render_readiness(self.root, self.binding_path.read_bytes(),
            self.receipt_path.read_bytes(), self.sources)

    def load(self, name, raw):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        module_name = 'owned_r157_' + path.stem
        module = types.ModuleType(module_name)
        module.__file__ = str(path)
        sys.modules[module_name] = module
        self.addCleanup(sys.modules.pop, module_name, None)
        exec(compile(raw, str(path), 'exec', dont_inherit=True), module.__dict__)
        return module

    def host(self):
        files = self.render()
        for name, raw in files.items():
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
        return self.load(HOST, files[HOST]), files

    def frozen_host(self):
        host, files = self.host()
        with patch.object(host, 'current_head', return_value=prepare.BASE_COMMIT):
            receipt = host.prepare(self.evidence, self.ordinary)
        return host, files, receipt

    def publish_with_owned_candidate_double(self):
        with patch.object(prepare, 'verified_sources', return_value=self.sources) as verifier:
            report = prepare.prepare_sources(self.root, self.binding_path, self.receipt_path, self.output)
        verifier.assert_called_once()
        return report


class SourcePreparationTests(OwnedPreparationFixture):
    def test_exact_four_sources_are_deterministic_and_reuse_r156_bytes(self):
        before = {(self.root / name).as_posix(): (self.root / name).read_bytes()
                  for name in (*prepare.TEMPLATES, prepare.PRODUCER, prepare.ORDINARY_DRIVER)}
        first, second = self.render(), self.render()
        self.assertEqual(first, second)
        self.assertEqual(set(first), prepare.GENERATED_FILES)
        self.assertEqual(len(first), 4)
        self.assertEqual(before, {name: Path(name).read_bytes() for name in before})
        host = self.load(HOST, first[HOST])
        transport = self.load(TRANSPORT, first[TRANSPORT])
        self.assertEqual(host.SOURCES, {prepare.PRODUCER, CALLER, CHILD})
        self.assertEqual(transport.FILES, host.SOURCES)
        self.assertEqual(host.BASE_COMMIT, prepare.BASE_COMMIT)
        self.assertEqual(host.HARNESS, prepare.HARNESS)
        self.assertNotEqual(host.BASE_COMMIT, host.HARNESS)
        self.assertEqual(host.ORDINARY_DRIVER, prepare.ORDINARY_DRIVER)
        self.assertEqual(host.RECEIPT_SHA, prepare.RECEIPT_SHA)
        self.assertEqual(host.REVIEWED_PRODUCER_SHA, prepare.PRODUCER_SHA)
        for name, raw in first.items():
            compile(raw, name, 'exec')
            self.assertNotIn(b'r157a1_finite_assert', raw)
            self.assertNotIn(b'R157A1_TASK_FREE_RETAINED_SEED', raw)
            self.assertNotIn(b'R157A1_ORDINARY_NATIVE_SEED_PROOF', raw)

    def test_readiness_controller_and_unknown_custody_methods_remain_byte_exact(self):
        files = self.render()
        helper = prepare.reviewed_helpers(self.root)
        original = (self.root / 'scripts/qa/r155a1_linux_accept.py').read_bytes()
        current = files[CALLER]
        for raw in (original, current):
            tree = ast.parse(raw)
            controller = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'Controller')
            methods = {n.name: helper._node_bytes(raw, n) for n in controller.body if isinstance(n, ast.FunctionDef)}
            if raw is original:
                prior = methods
            else:
                for name in ('run_readiness', 'close_volume', 'stop_broker', 'snapshot'):
                    self.assertEqual(methods[name], prior[name], name)
        prior_custody = next(n for n in ast.parse(original).body if isinstance(n, ast.FunctionDef) and n.name == 'retain_alive')
        current_custody = next(n for n in ast.parse(current).body if isinstance(n, ast.FunctionDef) and n.name == 'retain_alive')
        self.assertEqual(helper._node_bytes(original, prior_custody), helper._node_bytes(current, current_custody))
        caller = self.load(CALLER, current)
        self.assertEqual((caller.SEED_SECONDS, caller.READY_SECONDS, caller.STOP_MARGIN), (35, 60, 15))

    def test_original_binding_and_receipt_stay_exact_with_separate_execution_binding(self):
        report = self.publish_with_owned_candidate_double()
        self.assertEqual(report['state'], 'READINESS_SOURCES_PREPARED_NOT_RUN')
        self.assertEqual(report['generatedFileCount'], 4)
        for key in ('installedBytesVerifiedNow', 'nativeExecuted', 'finiteWorkExecuted', 'rootRequested',
                    'projectedReadinessAccepted', 'sameImageReadinessAccepted', 'fullD3BAccepted',
                    'originalOrdinaryProofReexecuted', 'automaticRetry', 'automaticCleanup'):
            self.assertIs(report[key], False)
        self.assertEqual(report['executedTasks'], 0)
        self.assertEqual(report['realModelCalls'], 0)
        self.assertEqual((self.output / 'installation-binding.json').read_bytes(), self.binding_raw)
        self.assertEqual((self.output / 'installation-receipt.json').read_bytes(), self.receipt_raw)
        raw = (self.output / 'execution-binding.json').read_bytes()
        execution = json.loads(raw)
        self.assertEqual(prepare.sha(raw), report['executionBindingSha256'])
        self.assertEqual(execution['repositoryRoot'], str(self.root))
        self.assertNotEqual(execution['repositoryRoot'], json.loads(self.binding_raw)['repositoryRoot'])
        self.assertEqual(execution['installedHarnessCommit'], prepare.HARNESS)
        self.assertEqual(execution['baseCommit'], prepare.BASE_COMMIT)
        self.assertEqual(execution['acceptanceInput'], prepare.ACCEPT_INPUT)
        self.assertEqual(execution['installationInput'], prepare.INSTALL_INPUT)
        self.assertEqual(execution['stateRoot'], prepare.STATE_ROOT)
        self.assertEqual(execution['cgroup'], prepare.CGROUP)
        self.assertEqual(execution['ipcRoot'], prepare.IPC)
        self.assertEqual(set(execution['generatedFiles']), prepare.GENERATED_FILES)
        self.assertEqual(set(execution['stagedSources']), {prepare.PRODUCER, CALLER, CHILD})
        self.assertEqual(set(execution['reusedSources']), {prepare.PRODUCER, prepare.ORDINARY_DRIVER})
        found = {p.relative_to(self.output).as_posix() for p in self.output.rglob('*') if p.is_file()}
        self.assertEqual(found, prepare.GENERATED_FILES | {'installation-binding.json',
            'installation-receipt.json', 'execution-binding.json', 'preparation.json'})

    def test_candidate_verifier_allows_only_explicit_repository_root_difference(self):
        binding = json.loads(self.binding_raw)
        actual = {**binding, 'repositoryRoot': str(self.root)}
        helper = types.SimpleNamespace(verified_candidate=Mock(return_value=(actual, self.sources)))
        self.assertIs(prepare.verified_sources(helper, self.root, binding), self.sources)
        helper.verified_candidate.assert_called_once_with(self.root, binding['candidateDirectory'],
            harness_commit=prepare.HARNESS, manifest_sha=prepare.MANIFEST_SHA,
            archive_sha=prepare.ARCHIVE_SHA, with_sources=True)
        for key, value in (('sourceFileCount', 837), ('harnessCommit', prepare.BASE_COMMIT),
                           ('manifestSha256', '0' * 64), ('archiveSha256', '0' * 64),
                           ('nativeFeature', '0' * 40), ('candidateDirectory', str(self.root)),
                           ('repositoryRoot', binding['repositoryRoot'])):
            helper.verified_candidate.return_value = ({**actual, key: value}, self.sources)
            with self.subTest(field=key), self.assertRaisesRegex(ValueError, 'candidate_binding_changed'):
                prepare.verified_sources(helper, self.root, binding)

    def test_candidate_verification_failure_precedes_render_and_output(self):
        with (patch.object(prepare, 'verified_sources', side_effect=ValueError('owned_invalid_candidate')),
              patch.object(prepare, 'render_readiness') as renderer):
            with self.assertRaisesRegex(ValueError, 'owned_invalid_candidate'):
                prepare.prepare_sources(self.root, self.binding_path, self.receipt_path, self.output)
        renderer.assert_not_called()
        self.assertFalse(self.output.exists())

    def test_changed_helper_or_each_template_or_reused_source_refuses(self):
        for name in (prepare.HELPER, *prepare.TEMPLATES, prepare.PRODUCER, prepare.ORDINARY_DRIVER):
            path = self.root / name
            raw = path.read_bytes()
            path.write_bytes(raw + b'# owned mutation\n')
            try:
                with self.subTest(source=name), self.assertRaises(ValueError):
                    self.render()
            finally:
                path.write_bytes(raw)
        self.assertFalse(self.output.exists())

    def test_each_binding_or_receipt_mutation_refuses_before_render(self):
        for path in (self.binding_path, self.receipt_path):
            raw = path.read_bytes()
            value = json.loads(raw)
            variants = [raw + b'\n', prepare.canonical({**value, 'harnessCommit': prepare.BASE_COMMIT}),
                        prepare.canonical({**value, 'sourceFileCount': True}),
                        prepare.canonical({**value, 'sourceFileCount': 837}),
                        prepare.canonical({**value, 'unexpected': True}),
                        prepare.canonical({**value, 'destination': '/opt/alaz-r157a1'})]
            if path == self.receipt_path:
                variants += [prepare.canonical({**value, 'projectedReadinessAccepted': True}),
                             prepare.canonical({**value, 'executionAuthorized': True}),
                             prepare.canonical({**value, 'finiteWorkExecuted': True})]
            for changed in variants:
                path.write_bytes(changed)
                with self.subTest(path=path.name, changed=prepare.sha(changed)), self.assertRaises(ValueError):
                    self.render()
            path.write_bytes(raw)
        self.assertFalse(self.output.exists())

    def test_source_count_inventory_and_helper_mutations_refuse(self):
        original = self.sources
        variants = [dict(list(original.items())[:-1]), {**original, 'unexpected.py': b'owned'},
                    {**original, 'accepted-dependencies.json': self.inventory_raw + b'\n'}]
        variants += [{**original, name: original[name] + b'# owned mutation\n'} for name in HELPERS]
        for index, changed in enumerate(variants):
            self.sources = changed
            with self.subTest(index=index), self.assertRaises(ValueError):
                self.render()
        self.sources = original

    def test_generation_counts_do_not_accept_unreviewed_template_shape(self):
        helper = prepare.reviewed_helpers(self.root)
        raw = (self.root / 'scripts/qa/r155a1_seed_child.py').read_bytes()
        with self.assertRaisesRegex(ValueError, 'literal_generation_count'):
            prepare.version_literals(helper, raw + b"\nEXTRA = 'r155a1'\n", 8)
        host = (self.root / 'scripts/qa/r155a1_accept.py').read_bytes()
        tree = ast.parse(host)
        node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'proof_bytes')
        altered = helper._replace_nodes(host, [(node, b'def proof_bytes(directory):\n    return {}')])
        with self.assertRaisesRegex(ValueError, 'proof_guard_count'):
            prepare.original_proof_guard(helper, altered)

    def test_output_reuse_and_outside_path_refuse_without_overwrite(self):
        self.publish_with_owned_candidate_double()
        before = {p.relative_to(self.output).as_posix(): p.read_bytes()
                  for p in self.output.rglob('*') if p.is_file()}
        with self.assertRaisesRegex(ValueError, 'fresh_owned_output'):
            self.publish_with_owned_candidate_double()
        self.assertEqual(before, {p.relative_to(self.output).as_posix(): p.read_bytes()
                                 for p in self.output.rglob('*') if p.is_file()})
        self.output = self.root / 'outside'
        with self.assertRaisesRegex(ValueError, 'fresh_owned_output'):
            self.publish_with_owned_candidate_double()
        self.assertFalse(self.output.exists())

    @unittest.skipIf(sys.platform == 'win32', 'Creating test symlinks requires unrelated Windows privileges')
    def test_source_and_output_aliases_refuse(self):
        path = self.root / prepare.PRODUCER
        saved = self.root / 'saved-producer.py'
        path.rename(saved)
        path.symlink_to(saved)
        with self.assertRaisesRegex(ValueError, 'source_alias'):
            self.render()
        path.unlink()
        saved.rename(path)
        outside = self.root / 'owned-real-output'
        outside.mkdir()
        alias = self.root / 'scratch'
        alias.symlink_to(outside, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'fresh_owned_output'):
            self.publish_with_owned_candidate_double()
        self.assertEqual(list(outside.iterdir()), [])


class OriginalProofAndHostTests(OwnedPreparationFixture):
    def test_original_proof_pass_and_fresh_three_source_freeze_roundtrip(self):
        host, _, receipt = self.frozen_host()
        self.assertEqual(receipt['result'], 'PREPARED')
        self.assertEqual(receipt['producerSha256'], prepare.PRODUCER_SHA)
        with patch.object(host, 'current_head', return_value=prepare.BASE_COMMIT):
            _, intent, files = host.load_prepared(self.evidence, receipt['intentSha256'])
        self.assertEqual(intent['inputRoot'], prepare.ACCEPT_INPUT)
        self.assertEqual(intent['stateRoot'], prepare.STATE_ROOT)
        self.assertEqual(set(intent['sourceFiles']), {prepare.PRODUCER, CALLER, CHILD})
        ordinary = host.parse(files['ordinary-proof.json'], 8192)
        self.assertEqual(ordinary['ordinaryDirectory'], str(self.ordinary))
        self.assertEqual(ordinary['files'], prepare.ORIGINAL_PROOF_ROWS)
        manifest = host.parse(files['manifest.json'], 8192)
        self.assertEqual(manifest['protocol'], 'alaz-r157a1-input-v1')
        archive = base64.b64decode(files['bundle.zip.b64'])
        with zipfile.ZipFile(io.BytesIO(archive)) as zipped:
            self.assertEqual(set(zipped.namelist()), host.SOURCES | {'manifest.json'})
            for name in host.SOURCES:
                self.assertEqual(zipped.read(name), (self.root / name).read_bytes())

    def test_old_proof_read_scope_and_new_evidence_write_scope_are_disjoint(self):
        host, _ = self.host()
        alternatives = [self.root / prepare.EVIDENCE / 'ordinary001',
                        self.ordinary.parent / 'ordinary002', self.root / 'ordinary001']
        for wrong in alternatives:
            shutil.copytree(self.ordinary, wrong)
            with self.subTest(path=str(wrong)), patch.object(host, 'current_head') as head:
                with self.assertRaisesRegex(ValueError, 'original_ordinary_directory'):
                    host.prepare(self.evidence, wrong)
                head.assert_not_called()
                with self.assertRaisesRegex(ValueError, 'original_ordinary_directory'):
                    host.proof_bytes(wrong)
            self.assertFalse(self.evidence.exists())
        with self.assertRaisesRegex(ValueError, 'owned_evidence_directory'):
            host.owned_directory(self.ordinary, exists=True)
        with self.assertRaisesRegex(ValueError, 'original_ordinary_read_only'):
            host.original_ordinary_directory(self.ordinary, exists=False)

    def test_all_six_proof_file_pins_and_inventory_are_revalidated(self):
        host, _ = self.host()
        for name in prepare.ORIGINAL_PROOF_ROWS:
            path = self.ordinary / name
            raw = path.read_bytes()
            path.write_bytes(raw + b'\n')
            try:
                with self.subTest(file=name), self.assertRaisesRegex(ValueError, 'original_ordinary_bytes_changed'):
                    host.proof_bytes(self.ordinary)
            finally:
                path.write_bytes(raw)
        extra = self.ordinary / 'unreviewed.txt'
        extra.write_bytes(b'owned extra file\n')
        with self.assertRaisesRegex(ValueError, 'original_ordinary_inventory'):
            host.proof_bytes(self.ordinary)
        with self.assertRaisesRegex(ValueError, 'original_ordinary_inventory'):
            self.render()

    def test_r156_inner_seed_kind_is_required_even_when_outer_record_hashes_are_coherent(self):
        host, _ = self.host()
        original = host.proof_bytes(self.ordinary)
        producer = (self.root / prepare.PRODUCER).read_bytes()
        driver = (self.root / prepare.ORDINARY_DRIVER).read_bytes()
        for wrong in ('R155A1_TASK_FREE_RETAINED_SEED', 'R157A1_TASK_FREE_RETAINED_SEED'):
            proof = host.parse(original['stdout.txt'], host.MAX_SOURCE)
            seed = host.parse(base64.b64decode(proof['producerStdoutBase64']), 32768)
            seed['kind'] = wrong
            out = host.canonical(seed)
            proof.update(seed=seed, producerStdoutBase64=base64.b64encode(out).decode(),
                         producerStdoutSha256=host.sha(out), producerStdoutBytes=len(out))
            proof_raw = host.canonical(proof)
            result = host.parse(original['result.json'], host.MAX_OUTPUT, form='pretty')
            result.update(proof=proof, stdoutSha256=host.sha(proof_raw))
            files = {**original, 'stdout.txt': proof_raw, 'result.json': host.pretty(result)}
            with self.subTest(kind=wrong), self.assertRaisesRegex(ValueError, 'seed_identity'):
                host.validate_ordinary(files, producer, driver)

    def test_reused_r156_source_changes_after_preparation_refuse(self):
        host, _, receipt = self.frozen_host()
        for name in (prepare.PRODUCER, prepare.ORDINARY_DRIVER):
            path = self.root / name
            raw = path.read_bytes()
            path.write_bytes(raw + b'# owned change after freeze\n')
            try:
                with self.subTest(file=name), patch.object(host, 'current_head', return_value=prepare.BASE_COMMIT):
                    with self.assertRaisesRegex(ValueError, 'original_r156_sources_changed'):
                        host.load_prepared(self.evidence, receipt['intentSha256'])
            finally:
                path.write_bytes(raw)

    def test_original_proof_mutation_after_preparation_refuses(self):
        host, _, receipt = self.frozen_host()
        path = self.ordinary / 'stdout.txt'
        path.write_bytes(path.read_bytes() + b'\n')
        with patch.object(host, 'current_head', return_value=prepare.BASE_COMMIT):
            with self.assertRaisesRegex(ValueError, 'original_ordinary_bytes_changed'):
                host.load_prepared(self.evidence, receipt['intentSha256'])
        self.assertFalse((self.evidence / 'execution-start.json').exists())

    def test_coherent_rebinding_to_other_proof_directory_refuses(self):
        host, _, receipt = self.frozen_host()
        wrong = self.root / prepare.EVIDENCE / 'ordinary001'
        shutil.copytree(self.ordinary, wrong)
        binding_path = self.evidence / 'ordinary-proof.json'
        binding = host.parse(binding_path.read_bytes(), 8192)
        binding['ordinaryDirectory'] = str(wrong)
        binding_path.write_bytes(host.canonical(binding))
        intent_path = self.evidence / 'intent.json'
        intent = host.parse(intent_path.read_bytes(), 16384)
        intent['ordinaryProofSha256'] = host.sha(binding_path.read_bytes())
        intent_path.write_bytes(host.canonical(intent))
        with patch.object(host, 'current_head', return_value=prepare.BASE_COMMIT):
            with self.assertRaisesRegex(ValueError, 'original_ordinary_directory'):
                host.load_prepared(self.evidence, host.sha(intent_path.read_bytes()))
        self.assertFalse((self.evidence / 'execution-start.json').exists())

    def test_intent_frozen_bundle_extra_file_and_execution_marker_refuse(self):
        host, _, receipt = self.frozen_host()
        with patch.object(host, 'current_head', return_value=prepare.BASE_COMMIT):
            with self.assertRaisesRegex(ValueError, 'expected_intent_changed'):
                host.load_prepared(self.evidence, '0' * 64)
            bundle = self.evidence / 'bundle.zip.b64'
            raw = bundle.read_bytes()
            bundle.write_bytes(raw[:-2] + b'A\n')
            with self.assertRaisesRegex(ValueError, 'frozen_bytes_changed'):
                host.load_prepared(self.evidence, receipt['intentSha256'])
            bundle.write_bytes(raw)
            extra = self.evidence / 'extra.txt'
            extra.write_bytes(b'owned extra\n')
            with self.assertRaisesRegex(ValueError, 'frozen_inventory'):
                host.load_prepared(self.evidence, receipt['intentSha256'])
            extra.unlink()
            (self.evidence / 'execution-start.json').write_bytes(b'owned already-started marker\n')
            with self.assertRaisesRegex(ValueError, 'execution_no_replay'):
                host.load_prepared(self.evidence, receipt['intentSha256'])


class ReadinessObservationTests(OwnedPreparationFixture):
    def owned_caller(self, host, intent):
        """A labelled synthetic R157 observation, never persisted as native evidence."""
        original = host.parse((self.ordinary / 'stdout.txt').read_bytes(), host.MAX_SOURCE)
        seed = deepcopy(original['seed'])
        seed['home'], seed['instanceId'] = '/srv/alaz-r157a1/mount/profile', 'r157a1-seed'
        seed['supplementaryGroups'] = []
        handoff = host.parse(seed['handoff'].encode(), 16384, form='wire')
        handoff['retained'].update(home=seed['home'], instance_id=seed['instanceId'])
        handoff['state']['instance_id'] = seed['instanceId']
        seed['handoff'] = host.canonical(handoff)[:-1].decode()
        seed['handoffSha256'] = host.sha(seed['handoff'].encode())
        caller = {'kind': 'R157A1_SAME_IMAGE_SEED_READINESS', 'result': 'PASS',
            'state': 'SAME_IMAGE_SEED_READINESS_CLOSED', 'manifestSha256': intent['manifestSha256'],
            'seedResult': seed, 'executedTasks': 0, 'realModelCalls': 0,
            'readiness': {'state': 'SUPERVISED_PROJECTED_OWNER_CLOSED', 'childExited': True,
                'volumeMayClose': True, 'observedAfterUnknown': False, 'finiteWorkExecuted': False,
                'fullD3BAccepted': False, 'owner': {'epoch': 2, 'completedChecks': host.CHECKS}},
            'closure': {'finish': {'state': 'CLOSED', 'ownedUsersGone': True, 'loopAttachmentGone': True,
                'fenceRemovedAfterCleanup': True, 'leaseReleasedLast': True}}}
        caller.update({key: True for key in ('projectedReadinessAccepted', 'sameImageSeedAndReadiness',
            'sameOriginalSupervisor', 'allOwnedChildrenTerminal', 'hostMountNamespaceUnchanged',
            'hostMountTableUnchanged', 'brokerMetadataFixtureOnly')})
        caller.update({key: False for key in ('realBrokerExchangeAccepted', 'serviceStarted',
            'runtimeAdmissionAuthorized', 'finiteWorkExecuted', 'fullD3BAccepted', 'm1Accepted',
            'productionReady', 'automaticCleanup', 'automaticRetry')})
        return caller

    def frame(self, host, intent, caller):
        out = host.canonical(caller)
        row = lambda raw: {'bytes': len(raw), 'sha256': host.sha(raw),
                          'base64': base64.b64encode(raw).decode()}
        return host.canonical({'kind': 'R157A1_ROOT_TRANSPORT', 'result': 'PASS', 'rootUsed': True,
            'automaticRetry': False, 'automaticCleanup': False, 'phase': 'OBSERVED',
            'state': 'CALLER_TERMINAL_ACCEPTED', 'intentSha256': host.sha(host.canonical(intent)),
            'manifestSha256': intent['manifestSha256'], 'pipesComplete': True,
            'callerTerminalObserved': True, 'callerExitCode': 0, 'callerPid': 101, 'callerStartTicks': 103,
            'caller': caller, 'stdout': row(out), 'stderr': row(b'')})

    def test_owned_epoch_two_zero_work_observation_is_accepted_without_native_invocation(self):
        host, _ = self.host()
        intent = {'manifestSha256': 'a' * 64}
        caller = self.owned_caller(host, intent)
        value = host.transport_result(self.frame(host, intent, caller), b'', 0, intent)
        self.assertEqual(value['state'], 'SAME_IMAGE_SEED_READINESS_ACCEPTED')
        self.assertIs(value['continuingLiveCustodyVerified'], False)
        self.assertEqual(caller['seedResult']['kind'], 'R156A1_TASK_FREE_RETAINED_SEED')

    def test_finite_work_stale_epoch_or_incomplete_close_never_becomes_readiness_pass(self):
        host, _ = self.host()
        intent = {'manifestSha256': 'a' * 64}
        changes = [lambda c: c.update(finiteWorkExecuted=True), lambda c: c.update(executedTasks=1),
                   lambda c: c.update(realModelCalls=1), lambda c: c.update(productionReady=True),
                   lambda c: c.update(kind='R156A1_SAME_IMAGE_SEED_FINITE'),
                   lambda c: c['seedResult'].update(kind='R157A1_TASK_FREE_RETAINED_SEED'),
                   lambda c: c['readiness']['owner'].update(epoch=1),
                   lambda c: c['readiness'].update(observedAfterUnknown=True),
                   lambda c: c['readiness'].update(childExited=False),
                   lambda c: c['readiness'].update(volumeMayClose=False),
                   lambda c: c['closure']['finish'].update(leaseReleasedLast=False)]
        for index, change in enumerate(changes):
            caller = self.owned_caller(host, intent)
            change(caller)
            with self.subTest(fault=index), self.assertRaises(ValueError):
                host.transport_result(self.frame(host, intent, caller), b'', 0, intent)

    def test_live_unknown_custody_never_waits_signals_or_claims_terminal_success(self):
        files = self.render()
        transport = self.load(TRANSPORT, files[TRANSPORT])
        identity = {'pid': 41, 'startTicks': 43}
        process = types.SimpleNamespace(pid=41, poll=Mock(return_value=None),
            wait=Mock(side_effect=AssertionError('wait forbidden')),
            kill=Mock(side_effect=AssertionError('kill forbidden')),
            terminate=Mock(side_effect=AssertionError('terminate forbidden')))
        caller = {'kind': 'R157A1_SAME_IMAGE_SEED_READINESS', 'result': 'NOT_ACCEPTED',
            'state': 'OUTCOME_UNKNOWN', 'custody': {'state': 'RETAINED_CONTROLLER', **identity}}
        with patch.object(transport, 'process_identity', return_value=identity):
            result = transport.classify(process, identity, b'', transport.canonical(caller))
            self.assertEqual(result['state'], 'CALLER_RETAINED_OUTCOME_UNKNOWN')
            self.assertIs(result['callerTerminalObserved'], False)
            for wrong in (42, True):
                caller['custody']['pid'] = wrong
                with self.assertRaises(transport.TransportRejected):
                    transport.classify(process, identity, b'', transport.canonical(caller))
        for operation in (process.wait, process.kill, process.terminate):
            operation.assert_not_called()


if __name__ == '__main__':
    unittest.main()
