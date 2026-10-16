"""Host-report regressions: real readers/validators, synthetic local SQLite records.
Not live Gateway execution, real provider inference, or billing qualification.
"""
from __future__ import annotations
from contextlib import closing
from dataclasses import asdict,replace
import hashlib
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import time
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'packages/claw-hermes'));sys.path.insert(0,str(ROOT/'tests'))
import test_recovery_inspector as fx
import test_host_gate_qa as owners
import recovery_inspector as ri
import host_report as hr
from execution_budget import ExecutionLedger,ExecutionPolicy,seal


class HostReportTests(unittest.TestCase):
    def setUp(self):
        fx.InspectorTests.setUp(self)
        self.p=ExecutionPolicy('fixture-model',4,2,100,20,480,2000,2000000,5000000)
        self.http['usage']={'input_tokens':12,'output_tokens':4,'total_tokens':16}
        self.saved['usage']=self.http['usage'].copy();self.save_result()
        self.owner=owners.SyntheticOwner(self.home/'state.db')
        self.b=ExecutionLedger(self.owner,self.context,self.p);self.b.initialize()
        self.inspector=hr.HostReportInspector(self.context,self.p,clock=lambda:self.now)
    def sql(self,*args,**kwargs):return fx.InspectorTests.sql(self,*args,**kwargs)
    def query(self,**changes):
        return self.inspector.inspect(**(dict(body=self.body,idempotency_key=self.key,observed=self.http)|changes))
    def save_result(self):self.sql('UPDATE state_meta SET value=? WHERE key=?',(ri._json(self.saved),ri.RESULT+self.aid))
    def claim(self,usage=None,outcome='response',kind='provider'):
        row=self.b.claim(kind,'a'*64)
        if outcome is not None:self.b.settle(row['ticket'],usage,outcome)
        return row
    def hashes(self):return [hashlib.sha256((self.home/n).read_bytes()).hexdigest() for n in ['state.db','runs_idempotency.db']]
    def refuse(self,**changes):
        r=self.query(**changes);self.assertEqual(r['reportStatus'],'unverified',r)
        self.assertFalse(r['execution']['available']);self.assertFalse(r['task']['taskSucceeded'])
        self.assertFalse(r['retryAllowed']);self.assertFalse(r['repairAllowed']);return r
    def test_complete_task_and_scoped_usage_are_separate(self):
        self.claim({'input_tokens':12,'output_tokens':4});self.claim({'input_tokens':12,'output_tokens':4})
        r=self.query();self.assertTrue(r['task']['taskSucceeded'])
        self.assertEqual(r['nativeReportedUsage']['inputTokens'],12)
        self.assertEqual(r['execution']['observedUsage']['inputTokens'],24)
        self.assertFalse(r['usageComparison']['comparable']);self.assertIsNone(r['usageComparison']['numericDifference'])
    def test_summary_text_does_not_imply_completed_task(self):
        self.saved['result'].update(completed=False,partial=False,turn_exit_reason='max_iterations_reached(1/1)')
        self.save_result();self.http['status']='failed'
        r=self.query();self.assertEqual(r['reportStatus'],'verified_snapshot');self.assertFalse(r['task']['taskSucceeded'])
        self.assertEqual(r['task']['nativeStatus'],'failed');self.assertEqual(r['task']['nativeAdmissionOutcome'],'completed')
        self.assertEqual(r['task']['completionReason'],'max_iterations_reached(1/1)')
    def test_partial_task_is_not_success(self):
        self.saved['result'].update(completed=False,partial=True);self.save_result();self.http['status']='failed'
        self.assertFalse(self.query()['task']['taskSucceeded'])
    def test_cancelled_task(self):
        self.saved['result'].update(completed=False,interrupted=True);self.save_result();self.http['status']='cancelled'
        self.assertEqual(self.query()['task']['outcome'],'cancelled')
    def test_unknown_execution_never_grants_retry(self):
        self.sql("UPDATE session_admissions SET status='unknown',outcome=NULL");self.http['status']='unknown'
        r=self.query();self.assertEqual(r['task']['classification'],'execution_unknown');self.assertTrue(r['task']['requiresOperator']);self.assertFalse(r['executionAllowed'])
    def test_reserved_without_response_usage_is_unknown_not_zero(self):
        self.claim(outcome=None);r=self.query()['execution']
        self.assertEqual(r['providerAttempts']['usageUnknown'],1);self.assertIsNone(r['observedUsage']['totalTokens'])
        self.assertEqual(r['reservedExposure']['tokens'],120)
    def test_missing_usage_preserves_exposure(self):
        self.claim(None,'unknown_usage');r=self.query()['execution']
        self.assertEqual(r['reservedExposure']['costMicrousd'],300);self.assertEqual(r['observedUsage']['coverage'],'unknown')
    def test_partial_usage_keeps_known_sum_and_unknown_count(self):
        self.claim({'input_tokens':2,'output_tokens':1});self.claim(None,'transport_error')
        r=self.query()['execution'];self.assertEqual(r['observedUsage']['totalTokens'],3)
        self.assertEqual(r['observedUsage']['coverage'],'partial');self.assertEqual(r['providerAttempts']['usageUnknown'],1)
    def test_zero_known_usage_is_distinct_from_unknown(self):
        self.claim({'input_tokens':0,'output_tokens':0})
        self.assertEqual(self.query()['execution']['observedUsage']['totalTokens'],0)
        self.assertEqual(self.query()['execution']['providerAttempts']['usageKnown'],1)
    def test_zero_retained_claims_not_global_no_calls(self):
        r=self.query()['execution'];self.assertEqual(r['observedUsage']['coverage'],'no_reserved_attempts')
        self.assertEqual(r['observedUsage']['totalTokens'],0);self.assertFalse(r['observedUsage']['includesUnconfiguredProviders'])
    def test_reservation_never_reported_as_wire_delivery(self):
        self.claim(outcome=None);r=self.query()['execution']['providerAttempts'];self.assertIsNone(r['wireDeliveryCount'])
        self.assertEqual(r['wireDeliveryProof'],'reservation_is_not_delivery')
    def test_tool_handler_return_not_claimed_successful_effect(self):
        self.claim(None,'tool_return',kind='read_file');r=self.query()['execution']['toolAttempts']
        self.assertEqual(r['handlerReturns'],1);self.assertIsNone(r['successfulEffects'])
    def test_budget_is_not_invoice(self):
        self.claim({'input_tokens':1,'output_tokens':1});r=self.query()['execution']['reservedExposure']
        self.assertFalse(r['isInvoice']);self.assertIsNone(r['actualBilledMicrousd']);self.assertFalse(r['tariffVerified'])
    def test_remaining_capacity_is_not_permission(self):
        r=self.query();self.assertFalse(r['execution']['remainingReservedCapacity']['grantsExecutionPermission']);self.assertFalse(r['executionAllowed'])
    def test_no_state_or_replay_bytes_changed(self):
        self.claim({'input_tokens':1,'output_tokens':1});before=self.hashes();self.query();self.query();self.assertEqual(self.hashes(),before)
    def test_read_only_adapter_never_invokes_write(self):
        with patch.object(hr._NoWriteOwner,'_execute_write',side_effect=AssertionError('unexpected write')):
            self.assertEqual(self.query()['reportStatus'],'verified_snapshot')
    def test_database_connections_closed_no_dml(self):
        original=sqlite3.connect;opened=[];statements=[]
        def connect(*a,**kw):
            c=original(*a,**kw);c.set_trace_callback(statements.append);opened.append(c);return c
        with patch('recovery_inspector.sqlite3.connect',connect):self.query()
        self.assertEqual(len(opened),1)
        for c in opened:
            with self.assertRaises(sqlite3.ProgrammingError):c.execute('SELECT 1')
        self.assertFalse(any(s.split()[0].upper() in {'INSERT','UPDATE','DELETE','CREATE','DROP','REPLACE'} for s in statements))
    def test_quarantine_visible_but_never_reset(self):
        self.b.quarantine();before=self.hashes();r=self.query()
        self.assertTrue(r['execution']['quarantined']);self.assertFalse(r['executionAllowed']);self.assertEqual(self.hashes(),before)
    def test_wrong_bearer_discloses_no_execution(self):
        self.inspector=hr.HostReportInspector(replace(self.context,api_token='wrong'),self.p,clock=lambda:self.now);self.refuse()
    def test_wrong_request(self):self.refuse(body={'input':'other'})
    def test_wrong_key(self):self.refuse(idempotency_key='other')
    def test_wrong_run(self):self.refuse(observed=self.http|{'run_id':'run_'+'c'*32})
    def test_stale_epoch(self):
        self.sql('UPDATE runtime_epoch SET epoch=3');self.refuse()
    def test_missing_db_not_created(self):
        p=self.home/'runs_idempotency.db';p.unlink();self.refuse();self.assertFalse(p.exists())
    def test_missing_budget_not_zero(self):
        self.sql('DELETE FROM state_meta WHERE key=?',(self.b.key,));r=self.query()
        self.assertTrue(r['task']['canonicalVerified']);self.assertEqual(r['reportStatus'],'partial_snapshot');self.assertFalse(r['execution']['available'])
    def test_policy_change_does_not_reprice_or_reset(self):
        self.inspector=hr.HostReportInspector(self.context,replace(self.p,max_provider_calls=3),clock=lambda:self.now)
        before=self.hashes();r=self.query();self.assertFalse(r['execution']['available']);self.assertEqual(self.hashes(),before)
    def test_missing_claim_with_retained_counter_refused(self):
        row=self.claim(outcome=None);self.sql('DELETE FROM state_meta WHERE key=?',(self.b.prefix+row['ticket'],))
        self.assertFalse(self.query()['execution']['available'])
    def test_fake_counter_refused(self):
        self.claim(outcome=None);cfg=self.b.snapshot();cfg['providerCalls']=0
        self.sql('UPDATE state_meta SET value=? WHERE key=?',(ri._json(seal(cfg)),self.b.key))
        self.assertFalse(self.query()['execution']['available'])
    def test_error_claim_with_usage_not_reported_as_success(self):
        self.claim({'input_tokens':1,'output_tokens':1},'transport_error')
        self.assertFalse(self.query()['execution']['available'])
    def test_expired_retention_does_not_publish_usage(self):
        self.sql('UPDATE run_idempotency SET retention_until=?',(self.now-1,),replay=True);self.refuse()
    def test_completed_output_not_disclosed(self):
        r=self.query();rendered=json.dumps(r)+hr.render_text(r)
        for secret in [self.context.api_token,self.body['input'],'native-output',str(self.home),self.key]:self.assertNotIn(secret,rendered)
    def test_arbitrary_terminal_reason_not_exposed(self):
        self.saved['result']['turn_exit_reason']='SECRET diagnostic';self.save_result()
        self.assertNotIn('SECRET',json.dumps(self.query()))
    def test_returned_report_mutation_does_not_affect_storage(self):
        r=self.query();r['execution']['reservedExposure']['tokens']=999
        self.assertEqual(self.query()['execution']['reservedExposure']['tokens'],0)
    def test_read_snapshot_invalidated_by_concurrent_epoch_change(self):
        original=sqlite3.connect;outer=self
        class Changing(sqlite3.Connection):
            def rollback(self):
                super().rollback()
                with closing(original(outer.home/'state.db')) as c:c.execute('UPDATE runtime_epoch SET epoch=3');c.commit()
        def connect(*a,**kw):return original(*a,**kw,factory=Changing)
        with patch('recovery_inspector.sqlite3.connect',connect):self.refuse()
    def test_text_explains_scope_and_unknown(self):
        self.claim(outcome=None);text=hr.render_text(self.query())
        self.assertIn('UNKNOWN',text);self.assertIn('NOT attributed',text);self.assertIn('NOT an invoice',text)
    def test_invalid_trusted_types_refused(self):
        with self.assertRaises(TypeError):hr.HostReportInspector(self.context,{})
    def test_missing_native_usage_not_zero(self):
        self.http.pop('usage');self.saved['usage']={};self.save_result()
        r=self.query()['nativeReportedUsage'];self.assertEqual(r['coverage'],'unavailable');self.assertIsNone(r['totalTokens'])
    def test_bool_native_token_not_one(self):
        self.http['usage']={'input_tokens':True};self.saved['usage']=self.http['usage'];self.save_result()
        self.assertEqual(self.query()['nativeReportedUsage']['coverage'],'invalid')
    def test_cli_report_has_no_secret_and_exit_matches_evidence(self):
        self.sql('UPDATE run_idempotency SET updated_at=?,created_at=?',(time.time(),time.time()),replay=True)
        context=asdict(self.context);context['profile_home']=str(context['profile_home']);context.pop('profile_name')
        for name,obj in [('context.json',context),('policy.json',asdict(self.p)),('request.json',{'body':self.body,'idempotency_key':self.key,'observed':self.http})]:
            (self.home/name).write_text(json.dumps(obj),encoding='utf-8')
        cmd=[sys.executable,'-B',str(ROOT/'scripts/inspect_host_report.py'),'--context',str(self.home/'context.json'),'--policy',str(self.home/'policy.json'),'--request',str(self.home/'request.json')]
        result=subprocess.run(cmd,capture_output=True,text=True,encoding='utf-8',timeout=10)
        self.assertEqual(result.returncode,0,result.stderr);self.assertTrue(json.loads(result.stdout)['task']['taskSucceeded'])
        self.assertNotIn(self.context.api_token,result.stdout)
        (self.home/'request.json').write_text('{"body":null}',encoding='utf-8')
        result=subprocess.run(cmd,capture_output=True,text=True,encoding='utf-8',timeout=10)
        self.assertEqual(result.returncode,2);self.assertEqual(json.loads(result.stdout)['reason'],'invalid_local_input')

if __name__=='__main__':unittest.main()
