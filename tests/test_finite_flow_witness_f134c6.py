"""Synthetic witness refusal tests. These do NOT execute Hermes or prove native flow."""
import importlib.util,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('finite_witness_f134c6',ROOT/'scripts/qa/f134c6_flow_witness.py')
witness=importlib.util.module_from_spec(spec);spec.loader.exec_module(witness)
class FiniteWitnessContract(unittest.TestCase):
    def full(self):
        rows=[]
        for path,function in (
            ('gateway/session_api_turn.py','run_api_turn'),('gateway/session_api_turn.py','observe_api_turn'),
            ('gateway/session_authority.py','_execute_claimed'),('gateway/session_finite.py','execute_finite_admission'),
            ('gateway/session_ingress.py','execute_admission'),('gateway/run_turn_runner.py','run_sync'),
            ('gateway/session_runtime_workers.py','track_turn_worker'),('gateway/session_settlement_recovery.py','commit_and_publish')):
            rows.append({'kind':'native','path':path,'function':function,'thread':10,'stack':[]})
        rows.append({'kind':'fixture_computation','path':'explicit_fixture.py','function':'run_conversation','thread':20,'stack':[]})
        rows.append({'kind':'native','path':'hermes_state_runtime.py','function':'settle_session_input','thread':30,
                     'stack':[{'path':'gateway/session_settlement_recovery.py','function':'commit_and_publish'}]})
        return rows
    def test_complete_synthetic_flow_only_has_scoped_verdict(self):
        r=witness.verdict(self.full(),10);self.assertTrue(r['flowObserved']);self.assertTrue(r['payloadCorrectnessNeedsDriverAssertions']);self.assertTrue(r['nativeCallCountsNotTaskCounts'])
    def test_zero_events_never_pass(self):self.assertFalse(witness.verdict([],10)['flowObserved'])
    def test_missing_finite_execution_refused(self):
        rows=[r for r in self.full() if r['function']!='execute_finite_admission'];self.assertFalse(witness.verdict(rows,10)['flowObserved'])
    def test_missing_physical_worker_tracking_refused(self):
        rows=[r for r in self.full() if r['function']!='track_turn_worker'];self.assertFalse(witness.verdict(rows,10)['flowObserved'])
    def test_model_on_main_thread_refused(self):
        rows=self.full();rows[-2]['thread']=10;r=witness.verdict(rows,10);self.assertFalse(r['computationOffMainThread']);self.assertFalse(r['flowObserved'])
    def test_no_computation_despite_native_calls_refused(self):
        rows=[r for r in self.full() if r['kind']!='fixture_computation'];self.assertFalse(witness.verdict(rows,10)['flowObserved'])
    def test_manual_settlement_cannot_impersonate_native_result(self):
        rows=self.full();rows[-1]['stack']=[{'path':'test_driver.py','function':'set_terminal'}];r=witness.verdict(rows,10);self.assertTrue(r['manualSettlementStackObserved']);self.assertFalse(r['flowObserved'])
    def test_one_valid_settle_does_not_hide_second_manual_settle(self):
        rows=self.full();rows.append({'kind':'native','path':'hermes_state_runtime.py','function':'settle_session_input','thread':10,'stack':[]});self.assertFalse(witness.verdict(rows,10)['flowObserved'])
    def test_witness_does_not_count_coroutine_resumptions_as_jobs(self):
        rows=self.full();r=witness.verdict(rows+rows,10);self.assertTrue(r['flowObserved']);self.assertTrue(r['nativeCallCountsNotTaskCounts'])
if __name__=='__main__':unittest.main()
