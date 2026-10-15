"""Offline identity/completeness tests for independent component evidence; no OpenCode import."""
import copy
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from run_independent_opencode_qa import EXPECTED,validate


def good():
    return {'nonce':'abc','pid':19,'cases':[{'name':name,'result':'PASS'} for name in EXPECTED['permission']],
            'passed':12,'failed':0,'model_calls':0,'source_loads':[{'path':'permission.ts','sha256':'x'}]}


class IndependentOpenCodeEvidenceTests(unittest.TestCase):
    def test_exact_receipt_accepted(self):self.assertEqual(validate(good(),'permission','abc',19,0),[])
    def test_nonzero_exit_not_success(self):self.assertTrue(validate(good(),'permission','abc',19,1))
    def test_wrong_nonce_refused(self):self.assertTrue(validate(good(),'permission','wrong',19,0))
    def test_wrong_pid_refused(self):self.assertTrue(validate(good(),'permission','abc',20,0))
    def test_missing_case_refused(self):
        x=good();x['cases'].pop();self.assertTrue(validate(x,'permission','abc',19,0))
    def test_duplicate_case_refused(self):
        x=good();x['cases'][-1]=copy.deepcopy(x['cases'][0]);self.assertTrue(validate(x,'permission','abc',19,0))
    def test_boolean_total_refused(self):
        x=good();x['passed']=True;self.assertTrue(validate(x,'permission','abc',19,0))
    def test_missing_provenance_refused(self):
        x=good();x['source_loads']=[];self.assertTrue(validate(x,'permission','abc',19,0))
    def test_nonzero_model_calls_refused(self):
        x=good();x['model_calls']=1;self.assertTrue(validate(x,'permission','abc',19,0))
    def test_failed_observation_refused(self):
        x=good();x['cases'][0]['result']='FAIL';self.assertTrue(validate(x,'permission','abc',19,0))
    def test_malformed_refused(self):
        for x in [None,{},[],{'cases':None}]:self.assertTrue(validate(x,'permission','abc',19,0))

if __name__=='__main__':unittest.main()
