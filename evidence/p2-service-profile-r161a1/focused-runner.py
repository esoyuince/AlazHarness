"""Reproducible R161 source/fixture gate; not native service acceptance.

Run from this checkout with --label linux or windows. Evidence files must be
absent; pass --label another-name for a separate investigation without overwriting.
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

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'tests'), str(ROOT / 'packages/claw-hermes')]
NAMES = [
    'test_service_profile_r161a1',
    'test_service_profile_binding_r161a1',
    'test_service_projection_r161a1',
    'test_service_handoff_r161a1',
    'test_service_profile_history_r161a1',
    'test_gateway_store_startup',
    'test_three_store_lifecycle_l113f6',
    'test_startup_consumer_owner_s124b1',
    'test_execution_profile_qa3156',
    'test_borrowed_service_host_r159a1.SourceSelectionTests',
    'test_borrowed_service_host_r159a1.ServiceConsumerSelection',
    'test_borrowed_service_host_r159a1.ServiceStartupGuards',
    'test_gateway_state_projection',
    'test_retained_projection_p142c6.MappingContract',
    'test_retained_projection_p142c6.ProjectionSequence',
    'test_retained_projection_p142c6.PivotBarrier',
    'test_retained_projection_p142c6.OriginalStartupHandoff',
    'test_retained_handoff_t143a7',
] + ['test_self_identity_history_r150a1.SelfIdentityHistory.' + name for name in (
    'test_current_product_is_checked_live_not_old_kernel_snapshot',
    'test_tampered_current_launcher_cannot_be_hidden_by_applied_archive',
    'test_tampered_applied_launcher_cannot_be_hidden_by_current_source',
    'test_tampered_current_projection_cannot_be_hidden_by_parent_archive',
    'test_tampered_applied_projection_cannot_be_hidden_by_current_source',
    'test_unknown_paths_or_generations_are_not_redirected',
    'test_tampered_archive_is_never_accepted',
    'test_manifest_cannot_point_to_another_file',
)]
SOURCES = ['packages/claw-hermes/' + name for name in (
    'gateway_service_profile.py', 'gateway_service_projection.py',
    'gateway_service_handoff.py', 'gateway_state_projection.py',
    'gateway_store_startup.py', 'gateway_prepared_consumer.py', 'execution_boundary.py',
)]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--label', required=True)
    args = parser.parse_args()
    assert args.label and all(c.isascii() and (c.isalnum() or c == '-') for c in args.label)
    os.chdir(ROOT)
    folder = Path(__file__).resolve().parent
    log = folder / ('focused-' + args.label + '.log')
    report = folder / ('focused-' + args.label + '.json')
    assert not log.exists() and not report.exists(), 'evidence already exists'
    before = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in SOURCES}
    suite = unittest.defaultTestLoader.loadTestsFromNames(NAMES)
    selected = suite.countTestCases()
    started = time.perf_counter()
    with log.open('x', encoding='utf-8') as stream:
        result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    duration = time.perf_counter() - started
    after = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in SOURCES}
    unchanged = before == after
    successful = result.wasSuccessful() and unchanged and result.testsRun == selected
    data = {'schema': 1, 'atUtc': datetime.now(timezone.utc).isoformat(),
        'scope': 'selected source and fixture contracts; not installed/native/kernel/model acceptance',
        'result': 'PASS' if successful else 'FAIL', 'exitCode': 0 if successful else 1,
        'platform': platform.platform(), 'python': sys.version, 'label': args.label,
        'testSelectors': NAMES, 'selectedTests': selected, 'testsRun': result.testsRun,
        'passed': result.testsRun - len(result.skipped) - len(result.failures) - len(result.errors),
        'failures': len(result.failures), 'errors': len(result.errors),
        'skipped': len(result.skipped), 'skippedTests': [(t.id(), why) for t, why in result.skipped],
        'seconds': round(duration, 6), 'sourceHashes': before,
        'sourceHashesUnchangedAfterTest': unchanged,
        'runnerSha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'logFile': log.name, 'logBytes': log.stat().st_size,
        'logSha256': hashlib.sha256(log.read_bytes()).hexdigest(),
        'realModelCalls': 0, 'realProviderCalls': 0,
        'nativeServiceStarted': False, 'kernelConfinementTested': False}
    with report.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(data, stream, indent=2, sort_keys=True)
        stream.write('\n')
    print(json.dumps({k: v for k, v in data.items() if k not in ('testSelectors', 'sourceHashes')}, ensure_ascii=False))
    if not successful:
        print(log.read_text(encoding='utf-8')[-16000:])
    return data['exitCode']


if __name__ == '__main__':
    sys.exit(main())
