"""Independent SQLite-shaped corruption/identity QA; no native Gateway execution.

Fixtures are fabricated only in TemporaryDirectory. Original native profiles and
live stores are never changed. The actual production LocalRecoveryInspector runs.
"""
from __future__ import annotations
from contextlib import closing
import hashlib
import importlib.util
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location('alaz_recovery_independent_qa',ROOT/'packages/claw-hermes/recovery_inspector.py')
MOD=importlib.util.module_from_spec(SPEC);sys.modules[SPEC.name]=MOD;SPEC.loader.exec_module(MOD)
RID='run_'+'a'*32;AID='b'*32;TOKEN='independent-local-fixture'
NOW=1000000.0

def encode(value):return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)
def sha(value):return hashlib.sha256(encode(value).encode('utf-8')).hexdigest()
def admission_sha(target,payload):return sha({'target':target,'payload':payload})

class StoreFixture:
    def __init__(self,home):
        self.home=home;self.body={'input':'Test ışık 42','model':'chosen-model'};self.key='own-key'
        self.scope=hashlib.sha256(('default\0'+TOKEN).encode()).hexdigest()
        self.payload={'text':self.body['input'],'api_turn_v1':{'history':None,'run_owner_scope':self.scope,'settings':{'requested_model':'chosen-model','requested_provider':None,'route':None}}}
        self.http={'run_id':RID,'status':'completed','admission_id':AID,'session_id':RID,'execution_generation':1,'output':'exact output','usage':{'total_tokens':12}}
        self.result={'result':{'completed':True,'final_response':'exact output','messages':[]},'usage':{'total_tokens':12}}
        self.row={'seq':1,'admission_id':AID,'request_id':RID,'principal_id':'api','target_session_id':RID,'lineage_json':encode([RID]),'payload_json':encode(self.payload),'payload_digest':admission_sha(RID,{'input':self.payload,'intent':'queue'}),'intent':'queue','status':'terminal','outcome':'completed','owner_epoch':1,'generation':1}
        with closing(sqlite3.connect(home/'state.db')) as c:
            c.executescript('CREATE TABLE runtime_epoch(singleton INTEGER PRIMARY KEY,epoch INTEGER,instance_id TEXT); CREATE TABLE session_admissions(seq INTEGER PRIMARY KEY,admission_id TEXT,request_id TEXT,principal_id TEXT,target_session_id TEXT,lineage_json TEXT,payload_json TEXT,payload_digest TEXT,intent TEXT,status TEXT,outcome TEXT,owner_epoch INTEGER,generation INTEGER); CREATE TABLE state_meta(key TEXT PRIMARY KEY,value TEXT);')
            c.execute('INSERT INTO runtime_epoch VALUES(1,2,?)',('owner-two',))
            c.execute('INSERT INTO session_admissions VALUES('+','.join('?' for _ in self.row)+')',tuple(self.row.values()))
            c.execute('INSERT INTO state_meta VALUES(?,?)',(MOD.RESULT+AID,encode(self.result)));c.commit()
        with closing(sqlite3.connect(home/'runs_idempotency.db')) as c:
            c.execute('CREATE TABLE run_idempotency(scope TEXT,idempotency_key TEXT,fingerprint TEXT,run_id TEXT,status_json TEXT,owner_pid INTEGER,owner_started INTEGER,retention_until REAL,acknowledged_at REAL,created_at REAL,updated_at REAL)')
            c.execute('INSERT INTO run_idempotency VALUES(?,?,?,?,?,?,?,?,?,?,?)',(self.scope,self.key,sha({'body':self.body,'gateway_session_key':''}),RID,encode({'run_id':RID,'status':'completed'}),1,1,0,None,NOW-10,NOW-1));c.commit()
        self.context=MOD.LocalRecoveryContext(home,TOKEN,2,'owner-two')
        self.inspector=MOD.LocalRecoveryInspector(self.context,clock=lambda:NOW)
    def inspect(self,**kw):return self.inspector.inspect(body=kw.get('body',self.body),idempotency_key=kw.get('key',self.key),observed=kw.get('observed',self.http))
    def sql(self,text,args=(),*,runs=False):
        with closing(sqlite3.connect(self.home/('runs_idempotency.db' if runs else 'state.db'))) as c:c.execute(text,args);c.commit()
    def change_payload(self,payload):
        self.sql('UPDATE session_admissions SET payload_json=?,payload_digest=?',(encode(payload),admission_sha(RID,{'input':payload,'intent':'queue'})))
    def archive(self):
        identity=MOD.IDENTITY+admission_sha(RID,{'principal':'api','request':RID})
        self.sql('INSERT INTO state_meta VALUES(?,?)',(identity,encode(AID)))
        self.sql('INSERT INTO state_meta VALUES(?,?)',(MOD.ARCHIVE+AID,encode(self.row)))
        self.sql('DELETE FROM session_admissions')
    def hashes(self):return {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in self.home.iterdir() if p.is_file()}

class InspectorIndependentQA(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.f=StoreFixture(Path(self.tmp.name))
    def rejected(self,**kw):
        before=self.f.hashes();r=self.f.inspect(**kw)
        self.assertEqual(r['classification'],'unverified',r);self.assertIs(r['canonicalVerified'],False)
        self.assertIs(r['requiresOperator'],True);self.assertIs(r['retryAllowed'],False);self.assertIs(r['repairAllowed'],False)
        self.assertIs(r['writesPerformed'],False);self.assertIs(r.get('taskSucceeded',False),False)
        self.assertEqual(before,self.f.hashes());self.assertNotIn(TOKEN,json.dumps(r));return r
    def test_valid_terminal_is_information_not_repair_permission(self):
        before=self.f.hashes();r=self.f.inspect();self.assertEqual(r['classification'],'canonical_terminal_verified');self.assertTrue(r['taskSucceeded'])
        self.assertFalse(r['retryAllowed']);self.assertFalse(r['repairAllowed']);self.assertEqual(before,self.f.hashes())
    def test_archived_terminal_not_orphan(self):
        self.f.archive();r=self.f.inspect();self.assertEqual(r['classification'],'canonical_terminal_verified');self.assertTrue(r['canonicalVerified'])
    def test_archive_missing_rejected(self):
        self.f.archive();self.f.sql('DELETE FROM state_meta WHERE key=?',(MOD.ARCHIVE+AID,));self.rejected()
    def test_archive_identity_wrong_run(self):
        self.f.archive();row=dict(self.f.row,request_id='run_'+'c'*32);self.f.sql('UPDATE state_meta SET value=? WHERE key=?',(encode(row),MOD.ARCHIVE+AID));self.rejected()
    def test_duplicate_live_and_archive_rejected(self):
        self.f.archive();self.f.sql('INSERT INTO session_admissions VALUES('+','.join('?' for _ in self.f.row)+')',tuple(self.f.row.values()));self.rejected()
    def test_payload_json_array_returns_unverified_not_exception(self):
        self.f.sql('UPDATE session_admissions SET payload_json=?',('[]',));self.rejected()
    def test_nested_api_array_returns_unverified_not_exception(self):
        self.f.sql('UPDATE session_admissions SET payload_json=?',(encode({'text':self.f.body['input'],'api_turn_v1':[]}),));self.rejected()
    def test_nested_api_null_returns_unverified_not_exception(self):
        self.f.sql('UPDATE session_admissions SET payload_json=?',(encode({'text':self.f.body['input'],'api_turn_v1':None}),));self.rejected()
    def test_duplicate_json_key_rejected(self):
        self.f.sql('UPDATE session_admissions SET payload_json=?',('{"text":"a","text":"b"}',));self.rejected()
    def test_changed_selected_model_rejected(self):
        payload=json.loads(encode(self.f.payload));payload['api_turn_v1']['settings']['requested_model']='other-model';self.f.change_payload(payload);self.rejected()
    def test_changed_native_scope_rejected(self):
        payload=json.loads(encode(self.f.payload));payload['api_turn_v1']['run_owner_scope']='c'*64;self.f.change_payload(payload);self.rejected()
    def test_wrong_context_scope_refuses_without_private_data(self):
        self.f.inspector=MOD.LocalRecoveryInspector(MOD.LocalRecoveryContext(self.f.home,'different-local-token',2,'owner-two'),clock=lambda:NOW)
        r=self.rejected();self.assertNotIn('runId',r);self.assertNotIn('requestFingerprint',r)
    def test_wrong_epoch_rejected(self):
        self.f.inspector=MOD.LocalRecoveryInspector(MOD.LocalRecoveryContext(self.f.home,TOKEN,1,'owner-two'),clock=lambda:NOW);self.rejected()
    def test_wrong_runtime_instance_rejected(self):
        self.f.inspector=MOD.LocalRecoveryInspector(MOD.LocalRecoveryContext(self.f.home,TOKEN,2,'foreign-instance'),clock=lambda:NOW);self.rejected()
    def test_observed_bool_generation_not_integer(self):
        self.rejected(observed={**self.f.http,'execution_generation':True})
    def test_observed_float_generation_not_integer(self):
        self.rejected(observed={**self.f.http,'execution_generation':1.0})
    def test_admission_from_future_epoch_rejected(self):
        self.f.sql('UPDATE session_admissions SET owner_epoch=3');self.rejected()
    def test_wrong_observed_session_rejected(self):self.rejected(observed={**self.f.http,'session_id':'another'})
    def test_changed_payload_requires_conflict(self):
        r=self.rejected(body={**self.f.body,'input':self.f.body['input']+' changed'});self.assertEqual(r['reason'],'request_payload_conflict')
    def test_expired_retention_not_deleted(self):
        self.f.sql('UPDATE run_idempotency SET retention_until=?',(NOW-1,),runs=True);r=self.rejected();self.assertEqual(r['reason'],'retention_expired')
    def test_expired_ack_not_deleted(self):
        self.f.sql('UPDATE run_idempotency SET acknowledged_at=?',(NOW-86400,),runs=True);self.rejected()
    def test_missing_key_not_new_work(self):
        self.f.sql('DELETE FROM run_idempotency',runs=True);self.rejected()
    def test_corrupt_stored_fingerprint_rejected(self):
        self.f.sql('UPDATE run_idempotency SET fingerprint=?',('invalid',),runs=True);self.rejected()
    def test_wrong_admission_digest_rejected(self):
        self.f.sql('UPDATE session_admissions SET payload_digest=?',('0'*64,));self.rejected()
    def test_missing_terminal_result_rejected(self):
        self.f.sql('DELETE FROM state_meta');self.rejected()
    def test_changed_output_rejected(self):self.rejected(observed={**self.f.http,'output':'invented'})
    def test_changed_usage_rejected(self):self.rejected(observed={**self.f.http,'usage':{'total_tokens':13}})
    def test_unknown_keeps_operator_and_no_retry(self):
        self.f.sql("UPDATE session_admissions SET status='unknown',outcome=NULL")
        r=self.f.inspect(observed={**self.f.http,'status':'unknown'});self.assertEqual(r['classification'],'execution_unknown');self.assertTrue(r['requiresOperator']);self.assertFalse(r['retryAllowed'])
    def test_no_admission_is_snapshot_only(self):
        self.f.sql('DELETE FROM session_admissions');self.f.sql('DELETE FROM state_meta')
        self.f.sql('UPDATE run_idempotency SET status_json=?',(encode({'run_id':RID,'status':'interrupted'}),),runs=True)
        r=self.f.inspect(observed={'run_id':RID,'status':'interrupted'});self.assertEqual(r['classification'],'reservation_without_admission_observed');self.assertTrue(r['snapshotOnly']);self.assertTrue(r['requiresOperator']);self.assertFalse(r['repairAllowed'])
    def test_missing_database_not_recreated(self):
        (self.f.home/'state.db').unlink();self.rejected();self.assertFalse((self.f.home/'state.db').exists())
    def test_corrupt_second_store_still_closes_connection(self):
        (self.f.home/'runs_idempotency.db').write_bytes(b'corrupt')
        original=sqlite3.connect;connections=[]
        def capture(*args,**kwargs):
            c=original(*args,**kwargs);connections.append(c);return c
        with patch.object(MOD.sqlite3,'connect',capture):self.rejected()
        self.assertEqual(len(connections),1)
        with self.assertRaises(sqlite3.ProgrammingError):connections[0].execute('SELECT 1')
    def test_success_reader_is_readonly_and_closed(self):
        original=sqlite3.connect;connections=[]
        def capture(*args,**kwargs):
            self.assertIn('?mode=ro',args[0]);self.assertIs(kwargs.get('uri'),True)
            c=original(*args,**kwargs);connections.append(c);return c
        before=self.f.hashes()
        with patch.object(MOD.sqlite3,'connect',capture):r=self.f.inspect()
        self.assertTrue(r['canonicalVerified']);self.assertEqual(before,self.f.hashes());self.assertEqual(len(connections),1)
        with self.assertRaises(sqlite3.ProgrammingError):connections[0].execute('SELECT 1')
    def test_query_failure_reader_is_closed(self):
        self.f.sql('DROP TABLE session_admissions');original=sqlite3.connect;connections=[]
        def capture(*args,**kwargs):
            c=original(*args,**kwargs);connections.append(c);return c
        with patch.object(MOD.sqlite3,'connect',capture):self.rejected()
        with self.assertRaises(sqlite3.ProgrammingError):connections[0].execute('SELECT 1')

if __name__=='__main__':unittest.main()
