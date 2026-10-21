"""Exact self-mount read opt-in; no privileged calls in these contract tests."""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'packages/claw-hermes'))
import credential_guard as guard
import gateway_state_projection as state
POLICY={'version':1,'enabled':True,'readonly':['/usr/bin'],'writable':['/srv/owned/work'],
        'protected':['/srv/owned/canary'],'self_process_metadata':True}

class SelfMountMetadata(unittest.TestCase):
    def test_default_metadata_unchanged(self):
        self.assertEqual(guard.self_metadata_paths(42),('/proc/42/stat','/proc/42/status','/proc/42/statm','/proc/42/cmdline','/proc/stat'))
    def test_optin_adds_only_numeric_self_mountinfo(self):
        default=guard.self_metadata_paths(42)
        self.assertEqual(guard.self_metadata_paths(42,mountinfo=True),default+('/proc/42/mountinfo',))
    def test_false_is_exact_default(self):
        self.assertEqual(guard.self_metadata_paths(42,mountinfo=False),guard.self_metadata_paths(42))
    def test_invalid_pids_rejected(self):
        for value in (True,0,-1,'42',42.0):
            with self.subTest(value=value),self.assertRaises(guard.GuardRejected):
                guard.self_metadata_paths(value,mountinfo=True)
    def test_nonboolean_metadata_flag_refused(self):
        for value in (1,0,None,'true',[],{}):
            with self.subTest(value=value),self.assertRaises(guard.GuardRejected):
                guard.self_metadata_paths(42,mountinfo=value)
    def test_no_directory_fd_environment_or_other_process_grant(self):
        paths=guard.self_metadata_paths(42,mountinfo=True)
        self.assertEqual(len(paths),6)
        self.assertNotIn('/proc/self/mountinfo',paths)
        for name in ('/proc','/proc/42','/proc/42/fd','/proc/42/environ','/proc/42/mem','/proc/41/mountinfo'):
            self.assertNotIn(name,paths)
    def test_apply_option_checked_before_kernel(self):
        for value in (1,None,'yes'):
            with self.subTest(value=value),patch.object(guard,'kernel') as kernel,self.assertRaises(guard.GuardRejected):
                guard.apply(POLICY,self_mount_metadata=value)
            kernel.assert_not_called()
    def test_requires_existing_process_metadata_optin(self):
        for policy in ({k:v for k,v in POLICY.items() if k!='self_process_metadata'},POLICY|{'self_process_metadata':False}):
            with patch.object(guard,'kernel') as kernel,self.assertRaises(guard.GuardRejected):
                guard.apply(policy,self_mount_metadata=True)
            kernel.assert_not_called()
    def test_json_policy_does_not_accept_extra_permission_field(self):
        with self.assertRaises(guard.GuardRejected):guard.validate_policy(POLICY|{'self_mount_metadata':True})
    def test_state_enter_rejects_nonbool_before_observation(self):
        for value in (1,None,'true'):
            with self.subTest(value=value),patch.object(state.gp,'inspect') as inspect,self.assertRaises(state.StateProjectionRejected):
                state.enter({},POLICY,object(),observe_self_mount=value)
            inspect.assert_not_called()
if __name__=='__main__':unittest.main()
