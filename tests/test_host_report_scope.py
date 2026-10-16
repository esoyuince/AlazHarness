"""Scope-only reports use existing synthetic ledger fixtures, not native runs."""
from contextlib import closing
from dataclasses import asdict,replace
import hashlib
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'packages/claw-hermes'))
import host_report as hr
import test_execution_gate_qa as fx


class ScopeReportTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.home=Path(self.tmp.name);self.f=fx.GateFixture(self.home);self.p=fx.policy()
        self.b=fx.ExecutionLedger(self.f.db,self.f.context,self.p);self.b.initialize()
    def reporter(self,**kwargs):return hr.HostReportInspector(kwargs.get('context',self.f.context),kwargs.get('policy',self.p))
    def read(self):return self.reporter().inspect_scope()
    def test_no_fake_task_needed(self):
        r=self.read();self.assertEqual(r['reportStatus'],'verified_scope_snapshot');self.assertEqual(r['task']['classification'],'not_selected');self.assertFalse(r['task']['taskSucceeded'])
    def test_does_not_require_or_create_replay_store(self):
        (self.home/'runs_idempotency.db').unlink();self.assertEqual(self.read()['reportStatus'],'verified_scope_snapshot');self.assertFalse((self.home/'runs_idempotency.db').exists())
    def test_sdk_error_usage_is_unknown(self):
        row=self.b.claim('provider','a'*64);self.b.settle(row['ticket'],None,'transport_error')
        r=self.read();self.assertEqual(r['execution']['providerAttempts']['reserved'],1)
        self.assertIsNone(r['execution']['observedUsage']['totalTokens']);self.assertEqual(r['execution']['reservedExposure']['costMicrousd'],300)
    def test_scope_credential_not_crossed(self):
        r=self.reporter(context=replace(self.f.context,api_token='other')).inspect_scope()
        self.assertEqual(r['reportStatus'],'unverified');self.assertFalse(r['execution']['available'])
    def test_stale_context_refused(self):
        self.f.sql('UPDATE runtime_epoch SET epoch=2');self.assertEqual(self.read()['reportStatus'],'unverified')
    def test_missing_budget_remains_missing(self):
        self.f.sql('DELETE FROM state_meta');before=self.f.rows();self.assertEqual(self.read()['reportStatus'],'unverified');self.assertEqual(self.f.rows(),before)
    def test_missing_database_remains_missing(self):
        (self.home/'state.db').unlink();self.assertEqual(self.read()['reportStatus'],'unverified');self.assertFalse((self.home/'state.db').exists())
    def test_view_is_not_trusted_schema(self):
        self.f.sql('ALTER TABLE state_meta RENAME TO hidden');self.f.sql('CREATE VIEW state_meta AS SELECT * FROM hidden')
        self.assertEqual(self.read()['reason'],'unsupported_schema')
    def test_same_snapshot_unmodified(self):
        before=(self.home/'state.db').read_bytes();self.read();self.read();self.assertEqual((self.home/'state.db').read_bytes(),before)
    def test_query_only_connection_closed(self):
        original=sqlite3.connect;opened=[];statements=[]
        def connect(*a,**kw):
            self.assertIn('?mode=ro',a[0]);c=original(*a,**kw);c.set_trace_callback(statements.append);opened.append(c);return c
        with patch('host_report.sqlite3.connect',connect):self.read()
        self.assertEqual(len(opened),1)
        with self.assertRaises(sqlite3.ProgrammingError):opened[0].execute('SELECT 1')
        self.assertFalse(any(s.split()[0].upper() in {'INSERT','UPDATE','DELETE','CREATE','DROP','REPLACE'} for s in statements))
    def test_wal_race_discards_all_numbers(self):
        with closing(sqlite3.connect(self.home/'state.db')) as c:c.execute('PRAGMA journal_mode=WAL')
        orig=hr._execution_snapshot
        def change(*a):
            value=orig(*a);self.b.quarantine();return value
        with patch.object(hr,'_execution_snapshot',change):r=self.read()
        self.assertEqual(r['reportStatus'],'unverified');self.assertEqual(r['reason'],'concurrent_state_change');self.assertFalse(r['execution']['available'])
    def test_policy_mismatch_does_not_reprice(self):
        r=self.reporter(policy=replace(self.p,total_token_limit=100)).inspect_scope();self.assertEqual(r['reportStatus'],'unverified')
    def test_quarantine_visible_no_permission(self):
        self.b.quarantine();r=self.read();self.assertTrue(r['execution']['quarantined']);self.assertFalse(r['executionAllowed'])
    def test_scope_cli_no_task_inputs(self):
        context=asdict(self.f.context);context.pop('profile_name');context['profile_home']=str(context['profile_home'])
        for name,value in [('context.json',context),('policy.json',asdict(self.p))]:(self.home/name).write_text(json.dumps(value),encoding='utf-8')
        cmd=[sys.executable,'-B',str(ROOT/'scripts/inspect_host_report.py'),'--context',str(self.home/'context.json'),'--policy',str(self.home/'policy.json'),'--scope-only','--format','text']
        r=subprocess.run(cmd,capture_output=True,text=True,encoding='utf-8',timeout=10)
        self.assertEqual(r.returncode,0,r.stderr);self.assertIn('not_selected',r.stdout);self.assertNotIn(self.f.context.api_token,r.stdout)

if __name__=='__main__':unittest.main()
