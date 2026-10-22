"""Pure policy tests; inventory/ownership assertions are fixtures, not live proof."""
from dataclasses import replace
from pathlib import Path
import builtins,json,os,sys,unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'packages/claw-hermes'))
import gateway_work_health as p
class WorkPolicyTests(unittest.TestCase):
    def setUp(self):
        self.identity=p.RuntimeIdentity('12345678-1234-4234-8234-123456789012',3,'process-owned',100,900)
        self.empty=p.WorkSnapshot(self.identity,(),(),(),(),0,1000,5,5,True,True,False,False,False)
        self.a=p.Admission('a','session','started',3,2,2)
        self.run=p.Run('run-owned','{"status":"running"}',100,900)
        self.response=p.ResponseIdentity('idem:owned','a',False)
        self.owner=p.LiveWork('a','session',3,2,'RUNNING',True,'run-owned','idem:owned')
        self.busy=replace(self.empty,admissions=(self.a,),runs=(self.run,),responses=(self.response,),live_work=(self.owner,))
    def state(self,s,want,reason=None):
        result=p.assess(s,self.identity,now_ns=1100,max_age_ns=500);self.assertIs(result.state,want)
        if reason is not None:self.assertEqual(result.reason,reason)
        body=result.public()
        for key in ('runtimeAdmissionAuthorized','retryAuthorized','storeReleaseAuthorized'):self.assertFalse(body[key])
        return result
    def test_idle_never_grants_execution_or_release(self):self.state(self.empty,p.Health.IDLE)
    def test_owned_running_is_busy_not_fault(self):self.assertEqual(self.state(self.busy,p.Health.BUSY).owned_work_count,1)
    def test_native_queued_generation_is_null(self):
        s=replace(self.busy,admissions=(replace(self.a,status='queued',generation=None),),live_work=(replace(self.owner,phase='QUEUED',generation=None),),runs=(replace(self.run,status_json='{"status":"queued"}'),))
        self.state(s,p.Health.BUSY)
    def test_unowned_native_queue_is_not_healthy(self):self.state(replace(self.empty,admissions=(replace(self.a,status='queued',generation=None),)),p.Health.RECONCILE,'unowned_admission')
    def test_session_only_work_without_optional_api_links(self):self.state(replace(self.busy,runs=(),responses=(),live_work=(replace(self.owner,run_id=None,response_key=None),)),p.Health.BUSY)
    def test_terminal_settling_stays_busy_until_owner_finishes(self):
        s=replace(self.busy,admissions=(replace(self.a,status='terminal'),),live_work=(replace(self.owner,phase='SETTLING'),))
        self.state(s,p.Health.BUSY)
        s=replace(s,runs=(replace(self.run,status_json='{"status":"completed"}'),),responses=(replace(self.response,settled=True),))
        self.state(s,p.Health.BUSY);self.state(replace(s,live_work=()),p.Health.IDLE)
    def test_terminal_unsettled_response_without_owner_not_idle(self):self.state(replace(self.empty,admissions=(replace(self.a,status='terminal'),),responses=(self.response,)),p.Health.RECONCILE,'unowned_unsettled_response')
    def test_unknown_and_unsupported_admissions(self):
        for value in ('unknown','pending','lost',''):
            with self.subTest(value=value):self.state(replace(self.busy,admissions=(replace(self.a,status=value),)),p.Health.RECONCILE)
    def test_runtime_epoch_pid_start_and_uuid_fences(self):
        for values in ({'epoch':4},{'instance_id':'other'},{'owner_pid':101},{'owner_started':901},{'store_instance_id':'22345678-1234-4234-8234-123456789012'}):
            with self.subTest(values=values):self.state(replace(self.busy,identity=replace(self.identity,**values)),p.Health.RECONCILE,'runtime_identity_changed')
    def test_stale_admission_epoch(self):self.state(replace(self.busy,admissions=(replace(self.a,owner_epoch=2),)),p.Health.RECONCILE,'stale_work_epoch')
    def test_wrong_session_or_claim_generation(self):
        for values in ({'session_id':'other'},{'generation':3},{'epoch':2}):
            with self.subTest(values=values):self.state(replace(self.busy,live_work=(replace(self.owner,**values),)),p.Health.RECONCILE)
    def test_session_generation_fence(self):self.state(replace(self.busy,admissions=(replace(self.a,session_generation=3),)),p.Health.RECONCILE,'stale_work_generation')
    def test_gone_task_cannot_inherit_durable_running_row(self):self.state(replace(self.busy,live_work=(replace(self.owner,task_alive=False),)),p.Health.RECONCILE,'owner_task_gone')
    def test_owner_without_native_admission(self):self.state(replace(self.busy,admissions=()),p.Health.RECONCILE,'owner_without_admission')
    def test_historical_terminal_rows_not_live_ownership(self):
        old=replace(self.a,status='terminal',owner_epoch=1,generation=None,session_generation=20)
        self.state(replace(self.empty,admissions=(old,),runs=(replace(self.run,status_json='{"status":"completed"}',owner_pid=0,owner_started=0),)),p.Health.IDLE)
    def test_drain_preserves_health_without_admission(self):
        self.state(replace(self.busy,draining=True),p.Health.DRAINING);self.state(replace(self.empty,draining=True),p.Health.DRAINING)
    def test_drain_cannot_ignore_unknown_work(self):self.state(replace(self.busy,draining=True,live_work=()),p.Health.RECONCILE)
    def test_unknown_shutdown_never_healthy(self):self.state(replace(self.empty,shutdown_unknown=True),p.Health.RECONCILE,'shutdown_outcome_unknown')
    def test_open_transaction_or_incomplete_snapshot_unobservable(self):
        for values in ({'transaction_active':True},{'complete':False},{'storage_verified':False},{'revision_after':6}):
            with self.subTest(values=values):self.state(replace(self.busy,**values),p.Health.UNOBSERVABLE)
    def test_expired_or_future_snapshot(self):
        for captured in (0,1101):self.state(replace(self.empty,captured_ns=captured),p.Health.UNOBSERVABLE,'snapshot_stale_or_future')
    def test_snapshot_age_boundary_inclusive(self):self.state(replace(self.empty,captured_ns=600),p.Health.IDLE)
    def test_bool_and_integer_not_coerced(self):
        for values in ({'complete':1},{'storage_verified':'yes'},{'draining':0},{'unresolved_workers':False},{'revision_before':True},{'captured_ns':-1}):
            with self.subTest(values=values):self.state(replace(self.empty,**values),p.Health.UNOBSERVABLE)
    def test_delegated_workers_not_qualified_by_main_task(self):self.state(replace(self.busy,unresolved_workers=1),p.Health.RECONCILE,'delegated_worker_not_qualified')
    def test_single_global_active_owner_limit(self):
        a=replace(self.a,admission_id='b',session_id='other');owner=replace(self.owner,admission_id='b',session_id='other',run_id=None,response_key=None)
        self.state(replace(self.busy,admissions=(self.a,a),live_work=(self.owner,owner)),p.Health.RECONCILE,'single_active_owner_limit')
    def test_multiple_owners_same_session(self):
        a=replace(self.a,admission_id='b');owner=replace(self.owner,admission_id='b',run_id=None,response_key=None)
        self.state(replace(self.busy,admissions=(self.a,a),live_work=(self.owner,owner)),p.Health.RECONCILE,'multiple_session_owners')
    def test_duplicate_mutable_oversized_inventory(self):
        for values in ({'admissions':(self.a,self.a)},{'admissions':[self.a]},{'live_work':(self.owner,)*257},{'runs':(object(),)}):
            with self.subTest(values=values):self.state(replace(self.busy,**values),p.Health.UNOBSERVABLE)
    def test_bad_run_json_duplicate_keys_nonfinite_and_statuses(self):
        for raw in ('{"status":"running","status":"completed"}','{"status":"running","nested":{"x":1,"x":2}}','{"status":"running","n":NaN}','[]','{"status":"unknown"}','{"status":1}','{'+' '*65536,chr(0xdcff)):
            with self.subTest(raw=repr(raw[:100])):self.state(replace(self.busy,runs=(replace(self.run,status_json=raw),)),p.Health.UNOBSERVABLE)
    def test_unowned_run(self):self.state(replace(self.empty,runs=(self.run,)),p.Health.RECONCILE,'unowned_active_run')
    def test_pid_reuse(self):self.state(replace(self.busy,runs=(replace(self.run,owner_started=901),)),p.Health.RECONCILE,'run_owner_process_mismatch')
    def test_missing_run_and_wrong_phase(self):
        self.state(replace(self.busy,runs=()),p.Health.RECONCILE,'run_owner_missing_or_ambiguous')
        self.state(replace(self.busy,runs=(replace(self.run,status_json='{"status":"completed"}'),)),p.Health.RECONCILE,'run_phase_mismatch')
    def test_response_link_and_settlement_order(self):
        self.state(replace(self.busy,responses=()),p.Health.RECONCILE,'response_owner_missing_or_ambiguous')
        self.state(replace(self.busy,responses=(replace(self.response,admission_id='b'),)),p.Health.RECONCILE,'response_admission_mismatch')
        self.state(replace(self.busy,responses=(replace(self.response,settled=True),)),p.Health.RECONCILE,'response_settled_before_admission')
    def test_unqualified_transition_not_corruption(self):self.state(replace(self.busy,live_work=(replace(self.owner,phase='ADMITTING'),)),p.Health.UNOBSERVABLE,'owner_transition_unqualified')
    def test_reconciliation_latches(self):
        session=p.WorkHealthSession(self.identity);bad=session.observe(replace(self.busy,live_work=()),now_ns=1100,max_age_ns=500)
        self.assertIs(bad.state,p.Health.RECONCILE);self.assertIs(session.observe(self.busy,now_ns=1100,max_age_ns=500),bad)
    def test_contention_recovers_without_permanent_failure(self):
        session=p.WorkHealthSession(self.identity)
        self.assertIs(session.observe(replace(self.busy,transaction_active=True),now_ns=1100,max_age_ns=500).state,p.Health.UNOBSERVABLE)
        self.assertIs(session.observe(self.busy,now_ns=1100,max_age_ns=500).state,p.Health.BUSY)
    def test_drain_latches(self):
        session=p.WorkHealthSession(self.identity);session.observe(replace(self.busy,draining=True),now_ns=1100,max_age_ns=500)
        self.assertIs(session.observe(self.empty,now_ns=1100,max_age_ns=500).state,p.Health.DRAINING)
    def test_no_io_and_no_private_identity_publicly(self):
        with patch.object(builtins,'open',side_effect=AssertionError('file')),patch.object(os,'open',side_effect=AssertionError('fd')):body=self.state(self.busy,p.Health.BUSY).public()
        self.assertNotIn('session',json.dumps(body));self.assertNotIn('idem:owned',json.dumps(body));self.assertFalse(body['liveCollectorVerifiedHere'])
    def test_explicit_expected_identity_and_clock(self):
        for value in ({},None,self.empty):
            with self.assertRaises(p.InvalidEvidence):p.assess(self.empty,value,now_ns=1100,max_age_ns=500)
        for now,age in ((True,1),(1100,0),(1100,60_000_000_001)):
            with self.assertRaises(p.InvalidEvidence):p.assess(self.empty,self.identity,now_ns=now,max_age_ns=age)
        self.state({},p.Health.UNOBSERVABLE)
if __name__=='__main__':unittest.main()
