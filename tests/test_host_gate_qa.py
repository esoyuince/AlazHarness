"""Independent HYB005A ledger tests: REAL host code, synthetic SQLite owner.
These are not native Gateway tests. Faults intentionally mutate ONLY temp stores.
"""
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import threading
import unittest
ROOT_PATH=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT_PATH/'packages/claw-hermes'))
from host_gate import HostGateLedger,HostGatePolicy,HostGateError,ROOT,INTENT
from recovery_inspector import LocalRecoveryContext
from resolution_receipts import PREFIX,digest,key_digest

class SyntheticOwner:
    """The test substitutes native _execute_write; real native ownership is separate."""
    def __init__(self,path):
        self.db_path=str(path);self.lock=threading.RLock();self.fail_before_commit=False;self.lose_ack=False
    def _execute_write(self,fn):
        with self.lock, closing(sqlite3.connect(self.db_path,timeout=3)) as c:
            c.execute('BEGIN IMMEDIATE')
            try:
                result=fn(c)
                if self.fail_before_commit:raise sqlite3.OperationalError('fixture-before-commit')
                c.commit()
                if self.lose_ack:raise sqlite3.OperationalError('fixture-after-commit')
                return result
            except BaseException:
                c.rollback();raise

class GateFixture:
    def __init__(self,home):
        self.home=Path(home);self.now=1800000000.;self.body={'input':'Read the scoped fixture.','model':'test-model'}
        self.rid='a'*32
        with closing(sqlite3.connect(self.home/'state.db')) as db:
            db.executescript('CREATE TABLE state_meta(key TEXT PRIMARY KEY,value TEXT);CREATE TABLE runtime_epoch(singleton INTEGER PRIMARY KEY,epoch INTEGER,instance_id TEXT);INSERT INTO runtime_epoch VALUES(1,1,\'first-owner\');')
            db.commit()
        with closing(sqlite3.connect(self.home/'runs_idempotency.db')) as db:
            db.execute('CREATE TABLE run_idempotency(scope TEXT,idempotency_key TEXT,run_id TEXT)');db.commit()
        self.db=SyntheticOwner(self.home/'state.db');self.context=LocalRecoveryContext(self.home,'fixture-bearer',1,'first-owner')
        self.policy=HostGatePolicy(frozenset({'test-model'}));self.service=self.new()
    def new(self):return HostGateLedger(self.db,self.context,self.policy,clock=lambda:self.now)
    def issue(self,rid=None,body=None):return self.service.issue(rid or self.rid,self.body if body is None else body)
    def consume(self,document,body=None):return self.service.consume(document['key'],self.body if body is None else body)
    def sql(self,sql,args=(),replay=False):
        with closing(sqlite3.connect(self.home/('runs_idempotency.db' if replay else 'state.db'))) as db:
            db.execute(sql,args);db.commit()
    def rows(self):
        with closing(sqlite3.connect(self.home/'state.db')) as db:return db.execute('SELECT key,value FROM state_meta ORDER BY key').fetchall()
    def get(self,key):
        with closing(sqlite3.connect(self.home/'state.db')) as db:return json.loads(db.execute('SELECT value FROM state_meta WHERE key=?',(key,)).fetchone()[0])
    def set(self,key,row):self.sql('UPDATE state_meta SET value=? WHERE key=?',(json.dumps(row),key))
    @property
    def config_key(self):return ROOT+self.context.scope
    @property
    def intent_key(self):return INTENT+self.context.scope+'.'+self.rid
    def close_key(self,key):
        record={'scopeHash':self.context.scope,'keyHash':key_digest(key)}
        self.sql('INSERT INTO state_meta VALUES(?,?)',(PREFIX+'c'*32,json.dumps(record)))

class HostGateIndependentTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.f=GateFixture(self.tmp.name)
    def refused_without_write(self,fn):
        before=self.f.rows()
        with self.assertRaises(HostGateError):fn()
        self.assertEqual(before,self.f.rows())
    def test_same_request_document_replays_without_write(self):
        one=self.f.issue();before=self.f.rows();two=self.f.issue()
        self.assertTrue(two['replayed']);self.assertEqual(one['key'],two['key']);self.assertEqual(before,self.f.rows())
    def test_changed_body_same_id_refused(self):
        self.f.issue();self.refused_without_write(lambda:self.f.issue(body=self.f.body|{'input':'different'}))
    def test_issued_document_detached_from_stored_record(self):
        doc=self.f.issue();doc['dispatchState']='consumed';doc['fingerprint']='f'*64
        self.assertEqual(self.f.get(self.f.intent_key)['dispatchState'],'issued')
    def test_body_changed_after_issue_refused(self):
        doc=self.f.issue();self.f.body['input']='changed';self.refused_without_write(lambda:self.f.consume(doc))
    def test_consumed_is_not_success(self):
        result=self.f.consume(self.f.issue());self.assertTrue(result['handoffClaimed']);self.assertFalse(result['taskSucceeded']);self.assertFalse(result['retryAllowed'])
    def test_consumed_record_refuses_duplicate(self):
        doc=self.f.issue();self.f.consume(doc);self.refused_without_write(lambda:self.f.consume(doc))
    def test_reopened_same_owner_cannot_consume_twice(self):
        doc=self.f.issue();self.f.consume(doc);self.f.service=self.f.new();self.refused_without_write(lambda:self.f.consume(doc))
    def test_replay_row_pruning_does_not_reenable_consumed(self):
        doc=self.f.issue();self.f.consume(doc)
        self.f.sql('INSERT INTO run_idempotency VALUES(?,?,?)',(self.f.context.scope,doc['key'],'run_'+'1'*32),True)
        self.f.sql('DELETE FROM run_idempotency',replay=True)
        self.refused_without_write(lambda:self.f.consume(doc))
    def test_legacy_unissued_key_refused(self):self.refused_without_write(lambda:self.f.service.consume('old-key',self.f.body))
    def test_forged_well_formed_unissued_key_refused(self):self.refused_without_write(lambda:self.f.service.consume('ah1-'+'b'*32+'-'+'c'*32,self.f.body))
    def test_wrong_namespace_refused(self):
        d=self.f.issue();d['key']='ah1-'+'f'*32+'-'+self.f.rid;self.refused_without_write(lambda:self.f.consume(d))
    def test_native_existing_key_refuses_dispatch(self):
        d=self.f.issue();self.f.sql('INSERT INTO run_idempotency VALUES(?,?,?)',(self.f.context.scope,d['key'],'run_'+'1'*32),True)
        self.refused_without_write(lambda:self.f.consume(d))
    def test_closed_key_refuses_without_replay_row(self):
        d=self.f.issue();self.f.close_key(d['key']);self.refused_without_write(lambda:self.f.consume(d))
    def test_corrupt_history_refuses(self):
        d=self.f.issue();self.f.sql('INSERT INTO state_meta VALUES(?,?)',(PREFIX+'b'*32,'not-json'));self.refused_without_write(lambda:self.f.consume(d))
    def test_missing_replay_db_does_not_create_it(self):
        d=self.f.issue();p=self.f.home/'runs_idempotency.db';p.unlink();self.refused_without_write(lambda:self.f.consume(d));self.assertFalse(p.exists())
    def test_expired_issued_document_refused(self):
        d=self.f.issue();self.f.now+=301;self.refused_without_write(lambda:self.f.consume(d))
    def test_clock_rollback_refused(self):
        d=self.f.issue();self.f.now-=1;self.refused_without_write(lambda:self.f.consume(d))
    def test_new_epoch_does_not_revive_issued_intent(self):
        d=self.f.issue();self.f.sql("UPDATE runtime_epoch SET epoch=2,instance_id='second-owner'")
        self.f.context=replace(self.f.context,epoch=2,instance_id='second-owner');self.f.service=self.f.new()
        self.refused_without_write(lambda:self.f.consume(d))
    def test_old_owner_context_refused(self):
        d=self.f.issue();self.f.sql('UPDATE runtime_epoch SET epoch=2');self.refused_without_write(lambda:self.f.consume(d))
    def test_foreign_scope_refused(self):
        d=self.f.issue();self.f.context=replace(self.f.context,api_token='other-bearer');self.f.service=self.f.new();self.refused_without_write(lambda:self.f.consume(d))
    def test_unknown_request_fields_refused(self):self.refused_without_write(lambda:self.f.issue(body=self.f.body|{'budget':99}))
    def test_explicit_session_refused(self):self.refused_without_write(lambda:self.f.issue(body=self.f.body|{'session_id':'existing'}))
    def test_missing_model_refused(self):self.refused_without_write(lambda:self.f.issue(body={'input':'x'}))
    def test_foreign_model_refused(self):self.refused_without_write(lambda:self.f.issue(body=self.f.body|{'model':'untrusted'}))
    def test_policy_changed_model_rechecked_before_consume(self):
        d=self.f.issue();self.f.policy=HostGatePolicy(frozenset({'different-model'}));self.f.service=self.f.new();self.refused_without_write(lambda:self.f.consume(d))
    def test_count_limit_refuses_another_dispatch(self):
        self.f.policy=HostGatePolicy(frozenset({'test-model'}),max_dispatches=1);self.f.service=self.f.new()
        self.f.consume(self.f.issue());second=self.f.issue('b'*32);self.refused_without_write(lambda:self.f.consume(second))
    def test_issue_count_limit_refused(self):
        self.f.policy=HostGatePolicy(frozenset({'test-model'}),max_issued=1);self.f.service=self.f.new();self.f.issue();self.refused_without_write(lambda:self.f.issue('b'*32))
    def test_before_commit_failure_rolls_back(self):
        d=self.f.issue();self.f.db.fail_before_commit=True;self.refused_without_write(lambda:self.f.consume(d))
        self.f.db.fail_before_commit=False;self.assertTrue(self.f.consume(d)['handoffClaimed'])
    def test_after_commit_ack_loss_does_not_refund(self):
        d=self.f.issue();self.f.db.lose_ack=True
        with self.assertRaises(HostGateError):self.f.consume(d)
        self.f.db.lose_ack=False;self.assertEqual(self.f.get(self.f.intent_key)['dispatchState'],'consumed');self.refused_without_write(lambda:self.f.consume(d))
    def test_twenty_concurrent_consumers_only_one_claim(self):
        d=self.f.issue()
        def call(_):
            try:return self.f.consume(d)['handoffClaimed']
            except HostGateError:return False
        with ThreadPoolExecutor(max_workers=20) as pool:answers=list(pool.map(call,range(20)))
        self.assertEqual(sum(answers),1);self.assertEqual(self.f.get(self.f.config_key)['spent'],1)
    def test_twenty_concurrent_issuers_only_one_issue(self):
        with ThreadPoolExecutor(max_workers=20) as pool:answers=list(pool.map(lambda _:self.f.issue(),range(20)))
        self.assertEqual(sum(not x['replayed'] for x in answers),1);self.assertEqual(len({x['key'] for x in answers}),1)
    def test_digest_corruption_refused(self):
        d=self.f.issue();row=self.f.get(self.f.intent_key);row['fingerprint']='f'*64;self.f.set(self.f.intent_key,row);self.refused_without_write(lambda:self.f.consume(d))
    def test_written_table_trigger_refused(self):
        d=self.f.issue();self.f.sql("CREATE TRIGGER t AFTER UPDATE ON state_meta BEGIN SELECT 1; END");self.refused_without_write(lambda:self.f.consume(d))
    def test_deleted_consumed_intent_not_reissued(self):
        d=self.f.issue();self.f.consume(d);self.f.sql('DELETE FROM state_meta WHERE key=?',(self.f.intent_key,))
        self.refused_without_write(lambda:self.f.issue())
    def test_missing_configuration_not_recreated_over_history(self):
        self.f.issue();self.f.sql('DELETE FROM state_meta WHERE key=?',(self.f.config_key,));self.refused_without_write(lambda:self.f.issue('b'*32))
    def test_dishonest_counter_not_accepted(self):
        self.f.issue();cfg=self.f.get(self.f.config_key);cfg['issued']=0;self.f.set(self.f.config_key,cfg)
        self.refused_without_write(lambda:self.f.issue('b'*32))

if __name__=='__main__':unittest.main()
