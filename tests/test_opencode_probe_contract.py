"""Offline projection/receipt tests. No Effect install or OpenCode runtime is invoked."""
from __future__ import annotations
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from run_opencode_components import EXPECTED_CASES, validate_receipt
from opencode_probe_support import ROOT, relative_imports, slice_lines, config


def good():
    return {'nonce':'a'*32,'pid':123,'platform':'win32','total':len(EXPECTED_CASES),
            'passed':len(EXPECTED_CASES),'failed':0,'model_inference_calls':0,'paid_calls':0,
            'full_server_tested':False,'http_routing_tested':False,
            'persistent_database_tested':False,'os_sandbox_claimed':False,
            'cases':[{'name':name,'result':'PASS','elapsed_ms':1} for name in EXPECTED_CASES]}

class ReceiptContractTests(unittest.TestCase):
    def check(self,value,exit_code=0):return validate_receipt(value,'a'*32,123,exit_code)
    def test_valid_receipt(self):self.assertEqual(self.check(good()),[])
    def test_nonzero_exit(self):self.assertTrue(self.check(good(),1))
    def test_missing_case(self):
        v=good();v['cases'].pop();self.assertTrue(self.check(v))
    def test_duplicate_case(self):
        v=good();v['cases'][-1]=v['cases'][0];self.assertTrue(self.check(v))
    def test_unknown_case(self):
        v=good();v['cases'][0]['name']='invented';self.assertTrue(self.check(v))
    def test_reordered_case(self):
        v=good();v['cases'].reverse();self.assertTrue(self.check(v))
    def test_failed_case(self):
        v=good();v['cases'][0]['result']='FAIL';self.assertTrue(self.check(v))
    def test_skip_not_success(self):
        v=good();v['cases'][0]['result']='SKIP';self.assertTrue(self.check(v))
    def test_wrong_identity(self):
        for key,value in [('pid',124),('nonce','b'*32)]:
            v=good();v[key]=value
            with self.subTest(key=key):self.assertTrue(self.check(v))
    def test_boolean_or_nonfinite_count(self):
        for value in (True,float('nan'),float('inf'),-1):
            v=good();v['passed']=value
            with self.subTest(value=value):self.assertTrue(self.check(v))
    def test_inference_not_permitted(self):
        for key in ('model_inference_calls','paid_calls'):
            v=good();v[key]=1
            with self.subTest(key=key):self.assertTrue(self.check(v))
    def test_broad_claims_rejected(self):
        for key in ('full_server_tested','http_routing_tested','persistent_database_tested','os_sandbox_claimed'):
            v=good();v[key]=True
            with self.subTest(key=key):self.assertTrue(self.check(v))
    def test_invalid_case_time(self):
        v=good();v['cases'][0]['elapsed_ms']=float('nan');self.assertTrue(self.check(v))
    def test_malformed_receipt(self):
        for value in (None,[],{}, {'cases':[None]}):
            with self.subTest(value=value):self.assertTrue(self.check(value))
    def test_zero_discovery(self):
        v=good();v.update(total=0,passed=0,cases=[]);self.assertTrue(self.check(v))

class ProjectionContractTests(unittest.TestCase):
    def test_relative_import_relocation_only(self):
        source='import {x} from "./a.js"; const s="file.js"; export * from "../b.js";'
        self.assertEqual(relative_imports(source),'import {x} from "./a.ts"; const s="file.js"; export * from "../b.ts";')
    def test_external_imports_unchanged(self):
        source='import {Effect} from "effect"; import x from "pkg/a.js";'
        self.assertEqual(relative_imports(source),source)
    def test_slice_preserves_selected_body(self):
        with tempfile.TemporaryDirectory() as name:
            root=Path(name);(root/'a.ts').write_text('first\n second\nthird\n',encoding='utf-8')
            self.assertEqual(slice_lines(root,'a.ts',2,2,'// prefix\n'),'// prefix\n second\n')
    def test_out_of_range_slice(self):
        with tempfile.TemporaryDirectory() as name:
            root=Path(name);(root/'a.ts').write_text('line\n',encoding='utf-8')
            with self.assertRaises(ValueError):slice_lines(root,'a.ts',1,3,'')
    def test_exact_dependency_lock(self):
        lock=json.loads((ROOT/'config/opencode-probe/package-lock.json').read_text(encoding='utf-8'))
        self.assertEqual(set(lock['packages']),{'','node_modules/effect'})
        e=lock['packages']['node_modules/effect'];c=config()
        self.assertEqual((e['version'],e['integrity']),(c['effect_version'],c['effect_integrity']))
    def test_authoring_scripts_parse_without_dependency_execution(self):
        for name in ('opencode_component_worker.mjs','opencode_services.mjs'):
            p=subprocess.run(['node','--check',str(ROOT/'scripts'/name)],capture_output=True,text=True,timeout=10)
            with self.subTest(name=name):self.assertEqual(p.returncode,0,p.stderr)

if __name__=='__main__':unittest.main()
