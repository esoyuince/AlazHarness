"""R147 contract tests. Real observer/guard code, explicit file/kernel adapters.
No test installs Landlock, mounts a profile, starts an agent or reads real proc data.
"""
from contextlib import ExitStack
from pathlib import Path
from types import SimpleNamespace
import ctypes,inspect,stat,sys,unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'packages/claw-hermes'))
import credential_guard as g
import principal_launch as observer
import gateway_retained_launch as launcher
import gateway_state_projection as projection
import test_retained_projection_p142c6 as projection_fixture
import test_projected_launch_l145a8 as launch_fixture
import test_gateway_state_projection as old
PID=4242
BASE=tuple('/proc/'+str(PID)+'/'+n for n in ('stat','status','statm','cmdline'))+('/proc/stat',)
MAPS=('/proc/4242/uid_map','/proc/4242/gid_map')

def policy():
    return {'version':1,'enabled':True,'readonly':['/opt/test/readonly'],
        'writable':['/opt/test/scratch'],'protected':['/private/key.json'],
        'self_process_metadata':True}

class GuardAdapter:
    """Captures real apply() syscall rule construction; does not invoke a kernel."""
    def __init__(self):self.fdpaths={};self.rules=[];self.enforced=False;self.closed=[];self.nextfd=100
    def info(self,path):
        return SimpleNamespace(st_dev=1,st_ino=sum(path.encode())+1,
            st_mode=(stat.S_IFREG if path.startswith('/proc/') or path.endswith('.json') else stat.S_IFDIR)|0o600)
    def open(self,path,flags):
        path=str(path)
        if self.enforced and path=='/private/key.json':raise PermissionError(13,'explicit model denial')
        self.nextfd+=1;self.fdpaths[self.nextfd]=path;return self.nextfd
    def close(self,fd):self.closed.append(fd)
    def syscall(self,number,*args):
        num=number.value
        if num==444:return 3 if args[1].value==0 else 70
        if num==445:
            rule=ctypes.cast(args[2],ctypes.POINTER(g.PathRule)).contents
            self.rules.append((self.fdpaths[rule.parent_fd],rule.allowed_access));return 0
        if num==446:self.enforced=True;return 0
        raise AssertionError(num)
    def prctl(self,number,*args):return 1 if number==39 else 0
    def apply(self,identity=False,mount=True):
        adapter=self
        class FakePath:
            def __init__(self,p):self.path=str(p)
            def stat(self):return adapter.info(self.path)
        fakeos=SimpleNamespace(O_PATH=0x200000,O_CLOEXEC=0x80000,O_NOFOLLOW=0x20000,O_RDONLY=0,
            open=self.open,close=self.close,fstat=lambda fd:self.info(self.fdpaths[fd]),getpid=lambda:PID)
        options={'self_mount_metadata':mount}
        # Baseline lacks the option: exercise its ACTUAL unchanged apply/observer failure.
        if 'self_identity_metadata' in inspect.signature(g.apply).parameters:options['self_identity_metadata']=identity
        with patch.object(g,'kernel',return_value=self),patch.object(g,'_preflight',return_value=0),patch.object(g,'os',fakeos),patch.object(g,'Path',FakePath):
            return g.apply(policy(),**options)

class ObservationRegression(unittest.TestCase):
    def observe(self,allowed,cap=0):
        reads=[]
        status='\n'.join(['Uid: 23001 23001 23001 23001','Gid: 23003 23003 23003 23003','Groups:',
                         'NoNewPrivs: 1','Threads: 1']+[k+': '+format(cap,'x') for k in observer.CAPS])
        class ProcPath:
            def __init__(self,path):self.path=str(path)
            def read_text(self,*a,**k):
                name=self.path.replace('/proc/self/','/proc/4242/');reads.append(name)
                if name not in allowed:raise PermissionError(13,'explicit read-right model',name)
                if name.endswith('/status'):return status
                if name.endswith(('/uid_map','/gid_map')):return '0 0 4294967295'
                raise AssertionError(name)
        ns={'user':'user:[1]','mnt':'mnt:[2]','net':'net:[3]','ipc':'ipc:[4]'}
        with patch.object(observer,'sys',SimpleNamespace(platform='linux')),patch.object(observer,'Path',ProcPath),patch.object(observer,'os',SimpleNamespace(getpid=lambda:PID,readlink=lambda p:'user:[1]')), \
             patch.object(observer.platform,'system',return_value='Linux'),patch.object(observer.platform,'machine',return_value='x86_64'), \
             patch.object(launcher.state.gp.hp,'gateway_identity',return_value=None),patch.object(launcher,'_namespaces',return_value=ns), \
             patch.object(launcher.state.gp.net,'status',return_value={'Seccomp':'2'}),patch.object(launcher.os,'getpid',return_value=PID):
            self.assertIs(launcher.state.gp.launch.observation,observer.observation)
            launcher._live(old.P,ns,PID)
        return reads
    def test_selected_grants_allow_the_unmodified_observer_and_live_check(self):
        adapter=GuardAdapter();adapter.apply(identity=True)
        allowed={path for path,right in adapter.rules if right & (1<<2)}
        self.assertEqual(self.observe(allowed),['/proc/4242/status',*MAPS])
    def test_default_still_refuses_the_map_read(self):
        a=GuardAdapter();a.apply(identity=False)
        with self.assertRaises(PermissionError) as caught:self.observe({p for p,r in a.rules if r&(1<<2)})
        self.assertEqual(caught.exception.filename,MAPS[0])
    def test_one_map_is_not_enough(self):
        with self.assertRaises(PermissionError) as caught:self.observe(set(BASE)|{MAPS[0]})
        self.assertEqual(caught.exception.filename,MAPS[1])
    def test_allowed_maps_do_not_hide_nonzero_capabilities(self):
        with self.assertRaises(launcher.ProjectedLaunchRejected):self.observe(set(BASE)|set(MAPS),cap=1)

class MetadataContract(unittest.TestCase):
    def test_defaults_exactly_unchanged(self):
        self.assertEqual(g.self_metadata_paths(PID),BASE)
        self.assertEqual(g.self_metadata_paths(PID,mountinfo=True),BASE+('/proc/4242/mountinfo',))
    def test_selected_adds_only_two_fixed_self_files(self):
        self.assertEqual(g.self_metadata_paths(PID,identity_maps=True),BASE+MAPS)
        self.assertEqual(g.self_metadata_paths(PID,mountinfo=True,identity_maps=True),BASE+('/proc/4242/mountinfo',)+MAPS)
    def test_invalid_pid_or_boolean_rejected(self):
        for pid in (True,0,-1,1.0,'4242'):
            with self.subTest(pid=pid),self.assertRaises(g.GuardRejected):g.self_metadata_paths(pid,identity_maps=True)
        for value in (1,0,None,'true',[]):
            with self.subTest(value=value),self.assertRaises(g.GuardRejected):g.self_metadata_paths(PID,identity_maps=value)
    def test_apply_invalid_option_refuses_before_any_kernel(self):
        with patch.object(g,'kernel') as kernel:
            for value in (1,0,None,'true',[]):
                with self.subTest(value=value),self.assertRaises(g.GuardRejected):g.apply(policy(),self_identity_metadata=value)
        kernel.assert_not_called()
    def test_optin_requires_self_metadata_policy(self):
        for value in (False,None):
            p=policy()
            if value is None:p.pop('self_process_metadata')
            else:p['self_process_metadata']=value
            with patch.object(g,'kernel') as kernel,self.assertRaises(g.GuardRejected):g.apply(p,self_identity_metadata=True)
            kernel.assert_not_called()
    def test_no_json_knob_or_arbitrary_proc_allowlist(self):
        p=policy();p['self_identity_metadata']=True
        with self.assertRaises(g.GuardRejected):g.validate_policy(p)
        for path in ('/proc','/proc/4242','/proc/4242/uid_map','/proc/1/gid_map'):
            p=policy();p['readonly']=[path]
            with self.assertRaises(g.GuardRejected):g.validate_policy(p)
    def test_metadata_rules_only_read_file_current_pid(self):
        adapter=GuardAdapter();out=adapter.apply(identity=True)
        proc=[(p,r) for p,r in adapter.rules if p.startswith('/proc/')]
        self.assertEqual(proc,[(p,1<<2) for p in BASE+('/proc/4242/mountinfo',)+MAPS])
        self.assertEqual(out['metadataReadFileCount'],8);self.assertIs(out['selfIdentityMetadata'],True)
        self.assertEqual(set(MAPS),{p for p,r in proc if p.endswith(('_map'))})
        self.assertFalse(any(p in ('/proc','/proc/4242','/proc/1/uid_map','/proc/4242/environ','/proc/4242/mem','/proc/4242/fd','/proc/4242/exe') for p,r in proc))
    def test_old_digest_and_receipt_shape_preserved(self):
        for mount in (False,True):
            a=GuardAdapter();out=a.apply(identity=False,mount=mount)
            p=g.validate_policy(policy())
            if mount:p=p|{'self_mount_metadata':True}
            self.assertEqual(out['policySha256'],g.policy_digest(p));self.assertNotIn('selfIdentityMetadata',out)
            self.assertEqual(out['metadataReadFileCount'],6 if mount else 5)
    def test_enabled_digest_distinct_and_binds_both_options(self):
        digests=set()
        for mount in (False,True):
            a=GuardAdapter();out=a.apply(identity=True,mount=mount)
            p=g.validate_policy(policy())|{'self_identity_metadata':True}
            if mount:p=p|{'self_mount_metadata':True}
            self.assertEqual(out['policySha256'],g.policy_digest(p));digests.add(out['policySha256'])
            b=GuardAdapter();oldout=b.apply(identity=False,mount=mount)
            self.assertNotEqual(out['policySha256'],oldout['policySha256']);digests.add(oldout['policySha256'])
        self.assertEqual(len(digests),4)
    def test_missing_map_file_cannot_fall_back(self):
        a=GuardAdapter();original=a.open
        def denied(path,flags):
            if str(path)==MAPS[0]:raise PermissionError(13,'map missing')
            return original(path,flags)
        a.open=denied
        with self.assertRaises(PermissionError):a.apply(identity=True)
        self.assertFalse(a.enforced)

class ProjectionSelection(unittest.TestCase):
    setUp=projection_fixture.ProjectionSequence.setUp
    def test_selected_retained_path_forwards_two_true_flags(self):
        projection.enter(old.V,old.FS,self.b,profile_layout=projection.NATIVE_RETAINED_LAYOUT,
            retained_profile=self.r,observe_self_mount=True,observe_self_identity=True)
        self.assertEqual(self.guard.call_args.kwargs,{'self_mount_metadata':True,'self_identity_metadata':True})
    def test_old_default_modes_do_not_gain_new_flag(self):
        for layout in (projection.MINIMAL_LAYOUT,projection.NATIVE_STORE_LAYOUT,projection.NATIVE_RESPONSE_LAYOUT,projection.NATIVE_PREPARED_LAYOUT):
            projection.enter(old.V,old.FS,self.b,profile_layout=layout)
            self.assertEqual(self.guard.call_args.kwargs,{})
        projection.enter(old.V,old.FS,self.b,profile_layout=projection.NATIVE_RETAINED_LAYOUT,retained_profile=self.r,observe_self_mount=True)
        self.assertEqual(self.guard.call_args.kwargs,{'self_mount_metadata':True})
    def test_only_retained_and_mount_observed_can_select_identity(self):
        for layout in (projection.MINIMAL_LAYOUT,projection.NATIVE_STORE_LAYOUT,projection.NATIVE_RESPONSE_LAYOUT,projection.NATIVE_PREPARED_LAYOUT):
            with self.assertRaises(projection.StateProjectionRejected):projection.enter(old.V,old.FS,self.b,profile_layout=layout,observe_self_mount=True,observe_self_identity=True)
        with self.assertRaises(projection.StateProjectionRejected):
            projection.enter(old.V,old.FS,self.b,profile_layout=projection.NATIVE_RETAINED_LAYOUT,retained_profile=self.r,observe_self_identity=True)
        self.inspector.assert_not_called();self.guard.assert_not_called()
    def test_nonboolean_selection_fails_before_projection(self):
        for value in (1,0,None,'true'):
            with self.assertRaises(projection.StateProjectionRejected):projection.enter(old.V,old.FS,self.b,observe_self_identity=value)
        self.inspector.assert_not_called();self.guard.assert_not_called()

class LauncherSelection(unittest.TestCase):
    configure=launch_fixture.Fixtures.configure
    setUp=launch_fixture.LaunchFlow.setUp
    def test_only_existing_fixed_launcher_explicitly_requests_maps(self):
        with self.assertRaises(launch_fixture.ExecTransferred):
            launcher.launch(old.V,old.FS,self.b,self.value,scratch='/srv/test/scratch',instance_id='next-owner')
        self.assertIs(self.enter.call_args.kwargs['observe_self_identity'],True)
        self.assertIs(self.enter.call_args.kwargs['observe_self_mount'],True)
        self.assertEqual(self.enter.call_args.kwargs['profile_layout'],projection.NATIVE_RETAINED_LAYOUT)
        self.assertEqual(self.exe.call_args.args[0],launcher.PYTHON)

if __name__=='__main__':unittest.main()
