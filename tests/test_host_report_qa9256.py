"""Independent report contracts: real inspector/ledger on temporary synthetic stores.
No native Gateway, network request, provider invocation or real profile mutation.
"""
from contextlib import closing
from dataclasses import replace
import copy
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'packages/claw-hermes'))
import host_report as hr
import recovery_inspector as ri
from execution_budget import ExecutionLedger,ExecutionPolicy,CONFIG,CLAIM,seal
import test_reconciliation_inspector_qa as fixtures
import test_execution_budget as owner_fixture


class HostReportIndependentTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        self.f=fixtures.StoreFixture(Path(tmp.name))
        self.context=ri.LocalRecoveryContext(self.f.home,fixtures.TOKEN,2,'owner-two')
        self.policy=ExecutionPolicy('chosen-model',6,2,100,20,720,1000,1000000,2000000)
        self.ledger=ExecutionLedger(owner_fixture.TestOwner(self.f.home/'state.db'),self.context,self.policy)
        self.ledger.initialize()
        self.f.http['usage']={'input_tokens':10,'output_tokens':2,'total_tokens':12}
        self.f.result['usage']=dict(self.f.http['usage']);self.save_result()
    def save_result(self):
        self.f.sql('UPDATE state_meta SET value=? WHERE key=?',(ri._json(self.f.result),ri.RESULT+fixtures.AID))
    def reporter(self,context=None,policy=None):
        return hr.HostReportInspector(context or self.context,policy or self.policy,clock=lambda:fixtures.NOW)
    def read(self,**overrides):
        before=self.f.hashes()
        ans=self.reporter().inspect(**({'body':self.f.body,'idempotency_key':self.f.key,'observed':self.f.http}|overrides))
        self.assertEqual(before,self.f.hashes(),'report changed its source stores')
        self.assertIs(ans['writesPerformed'],False)
        for name in ('executionAllowed','retryAllowed','repairAllowed'):self.assertIs(ans[name],False)
        return ans
    def claim(self,usage='known',outcome='response'):
        row=self.ledger.claim('provider','c'*64)
        if usage!='pending':
            value={'input_tokens':10,'output_tokens':2} if usage=='known' else usage
            self.ledger.settle(row['ticket'],value,outcome)
        return row
    def change_row(self,ticket,**values):
        key=CLAIM+self.context.scope+'.'+ticket
        with closing(sqlite3.connect(self.f.home/'state.db')) as c:
            row=json.loads(c.execute('SELECT value FROM state_meta WHERE key=?',(key,)).fetchone()[0])
        self.f.sql('UPDATE state_meta SET value=? WHERE key=?',(ri._json(seal(row|values)),key))
    def test_profile_totals_are_not_attributed_to_run(self):
        self.claim();r=self.read();e=r['execution']
        self.assertEqual(e['scope'],'profile_principal');self.assertIs(e['attributedToThisRun'],False)
        self.assertEqual(e['runAttribution'],'unavailable');self.assertIs(r['usageComparison']['comparable'],False)
        self.assertIsNone(r['usageComparison']['numericDifference'])
    def test_pending_reservation_is_not_network_delivery(self):
        self.claim('pending');e=self.read()['execution'];a=e['providerAttempts']
        self.assertEqual(a['reserved'],1);self.assertEqual(a['unsettled'],1);self.assertEqual(a['settled'],0)
        self.assertIsNone(a['wireDeliveryCount']);self.assertEqual(e['observedUsage']['coverage'],'unknown')
        self.assertIsNone(e['observedUsage']['totalTokens'])
    def test_unknown_usage_not_zero(self):
        self.claim(None,'unknown_usage');e=self.read()['execution']
        self.assertEqual(e['providerAttempts']['usageUnknown'],1);self.assertIsNone(e['observedUsage']['inputTokens'])
        self.assertEqual(e['reservedExposure']['tokens'],120);self.assertEqual(e['reservedExposure']['costMicrousd'],140)
    def test_transport_error_unknown_usage_preserves_charge(self):
        self.claim(None,'transport_error');e=self.read()['execution']
        self.assertEqual(e['providerAttempts']['transportErrors'],1);self.assertEqual(e['observedUsage']['coverage'],'unknown')
        self.assertEqual(e['reservedExposure']['costMicrousd'],140)
    def test_partial_usage_counts_only_known_subset(self):
        self.claim();self.claim(None,'unknown_usage');e=self.read()['execution']
        self.assertEqual(e['observedUsage']['coverage'],'partial');self.assertEqual(e['observedUsage']['totalTokens'],12)
        self.assertEqual(e['providerAttempts']['usageUnknown'],1);self.assertEqual(e['reservedExposure']['tokens'],240)
    def test_known_zero_usage_is_not_missing(self):
        self.claim({'input_tokens':0,'output_tokens':0});e=self.read()['execution']
        self.assertEqual(e['observedUsage']['coverage'],'complete_for_retained_claims');self.assertEqual(e['observedUsage']['totalTokens'],0)
        self.assertEqual(e['providerAttempts']['usageUnknown'],0);self.assertEqual(e['reservedExposure']['costMicrousd'],140)
    def test_empty_initialized_ledger_is_explicit(self):
        e=self.read()['execution'];self.assertEqual(e['providerAttempts']['reserved'],0)
        self.assertEqual(e['observedUsage']['coverage'],'no_reserved_attempts');self.assertEqual(e['observedUsage']['totalTokens'],0)
    def test_no_invoice_or_execution_authority(self):
        self.claim();e=self.read()['execution'];risk=e['reservedExposure']
        self.assertIs(risk['isInvoice'],False);self.assertIs(risk['tariffVerified'],False)
        self.assertIsNone(risk['actualBilledMicrousd']);self.assertIs(risk['automaticRefund'],False)
        self.assertIs(e['remainingReservedCapacity']['grantsExecutionPermission'],False)
    def test_missing_budget_never_initialized(self):
        self.f.sql('DELETE FROM state_meta WHERE key=?',(CONFIG+self.context.scope,))
        r=self.read();self.assertFalse(r['execution']['available']);self.assertTrue(r['task']['canonicalVerified'])
        self.assertEqual(r['reportStatus'],'partial_snapshot')
    def test_corrupt_claim_has_no_partial_usage_numbers(self):
        claim=self.claim();key=CLAIM+self.context.scope+'.'+claim['ticket']
        self.f.sql('UPDATE state_meta SET value=? WHERE key=?',('{"corrupt":true}',key))
        e=self.read()['execution'];self.assertIs(e['available'],False);self.assertNotIn('observedUsage',e)
    def test_counter_drift_not_reported_as_valid(self):
        self.claim();key=CONFIG+self.context.scope
        with closing(sqlite3.connect(self.f.home/'state.db')) as c:cfg=json.loads(c.execute('SELECT value FROM state_meta WHERE key=?',(key,)).fetchone()[0])
        self.f.sql('UPDATE state_meta SET value=? WHERE key=?',(ri._json(seal(cfg|{'providerCalls':0})),key))
        self.assertFalse(self.read()['execution']['available'])
    def test_error_usage_cannot_be_claimed_as_response(self):
        claim=self.claim();self.change_row(claim['ticket'],outcome='transport_error')
        e=self.read()['execution'];self.assertIs(e['available'],False)
        self.assertEqual(e['reason'],'usage_outcome_not_reportable')
    def test_quarantine_does_not_hide_spent_exposure(self):
        self.claim();self.ledger.quarantine();e=self.read()['execution']
        self.assertIs(e['quarantined'],True);self.assertEqual(e['reservedExposure']['tokens'],120)
        self.assertIs(e['remainingReservedCapacity']['grantsExecutionPermission'],False)
    def test_foreign_policy_cannot_read_totals_as_current(self):
        self.claim();r=self.reporter(policy=replace(self.policy,max_provider_calls=5)).inspect(body=self.f.body,idempotency_key=self.f.key,observed=self.f.http)
        self.assertFalse(r['execution']['available']);self.assertEqual(r['reportStatus'],'partial_snapshot')
    def test_foreign_token_discloses_no_budget(self):
        self.claim();r=self.reporter(context=replace(self.context,api_token='other-secret')).inspect(body=self.f.body,idempotency_key=self.f.key,observed=self.f.http)
        self.assertEqual(r['reportStatus'],'unverified');self.assertFalse(r['execution']['available'])
        self.assertNotIn('other-secret',ri._json(r));self.assertNotIn('profileBinding',r)
    def test_stale_epoch_discloses_no_budget(self):
        self.claim();self.f.sql('UPDATE runtime_epoch SET epoch=3')
        r=self.read();self.assertEqual(r['reportStatus'],'unverified');self.assertFalse(r['execution']['available'])
    def test_wrong_request_content_rejects_all_sections(self):
        self.claim();r=self.read(body=self.f.body|{'input':'different'})
        self.assertEqual(r['reportStatus'],'unverified');self.assertFalse(r['execution']['available'])
    def test_missing_state_db_is_not_created(self):
        (self.f.home/'state.db').unlink();r=self.read()
        self.assertEqual(r['reportStatus'],'unverified');self.assertFalse((self.f.home/'state.db').exists())
    def test_missing_replay_db_is_not_created(self):
        (self.f.home/'runs_idempotency.db').unlink();r=self.read()
        self.assertEqual(r['reportStatus'],'unverified');self.assertFalse((self.f.home/'runs_idempotency.db').exists())
    def test_summary_is_failed_even_with_admission_completed(self):
        self.claim();self.claim();self.f.result['result'].update(completed=False,turn_exit_reason='max_iterations_reached(1/1)')
        self.f.http['status']='failed';self.save_result();r=self.read()
        self.assertEqual(r['task']['outcome'],'failed');self.assertFalse(r['task']['taskSucceeded'])
        self.assertEqual(r['task']['nativeAdmissionOutcome'],'completed')
        self.assertEqual(r['execution']['observedUsage']['totalTokens'],24);self.assertEqual(r['nativeReportedUsage']['totalTokens'],12)
        self.assertFalse(r['usageComparison']['comparable'])
    def test_unverified_live_usage_not_promoted_to_verified_native_usage(self):
        self.f.sql("UPDATE session_admissions SET status='started',outcome=NULL");self.f.http['status']='running'
        self.f.http['usage']={'input_tokens':999,'output_tokens':888,'total_tokens':1887}
        r=self.read();self.assertTrue(r['task']['canonicalVerified'])
        n=r['nativeReportedUsage'];self.assertIsNone(n.get('inputTokens'),'live usage is not checked against any canonical result')
        self.assertNotEqual(n.get('coverage'),'complete_fields')
    def test_unknown_execution_usage_not_promoted_to_verified_native_usage(self):
        self.f.sql("UPDATE session_admissions SET status='unknown',outcome=NULL");self.f.http['status']='unknown'
        self.f.http['usage']={'input_tokens':999,'output_tokens':888,'total_tokens':1887}
        n=self.read()['nativeReportedUsage'];self.assertIsNone(n.get('inputTokens'))
        self.assertNotEqual(n.get('coverage'),'complete_fields')
    def test_orphan_arbitrary_status_is_not_echoed(self):
        self.f.sql('DELETE FROM session_admissions');self.f.sql('DELETE FROM state_meta WHERE key=?',(ri.RESULT+fixtures.AID,))
        status='PRIVATE_STATUS_CONTENT\nforged line';self.f.http={'run_id':fixtures.RID,'status':status}
        self.f.sql('UPDATE run_idempotency SET status_json=?',(ri._json(self.f.http),),runs=True)
        r=self.read();self.assertNotIn('PRIVATE_STATUS_CONTENT',ri._json(r)+hr.render_text(r))
    def test_active_arbitrary_admission_outcome_is_not_echoed(self):
        self.f.sql("UPDATE session_admissions SET status='started',outcome=?",('PRIVATE_OUTCOME_CONTENT',));self.f.http['status']='running'
        r=self.read();self.assertNotIn('PRIVATE_OUTCOME_CONTENT',ri._json(r)+hr.render_text(r))
    def test_no_prompt_output_or_credentials_in_rendered_report(self):
        self.claim();r=self.read();serialized=ri._json(r)+hr.render_text(r)
        for private in (self.f.body['input'],self.f.http['output'],fixtures.TOKEN,self.f.key):self.assertNotIn(private,serialized)
    def test_arbitrary_completion_reason_is_not_echoed(self):
        self.f.result['result']['turn_exit_reason']='PRIVATE_REASON_CONTENT';self.save_result()
        r=self.read();self.assertIsNone(r['task']['completionReason']);self.assertNotIn('PRIVATE_REASON_CONTENT',ri._json(r))
    def test_partial_native_usage_preserves_missing_fields(self):
        self.f.http['usage']={'total_tokens':12};self.f.result['usage']={'total_tokens':12};self.save_result()
        n=self.read()['nativeReportedUsage'];self.assertEqual(n['coverage'],'partial_fields')
        self.assertIsNone(n['inputTokens']);self.assertIsNone(n['outputTokens']);self.assertEqual(n['totalTokens'],12)
    def test_report_never_calls_ledger_write_api(self):
        self.claim()
        def forbidden(*a,**k):raise AssertionError('report invoked write path')
        with patch.object(ExecutionLedger,'_write',forbidden),patch.object(ExecutionLedger,'initialize',forbidden),patch.object(ExecutionLedger,'claim',forbidden),patch.object(ExecutionLedger,'settle',forbidden):
            self.assertEqual(self.read()['reportStatus'],'verified_snapshot')
    def test_all_sqlite_connections_closed_and_readonly(self):
        self.claim();connect=sqlite3.connect;seen=[]
        def traced(*args,**kwargs):
            self.assertIn('mode=ro',args[0]);self.assertIs(kwargs['uri'],True)
            c=connect(*args,**kwargs);seen.append(c);return c
        with patch('host_report.sqlite3.connect',traced):r=self.read()
        self.assertEqual(r['reportStatus'],'verified_snapshot');self.assertTrue(seen)
        for c in seen:
            with self.assertRaises(sqlite3.ProgrammingError):c.execute('SELECT 1')
    def test_concurrent_ledger_change_discards_report(self):
        self.claim()
        with closing(sqlite3.connect(self.f.home/'state.db')) as c:c.execute('PRAGMA journal_mode=WAL')
        original=hr._execution_snapshot
        def changed(*args):
            result=original(*args);self.ledger.quarantine();return result
        with patch.object(hr,'_execution_snapshot',changed):
            r=self.reporter().inspect(body=self.f.body,idempotency_key=self.f.key,observed=self.f.http)
        self.assertEqual(r['reportStatus'],'unverified');self.assertEqual(r['reason'],'concurrent_state_change')
        self.assertFalse(r['execution']['available'])

if __name__=='__main__':unittest.main()
