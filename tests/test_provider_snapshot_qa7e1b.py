"""Independent read-only grant snapshot tests with fresh synthetic SQLite stores.
No network, broker process, model, credentials or native Gateway is executed.
"""
from contextlib import closing
import hashlib
from pathlib import Path
import sqlite3
import sys
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'packages/claw-hermes'))
import test_provider_egress as primary_fixtures
from execution_budget import ExecutionDenied
from provider_egress import EGRESS


class ProviderSnapshotQA(unittest.TestCase):
    def setUp(self):
        self.source=primary_fixtures.EgressContracts('test_reservation_then_irrevocable_grant')
        self.source.setUp();self.addCleanup(self.source.doCleanups)
        self.document=self.source.permit();self.grant=self.document['grant']
        self.path=self.source.f.home/'state.db'
    def check(self):return self.source.verifier.check_authority(self.grant)
    def test_valid_snapshot_preserves_source_bytes(self):
        before=self.path.read_bytes();self.check();self.assertEqual(before,self.path.read_bytes())
    def test_reader_never_calls_native_write_owner(self):
        with patch.object(self.source.f.owner,'_execute_write',side_effect=AssertionError('unexpected writer')):
            self.check()
    def test_connections_query_only_and_closed(self):
        original=sqlite3.connect;seen=[];statements=[]
        def traced(*a,**kw):
            self.assertIn('mode=ro',a[0]);self.assertIs(kw['uri'],True)
            c=original(*a,**kw);c.set_trace_callback(statements.append);seen.append(c);return c
        with patch('provider_egress.sqlite3.connect',traced):self.check()
        self.assertTrue(seen)
        for conn in seen:
            with self.assertRaises(sqlite3.ProgrammingError):conn.execute('SELECT 1')
        self.assertFalse(any(s.split()[0].upper() in {'INSERT','UPDATE','DELETE','CREATE','DROP','REPLACE'} for s in statements))
    def test_expired_grant_rechecked_at_authority_read(self):
        # Consumption and the worker-thread read are distinct stages. Expiry can
        # occur while the latter is queued. No real sleeping or network involved.
        self.source.verifier.consume(self.document)
        self.source.now+=21
        with self.assertRaisesRegex(ExecutionDenied,'egress_grant_expired'):self.check()
    def test_exact_expiry_boundary_not_still_authorized(self):
        self.source.now=self.grant['expiresAtMs']/1000
        with self.assertRaisesRegex(ExecutionDenied,'egress_grant_expired'):self.check()
    def changed_on_close(self,sql,args=()):
        original=sqlite3.connect;outer=self;changed=[]
        class ChangesAtSnapshotEnd(sqlite3.Connection):
            def rollback(self):
                super().rollback()
                if not changed:
                    with closing(original(outer.path)) as writer:
                        writer.execute(sql,args);writer.commit()
                    changed.append(True)
        def connect(*a,**kw):return original(*a,**kw,factory=ChangesAtSnapshotEnd)
        with patch('provider_egress.sqlite3.connect',connect):
            with self.assertRaises(ExecutionDenied):self.check()
        self.assertEqual(changed,[True])
    def test_owner_changes_before_reader_returns(self):
        self.changed_on_close('UPDATE runtime_epoch SET epoch=epoch+1')
    def test_instance_changes_before_reader_returns(self):
        self.changed_on_close("UPDATE runtime_epoch SET instance_id='next-instance'")
    def test_grant_removed_before_reader_returns(self):
        self.changed_on_close('DELETE FROM state_meta WHERE key=?',(EGRESS+self.source.config.scope+'.'+self.grant['ticket'],))
    def test_missing_grant_never_restores_budget(self):
        self.source.f.sql('DELETE FROM state_meta WHERE key=?',(EGRESS+self.source.config.scope+'.'+self.grant['ticket'],))
        before=self.source.f.ledger.snapshot()
        with self.assertRaises(ExecutionDenied):self.check()
        self.assertEqual(self.source.f.ledger.snapshot(),before)

if __name__=='__main__':unittest.main()
