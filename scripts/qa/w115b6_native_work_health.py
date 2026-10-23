"""Genuine native table/connection probes; producer inventory is an explicit fixture.
No worker process, HTTP endpoint, network, root, Linux query or model is started.
"""
import argparse,hashlib,json,os,sqlite3,sys,tempfile,time,unittest
from pathlib import Path
from dataclasses import replace
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'packages/claw-hermes'))
import gateway_work_health as policy
import gateway_work_health_reader as reader
WATCH=None
State=Replay=Response=Ownership=runtime=None
BASE=None
SCHEMAS=None

def audit(event,args):
    if event in ('socket.connect','socket.bind','socket.getaddrinfo','subprocess.Popen','os.system'):
        raise PermissionError('work_health_offline_probe')
    if WATCH is not None:
        if event=='sqlite3.connect':WATCH['connects']+=1
        if event=='open' and isinstance(args[0],(str,bytes,os.PathLike)) and str(args[0]).endswith(('.db','.db-wal','.db-shm','.db-journal')):WATCH['rawDatabaseOpens']+=1

def open_stores(home):
    os.environ['HERMES_HOME']=str(home);Ownership.reserve([home])
    state=State(home/'state.db');replay=Replay(str(home/'runs_idempotency.db'))
    response=Response(db_path=str(home/'response_store.db'),canonical_state=state)
    return state,replay,response

def close_stores(stores):
    for store in reversed(stores):store.close()
    Ownership.close()

class NativeWorkHealth(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='profile-',dir=BASE);self.addCleanup(self.temp.cleanup)
        self.home=Path(self.temp.name).resolve();self.stores=open_stores(self.home);self.addCleanup(close_stores,self.stores)
        self.state,self.replay,self.response=self.stores
        epoch=runtime.begin_runtime_epoch(self.state,instance_id='work-health-probe')
        self.state.create_session('session','api')
        store_id=self.state._conn.execute("SELECT value FROM main.state_meta WHERE key='store_instance_id'").fetchone()[0]
        self.identity=policy.RuntimeIdentity(store_id,epoch,'work-health-probe',os.getpid(),77)
        self.reader=reader.NativeWorkReader(*self.stores,self.identity,schema_hashes=SCHEMAS)
        self.monitor=policy.WorkHealthSession(self.identity)
    def admission(self,started=False,all_stores=False):
        row=runtime.admit_session_input(self.state,epoch=self.identity.epoch,principal_id='fixture',session_id='session',request_id='request',payload={'text':'owned fixture'})
        if started:row=runtime.claim_session_input(self.state,epoch=self.identity.epoch,session_id='session')
        claim=policy.LiveWork(row['admission_id'],'session',self.identity.epoch,row['generation'],'RUNNING' if started else 'QUEUED',True)
        if all_stores:
            outcome,_=self.replay.reserve('scope','key','a'*64,'run_owned',{'status':'running' if started else 'queued'},owner_pid=os.getpid(),owner_started=77)
            self.assertEqual(outcome,'created')
            self.response.bind_request_key('idem:owned','b'*64,model='fixture')
            self.response.bind_request_admission('idem:owned',row['admission_id'])
            claim=replace(claim,run_id='run_owned',response_key='idem:owned')
        return row,claim
    def capture(self,claims=()):
        global WATCH
        audit_result={'connects':0,'rawDatabaseOpens':0};traces=[];before=[s._conn.total_changes for s in self.stores]
        for s in self.stores:s._conn.set_trace_callback(traces.append)
        WATCH=audit_result
        try:snapshot=self.reader.capture(live_work=claims)
        finally:
            WATCH=None
            for s in self.stores:s._conn.set_trace_callback(None)
        self.assertEqual(audit_result,{'connects':0,'rawDatabaseOpens':0})
        self.assertEqual([s._conn.total_changes for s in self.stores],before)
        self.assertTrue(all(q.lstrip().startswith(('SELECT','PRAGMA')) for q in traces),traces)
        return snapshot
    def assess(self,claims=(),draining=False,storage_verified=True):
        rows=self.capture(claims)
        # Flags and live tasks are explicit TEST FIXTURES, not runtime verification.
        snapshot=policy.WorkSnapshot(rows.identity,rows.admissions,rows.runs,rows.responses,claims,
            rows.unresolved_workers,rows.captured_ns,1,1,True,storage_verified,False,draining,False)
        return self.monitor.observe(snapshot,now_ns=time.monotonic_ns(),max_age_ns=5_000_000_000).public()
    def test_idle_real_three_store_capture(self):self.assertEqual(self.assess()['state'],'IDLE')
    def test_committed_queued_native_admission_is_owned_busy(self):
        _,c=self.admission();self.assertEqual(self.assess((c,))['state'],'BUSY')
    def test_started_native_admission_is_owned_busy(self):
        _,c=self.admission(True);self.assertEqual(self.assess((c,))['state'],'BUSY')
    def test_three_native_record_families_match(self):
        _,c=self.admission(True,True);r=self.assess((c,));self.assertEqual(r['state'],'BUSY');self.assertEqual(r['ownedWorkCount'],1)
    def test_native_delegated_worker_is_explicitly_not_qualified(self):
        _,c=self.admission(True,True)
        runtime.register_worker_execution(self.state,epoch=self.identity.epoch,execution_id='worker',session_id='session',generation=c.generation,kind='compute',adoption_secret='s'*64)
        runtime.adopt_worker_execution(self.state,epoch=self.identity.epoch,execution_id='worker',session_id='session',generation=c.generation,adoption_secret='s'*64)
        self.assertEqual(self.assess((c,))['reason'],'delegated_worker_not_qualified')
    def test_settled_native_rows_require_explicit_owner_commit(self):
        row,c=self.admission(True,True)
        runtime.settle_session_input(self.state,epoch=self.identity.epoch,admission_id=row['admission_id'],generation=c.generation,outcome='completed')
        self.replay.update_status(c.run_id,{'status':'completed'})
        self.response._settle_terminal_admissions()
        with self.assertRaisesRegex(reader.WorkReadUnavailable,'transaction_active'):self.capture()
        self.assertTrue(self.response._conn.in_transaction)
        self.response._conn.commit()  # Explicit fixture-owned settlement, never by reader.
        self.assertEqual(self.assess()['state'],'IDLE')
    def test_unsettled_orphan_response_requires_recovery(self):
        self.response.bind_request_key('idem:orphan','c'*64)
        self.assertEqual(self.assess()['reason'],'unowned_unsettled_response')
    def test_live_settling_task_keeps_terminal_admission_visible(self):
        row,c=self.admission(True,True)
        runtime.settle_session_input(self.state,epoch=self.identity.epoch,admission_id=row['admission_id'],generation=c.generation,outcome='completed')
        owner=replace(c,phase='SETTLING')
        rows=self.capture((owner,));self.assertEqual(rows.admissions[0].status,'terminal')
        self.assertEqual(self.assess((owner,))['state'],'BUSY')
    def test_orphan_native_work_never_becomes_idle(self):
        self.admission();self.assertEqual(self.assess()['state'],'RECONCILE_REQUIRED')
    def test_unknown_is_not_automatic_recovery(self):
        row,c=self.admission(True)
        self.state._conn.execute("UPDATE main.session_admissions SET status='unknown' WHERE admission_id=?",(row['admission_id'],));self.state._conn.commit()
        self.assertEqual(self.assess((c,))['reason'],'admission_unknown_or_unsupported')
        self.assertEqual(self.state._conn.execute('SELECT status FROM main.session_admissions').fetchone()[0],'unknown')
    def test_temp_table_cannot_hide_pending_native_work(self):
        self.admission();self.state._conn.execute('CREATE TEMP TABLE session_admissions(dummy)')
        self.assertEqual(self.assess()['reason'],'unowned_admission')
    def test_epoch_change_refused_without_adoption(self):
        runtime.begin_runtime_epoch(self.state,instance_id='foreign-epoch')
        with self.assertRaisesRegex(reader.WorkReadRejected,'runtime_changed'):self.capture()
    def test_native_stale_generation_not_busy(self):
        _,c=self.admission(True)
        self.state._conn.execute('UPDATE main.sessions SET runtime_generation=99');self.state._conn.commit()
        self.assertEqual(self.assess((c,))['reason'],'stale_work_generation')
    def test_pid_reuse_tuple_mismatch_refused(self):
        _,c=self.admission(True,True)
        self.replay._conn.execute('UPDATE main.run_idempotency SET owner_started=88');self.replay._conn.commit()
        self.assertEqual(self.assess((c,))['reason'],'run_owner_process_mismatch')
    def test_replay_duplicate_json_keys_cannot_hide_running_status(self):
        _,c=self.admission(True,True)
        self.replay._conn.execute('UPDATE main.run_idempotency SET status_json=?',('{"status":"running","status":"completed"}',));self.replay._conn.commit()
        with self.assertRaisesRegex(reader.WorkReadRejected,'observation_invalid'):self.capture()
    def test_large_replay_json_bounded_before_transfer(self):
        _,c=self.admission(True,True)
        self.replay._conn.execute('UPDATE main.run_idempotency SET status_json=?',('x'*131073,));self.replay._conn.commit()
        with self.assertRaisesRegex(reader.WorkReadRejected,'observation_invalid'):self.capture()
    def test_malformed_replay_json_refused(self):
        self.admission(True,True)
        self.replay._conn.execute("UPDATE main.run_idempotency SET status_json='bad'");self.replay._conn.commit()
        with self.assertRaises(reader.WorkReadRejected):self.capture()
    def test_existing_transaction_not_rolled_back_or_queried(self):
        self.response._conn.execute('BEGIN IMMEDIATE')
        try:
            with self.assertRaisesRegex(reader.WorkReadUnavailable,'transaction_active'):self.capture()
            self.assertTrue(self.response._conn.in_transaction)
        finally:self.response._conn.rollback()
        self.assertEqual(self.assess()['state'],'IDLE')
    def test_existing_mutex_not_stolen(self):
        self.state._lock.acquire()
        try:
            with self.assertRaisesRegex(reader.WorkReadUnavailable,'mutex_busy'):self.capture()
            self.assertTrue(self.state._lock.locked())
        finally:self.state._lock.release()
    def test_reader_never_closes_caller_connections(self):
        self.capture()
        self.assertTrue(all(s._conn.execute('SELECT 1').fetchone()[0]==1 for s in self.stores));self.assertTrue(Ownership.owns(self.home))
    def test_schema_change_refused_without_repair(self):
        self.response._conn.execute('CREATE TABLE extra(x)')
        with self.assertRaises(reader.WorkReadRejected):self.capture()
        self.assertIsNotNone(self.response._conn.execute("SELECT name FROM sqlite_schema WHERE name='extra'").fetchone())
    def test_response_mapping_mismatch_is_not_healthy(self):
        _,c=self.admission(True,True)
        self.response._conn.execute("UPDATE main.response_admissions SET admission_id='foreign'");self.response._conn.commit()
        self.assertEqual(self.assess((c,))['reason'],'response_admission_mismatch')
    def test_worker_unknown_is_not_erased(self):
        _,c=self.admission(True)
        runtime.register_worker_execution(self.state,epoch=self.identity.epoch,execution_id='worker',session_id='session',generation=c.generation,kind='compute',adoption_secret='s'*64)
        self.state._conn.execute("UPDATE main.worker_executions SET status='unknown'");self.state._conn.commit()
        self.assertEqual(self.assess((c,))['reason'],'delegated_worker_not_qualified')


    def test_settled_run_and_response_retained_for_owner_settling(self):
        row,c=self.admission(True,True)
        runtime.settle_session_input(self.state,epoch=self.identity.epoch,admission_id=row['admission_id'],generation=c.generation,outcome='completed')
        self.replay.update_status(c.run_id,{'status':'completed'})
        self.response._settle_terminal_admissions();self.response._conn.commit()
        owner=replace(c,phase='SETTLING');rows=self.capture((owner,))
        self.assertEqual(len(rows.runs),1);self.assertTrue(rows.responses[0].settled)
        self.assertEqual(self.assess((owner,))['state'],'BUSY')
    def test_native_rows_do_not_prove_storage_or_liveness_flags(self):
        _,c=self.admission(True,True)
        self.assertEqual(self.assess((c,),storage_verified=False)['state'],'UNOBSERVABLE')
        self.assertFalse(hasattr(self.capture((c,)),'storage_verified'))
    def test_draining_is_latched_without_authorizing_release(self):
        _,c=self.admission(True,True)
        first=self.assess((c,),draining=True);self.assertEqual(first['state'],'DRAINING')
        later=self.assess((c,));self.assertEqual(later['state'],'DRAINING')
        self.assertFalse(later['storeReleaseAuthorized']);self.assertFalse(later['runtimeAdmissionAuthorized'])
    def test_inventory_overflow_not_truncated_into_health(self):
        self.response._conn.executemany('INSERT INTO response_keys(request_key,fingerprint,created_at) VALUES(?,?,?)',[(str(i),'a'*64,1) for i in range(257)])
        self.response._conn.commit()
        with self.assertRaisesRegex(reader.WorkReadUnavailable,'inventory_limit'):self.capture()
    def test_parameterized_owner_identity_does_not_change_query(self):
        _,c=self.admission(True,True)
        owner=replace(c,admission_id="x') OR 1=1 --",run_id="y') OR 1=1 --",response_key="z') OR 1=1 --")
        rows=self.capture((owner,));self.assertEqual(len(rows.admissions),1)
        self.assertNotEqual(rows.admissions[0].admission_id,owner.admission_id)
        self.assertEqual(self.assess((owner,))['state'],'RECONCILE_REQUIRED')


def main():
    global BASE,State,Replay,Response,Ownership,runtime,SCHEMAS
    parser=argparse.ArgumentParser();parser.add_argument('--native',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();native=args.native.resolve(strict=True);out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
    with tempfile.TemporaryDirectory(prefix='alaz-w115b6-') as temp:
        BASE=Path(temp).resolve();home=BASE/'schema-reference';home.mkdir()
        os.environ.update(HERMES_HOME=str(home),HOME=str(BASE),USERPROFILE=str(BASE));sys.path.insert(0,str(native));sys.addaudithook(audit)
        from hermes_state import SessionDB
        from gateway.platforms.api_server_run_idempotency import RunIdempotencyStore
        from gateway.platforms.api_server_response_store import ResponseStore
        from gateway.runtime_ownership import process_ownership
        import hermes_state_runtime
        State,Replay,Response,Ownership,runtime=SessionDB,RunIdempotencyStore,ResponseStore,process_ownership,hermes_state_runtime
        reference=open_stores(home)
        try:SCHEMAS=tuple(reader.live.schema_digest(s._conn) for s in reference)
        finally:close_stores(reference)
        suite=unittest.defaultTestLoader.loadTestsFromTestCase(NativeWorkHealth)
        with (out/'tests.txt').open('x',encoding='utf-8',newline='\n') as f:r=unittest.TextTestRunner(stream=f,verbosity=2).run(suite)
        imported={}
        for m in tuple(sys.modules.values()):
            file=getattr(m,'__file__',None)
            if file:
                p=Path(file).resolve()
                if p.is_relative_to(native) and p.suffix=='.py':imported[p.relative_to(native).as_posix()]=hashlib.sha256(p.read_bytes()).hexdigest()
        result={'result':'PASS_SCOPED_NATIVE_WORK_METADATA' if r.wasSuccessful() else 'FAIL','total':r.testsRun,'passed':r.testsRun-len({t.id() for t,_ in r.failures+r.errors})-len(r.skipped),'failures':len(r.failures),'errors':len(r.errors),'skipped':len(r.skipped),'failureIds':[t.id() for t,_ in r.failures],'errorIds':[t.id() for t,_ in r.errors],'nativeSources':imported,'schemasFromSeparatePreparedFixture':SCHEMAS,'nativeClassesMocked':False,'producerInventoryIsExplicitFixture':True,'storageVerificationIsFixture':True,'liveWorkerProcessesStarted':False,'httpStarted':False,'fullIsolationTested':False,'rootUsed':False,'providerCalls':0,'ownershipReleased':not Ownership.homes,
        'currentSources':{str(p.relative_to(ROOT)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'packages/claw-hermes/gateway_work_health.py',ROOT/'packages/claw-hermes/gateway_work_health_reader.py',Path(__file__))}}
    result['temporaryProfilesRemoved']=not BASE.exists()
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ('nativeSources','currentSources')}),flush=True)
    if not r.wasSuccessful():print((out/'tests.txt').read_text(encoding='utf-8')[-14000:],flush=True)
    return 0 if r.wasSuccessful() and result['temporaryProfilesRemoved'] and result['ownershipReleased'] else 1
if __name__=='__main__':raise SystemExit(main())
