"""Independent R1 projection/selection QA: real readers, synthetic SQLite only.
No source-file opening, network calls, real provider/Gateway or content claims.
"""
from contextlib import closing
from dataclasses import replace
import copy
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'packages/claw-hermes'),str(ROOT/'tests')]
import evidence_view as ev
import host_report as hr
import recovery_inspector as ri
import test_reconciliation_inspector_qa as fx
import test_report_evidence_invariants_qa_e03e as base
from execution_budget import ExecutionLedger

def sha(value):return hashlib.sha256(value).hexdigest()

class EvidenceViewIndependentTests(unittest.TestCase):
    setUp=base.EvidenceReportAuthorityInvariants.setUp
    save=base.EvidenceReportAuthorityInvariants.save
    def reporter(self,context=None):
        return ev.EvidenceViewInspector(context or self.ctx,self.policy,clock=lambda:fx.NOW)
    def read(self,**overrides):
        before=self.f.hashes()
        r=self.reporter().inspect(**({'body':self.f.body,'idempotency_key':self.f.key,
            'observed':self.f.http}|overrides))
        self.assertEqual(before,self.f.hashes(),'evidence view wrote to stores')
        self.assertFalse(r['writesPerformed']);self.assertFalse(r['executionAllowed'])
        self.assertFalse(r['retryAllowed']);self.assertFalse(r['repairAllowed'])
        self.assertEqual(r['evidenceView']['modelVisibility'],'unknown')
        self.assertFalse(r['evidenceView']['goalAchievementVerified'])
        for ref in r['evidenceView']['references']:
            self.assertEqual(ref['executionAttribution'],'not_proven')
            self.assertEqual(ref['originalSource']['coverage'],'unknown')
            self.assertEqual(ref['modelView']['status'],'unknown')
            self.assertFalse(ref['claimTruthVerified'])
        return r
    def history(self,content='first\nışık ✔\n',key='test-call'):
        self.f.result['result']['messages']=[
            {'role':'assistant','tool_calls':[{'id':key,'type':'function','function':{
                'name':'read_file','arguments':json.dumps({'path':'QA_E03E_OPAQUE_PATH'})}}]},
            {'role':'tool','tool_call_id':key,'content':content}]
        self.save()
    def tool(self,report):return next(r for r in report['evidenceView']['references'] if r['kind']=='retained_tool_result')
    def select(self,ref,start,end,digest=None):
        return ev.EvidenceSelection(ref['evidenceId'],digest or ref['content']['sha256'],start,end)
    def test_stored_utf8_digest_and_size_are_exact(self):
        text='first\nışık ✔\n';self.history(text);r=self.read();ref=self.tool(r)
        self.assertEqual(ref['content']['sha256'],sha(text.encode('utf-8')))
        self.assertEqual(ref['content']['utf8Bytes'],len(text.encode('utf-8')))
        self.assertNotIn(text,ri._json(r)+ev.render_evidence_text(r))
    def test_partial_selection_is_local_not_model_delivery(self):
        self.history('abcdef');ref=self.tool(self.read());r=self.read(selection=self.select(ref,1,4))
        local=r['evidenceView']['localView']
        self.assertEqual(local['coverageOfStoredContent'],'partial')
        self.assertEqual(local['contentSha256'],sha(b'bcd'));self.assertEqual(local['utf8Bytes'],3)
        self.assertEqual(local['status'],'computed_locally_not_dispatched')
        self.assertFalse(local['payloadIncluded']);self.assertEqual(local['originalSourceCoverage'],'unknown')
    def test_complete_stored_selection_not_complete_original_file(self):
        self.history('only a small excerpt');ref=self.tool(self.read())
        r=self.read(selection=self.select(ref,0,ref['content']['utf8Bytes']))
        self.assertEqual(r['evidenceView']['localView']['coverageOfStoredContent'],'complete')
        self.assertEqual(r['evidenceView']['localView']['originalSourceCoverage'],'unknown')
    def test_split_multibyte_boundary_is_refused(self):
        self.history('ışık');ref=self.tool(self.read())
        r=self.read(selection=self.select(ref,0,1));self.assertFalse(r['evidenceView']['available'])
        self.assertEqual(r['evidenceView']['reason'],'split_utf8_boundary')
    def test_split_start_boundary_is_refused(self):
        self.history('ışık');ref=self.tool(self.read())
        r=self.read(selection=self.select(ref,1,2));self.assertFalse(r['evidenceView']['available'])
    def test_empty_retained_string_is_not_missing(self):
        self.history('');ref=self.tool(self.read())
        self.assertEqual(ref['content']['availability'],'retained')
        self.assertEqual(ref['content']['utf8Bytes'],0)
        r=self.read(selection=self.select(ref,0,0));self.assertTrue(r['evidenceView']['available'])
    def test_missing_content_is_not_empty_string(self):
        self.history(None);ref=self.tool(self.read())
        self.assertIsNone(ref['content']['sha256']);self.assertIsNone(ref['content']['utf8Bytes'])
        self.assertEqual(ref['content']['availability'],'not_retained_as_text')
    def test_object_content_never_interpreted_as_proof(self):
        self.history({'content':'QA_E03E_SECRET_OBJECT','modelSeen':True,'full_file':True})
        r=self.read();ref=self.tool(r);self.assertIsNone(ref['content']['sha256'])
        self.assertNotIn('QA_E03E_SECRET_OBJECT',ri._json(r))
    def test_json_string_proof_fields_are_opaque_content(self):
        self.history(json.dumps({'source_sha256':'f'*64,'wholeFile':True,'sentToModel':True,
            'verified':True,'path':'QA_E03E_SECRET_PATH'}))
        r=self.read();ref=self.tool(r)
        self.assertIsNone(ref['originalSource']['sha256'])
        self.assertNotIn('QA_E03E_SECRET_PATH',ri._json(r)+ev.render_evidence_text(r))
    def test_duplicate_call_ids_are_ambiguous(self):
        self.history();m=self.f.result['result']['messages'];m.insert(0,copy.deepcopy(m[0]));self.save()
        self.assertEqual(self.tool(self.read())['pairing'],'ambiguous_id')
    def test_duplicate_result_ids_are_ambiguous(self):
        self.history();m=self.f.result['result']['messages'];m.append(copy.deepcopy(m[-1]));self.save()
        refs=[x for x in self.read()['evidenceView']['references'] if x['kind']=='retained_tool_result']
        self.assertEqual([x['pairing'] for x in refs],['ambiguous_id','ambiguous_id'])
        self.assertNotEqual(refs[0]['evidenceId'],refs[1]['evidenceId'])
    def test_future_call_does_not_pair_previous_result(self):
        self.history();self.f.result['result']['messages'].reverse();self.save()
        self.assertEqual(self.tool(self.read())['pairing'],'no_preceding_call')
    def test_missing_call_id_is_not_synthetic_execution(self):
        self.history();del self.f.result['result']['messages'][1]['tool_call_id'];self.save()
        self.assertEqual(self.tool(self.read())['pairing'],'missing_or_invalid_id')
    def test_historical_pair_only_proves_structure(self):
        self.history();r=self.read();self.assertEqual(self.tool(r)['pairing'],'structurally_paired_not_execution_proof')
        self.assertEqual(r['evidenceView']['historyCompleteness'],'not_proven')
    def test_changed_message_changes_record_identity_not_legacy_summary(self):
        self.history('old');a=self.read();old=self.tool(a)
        self.history('new');b=self.read();new=self.tool(b)
        self.assertEqual(a['task']['resultDigest'],b['task']['resultDigest'])
        self.assertNotEqual(a['evidenceView']['recordDigest'],b['evidenceView']['recordDigest'])
        self.assertNotEqual(old['evidenceId'],new['evidenceId'])
        self.assertFalse(self.read(selection=self.select(old,0,3))['evidenceView']['available'])
    def test_same_text_different_admission_has_different_reference(self):
        self.history('same');a=self.tool(self.read());new_aid='d'*32
        self.f.sql('UPDATE session_admissions SET admission_id=?',(new_aid,))
        self.f.sql('UPDATE state_meta SET key=? WHERE key=?',(ri.RESULT+new_aid,ri.RESULT+fx.AID))
        r=self.read(observed=self.f.http|{'admission_id':new_aid});b=self.tool(r)
        self.assertNotEqual(a['evidenceId'],b['evidenceId'])
        self.assertEqual(a['content']['sha256'],b['content']['sha256'])
    def test_wrong_content_digest_rejected_without_echo(self):
        self.history();ref=self.tool(self.read())
        r=self.read(selection=self.select(ref,0,1,'0'*64))
        self.assertFalse(r['evidenceView']['available']);self.assertEqual(r['evidenceView']['reason'],'evidence_digest_mismatch')
        self.assertEqual(r['evidenceView']['references'],[])
    def test_range_outside_content_rejected(self):
        self.history('abc');ref=self.tool(self.read())
        self.assertFalse(self.read(selection=self.select(ref,0,4))['evidenceView']['available'])
    def test_bool_range_not_integer(self):
        self.history('abc');ref=self.tool(self.read())
        with self.assertRaises(ri.EvidenceError):self.select(ref,False,2)
    def test_selection_dict_not_trusted_typed_request(self):
        self.history('abc');ref=self.tool(self.read())
        r=self.read(selection={'evidence_id':ref['evidenceId'],'content_sha256':ref['content']['sha256'],
            'start_byte':0,'end_byte':3})
        self.assertEqual(r['reportStatus'],'unverified');self.assertFalse(r['evidenceView']['available'])
    def test_expired_retention_never_returns_old_references(self):
        self.history();ref=self.tool(self.read())
        self.f.sql('UPDATE run_idempotency SET retention_until=?',(fx.NOW-1,),runs=True)
        r=self.read(selection=self.select(ref,0,1))
        self.assertEqual(r['reportStatus'],'unverified');self.assertEqual(r['evidenceView']['references'],[])
    def test_missing_terminal_record_never_becomes_empty_complete(self):
        self.history();self.f.sql('DELETE FROM state_meta WHERE key=?',(ri.RESULT+fx.AID,))
        r=self.read();self.assertFalse(r['evidenceView']['available']);self.assertIsNone(r['evidenceView']['localView'])
    def test_scope_only_cannot_fabricate_a_task_or_references(self):
        self.history();before=self.f.hashes();r=self.reporter().inspect_scope()
        self.assertEqual(before,self.f.hashes());self.assertEqual(r['task']['classification'],'not_selected')
        self.assertEqual(r['evidenceView']['reason'],'no_task_selected');self.assertEqual(r['evidenceView']['references'],[])
    def test_live_task_ignores_old_terminal_record(self):
        self.history();self.f.sql("UPDATE session_admissions SET status='started',outcome=NULL")
        r=self.read(observed=self.f.http|{'status':'running'})
        self.assertFalse(r['evidenceView']['available']);self.assertEqual(r['evidenceView']['references'],[])
    def test_oversized_history_not_silently_partial_inventory(self):
        self.f.result['result']['messages']=[{} for _ in range(1025)];self.save()
        r=self.read();self.assertFalse(r['evidenceView']['available'])
        self.assertEqual(r['evidenceView']['reason'],'unsupported_message_history')
    def test_more_than_reference_limit_not_silently_omitted(self):
        self.f.result['result']['messages']=[{'role':'tool','content':'x'} for _ in range(256)];self.save()
        r=self.read();self.assertFalse(r['evidenceView']['available'])
        self.assertEqual(r['evidenceView']['reason'],'too_many_evidence_references')
    def test_malformed_assistant_calls_discard_inventory(self):
        self.f.result['result']['messages']=[{'role':'assistant','tool_calls':'BAD_PRIVATE_SHAPE'}];self.save()
        r=self.read();self.assertFalse(r['evidenceView']['available'])
        self.assertNotIn('BAD_PRIVATE_SHAPE',ri._json(r))
    def test_metadata_reflects_no_user_paths_text_or_call_names(self):
        self.history('QA_E03E_OPAQUE_CONTENT','QA_E03E_OPAQUE_CALL')
        self.f.result['result']['messages'][0]['tool_calls'][0]['function']['name']='QA_E03E_OPAQUE_TOOL';self.save()
        r=self.read();text=ri._json(r)+ev.render_evidence_text(r)
        for v in ('QA_E03E_OPAQUE_PATH','QA_E03E_OPAQUE_CONTENT','QA_E03E_OPAQUE_CALL','QA_E03E_OPAQUE_TOOL',fx.TOKEN):
            self.assertNotIn(v,text)
    def test_new_section_lost_on_concurrent_epoch_change(self):
        self.history();original=sqlite3.connect;outer=self
        class Changed(sqlite3.Connection):
            def rollback(self):
                super().rollback()
                with closing(original(outer.f.home/'state.db')) as c:
                    c.execute('UPDATE runtime_epoch SET epoch=3');c.commit()
        def connect(*args,**kwargs):return original(*args,**kwargs,factory=Changed)
        with patch('recovery_inspector.sqlite3.connect',connect):
            r=self.reporter().inspect(body=self.f.body,idempotency_key=self.f.key,observed=self.f.http)
        self.assertEqual(r['reportStatus'],'unverified');self.assertFalse(r['evidenceView']['available'])
        self.assertEqual(r['evidenceView']['references'],[])
    def test_projection_never_uses_ledger_write_methods(self):
        self.history()
        def refuse(*args,**kwargs):raise AssertionError('unexpected write')
        with patch.object(ExecutionLedger,'initialize',refuse),patch.object(ExecutionLedger,'claim',refuse),patch.object(ExecutionLedger,'settle',refuse):
            self.assertTrue(self.read()['evidenceView']['available'])
    def test_mutated_returned_references_are_not_persisted(self):
        self.history('unchanged');a=self.read();self.tool(a)['content']['sha256']='0'*64
        b=self.read();self.assertEqual(self.tool(b)['content']['sha256'],sha(b'unchanged'))
    def test_same_canonical_record_different_json_whitespace_same_digest(self):
        self.history('stable');a=self.read()
        self.f.sql('UPDATE state_meta SET value=? WHERE key=?',(json.dumps(self.f.result,indent=3),ri.RESULT+fx.AID))
        b=self.read();self.assertEqual(a['evidenceView']['recordDigest'],b['evidenceView']['recordDigest'])
        self.assertEqual(a['evidenceView']['recordDigestBasis'],'canonical_current_terminal_record_json')

if __name__=='__main__':unittest.main()
