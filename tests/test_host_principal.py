"""Offline contracts for opt-in genuine OS UID separation.

No account changes, permissions, sockets or real providers in default CI.
"""
import importlib.util
import os
from pathlib import Path
import socket
import struct
import sys
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'packages/claw-hermes'))
import host_principal as hp

def spec():
    return {'version':1,'enabled':True,
            'gatewayUid':1000,'brokerUid':65534,'socketGroupGid':1000,'hostUserNamespace':'user:[4026531837]'}

class PolicyContract(unittest.TestCase):
    def test_exact_optin(self):
        self.assertEqual(hp.policy(spec()),spec())
    def test_default_absent_refused(self):
        with self.assertRaises(hp.PrincipalRejected):hp.policy(None)
    def test_unknown_permissions_refused(self):
        for extra in ({'fallback':True},{'useCurrentUser':True},
                      {'writableRoots':['/']},{'allowAllSockets':True}):
            with self.subTest(extra=extra),self.assertRaises(hp.PrincipalRejected):
                hp.policy(spec()|extra)
    def test_missing_fields_refused(self):
        for key in spec():
            item=spec();del item[key]
            with self.subTest(key=key),self.assertRaises(hp.PrincipalRejected):
                hp.policy(item)
    def test_bool_or_false_version_refused(self):
        for value in (0,2,True,False,'1',None):
            with self.subTest(value=value),self.assertRaises(hp.PrincipalRejected):
                hp.policy(spec()|{'version':value})
    def test_disabled_refused(self):
        for value in (False,None,0,1,'true'):
            with self.subTest(value=value),self.assertRaises(hp.PrincipalRejected):
                hp.policy(spec()|{'enabled':value})
    def test_zero_root_and_same_host_uid_refused(self):
        for key in ('gatewayUid','brokerUid','socketGroupGid'):
            with self.subTest(key=key),self.assertRaises(hp.PrincipalRejected):
                hp.policy(spec()|{key:0})
        with self.assertRaisesRegex(hp.PrincipalRejected,'same_host_uid'):
            hp.policy(spec()|{'brokerUid':1000})
    def test_noninteger_and_overflow_refused(self):
        for value in (-1,True,1000.0,'1000',None,2**32):
            with self.subTest(value=value),self.assertRaises(hp.PrincipalRejected):
                hp.policy(spec()|{'brokerUid':value})
    def test_policy_does_not_mutate_input(self):
        a=spec();self.assertEqual(hp.policy(a),a)

class PathContract(unittest.TestCase):
    def test_valid_canonical(self):
        self.assertEqual(str(hp.canonical('/tmp/alaz-owned/path')),'/tmp/alaz-owned/path')
    def test_relative_traversal_alias_refused(self):
        for path in ('', 'relative','./x','/a/../b','/a//b','/a/',
                     '//host/share','/a\x00b',123,None):
            with self.subTest(path=path),self.assertRaises(hp.PrincipalRejected):
                hp.canonical(path)
    def test_overlong_refused(self):
        with self.assertRaises(hp.PrincipalRejected):hp.canonical('/'+('a'*4200))
    def test_socket_is_one_named_endpoint(self):
        with patch.object(hp,'regular',return_value=(1,2,3,4,5)):
            result=hp.socket_identity(spec(),'/tmp/alaz-owned/socket/egress.sock')
            self.assertEqual(set(result),{'directory','socket'})
    def test_wrong_socket_name_refused(self):
        with self.assertRaises(hp.PrincipalRejected):
            hp.socket_identity(spec(),'/tmp/alaz-owned/socket/other.sock')
    def test_socket_path_length_refused(self):
        with self.assertRaises(hp.PrincipalRejected):
            hp.socket_identity(spec(),'/tmp/'+('x'*95)+'/egress.sock')
    def test_regular_rejects_missing_file(self):
        with self.assertRaises(hp.PrincipalRejected):
            hp.regular('/does-not-exist-alaz-principal-unique','file',65534,1000,0o600)
    def test_expected_owner_mode_not_widened(self):
        with patch.object(hp,'regular',return_value=(1,2,3,4,5)) as check:
            hp.budget_identity(spec(),'/tmp/owned/budget')
        self.assertEqual(check.call_args_list[0].args,
                         ('/tmp/owned/budget','dir',65534,1000,0o700))
        self.assertEqual(check.call_args_list[1].args,
                         ('/tmp/owned/budget/budget.sqlite3','file',65534,1000,0o600))
    def test_socket_requires_group_traversal_without_group_write(self):
        with patch.object(hp,'regular',return_value=(1,2,3,4,5)) as check:
            hp.socket_identity(spec(),'/tmp/owned/socket/egress.sock')
        self.assertEqual(check.call_args_list[0].args,
                         ('/tmp/owned/socket','dir',65534,1000,0o710))
        self.assertEqual(check.call_args_list[1].args,
                         ('/tmp/owned/socket/egress.sock','socket',65534,1000,0o660))
    def test_inode_or_alias_change_rejected(self):
        with patch.object(hp,'socket_identity',return_value={'socket':(2,3)}) as same:
            with self.assertRaisesRegex(hp.PrincipalRejected,'socket_rebound'):
                hp.pinned_socket(spec(),'/tmp/owned/socket/egress.sock',
                                 {'socket':(2,4)})
    def test_stable_inode_accepted(self):
        state={'socket':(2,3)}
        with patch.object(hp,'socket_identity',return_value=state):
            self.assertEqual(hp.pinned_socket(spec(),'/tmp/owned/socket/egress.sock',state),state)

class PrincipalProcessContract(unittest.TestCase):
    def test_broker_uid_and_empty_supplementary_groups_required(self):
        with patch.object(hp.os,'name','posix'),patch.object(hp.socket,'SO_PEERCRED',17,create=True),\
             patch.object(hp.os,'getuid',return_value=65534,create=True),\
             patch.object(hp.os,'geteuid',return_value=65534,create=True),\
             patch.object(hp.os,'getgid',return_value=1000,create=True),\
             patch.object(hp.os,'getegid',return_value=1000,create=True),\
             patch.object(hp.os,'getgroups',return_value=[],create=True),\
             patch.object(hp.os,'readlink',return_value='user:[4026531837]'):
            self.assertTrue(hp.broker_identity(spec()))
    def test_forged_userns_identity_refused(self):
        # Numbers alone are insufficient if broker is remapped to same host UID.
        with patch.object(hp.os,'name','posix'),patch.object(hp.socket,'SO_PEERCRED',17,create=True),\
             patch.object(hp.os,'getuid',return_value=65534,create=True),\
             patch.object(hp.os,'geteuid',return_value=65534,create=True),\
             patch.object(hp.os,'getgid',return_value=1000,create=True),\
             patch.object(hp.os,'getegid',return_value=1000,create=True),\
             patch.object(hp.os,'getgroups',return_value=[],create=True),\
             patch.object(hp.os,'readlink',return_value='user:[99999999]'):
            with self.assertRaisesRegex(hp.PrincipalRejected,'userns_changed'):
                hp.broker_identity(spec())
    def test_untrusted_userns_fields_refused(self):
        for value in ('',None,123,'net:[4026531837]','user:[x]',
                      'user:[1]/../../root'):
            with self.subTest(value=value),self.assertRaises(hp.PrincipalRejected):
                hp.policy(spec()|{'hostUserNamespace':value})
    def test_wrong_broker_uid_refused(self):
        with patch.object(hp.os,'name','posix'),patch.object(hp.socket,'SO_PEERCRED',17,create=True),\
             patch.object(hp.os,'getuid',return_value=1000,create=True):
            with self.assertRaises(hp.PrincipalRejected):hp.broker_identity(spec())
    def test_broker_supplementary_groups_refused(self):
        with patch.object(hp.os,'name','posix'),patch.object(hp.socket,'SO_PEERCRED',17,create=True),\
             patch.object(hp.os,'getuid',return_value=65534,create=True),\
             patch.object(hp.os,'geteuid',return_value=65534,create=True),\
             patch.object(hp.os,'getgid',return_value=1000,create=True),\
             patch.object(hp.os,'getegid',return_value=1000,create=True),\
             patch.object(hp.os,'getgroups',return_value=[1000],create=True):
            with self.assertRaises(hp.PrincipalRejected):hp.broker_identity(spec())
    def test_gateway_is_distinct(self):
        with patch.object(hp.os,'name','posix'),\
             patch.object(hp.os,'getuid',return_value=1000,create=True),\
             patch.object(hp.os,'geteuid',return_value=1000,create=True),\
             patch.object(hp.os,'getgid',return_value=1000,create=True),\
             patch.object(hp.os,'getegid',return_value=1000,create=True):
            self.assertTrue(hp.gateway_identity(spec()))
    def test_gateway_wrong_uid_refused(self):
        with patch.object(hp.os,'name','posix'),patch.object(hp.os,'getuid',return_value=65534,create=True):
            with self.assertRaises(hp.PrincipalRejected):hp.gateway_identity(spec())
    def test_peer_cred_mismatch_refused(self):
        class Fake:
            def getsockopt(self,*args):return struct.pack('3i',41,1000,1000)
        with patch.object(hp.os,'name','posix'),patch.object(hp.socket,'SO_PEERCRED',17,create=True):
            self.assertEqual(hp.socket_peer(Fake(),spec(),role='broker'),
                             {'pid':41,'uid':1000,'gid':1000})
            with self.assertRaises(hp.PrincipalRejected):
                hp.socket_peer(Fake(),spec(),role='gateway')
    def test_peer_root_refused(self):
        class Fake:
            def getsockopt(self,*args):return struct.pack('3i',42,0,0)
        with patch.object(hp.os,'name','posix'),patch.object(hp.socket,'SO_PEERCRED',17,create=True):
            for role in ('broker','gateway'):
                with self.subTest(role=role),self.assertRaises(hp.PrincipalRejected):
                    hp.socket_peer(Fake(),spec(),role=role)
    def test_bad_role_refused(self):
        class Fake:pass
        with self.assertRaises(hp.PrincipalRejected):
            hp.socket_peer(Fake(),spec(),role='anything')

if __name__=='__main__':unittest.main()
