"""Joint argv/refusal unit contracts. Native enforcement is measured separately.

Temporary host paths are used for pathname choreography; only that translation
is mocked for Windows. Strict policy parsing has independent unmocked tests.
"""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('alaz_joint_launcher',ROOT/'scripts/run_joint_boundary.py')
launcher=importlib.util.module_from_spec(spec);spec.loader.exec_module(launcher)


class JointLaunchContracts(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name).resolve()
        self.ro=self.root/'ro';self.ro.mkdir()
        self.work=self.root/'work';self.work.mkdir()
        self.code=self.ro/'repo';(self.code/'scripts').mkdir(parents=True)
        for name in ('run_in_network_namespace.py','run_credential_guard.py'):
            (self.code/'scripts'/name).write_text('reviewed placeholder')
        self.python=self.ro/'python-local';self.python.write_text('not executed')
        self.cfg=self.root/'policy.json'
        self.policy={'version':1,'enabled':True,'readonly':['/usr'],
             'writable':['/tmp/alaz-owned'],'protected':['/tmp/alaz-private/key']}
        self.cfg.write_text(json.dumps(self.policy))
        self.net=self.work/'network.json';self.cred=self.work/'credential.json'
        self.translated={'version':1,'enabled':True,'readonly':[str(self.ro)],
             'writable':[str(self.work)],'protected':[str(self.root/'secret')]}

    def call(self,command=None,**overrides):
        options={'policy_file':self.cfg,'network_receipt':self.net,'credential_receipt':self.cred,
            'command':[str(self.python),'-I','-B','task.py'] if command is None else command,
            'python':self.python,'root':self.code}|overrides
        with patch.object(launcher,'validate_policy',return_value=self.translated):
            return launcher.compose(**options)

    def test_network_precedes_credential_and_original_target(self):
        command=[str(self.python),'-I','-B','task.py','argument with spaces']
        argv=self.call(command)
        self.assertIsInstance(argv,tuple)
        n=argv.index(str(self.code/'scripts/run_in_network_namespace.py'))
        c=argv.index(str(self.code/'scripts/run_credential_guard.py'))
        self.assertLess(n,c);self.assertEqual(tuple(command),argv[-len(command):])
        self.assertEqual(argv.count('--'),2)
        self.assertNotIn('shell',argv)

    def test_no_disable_mode_or_fallback_argv(self):
        argv=self.call();self.assertNotIn('--off',argv);self.assertNotIn('--fallback',argv)
        self.assertEqual(argv[0],str(self.python))

    def test_empty_command_refuses(self):
        with self.assertRaisesRegex(launcher.GuardRejected,'command_count'):self.call([])

    def test_too_many_arguments_refuse(self):
        with self.assertRaisesRegex(launcher.GuardRejected,'command_count'):self.call([str(self.python)]+['a']*128)

    def test_null_argument_refuses(self):
        with self.assertRaisesRegex(launcher.GuardRejected,'command_argument'):self.call([str(self.python),'bad\x00value'])

    def test_nonstring_argument_refuses(self):
        with self.assertRaisesRegex(launcher.GuardRejected,'command_argument'):self.call([str(self.python),5])

    def test_large_argument_refuses(self):
        with self.assertRaisesRegex(launcher.GuardRejected,'command_argument'):self.call([str(self.python),'x'*8193])

    def test_aggregate_argument_budget_refuses(self):
        with self.assertRaisesRegex(launcher.GuardRejected,'command_size'):self.call([str(self.python)]+['x'*8192]*17)

    def test_relative_executable_refuses(self):
        with self.assertRaisesRegex(launcher.GuardRejected,'target_file'):self.call(['relative-python','-c','pass'])

    def test_missing_executable_refuses(self):
        with self.assertRaisesRegex(launcher.GuardRejected,'target_file'):self.call([str(self.ro/'missing')])

    def test_receipt_collision_refuses(self):
        with self.assertRaisesRegex(launcher.GuardRejected,'receipt_collision'):self.call(credential_receipt=self.net)

    def test_existing_receipt_preserved(self):
        self.net.write_text('prior receipt')
        with self.assertRaisesRegex(launcher.GuardRejected,'fresh_granted_receipt'):self.call()
        self.assertEqual(self.net.read_text(),'prior receipt')

    def test_receipt_outside_grant_refuses(self):
        with self.assertRaisesRegex(launcher.GuardRejected,'fresh_granted_receipt'):self.call(network_receipt=self.root/'not-granted.json')

    def test_missing_receipt_parent_refuses(self):
        with self.assertRaisesRegex(launcher.GuardRejected,'fresh_granted_receipt'):self.call(network_receipt=self.work/'missing'/'record.json')

    def test_target_in_writable_tree_refuses(self):
        target=self.work/'program';target.write_text('must not execute')
        with self.assertRaisesRegex(launcher.GuardRejected,'not_readonly'):self.call([str(target)])

    def test_missing_credential_launcher_refuses(self):
        (self.code/'scripts/run_credential_guard.py').unlink()
        with self.assertRaisesRegex(launcher.GuardRejected,'credential_launcher'):self.call()

    def test_duplicate_json_refuses_before_translation(self):
        self.cfg.write_text('{"version":1,"version":1}')
        with self.assertRaisesRegex(launcher.GuardRejected,'duplicate_key'):self.call()

    def test_disabled_policy_refuses_without_mock(self):
        self.cfg.write_text(json.dumps(self.policy|{'enabled':False}))
        with self.assertRaisesRegex(launcher.GuardRejected,'optin_required'):
            launcher.compose(self.cfg,self.net,self.cred,[str(self.python)],python=self.python,root=self.code)

    def test_unknown_policy_field_refuses_without_mock(self):
        self.cfg.write_text(json.dumps(self.policy|{'allowAll':True}))
        with self.assertRaisesRegex(launcher.GuardRejected,'policy_fields'):
            launcher.compose(self.cfg,self.net,self.cred,[str(self.python)],python=self.python,root=self.code)

    def test_exec_failure_never_retries_or_calls_target(self):
        args=['run_joint_boundary.py','--policy',str(self.cfg),'--network-receipt',str(self.net),
              '--credential-receipt',str(self.cred),'--',str(self.python)]
        with patch.object(sys,'argv',args),patch.object(sys,'platform','linux'),\
             patch.object(launcher,'compose',return_value=('fixed-launcher','--arg')),\
             patch.object(launcher.os,'execv',side_effect=OSError('deliberate failure')) as execute,\
             contextlib.redirect_stderr(io.StringIO()) as stderr:
            self.assertEqual(launcher.main(),2)
        execute.assert_called_once_with('fixed-launcher',('fixed-launcher','--arg'))
        self.assertIs(json.loads(stderr.getvalue())['fallback'],False)


if __name__=='__main__':unittest.main(verbosity=2)
