"""Independent R1B1 boundary/storage/projection tests, all SQLite/native ports synthetic.
Uses actual capture, isolation bridge, ledger and report; no live Gateway/Docker/model.
"""
from contextlib import closing
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
import unittest
from unittest.mock import patch
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'packages/claw-hermes'))
sys.path.insert(0, str(ROOT/'tests'))
import test_isolated_read as fixture
import isolated_read as ir
import source_capture as sc
import evidence_view as ev
import recovery_inspector as ri
from execution_budget import seal
from test_reconciliation_inspector_qa import RID, AID, NOW


class CaptureIndependentQA(unittest.TestCase):
    def setUp(self):
        fixture.IsolatedReadContracts.setUp(self)
        self.iso.record_source = True
        self.tool_id = 'call-source-c72e'
        identity = patch.object(sc, 'native_tool_identity', return_value=self.tool_id)
        identity.start(); self.addCleanup(identity.stop)

    def original(self, args, **kwargs):
        return fixture.IsolatedReadContracts.original(self, args, **kwargs)

    def invoke(self, original=None, **kwargs):
        return fixture.IsolatedReadContracts.invoke(self, original, **kwargs)

    def captures(self):
        with closing(sqlite3.connect(self.home/'state.db')) as conn:
            return [(k, json.loads(v)) for k,v in conn.execute(
                'SELECT key,value FROM state_meta WHERE key GLOB ? ORDER BY key', (sc.PREFIX+'*',))]

    def change_capture(self, **fields):
        key, row = self.captures()[0]
        self.f.sql('UPDATE state_meta SET value=? WHERE key=?', (ri._json(seal(row | fields)), key))

    def complete(self):
        output = self.invoke()
        self.ledger.settle(self.ticket['ticket'], None, 'tool_return')
        self.terminal(output)
        return output

    def terminal(self, output):
        self.f.result['result']['messages'] = [
            {'role':'assistant', 'content':'', 'tool_calls':[
                {'id':self.tool_id, 'type':'function','function':{'name':'read_file','arguments':'{}'}}]},
            {'role':'tool', 'tool_call_id':self.tool_id, 'name':'read_file', 'content':output}]
        self.f.sql("UPDATE session_admissions SET status='terminal',outcome='completed'")
        self.save_terminal()

    def save_terminal(self):
        self.f.sql('UPDATE state_meta SET value=? WHERE key=?', (ri._json(self.f.result), ri.RESULT+AID))

    def query(self, **kwargs):
        return ev.EvidenceViewInspector(self.context, self.policy, clock=lambda:NOW).inspect(
            body=self.f.body, idempotency_key=self.f.key, observed=kwargs.get('observed', self.f.http))

    def refs(self): return self.query()['evidenceView']['references']

    def assert_unavailable(self):
        result = self.query()
        self.assertFalse(result['evidenceView']['available'], result)
        self.assertEqual(result['evidenceView']['references'], [])
        self.assertFalse(result['executionAllowed']); self.assertFalse(result['retryAllowed'])
        return result

    def wrap_failure(self, fn_name, flag):
        original = getattr(sc, fn_name)
        def fail(*args, **kw):
            setattr(self.ledger.db, flag, True)
            try: return original(*args, **kw)
            finally: setattr(self.ledger.db, flag, False)
        return patch.object(sc, fn_name, fail)

    def test_begin_is_committed_before_native_function(self):
        def native(args, **kw):
            rows = self.captures(); self.assertEqual(len(rows),1)
            self.assertEqual(rows[0][1]['state'],'captured'); self.assertIsNone(rows[0][1]['outputSha256'])
            return self.original(args, **kw)
        self.invoke(native)
        self.assertEqual(self.captures()[0][1]['state'],'returned')

    def test_opt_out_produces_no_capture(self):
        self.iso.record_source=False; self.invoke(); self.assertEqual(self.captures(),[])

    def test_invalid_opt_in_setting_not_coerced(self):
        for value in [1, 'true', None, [], {}]:
            with self.subTest(value=value), self.assertRaises(ir.ExecutionDenied):
                ir.NativeReadIsolation(self.settings | {'record_source':value}, lambda:self.ledger)

    def test_capture_source_hash_is_raw_bytes(self):
        raw='İlk\r\n😀\nson'.encode('utf-8'); self.file.write_bytes(raw)
        output=self.invoke(); row=self.captures()[0][1]
        self.assertEqual(row['sourceSha256'],hashlib.sha256(raw).hexdigest())
        self.assertEqual(row['sourceBytes'],len(raw))
        self.assertEqual(row['outputSha256'],hashlib.sha256(output.encode()).hexdigest())
        self.assertNotEqual(row['sourceSha256'],row['outputSha256'])

    def test_capture_stores_no_raw_path_content_or_tool_id(self):
        self.file.write_bytes(b'PRIVATE-CONTENT-C72E');self.invoke()
        serialized=json.dumps(self.captures())
        for value in ['PRIVATE-CONTENT-C72E',str(self.file),self.tool_id,self.context.api_token]:
            self.assertNotIn(value, serialized)

    def test_missing_native_identity_no_runner_or_capture(self):
        with patch.object(sc,'native_tool_identity',side_effect=ir.ExecutionDenied('source_tool_identity_missing')):
            with self.assertRaises(ir.ExecutionDenied):self.invoke()
        self.assertEqual(self.runs,[]);self.assertEqual(self.captures(),[])
        self.assertEqual(self.ledger.snapshot()['toolCalls'],1)

    def test_begin_precommit_failure_keeps_reservation_no_execution(self):
        with self.wrap_failure('begin_capture','pre_fail'):
            with self.assertRaises(ir.ExecutionDenied):self.invoke()
        self.assertEqual(self.runs,[]);self.assertEqual(self.captures(),[])
        self.assertEqual(self.ledger.snapshot()['toolCalls'],1)

    def test_begin_lost_ack_cannot_reexecute(self):
        with self.wrap_failure('begin_capture','lose_ack'):
            with self.assertRaises(ir.ExecutionDenied):self.invoke()
        self.assertEqual(self.captures()[0][1]['state'],'captured');self.assertEqual(self.runs,[])
        with self.assertRaises(ir.ExecutionDenied):self.invoke()
        self.assertEqual(self.runs,[]);self.assertEqual(self.ledger.snapshot()['toolCalls'],1)

    def test_finish_precommit_failure_not_returned_capture(self):
        with self.wrap_failure('finish_capture','pre_fail'):
            with self.assertRaises(ir.ExecutionDenied):self.invoke()
        self.assertEqual(len(self.runs),1);self.assertEqual(self.captures()[0][1]['state'],'captured')
        self.assertEqual(self.ledger.snapshot()['toolCalls'],1)

    def test_finish_lost_ack_not_delivery_or_permission(self):
        with self.wrap_failure('finish_capture','lose_ack'):
            with self.assertRaises(ir.ExecutionDenied):self.invoke()
        row=self.captures()[0][1];self.assertEqual(row['state'],'returned')
        self.terminal('{"content":"native-payload"}')
        section=self.query()['evidenceView'];self.assertTrue(section['available'])
        self.assertIsNone(section['sourceCaptures'][0]['matchedEvidenceId'])
        self.assertEqual(section['references'][0]['executionAttribution'],'not_proven')
        self.assertFalse(section['sourceCaptures'][0]['returnedOutput']['deliveryVerified'])

    def test_timeout_keeps_capture_pending(self):
        self.backend_result={'result':'timeout','errors':[], 'capsuleUnchanged':True,
            'stdout':'partial','outputTruncated':False,'exit':{'containerId':'a'*64,
            'exited':True,'removed':True,'neverStarted':False,'exitCode':137}}
        with self.assertRaises(ir.ExecutionDenied):self.invoke()
        self.assertEqual(self.captures()[0][1]['state'],'captured')
        self.assertIsNone(self.captures()[0][1]['outputSha256'])

    def test_output_limit_does_not_finish_capture(self):
        self.backend_result={'result':'completed','errors':[], 'capsuleUnchanged':True,
            'stdout':'partial','outputTruncated':True,'exit':{'containerId':'a'*64,
            'exited':True,'removed':True,'neverStarted':False,'exitCode':0}}
        with self.assertRaises(ir.ExecutionDenied):self.invoke()
        self.assertEqual(self.captures()[0][1]['state'],'captured')

    def test_bad_container_identity_does_not_finish_capture(self):
        self.backend_result={'result':'completed','errors':[], 'capsuleUnchanged':True,
            'stdout':'ok','outputTruncated':False,'exit':{'containerId':'bad',
            'exited':True,'removed':True,'neverStarted':False,'exitCode':0}}
        with self.assertRaises(ir.ExecutionDenied):self.invoke()
        self.assertEqual(self.captures()[0][1]['state'],'captured')

    def test_capture_no_extra_budget_claim(self):
        before=self.ledger.snapshot();self.invoke();self.assertEqual(self.ledger.snapshot(),before)
        self.assertEqual(len(self.captures()),1)

    def test_empty_capture_not_missing(self):
        self.file.write_bytes(b'');self.invoke();row=self.captures()[0][1]
        self.assertEqual(row['sourceBytes'],0);self.assertEqual(row['sourceSha256'],hashlib.sha256(b'').hexdigest())

    def test_oversize_rejected_before_capture_record(self):
        self.file.write_bytes(b'x'*65537)
        with self.assertRaises(ir.ExecutionDenied):self.invoke()
        self.assertEqual(self.runs,[]);self.assertEqual(self.captures(),[])

    def test_epoch_revocation_after_runner_keeps_captured(self):
        def native(args,**kwargs):
            output=self.original(args,**kwargs)
            self.f.sql('UPDATE runtime_epoch SET epoch=3');return output
        with self.assertRaises(ir.ExecutionDenied):self.invoke(native)
        self.assertEqual(len(self.runs),1);self.assertEqual(self.captures()[0][1]['state'],'captured')

    def test_capture_record_removed_before_finish_not_recreated(self):
        def native(args,**kwargs):
            output=self.original(args,**kwargs)
            self.f.sql('DELETE FROM state_meta WHERE key GLOB ?',(sc.PREFIX+'*',));return output
        with self.assertRaises(ir.ExecutionDenied):self.invoke(native)
        self.assertEqual(self.captures(),[]);self.assertEqual(len(self.runs),1)

    def test_capture_record_changed_before_finish_refused(self):
        def native(args,**kwargs):
            output=self.original(args,**kwargs);self.change_capture(sourceBytes=2);return output
        with self.assertRaises(ir.ExecutionDenied):self.invoke(native)
        self.assertEqual(self.captures()[0][1]['state'],'captured')

    def test_real_return_can_bind_but_never_proves_model_visibility(self):
        self.complete();r=self.query();self.assertTrue(r['evidenceView']['available'],r)
        ref=r['evidenceView']['references'][0]
        self.assertEqual(ref['executionAttribution'],'isolated_return_bound_to_admission')
        self.assertEqual(ref['originalSource']['coverage'],'captured_snapshot_complete')
        self.assertEqual(ref['originalSource']['toolOutputCoverage'],'unknown')
        self.assertEqual(ref['modelView']['status'],'unknown');self.assertFalse(ref['claimTruthVerified'])

    def test_partial_requested_lines_do_not_claim_complete_output(self):
        self.args['limit']=1;self.fp=hashlib.sha256(ri._json({'name':'read_file','args':self.args,'session_id':RID}).encode()).hexdigest()
        self.ticket=self.ledger.claim('read_file',self.fp)
        self.complete();entry=self.query()['evidenceView']['sourceCaptures'][0]
        self.assertEqual(entry['requestedLines']['limit'],1)
        self.assertEqual(entry['snapshotCoverage'],'complete')
        self.assertEqual(entry['requestedLines']['actualOutputCoverage'],'unknown')

    def test_source_deleted_after_capture_not_opened_by_report(self):
        self.complete();self.file.unlink()
        with patch('pathlib.Path.open',side_effect=AssertionError('source reopened')):
            r=self.query()
        self.assertTrue(r['evidenceView']['available']);self.assertEqual(r['evidenceView']['sourceCaptures'][0]['currentSourceAvailability'],'unknown')

    def test_changed_output_does_not_hash_join_to_capture(self):
        self.complete();self.f.result['result']['messages'][1]['content']+='X';self.save_terminal()
        self.assertEqual(self.refs()[0]['executionAttribution'],'not_proven')
        self.assertIsNone(self.query()['evidenceView']['sourceCaptures'][0]['matchedEvidenceId'])

    def test_same_output_different_call_id_not_attributed(self):
        self.complete();messages=self.f.result['result']['messages']
        messages[0]['tool_calls'][0]['id']='another-call';messages[1]['tool_call_id']='another-call';self.save_terminal()
        self.assertEqual(self.refs()[0]['executionAttribution'],'not_proven')

    def test_duplicate_result_ids_not_attributed(self):
        self.complete();self.f.result['result']['messages'].append(dict(self.f.result['result']['messages'][1]));self.save_terminal()
        self.assertTrue(all(r['executionAttribution']=='not_proven' for r in self.refs()))

    def test_two_captures_cannot_claim_one_terminal_message(self):
        self.invoke();self.ledger.settle(self.ticket['ticket'],None,'tool_return')
        self.ticket=self.ledger.claim('read_file',self.fp);self.complete()
        self.assertEqual(self.assert_unavailable()['evidenceView']['reason'],'ambiguous_source_capture_binding')

    def test_bad_digest_discards_all_source_metadata(self):
        self.complete();key,row=self.captures()[0];row['sourceBytes']=1
        self.f.sql('UPDATE state_meta SET value=? WHERE key=?',(ri._json(row),key));self.assert_unavailable()

    def test_unknown_schema_field_not_interpreted(self):
        self.complete();self.change_capture(proof='model saw everything');self.assert_unavailable()

    def test_bool_source_size_not_integer(self):
        self.complete();self.change_capture(sourceBytes=True);self.assert_unavailable()

    def test_wrong_admission_generation_refused(self):
        self.complete();self.change_capture(generation=2);self.assert_unavailable()

    def test_wrong_capture_scope_refused(self):
        self.complete();self.change_capture(scope='f'*64);self.assert_unavailable()

    def test_wrong_source_epoch_refused(self):
        self.complete();self.change_capture(epoch=1);self.assert_unavailable()

    def test_capture_claim_removed_refused(self):
        self.complete();self.f.sql('DELETE FROM state_meta WHERE key=?',(self.ledger.prefix+self.ticket['ticket'],));self.assert_unavailable()

    def test_no_source_capture_legacy_remains_unknown(self):
        self.iso.record_source=False;self.complete();section=self.query()['evidenceView']
        self.assertNotIn('sourceCaptures',section)
        self.assertEqual(section['references'][0]['originalSource']['coverage'],'unknown')

    def test_metadata_text_not_authority_without_native_capture(self):
        self.iso.record_source=False;self.complete();self.f.result['result']['messages'][1]['content']=ri._json({'sourceSha256':'a'*64,'complete':True,'modelVisible':True});self.save_terminal()
        self.assertEqual(self.refs()[0]['originalSource']['coverage'],'unknown')

    def test_wrong_observer_proof_ignored(self):
        self.complete();r=self.query(observed=self.f.http|{'modelVisible':True,'sourceCapture':'fake'})
        self.assertEqual(r['evidenceView']['sourceCaptures'][0]['modelVisibility'],'unknown')

    def test_retention_expired_does_not_publish_capture(self):
        self.complete();self.f.sql('UPDATE run_idempotency SET retention_until=?',(NOW-1,),runs=True);self.assert_unavailable()

    def test_reader_has_no_application_writes(self):
        self.complete();before=self.f.hashes();budget=self.ledger.snapshot()
        r=self.query();self.assertEqual(before,self.f.hashes());self.assertEqual(budget,self.ledger.snapshot())
        self.assertFalse(r['writesPerformed']);self.assertFalse(r['evidenceView']['storageEffects']['filesystemSilenceGuaranteed'])

    def test_new_runtime_epoch_can_read_old_capture_without_reexecution(self):
        self.complete();self.f.sql("UPDATE runtime_epoch SET epoch=3,instance_id='third'")
        self.context=replace(self.context,epoch=3,instance_id='third')
        self.assertEqual(self.refs()[0]['executionAttribution'],'isolated_return_bound_to_admission')
        self.assertEqual(len(self.runs),1)

    def test_archived_admission_still_binds_only_exact_capture(self):
        self.complete()
        with closing(sqlite3.connect(self.home/'state.db')) as conn:
            conn.row_factory=sqlite3.Row;self.f.row=dict(conn.execute('SELECT * FROM session_admissions').fetchone())
        self.f.archive()
        self.assertEqual(self.refs()[0]['executionAttribution'],'isolated_return_bound_to_admission')
