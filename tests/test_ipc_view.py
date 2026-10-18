"""Opt-in pathname mount-view contracts. No kernel or real model in discovery."""
import copy
import errno
from pathlib import Path
import stat
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'packages/claw-hermes'))
import combined_guard as combined
import ipc_view as ipc


def fs_policy():
    return {'version':1,'enabled':True,'readonly':['/usr','/owned/source'],
            'writable':['/owned/runtime','/dev/null'],
            'protected':['/owned/private/key']}


def ipc_policy():
    return {'version':1,'mode':'projected_root','root':'/tmp/alaz-ipc-test',
            'brokerSocket':'/owned/broker/egress.sock'}


class IPCContractTests(unittest.TestCase):
    def test_explicit_pinned_shape(self):
        value,fs=ipc.validate(ipc_policy(),fs_policy())
        self.assertEqual(value,ipc_policy())
        self.assertEqual(fs['protected'],['/owned/private/key'])

    def test_unknown_fields_and_fallback_refused(self):
        for extra in ({'allowFallback':True},{'extraSockets':[]},{'hostRoot':'/'}):
            with self.subTest(extra=extra),self.assertRaises(ipc.IPCViewRejected):
                ipc.validate(ipc_policy()|extra,fs_policy())

    def test_missing_fields_refused(self):
        for key in ipc_policy():
            value=ipc_policy();del value[key]
            with self.subTest(key=key),self.assertRaises(ipc.IPCViewRejected):
                ipc.validate(value,fs_policy())

    def test_version_must_be_integer_one(self):
        for value in (True,False,0,2,'1',None):
            with self.subTest(value=value),self.assertRaises(ipc.IPCViewRejected):
                ipc.validate(ipc_policy()|{'version':value},fs_policy())

    def test_only_projected_mode(self):
        for value in ('off','host','allow_all','',True):
            with self.subTest(value=value),self.assertRaises(ipc.IPCViewRejected):
                ipc.validate(ipc_policy()|{'mode':value},fs_policy())

    def test_canonical_paths_only(self):
        for value in ('relative','/a/../b','//server/share','/a//b','/a/','/a\0b'):
            with self.subTest(value=value),self.assertRaises(ipc.IPCViewRejected):
                ipc.canonical(value)

    def test_path_type_and_size(self):
        for value in (None,0,[],b'/x','', '/'+('x'*4097)):
            with self.subTest(kind=type(value).__name__),self.assertRaises(ipc.IPCViewRejected):
                ipc.canonical(value)

    def test_anchor_has_strict_owned_location(self):
        for value in ('/tmp','/tmp/foreign','/tmp/alaz-ipc-test/nested','/home/alaz-ipc-test'):
            with self.subTest(value=value),self.assertRaises(ipc.IPCViewRejected):
                ipc.validate(ipc_policy()|{'root':value},fs_policy())

    def test_socket_cannot_target_system_trees(self):
        for value in ('/proc/123/fd/7','/dev/socket/path','/usr/lib/private.sock','/etc/x/y.sock','/sys/x/y.sock'):
            with self.subTest(value=value),self.assertRaises(ipc.IPCViewRejected):
                ipc.validate(ipc_policy()|{'brokerSocket':value},fs_policy())

    def test_socket_length_enforced(self):
        with self.assertRaises(ipc.IPCViewRejected):
            ipc.validate(ipc_policy()|{'brokerSocket':'/owned/broker/'+('a'*95)},fs_policy())

    def test_anchor_under_export_refused(self):
        fs=fs_policy();fs['readonly'].append('/tmp/alaz-ipc-test')
        with self.assertRaisesRegex(ipc.IPCViewRejected,'root_overlap'):
            ipc.validate(ipc_policy(),fs)

    def test_export_inside_anchor_refused(self):
        fs=fs_policy();fs['readonly'].append('/tmp/alaz-ipc-test/source')
        with self.assertRaisesRegex(ipc.IPCViewRejected,'root_overlap'):
            ipc.validate(ipc_policy(),fs)

    def test_socket_under_runtime_not_a_whole_directory_grant(self):
        with self.assertRaisesRegex(ipc.IPCViewRejected,'socket_overlap'):
            ipc.validate(ipc_policy()|{'brokerSocket':'/owned/runtime/egress.sock'},fs_policy())

    def test_socket_under_readonly_grant_refused(self):
        with self.assertRaisesRegex(ipc.IPCViewRejected,'socket_overlap'):
            ipc.validate(ipc_policy()|{'brokerSocket':'/owned/source/egress.sock'},fs_policy())

    def test_filesystem_broad_grants_still_refused(self):
        fs=fs_policy();fs['readonly']=['/']
        with self.assertRaises(ValueError):ipc.validate(ipc_policy(),fs)

    def test_policy_not_mutated(self):
        raw=ipc_policy();fs=fs_policy();before=copy.deepcopy((raw,fs))
        ipc.validate(raw,fs)
        self.assertEqual((raw,fs),before)

    def test_nested_readonly_exports_rejected(self):
        fs=fs_policy();fs['readonly'].append('/usr/lib')
        with self.assertRaisesRegex(ipc.IPCViewRejected,'overlapping_exports'):
            ipc.validate(ipc_policy(),fs)

    def test_nested_writable_exports_rejected(self):
        fs=fs_policy();fs['writable'].append('/owned/runtime/sub')
        with self.assertRaisesRegex(ipc.IPCViewRejected,'overlapping_exports'):
            ipc.validate(ipc_policy(),fs)



class IPCScanTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);(self.root/'sub').mkdir()
        (self.root/'regular').write_text('source')

    def test_real_regular_tree_counted(self):
        count,hidden=ipc.inspect_tree(self.root)
        self.assertEqual(count,2);self.assertEqual(hidden,[])

    def test_scan_limit_is_a_failure_not_truncation(self):
        with patch.object(ipc,'MAX_ENTRIES',1),self.assertRaisesRegex(ipc.IPCViewRejected,'scan_limit'):
            ipc.inspect_tree(self.root)

    def test_fifo_or_socket_in_export_refused(self):
        original=Path.lstat
        for mode in (stat.S_IFIFO,stat.S_IFSOCK,stat.S_IFCHR,stat.S_IFBLK):
            def fake(p,mode=mode):
                info=original(p)
                if p.name=='regular':return SimpleNamespace(st_mode=mode,st_dev=info.st_dev)
                return info
            with self.subTest(mode=mode),patch.object(Path,'lstat',fake),self.assertRaisesRegex(ipc.IPCViewRejected,'special_file'):
                ipc.inspect_tree(self.root)

    def test_nested_directory_mount_is_masked_not_scanned(self):
        (self.root/'sub/hidden').write_text('never read')
        with patch.object(ipc.os.path,'ismount',side_effect=lambda p:Path(p).name=='sub'):
            count,hidden=ipc.inspect_tree(self.root)
        self.assertEqual(count,2);self.assertEqual(hidden,[str(self.root/'sub')])

    def test_incomplete_tree_scan_rejected(self):
        def failed(*args,**kwargs):
            kwargs['onerror'](PermissionError('owned test unreadable'))
            return iter(())
        with patch.object(ipc.os,'walk',side_effect=failed),self.assertRaisesRegex(ipc.IPCViewRejected,'tree_scan_incomplete'):
            ipc.inspect_tree(self.root)



class IPCCompositionTests(unittest.TestCase):
    def contract(self,enabled=True):
        command=['/usr/bin/python3','-B','owned.py']
        value={'version':1,'enabled':True,'launchId':'unit-ipc-test',
               'network':'loopback_only','filesystem':fs_policy(),
               'commandSha256':combined.command_digest(command)}
        if enabled:value['ipc']=ipc_policy()
        return value,command

    def fs_receipt(self):return {'state':'enforced','noNewPrivs':True,'protectedReadDenials':1}

    def net_receipt(self,projection=True):
        value={'mode':'linux_netns_loopback_only','after':{'pid':combined.os.getpid()}}
        if projection:value['filesystemView']={'state':'projected','oldRootDetached':True,'explicitHostSocketCount':1}
        return value

    def test_old_mode_retains_original_network_signature(self):
        value,command=self.contract(False)
        with patch.object(combined.network,'enter',return_value=self.net_receipt(False)) as net,patch.object(combined.filesystem,'apply',return_value=self.fs_receipt()):
            result=combined.enforce(value,command)
        net.assert_called_once_with()
        self.assertFalse(result['explicitBrokerMountOnly'])
        self.assertFalse(result['completeD3B'])

    def test_new_mode_binds_filesystem_and_socket_in_contract(self):
        value,command=self.contract()
        with patch.object(combined.network,'enter',return_value=self.net_receipt()) as net,patch.object(combined.filesystem,'apply',return_value=self.fs_receipt()):
            result=combined.enforce(value,command)
        supplied=net.call_args.kwargs['filesystem_view']
        self.assertEqual(supplied['ipc'],ipc_policy())
        self.assertEqual(supplied['filesystem']['protected'],fs_policy()['protected'])
        self.assertTrue(result['explicitBrokerMountOnly'])
        self.assertFalse(result['independentBrokerBudgetAuthority'])

    def test_missing_projection_receipt_refuses_filesystem_step(self):
        value,command=self.contract()
        with patch.object(combined.network,'enter',return_value=self.net_receipt(False)),patch.object(combined.filesystem,'apply') as fs,self.assertRaisesRegex(combined.CombinedGuardRejected,'ipc_receipt'):
            combined.enforce(value,command)
        fs.assert_not_called()

    def test_projection_failure_never_falls_back(self):
        value,command=self.contract()
        with patch.object(combined.network,'enter',side_effect=ipc.IPCViewRejected('mount_failed')) as net,patch.object(combined.filesystem,'apply') as fs,self.assertRaises(ipc.IPCViewRejected):
            combined.enforce(value,command)
        self.assertEqual(net.call_count,1);fs.assert_not_called()

    def test_wrong_command_refused_before_mount(self):
        value,command=self.contract()
        with patch.object(combined.network,'enter') as net,self.assertRaisesRegex(combined.CombinedGuardRejected,'command_mismatch'):
            combined.enforce(value,command+['different'])
        net.assert_not_called()

    def test_all_host_sockets_not_claimed_from_one_mount(self):
        value,command=self.contract()
        with patch.object(combined.network,'enter',return_value=self.net_receipt()),patch.object(combined.filesystem,'apply',return_value=self.fs_receipt()):
            result=combined.enforce(value,command)
        self.assertFalse(result['unixSocketAuthorityIsolated'])
        self.assertFalse(result['separateHostUid'])
        self.assertFalse(result['completeD3B'])


if __name__=='__main__':unittest.main(verbosity=2)
