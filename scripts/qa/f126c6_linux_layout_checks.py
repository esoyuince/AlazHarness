"""Real POSIX fixture metadata checks of exact prepared-layout source.
Fresh ordinary-user temporary files only; no native runner or confinement rerun.
"""
from pathlib import Path
import hashlib,importlib.util,io,json,os,stat,sys,tempfile,unittest
LAYOUT=None;ROOT=None;DATA=None;RESULTS=[]
class RealLayout(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='case-',dir=ROOT);self.home=Path(self.temp.name);self.home.chmod(0o700)
        for name in sorted(LAYOUT.DIRECTORIES,key=lambda n:len(Path(n).parts)):(self.home/name).mkdir(mode=0o700)
        for name in LAYOUT.DATABASES|{'response_store.db'}:(self.home/name).write_bytes(b'0'*512)
        for name in LAYOUT.LOCKS:(self.home/name).write_bytes(b'')
        (self.home/'SOUL.md').write_bytes(DATA['soul'].encode())
        (self.home/'cache/schema_columns.json').write_text(json.dumps(DATA['cache']),encoding='utf-8')
        for p in self.home.rglob('*'):
            if p.is_file():p.chmod(0o600)
        self.args={'uid':os.getuid(),'gid':os.getgid(),'device':self.home.stat().st_dev,'include_response':True}
    def tearDown(self):
        self.temp.cleanup();self.assertFalse(self.home.exists())
    def check(self,**kw):return LAYOUT.inspect_profile(self.home,**(self.args|{'include_prepared':True}|kw))
    def pair(self):
        (self.home/'platforms').mkdir(mode=0o700);(self.home/'platforms/pairing').mkdir(mode=0o700)
    def test_fresh_profile_has_no_implicit_directory_creation(self):
        before={p.relative_to(self.home).as_posix() for p in self.home.rglob('*')};self.check()
        self.assertEqual(before,{p.relative_to(self.home).as_posix() for p in self.home.rglob('*')})
    def test_exact_pair_accepted_real_uid_gid_and_modes(self):
        self.pair();r=self.check();self.assertIn('platforms/pairing',r)
        for n in ('platforms','platforms/pairing'):
            s=(self.home/n).lstat();self.assertEqual((s.st_uid,s.st_gid,stat.S_IMODE(s.st_mode)),(23001,23003,0o700))
    def test_unchanged_default_refuses_pair(self):
        self.pair()
        with self.assertRaisesRegex(LAYOUT.NativeLayoutRejected,'unexpected_entry'):self.check(include_prepared=False)
    def test_parent_alone_refused(self):
        (self.home/'platforms').mkdir(mode=0o700)
        with self.assertRaisesRegex(LAYOUT.NativeLayoutRejected,'required_entry'):self.check()
    def test_group_readable_parent_or_leaf_refused(self):
        self.pair()
        for n in ('platforms','platforms/pairing'):
            p=self.home/n;p.chmod(0o750)
            try:
                with self.subTest(n=n),self.assertRaises(LAYOUT.NativeLayoutRejected):self.check()
                self.assertEqual(stat.S_IMODE(p.stat().st_mode),0o750)
            finally:p.chmod(0o700)
    def test_symlink_parent_refused_without_following(self):
        outside=ROOT/'outside';outside.mkdir(mode=0o700);(outside/'pairing').mkdir(mode=0o700)
        try:
            (self.home/'platforms').symlink_to(outside,target_is_directory=True)
            with self.assertRaises(LAYOUT.NativeLayoutRejected):self.check()
            self.assertEqual(list((outside/'pairing').iterdir()),[])
        finally:(outside/'pairing').rmdir();outside.rmdir()
    def test_symlink_leaf_refused(self):
        (self.home/'platforms').mkdir(mode=0o700);(self.home/'platforms/pairing').symlink_to(self.home/'pairing',target_is_directory=True)
        with self.assertRaises(LAYOUT.NativeLayoutRejected):self.check()
    def test_credential_payload_and_extra_platform_refused(self):
        self.pair()
        for n in ('platforms/pairing/.env','platforms/pairing/auth.json','platforms/discord','cache/scratch'):
            p=self.home/n;p.write_bytes(b'fixture-only');p.chmod(0o600)
            try:
                with self.subTest(n=n),self.assertRaisesRegex(LAYOUT.NativeLayoutRejected,'unexpected_entry'):self.check()
                self.assertEqual(p.read_bytes(),b'fixture-only')
            finally:p.unlink()
    def test_named_pipe_leaf_refused_without_opening(self):
        self.pair();p=self.home/'platforms/pairing/pipe';os.mkfifo(p,0o600)
        with self.assertRaisesRegex(LAYOUT.NativeLayoutRejected,'unexpected_entry'):self.check()
        self.assertTrue(stat.S_ISFIFO(p.lstat().st_mode))
    def test_wrong_requested_identity_not_normalized(self):
        self.pair()
        for kw in ({'uid':23002},{'gid':23004},{'device':self.home.stat().st_dev+1}):
            with self.subTest(kw=kw),self.assertRaises(LAYOUT.NativeLayoutRejected):self.check(**kw)

def main():
    global LAYOUT,ROOT,DATA
    assert os.environ.get('WSL_DISTRO_NAME')=='AlazHarness-D3B-P71C' and Path('/etc/alaz-p71c-lab-id').read_text().strip()=='AlazHarness-D3B-P71C'
    assert os.getresuid()==(23001,)*3 and os.getresgid()==(23003,)*3 and not Path('/mnt/c').exists()
    raw=sys.stdin.buffer.read(100001);assert len(raw)<=100000;input=json.loads(raw)
    source=input['layout'].encode();assert hashlib.sha256(source).hexdigest()==input['layoutSha256'];DATA=input['fixture']
    os.umask(0o077)
    with tempfile.TemporaryDirectory(prefix='alaz-f126c6-layout-') as temp:
        ROOT=Path(temp);module=ROOT/'qualified_layout.py';module.write_bytes(source)
        spec=importlib.util.spec_from_file_location('qualified_layout',module);LAYOUT=importlib.util.module_from_spec(spec);spec.loader.exec_module(LAYOUT)
        output=io.StringIO();r=unittest.TextTestRunner(stream=output,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(RealLayout))
        assert module.read_bytes()==source
        result={'result':'PASS_REAL_POSIX_FINITE_LAYOUT_ONLY' if r.wasSuccessful() else 'FAIL','total':r.testsRun,'errors':len(r.errors),'failures':len(r.failures),'skipped':len(r.skipped),'tests':output.getvalue(),'layoutSha256':input['layoutSha256'],'qaSha256':input['qaSha256'],'inputSha256':hashlib.sha256(raw).hexdigest(),'uid':list(os.getresuid()),'gid':list(os.getresgid()),'boundaryMethodsReplaced':False,'actualProfileFixtureFilesOnly':True,'rootUsed':False,'nativeRunnerExecuted':False,'fullConfinementRerun':False}
    result['temporaryRootRemoved']=not ROOT.exists();print(json.dumps(result),flush=True)
    return 0 if r.wasSuccessful() and result['temporaryRootRemoved'] else 1
if __name__=='__main__':raise SystemExit(main())
