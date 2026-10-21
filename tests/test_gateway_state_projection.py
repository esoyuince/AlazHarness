"""P102 contracts and orchestration; privileged boundaries are explicit doubles."""
from contextlib import ExitStack
from dataclasses import replace,FrozenInstanceError
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch,MagicMock
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'packages/claw-hermes'))
import gateway_state_projection as p
from state_image_lease import ImagePin


def binding():
    return p.VolumeBinding(ImagePin('/srv/test/images/state.img',100,20,65536,0,0,100,19),
        '/sys/fs/cgroup/test/volume-'+'a'*32,(23,50),'a'*32,10,100,11,110,1000,
        '/srv/test/volume',12,0,'b'*64)
P={'version':1,'enabled':True,'gatewayUid':23001,'brokerUid':23002,
   'socketGroupGid':23003,'hostUserNamespace':'user:[1]'}
V={'root':'/tmp/alaz-ipc-test','brokerSocket':'/srv/broker/egress.sock','principalContract':P}
FS={'version':1,'enabled':True,'readonly':['/usr/bin','/opt/owned'],
    'writable':['/dev/null','/srv/test/scratch'],'protected':['/srv/test/canary'],
    'self_process_metadata':True}


class Contracts(unittest.TestCase):
    def test_immutable_and_no_io(self):
        with patch.object(Path,'stat',side_effect=AssertionError('no io')):
            b=binding()
        with self.assertRaises(FrozenInstanceError):b.loop_number=2
    def test_non_root_image_rejected(self):
        with self.assertRaisesRegex(p.StateProjectionRejected,'root_image'):
            replace(binding(),image=replace(binding().image,uid=23001))
    def test_identity_bool_zero_float_rejected(self):
        for name in ('controller_pid','controller_start','worker_pid','worker_start','namespace_inode','profile_inode'):
            for value in (True,0,-1,1.0,2**64):
                with self.subTest(name=name,value=value),self.assertRaises(p.StateProjectionRejected):
                    replace(binding(),**{name:value})
    def test_scope_has_exact_token_and_parent(self):
        for value in ('/sys/fs/cgroup','/sys/fs/cgroup/volume-'+'a'*32,'/tmp/volume-'+'a'*32,
                      '/sys/fs/cgroup/test/volume-'+'b'*32):
            with self.subTest(value=value),self.assertRaises(p.StateProjectionRejected):replace(binding(),scope=value)
    def test_canonical_paths_reject_aliases(self):
        for value in ('srv/test','/srv//test','/srv/test/../other','/srv/./test','//srv/test','/srv/test\x00'):
            with self.subTest(value=value),self.assertRaises(p.StateProjectionRejected):p.canonical(value)
    def test_token_and_digest_bounds(self):
        for name,value in (('token','g'*32),('token','a'*31),('fence_sha256','b'*63),('fence_sha256','B'*64)):
            with self.subTest(name=name),self.assertRaises(p.StateProjectionRejected):replace(binding(),**{name:value})
    def test_scope_identity_must_be_immutable_positive_pair(self):
        for value in ([23,50],(0,1),(1,),(True,2)):
            with self.subTest(value=value),self.assertRaises(p.StateProjectionRejected):replace(binding(),scope_identity=value)
    def test_loop_bounds_and_same_pid(self):
        for value in (True,-1,65536,1.0):
            with self.subTest(value=value),self.assertRaises(p.StateProjectionRejected):replace(binding(),loop_number=value)
        with self.assertRaises(p.StateProjectionRejected):replace(binding(),worker_pid=10)
    def test_dictionary_not_authority(self):
        with self.assertRaisesRegex(p.StateProjectionRejected,'trusted_binding'):
            p.validate_exports({},V,FS)
    def test_adding_profile_does_not_mutate_original_policy(self):
        original={k:list(v) if isinstance(v,list) else v for k,v in FS.items()}
        out=p.validate_exports(binding(),V,FS)
        self.assertEqual(FS,original);self.assertIn(p.TARGET,out['writable'])
        self.assertNotIn(p.TARGET,FS['writable']);self.assertTrue(out['self_process_metadata'])
    def test_profile_and_source_overlaps_refused(self):
        for name in ('/run/alaz-state','/run/alaz-state/profile/x','/srv/test/volume',
                     '/srv/test','/srv/test/volume/profile/state.db'):
            with self.subTest(name=name),self.assertRaisesRegex(p.StateProjectionRejected,'overlap'):
                p.validate_exports(binding(),V,{**FS,'readonly':[name]})
    def test_broker_parent_overlap_refused(self):
        with self.assertRaisesRegex(p.StateProjectionRejected,'overlap'):
            p.validate_exports(binding(),{**V,'brokerSocket':'/run/alaz-state/b.sock'},FS)
    def test_dead_or_reused_pid_refused(self):
        with patch.object(p,'process_start',return_value=101),self.assertRaisesRegex(
            p.StateProjectionRejected,'process_changed'):p._live_root(10,100)
    def test_zombie_and_start_field(self):
        fields=['S']+['0']*18+['123']+['0']*4
        with patch.object(Path,'read_text',return_value='10 (name with ) spaces) '+' '.join(fields)):
            self.assertEqual(p.process_start(10),123)
        fields[0]='Z'
        with patch.object(Path,'read_text',return_value='10 (child) '+' '.join(fields)),self.assertRaises(
            p.StateProjectionRejected):p.process_start(10)


class Sequence(unittest.TestCase):
    def setUp(self):
        self.stack=ExitStack();self.addCleanup(self.stack.close);self.events=[]
        def mark(name,value=None):
            def effect(*a,**k):self.events.append(name);return value
            return effect
        self.b=binding();self.plan={'ipc':V,'filesystem':FS,'before':{'pid':os.getpid()}}
        self.inspector=self.stack.enter_context(patch.object(p.gp,'inspect',side_effect=mark('inspect',self.plan)))
        self.observed={'profile':(1,2,3,4,5,6,7,8,9)}
        self.volume=self.stack.enter_context(patch.object(p,'inspect_volume',side_effect=mark('volume',self.observed)))
        self.stack.enter_context(patch.object(p.gp.fs_guard,'kernel',return_value=object()))
        self.stack.enter_context(patch.object(p.gp.fs_guard,'abi_version',side_effect=mark('abi',3)))
        self.stack.enter_context(patch.object(p.gp.net,'_load_seccomp',side_effect=mark('loadfilter',object())))
        self.stack.enter_context(patch.object(p.os,'readlink',return_value='ns:[1]'))
        self.stack.enter_context(patch.object(p.gp.launch,'close_ambient_fds',side_effect=mark('closefds')))
        self.mounts=MagicMock();self.mounts.projected=True;self.mounts.unshare.side_effect=mark('unshare')
        self.stack.enter_context(patch.object(p,'_ProfileMounts',return_value=self.mounts))
        self.stack.enter_context(patch.object(p.gp,'_loopback_up',side_effect=mark('loopback')))
        self.project=self.stack.enter_context(patch.object(p.gp,'_project',side_effect=mark('project',7)))
        self.stack.enter_context(patch.object(Path,'lstat',return_value=object()))
        self.meta=self.stack.enter_context(patch.object(p,'_metadata',return_value=self.observed['profile']))
        self.stack.enter_context(patch.object(p.os,'umask',side_effect=mark('umask')))
        self.drop=self.stack.enter_context(patch.object(p.gp.launch,'drop_identity',side_effect=mark('drop')))
        self.stack.enter_context(patch.object(p.gp,'_verify_gateway',side_effect=mark('verifyids',{})))
        self.stack.enter_context(patch.object(p.gp.net,'_filter',side_effect=mark('filter')))
        self.filterstatus=self.stack.enter_context(patch.object(p.gp.net,'status',return_value={'Seccomp':'2'}))
        self.guard=self.stack.enter_context(patch.object(p.gp.fs_guard,'apply',side_effect=mark('landlock',{})))
    def run_enter(self):return p.enter(V,FS,self.b)
    def test_order_and_narrow_return(self):
        out=self.run_enter()
        self.assertEqual(self.events,['inspect','volume','abi','loadfilter','closefds','unshare',
            'loopback','project','umask','drop','verifyids','filter','closefds','landlock'])
        self.assertIn(p.TARGET,self.guard.call_args.args[0]['writable'])
        self.assertEqual(out['stateDirectoryCount'],1)
        for key in ('profileOwnershipAcquired','nativeHermesStoresOpened','realHermesGatewayTested',
                    'legacyIpcV2Activated','fullD3BAccepted'):self.assertIs(out[key],False)
    def test_rejected_volume_never_unshares_or_drops(self):
        self.volume.side_effect=p.StateProjectionRejected('fixture')
        with self.assertRaises(p.StateProjectionRejected):self.run_enter()
        self.mounts.unshare.assert_not_called();self.drop.assert_not_called();self.guard.assert_not_called()
    def test_overlap_fails_before_volume_probe(self):
        self.plan['filesystem']={**FS,'readonly':['/run/alaz-state']}
        with self.assertRaises(p.StateProjectionRejected):self.run_enter()
        self.volume.assert_not_called();self.mounts.unshare.assert_not_called()
    def test_failed_projection_does_not_start_security_drop_or_work(self):
        self.project.side_effect=p.gp.ProjectionRejected('fixture')
        with self.assertRaises(p.gp.ProjectionRejected):self.run_enter()
        self.drop.assert_not_called();self.guard.assert_not_called()
    def test_missing_profile_projection_rejected(self):
        self.mounts.projected=False
        with self.assertRaisesRegex(p.StateProjectionRejected,'not_projected'):self.run_enter()
        self.drop.assert_not_called()
    def test_final_profile_changed_rejected(self):
        self.meta.return_value=(9,)*9
        with self.assertRaisesRegex(p.StateProjectionRejected,'final_identity'):self.run_enter()
        self.drop.assert_not_called()
    def test_filter_missing_never_applies_guard_or_returns_success(self):
        self.filterstatus.return_value={'Seccomp':'0'}
        with self.assertRaisesRegex(p.StateProjectionRejected,'filter_missing'):self.run_enter()
        self.guard.assert_not_called()
    def test_landlock_failure_not_swallowed(self):
        self.guard.side_effect=p.gp.fs_guard.GuardRejected('fixture')
        with self.assertRaises(p.gp.fs_guard.GuardRejected):self.run_enter()

if __name__=='__main__':unittest.main()
