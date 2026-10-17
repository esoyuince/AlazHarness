"""Actual capture/report code, synthetic native owner/registry/container ports.

No native Hermes/Docker/provider acceptance. Captured source is a real temporary
file. Every pretend execution/identity/redaction boundary is explicitly patched.
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
import test_isolated_read as fx
import isolated_read as ir
import source_capture as sc
import evidence_view as ev
from recovery_inspector import _json, _load, RESULT
from execution_budget import seal, ExecutionDenied, ExecutionLedger
from test_reconciliation_inspector_qa import RID, AID, NOW


class CaptureContracts(unittest.TestCase):
    original = fx.IsolatedReadContracts.original
    invoke = fx.IsolatedReadContracts.invoke

    def setUp(self):
        fx.IsolatedReadContracts.setUp(self)
        self.iso.record_source = True
        self.cid = 'native-tool-one'
        m = patch.object(sc, 'native_tool_identity', return_value=self.cid)
        m.start(); self.addCleanup(m.stop)

    def rows(self):
        with closing(sqlite3.connect(self.home/'state.db')) as c:
            return [(k, _load(v)) for k,v in c.execute(
                'SELECT key,value FROM state_meta WHERE key GLOB ? ORDER BY key', (sc.PREFIX+'*',))]

    def update(self, changes, *, reseal=True):
        key, value = self.rows()[0]
        value.update(changes)
        self.f.sql('UPDATE state_meta SET value=? WHERE key=?', (_json(seal(value) if reseal else value),key))

    def completed(self):
        output = self.invoke()
        self.ledger.settle(self.ticket['ticket'], None, 'tool_return')
        self.f.sql("UPDATE session_admissions SET status='terminal',outcome='completed'")
        self.f.result['result']['messages'] = [
            {'role':'assistant','content':'','tool_calls':[{'id':self.cid,'type':'function',
               'function':{'name':'read_file','arguments':_json(self.args)}}]},
            {'role':'tool','tool_call_id':self.cid,'content':output}]
        self.save_result()
        return output

    def save_result(self):
        self.f.sql('UPDATE state_meta SET value=? WHERE key=?', (_json(self.f.result), RESULT+AID))

    def query(self):
        return ev.EvidenceViewInspector(self.context, self.policy, clock=lambda:NOW).inspect(
            body=self.f.body,idempotency_key=self.f.key,observed=self.f.http)

    def unavailable(self):
        report = self.query()
        self.assertFalse(report['evidenceView']['available'], report)
        self.assertEqual(report['evidenceView']['references'], [])
        self.assertFalse(report['executionAllowed'])

    def test_disabled_retains_exact_legacy_behavior(self):
        self.iso.record_source=False; self.invoke(); self.assertEqual(self.rows(),[])

    def test_opt_in_setting_and_default(self):
        self.assertFalse(ir.NativeReadIsolation(self.settings,lambda:self.ledger).record_source)
        self.assertTrue(ir.NativeReadIsolation(self.settings|{'record_source':True},lambda:self.ledger).record_source)

    def test_flag_exact_boolean(self):
        for flag in [1,0,None,'true',{},[]]:
            with self.subTest(flag=flag),self.assertRaises(ExecutionDenied):
                ir.NativeReadIsolation(self.settings|{'record_source':flag},lambda:self.ledger)

    def test_snapshot_hash_and_count_exact(self):
        raw=b'\xef\xbb\xbfA\r\n'+ 'ışık😀'.encode();self.file.write_bytes(raw)
        self.invoke();row=self.rows()[0][1]
        self.assertEqual(row['sourceSha256'],hashlib.sha256(raw).hexdigest())
        self.assertEqual(row['sourceBytes'],len(raw))

    def test_capture_is_committed_before_original(self):
        def original(args,**kw):
            self.assertEqual(self.rows()[0][1]['state'],'captured')
            self.assertIsNone(self.rows()[0][1]['outputSha256'])
            return self.original(args,**kw)
        self.invoke(original)

    def test_output_hash_is_after_redaction(self):
        output='{"content":"redacted"}'
        with patch.object(ir,'native_redact_result',return_value=output):self.invoke()
        row=self.rows()[0][1]
        self.assertEqual(row['outputSha256'],hashlib.sha256(output.encode()).hexdigest())
        self.assertEqual(row['outputBytes'],len(output.encode()))

    def test_snapshot_and_output_digests_not_conflated(self):
        self.invoke();row=self.rows()[0][1]
        self.assertNotEqual(row['sourceSha256'],row['outputSha256'])
        self.assertEqual(row['state'],'returned')

    def test_empty_snapshot_is_not_missing(self):
        self.file.write_bytes(b'');self.invoke();row=self.rows()[0][1]
        self.assertEqual(row['sourceBytes'],0)
        self.assertEqual(row['sourceSha256'],hashlib.sha256(b'').hexdigest())

    def test_failed_begin_commit_never_executes(self):
        self.ledger.db.pre_fail=True
        with self.assertRaises(ExecutionDenied):self.invoke()
        self.assertEqual(self.runs,[]);self.assertEqual(self.rows(),[])

    def test_lost_begin_ack_never_executes_or_reuses(self):
        original=sc.begin_capture
        def lose(*a,**kw):
            self.ledger.db.lose_ack=True
            try:return original(*a,**kw)
            finally:self.ledger.db.lose_ack=False
        with patch.object(sc,'begin_capture',lose),self.assertRaises(ExecutionDenied):self.invoke()
        self.assertEqual(self.runs,[]);self.assertEqual(self.rows()[0][1]['state'],'captured')
        with self.assertRaises(ExecutionDenied):self.invoke()
        self.assertEqual(self.runs,[]);self.assertEqual(self.ledger.snapshot()['toolCalls'],1)

    def test_failure_after_begin_keeps_capture_no_output(self):
        with self.assertRaises(RuntimeError):self.invoke(lambda a,**k:(_ for _ in ()).throw(RuntimeError('fixture failure')))
        row=self.rows()[0][1];self.assertEqual(row['state'],'captured');self.assertIsNone(row['outputSha256'])
        self.assertEqual(self.ledger.snapshot()['toolCalls'],1)

    def test_failed_finish_retains_charge_and_no_return_claim(self):
        def original(args,**kw):
            result=self.original(args,**kw);self.ledger.db.pre_fail=True;return result
        with self.assertRaises(ExecutionDenied):self.invoke(original)
        self.ledger.db.pre_fail=False
        self.assertEqual(len(self.runs),1);self.assertEqual(self.rows()[0][1]['state'],'captured')
        self.assertEqual(self.ledger.snapshot()['toolCalls'],1)

    def test_lost_finish_ack_not_delivery(self):
        original=sc.finish_capture
        def lose(*a,**kw):
            self.ledger.db.lose_ack=True
            try:return original(*a,**kw)
            finally:self.ledger.db.lose_ack=False
        with patch.object(sc,'finish_capture',lose),self.assertRaises(ExecutionDenied):self.invoke()
        self.assertEqual(len(self.runs),1);self.assertEqual(self.rows()[0][1]['state'],'returned')
        with self.assertRaises(ExecutionDenied):self.invoke()
        self.assertEqual(self.ledger.snapshot()['toolCalls'],1)

    def test_missing_native_identity_blocks_before_container(self):
        with patch.object(sc,'native_tool_identity',side_effect=ExecutionDenied('source_tool_identity_missing')):
            with self.assertRaises(ExecutionDenied):self.invoke()
        self.assertEqual(self.runs,[]);self.assertEqual(self.rows(),[])

    def test_duplicate_ticket_persistent_begin_refused(self):
        self.invoke();self.iso._tickets.clear()
        with self.assertRaisesRegex(ExecutionDenied,'source_capture_already_recorded'):self.invoke()
        self.assertEqual(len(self.runs),1)

    def test_cancelled_before_execution_creates_no_return(self):
        self.parent.is_interrupted=True
        with self.assertRaises(ExecutionDenied):self.invoke()
        self.assertEqual(self.runs,[])
        self.assertTrue(all(r['state']=='captured' for _,r in self.rows()))

    def test_authority_changed_after_return_does_not_finish(self):
        def original(args,**kw):
            result=self.original(args,**kw);self.f.sql('UPDATE runtime_epoch SET epoch=3');return result
        with self.assertRaises(ExecutionDenied):self.invoke(original)
        self.assertEqual(self.rows()[0][1]['state'],'captured')

    def test_corrupt_capture_does_not_get_overwritten(self):
        def original(args,**kw):
            result=self.original(args,**kw);self.update({'sourceBytes':9});return result
        with self.assertRaisesRegex(ExecutionDenied,'source_capture_changed'):self.invoke(original)
        self.assertEqual(self.rows()[0][1]['sourceBytes'],9)

    def test_report_binds_exact_return_to_source(self):
        self.completed();r=self.query()['evidenceView'];ref=r['references'][0]
        self.assertEqual(ref['executionAttribution'],'isolated_return_bound_to_admission')
        self.assertEqual(ref['originalSource']['sha256'],hashlib.sha256(self.file.read_bytes()).hexdigest())
        self.assertEqual(ref['originalSource']['coverage'],'captured_snapshot_complete')
        self.assertEqual(r['sourceCaptures'][0]['matchedEvidenceId'],ref['evidenceId'])

    def test_report_does_not_claim_model_visibility_or_truth(self):
        self.completed();r=self.query()['evidenceView'];ref=r['references'][0]
        self.assertEqual(r['modelVisibility'],'unknown');self.assertFalse(r['goalAchievementVerified'])
        self.assertEqual(ref['modelView']['status'],'unknown');self.assertFalse(ref['claimTruthVerified'])
        self.assertFalse(r['sourceCaptures'][0]['returnedOutput']['deliveryVerified'])

    def test_full_capture_not_full_requested_read(self):
        self.file.write_bytes(b'a\n'*250);self.completed()
        c=self.query()['evidenceView']['sourceCaptures'][0]
        self.assertEqual(c['sourceBytes'],500);self.assertEqual(c['requestedLines']['limit'],20)
        self.assertEqual(c['requestedLines']['actualOutputCoverage'],'unknown')

    def test_does_not_reopen_original_source(self):
        self.completed();self.file.unlink()
        with patch.object(Path,'open',side_effect=AssertionError('file reopened')):r=self.query()
        self.assertEqual(r['evidenceView']['sourceCaptures'][0]['currentSourceAvailability'],'unknown')

    def test_unknown_source_when_no_capture_record(self):
        self.completed();self.f.sql('DELETE FROM state_meta WHERE key GLOB ?', (sc.PREFIX+'*',))
        r=self.query()['evidenceView'];self.assertNotIn('sourceCaptures',r)
        self.assertEqual(r['references'][0]['originalSource']['coverage'],'unknown')

    def test_changed_output_not_fuzzy_matched(self):
        self.completed();self.f.result['result']['messages'][1]['content']+=' ';self.save_result()
        r=self.query()['evidenceView'];self.assertEqual(r['references'][0]['executionAttribution'],'not_proven')
        self.assertIsNone(r['sourceCaptures'][0]['matchedEvidenceId'])

    def test_different_tool_id_not_matched(self):
        self.completed();m=self.f.result['result']['messages'];m[0]['tool_calls'][0]['id']='different';m[1]['tool_call_id']='different';self.save_result()
        self.assertIsNone(self.query()['evidenceView']['sourceCaptures'][0]['matchedEvidenceId'])

    def test_ambiguous_tool_history_not_matched(self):
        self.completed();self.f.result['result']['messages'].append(self.f.result['result']['messages'][1].copy());self.save_result()
        self.assertIsNone(self.query()['evidenceView']['sourceCaptures'][0]['matchedEvidenceId'])

    def test_unsettled_ticket_not_bound(self):
        self.completed()
        with closing(sqlite3.connect(self.home/'state.db')) as c:
            key=self.ledger.prefix+self.ticket['ticket'];row=_load(c.execute('SELECT value FROM state_meta WHERE key=?',(key,)).fetchone()[0])
        row.update(state='reserved',outcome=None,usage=None)
        self.f.sql('UPDATE state_meta SET value=? WHERE key=?',(_json(seal(row)),key))
        self.assertIsNone(self.query()['evidenceView']['sourceCaptures'][0]['matchedEvidenceId'])

    def test_tampered_source_digest_refused(self):
        self.completed();self.update({'sourceSha256':'f'*64},reseal=False);self.unavailable()

    def test_wrong_run_capture_refused(self):
        self.completed();self.update({'runId':'run_'+'c'*32});self.unavailable()

    def test_wrong_generation_capture_refused(self):
        self.completed();self.update({'generation':2});self.unavailable()

    def test_wrong_payload_capture_refused(self):
        self.completed();self.update({'payloadDigest':'f'*64});self.unavailable()

    def test_wrong_ticket_capture_refused(self):
        self.completed();self.update({'ticket':'f'*32});self.unavailable()

    def test_wrong_policy_capture_refused(self):
        self.completed();self.update({'policy':'f'*64});self.unavailable()

    def test_wrong_instance_capture_refused(self):
        self.completed();self.update({'instance':'other'});self.unavailable()

    def test_invalid_capture_integer_refused(self):
        self.completed();self.update({'sourceBytes':True});self.unavailable()

    def test_foreign_extra_field_refused(self):
        self.completed();self.update({'modelSeen':True});self.unavailable()

    def test_old_capture_survives_runtime_reopen(self):
        self.completed();self.f.sql("UPDATE runtime_epoch SET epoch=3,instance_id='owner-three'")
        self.context=replace(self.context,epoch=3,instance_id='owner-three')
        ref=self.query()['evidenceView']['references'][0]
        self.assertEqual(ref['executionAttribution'],'isolated_return_bound_to_admission')

    def test_raw_content_path_and_identity_not_reflected(self):
        self.completed();r=self.query();serialized=_json(r)+ev.render_evidence_text(r)
        for value in [str(self.file),self.file.read_text(),self.cid,self.context.api_token,'native-payload']:
            self.assertNotIn(value,serialized)
        self.assertNotIn(str(self.file),_json(self.rows()))

    def test_reader_does_not_write_sql_or_budget(self):
        self.completed();before=self.f.hashes();budget=self.ledger.snapshot();traces=[];original=sqlite3.connect
        def connect(*a,**k):
            c=original(*a,**k);c.set_trace_callback(traces.append);return c
        with patch('recovery_inspector.sqlite3.connect',connect):self.query()
        self.assertFalse(any(s.split()[0].upper() in {'INSERT','UPDATE','DELETE','CREATE','REPLACE','DROP'} for s in traces))
        self.assertEqual(before,self.f.hashes());self.assertEqual(budget,self.ledger.snapshot())

    def test_filesystem_silence_not_claimed(self):
        self.completed();e=self.query()['evidenceView']['storageEffects']
        self.assertIs(e['applicationStateWrites'],False);self.assertIs(e['filesystemSilenceGuaranteed'],False)
        self.assertIs(e['sqliteAuxiliaryFilesMayBeCreated'],True)


if __name__=='__main__':unittest.main()
