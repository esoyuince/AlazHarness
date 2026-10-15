"""Offline refusal-receipt/reader checks, not native Gateway execution."""
import copy
from contextlib import closing
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from run_gateway_refusal_qa import CASES,PIN,validate_refusal,db_counts


def good():
    return {'result':'PASS','pid':12,'nonce':'a'*32,'source_commit':PIN,
            'cases':[{'name':n,'http_status':s,'code':c,'no_admission_or_active_run_change':True} for n,s,c in CASES],
            'passed':9,'failed':0,'model_inference_calls':0,
            'before':{'native_admissions':0,'memory_run_statuses':0,'active_runs':0},
            'after':{'native_admissions':0,'memory_run_statuses':0,'active_runs':0},
            'native_store_identity_shared':True,'owned_cleanup_completed':True,
            'unexpected_network_connections':[],'runtime_socketpair_connections':1,
            'aiohttp_version':'3.14.3','full_gateway_lifecycle_tested':False,'os_sandbox_claimed':False}

class RefusalEvidenceTests(unittest.TestCase):
    def test_complete(self):self.assertEqual(validate_refusal(good(),'a'*32,12),[])
    def test_wrong_pid(self):self.assertTrue(validate_refusal(good(),'a'*32,13))
    def test_wrong_nonce(self):self.assertTrue(validate_refusal(good(),'b'*32,12))
    def test_missing_case(self):
        d=good();d['cases'].pop();self.assertTrue(validate_refusal(d,'a'*32,12))
    def test_duplicate_case(self):
        d=good();d['cases'][1]=d['cases'][0];self.assertTrue(validate_refusal(d,'a'*32,12))
    def test_unwanted_admission(self):
        d=good();d['after']['native_admissions']=1;self.assertTrue(validate_refusal(d,'a'*32,12))
    def test_unclosed_resources(self):
        d=good();d['owned_cleanup_completed']=False;self.assertTrue(validate_refusal(d,'a'*32,12))
    def test_model_call(self):
        d=good();d['model_inference_calls']=1;self.assertTrue(validate_refusal(d,'a'*32,12))
    def test_boolean_zero_rejected(self):
        d=good();d['after']['active_runs']=False;self.assertTrue(validate_refusal(d,'a'*32,12))
    def test_wrong_dependency(self):
        d=good();d['aiohttp_version']='other';self.assertTrue(validate_refusal(d,'a'*32,12))
    def test_missing_shared_owner(self):
        d=good();d['native_store_identity_shared']=False;self.assertTrue(validate_refusal(d,'a'*32,12))
    def test_false_full_lifecycle_claim(self):
        d=good();d['full_gateway_lifecycle_tested']=True;self.assertTrue(validate_refusal(d,'a'*32,12))
    def test_unexpected_network(self):
        d=good();d['unexpected_network_connections']=[{'host':'unexpected'}];self.assertTrue(validate_refusal(d,'a'*32,12))
    def test_malformed(self):
        for d in (None,{},[],{'result':'PASS'}):self.assertTrue(validate_refusal(d,'a'*32,12))
    def test_missing_db_not_created(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'state.db'
            with self.assertRaises(sqlite3.Error):db_counts(p)
            self.assertFalse(p.exists())
    def test_reader_is_closed(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'state.db'
            with closing(sqlite3.connect(p)) as db:
                db.executescript('CREATE TABLE session_admissions(id INTEGER);CREATE TABLE messages(role TEXT);')
            real=sqlite3.connect;created=[]
            def record(*a,**kw):
                con=real(*a,**kw);created.append(con);return con
            with patch('run_gateway_refusal_qa.sqlite3.connect',record):
                result=db_counts(p)
            self.assertEqual(result['admissions'],0);self.assertTrue(result['read_only'])
            self.assertEqual(len(created),1)
            with self.assertRaises(sqlite3.ProgrammingError):created[0].execute('SELECT 1')

if __name__=='__main__':unittest.main()
