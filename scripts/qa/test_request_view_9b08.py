"""Independent R1B2 API QA against an explicitly selected immutable source tree.
Set ALAZ_R1B2_QA_SOURCE to the reviewed checkout/copy. This opt-in script is not
part of automatic baseline CI discovery. SQLite/native/IPC ports are synthetic.
"""
import asyncio
import base64
from contextlib import closing
from dataclasses import replace
import copy
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import sys
import unittest
from unittest.mock import patch
TARGET=Path(os.environ['ALAZ_R1B2_QA_SOURCE']).resolve()
if not (TARGET/'packages/claw-hermes/request_view.py').is_file():
    raise RuntimeError('Explicit reviewed R1B2 source required')
sys.path[:0]=[str(TARGET/'packages/claw-hermes'),str(TARGET/'tests')]
import test_source_capture_qa_c72e as source_fixture
import request_view as rv
import provider_egress as pe
import provider_broker as pb
import source_capture as sc
import evidence_view as ev
from execution_budget import ExecutionDenied,seal
from recovery_inspector import _json


class RequestViewIndependentQA(unittest.TestCase):
    def setUp(self):
        self.f=source_fixture.CaptureIndependentQA()
        self.f.setUp();self.addCleanup(self.f.doCleanups)
        self.ledger=self.f.ledger
        self.link=pe.BrokerLink('/tmp/request-qa-9b08/egress.sock','a'*32,
            pe.route_fingerprint('http://127.0.0.1:19231/v1',self.f.policy.model),'b'*64)
        self.client=pb.ProviderBrokerClient({'socket_path':self.link.socket_path,
            'broker_id':self.link.broker_id,'route_fingerprint':self.link.route_fingerprint,
            'signing_key':self.link.signing_key})
        self.pticket=None

    def body(self,output='{"content":"native-payload"}',ident=None,name='read_file'):
        ident=ident or self.f.tool_id
        return {'model':self.f.policy.model,'max_tokens':20,'messages':[
            {'role':'assistant','content':None,'tool_calls':[{'id':ident,'type':'function',
                'function':{'name':name,'arguments':'{}'}}]},
            {'role':'tool','tool_call_id':ident,'content':output}]}

    def prepare(self,body=None):
        body=body or self.body()
        self.pticket=self.ledger.claim('provider',pe.hashed(body))
        return pe.authorize_egress(self.ledger,self.link,self.pticket['ticket'],body,record_view=True)

    def rows(self,prefix=rv.PREFIX):
        with closing(sqlite3.connect(self.f.home/'state.db')) as c:
            return [(k,json.loads(v)) for k,v in c.execute('SELECT key,value FROM state_meta WHERE key GLOB ? ORDER BY key',(prefix+'*',))]

    def row(self):return self.rows()[0][1]
    def section(self):
        report=self.f.query();self.assertTrue(report['evidenceView']['available'],report)
        return report['evidenceView']
    def request(self):return self.section()['providerRequestViews']['requests'][0]
    def inclusion(self):
        values=self.request()['selectedEvidenceInclusions'];self.assertEqual(len(values),1)
        return values[0]
    def arm(self):return rv.arm_handoff(self.ledger,self.pticket['ticket'])
    def observe(self,armed,raw=b'{}',status=200):
        return rv.observe_response(self.ledger,armed,raw,status,'application/json')
    def complete_source(self):return self.f.complete()
    def corrupt(self,**fields):
        key,row=self.rows()[0];self.f.f.sql('UPDATE state_meta SET value=? WHERE key=?',(_json(seal(row|fields)),key))
    def refused_report(self):
        report=self.f.query();self.assertFalse(report['evidenceView']['available'],report)
        self.assertEqual(report['evidenceView']['references'],[]);self.assertFalse(report['executionAllowed'])
        return report
    def reply(self):
        return {'version':1,'brokerId':self.link.broker_id,'nonce':self.pticket['ticket'],
            'ok':True,'status':200,'contentType':'application/json','dataBase64':base64.b64encode(b'{}').decode()}
    def send_with_fault(self,which,flag):
        self.complete_source();body=self.body();self.pticket=self.ledger.claim('provider',pe.hashed(body))
        # The prepare callback returns BEFORE its enclosing transaction commits.
        # Keep injected failure active through authorize_egress's actual COMMIT.
        module,name=(pb,'authorize_egress') if which=='prepare_in_transaction' else (rv,which)
        original=getattr(module,name)
        def wrapped(*args,**kwargs):
            setattr(self.ledger.db,flag,True)
            try:return original(*args,**kwargs)
            finally:setattr(self.ledger.db,flag,False)
        async def run():
            async def reply(*args):return self.reply()
            with patch.object(module,name,side_effect=wrapped),patch.object(self.client,'_exchange',side_effect=reply) as exchange:
                with self.assertRaises(ExecutionDenied):
                    await self.client.send(self.ledger,self.pticket['ticket'],body,record_view=True)
                return exchange.call_count
        return asyncio.run(run())

    def test_prepared_inclusion_is_not_handoff_response_or_model_processing(self):
        self.complete_source();doc=self.prepare();r=self.request();inc=self.inclusion()
        self.assertEqual(r['requestDigest'],pe.hashed(doc['payload']))
        self.assertEqual(r['requestBytes'],len(_json(doc['payload']).encode()))
        self.assertEqual(r['state'],'prepared');self.assertIsNone(r['initiatingRunId'])
        self.assertTrue(inc['preparationRecorded']);self.assertFalse(inc['handoffIntentRecorded'])
        self.assertFalse(inc['brokerHttpResponseObserved']);self.assertFalse(inc['providerResponseValidated'])
        self.assertFalse(inc['initiatingRunVerified']);self.assertFalse(inc['modelProcessingVerified'])
        self.assertFalse(inc['understandingVerified']);self.assertEqual(inc['sourceFileCoverage'],'not_inferred')

    def test_armed_intent_is_not_a_send_receipt(self):
        self.complete_source();self.prepare();self.arm();inc=self.inclusion()
        self.assertTrue(inc['handoffIntentRecorded']);self.assertFalse(inc['brokerHttpResponseObserved'])
        self.assertFalse(inc['providerResponseValidated']);self.assertFalse(inc['modelProcessingVerified'])
        self.assertEqual(self.section()['modelVisibility'],'unknown')

    def test_response_observation_is_separate_from_provider_validation(self):
        self.complete_source();self.prepare();self.observe(self.arm(),b'not valid provider JSON')
        self.assertTrue(self.inclusion()['brokerHttpResponseObserved'])
        self.assertFalse(self.inclusion()['providerResponseValidated'])
        self.assertFalse(self.inclusion()['modelProcessingVerified'])

    def test_successful_settlement_still_does_not_prove_comprehension(self):
        self.complete_source();self.prepare();self.observe(self.arm())
        self.ledger.settle(self.pticket['ticket'],{'input_tokens':1,'output_tokens':1},'response')
        inc=self.inclusion();self.assertTrue(inc['providerResponseValidated'])
        self.assertFalse(inc['understandingVerified']);self.assertFalse(inc['initiatingRunVerified'])
        self.assertFalse(inc['grantsExecutionPermission'])

    def test_error_response_not_successfully_validated(self):
        self.complete_source();self.prepare();self.observe(self.arm(),status=503)
        self.ledger.settle(self.pticket['ticket'],None,'transport_error')
        self.assertTrue(self.inclusion()['brokerHttpResponseObserved'])
        self.assertFalse(self.inclusion()['providerResponseValidated'])

    def test_settlement_without_observed_response_is_a_conflict(self):
        self.complete_source();self.prepare();self.arm()
        self.ledger.settle(self.pticket['ticket'],None,'unknown_usage')
        self.refused_report()

    def test_source_created_after_preparation_never_retroactively_attaches(self):
        self.prepare();self.complete_source()
        self.assertEqual(self.request()['selectedEvidenceInclusions'],[])
        self.assertIsNone(self.row()['toolMessages'][0]['sourceCaptureDigest'])

    def test_changed_return_text_does_not_match_source(self):
        self.complete_source();self.prepare(self.body(output='{"content":"native-payload"}\n'))
        self.assertEqual(self.request()['selectedEvidenceInclusions'],[])

    def test_equal_text_different_tool_identity_is_not_bound(self):
        self.complete_source();self.prepare(self.body(ident='other-call'))
        self.assertEqual(self.request()['selectedEvidenceInclusions'],[])

    def test_wrong_assistant_tool_name_is_not_bound(self):
        self.complete_source();self.prepare(self.body(name='write_file'))
        self.assertEqual(self.request()['selectedEvidenceInclusions'],[])

    def test_duplicate_result_identity_is_not_bound(self):
        self.complete_source();body=self.body();body['messages'].append(copy.deepcopy(body['messages'][1]))
        self.prepare(body);self.assertEqual(self.request()['selectedEvidenceInclusions'],[])

    def test_ambiguous_two_source_captures_abort_authorization_atomically(self):
        output=self.f.invoke();self.ledger.settle(self.f.ticket['ticket'],None,'tool_return')
        self.f.ticket=self.ledger.claim('read_file',self.f.fp);self.complete_source()
        with self.assertRaisesRegex(ExecutionDenied,'ambiguous_request_source'):self.prepare()
        self.assertEqual(self.rows(),[]);self.assertEqual(self.rows(pe.EGRESS),[])
        self.assertEqual(self.ledger.snapshot()['providerCalls'],1)

    def test_missing_text_and_empty_text_have_distinct_inventory(self):
        empty=rv.inventory(self.body(output=''))[0][0]
        null=rv.inventory(self.body(output=None))[0][0]
        self.assertEqual(empty['contentBytes'],0);self.assertEqual(empty['contentSha256'],hashlib.sha256(b'').hexdigest())
        self.assertIsNone(null['contentBytes']);self.assertIsNone(null['contentSha256'])

    def test_source_body_and_tool_identifier_do_not_leak_to_manifest(self):
        self.complete_source();self.prepare();encoded=_json(self.row())
        for text in [str(self.f.file),'native-payload',self.f.tool_id,self.f.context.api_token,self.link.signing_key]:
            self.assertNotIn(text,encoded)

    def test_user_field_does_not_create_initiating_run_attribution(self):
        self.complete_source();body=self.body()|{'user':'run_'+'f'*32};self.prepare(body)
        self.assertIsNone(self.request()['initiatingRunId']);self.assertFalse(self.inclusion()['initiatingRunVerified'])

    def test_prepare_failure_rolls_back_grant_and_view(self):
        self.assertEqual(self.send_with_fault('prepare_in_transaction','pre_fail'),0)
        self.assertEqual(self.rows(),[]);self.assertEqual(self.rows(pe.EGRESS),[])
        self.assertEqual(self.ledger.snapshot()['providerCalls'],1)

    def test_prepare_lost_ack_records_no_ipc_or_reoffer(self):
        self.assertEqual(self.send_with_fault('prepare_in_transaction','lose_ack'),0)
        self.assertEqual(self.row()['state'],'prepared');self.assertEqual(len(self.rows(pe.EGRESS)),1)
        with self.assertRaisesRegex(ExecutionDenied,'egress_already_authorized'):
            pe.authorize_egress(self.ledger,self.link,self.pticket['ticket'],self.body(),record_view=True)

    def test_arm_precommit_failure_prevents_ipc(self):
        self.assertEqual(self.send_with_fault('arm_handoff','pre_fail'),0)
        self.assertEqual(self.row()['state'],'prepared')

    def test_arm_lost_ack_can_record_intent_without_any_ipc(self):
        self.assertEqual(self.send_with_fault('arm_handoff','lose_ack'),0)
        self.assertEqual(self.row()['state'],'handoff_armed')
        self.assertFalse(self.inclusion()['brokerHttpResponseObserved'])

    def test_observe_precommit_failure_keeps_only_handoff(self):
        self.assertEqual(self.send_with_fault('observe_response','pre_fail'),1)
        self.assertEqual(self.row()['state'],'handoff_armed')
        self.assertFalse(self.inclusion()['providerResponseValidated'])

    def test_observe_lost_ack_does_not_prove_downstream_delivery(self):
        self.assertEqual(self.send_with_fault('observe_response','lose_ack'),1)
        self.assertEqual(self.row()['state'],'broker_response_observed')
        self.assertFalse(self.inclusion()['providerResponseValidated'])
        self.assertFalse(self.inclusion()['modelProcessingVerified'])

    def test_epoch_change_before_handoff_refuses(self):
        self.complete_source();self.prepare();self.f.f.sql('UPDATE runtime_epoch SET epoch=3')
        with self.assertRaises(ExecutionDenied):self.arm()
        self.assertEqual(self.row()['state'],'prepared')

    def test_second_handoff_attempt_is_not_idempotent_permission(self):
        self.complete_source();self.prepare();self.arm()
        with self.assertRaises(ExecutionDenied):self.arm()

    def test_missing_egress_cannot_be_reconstructed_from_manifest(self):
        self.complete_source();self.prepare();self.f.f.sql('DELETE FROM state_meta WHERE key GLOB ?',(pe.EGRESS+'*',))
        self.refused_report();self.assertEqual(self.rows(pe.EGRESS),[])

    def test_resealed_wrong_request_hash_refused_by_actual_provider_claim(self):
        self.complete_source();self.prepare();self.corrupt(requestDigest='f'*64)
        self.refused_report()

    def test_wrong_scope_or_boolean_metadata_refused(self):
        self.complete_source();self.prepare();self.corrupt(messageCount=True)
        self.refused_report()

    def test_reader_does_not_mutate_application_data_or_budget(self):
        self.complete_source();self.prepare();before=self.f.f.hashes();budget=self.ledger.snapshot()
        report=self.f.query();self.assertEqual(self.f.f.hashes(),before)
        self.assertEqual(self.ledger.snapshot(),budget)
        self.assertFalse(report['writesPerformed']);self.assertFalse(report['executionAllowed'])

    def test_new_epoch_can_read_historical_request_but_not_arm_it(self):
        self.complete_source();self.prepare();self.f.f.sql("UPDATE runtime_epoch SET epoch=3,instance_id='third'")
        self.f.context=replace(self.f.context,epoch=3,instance_id='third')
        self.assertEqual(self.request()['state'],'prepared')
        with self.assertRaises(ExecutionDenied):self.arm()

    def test_optout_keeps_legacy_request_visibility_unknown(self):
        self.complete_source();body=self.body();ticket=self.ledger.claim('provider',pe.hashed(body))
        pe.authorize_egress(self.ledger,self.link,ticket['ticket'],body)
        self.assertEqual(self.rows(),[]);self.assertNotIn('providerRequestViews',self.section())


if __name__=='__main__':unittest.main(verbosity=2)
