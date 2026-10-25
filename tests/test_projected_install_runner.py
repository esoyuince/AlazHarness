"""Operator receipt propagation; no WSL, root actor or installer invocation."""
import ast
import importlib.util
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest

PATH = Path(__file__).resolve().parents[1] / 'scripts/qa/r154a1_install_candidate.py'
SPEC = importlib.util.spec_from_file_location('projected_install_operator_under_test', PATH)
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


class OperatorTerminalTests(unittest.TestCase):
    def report(self, **change):
        value = {'kind': 'R154A1_SOURCE_INSTALL_OPERATION', 'phase': 'INSTALLED_SOURCE_ONLY',
                 'installerSpawnAttempted': True, 'installerTerminalObserved': True,
                 'installerPid': 321, 'installerExitCode': 0, 'installed': True}
        value.update(change)
        return value

    def terminal(self, value, code=0, error=b''):
        return runner.installation_terminal(code, b'bounded output', error, value, 123)

    def test_complete_receipt_accepts_source_installation_only(self):
        result = self.terminal(self.report())
        self.assertEqual(result['state'], 'INSTALLED_SOURCE_ONLY')
        self.assertTrue(result['installed'])
        self.assertEqual((result['hostPid'], result['installerPid']), (123, 321))
        for name in ('processMayBeRunning', 'projectedReadinessAccepted', 'finiteWorkExecuted',
                     'automaticRetry', 'automaticCleanup'):
            self.assertIs(result[name], False)

    def test_inner_timeout_remains_unknown_with_original_process_identity(self):
        result = self.terminal(self.report(phase='INSTALLER_OUTCOME_UNKNOWN',
            installed=False, installerTerminalObserved=False, processMayBeRunning=True), code=2)
        self.assertEqual(result['state'], 'UNKNOWN')
        self.assertEqual(result['installerPid'], 321)
        self.assertTrue(result['processMayBeRunning'])
        self.assertFalse(result['installed'])

    def test_exception_during_spawn_remains_unknown_without_a_returned_pid(self):
        result = self.terminal(self.report(phase='INSTALLER_INVOKED', installed=False,
            installerTerminalObserved=False, installerPid=None), code=2)
        self.assertEqual(result['state'], 'UNKNOWN')
        self.assertIsNone(result['installerPid'])

    def test_missing_root_report_is_unknown(self):
        result = self.terminal(None, code=1, error=b'root carrier interrupted')
        self.assertEqual(result['state'], 'UNKNOWN')
        self.assertTrue(result['processMayBeRunning'])

    def test_wrong_report_kind_is_unknown(self):
        self.assertEqual(self.terminal(self.report(kind='unrelated'))['state'], 'UNKNOWN')

    def test_known_preflight_refusal_has_no_live_child_claim(self):
        result = self.terminal({'kind': 'R154A1_SOURCE_INSTALL_OPERATION',
            'phase': 'PREFLIGHT', 'installed': False}, code=2)
        self.assertEqual(result['state'], 'NOT_ACCEPTED')
        self.assertFalse(result['processMayBeRunning'])

    def test_observed_installer_failure_is_not_a_running_child(self):
        result = self.terminal(self.report(phase='INSTALLER_INVOKED',
            installerExitCode=2, installed=False), code=2)
        self.assertEqual(result['state'], 'NOT_ACCEPTED')
        self.assertTrue(result['installerTerminalObserved'])
        self.assertFalse(result['processMayBeRunning'])

    def test_stderr_prevents_acceptance_without_inventing_unknown_child(self):
        result = self.terminal(self.report(), error=b'unexpected carrier warning')
        self.assertEqual(result['state'], 'NOT_ACCEPTED')
        self.assertFalse(result['processMayBeRunning'])

    def test_unknown_flag_overrides_an_apparent_success(self):
        result = self.terminal(self.report(processMayBeRunning=True))
        self.assertEqual(result['state'], 'UNKNOWN')
        self.assertFalse(result['installed'])

    def test_optimized_driver_refuses_before_any_action(self):
        result = subprocess.run([sys.executable, '-I', '-O', '-B', str(PATH), '--help'],
                                capture_output=True, timeout=5)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(b'optimized_driver_refused', result.stderr)
        self.assertEqual(result.stdout, b'')


@unittest.skipUnless(sys.platform == 'linux', 'owned descriptor/mode fixture requires Linux')
class ProvisioningModeTests(unittest.TestCase):
    def test_exact_transport_writers_set_modes_even_with_restrictive_umask(self):
        # Execute only the two actual filesystem helpers in an owned temporary
        # tree; none of the transport actor/WSL/installer body is invoked.
        tree = ast.parse(runner.LINUX_TRANSPORT)
        helpers = [n for n in tree.body if isinstance(n, ast.FunctionDef)
                   and n.name in ('put', 'new_directory')]
        self.assertEqual({n.name for n in helpers}, {'put', 'new_directory'})
        namespace = {'os': os}
        exec(compile(ast.Module(body=helpers, type_ignores=[]), '<owned-provisioner-helpers>', 'exec'), namespace)
        with tempfile.TemporaryDirectory(prefix='alaz-r154-modes-') as temporary:
            root = Path(temporary)
            before = os.umask(0o077)
            try:
                directory = root / 'new-input'
                namespace['new_directory'](directory)
                namespace['put'](directory / 'source.py', b'raise AssertionError("must not execute")\n')
            finally:
                os.umask(before)
            self.assertEqual(stat.S_IMODE(directory.stat().st_mode), 0o755)
            self.assertEqual(stat.S_IMODE((directory / 'source.py').stat().st_mode), 0o644)
            self.assertEqual((directory / 'source.py').read_bytes(), b'raise AssertionError("must not execute")\n')
            with self.assertRaises(FileExistsError):
                namespace['put'](directory / 'source.py', b'overwrite')
            with self.assertRaises(FileExistsError):
                namespace['new_directory'](directory)


if __name__ == '__main__':
    unittest.main()
