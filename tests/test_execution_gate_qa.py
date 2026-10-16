"""Independent real ExecutionLedger tests with a SYNTHETIC SQLite write owner.
No native Gateway/provider/tool is executed. Faults affect only fresh temp stores.
"""
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from dataclasses import replace
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'packages/claw-hermes'))
sys.path.insert(0,str(ROOT/'tests'))
from test_host_gate_qa import GateFixture,SyntheticOwner
from execution_budget import ExecutionPolicy,ExecutionLedger,ExecutionDenied,CONFIG,CLAIM,seal


def policy(**changes):
    return ExecutionPolicy(**(dict(model='fixture-model',max_provider_calls=3,max_tool_calls=2,
        input_ceiling_tokens=100,output_ceiling_tokens=20,total_token_limit=360,
        total_cost_microusd=900,input_rate_microusd_per_million=2_000_000,
        output_rate_microusd_per_million=5_000_000)|changes))


class BudgetIndependentTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.f=GateFixture(self.tmp.name);self.p=policy();self.b=self.make();self.b.initialize()
    def make(self):return ExecutionLedger(self.f.db,self.f.context,self.p)
    def claim(self,kind='provider'):return self.b.claim(kind,'a'*64)
    def rows(self):return self.f.rows()
    def configure(self,**changes):
        # Each test gets fresh state; deliberate policy substitutions elsewhere must refuse.
        self.f.sql('DELETE FROM state_meta');self.p=policy(**changes);self.b=self.make();self.b.initialize()
    def refuse_unchanged(self,fn,pattern=None):
        before=self.rows()
        with self.assertRaisesRegex(ExecutionDenied,pattern or '.+'):fn()
        self.assertEqual(self.rows(),before)
    def test_full_exposure_reserved_before_settlement(self):
        r=self.claim();s=self.b.snapshot()
        self.assertEqual((r['tokens'],r['costMicrousd']),(120,300))
        self.assertEqual((s['providerCalls'],s['reservedTokens'],s['reservedCostMicrousd']),(1,120,300))
    def test_tool_claim_separate_and_zero_model_exposure(self):
        r=self.claim('read_file');s=self.b.snapshot()
        self.assertEqual((r['tokens'],r['costMicrousd']),(0,0));self.assertEqual((s['toolCalls'],s['providerCalls']),(1,0))
    def test_low_usage_never_refunds_reservation(self):
        r=self.claim();self.b.settle(r['ticket'],{'input_tokens':1,'output_tokens':1},'response')
        self.assertEqual(self.b.snapshot()['reservedCostMicrousd'],300);self.assertEqual(self.b.snapshot()['reservedTokens'],120)
    def test_transport_failure_never_refunds(self):
        r=self.claim();self.b.settle(r['ticket'],None,'transport_error');self.assertEqual(self.b.snapshot()['providerCalls'],1)
    def test_unknown_usage_stays_full_exposure(self):
        r=self.claim();self.b.settle(r['ticket'],None,'unknown_usage');self.assertEqual(self.b.snapshot()['reservedCostMicrousd'],300)
    def test_three_provider_attempts_not_four(self):
        for _ in range(3):self.claim()
        self.refuse_unchanged(self.claim,'provider_attempt_limit')
    def test_tools_hit_their_own_cap(self):
        self.claim('read_file');self.claim('read_file');self.refuse_unchanged(lambda:self.claim('read_file'),'tool_attempt_limit')
    def test_token_ceiling_stops_before_claim(self):
        self.configure(total_token_limit=119);self.refuse_unchanged(self.claim,'token_exposure_limit')
    def test_cost_ceiling_stops_before_claim(self):
        self.configure(total_cost_microusd=299);self.refuse_unchanged(self.claim,'cost_exposure_limit')
    def test_zero_call_allowance_does_not_mean_unlimited(self):
        self.configure(max_provider_calls=0);self.refuse_unchanged(self.claim,'provider_attempt_limit')
    def test_zero_explicit_tariff_can_represent_free_fixture(self):
        self.configure(input_rate_microusd_per_million=0,output_rate_microusd_per_million=0,total_cost_microusd=0)
        self.assertEqual(self.claim()['costMicrousd'],0)
    def test_rounding_is_up_not_down(self):
        p=policy(input_ceiling_tokens=1,output_ceiling_tokens=1,input_rate_microusd_per_million=1,output_rate_microusd_per_million=0)
        self.assertEqual(p.cost_per_attempt,1)
    def test_initialize_cannot_reset_live_counters(self):
        self.claim();before=self.rows();self.b.initialize();self.assertEqual(self.rows(),before)
    def test_missing_budget_refuses_claim(self):
        self.f.sql('DELETE FROM state_meta');self.refuse_unchanged(self.claim,'execution_budget_missing')
    def test_missing_config_over_retained_claims_refused(self):
        self.claim();self.f.sql('DELETE FROM state_meta WHERE key=?',(self.b.key,));self.refuse_unchanged(self.b.initialize)
    def test_deleted_claim_cannot_recreate_budget(self):
        r=self.claim();self.f.sql('DELETE FROM state_meta WHERE key=?',(self.b.prefix+r['ticket'],));self.refuse_unchanged(self.claim)
    def test_dishonest_counter_not_trusted_even_with_valid_digest(self):
        self.claim();cfg=self.f.get(self.b.key);cfg['providerCalls']=0;self.f.set(self.b.key,seal(cfg));self.refuse_unchanged(self.claim)
    def test_dishonest_token_total_refused(self):
        self.claim();cfg=self.f.get(self.b.key);cfg['reservedTokens']=0;self.f.set(self.b.key,seal(cfg));self.refuse_unchanged(self.claim)
    def test_wrong_reservation_token_value_refused(self):
        r=self.claim();r['tokens']=0;self.f.set(self.b.prefix+r['ticket'],seal(r));self.refuse_unchanged(self.claim)
    def test_modified_digest_refused(self):
        r=self.claim();r['digest']='f'*64;self.f.set(self.b.prefix+r['ticket'],r);self.refuse_unchanged(self.claim)
    def test_returned_claim_is_not_stored_object(self):
        r=self.claim();r['tokens']=0;r['state']='settled';self.assertEqual(self.b.snapshot()['reservedTokens'],120)
    def test_same_settlement_replay_unchanged(self):
        r=self.claim();u={'input_tokens':2,'output_tokens':3};first=self.b.settle(r['ticket'],u,'response');before=self.rows()
        self.assertEqual(self.b.settle(r['ticket'],u,'response'),first);self.assertEqual(self.rows(),before)
    def test_changed_settlement_conflicts_without_refund(self):
        r=self.claim();self.b.settle(r['ticket'],{'input_tokens':2,'output_tokens':3},'response')
        self.refuse_unchanged(lambda:self.b.settle(r['ticket'],{'input_tokens':3,'output_tokens':3},'response'),'execution_settlement_conflict')
    def test_unknown_ticket_refused(self):self.refuse_unchanged(lambda:self.b.settle('f'*32,None,'unknown_usage'))
    def test_overreported_usage_quarantines_future_claims(self):
        r=self.claim()
        with self.assertRaisesRegex(ExecutionDenied,'provider_usage_out_of_contract'):self.b.settle(r['ticket'],{'input_tokens':101,'output_tokens':1},'response')
        self.assertTrue(self.b.snapshot()['quarantined']);self.assertEqual(self.b.snapshot()['reservedTokens'],120)
        self.refuse_unchanged(self.claim,'execution_budget_quarantined')
        self.refuse_unchanged(lambda:self.claim('read_file'),'execution_budget_quarantined')
    def test_bool_usage_is_not_one_token(self):
        r=self.claim()
        with self.assertRaises(ExecutionDenied):self.b.settle(r['ticket'],{'input_tokens':True,'output_tokens':0},'response')
        self.assertTrue(self.b.snapshot()['quarantined'])
    def test_negative_usage_does_not_restore_budget(self):
        r=self.claim()
        with self.assertRaises(ExecutionDenied):self.b.settle(r['ticket'],{'input_tokens':-1,'output_tokens':0},'response')
        self.assertEqual(self.b.snapshot()['reservedCostMicrousd'],300)
    def test_unknown_usage_field_is_not_silently_ignored(self):
        r=self.claim()
        with self.assertRaises(ExecutionDenied):self.b.settle(r['ticket'],{'input_tokens':1,'output_tokens':1,'credit':100},'response')
        self.assertTrue(self.b.snapshot()['quarantined'])
    def test_policy_change_refuses_old_budget(self):
        self.claim();self.p=replace(self.p,max_provider_calls=4);self.b=self.make();self.refuse_unchanged(self.b.initialize)
    def test_stale_epoch_refuses(self):
        self.f.sql('UPDATE runtime_epoch SET epoch=2');self.refuse_unchanged(self.claim)
    def test_new_epoch_preserves_reserved_exposure(self):
        self.claim();self.f.sql("UPDATE runtime_epoch SET epoch=2,instance_id='new-owner'")
        self.f.context=replace(self.f.context,epoch=2,instance_id='new-owner');self.b=self.make();self.b.initialize()
        self.assertEqual(self.b.snapshot()['providerCalls'],1)
    def test_previous_epoch_claim_not_settled_by_new_owner(self):
        r=self.claim();self.f.sql("UPDATE runtime_epoch SET epoch=2,instance_id='new-owner'")
        self.f.context=replace(self.f.context,epoch=2,instance_id='new-owner');self.b=self.make()
        self.refuse_unchanged(lambda:self.b.settle(r['ticket'],None,'unknown_usage'),'stale_execution_claim')
    def test_foreign_database_refused(self):
        with tempfile.TemporaryDirectory() as other:
            with self.assertRaises(ExecutionDenied):ExecutionLedger(SyntheticOwner(Path(other)/'state.db'),self.f.context,self.p)
    def test_before_commit_failure_rolls_back_claim(self):
        self.f.db.fail_before_commit=True;self.refuse_unchanged(self.claim)
        self.f.db.fail_before_commit=False;self.assertEqual(self.b.snapshot()['providerCalls'],0)
    def test_lost_commit_ack_is_permanent_exposure(self):
        self.configure(max_provider_calls=1);self.f.db.lose_ack=True
        with self.assertRaises(ExecutionDenied):self.claim()
        self.f.db.lose_ack=False;self.assertEqual(self.b.snapshot()['providerCalls'],1)
        self.refuse_unchanged(self.claim,'provider_attempt_limit')
    def test_lost_settlement_ack_can_read_same_settlement(self):
        r=self.claim();self.f.db.lose_ack=True
        with self.assertRaises(ExecutionDenied):self.b.settle(r['ticket'],None,'transport_error')
        self.f.db.lose_ack=False;before=self.rows();self.b.settle(r['ticket'],None,'transport_error');self.assertEqual(before,self.rows())
    def test_concurrent_twenty_requests_only_three_claims(self):
        def attempt(_):
            try:return self.claim()['ticket']
            except ExecutionDenied:return None
        with ThreadPoolExecutor(max_workers=20) as pool:rows=list(pool.map(attempt,range(20)))
        self.assertEqual(sum(x is not None for x in rows),3);self.assertEqual(len({x for x in rows if x is not None}),3)
        self.assertEqual(self.b.snapshot()['reservedCostMicrousd'],900)
    def test_missing_history_no_implicit_initialize_on_claim(self):
        self.f.sql('DROP TABLE state_meta')
        with self.assertRaises(ExecutionDenied):self.claim()
        with closing(sqlite3.connect(self.f.home/'state.db')) as c:self.assertIsNone(c.execute("SELECT 1 FROM sqlite_master WHERE name='state_meta'").fetchone())
    def test_trigger_refused(self):
        self.f.sql('CREATE TRIGGER surprise AFTER UPDATE ON state_meta BEGIN SELECT 1; END');self.refuse_unchanged(self.claim)
    def test_invalid_kind_does_not_claim(self):self.refuse_unchanged(lambda:self.b.claim('terminal','a'*64))
    def test_invalid_fingerprint_does_not_claim(self):self.refuse_unchanged(lambda:self.b.claim('provider','old-key'))
    def test_float_nan_infinite_limits_refused(self):
        for v in (True,-1,1.5,float('nan'),float('inf'),None):
            with self.subTest(v=v),self.assertRaises(ExecutionDenied):policy(max_provider_calls=v)
    def test_unknown_price_is_not_free(self):
        for v in (None,False,-1,1.5):
            with self.subTest(v=v),self.assertRaises(ExecutionDenied):policy(input_rate_microusd_per_million=v)
    def test_provider_cannot_settle_as_tool_return(self):
        r=self.claim();self.refuse_unchanged(lambda:self.b.settle(r['ticket'],None,'tool_return'))
    def test_tool_cannot_settle_as_provider_response(self):
        r=self.claim('read_file');self.refuse_unchanged(lambda:self.b.settle(r['ticket'],None,'response'))

if __name__=='__main__':unittest.main()
