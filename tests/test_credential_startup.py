"""Narrow self-process metadata policy; no Linux sandbox is applied by unittest."""
import copy
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'packages/claw-hermes'))
import credential_guard as g


def policy():
    return {'version':1,'enabled':True,'readonly':['/usr'],
            'writable':['/tmp/owned/work'],'protected':['/private/broker.json']}


class SelfMetadataPolicy(unittest.TestCase):
    def test_legacy_normalization_and_digest_unchanged(self):
        p=policy()
        self.assertEqual(g.validate_policy(p),p)
        self.assertNotIn('self_metadata',g.validate_policy(p))
        self.assertEqual(g.policy_digest(p),g.policy_digest(g.validate_policy(p)))

    def test_explicit_subset_is_sorted(self):
        p=policy()|{'self_metadata':['status','cmdline','stat']}
        self.assertEqual(g.validate_policy(p)['self_metadata'],['cmdline','stat','status'])

    def test_caller_object_not_mutated(self):
        p=policy()|{'self_metadata':['status','stat']}
        before=copy.deepcopy(p)
        g.validate_policy(p)
        self.assertEqual(p,before)

    def test_invalid_or_empty_list_refused(self):
        for value in ([],True,{},'status',None,1):
            with self.subTest(value=value),self.assertRaises(g.GuardRejected):
                g.validate_policy(policy()|{'self_metadata':value})

    def test_duplicate_names_refused(self):
        with self.assertRaisesRegex(g.GuardRejected,'duplicate_self_metadata'):
            g.validate_policy(policy()|{'self_metadata':['status','status']})

    def test_sensitive_and_directory_leaves_refused(self):
        for name in ('environ','mem','fd','fd/0','root','exe','maps','net','task'):
            with self.subTest(name=name),self.assertRaises(g.GuardRejected):
                g.validate_policy(policy()|{'self_metadata':[name]})

    def test_traversal_and_absolute_path_refused(self):
        for name in ('../1/status','/proc/1/stat','./status','status/../environ'):
            with self.subTest(name=name),self.assertRaises(g.GuardRejected):
                g.validate_policy(policy()|{'self_metadata':[name]})

    def test_direct_proc_grants_still_refused(self):
        for key in ('readonly','writable'):
            for target in ('/proc','/proc/self','/proc/self/status','/proc/1/status'):
                p=policy();p[key]=[target]
                with self.subTest(key=key,target=target),self.assertRaises(g.GuardRejected):
                    g.validate_policy(p)

    def test_caller_cannot_supply_process_identity(self):
        with self.assertRaisesRegex(g.GuardRejected,'policy_fields'):
            g.validate_policy(policy()|{'self_metadata':['status'],'pid':1})

    def test_exact_current_launcher_pid_only(self):
        p=g.validate_policy(policy()|{'self_metadata':['stat','status']})
        with patch.object(g.os,'getpid',return_value=12345):
            self.assertEqual(g.self_metadata_paths(p),
                [Path('/proc/12345/stat'),Path('/proc/12345/status')])

    def test_default_grants_no_process_paths(self):
        self.assertEqual(g.self_metadata_paths(g.validate_policy(policy())),[])

    def test_policy_digest_binds_metadata_selection(self):
        a=g.validate_policy(policy());b=g.validate_policy(policy()|{'self_metadata':['stat']})
        c=g.validate_policy(policy()|{'self_metadata':['status']})
        self.assertEqual(len({g.policy_digest(a),g.policy_digest(b),g.policy_digest(c)}),3)


if __name__=='__main__':unittest.main(verbosity=2)
