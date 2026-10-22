"""Read-only real SQLite tests; Linux/lease boundaries are explicit unit doubles."""
from dataclasses import asdict,replace
from contextlib import ExitStack
import hashlib,json,os
from pathlib import Path
import sqlite3,stat,subprocess,sys,tempfile,unittest
from types import SimpleNamespace
from unittest.mock import patch,MagicMock
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'packages/claw-hermes'))
import gateway_store_preopen as p

class ReadOnlyChecks(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory(prefix='preopen-unit-');self.addCleanup(tmp.cleanup)
        self.home=Path(tmp.name).resolve();self.state=self.home/'state.db';self.replay=self.home/'runs_idempotency.db'
        c=sqlite3.connect(self.state)
        c.executescript("PRAGMA application_id=123; CREATE TABLE schema_version(version INTEGER);INSERT INTO schema_version VALUES(31); CREATE TABLE state_meta(key TEXT PRIMARY KEY,value TEXT);CREATE TABLE runtime_epoch(singleton INTEGER PRIMARY KEY,epoch INTEGER,instance_id TEXT);")
        c.executemany('INSERT INTO state_meta VALUES(?,?)',[('store_instance_id','12345678-1234-4234-8234-123456789012'),('message_uid_backfill','1')]);c.commit()
        state_digest=p.live.schema_digest(c);c.close()
        c=sqlite3.connect(self.replay);c.execute('CREATE TABLE run_idempotency(status_json TEXT)');c.commit();replay_digest=p.live.schema_digest(c);c.close()
        self.expected=p.live.PreparedStoreExpectation(p.live.NATIVE_PIN,state_digest,replay_digest,'12345678-1234-4234-8234-123456789012',123,
            (self.state.stat().st_dev,self.state.stat().st_ino),(self.replay.stat().st_dev,self.replay.stat().st_ino),0,None)
    def read(self):return p._readonly(self.state,self.expected.state_schema_sha256,self.expected,state=True)
    def change(self,sql,args=()):
        c=sqlite3.connect(self.state);c.execute(sql,args);c.commit();c.close()
    def test_valid_state_and_replay_never_write_or_create_sidecars(self):
        before={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in self.home.iterdir()}
        r=self.read();self.assertEqual(r['state'],'KNOWN_CONSTRUCTOR_REPAIR_MARKERS_CLEAR')
        self.assertIsNone(p._readonly(self.replay,self.expected.replay_schema_sha256,self.expected,state=False))
        self.assertEqual(before,{f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in self.home.iterdir()})
    def test_missing_file_not_created(self):
        with self.assertRaises(sqlite3.Error):p._readonly(self.home/'absent.db','f'*64,self.expected,state=False)
        self.assertFalse((self.home/'absent.db').exists())
    def test_wrong_schema_digest(self):
        with self.assertRaisesRegex(p.PreopenRejected,'schema_mismatch'):p._readonly(self.state,'f'*64,self.expected,state=True)
    def test_schema_changed(self):
        self.change('CREATE TABLE extra(value)')
        with self.assertRaisesRegex(p.PreopenRejected,'schema_mismatch'):self.read()
    def test_old_version_not_migrated(self):
        self.change('UPDATE schema_version SET version=30');before=self.state.read_bytes()
        with self.assertRaisesRegex(p.PreopenRejected,'schema_version'):self.read()
        self.assertEqual(before,self.state.read_bytes())
    def test_uuid_mismatch(self):
        self.change("UPDATE state_meta SET value='different' WHERE key='store_instance_id'")
        with self.assertRaisesRegex(p.PreopenRejected,'store_instance'):self.read()
    def test_application_mismatch(self):
        self.change('PRAGMA application_id=124')
        with self.assertRaisesRegex(p.PreopenRejected,'application_id'):self.read()
    def test_epoch_mismatch_no_advance(self):
        self.change("INSERT INTO runtime_epoch VALUES(1,1,'existing')");before=self.state.read_bytes()
        with self.assertRaisesRegex(p.PreopenRejected,'epoch'):self.read()
        self.assertEqual(before,self.state.read_bytes())
    def test_existing_epoch_exact(self):
        self.change("INSERT INTO runtime_epoch VALUES(1,1,'existing')")
        expected=replace(self.expected,epoch=1,instance_id='existing')
        self.assertEqual(p._readonly(self.state,expected.state_schema_sha256,expected,state=True)['schemaVersion'],31)
    def test_repair_markers_not_erased(self):
        for key in p.metadata.REPAIR_KEYS:
            with self.subTest(key=key):
                self.change('INSERT INTO state_meta VALUES(?,?)',(key,'0'));before=self.state.read_bytes()
                with self.assertRaises(p.metadata.ConstructorMetadataRejected):self.read()
                self.assertEqual(before,self.state.read_bytes());self.change('DELETE FROM state_meta WHERE key=?',(key,))
    def test_missing_backfill_rejected(self):
        self.change("DELETE FROM state_meta WHERE key='message_uid_backfill'")
        with self.assertRaises(p.metadata.ConstructorMetadataRejected):self.read()
    def test_corruption_is_not_repaired(self):
        self.state.write_bytes(b'not a database'*100);before=self.state.read_bytes()
        with self.assertRaises(sqlite3.Error):self.read()
        self.assertEqual(before,self.state.read_bytes())
    def test_sql_budget_is_fail_closed(self):
        with patch.object(p,'MAX_SQL_STEPS',0),patch.object(p,'SQL_SECONDS',-1),self.assertRaises(sqlite3.Error):
            c=sqlite3.connect(self.state);c.executemany('INSERT INTO state_meta VALUES(?,?)',[(str(i),'a') for i in range(4000)]);c.commit();c.close();self.read()
    def test_mode_readonly_no_nolock_immutable(self):
        actual=p.sqlite3.connect;calls=[]
        def opened(*a,**kw):calls.append((a,kw));return actual(*a,**kw)
        with patch.object(p.sqlite3,'connect',side_effect=opened):self.read()
        self.assertTrue(calls[0][0][0].endswith('?mode=ro'));self.assertEqual(calls[0][1]['timeout'],0)
    def test_sidecars_all_refused_even_empty(self):
        for name in p.FILES:
            for suffix in p.SUFFIXES:
                f=self.home/(name+suffix);f.touch()
                with self.subTest(file=f.name),self.assertRaisesRegex(p.PreopenRejected,'recovery_required'):p._no_sidecars(self.home)
                self.assertTrue(f.exists());f.unlink()
    def test_expectation_roundtrip_and_no_other_journal(self):
        obj=json.loads(json.dumps(asdict(self.expected)));self.assertEqual(p._expectation(obj),self.expected)
        with self.assertRaisesRegex(p.PreopenRejected,'cold_delete'):p._expectation(obj|{'journal_mode':'wal'})
    def test_expectation_extra_missing_keys(self):
        obj=json.loads(json.dumps(asdict(self.expected)))
        for bad in (obj|{'extra':1},{k:v for k,v in obj.items() if k!='epoch'}):
            with self.assertRaises(p.PreopenRejected):p._expectation(bad)
    def test_duplicate_json_and_nonfinite_rejected(self):
        for raw in ('{"epoch":0,"epoch":1}','{"epoch":NaN}'):
            with self.assertRaises(p.PreopenRejected):p._json(raw)

class ParentContracts(unittest.TestCase):
    def setUp(self):
        self.stack=ExitStack();self.addCleanup(self.stack.close)
        self.held=p.live.profiles.ProfileLease.__new__(p.live.profiles.ProfileLease)
        self.held._home=Path('/owned/profile');self.held._actor=(123,23001,23003,1)
        self.check=self.stack.enter_context(patch.object(p.live.profiles.ProfileLease,'check',return_value={}))
        self.stack.enter_context(patch.object(p.live.profiles,'_actor',return_value=self.held._actor))
        self.mount=p.live.mounts.ExpectedMount(1,(7,0),'/profile','/owned/profile','ext4')
        self.observe=self.stack.enter_context(patch.object(p.live.mounts,'observe_profile_mounts',return_value={'mountTableSha256':'a'}))
        self.expected=p.live.PreparedStoreExpectation(p.live.NATIVE_PIN,'a'*64,'b'*64,'12345678-1234-4234-8234-123456789012',123,(1,2),(1,3),0,None)
        self.proc=MagicMock();self.proc.pid=456;self.proc.returncode=0;self.proc.poll.return_value=0
        def complete(raw,timeout):
            request=json.loads(raw);reply={'state':'COLD_STORES_PREFLIGHT_VERIFIED','workerPid':456,'parentPid':123,'uid':23001,'requestSha256':hashlib.sha256(raw).hexdigest()}
            reply.update({k:False for k in ('sqlWritesPerformed','nativeConstructorsInvoked','sidecarRecoveryPerformed','runtimeAdmissionAuthorized','fullD3BAccepted')})
            return json.dumps(reply).encode(),b''
        self.proc.communicate.side_effect=complete
        self.spawn=self.stack.enter_context(patch.object(p.subprocess,'Popen',return_value=self.proc))
    def run_it(self,**kwargs):return p.verify_preopen(self.held,self.mount,self.expected,**kwargs)
    def test_fixed_command_no_ambient_handles_or_custom_environment(self):
        r=self.run_it();self.assertEqual(r['workerPid'],456)
        args=self.spawn.call_args;self.assertEqual(args.args[0],[sys.executable,'-I','-B',str(p.ROOT/'scripts/run_store_preopen.py')])
        self.assertIs(args.kwargs['close_fds'],True);self.assertEqual(set(args.kwargs['env']),{'PATH','HOME','LANG'})
        self.assertEqual(self.check.call_count,2);self.assertEqual(self.observe.call_count,2)
    def test_no_lease_no_spawn(self):
        with self.assertRaises(p.PreopenRejected):p.verify_preopen({},self.mount,self.expected)
        self.spawn.assert_not_called()
    def test_bad_mount_no_spawn(self):
        with self.assertRaises(p.PreopenRejected):p.verify_preopen(self.held,{},self.expected)
        self.spawn.assert_not_called()
    def test_no_dynamic_timeout_or_bool(self):
        for value in (True,0,-1,31,float('nan'),float('inf')):
            with self.subTest(value=value),self.assertRaises(p.PreopenRejected):self.run_it(timeout_seconds=value)
        self.spawn.assert_not_called()
    def test_lease_failure_no_spawn(self):
        self.check.side_effect=p.live.profiles.ProfileLeaseRejected('held')
        with self.assertRaises(p.PreopenRejected):self.run_it()
        self.spawn.assert_not_called()
    def test_child_refusal_propagates_bounded_code(self):
        self.proc.returncode=2;self.proc.communicate.side_effect=None;self.proc.communicate.return_value=(b'{"state":"REFUSED","reason":"preopen_schema_mismatch"}',b'')
        with self.assertRaisesRegex(p.PreopenRejected,'^preopen_schema_mismatch$'):self.run_it()
    def test_untrusted_diagnostic_not_echoed(self):
        self.proc.returncode=2;self.proc.communicate.side_effect=None;self.proc.communicate.return_value=(b'{"reason":"/private/path"}',b'')
        with self.assertRaisesRegex(p.PreopenRejected,'^preopen_worker_failed$'):self.run_it()
    def test_stderr_cannot_be_accepted(self):
        self.proc.communicate.side_effect=None;self.proc.communicate.return_value=(b'{}',b'error')
        with self.assertRaisesRegex(p.PreopenRejected,'worker_output'):self.run_it()
    def test_pid_binding_refuses_old_receipt(self):
        original=self.proc.communicate.side_effect
        def wrong(*a,**k):raw,err=original(*a,**k);obj=json.loads(raw);obj['workerPid']=1;return json.dumps(obj).encode(),err
        self.proc.communicate.side_effect=wrong
        with self.assertRaisesRegex(p.PreopenRejected,'worker_binding'):self.run_it()
    def test_mount_change_refuses_result(self):
        self.observe.side_effect=[{'hash':'a'},{'hash':'b'}]
        with self.assertRaisesRegex(p.PreopenRejected,'parent_changed'):self.run_it()
    def test_timeout_kills_and_reaps_only_owned_child(self):
        self.proc.communicate.side_effect=[subprocess.TimeoutExpired('fixed-worker',.1),(b'',b'')]
        with self.assertRaisesRegex(p.PreopenRejected,'worker_timeout'):self.run_it()
        self.proc.kill.assert_called_once();self.assertEqual(self.proc.communicate.call_count,2)

if __name__=='__main__':unittest.main()
