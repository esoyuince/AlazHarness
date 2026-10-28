"""Fixed R168 fixture selection with complete logs and stable source-byte evidence."""
from __future__ import annotations
import argparse
from contextlib import redirect_stdout, redirect_stderr
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

ROOT = Path(__file__).resolve().parents[2]
MODULES = ('test_bootstrap_probe_r168a1', 'test_ping_broker_r168a1',
           'test_service_accept_host_r168a1', 'test_service_lifecycle_qa_r168a1',
           'test_service_seed_r168a1')
QA = ('r168a1_accept.py', 'r168a1_bootstrap_probe.py', 'r168a1_focus.py',
      'r168a1_linux_accept.py', 'r168a1_linux_transport.py', 'r168a1_ping_broker.py',
      'r168a1_seed_child.py', 'r168a1_service_seed.py')


def require(ok, reason):
    if not ok:
        raise RuntimeError(reason)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def inputs():
    # Include the fixture/support and product-module trees, since this fixed
    # selection imports shared validators and prior fixture helpers.
    names = {str(p.relative_to(ROOT)).replace(os.sep, '/')
             for folder in ('tests', 'packages/claw-hermes', 'config')
             for p in (ROOT / folder).rglob('*')
             if p.is_file() and p.suffix in ('.py', '.mjs', '.json')}
    names.update('scripts/qa/' + name for name in QA)
    names.update(('scripts/build_service_candidate.py', 'scripts/verify_service_candidate.py',
                  'scripts/install_service_candidate.py', 'scripts/build_projected_candidate.py',
                  'scripts/install_projected_candidate.py', 'scripts/ci_check.py', 'sources.lock.json'))
    result = {}
    for name in sorted(names):
        p = ROOT / name
        require(p.is_file() and not p.is_symlink(), 'focus_input_not_regular')
        result[name] = sha(p.read_bytes())
    return result


def cases(suite):
    for value in suite:
        if isinstance(value, unittest.TestSuite):
            yield from cases(value)
        else:
            yield value


class RecordedResult(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.executed = []

    def startTest(self, test):
        self.executed.append(test.id())
        super().startTest(test)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--label', required=True)
    args = parser.parse_args(argv)
    require(re.fullmatch('(linux|windows)-[0-9]{2}', args.label), 'focus_label')
    require(platform.system().lower() == args.label.split('-')[0], 'focus_platform')
    require(__debug__ and sys.dont_write_bytecode, 'focus_python_flags')
    before = inputs()
    sys.path[:0] = [str(ROOT / 'tests'), str(ROOT / 'scripts')]
    loader = unittest.TestLoader()
    selected_suites = [loader.loadTestsFromName(name) for name in MODULES]
    require(not loader.errors and all(s.countTestCases() > 0 for s in selected_suites), 'focus_selection_empty')
    require([s.countTestCases() for s in selected_suites] == [22, 25, 31, 28, 30],
            'focus_known_selection_changed')
    suite = unittest.TestSuite(selected_suites)
    selected_cases = list(cases(suite))
    selected = [case.id() for case in selected_cases]
    require(len(selected) == len(set(selected)) == 136, 'focus_selection')
    declared = {}
    for case in selected_cases:
        method = getattr(case, case._testMethodName)
        subject = type(case) if getattr(type(case), '__unittest_skip__', False) else method
        if getattr(subject, '__unittest_skip__', False):
            declared[case.id()] = getattr(subject, '__unittest_skip_why__')
    require(platform.system() != 'Linux' or not declared, 'focus_linux_requires_all_cases')
    folder = ROOT / 'scratch/r168-service' / ('focus-' + args.label)
    folder.mkdir(exist_ok=False)
    log = folder / 'full.log'
    start = time.monotonic()
    with log.open('x', encoding='utf-8', newline='\n') as output:
        with redirect_stdout(output), redirect_stderr(output):
            result = unittest.TextTestRunner(stream=output, verbosity=2, resultclass=RecordedResult).run(suite)
        output.flush()
        os.fsync(output.fileno())
    after = inputs()
    skipped = {case.id(): reason for case, reason in result.skipped}
    accepted = (result.wasSuccessful() and result.testsRun == len(selected)
                and result.executed == selected and before == after and skipped == declared
                and not result.expectedFailures and not result.unexpectedSuccesses)
    raw_log = log.read_bytes()
    record = {'schema': 1, 'kind': 'R168_FIXED_FOCUSED_FIXTURES',
        'atUtc': datetime.now(timezone.utc).isoformat(), 'label': args.label,
        'result': 'PASS' if accepted else 'FAIL', 'platform': platform.system(),
        'pythonVersion': platform.python_version(), 'selectedTestIds': selected,
        'selectedTestIdsSha256': sha(('\n'.join(selected) + '\n').encode()),
        'executedTestIds': result.executed, 'testsRun': result.testsRun,
        'passed': result.testsRun - len(result.failures) - len(result.errors) - len(skipped),
        'failures': len(result.failures), 'errors': len(result.errors), 'skipped': len(skipped),
        'skippedTests': skipped, 'expectedSkippedTests': declared,
        'expectedFailures': len(result.expectedFailures), 'unexpectedSuccesses': len(result.unexpectedSuccesses),
        'seconds': round(time.monotonic() - start, 6), 'inputHashes': before,
        'inputFileCount': len(before), 'sourceBytesUnchanged': before == after,
        'runnerSha256': before['scripts/qa/r168a1_focus.py'],
        'logSha256': sha(raw_log), 'logBytes': len(raw_log), 'fullLogCaptured': True,
        'serviceStarted': False, 'installedAcceptance': False, 'kernelAcceptance': False,
        'realModelCalls': 0, 'productionReady': False, 'exitCode': 0 if accepted else 1}
    raw = (json.dumps(record, sort_keys=True, indent=2, ensure_ascii=True) + '\n').encode('ascii')
    target = folder / 'result.json'
    with target.open('xb') as output:
        output.write(raw)
        output.flush()
        os.fsync(output.fileno())
    print(json.dumps({k: record[k] for k in ('result', 'testsRun', 'passed', 'failures', 'errors',
        'skipped', 'exitCode', 'inputFileCount', 'sourceBytesUnchanged', 'logSha256')} |
        {'resultPath': str(target), 'resultSha256': sha(raw)}, sort_keys=True), flush=True)
    return record['exitCode']


if __name__ == '__main__':
    raise SystemExit(main())
