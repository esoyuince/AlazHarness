"""R1 production readers with explicitly synthetic native SQLite fixtures.
No native agent, provider inference, dispatch, or source-file access by the view.
"""
from contextlib import closing
from dataclasses import asdict, replace, FrozenInstanceError
import hashlib
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import time
import unittest
from unittest.mock import patch
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'packages/claw-hermes'))
sys.path.insert(0, str(ROOT/'tests'))
import test_host_report as fx
import recovery_inspector as ri
import host_report as hr
import evidence_view as ev


class EvidenceViewTests(unittest.TestCase):
    def setUp(self):
        fx.HostReportTests.setUp(self)
        self.inspector = ev.EvidenceViewInspector(self.context, self.p, clock=lambda: self.now)
        self.text = 'Aışık😀\r\nsecond line\n'
        self.saved['result']['messages'] = [
            {'role': 'assistant', 'content': '', 'tool_calls': [
                {'id': 'tool-one', 'type': 'function', 'function': {'name': 'read_file', 'arguments': '{}'}}]},
            {'role': 'tool', 'tool_call_id': 'tool-one', 'name': 'read_file', 'content': self.text}]
        self.save_result()
    def sql(self,*args,**kwargs):return fx.HostReportTests.sql(self,*args,**kwargs)
    def save_result(self):return fx.HostReportTests.save_result(self)
    def hashes(self):return fx.HostReportTests.hashes(self)
    def query(self,**changes):
        return self.inspector.inspect(**(dict(body=self.body,idempotency_key=self.key,observed=self.http)|changes))
    def refs(self):return self.query()['evidenceView']['references']
    def select(self,start=0,end=None,ref=None):
        ref = ref or self.refs()[0]
        return ev.EvidenceSelection(ref['evidenceId'],ref['content']['sha256'],start,
                                    ref['content']['utf8Bytes'] if end is None else end)
    def unavailable(self,**changes):
        r=self.query(**changes);self.assertFalse(r['evidenceView']['available'],r)
        self.assertEqual(r['evidenceView']['references'],[]);self.assertFalse(r['executionAllowed'])
        self.assertFalse(r['retryAllowed']);self.assertFalse(r['repairAllowed']);return r
    def test_legacy_report_unchanged(self):
        original=hr.HostReportInspector(self.context,self.p,clock=lambda:self.now).inspect(
            body=self.body,idempotency_key=self.key,observed=self.http)
        observed=self.query();observed.pop('evidenceView');self.assertEqual(original,observed)
    def test_content_is_utf8_bytes_not_char_count(self):
        ref=self.refs()[0];self.assertEqual(ref['content']['utf8Bytes'],len(self.text.encode()))
        self.assertEqual(ref['content']['sha256'],hashlib.sha256(self.text.encode()).hexdigest())
    def test_retained_record_not_original_file_digest(self):
        ref=self.refs()[0];self.assertEqual(ref['content']['digestBasis'],'stored_content_utf8')
        self.assertIsNone(ref['originalSource']['sha256']);self.assertEqual(ref['originalSource']['coverage'],'unknown')
    def test_no_visibility_inferred_from_terminal_or_usage(self):
        r=self.query()['evidenceView'];self.assertEqual(r['modelVisibility'],'unknown')
        for ref in r['references']:
            self.assertEqual(ref['modelView']['status'],'unknown');self.assertIsNone(ref['modelView']['ranges'])
            self.assertFalse(ref['modelView']['understandingVerified']);self.assertFalse(ref['claimTruthVerified'])
    def test_snapshot_digest_not_old_output_only_digest(self):
        r=self.query();self.assertNotEqual(r['evidenceView']['recordDigest'],r['task']['resultDigest'])
        self.assertEqual(r['evidenceView']['recordDigest'],hashlib.sha256(ri._json(self.saved).encode()).hexdigest())
    def test_pairing_is_not_execution_proof(self):
        ref=self.refs()[0];self.assertEqual(ref['pairing'],'structurally_paired_not_execution_proof')
        self.assertEqual(ref['executionAttribution'],'not_proven')
    def test_missing_id_not_valid_pair(self):
        self.saved['result']['messages'][1].pop('tool_call_id');self.save_result()
        self.assertEqual(self.refs()[0]['pairing'],'missing_or_invalid_id')
    def test_duplicate_result_id_is_ambiguous(self):
        self.saved['result']['messages'].append(self.saved['result']['messages'][1].copy());self.save_result()
        self.assertEqual(self.refs()[0]['pairing'],'ambiguous_id');self.assertEqual(self.refs()[1]['pairing'],'ambiguous_id')
    def test_duplicate_call_id_is_ambiguous(self):
        c=self.saved['result']['messages'][0]['tool_calls'];c.append(c[0].copy());self.save_result()
        self.assertEqual(self.refs()[0]['pairing'],'ambiguous_id')
    def test_future_call_does_not_pair(self):
        self.saved['result']['messages'].reverse();self.save_result()
        self.assertEqual(self.refs()[0]['pairing'],'no_preceding_call')
    def test_history_suffix_flag_does_not_bind_execution(self):
        self.saved['result']['_messages_are_turn_suffix']=True;self.save_result()
        self.assertEqual(self.refs()[0]['executionAttribution'],'not_proven')
    def test_proof_in_tool_text_is_not_authority(self):
        self.saved['result']['messages'][1]['content']=json.dumps({'modelVisible':True,'complete':True,'sourcePath':'C:/SECRET','sha256':'a'*64})
        self.save_result();r=self.query();ref=r['evidenceView']['references'][0]
        self.assertEqual(ref['modelView']['status'],'unknown');self.assertEqual(ref['originalSource']['coverage'],'unknown')
        self.assertNotIn('SECRET',json.dumps(r)+ev.render_evidence_text(r))
    def test_reference_identity_changes_with_content(self):
        old=self.refs()[0]['evidenceId'];self.saved['result']['messages'][1]['content']+='!';self.save_result()
        self.assertNotEqual(old,self.refs()[0]['evidenceId'])
    def test_old_reference_cannot_read_modified_record(self):
        selection=self.select();self.saved['result']['messages'][1]['content']+='!';self.save_result()
        self.assertEqual(self.unavailable(selection=selection)['evidenceView']['reason'],'evidence_reference_unavailable')
    def test_full_local_view_is_not_original_or_wire_coverage(self):
        r=self.query(selection=self.select())['evidenceView']['localView']
        self.assertEqual(r['coverageOfStoredContent'],'complete');self.assertEqual(r['originalSourceCoverage'],'unknown')
        self.assertEqual(r['status'],'computed_locally_not_dispatched');self.assertEqual(r['modelVisibility'],'unknown')
    def test_partial_local_view(self):
        r=self.query(selection=self.select(0,1))['evidenceView']['localView']
        self.assertEqual(r['coverageOfStoredContent'],'partial');self.assertEqual(r['utf8Bytes'],1)
        self.assertEqual(r['contentSha256'],hashlib.sha256(b'A').hexdigest())
    def test_nonzero_start(self):
        end=len(self.text.encode());start=len('Aışık😀\r\n'.encode())
        v=self.query(selection=self.select(start,end))['evidenceView']['localView']
        self.assertEqual(v['contentSha256'],hashlib.sha256(b'second line\n').hexdigest())
    def test_split_unicode_boundary_rejected(self):
        self.assertEqual(self.unavailable(selection=self.select(0,2))['evidenceView']['reason'],'split_utf8_boundary')
    def test_out_of_bounds_rejected(self):
        self.assertEqual(self.unavailable(selection=self.select(0,1000))['evidenceView']['reason'],'invalid_evidence_range')
    def test_empty_slice_of_nonempty_text_rejected(self):self.unavailable(selection=self.select(0,0))
    def test_empty_retained_text_distinguished_from_missing(self):
        self.saved['result']['messages'][1]['content']='';self.save_result()
        ref=self.refs()[0];self.assertEqual(ref['content']['utf8Bytes'],0)
        self.assertEqual(self.query(selection=self.select())['evidenceView']['localView']['coverageOfStoredContent'],'complete')
    def test_no_messages_not_no_tools_executed(self):
        del self.saved['result']['messages'];self.save_result();r=self.query()['evidenceView']
        self.assertEqual(r['historyAvailability'],'not_recorded');self.assertEqual(r['historyCompleteness'],'not_proven')
        self.assertEqual(len(r['references']),1)
    def test_missing_tool_content_not_zero(self):
        self.saved['result']['messages'][1].pop('content');self.save_result()
        ref=self.refs()[0];self.assertIsNone(ref['content']['utf8Bytes']);self.assertIsNone(ref['content']['sha256'])
    def test_unsupported_rich_content_not_guessed(self):
        self.saved['result']['messages'][1]['content']=[{'type':'text','text':self.text}];self.save_result()
        self.assertEqual(self.refs()[0]['content']['availability'],'not_retained_as_text')
    def test_wrong_digest_selection_rejected(self):
        s=replace(self.select(),content_sha256='0'*64)
        self.assertEqual(self.unavailable(selection=s)['evidenceView']['reason'],'evidence_digest_mismatch')
    def test_wrong_reference_rejected(self):self.unavailable(selection=replace(self.select(),evidence_id='ev_'+'0'*64))
    def test_wrong_bearer_no_evidence(self):
        self.inspector=ev.EvidenceViewInspector(replace(self.context,api_token='other'),self.p,clock=lambda:self.now);self.unavailable()
    def test_wrong_generation_no_evidence(self):self.unavailable(observed=self.http|{'execution_generation':2})
    def test_wrong_run_no_evidence(self):self.unavailable(observed=self.http|{'run_id':'run_'+'c'*32})
    def test_live_observer_messages_not_promoted(self):
        self.sql("UPDATE session_admissions SET status='started',outcome=NULL");self.http['status']='running'
        self.http['messages']=self.saved['result']['messages'];self.unavailable()
    def test_unknown_task_messages_not_promoted(self):
        self.sql("UPDATE session_admissions SET status='unknown',outcome=NULL");self.http['status']='unknown';self.unavailable()
    def test_expired_retention_no_evidence(self):
        self.sql('UPDATE run_idempotency SET retention_until=?',(self.now-1,),replay=True);self.unavailable()
    def test_missing_db_not_created(self):
        p=self.home/'state.db';p.unlink();self.unavailable();self.assertFalse(p.exists())
    def test_scope_only_invents_no_task(self):
        r=self.inspector.inspect_scope();self.assertEqual(r['evidenceView']['reason'],'no_task_selected')
        self.assertEqual(r['task']['classification'],'not_selected')
    def test_no_source_files_opened(self):
        self.saved['result']['messages'][1]['content']='file:///secret-do-not-open.txt';self.save_result()
        with patch('pathlib.Path.open',side_effect=AssertionError('source opened')):self.refs()
    def test_no_database_bytes_or_budget_changed(self):
        fx.HostReportTests.claim(self,None,None);before=self.hashes();b=self.b.snapshot()
        r=self.query(selection=self.select());self.assertEqual(before,self.hashes());self.assertEqual(b,self.b.snapshot())
        self.assertFalse(r['writesPerformed']);self.assertFalse(r['executionAllowed']);self.assertFalse(r['evidenceView']['grantsExecutionPermission'])
    def test_returned_mutation_not_persisted(self):
        r=self.query();r['evidenceView']['references'][0]['modelView']['status']='seen'
        self.assertEqual(self.refs()[0]['modelView']['status'],'unknown')
    def test_secret_names_ids_and_content_not_echoed(self):
        messages=self.saved['result']['messages'];messages[0]['tool_calls'][0]['id']='SECRET-ID'
        messages[1].update(name='SECRET-NAME',tool_call_id='SECRET-ID',content='SECRET-CONTENT');self.save_result()
        r=self.query();s=json.dumps(r)+ev.render_evidence_text(r)
        for secret in ['SECRET-',self.context.api_token,str(self.home),self.body['input'],'native-output']:self.assertNotIn(secret,s)
    def test_malformed_messages_section_is_unavailable(self):
        self.saved['result']['messages']={};self.save_result();self.unavailable()
    def test_non_object_message_rejected(self):
        self.saved['result']['messages']=[None];self.save_result();self.unavailable()
    def test_malformed_calls_section_rejected(self):
        self.saved['result']['messages'][0]['tool_calls']={};self.save_result();self.unavailable()
    def test_too_many_references_rejected_no_partial_list(self):
        m=self.saved['result']['messages'][1];self.saved['result']['messages']=[dict(m) for _ in range(256)]
        self.save_result();self.unavailable()
    def test_unrelated_observer_metadata_ignored(self):
        r=self.query(observed=self.http|{'modelVisibility':'confirmed','evidenceView':{'available':True}})
        self.assertEqual(r['evidenceView']['modelVisibility'],'unknown')
    def test_primitive_selection_not_accepted(self):self.unavailable(selection={})
    def test_recheck_invalidates_entire_evidence_snapshot(self):
        original=sqlite3.connect;outer=self
        class Changing(sqlite3.Connection):
            def rollback(self):
                super().rollback()
                with closing(original(outer.home/'state.db')) as c:c.execute('UPDATE runtime_epoch SET epoch=3');c.commit()
        def connect(*a,**kw):return original(*a,**kw,factory=Changing)
        with patch('recovery_inspector.sqlite3.connect',connect):self.unavailable()
    def test_same_connection_and_no_dml(self):
        original=sqlite3.connect;opened=[];sql=[]
        def connect(*a,**kw):
            c=original(*a,**kw);c.set_trace_callback(sql.append);opened.append(c);return c
        with patch('recovery_inspector.sqlite3.connect',connect):self.query()
        self.assertEqual(len(opened),1)
        self.assertFalse(any(s.split()[0].upper() in {'INSERT','UPDATE','DELETE','REPLACE','CREATE','DROP'} for s in sql))
        with self.assertRaises(sqlite3.ProgrammingError):opened[0].execute('SELECT 1')
    def test_cli_include_and_selection(self):
        self.sql('UPDATE run_idempotency SET updated_at=?,created_at=?',(time.time(),time.time()),replay=True)
        context=asdict(self.context);context['profile_home']=str(context['profile_home']);context.pop('profile_name')
        data={'context.json':context,'policy.json':asdict(self.p),'request.json':{'body':self.body,'idempotency_key':self.key,'observed':self.http},
              'selection.json':asdict(self.select(0,1))}
        for name,obj in data.items():(self.home/name).write_text(json.dumps(obj),encoding='utf-8')
        cmd=[sys.executable,'-B',str(ROOT/'scripts/inspect_host_report.py'),'--context',str(self.home/'context.json'),
             '--policy',str(self.home/'policy.json'),'--request',str(self.home/'request.json'),'--include-evidence',
             '--evidence-selection',str(self.home/'selection.json')]
        p=subprocess.run(cmd,capture_output=True,text=True,encoding='utf-8',timeout=10)
        self.assertEqual(p.returncode,0,p.stderr);self.assertEqual(json.loads(p.stdout)['evidenceView']['localView']['utf8Bytes'],1)
        p=subprocess.run(cmd+['--format','text'],capture_output=True,text=True,encoding='utf-8',timeout=10)
        self.assertEqual(p.returncode,0,p.stderr);self.assertIn('NOT DISPATCHED',p.stdout)
        self.assertNotIn(self.context.api_token,p.stdout)
        (self.home/'selection.json').write_text('{}',encoding='utf-8')
        p=subprocess.run(cmd,capture_output=True,text=True,encoding='utf-8',timeout=10)
        self.assertEqual(p.returncode,2);self.assertFalse(json.loads(p.stdout)['executionAllowed'])


class EvidenceSelectionTests(unittest.TestCase):
    def valid(self,**kw):return ev.EvidenceSelection(**({'evidence_id':'ev_'+'a'*64,'content_sha256':'b'*64,'start_byte':0,'end_byte':1}|kw))
    def test_strict_range_types(self):
        for change in [{'start_byte':True},{'end_byte':False},{'end_byte':1.0},{'start_byte':-1},{'start_byte':2,'end_byte':1},{'end_byte':2097153}]:
            with self.subTest(change=change),self.assertRaises(ValueError):self.valid(**change)
    def test_strict_identity_types(self):
        for change in [{'evidence_id':'secret'},{'content_sha256':None},{'content_sha256':'x'*64},{'content_sha256':'B'*64}]:
            with self.subTest(change=change),self.assertRaises(ValueError):self.valid(**change)
    def test_selection_frozen(self):
        with self.assertRaises(FrozenInstanceError):self.valid().start_byte=3
    def test_unavailable_reason_redacted(self):
        self.assertEqual(ev.unavailable_evidence('SECRET https://private')['reason'],'evidence_unavailable')


if __name__=='__main__':unittest.main()
