"""Native-data compatibility of work health; live-owner inventory is EXPLICIT QA.

No HTTP collector, real agent task, mount or root acceptance is claimed. All
native data transitions use genuine native APIs except identified corruption
fixtures. Existing ProfileOwnership and existing owned temporary homes are reused.
"""
import argparse,hashlib,json,os,sys,tempfile,time,unittest
from dataclasses import replace
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'packages/claw-hermes'),str(Path(__file__).parent)]
import gateway_work_health as policy
import a112x7d_response_probe as fixture
Replay=None
WATCH=False
OBSERVATIONS=[]

def audit(event,args):
    if event in ('socket.connect','socket.bind','socket.getaddrinfo','subprocess.Popen','os.system'):
        raise PermissionError('b115w6_native_data_offline')
    if WATCH and event in ('sqlite3.connect','open'):
        raise AssertionError('policy_must_not_open_files_or_connections')

class NativeWorkPolicy(unittest.TestCase):
    restore_home=fixture.BorrowedResponseCases.restore_home
    make=fixture.BorrowedResponseCases.make
    def setUp(self):
        fixture.BorrowedResponseCases.setUp(self)
        self.replay=Replay(str(self.home/'runs_idempotency.db'));self.addCleanup(self.replay.close)
        self.response=self.make()
        # Fixture identity/liveness assertions are not an OS or live adapter proof.
        self.process_started=77
        self.expected=self.identity()
    def identity(self):
        store=self.state._conn.execute("SELECT value FROM main.state_meta WHERE key='store_instance_id'").fetchone()[0]
        epoch,instance=self.state._conn.execute('SELECT epoch,instance_id FROM main.runtime_epoch').fetchone()
        return policy.RuntimeIdentity(store,epoch,instance,os.getpid(),self.process_started)
    def snapshot(self,owners=(),**changes):
        admissions=tuple(policy.Admission(*tuple(r)) for r in self.state._conn.execute(
            'SELECT a.admission_id,a.target_session_id,a.status,a.owner_epoch,a.generation,s.runtime_generation '
            'FROM main.session_admissions a LEFT JOIN main.sessions s ON s.id=a.target_session_id ORDER BY a.seq').fetchmany(257))
        runs=tuple(policy.Run(*tuple(r)) for r in self.replay._conn.execute(
            'SELECT run_id,status_json,owner_pid,owner_started FROM main.run_idempotency ORDER BY run_id').fetchmany(257))
        responses=tuple(policy.ResponseIdentity(r[0],r[1],r[2] is not None) for r in self.response._conn.execute(
            'SELECT k.request_key,a.admission_id,k.settled_at FROM main.response_keys k '
            'LEFT JOIN main.response_admissions a ON a.request_key=k.request_key ORDER BY k.request_key').fetchmany(257))
        workers=self.state._conn.execute("SELECT COUNT(*) FROM main.worker_executions WHERE status!='terminal'").fetchone()[0]
        tx=any(c.in_transaction for c in (self.state._conn,self.replay._conn,self.response._conn))
        return replace(policy.WorkSnapshot(self.identity(),admissions,runs,responses,tuple(owners),workers,
            time.monotonic_ns(),1,1,True,True,tx,False,False),**changes)
    def assess(self,owners=(),wanted=policy.Health.BUSY,session=None,**changes):
        global WATCH
        s=self.snapshot(owners,**changes)
        before=tuple(c.total_changes for c in (self.state._conn,self.replay._conn,self.response._conn))
        WATCH=True
        try:
            if session is None:r=policy.assess(s,self.expected,now_ns=time.monotonic_ns(),max_age_ns=1_000_000_000)
            else:r=session.observe(s,now_ns=time.monotonic_ns(),max_age_ns=1_000_000_000)
        finally:WATCH=False
        self.assertEqual(before,tuple(c.total_changes for c in (self.state._conn,self.replay._conn,self.response._conn)))
        self.assertIs(r.state,wanted);self.assertFalse(r.public()['runtimeAdmissionAuthorized'])
        OBSERVATIONS.append({'case':self._testMethodName,'state':r.state.value,'reason':r.reason,
            'observedTaskInventoryIsFixture':True,'sqlChangesByPolicy':0,'noFileOrConnectionOpenByPolicy':True})
        return r
    def admit(self):
        return fixture.Runtime.admit_session_input(self.state,epoch=self.epoch,principal_id='owned',session_id='session',request_id='request',payload={'text':'owned offline data fixture'})
    def owner(self,a,phase,*,api=False):
        return policy.LiveWork(a['admission_id'],a['target_session_id'],a['owner_epoch'],a['generation'],phase,True,
            'run_owned' if api else None,'idem:owned' if api else None)
    def running(self):
        self.admit();return fixture.Runtime.claim_session_input(self.state,epoch=self.epoch,session_id='session')
    def bind_api(self,a,status='running'):
        self.assertEqual(self.replay.reserve('owned','key','f'*64,'run_owned',{'status':status},owner_pid=os.getpid(),owner_started=self.process_started)[0],'created')
        self.assertTrue(self.response.bind_request_key('idem:owned','a'*64));self.response.bind_request_admission('idem:owned',a['admission_id'])
    def finish(self,a):
        return fixture.Runtime.settle_session_input(self.state,epoch=self.epoch,admission_id=a['admission_id'],generation=a['generation'],outcome='completed')
    def test_real_empty_native_inventory_idle(self):self.assess(wanted=policy.Health.IDLE)
    def test_real_queue_generation_null_and_owned_busy(self):
        a=self.admit();self.assertIsNone(a['generation']);self.assess((self.owner(a,'QUEUED'),))
    def test_real_unowned_queue_requires_reconciliation(self):self.admit();self.assess(wanted=policy.Health.RECONCILE)
    def test_real_running_session_is_not_corruption(self):a=self.running();self.assess((self.owner(a,'RUNNING'),))
    def test_real_all_three_running_links_busy(self):
        a=self.running();self.bind_api(a);self.assess((self.owner(a,'RUNNING',api=True),))
    def test_real_complete_settlement_chain_to_idle(self):
        a=self.running();self.bind_api(a);self.assess((self.owner(a,'RUNNING',api=True),))
        self.finish(a);owner=self.owner(a,'SETTLING',api=True);self.assess((owner,))
        self.replay.update_status('run_owned',{'status':'completed'});self.assess((owner,))
        self.response._settle_terminal_admissions();self.response._conn.commit()
        self.assess((owner,));self.assess(wanted=policy.Health.IDLE)
    def test_real_dead_owner_does_not_get_rebuilt_from_rows(self):
        a=self.running();self.bind_api(a);self.assess((replace(self.owner(a,'RUNNING',api=True),task_alive=False),),wanted=policy.Health.RECONCILE)
    def test_native_new_epoch_cannot_inherit_previous_owner(self):
        a=self.running();owner=self.owner(a,'RUNNING');fixture.Runtime.begin_runtime_epoch(self.state,instance_id='new-owned')
        self.assess((owner,),wanted=policy.Health.RECONCILE)
    def test_native_unknown_after_explicit_fixture_recovery_not_replayable(self):
        a=self.running();epoch=fixture.Runtime.begin_runtime_epoch(self.state,instance_id='recovery-fixture')
        fixture.Runtime.recover_session_inputs(self.state,epoch=epoch);self.expected=self.identity()
        self.assess(wanted=policy.Health.RECONCILE)
        self.assertEqual(fixture.Runtime.get_session_admission(self.state,admission_id=a['admission_id'])['status'],'unknown')
    def test_real_response_transaction_not_rolled_back_by_observer(self):
        a=self.running();self.bind_api(a);owner=self.owner(a,'RUNNING',api=True);self.response._conn.execute('BEGIN IMMEDIATE')
        try:self.assess((owner,),wanted=policy.Health.UNOBSERVABLE);self.assertTrue(self.response._conn.in_transaction)
        finally:self.response._conn.rollback()
        self.assess((owner,))
    def test_real_partial_settlement_owner_gone_is_not_idle(self):
        a=self.running();self.bind_api(a);self.finish(a);self.replay.update_status('run_owned',{'status':'completed'})
        self.assess(wanted=policy.Health.RECONCILE)
    def test_real_worker_registry_not_disguised_as_idle(self):
        fixture.Runtime.register_worker_execution(self.state,epoch=self.epoch,execution_id='worker',session_id='session',generation=0,kind='compute',adoption_secret='a'*32)
        self.assess(wanted=policy.Health.RECONCILE)
    def test_real_pid_reuse_fixture_refused(self):
        a=self.running();self.bind_api(a)
        self.replay._conn.execute('UPDATE main.run_idempotency SET owner_started=88');self.replay._conn.commit()
        self.assess((self.owner(a,'RUNNING',api=True),),wanted=policy.Health.RECONCILE)
    def test_real_duplicate_json_fault_never_means_healthy(self):
        a=self.running();self.bind_api(a)
        self.replay._conn.execute('UPDATE main.run_idempotency SET status_json=?',('{"status":"running","status":"completed"}',));self.replay._conn.commit()
        self.assess((self.owner(a,'RUNNING',api=True),),wanted=policy.Health.UNOBSERVABLE)
    def test_real_temp_shadow_cannot_hide_main_pending(self):
        self.admit();self.state._conn.execute('CREATE TEMP TABLE session_admissions(admission_id TEXT,status TEXT)')
        self.assess(wanted=policy.Health.RECONCILE)
    def test_real_drain_does_not_turn_completed_owner_into_new_capacity(self):
        a=self.running();owner=self.owner(a,'RUNNING');session=policy.WorkHealthSession(self.expected)
        self.assess((owner,),draining=True,wanted=policy.Health.DRAINING,session=session)
        self.finish(a);self.assess(wanted=policy.Health.DRAINING,session=session)

def main():
    global Replay
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--native',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();native=args.native.resolve(strict=True);out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
    with tempfile.TemporaryDirectory(prefix='alaz-b115w6-native-') as tmp:
        temp=Path(tmp);fixture.BASE=temp;home=temp/'import-home';home.mkdir()
        os.environ.update(HERMES_HOME=str(home),HOME=str(temp),USERPROFILE=str(temp));sys.path.insert(0,str(native));sys.addaudithook(audit)
        from hermes_state import SessionDB
        from gateway.platforms.api_server_response_store import ResponseStore
        from gateway.platforms.api_server_response_state import CanonicalStateUnavailable
        from gateway.platforms.api_server_run_idempotency import RunIdempotencyStore
        from gateway.runtime_ownership import process_ownership
        import hermes_state_runtime
        fixture.State,fixture.Responses,fixture.BindingError,fixture.Ownership,fixture.Runtime=SessionDB,ResponseStore,CanonicalStateUnavailable,process_ownership,hermes_state_runtime
        Replay=RunIdempotencyStore
        suite=unittest.defaultTestLoader.loadTestsFromTestCase(NativeWorkPolicy)
        with (out/'tests.txt').open('x',encoding='utf-8',newline='\n') as stream:result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
        imports={}
        for mod in tuple(sys.modules.values()):
            f=getattr(mod,'__file__',None)
            if f:
                p=Path(f).resolve()
                if p.is_relative_to(native) and p.suffix=='.py':imports[p.relative_to(native).as_posix()]=hashlib.sha256(p.read_bytes()).hexdigest()
        report={'result':'PASS_NATIVE_DATA_MAPPING_ONLY' if result.wasSuccessful() else 'FAIL','total':result.testsRun,
                'passed':result.testsRun-len({t.id() for t,_ in result.errors+result.failures})-len(result.skipped),
                'errors':len(result.errors),'failures':len(result.failures),'skipped':len(result.skipped),
                'errorIds':[t.id() for t,_ in result.errors],'failureIds':[t.id() for t,_ in result.failures],
                'nativeImports':imports,'observations':OBSERVATIONS,'profileReleased':not process_ownership.homes,
                'policySha256':hashlib.sha256((ROOT/'packages/claw-hermes/gateway_work_health.py').read_bytes()).hexdigest(),
                'qaSha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                'fixtureSourceSha256':hashlib.sha256(Path(fixture.__file__).read_bytes()).hexdigest(),
                'realNativeDatabases':True,'nativeMethodsReplaced':False,'liveTaskInventoryIsTestFixture':True,
                'storageVerificationFlagIsFixture':True,'realAdapterCollectorTested':False,'healthyBusyHttpIntegrated':False,
                'kernelIsolationTested':False,'providerCalls':0,'rootOrWslAction':False}
    report['temporaryProfilesRemoved']=not temp.exists()
    (out/'result.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ('nativeImports','observations')}),flush=True)
    if not result.wasSuccessful():print((out/'tests.txt').read_text(encoding='utf-8')[-12000:],flush=True)
    return 0 if result.wasSuccessful() and report['temporaryProfilesRemoved'] and report['profileReleased'] else 1
if __name__=='__main__':raise SystemExit(main())
