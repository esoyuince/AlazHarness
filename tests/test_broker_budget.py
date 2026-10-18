"""Private budget SQLite contracts; no actual provider/network in these tests."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from dataclasses import asdict,replace
import copy
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch
import uuid
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'packages/claw-hermes'))
from execution_budget import ExecutionPolicy,ExecutionDenied
from provider_egress import BrokerConfig
import broker_budget as budget


class BudgetFixture:
    def __init__(self,case,**changes):
        self.tmp=tempfile.TemporaryDirectory();case.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name).resolve();self.gateway=self.root/'gateway';self.gateway.mkdir()
        self.policy=replace(ExecutionPolicy('test',3,1,1000,20,3060,10000,1000000,2000000),**changes)
        self.settings={'version':1,'enabled':True,'directory':str(self.root/'authority'),
                       'budget_id':'a'*32,'policy':asdict(self.policy)}
        self.config=BrokerConfig('http://127.0.0.1:19440/v1','test','p'*48,'b'*64,
              str(self.gateway/'state.db'),'c'*64,'d'*64,self.policy.fingerprint,self.settings)
        self.body={'model':'test','messages':[{'role':'user','content':'test owned data'}],
                   'max_tokens':10,'stream':False}

    def grant(self,body=None,ticket=None,broker='e'*32):
        return {'version':1,'brokerId':broker,'routeFingerprint':self.config.route,
             'scope':self.config.scope,'binding':self.config.binding,'policy':self.policy.fingerprint,
             'ticket':ticket or uuid.uuid4().hex,'fingerprint':budget.hexdigest(body or self.body),
             'epoch':1,'instance':'one','expiresAtMs':1800000020000}


class BrokerBudgetTests(unittest.TestCase):
    def setUp(self):
        self.f=BudgetFixture(self)
        budget.initialize(self.f.config)
        self.b=budget.BrokerBudget(self.f.config)

    def reserve(self,body=None,ticket=None,broker='e'*32):
        return self.b.reserve(self.f.grant(body,ticket,broker),body or self.f.body)

    def test_empty_explicitly_initialized_budget(self):
        s=self.b.snapshot();self.assertEqual(s['providerReservations'],0)
        self.assertFalse(s['gatewayDatabaseIsBudgetAuthority'])
        self.assertFalse(s['hostFilesystemConfinementVerified'])

    def test_full_conservative_reservation_not_measured_invoice(self):
        r=self.reserve();s=self.b.snapshot()
        self.assertEqual(r['reservedTokens'],1020)
        self.assertEqual(r['reservedCostMicrousd'],1040)
        self.assertEqual(s['providerReservations'],1)
        self.assertFalse(s['measuredInvoiceVerified'])

    def test_three_calls_cap_fourth_refused(self):
        for _ in range(3):self.reserve()
        with self.assertRaisesRegex(ExecutionDenied,'attempt_limit'):self.reserve()
        self.assertEqual(self.b.snapshot()['providerReservations'],3)

    def test_duplicate_ticket_refused(self):
        row=self.reserve()
        with self.assertRaisesRegex(ExecutionDenied,'private_budget_replay'):
            self.reserve(ticket=row['ticket'])
        self.assertEqual(self.b.snapshot()['providerReservations'],1)

    def test_replay_survives_new_broker_and_new_object(self):
        row=self.reserve()
        self.b=budget.BrokerBudget(self.f.config)
        with self.assertRaisesRegex(ExecutionDenied,'private_budget_replay'):
            self.reserve(ticket=row['ticket'],broker='f'*32)
        self.assertEqual(self.b.snapshot()['providerReservations'],1)

    def test_changed_payload_same_ticket_not_new_authority(self):
        row=self.reserve();body=copy.deepcopy(self.f.body);body['messages'][0]['content']='different'
        with self.assertRaisesRegex(ExecutionDenied,'private_budget_replay'):
            self.reserve(body,ticket=row['ticket'],broker='f'*32)

    def test_gateway_database_rewrite_does_not_reset_budget(self):
        self.reserve();self.reserve();self.reserve()
        path=self.f.gateway/'state.db'
        with closing(sqlite3.connect(path)) as c:
            c.execute('CREATE TABLE fake_claims(ticket TEXT)');c.commit()
        path.unlink()
        with closing(sqlite3.connect(path)) as c:
            c.execute('CREATE TABLE state_meta(key TEXT,value TEXT)');c.commit()
        self.b=budget.BrokerBudget(self.f.config)
        with self.assertRaisesRegex(ExecutionDenied,'attempt_limit'):self.reserve()

    def test_no_implicit_create_missing_authority(self):
        f=BudgetFixture(self)
        with self.assertRaisesRegex(ExecutionDenied,'missing_or_linked'):budget.BrokerBudget(f.config)
        self.assertFalse(Path(f.settings['directory']).exists())

    def test_explicit_init_never_reuses_directory(self):
        self.reserve();before=self.b.path.read_bytes()
        with self.assertRaisesRegex(ExecutionDenied,'fresh_directory_required'):budget.initialize(self.f.config)
        self.assertEqual(before,self.b.path.read_bytes())

    def test_deleted_database_never_recreated(self):
        self.b.path.unlink()
        with self.assertRaises(ExecutionDenied):self.reserve()
        self.assertFalse(self.b.path.exists())

    def test_changed_policy_cannot_reopen_or_raise_limit(self):
        policy=replace(self.f.policy,max_provider_calls=10,total_token_limit=10200)
        conf=replace(self.f.config,policy_fingerprint=policy.fingerprint,
            budget_authority=self.f.settings|{'policy':asdict(policy)})
        with self.assertRaisesRegex(ExecutionDenied,'binding_changed'):budget.BrokerBudget(conf)

    def test_changed_budget_id_or_route_refused(self):
        for conf in (replace(self.f.config,budget_authority=self.f.settings|{'budget_id':'f'*32}),
                     replace(self.f.config,upstream_base_url='http://127.0.0.1:19441/v1')):
            with self.assertRaisesRegex(ExecutionDenied,'binding_changed'):budget.BrokerBudget(conf)

    def test_no_automatic_refund_on_http_error(self):
        row=self.reserve();self.b.observe(row['ticket'],b'{}',500,'application/json')
        self.assertEqual(self.b.snapshot()['reservedCostMicrousd'],1040)
        self.assertEqual(self.b.snapshot()['observedHttpResponses'],1)

    def test_observation_is_idempotent_but_not_refund(self):
        row=self.reserve()
        self.b.observe(row['ticket'],b'{}',200,'application/json')
        self.b.observe(row['ticket'],b'{}',200,'application/json')
        self.assertEqual(self.b.snapshot()['observedHttpResponses'],1)
        self.assertEqual(self.b.snapshot()['providerReservations'],1)

    def test_conflicting_observation_refused(self):
        row=self.reserve();self.b.observe(row['ticket'],b'{}',200,'application/json')
        with self.assertRaisesRegex(ExecutionDenied,'response_conflict'):
            self.b.observe(row['ticket'],b'changed',200,'application/json')

    def test_unreserved_observation_refused(self):
        with self.assertRaisesRegex(ExecutionDenied,'reservation_missing'):
            self.b.observe('f'*32,b'{}',200,'application/json')

    def test_precommit_error_no_reservation(self):
        with patch.object(self.b,'_commit',side_effect=sqlite3.OperationalError('owned injection')):
            with self.assertRaisesRegex(ExecutionDenied,'storage_unconfirmed'):self.reserve()
        self.assertEqual(self.b.snapshot()['providerReservations'],0)

    def test_commit_ack_lost_retains_reservation(self):
        def lost(c):c.commit();raise sqlite3.OperationalError('owned ack loss')
        ticket='1'*32
        with patch.object(self.b,'_commit',side_effect=lost):
            with self.assertRaisesRegex(ExecutionDenied,'storage_unconfirmed'):
                self.reserve(ticket=ticket)
        self.assertEqual(self.b.snapshot()['providerReservations'],1)
        self.b=budget.BrokerBudget(self.f.config)
        with self.assertRaisesRegex(ExecutionDenied,'private_budget_replay'):self.reserve(ticket=ticket)

    def test_twelve_parallel_connections_still_three_reservations(self):
        def attempt(_):
            try:
                other=budget.BrokerBudget(self.f.config)
                other.reserve(self.f.grant(),self.f.body);return 1
            except ExecutionDenied:return 0
        with ThreadPoolExecutor(max_workers=6) as pool:
            self.assertEqual(sum(pool.map(attempt,range(12))),3)
        self.assertEqual(self.b.snapshot()['providerReservations'],3)

    def test_omitted_or_excessive_output_ceiling_refused(self):
        for body in ({k:v for k,v in self.f.body.items() if k!='max_tokens'},
                     self.f.body|{'max_tokens':21},self.f.body|{'max_tokens':True}):
            with self.assertRaises(ExecutionDenied):self.reserve(body)
        self.assertEqual(self.b.snapshot()['providerReservations'],0)

    def test_gateway_alternative_token_ceiling_stays_bounded(self):
        body={k:v for k,v in self.f.body.items() if k!='max_tokens'}
        body|={'max_completion_tokens':10,'user':'owned-fixture',
               'reasoning_effort':'low','verbosity':'low'}
        self.reserve(body)
        for invalid in (body|{'max_tokens':10},
                        body|{'max_completion_tokens':21},
                        body|{'max_completion_tokens':True}):
            with self.assertRaises(ExecutionDenied):self.reserve(invalid)
        self.assertEqual(self.b.snapshot()['providerReservations'],1)

    def test_no_multiple_completions_or_unknown_provider_knobs(self):
        for body in (self.f.body|{'n':2},self.f.body|{'best_of':12},
                     self.f.body|{'max_completion_tokens':300},self.f.body|{'budget':999999}):
            with self.assertRaises(ExecutionDenied):self.reserve(body)
        self.assertEqual(self.b.snapshot()['providerReservations'],0)

    def test_wrong_model_or_body_fingerprint_refused(self):
        with self.assertRaises(ExecutionDenied):self.reserve(self.f.body|{'model':'other'})
        with self.assertRaises(ExecutionDenied):
            self.b.reserve(self.f.grant()|{'fingerprint':'0'*64},self.f.body)

    def test_oversize_serialized_input_refused(self):
        body=self.f.body|{'messages':[{'role':'user','content':'x'*4000}]}
        with self.assertRaisesRegex(ExecutionDenied,'input_bytes'):self.reserve(body)

    def test_input_bytes_not_four_to_one_token_heuristic(self):
        # A former four-bytes-per-token assumption admitted this payload.
        body=self.f.body|{'messages':[{'role':'user','content':'x'*1200}]}
        self.assertLess(len(budget._json(body).encode('utf-8')),self.f.policy.input_ceiling_tokens*4)
        with self.assertRaisesRegex(ExecutionDenied,'input_bytes'):
            self.reserve(body)
        self.assertEqual(self.b.snapshot()['providerReservations'],0)

    def test_deleted_reservation_breaks_private_chain(self):
        self.reserve()
        with closing(sqlite3.connect(self.b.path)) as c:c.execute('DELETE FROM attempts');c.commit()
        with self.assertRaisesRegex(ExecutionDenied,'history'):self.b.snapshot()

    def test_fake_private_trigger_or_table_rejected(self):
        with closing(sqlite3.connect(self.b.path)) as c:
            c.execute('CREATE TRIGGER injected AFTER INSERT ON attempts BEGIN SELECT 1; END');c.commit()
        with self.assertRaisesRegex(ExecutionDenied,'schema'):self.b.snapshot()

    def test_new_scope_binding_not_accepted(self):
        with self.assertRaises(ExecutionDenied):
            self.b.reserve(self.f.grant()|{'scope':'f'*64},self.f.body)


class PrivateBudgetConfigTests(unittest.TestCase):
    def test_separate_path_required(self):
        f=BudgetFixture(self)
        for directory in (f.gateway/'private',f.root):
            with self.assertRaisesRegex(ExecutionDenied,'not_separate'):
                replace(f.config,budget_authority=f.settings|{'directory':str(directory)})

    def test_closed_settings_no_implicit_defaults(self):
        f=BudgetFixture(self)
        for delta in ({'enabled':False},{'enabled':1},{'version':True},{'budget_id':'unknown'},
                      {'directory':'relative'},{'reset':True}):
            with self.subTest(delta=delta),self.assertRaises(ExecutionDenied):
                budget.validate_settings(f.settings|delta)

    def test_gateway_policy_and_private_contract_must_match(self):
        f=BudgetFixture(self)
        with self.assertRaisesRegex(ExecutionDenied,'policy_mismatch'):
            replace(f.config,policy_fingerprint='0'*64)

    def test_token_and_cost_limits_independently_enforced(self):
        for field,limit,code in [('total_token_limit',1020,'token_limit'),
                                 ('total_cost_microusd',1040,'cost_limit')]:
            f=BudgetFixture(self,**{field:limit});budget.initialize(f.config);b=budget.BrokerBudget(f.config)
            b.reserve(f.grant(),f.body)
            with self.assertRaisesRegex(ExecutionDenied,code):b.reserve(f.grant(),f.body)

    def test_optional_mode_absent_keeps_legacy_explicit(self):
        f=BudgetFixture(self);conf=replace(f.config,budget_authority=None)
        self.assertIsNone(conf.budget_authority)

    def test_private_policy_input_is_copied(self):
        f=BudgetFixture(self);original=f.config.budget_authority['policy']['max_provider_calls']
        f.settings['policy']['max_provider_calls']=999
        self.assertEqual(f.config.budget_authority['policy']['max_provider_calls'],original)


if __name__=='__main__':unittest.main(verbosity=2)
