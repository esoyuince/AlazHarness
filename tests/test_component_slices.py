"""Provenance and executed Hermes helper contracts; no upstream application imports."""
import concurrent.futures
import errno
import importlib.util
import io
import json
from pathlib import Path
import sys
import threading
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from verify_components import inspect, materialize

def transform(data, kind):
    if kind == 'verbatim': return materialize(data, {'mode': 'copy'})
    if kind != 'relocate-deadline-import': raise ValueError('Unknown transformation')
    return materialize(data, {'mode': 'rewrite', 'replacements': [['"@openclaw/normalization-core/number-coercion"', '"./number-coercion.ts"']]})

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,ROOT/path)
    m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m
transport=load('alaz_component_transport','packages/upstream/hermes/transport.py')
budget=load('alaz_component_budget','packages/upstream/hermes/iteration_budget.py')

class ComponentProvenanceTests(unittest.TestCase):
    def test_copies_match_recorded_digests(self):
        result=inspect(ROOT);self.assertEqual(result['components'],10);self.assertFalse(result['vendor_bytes_compared'])
    def test_import_relocation_only(self):
        source=b'import x from "@openclaw/normalization-core/number-coercion";\nbody();'
        self.assertEqual(transform(source,'relocate-deadline-import'),b'import x from "./number-coercion.ts";\nbody();')
    def test_unknown_transform_fails(self):
        with self.assertRaises(ValueError):transform(b'x','unknown')
    def test_missing_import_fails(self):
        with self.assertRaises(ValueError):transform(b'x','relocate-deadline-import')
    def test_multiple_imports_fail(self):
        with self.assertRaises(ValueError):transform(b'"@openclaw/normalization-core/number-coercion"'*2,'relocate-deadline-import')
    def test_licenses_kept_separate(self):
        for name in ('openclaw','hermes'):
            self.assertIn('MIT License',(ROOT/'packages/upstream'/name/'LICENSE').read_text(encoding='utf-8'))

class HermesComponentTests(unittest.TestCase):
    def test_stdio_roundtrip_unicode(self):
        out=io.StringIO();t=transport.StdioTransport(lambda:out,threading.Lock())
        value={'text':'ışık 🚀\nnext','id':'1'};self.assertTrue(t.write(value))
        self.assertEqual(json.loads(out.getvalue()),value);self.assertEqual(len(out.getvalue().splitlines()),1)
    def test_stdio_fallback_is_error_not_success(self):
        out=io.StringIO();t=transport.StdioTransport(lambda:out,threading.Lock())
        with self.assertLogs(transport.logger,level='ERROR'):self.assertTrue(t.write({'id':'r','bad':object()}))
        response=json.loads(out.getvalue());self.assertEqual(response['id'],'r');self.assertEqual(response['error']['code'],-32603)
    def test_broken_pipe_is_distinct_from_storage_failure(self):
        class Broken:
            def write(self,text):raise BrokenPipeError()
        self.assertFalse(transport.StdioTransport(lambda:Broken(),threading.Lock()).write({'ok':1}))
        class Full:
            def write(self,text):raise OSError(errno.ENOSPC,'fixture full')
        with self.assertRaises(OSError):transport.StdioTransport(lambda:Full(),threading.Lock()).write({'ok':1})
    def test_stdio_serializes_concurrent_writes(self):
        out=io.StringIO();t=transport.StdioTransport(lambda:out,threading.Lock())
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            self.assertTrue(all(pool.map(lambda i:t.write({'id':i}),range(64))))
        self.assertEqual({json.loads(s)['id'] for s in out.getvalue().splitlines()},set(range(64)))
    def test_budget_concurrent_limit(self):
        b=budget.IterationBudget(17)
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            results=list(pool.map(lambda _:b.consume(),range(64)))
        self.assertEqual(sum(results),17);self.assertEqual(b.used,17);self.assertEqual(b.remaining,0)
    def test_budget_refund_never_negative(self):
        b=budget.IterationBudget(1);b.refund();self.assertEqual(b.used,0)
        self.assertTrue(b.consume());self.assertFalse(b.consume());b.refund();self.assertTrue(b.consume())
    def test_warning_ratio_validation(self):
        for value in (True,False,0,1,float('nan'),'invalid'):
            self.assertIsNone(budget.normalize_budget_warning_ratio(value))
        self.assertEqual(budget.normalize_budget_warning_ratio('0.8'),0.8)
if __name__=='__main__':unittest.main()
