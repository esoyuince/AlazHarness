"""Unchanged native admission transaction controls, not borrowed activation.

Actual SessionDB, ownership, SessionAuthority guard and native SQL transactions.
The ordinary runner is an explicit flags-only fixture; no model/task execution.
"""
import argparse,hashlib,json,os,sys,tempfile,threading
from pathlib import Path
from types import SimpleNamespace

def main():
    p=argparse.ArgumentParser();p.add_argument('--native',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    native=a.native.resolve(strict=True);out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
    denied=[]
    def audit(event,args):
        if event in ('socket.connect','socket.bind','socket.getaddrinfo','subprocess.Popen','os.system'):
            denied.append(event);raise PermissionError('offline_native_admission_control')
    with tempfile.TemporaryDirectory(prefix='alaz-q128c6-gate-') as tmp:
        home=Path(tmp).resolve();os.environ.update(HERMES_HOME=str(home),HOME=str(home),USERPROFILE=str(home),APPDATA=str(home),LOCALAPPDATA=str(home))
        sys.path.insert(0,str(native));sys.addaudithook(audit)
        from hermes_state import SessionDB
        from gateway.session_authority import SessionAuthority
        from gateway.runtime_ownership import process_ownership
        import hermes_state_runtime as rt
        process_ownership.reserve([home]);db=SessionDB(home/'state.db');threads=[]
        try:
            epoch=rt.begin_runtime_epoch(db,instance_id='q128c6-original');db.create_session('owned-session','api_server')
            runner=SimpleNamespace(_draining=False)
            authority=SessionAuthority(runner,profile_id=str(home),instance_id='q128c6-original',db=db,epoch=epoch)
            def admit(name,extra=None):return rt.admit_session_input(db,epoch=epoch,principal_id='api',session_id='owned-session',request_id=name,payload={'text':name},_authorize_write=authority._admission_gate(extra))
            controls={};first=admit('accepted-before-drain');controls['original_guard_accepts_when_ordinary_authority_open']=first['status']=='queued'
            # Hold real Python DB mutex so another actual native writer cannot reach its transaction.
            before=db._conn.total_changes;started=threading.Event();result=[]
            def blocked():
                started.set()
                try:result.append(admit('blocked-before-guard'))
                except rt.RuntimeStoreError as exc:result.append(exc.reason)
            db._lock.acquire()
            try:
                t=threading.Thread(target=blocked);threads.append(t);t.start();assert started.wait(5)
                runner._draining=True;authority.retiring=True
            finally:db._lock.release()
            t.join(10);assert not t.is_alive();assert result==['runtime_draining']
            controls['drain_before_transaction_guard_refuses_new_row']=db._conn.execute("SELECT COUNT(*) FROM session_admissions WHERE request_id='blocked-before-guard'").fetchone()[0]==0
            controls['refused_new_write_has_no_sql_row_changes']=db._conn.total_changes==before
            same=admit('accepted-before-drain');controls['native_exact_replay_during_drain_is_read_only_identity']=same['admission_id']==first['admission_id'] and same['status']=='queued'
            try:rt.claim_session_input(db,epoch=epoch,session_id='owned-session',_guard=authority._admission_gate())
            except rt.RuntimeStoreError as exc:controls['native_claim_during_drain_refused']=exc.reason=='runtime_draining'
            else:controls['native_claim_during_drain_refused']=False
            # The accepted-write boundary is guard authorization, not when its async caller returns.
            runner._draining=False;authority.retiring=False;entered=threading.Event();release=threading.Event();result=[]
            def paused_authorize(conn):
                assert conn is db._conn and conn.in_transaction;entered.set()
                if not release.wait(10):raise TimeoutError('owned admission callback release missing')
            def passed_guard():
                try:result.append(admit('guard-before-drain',paused_authorize))
                except BaseException as exc:result.append({'error':type(exc).__name__})
            t=threading.Thread(target=passed_guard);threads.append(t);t.start()
            try:
                assert entered.wait(5);runner._draining=True;authority.retiring=True
                controls['writer_still_alive_after_drain_flag']=t.is_alive()
            finally:release.set()
            t.join(10);assert not t.is_alive();assert len(result)==1 and result[0].get('status')=='queued',result
            controls['authorized_inflight_write_commits_after_drain_flags']=result[0]['status']=='queued'
            rows=[tuple(r) for r in db._conn.execute('SELECT request_id,status FROM session_admissions ORDER BY seq')]
            controls['both_accepted_rows_remain_queued_not_replayed']=rows==[('accepted-before-drain','queued'),('guard-before-drain','queued')]
            controls['epoch_unchanged']=tuple(db._conn.execute('SELECT epoch,instance_id FROM runtime_epoch').fetchone())==(epoch,'q128c6-original')
            assert all(controls.values()),controls
        finally:
            for t in threads:t.join(12)
            assert not any(t.is_alive() for t in threads)
            db.close();process_ownership.close()
        imports={}
        for mod in tuple(sys.modules.values()):
            file=getattr(mod,'__file__',None)
            if file:
                q=Path(file).resolve()
                if q.is_relative_to(native) and q.suffix=='.py':imports[q.relative_to(native).as_posix()]=hashlib.sha256(q.read_bytes()).hexdigest()
        report={'result':'PASS_UNCHANGED_NATIVE_ADMISSION_GATE_CONTROL','controls':controls,'controlCount':len(controls),'actualNativeAdmissionGuardAndSql':True,'ordinaryRunnerFlagsOnlyFixture':True,'borrowedLifecycleActivated':False,'nativeMethodsReplaced':False,'admittedAgentOrTaskExecuted':False,'nativeSources':imports,'qaSha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'providerCalls':0,'rootWslAction':False,'deniedEvents':denied,'profileOwnershipReleased':not process_ownership.homes}
    report['temporaryProfileRemoved']=not home.exists();(out/'result.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ('nativeSources','deniedEvents')}),flush=True)
if __name__=='__main__':main()
