"""Independent R1 legacy-boundary invariants on synthetic SQLite; not native runs."""
from contextlib import closing
from dataclasses import replace
import builtins
import copy
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'packages/claw-hermes'),str(ROOT/'tests')]
import test_reconciliation_inspector_qa as fx
import test_execution_budget as owner_fx
import recovery_inspector as ri
import host_report as hr
from execution_budget import ExecutionPolicy,ExecutionLedger

class EvidenceReportAuthorityInvariants(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        self.f=fx.StoreFixture(Path(temp.name))
        self.ctx=ri.LocalRecoveryContext(self.f.home,fx.TOKEN,2,'owner-two')
        self.policy=ExecutionPolicy('chosen-model',6,2,100,20,720,1000,1000000,2000000)
        self.ledger=ExecutionLedger(owner_fx.TestOwner(self.f.home/'state.db'),self.ctx,self.policy)
        self.ledger.initialize()
    def save(self):
        self.f.sql('UPDATE state_meta SET value=? WHERE key=?',(ri._json(self.f.result),ri.RESULT+fx.AID))
    def read(self,**overrides):
        before=self.f.hashes()
        report=hr.HostReportInspector(self.ctx,self.policy,clock=lambda:fx.NOW).inspect(**(
            {'body':self.f.body,'idempotency_key':self.f.key,'observed':self.f.http}|overrides))
        self.assertEqual(before,self.f.hashes())
        for name in ('writesPerformed','retryAllowed','repairAllowed','executionAllowed'):
            self.assertIs(report[name],False,name)
        self.assertIs(report['task'].get('goalAchievementIndependentlyVerified',False),False)
        return report
    def test_model_goal_claim_does_not_verify_goal(self):
        self.f.result['result']['messages']=[{'role':'assistant','content':'The goal passed',
            'goalAchievementIndependentlyVerified':True,'evidenceComplete':True}]
        self.save();self.assertIs(self.read()['task']['taskSucceeded'],True)
    def test_observer_evidence_fields_are_not_authority(self):
        observed=copy.deepcopy(self.f.http)
        observed['evidence']={'modelSeen':True,'sourcePath':'QA_E03E_PRIVATE_OBSERVER',
            'goalVerified':True,'executionAllowed':True}
        r=self.read(observed=observed)
        self.assertNotIn('QA_E03E_PRIVATE_OBSERVER',ri._json(r)+hr.render_text(r))
    def test_hidden_tool_error_not_independent_goal_success(self):
        self.f.result['result']['messages']=[{'role':'tool','tool_call_id':'hidden',
            'content':json.dumps({'error':'tool_not_allowed'})}]
        self.save();self.read()
    def test_untrusted_identifiers_not_plaintext_report_content(self):
        self.f.result['result']['messages']=[{'role':'assistant','tool_calls':[
            {'id':'QA_E03E_PRIVATE_CALL_ID','type':'function','function':{
                'name':'QA_E03E_PRIVATE_TOOL_NAME','arguments':'{}'}}]},
            {'role':'tool','tool_call_id':'QA_E03E_PRIVATE_CALL_ID','content':'QA_E03E_PRIVATE_RESULT'}]
        self.save();report=self.read();text=ri._json(report)+hr.render_text(report)
        for marker in ('QA_E03E_PRIVATE_CALL_ID','QA_E03E_PRIVATE_TOOL_NAME','QA_E03E_PRIVATE_RESULT'):
            self.assertNotIn(marker,text)
    def test_an_unpaired_unicode_tool_never_creates_execution_permission(self):
        self.f.result['result']['messages']=[{'role':'tool','tool_call_id':'ışık\n\u202e','content':'Parça ✔'}]
        self.save();self.read()
    def test_boolean_generation_discloses_no_extra_evidence(self):
        r=self.read(observed=self.f.http|{'execution_generation':True})
        self.assertEqual(r['reportStatus'],'unverified')
        self.assertFalse(r['execution']['available'])
    def test_foreign_session_discloses_no_extra_evidence(self):
        r=self.read(observed=self.f.http|{'session_id':'run_'+'c'*32})
        self.assertEqual(r['reportStatus'],'unverified')
        self.assertFalse(r['execution']['available'])
    def test_returned_nested_report_not_a_live_state_alias(self):
        first=self.read();first['task']['taskSucceeded']=False
        first['execution']['reservedExposure']['tokens']=900
        second=self.read()
        self.assertIs(second['task']['taskSucceeded'],True)
        self.assertEqual(second['execution']['reservedExposure']['tokens'],0)
    def test_embedded_result_path_is_never_opened(self):
        target=self.f.home/'private-file.txt';target.write_text('PRIVATE_SOURCE',encoding='utf-8')
        self.f.result['result']['messages']=[{'role':'tool','tool_call_id':'unpaired',
            'content':json.dumps({'path':str(target),'content':'retained','total_lines':1,'lines_shown':1})}]
        self.save();raw_open=builtins.open;path_open=Path.open
        def guard_open(file,*args,**kwargs):
            self.assertNotEqual(str(file),str(target),'report opened a path from untrusted output')
            return raw_open(file,*args,**kwargs)
        def guard_path(path,*args,**kwargs):
            self.assertNotEqual(path,target,'report opened an untrusted Path')
            return path_open(path,*args,**kwargs)
        # read() hashes fixture files for a no-write assertion; do those reads outside patch.
        before=self.f.hashes()
        with patch('builtins.open',guard_open),patch.object(Path,'open',guard_path):
            report=hr.HostReportInspector(self.ctx,self.policy,clock=lambda:fx.NOW).inspect(
                body=self.f.body,idempotency_key=self.f.key,observed=self.f.http)
        self.assertFalse(report['executionAllowed']);self.assertEqual(before,self.f.hashes())
    def test_unknown_and_error_do_not_refund_prior_reservation(self):
        ticket=self.ledger.claim('provider','c'*64)
        self.ledger.settle(ticket['ticket'],None,'transport_error')
        self.f.sql("UPDATE session_admissions SET status='unknown',outcome=NULL")
        r=self.read(observed=self.f.http|{'status':'unknown'})
        self.assertEqual(r['execution']['reservedExposure']['tokens'],120)
        self.assertIsNone(r['execution']['providerAttempts']['wireDeliveryCount'])
        self.assertEqual(r['execution']['providerAttempts']['usageUnknown'],1)

if __name__=='__main__':unittest.main()
