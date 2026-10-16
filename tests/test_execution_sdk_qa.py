"""Wire-control receipt checks only. These do not run a provider, SDK or Gateway."""
import copy
import json
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]

def validate_wire_control(r):
    if not isinstance(r,dict):return False
    try:
        if r['source_commit']!='eb75627faf532fa6ffbdae59a0d14b0b385fc780':return False
        if r['source_changed'] is not False:return False
        for k,expected in [('passed',2),('failed',0),('nonloopback_attempts_blocked',0),('model_inference_calls',0),('paid_calls',0)]:
            if type(r[k]) is not int or r[k]!=expected:return False
        rows=r['cases']
        if type(rows) is not list or len(rows)!=2:return False
        expected=[('native-default',1,False,'InternalServerError'),('explicit-sdk-retry',2,True,None)]
        for row,(name,count,success,error) in zip(rows,expected):
            if type(row) is not dict or row['scenario']!=name:return False
            if type(row['sdk_method_invocations']) is not int or row['sdk_method_invocations']!=1:return False
            if type(row['server_http_requests']) is not int or row['server_http_requests']!=count:return False
            if row['success'] is not success or row['exception_type']!=error or row['passed'] is not True:return False
        return True
    except (KeyError,TypeError,ValueError):return False

class SDKWireReceiptTests(unittest.TestCase):
    def setUp(self):self.report=json.loads((ROOT/'evidence/hyb-005b-qa3193/sdk-wire-control.json').read_text(encoding='utf-8'))
    def test_complete_observation(self):self.assertTrue(validate_wire_control(self.report))
    def test_missing_case(self):self.report['cases'].pop();self.assertFalse(validate_wire_control(self.report))
    def test_extra_case(self):self.report['cases'].append(copy.deepcopy(self.report['cases'][0]));self.assertFalse(validate_wire_control(self.report))
    def test_swapped_case(self):self.report['cases'].reverse();self.assertFalse(validate_wire_control(self.report))
    def test_boolean_counter(self):self.report['cases'][0]['server_http_requests']=True;self.assertFalse(validate_wire_control(self.report))
    def test_wrong_invocation_count(self):self.report['cases'][1]['sdk_method_invocations']=2;self.assertFalse(validate_wire_control(self.report))
    def test_not_retried(self):self.report['cases'][1]['server_http_requests']=1;self.assertFalse(validate_wire_control(self.report))
    def test_paid_call(self):self.report['paid_calls']=1;self.assertFalse(validate_wire_control(self.report))
    def test_program_drift(self):self.report['source_changed']=True;self.assertFalse(validate_wire_control(self.report))
    def test_report_omission(self):del self.report['cases'][0]['exception_type'];self.assertFalse(validate_wire_control(self.report))
    def test_bad_root(self):self.assertFalse(validate_wire_control(None))
    def test_failed_control(self):self.report['cases'][0]['passed']=False;self.assertFalse(validate_wire_control(self.report))

if __name__=='__main__':unittest.main()
