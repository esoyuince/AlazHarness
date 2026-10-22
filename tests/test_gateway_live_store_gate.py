"""Real SQLite query tests with explicit native-identity/mount doubles.

No native Hermes or privileged Linux success is implied by this unit fixture.
"""
from contextlib import ExitStack
from dataclasses import replace,FrozenInstanceError
import builtins
import os
from pathlib import Path
import sqlite3
import stat
import sys
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'packages/claw-hermes'))
import gateway_live_store_gate as g

class StateDouble:pass
class ReplayDouble:pass

class LiveStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='alaz-live-store-unit-')
        self.addCleanup(self.temp.cleanup);self.home=Path(self.temp.name).resolve()
        self.state=StateDouble();self.replay=ReplayDouble()
        self.state._conn=sqlite3.connect(self.home/'state.db')
        self.replay._conn=sqlite3.connect(self.home/'runs_idempotency.db')
        self.addCleanup(self.state._conn.close);self.addCleanup(self.replay._conn.close)
        self.sid='12345678-1234-4234-8234-123456789012'
        self.state._conn.executescript("""
            PRAGMA foreign_keys=ON; PRAGMA application_id=12345; PRAGMA synchronous=FULL;
            CREATE TABLE schema_version(version INTEGER);
            INSERT INTO schema_version VALUES(31);
            CREATE TABLE state_meta(key TEXT PRIMARY KEY,value TEXT);
            CREATE TABLE runtime_epoch(singleton INTEGER PRIMARY KEY,epoch INTEGER,instance_id TEXT);
            CREATE TABLE session_admissions(status TEXT);
            CREATE TABLE worker_executions(status TEXT);
        """)
        self.state._conn.execute('INSERT INTO state_meta VALUES (?,?)',('store_instance_id',self.sid));self.state._conn.commit()
        self.replay._conn.execute('CREATE TABLE run_idempotency(status_json TEXT)');self.replay._conn.commit()
        for p in (self.home/'state.db',self.home/'runs_idempotency.db'):p.chmod(0o600)
        ids=[(p.stat().st_dev,p.stat().st_ino) for p in (self.home/'state.db',self.home/'runs_idempotency.db')]
        self.state.db_path=self.home/'state.db';self.replay._db_path=str(self.home/'runs_idempotency.db')
        self.state.read_only=False;self.state._shared_registry_owned=False;self.state._token_writer_thread=None
        self.state._lock=threading.Lock();self.replay._lock=threading.Lock();self.replay.durable=True
        self.state._db_file_identity=ids[0];self.state._db_file_application_id=12345
        self.expected=g.PreparedStoreExpectation(g.NATIVE_PIN,g.schema_digest(self.state._conn),g.schema_digest(self.replay._conn),self.sid,12345,ids[0],ids[1],0,None)
        self.actor=(os.getpid(),self.home.stat().st_uid,self.home.stat().st_gid,threading.get_ident())
        self.held=g.profiles.ProfileLease.__new__(g.profiles.ProfileLease)
        self.held._home=self.home;self.held._actor=self.actor
        self.mount=g.mounts.ExpectedMount(10,(7,0),'/profile','/test-profile','ext4')
        self.stack=ExitStack();self.addCleanup(self.stack.close)
        self.check=self.stack.enter_context(patch.object(g.profiles.ProfileLease,'check',return_value={'state':'NATIVE_PROFILE_RESERVED'}))
        self.actor_call=self.stack.enter_context(patch.object(g.profiles,'_actor',return_value=self.actor))
        self.types=self.stack.enter_context(patch.object(g,'_native_types',return_value=(StateDouble,ReplayDouble,sqlite3.Connection)))
        self.mount_call=self.stack.enter_context(patch.object(g.mounts,'observe_profile_mounts',return_value={'mountTableSha256':'a'*64}))
        if os.name=='nt':
            original=Path.lstat
            def portable(path,*a,**k):
                info=original(path,*a,**k)
                if path in (self.home/'state.db',self.home/'runs_idempotency.db'):
                    info=SimpleNamespace(**{n:getattr(info,n) for n in ('st_dev','st_ino','st_mode','st_uid','st_gid','st_nlink')})
                    info.st_mode=stat.S_IFREG|0o600
                return info
            self.stack.enter_context(patch.object(Path,'lstat',portable))
    def verify(self,expected=None):return g.verify_live_stores(self.held,self.mount,self.state,self.replay,expected or self.expected)
    def denied(self,code,expected=None):
        with self.assertRaisesRegex(g.LiveStoreRejected,'^'+code+'$'):self.verify(expected)
        self.assertFalse(self.state._lock.locked());self.assertFalse(self.replay._lock.locked())
    def test_exact_fixture_connection_metadata_passes_without_writes(self):
        queries=[];self.state._conn.set_trace_callback(queries.append);self.replay._conn.set_trace_callback(queries.append)
        before=(self.state._conn.total_changes,self.replay._conn.total_changes)
        with patch.object(builtins,'open',side_effect=AssertionError('raw open')),patch.object(os,'open',side_effect=AssertionError('raw fd')),patch.object(Path,'open',side_effect=AssertionError('path open')):
            result=self.verify()
        self.assertEqual(result['state'],'NATIVE_STORE_CONNECTIONS_VERIFIED')
        self.assertEqual(before,(self.state._conn.total_changes,self.replay._conn.total_changes))
        self.assertTrue(all(q.startswith(('SELECT ','PRAGMA ')) and '=' not in q.split('WHERE')[0] for q in queries))
        for key in ('sqlWritesPerformed','rawDatabaseFilesOpened','connectionsClosed','sqliteHandleInodeProven','writeCapabilityProven','preConstructorValidationPerformed','pairedRecoveryVerified','runtimeAdmissionAuthorized','fullD3BAccepted'):
            self.assertIs(result[key],False)
        self.assertEqual(self.mount_call.call_count,2)
    def test_native_memory_fallback_refused_before_mutex_or_sql(self):
        self.replay.durable=False
        with patch.object(g,'_connection') as connection:self.denied('live_store_volatile_replay')
        connection.assert_not_called();self.mount_call.assert_not_called()
    def test_memory_connection_cannot_be_disguised_with_disk_path(self):
        conn=sqlite3.connect(':memory:');self.addCleanup(conn.close);self.replay._conn=conn
        self.denied('live_store_connection_path')
    def test_missing_lease_not_authority(self):
        with self.assertRaisesRegex(g.LiveStoreRejected,'profile_lease_required'):
            g.verify_live_stores({},self.mount,self.state,self.replay,self.expected)
        self.types.assert_not_called()
    def test_expected_dictionary_not_authority(self):
        with self.assertRaisesRegex(g.LiveStoreRejected,'trusted_expectation'):
            g.verify_live_stores(self.held,self.mount,self.state,self.replay,dict(self.expected.__dict__))
    def test_wrong_actor_refused(self):
        self.actor_call.return_value=(self.actor[0]+1,*self.actor[1:])
        self.denied('live_store_other_actor');self.types.assert_not_called()
    def test_finished_native_lease_failure_is_bounded(self):
        self.check.side_effect=g.profiles.ProfileLeaseRejected('untrusted path')
        self.denied('live_store_observation_unavailable');self.types.assert_not_called()
    def test_native_type_mismatch_refused(self):
        self.types.return_value=(SimpleNamespace,ReplayDouble,sqlite3.Connection)
        self.denied('live_store_native_types')
    def test_shared_or_readonly_native_state_refused(self):
        for attr in ('read_only','_shared_registry_owned'):
            setattr(self.state,attr,True);self.denied('live_store_dedicated_writer_required');setattr(self.state,attr,False)
    def test_foreign_declared_path_refused(self):
        self.replay._db_path=str(self.home/'foreign.db');self.denied('live_store_declared_paths')
    def test_foreign_actual_connection_refused(self):
        other=sqlite3.connect(self.home/'foreign.db');self.addCleanup(other.close);self.replay._conn=other
        self.denied('live_store_connection_path')
    def test_attached_foreign_database_refused_without_detach(self):
        self.replay._conn.execute("ATTACH DATABASE ':memory:' AS foreign_db")
        self.denied('live_store_connection_path')
        self.assertIn('foreign_db',[r[1] for r in self.replay._conn.execute('PRAGMA database_list')])
    def test_query_only_is_not_silently_reset(self):
        self.replay._conn.execute('PRAGMA query_only=ON');self.denied('live_store_query_only_connection')
        self.assertEqual(self.replay._conn.execute('PRAGMA query_only').fetchone()[0],1)
    def test_normal_sync_is_not_silently_raised(self):
        self.replay._conn.execute('PRAGMA synchronous=NORMAL');self.denied('live_store_synchronous')
        self.assertEqual(self.replay._conn.execute('PRAGMA synchronous').fetchone()[0],1)
    def test_journal_drift_refused(self):
        self.replay._conn.execute('PRAGMA journal_mode=MEMORY');self.denied('live_store_journal_mode')
    def test_schema_added_table_refused(self):
        self.replay._conn.execute('CREATE TABLE extra(x)');self.denied('live_store_schema_mismatch')
    def test_expected_schema_digest_not_derived_from_candidate(self):
        self.denied('live_store_schema_mismatch',replace(self.expected,replay_schema_sha256='f'*64))
    def test_schema_version_value_mismatch(self):
        self.state._conn.execute('UPDATE schema_version SET version=30');self.state._conn.commit()
        self.denied('live_store_native_schema_version')
    def test_duplicate_version_rows_refused(self):
        self.state._conn.execute('INSERT INTO schema_version VALUES(31)');self.state._conn.commit();self.denied('live_store_single_value')
    def test_store_instance_value_mismatch(self):
        self.state._conn.execute("UPDATE state_meta SET value='other'");self.state._conn.commit();self.denied('live_store_instance_mismatch')
    def test_application_identity_drift(self):
        self.state._conn.execute('PRAGMA application_id=222');self.denied('live_store_application_id')
    def test_native_state_open_identity_drift(self):
        self.state._db_file_identity=(1,2);self.denied('live_store_native_state_identity')
    def test_foreign_keys_off_refused(self):
        self.state._conn.execute('PRAGMA foreign_keys=OFF');self.denied('live_store_foreign_keys')
    def test_epoch_is_exact_not_advanced_by_gate(self):
        self.state._conn.execute("INSERT INTO runtime_epoch VALUES(1,2,'owner-two')");self.state._conn.commit()
        self.denied('live_store_epoch_mismatch')
        accepted=self.verify(replace(self.expected,epoch=2,instance_id='owner-two'))
        self.assertEqual(accepted['epochObserved'],2)
        self.assertEqual(self.state._conn.execute('SELECT epoch FROM runtime_epoch').fetchone()[0],2)
    def test_any_nonterminal_or_null_admission_refused(self):
        for status in ('queued','started','unknown','alien',None):
            self.state._conn.execute('INSERT INTO session_admissions VALUES(?)',(status,));self.state._conn.commit()
            self.denied('live_store_unresolved_admissions')
            self.state._conn.execute('DELETE FROM session_admissions');self.state._conn.commit()
    def test_any_nonterminal_or_null_worker_refused(self):
        for status in ('registered','running','unknown','alien',None):
            self.state._conn.execute('INSERT INTO worker_executions VALUES(?)',(status,));self.state._conn.commit()
            self.denied('live_store_unresolved_workers')
            self.state._conn.execute('DELETE FROM worker_executions');self.state._conn.commit()
    def test_unresolved_or_invalid_replay_refused(self):
        for raw in ('{"status":"running"}','{}','{"status":null}','{"status":7}','{"status":"alien"}','[]'):
            self.replay._conn.execute('INSERT INTO run_idempotency VALUES(?)',(raw,));self.replay._conn.commit()
            self.denied('live_store_unresolved_replay')
            self.replay._conn.execute('DELETE FROM run_idempotency');self.replay._conn.commit()
    def test_duplicate_status_key_is_not_a_terminal_decision(self):
        raw='{"status":"completed","status":"running"}'
        self.replay._conn.execute('INSERT INTO run_idempotency VALUES(?)',(raw,));self.replay._conn.commit()
        self.denied('live_store_unresolved_replay')
    def test_nested_duplicate_keys_refused(self):
        raw='{"status":"completed","detail":{"same":1,"same":2}}'
        self.replay._conn.execute('INSERT INTO run_idempotency VALUES(?)',(raw,));self.replay._conn.commit()
        self.denied('live_store_unresolved_replay')
    def test_oversized_status_refused_without_parsing(self):
        self.replay._conn.execute('INSERT INTO run_idempotency VALUES(?)',('x'*2097153,));self.replay._conn.commit()
        self.denied('live_store_unresolved_replay')
    def test_null_replay_status_is_not_terminal(self):
        self.replay._conn.execute('INSERT INTO run_idempotency VALUES(NULL)');self.replay._conn.commit()
        self.denied('live_store_unresolved_replay')
    def test_malformed_replay_is_bounded_and_not_deleted(self):
        self.replay._conn.execute("INSERT INTO run_idempotency VALUES('not-json')");self.replay._conn.commit()
        with self.assertRaises(g.LiveStoreRejected):self.verify()
        self.assertEqual(self.replay._conn.execute('SELECT status_json FROM run_idempotency').fetchone()[0],'not-json')
    def test_terminal_records_do_not_claim_cross_store_consistency(self):
        self.state._conn.execute("INSERT INTO session_admissions VALUES('terminal')");self.state._conn.commit()
        self.replay._conn.execute('INSERT INTO run_idempotency VALUES(?)',('{"status":"completed"}',));self.replay._conn.commit()
        result=self.verify();self.assertIs(result['pairedRecoveryVerified'],False);self.assertIs(result['runtimeAdmissionAuthorized'],False)
    def test_active_native_transaction_survives_rejection(self):
        self.replay._conn.execute('BEGIN IMMEDIATE');self.denied('live_store_transaction_active')
        self.assertTrue(self.replay._conn.in_transaction);self.replay._conn.rollback()
    def test_first_busy_mutex_is_not_released_by_gate(self):
        self.state._lock.acquire()
        try:
            with self.assertRaisesRegex(g.LiveStoreRejected,'busy'):self.verify()
            self.assertTrue(self.state._lock.locked());self.assertFalse(self.replay._lock.locked())
        finally:self.state._lock.release()
    def test_second_busy_mutex_releases_only_first(self):
        self.replay._lock.acquire()
        try:
            with self.assertRaisesRegex(g.LiveStoreRejected,'busy'):self.verify()
            self.assertFalse(self.state._lock.locked());self.assertTrue(self.replay._lock.locked())
        finally:self.replay._lock.release()
    def test_registered_background_writer_refused(self):
        self.state._token_writer_thread=SimpleNamespace(is_alive=lambda:True)
        self.denied('live_store_background_writer')
    def test_duplicate_mutex_refused_before_acquisition(self):
        self.replay._lock=self.state._lock;self.denied('live_store_distinct_mutexes')
    def test_mount_change_refused_and_connections_left_open(self):
        self.mount_call.side_effect=[{'mountTableSha256':'a'*64},{'mountTableSha256':'b'*64}]
        self.denied('live_store_mount_changed')
        self.assertEqual(self.state._conn.execute('SELECT 1').fetchone(),(1,));self.assertEqual(self.replay._conn.execute('SELECT 1').fetchone(),(1,))
    def test_temp_schema_cannot_hide_wrong_main_version(self):
        self.state._conn.execute('UPDATE main.schema_version SET version=30');self.state._conn.commit()
        self.state._conn.execute('CREATE TEMP TABLE schema_version(version INTEGER)')
        self.state._conn.execute('INSERT INTO temp.schema_version VALUES(31)');self.state._conn.commit()
        self.denied('live_store_native_schema_version')
    def test_temp_epoch_cannot_hide_main_generation(self):
        self.state._conn.execute("INSERT INTO main.runtime_epoch VALUES(1,1,'actual')");self.state._conn.commit()
        self.state._conn.execute('CREATE TEMP TABLE runtime_epoch(singleton INTEGER,epoch INTEGER,instance_id TEXT)')
        self.denied('live_store_epoch_mismatch')
    def test_temp_admission_cannot_hide_pending_main_work(self):
        self.state._conn.execute("INSERT INTO main.session_admissions VALUES('queued')");self.state._conn.commit()
        self.state._conn.execute('CREATE TEMP TABLE session_admissions(status TEXT)')
        self.denied('live_store_unresolved_admissions')
    def test_temp_worker_cannot_hide_unknown_main_work(self):
        self.state._conn.execute("INSERT INTO main.worker_executions VALUES('unknown')");self.state._conn.commit()
        self.state._conn.execute('CREATE TEMP TABLE worker_executions(status TEXT)')
        self.denied('live_store_unresolved_workers')
    def test_temp_replay_cannot_hide_running_main_work(self):
        self.replay._conn.execute('INSERT INTO main.run_idempotency VALUES(?)',('{"status":"running"}',));self.replay._conn.commit()
        self.replay._conn.execute('CREATE TEMP TABLE run_idempotency(status_json TEXT)')
        self.denied('live_store_unresolved_replay')
    def test_closed_connection_bounded(self):
        self.replay._conn.close();self.denied('live_store_observation_unavailable')
    def test_wrong_expected_inode(self):
        wrong=replace(self.expected,replay_identity=(self.expected.replay_identity[0],self.expected.replay_identity[1]+1))
        self.denied('live_store_file_identity',wrong)
    def test_schema_size_bound(self):
        with patch.object(g,'MAX_SCHEMA_ROWS',1):self.denied('live_store_schema_limit')

class ExpectationContracts(unittest.TestCase):
    def valid(self):return g.PreparedStoreExpectation(g.NATIVE_PIN,'a'*64,'b'*64,'12345678-1234-4234-8234-123456789012',123,(1,2),(1,3),0,None)
    def test_frozen_no_io(self):
        with patch.object(Path,'stat',side_effect=AssertionError('io')):value=self.valid()
        with self.assertRaises(FrozenInstanceError):value.epoch=1
    def test_invalid_source_schema_or_uuid(self):
        for values in ({'native_pin':'a'*40},{'state_schema_sha256':'A'*64},{'replay_schema_sha256':'short'},{'store_instance_id':'not-uuid'}):
            with self.subTest(values=values),self.assertRaises(g.LiveStoreRejected):replace(self.valid(),**values)
    def test_invalid_identity_or_generation(self):
        for values in ({'state_identity':[1,2]},{'replay_identity':(1,2)},{'replay_identity':(2,3)}, {'state_identity':(True,2)}, {'application_id':0},{'application_id':True},{'epoch':True},{'epoch':-1},{'epoch':1},{'instance_id':'unexpected'},{'journal_mode':'memory'}):
            with self.subTest(values=values),self.assertRaises(g.LiveStoreRejected):replace(self.valid(),**values)

if __name__=='__main__':unittest.main()
