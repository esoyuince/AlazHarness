"""Owned source/byte fixtures only; never a candidate install or native acceptance."""
import ast
import base64
from copy import deepcopy
import importlib.util
import json
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'scripts/qa/r156a1_prepare.py'
SPEC = importlib.util.spec_from_file_location('owned_r156_preparation', SOURCE)
prepare = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(prepare)

from test_projected_install import source_fixture, seal


class OwnedCandidateFixture(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='owned-r156-preparation-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        for name in ('scripts/build_projected_candidate.py', 'scripts/install_projected_candidate.py',
                     prepare.INSTALL_TEMPLATE):
            target = self.root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, target)
        self.source, _ = source_fixture()
        self.manifest, self.archive = seal(self.source)
        self.candidate = self.root / 'owned-candidate'
        self.candidate.mkdir()
        self.write_candidate()
        self.output = self.root / 'scratch/r156-preparation/owned-attempt'

    def write_candidate(self):
        self.manifest_raw = prepare.canonical(self.manifest)
        (self.candidate / 'manifest.json').write_bytes(self.manifest_raw)
        (self.candidate / 'projected-source.tar').write_bytes(self.archive)

    def kwargs(self):
        return {'harness_commit': self.manifest['harnessCommit'],
                'manifest_sha': prepare.sha(self.manifest_raw),
                'archive_sha': prepare.sha(self.archive)}

    def run_prepare(self):
        return prepare.prepare_install(self.root, self.candidate, self.output, **self.kwargs())

    def binding(self):
        return prepare.verified_candidate(self.root, self.candidate, **self.kwargs())


class InstallationPreparationTests(OwnedCandidateFixture):
    def test_verified_fixture_renders_fixed_operator_without_processes_or_execution_claims(self):
        with patch.object(subprocess, 'Popen', side_effect=AssertionError('process forbidden')):
            result = self.run_prepare()
        self.assertEqual(result['state'], 'INSTALL_OPERATOR_PREPARED_NOT_RUN')
        self.assertEqual(result['sourceFileCount'], len(self.source))
        for key in ('installed', 'rootRequested', 'nativeExecuted', 'finiteWorkExecuted',
                    'acceptancePrepared', 'automaticRetry', 'automaticCleanup'):
            self.assertIs(result[key], False)
        self.assertIsNone(result['installationReceiptSha256'])
        self.assertEqual(result['realProviderCalls'], 0)
        self.assertEqual({p.name for p in self.output.iterdir()}, {
            'installation-binding.json', 'r156a1_install_candidate.py',
            'linux-transport.py', 'preparation.json'})
        raw = (self.output / result['operatorFile']).read_bytes()
        self.assertEqual(prepare.sha(raw), result['operatorSha256'])
        compile(raw, '<owned-rendered-install-operator>', 'exec')
        self.assertEqual(prepare._literal_assignment(raw, 'SOURCE'), self.manifest['harnessCommit'])
        self.assertEqual(prepare._literal_assignment(raw, 'MANIFEST_SHA'), prepare.sha(self.manifest_raw))
        self.assertEqual(prepare._literal_assignment(raw, 'ARCHIVE_SHA'), prepare.sha(self.archive))
        self.assertEqual(prepare._literal_assignment(raw, 'INPUT'), prepare.INSTALL_INPUT)
        self.assertEqual(prepare._literal_assignment(raw, 'DESTINATION'), prepare.DESTINATION)
        self.assertEqual(prepare._literal_assignment(raw, 'BUILDER_SHA'), prepare.BUILDER_SHA)
        self.assertEqual(prepare._literal_assignment(raw, 'NATIVE'), prepare.NATIVE)
        transport = (self.output / 'linux-transport.py').read_bytes()
        self.assertEqual(transport, prepare._literal_assignment(raw, 'LINUX_TRANSPORT').encode())
        self.assertEqual(prepare.sha(transport), result['transportSha256'])
        self.assertIn(prepare.INSTALL_INPUT.encode(), transport)
        self.assertNotIn(b'/opt/alaz-r154a1', transport)
        self.assertNotIn(b'R154A1_SOURCE_INSTALL', raw)

    def test_source_count_is_derived_from_verified_candidate_not_hardcoded_as_838(self):
        result = self.run_prepare()
        self.assertEqual(result['sourceFileCount'], 834)  # Owned 77-harness-file fixture.
        raw = (self.output / 'linux-transport.py').read_bytes()
        count_checks = [node for node in ast.walk(ast.parse(raw)) if isinstance(node, ast.Compare)
                        and isinstance(node.left, ast.Subscript)
                        and isinstance(node.left.slice, ast.Constant)
                        and node.left.slice.value == 'sourceFileCount']
        self.assertEqual(len(count_checks), 1)
        self.assertEqual(ast.literal_eval(count_checks[0].comparators[0]), len(self.source))

    def test_changed_template_refuses_before_output(self):
        path = self.root / prepare.INSTALL_TEMPLATE
        path.write_bytes(path.read_bytes() + b'# owned changed template\n')
        with self.assertRaisesRegex(ValueError, 'template_changed'):
            self.run_prepare()
        self.assertFalse(self.output.exists())

    def test_changed_installer_refuses_before_output(self):
        path = self.root / 'scripts/install_projected_candidate.py'
        path.write_bytes(path.read_bytes() + b'# owned changed verifier\n')
        with self.assertRaisesRegex(ValueError, 'template_changed'):
            self.run_prepare()
        self.assertFalse(self.output.exists())

    def test_changed_manifest_external_pin_refuses_before_output(self):
        args = self.kwargs()
        args['manifest_sha'] = '0' * 64  # Explicit invalid owned-fixture pin.
        with self.assertRaisesRegex(ValueError, 'template_changed'):
            prepare.prepare_install(self.root, self.candidate, self.output, **args)
        self.assertFalse(self.output.exists())

    def test_incomplete_commit_is_not_replaced_with_a_placeholder(self):
        args = self.kwargs()
        args['harness_commit'] = None
        with self.assertRaisesRegex(ValueError, 'exact_digest_required'):
            prepare.prepare_install(self.root, self.candidate, self.output, **args)
        self.assertFalse(self.output.exists())

    def test_missing_finite_entry_in_resealed_candidate_refuses_before_output(self):
        del self.source['scripts/run_finite_projected.py']
        self.manifest, self.archive = seal(self.source)
        self.manifest['harnessSourceFileCount'] -= 1
        self.write_candidate()
        with self.assertRaisesRegex(ValueError, 'required_sources'):
            self.run_prepare()
        self.assertFalse(self.output.exists())

    def test_native_revision_remains_fixed(self):
        self.manifest['nativeFeature'] = 'b' * 40
        self.write_candidate()
        with self.assertRaisesRegex(ValueError, 'manifest_schema'):
            self.run_prepare()
        self.assertFalse(self.output.exists())

    def test_existing_output_is_not_overwritten(self):
        first = self.run_prepare()
        saved = {p.name: p.read_bytes() for p in self.output.iterdir()}
        with self.assertRaisesRegex(ValueError, 'fresh_owned_output_required'):
            self.run_prepare()
        self.assertEqual(saved, {p.name: p.read_bytes() for p in self.output.iterdir()})
        self.assertEqual(first, json.loads(saved['preparation.json']))

    def test_output_outside_owned_preparation_tree_refuses(self):
        self.output = self.root / 'outside'
        with self.assertRaisesRegex(ValueError, 'fresh_owned_output_required'):
            self.run_prepare()
        self.assertFalse(self.output.exists())

    def test_explicit_binding_rejects_extra_fields_and_alternate_runtime_roots(self):
        original = self.binding()
        for key, value in (('unexpected', True), ('destination', '/opt/alaz-r154a1'),
                           ('acceptanceInput', prepare.INSTALL_INPUT), ('sourceFileCount', True)):
            binding = deepcopy(original)
            binding[key] = value
            with self.subTest(field=key), self.assertRaises(prepare.PreparationRejected):
                prepare.render_install_operator((self.root / prepare.INSTALL_TEMPLATE).read_bytes(), binding)


class AcceptancePreparationTests(OwnedCandidateFixture):
    def setUp(self):
        super().setUp()
        for name in (*prepare.SEED_TEMPLATES, prepare.ACCEPT_TEMPLATES):
            target = self.root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, target)
        for leaf in ('gateway_finite_protocol.py', 'state_image_lease.py',
                     'state_volume_supervisor.py', 'gateway_storage_mounts.py'):
            name = 'packages/claw-hermes/' + leaf
            if name not in self.source:
                del self.source[next(n for n in self.source if n.startswith('packages/claw-hermes/fixture_'))]
            self.source[name] = (ROOT / name).read_bytes()
        self.manifest, self.archive = seal(self.source)
        self.write_candidate()
        self.install_binding = self.binding()
        self.binding_path = self.root / 'owned-installation-binding.json'
        self.binding_path.write_bytes(prepare.canonical(self.install_binding))
        self.receipt = self.receipt_double()
        self.receipt_raw = prepare.canonical(self.receipt)
        self.receipt_path = self.root / 'owned-installation-receipt.json'
        self.receipt_path.write_bytes(self.receipt_raw)
        self.receipt_sha = prepare.sha(self.receipt_raw)

    def receipt_double(self):
        b = self.install_binding
        return {'schemaVersion': 1, 'kind': 'VERIFIED_PROJECTED_INSTALLATION',
            'destination': prepare.DESTINATION, 'sourceManifestSha256': b['manifestSha256'],
            'archiveSha256': b['archiveSha256'], 'harnessCommit': b['harnessCommit'],
            'nativeFeature': prepare.NATIVE, 'sourceFileCount': b['sourceFileCount'],
            'dependencyFileCount': 1162, 'dependencyInventorySha256': prepare.sha(self.source['accepted-dependencies.json']),
            'python': {'path': '/usr/bin/python3.12', 'sha256': prepare.PYTHON_SHA,
                       'device': 7, 'inode': 19, 'uid': 0, 'gid': 0, 'mode': 0o755},
            'rootDevice': 7, 'rootInode': 23, 'sourceAndDependenciesReadBack': True,
            'rootControlledAncestryVerified': True, 'installed': True, 'executionAuthorized': False,
            'projectedReadinessAccepted': False, 'finiteWorkExecuted': False, 'realModelCalls': 0}

    def render(self):
        return prepare.render_acceptance(self.root, self.install_binding, self.receipt_raw,
            self.receipt_sha, self.source, base_commit='a' * 40)

    def load(self, name, raw):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        module_name = 'owned_r156_' + path.stem
        module = types.ModuleType(module_name)
        module.__file__ = str(path)
        sys.modules[module_name] = module
        self.addCleanup(sys.modules.pop, module_name, None)
        exec(compile(raw, str(path), 'exec'), module.__dict__)
        return module

    def validator(self):
        files = self.render()
        return self.load(prepare.FINITE_ENTRY, files[prepare.FINITE_ENTRY])

    def finite_double(self, validator):
        cases = []
        for index, kind in enumerate(('normal', 'replay', 'new', 'error')):
            request_kind = 'normal' if kind == 'replay' else kind
            cases.append({'kind': kind, 'requestId': validator.WORK['requestIds'][request_kind],
                'admissionId': 'owned:' + request_kind, 'outcome': 'failed' if kind == 'error' else 'completed',
                'apiResultSha256': 'b' * 64, 'storedResultSha256': 'c' * 64,
                'computationCount': (1, 1, 2, 3)[index]})
        owner = {'protocol': validator.RESULT_PROTOCOL, 'state': 'PROJECTED_FINITE_OWNER_CLOSED',
            'pid': 47, 'epoch': 2, 'completedChecks': list(validator.COMPLETED_CHECKS),
            'workSha256': validator.work_digest(validator.WORK), 'caseReceipts': cases,
            'nativeProfileCallEvents': {name: 1 for name in validator.PROFILE_FUNCTIONS},
            'close': {'consumerState': 'DETACHED', 'ownerState': 'CLOSED', 'sameThreeConnections': True,
                'registryRefcounts': 0, 'physicalConnectionsClosed': 3, 'modelInstancesClosed': True,
                'rowsChangedByRetirement': 0, 'callerLeaseReleased': True},
            'model': {'kind': 'scripted-factory-fixture', 'factoryComputationCloseDoubled': True,
                'realProviderCalls': 0, 'modelInvocations': 3}, 'localAdmissionActivated': True,
            'canonicalApiPublished': True, 'serviceStarted': False, 'runtimeAdmissionAuthorized': False,
            'finiteWorkExecuted': True, 'fullD3BAccepted': False}
        return {'state': 'SUPERVISED_PROJECTED_FINITE_OWNER_CLOSED', 'pid': 47,
            'childStartTicks': 53, 'owner': owner, 'inputSha256': 'd' * 64,
            'stdoutSha256': prepare.sha(validator.canonical(owner) + b'\n'),
            'stderrSha256': prepare.sha(b''), 'stderrBytes': 0,
            'observedAfterUnknown': False, 'childExited': True, 'volumeMayClose': True,
            'finiteWorkExecuted': True, 'fullD3BAccepted': False}

    def caller_double(self, validator):
        finite = self.finite_double(validator)
        out = validator.canonical(finite['owner']) + b'\n'
        row = lambda raw: {'bytes': len(raw), 'sha256': prepare.sha(raw),
                           'base64': base64.b64encode(raw).decode('ascii')}
        return {'kind': 'R156A1_SAME_IMAGE_SEED_FINITE', 'result': 'PASS',
            'state': 'SAME_IMAGE_SEED_FINITE_CLOSED', 'manifestSha256': 'e' * 64,
            'projectedFiniteAccepted': True, 'sameImageSeedAndFinite': True, 'sameOriginalSupervisor': True,
            'allOwnedChildrenTerminal': True, 'hostMountNamespaceUnchanged': True,
            'hostMountTableUnchanged': True, 'brokerMetadataFixtureOnly': True,
            'finiteWorkExecuted': True, 'realBrokerExchangeAccepted': False, 'serviceStarted': False,
            'runtimeAdmissionAuthorized': False, 'fullD3BAccepted': False, 'm1Accepted': False,
            'productionReady': False, 'automaticCleanup': False, 'automaticRetry': False,
            'executedTasks': 3, 'scriptedModelInvocations': 3, 'realModelCalls': 0, 'realProviderCalls': 0,
            'seedResult': {'installationReceiptSha256': self.receipt_sha,
                'harnessCommit': self.install_binding['harnessCommit'], 'previousEpoch': 1},
            'installation': {'receiptSha256': self.receipt_sha, 'harnessCommit': self.install_binding['harnessCommit'],
                'destination': prepare.DESTINATION, 'verifiedInstalledBytesNow': True},
            'finite': finite, 'observations': {'retained': {'phase': 'COMPLETED', 'pid': 47,
                'startTicks': 53, 'exitCode': 0, 'complete': True, 'overflowed': False,
                'inputWritten': 123, 'payloadSha256': 'd' * 64, 'stdout': row(out), 'stderr': row(b'')}},
            'closure': {'finish': {'state': 'CLOSED', 'ownedUsersGone': True, 'loopAttachmentGone': True,
                'fenceRemovedAfterCleanup': True, 'leaseReleasedLast': True}}}

    def test_receipt_bound_sources_render_without_processes_or_acceptance_claims(self):
        with patch.object(subprocess, 'Popen', side_effect=AssertionError('process forbidden')):
            result = prepare.prepare_acceptance(self.root, self.binding_path, self.receipt_path, self.output,
                receipt_sha=self.receipt_sha, base_commit='a' * 40)
        self.assertEqual(result['state'], 'ACCEPTANCE_SOURCES_PREPARED_NOT_RUN')
        self.assertEqual(len(result['files']), 7)
        for key in ('installedBytesVerifiedNow', 'ordinaryProofAccepted', 'rootRequested',
                    'nativeExecuted', 'finiteWorkExecuted', 'sameImageFiniteAccepted', 'fullD3BAccepted'):
            self.assertIs(result[key], False)
        for name, row in result['files'].items():
            raw = (self.output / name).read_bytes()
            self.assertEqual(prepare.sha(raw), row['sha256'])
            self.assertEqual(len(raw), row['bytes'])
            compile(raw, name, 'exec')
        for name, digest in prepare.SEED_TEMPLATES.items():
            self.assertEqual(prepare.sha((self.root / name).read_bytes()), digest)

    def test_absent_receipt_cannot_render_placeholder_sources(self):
        with self.assertRaisesRegex(ValueError, 'actual_receipt_digest_required'):
            prepare.render_acceptance(self.root, self.install_binding, None, None, self.source, base_commit='a' * 40)

    def test_old_installation_receipt_is_rejected_even_with_its_matching_digest(self):
        receipt = dict(self.receipt, destination='/opt/alaz-r154a1', harnessCommit='e03f7fd4e47fea6a58b749564ab350aeb4237a26')
        raw = prepare.canonical(receipt)
        with self.assertRaisesRegex(ValueError, 'receipt_binding'):
            prepare.verify_receipt(raw, prepare.sha(raw), self.install_binding)

    def test_receipt_claiming_work_or_wrong_dependency_inventory_is_rejected(self):
        for key, value in (('finiteWorkExecuted', True), ('dependencyInventorySha256', '0' * 64)):
            raw = prepare.canonical(dict(self.receipt, **{key: value}))
            with self.subTest(field=key), self.assertRaises(prepare.PreparationRejected):
                prepare.render_acceptance(self.root, self.install_binding, raw, prepare.sha(raw),
                                         self.source, base_commit='a' * 40)

    def test_changed_original_seed_helper_is_not_silently_repinned(self):
        sources = dict(self.source)
        sources['packages/claw-hermes/state_image_lease.py'] += b'# changed owned fixture\n'
        with self.assertRaisesRegex(ValueError, 'seed_helper_changed'):
            prepare.render_acceptance(self.root, self.install_binding, self.receipt_raw,
                                      self.receipt_sha, sources, base_commit='a' * 40)

    def test_rendered_producer_native_algorithm_and_offline_boundary_are_unchanged(self):
        old = (self.root / 'scripts/bootstrap_retained_profile.py').read_bytes()
        new = self.render()['scripts/bootstrap_retained_profile_r156.py']
        for name in ('native_lifecycle', 'OfflineBoundary', 'configure_environment', 'validate_actor'):
            before = next(n for n in ast.parse(old).body if getattr(n, 'name', None) == name)
            after = next(n for n in ast.parse(new).body if getattr(n, 'name', None) == name)
            self.assertEqual(prepare._node_bytes(old, before), prepare._node_bytes(new, after))

    def test_generated_sources_load_as_modules_with_fixed_inputs_and_budget(self):
        files = self.render()
        modules = {name: self.load(name, raw) for name, raw in files.items()}
        caller = modules['scripts/qa/r156a1_linux_accept.py']
        host = modules['scripts/qa/r156a1_accept.py']
        transport = modules['scripts/qa/r156a1_linux_transport.py']
        self.assertEqual((caller.SEED_SECONDS, caller.FINITE_SECONDS, caller.STOP_MARGIN), (35, 60, 15))
        self.assertLess(caller.SEED_SECONDS + caller.FINITE_SECONDS + caller.STOP_MARGIN, 120)
        self.assertEqual(caller.INPUT_FILES, host.SOURCES)
        self.assertEqual(caller.INPUT_FILES, transport.FILES)
        self.assertEqual(len(host.SOURCES), 4)
        sources, raw_transport, _, ordinary = host.current_inputs()
        self.assertEqual(sources[prepare.FINITE_ENTRY], files[prepare.FINITE_ENTRY])
        self.assertEqual(raw_transport, files['scripts/qa/r156a1_linux_transport.py'])
        self.assertEqual(host.ordinary_literals(ordinary)[0], prepare.sha(files['scripts/bootstrap_retained_profile_r156.py']))
        intent = {'kind': 'R156A1_SAME_IMAGE_ACCEPT_INTENT', 'lab': 'AlazHarness-D3B-P71C',
            'inputRoot': prepare.ACCEPT_INPUT, 'stateRoot': '/srv/alaz-r156a1',
            'manifestSha256': 'a' * 64, 'bundleSha256': 'b' * 64, 'bundleBytes': 123,
            'transportSha256': prepare.sha(raw_transport), 'hostRunnerSha256': 'c' * 64,
            'ordinaryProofSha256': 'd' * 64, 'ordinaryProducerSha256': prepare.sha(sources[host.SEED]),
            'sourceFiles': {name: host.row(raw) for name, raw in sources.items()}, 'baseCommit': 'a' * 40}
        # This is a Linux transport imported by a host-side owned fixture.
        # Preserve its POSIX path spelling when the fixture runs on Windows.
        with patch.object(transport, 'INPUT', PurePosixPath(prepare.ACCEPT_INPUT)):
            transport.validate_intent(intent)
        host.command_for({'transport.py': raw_transport}, intent)

    def test_exact_four_cases_and_original_captured_close_accept_as_declared_owned_fixture(self):
        validator = self.validator()
        value = self.caller_double(validator)
        self.assertEqual(validator.validate_caller(value, 'e' * 64), value)

    def test_bad_finite_semantics_cannot_be_hidden_by_outer_pass_and_resealed_stdout(self):
        validator = self.validator()
        mutations = (
            lambda v: v['caseReceipts'][1].update(computationCount=2),
            lambda v: v['caseReceipts'][2].update(admissionId=v['caseReceipts'][0]['admissionId']),
            lambda v: v['caseReceipts'][3].update(outcome='completed'),
            lambda v: v['close'].update(physicalConnectionsClosed=2),
            lambda v: v['model'].update(realProviderCalls=1),
            lambda v: v.update(canonicalApiPublished=False),
        )
        for mutate in mutations:
            value = self.caller_double(validator)
            mutate(value['finite']['owner'])
            raw = validator.canonical(value['finite']['owner']) + b'\n'
            value['finite']['stdoutSha256'] = prepare.sha(raw)
            value['observations']['retained']['stdout'] = {'bytes': len(raw), 'sha256': prepare.sha(raw),
                'base64': base64.b64encode(raw).decode('ascii')}
            with self.subTest(change=mutate), self.assertRaises(validator.FiniteProtocolRejected):
                validator.validate_caller(value, 'e' * 64)

    def test_live_or_mismatched_original_child_cannot_claim_close(self):
        validator = self.validator()
        for field, change in (('pid', 99), ('exitCode', None), ('complete', False),
                              ('inputWritten', True), ('overflowed', True)):
            value = self.caller_double(validator)
            value['observations']['retained'][field] = change
            with self.subTest(field=field), self.assertRaises(validator.FiniteProtocolRejected):
                validator.validate_caller(value, 'e' * 64)

    def test_single_finite_call_then_original_observer_no_readiness_invocation(self):
        files = self.render()
        caller = self.load('scripts/qa/r156a1_linux_accept.py', files['scripts/qa/r156a1_linux_accept.py'])
        validator = self.load(prepare.FINITE_ENTRY, files[prepare.FINITE_ENTRY])
        receipt = self.finite_double(validator)
        calls = []
        class Volume:
            def run_finite(self, *args, **kwargs):
                calls.append(('run_finite', args, kwargs))
                return deepcopy(receipt)
            def observe_finite(self):
                calls.append(('observe_finite',))
                return deepcopy(receipt)
        controller = caller.Controller()
        controller.seed = {'phase': 'COMPLETED'}
        controller.volume = Volume()
        controller.modules = types.SimpleNamespace(finite=validator)
        controller.run_finite('ipc', 'fs', 'retained-record')
        self.assertEqual([row[0] for row in calls], ['run_finite', 'observe_finite'])
        self.assertEqual(calls[0][1], ('ipc', 'fs', 'retained-record', validator.WORK))
        self.assertEqual(calls[0][2]['timeout'], 60)
        self.assertEqual(controller.events, ['PROJECTED_FINITE_ATTEMPT', 'PROJECTED_FINITE_COMPLETED'])

    def test_host_rejects_changed_shared_finite_validator_before_preparation(self):
        files = self.render()
        for name, raw in files.items():
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
        host = self.load('scripts/qa/r156a1_accept.py', files['scripts/qa/r156a1_accept.py'])
        path = self.root / prepare.FINITE_ENTRY
        path.write_bytes(path.read_bytes() + b'# owned changed validator\n')
        with self.assertRaisesRegex(ValueError, 'reviewed_sources_changed'):
            host.current_inputs()


if __name__ == '__main__':
    unittest.main()
