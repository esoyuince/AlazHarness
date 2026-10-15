"""Synthetic-schema unit tests, not native Gateway execution evidence."""
from contextlib import closing
import dataclasses
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'packages/claw-hermes'))
import recovery_inspector as ri

class InspectorTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.home=Path(self.tmp.name);self.now=100000.0
        self.rid='run_'+'a'*32;self.aid='b'*32;self.body={'input':'Read ışık 😀'};self.key='one-request'
        self.context=ri.LocalRecoveryContext(self.home,'test-only-bearer-credential',2,'new-instance')
        self.inspector=ri.LocalRecoveryInspector(self.context,clock=lambda:self.now)
        self.payload={'text':self.body['input'],'api_turn_v1':{'run_owner_scope':self.context.scope}}
        digest=ri._KEYS.admission_fingerprint(canonical_target=self.rid,payload={'input':self.payload,'intent':'queue'})
        self.http={'run_id':self.rid,'session_id':self.rid,'admission_id':self.aid,'execution_generation':1,
                   'status':'completed','output':'native-output','usage':{'input_tokens':12}}
        self.saved={'result':{'completed':True,'final_response':'native-output'},'usage':self.http['usage']}
        with closing(sqlite3.connect(self.home/'state.db')) as c:
            c.executescript("""CREATE TABLE runtime_epoch(singleton INTEGER PRIMARY KEY,epoch INTEGER,instance_id TEXT);
            CREATE TABLE session_admissions(seq INTEGER PRIMARY KEY,admission_id TEXT,request_id TEXT,principal_id TEXT,
            target_session_id TEXT,lineage_json TEXT,payload_json TEXT,payload_digest TEXT,intent TEXT,status TEXT,
            outcome TEXT,owner_epoch INTEGER,generation INTEGER);
            CREATE TABLE state_meta(key TEXT PRIMARY KEY,value TEXT);""")
            c.execute('INSERT INTO runtime_epoch VALUES(1,2,?)',('new-instance',))
            c.execute('INSERT INTO session_admissions VALUES(1,?,?,?,?,?,?,?,?,?,?,?,?)',
              (self.aid,self.rid,'api',self.rid,json.dumps([self.rid]),ri._json(self.payload),digest,'queue','terminal','completed',1,1))
            c.execute('INSERT INTO state_meta VALUES(?,?)',(ri.RESULT+self.aid,ri._json(self.saved)));c.commit()
        with closing(sqlite3.connect(self.home/'runs_idempotency.db')) as c:
            c.execute("""CREATE TABLE run_idempotency(scope TEXT,idempotency_key TEXT,fingerprint TEXT,run_id TEXT,
             status_json TEXT,owner_pid INTEGER,owner_started INTEGER,retention_until REAL,acknowledged_at REAL,created_at REAL,updated_at REAL)""")
            c.execute('INSERT INTO run_idempotency VALUES(?,?,?,?,?,100,1,0,NULL,?,?)',
              (self.context.scope,self.key,ri.request_fingerprint(self.body),self.rid,ri._json(self.http),self.now,self.now));c.commit()
    def query(self,**kwargs):return self.inspector.inspect(**({'body':self.body,'idempotency_key':self.key,'observed':self.http}|kwargs))
    def sql(self,statement,args=(),replay=False):
        with closing(sqlite3.connect(self.home/('runs_idempotency.db' if replay else 'state.db'))) as c:c.execute(statement,args);c.commit()
    def denied(self,reason,**kwargs):
        r=self.query(**kwargs);self.assertEqual(r['classification'],'unverified',r);self.assertEqual(r['reason'],reason)
        self.assertFalse(r['canonicalVerified']);self.assertTrue(r['requiresOperator']);self.assertFalse(r['retryAllowed']);self.assertFalse(r['repairAllowed']);return r
    def test_completed_exact_result(self):
        r=self.query();self.assertEqual(r['classification'],'canonical_terminal_verified');self.assertTrue(r['taskSucceeded']);self.assertTrue(r['canonicalVerified']);self.assertFalse(r['retryAllowed'])
    def test_unknown_not_replayed(self):
        self.sql("UPDATE session_admissions SET status='unknown',outcome=NULL");self.http['status']='unknown'
        r=self.query();self.assertEqual(r['classification'],'execution_unknown');self.assertTrue(r['requiresOperator'])
    def test_active_not_terminal(self):
        self.sql("UPDATE session_admissions SET status='started',outcome=NULL");self.http['status']='running'
        r=self.query();self.assertEqual(r['classification'],'in_progress');self.assertFalse(r['retryAllowed'])
    def test_waiting_approval(self):
        self.sql("UPDATE session_admissions SET status='started',outcome=NULL");self.http['status']='waiting_for_approval'
        r=self.query();self.assertTrue(r['requiresOperator']);self.assertTrue(r['canonicalVerified'])
    def test_reservation_only_not_success(self):
        self.sql('DELETE FROM session_admissions');self.sql('DELETE FROM state_meta');self.http={'run_id':self.rid,'status':'interrupted'}
        self.sql('UPDATE run_idempotency SET status_json=?',(ri._json(self.http),),True)
        r=self.query();self.assertEqual(r['classification'],'reservation_without_admission_observed');self.assertFalse(r['canonicalVerified']);self.assertTrue(r['requiresOperator'])
    def test_missing_reservation_is_not_never_submitted(self):self.sql('DELETE FROM run_idempotency',replay=True);self.denied('lookup_unavailable')
    def test_wrong_bearer_no_data_disclosure(self):
        self.inspector=ri.LocalRecoveryInspector(dataclasses.replace(self.context,api_token='different-credential'),clock=lambda:self.now)
        r=self.denied('lookup_unavailable');self.assertNotIn('runId',r);self.assertNotIn('native-output',json.dumps(r))
    def test_wrong_key(self):self.denied('lookup_unavailable',idempotency_key='different')
    def test_wrong_run(self):self.denied('run_identity_mismatch',observed=self.http|{'run_id':'run_'+'c'*32})
    def test_different_body(self):self.denied('request_payload_conflict',body={'input':'different'})
    def test_unicode_no_normalization(self):self.denied('request_payload_conflict',body={'input':'Read isik 😀'})
    def test_unknown_body_fields(self):self.denied('unsupported_request_shape',body=self.body|{'gateway_session_key':'other'})
    def test_nonstring_input(self):self.denied('invalid_request',body={'input':False})
    def test_wrong_epoch(self):
        self.inspector=ri.LocalRecoveryInspector(dataclasses.replace(self.context,epoch=1),clock=lambda:self.now);self.denied('stale_epoch')
    def test_wrong_instance(self):
        self.inspector=ri.LocalRecoveryInspector(dataclasses.replace(self.context,instance_id='old'),clock=lambda:self.now);self.denied('stale_epoch')
    def test_bool_http_generation_rejected(self):self.denied('projection_identity_mismatch',observed=self.http|{'execution_generation':True})
    def test_wrong_generation(self):self.denied('projection_identity_mismatch',observed=self.http|{'execution_generation':2})
    def test_forged_admission(self):self.denied('projection_identity_mismatch',observed=self.http|{'admission_id':'c'*32})
    def test_forged_scope(self):
        payload={**self.payload,'api_turn_v1':{'run_owner_scope':'e'*64}};self.sql('UPDATE session_admissions SET payload_json=?',(ri._json(payload),));self.denied('scope_mismatch')
    def test_corrupt_digest(self):self.sql('UPDATE session_admissions SET payload_digest=?',('d'*64,));self.denied('admission_digest_mismatch')
    def test_missing_final_result(self):self.sql('DELETE FROM state_meta');self.denied('missing_terminal_result')
    def test_wrong_output(self):self.denied('terminal_result_mismatch',observed=self.http|{'output':'invented'})
    def test_wrong_usage(self):self.denied('terminal_result_mismatch',observed=self.http|{'usage':{'input_tokens':13}})
    def test_partial_not_success(self):
        self.saved['result'].update(completed=False,partial=True);self.sql('UPDATE state_meta SET value=?',(ri._json(self.saved),));self.http['status']='failed'
        r=self.query();self.assertEqual(r['outcome'],'failed');self.assertFalse(r['taskSucceeded'])
    def test_expired_retention(self):self.sql('UPDATE run_idempotency SET retention_until=?',(self.now-1,),True);self.denied('retention_expired')
    def test_acknowledged_expired(self):self.sql('UPDATE run_idempotency SET acknowledged_at=1',replay=True);self.denied('retention_expired')
    def test_default_retention_expired(self):self.sql('UPDATE run_idempotency SET updated_at=1',replay=True);self.denied('retention_expired')
    def test_malformed_json(self):self.sql('UPDATE run_idempotency SET status_json=?',('{broken',),True);self.denied('malformed_evidence')
    def test_duplicate_json_keys(self):self.sql('UPDATE run_idempotency SET status_json=?',('{"run_id":"a","run_id":"b"}',),True);self.denied('duplicate_json_key')
    def test_nonfinite_json(self):self.sql('UPDATE run_idempotency SET status_json=?',('{"run_id":NaN}',),True);self.denied('nonfinite_json')
    def test_missing_database_not_created(self):
        p=self.home/'runs_idempotency.db';p.unlink();self.denied('storage_unavailable');self.assertFalse(p.exists())
    def test_view_not_trusted_table(self):
        self.sql('ALTER TABLE runtime_epoch RENAME TO original_epoch');self.sql('CREATE VIEW runtime_epoch AS SELECT * FROM original_epoch');self.denied('unsupported_schema')
    def test_retired_result_not_orphan(self):
        with closing(sqlite3.connect(self.home/'state.db')) as c:
            c.row_factory=sqlite3.Row;row=dict(c.execute('SELECT * FROM session_admissions').fetchone())
        identity=ri.IDENTITY+ri._KEYS.admission_fingerprint(canonical_target=self.rid,payload={'principal':'api','request':self.rid})
        self.sql('INSERT INTO state_meta VALUES(?,?)',(identity,ri._json(self.aid)));self.sql('INSERT INTO state_meta VALUES(?,?)',(ri.ARCHIVE+self.aid,ri._json(row)));self.sql('DELETE FROM session_admissions')
        self.assertEqual(self.query()['classification'],'canonical_terminal_verified')
    def test_missing_archive_not_orphan(self):
        identity=ri.IDENTITY+ri._KEYS.admission_fingerprint(canonical_target=self.rid,payload={'principal':'api','request':self.rid})
        self.sql('INSERT INTO state_meta VALUES(?,?)',(identity,ri._json(self.aid)));self.sql('DELETE FROM session_admissions');self.denied('missing_retired_admission')
    def test_no_database_bytes_changed(self):
        files=list(self.home.glob('*.db'));before=[p.read_bytes() for p in files];self.query();self.assertEqual(before,[p.read_bytes() for p in files])
    def test_connection_closed_and_no_writes(self):
        original=sqlite3.connect;connections=[];statements=[]
        def connect(*a,**kw):
            c=original(*a,**kw);c.set_trace_callback(statements.append);connections.append(c);return c
        with patch('recovery_inspector.sqlite3.connect',connect):self.assertTrue(self.query()['canonicalVerified'])
        self.assertEqual(len(connections),1)
        for c in connections:
            with self.assertRaises(sqlite3.ProgrammingError):c.execute('SELECT 1')
        self.assertFalse(any(s.lstrip().split()[0].upper() in {'INSERT','UPDATE','DELETE','CREATE','DROP','REPLACE'} for s in statements))
    def test_epoch_change_during_read_rejected(self):
        original=sqlite3.connect;outer=self
        class Changing(sqlite3.Connection):
            def rollback(self):
                super().rollback()
                with closing(original(outer.home/'state.db')) as c:c.execute('UPDATE runtime_epoch SET epoch=3');c.commit()
        def connect(*a,**kw):return original(*a,**kw,factory=Changing)
        with patch('recovery_inspector.sqlite3.connect',connect):self.denied('concurrent_state_change')
    def test_context_is_immutable_and_hides_token(self):
        self.assertNotIn(self.context.api_token,repr(self.context))
        with self.assertRaises(dataclasses.FrozenInstanceError):self.context.epoch=3
    def test_bool_epoch_refused(self):
        with self.assertRaises(ValueError):dataclasses.replace(self.context,epoch=True)
    def test_named_profile_not_silently_accepted(self):
        with self.assertRaises(ValueError):dataclasses.replace(self.context,profile_name='other')

if __name__=='__main__':unittest.main()
