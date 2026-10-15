"""Independent probe evidence checks; these tests do not execute Pi."""
import copy
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from run_native_admission import snapshot,validate_case,validate_boundary


def good_case():
    name='kill-after';nonce='a'*32
    sub={'id':9,'conversationId':1,'status':'done'}
    db={'integrity':'ok','read_only':True,'submissions':[sub],'binding_count':1,'effects':0}
    first={'phase':'seed','pid':10,'started':1,'finished':2,'exit_code':1,'intentional_kill':True,'reaped':True,'timed_out':False,
           'barrier':{'scenario':name,'phase':'seed','pid':10,'nonce':nonce,'boundary':'after-commit-before-ack','rootId':1}}
    last={'phase':'resume','pid':11,'started':3,'finished':4,'exit_code':0,'intentional_kill':False,'reaped':True,'timed_out':False,
          'receipt':{'result':'PASS','scenario':name,'nonce':nonce,'pid':11,'phase':'resume','checks':['recovery'],'modelCalls':0,'idle':True,'reused':True}}
    return {'scenario':name,'nonce':nonce,'processes':[first,last],'interim_database':copy.deepcopy(db),'final_database':db}

class AdmissionEvidenceTests(unittest.TestCase):
    def test_complete_owned_restart(self):self.assertEqual(validate_case(good_case()),[])
    def test_unknown_case(self):
        x=good_case();x['scenario']='oops';self.assertTrue(validate_case(x))
    def test_missing_phase(self):
        x=good_case();x['processes'].pop(0);self.assertTrue(validate_case(x))
    def test_normal_exit_is_not_crash(self):
        x=good_case();x['processes'][0]['exit_code']=0;self.assertTrue(validate_case(x))
    def test_overlap_rejected(self):
        x=good_case();x['processes'][1]['started']=1.5;self.assertTrue(validate_case(x))
    def test_wrong_nonce(self):
        x=good_case();x['processes'][0]['barrier']['nonce']='b'*32;self.assertTrue(validate_case(x))
    def test_wrong_receipt_pid(self):
        x=good_case();x['processes'][1]['receipt']['pid']=15;self.assertTrue(validate_case(x))
    def test_missing_fingerprint_pair(self):
        x=good_case();x['interim_database']['binding_count']=0;self.assertTrue(validate_case(x))
    def test_extra_native_admission(self):
        x=good_case();x['final_database']['submissions'].append({'id':10,'status':'done'});self.assertTrue(validate_case(x))
    def test_timeout_fails(self):
        x=good_case();x['processes'][1]['timed_out']=True;self.assertTrue(validate_case(x))
    def test_false_idle_fails(self):
        x=good_case();x['processes'][1]['receipt']['idle']=False;self.assertTrue(validate_case(x))
    def test_lost_submission_fails(self):
        x=good_case();x['final_database']['submissions'][0]['id']=20;self.assertTrue(validate_case(x))
    def test_boolean_count_fails(self):
        x=good_case();x['final_database']['binding_count']=True;self.assertTrue(validate_case(x))
    def test_malformed_fails(self):
        for x in [None,{},[],{'scenario':'kill-after'}]:self.assertTrue(validate_case(x))
    def test_missing_db_not_created(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)
            with self.assertRaises(sqlite3.Error):snapshot(path)
            self.assertFalse((path/'session.sqlite').exists())
    def test_json_encoded_kind_column(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)
            with closing(sqlite3.connect(path/'session.sqlite')) as db:
                db.executescript('CREATE TABLE entries(id INTEGER,record TEXT);CREATE TABLE submissions(id INTEGER,record TEXT);CREATE TABLE documents(record TEXT,kind TEXT,retired_at INTEGER);')
                db.execute('INSERT INTO documents VALUES(?,?,NULL)',(json.dumps({'kind':'alaz.admission.v1'}),json.dumps('alaz.admission.v1')))
                db.commit()
            self.assertEqual(snapshot(path)['binding_count'],1)

if __name__=='__main__':unittest.main()
