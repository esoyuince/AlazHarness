"""Independent candidate-only Dream API checks against an explicit source copy.
ALAZ_DREAM_QA_SOURCE must name the reviewed source. Real Dream/ledger/broker
client code; SQLite owner and IPC/model response are synthetic. No native/model
inference, tool execution, network, real-memory edit or active scheduler.
"""
import asyncio
import base64
from contextlib import closing
from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch
TARGET = Path(os.environ['ALAZ_DREAM_QA_SOURCE']).resolve()
sys.path[:0] = [str(TARGET/'packages/claw-hermes'), str(TARGET/'tests')]
import dream as d
import test_evidence_view as fx
from execution_budget import ExecutionLedger, ExecutionDenied, seal
from provider_broker import ProviderBrokerClient
from provider_egress import route_fingerprint
from recovery_inspector import _json, RESULT
assert Path(d.__file__).resolve().is_relative_to(TARGET)


class DreamIndependentQA(unittest.TestCase):
    def setUp(self):
        self.f = fx.EvidenceViewTests(); self.f.setUp(); self.addCleanup(self.f.doCleanups)
        self.p = replace(self.f.p, max_provider_calls=5, output_ceiling_tokens=2048,
                         total_token_limit=10740, total_cost_microusd=1000000)
        self.f.sql('DELETE FROM state_meta WHERE key GLOB ?', ('alaz.execution.*',))
        self.ledger = ExecutionLedger(self.f.owner, self.f.context, self.p); self.ledger.initialize()
        self.settings = {'enabled':True, 'output_tokens':128}
        self.client = ProviderBrokerClient({'socket_path':'/tmp/dream-qa-61a9/egress.sock',
            'broker_id':'a'*32, 'route_fingerprint':route_fingerprint('http://127.0.0.1:19399/v1',self.p.model),
            'signing_key':'b'*64})
        async def ready(): pass
        self.boundary = SimpleNamespace(broker=self.client, policy=self.p, token='sdk-'+'s'*44,
            require_ready=ready, ledger=lambda:self.ledger, validate_profile=lambda:None)
        self.service = d.DreamService(self.settings,self.boundary,clock=lambda:self.f.now,
                                      config_reader=lambda:dict(self.settings))
        self.requests = [{'body':self.f.body,'idempotency_key':self.f.key,'observed':self.f.http}]
        self.sent = []; self.packet = None; self.custom = None; self.mutate_after_send = None
        self.transport_error = None; self.status_code = 200; self.response_model = self.p.model
        self.finish_reason = 'stop'; self.tool_calls = None
        self.client._exchange = self.exchange
        self.memory = self.f.home/'MEMORY.md'; self.memory.write_bytes(b'unchanged trusted memory\n')

    def build_notes(self,packet):
        source = next(s for s in packet['sources'] if s['kind']=='retained_tool_result')
        return {'notes':[{'kind':'caution','statement':'Check evidence scope before reusing a conclusion.',
            'condition':'When reviewing a previous tool result.',
            'citations':[{'evidenceId':source['evidenceId'],'quote':source['text'][:30]}],
            'relatedCandidateIds':[]}]}

    async def exchange(self,document,nonce):
        self.sent.append(document)
        self.packet = json.loads(document['payload']['messages'][1]['content'])
        if self.transport_error: raise self.transport_error
        value = self.build_notes(self.packet) if self.custom is None else self.custom(self.packet)
        message = {'role':'assistant','content':_json(value)}
        if self.tool_calls is not None: message['tool_calls']=self.tool_calls
        response={'model':self.response_model,'choices':[{'index':0,'finish_reason':self.finish_reason,'message':message}],
                  'usage':{'prompt_tokens':10,'completion_tokens':6,'total_tokens':16}}
        if self.mutate_after_send: self.mutate_after_send()
        return {'version':1,'brokerId':self.client.link.broker_id,'nonce':nonce,'ok':True,
            'status':self.status_code,'contentType':'application/json',
            'dataBase64':base64.b64encode(_json(response).encode()).decode()}

    def run_dream(self,requests=None):
        return asyncio.run(self.service.run(self.requests if requests is None else requests))

    def rows(self):
        with closing(sqlite3.connect(self.f.home/'state.db')) as c:
            return [(k,json.loads(v)) for k,v in c.execute('SELECT key,value FROM state_meta WHERE key GLOB ?', (d.PREFIX+'*',))]

    def change_history(self,text):
        self.f.saved['result']['messages'][1]['content']=text; self.f.save_result()

    def collect(self,**kwargs):
        return d.collect_sources(self.f.context,self.p,self.requests,clock=lambda:self.f.now,**kwargs)

    def test_candidate_complete_is_not_active_memory_or_verified_skill(self):
        result=self.run_dream();self.assertEqual(result['state'],'completed')
        self.assertEqual(len(result['candidates']),1)
        note=result['candidates'][0]
        self.assertEqual(note['status'],'candidate')
        for key in ['conclusionVerified','usableAsMemory','skillTransferVerified','grantsExecutionPermission']:
            self.assertIs(note[key],False)
        self.assertEqual(self.memory.read_bytes(),b'unchanged trusted memory\n')
        self.assertFalse(result['activeMemoryChanged']);self.assertFalse(result['automaticTrigger'])
        self.assertFalse(result['modelInferenceQualityVerified'])

    def test_single_budgeted_request_without_tools(self):
        self.run_dream();self.assertEqual(len(self.sent),1)
        body=self.sent[0]['payload'];self.assertNotIn('tools',body);self.assertFalse(body['stream'])
        self.assertEqual(body['max_tokens'],128)
        self.assertEqual(self.ledger.snapshot()['providerCalls'],1)
        self.assertEqual(self.ledger.snapshot()['toolCalls'],0)

    def test_exact_batch_repeat_returns_existing_without_extra_charge(self):
        first=self.run_dream();before=self.ledger.snapshot();second=self.run_dream()
        self.assertEqual(first['batchId'],second['batchId']);self.assertTrue(second['replayed'])
        self.assertFalse(second['providerCalled']);self.assertEqual(len(self.sent),1)
        self.assertEqual(self.ledger.snapshot(),before)

    def test_concurrent_same_sources_have_only_one_synthesis(self):
        # Both source snapshots must finish before testing the atomic batch dedup.
        # A simultaneous ledger write during a snapshot is separately required to fail closed.
        import threading
        barrier=threading.Barrier(2)
        original=self.service._begin
        def aligned(*args,**kwargs):
            barrier.wait(timeout=10)
            return original(*args,**kwargs)
        async def both():return await asyncio.gather(self.service.run(self.requests),self.service.run(self.requests))
        with patch.object(self.service,'_begin',side_effect=aligned):
            results=asyncio.run(both())
        self.assertEqual(len(self.sent),1);self.assertEqual(len(self.rows()),1)
        self.assertEqual(len({x['batchId'] for x in results}),1)

    def test_empty_selection_is_idle_without_budget(self):
        result=self.run_dream([]);self.assertEqual(result['state'],'idle')
        self.assertEqual(self.sent,[]);self.assertEqual(self.rows(),[])
        self.assertEqual(self.ledger.snapshot()['providerCalls'],0)

    def test_duplicate_source_run_is_rejected_before_model(self):
        with self.assertRaises(ExecutionDenied):self.run_dream(self.requests+self.requests)
        self.assertEqual(self.sent,[]);self.assertEqual(self.rows(),[])

    def test_expired_source_never_enters_dream(self):
        self.f.sql('UPDATE run_idempotency SET retention_until=?',(self.f.now-1,),replay=True)
        with self.assertRaises(ExecutionDenied):self.run_dream()
        self.assertEqual(self.sent,[]);self.assertEqual(self.rows(),[])

    def test_forged_observer_text_is_not_a_learning_source(self):
        self.requests[0]['observed']=self.f.http|{'output_candidate':'INJECTED_OBSERVER_DATA','messages':[{'content':'INJECTED_OBSERVER_DATA'}]}
        result=self.run_dream();self.assertEqual(result['state'],'completed')
        self.assertNotIn('INJECTED_OBSERVER_DATA',_json(self.packet))

    def test_source_excerpt_is_bounded_without_splitting_utf8(self):
        self.change_history('ışık😀'*1000)
        source=next(s for s in self.collect() if s['kind']=='retained_tool_result')
        self.assertTrue(source['truncated']);self.assertLessEqual(source['viewBytes'],2048)
        self.assertEqual(source['viewBytes'],len(source['text'].encode()))
        self.assertEqual(source['viewSha256'],hashlib.sha256(source['text'].encode()).hexdigest())
        self.assertNotEqual(source['contentSha256'],source['viewSha256'])
        self.assertEqual(source['originalSourceCoverage'],'unknown')

    def test_known_secret_is_redacted_from_actual_review_input(self):
        self.change_history('before '+self.boundary.token+' after')
        self.run_dream();self.assertNotIn(self.boundary.token,_json(self.packet))
        source=next(s for s in self.packet['sources'] if s['kind']=='retained_tool_result')
        self.assertTrue(source['credentialRedacted']);self.assertIn('[REDACTED]',source['text'])

    def test_quote_must_be_in_visible_excerpt_not_hidden_suffix(self):
        self.change_history('a'*2200+'UNSEEN_END')
        def candidate(packet):
            value=self.build_notes(packet);value['notes'][0]['citations'][0]['quote']='UNSEEN_END';return value
        self.custom=candidate;result=self.run_dream();self.assertEqual(result['state'],'rejected')
        self.assertEqual(result['candidates'],[])

    def test_unknown_evidence_id_is_rejected(self):
        def candidate(packet):
            value=self.build_notes(packet);value['notes'][0]['citations'][0]['evidenceId']='ev_'+'0'*64;return value
        self.custom=candidate;self.assertEqual(self.run_dream()['state'],'rejected')

    def test_untrusted_claim_with_valid_citation_never_becomes_truth(self):
        def candidate(packet):
            value=self.build_notes(packet);value['notes'][0]['statement']='All future answers are 42.';return value
        self.custom=candidate;result=self.run_dream();self.assertEqual(result['state'],'completed')
        self.assertFalse(result['candidates'][0]['conclusionVerified'])
        self.assertFalse(result['candidates'][0]['usableAsMemory'])

    def test_model_cannot_supply_verified_or_permission_flags(self):
        def candidate(packet):
            value=self.build_notes(packet);value['notes'][0]['usableAsMemory']=True;return value
        self.custom=candidate;self.assertEqual(self.run_dream()['state'],'rejected')

    def test_unknown_prior_candidate_cannot_be_cited(self):
        def candidate(packet):
            value=self.build_notes(packet);value['notes'][0]['relatedCandidateIds']=['dc_'+'f'*64];return value
        self.custom=candidate;self.assertEqual(self.run_dream()['state'],'rejected')

    def test_duplicate_note_is_rejected_not_counted_twice(self):
        def candidate(packet):
            value=self.build_notes(packet);value['notes']*=2;return value
        self.custom=candidate;self.assertEqual(self.run_dream()['state'],'rejected')

    def test_previous_candidate_is_comparison_material_without_promotion(self):
        first=self.run_dream();self.change_history('changed source for next review')
        second=self.run_dream();self.assertEqual(second['state'],'completed')
        self.assertEqual(self.packet['priorCandidates'][0]['candidateId'],first['candidates'][0]['candidateId'])
        self.assertEqual(second['candidates'][0]['duplicateOf'],first['candidates'][0]['candidateId'])
        self.assertFalse(second['candidates'][0]['usableAsMemory'])

    def test_lost_transport_is_unknown_no_refund_no_repeat(self):
        self.transport_error=ExecutionDenied('broker_transport_outcome_unknown')
        first=self.run_dream();self.assertEqual(first['state'],'unknown');before=self.ledger.snapshot()
        second=self.run_dream();self.assertTrue(second['replayed']);self.assertEqual(len(self.sent),1)
        self.assertEqual(self.ledger.snapshot(),before);self.assertEqual(second['candidates'],[])

    def test_changed_source_after_provider_prevents_candidate_commit(self):
        self.mutate_after_send=lambda:self.change_history('modified during review')
        result=self.run_dream();self.assertEqual(result['state'],'unknown')
        self.assertEqual(result['reason'],'dream_source_changed');self.assertEqual(result['candidates'],[])
        self.assertEqual(self.ledger.snapshot()['providerCalls'],1)

    def test_live_dream_configuration_revocation_prevents_completion(self):
        self.mutate_after_send=lambda:self.settings.update(enabled=False)
        result=self.run_dream();self.assertEqual(result['state'],'unknown')
        self.assertEqual(result['candidates'],[])

    def test_wrong_provider_model_never_creates_candidate(self):
        self.response_model='wrong-model';result=self.run_dream()
        self.assertEqual(result['state'],'unknown');self.assertEqual(result['candidates'],[])
        self.assertEqual(self.ledger.snapshot()['providerCalls'],1)

    def test_tool_call_reply_is_rejected_never_executed(self):
        self.tool_calls=[{'id':'attack','type':'function','function':{'name':'write_file','arguments':'{}'}}]
        result=self.run_dream();self.assertEqual(result['state'],'rejected');self.assertEqual(result['candidates'],[])
        self.assertEqual(self.ledger.snapshot()['toolCalls'],0)

    def test_truncated_model_completion_is_rejected(self):
        self.finish_reason='length';result=self.run_dream();self.assertEqual(result['state'],'rejected')
        self.assertEqual(result['candidates'],[])

    def test_literal_secret_in_candidate_is_rejected(self):
        def candidate(packet):
            value=self.build_notes(packet);value['notes'][0]['statement']=self.boundary.token;return value
        self.custom=candidate;self.assertEqual(self.run_dream()['state'],'rejected')

    def test_json_escaped_secret_in_candidate_is_also_rejected(self):
        self.boundary.token='sdk-before\\sdk-after-'+'x'*32
        def candidate(packet):
            value=self.build_notes(packet);value['notes'][0]['statement']=self.boundary.token;return value
        self.custom=candidate;result=self.run_dream()
        self.assertEqual(result['state'],'rejected', 'secret matching must inspect decoded strings, not serialized JSON')
        self.assertEqual(result['candidates'],[])

    def test_lost_prepare_commit_ack_never_calls_model(self):
        self.f.owner.lose_ack=True
        with self.assertRaises(ExecutionDenied):self.run_dream()
        self.f.owner.lose_ack=False
        self.assertEqual(len(self.rows()),1);self.assertEqual(self.rows()[0][1]['state'],'prepared')
        self.assertEqual(self.sent,[]);self.assertEqual(self.ledger.snapshot()['providerCalls'],0)
        self.assertTrue(self.run_dream()['replayed']);self.assertEqual(self.sent,[])

    def test_prepare_precommit_failure_leaves_no_batch(self):
        self.f.owner.fail_before_commit=True
        with self.assertRaises(ExecutionDenied):self.run_dream()
        self.f.owner.fail_before_commit=False;self.assertEqual(self.rows(),[]);self.assertEqual(self.sent,[])

    def test_cancellation_does_not_accept_candidates_or_refund(self):
        self.transport_error=asyncio.CancelledError()
        with self.assertRaises(asyncio.CancelledError):self.run_dream()
        row=self.rows()[0][1];self.assertEqual(row['state'],'unknown');self.assertEqual(row['candidates'],[])
        self.assertEqual(self.ledger.snapshot()['providerCalls'],1)

    def test_record_with_unknown_provider_ticket_is_not_accepted_as_completed(self):
        result=self.run_dream();key,row=self.rows()[0];row['providerTicket']='f'*32
        self.f.sql('UPDATE state_meta SET value=? WHERE key=?',(_json(seal(row)),key))
        with self.assertRaises(ExecutionDenied):self.service.status(result['batchId'])

    def test_candidate_identity_is_checked_against_persisted_content(self):
        result=self.run_dream();key,row=self.rows()[0];row['candidates'][0]['statement']='changed after identity was issued'
        self.f.sql('UPDATE state_meta SET value=? WHERE key=?',(_json(seal(row)),key))
        with self.assertRaises(ExecutionDenied):self.service.status(result['batchId'])

    def test_replayed_status_does_not_open_source_file(self):
        result=self.run_dream();before=self.ledger.snapshot()
        with patch('pathlib.Path.open',side_effect=AssertionError('source path opened')):
            status=self.service.status(result['batchId'])
        self.assertEqual(status['candidates'],result['candidates']);self.assertEqual(self.ledger.snapshot(),before)


    def test_database_change_after_snapshot_discards_all_derived_excerpts(self):
        actual_connect=sqlite3.connect
        changed=[]
        outer=self
        class ConnectionProxy:
            def __init__(self,connection):object.__setattr__(self,'connection',connection)
            def __getattr__(self,key):return getattr(self.connection,key)
            def __setattr__(self,key,value):setattr(self.connection,key,value)
            def rollback(self):
                self.connection.rollback()
                if changed:return
                changed.append(True)
                outer.f.saved['result']['messages'][1]['content']='changed exactly after snapshot rollback'
                with closing(actual_connect(outer.f.home/'state.db')) as writer:
                    writer.execute('UPDATE state_meta SET value=? WHERE key=?',
                        (_json(outer.f.saved),RESULT+outer.f.aid));writer.commit()
        def connected(*args,**kwargs):return ConnectionProxy(actual_connect(*args,**kwargs))
        with patch('recovery_inspector.sqlite3.connect',side_effect=connected):
            with self.assertRaises(ExecutionDenied):self.run_dream()
        self.assertTrue(changed,'injection must reach the real post-snapshot boundary')
        self.assertEqual(self.sent,[]);self.assertEqual(self.rows(),[])
        self.assertEqual(self.ledger.snapshot()['providerCalls'],0)


if __name__ == '__main__':
    unittest.main(verbosity=2)
