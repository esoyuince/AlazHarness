"""Reproducible R163 supervisor/Unix source integration gate, not installed service acceptance.

Use a fresh --label for each attempt; no existing evidence is overwritten.
The focused set exercises the new assembly and its direct legacy dependencies.
"""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import hashlib
import json
import os
import platform
import sys
import time
import unittest

if not __debug__:
    raise RuntimeError('optimized verification is forbidden')
ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'tests'), str(ROOT / 'packages/claw-hermes')]
NAMES = ['test_service_supervisor_r163a1', 'test_service_control_server_r163a1', 'test_service_control_cli_r163a1', 'test_service_supervisor_history_r163a1', 'test_service_launch_r162a1', 'test_service_factory_r162a1', 'test_service_ready_config_r162a1', 'test_service_receiver_history_r162a1', 'test_projected_launch_l145a8', 'test_finite_projected_launch', 'test_service_child_control_r160a1', 'test_borrowed_service_host_r159a1.ServiceClosureTests', 'test_historical_borrowed_service_r159a1', 'test_service_profile_r161a1', 'test_service_profile_binding_r161a1', 'test_service_projection_r161a1', 'test_service_handoff_r161a1', 'test_service_profile_history_r161a1', 'test_gateway_store_startup', 'test_three_store_lifecycle_l113f6', 'test_startup_consumer_owner_s124b1', 'test_prepared_work_guard_c127a6', 'test_execution_profile_qa3156', 'test_borrowed_service_host_r159a1.SourceSelectionTests', 'test_borrowed_service_host_r159a1.ServiceConsumerSelection', 'test_borrowed_service_host_r159a1.ServiceStartupGuards', 'test_gateway_state_projection', 'test_retained_projection_p142c6.MappingContract', 'test_retained_projection_p142c6.ProjectionSequence', 'test_retained_projection_p142c6.PivotBarrier', 'test_retained_projection_p142c6.OriginalStartupHandoff', 'test_retained_handoff_t143a7', 'test_self_identity_history_r150a1.SelfIdentityHistory.test_current_product_is_checked_live_not_old_kernel_snapshot', 'test_self_identity_history_r150a1.SelfIdentityHistory.test_tampered_current_launcher_cannot_be_hidden_by_applied_archive', 'test_self_identity_history_r150a1.SelfIdentityHistory.test_tampered_applied_launcher_cannot_be_hidden_by_current_source', 'test_self_identity_history_r150a1.SelfIdentityHistory.test_tampered_current_projection_cannot_be_hidden_by_parent_archive', 'test_self_identity_history_r150a1.SelfIdentityHistory.test_tampered_applied_projection_cannot_be_hidden_by_current_source', 'test_self_identity_history_r150a1.SelfIdentityHistory.test_unknown_paths_or_generations_are_not_redirected', 'test_self_identity_history_r150a1.SelfIdentityHistory.test_tampered_archive_is_never_accepted', 'test_self_identity_history_r150a1.SelfIdentityHistory.test_manifest_cannot_point_to_another_file', 'test_service_volume_r160a1', 'test_supervised_service_channel_r160a1', 'test_service_control_r160a1', 'test_supervised_retained_launch', 'test_supervised_finite_launch', 'test_supervised_pipe_capture', 'test_state_volume_supervisor']
SOURCES = ['packages/claw-hermes/execution_boundary.py', 'packages/claw-hermes/gateway_prepared_consumer.py', 'packages/claw-hermes/gateway_profile_lease.py', 'packages/claw-hermes/gateway_service_control.py', 'packages/claw-hermes/gateway_service_factory.py', 'packages/claw-hermes/gateway_service_handoff.py', 'packages/claw-hermes/gateway_service_launch.py', 'packages/claw-hermes/gateway_service_profile.py', 'packages/claw-hermes/gateway_service_projection.py', 'packages/claw-hermes/gateway_service_runtime.py', 'packages/claw-hermes/gateway_state_projection.py', 'packages/claw-hermes/gateway_store_startup.py', 'packages/claw-hermes/gateway_supervised_launch.py', 'packages/claw-hermes/gateway_supervised_service.py', 'packages/claw-hermes/host_gate.py', 'packages/claw-hermes/service-control.mjs', 'packages/claw-hermes/service_control_server.py', 'packages/claw-hermes/service_volume_supervisor.py', 'packages/claw-hermes/state_image_lease.py', 'packages/claw-hermes/state_volume_supervisor.py', 'packages/claw-hermes/supervised_service_channel.py', 'scripts/alaz_local.mjs', 'scripts/run_service_projected.py', 'scripts/run_service_volume_worker.py', 'scripts/run_supervised_service.py']
TEST_FILES = ['tests/fixtures/service-control-server-r163a1.py', 'tests/historical_service_receiver_r162a1.py', 'tests/historical_service_supervisor_r163a1.py', 'tests/node/service-control-r160a1.mjs', 'tests/node/service-control-r163a1.mjs', 'tests/service_factory_fixtures_r162a1.py', 'tests/service_profile_fixtures_r161a1.py', 'tests/service_supervisor_fixtures_r163a1.py', 'tests/test_borrowed_service_host_r159a1.py', 'tests/test_execution_profile_qa3156.py', 'tests/test_finite_projected_launch.py', 'tests/test_gateway_state_projection.py', 'tests/test_gateway_store_startup.py', 'tests/test_historical_borrowed_service_r159a1.py', 'tests/test_prepared_work_guard_c127a6.py', 'tests/test_projected_launch_l145a8.py', 'tests/test_retained_handoff_t143a7.py', 'tests/test_retained_projection_p142c6.py', 'tests/test_self_identity_history_r150a1.py', 'tests/test_service_child_control_r160a1.py', 'tests/test_service_control_cli_r163a1.py', 'tests/test_service_control_r160a1.py', 'tests/test_service_control_server_r163a1.py', 'tests/test_service_factory_r162a1.py', 'tests/test_service_handoff_r161a1.py', 'tests/test_service_launch_r162a1.py', 'tests/test_service_profile_binding_r161a1.py', 'tests/test_service_profile_history_r161a1.py', 'tests/test_service_profile_r161a1.py', 'tests/test_service_projection_r161a1.py', 'tests/test_service_ready_config_r162a1.py', 'tests/test_service_receiver_history_r162a1.py', 'tests/test_service_supervisor_history_r163a1.py', 'tests/test_service_supervisor_r163a1.py', 'tests/test_service_volume_r160a1.py', 'tests/test_startup_consumer_owner_s124b1.py', 'tests/test_state_volume_supervisor.py', 'tests/test_supervised_finite_launch.py', 'tests/test_supervised_pipe_capture.py', 'tests/test_supervised_retained_launch.py', 'tests/test_supervised_service_channel_r160a1.py', 'tests/test_three_store_lifecycle_l113f6.py']


def cases(suite):
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from cases(item)
        else:
            yield item


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--label', required=True)
    args = parser.parse_args()
    assert 0 < len(args.label) <= 64 and all(c.isascii() and (c.isalnum() or c == '-') for c in args.label)
    os.chdir(ROOT)
    folder = Path(__file__).resolve().parent
    log = folder / ('focused-' + args.label + '.log')
    report = folder / ('focused-' + args.label + '.json')
    assert not log.exists() and not report.exists(), 'evidence already exists'
    before = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in SOURCES}
    test_before = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in TEST_FILES}
    runner_before = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    suite = unittest.defaultTestLoader.loadTestsFromNames(NAMES)
    ids = [test.id() for test in cases(suite)]
    selected = len(ids)
    assert selected > 0 and selected == len(set(ids)), 'missing or duplicate selected tests'
    started = time.perf_counter()
    with log.open('x', encoding='utf-8') as stream:
        result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    duration = time.perf_counter() - started
    after = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in SOURCES}
    test_after = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in TEST_FILES}
    runner_after = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    unchanged = before == after
    tests_unchanged = test_before == test_after and runner_before == runner_after
    successful = (result.wasSuccessful() and unchanged and tests_unchanged and result.testsRun == selected
                  and not result.expectedFailures and not result.unexpectedSuccesses)
    data = {'schema': 1, 'atUtc': datetime.now(timezone.utc).isoformat(),
        'scope': 'supervisor/Unix/CLI and direct dependency source/fixture contracts; real fixture sockets and pipes, not installed/native/kernel/model acceptance',
        'result': 'PASS' if successful else 'FAIL', 'exitCode': 0 if successful else 1,
        'platform': platform.platform(), 'python': sys.version, 'label': args.label,
        'testSelectors': NAMES, 'selectedTests': selected, 'testsRun': result.testsRun,
        'uniqueTestIds': selected, 'selectedTestIdsSha256': hashlib.sha256(('\n'.join(ids)+'\n').encode()).hexdigest(),
        'passed': result.testsRun-len(result.skipped)-len(result.failures)-len(result.errors)-len(result.expectedFailures),
        'failures': len(result.failures), 'errors': len(result.errors),
        'expectedFailures': len(result.expectedFailures), 'unexpectedSuccesses': len(result.unexpectedSuccesses),
        'skipped': len(result.skipped), 'skippedTests': [(t.id(), why) for t, why in result.skipped],
        'seconds': round(duration, 6), 'sourceHashes': before,
        'sourceHashesUnchangedAfterTest': unchanged,
        'testHashes': test_before, 'testHashesUnchangedAfterTest': tests_unchanged,
        'runnerSha256': runner_before,
        'logFile': log.name, 'logBytes': log.stat().st_size,
        'logSha256': hashlib.sha256(log.read_bytes()).hexdigest(),
        'realModelCalls': 0, 'realProviderCalls': 0,
        'nativeServiceStarted': False, 'kernelConfinementTested': False}
    with report.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(data, stream, indent=2, sort_keys=True)
        stream.write('\n')
    print(json.dumps({k: v for k, v in data.items() if k not in ('testSelectors', 'sourceHashes', 'testHashes')}, ensure_ascii=False))
    if not successful:
        print(log.read_text(encoding='utf-8')[-16000:])
    return data['exitCode']


if __name__ == '__main__':
    sys.exit(main())
