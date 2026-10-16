"""Independent real response validator/path guard tests; no SDK/Gateway runs."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'packages/claw-hermes'));sys.path.insert(0,str(ROOT/'tests'))
from execution_boundary import validate_provider_response,scoped_file,GuardedFileTools
from execution_budget import ExecutionDenied
from test_execution_gate_qa import policy


def frame(model='fixture-model',usage=None):
    return {'model':model,'choices':[],'usage':usage}

def encoded(value):return json.dumps(value).encode()

def stream(*values,compact=False):
    separator='data:' if compact else 'data: '
    return (''.join(separator+json.dumps(v)+'\n\n' for v in values)+separator+'[DONE]\n\n').encode()

class ResponseIndependentTests(unittest.TestCase):
    def setUp(self):self.p=policy();self.u={'prompt_tokens':2,'completion_tokens':1,'total_tokens':3}
    def parse(self,raw,streaming=True):return validate_provider_response(raw,streaming=streaming,policy=self.p)
    def test_json_valid(self):self.assertEqual(self.parse(encoded(frame(usage=self.u)),False),{'input_tokens':2,'output_tokens':1})
    def test_unknown_usage_is_none_not_zero(self):self.assertIsNone(self.parse(encoded(frame()),False))
    def test_sse_spaced(self):self.assertEqual(self.parse(stream(frame(usage=self.u))),{'input_tokens':2,'output_tokens':1})
    def test_sse_compact(self):self.assertEqual(self.parse(stream(frame(usage=self.u),compact=True)),{'input_tokens':2,'output_tokens':1})
    def test_sse_comments(self):self.assertEqual(self.parse(b': ping\n\n'+stream(frame(usage=self.u))),{'input_tokens':2,'output_tokens':1})
    def test_sse_crlf(self):self.assertEqual(self.parse(stream(frame(usage=self.u)).replace(b'\n',b'\r\n')),{'input_tokens':2,'output_tokens':1})
    def test_sse_same_usage_repeat(self):self.assertEqual(self.parse(stream(frame(usage=self.u),frame(usage=self.u))),{'input_tokens':2,'output_tokens':1})
    def test_sse_multiline_json_event(self):
        raw=b'data: {"model":"fixture-model",\ndata: "choices":[],"usage":null}\n\ndata: [DONE]\n\n';self.assertIsNone(self.parse(raw))
    def test_json_wrong_model(self):
        with self.assertRaises(ExecutionDenied):self.parse(encoded(frame('wrong',self.u)),False)
    def test_sse_wrong_model(self):
        with self.assertRaises(ExecutionDenied):self.parse(stream(frame('wrong',self.u)))
    def test_compact_sse_wrong_model(self):
        with self.assertRaises(ExecutionDenied):self.parse(stream(frame('wrong',self.u),compact=True))
    def test_sse_early_model_mismatch_not_hidden_by_later(self):
        with self.assertRaises(ExecutionDenied):self.parse(stream(frame('wrong'),frame(usage=self.u)))
    def test_sse_early_overuse_not_hidden_by_later(self):
        with self.assertRaises(ExecutionDenied):self.parse(stream(frame(usage={'prompt_tokens':101,'completion_tokens':1}),frame(usage=self.u)))
    def test_sse_conflicting_usage_below_cap_rejected(self):
        with self.assertRaises(ExecutionDenied):self.parse(stream(frame(usage={'prompt_tokens':1,'completion_tokens':1}),frame(usage=self.u)))
    def test_json_bool_usage_rejected(self):
        with self.assertRaises(ExecutionDenied):self.parse(encoded(frame(usage={'prompt_tokens':True,'completion_tokens':1})),False)
    def test_json_negative_usage_rejected(self):
        with self.assertRaises(ExecutionDenied):self.parse(encoded(frame(usage={'prompt_tokens':-1,'completion_tokens':1})),False)
    def test_json_bad_usage_total_rejected(self):
        with self.assertRaises(ExecutionDenied):self.parse(encoded(frame(usage=self.u|{'total_tokens':99})),False)
    def test_missing_done(self):
        with self.assertRaises(ExecutionDenied):self.parse(stream(frame())[:-14])
    def test_only_done(self):
        with self.assertRaises(ExecutionDenied):self.parse(b'data: [DONE]\n\n')
    def test_duplicate_done(self):
        with self.assertRaises(ExecutionDenied):self.parse(stream(frame())+b'data: [DONE]\n\n')
    def test_data_after_done(self):
        with self.assertRaises(ExecutionDenied):self.parse(stream(frame())+b'data: {}\n\n')
    def test_incomplete_event(self):
        with self.assertRaises(ExecutionDenied):self.parse(b'data: {"model":"fixture-model"}')
    def test_invalid_utf8(self):
        with self.assertRaises(ExecutionDenied):self.parse(b'\xff')
    def test_nonobject_json(self):
        with self.assertRaises(ExecutionDenied):self.parse(b'[]',False)
    def test_duplicate_json_fields(self):
        with self.assertRaises(ExecutionDenied):self.parse(b'{"model":"fixture-model","model":"fixture-model"}',False)
    def test_nonfinite_usage(self):
        with self.assertRaises(ExecutionDenied):self.parse(b'{"model":"fixture-model","usage":{"prompt_tokens":NaN,"completion_tokens":1}}',False)

class ReadPathIndependentTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name);self.p=self.root/'allowed.txt';self.p.write_text('fixture',encoding='utf-8')
    def test_literal_plain_allowed_file(self):self.assertEqual(scoped_file(str(self.p),frozenset({self.p})),str(self.p.resolve()))
    def test_other_existing_file_denied(self):
        p=self.root/'other.txt';p.write_text('other')
        with self.assertRaises(ExecutionDenied):scoped_file(str(p),frozenset({self.p}))
    def test_directory_named_txt_denied(self):
        p=self.root/'directory.txt';p.mkdir()
        with self.assertRaises(ExecutionDenied):scoped_file(str(p),frozenset({p}))
    def test_non_text_suffix_denied(self):
        p=self.root/'file.json';p.write_text('{}')
        with self.assertRaises(ExecutionDenied):scoped_file(str(p),frozenset({p}))
    def test_too_large_file_denied(self):
        self.p.write_bytes(b'x'*65537)
        with self.assertRaises(ExecutionDenied):scoped_file(str(self.p),frozenset({self.p}))
    def test_hardlinked_file_denied(self):
        # A failed platform hardlink is an ERROR, not silently skipped acceptance.
        os.link(self.p,self.root/'other.txt')
        with self.assertRaises(ExecutionDenied):scoped_file(str(self.p),frozenset({self.p}))
    def test_relative_network_and_device_paths_denied(self):
        for path in ['file.txt','//host/share/file.txt','\\host\\share\\file.txt','\\\\?\\C:\\file.txt']:
            with self.subTest(path=path),self.assertRaises(ExecutionDenied):scoped_file(path,frozenset({self.p}))
    def test_empty_allowlist_denied(self):
        with self.assertRaises(ExecutionDenied):GuardedFileTools([],lambda:None)
    def test_duplicate_allowlist_denied(self):
        with self.assertRaises(ExecutionDenied):GuardedFileTools([str(self.p),str(self.p)],lambda:None)
    def test_nonstring_path_denied(self):
        for path in [None,True,1,self.p]:
            with self.subTest(path=path),self.assertRaises(ExecutionDenied):scoped_file(path,frozenset({self.p}))

if __name__=='__main__':unittest.main()
