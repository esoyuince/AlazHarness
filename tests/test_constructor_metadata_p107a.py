"""Actual SQLite unit fixtures; no native source/OS boundary is faked."""
from pathlib import Path
import builtins
import os
import sqlite3
import sys
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'packages/claw-hermes'))
import gateway_constructor_metadata as gate

class MetadataTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:');self.addCleanup(self.db.close)
        self.db.executescript('CREATE TABLE schema_version(version); INSERT INTO schema_version VALUES(31); CREATE TABLE state_meta(key,value);')
        self.db.execute('INSERT INTO state_meta VALUES(?,?)',('message_uid_backfill','1'));self.db.commit();self.db.execute('PRAGMA query_only=ON')
    def check(self):return gate.verify_constructor_metadata(self.db,native_pin=gate.NATIVE_PIN)
    def mutation(self,sql,args=()):
        self.db.execute('PRAGMA query_only=OFF');self.db.execute(sql,args);self.db.commit();self.db.execute('PRAGMA query_only=ON')
    def refusal(self,code):
        before=self.db.total_changes
        with self.assertRaisesRegex(gate.ConstructorMetadataRejected,'^'+code+'$'):self.check()
        self.assertEqual(self.db.total_changes,before)
        self.assertEqual(tuple(self.db.execute('PRAGMA query_only').fetchone()),(1,))
    def test_clear_metadata_is_scoped_observation_only(self):
        queries=[];self.db.set_trace_callback(queries.append);before=self.db.total_changes
        with patch.object(builtins,'open',side_effect=AssertionError('file')),patch.object(os,'open',side_effect=AssertionError('fd')):
            result=self.check()
        self.assertEqual(result['state'],'KNOWN_CONSTRUCTOR_REPAIR_MARKERS_CLEAR');self.assertEqual(before,self.db.total_changes)
        self.assertTrue(all(q.startswith(('SELECT ','PRAGMA ')) for q in queries))
        for key in ('sqlWritesPerformed','connectionCreated','connectionClosed','allConstructorSideEffectsExcluded','schemaDigestVerifiedHere','runtimeAdmissionAuthorized','fullD3BAccepted'):self.assertIs(result[key],False)
        self.assertIs(result['nativeConstructorMayWrite'],True)
    def test_sqlite_row_factory_supported(self):
        self.db.row_factory=sqlite3.Row;self.assertEqual(self.check()['state'],'KNOWN_CONSTRUCTOR_REPAIR_MARKERS_CLEAR')
    def test_readwrite_policy_refused_not_reset(self):
        self.db.execute('PRAGMA query_only=OFF')
        with self.assertRaisesRegex(gate.ConstructorMetadataRejected,'query_only_required'):self.check()
        self.assertEqual(self.db.execute('PRAGMA query_only').fetchone(),(0,))
    def test_old_or_future_version_refused_without_migration(self):
        for value in (30,32,0,None,'31'):
            self.mutation('UPDATE main.schema_version SET version=?',(value,));self.refusal('constructor_metadata_schema_version')
            self.assertEqual(self.db.execute('SELECT version FROM main.schema_version').fetchone(),(value,))
    def test_duplicate_version_not_first_row_wins(self):
        self.mutation('INSERT INTO main.schema_version VALUES(31)');self.refusal('constructor_metadata_schema_version')
    def test_missing_version_refused(self):
        self.mutation('DELETE FROM main.schema_version');self.refusal('constructor_metadata_schema_version')
    def test_missing_backfill_not_written(self):
        self.mutation('DELETE FROM main.state_meta');self.refusal('constructor_metadata_backfill_incomplete')
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM main.state_meta').fetchone(),(0,))
    def test_backfill_requires_exact_string_one(self):
        for value in ('0','true','',None,1,b'1'):
            self.mutation('UPDATE main.state_meta SET value=?',(value,));self.refusal('constructor_metadata_backfill_incomplete')
    def test_all_known_repair_keys_refused_regardless_of_value(self):
        for key in sorted(gate.REPAIR_KEYS):
            for value in ('1','0','',None):
                self.mutation('INSERT INTO main.state_meta VALUES(?,?)',(key,value))
                self.refusal('constructor_metadata_repair_pending')
                self.assertEqual(self.db.execute('SELECT value FROM main.state_meta WHERE key=?',(key,)).fetchone(),(value,))
                self.mutation('DELETE FROM main.state_meta WHERE key=?',(key,))
    def test_duplicate_backfill_key_refused(self):
        self.mutation("INSERT INTO main.state_meta VALUES('message_uid_backfill','1')");self.refusal('constructor_metadata_ambiguous')
    def test_row_limit_does_not_scan_unbounded_results(self):
        self.db.execute('PRAGMA query_only=OFF');self.db.executemany('INSERT INTO main.state_meta VALUES(?,?)',[('message_uid_backfill','1')]*100);self.db.commit();self.db.execute('PRAGMA query_only=ON')
        self.refusal('constructor_metadata_ambiguous')
    def test_temporary_metadata_cannot_hide_main_repair(self):
        self.mutation("INSERT INTO main.state_meta VALUES('fts_stale','1')")
        self.mutation('CREATE TEMP TABLE state_meta(key,value)')
        self.mutation("INSERT INTO temp.state_meta VALUES('message_uid_backfill','1')")
        self.refusal('constructor_metadata_repair_pending')
    def test_temporary_version_cannot_hide_old_main_version(self):
        self.mutation('UPDATE main.schema_version SET version=30')
        self.mutation('CREATE TEMP TABLE schema_version(version)');self.mutation('INSERT INTO temp.schema_version VALUES(31)')
        self.refusal('constructor_metadata_schema_version')
    def test_unrelated_metadata_is_not_erased_or_claimed_qualified(self):
        self.mutation("INSERT INTO main.state_meta VALUES('future_aux','unreviewed')")
        result=self.check();self.assertIs(result['allConstructorSideEffectsExcluded'],False)
        self.assertEqual(self.db.execute("SELECT value FROM main.state_meta WHERE key='future_aux'").fetchone(),('unreviewed',))
    def test_open_read_transaction_is_preserved(self):
        self.db.execute('BEGIN');self.check();self.assertTrue(self.db.in_transaction)
        self.db.rollback()
    def test_closed_connection_is_bounded(self):
        self.db.close()
        with self.assertRaisesRegex(gate.ConstructorMetadataRejected,'^constructor_metadata_unavailable$'):self.check()
    def test_missing_table_bounded_no_creation(self):
        self.mutation('DROP TABLE main.state_meta');self.refusal('constructor_metadata_unavailable')
        self.assertEqual(self.db.execute("SELECT name FROM main.sqlite_schema WHERE name='state_meta'").fetchall(),[])
    def test_wrong_pin_refused_before_query(self):
        traces=[];self.db.set_trace_callback(traces.append)
        with self.assertRaisesRegex(gate.ConstructorMetadataRejected,'pin'):
            gate.verify_constructor_metadata(self.db,native_pin='0'*40)
        self.assertEqual(traces,[])
    def test_foreign_object_rejected_without_using_it(self):
        with self.assertRaisesRegex(gate.ConstructorMetadataRejected,'connection'):
            gate.verify_constructor_metadata(object(),native_pin=gate.NATIVE_PIN)

if __name__=='__main__':unittest.main()
