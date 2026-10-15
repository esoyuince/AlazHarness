"""Pure evidence/launcher checks, not execution of Pi or a crash experiment."""
from __future__ import annotations
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from pi_durable_contract import evaluate_case,check_barrier
from run_native_pi_durable import read_object


def sample(scenario='crash-unsafe'):
    safe=scenario=='crash-safe';pending=scenario=='crash-pending';committed=scenario=='crash-committed'
    tasks=[{'id':12,'kind':'pi.tool','state':{'status':'running','checkpoint':{'phase':'execute','replay':'safe' if safe else 'unsafe'}}}]
    barrier={'scenario':scenario,'phase':'before','pid':100,'rootId':1,'submissionId':8,
             'cut':'effect_complete_result_uncommitted','entries':['pi.user','pi.assistant'],
             'taskStates':tasks,'effects':1,'attempts':1}
    if pending:
        barrier.update(cut='request_pending_no_response',entries=['pi.user'],effects=0,attempts=0,
                       taskStates=[{'id':9,'kind':'pi.generation','state':{'status':'running','checkpoint':{'phase':'request'}}}])
    if committed:
        barrier.update(cut='settled_commit_before_close',settlement={'status':'done'},entries=['pi.user','pi.tool-result'],
                       taskStates=[{'id':12,'kind':'pi.tool','state':{'status':'terminal'}}])
    o={'schema':1,'scenario':scenario,'characterization':'PASS','modelInferenceCalls':0,'paidCalls':0,
       'osSandboxClaimed':False,'powerLossTested':False,'productionIntegrated':False,
       'processCleanClose':True,'modelCalls':0 if committed else 1,'toolExecutions':1 if safe else 0,
       'rootIdentityPreserved':True,'submissionIdentityPreserved':True,'providerIdentityPreserved':True,'idle':True,
       'attempts':0 if pending else (2 if safe else 1),'effects':0 if pending else 1,
       'toolErrors':1 if scenario=='crash-unsafe' else 0,'taskCompleted':scenario!='crash-unsafe','uncertainEffect':scenario=='crash-unsafe'}
    before={'phase':'before','pid':100,'timed_out':False,'child_reaped':True,'exit_code':1,
            'ready_received':True,'killed_at_barrier':True,'started_monotonic':1.,'finished_monotonic':2.,'barrier':barrier}
    after={'phase':'after','pid':200,'timed_out':False,'child_reaped':True,'exit_code':0,'started_monotonic':3.,'finished_monotonic':4.}
    return {'scenario':scenario,'characterization':'PASS','observation':o,'processes':[before,after],
            'independent_effect_counts':{'attempts':o['attempts'],'effects':o['effects']},
            'database_after_crash':{'integrity':'ok','read_only':True,'entry_kinds':copy.deepcopy(barrier['entries']),
                                    'tasks':copy.deepcopy(barrier['taskStates']),'submissions':[{'id':8,'conversationId':1}]}}

class DurableEvidenceTests(unittest.TestCase):
    def test_valid_four_crash_contracts(self):
        for scenario in ('crash-unsafe','crash-safe','crash-pending','crash-committed'):
            with self.subTest(scenario=scenario):self.assertEqual(evaluate_case(sample(scenario)),[])
    def test_missing_execution_rejected(self):
        c=sample();c['processes']=[];self.assertTrue(evaluate_case(c))
    def test_normal_exit_not_a_crash(self):
        c=sample();c['processes'][0]['exit_code']=0;self.assertTrue(evaluate_case(c))
    def test_unknown_termination_not_accepted(self):
        c=sample();c['processes'][0]['killed_at_barrier']=False;self.assertTrue(evaluate_case(c))
    def test_recovery_does_not_overlap_owner(self):
        c=sample();c['processes'][1]['started_monotonic']=1.5;self.assertTrue(evaluate_case(c))
    def test_unreaped_child_rejected(self):
        c=sample();c['processes'][0]['child_reaped']=False;self.assertTrue(evaluate_case(c))
    def test_timeout_rejected_even_with_pass_receipt(self):
        c=sample();c['processes'][1]['timed_out']=True;self.assertTrue(evaluate_case(c))
    def test_database_must_confirm_checkpoint(self):
        c=sample();c['database_after_crash']['tasks'][0]['state']['checkpoint']['phase']='done';self.assertTrue(evaluate_case(c))
    def test_uncommitted_result_cut_enforced(self):
        b=sample()['processes'][0]['barrier'];b['entries'].append('pi.tool-result');self.assertTrue(check_barrier(b,'crash-unsafe'))
    def test_independent_counter_not_agent_self_report(self):
        c=sample();c['independent_effect_counts']['effects']=2;self.assertTrue(evaluate_case(c))
    def test_safe_tag_does_not_excuse_double_effect(self):
        c=sample('crash-safe');c['observation']['effects']=2;c['independent_effect_counts']['effects']=2;self.assertTrue(evaluate_case(c))
    def test_unknown_effect_not_task_success(self):
        c=sample();c['observation']['taskCompleted']=True;self.assertTrue(evaluate_case(c))
    def test_committed_work_not_reissued(self):
        c=sample('crash-committed');c['observation']['modelCalls']=1;self.assertTrue(evaluate_case(c))
    def test_missing_readonly_integrity_proof(self):
        c=sample();c['database_after_crash']={};self.assertTrue(evaluate_case(c))
    def test_malformed_receipt_fails_closed(self):
        for c in (None,{}, {'scenario':'crash-safe','observation':None}, {'scenario':'unknown'}):
            with self.subTest(c=c):self.assertTrue(evaluate_case(c))
    def test_boolean_not_request_count(self):
        c=sample();c['observation']['modelCalls']=True;self.assertTrue(evaluate_case(c))
    def test_broad_sandbox_claim_refused(self):
        c=sample();c['observation']['osSandboxClaimed']=True;self.assertTrue(evaluate_case(c))
    def test_native_stderr_exit_not_hidden(self):
        c=sample();c['processes'][-1]['exit_code']=2;self.assertTrue(evaluate_case(c))

class ReceiptReadTests(unittest.TestCase):
    def test_json_array_not_a_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'receipt.json';p.write_text('[]')
            with self.assertRaises(ValueError):read_object(p)
    def test_oversized_receipt_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'receipt.json';p.write_text(' '*262145)
            with self.assertRaises(ValueError):read_object(p)
    def test_small_object_read(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'receipt.json';p.write_text(json.dumps({'result':'FAIL'}))
            self.assertEqual(read_object(p),{'result':'FAIL'})

class AdmissionOutcomeTests(unittest.TestCase):
    def case(self):
        c=sample();c['scenario']='admission';c['processes']=[dict(c['processes'][-1],phase='single')]
        c['observation']={**c['observation'],'scenario':'admission','sameKeySameId':True,'changedPayloadSameId':True,
            'originalPayloadPreserved':True,'typeMismatchRejected':True,'conversationScopeSeparated':True,
            'reopenIdentityPreserved':True,'inputChangedPayloadSameId':True,'inputOriginalPayloadPreserved':True,
            'inputDuplicateAfterReopenSameId':True,'strictPayloadConflict':False,'adoptionBlockers':['payload-conflict']}
        return c
    def test_observed_gap_kept_explicit(self):
        self.assertEqual(evaluate_case(self.case()),[])
    def test_gap_cannot_be_silently_promoted(self):
        c=self.case();c['observation']['strictPayloadConflict']=True;c['observation']['adoptionBlockers']=[]
        self.assertTrue(evaluate_case(c))

if __name__=='__main__':unittest.main()
