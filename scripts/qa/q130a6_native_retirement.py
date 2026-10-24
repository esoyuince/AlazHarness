"""Independent memory retirement on real native objects, no full agent turn.

Reuse Q128's explicit native fixture only. Own cases are selected explicitly;
old28 cases are NOT silently counted again. Public native binding/admit/claim/
settle populate sessions; lifecycle gate and all runtime methods remain real.
"""
import asyncio,hashlib,json,sys,threading,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import q128c6_native_lifecycle_checks as fixture
RETIRE=[]

class RetirementCases(fixture.IndependentLifecycle):
    def make_bound(self,sid='s-owned',*,terminal=True):
        from gateway.session_api import bind_api_session
        if self.binding._stage=='PREPARED':self.activate()
        ref=self.call(bind_api_session,self.authority,sid)
        self.state.append_message(sid,'user','retained native transcript '+sid)
        row=fixture.RT.admit_session_input(self.state,epoch=self.epoch,principal_id='api',session_id=sid,request_id='request-'+sid,payload={'text':'fixture'},_authorize_write=self.authority._admission_gate())
        if terminal:
            claim=fixture.RT.claim_session_input(self.state,epoch=self.epoch,session_id=sid,_guard=self.authority._admission_gate())
            fixture.RT.settle_session_input(self.state,epoch=self.epoch,admission_id=row['admission_id'],generation=claim['generation'],outcome='completed',result={'final_response':'leaf result','messages':[]})
        return ref,row,self.authority.sessions[sid]
    def retire(self):return self.call(self.bundle.retire_idle_api_sessions)
    def durable_snapshot(self):
        return tuple(hashlib.sha256('\n'.join(c.iterdump()).encode()).hexdigest() for c in self.connections)
    def reject(self):
        sessions=dict(self.authority.sessions);entries=dict(self.runner.session_store._entries);before=self.durable_snapshot()
        with self.watched(),self.assertRaises((fixture.Reject,fixture.RunnerReject)):self.retire()
        self.assertEqual(self.authority.sessions,sessions);self.assertEqual(self.runner.session_store._entries,entries)
        self.assertEqual(self.durable_snapshot(),before);self.assert_open();self.assertEqual(self.binding._stage,'DRAINING')
    def test_review_pending_native_reply_survives_failed_retirement(self):
        from gateway.session_ingress import waiter_replies
        self.make_bound();self.drain();replies=waiter_replies(self.authority);token=object();replies['held-reply']=token
        try:self.reject();self.assertIs(replies['held-reply'],token)
        finally:replies.clear()
    def test_review_memory_turn_marker_retains_exact_session(self):
        _,_,live=self.make_bound();self.drain();entry=self.runner.session_store._entries[live.route];old=entry.active_turn_token;entry.active_turn_token='unresolved-owned-token'
        try:self.reject();self.assertEqual(entry.active_turn_token,'unresolved-owned-token')
        finally:entry.active_turn_token=old
    def test_review_persisted_turn_marker_is_never_erased_or_relearned(self):
        _,_,live=self.make_bound();self.drain();c=self.state._conn;original=c.execute("SELECT entry_json FROM gateway_routing WHERE scope='' AND session_key=?",(live.route,)).fetchone()[0]
        data=json.loads(original);data['active_turn_started_at']='unresolved-owned-time';changed=json.dumps(data)
        c.execute("UPDATE gateway_routing SET entry_json=? WHERE scope='' AND session_key=?",(changed,live.route));c.commit()
        try:self.reject();self.assertEqual(c.execute("SELECT entry_json FROM gateway_routing WHERE scope='' AND session_key=?",(live.route,)).fetchone()[0],changed)
        finally:c.execute("UPDATE gateway_routing SET entry_json=? WHERE scope='' AND session_key=?",(original,live.route));c.commit()
    def test_review_live_profile_change_is_not_retired_as_original(self):
        _,_,live=self.make_bound();self.drain();original=live.source.profile;live.source.profile='other-owned-context'
        try:self.reject();self.assertEqual(live.source.profile,'other-owned-context')
        finally:live.source.profile=original
    def test_terminal_history_retry_and_route_persist_while_only_memory_retires(self):
        ref,row,live=self.make_bound();self.drain();before=self.durable_snapshot();route=live.route;store=self.runner.session_store
        maps=(self.authority.sessions,store._entries,store._session_owner_hints)
        with self.watched():r=self.retire()
        self.assertEqual(r['state'],'IDLE_API_SESSIONS_RETIRED');self.assertEqual(r['retiredCount'],1)
        self.assertEqual(self.durable_snapshot(),before);self.assertIs(self.authority.sessions,maps[0]);self.assertIs(store._entries,maps[1]);self.assertIs(store._session_owner_hints,maps[2])
        self.assertNotIn(ref.session_id,self.authority.sessions);self.assertNotIn(route,store._entries)
        self.assertEqual(fixture.RT.get_session_admission(self.state,admission_id=row['admission_id'])['status'],'terminal')
        self.assertIsNotNone(self.state.get_session(ref.session_id));self.assertGreater(self.state._conn.execute('SELECT COUNT(*) FROM messages').fetchone()[0],0)
        replay=fixture.RT.admit_session_input(self.state,epoch=self.epoch,principal_id='api',session_id=ref.session_id,request_id='request-'+ref.session_id,payload={'text':'fixture'},_authorize_write=self.authority._admission_gate())
        self.assertEqual(replay['admission_id'],row['admission_id']);self.assertEqual(self.durable_snapshot(),before)
        with self.watched():self.finish();fixture.LOOP.run_until_complete(self.api.disconnect());self.runner.close_all_session_db_handles()
        self.assert_open();RETIRE.append({'case':self._testMethodName,'retired':1,'allThreeDatabaseDumpsUnchanged':True,'nativeRetryIdentityRetained':True,'callerConnectionsAndProfileRemainOpen':True})
    def test_two_sessions_are_preflighted_all_before_any_memory_removal(self):
        self.make_bound('s-first');_,_,bad=self.make_bound('s-second');self.drain();bad.subscribers['held']=object()
        try:self.reject();self.assertEqual(len(self.authority.sessions),2)
        finally:bad.subscribers.clear()
        with self.watched():r=self.retire()
        self.assertEqual(r['retiredCount'],2)
    def test_no_implicit_retirement_by_finish_and_wrong_phase_refuses(self):
        with self.assertRaises((fixture.Reject,fixture.RunnerReject)):self.retire()
        self.make_bound()
        with self.assertRaises((fixture.Reject,fixture.RunnerReject)):self.retire()
        self.drain()
        with self.watched(),self.assertRaises((fixture.Reject,fixture.RunnerReject)):self.finish()
        self.assertEqual(len(self.authority.sessions),1);self.retire();self.finish()
        with self.assertRaises((fixture.Reject,fixture.RunnerReject)):self.retire()
    def test_empty_retirement_in_draining_is_readonly_and_not_finish(self):
        self.activate();self.drain()
        with self.watched():a=self.retire();b=self.retire()
        self.assertEqual((a['retiredCount'],b['retiredCount']),(0,0));self.assertEqual(self.binding._stage,'DRAINING');self.assertFalse(a['drainFinished'])
    def test_queued_and_unknown_rows_are_not_cleared_to_retire(self):
        _,row,_=self.make_bound(terminal=False);self.drain();self.reject()
        self.state._conn.execute("UPDATE session_admissions SET status='unknown' WHERE admission_id=?",(row['admission_id'],));self.state._conn.commit();self.reject()
        self.assertEqual(fixture.RT.get_session_admission(self.state,admission_id=row['admission_id'])['status'],'unknown')
    def test_each_store_transaction_preserved_on_refusal(self):
        self.make_bound();self.drain()
        for c in self.connections:
            c.execute('BEGIN IMMEDIATE')
            try:self.reject();self.assertTrue(c.in_transaction)
            finally:c.rollback()
    def test_live_native_dispatcher_must_end_without_cancellation(self):
        _,_,live=self.make_bound();event,task=self.pending();live.task=task;self.drain()
        try:self.reject();self.assertFalse(task.cancelled());self.assertFalse(task.done())
        finally:self.complete(event,task)
        # The task returned True, not the native dispatcher's expected None.
        self.reject();live.task=None;self.retire()
    def test_successful_done_dispatcher_is_permitted_but_cancelled_is_not(self):
        _,_,live=self.make_bound();event,task=self.pending();live.task=task
        async def cancel():
            task.cancel()
            with self.assertRaises(asyncio.CancelledError):await task
        fixture.LOOP.run_until_complete(cancel());self.drain();self.reject()
        async def done():return None
        live.task=fixture.LOOP.create_task(done());fixture.LOOP.run_until_complete(live.task);self.retire()
    def test_real_physical_thread_retained_after_cancelled_carrier(self):
        _,_,live=self.make_bound();entered=threading.Event();release=threading.Event();done=threading.Event();self.releases.append(release)
        def body():
            entered.set()
            try:release.wait(15)
            finally:done.set()
        async def start():return asyncio.create_task(asyncio.to_thread(body))
        task=fixture.LOOP.run_until_complete(start())
        async def cancel():
            for _ in range(1000):
                if entered.is_set():break
                await asyncio.sleep(.002)
            self.assertTrue(entered.is_set());task.cancel()
            with self.assertRaises(asyncio.CancelledError):await task
        fixture.LOOP.run_until_complete(cancel());worker=fixture.Runner._RunAgentWorker(executor_task=task,task_id='retire-owned-worker',worker_done=done)
        self.authority._turn_workers={id(worker):(worker,[None])};self.drain()
        try:self.reject();self.assertFalse(done.is_set());self.assertIn(id(worker),self.authority._turn_workers)
        finally:release.set();self.assertTrue(done.wait(5))
        self.reject()  # Completed-but-retained record still belongs to native producer.
        from gateway.session_runtime_workers import physical_workers
        self.assertEqual(list(physical_workers(self.authority)),[]);self.retire()
    def test_live_subscriber_observer_pending_control_and_settling_each_refuse(self):
        _,_,live=self.make_bound();self.drain()
        for obj,name,value in ((live,'subscribers',{'held':object()}),(live,'settling',{'held':object()}),(live.event_stream,'execution',{'run':'held'}),(live.event_stream,'observers',{lambda frame:None}),(live.controls,'pending',{'held':object()}),(live.controls,'remote_responders',{'held':lambda *a:None})):
            old=getattr(obj,name);setattr(obj,name,value)
            try:self.reject();self.assertIs(getattr(obj,name),value)
            finally:setattr(obj,name,old)
    def test_actual_detached_fanout_writer_is_still_obligation(self):
        _,_,live=self.make_bound();entered=threading.Event();release=threading.Event();self.releases.append(release)
        class Transport:
            def write(self,frame):entered.set();return release.wait(15)
        transport=Transport();fanout=live.event_stream.fanout;fanout.attach(transport);fanout.write({'fixture':'frame'})
        self.assertTrue(entered.wait(5));fanout.detach(transport);self.assertFalse(fanout.has_transports());self.drain()
        try:self.reject();self.assertTrue(fanout._peers)
        finally:
            release.set();end=time.monotonic()+5
            while fanout._peers and time.monotonic()<end:time.sleep(.005)
            self.assertFalse(fanout._peers)
        self.retire()
    def test_session_async_claim_and_mutation_locks_refuse_without_release(self):
        _,_,live=self.make_bound();self.drain()
        for lock in (live.claim_gate,live.mutation_lock):
            fixture.LOOP.run_until_complete(lock.acquire())
            try:self.reject();self.assertTrue(lock.locked())
            finally:lock.release()
        self.retire()
    def test_other_thread_holding_event_lock_refuses_without_wait(self):
        _,_,live=self.make_bound();self.drain();entered=threading.Event();release=threading.Event();self.releases.append(release)
        def body():
            with live.event_stream.lock:entered.set();release.wait(10)
        t=threading.Thread(target=body);self.threads.append(t);t.start();self.assertTrue(entered.wait(5))
        try:self.reject();self.assertTrue(t.is_alive())
        finally:release.set();t.join(5)
        self.retire()
    def test_nonempty_agent_cache_is_not_evicted_or_cleaned(self):
        _,_,live=self.make_bound();token=object();self.runner._agent_cache[live.route]=token;self.drain()
        try:self.reject();self.assertIs(self.runner._agent_cache[live.route],token)
        finally:self.runner._agent_cache.clear()
        self.retire()
    def test_identity_drift_precedes_any_memory_removal(self):
        _,_,live=self.make_bound();self.drain();old=self.authority.epoch;self.authority.epoch+=1
        try:self.reject()
        finally:self.authority.epoch=old
        self.retire()
    def test_unsettled_response_and_replay_are_not_ignored(self):
        self.make_bound();self.drain();c=self.response._conn;c.execute("INSERT INTO response_keys(request_key,fingerprint,created_at,model_json) VALUES('held',?,1,'null')",('e'*64,));c.commit()
        try:self.reject()
        finally:c.execute("DELETE FROM response_keys WHERE request_key='held'");c.commit()
        self.retire()
    def test_foreign_scope_keeps_exact_original_session(self):
        import hermes_constants
        self.make_bound();self.drain();token=hermes_constants.set_hermes_home_override(self.home/'foreign')
        try:self.reject();self.assertFalse((self.home/'foreign').exists())
        finally:hermes_constants.reset_hermes_home_override(token)
    def test_durable_route_and_binding_drift_refuse_before_memory_changes(self):
        _,_,live=self.make_bound();self.drain();c=self.state._conn;row=c.execute("SELECT entry_json FROM gateway_routing WHERE scope='' AND session_key=?",(live.route,)).fetchone()[0]
        c.execute("UPDATE gateway_routing SET entry_json='{}' WHERE scope='' AND session_key=?",(live.route,));c.commit()
        try:
            with self.watched(),self.assertRaises(Exception):self.retire()
            self.assertEqual(len(self.authority.sessions),1);self.assertEqual(self.binding._stage,'DRAINING')
        finally:c.execute("UPDATE gateway_routing SET entry_json=? WHERE scope='' AND session_key=?",(row,live.route));c.commit()
        self.retire()
    def test_idle_retirement_is_not_delete_or_profile_release(self):
        from hermes_state_mutation_retirement import RETIRED_PREFIX
        ref,_,_=self.make_bound();self.drain();before=self.durable_snapshot();self.retire()
        self.assertEqual(before,self.durable_snapshot());self.assertIsNone(self.state._conn.execute('SELECT value FROM state_meta WHERE key=?',(RETIRED_PREFIX+ref.session_id,)).fetchone());self.assert_open()
    def test_new_native_binding_restore_after_retire_blocks_finish_again(self):
        from gateway.session_api import restore_api_session
        ref,_,_=self.make_bound();self.drain();self.retire();self.call(restore_api_session,self.authority,ref.session_id)
        self.assertIn(ref.session_id,self.authority.sessions)
        with self.assertRaises((fixture.Reject,fixture.RunnerReject)):self.finish()
        self.retire();self.finish()

def main():
    # Select only our newly defined cases; inherited admission cases are not rerun.
    names=sorted(n for n in RetirementCases.__dict__ if n.startswith('test_'))
    output=Path(sys.argv[sys.argv.index('--output')+1]);fixture.IndependentLifecycle=RetirementCases
    selected=any(x=='--case' for x in sys.argv)
    if not selected:
        for name in names:sys.argv.extend(['--case',name])
    code=fixture.main();original=json.loads((output/'result.json').read_text(encoding='utf-8'))
    original.update(result='PASS_INDEPENDENT_NATIVE_SESSION_RETIREMENT' if code==0 else 'FAIL',retirementChecks=RETIRE,retirementQaSha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),fixtureQaSha256=hashlib.sha256(Path(fixture.__file__).read_bytes()).hexdigest(),selectedOwnMethodsOnly=True,newRetirementMethodCount=len(names),sameOwnerHarnessIntegrationTested=False,actualApiSessionBinding=True,terminalWorkUsesGuardedNativeLeafSettlement=True,wholeApiAgentTurnExecuted=False,sourceGeneration='native candidate supplied by producer, immutable pin checked externally')
    (output/'retirement-result.json').write_text(json.dumps(original,indent=2)+'\n',encoding='utf-8')
    print('RETIREMENT_SCOPE',json.dumps({k:v for k,v in original.items() if k not in ('nativeImports','checks','caseEnd','deniedEvents')}),flush=True)
    return code
if __name__=='__main__':raise SystemExit(main())
