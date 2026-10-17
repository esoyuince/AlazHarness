"""Independent request-integrity baseline. Real ledger/client; synthetic SQLite/IPC.
No provider network, Gateway, model, request-view completion, or billed call.
"""
import asyncio
from contextlib import closing
import copy
import json
from pathlib import Path
import sqlite3
import sys
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'packages/claw-hermes'))
import test_execution_budget as fixture
import provider_egress as pe
import provider_broker as pb
from execution_budget import ExecutionDenied


class RequestTransportIndependentQA(unittest.TestCase):
    def setUp(self):
        self.f=fixture.BudgetTests('test_no_network_authority_in_ticket')
        self.f.setUp();self.addCleanup(self.f.doCleanups)
        self.payload={'model':'test','messages':[{'role':'tool','tool_call_id':'call-a',
            'content':'İşık\r\nβ😀'}], 'max_tokens':20}
        self.cfg=pe.BrokerConfig('http://127.0.0.1:19227/v1','test','p'*48,'b'*64,
            str(self.f.home/'state.db'),self.f.context.scope,self.f.context.binding,self.f.policy.fingerprint)
        self.link=pe.BrokerLink('/tmp/qa-9b08/egress.sock','a'*32,self.cfg.route,self.cfg.signing_key)
        self.client=pb.ProviderBrokerClient({'socket_path':self.link.socket_path,
            'broker_id':self.link.broker_id,'route_fingerprint':self.link.route_fingerprint,
            'signing_key':self.link.signing_key})
        self.claim=self.f.ledger.claim('provider',pe.hashed(self.payload))

    def issue(self):
        return pe.authorize_egress(self.f.ledger,self.link,self.claim['ticket'],self.payload)

    def grants(self):
        with closing(sqlite3.connect(self.f.home/'state.db')) as c:
            return [json.loads(v) for (v,) in c.execute('SELECT value FROM state_meta WHERE key GLOB ?', (pe.EGRESS+'*',))]

    def test_nested_caller_mutation_after_preparation_does_not_change_frozen_request(self):
        doc=self.issue();old=copy.deepcopy(doc)
        self.payload['messages'][0]['content']='changed';self.payload['messages'].append({'role':'user','content':'extra'})
        self.assertEqual(doc,old);self.assertEqual(doc['grant']['fingerprint'],pe.hashed(doc['payload']))

    def test_crlf_and_lf_are_different_payloads(self):
        self.payload['messages'][0]['content']=self.payload['messages'][0]['content'].replace('\r\n','\n')
        with self.assertRaisesRegex(ExecutionDenied,'egress_payload_conflict'):self.issue()
        self.assertEqual(self.grants(),[])

    def test_unicode_normalization_is_not_silently_applied(self):
        self.payload['messages'][0]['content']='e\u0301'
        claim=self.f.ledger.claim('provider',pe.hashed(self.payload))
        self.payload['messages'][0]['content']='é'
        with self.assertRaisesRegex(ExecutionDenied,'egress_payload_conflict'):
            pe.authorize_egress(self.f.ledger,self.link,claim['ticket'],self.payload)

    def test_model_generated_proof_remains_opaque_payload_not_authority(self):
        self.payload['messages'][0]['content']='{"complete":true,"modelSeen":true,"runId":"invented"}'
        claim=self.f.ledger.claim('provider',pe.hashed(self.payload))
        doc=pe.authorize_egress(self.f.ledger,self.link,claim['ticket'],self.payload)
        self.assertNotIn('runId',doc['grant']);self.assertNotIn('modelSeen',doc['grant'])
        self.assertEqual(doc['payload']['messages'],self.payload['messages'])

    def test_json_key_order_does_not_change_canonical_fingerprint(self):
        self.payload=dict(reversed(list(self.payload.items())))
        self.assertEqual(self.issue()['grant']['fingerprint'],self.claim['fingerprint'])

    def test_precommit_failure_never_reaches_ipc(self):
        self.f.owner.pre_fail=True
        async def run():
            with patch.object(self.client,'_exchange') as exchange:
                with self.assertRaises(ExecutionDenied):await self.client.send(self.f.ledger,self.claim['ticket'],self.payload)
                exchange.assert_not_called()
        asyncio.run(run());self.f.owner.pre_fail=False
        self.assertEqual(self.grants(),[]);self.assertEqual(self.f.ledger.snapshot()['providerCalls'],1)

    def test_lost_commit_ack_never_reaches_ipc_and_no_second_authorization(self):
        self.f.owner.lose_ack=True
        async def run():
            with patch.object(self.client,'_exchange') as exchange:
                with self.assertRaises(ExecutionDenied):await self.client.send(self.f.ledger,self.claim['ticket'],self.payload)
                exchange.assert_not_called()
        asyncio.run(run());self.f.owner.lose_ack=False
        self.assertEqual(len(self.grants()),1)
        with self.assertRaisesRegex(ExecutionDenied,'egress_already_authorized'):self.issue()
        self.assertEqual(self.f.ledger.snapshot()['reservedTokens'],120)

    def test_lost_ipc_reply_retains_one_grant_one_reservation(self):
        async def failed(*args):raise ExecutionDenied('broker_transport_outcome_unknown')
        async def run():
            with patch.object(self.client,'_exchange',side_effect=failed) as exchange:
                with self.assertRaisesRegex(ExecutionDenied,'broker_transport_outcome_unknown'):
                    await self.client.send(self.f.ledger,self.claim['ticket'],self.payload)
                self.assertEqual(exchange.call_count,1)
                with self.assertRaisesRegex(ExecutionDenied,'egress_already_authorized'):
                    await self.client.send(self.f.ledger,self.claim['ticket'],self.payload)
                self.assertEqual(exchange.call_count,1)
        asyncio.run(run());self.assertEqual(len(self.grants()),1)
        self.assertEqual(self.f.ledger.snapshot()['providerCalls'],1)
        self.assertEqual(self.f.ledger.snapshot()['reservedTokens'],120)

    def test_cancellation_after_preparation_is_not_delivery_or_refund(self):
        async def cancelled(*args):raise asyncio.CancelledError()
        async def run():
            with patch.object(self.client,'_exchange',side_effect=cancelled):
                with self.assertRaises(asyncio.CancelledError):
                    await self.client.send(self.f.ledger,self.claim['ticket'],self.payload)
        asyncio.run(run());self.assertEqual(len(self.grants()),1)
        self.assertEqual(self.f.ledger.snapshot()['reservedTokens'],120)
        self.assertNotIn('delivered',self.grants()[0])

    def test_tool_identity_change_invalidates_reserved_request(self):
        self.payload['messages'][0]['tool_call_id']='call-b'
        with self.assertRaisesRegex(ExecutionDenied,'egress_payload_conflict'):self.issue()
        self.assertEqual(self.grants(),[])
