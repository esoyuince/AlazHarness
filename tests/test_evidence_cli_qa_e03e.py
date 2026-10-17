"""Independent real CLI process tests with private synthetic SQLite inputs."""
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'packages/claw-hermes'),str(ROOT/'tests')]
import recovery_inspector as ri
import evidence_view as ev
import test_report_evidence_invariants_qa_e03e as base

class EvidenceCliIndependentTests(unittest.TestCase):
    save=base.EvidenceReportAuthorityInvariants.save
    def setUp(self):
        base.EvidenceReportAuthorityInvariants.setUp(self)
        self.f.sql('UPDATE run_idempotency SET retention_until=?,created_at=?,updated_at=?',
            (time.time()+3600,time.time(),time.time()),runs=True)
        self.f.result['result']['messages']=[{'role':'tool','tool_call_id':'call-private',
            'content':'line one\nışık second\n'}];self.save()
        ctx=asdict(self.ctx);ctx['profile_home']=str(ctx['profile_home']);ctx.pop('profile_name')
        for name,value in [('context.json',ctx),('policy.json',asdict(self.policy)),('request.json',{
            'body':self.f.body,'idempotency_key':self.f.key,'observed':self.f.http})]:
            (self.f.home/name).write_text(json.dumps(value),encoding='utf-8')
        self.cmd=[sys.executable,'-B',str(ROOT/'scripts/inspect_host_report.py'),
            '--context',str(self.f.home/'context.json'),'--policy',str(self.f.home/'policy.json')]
    def cli(self,*args,scope=False):
        before=self.f.hashes()
        choice=['--scope-only'] if scope else ['--request',str(self.f.home/'request.json')]
        result=subprocess.run(self.cmd+choice+list(args),capture_output=True,text=True,
            encoding='utf-8',timeout=10)
        self.assertEqual(before,self.f.hashes())
        self.assertNotIn('Traceback',result.stderr)
        for secret in (self.ctx.api_token,self.f.body['input'],'line one',str(self.f.home)):
            self.assertNotIn(secret,result.stdout)
        return result
    def selection(self):
        r=ev.EvidenceViewInspector(self.ctx,self.policy).inspect(body=self.f.body,
            idempotency_key=self.f.key,observed=self.f.http)
        ref=next(x for x in r['evidenceView']['references'] if x['kind']=='retained_tool_result')
        path=self.f.home/'selection.json'
        path.write_text(json.dumps({'evidence_id':ref['evidenceId'],'content_sha256':ref['content']['sha256'],
            'start_byte':0,'end_byte':4}),encoding='utf-8')
        return path
    def test_opt_in_json_has_unknown_wire_and_no_content(self):
        result=self.cli('--include-evidence');self.assertEqual(result.returncode,0,result.stderr)
        report=json.loads(result.stdout);self.assertEqual(report['evidenceView']['modelVisibility'],'unknown')
        self.assertFalse(report['evidenceView']['goalAchievementVerified'])
    def test_legacy_default_remains_without_extra_section(self):
        result=self.cli();self.assertEqual(result.returncode,0,result.stderr)
        self.assertNotIn('evidenceView',json.loads(result.stdout))
    def test_selected_view_text_says_not_dispatched(self):
        path=self.selection()
        result=self.cli('--include-evidence','--evidence-selection',str(path),'--format','text')
        self.assertEqual(result.returncode,0,result.stderr);self.assertIn('NOT DISPATCHED',result.stdout)
        self.assertIn('UNKNOWN',result.stdout)
    def test_selection_without_opt_in_rejected(self):
        result=self.cli('--evidence-selection',str(self.selection()))
        self.assertEqual(result.returncode,2);self.assertEqual(json.loads(result.stdout)['reportStatus'],'unverified')
    def test_selection_and_scope_only_refused(self):
        result=self.cli('--include-evidence','--evidence-selection',str(self.selection()),scope=True)
        self.assertEqual(result.returncode,2);self.assertFalse(json.loads(result.stdout)['executionAllowed'])
    def test_duplicate_json_key_selection_refused(self):
        path=self.f.home/'bad.json';path.write_text('{"start_byte":0,"start_byte":1}',encoding='utf-8')
        result=self.cli('--include-evidence','--evidence-selection',str(path),'--format','text')
        self.assertEqual(result.returncode,2)
    def test_invalid_source_record_never_cli_success(self):
        self.f.sql('DELETE FROM state_meta WHERE key=?',(ri.RESULT+self.f.row['admission_id'],))
        result=self.cli('--include-evidence');self.assertEqual(result.returncode,2)
        self.assertFalse(json.loads(result.stdout)['evidenceView']['available'])
    def test_scope_only_explains_missing_task_not_empty_proof(self):
        result=self.cli('--include-evidence',scope=True);self.assertEqual(result.returncode,0)
        report=json.loads(result.stdout);self.assertEqual(report['evidenceView']['reason'],'no_task_selected')
        self.assertEqual(report['evidenceView']['references'],[])

if __name__=='__main__':unittest.main()
