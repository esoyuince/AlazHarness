"""R167 focused installer evidence; owned fixtures, not privileged install acceptance."""
from __future__ import annotations

import argparse
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import sys
import time
import unittest

if not __debug__:
    raise RuntimeError('optimized evidence collection is forbidden')
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = 'evidence/p2-service-install-r167a1'
RUNNER = 'scripts/qa/run_r167_install_focus.py'
MODULES = ('test_projected_candidate', 'test_projected_install', 'test_service_candidate', 'test_service_install')
SOURCE_FILES = ('scripts/build_service_candidate.py', 'scripts/verify_service_candidate.py', 'scripts/install_service_candidate.py')
TEST_FILES = tuple('tests/' + name + '.py' for name in MODULES)
SUPPORT_FILES = ('LICENSE', 'SECURITY.md', 'config/admission-consumer-b129d6-sources.json', 'config/borrowed-service-r159a1-host-lock.json', 'config/borrowed-service-r159a1-sources.json', 'config/canonical-api-consumer-i133p1-sources.json', 'config/components.lock.json', 'config/execution-gate/source-lock.json', 'config/finite-close-f135c6-sources.json', 'config/hermes-borrowed-service-r159a1.json', 'config/hermes-finite-close-f135c6.json', 'config/linux-prepared-dependencies-l125p1.json', 'config/prepared-consumer-s124b1-sources.json', 'config/retained-profile-r140c6-sources.json', 'docs/THIRD-PARTY.md', 'packages/claw-hermes/UPSTREAM.md', 'packages/claw-hermes/gateway_finite_protocol.py', 'packages/claw-hermes/gateway_finite_runtime.py', 'packages/claw-hermes/gateway_prepared_consumer.py', 'packages/claw-hermes/gateway_retained_handoff.py', 'packages/claw-hermes/gateway_retained_launch.py', 'packages/claw-hermes/gateway_retained_profile.py', 'packages/claw-hermes/gateway_retained_projection.py', 'packages/claw-hermes/gateway_service_control.py', 'packages/claw-hermes/gateway_service_factory.py', 'packages/claw-hermes/gateway_service_handoff.py', 'packages/claw-hermes/gateway_service_launch.py', 'packages/claw-hermes/gateway_service_profile.py', 'packages/claw-hermes/gateway_service_projection.py', 'packages/claw-hermes/gateway_service_runtime.py', 'packages/claw-hermes/gateway_service_sources.py', 'packages/claw-hermes/gateway_state_projection.py', 'packages/claw-hermes/gateway_store_startup.py', 'packages/claw-hermes/gateway_supervised_launch.py', 'packages/claw-hermes/gateway_supervised_service.py', 'packages/claw-hermes/hermes-runs.mjs', 'packages/claw-hermes/host-gate-client.mjs', 'packages/claw-hermes/local-control.mjs', 'packages/claw-hermes/package.json', 'packages/claw-hermes/run-recovery.mjs', 'packages/claw-hermes/service-control.mjs', 'packages/claw-hermes/service-task.mjs', 'packages/claw-hermes/service_control_server.py', 'packages/claw-hermes/service_task_http.py', 'packages/claw-hermes/service_task_protocol.py', 'packages/claw-hermes/service_task_server.py', 'packages/claw-hermes/service_volume_supervisor.py', 'packages/claw-hermes/state_image_lease.py', 'packages/claw-hermes/state_volume_supervisor.py', 'packages/claw-hermes/supervised_pipe_capture.py', 'packages/claw-hermes/supervised_service_channel.py', 'packages/upstream/hermes/LICENSE', 'packages/upstream/hermes/hermes_state_keys.py', 'packages/upstream/hermes/terminal_status.py', 'packages/upstream/openclaw/LICENSE', 'packages/upstream/openclaw/attempt-cancellation.ts', 'packages/upstream/openclaw/attempt-deadlines.ts', 'packages/upstream/openclaw/number-coercion.ts', 'packages/upstream/openclaw/string-coerce.ts', 'scripts/alaz_local.mjs', 'scripts/build_projected_candidate.py', 'scripts/ci_check.py', 'scripts/install_projected_candidate.py', 'scripts/run_finite_projected.py', 'scripts/run_response_preopen.py', 'scripts/run_retained_projected.py', 'scripts/run_service_projected.py', 'scripts/run_service_volume_worker.py', 'scripts/run_state_volume_worker.py', 'scripts/run_store_preopen.py', 'scripts/run_supervised_finite.py', 'scripts/run_supervised_retained.py', 'scripts/run_supervised_service.py', 'sources.lock.json')
EXPECTED_HASHES = {'LICENSE': 'f124b0474189e3cade42b6efec680e515f38908341eb909a4bad1a2012607e40', 'SECURITY.md': 'f3c6027eabba1de3b5e8ab75a192a88b522c5772ff5f390aa136f71b80ab68d8', 'config/admission-consumer-b129d6-sources.json': 'd0a1067de53e224c43f44c04b039fe12491f10a62a843719519174a2cf8d7e35', 'config/borrowed-service-r159a1-host-lock.json': 'e5eb2a3a881843d036336a7bb6d2473a9fbe3d21a7938ffe2e669869d45bd0ff', 'config/borrowed-service-r159a1-sources.json': '05dee55dede392d10af65fc123969b8f317cf417d1af669b655d2115a2757bd2', 'config/canonical-api-consumer-i133p1-sources.json': 'f650c067e1d4a7d303c48e9be10e75273fee4d8d48dda721af320fe3ac80ae27', 'config/components.lock.json': '6bc6caf69c3a9f9f7618a2d787ff493a5e8e58039196224423e05ae0383fd646', 'config/execution-gate/source-lock.json': '4a43e5fcd6effc5bc4525a6cf13c1d1d50ca26d05c64f4f3c8b4e7a68351069e', 'config/finite-close-f135c6-sources.json': '30095cdda6fadecaf332b5a5dbf8c2f3e43ad550d8dfd08adfe5469f26a324f4', 'config/hermes-borrowed-service-r159a1.json': 'a160fb456573bcf4b9efca53a62a42e6d5b9347378bec195d9df7e6ec125e7b3', 'config/hermes-finite-close-f135c6.json': 'bf4e3bed99780e14061bc106a469c9fbafef00c22d4be748aeb43bc5ad175113', 'config/linux-prepared-dependencies-l125p1.json': '3bedcdf288ac788c17bf86713907edee0eeb9bce0ba91eb93e596126d1629201', 'config/prepared-consumer-s124b1-sources.json': '6dc037dfecb6365db67c57c8e8ef96e0c152b5b8e8aa0f96ef9b2f6e525bc215', 'config/retained-profile-r140c6-sources.json': '0af0852042217675b8398e2f64c7e509935726b992d91b4bdf4080512b35f8e4', 'docs/THIRD-PARTY.md': 'd12d3b7aa0da6d6c0baa06020cdfe9b22a54aaf0974dd596328cff4db570588c', 'packages/claw-hermes/UPSTREAM.md': 'a136295274f2960032231b5c12d050ce5f424560a165dc740227659ebe9120ba', 'packages/claw-hermes/gateway_finite_protocol.py': '0e727aaf40ab22cb9c9714b26563f237cc04afdf86455d481b9f397b974cc95c', 'packages/claw-hermes/gateway_finite_runtime.py': 'e710f75ebc6900e1d16807a5d0a691f1c2f10c2f066c5d8918a6c13317e78c95', 'packages/claw-hermes/gateway_prepared_consumer.py': 'a39245d907a1d8526634d6b55168a2e8ff8d08d59ea17344822b6a6bef354d2c', 'packages/claw-hermes/gateway_retained_handoff.py': '1bc4ce046f33b88c2c0b3ca3092f6f23224297a10a6524bb940d83e6972a9ebc', 'packages/claw-hermes/gateway_retained_launch.py': '4140c06d74e9603664ababb97955cd04779bf9a0494fb1361ae8a426d23a90e2', 'packages/claw-hermes/gateway_retained_profile.py': '84400109ec08b75e33453a459fc0985b0c4da6ff37f7781e0f5f165910551fbf', 'packages/claw-hermes/gateway_retained_projection.py': '68cf4520873efc402860f4d9a9f31ee478d87e4f1b00ad7a0079aa335200ab79', 'packages/claw-hermes/gateway_service_control.py': '57f01cce0234804812eced7732917c4561c87db35db5d9903d5acc8e643cc711', 'packages/claw-hermes/gateway_service_factory.py': '3e92cae2ebdffea75b5a9a02c135f0011b4dfa513d81474db60fc4195e177559', 'packages/claw-hermes/gateway_service_handoff.py': '37ffa5bd23b77b858c7a38cc90434ecb8416ba1e95ea491f8e913b91015daf9c', 'packages/claw-hermes/gateway_service_launch.py': '8c914925e6860c8e7b7e35e247cab480e4f34d085fce57b5eb276aa0ea9c289c', 'packages/claw-hermes/gateway_service_profile.py': 'a6e4f1f5572006f72658902a6927a71faaa7d837d41a0dfa67e473622b05d05b', 'packages/claw-hermes/gateway_service_projection.py': 'dc4ad0577625b2cb9197278ae76ad29289c5c0e1f695991f3485c42b25c5b57a', 'packages/claw-hermes/gateway_service_runtime.py': '109bc6eef0a8507f9149e83785e9b51f270b4689e45dd96830cf57aae2195fea', 'packages/claw-hermes/gateway_service_sources.py': 'c46cfb1e093d56071c09390cb090021d356954c83cf6ba5efc55b7da5b8968e7', 'packages/claw-hermes/gateway_state_projection.py': '1704cd025ce82779fabbeb6b39dc5ad501e06b0c3ef3b2dc645c09e2d95ccdba', 'packages/claw-hermes/gateway_store_startup.py': 'df19918eaa16e6ed9c1cb679971810ba7d60089b8d6bebb91460323ac6290314', 'packages/claw-hermes/gateway_supervised_launch.py': '94073b8bb3f1d47220d0b9c684e287c3f27d2bd8f50a5656620516d12229c364', 'packages/claw-hermes/gateway_supervised_service.py': 'ed8f37b30e893980cf82dc594b22478893f74b079196ef7f28593c066f5c49f0', 'packages/claw-hermes/hermes-runs.mjs': '54903fc7c9596498d7b6b8a829aa2f8e9c1be9ca9bdb882214dafcaa781b93e8', 'packages/claw-hermes/host-gate-client.mjs': 'd319a405e9469dea9e9a5023a004adb0fdd29c65b27a8d8582a0f2f0b7023a51', 'packages/claw-hermes/local-control.mjs': 'a5d9016be5f8e208a3f467d1ed4d26d67b966f8c7ee59d8dc9d8b86f871060b7', 'packages/claw-hermes/package.json': 'c68b7ffc274b9217ed60907218adc56ca0d9378175340621c6ce81d1ad0d0328', 'packages/claw-hermes/run-recovery.mjs': '21793d7583cc2c56e955e85667561f83edfefd72fc219d81cd8469d35f97e748', 'packages/claw-hermes/service-control.mjs': '6cba0cdac5de88990a861d811be6b81c66838784da9d260f32dfb243e45198a3', 'packages/claw-hermes/service-task.mjs': '20dd9f2fe07ba8b229abc13f891455c17fa5d914a561048a9f1013cfb0c72746', 'packages/claw-hermes/service_control_server.py': '6cabc38272be706c5c11f9993b6a55b7683e733611d9049a0c133696f87c62f9', 'packages/claw-hermes/service_task_http.py': '877cdf4c1abb0cb928b050059f8534175708dd78d6ad16defdc7bf5a5bdd96fb', 'packages/claw-hermes/service_task_protocol.py': '6fcdd9654238e4eddac5d61e36c515bcec6185bc717718bc17487f0c02d38a0a', 'packages/claw-hermes/service_task_server.py': '7c7daece0697effc9be3a205f5b10a3796c150322f12ce59ec6b648ee91c1f60', 'packages/claw-hermes/service_volume_supervisor.py': 'f7487d23a3d34aa3eea1aa6a24c64924685a4f1c9f3672ef58276ea68e4eb1ec', 'packages/claw-hermes/state_image_lease.py': 'f57fbf1f24ea6953dd66726c6dcedb7566d66e3e12083881e78f7025c1490ddc', 'packages/claw-hermes/state_volume_supervisor.py': '5088f1b0a27eb1bed83c635a3b356bd2281d3150aad1af57f1f714530a12c080', 'packages/claw-hermes/supervised_pipe_capture.py': 'b3fe4c30607469ca05d95b7f329970c5093a429c2f952280371ddf4c085a1695', 'packages/claw-hermes/supervised_service_channel.py': '8ddc00e32294614f5d39df3b9c9cf515584fd660057f3ee45b727d89ecb2ce72', 'packages/upstream/hermes/LICENSE': '821556e6336796450ab852d375117b48a4887e71d255794fd6318d99982a5ab6', 'packages/upstream/hermes/hermes_state_keys.py': '00311a21ba6fd6388bfc9cbd1d507bef20b85e65ee35287a6c24a0dddfaa97a8', 'packages/upstream/hermes/terminal_status.py': '9290a3d8ebba3dd9e10788323e712300b5c5aa7b78e1821bd9e84b4513831371', 'packages/upstream/openclaw/LICENSE': '9efd316ecf1c4c60f6fd5d26433142fff2b6794d7d328e9bc6179b29bf9c82a4', 'packages/upstream/openclaw/attempt-cancellation.ts': '8bb3ec23f95054d55a18f5d3d5f124aa2f0e57e6168b976f8c5b73bec5f8e634', 'packages/upstream/openclaw/attempt-deadlines.ts': 'cdfe9b26f74cd5e0b88e6b29850faac6f2472ca708defbda7419af0aa82bb7e4', 'packages/upstream/openclaw/number-coercion.ts': '59296d074f0f4c81068c124f0499be87b5f6ed9fc542d5a62a7a864d859549a7', 'packages/upstream/openclaw/string-coerce.ts': '9d0648121488d3cbbb47716c4b3048faa4c94f607bfaafe7ed6617562d4fc3c3', 'scripts/alaz_local.mjs': 'd37441853cf31d8fe482bc7f6f2f1d5659ebf4a03de62d6f5e0952a183b56523', 'scripts/build_projected_candidate.py': '7b26916aec3c806ef2debf77e9e9c728ec473d8c8d2689bbbdcfc4cd7223a64b', 'scripts/build_service_candidate.py': '54c83be327e3e9e08e0a149b096f5a4f873364461069711a4c2d3f20e862f6cf', 'scripts/ci_check.py': 'b55871b560f4f30d30fb22869ac63a3b47aaa5928d4aae9dee499c88c9fa94c8', 'scripts/install_projected_candidate.py': 'f261fd22c641a1ffdd6fb9694fec0c7d3cb0c8dba788cb7549c142fd1e4dcef6', 'scripts/install_service_candidate.py': 'bc014b7e4f9ac2a0c6d170e80501eee5e458d526a2b21c4f076bfa4f590de30a', 'scripts/run_finite_projected.py': '97c905dae7e9391ad01103a011cc5216b23ced95ef2d2bffdf1e809512ff95eb', 'scripts/run_response_preopen.py': 'e166d3d1cc05e664ef541ffd70dfd2cdb5b5145046b523325b38bf4e22bcd38e', 'scripts/run_retained_projected.py': '7aa5398ca3b962ef2960de23f32d126b653842cb741be351c329d4cad28b6298', 'scripts/run_service_projected.py': 'b55c8a8d40aec5ccd5829c619bb8ab32afd26e87d8d398604d2dbacd3f413828', 'scripts/run_service_volume_worker.py': '71435f9fc1a04d3213976a93a3623a54a8aca69f1194c8470c62fc28669c4586', 'scripts/run_state_volume_worker.py': '835593ff0e5bffc3a421761e443777cc563f198ff5aaea3a29986746f7f7b97f', 'scripts/run_store_preopen.py': 'c018918593e211071bd51cb83a5b978e0873904db3ce987f9dc574b4e626e844', 'scripts/run_supervised_finite.py': 'e45cb067233e6e55ee191628d447e48628f2207462c33c9822f88150ea33f865', 'scripts/run_supervised_retained.py': '208a9f42201e7fe8ff57469d56d604baa0a19a685dccffea871ade43807fed74', 'scripts/run_supervised_service.py': '461e9ad2c1808714a688e2a391f8e0b5605f658f376cc8913b396e354e5d1629', 'scripts/verify_service_candidate.py': 'ddd8fb60dc030c36c0aefcf2790c788d012dc13e39e37f1a14f5bcd0725e3288', 'sources.lock.json': 'a4a66c6ad75cfd9d53635f7e436564b8c72c42a8d98592312057184d41bb95ff', 'tests/test_projected_candidate.py': 'fba6f2d87f29fcb774319da62bb5198cac11f411bde574d2833f08002337af19', 'tests/test_projected_install.py': '8587e0a36d79d6b4b4dfcd3969088178b4721da71578c6d3350b9b9c0fd8ae4a', 'tests/test_service_candidate.py': '01eecade206c607aae3aa2075b91872dfb708aeb1436f69ef7b8d35fb772e54b', 'tests/test_service_install.py': '1da78e2b6e26b30b93e73af3a93722578d9161b0f90e40a5013e3c3d2d39c71f'}
LINUX_ONLY_RULES = (
    ('test_projected_install.OwnedFilesystemTests.',
     'descriptor and atomic-publication fixtures require Linux', 20),
    ('test_service_install.BoundedProbeTests.',
     'owned bounded process probes require Linux', 6),
    ('test_service_install.RuntimeReadbackTests.',
     'held-descriptor runtime fixtures require Linux', 8),
    ('test_service_install.ServicePayloadTests.test_all_service_and_dependency_bytes_materialize_without_execution_or_receipt',
     'owned descriptor materialization requires Linux', 1),
)
EXPECTED_COUNT = 123


def require(value, message):
    if not value:
        raise RuntimeError(message)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def hashes(names):
    result = {}
    for name in names:
        path = ROOT / name
        require(path.is_file() and not path.is_symlink(), 'missing_or_linked_input:' + name)
        result[name] = digest(path.read_bytes())
    return result


def groups():
    return {'sourceHashes': hashes(SOURCE_FILES), 'testFileHashes': hashes(TEST_FILES),
            'supportHashes': hashes(SUPPORT_FILES)}


def flatten_ids(suite):
    for test in suite:
        if isinstance(test, unittest.TestSuite):
            yield from flatten_ids(test)
        else:
            yield test.id()


class RecordedResult(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.executed_ids = []

    def startTest(self, test):
        self.executed_ids.append(test.id())
        super().startTest(test)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--label', required=True)
    args = parser.parse_args()
    require(re.fullmatch(r'(?:linux|windows)(?:-[0-9]{2})?', args.label) is not None,
            'invalid_focused_label')
    operating_system = platform.system()
    wanted_platform = 'Linux' if args.label.startswith('linux') else 'Windows'
    require(operating_system == wanted_platform, 'label_platform_mismatch')
    require(Path(__file__).resolve() == ROOT / RUNNER, 'runner_location_changed')
    require(len(SUPPORT_FILES) == 74 and len(set(SOURCE_FILES + TEST_FILES + SUPPORT_FILES)) == 81
            and set(EXPECTED_HASHES) == set(SOURCE_FILES + TEST_FILES + SUPPORT_FILES),
            'focused_input_inventory')
    before = groups()
    require({name: pin for group in before.values() for name, pin in group.items()} == EXPECTED_HASHES,
            'focused_input_pin_mismatch')
    runner_raw = Path(__file__).read_bytes()
    runner_sha = digest(runner_raw)
    folder = ROOT / EVIDENCE
    log_path = folder / ('focused-' + args.label + '.log')
    evidence_path = folder / ('focused-' + args.label + '.json')
    require(not log_path.exists() and not evidence_path.exists(),
            'focused_output_exists_inspect_without_replay')

    sys.path.insert(0, str(ROOT / 'scripts'))
    sys.path.insert(0, str(ROOT / 'tests'))
    loader = unittest.TestLoader()
    suite = unittest.TestSuite(loader.loadTestsFromName(name) for name in MODULES)
    selected = list(flatten_ids(suite))
    require(len(selected) == EXPECTED_COUNT and selected == sorted(set(selected))
            and not loader.errors, 'focused_selection_mismatch')
    skip_reasons = {}
    for prefix, reason, count in LINUX_ONLY_RULES:
        matched = [name for name in selected if name.startswith(prefix)]
        require(len(matched) == count, 'declared_linux_only_selection_changed:' + prefix)
        require(not set(matched).intersection(skip_reasons), 'overlapping_skip_rules')
        skip_reasons.update({name: reason for name in matched})
    require(len(skip_reasons) == 35, 'declared_platform_skip_count')

    started = time.perf_counter()
    with log_path.open('x', encoding='utf-8', newline='\n') as stream:
        with redirect_stdout(stream), redirect_stderr(stream):
            result = unittest.TextTestRunner(stream=stream, verbosity=2,
                resultclass=RecordedResult).run(suite)
        stream.flush()
        os.fsync(stream.fileno())
    elapsed = round(time.perf_counter() - started, 6)
    after = groups()
    unchanged = after == before and Path(__file__).read_bytes() == runner_raw
    skipped = [{'id': test.id(), 'reason': reason} for test, reason in result.skipped]
    expected_skips = [] if operating_system == 'Linux' else [
        {'id': name, 'reason': skip_reasons[name]} for name in selected if name in skip_reasons]
    log_raw = log_path.read_bytes()
    import ci_check
    credential_detectors = ci_check.credential_hits(log_raw)
    absolute_private_paths = bool(re.search(rb'(?:/workspace/|/home/|[A-Za-z]:\\Users\\)', log_raw))
    scan_clean = not credential_detectors and not absolute_private_paths
    problems = []
    if not result.wasSuccessful(): problems.append('unittest_unsuccessful')
    if result.testsRun != EXPECTED_COUNT or result.executed_ids != selected:
        problems.append('executed_selection_mismatch')
    if skipped != expected_skips: problems.append('unexpected_skip_set')
    if result.expectedFailures or result.unexpectedSuccesses:
        problems.append('unexpected_expected_failure_or_success')
    if not unchanged: problems.append('source_or_runner_changed')
    if not scan_clean: problems.append('full_log_requires_private_review_before_publication')
    accepted = not problems
    record = {
        'schema': 1, 'atUtc': datetime.now(timezone.utc).isoformat(),
        'kind': 'R167_SERVICE_INSTALLATION_FOCUSED_FIXTURES',
        'result': 'PASS' if accepted else 'FAIL', 'label': args.label,
        'platform': operating_system,
        'pythonImplementation': platform.python_implementation(),
        'pythonVersion': platform.python_version(),
        'command': ['python', '-B', RUNNER, '--label', args.label],
        'selectedTests': EXPECTED_COUNT, 'selectedTestIds': selected,
        'selectedTestIdsSha256': digest(('\n'.join(selected) + '\n').encode('utf-8')),
        'executedTestIds': result.executed_ids,
        'testsRun': result.testsRun,
        'passed': max(0, result.testsRun - len(result.failures) - len(result.errors)
                      - len(result.skipped) - len(result.expectedFailures)
                      - len(result.unexpectedSuccesses)),
        'skipped': len(result.skipped), 'skippedTests': skipped,
        'failures': len(result.failures), 'failureTestIds': [test.id() for test, _ in result.failures],
        'errors': len(result.errors), 'errorTestIds': [test.id() for test, _ in result.errors],
        'expectedFailures': len(result.expectedFailures),
        'unexpectedSuccesses': len(result.unexpectedSuccesses),
        'exitCode': 0 if accepted else 1, 'seconds': elapsed,
        **before, 'hashesAfterTest': after, 'sourceBytesUnchanged': unchanged,
        'runnerSha256': runner_sha, 'logPath': log_path.relative_to(ROOT).as_posix(),
        'logSha256': digest(log_raw), 'logBytes': len(log_raw), 'fullLogCaptured': True,
        'boundedLogScan': {'credentialDetectors': credential_detectors,
            'absolutePrivatePathDetected': absolute_private_paths, 'passed': scan_clean},
        'gateProblems': problems,
        'scope': 'Owned Git/byte/filesystem fixtures, runtime reader doubles and owned bounded subprocesses; no privileged installation or installed service acceptance',
        'ownedSyntheticFilesystemMaterializationTested': operating_system == 'Linux',
        'ownedSubprocessCaptureTested': operating_system == 'Linux',
        'runtimeIdentityTestsUseDeclaredReaderDoubles': True,
        'installed': False, 'runtimeTested': False, 'nativeServiceStarted': False,
        'kernelAcceptance': False, 'realModelCalls': 0, 'realProviderCalls': 0,
        'windowsFileCliAccepted': False,
        'evidenceLimit': 'The unchanged94-test R166 selection and29 new installer tests are counted once. Windows has35 declared Linux-only skips. Candidate/dependency/synthetic ELF fixture bytes are not executed. Owned subprocess tests run the current Python with fixed snippets only. Runtime identity tests use declared filesystem reader/capture doubles. This is not full CI, privileged installation, actual selected-runtime qualification, kernel, service or model acceptance.',
    }
    raw = (json.dumps(record, indent=2, sort_keys=True, allow_nan=False) + '\n').encode('utf-8')
    with evidence_path.open('xb') as stream:
        require(stream.write(raw) == len(raw), 'focused_evidence_short_write')
        stream.flush()
        os.fsync(stream.fileno())
    summary = {key: record[key] for key in ('result', 'platform', 'testsRun', 'passed', 'skipped',
        'failures', 'errors', 'expectedFailures', 'unexpectedSuccesses', 'exitCode', 'seconds',
        'selectedTestIdsSha256', 'runnerSha256', 'logSha256', 'sourceBytesUnchanged')}
    summary.update({'evidencePath': evidence_path.relative_to(ROOT).as_posix(),
                    'evidenceSha256': digest(raw), 'gateProblems': problems})
    print(json.dumps(summary, sort_keys=True), flush=True)
    return record['exitCode']


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(json.dumps({'result': 'REFUSED', 'reason': str(exc),
                          'scope': 'focused evidence collection only'}), file=sys.stderr)
        raise SystemExit(2)
