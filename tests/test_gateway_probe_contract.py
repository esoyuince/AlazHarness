"""Offline validation of native Gateway evidence; these tests do not boot Hermes."""
from __future__ import annotations
import copy
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from gateway_probe_contract import CHECKS,validate,database_evidence
from gateway_process import ancestry
from prepare_native_hermes import build_code

def good(scenario='normal'):
    stop=scenario=='stop';status='cancelled' if stop else 'completed'
    final={'run_id':'run_test','session_id':'run_test','admission_id':'admit_test','execution_generation':1,'status':status}
    report={'scenario':scenario,'nonce':'a'*32,'ready':{'nonce':'a'*32,'pid':12,'runner':'gateway.run.GatewayRunner',
       'adapter':'gateway.platforms.api_server.APIServerAdapter','authority':'gateway.session_authority.SessionAuthority',
       'state':'ready','profile_bound':True,'api_host':'127.0.0.1','epoch':1},
       'launcher_pid':11,'ownership_chain':[12,11],'child_exit':0,'client_exit':0,'child_reaped':True,'gateway_reaped':True,
       'shutdown':{'nonce':'a'*32,'pid':12,'native_result':True,'lifecycle_completed':True},
       'client':{'nonce':'a'*32,'scenario':scenario,'result':'PASS','run_id':'run_test','final':final,'checks':CHECKS[scenario][:],
                 'admission':{'replayed':scenario=='lost-ack'}},
       'database':{'read_only':True,'after_process_exit':True,'integrity':'ok','admissions':[
         {'request_id':'run_test','target_session_id':'run_test','admission_id':'admit_test','owner_epoch':1,'generation':1,'status':'terminal','outcome':status}],
         'run_records':[{'run_id':'run_test'}],'user_messages':1,'tool_results':0 if stop else 1,
         'tool_names':[] if stop else ['read_file'],'tool_contains_marker':not stop,'assistant_contains_marker':not stop},
       'model_calls':[{'tool_result':False}]+([] if stop else [{'tool_result':True}]),
       'fixture_errors':[],'source_or_program_drift':False,'model_inference_calls':0,'paid_calls':0}
    if scenario=='lost-ack':
        report['relay']={'dropped_run':'run_test'};report['client']['lost_error']='write_outcome_unknown'
    return report

class GatewayEvidenceTests(unittest.TestCase):
    def test_valid_normal(self):self.assertEqual(validate(good()),[])
    def test_valid_lost_ack(self):self.assertEqual(validate(good('lost-ack')),[])
    def test_valid_stop(self):self.assertEqual(validate(good('stop')),[])
    def test_fake_runtime_rejected(self):
        x=good();x['ready']['authority']='fixture.Authority';self.assertTrue(validate(x))
    def test_foreign_nonce_rejected(self):
        x=good();x['client']['nonce']='other';self.assertTrue(validate(x))
    def test_readiness_not_admission(self):
        x=good();x['database']['admissions']=[];self.assertTrue(validate(x))
    def test_duplicate_admission_rejected(self):
        x=good();x['database']['admissions']*=2;self.assertTrue(validate(x))
    def test_wrong_native_identity_rejected(self):
        x=good();x['database']['admissions'][0]['admission_id']='other';self.assertTrue(validate(x))
    def test_missing_tool_proof_rejected(self):
        x=good();x['database']['tool_contains_marker']=False;self.assertTrue(validate(x))
    def test_lost_ack_requires_same_native_run(self):
        x=good('lost-ack');x['relay']['dropped_run']='other';self.assertTrue(validate(x))
    def test_post_stop_tool_rejected(self):
        x=good('stop');x['database']['tool_results']=1;self.assertTrue(validate(x))
    def test_source_drift_rejected(self):
        x=good();x['source_or_program_drift']=True;self.assertTrue(validate(x))
    def test_shutdown_is_not_just_process_exit(self):
        x=good();x['shutdown']['native_result']=False;self.assertTrue(validate(x))
    def test_extra_model_call_rejected(self):
        x=good();x['model_calls'].append({});self.assertTrue(validate(x))
    def test_incomplete_checks_rejected(self):
        x=good();x['client']['checks'].pop();self.assertTrue(validate(x))
    def test_boolean_exit_rejected(self):
        x=good();x['child_exit']=False;self.assertTrue(validate(x))
    def test_boolean_tool_counter_rejected(self):
        x=good();x['database']['tool_results']=True;self.assertTrue(validate(x))
    def test_malformed_evidence_rejected(self):
        for value in (None,{},[],{'scenario':'unknown'}):self.assertTrue(validate(value))
    def test_missing_db_reader_does_not_create(self):
        import sqlite3
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)
            with self.assertRaises(sqlite3.Error):database_evidence(path,{'run_id':'x','session_id':'x'},'marker')
            self.assertFalse((path/'state.db').exists())

class GatewayProcessTests(unittest.TestCase):
    def test_direct_child(self):self.assertEqual(ancestry(10,10,{}),[10])
    def test_venv_redirector_child(self):self.assertEqual(ancestry(11,10,{11:10}),[11,10])
    def test_unrelated_pid_rejected(self):
        with self.assertRaises(ValueError):ancestry(11,10,{11:12})
    def test_cycle_rejected(self):
        with self.assertRaises(ValueError):ancestry(11,10,{11:12,12:11})
    def test_boolean_pid_rejected(self):
        with self.assertRaises(ValueError):ancestry(True,10,{})
    def test_frozen_minimal_gateway_extra(self):
        value=build_code(Path('source'),Path('output'),gateway_http=True)
        compile(value,'build-code','exec');self.assertIn("extras=('sms',)",value)
        self.assertIn('frozen=True',value);self.assertIn('no_install_project=True',value)

if __name__=='__main__':unittest.main()
