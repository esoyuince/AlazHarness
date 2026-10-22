"""Actual SQLite query checks; parent lease/process boundaries explicitly doubled."""
from contextlib import ExitStack
from dataclasses import asdict,replace,FrozenInstanceError
import hashlib,json,os,sqlite3,subprocess,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import MagicMock,patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'packages/claw-hermes'))
import gateway_response_preopen as p

class ResponseReadOnly(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory(prefix='r113-query-');self.addCleanup(t.cleanup);self.home=Path(t.name).resolve();self.path=self.home/p.FILENAME
        schema=json.loads((ROOT/'evidence/d3b-response-preflight-r113q8/native-schema.json').read_text(encoding='utf-8'))
        self.assertEqual(schema['digest'],p.SCHEMA_SHA256)
        conn=sqlite3.connect(self.path)
        for kind in ('table','index'):
            for row in schema['rows']:
                if row[0]==kind and row[3]:conn.execute(row[3])
        conn.commit();self.assertEqual(p.live.schema_digest(conn),p.SCHEMA_SHA256);conn.close()
        self.expected=p.PreparedResponseExpectation(p.NATIVE_FEATURE,p.SCHEMA_SHA256,(self.path.stat().st_dev,self.path.stat().st_ino))
    def mutate(self,sql,args=()):
        c=sqlite3.connect(self.path);c.execute(sql,args);c.commit();c.close()
    def read(self):return p._readonly(self.path,self.expected)
    def key(self,settled=1,model='null',key='idem:owned'):
        self.mutate('INSERT INTO response_keys VALUES(?,?,?,?,?,?)',(key,'a'*64,1,model,settled,'resp-owned'))
    def body(self):self.mutate('INSERT INTO responses VALUES(?,?,?)',('resp-owned','{"output":[]}',1))
    def denied(self,code):
        before=self.path.read_bytes()
        with self.assertRaisesRegex(p.ResponsePreopenRejected,code):self.read()
        self.assertEqual(self.path.read_bytes(),before)
    def test_empty_prepared_native_schema_read_without_content_changes(self):
        before=self.path.read_bytes();self.assertEqual(self.read(),dict.fromkeys(('responses','response_keys','conversations','response_admissions','response_output_order'),0))
        self.assertEqual(self.path.read_bytes(),before);self.assertEqual([x.name for x in self.home.iterdir()],[p.FILENAME])
    def test_closed_settled_response_and_derivative_rows_preserved(self):
        self.key();self.body();self.mutate('INSERT INTO response_admissions VALUES(?,?)',('idem:owned','a'*32));self.mutate('INSERT INTO response_output_order VALUES(?,?,?)',('idem:owned','item-owned',0));self.mutate('INSERT INTO conversations VALUES(?,?)',('owned','resp-owned'))
        before=self.path.read_bytes();counts=self.read();self.assertTrue(all(v==1 for v in counts.values()));self.assertEqual(before,self.path.read_bytes())
    def test_evicted_body_does_not_erase_settled_identity(self):
        self.key();self.assertEqual(self.read()['response_keys'],1)
    def test_missing_file_is_not_created(self):
        q=self.home/'absent.db'
        with self.assertRaises(sqlite3.Error):p._readonly(q,self.expected)
        self.assertFalse(q.exists())
    def test_schema_missing_column_not_migrated(self):
        self.mutate('ALTER TABLE response_keys DROP COLUMN model_json');self.denied('schema_mismatch')
    def test_extra_table_rejected(self):
        self.mutate('CREATE TABLE extra(x)');self.denied('schema_mismatch')
    def test_extra_trigger_rejected_before_it_can_run(self):
        self.mutate('CREATE TRIGGER surprise AFTER INSERT ON responses BEGIN DELETE FROM response_keys; END');self.denied('schema_mismatch')
    def test_view_replacing_native_table_refused(self):
        self.mutate('DROP TABLE conversations');self.mutate('CREATE VIEW conversations AS SELECT 1 AS name,2 AS response_id');self.denied('schema_mismatch')
    def test_old_user_version_not_reset(self):
        self.mutate('PRAGMA user_version=1');self.denied('preopen_version')
    def test_unknown_application_id_not_adopted(self):
        self.mutate('PRAGMA application_id=1');self.denied('preopen_version')
    def test_unsettled_request_no_synthetic_terminal(self):
        self.key(settled=None);self.denied('unsettled_identity')
    def test_response_body_over_limit_not_evicted(self):
        c=sqlite3.connect(self.path);c.executemany('INSERT INTO responses VALUES(?,?,?)',[(str(i),'{}',1) for i in range(101)]);c.commit();c.close();self.denied('retention_pressure')
    def test_identity_over_limit_not_evicted(self):
        c=sqlite3.connect(self.path);c.executemany('INSERT INTO response_keys VALUES(?,?,?,?,?,?)',[(str(i),'a'*64,1,'null',1,'r') for i in range(1001)]);c.commit();c.close();self.denied('retention_pressure')
    def test_body_invalid_json_not_deleted(self):
        self.mutate('INSERT INTO responses VALUES(?,?,?)',('r','bad-json',1));self.denied('invalid_body')
    def test_body_scalar_or_array_not_accepted(self):
        for raw in ('null','[]','3','"value"'):
            self.mutate('INSERT INTO responses VALUES(?,?,?)',('r',raw,1));self.denied('invalid_body');self.mutate('DELETE FROM responses')
    def test_null_body_primary_key_not_accepted(self):
        self.mutate('INSERT INTO responses VALUES(NULL,?,?)',('{}',1));self.denied('invalid_body')
    def test_infinite_timestamp_refused(self):
        self.mutate('INSERT INTO responses VALUES(?,?,?)',('r','{}',float('inf')));self.denied('invalid_body')
    def test_invalid_fingerprint_refused(self):
        self.key();self.mutate("UPDATE response_keys SET fingerprint='x'");self.denied('invalid_identity')
    def test_missing_model_binding_not_filled(self):
        self.key(model=None);self.denied('invalid_identity')
    def test_malformed_model_binding_not_filled(self):
        self.key(model='{');self.denied('invalid_identity')
    def test_null_key_not_accepted(self):
        self.key(key=None);self.denied('invalid_identity')
    def test_orphan_admission_not_deleted(self):
        self.mutate('INSERT INTO response_admissions VALUES(?,?)',('missing','a'*32));self.denied('orphan_admission')
    def test_orphan_output_not_deleted(self):
        self.mutate('INSERT INTO response_output_order VALUES(?,?,?)',('missing','item',0));self.denied('orphan_output')
    def test_negative_output_order_rejected(self):
        self.key();self.mutate('INSERT INTO response_output_order VALUES(?,?,?)',('idem:owned','item',-1));self.denied('orphan_output')
    def test_orphan_conversation_not_deleted(self):
        self.mutate('INSERT INTO conversations VALUES(?,?)',('name','missing'));self.denied('orphan_conversation')
    def test_normal_read_locks_and_uri_no_immutable(self):
        original=sqlite3.connect;calls=[]
        def observed(*a,**k):calls.append((a,k));return original(*a,**k)
        with patch.object(p.sqlite3,'connect',side_effect=observed):self.read()
        self.assertEqual(len(calls),1);self.assertTrue(calls[0][0][0].endswith('?mode=ro'));self.assertEqual(calls[0][1]['timeout'],0)
        self.assertNotIn('immutable',calls[0][0][0]);self.assertNotIn('nolock',calls[0][0][0])
    def test_readonly_policy_is_required_not_imposed_on_callers(self):
        c=sqlite3.connect(self.path)
        try:
            with self.assertRaisesRegex(p.ResponsePreopenRejected,'readonly_policy'):p.verify_response_connection(c,self.expected)
            self.assertEqual(c.execute('PRAGMA query_only').fetchone()[0],0)
        finally:c.close()
    def test_helper_query_function_does_not_close_connection(self):
        c=sqlite3.connect(self.path.as_uri()+'?mode=ro',uri=True)
        try:
            c.execute('PRAGMA query_only=ON');c.execute('PRAGMA trusted_schema=OFF');p.verify_response_connection(c,self.expected)
            self.assertEqual(c.execute('SELECT 1').fetchone()[0],1)
        finally:c.close()
    def test_active_transaction_refused_without_rollback(self):
        c=sqlite3.connect(self.path.as_uri()+'?mode=ro',uri=True)
        try:
            c.execute('PRAGMA query_only=ON');c.execute('PRAGMA trusted_schema=OFF');c.execute('BEGIN')
            with self.assertRaisesRegex(p.ResponsePreopenRejected,'readonly_connection'):p.verify_response_connection(c,self.expected)
            self.assertTrue(c.in_transaction)
        finally:c.close()
    def test_sql_budget_failure_not_partial_success(self):
        c=sqlite3.connect(self.path);c.executemany('INSERT INTO responses VALUES(?,?,?)',[(str(i),'{}',1) for i in range(100)]);c.commit();c.close()
        with patch.object(p.cold,'MAX_SQL_STEPS',0),patch.object(p.cold,'SQL_SECONDS',-1),self.assertRaises(sqlite3.Error):self.read()
    def test_corrupt_database_not_repaired(self):
        self.path.write_bytes(b'broken'*100)
        with self.assertRaises(sqlite3.Error):self.read()
    def test_sidecars_always_refused_without_cleanup(self):
        for n in (*p.cold.FILES,p.FILENAME):
            for suffix in p.cold.SUFFIXES:
                f=self.home/(n+suffix);f.touch()
                with self.subTest(name=f.name),self.assertRaises((p.ResponsePreopenRejected,p.cold.PreopenRejected)):p._no_sidecars(self.home)
                self.assertTrue(f.exists());f.unlink()

class ExpectedContract(unittest.TestCase):
    def valid(self):return p.PreparedResponseExpectation(p.NATIVE_FEATURE,p.SCHEMA_SHA256,(1,3))
    def test_exact_pinned_contract_immutable(self):
        x=self.valid()
        with self.assertRaises(FrozenInstanceError):x.max_size=101
        self.assertEqual(p._expected(json.loads(json.dumps(asdict(x)))),x)
    def test_wrong_pin_schema_limits_or_identity(self):
        for values in ({'native_feature':'f'*40},{'schema_sha256':'f'*64},{'response_identity':[1,3]}, {'response_identity':(True,3)},{'response_identity':(1,0)},{'max_size':True},{'max_size':101},{'max_identities':10}):
            with self.subTest(values=values),self.assertRaises(p.ResponsePreopenRejected):replace(self.valid(),**values)
    def test_expectation_extra_field_rejected(self):
        obj=json.loads(json.dumps(asdict(self.valid())))
        with self.assertRaises(p.ResponsePreopenRejected):p._expected(obj|{'unsafe':True})
    def test_separate_response_inode_and_same_device(self):
        canonical=p.live.PreparedStoreExpectation(p.live.NATIVE_PIN,'a'*64,'b'*64,'12345678-1234-4234-8234-123456789012',123,(1,1),(1,2),0,None)
        p._pair(self.valid(),canonical)
        for identity in ((1,1),(1,2),(2,3)):
            with self.assertRaisesRegex(p.ResponsePreopenRejected,'distinct_store'):p._pair(replace(self.valid(),response_identity=identity),canonical)

class ParentContract(unittest.TestCase):
    def setUp(self):
        self.stack=ExitStack();self.addCleanup(self.stack.close)
        self.held=p.live.profiles.ProfileLease.__new__(p.live.profiles.ProfileLease)
        self.held._home=Path('/owned/profile');self.held._actor=(123,23001,23003,1)
        self.check=self.stack.enter_context(patch.object(p.live.profiles.ProfileLease,'check',return_value={}))
        self.stack.enter_context(patch.object(p.live.profiles,'_actor',return_value=self.held._actor))
        self.snapshot=self.stack.enter_context(patch.object(p,'_parent_snapshot',return_value=('stable',)))
        self.expected=p.PreparedResponseExpectation(p.NATIVE_FEATURE,p.SCHEMA_SHA256,(1,3))
        self.canonical=p.live.PreparedStoreExpectation(p.live.NATIVE_PIN,'a'*64,'b'*64,'12345678-1234-4234-8234-123456789012',123,(1,1),(1,2),0,None)
        self.mount=p.live.mounts.ExpectedMount(1,(7,0),'/profile','/owned/profile','ext4')
        self.proc=MagicMock();self.proc.pid=456;self.proc.returncode=0;self.proc.poll.return_value=0
        def completed(raw,timeout):
            r={'state':'COLD_RESPONSE_PREFLIGHT_VERIFIED','workerPid':456,'parentPid':123,'uid':23001,
               'nativeFeature':p.NATIVE_FEATURE,'schemaSha256':p.SCHEMA_SHA256,'responseIdentity':[1,3],
               'constructorLimits':{'max_size':100,'max_identities':1000},'requestSha256':hashlib.sha256(raw).hexdigest(),
               'contentAndMetadataUnchanged':True,'normalSqliteLocks':True,'fileSha256':'c'*64}
            r.update({k:False for k in ('sqlWritesPerformed','nativeConstructorsInvoked','sidecarRecoveryPerformed','runtimeAdmissionAuthorized','fullD3BAccepted','knownConstructorMutationNeeded','canonicalOutcomeEquivalenceVerified')})
            return json.dumps(r).encode(),b''
        self.proc.communicate.side_effect=completed
        self.spawn=self.stack.enter_context(patch.object(p.subprocess,'Popen',return_value=self.proc))
    def call(self,**kwargs):return p.verify_response_preopen(self.held,self.mount,self.expected,self.canonical,**kwargs)
    def test_fixed_process_and_bound_response(self):
        self.assertEqual(self.call()['workerPid'],456)
        args=self.spawn.call_args;self.assertEqual(args.args[0],[sys.executable,'-I','-B',str(p.ROOT/'scripts/run_response_preopen.py')]);self.assertTrue(args.kwargs['close_fds'])
        self.assertEqual(set(args.kwargs['env']),{'PATH','HOME','LANG'});self.assertEqual(self.check.call_count,2)
    def test_wrong_lease_no_spawn(self):
        with self.assertRaises(p.ResponsePreopenRejected):p.verify_response_preopen({},self.mount,self.expected,self.canonical)
        self.spawn.assert_not_called()
    def test_unknown_timeout_no_spawn(self):
        for value in (True,0,31,float('nan'),float('inf')):
            with self.assertRaises(p.ResponsePreopenRejected):self.call(timeout_seconds=value)
        self.spawn.assert_not_called()
    def test_child_refusal_is_bounded(self):
        self.proc.returncode=2;self.proc.communicate.side_effect=lambda *a,**k:(b'{"reason":"response_preopen_unsettled_identity"}',b'')
        with self.assertRaisesRegex(p.ResponsePreopenRejected,'^response_preopen_unsettled_identity$'):self.call()
    def test_child_private_diagnostic_not_echoed(self):
        self.proc.returncode=2;self.proc.communicate.side_effect=lambda *a,**k:(b'{"reason":"/private/path"}',b'')
        with self.assertRaisesRegex(p.ResponsePreopenRejected,'^response_preopen_worker_failed$'):self.call()
    def test_forged_worker_pid_rejected(self):
        orig=self.proc.communicate.side_effect
        def changed(*a,**k):raw,err=orig(*a,**k);r=json.loads(raw);r['workerPid']=1;return json.dumps(r).encode(),err
        self.proc.communicate.side_effect=changed
        with self.assertRaisesRegex(p.ResponsePreopenRejected,'worker_binding'):self.call()
    def test_changed_metadata_not_accepted(self):
        self.snapshot.side_effect=[('before',),('after',)]
        with self.assertRaisesRegex(p.ResponsePreopenRejected,'parent_changed'):self.call()
    def test_timeout_kills_and_reaps_only_child(self):
        self.proc.communicate.side_effect=[subprocess.TimeoutExpired('fixed',1),(b'',b'')]
        with self.assertRaisesRegex(p.ResponsePreopenRejected,'worker_timeout'):self.call()
        self.proc.kill.assert_called_once();self.assertEqual(self.proc.communicate.call_count,2)

if __name__=='__main__':unittest.main()
