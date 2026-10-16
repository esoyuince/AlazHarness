"""Offline native-owner substitute; actual Gateway evidence is separate."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from dataclasses import replace
import json
from pathlib import Path
import sqlite3,sys,tempfile,threading,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'packages/claw-hermes'))
from execution_budget import ExecutionPolicy,ExecutionLedger,ExecutionDenied,CONFIG,CLAIM,seal
from recovery_inspector import LocalRecoveryContext
from execution_boundary import scoped_file,ExecutionBoundary

class TestOwner:
    def __init__(self,path):self.db_path=str(path);self.lock=threading.RLock();self.lose_ack=False;self.pre_fail=False
    def _execute_write(self,fn):
        with self.lock,closing(sqlite3.connect(self.db_path,timeout=3)) as c:
            c.execute('BEGIN IMMEDIATE')
            try:
                value=fn(c)
                if self.pre_fail:raise sqlite3.OperationalError('test precommit')
                c.commit()
                if self.lose_ack:raise sqlite3.OperationalError('test lost commit reply')
                return value
            except BaseException:c.rollback();raise

class BudgetTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.home=Path(self.tmp.name)
        with closing(sqlite3.connect(self.home/'state.db')) as c:
            c.executescript("CREATE TABLE state_meta(key TEXT PRIMARY KEY,value TEXT);CREATE TABLE runtime_epoch(singleton INTEGER PRIMARY KEY,epoch INTEGER,instance_id TEXT);INSERT INTO runtime_epoch VALUES(1,1,'first');");c.commit()
        self.owner=TestOwner(self.home/'state.db');self.context=LocalRecoveryContext(self.home,'local-test-token',1,'first')
        self.policy=ExecutionPolicy('test',3,2,100,20,360,1000,1000000,2000000);self.ledger=self.make();self.ledger.initialize()
    def make(self):return ExecutionLedger(self.owner,self.context,self.policy)
    def sql(self,statement,args=()):
        with closing(sqlite3.connect(self.home/'state.db')) as c:c.execute(statement,args);c.commit()
    def rows(self):
        with closing(sqlite3.connect(self.home/'state.db')) as c:return c.execute('SELECT key,value FROM state_meta ORDER BY key').fetchall()
    def claim(self):return self.ledger.claim('provider','a'*64)
    def test_per_attempt_conservative_exposure(self):
        t=self.claim();self.assertEqual(t['tokens'],120);self.assertEqual(t['costMicrousd'],140)
    def test_usage_does_not_refund(self):
        t=self.claim();self.ledger.settle(t['ticket'],{'input_tokens':1,'output_tokens':1},'response');s=self.ledger.snapshot();self.assertEqual(s['reservedTokens'],120);self.assertEqual(s['reservedCostMicrousd'],140)
    def test_absent_usage_retains_exposure(self):
        t=self.claim();self.ledger.settle(t['ticket'],None,'unknown_usage');self.assertEqual(self.ledger.snapshot()['reservedTokens'],120)
    def test_attempt_cap_blocks(self):
        for _ in range(3):self.claim()
        with self.assertRaisesRegex(ExecutionDenied,'provider_attempt_limit'):self.claim()
    def test_tool_cap_separate(self):
        for _ in range(2):self.ledger.claim('read_file','b'*64)
        with self.assertRaisesRegex(ExecutionDenied,'tool_attempt_limit'):self.ledger.claim('read_file','b'*64)
        self.assertEqual(self.ledger.snapshot()['providerCalls'],0)
    def test_restart_no_refund(self):
        self.claim();other=self.make();other.initialize();self.assertEqual(other.snapshot()['providerCalls'],1)
    def test_new_epoch_retains_budget(self):
        self.claim();self.sql("UPDATE runtime_epoch SET epoch=2,instance_id='second'");self.context=replace(self.context,epoch=2,instance_id='second');other=self.make();other.initialize();self.assertEqual(other.snapshot()['providerCalls'],1)
    def test_stale_owner_denied(self):
        self.sql('UPDATE runtime_epoch SET epoch=2')
        with self.assertRaisesRegex(ExecutionDenied,'stale_execution_owner'):self.claim()
    def test_changed_policy_not_reset(self):
        self.policy=replace(self.policy,max_provider_calls=4)
        with self.assertRaisesRegex(ExecutionDenied,'execution_policy_or_scope_changed'):self.make().initialize()
    def test_deleted_claim_refuses(self):
        t=self.claim();self.sql('DELETE FROM state_meta WHERE key=?',(CLAIM+self.context.scope+'.'+t['ticket'],))
        with self.assertRaises(ExecutionDenied):self.claim()
    def test_missing_config_not_reinitialized(self):
        self.claim();self.sql('DELETE FROM state_meta WHERE key=?',(CONFIG+self.context.scope,))
        with self.assertRaisesRegex(ExecutionDenied,'execution_budget_missing'):self.make().initialize()
    def test_corrupt_counter_refuses(self):
        k=CONFIG+self.context.scope;row=json.loads(dict(self.rows())[k]);row['providerCalls']=1;self.sql('UPDATE state_meta SET value=? WHERE key=?',(json.dumps(seal(row)),k))
        with self.assertRaisesRegex(ExecutionDenied,'execution_history_inconsistent'):self.claim()
    def test_bool_counter_refuses(self):
        k=CONFIG+self.context.scope;row=json.loads(dict(self.rows())[k]);row['providerCalls']=False;self.sql('UPDATE state_meta SET value=? WHERE key=?',(json.dumps(seal(row)),k))
        with self.assertRaises(ExecutionDenied):self.claim()
    def test_no_network_authority_in_ticket(self):
        t=self.claim();self.assertNotIn('retryAllowed',t);self.assertNotIn('success',t)
    def test_twenty_concurrent_claims_bounded(self):
        def attempt(_):
            try:self.claim();return 1
            except ExecutionDenied:return 0
        with ThreadPoolExecutor(max_workers=20) as pool:results=list(pool.map(attempt,range(20)))
        self.assertEqual(sum(results),3);self.assertEqual(self.ledger.snapshot()['providerCalls'],3)
    def test_precommit_failure_no_charge(self):
        before=self.rows();self.owner.pre_fail=True
        with self.assertRaisesRegex(ExecutionDenied,'execution_storage_unconfirmed'):self.claim()
        self.owner.pre_fail=False;self.assertEqual(before,self.rows())
    def test_lost_commit_ack_keeps_charge(self):
        self.owner.lose_ack=True
        with self.assertRaises(ExecutionDenied):self.claim()
        self.owner.lose_ack=False;self.assertEqual(self.ledger.snapshot()['providerCalls'],1)
    def test_invalid_usage_quarantines(self):
        t=self.claim()
        with self.assertRaisesRegex(ExecutionDenied,'provider_usage_out_of_contract'):self.ledger.settle(t['ticket'],{'input_tokens':101,'output_tokens':1},'response')
        with self.assertRaisesRegex(ExecutionDenied,'execution_budget_quarantined'):self.claim()
        self.assertEqual(self.ledger.snapshot()['reservedTokens'],120)
    def test_identical_settlement_idempotent(self):
        t=self.claim();a=self.ledger.settle(t['ticket'],None,'transport_error');b=self.ledger.settle(t['ticket'],None,'transport_error');self.assertEqual(a,b)
    def test_conflicting_settlement_refused(self):
        t=self.claim();self.ledger.settle(t['ticket'],None,'transport_error')
        with self.assertRaisesRegex(ExecutionDenied,'execution_settlement_conflict'):self.ledger.settle(t['ticket'],None,'response')
    def test_bad_ticket_refused(self):
        with self.assertRaises(ExecutionDenied):self.ledger.settle(True,None,'response')
    def test_unknown_usage_not_zero(self):
        t=self.claim();self.assertIsNone(t['usage']);self.assertEqual(self.ledger.snapshot()['reservedCostMicrousd'],140)
    def test_trigger_refused(self):
        self.sql('CREATE TRIGGER t AFTER INSERT ON state_meta BEGIN SELECT 1; END')
        with self.assertRaises(ExecutionDenied):self.claim()
    def test_foreign_database_refused(self):
        other=TestOwner(self.home/'other.db')
        with self.assertRaises(ExecutionDenied):ExecutionLedger(other,self.context,self.policy)
        self.assertFalse((self.home/'other.db').exists())

class PolicyAndPathTests(unittest.TestCase):
    def test_unknown_price_not_zero(self):
        with self.assertRaises(ExecutionDenied):ExecutionPolicy('test',1,1,10,10,20,100,None,0)
    def test_bool_and_float_limits_refused(self):
        for value in (True,1.0,-1,float('nan'),float('inf')):
            with self.subTest(value=value),self.assertRaises(ExecutionDenied):ExecutionPolicy('test',value,1,10,10,20,100,1,1)
    def test_ceil_price_no_float(self):
        p=ExecutionPolicy('test',1,1,1,1,2,1,1,1);self.assertEqual(p.cost_per_attempt,1)
    def test_free_tariff_requires_explicit_integer(self):
        self.assertEqual(ExecutionPolicy('test',1,1,10,10,20,0,0,0).cost_per_attempt,0)
    def test_read_exact_plain_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'allowed.txt';p.write_text('fixture');self.assertEqual(scoped_file(str(p),frozenset({p})),str(p.resolve()))
    def test_relative_or_network_paths_refuse(self):
        for s in ('relative.txt','//host/share.txt','\\server\\share.txt'):
            with self.subTest(path=s),self.assertRaises(ExecutionDenied):scoped_file(s,frozenset())
    def test_outside_allowed_file_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'outside.txt';p.write_text('fixture')
            with self.assertRaises(ExecutionDenied):scoped_file(str(p),frozenset())
    def test_provider_usage_type(self):
        for v in ({'prompt_tokens':True,'completion_tokens':1},{'prompt_tokens':1,'completion_tokens':1,'total_tokens':3},None):
            with self.subTest(value=v),self.assertRaises(ExecutionDenied):ExecutionBoundary._usage(v)
if __name__=='__main__':unittest.main()
