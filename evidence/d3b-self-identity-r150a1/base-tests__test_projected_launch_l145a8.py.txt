"""Fixed launcher control-flow contracts; kernel/exec/native stores explicitly doubled.
No test in this module is current kernel or active native-work acceptance.
"""
from contextlib import ExitStack
from dataclasses import asdict,replace
from pathlib import Path,PurePosixPath
from types import SimpleNamespace
import copy,hashlib,importlib.util,io,json,os,sys,unittest
from unittest.mock import Mock,patch
import test_retained_handoff_t143a7 as fixture
import test_gateway_state_projection as old
import gateway_retained_launch as l

class ExecTransferred(BaseException):pass

class Fixtures:
    def configure(self):
        fixture.HandoffContract.setUp(self)
        self.stack.enter_context(patch.object(l,'ROOT',PurePosixPath('/opt/owned')))
        self.stack.enter_context(patch.object(l.os,'makedev',side_effect=lambda a,b:1792+b,create=True))
        self.b=old.binding();self.principal=dict(old.P);self.ns={'user':'user:[1]','mnt':'mnt:[2]','net':'net:[3]','ipc':'ipc:[4]'}
        self.mount=l.mounts.ExpectedMount(40,(7,0),'/profile',l.handoff.TARGET,'ext4')
        self.projected={'version':1,'pid':os.getpid(),'stateDirectoryCount':1,
           'ambientHostDirectoriesBound':0,'hostUserNamespacePreserved':True,'legacyIpcV2Activated':False,
           'fullD3BAccepted':False,'state':'confined_state_profile','profile':l.handoff.TARGET,
           'profileLayout':l.state.NATIVE_RETAINED_LAYOUT,'retainedProjectionVerified':True,
           'persistentProfileProjected':True,'rootPrivilegesDropped':True,'profileOwnershipAcquired':False,
           'nativeHermesStoresOpened':False,'retainedProfile':self.receipt,'profileDevice':1792,'profileInode':12}
        self.context={'protocol':l.PROTOCOL,'pid':os.getpid(),'principal':self.principal,'namespaces':self.ns,
            'mount':asdict(self.mount),'scratch':'/srv/test/scratch','instanceId':'next-owner',
            'wireSha256':hashlib.sha256(self.raw).hexdigest()}
        self.env=l._environment(self.raw,self.context)
    def context_env(self,change):
        c=copy.deepcopy(json.loads(self.env[l.CONTEXT_ENV]));change(c)
        return {**self.env,l.CONTEXT_ENV:l._bytes(c).decode('ascii')}

class LaunchFlow(unittest.TestCase,Fixtures):
    def setUp(self):
        self.configure();self.events=[]
        self.validate=self.stack.enter_context(patch.object(l.state.gp,'validate',return_value=(old.V,copy.deepcopy(old.FS))))
        def enter(*a,**kw):self.events.append('projection');return self.projected
        self.enter=self.stack.enter_context(patch.object(l.state,'enter',side_effect=enter))
        self.stack.enter_context(patch.object(l,'_namespaces',return_value=self.ns))
        self.live=self.stack.enter_context(patch.object(l,'_live',side_effect=lambda *a:self.events.append('live')))
        self.mountfn=self.stack.enter_context(patch.object(l,'_mount',side_effect=lambda:(self.events.append('mount') or self.mount)))
        def exe(*a):self.events.append('exec');raise ExecTransferred()
        self.exe=self.stack.enter_context(patch.object(l.os,'execve',side_effect=exe))
    def invoke(self,**kw):
        return l.launch(old.V,old.FS,self.b,self.value,scratch=kw.pop('scratch','/srv/test/scratch'),instance_id=kw.pop('instance_id','next-owner'),**kw)
    def test_real_codec_links_projection_to_exact_exec_and_scrubbed_environment(self):
        with patch.dict(os.environ,{'UNRELATED_SECRET':'must-not-inherit','PYTHONPATH':'/evil','HOME':'/host'}),self.assertRaises(ExecTransferred):self.invoke()
        self.assertEqual(self.events,['projection','live','mount','exec'])
        args=self.exe.call_args.args;self.assertEqual(args[:2],(l.PYTHON,[l.PYTHON,'-I','-B','/opt/owned/'+l.ENTRY]))
        env=args[2];self.assertEqual(set(env),set(self.env));self.assertNotIn('UNRELATED_SECRET',env)
        self.assertEqual(l.handoff.decode_projected(env[l.WIRE_ENV].encode('ascii')),self.value)
        self.assertEqual(self.enter.call_args.kwargs,dict(observe_self_mount=True,profile_layout=l.state.NATIVE_RETAINED_LAYOUT,retained_profile=self.receipt))
        self.assertEqual(self.receipt.home,l.handoff.TARGET)
    def test_wrong_typed_record_refuses_before_projection(self):
        self.value=asdict(self.value)
        with self.assertRaises(l.ProjectedLaunchRejected):self.invoke()
        self.enter.assert_not_called();self.exe.assert_not_called()
    def test_same_or_invalid_instance_before_projection(self):
        for instance in ('prior-owner','',True,'a/b','x'*129):
            with self.subTest(instance=instance),self.assertRaises(l.ProjectedLaunchRejected):self.invoke(instance_id=instance)
        self.enter.assert_not_called()
    def test_scratch_must_be_explicit_private_export(self):
        for scratch in ('/dev/null','/tmp/foreign','/srv//test/scratch',l.handoff.TARGET):
            with self.assertRaises((l.ProjectedLaunchRejected,l.handoff.HandoffRejected)):self.invoke(scratch=scratch)
        self.enter.assert_not_called();self.exe.assert_not_called()
    def test_no_unexported_python_or_target(self):
        for readonly in (['/usr/bin'],['/opt/owned']):
            self.validate.return_value=(old.V,{**old.FS,'readonly':readonly})
            with self.assertRaisesRegex(l.ProjectedLaunchRejected,'readonly'):self.invoke()
        self.enter.assert_not_called();self.exe.assert_not_called()
    def test_projection_error_never_encodes_or_executes(self):
        self.enter.side_effect=RuntimeError('projection effect unknown')
        with patch.object(l.handoff,'encode_projected') as encode,self.assertRaises(RuntimeError):self.invoke()
        encode.assert_not_called();self.live.assert_not_called();self.exe.assert_not_called()
    def test_incomplete_projected_metadata_never_executes(self):
        self.projected['rootPrivilegesDropped']=False
        with self.assertRaises(l.handoff.HandoffRejected):self.invoke()
        self.live.assert_not_called();self.exe.assert_not_called()
    def test_wrong_live_identity_blocks_exec(self):
        self.live.side_effect=l.ProjectedLaunchRejected('not isolated')
        with self.assertRaises(l.ProjectedLaunchRejected):self.invoke()
        self.mountfn.assert_not_called();self.exe.assert_not_called()
    def test_wrong_mount_root_or_profile_device_blocks_exec(self):
        for mount in (replace(self.mount,root='/other'),replace(self.mount,mount_point='/other'),replace(self.mount,device=(7,1))):
            self.mountfn.side_effect=None;self.mountfn.return_value=mount
            with self.assertRaisesRegex(l.ProjectedLaunchRejected,'mount_identity'):self.invoke()
        self.exe.assert_not_called()
    def test_returning_exec_never_reported_as_success(self):
        self.exe.side_effect=None
        with self.assertRaisesRegex(l.ProjectedLaunchRejected,'exec_returned'):self.invoke()
        self.assertEqual(self.exe.call_count,1)
    def test_failed_exec_not_retried_or_replaced_by_direct_owner(self):
        self.exe.side_effect=OSError('exec failed')
        with self.assertRaises(OSError):self.invoke()
        self.assertEqual(self.exe.call_count,1);self.assertEqual(self.events[:3],['projection','live','mount'])

class ReceiveContracts(unittest.TestCase,Fixtures):
    def setUp(self):
        self.configure()
        self.stack.enter_context(patch.object(l,'sys',SimpleNamespace(platform='linux',flags=SimpleNamespace(isolated=1),dont_write_bytecode=True,executable=l.PYTHON)))
        self.live=self.stack.enter_context(patch.object(l,'_live'))
        self.mountfn=self.stack.enter_context(patch.object(l,'_mount',return_value=self.mount))
    def refuse(self,env):
        with self.assertRaises((l.ProjectedLaunchRejected,l.handoff.HandoffRejected)):l.receive(env)
    def test_real_fixed_codec_reconstructs_original_types_before_live_check(self):
        actual=l.receive(self.env);self.assertEqual(actual,(self.value,self.mount,'next-owner'))
        self.assertIs(type(actual[0]),l.handoff.RetainedStartup);self.assertEqual(self.live.call_count,1)
    def test_wrong_interpreter_or_not_isolated_before_payload(self):
        for key,value in (('platform','win32'),('executable','/tmp/python'),('dont_write_bytecode',False)):
            with patch.object(l.sys,key,value):self.refuse(self.env)
        with patch.object(l.sys,'flags',SimpleNamespace(isolated=0)):self.refuse(self.env)
        self.live.assert_not_called();self.mountfn.assert_not_called()
    def test_extra_or_missing_environment_never_reaches_live_or_mount(self):
        for env in ({**self.env,'PYTHONPATH':'/evil'},{k:v for k,v in self.env.items() if k!='LANG'},None):self.refuse(env)
        self.live.assert_not_called();self.mountfn.assert_not_called()
    def test_bound_payload_and_context_sizes_before_parse(self):
        for key,limit in ((l.WIRE_ENV,l.handoff.MAX_BYTES),(l.CONTEXT_ENV,l.MAX_CONTEXT)):
            for value in ('',True,'x'*(limit+1)):
                with self.subTest(key=key,value=str(value)[:10]):self.refuse({**self.env,key:value})
        self.live.assert_not_called()
    def test_invalid_wire_or_wrong_target_before_live(self):
        for raw in ('{','\xff','[]',' '+self.env[l.WIRE_ENV]):self.refuse({**self.env,l.WIRE_ENV:raw})
        wrong=replace(self.value,retained=replace(self.receipt,home='/other/profile'))
        raw=l.handoff.encode(wrong,expected_home='/other/profile')
        self.refuse({**self.env,l.WIRE_ENV:raw.decode('ascii')});self.live.assert_not_called()
    def test_context_duplicate_unknown_protocol_and_noncanonical_refused(self):
        raw=self.env[l.CONTEXT_ENV]
        for text in (raw[:-1]+',"pid":1}',' '+raw,raw+'\n','[]'):
            self.refuse({**self.env,l.CONTEXT_ENV:text})
        for fn in (lambda c:c.update(extra=1),lambda c:c.update(protocol='other'),lambda c:c.pop('pid')):self.refuse(self.context_env(fn))
        self.live.assert_not_called()
    def test_context_pid_and_hash_bound(self):
        for fn in (lambda c:c.update(pid=os.getpid()+1),lambda c:c.update(pid=True),lambda c:c.update(wireSha256='0'*64)):
            self.refuse(self.context_env(fn))
        self.live.assert_not_called()
    def test_namespace_shapes_and_user_policy_strict(self):
        for fn in (lambda c:c['namespaces'].update(net='mnt:[3]'),lambda c:c['namespaces'].pop('ipc'),lambda c:c['principal'].update(gatewayUid=True)):
            with self.assertRaises(Exception):l.receive(self.context_env(fn))
        self.live.assert_not_called()
    def test_environment_path_home_temp_must_equal_context(self):
        for key,val in (('PATH','/evil'),('HOME','/host'),('HERMES_HOME','/host'),('TMP','/evil'),('LANG','C')):
            self.refuse({**self.env,key:val})
        self.live.assert_not_called()
    def test_scratch_alias_and_profile_overlap_refused(self):
        for val in ('/','/dev/null',l.handoff.TARGET,l.handoff.TARGET+'/tmp','/run/alaz-state','/x//y'):
            self.refuse(self.context_env(lambda c:c.update(scratch=val)))
        self.live.assert_not_called()
    def test_malformed_mount_before_live(self):
        for fn in (lambda c:c['mount'].update(device=True),lambda c:c['mount'].update(mount_id=True),lambda c:c['mount'].update(extra=1),lambda c:c['mount'].update(root='/wrong')):
            self.refuse(self.context_env(fn))
        self.live.assert_not_called();self.mountfn.assert_not_called()
    def test_changed_mount_after_exec_refused(self):
        self.mountfn.return_value=replace(self.mount,mount_id=41)
        with self.assertRaisesRegex(l.ProjectedLaunchRejected,'changed_after_exec'):l.receive(self.env)
    def test_same_instance_or_mismatched_generation_refused(self):
        self.refuse(self.context_env(lambda c:c.update(instanceId='prior-owner')))
        self.live.assert_not_called()

class LiveReceiverChecks(unittest.TestCase,Fixtures):
    def setUp(self):
        self.configure();self.actor={'pid':os.getpid(),'uids':(23001,)*4,'gids':(23003,)*4,'groups':(),'threads':1,'nnp':1,
            'caps':{n:0 for n in l.state.gp.launch.CAPS},'userns':'user:[1]','uidMap':['0','0','4294967295'],'gidMap':['0','0','4294967295']}
        self.stack.enter_context(patch.object(l.state.gp.hp,'gateway_identity',return_value=True))
        self.observation=self.stack.enter_context(patch.object(l.state.gp.launch,'observation',return_value=self.actor))
        self.filter=self.stack.enter_context(patch.object(l.state.gp.net,'status',return_value={'Seccomp':'2'}))
        self.nsfn=self.stack.enter_context(patch.object(l,'_namespaces',return_value=self.ns))
    def invoke(self):return l._live(self.principal,self.ns,os.getpid())
    def test_correct_live_kernel_fields_pass_without_store_access(self):self.assertIsNone(self.invoke())
    def test_wrong_real_saved_uid_gid_groups_threads_or_nnp_refused(self):
        for key,value in (('uids',(0,)*4),('gids',(0,)*4),('groups',(23003,)),('threads',2),('nnp',0),('pid',os.getpid()+1)):
            with patch.dict(self.actor,{key:value}),self.assertRaises(l.ProjectedLaunchRejected):self.invoke()
    def test_any_remaining_capability_refused(self):
        for name in l.state.gp.launch.CAPS:
            with patch.dict(self.actor['caps'],{name:1}),self.assertRaises(l.ProjectedLaunchRejected):self.invoke()
    def test_wrong_userns_maps_or_changed_private_namespace_refused(self):
        for key,value in (('userns','user:[99]'),('uidMap',['0','23001','1']),('gidMap',['0','23003','1'])):
            with patch.dict(self.actor,{key:value}),self.assertRaises(l.ProjectedLaunchRejected):self.invoke()
        self.nsfn.return_value={**self.ns,'mnt':'mnt:[99]'}
        with self.assertRaises(l.ProjectedLaunchRejected):self.invoke()
    def test_live_filter_must_still_be_active(self):
        self.filter.return_value={'Seccomp':'0'}
        with self.assertRaisesRegex(l.ProjectedLaunchRejected,'live_filter'):self.invoke()

class TargetOwnerFlow(unittest.TestCase,Fixtures):
    def setUp(self):
        self.configure();self.events=[]
        import gateway_profile_lease as lease
        import gateway_store_startup as startup
        self.receiver=self.stack.enter_context(patch.object(l,'receive',side_effect=lambda env:(self.events.append('receive') or (self.value,self.mount,'next-owner'))))
        self.held=SimpleNamespace(finish=Mock(side_effect=lambda:self.events.append('lease-release')))
        self.reserve=self.stack.enter_context(patch.object(lease,'reserve_profile',side_effect=lambda *a:(self.events.append('lease') or self.held)))
        test=self
        class Owner:
            def __init__(self,*a,**kw):self.phase='NEW';self.args=a;self.kw=kw
            def start(self):test.events.append('start');self.phase='VERIFIED';return {'completedChecks':['six-fixture-checks']}
            def close(self):test.events.append('close');self.phase='CLOSED'
            def status(self):return {'callerLeaseMayBeReleased':self.phase=='CLOSED'}
            @property
            def expectation(self):
                if self.phase!='VERIFIED':raise startup.StoreStartupRejected('startup_not_verified')
                return replace(test.state,epoch=2,instance_id='next-owner')
        self.owner=Owner()
        self.constructor=self.stack.enter_context(patch.object(startup,'NativeStoreStartup',side_effect=lambda *a,**kw:self.construct(a,kw)))
    def construct(self,args,kwargs):self.events.append('constructor');self.owner.args=args;self.owner.kw=kwargs;return self.owner
    def test_original_owner_contract_snapshot_before_close_and_release(self):
        result=l.target_main()
        self.assertEqual(self.events,['receive','lease','constructor','start','close','lease-release'])
        self.assertEqual(result['epoch'],2);self.assertFalse(result['finiteWorkExecuted']);self.assertFalse(result['runtimeAdmissionAuthorized'])
        self.assertIs(self.owner.args[0],self.held);self.assertIs(self.owner.args[1],self.mount);self.assertIs(self.owner.args[2],self.state)
        self.assertEqual(self.owner.kw,dict(instance_id='next-owner',response_expected=self.reply,prepared_layout=True,retained_profile=self.receipt))
    def test_receive_failure_never_reserves_profile(self):
        self.receiver.side_effect=l.ProjectedLaunchRejected('invalid payload')
        with self.assertRaises(l.ProjectedLaunchRejected):l.target_main()
        self.reserve.assert_not_called();self.constructor.assert_not_called()
    def test_constructor_unknown_does_not_release_caller_lease(self):
        self.constructor.side_effect=RuntimeError('unknown constructor')
        with self.assertRaises(RuntimeError):l.target_main()
        self.held.finish.assert_not_called();self.assertEqual(self.events,['receive','lease'])
    def test_start_unknown_never_forces_close_or_release(self):
        self.owner.start=Mock(side_effect=RuntimeError('unknown epoch'))
        with self.assertRaises(RuntimeError):l.target_main()
        self.held.finish.assert_not_called();self.assertNotIn('close',self.events)
    def test_close_unknown_never_releases_lease_or_retries(self):
        self.owner.close=Mock(side_effect=RuntimeError('unknown close'))
        with self.assertRaises(RuntimeError):l.target_main()
        self.owner.close.assert_called_once();self.held.finish.assert_not_called()
    def test_no_false_success_when_owner_not_releasable(self):
        self.owner.status=lambda:{'callerLeaseMayBeReleased':False}
        with self.assertRaisesRegex(l.ProjectedLaunchRejected,'not_closeable'):l.target_main()
        self.held.finish.assert_not_called()

class OriginalThreeStoreOwner(unittest.TestCase):
    """Original owner/start/close code and real SQLite handles; cold/native boundaries doubled."""
    def setUp(self):
        import test_three_store_lifecycle_l113f6 as f
        self.f=f;f.ThreeStoreLifecycle.setUp(self)
        if sys.platform=='win32':self.stack.enter_context(patch.object(l.handoff.retained,'Path',PurePosixPath))
        self.held._home=Path(l.handoff.TARGET)
        self.expected=replace(self.expected,state_identity=(1792,21),replay_identity=(1792,22),epoch=1,instance_id='prior-owner')
        self.want=replace(self.want,response_identity=(1792,23))
        self.receipt=l.handoff.retained.RetainedProfileExpectation(l.handoff.retained.FEATURE,l.handoff.TARGET,(1792,12),((1792,21),(1792,22),(1792,23)),1,'prior-owner','c'*64)
        self.record=l.handoff.RetainedStartup(self.expected,self.want,self.receipt)
        self.mount=l.mounts.ExpectedMount(40,(7,0),'/profile',l.handoff.TARGET,'ext4')
        self.layout.side_effect=lambda *a,**kw:self.mark('layout',{'state.db':(1792,21),'runs_idempotency.db':(1792,22),'response_store.db':(1792,23)})
        self.epoch.side_effect=lambda *a,**kw:self.mark('epoch',2)
        self.stack.enter_context(patch.object(l,'receive',return_value=(self.record,self.mount,'next-owner')))
        self.reserve=self.stack.enter_context(patch.object(f.s.live.profiles,'reserve_profile',return_value=self.held))
        self.finish.side_effect=self.release
    def mark(self,name,result):self.events.append(name);return result
    def make_store(self,name):return self.f.existing.Lifecycle.make_store(self,name)
    def release(self):
        import sqlite3
        for store in self.created:
            with self.assertRaises(sqlite3.ProgrammingError):store._conn.execute('SELECT 1')
        self.events.append('release')
    def test_fixed_target_uses_original_owner_and_closes_all_three_before_lease(self):
        out=l.target_main()
        self.assertEqual(out['epoch'],2);self.assertEqual(len(out['completedChecks']),6)
        self.assertEqual(self.events[-4:],['close-response','close-replay','close-state','release'])
        self.assertEqual(len(self.created),3);self.assertEqual(self.epoch.call_count,1);self.assertEqual(self.finish.call_count,1)
        self.assertIs(self.layout.call_args.kwargs['retained'],self.receipt)
        self.assertFalse(out['runtimeAdmissionAuthorized']);self.assertFalse(out['finiteWorkExecuted'])
    def test_original_cold_refusal_does_not_open_database_or_release(self):
        self.pre.side_effect=self.f.s.preopen.PreopenRejected('unqualified schema')
        with self.assertRaises(self.f.s.StoreStartupRejected):l.target_main()
        self.native.assert_not_called();self.epoch.assert_not_called();self.finish.assert_not_called();self.assertEqual(self.created,[])
    def test_original_close_refusal_does_not_force_release(self):
        make=self.Response.side_effect
        def response(**kwargs):
            obj=make(**kwargs);obj.close.side_effect=RuntimeError('unknown original close');return obj
        self.Response.side_effect=response
        with self.assertRaises(self.f.s.StoreStartupRejected):l.target_main()
        self.finish.assert_not_called();self.assertEqual(self.created[2].close.call_count,1)
        self.created[0].close.assert_not_called();self.created[1].close.assert_not_called()
    def test_original_epoch_failure_is_not_retried(self):
        self.epoch.side_effect=RuntimeError('epoch commit effect unknown')
        with self.assertRaises(self.f.s.StoreStartupRejected):l.target_main()
        self.epoch.assert_called_once();self.finish.assert_not_called()
        for obj in self.created:obj.close.assert_not_called()

if __name__=='__main__':unittest.main()
