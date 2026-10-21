"""Pure contracts/order tests. No native identity or namespace mutation here."""
from contextlib import ExitStack
from copy import deepcopy
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'packages/claw-hermes'))
import gateway_projection as gp
P={'version':1,'enabled':True,'gatewayUid':23001,'brokerUid':23002,
   'socketGroupGid':23003,'hostUserNamespace':'user:[4026531837]'}
V={'version':2,'mode':'projected_root_principal','root':'/tmp/alaz-ipc-g84e-test',
   'brokerSocket':'/srv/test/socket/egress.sock','principalContract':P}
FS={'version':1,'enabled':True,'readonly':['/usr'],'writable':['/srv/work/run','/dev/null'],
    'protected':['/srv/canary'],'self_process_metadata':True}

class Validation(unittest.TestCase):
    def test_valid_contract_is_detached(self):
        v=deepcopy(V);f=deepcopy(FS);a,b=gp.validate(v,f)
        v['principalContract']['gatewayUid']=91;f['readonly'].append('/opt/changed')
        self.assertEqual(a['principalContract'],P);self.assertEqual(b['readonly'],['/usr'])
    def test_v1_is_not_a_principal_projection(self):
        v={k:x for k,x in V.items() if k!='principalContract'}
        v.update(version=1,mode='projected_root')
        with self.assertRaisesRegex(gp.ProjectionRejected,'v2_required'):gp.validate(v,FS)
    def test_same_uid_rejected(self):
        with self.assertRaises(ValueError):gp.validate(V|{'principalContract':P|{'brokerUid':23001}},FS)
    def test_legacy_gate_stays_closed(self):
        with self.assertRaisesRegex(gp.ipc.IPCViewRejected,'not_integrated'):gp.ipc.prepare(V,FS)
    def test_metadata_opt_in_required(self):
        for value in (False,None):
            f=deepcopy(FS)
            if value is None:del f['self_process_metadata']
            else:f['self_process_metadata']=value
            with self.subTest(value=value),self.assertRaises(gp.ProjectionRejected):gp.validate(V,f)
    def test_parent_directory_cannot_be_exported(self):
        with self.assertRaises(Exception):gp.validate(V,FS|{'readonly':['/srv/test/socket']})
    def test_sibling_file_below_socket_parent_cannot_be_exported(self):
        with self.assertRaisesRegex(gp.ProjectionRejected,'parent_export_overlap'):
            gp.validate(V,FS|{'protected':['/srv/test/socket/config']})
    def test_proc_and_sys_cannot_enter_through_protected(self):
        for name in ('/proc/self/mem','/sys/kernel'):
            with self.subTest(name=name),self.assertRaises(gp.ProjectionRejected):
                gp.validate(V,FS|{'protected':[name]})
    def test_broad_opt_and_srv_export_refused(self):
        for path in ('/opt','/srv'):
            with self.subTest(path=path),self.assertRaises(Exception):
                gp.validate(V,FS|{'readonly':[path]})
    def test_real_workspace_required(self):
        with self.assertRaisesRegex(gp.ProjectionRejected,'workspace_required'):
            gp.validate(V,FS|{'writable':['/dev/null']})
    def test_unprivileged_refuses_before_path_access(self):
        with (patch.object(gp.launch,'controller',side_effect=RuntimeError('not_root')),
              patch.object(gp,'_path') as path,self.assertRaisesRegex(RuntimeError,'not_root')):
            gp.inspect(V,FS)
        path.assert_not_called()
    def test_controller_requires_mount_and_network_capabilities(self):
        with (patch.object(gp.launch,'controller',return_value={'caps':{'CapEff':0}}),
              patch.object(gp,'_path') as path,self.assertRaisesRegex(gp.ProjectionRejected,'controller_caps')):
            gp.inspect(V,FS)
        path.assert_not_called()
    def test_user_namespace_flag_is_never_requested(self):
        self.assertEqual(gp.PRIVATE_FLAGS,gp.ipc.NEWNS|gp.NEWNET|gp.NEWIPC)
        self.assertEqual(gp.PRIVATE_FLAGS & 0x10000000,0)

class Identity(unittest.TestCase):
    def states(self):
        before={'pid':120,'userns':P['hostUserNamespace'],'uidMap':['0','0','4294967295'],
                'gidMap':['0','0','4294967295']}
        after=before|{'uids':(23001,)*4,'gids':(23003,)*4,'groups':(),'threads':1,'nnp':1,
                      'caps':{k:0 for k in gp.launch.CAPS}}
        return before,after
    def verify(self,change=None,ns=None):
        before,after=self.states();after.update(change or {})
        with (patch.object(gp.hp,'gateway_identity',return_value=True),
              patch.object(gp.launch,'observation',return_value=after),
              patch.object(gp.os,'readlink',return_value=ns or 'new')):
            return gp._verify_gateway(P,before,{'mnt':'old','net':'old','ipc':'old'})
    def test_exact_gateway_state_accepted(self):self.assertEqual(self.verify()['uids'],(23001,)*4)
    def test_broker_identity_cannot_be_mislabeled_gateway(self):
        with self.assertRaises(gp.ProjectionRejected):self.verify({'uids':(23002,)*4})
    def test_saved_root_uid_is_rejected(self):
        with self.assertRaises(gp.ProjectionRejected):self.verify({'uids':(23001,23001,0,23001)})
    def test_supplementary_group_is_rejected(self):
        with self.assertRaises(gp.ProjectionRejected):self.verify({'groups':(23003,)})
    def test_each_retained_capability_is_rejected(self):
        for key in gp.launch.CAPS:
            with self.subTest(key=key),self.assertRaises(gp.ProjectionRejected):
                self.verify({'caps':{k:int(k==key) for k in gp.launch.CAPS}})
    def test_user_namespace_remap_is_rejected(self):
        with self.assertRaisesRegex(gp.ProjectionRejected,'host_identity_changed'):
            self.verify({'userns':'user:[99]'})
    def test_uid_mapping_change_is_rejected(self):
        with self.assertRaises(gp.ProjectionRejected):self.verify({'uidMap':['23001','23001','1']})
    def test_unchanged_mount_network_or_ipc_namespace_is_rejected(self):
        with self.assertRaisesRegex(gp.ProjectionRejected,'namespace_unchanged'):self.verify(ns='old')

class Order(unittest.TestCase):
    def run_enter(self,failed=None):
        events=[];v,f=gp.validate(V,FS)
        plan={'ipc':v,'filesystem':f,'before':{},'socket':{'socket':(1,2,23002,23003,0o660)}}
        class FakeMounts:
            def unshare(self):record('unshare')
        def record(name,result=None):
            events.append(name)
            if name==failed:raise RuntimeError('injected_'+name)
            return result
        with ExitStack() as stack:
            for obj,name,fn in (
                (gp,'inspect',lambda *a:record('inspect',plan)),
                (gp.fs_guard,'kernel',lambda:record('landlock_kernel','libc')),
                (gp.fs_guard,'abi_version',lambda *a:record('abi',3)),
                (gp.net,'_load_seccomp',lambda:record('load_filter','seccomp')),
                (gp.os,'readlink',lambda *a:'old'),
                (gp.launch,'close_ambient_fds',lambda:record('close_fds')),
                (gp,'Mounts',lambda:FakeMounts()),
                (gp,'_loopback_up',lambda:record('loopback')),
                (gp,'_project',lambda *a:record('project',8)),
                (gp.os,'umask',lambda *a:record('umask')),
                (gp.launch,'drop_identity',lambda p:record('drop_'+str(p['brokerUid']))),
                (gp,'_verify_gateway',lambda *a:record('verify',{})),
                (gp.net,'_filter',lambda *a:record('filter')),
                (gp.net,'status',lambda:{'Seccomp':'2'}),
                (gp.fs_guard,'apply',lambda *a:record('landlock',{'state':'enforced'}))):
                stack.enter_context(patch.object(obj,name,side_effect=fn))
            if failed:
                with self.assertRaisesRegex(RuntimeError,'injected_'+failed):gp.enter(V,FS)
                return events,None
            return events,gp.enter(V,FS)
    def test_mount_before_drop_and_filters_before_return(self):
        events,r=self.run_enter()
        self.assertEqual(events,['inspect','landlock_kernel','abi','load_filter','close_fds',
          'unshare','loopback','project','umask','drop_23001','verify','filter','close_fds','landlock'])
        self.assertEqual(r['hostWritableDirectoriesBound'],0)
        self.assertEqual(r['explicitHostSocketCount'],1)
        self.assertIs(r['fullD3BAccepted'],False)
        self.assertIs(r['legacyIpcV2Activated'],False)
    def test_any_setup_failure_prevents_later_steps(self):
        for name in ('inspect','abi','load_filter','unshare','loopback','project','drop_23001','verify','filter','landlock'):
            with self.subTest(name=name):
                events,result=self.run_enter(name)
                self.assertEqual(events[-1],name);self.assertIsNone(result)

if __name__=='__main__':unittest.main()
