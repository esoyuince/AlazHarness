"""Policy-only credential guard tests; no kernel sandbox in unittest process."""
import copy
import ctypes
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock, patch
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'packages/claw-hermes'))
import credential_guard as g


def policy():
    return {'version':1,'enabled':True,'readonly':['/usr','/work/readonly'],
            'writable':['/work/runtime','/dev/null'],'protected':['/private/key.json']}


class PolicyTests(unittest.TestCase):
    def reject(self, p, reason):
        with self.assertRaisesRegex(g.GuardRejected, reason):g.validate_policy(p)

    def test_explicit_valid_policy(self):
        p=g.validate_policy(policy());self.assertEqual(p['readonly'],sorted(p['readonly']))

    def test_no_extra_keys(self):
        p=policy();p['fallback']=True;self.reject(p,'policy_fields')

    def test_optin_required(self):
        for value in (False,1,'true',None):
            p=policy();p['enabled']=value
            with self.subTest(value=value):self.reject(p,'optin_required')

    def test_bool_version_refused(self):
        p=policy();p['version']=True;self.reject(p,'version')

    def test_missing_protected_refused(self):
        p=policy();p['protected']=[];self.reject(p,'path_count')

    def test_nonlist_paths_refused(self):
        p=policy();p['readonly']='/usr';self.reject(p,'path_count')

    def test_duplicate_paths_refused(self):
        p=policy();p['readonly']=['/usr','/usr'];self.reject(p,'duplicate_path')

    def test_broad_paths_refused(self):
        for path in ('/','/home','/tmp','/proc','/proc/self','/sys','/etc','/dev'):
            p=policy();p['readonly']=[path]
            with self.subTest(path=path):self.reject(p,'broad_grant')

    def test_noncanonical_paths_refused(self):
        for path in ('../usr','/usr/../home','/usr/','//usr','/usr//bin','/work/./file','/bad\x00path'):
            p=policy();p['readonly']=[path]
            with self.subTest(path=path):self.reject(p,'path_not_canonical')

    def test_secret_cannot_be_under_readable_root(self):
        p=policy();p['readonly']=['/private'];self.reject(p,'secret_in_granted_tree')

    def test_secret_cannot_be_under_writable_root(self):
        p=policy();p['protected']=['/work/runtime/broker.json'];self.reject(p,'secret_in_granted_tree')

    def test_read_write_ancestor_overlap_refused(self):
        p=policy();p['readonly']=['/work'];self.reject(p,'overlapping_access')

    def test_read_write_descendant_overlap_refused(self):
        p=policy();p['readonly']=['/work/runtime/code'];self.reject(p,'overlapping_access')

    def test_system_writes_refused(self):
        for path in ('/usr/bin','/etc/hosts','/usr'):
            p=policy();p['writable']=[path]
            with self.subTest(path=path):self.reject(p,'system_write')

    def test_device_grants_refused_except_null(self):
        p=policy();p['writable']=['/dev/mem'];self.reject(p,'device_grant')

    def test_bit_layout_no_device_or_exec_creation(self):
        self.assertEqual(g.HANDLED,32767)
        self.assertFalse(g.WRITE & ((1<<0)|(1<<6)|(1<<11)))
        self.assertTrue(g.WRITE & (1<<14))
        self.assertEqual(ctypes.sizeof(g.Ruleset),8)
        self.assertEqual(ctypes.sizeof(g.PathRule),12)

    def test_kernel_unsupported_rejects_before_cdll(self):
        with patch.object(g.platform,'system',return_value='Windows'),patch.object(g.ctypes,'CDLL') as m:
            with self.assertRaisesRegex(g.GuardRejected,'unsupported_platform'):g.kernel()
            m.assert_not_called()

    def test_unknown_arch_refused(self):
        with patch.object(g.platform,'system',return_value='Linux'),patch.object(g.platform,'machine',return_value='aarch64'):
            with self.assertRaisesRegex(g.GuardRejected,'unsupported_platform'):g.kernel()

    def test_old_or_disabled_kernel_refused(self):
        for abi in (-1,0,1,2):
            with self.subTest(abi=abi),self.assertRaisesRegex(g.GuardRejected,'abi3_required'):
                g.abi_version(Mock(syscall=Mock(return_value=abi)))

    def test_abi3_required_and_supported(self):
        self.assertEqual(g.abi_version(Mock(syscall=Mock(return_value=3))),3)

    def test_json_duplicate_key_refused(self):
        with self.assertRaisesRegex(g.GuardRejected,'duplicate_key'):
            g.unique_json('{"enabled":true,"enabled":false}')

    def test_json_nonfinite_and_oversize_refused(self):
        for s in ('{"a":NaN}', 'x'*32769):
            with self.subTest(size=len(s)),self.assertRaises(g.GuardRejected):g.unique_json(s)

    def test_policy_digest_stable_order(self):
        a=policy();b=copy.deepcopy(a);b['readonly'].reverse()
        self.assertEqual(g.policy_digest(g.validate_policy(a)),g.policy_digest(g.validate_policy(b)))

    def test_entropy_device_readonly_only(self):
        p=policy();p['readonly'].append('/dev/urandom')
        self.assertIn('/dev/urandom',g.validate_policy(p)['readonly'])
        p=policy();p['writable'].append('/dev/urandom');self.reject(p,'device_grant')

    def test_too_many_paths_refused(self):
        p=policy();p['readonly']=['/file/'+str(i) for i in range(65)];self.reject(p,'path_count')

    def test_prefix_lookalike_not_a_secret_ancestor(self):
        p=policy();p['readonly'].append('/private-safe')
        self.assertEqual(g.validate_policy(p)['protected'],['/private/key.json'])
