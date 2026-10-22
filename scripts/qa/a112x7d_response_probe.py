"""Real native ResponseStore borrowed-state acceptance in owned temporary homes.

No listener/provider, no native class or factory replacement. Direct owned SQL
corruption and one deliberately substituted handle are explicit fault fixtures.
This is a narrow harness acceptance, not the upstream full pytest suite.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import threading
import unittest

BASE=None
State=Responses=Runtime=Ownership=BindingError=None
WATCH=None


def audit(event,args):
    if event in ('socket.connect','socket.bind','socket.getaddrinfo','subprocess.Popen','os.system'):
        raise PermissionError('a112x7d_offline_acceptance')
    if WATCH is not None and event=='sqlite3.connect':WATCH.append(str(args[0]))


class BorrowedResponseCases(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='profile-',dir=BASE)
        self.addCleanup(self.temp.cleanup);self.home=Path(self.temp.name).resolve()
        self.old_home=os.environ.get('HERMES_HOME');os.environ['HERMES_HOME']=str(self.home)
        self.addCleanup(self.restore_home)
        Ownership.reserve([self.home]);self.addCleanup(Ownership.close)
        self.state=State(self.home/'state.db');self.addCleanup(self.state.close)
        self.epoch=Runtime.begin_runtime_epoch(self.state,instance_id='owned-a112x7d')
        self.state.create_session('session','api')
        self.responses=[]
        self.addCleanup(lambda:[r.close() for r in reversed(self.responses)])
    def restore_home(self):
        if self.old_home is None:os.environ.pop('HERMES_HOME',None)
        else:os.environ['HERMES_HOME']=self.old_home
    def make(self,borrow=True,path=None):
        kwargs={'canonical_state':self.state} if borrow else {}
        value=Responses(db_path=str(path or self.home/'response_store.db'),**kwargs)
        self.responses.append(value);return value
    def pending(self,response,*,request='request',key='idem:owned',status='queued'):
        row=Runtime.admit_session_input(self.state,epoch=self.epoch,principal_id='owned',
            session_id='session',request_id=request,payload={'text':'offline owned fixture'})
        if status in ('started','terminal','unknown'):
            row=Runtime.claim_session_input(self.state,epoch=self.epoch,session_id='session')
        if status=='terminal':
            row=Runtime.settle_session_input(self.state,epoch=self.epoch,admission_id=row['admission_id'],
                generation=row['generation'],outcome='completed')
        elif status=='unknown':
            epoch=Runtime.begin_runtime_epoch(self.state,instance_id='owned-a112x7d-next')
            self.assertEqual(Runtime.recover_session_inputs(self.state,epoch=epoch),1)
        self.assertTrue(response.bind_request_key(key,'a'*64,model='fixture-only'))
        response.bind_request_admission(key,row['admission_id']);return row
    def settlement(self,r):
        global WATCH
        connects=[];WATCH=connects
        before=self.state._conn.total_changes
        try:r._settle_terminal_admissions()
        finally:WATCH=None
        self.assertEqual(self.state._conn.total_changes,before)
        return connects
    def settled(self,r,key='idem:owned'):
        return r._conn.execute('SELECT settled_at FROM response_keys WHERE request_key=?',(key,)).fetchone()[0]
    def test_borrowed_constructor_opens_only_response_file(self):
        global WATCH
        connects=[];WATCH=connects
        try:r=self.make()
        finally:WATCH=None
        self.assertEqual(connects,[str(self.home/'response_store.db')])
        self.assertIs(r._canonical_state._state,self.state)
        self.assertIs(r._canonical_state._connection,self.state._conn)
    def test_terminal_admission_settles_without_second_state_connection(self):
        r=self.make();self.pending(r,status='terminal')
        self.assertEqual(self.settlement(r),[]);self.assertIsNotNone(self.settled(r))
        self.assertFalse(self.state._conn.in_transaction)
    def test_queued_identity_stays_unsettled(self):
        r=self.make();row=self.pending(r)
        self.assertEqual(self.settlement(r),[]);self.assertIsNone(self.settled(r))
        self.assertEqual(Runtime.get_session_admission(self.state,admission_id=row['admission_id'])['status'],'queued')
    def test_started_identity_stays_unsettled(self):
        r=self.make();row=self.pending(r,status='started')
        self.assertEqual(self.settlement(r),[]);self.assertIsNone(self.settled(r))
        self.assertEqual(Runtime.get_session_admission(self.state,admission_id=row['admission_id'])['status'],'started')
    def test_unknown_identity_does_not_become_retryable(self):
        r=self.make();row=self.pending(r,status='unknown')
        self.assertEqual(self.settlement(r),[]);self.assertIsNone(self.settled(r))
        self.assertEqual(Runtime.get_session_admission(self.state,admission_id=row['admission_id'])['status'],'unknown')
    def test_canonical_tombstone_settles_without_reopening(self):
        from hermes_state_terminal import ADMISSION_PREFIX
        r=self.make();self.assertTrue(r.bind_request_key('idem:owned','a'*64));r.bind_request_admission('idem:owned','a'*32)
        self.state._conn.execute('INSERT INTO main.state_meta(key,value) VALUES(?,?)',(ADMISSION_PREFIX+'a'*32,'{}'));self.state._conn.commit()
        self.assertEqual(self.settlement(r),[]);self.assertIsNotNone(self.settled(r))
    def test_state_sqlite_lock_remains_on_same_live_connection(self):
        r=self.make();self.pending(r,status='terminal')
        conn=self.state._conn;self.assertEqual(conn.execute('PRAGMA locking_mode=EXCLUSIVE').fetchone()[0],'exclusive')
        conn.execute('BEGIN EXCLUSIVE');conn.execute('COMMIT')
        self.assertEqual(self.settlement(r),[]);self.assertIs(self.state._conn,conn)
        self.assertEqual(conn.execute('PRAGMA locking_mode').fetchone()[0],'exclusive')
    def test_default_mode_keeps_native_separate_reader_behavior(self):
        r=self.make(borrow=False);self.pending(r,status='terminal')
        calls=self.settlement(r);self.assertEqual(len(calls),1);self.assertIn('state.db',calls[0]);self.assertIsNotNone(self.settled(r))
    def test_close_never_closes_caller_state_or_profile(self):
        r=self.make();r.close();self.assertEqual(self.state._conn.execute('SELECT 1').fetchone()[0],1)
        self.assertTrue(Ownership.owns(self.home))
        self.assertEqual(Runtime.begin_runtime_epoch(self.state,instance_id='still-owned'),self.epoch+1)
    def test_request_identity_conflict_behavior_retained(self):
        r=self.make();self.assertTrue(r.bind_request_key('idem:key','a'*64))
        self.assertFalse(r.bind_request_key('idem:key','b'*64));self.assertTrue(r.request_key_matches('idem:key','a'*64))
    def test_response_body_and_conversation_behavior_retained(self):
        r=self.make();r.put('resp_owned',{'output':'dummy fixture'})
        self.assertEqual(r.get('resp_owned'),{'output':'dummy fixture'})
        r.set_conversation('owned','resp_owned');self.assertEqual(r.get_conversation('owned'),'resp_owned')
        self.assertTrue(r.delete('resp_owned'));self.assertIsNone(r.get('resp_owned'))
    def test_active_canonical_transaction_refused_not_rolled_back(self):
        r=self.make();self.pending(r,status='terminal');self.state._conn.execute('BEGIN IMMEDIATE')
        try:
            with self.assertRaisesRegex(BindingError,'response_canonical_transaction_active'):self.settlement(r)
            self.assertTrue(self.state._conn.in_transaction);self.assertIsNone(self.settled(r))
        finally:self.state._conn.rollback()
    def test_closed_canonical_connection_is_not_reopened(self):
        global WATCH
        r=self.make();self.pending(r,status='terminal');self.state.close();calls=[];WATCH=calls
        try:
            with self.assertRaises(BindingError):r._settle_terminal_admissions()
        finally:WATCH=None
        self.assertEqual(calls,[]);self.assertIsNone(self.settled(r))
    def test_substituted_handle_does_not_get_adopted(self):
        r=self.make();self.pending(r,status='terminal');old=self.state._conn;other=sqlite3.connect(':memory:')
        self.state._conn=other
        try:
            with self.assertRaisesRegex(BindingError,'response_canonical_connection_changed'):r._settle_terminal_admissions()
            self.assertIs(self.state._conn,other)
        finally:self.state._conn=old;other.close()
    def test_busy_native_mutex_stays_owned_by_caller(self):
        r=self.make();self.pending(r,status='terminal');self.state._lock.acquire()
        try:
            with self.assertRaisesRegex(BindingError,'response_canonical_busy'):r._settle_terminal_admissions()
            self.assertTrue(self.state._lock.locked())
        finally:self.state._lock.release()
    def test_other_thread_cannot_borrow_binding(self):
        r=self.make();self.pending(r,status='terminal');result=[]
        def child():
            try:r._settle_terminal_admissions()
            except BindingError as exc:result.append(str(exc))
        t=threading.Thread(target=child);t.start();t.join(5)
        self.assertFalse(t.is_alive());self.assertEqual(result,['response_canonical_other_actor'])
    def test_foreign_home_refused_before_response_file_open(self):
        home=self.home/'other';home.mkdir();path=home/'response_store.db'
        with self.assertRaisesRegex(BindingError,'response_canonical_profile_mismatch'):self.make(path=path)
        self.assertFalse(path.exists())
    def test_memory_response_rejected_before_creation(self):
        with self.assertRaisesRegex(BindingError,'response_canonical_disk_required'):Responses(db_path=':memory:',canonical_state=self.state)
    def test_implicit_response_path_not_accepted_as_prepared(self):
        with self.assertRaisesRegex(BindingError,'response_canonical_disk_required'):Responses(canonical_state=self.state)
        self.assertFalse((self.home/'response_store.db').exists())
    def test_fake_native_state_rejected(self):
        with self.assertRaisesRegex(BindingError,'response_canonical_native_state'):Responses(db_path=str(self.home/'response_store.db'),canonical_state=object())
    def test_response_open_failure_has_no_memory_fallback(self):
        path=self.home/'response_store.db';path.mkdir()
        with self.assertRaisesRegex(BindingError,'response_store_disk_open_failed'):self.make()
        self.assertTrue(path.is_dir())
    def test_temp_table_cannot_fabricate_terminal_state(self):
        r=self.make();row=self.pending(r)
        self.state._conn.execute('CREATE TEMP TABLE session_admissions(admission_id TEXT,status TEXT)')
        self.state._conn.execute('INSERT INTO temp.session_admissions VALUES(?,?)',(row['admission_id'],'terminal'))
        self.state._conn.execute('CREATE TEMP TABLE state_meta(key TEXT,value TEXT)');self.state._conn.commit()
        self.assertEqual(self.settlement(r),[]);self.assertIsNone(self.settled(r))
    def test_changed_application_generation_refused(self):
        r=self.make();self.pending(r,status='terminal');old=self.state._conn.execute('PRAGMA application_id').fetchone()[0]
        self.state._conn.execute('PRAGMA application_id=7')
        try:
            with self.assertRaisesRegex(BindingError,'response_canonical_generation_changed'):r._settle_terminal_admissions()
        finally:self.state._conn.execute('PRAGMA application_id='+str(old))
    def test_reopened_response_store_borrows_same_state(self):
        r=self.make();self.pending(r,status='terminal');r.close()
        r2=self.make();self.assertIsNotNone(self.settled(r2));self.assertIs(r2._canonical_state._connection,self.state._conn)


def main():
    global BASE,State,Responses,Runtime,Ownership,BindingError
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();native=args.source.resolve(strict=True);output=args.output.resolve();output.mkdir(exist_ok=False,parents=True)
    with tempfile.TemporaryDirectory(prefix='alaz-a112x7d-run-') as tmp:
        BASE=Path(tmp);home=BASE/'import-home';home.mkdir()
        os.environ.update(HERMES_HOME=str(home),HOME=str(BASE),USERPROFILE=str(BASE))
        sys.path.insert(0,str(native));sys.addaudithook(audit)
        from hermes_state import SessionDB
        from gateway.platforms.api_server_response_store import ResponseStore
        from gateway.platforms.api_server_response_state import CanonicalStateUnavailable
        from gateway.runtime_ownership import process_ownership
        import hermes_state_runtime
        State,Responses,Runtime,Ownership,BindingError=SessionDB,ResponseStore,hermes_state_runtime,process_ownership,CanonicalStateUnavailable
        suite=unittest.defaultTestLoader.loadTestsFromTestCase(BorrowedResponseCases)
        with (output/'tests.txt').open('x',encoding='utf-8',newline='\n') as stream:result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
        imported={}
        for m in tuple(sys.modules.values()):
            name=getattr(m,'__file__',None)
            if name:
                path=Path(name).resolve()
                if path.is_relative_to(native) and path.suffix=='.py':imported[path.relative_to(native).as_posix()]=hashlib.sha256(path.read_bytes()).hexdigest()
        report={'result':'PASS_SCOPED_NATIVE_RESPONSE_BORROW' if result.wasSuccessful() else 'FAIL','total':result.testsRun,'passed':result.testsRun-len({t.id() for t,_ in result.failures+result.errors})-len(result.skipped),'failures':len(result.failures),'errors':len(result.errors),'skipped':len(result.skipped),'failureIds':[t.id() for t,_ in result.failures],'errorIds':[t.id() for t,_ in result.errors],'nativeSources':imported,'qaSha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'nativeMethodsReplaced':False,'profileOwnerReleased':not Ownership.homes,'httpAdapterStarted':False,'fullIsolationTested':False,'healthyBusyHttpPolicyImplemented':False,'providerCalls':0,'nativeFullSuiteRun':False}
    report['temporaryProfilesRemoved']=not BASE.exists()
    (output/'result.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report),flush=True)
    if not result.wasSuccessful():print((output/'tests.txt').read_text(encoding='utf-8')[-12000:],flush=True)
    return 0 if result.wasSuccessful() and report['temporaryProfilesRemoved'] else 1

if __name__=='__main__':raise SystemExit(main())
