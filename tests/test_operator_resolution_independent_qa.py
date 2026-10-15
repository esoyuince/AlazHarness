"""Independent operator semantics QA on fabricated SQLite stores.

Only native source loading/maintenance ownership are test doubles here. Actual
production prepare/apply/receipt/inspector and real SQLite transactions execute.
The actual lock has its own native acceptance, never inferred from these tests.
"""
from contextlib import closing,contextmanager
import dataclasses
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'packages/claw-hermes'))
import operator_resolution as op
import recovery_inspector as ri
import resolution_receipts as rr
from test_reconciliation_inspector_qa import StoreFixture,RID,AID,TOKEN,NOW,encode

@contextmanager
def no_owner():
    yield SimpleNamespace(_pid_exists=lambda pid:False)

class OperatorIndependentQA(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.home=Path(self.tmp.name);self.f=StoreFixture(self.home)
        self.f.sql('DELETE FROM session_admissions');self.f.sql('DELETE FROM state_meta')
        for statement in ('CREATE TABLE sessions(id TEXT PRIMARY KEY)','CREATE TABLE messages(session_id TEXT,role TEXT,content TEXT)','CREATE TABLE worker_executions(session_id TEXT)'):
            self.f.sql(statement)
        self.f.http={'run_id':RID,'status':'interrupted'}
        self.f.sql('UPDATE run_idempotency SET status_json=?,owner_pid=999999,owner_started=1',(encode(self.f.http),),runs=True)
        self.now=NOW;self.context=ri.LocalRecoveryContext(self.home,TOKEN,2,'owner-two')
        self.service=op.OperatorResolution(self.context,source_root=self.home,clock=lambda:self.now)
        self.addCleanup(patch.stopall)
        patch.object(self.service,'_source',return_value=self.home).start()
        patch.object(self.service,'_maintenance',no_owner).start()
        self.args={'body':self.f.body,'idempotency_key':self.f.key,'observed':self.f.http}
        self.command='c'*32
    def plan(self,**kw):return self.service.prepare(command_id=kw.pop('command_id',self.command),**(self.args|kw))
    def apply(self,plan=None,**kw):
        plan=plan if plan is not None else self.plan()
        return self.service.apply(plan=plan,confirmation=kw.pop('confirmation',plan['confirmationDigest']),**(self.args|kw))
    def rows(self):
        with closing(sqlite3.connect(self.home/'state.db')) as c:return c.execute('SELECT key,value FROM state_meta ORDER BY key').fetchall()
    def refused(self,callback):
        before=self.f.hashes()
        with self.assertRaises(op.ResolutionError) as cm:callback()
        self.assertEqual(before,self.f.hashes());self.assertNotIn(TOKEN,str(cm.exception));self.assertNotIn(self.f.body['input'],str(cm.exception));return str(cm.exception)
    def restore_canonical(self,status='terminal'):
        row=dict(self.f.row,status=status)
        self.f.sql('INSERT INTO session_admissions VALUES('+','.join('?' for _ in row)+')',tuple(row.values()))
    def test_preview_no_native_write_or_secret(self):
        before=self.f.hashes();p=self.plan();self.assertEqual(before,self.f.hashes())
        for value in [TOKEN,self.f.key,self.f.body['input']]:self.assertNotIn(value,json.dumps(p))
        self.assertEqual(p['action'],'abandon_unadmitted')
    def test_apply_only_two_audit_rows(self):
        before=(self.home/'runs_idempotency.db').read_bytes();r=self.apply()
        self.assertEqual(len(self.rows()),2);self.assertEqual((self.home/'runs_idempotency.db').read_bytes(),before)
        self.assertIs(r['requestClosed'],True);self.assertIs(r['taskSucceeded'],False);self.assertIs(r['retryAllowed'],False)
        self.assertIs(r['admissionCreated'],False);self.assertIs(r['reservationDeleted'],False)
    def test_same_confirmation_replays_one_receipt(self):
        p=self.plan();a=self.apply(p);before=self.f.hashes();b=self.apply(p)
        self.assertEqual(a['receipt'],b['receipt']);self.assertEqual(b['status'],'already_recorded');self.assertEqual(before,self.f.hashes())
    def test_replay_after_plan_expiry_is_read_only(self):
        p=self.plan();self.apply(p);self.now+=400
        before=self.f.hashes();r=self.apply(p);self.assertEqual(r['status'],'already_recorded');self.assertEqual(before,self.f.hashes())
    def test_second_command_same_run_refused(self):
        self.apply();self.refused(lambda:self.plan(command_id='d'*32))
    def test_missing_confirmation(self):
        p=self.plan();self.refused(lambda:self.apply(p,confirmation=None))
    def test_wrong_confirmation(self):
        p=self.plan();self.refused(lambda:self.apply(p,confirmation='0'*64))
    def test_unknown_action(self):
        p=self.plan();p['action']='reoffer';p['confirmationDigest']=rr.digest({k:v for k,v in p.items() if k!='confirmationDigest'})
        self.refused(lambda:self.apply(p))
    def test_same_command_changed_body(self):
        p=self.plan();self.apply(p);self.refused(lambda:self.apply(p,body={'input':'different'}))
    def test_modified_preview_snapshot(self):
        p=self.plan();p['snapshotDigest']='f'*64;p['confirmationDigest']=rr.digest({k:v for k,v in p.items() if k!='confirmationDigest'})
        self.refused(lambda:self.apply(p))
    def test_expired_confirmation(self):
        p=self.plan();self.now+=300;self.refused(lambda:self.apply(p))
    def test_future_confirmation(self):
        p=self.plan();self.now-=1;self.refused(lambda:self.apply(p))
    def test_stale_runtime_after_preview(self):
        p=self.plan();self.f.sql('UPDATE runtime_epoch SET epoch=3');self.refused(lambda:self.apply(p))
    def test_new_runtime_instance_same_epoch(self):
        p=self.plan();self.f.sql('UPDATE runtime_epoch SET instance_id=?',('other',));self.refused(lambda:self.apply(p))
    def test_reservation_changed_after_preview(self):
        p=self.plan();self.f.sql('UPDATE run_idempotency SET updated_at=updated_at+1',runs=True);self.refused(lambda:self.apply(p))
    def test_canonical_appears_after_preview(self):
        p=self.plan();self.restore_canonical();self.refused(lambda:self.apply(p))
    def test_unknown_execution_never_closed(self):
        self.restore_canonical('unknown');self.refused(self.plan)
    def test_completed_never_closed(self):
        self.restore_canonical();self.refused(self.plan)
    def test_related_session_refused(self):
        self.f.sql('INSERT INTO sessions VALUES(?)',(RID,));self.refused(self.plan)
    def test_related_history_refused(self):
        self.f.sql('INSERT INTO messages VALUES(?,?,?)',(RID,'tool','effect'));self.refused(self.plan)
    def test_related_worker_refused(self):
        self.f.sql('INSERT INTO worker_executions VALUES(?)',(RID,));self.refused(self.plan)
    def test_terminal_archive_identity_refused(self):
        self.f.archive();self.refused(self.plan)
    def test_retired_row_without_identity_refused(self):
        self.f.sql('INSERT INTO state_meta VALUES(?,?)',(ri.ARCHIVE+AID,encode(self.f.row)))
        self.refused(self.plan)
    def test_missing_second_db_not_recreated(self):
        (self.home/'runs_idempotency.db').unlink();self.refused(self.plan);self.assertFalse((self.home/'runs_idempotency.db').exists())
    def test_deleted_key_not_recreated(self):
        self.f.sql('DELETE FROM run_idempotency',runs=True);self.refused(self.plan)
    def test_expired_retention_not_removed(self):
        self.f.sql('UPDATE run_idempotency SET retention_until=1',runs=True);self.refused(self.plan)
    def test_bad_reservation_json(self):
        self.f.sql('UPDATE run_idempotency SET status_json=?',('[]',),runs=True);self.refused(self.plan)
    def test_trigger_refused_before_audit_write(self):
        self.f.sql('CREATE TRIGGER hidden_effect AFTER INSERT ON state_meta BEGIN INSERT INTO sessions VALUES(NEW.key); END')
        self.refused(self.plan)
    def test_bool_plan_epoch_refused(self):
        p=self.plan();p['epoch']=True;p['confirmationDigest']=rr.digest({k:v for k,v in p.items() if k!='confirmationDigest'})
        self.refused(lambda:self.apply(p))
    def test_explicit_session_not_adopted(self):self.refused(lambda:self.plan(body=self.f.body|{'session_id':RID}))
    def test_live_previous_pid_refused(self):
        p=self.plan()
        @contextmanager
        def live():yield SimpleNamespace(_pid_exists=lambda pid:True)
        with patch.object(self.service,'_maintenance',live):self.refused(lambda:self.apply(p))
    def test_missing_previous_pid_refused(self):
        self.f.sql('UPDATE run_idempotency SET owner_pid=0',runs=True);p=self.plan();self.refused(lambda:self.apply(p))
    def test_closure_inspector_never_says_task_succeeded(self):
        self.apply();r=ri.LocalRecoveryInspector(self.context,clock=lambda:self.now).inspect(**self.args)
        self.assertEqual(r['classification'],'reservation_abandoned_verified');self.assertIs(r['taskSucceeded'],False);self.assertIs(r['retryAllowed'],False)
    def test_tampered_stored_receipt_refused(self):
        p=self.plan();self.apply(p);self.f.sql('UPDATE state_meta SET value=? WHERE key=?',('[]',rr.PREFIX+self.command))
        self.refused(lambda:self.apply(p))
    def test_missing_receipt_index_refused(self):
        p=self.plan();self.apply(p);self.f.sql('DELETE FROM state_meta WHERE key=?',(rr.run_index(self.context.scope,RID),))
        self.refused(lambda:self.apply(p))
    def test_receipt_user_mutation_not_persisted(self):
        p=self.plan();r=self.apply(p);r['receipt']['action']='reoffer';r['retryAllowed']=True
        fresh=self.apply(p);self.assertEqual(fresh['receipt']['action'],'abandon_unadmitted');self.assertIs(fresh['retryAllowed'],False)
    def test_insert_failure_rolls_back_both_receipt_rows(self):
        p=self.plan();original=sqlite3.connect
        class Fail(sqlite3.Connection):
            def execute(self,sql,params=(),/):
                if sql.startswith('INSERT INTO state_meta') and params[0].startswith(rr.INDEX):raise sqlite3.OperationalError('injected second insert failure')
                return super().execute(sql,params)
        with patch('operator_resolution.sqlite3.connect',lambda *a,**kw:original(*a,**kw,factory=Fail)):
            self.refused(lambda:self.apply(p))
        self.assertEqual(self.rows(),[])
    def test_committed_but_ack_lost_is_replayed(self):
        p=self.plan();original=sqlite3.connect
        class Lost(sqlite3.Connection):
            def commit(self):super().commit();raise sqlite3.OperationalError('injected acknowledgement loss')
        with patch('operator_resolution.sqlite3.connect',lambda *a,**kw:original(*a,**kw,factory=Lost)):
            with self.assertRaises(op.ResolutionError) as cm:self.apply(p)
        self.assertEqual(str(cm.exception),'storage_or_commit_unconfirmed');self.assertEqual(len(self.rows()),2)
        before=self.f.hashes();r=self.apply(p);self.assertEqual(r['status'],'already_recorded');self.assertEqual(before,self.f.hashes())
    def test_statement_log_never_updates_replay(self):
        p=self.plan();original=sqlite3.connect;statements=[]
        def spy(*a,**kw):
            c=original(*a,**kw);c.set_trace_callback(statements.append);return c
        with patch('operator_resolution.sqlite3.connect',spy):self.apply(p)
        writes=[s for s in statements if s.lstrip().split()[0].upper() in {'INSERT','UPDATE','DELETE','REPLACE','CREATE','DROP'}]
        self.assertEqual(len(writes),2);self.assertTrue(all(s.startswith('INSERT INTO state_meta') for s in writes))

    def test_canonical_appears_after_closure_replay_refused(self):
        p=self.plan();self.apply(p);self.restore_canonical('unknown')
        self.refused(lambda:self.apply(p))
    def test_index_without_command_receipt_refused(self):
        self.f.sql('INSERT INTO state_meta VALUES(?,?)',(rr.run_index(self.context.scope,RID),encode(self.command)))
        self.refused(self.plan)
    def test_command_identity_reused_for_other_run_refused(self):
        p=self.plan();self.apply(p);rid2='run_'+'d'*32;key2='another-key'
        self.f.sql('INSERT INTO run_idempotency SELECT scope,?,fingerprint,?, ?,owner_pid,owner_started,retention_until,acknowledged_at,created_at,updated_at FROM run_idempotency',(key2,rid2,encode({'run_id':rid2,'status':'interrupted'})),runs=True)
        self.refused(lambda:self.plan(idempotency_key=key2,observed={'run_id':rid2,'status':'interrupted'}))
    def test_bad_receipt_action_even_self_consistent_rejected(self):
        p=self.plan();r=self.apply(p);record=r['receipt'];record['action']='reoffer';record['recordDigest']=rr.digest({k:v for k,v in record.items() if k!='recordDigest'})
        self.f.sql('UPDATE state_meta SET value=? WHERE key=?',(encode(record),rr.PREFIX+self.command))
        self.refused(lambda:self.apply(p))
    def test_new_owner_can_read_prior_receipt_without_write(self):
        p=self.plan();a=self.apply(p);self.f.sql('UPDATE runtime_epoch SET epoch=3,instance_id=?',('new-owner',))
        self.context=dataclasses.replace(self.context,epoch=3,instance_id='new-owner');self.service.context=self.context
        before=self.f.hashes();b=self.apply(p);self.assertEqual(a['receipt'],b['receipt']);self.assertEqual(b['status'],'already_recorded');self.assertEqual(before,self.f.hashes())
    def test_inspector_rejects_canonical_conflict_after_closure(self):
        self.apply();self.restore_canonical('unknown')
        r=ri.LocalRecoveryInspector(self.context,clock=lambda:self.now).inspect(**self.args)
        self.assertEqual(r['classification'],'unverified');self.assertIs(r['canonicalVerified'],False);self.assertIs(r['taskSucceeded'],False)

if __name__=='__main__':unittest.main()
