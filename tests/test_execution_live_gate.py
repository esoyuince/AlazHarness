"""Final-boundary configuration checks; fixture config ports, no native process."""
import unittest
import test_execution_profile_qa3156 as profile_fixture
from execution_budget import ExecutionDenied

class FinalBoundaryConfigurationTests(unittest.TestCase):
    def setUp(self):
        self.f=profile_fixture.LiveProfileConsistencyTests('test_unchanged_profile_is_accepted')
        self.f.setUp();self.addCleanup(self.f.doCleanups)
    def test_tool_ledger_rechecks_revoked_allowlist(self):
        self.f.live()['allowed_read_files']=[]
        with self.assertRaisesRegex(ExecutionDenied,'execution_settings_changed'):
            self.f.boundary.ledger()
    def test_ledger_rechecks_lowered_budget_before_owner_access(self):
        self.f.live()['policy']['max_provider_calls']=0
        with self.assertRaisesRegex(ExecutionDenied,'execution_settings_changed'):
            self.f.boundary.ledger()
    def test_unavailable_settings_are_not_default_permission(self):
        def broken(_):raise OSError('fixture lookup failure')
        self.f.context.get_config=broken
        with self.assertRaisesRegex(ExecutionDenied,'execution_settings_unavailable'):
            self.f.boundary.ledger()
    def test_changed_provider_token_is_not_implicitly_adopted(self):
        self.f.live()['provider_bearer']='q'*32
        with self.assertRaisesRegex(ExecutionDenied,'execution_settings_changed'):
            self.f.boundary.validate_profile()
    def test_reordered_settings_do_not_revoke_equal_policy(self):
        entry=self.f.cfg['plugins']['entries']['alaz-host-gate']['settings']
        entry['execution']=dict(reversed(list(self.f.live().items())))
        self.assertIsNone(self.f.boundary.validate_profile())
    def test_nonfinite_policy_refuses_before_ledger(self):
        self.f.live()['policy']['max_provider_calls']=float('nan')
        with self.assertRaisesRegex(ExecutionDenied,'execution_settings_unavailable'):
            self.f.boundary.ledger()

if __name__=='__main__':unittest.main()
