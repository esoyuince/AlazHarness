"""Independent native SessionStore borrowed-handle behavior, fresh Windows profiles.
No native method replacements; corruption/transaction cases affect own test data.
Not shared GatewayRunner/API bootstrap or full upstream test-suite acceptance.
"""
import argparse,hashlib,json,os,sys,tempfile,threading,unittest
from contextlib import contextmanager
from pathlib import Path

State=Store=Config=Rejected=Ownership=Registry=Constants=None
BASE=None
WATCH=None
CHECKS=[]
END=[]

def audit(event,args):
    if event in ('socket.connect','socket.bind','socket.getaddrinfo','subprocess.Popen','os.system'):
        raise PermissionError('s121s1_offline_native_test')
    if WATCH is not None:
        if event=='sqlite3.connect':
            WATCH['sqliteOpens']+=1
            raise AssertionError('new_sqlite_connection_inside_borrowed_operation')
        if event=='open' and isinstance(args[0],(str,bytes,os.PathLike)):
            name=Path(os.fsdecode(args[0])).name.lower()
            if name=='state.db' or name.startswith('state.db-') or name=='sessions.json':
                if name!='sessions.json' and WATCH.get('allowNativeMutationHeaderRead',False):
                    WATCH['nativeMutationHeaderReads']+=1
                else:
                    WATCH['rawDatabaseOrJsonOpens']+=1
                    raise AssertionError('raw_database_or_json_open_inside_borrowed_operation')

class IndependentSessionChecks(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='profile-',dir=BASE)
        self.home=Path(self.temp.name).resolve();os.environ['HERMES_HOME']=str(self.home)
        Ownership.reserve([self.home]);self.db=State(self.home/'state.db');self.facades=[]
        self.config=Config();self.config.multiplex_profiles=False;self.config.write_sessions_json=False
        self._watch_records=[]
    def tearDown(self):
        global WATCH
        WATCH=None
        # Fixture-owned rollback only to release data explicitly changed by the test.
        try:
            if self.db._conn is not None and self.db._conn.in_transaction:self.db._conn.rollback()
        except Exception:pass
        for f in reversed(self.facades):
            try:f.close_all_db_handles()
            except Rejected:pass  # explicit revoked-owner cases retain the facade until caller close
        self.db.close();Ownership.close()
        counts=Registry.stats();self.temp.cleanup()
        END.append({'case':self._testMethodName,'temporaryProfileRemoved':not self.home.exists(),
                    'profileReleased':not Ownership.homes,'registry':counts})
        self.assertEqual(counts,{'live_generations':0,'retired_generations':0,'total_refcounts':0})
        self.assertFalse(self.home.exists());self.assertFalse(Ownership.homes)
    @contextmanager
    def observed(self,*,readonly=True,allow_native_mutation_header_read=False):
        global WATCH
        before=self.db._conn.total_changes
        counts=Registry.stats();record={'case':self._testMethodName,'sqliteOpens':0,'rawDatabaseOrJsonOpens':0,'readonly':readonly,'allowNativeMutationHeaderRead':allow_native_mutation_header_read,'nativeMutationHeaderReads':0}
        WATCH=record
        try:yield
        finally:
            WATCH=None
            if readonly:self.assertEqual(self.db._conn.total_changes,before)
            self.assertEqual(Registry.stats(),counts)
            CHECKS.append(record)
    def make(self,**options):
        f=Store(self.home/'sessions',self.config,session_db=self.db,**options);self.facades.append(f);return f
    def test_constructor_reuses_caller_without_registry_or_directory(self):
        before={q.relative_to(self.home).as_posix() for q in self.home.rglob('*')}
        with self.observed():f=self.make()
        self.assertIs(f._db,self.db);self.assertFalse(f._db_handles)
        self.assertEqual({q.relative_to(self.home).as_posix() for q in self.home.rglob('*')},before)
        self.assertFalse(self.db._shared_registry_owned)
    def test_all_selection_routes_reuse_exact_handle(self):
        f=self.make()
        with self.observed():
            for selected in (f._db,f._routing_db,f._db_for_key('agent:main:api:owned'),f._db_for_key(None),f._db_for_session_id(None),f._open_session_db_for_active_scope(self.home/'state.db')):
                self.assertIs(selected,self.db)
    def test_readonly_routing_load_does_not_import_legacy_json(self):
        f=self.make();folder=self.home/'sessions';folder.mkdir(exist_ok=True);file=folder/'sessions.json';file.write_text('{"legacy":"should not import"}',encoding='utf-8');before=file.read_bytes()
        with self.observed():f._ensure_loaded()
        self.assertEqual(f._entries,{});self.assertTrue(f._loaded);self.assertEqual(file.read_bytes(),before)
    def test_direct_legacy_import_and_save_are_refused(self):
        f=self.make()
        with self.observed():
            for action in (lambda:f._import_legacy_sessions_json(False),lambda:f._save_sessions_json({})):
                with self.assertRaises(Rejected):action()
        self.assertFalse((self.home/'sessions/sessions.json').exists())
    def test_routing_write_failure_cannot_create_json_fallback(self):
        f=self.make();self.db._conn.execute('PRAGMA query_only=ON')
        try:
            with self.observed(allow_native_mutation_header_read=True):
                with self.assertRaises(Rejected):f._persist_routing_data({},1)
            self.assertFalse((self.home/'sessions/sessions.json').exists())
        finally:self.db._conn.execute('PRAGMA query_only=OFF')
    def test_missing_routing_schema_refused_without_json_import(self):
        f=self.make();self.db._conn.execute('DROP TABLE gateway_routing');self.db._conn.commit()
        with self.observed():
            with self.assertRaises(Rejected):f._ensure_loaded()
        self.assertFalse(f._loaded);self.assertFalse((self.home/'sessions/sessions.json').exists())
    def test_detach_only_facade_not_caller_connection_or_profile(self):
        f=self.make()
        with self.observed():f.close_all_db_handles();f.close_all_db_handles()
        self.assertEqual(self.db._conn.execute('SELECT 1').fetchone()[0],1);self.assertTrue(Ownership.owns(self.home))
        with self.assertRaises(Rejected):f._db
    def test_active_transaction_blocks_selection_and_detach_without_rollback(self):
        f=self.make();self.db._conn.execute('BEGIN IMMEDIATE')
        try:
            with self.observed():
                for fn in (lambda:f._db,f.close_all_db_handles):
                    with self.assertRaises(Rejected):fn()
            self.assertTrue(self.db._conn.in_transaction)
        finally:self.db._conn.rollback()
        self.assertIs(f._db,self.db)
    def test_constructor_refuses_existing_transaction_without_open(self):
        self.db._conn.execute('BEGIN IMMEDIATE')
        try:
            with self.observed():
                with self.assertRaises(Rejected):self.make()
            self.assertTrue(self.db._conn.in_transaction)
        finally:self.db._conn.rollback()
    def test_locked_state_is_not_waited_or_repaired(self):
        f=self.make();self.db._lock.acquire()
        try:
            with self.observed():
                with self.assertRaises(Rejected):f._db
            self.assertTrue(self.db._lock.locked())
        finally:self.db._lock.release()
        self.assertIs(f._db,self.db)
    def test_foreign_active_scope_never_falls_back(self):
        f=self.make();foreign=self.home/'foreign';token=Constants.set_hermes_home_override(foreign)
        try:
            with self.observed():
                for fn in (lambda:f._db,lambda:f._routing_db,lambda:f._db_for_key('agent:main:api:owned')):
                    with self.assertRaises(Rejected):fn()
            self.assertFalse(foreign.exists())
        finally:Constants.reset_hermes_home_override(token)
        self.assertIs(f._db,self.db)
    def test_foreign_explicit_path_and_profile_key_do_not_materialize(self):
        f=self.make();foreign=self.home/'foreign/state.db'
        with self.observed():
            for fn in (lambda:f._open_session_db_for_active_scope(foreign),lambda:f._db_for_key('agent:other:api:owned'),lambda:f._db_for_key('agent:main:')):
                with self.assertRaises(Rejected):fn()
        self.assertFalse(foreign.parent.exists())
    def test_wrong_sessions_directory_refused_before_open(self):
        with self.observed():
            with self.assertRaises(Rejected):Store(self.home/'other',self.config,session_db=self.db)
        self.assertFalse((self.home/'other').exists())
    def test_unowned_profile_refused_before_open(self):
        Ownership.close()
        with self.observed():
            with self.assertRaises(Rejected):self.make()
        self.assertEqual(self.db._conn.execute('SELECT 1').fetchone()[0],1)
    def test_reacquired_profile_handle_is_not_original_ownership(self):
        f=self.make();Ownership.close();Ownership.reserve([self.home])
        with self.observed():
            with self.assertRaises(Rejected):f._db
        self.assertTrue(Ownership.owns(self.home))
    def test_repinned_handle_setter_disabled(self):
        f=self.make()
        with self.observed():
            for value in (None,self.db):
                with self.assertRaises(Rejected):f._db=value
        self.assertIs(f._db,self.db)
    def test_changed_config_or_facade_path_rejected(self):
        f=self.make()
        for field,value in (('multiplex_profiles',True),('write_sessions_json',True)):
            old=getattr(self.config,field);setattr(self.config,field,value)
            try:
                with self.observed():
                    with self.assertRaises(Rejected):f._db
            finally:setattr(self.config,field,old)
        old=f.sessions_dir;f.sessions_dir=self.home/'other'
        try:
            with self.observed():
                with self.assertRaises(Rejected):f._db
        finally:f.sessions_dir=old
    def test_nonexclusive_or_json_enabled_constructor_not_coerced(self):
        for field,bad in (('multiplex_profiles',True),('write_sessions_json',True),('write_sessions_json',0)):
            old=getattr(self.config,field);setattr(self.config,field,bad)
            try:
                with self.observed():
                    with self.assertRaises(Rejected):self.make()
            finally:setattr(self.config,field,old)
    def test_generation_changed_refused_without_reset(self):
        f=self.make();old=self.db._conn.execute('PRAGMA application_id').fetchone()[0];new=old+1
        self.db._conn.execute('PRAGMA application_id='+str(new))
        try:
            with self.observed():
                with self.assertRaises(Rejected):f._db
            self.assertEqual(self.db._conn.execute('PRAGMA application_id').fetchone()[0],new)
        finally:self.db._conn.execute('PRAGMA application_id='+str(old))
    def test_extra_database_not_detached_by_guard(self):
        f=self.make();self.db._conn.execute("ATTACH ':memory:' AS other")
        try:
            with self.observed():
                with self.assertRaises(Rejected):f._db
            self.assertIn('other',[r[1] for r in self.db._conn.execute('PRAGMA database_list')])
        finally:self.db._conn.execute('DETACH other')
    def test_dirty_or_inflight_facade_not_silently_discarded(self):
        f=self.make()
        f._dirty_transcripts['fixture']=[{'role':'user','content':'owned fixture'}]
        with self.observed():
            with self.assertRaises(Rejected):f.close_all_db_handles()
        self.assertTrue(f._dirty_transcripts);f._dirty_transcripts.clear()
        f._inflight_sessions['fixture']=object()
        with self.observed():
            with self.assertRaises(Rejected):f.close_all_db_handles()
        self.assertTrue(f._inflight_sessions);f._inflight_sessions.clear()
        self.assertIs(f._db,self.db)
    def test_cross_thread_same_scope_reuses_caller_connection(self):
        f=self.make();result=[];done=threading.Event()
        def reader():
            try:result.append(f._db is self.db)
            except Exception as exc:result.append(type(exc).__name__)
            finally:done.set()
        with self.observed():
            thread=threading.Thread(target=reader);thread.start();self.assertTrue(done.wait(5));thread.join(5)
        self.assertEqual(result,[True]);self.assertFalse(thread.is_alive())
    def test_closed_state_is_not_reopened_or_cached(self):
        global WATCH
        f=self.make();self.db.close();record={'case':self._testMethodName,'sqliteOpens':0,'rawDatabaseOrJsonOpens':0,'readonly':True};WATCH=record
        try:
            for fn in (lambda:f._db,lambda:f._routing_db,f.close_all_db_handles):
                with self.assertRaises(Rejected):fn()
        finally:WATCH=None;CHECKS.append(record)
        self.assertFalse(f._db_handles)
    def test_default_constructor_keeps_separate_registry_path(self):
        f=Store(self.home/'sessions',Config());self.facades.append(f)
        self.assertIsNot(f._db,self.db);self.assertTrue(f._db._shared_registry_owned)
        self.assertEqual(Registry.stats()['total_refcounts'],1)
        f.close_all_db_handles();self.facades.remove(f)
        self.assertEqual(Registry.stats()['total_refcounts'],0)
        self.assertEqual(self.db._conn.execute('SELECT 1').fetchone()[0],1)

def main():
    global State,Store,Config,Rejected,Ownership,Registry,Constants,BASE
    parser=argparse.ArgumentParser();parser.add_argument('--native',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    native=args.native.resolve(strict=True);out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
    with tempfile.TemporaryDirectory(prefix='alaz-s121s1-suite-') as tmp:
        BASE=Path(tmp).resolve();import_home=BASE/'import-home';import_home.mkdir()
        os.environ.update(HERMES_HOME=str(import_home),HOME=str(BASE),USERPROFILE=str(BASE));sys.path.insert(0,str(native));sys.addaudithook(audit)
        from hermes_state import SessionDB
        from gateway.session import SessionStore
        from gateway.config import GatewayConfig
        from gateway.session_borrowed_state import BorrowedSessionRejected
        from gateway.runtime_ownership import process_ownership
        import hermes_state_registry,hermes_constants
        State,Store,Config,Rejected,Ownership,Registry,Constants=SessionDB,SessionStore,GatewayConfig,BorrowedSessionRejected,process_ownership,hermes_state_registry,hermes_constants
        suite=unittest.defaultTestLoader.loadTestsFromTestCase(IndependentSessionChecks)
        with (out/'tests.txt').open('x',encoding='utf-8',newline='\n') as stream:result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
        imports={}
        for mod in tuple(sys.modules.values()):
            path=getattr(mod,'__file__',None)
            if path:
                p=Path(path).resolve()
                if p.is_relative_to(native) and p.suffix=='.py':imports[p.relative_to(native).as_posix()]=hashlib.sha256(p.read_bytes()).hexdigest()
        report={'result':'PASS_NATIVE_BORROWED_SESSION_INDEPENDENT' if result.wasSuccessful() else 'FAIL','total':result.testsRun,
                'passed':result.testsRun-len({t.id() for t,_ in result.errors+result.failures})-len(result.skipped),
                'errors':len(result.errors),'failures':len(result.failures),'skipped':len(result.skipped),
                'errorIds':[t.id() for t,_ in result.errors],'failureIds':[t.id() for t,_ in result.failures],
                'nativeImports':imports,'qaSha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'checks':CHECKS,'caseEnd':END,
                'nativeMethodsReplaced':False,'sharedGatewayRunnerBootstrap':False,'apiListenerStarted':False,
                'fullIsolationTested':False,'upstreamFullSuiteRun':False,'providerCalls':0,'rootWslAction':False}
    report['temporaryRootRemoved']=not BASE.exists()
    (out/'result.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ('nativeImports','checks','caseEnd')}),flush=True)
    if not result.wasSuccessful():print((out/'tests.txt').read_text(encoding='utf-8')[-12000:],flush=True)
    return 0 if result.wasSuccessful() and report['temporaryRootRemoved'] else 1
if __name__=='__main__':raise SystemExit(main())
