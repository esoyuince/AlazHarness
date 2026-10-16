"""Buffered provider response contracts. No real API/network call."""
import json
from pathlib import Path
import sys,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'packages/claw-hermes'))
from execution_boundary import validate_provider_response
from execution_budget import ExecutionPolicy,ExecutionDenied
POLICY=ExecutionPolicy('fixture',2,1,100,20,240,1000,1000000,1000000)
def frame(model='fixture',usage=None):return {'model':model,'choices':[],**({} if usage is None else {'usage':usage})}
def sse(frames,space=True):return (''.join('data:'+(' ' if space else '')+json.dumps(f)+'\n\n' for f in frames)+'data:[DONE]\n\n').encode()
def usage(i=2,o=1):return {'prompt_tokens':i,'completion_tokens':o,'total_tokens':i+o}
class ResponseTests(unittest.TestCase):
    def check(self,raw,stream=True):return validate_provider_response(raw,streaming=stream,policy=POLICY)
    def test_compact_sse_is_checked(self):self.assertEqual(self.check(sse([frame(usage=usage())],False)),{'input_tokens':2,'output_tokens':1})
    def test_compact_wrong_model_refused(self):
        with self.assertRaises(ExecutionDenied):self.check(sse([frame('wrong')],False))
    def test_normal_json_model_refused(self):
        with self.assertRaises(ExecutionDenied):self.check(json.dumps(frame('wrong')).encode(),False)
    def test_bad_earlier_usage_not_hidden(self):
        with self.assertRaises(ExecutionDenied):self.check(sse([frame(usage=usage(101)),frame(usage=usage())]))
    def test_conflicting_final_usage_refused(self):
        with self.assertRaises(ExecutionDenied):self.check(sse([frame(usage=usage()),frame(usage=usage(3))]))
    def test_repeated_identical_usage_accepted(self):self.assertEqual(self.check(sse([frame(usage=usage()),frame(usage=usage())])),{'input_tokens':2,'output_tokens':1})
    def test_no_usage_is_unknown_not_zero(self):self.assertIsNone(self.check(sse([frame()])))
    def test_missing_done_refused(self):
        with self.assertRaises(ExecutionDenied):self.check(b'data:{"model":"fixture"}\n\n')
    def test_duplicate_done_refused(self):
        with self.assertRaises(ExecutionDenied):self.check(sse([frame()])+b'data:[DONE]\n\n')
    def test_incomplete_event_refused(self):
        with self.assertRaises(ExecutionDenied):self.check(b'data:{"model":"fixture"}')
    def test_bool_usage_refused(self):
        with self.assertRaises(ExecutionDenied):self.check(sse([frame(usage=usage(True))]))
    def test_comments_and_crlf(self):self.assertIsNone(self.check(b':keepalive\r\n\r\n'+sse([frame()]).replace(b'\n',b'\r\n')))
if __name__=='__main__':unittest.main()
