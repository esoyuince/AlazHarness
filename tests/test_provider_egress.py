"""Real native-owner ledger code with a synthetic SQLite owner. No broker/server/provider starts."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from dataclasses import replace
import copy
import json
from pathlib import Path
import sqlite3
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'packages/claw-hermes'))
import test_execution_budget as f
from execution_budget import ExecutionDenied,seal,CLAIM
from provider_egress import (BrokerLink,BrokerConfig,PermitVerifier,authorize_egress,EGRESS,
                             route_fingerprint,hashed,signed,verified)

class EgressContracts(unittest.TestCase):
    def setUp(self):
        self.f=f.BudgetTests('test_no_network_authority_in_ticket');self.f.setUp();self.addCleanup(self.f.doCleanups)
        self.body={'model':'test','messages':[{'role':'user','content':'hello'}]};self.now=1800000000.
        self.config=BrokerConfig('http://127.0.0.1:19777/v1','test','p'*48,'b'*64,
                                str(self.f.home/'state.db'),self.f.context.scope,self.f.context.binding,self.f.policy.fingerprint)
        self.link=BrokerLink('/tmp/owned-broker/egress.sock','a'*32,self.config.route,self.config.signing_key)
        self.verifier=PermitVerifier(self.config,self.link.broker_id,clock=lambda:self.now)
    def reserve(self,kind='provider'):return self.f.ledger.claim(kind,hashed(self.body))
    def permit(self,claim=None):
        c=claim or self.reserve();return authorize_egress(self.f.ledger,self.link,c['ticket'],self.body,clock=lambda:self.now)
    def changed(self,envelope,key,value):
        e=copy.deepcopy(envelope);e.pop('signature');e['grant'][key]=value;return signed(e,self.link.signing_key,'request')
    def test_reservation_then_irrevocable_grant(self):
        r=self.reserve();before=self.f.ledger.snapshot();doc=self.permit(r)
        self.assertEqual(before,self.f.ledger.snapshot());self.assertIn(EGRESS+self.config.scope+'.'+r['ticket'],dict(self.f.rows()))
        parsed=self.verifier.consume(doc);self.verifier.check_authority(parsed['grant'])
    def test_no_provider_secret_in_grant_or_repr(self):
        d=self.permit();self.assertNotIn(self.config.upstream_bearer,json.dumps(d));self.assertNotIn(self.config.upstream_bearer,repr(self.config));self.assertNotIn(self.link.signing_key,repr(self.link))
    def test_missing_reservation_refused(self):
        with self.assertRaisesRegex(ExecutionDenied,'execution_claim_missing'):authorize_egress(self.f.ledger,self.link,'f'*32,self.body,clock=lambda:self.now)
    def test_tool_ticket_not_provider_grant(self):
        with self.assertRaisesRegex(ExecutionDenied,'provider_reservation_required'):self.permit(self.reserve('read_file'))
    def test_already_settled_ticket_refused(self):
        c=self.reserve();self.f.ledger.settle(c['ticket'],None,'unknown_usage')
        with self.assertRaises(ExecutionDenied):self.permit(c)
    def test_changed_request_refused(self):
        c=self.reserve();self.body['messages'][0]['content']='changed'
        with self.assertRaisesRegex(ExecutionDenied,'egress_payload_conflict'):self.permit(c)
    def test_quarantine_before_authorization_refused(self):
        c=self.reserve();self.f.ledger.quarantine()
        with self.assertRaisesRegex(ExecutionDenied,'execution_budget_quarantined'):self.permit(c)
    def test_native_epoch_changed_before_authorization(self):
        c=self.reserve();self.f.sql('UPDATE runtime_epoch SET epoch=2')
        with self.assertRaises(ExecutionDenied):self.permit(c)
    def test_old_ticket_cannot_be_authorized_in_new_epoch(self):
        c=self.reserve();self.f.sql("UPDATE runtime_epoch SET epoch=2,instance_id='second'")
        self.f.context=replace(self.f.context,epoch=2,instance_id='second');self.f.ledger=self.f.make()
        with self.assertRaisesRegex(ExecutionDenied,'stale_execution_claim'):self.permit(c)
    def test_second_authorization_rejected_no_new_budget(self):
        c=self.reserve();self.permit(c);before=self.f.rows()
        with self.assertRaisesRegex(ExecutionDenied,'egress_already_authorized'):self.permit(c)
        self.assertEqual(before,self.f.rows())
    def test_twenty_authorizations_only_one(self):
        c=self.reserve()
        def once(_):
            try:self.permit(c);return 1
            except ExecutionDenied:return 0
        with ThreadPoolExecutor(max_workers=10) as pool:self.assertEqual(sum(pool.map(once,range(20))),1)
        self.assertEqual(self.f.ledger.snapshot()['providerCalls'],1)
    def test_precommit_failure_leaves_no_grant(self):
        c=self.reserve();before=self.f.rows();self.f.owner.pre_fail=True
        with self.assertRaises(ExecutionDenied):self.permit(c)
        self.f.owner.pre_fail=False;self.assertEqual(before,self.f.rows())
    def test_lost_authorization_ack_never_reissued(self):
        c=self.reserve();self.f.owner.lose_ack=True
        with self.assertRaises(ExecutionDenied):self.permit(c)
        self.f.owner.lose_ack=False
        with self.assertRaisesRegex(ExecutionDenied,'egress_already_authorized'):self.permit(c)
        self.assertEqual(self.f.ledger.snapshot()['reservedTokens'],120)
    def test_raw_ticket_is_not_send_permission(self):
        with self.assertRaises(ExecutionDenied):self.verifier.consume(self.reserve())
    def test_broker_duplicate_refused(self):
        d=self.permit();self.verifier.consume(d)
        with self.assertRaisesRegex(ExecutionDenied,'broker_replay_refused'):self.verifier.consume(d)
    def test_new_broker_rejects_old_lifetime(self):
        d=self.permit();other=PermitVerifier(self.config,'c'*32,clock=lambda:self.now)
        with self.assertRaisesRegex(ExecutionDenied,'stale_broker_identity'):other.consume(d)
    def test_changed_payload_invalidates_signature(self):
        d=self.permit();d['payload']['messages'][0]['content']='changed'
        with self.assertRaisesRegex(ExecutionDenied,'broker_authentication_required'):self.verifier.consume(d)
    def test_re_signed_payload_still_must_match_grant(self):
        d=self.permit();d.pop('signature');d['payload']['messages'][0]['content']='changed'
        with self.assertRaisesRegex(ExecutionDenied,'egress_payload_conflict'):self.verifier.consume(signed(d,self.link.signing_key,'request'))
    def test_expired_grant(self):
        d=self.permit();self.now+=21
        with self.assertRaisesRegex(ExecutionDenied,'egress_grant_expired'):self.verifier.consume(d)
    def test_future_grant(self):
        d=self.changed(self.permit(),'expiresAtMs',int(self.now*1000)+90000)
        with self.assertRaises(ExecutionDenied):self.verifier.consume(d)
    def test_bool_expiry_not_integer(self):
        with self.assertRaises(ExecutionDenied):self.verifier.consume(self.changed(self.permit(),'expiresAtMs',True))
    def test_bool_epoch_not_one(self):
        with self.assertRaises(ExecutionDenied):self.verifier.consume(self.changed(self.permit(),'epoch',True))
    def test_wrong_scope(self):
        with self.assertRaisesRegex(ExecutionDenied,'broker_scope_mismatch'):self.verifier.consume(self.changed(self.permit(),'scope','0'*64))
    def test_wrong_policy(self):
        with self.assertRaises(ExecutionDenied):self.verifier.consume(self.changed(self.permit(),'policy','0'*64))
    def test_wrong_route(self):
        with self.assertRaises(ExecutionDenied):self.verifier.consume(self.changed(self.permit(),'routeFingerprint','0'*64))
    def test_no_arbitrary_envelope_destination(self):
        d=self.permit();d.pop('signature');d['url']='http://other/'
        with self.assertRaises(ExecutionDenied):self.verifier.consume(signed(d,self.link.signing_key,'request'))
    def test_request_reply_signatures_not_interchangeable(self):
        d=self.permit()
        with self.assertRaises(ExecutionDenied):verified(d,self.link.signing_key,'reply')
    def test_malformed_signature(self):
        d=self.permit();d['signature']=False
        with self.assertRaises(ExecutionDenied):self.verifier.consume(d)
    def test_unbounded_broker_history_refused(self):
        d=self.permit();self.verifier.seen={str(x) for x in range(1000)}
        with self.assertRaisesRegex(ExecutionDenied,'broker_lifetime_limit'):self.verifier.consume(d)
    def test_authority_row_required(self):
        d=self.permit();g=d['grant'];self.f.sql('DELETE FROM state_meta WHERE key=?',(EGRESS+self.config.scope+'.'+g['ticket'],))
        with self.assertRaisesRegex(ExecutionDenied,'unconfirmed_egress_grant'):self.verifier.check_authority(g)
    def test_quarantine_after_authorization_prevents_egress(self):
        d=self.permit();self.f.ledger.quarantine()
        with self.assertRaisesRegex(ExecutionDenied,'broker_budget_unavailable'):self.verifier.check_authority(d['grant'])
    def test_epoch_after_authorization_prevents_egress(self):
        d=self.permit();self.f.sql('UPDATE runtime_epoch SET epoch=2')
        with self.assertRaisesRegex(ExecutionDenied,'stale_egress_owner'):self.verifier.check_authority(d['grant'])
    def test_settlement_after_authorization_prevents_egress(self):
        d=self.permit();self.f.ledger.settle(d['grant']['ticket'],None,'unknown_usage')
        with self.assertRaisesRegex(ExecutionDenied,'broker_claim_unavailable'):self.verifier.check_authority(d['grant'])
    def test_readonly_authority_no_bytes_changed(self):
        g=self.permit()['grant'];before=(self.f.home/'state.db').read_bytes();self.verifier.check_authority(g)
        self.assertEqual(before,(self.f.home/'state.db').read_bytes())
    def test_missing_db_never_created(self):
        g=self.permit()['grant'];(self.f.home/'state.db').unlink()
        with self.assertRaises(ExecutionDenied):self.verifier.check_authority(g)
        self.assertFalse((self.f.home/'state.db').exists())
    def test_returned_permit_not_stored_object(self):
        c=self.reserve();d=self.permit(c);d['grant']['epoch']=99
        row=json.loads(dict(self.f.rows())[EGRESS+self.config.scope+'.'+c['ticket']]);self.assertEqual(row['epoch'],1)
    def test_scope_report_budget_validation_preserved(self):
        self.permit();s=self.f.ledger.snapshot();self.assertEqual(s['providerCalls'],1);self.assertEqual(s['reservedTokens'],120)
    def test_bad_route_variants_refused(self):
        for route in ['http://localhost:90/v1','http://127.0.0.1:65536/v1','http://127.0.0.1:90/v1/','http://127.0.0.1:90/v1?x','https://example.com/v1','http://u@127.0.0.1:90/v1']:
            with self.subTest(route=route),self.assertRaises(ExecutionDenied):route_fingerprint(route,'test')
    def test_separate_upstream_key_required(self):
        with self.assertRaises(ExecutionDenied):replace(self.config,upstream_bearer=self.config.signing_key)
    def test_endpoint_change_changes_route_identity(self):self.assertNotEqual(self.config.route,route_fingerprint('http://127.0.0.1:19778/v1','test'))
    def test_socket_invalid_paths(self):
        for value in ['relative','/tmp/a/../b','/tmp/a\n','/'+'a'*101]:
            with self.subTest(value=value),self.assertRaises(ExecutionDenied):replace(self.link,socket_path=value)
    def test_immutable_link(self):
        with self.assertRaises(AttributeError):self.link.broker_id='f'*32
    def test_nonfinite_clock(self):
        ticket=self.reserve()['ticket']
        for value in [True,float('nan'),float('inf'),-1]:
            with self.subTest(value=value),self.assertRaises(ExecutionDenied):authorize_egress(self.f.ledger,self.link,ticket,self.body,clock=lambda:value)

if __name__=='__main__':unittest.main()
