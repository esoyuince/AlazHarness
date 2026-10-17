"""Actual ledger/request-view/broker client with synthetic owner and IPC.
These are offline contracts, not a native provider/model or whole-OS test.
"""
import asyncio
import base64
import copy
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import AsyncMock, patch
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'packages/claw-hermes'),str(ROOT/'tests')]
import request_view as rv
import test_execution_budget as budget
import test_source_capture_qa_c72e as source_fixture
from execution_budget import ExecutionDenied, seal
from execution_boundary import ExecutionBoundary
from provider_broker import ProviderBrokerClient
from provider_egress import BrokerLink, authorize_egress, hashed, EGRESS
from recovery_inspector import _json, _load


class RequestViewContracts(unittest.TestCase):
    def setUp(self):
        self.f=budget.BudgetTests('test_no_network_authority_in_ticket');self.f.setUp();self.addCleanup(self.f.doCleanups)
        self.body={'model':'test','messages':[{'role':'user','content':'Işık😀\r\n'}],'max_tokens':20}
        self.link=BrokerLink('/tmp/test-view/egress.sock','a'*32,'c'*64,'b'*64)
        self.client=ProviderBrokerClient(dict(socket_path=self.link.socket_path,broker_id=self.link.broker_id,
                         route_fingerprint=self.link.route_fingerprint,signing_key=self.link.signing_key))
        self.ticket=self.f.ledger.claim('provider',hashed(self.body))['ticket']
        self.client._exchange=AsyncMock(side_effect=self.reply)
    def reply(self,doc,nonce):
        return {'version':1,'brokerId':self.link.broker_id,'nonce':nonce,'ok':True,'status':200,
                'contentType':'application/json','dataBase64':base64.b64encode(b'{}').decode()}
    def rows(self):return [(k,_load(v)) for k,v in self.f.rows() if k.startswith(rv.PREFIX)]
    def prepare(self,record=True):return authorize_egress(self.f.ledger,self.link,self.ticket,self.body,record_view=record)
    def send(self,record=True):return asyncio.run(self.client.send(self.f.ledger,self.ticket,self.body,record_view=record))
    def mutate(self,**fields):
        key,row=self.rows()[0];self.f.sql('UPDATE state_meta SET value=? WHERE key=?',(_json(seal(row|fields)),key))
    def test_prepared_and_grant_share_transaction(self):
        self.prepare();row=self.rows()[0][1]
        self.assertEqual(row['state'],'prepared');self.assertEqual(row['requestDigest'],hashed(self.body))
        self.assertIn(EGRESS+self.f.context.scope+'.'+self.ticket,dict(self.f.rows()))
    def test_exact_canonical_utf8_bytes(self):
        self.prepare();row=self.rows()[0][1];self.assertEqual(row['requestBytes'],len(_json(self.body).encode()))
    def test_body_nested_mutation_does_not_change_prepared_document(self):
        doc=self.prepare();self.body['messages'][0]['content']='new';self.assertNotEqual(hashed(self.body),doc['grant']['fingerprint'])
        self.assertEqual(doc['payload']['messages'][0]['content'],'Işık😀\r\n')
    def test_disabled_is_exact_legacy_no_manifest(self):self.send(False);self.assertEqual(self.rows(),[])
    def test_nonbool_record_flag_rejected_before_grant(self):
        for bad in [None,1,'true',{},[]]:
            with self.subTest(bad=bad),self.assertRaises(ExecutionDenied):self.send(bad)
        self.client._exchange.assert_not_called();self.assertFalse(self.rows())
    def test_precommit_failure_no_grant_or_manifest(self):
        before=self.f.rows();self.f.owner.pre_fail=True
        with self.assertRaises(ExecutionDenied):self.send()
        self.f.owner.pre_fail=False;self.assertEqual(before,self.f.rows());self.client._exchange.assert_not_called()
    def test_preparation_lost_ack_keeps_both_and_no_ipc(self):
        self.f.owner.lose_ack=True
        with self.assertRaises(ExecutionDenied):self.send()
        self.f.owner.lose_ack=False;self.assertEqual(self.rows()[0][1]['state'],'prepared')
        self.client._exchange.assert_not_called()
        with self.assertRaises(ExecutionDenied):self.send()
    def test_arm_is_intent_before_exchange(self):
        original=self.reply
        def check(doc,nonce):
            self.assertEqual(self.rows()[0][1]['state'],'handoff_armed');return original(doc,nonce)
        self.client._exchange=AsyncMock(side_effect=check);self.send()
    def fail_phase(self,function,flag):
        original=getattr(rv,function)
        def wrapped(*args,**kwargs):
            setattr(self.f.owner,flag,True)
            try:return original(*args,**kwargs)
            finally:setattr(self.f.owner,flag,False)
        return patch.object(rv,function,wrapped)
    def test_arm_precommit_failure_no_ipc(self):
        with self.fail_phase('arm_handoff','pre_fail'),self.assertRaises(ExecutionDenied):self.send()
        self.assertEqual(self.rows()[0][1]['state'],'prepared');self.client._exchange.assert_not_called()
    def test_arm_lost_ack_still_no_ipc(self):
        with self.fail_phase('arm_handoff','lose_ack'),self.assertRaises(ExecutionDenied):self.send()
        self.assertEqual(self.rows()[0][1]['state'],'handoff_armed');self.client._exchange.assert_not_called()
    def test_complete_reply_metadata_precedes_settlement(self):
        self.assertEqual(self.send(),(b'{}',200,'application/json'));row=self.rows()[0][1]
        self.assertEqual(row['state'],'broker_response_observed');self.assertEqual(row['responseSha256'],hashlib.sha256(b'{}').hexdigest())
        self.assertEqual(self.f.ledger.snapshot()['providerCalls'],1)
        claim=_load(dict(self.f.rows())[self.f.ledger.prefix+self.ticket]);self.assertEqual(claim['state'],'reserved')
    def test_finish_precommit_retains_armed_and_budget(self):
        with self.fail_phase('observe_response','pre_fail'),self.assertRaises(ExecutionDenied):self.send()
        self.assertEqual(self.rows()[0][1]['state'],'handoff_armed');self.client._exchange.assert_awaited_once()
        self.assertEqual(self.f.ledger.snapshot()['providerCalls'],1)
    def test_finish_lost_ack_does_not_deliver_or_replay(self):
        with self.fail_phase('observe_response','lose_ack'),self.assertRaises(ExecutionDenied):self.send()
        self.assertEqual(self.rows()[0][1]['state'],'broker_response_observed')
        with self.assertRaises(ExecutionDenied):self.send()
        self.client._exchange.assert_awaited_once()
    def test_network_error_stays_armed_unknown(self):
        self.client._exchange=AsyncMock(side_effect=ExecutionDenied('broker_transport_outcome_unknown'))
        with self.assertRaises(ExecutionDenied):self.send()
        self.assertEqual(self.rows()[0][1]['state'],'handoff_armed');self.assertEqual(self.f.ledger.snapshot()['providerCalls'],1)
    def test_cancel_does_not_recover_or_mark_response(self):
        self.client._exchange=AsyncMock(side_effect=asyncio.CancelledError)
        with self.assertRaises(asyncio.CancelledError):self.send()
        self.assertEqual(self.rows()[0][1]['state'],'handoff_armed')
    def test_malformed_response_not_recorded(self):
        self.client._exchange=AsyncMock(return_value=self.reply({},self.ticket)|{'dataBase64':'@@'})
        with self.assertRaises(ExecutionDenied):self.send()
        self.assertEqual(self.rows()[0][1]['state'],'handoff_armed')
    def test_error_status_is_observation_not_model_success(self):
        self.client._exchange=AsyncMock(return_value=self.reply({},self.ticket)|{'status':503})
        self.send();self.assertEqual(self.rows()[0][1]['httpStatus'],503)
    def test_duplicate_arm_refused(self):
        self.prepare();rv.arm_handoff(self.f.ledger,self.ticket)
        with self.assertRaises(ExecutionDenied):rv.arm_handoff(self.f.ledger,self.ticket)
    def test_missing_manifest_not_recreated(self):
        self.prepare();key=self.rows()[0][0];self.f.sql('DELETE FROM state_meta WHERE key=?',(key,))
        with self.assertRaises(ExecutionDenied):rv.arm_handoff(self.f.ledger,self.ticket)
        self.assertFalse(self.rows())
    def test_changed_grant_refused(self):
        self.prepare();self.f.sql('DELETE FROM state_meta WHERE key=?',(EGRESS+self.f.context.scope+'.'+self.ticket,))
        with self.assertRaises(ExecutionDenied):rv.arm_handoff(self.f.ledger,self.ticket)
    def test_changed_scope_not_accepted(self):
        self.prepare();self.mutate(scope='f'*64)
        with self.assertRaises(ExecutionDenied):rv.arm_handoff(self.f.ledger,self.ticket)
    def test_stale_owner_cannot_arm(self):
        self.prepare();self.f.sql("UPDATE runtime_epoch SET epoch=2,instance_id='second'")
        with self.assertRaises(ExecutionDenied):rv.arm_handoff(self.f.ledger,self.ticket)
    def test_already_settled_provider_cannot_arm(self):
        self.prepare();self.f.ledger.settle(self.ticket,None,'unknown_usage')
        with self.assertRaises(ExecutionDenied):rv.arm_handoff(self.f.ledger,self.ticket)
    def test_quarantine_prevents_handoff(self):
        self.prepare();self.f.ledger.quarantine()
        with self.assertRaises(ExecutionDenied):rv.arm_handoff(self.f.ledger,self.ticket)
    def test_wrong_state_response_rejected(self):
        self.prepare()
        with self.assertRaises(ExecutionDenied):rv.observe_response(self.f.ledger,self.rows()[0][1],b'{}',200,'application/json')
    def test_changed_record_between_arm_and_finish_refused(self):
        self.prepare();armed=rv.arm_handoff(self.f.ledger,self.ticket);self.mutate(messageCount=2)
        with self.assertRaises(ExecutionDenied):rv.observe_response(self.f.ledger,armed,b'{}',200,'application/json')
    def test_payload_claim_mismatch_refused(self):
        self.body['max_tokens']=19
        with self.assertRaises(ExecutionDenied):self.prepare()
        self.assertFalse(self.rows())
    def test_no_raw_content_or_api_secret_in_rows(self):
        self.send();text=_json(self.rows())
        for secret in [self.body['messages'][0]['content'],self.f.context.api_token,self.link.signing_key,self.link.socket_path]:
            self.assertNotIn(secret,text)
    def test_schema_and_boolean_corruption_refused(self):
        self.prepare();row=self.rows()[0][1]
        for edit in [{'version':True},{'messageCount':True},{'requestBytes':True},{'state':'sent'}, {'proof':'model saw'}]:
            with self.subTest(edit=edit),self.assertRaises(ExecutionDenied):rv.validate(seal(row|edit),self.f.context,self.f.policy)
    def test_discoverable_after_plugin_path_removed(self):
        program="import sys,importlib; p=sys.argv[1];sys.path.insert(0,p);import provider_egress;sys.path.remove(p);assert importlib.import_module('request_view').PREFIX=='alaz.evidence.request.v1.'"
        run=subprocess.run([sys.executable,'-I','-B','-c',program,str(ROOT/'packages/claw-hermes')],capture_output=True,text=True,timeout=10)
        self.assertEqual(run.returncode,0,run.stderr)


class SourceRequestBinding(unittest.TestCase):
    def setUp(self):
        self.f=source_fixture.CaptureIndependentQA('test_real_return_can_bind_but_never_proves_model_visibility')
        self.f.setUp();self.addCleanup(self.f.doCleanups);self.output=self.f.complete()
        self.body={'model':self.f.policy.model,'messages':copy.deepcopy(self.f.f.result['result']['messages']),'max_tokens':20}
        self.link=BrokerLink('/tmp/source-view/egress.sock','a'*32,'c'*64,'b'*64)
    def prepare(self,body=None):
        b=self.body if body is None else body;ticket=self.f.ledger.claim('provider',hashed(b))['ticket']
        doc=authorize_egress(self.f.ledger,self.link,ticket,b,record_view=True)
        return ticket,doc
    def query(self):return self.f.query()
    def views(self):return self.query()['evidenceView']['providerRequestViews']['requests']
    def test_exact_source_return_is_bound_at_preparation(self):
        self.prepare();view=self.views()[0];self.assertEqual(len(view['selectedEvidenceInclusions']),1)
        inc=view['selectedEvidenceInclusions'][0];self.assertEqual(inc['range']['end'],len(self.output.encode()))
        self.assertFalse(inc['handoffIntentRecorded']);self.assertFalse(inc['brokerHttpResponseObserved'])
    def test_matching_does_not_identify_initiating_run(self):
        self.body['user']='run_'+'a'*32;self.prepare();view=self.views()[0]
        self.assertIsNone(view['initiatingRunId']);self.assertFalse(view['initiatingRunVerified'])
        self.assertEqual(self.query()['evidenceView']['modelVisibility'],'unknown')
    def test_same_text_different_id_no_source_match(self):
        self.body['messages'][0]['tool_calls'][0]['id']='other';self.body['messages'][1]['tool_call_id']='other'
        self.prepare();self.assertEqual(self.views()[0]['selectedEvidenceInclusions'],[])
    def test_changed_content_no_fuzzy_match(self):
        self.body['messages'][1]['content']+=' ';self.prepare();self.assertEqual(self.views()[0]['selectedEvidenceInclusions'],[])
    def test_duplicate_id_does_not_gain_source_match(self):
        self.body['messages'].append(copy.deepcopy(self.body['messages'][1]));self.prepare()
        self.assertFalse(self.views()[0]['selectedEvidenceInclusions'])
    def test_wrong_function_does_not_match_source(self):
        self.body['messages'][0]['tool_calls'][0]['function']['name']='write_file';self.prepare()
        self.assertFalse(self.views()[0]['selectedEvidenceInclusions'])
    def test_absent_preceding_call_not_matched(self):
        self.body['messages']=self.body['messages'][1:];self.prepare()
        self.assertFalse(self.views()[0]['selectedEvidenceInclusions'])
    def test_source_not_present_at_preparation_is_not_backfilled(self):
        key,row=self.f.captures()[0];self.f.f.sql('DELETE FROM state_meta WHERE key=?',(key,))
        self.prepare();self.f.f.sql('INSERT INTO state_meta VALUES(?,?)',(key,_json(row)))
        self.assertFalse(self.views()[0]['selectedEvidenceInclusions'])
    def test_unsettled_source_never_included(self):
        key,row=self.f.captures()[0]
        claim_key=self.f.ledger.prefix+row['ticket'];claim=_load(dict(self._all_rows())[claim_key])
        self.f.f.sql('UPDATE state_meta SET value=? WHERE key=?',(_json(seal(claim|{'state':'reserved','outcome':None,'usage':None})),claim_key))
        self.prepare();self.assertFalse(self.views()[0]['selectedEvidenceInclusions'])
    def _all_rows(self):
        from contextlib import closing
        import sqlite3
        with closing(sqlite3.connect(self.f.home/'state.db')) as c:return c.execute('SELECT key,value FROM state_meta').fetchall()
    def test_validated_response_is_distinct_from_observation(self):
        ticket,_=self.prepare();armed=rv.arm_handoff(self.f.ledger,ticket)
        rv.observe_response(self.f.ledger,armed,b'{}',200,'application/json')
        self.assertTrue(self.views()[0]['brokerHttpResponseObserved']);self.assertFalse(self.views()[0]['providerResponseValidated'])
        self.f.ledger.settle(ticket,None,'unknown_usage');self.assertTrue(self.views()[0]['providerResponseValidated'])
        self.assertFalse(self.views()[0]['modelProcessingVerified'])
    def test_sql_reader_does_not_mutate_state_or_budget(self):
        self.prepare();before=self.f.f.hashes();counts=self.f.ledger.snapshot();r=self.query()
        self.assertFalse(r['writesPerformed']);self.assertEqual(before,self.f.f.hashes());self.assertEqual(counts,self.f.ledger.snapshot())
    def test_new_epoch_reads_history_without_resending(self):
        self.prepare();self.f.f.sql("UPDATE runtime_epoch SET epoch=3,instance_id='third'")
        self.f.context=replace(self.f.context,epoch=3,instance_id='third')
        self.assertEqual(len(self.views()[0]['selectedEvidenceInclusions']),1)
    def test_local_selection_not_a_request_dispatch(self):
        self.prepare();before=self._all_rows();r=self.query();self.assertEqual(before,self._all_rows())
        self.assertFalse(r['executionAllowed']);self.assertFalse(r['retryAllowed'])
    def test_source_deletion_does_not_reopen_file(self):
        self.prepare();self.f.file.unlink();self.assertEqual(len(self.views()[0]['selectedEvidenceInclusions']),1)
    def test_old_profile_without_request_records_stays_legacy(self):
        self.assertNotIn('providerRequestViews',self.query()['evidenceView'])
    def test_forged_observer_proof_does_not_upgrade(self):
        self.prepare();self.f.f.http['modelVisible']=True
        self.assertFalse(self.views()[0]['brokerHttpResponseObserved'])
