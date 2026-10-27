"""R165 task transport and direct service/client source/fixture verification.

Use a fresh --label for every attempt. Existing evidence is never overwritten.
Selection is explicit for legacy behavior and sorted for all new R165 wrappers;
missing required files, loader errors, duplicate IDs or input drift fail the run.
This runner does not attest an installed service, native runtime, kernel or model.
"""
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timezone
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import os
import platform
import sys
import time
import traceback
import unittest

if not __debug__:
    raise RuntimeError('optimized verification is forbidden')

ROOT = Path(__file__).resolve().parents[2]
RUNNER = Path(__file__).resolve()
sys.dont_write_bytecode = True
sys.path[:0] = [str(ROOT / 'tests'), str(ROOT / 'packages/claw-hermes')]

# Whole unrelated profile/history packages are not part of this focused gate.
# Hashing an imported fixture module below does not select all of its tests.
LEGACY_SELECTORS = (
    'test_service_child_control_r160a1',
    'test_supervised_service_channel_r160a1',
    'test_service_control_r160a1',
    'test_service_volume_r160a1',
    'test_service_supervisor_r163a1',
    'test_service_control_server_r163a1',
    'test_service_control_cli_r163a1',
    'test_service_closure_r164a1',
    'test_service_control_server_r164a1',
    'test_service_control_cli_r164a1',
    'test_service_supervisor_history_r163a1',
    'test_service_closure_history_r164a1',
    'test_historical_local_control_r158a1',
    'test_historical_borrowed_service_r159a1',
    'test_local_control',
    'test_host_gate_client',
    'test_host_client_qa',
    'test_hybrid_wire',
    'test_borrowed_service_host_r159a1.BorrowedHostRoutes',
    'test_borrowed_service_host_r159a1.ServiceClosureTests',
    'test_borrowed_service_host_r159a1.ServiceStartupGuards',
)
REQUIRED_R165_MODULES = (
    'test_service_task_channel_r165a1',
    'test_service_task_child_r165a1',
    'test_service_task_client_r165a1',
    'test_service_task_integration_r165a1',
    'test_service_task_protocol_r165a1',
    'test_service_task_server_r165a1',
    'test_service_task_supervisor_r165a1',
)
REQUIRED_R165_SUPPORT = (
    'tests/fixtures/service-task-child-r165a1.py',
    'tests/fixtures/service-task-server-r165a1.py',
    'tests/node/service-task-integration-r165a1.mjs',
    'tests/node/service-task-r165a1.mjs',
)

# Changed task/service/client inputs and the selected fixtures' existing local
# import dependencies. Every named path is required, including in partial exports.
SOURCE_FILES = (
    'config/borrowed-service-r159a1-host-lock.json',
    'config/borrowed-service-r159a1-sources.json',
    'config/hermes-borrowed-service-r159a1.json',
    'packages/claw-hermes/broker_budget.py',
    'packages/claw-hermes/combined_guard.py',
    'packages/claw-hermes/credential_guard.py',
    'packages/claw-hermes/dream.py',
    'packages/claw-hermes/dream_eval.py',
    'packages/claw-hermes/dream_review.py',
    'packages/claw-hermes/dream_trial.py',
    'packages/claw-hermes/evidence_view.py',
    'packages/claw-hermes/execution_boundary.py',
    'packages/claw-hermes/execution_budget.py',
    'packages/claw-hermes/gateway_constructor_metadata.py',
    'packages/claw-hermes/gateway_consumer_admission.py',
    'packages/claw-hermes/gateway_consumer_api.py',
    'packages/claw-hermes/gateway_finite_protocol.py',
    'packages/claw-hermes/gateway_finite_runtime.py',
    'packages/claw-hermes/gateway_http_readiness.py',
    'packages/claw-hermes/gateway_live_store_gate.py',
    'packages/claw-hermes/gateway_native_layout.py',
    'packages/claw-hermes/gateway_prepared_consumer.py',
    'packages/claw-hermes/gateway_profile_lease.py',
    'packages/claw-hermes/gateway_projection.py',
    'packages/claw-hermes/gateway_response_live.py',
    'packages/claw-hermes/gateway_response_preopen.py',
    'packages/claw-hermes/gateway_retained_handoff.py',
    'packages/claw-hermes/gateway_retained_launch.py',
    'packages/claw-hermes/gateway_retained_profile.py',
    'packages/claw-hermes/gateway_retained_projection.py',
    'packages/claw-hermes/gateway_service_control.py',
    'packages/claw-hermes/gateway_service_factory.py',
    'packages/claw-hermes/gateway_service_handoff.py',
    'packages/claw-hermes/gateway_service_launch.py',
    'packages/claw-hermes/gateway_service_profile.py',
    'packages/claw-hermes/gateway_service_projection.py',
    'packages/claw-hermes/gateway_service_runtime.py',
    'packages/claw-hermes/gateway_service_sources.py',
    'packages/claw-hermes/gateway_state_projection.py',
    'packages/claw-hermes/gateway_storage_mounts.py',
    'packages/claw-hermes/gateway_store_preopen.py',
    'packages/claw-hermes/gateway_store_startup.py',
    'packages/claw-hermes/gateway_supervised_launch.py',
    'packages/claw-hermes/gateway_supervised_service.py',
    'packages/claw-hermes/hermes-runs.mjs',
    'packages/claw-hermes/host-gate-client.mjs',
    'packages/claw-hermes/host_gate.py',
    'packages/claw-hermes/host_gate_plugin.py',
    'packages/claw-hermes/host_principal.py',
    'packages/claw-hermes/host_report.py',
    'packages/claw-hermes/ipc_view.py',
    'packages/claw-hermes/isolated_read.py',
    'packages/claw-hermes/isolated_tool.py',
    'packages/claw-hermes/linux_netns.py',
    'packages/claw-hermes/local-control.mjs',
    'packages/claw-hermes/principal_launch.py',
    'packages/claw-hermes/provider_broker.py',
    'packages/claw-hermes/provider_egress.py',
    'packages/claw-hermes/recovery_inspector.py',
    'packages/claw-hermes/request_view.py',
    'packages/claw-hermes/resolution_receipts.py',
    'packages/claw-hermes/run-recovery.mjs',
    'packages/claw-hermes/service-control.mjs',
    'packages/claw-hermes/service-task.mjs',
    'packages/claw-hermes/service_control_server.py',
    'packages/claw-hermes/service_task_http.py',
    'packages/claw-hermes/service_task_protocol.py',
    'packages/claw-hermes/service_task_server.py',
    'packages/claw-hermes/service_volume_supervisor.py',
    'packages/claw-hermes/source_capture.py',
    'packages/claw-hermes/state_image_lease.py',
    'packages/claw-hermes/state_volume_supervisor.py',
    'packages/claw-hermes/supervised_pipe_capture.py',
    'packages/claw-hermes/supervised_service_channel.py',
    'packages/upstream/openclaw/attempt-cancellation.ts',
    'packages/upstream/openclaw/attempt-deadlines.ts',
    'packages/upstream/openclaw/number-coercion.ts',
    'packages/upstream/openclaw/string-coerce.ts',
    'scripts/alaz_local.mjs',
    'scripts/run_service_projected.py',
    'scripts/run_service_volume_worker.py',
    'scripts/run_supervised_service.py',
)
SUPPORT_FILES = (
    # Exact archive/binding/receipt inputs read by the four selected history
    # suites. Keep these required so partial exports fail before test execution.
    'evidence/p2-borrowed-service-r159a1/base-packages__claw-hermes__execution_boundary.py.txt',
    'evidence/p2-borrowed-service-r159a1/base-packages__claw-hermes__gateway_consumer_admission.py.txt',
    'evidence/p2-borrowed-service-r159a1/base-packages__claw-hermes__gateway_consumer_api.py.txt',
    'evidence/p2-borrowed-service-r159a1/base-packages__claw-hermes__gateway_prepared_consumer.py.txt',
    'evidence/p2-borrowed-service-r159a1/base-packages__claw-hermes__gateway_store_startup.py.txt',
    'evidence/p2-borrowed-service-r159a1/base-packages__claw-hermes__host_gate.py.txt',
    'evidence/p2-borrowed-service-r159a1/base-packages__claw-hermes__host_gate_plugin.py.txt',
    'evidence/p2-borrowed-service-r159a1/base-packages__claw-hermes__local-control.mjs.txt',
    'evidence/p2-borrowed-service-r159a1/base-packages__claw-hermes__run-recovery.mjs.txt',
    'evidence/p2-borrowed-service-r159a1/base-tests__test_retained_restart_receipt_r140c6.py.txt',
    'evidence/p2-borrowed-service-r159a1/historical-source-bindings.json',
    'evidence/p2-local-control-r158a1/base-packages__claw-hermes__hermes-runs.mjs.txt',
    'evidence/p2-local-control-r158a1/base-packages__claw-hermes__host-gate-client.mjs.txt',
    'evidence/p2-local-control-r158a1/base-packages__claw-hermes__host_gate.py.txt',
    'evidence/p2-local-control-r158a1/base-packages__claw-hermes__host_gate_plugin.py.txt',
    'evidence/p2-local-control-r158a1/historical-source-bindings.json',
    'evidence/p2-service-closure-r164a1/historical-source-bindings.json',
    'evidence/p2-service-closure-r164a1/parent-packages__claw-hermes__gateway_supervised_service.py.txt',
    'evidence/p2-service-closure-r164a1/parent-packages__claw-hermes__service_control_server.py.txt',
    'evidence/p2-service-closure-r164a1/parent-packages__claw-hermes__service_volume_supervisor.py.txt',
    'evidence/p2-service-closure-r164a1/parent-tests__fixtures__service-control-server-r163a1.py.txt',
    'evidence/p2-service-closure-r164a1/parent-tests__node__service-control-r163a1.mjs.txt',
    'evidence/p2-service-closure-r164a1/parent-tests__service_supervisor_fixtures_r163a1.py.txt',
    'evidence/p2-service-closure-r164a1/parent-tests__test_service_control_cli_r163a1.py.txt',
    'evidence/p2-service-closure-r164a1/parent-tests__test_service_control_server_r163a1.py.txt',
    'evidence/p2-service-closure-r164a1/parent-tests__test_service_supervisor_r163a1.py.txt',
    'evidence/p2-service-control-r160a1/focused-linux.json',
    'evidence/p2-service-control-r160a1/focused-linux.log',
    'evidence/p2-service-control-r160a1/focused-windows.json',
    'evidence/p2-service-control-r160a1/focused-windows.log',
    'evidence/p2-service-control-r160a1/initial-focused-linux.json',
    'evidence/p2-service-control-r160a1/initial-focused-linux.log',
    'evidence/p2-service-supervisor-r163a1/baseline.json',
    'evidence/p2-service-supervisor-r163a1/focused-linux.json',
    'evidence/p2-service-supervisor-r163a1/focused-linux.log',
    'evidence/p2-service-supervisor-r163a1/focused-runner.py',
    'evidence/p2-service-supervisor-r163a1/focused-windows.json',
    'evidence/p2-service-supervisor-r163a1/focused-windows.log',
    'evidence/p2-service-supervisor-r163a1/historical-source-bindings.json',
    'evidence/p2-service-supervisor-r163a1/history-focused-linux.json',
    'evidence/p2-service-supervisor-r163a1/history-focused-linux.log',
    'evidence/p2-service-supervisor-r163a1/parent-packages__claw-hermes__service_volume_supervisor.py.txt',
    'evidence/p2-service-supervisor-r163a1/review-provenance.json',
    'evidence/p2-service-supervisor-r163a1/source-check.json',
    'evidence/p2-service-supervisor-r163a1/source-ci.json',
    'tests/fixtures/hermes_wire.py',
    'tests/fixtures/service-control-server-r163a1.py',
    'tests/fixtures/service-control-server-r164a1.py',
    'tests/historical_api_i133p1.py',
    'tests/historical_borrowed_service_r159a1.py',
    'tests/historical_finite_close_f135c6.py',
    'tests/historical_local_control_r158a1.py',
    'tests/historical_projection_p142c6.py',
    'tests/historical_retained_r140c6.py',
    'tests/historical_self_identity_r150a1.py',
    'tests/historical_service_closure_r164a1.py',
    'tests/historical_service_profile_r161a1.py',
    'tests/historical_service_receiver_r162a1.py',
    'tests/historical_service_supervisor_r163a1.py',
    'tests/node/host-client-cases.mjs',
    'tests/node/host_gate_qa.mjs',
    'tests/node/local-control-cases.mjs',
    'tests/node/service-control-r160a1.mjs',
    'tests/node/service-control-r163a1.mjs',
    'tests/node/service-control-r164a1.mjs',
    'tests/node/wire-cases.mjs',
    'tests/service_closure_fixtures_r164a1.py',
    'tests/service_supervisor_fixtures_r163a1.py',
    'tests/test_api_owner_i133p1.py',
    'tests/test_execution_gate_qa.py',
    'tests/test_gateway_state_projection.py',
    'tests/test_gateway_store_startup.py',
    'tests/test_host_gate_qa.py',
    'tests/test_host_request_observation.py',
    'tests/test_retained_restart_receipt_r140c6.py',
    'tests/test_service_projection_r161a1.py',
    'tests/test_three_store_lifecycle_l113f6.py',
)


def discover_r165():
    modules = sorted(path.stem for path in (ROOT / 'tests').glob('test_*r165a1.py')
                     if path.is_file())
    support = sorted(path.relative_to(ROOT).as_posix()
                     for path in (ROOT / 'tests').rglob('*r165a1*')
                     if path.is_file() and path.suffix in ('.py', '.mjs', '.json', '.ts')
                     and path.parent != ROOT / 'tests')
    # Top-level R165 helper modules are support too, without becoming selectors.
    support += sorted(path.relative_to(ROOT).as_posix()
                      for path in (ROOT / 'tests').glob('*r165a1.py')
                      if path.is_file() and path.stem not in modules)
    return {'modules': modules, 'supportFiles': sorted(set(support))}


def input_paths(discovery):
    selected_modules = {name.split('.')[0] for name in LEGACY_SELECTORS}
    selected_modules.update(REQUIRED_R165_MODULES)
    selected_modules.update(discovery['modules'])
    tests = sorted('tests/' + name + '.py' for name in selected_modules)
    support = sorted((set(SUPPORT_FILES) | set(REQUIRED_R165_SUPPORT)
                      | set(discovery['supportFiles'])) - set(tests))
    return {'source': sorted(SOURCE_FILES), 'test': tests, 'support': support}


def hashes(paths, errors, stage):
    result = {}
    for name in paths:
        try:
            path = ROOT / name
            if path.is_symlink() or not path.is_file():
                raise ValueError('required input is missing or is not a regular file')
            result[name] = hashlib.sha256(path.read_bytes()).hexdigest()
        except (OSError, ValueError) as exc:
            result[name] = None
            errors.append({'stage': stage, 'path': name, 'error': str(exc)})
    return result


def cases(suite):
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from cases(item)
        else:
            yield item


def ids_sha256(ids):
    return hashlib.sha256(('\n'.join(ids) + '\n').encode('utf-8')).hexdigest()


class EvidenceResult(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.started_test_ids = []
        self.successful_test_ids = []

    def startTest(self, test):
        self.started_test_ids.append(test.id())
        super().startTest(test)

    def addSuccess(self, test):
        self.successful_test_ids.append(test.id())
        super().addSuccess(test)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--label', required=True)
    args = parser.parse_args()
    if not (0 < len(args.label) <= 64 and all(
            char.isascii() and (char.isalnum() or char == '-') for char in args.label)):
        parser.error('--label must be 1..64 ASCII letters, digits or hyphens')
    os.chdir(ROOT)
    log = RUNNER.parent / ('focused-' + args.label + '.log')
    report = RUNNER.parent / ('focused-' + args.label + '.json')
    if log.exists() or report.exists():
        parser.error('evidence label already exists; use a fresh --label')

    started_at = datetime.now(timezone.utc).isoformat()
    input_errors, runner_errors = [], []
    ids, selectors, selector_counts = [], [], []
    before, after = {}, {}
    discovery_before = discovery_after = None
    runner_before = runner_after = None
    result = None
    seconds = 0.0
    stage = 'input-snapshot'
    runner_name = RUNNER.relative_to(ROOT).as_posix()

    # Both reservations use exclusive creation; a reused label never runs tests.
    with log.open('x', encoding='utf-8', newline='\n') as stream, \
            report.open('x', encoding='utf-8', newline='\n') as report_stream:
        with redirect_stdout(stream), redirect_stderr(stream):
            try:
                # The explicit Linux source/HTTP gate must execute its real
                # HTTP cases. Standard no-install discovery records dependency
                # skips separately, but cannot stand in for this local gate.
                if sys.platform == 'linux' and importlib.util.find_spec('aiohttp') is None:
                    raise RuntimeError('R165 Linux focused gate requires prepared aiohttp')
                discovery_before = discover_r165()
                paths_before = input_paths(discovery_before)
                before = {kind: hashes(paths, input_errors, 'before-' + kind)
                          for kind, paths in paths_before.items()}
                runner_before = hashes([runner_name], input_errors, 'before-runner')[runner_name]
                missing_modules = sorted(set(REQUIRED_R165_MODULES)
                                         - set(discovery_before['modules']))
                if input_errors or missing_modules:
                    print(json.dumps({'inputErrors': input_errors,
                                      'missingRequiredModules': missing_modules}, indent=2))
                    raise RuntimeError('required source/test/support input is unavailable')

                stage = 'selection'
                selectors = discovery_before['modules'] + list(LEGACY_SELECTORS)
                loader = unittest.TestLoader()
                suite = unittest.TestSuite()
                for name in selectors:
                    selected_suite = loader.loadTestsFromName(name)
                    selected_ids = [test.id() for test in cases(selected_suite)]
                    selector_counts.append({'selector': name, 'tests': len(selected_ids)})
                    ids.extend(selected_ids)
                    suite.addTests(selected_suite)
                if loader.errors:
                    print('\n'.join(loader.errors))
                    raise RuntimeError('test selection contains loader errors')
                if not ids or any(row['tests'] == 0 for row in selector_counts):
                    raise RuntimeError('one or more required selectors collected no tests')
                if len(ids) != len(set(ids)):
                    seen, duplicates = set(), set()
                    for test_id in ids:
                        if test_id in seen:
                            duplicates.add(test_id)
                        seen.add(test_id)
                    print('Duplicate selected IDs: ' + json.dumps(sorted(duplicates)))
                    raise RuntimeError('selected test IDs are not unique')

                stage = 'tests'
                started = time.perf_counter()

                def make_result(*args, **kwargs):
                    nonlocal result
                    result = EvidenceResult(*args, **kwargs)
                    return result

                try:
                    # Keep the result object if a test raises KeyboardInterrupt.
                    result = unittest.TextTestRunner(stream=stream, verbosity=2,
                        resultclass=make_result).run(suite)
                finally:
                    seconds = time.perf_counter() - started
                stage = 'completed'
            except BaseException as exc:
                runner_errors.append({'stage': stage, 'type': type(exc).__name__,
                                      'error': str(exc)})
                traceback.print_exc(file=stream)
            finally:
                try:
                    discovery_after = discover_r165()
                    paths_after = input_paths(discovery_after)
                    after = {kind: hashes(paths, input_errors, 'after-' + kind)
                             for kind, paths in paths_after.items()}
                    runner_after = hashes([runner_name], input_errors, 'after-runner')[runner_name]
                except BaseException as exc:
                    runner_errors.append({'stage': 'after-snapshot',
                                          'type': type(exc).__name__, 'error': str(exc)})
                    traceback.print_exc(file=stream)
            stream.flush()

        unchanged = {kind: bool(before.get(kind)) and before.get(kind) == after.get(kind)
                     for kind in ('source', 'test', 'support')}
        discovery_unchanged = discovery_before is not None and discovery_before == discovery_after
        runner_unchanged = runner_before is not None and runner_before == runner_after
        executed_ids = [] if result is None else result.started_test_ids
        successful = (result is not None and result.wasSuccessful()
                      and not result.expectedFailures and not result.unexpectedSuccesses
                      and not input_errors and not runner_errors
                      and all(unchanged.values()) and discovery_unchanged and runner_unchanged
                      and bool(ids) and len(ids) == len(set(ids))
                      and result.testsRun == len(ids) and executed_ids == ids)
        data = {
            'schema': 1,
            'startedAtUtc': started_at,
            'atUtc': datetime.now(timezone.utc).isoformat(),
            'scope': ('R165 task transport and direct lifecycle/closure/host-client '
                      'source/fixture contracts; real fixture sockets, pipes and HTTP, '
                      'not installed/native/kernel/model acceptance'),
            'result': 'PASS' if successful else 'FAIL',
            'exitCode': 0 if successful else 1,
            'platform': platform.platform(),
            'python': sys.version,
            'label': args.label,
            'testSelectors': selectors,
            'selectorCounts': selector_counts,
            'selectedTests': len(ids),
            'selectedTestIds': ids,
            'selectedTestIdsSha256': ids_sha256(ids),
            'uniqueTestIds': len(set(ids)),
            'testsRun': 0 if result is None else result.testsRun,
            'executedTestIds': executed_ids,
            'executedTestIdsSha256': ids_sha256(executed_ids),
            'executedIdsMatchSelection': executed_ids == ids and bool(ids),
            'passed': 0 if result is None else len(result.successful_test_ids),
            'failures': 0 if result is None else len(result.failures),
            'errors': 0 if result is None else len(result.errors),
            'expectedFailures': 0 if result is None else len(result.expectedFailures),
            'unexpectedSuccesses': 0 if result is None else len(result.unexpectedSuccesses),
            'skipped': 0 if result is None else len(result.skipped),
            'skippedTests': [] if result is None else [(test.id(), why) for test, why in result.skipped],
            'failedTests': [] if result is None else [test.id() for test, _ in result.failures],
            'errorTests': [] if result is None else [test.id() for test, _ in result.errors],
            'seconds': round(seconds, 6),
            'r165Discovery': discovery_before,
            'r165DiscoveryAfterTest': discovery_after,
            'r165DiscoveryUnchangedAfterTest': discovery_unchanged,
            'sourceHashes': before.get('source', {}),
            'sourceHashesAfterTest': after.get('source', {}),
            'sourceHashesUnchangedAfterTest': unchanged['source'],
            'testHashes': before.get('test', {}),
            'testHashesAfterTest': after.get('test', {}),
            'testHashesUnchangedAfterTest': unchanged['test'],
            'supportHashes': before.get('support', {}),
            'supportHashesAfterTest': after.get('support', {}),
            'supportHashesUnchangedAfterTest': unchanged['support'],
            'runnerSha256': runner_before,
            'runnerSha256AfterTest': runner_after,
            'runnerSha256UnchangedAfterTest': runner_unchanged,
            'inputErrors': input_errors,
            'runnerErrors': runner_errors,
            'logFile': log.name,
            'logBytes': log.stat().st_size,
            'logSha256': hashlib.sha256(log.read_bytes()).hexdigest(),
            'realModelCalls': 0,
            'realProviderCalls': 0,
            'nativeServiceStarted': False,
            'installedServiceAccepted': False,
            'kernelConfinementTested': False,
        }
        json.dump(data, report_stream, indent=2, sort_keys=True)
        report_stream.write('\n')

    bulky = {'testSelectors', 'selectorCounts', 'selectedTestIds', 'executedTestIds',
             'sourceHashes', 'sourceHashesAfterTest', 'testHashes', 'testHashesAfterTest',
             'supportHashes', 'supportHashesAfterTest', 'r165Discovery', 'r165DiscoveryAfterTest'}
    print(json.dumps({key: value for key, value in data.items() if key not in bulky},
                     ensure_ascii=False))
    if not successful:
        print(log.read_text(encoding='utf-8')[-16000:])
    return data['exitCode']


if __name__ == '__main__':
    sys.exit(main())
