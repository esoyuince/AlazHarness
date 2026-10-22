"""Real SQLite queries; native class/lease/mount boundaries explicitly doubled."""
from contextlib import contextmanager,ExitStack
from dataclasses import replace
import builtins,os,sqlite3,sys,tempfile,threading,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'packages/claw-hermes'))
import gateway_response_live as g
class State:pass
class Response:
    def _identity_bound(self):return self._max_identities or 10*self._max_size
class Binding:
    def __init__(self,state):self._state=state;self._connection=state._conn;self._lock=state._lock
    @contextmanager
    def read(self):
        if not self._lock.acquire(blocking=False):raise RuntimeError('fixture_busy')
        try:yield self._connection
        finally:self._lock.release()

class LiveResponseChecks(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='response-live-unit-');self.addCleanup(self.temp.cleanup)
        self.home=Path(self.temp.name).resolve();self.state=State();self.response=Response()
        self.state._conn=sqlite3.connect(self.home/'state.db');self.addCleanup(self.state._conn.close)
        self.state._lock=threading.Lock();self.state._db_file_identity=(7,12)
        self.response._conn=sqlite3.connect(self.home/'response_store.db');self.addCleanup(self.response._conn.close)
        self.response._conn.executescript('CREATE TABLE responses(response_id TEXT PRIMARY KEY,data TEXT,accessed_at REAL);CREATE TABLE response_keys(request_key TEXT PRIMARY KEY,settled_at REAL);')
        self.response._db_path=str(self.home/'response_store.db');self.response._max_size=100;self.response._max_identities=1000
        self.response._canonical_state=Binding(self.state)
        self.expected=g.ResponseConnectionExpectation(g.FEATURE_COMMIT,g.live.schema_digest(self.response._conn),(7,13))
        self.actor=(os.getpid(),23001,23003,threading.get_ident())
        self.held=g.live.profiles.ProfileLease.__new__(g.live.profiles.ProfileLease);self.held._actor=self.actor;self.held._home=self.home
        self.mount=g.live.mounts.ExpectedMount(11,(7,0),'/profile','/owned','ext4')
        self.stack=ExitStack();self.addCleanup(self.stack.close)
        self.lease=self.stack.enter_context(patch.object(g.live.profiles.ProfileLease,'check',return_value={}))
        self.stack.enter_context(patch.object(g.live.profiles,'_actor',return_value=self.actor))
        self.stack.enter_context(patch.object(g,'_native_types',return_value=(State,Response,Binding)))
        self.mountcall=self.stack.enter_context(patch.object(g,'_observe',return_value=({'hash':'owned'},(7,13))))
    def verify(self,expected=None,**kw):return g.verify_response_connection(self.held,self.mount,self.state,self.response,expected or self.expected,**kw)
    def denied(self,code,expected=None,**kw):
        with self.assertRaisesRegex(g.ResponseLiveRejected,'^'+code+'$'):self.verify(expected,**kw)
        self.assertFalse(self.state._lock.locked())
    def write(self,sql,args=()):self.response._conn.execute(sql,args);self.response._conn.commit()
    def test_no_write_or_new_connection_or_raw_file(self):
        queries=[];self.response._conn.set_trace_callback(queries.append)
        with patch.object(sqlite3,'connect',side_effect=AssertionError('new sqlite')),patch.object(builtins,'open',side_effect=AssertionError('raw open')),patch.object(os,'open',side_effect=AssertionError('fd open')):
            result=self.verify(constructor=True)
        self.assertEqual(result['state'],'NATIVE_RESPONSE_CONNECTION_VERIFIED')
        self.assertIs(result['constructorRowsUnchanged'],True);self.assertEqual(self.response._conn.total_changes,0)
        self.assertTrue(all(s.startswith(('SELECT ','PRAGMA ')) for s in queries))
        self.assertEqual((self.lease.call_count,self.mountcall.call_count),(2,2))
        for key in ('runtimeAdmissionAuthorized','sqlWritesPerformed','connectionsClosed','newDatabaseConnectionsOpened','rawDatabaseDescriptorsOpened','preConstructorVerificationPerformed','fullD3BAccepted'):
            self.assertIs(result[key],False)
    def test_non_constructor_check_does_not_claim_zero_initial_writes(self):
        self.write("INSERT INTO responses VALUES('body','{}',1)")
        result=self.verify();self.assertIsNone(result['constructorRowsUnchanged']);self.assertEqual(result['bodyCount'],1)
    def test_constructor_mutation_refused_before_mount(self):
        self.write("INSERT INTO responses VALUES('body','{}',1)")
        self.denied('response_live_constructor_changed_rows',constructor=True);self.mountcall.assert_not_called()
    def test_active_transaction_retained(self):
        self.response._conn.execute('BEGIN IMMEDIATE');self.denied('response_live_transaction_active')
        self.assertTrue(self.response._conn.in_transaction);self.response._conn.rollback()
    def test_closed_response_handle_not_reopened(self):
        self.response._conn.close()
        with patch.object(sqlite3,'connect',side_effect=AssertionError('unexpected reopen')):self.denied('response_live_observation_unavailable')
    def test_pending_response_identity_not_reinterpreted(self):
        self.write("INSERT INTO response_keys VALUES('idem',NULL)");self.denied('response_live_unsettled_identity')
        self.assertIsNone(self.response._conn.execute('SELECT settled_at FROM response_keys').fetchone()[0])
    def test_settled_identity_retained(self):
        self.write("INSERT INTO response_keys VALUES('idem',1)");r=self.verify();self.assertEqual(r['identityCount'],1)
    def test_temp_identity_table_does_not_hide_pending(self):
        self.write("INSERT INTO main.response_keys VALUES('idem',NULL)")
        self.response._conn.execute('CREATE TEMP TABLE response_keys(request_key TEXT,settled_at REAL)')
        self.denied('response_live_unsettled_identity')
    def test_response_count_limit_never_evicts(self):
        self.response._conn.executemany('INSERT INTO responses VALUES(?,?,?)',[(str(i),'{}',1) for i in range(101)]);self.response._conn.commit()
        self.denied('response_live_retention_overflow');self.assertEqual(self.response._conn.execute('SELECT count(*) FROM responses').fetchone()[0],101)
    def test_identity_count_limit(self):
        self.response._conn.executemany('INSERT INTO response_keys VALUES(?,?)',[(str(i),1) for i in range(1001)]);self.response._conn.commit()
        self.denied('response_live_retention_overflow')
    def test_retention_configuration_mismatch(self):
        self.response._max_size=99;self.denied('response_live_retention_mismatch')
    def test_foreign_response_path(self):
        self.response._db_path=str(self.home/'foreign.db');self.denied('response_live_disk_path')
    def test_memory_fallback_path_refused(self):
        self.response._db_path=None;self.denied('response_live_disk_path')
    def test_memory_connection_with_disk_label_refused(self):
        conn=sqlite3.connect(':memory:');self.addCleanup(conn.close);self.response._conn=conn
        self.denied('response_live_observation_unavailable')
    def test_missing_binding_refused(self):
        self.response._canonical_state=None;self.denied('response_live_canonical_binding')
    def test_other_state_binding_refused(self):
        other=State();other._conn=self.state._conn;other._lock=self.state._lock
        self.response._canonical_state=Binding(other);self.denied('response_live_canonical_binding')
    def test_swapped_state_handle_refused(self):
        conn=sqlite3.connect(':memory:');self.addCleanup(conn.close);self.state._conn=conn
        self.denied('response_live_canonical_binding')
    def test_other_actor_refused(self):
        with patch.object(g.live.profiles,'_actor',return_value=(999,23001,23003,1)):self.denied('response_live_other_actor')
    def test_mismatched_schema(self):self.denied('response_live_observation_unavailable',replace(self.expected,schema_sha256='f'*64))
    def test_extra_attached_database_refused_without_detach(self):
        self.response._conn.execute("ATTACH ':memory:' AS external")
        self.denied('response_live_observation_unavailable')
        self.assertIn('external',[r[1] for r in self.response._conn.execute('PRAGMA database_list')])
    def test_weak_sync_not_raised(self):
        self.response._conn.execute('PRAGMA synchronous=NORMAL');self.denied('response_live_observation_unavailable')
        self.assertEqual(self.response._conn.execute('PRAGMA synchronous').fetchone()[0],1)
    def test_queryonly_not_reset(self):
        self.response._conn.execute('PRAGMA query_only=ON');self.denied('response_live_observation_unavailable')
    def test_unexpected_application_or_user_version(self):
        for pragma in ('application_id','user_version'):
            self.response._conn.execute('PRAGMA '+pragma+'=7');self.denied('response_live_unexpected_header_version');self.response._conn.execute('PRAGMA '+pragma+'=0')
    def test_mount_change_releases_native_mutex(self):
        self.mountcall.side_effect=[({'hash':'a'},(7,13)),({'hash':'b'},(7,13))]
        self.denied('response_live_mount_changed')
    def test_expected_inode_not_same_as_canonical(self):self.denied('response_live_distinct_database',replace(self.expected,identity=(7,12)))
    def test_wrong_types_have_no_mount_or_query(self):
        for values in ({'feature_commit':'f'*40},{'identity':(True,13)},{'identity':[7,13]},{'max_size':True},{'max_identities':1001},{'schema_sha256':'X'*64}):
            with self.subTest(values=values),self.assertRaises(g.ResponseLiveRejected):replace(self.expected,**values)
        self.denied('response_live_constructor_flag',constructor=1);self.mountcall.assert_not_called()

if __name__=='__main__':unittest.main()
