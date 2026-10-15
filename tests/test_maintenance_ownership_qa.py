"""Offline native-lock receipt contracts, NOT additional Gateway executions."""
import json
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts/qa'))
from maintenance_lock_contract import validate

class MaintenanceEvidenceQA(unittest.TestCase):
    def fixture(self):return json.loads((ROOT/'evidence/hyb-004c-qa/ownership-final.json').read_text(encoding='utf-8'))
    def test_complete(self):self.assertEqual(validate(self.fixture()),[])
    def test_nonobject(self):self.assertTrue(validate([]))
    def test_missing_case(self):
        x=self.fixture();x['checks'].pop();self.assertTrue(validate(x))
    def test_duplicate_case(self):
        x=self.fixture();x['checks'][0]=x['checks'][1];self.assertTrue(validate(x))
    def test_unreaped(self):
        x=self.fixture();x['maintenance_kill']['native_reaped']=False;self.assertTrue(validate(x))
    def test_wrong_process(self):
        x=self.fixture();x['blocked_gateway_exit']['chain']=[123];self.assertTrue(validate(x))
    def test_graceful_not_kill(self):
        x=self.fixture();x['maintenance_kill']['exit_code']=0;self.assertTrue(validate(x))
    def test_missing_shutdown(self):
        x=self.fixture();del x['restarted_gateway_exit']['shutdown'];self.assertTrue(validate(x))
    def test_no_new_epoch(self):
        x=self.fixture();x['restarted_gateway_exit']['ready']['epoch']=x['gateway_exit']['ready']['epoch'];self.assertTrue(validate(x))
    def test_model_call(self):
        x=self.fixture();x['model_http_calls']=1;self.assertTrue(validate(x))
    def test_bool_count(self):
        x=self.fixture();x['model_http_calls']=False;self.assertTrue(validate(x))
    def test_native_record_present(self):
        x=self.fixture();x['snapshot']['admissions']=[{}];self.assertTrue(validate(x))
    def test_drift(self):
        x=self.fixture();x['code_drift']=['file'];self.assertTrue(validate(x))
    def test_failed_check(self):
        x=self.fixture();x['checks'][0]['passed']=False;self.assertTrue(validate(x))
if __name__=='__main__':unittest.main()
