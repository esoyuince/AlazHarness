"""Combined contract/order tests. No namespace, kernel or model call in discovery."""
import copy
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'packages/claw-hermes'))
import combined_guard as guard


class CombinedContractTests(unittest.TestCase):
    def setUp(self):
        self.command=['/usr/bin/python3','-I','-B','/owned/worker.py']
        self.policy={'version':1,'enabled':True,'readonly':['/usr','/owned/code'],
            'writable':['/owned/work','/dev/null'],'protected':['/private/canary']}
        self.contract={'version':1,'enabled':True,'launchId':'unit-owned-launch',
            'network':'loopback_only','filesystem':self.policy,
            'commandSha256':guard.command_digest(self.command)}

    def test_explicit_both_layers_validates_without_mutating_input(self):
        before=copy.deepcopy(self.contract)
        value=guard.validate_contract(self.contract)
        self.assertEqual(self.contract,before)
        self.assertEqual(value['filesystem']['readonly'],sorted(self.policy['readonly']))

    def test_unknown_contract_fields_are_not_authority(self):
        for field in ('allowFallback','privileged','capabilities','budget','approved'):
            with self.subTest(field=field),self.assertRaises(guard.CombinedGuardRejected):
                guard.validate_contract(self.contract|{field:True})

    def test_missing_layers_refused(self):
        for key in guard.FIELDS:
            candidate={k:v for k,v in self.contract.items() if k!=key}
            with self.subTest(key=key),self.assertRaises(guard.CombinedGuardRejected):
                guard.validate_contract(candidate)

    def test_version_boolean_or_future_not_accepted(self):
        for version in (True,False,0,2,'1'):
            with self.subTest(version=version),self.assertRaises(guard.CombinedGuardRejected):
                guard.validate_contract(self.contract|{'version':version})

    def test_disabled_or_single_layer_contract_is_refused(self):
        for fields in ({'enabled':False},{'enabled':1},{'network':'off'},{'network':'host'}):
            with self.subTest(fields=fields),self.assertRaises(guard.CombinedGuardRejected):
                guard.validate_contract(self.contract|fields)

    def test_launch_identity_is_bounded(self):
        for value in ('', 'abc', '../escape', 'spaces forbidden', 'a'*81, None):
            with self.subTest(value=value),self.assertRaises(guard.CombinedGuardRejected):
                guard.validate_contract(self.contract|{'launchId':value})

    def test_command_hash_requires_lowercase_sha256(self):
        for value in ('1'*63,'G'*64,'A'*64, None,42):
            with self.subTest(value=value),self.assertRaises(guard.CombinedGuardRejected):
                guard.validate_contract(self.contract|{'commandSha256':value})

    def test_filesystem_broad_grants_remain_refused(self):
        for root in ('/','/proc','/tmp','/etc'):
            with self.subTest(root=root),self.assertRaises(guard.filesystem.GuardRejected):
                guard.validate_contract(self.contract|{'filesystem':self.policy|{'readonly':[root]}})

    def test_secret_may_not_move_inside_any_grant(self):
        with self.assertRaises(guard.filesystem.GuardRejected):
            guard.validate_contract(self.contract|{'filesystem':self.policy|{'protected':['/owned/work/key']}})

    def test_command_fingerprint_changes_for_any_argument(self):
        self.assertNotEqual(guard.command_digest(self.command),guard.command_digest(self.command+['--force']))
        self.assertNotEqual(guard.command_digest(['a','bc']),guard.command_digest(['ab','c']))

    def test_command_shape_and_bounds(self):
        for command in ([],(),[''],['/bin/echo',None],['/bin/echo','bad\0arg'],['/bin/echo']*65,
                        ['/bin/echo','x'*4097],['/bin/echo']+['x'*4096]*4):
            with self.subTest(command=str(command)[:60]),self.assertRaises(guard.CombinedGuardRejected):
                guard.command_digest(command)

    def test_wrong_command_refused_before_any_enforcement(self):
        with patch.object(guard.network,'enter') as net,patch.object(guard.filesystem,'apply') as fs:
            with self.assertRaisesRegex(guard.CombinedGuardRejected,'command_mismatch'):
                guard.enforce(self.contract,self.command+['unexpected'])
            net.assert_not_called();fs.assert_not_called()

    def test_network_before_filesystem_in_same_pid(self):
        events=[]
        def network():
            events.append('network');return {'mode':'linux_netns_loopback_only','after':{'pid':os.getpid()}}
        def filesystem(policy):
            events.append('filesystem');return {'state':'enforced','noNewPrivs':True,'protectedReadDenials':1}
        with patch.object(guard.network,'enter',side_effect=network),patch.object(guard.filesystem,'apply',side_effect=filesystem):
            result=guard.enforce(self.contract,self.command)
        self.assertEqual(events,['network','filesystem'])
        self.assertEqual(result['pid'],os.getpid());self.assertEqual(result['state'],'enforced')
        for field in ('fallback','completeD3B','separateHostUid','unixSocketAuthorityIsolated',
                      'independentBrokerBudgetAuthority','targetExecutionVerified'):
            self.assertIs(result[field],False,field)

    def test_network_failure_cannot_become_filesystem_only_success(self):
        with patch.object(guard.network,'enter',side_effect=RuntimeError('refused')),patch.object(guard.filesystem,'apply') as fs:
            with self.assertRaises(RuntimeError):guard.enforce(self.contract,self.command)
            fs.assert_not_called()

    def test_filesystem_failure_cannot_become_network_only_success(self):
        net={'mode':'linux_netns_loopback_only','after':{'pid':os.getpid()}}
        with patch.object(guard.network,'enter',return_value=net),patch.object(guard.filesystem,'apply',side_effect=RuntimeError('denied')):
            with self.assertRaises(RuntimeError):guard.enforce(self.contract,self.command)

    def test_network_receipt_for_different_pid_refused(self):
        net={'mode':'linux_netns_loopback_only','after':{'pid':os.getpid()+1}}
        with patch.object(guard.network,'enter',return_value=net),patch.object(guard.filesystem,'apply') as fs:
            with self.assertRaisesRegex(guard.CombinedGuardRejected,'network_receipt'):
                guard.enforce(self.contract,self.command)
            fs.assert_not_called()

    def test_partial_or_missing_secret_denial_is_refused(self):
        net={'mode':'linux_netns_loopback_only','after':{'pid':os.getpid()}}
        for fs in ({'state':'off','noNewPrivs':True,'protectedReadDenials':1},
                   {'state':'enforced','noNewPrivs':False,'protectedReadDenials':1},
                   {'state':'enforced','noNewPrivs':True,'protectedReadDenials':0}):
            with self.subTest(fs=fs),patch.object(guard.network,'enter',return_value=net),patch.object(guard.filesystem,'apply',return_value=fs):
                with self.assertRaisesRegex(guard.CombinedGuardRejected,'filesystem_receipt'):
                    guard.enforce(self.contract,self.command)

    def test_contract_digest_is_deterministic_and_policy_bound(self):
        canonical=guard.validate_contract(self.contract)
        self.assertEqual(guard.digest(canonical),guard.digest(dict(reversed(list(canonical.items())))))
        changed=copy.deepcopy(canonical);changed['filesystem']['writable'].append('/owned/other')
        self.assertNotEqual(guard.digest(canonical),guard.digest(changed))


if __name__=='__main__':unittest.main()
