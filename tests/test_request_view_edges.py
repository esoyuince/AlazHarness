"""Bounded malformed-record and option regression, no native process/model."""
import copy
from dataclasses import asdict
from pathlib import Path
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'packages/claw-hermes'),str(ROOT/'tests')]
import test_request_view as fixture
import request_view as rv
from execution_boundary import ExecutionBoundary
from execution_budget import ExecutionDenied,ExecutionPolicy,seal
from recovery_inspector import _json

class RequestViewEdges(unittest.TestCase):
    def setUp(self):
        self.f=fixture.SourceRequestBinding('test_exact_source_return_is_bound_at_preparation');self.f.setUp();self.addCleanup(self.f.doCleanups)
    def alter(self,change):
        ticket,_=self.f.prepare();owner=self.f.f;key=rv.key_for(owner.context,ticket)
        rows=dict(self.f._all_rows());import json
        row=json.loads(rows[key]);row=change(row)
        owner.f.sql('UPDATE state_meta SET value=? WHERE key=?',(_json(row),key))
        report=self.f.query();self.assertFalse(report['evidenceView']['available'],report)
        self.assertFalse(report['executionAllowed']);self.assertFalse(report['retryAllowed'])
    def test_tampered_digest_discarded(self):self.alter(lambda r:r|{'requestBytes':r['requestBytes']+1})
    def test_wrong_broker_resealed_still_conflicts_with_grant(self):self.alter(lambda r:seal(r|{'brokerId':'d'*32}))
    def test_wrong_request_digest_cannot_override_claim(self):self.alter(lambda r:seal(r|{'requestDigest':'d'*64}))
    def test_foreign_scope_not_published(self):self.alter(lambda r:seal(r|{'scope':'d'*64}))
    def test_future_epoch_not_accepted(self):self.alter(lambda r:seal(r|{'epoch':100}))
    def test_forged_complete_state_not_published(self):self.alter(lambda r:seal(r|{'state':'completed'}))
    def test_extra_observer_proof_field_not_interpreted(self):self.alter(lambda r:seal(r|{'understood':True}))
    def test_boolean_tool_index_rejected(self):
        def change(r):r['toolMessages'][0]['index']=True;return seal(r)
        self.alter(change)
    def test_wrong_included_output_rejected(self):
        def change(r):r['toolMessages'][0]['contentSha256']='d'*64;return seal(r)
        self.alter(change)
    def test_wrong_tool_identity_rejected(self):
        def change(r):r['toolMessages'][0]['toolCallHash']='d'*64;return seal(r)
        self.alter(change)
    def test_duplicate_message_indexes_rejected(self):
        def change(r):r['toolMessages'].append(copy.deepcopy(r['toolMessages'][0]));return seal(r)
        self.alter(change)
    def test_missing_grant_refuses_reader(self):
        ticket,_=self.f.prepare();owner=self.f.f
        from provider_egress import EGRESS
        owner.f.sql('DELETE FROM state_meta WHERE key=?',(EGRESS+owner.context.scope+'.'+ticket,))
        self.assertFalse(self.f.query()['evidenceView']['available'])
    def test_settlement_without_response_record_refused(self):
        ticket,_=self.f.prepare();self.f.f.ledger.settle(ticket,None,'unknown_usage')
        self.assertFalse(self.f.query()['evidenceView']['available'])
    def test_two_sources_with_identical_id_and_text_are_ambiguous(self):
        source=self.f.f;source.f.sql("UPDATE session_admissions SET status='started',outcome=NULL")
        source.ticket=source.ledger.claim('read_file',source.fp);source.complete()
        with self.assertRaisesRegex(ExecutionDenied,'ambiguous_request_source'):self.f.prepare()
    def test_none_tool_content_is_not_zero_length_text(self):
        body={'messages':[{'role':'tool','tool_call_id':'abc','content':None}]}
        self.assertIsNone(rv.inventory(body)[0][0]['contentBytes'])
        body['messages'][0]['content']='';self.assertEqual(rv.inventory(body)[0][0]['contentBytes'],0)
    def test_invalid_false_call_list_is_not_empty(self):
        with self.assertRaises(ExecutionDenied):rv.inventory({'messages':[{'role':'assistant','tool_calls':False}]})
    def test_message_bound_is_enforced(self):
        with self.assertRaises(ExecutionDenied):rv.inventory({'messages':[{'role':'user','content':''}]*1025})
    def test_tool_bound_is_enforced(self):
        with self.assertRaises(ExecutionDenied):rv.inventory({'messages':[{'role':'tool','content':''}]*257})

class RequestViewSettings(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);self.path=Path(tmp.name)/'input.txt';self.path.write_bytes(b'fixture')
        self.settings={'policy':asdict(ExecutionPolicy('test',2,1,100,20,240,1000,1000000,2000000)),
            'provider_bearer':'x'*64,'allowed_read_files':[str(self.path)],'provider_broker':{
             'socket_path':'/tmp/request-setting/egress.sock','broker_id':'a'*32,'route_fingerprint':'c'*64,'signing_key':'b'*64}}
    def test_default_off(self):self.assertFalse(ExecutionBoundary(self.settings).record_request_view)
    def test_true_requires_broker(self):
        settings=self.settings|{'record_request_view':True,'upstream_base_url':'http://127.0.0.1:19900/v1'};del settings['provider_broker']
        with self.assertRaisesRegex(ExecutionDenied,'request_view_requires_broker'):ExecutionBoundary(settings)
    def test_true_allowed_with_broker(self):self.assertTrue(ExecutionBoundary(self.settings|{'record_request_view':True}).record_request_view)
    def test_no_truthiness_coercion(self):
        for value in [1,'true',None,[],{}]:
            with self.subTest(value=value),self.assertRaises(ExecutionDenied):ExecutionBoundary(self.settings|{'record_request_view':value})
