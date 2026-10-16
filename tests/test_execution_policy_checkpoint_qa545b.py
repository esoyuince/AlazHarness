"""Independent C01 checkpoint contracts: real boundary, synthetic config/registry.
No Gateway, provider SDK or native tool runs in these offline tests.
"""
import asyncio
import copy
from dataclasses import asdict
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tests'))
sys.path.insert(0, str(ROOT / 'packages/claw-hermes'))
import test_execution_profile_qa3156 as profile_fixture
from execution_budget import ExecutionDenied


class ExecutionCheckpointTests(unittest.TestCase):
    def setUp(self):
        # Reuse setup only, not inherited TestCase methods or duplicate discovery.
        self.fixture = profile_fixture.LiveProfileConsistencyTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.boundary = self.fixture.boundary

    def live(self):
        return self.fixture.live()

    def test_revocation_checked_before_tool_ledger_construction(self):
        self.live()['allowed_read_files'] = []
        # The synthetic adapter deliberately has no gateway_runner. Refusal must
        # precede native-owner access, not depend on that unrelated missing field.
        with self.assertRaisesRegex(ExecutionDenied, 'execution_settings_changed'):
            self.boundary.tools.ledger()

    def test_lowered_budget_checked_before_provider_ledger(self):
        self.live()['policy']['max_provider_calls'] = 0
        with self.assertRaisesRegex(ExecutionDenied, 'execution_settings_changed'):
            self.boundary.ledger()

    def test_live_credential_change_refuses_before_owner_access(self):
        self.live()['provider_bearer'] = 'q' * 32
        with self.assertRaisesRegex(ExecutionDenied, 'execution_settings_changed'):
            self.boundary.ledger()

    def test_settings_loader_error_is_bounded_refusal(self):
        self.boundary.context.get_config = Mock(side_effect=OSError('fixture hidden detail'))
        with self.assertRaisesRegex(ExecutionDenied, '^execution_settings_unavailable$'):
            self.boundary.ledger()

    def test_missing_registration_context_is_not_permissive(self):
        del self.boundary.context
        with self.assertRaisesRegex(ExecutionDenied, '^execution_settings_unavailable$'):
            self.boundary.validate_profile()

    def test_nonserializable_live_setting_refuses(self):
        self.live()['unqualified'] = object()
        with self.assertRaisesRegex(ExecutionDenied, '^execution_settings_unavailable$'):
            self.boundary.validate_profile()

    def test_null_live_settings_refuse(self):
        self.fixture.cfg['plugins']['entries']['alaz-host-gate']['settings']['execution'] = None
        with self.assertRaisesRegex(ExecutionDenied, '^execution_settings_changed$'):
            self.boundary.validate_profile()

    def test_boolean_live_limit_is_not_integer_alias(self):
        self.live()['policy']['max_tool_calls'] = True
        with self.assertRaisesRegex(ExecutionDenied, '^execution_settings_changed$'):
            self.boundary.validate_profile()

    def test_readiness_denial_does_not_initialize_or_reset_ledger(self):
        self.live()['policy']['total_cost_microusd'] = 0
        owner = Mock()
        self.boundary.ledger = owner
        with self.assertRaisesRegex(ExecutionDenied, '^execution_settings_changed$'):
            asyncio.run(self.boundary.require_ready())
        owner.assert_not_called()

    def test_failed_check_does_not_mutate_running_policy(self):
        before = asdict(self.boundary.policy)
        upstream = self.boundary.upstream
        self.live()['policy']['max_provider_calls'] = 0
        self.live()['upstream_base_url'] = 'http://127.0.0.1:45814/v1'
        with self.assertRaises(ExecutionDenied):
            self.boundary.validate_profile()
        self.assertEqual(asdict(self.boundary.policy), before)
        self.assertEqual(self.boundary.upstream, upstream)

    def test_failed_check_does_not_rebind_snapshot_to_new_policy(self):
        self.live()['policy']['max_provider_calls'] = 0
        for _ in range(2):
            with self.assertRaisesRegex(ExecutionDenied, '^execution_settings_changed$'):
                self.boundary.validate_profile()
        self.assertEqual(self.boundary.policy.max_provider_calls, 3)

    def test_reordered_unchanged_settings_are_equivalent(self):
        entry = self.fixture.cfg['plugins']['entries']['alaz-host-gate']['settings']
        entry['execution'] = dict(reversed(list(copy.deepcopy(self.live()).items())))
        self.assertIsNone(self.boundary.validate_profile())


if __name__ == '__main__':
    unittest.main()
