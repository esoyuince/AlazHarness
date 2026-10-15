"""Offline resolution contracts. Synthetic stores and a test-only ownership substitute."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing,contextmanager
import copy
import dataclasses
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tests/fixtures'))
from operator_resolution_fixture import ResolutionFixture
from operator_resolution import ResolutionError
from resolution_receipts import PREFIX,INDEX,digest

class OperatorResolutionTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.f=ResolutionFixture(self.tmp.name)
    def refusal(self,plan,**kwargs):
        before=self.f.hashes()
        with self.assertRaises(ResolutionError):self.f.apply(plan,**kwargs)
        self.assertEqual(before,self.f.hashes());self.assertFalse(self.f.audit())
    def test_preview_is_readonly_and_does_not_claim_auth(self):
        before=self.f.hashes();p=self.f.prepare();self.assertEqual(before,self.f.hashes());self.assertEqual(self.f.maintenance_entries,0)
        self.assertNotIn(self.f.key,json.dumps(p));self.assertNotIn(self.f.context.api_token,json.dumps(p));self.assertNotIn(self.f.body['input'],json.dumps(p))
    def test_only_audit_and_index_written_not_replay(self):
        p=self.f.prepare();before=self.f.hashes();r=self.f.apply(p)
        self.assertEqual(r['status'],'recorded');self.assertEqual(len(self.f.audit()),2)
        self.assertEqual(before['runs_idempotency.db'],self.f.hashes()['runs_idempotency.db'])
        self.assertFalse(r['taskSucceeded']);self.assertFalse(r['admissionCreated']);self.assertFalse(r['retryAllowed']);self.assertFalse(r['reservationDeleted'])
    def test_inspector_distinguishes_explicit_abandonment(self):
        self.f.apply(self.f.prepare());r=self.f.inspect()
        self.assertEqual(r['classification'],'reservation_abandoned_verified');self.assertTrue(r['resolutionVerified']);self.assertFalse(r['canonicalVerified']);self.assertFalse(r['requiresOperator']);self.assertFalse(r['taskSucceeded'])
    def test_same_confirmation_replay_has_no_write(self):
        p=self.f.prepare();one=self.f.apply(p);before=self.f.hashes();two=self.f.apply(p)
        self.assertEqual(two['status'],'already_recorded');self.assertEqual(one['receipt'],two['receipt']);self.assertEqual(before,self.f.hashes());self.assertFalse(two['writesPerformed'])
    def test_recorded_reply_can_be_recovered_after_plan_expiry(self):
        p=self.f.prepare();one=self.f.apply(p);self.f.now+=301;two=self.f.apply(p);self.assertEqual(one['receipt'],two['receipt'])
    def test_recorded_reply_rechecked_after_new_native_epoch(self):
        p=self.f.prepare();self.f.apply(p);self.f.sql("UPDATE runtime_epoch SET epoch=3,instance_id='third'")
        self.f.context=dataclasses.replace(self.f.context,epoch=3,instance_id='third');self.f.service.context=self.f.context
        self.assertEqual(self.f.apply(p)['status'],'already_recorded');self.assertEqual(self.f.inspect()['classification'],'reservation_abandoned_verified')
    def test_wrong_confirmation(self):self.refusal(self.f.prepare(),confirmation='f'*64)
    def test_missing_confirmation(self):self.refusal(self.f.prepare(),confirmation=None)
    def test_plan_tamper(self):
        p=self.f.prepare();p['snapshotDigest']='f'*64;self.refusal(p)
    def test_unsupported_action_even_rehashed(self):
        p=self.f.prepare();p['action']='retry';p['confirmationDigest']=digest({k:v for k,v in p.items() if k!='confirmationDigest'});self.refusal(p)
    def test_wrong_body(self):self.refusal(self.f.prepare(),body={'input':'other'})
    def test_wrong_key(self):self.refusal(self.f.prepare(),idempotency_key='other-key')
    def test_wrong_run(self):self.refusal(self.f.prepare(),observed={'run_id':'run_'+'b'*32,'status':'interrupted'})
    def test_snapshot_change_before_commit(self):
        p=self.f.prepare();self.f.sql('UPDATE run_idempotency SET updated_at=updated_at+1',replay=True);self.refusal(p)
    def test_expired_confirmation(self):
        p=self.f.prepare();self.f.now+=301;self.refusal(p)
    def test_clock_rollback(self):
        p=self.f.prepare();self.f.now-=1;self.refusal(p)
    def test_stale_epoch(self):
        p=self.f.prepare();self.f.sql('UPDATE runtime_epoch SET epoch=3');self.refusal(p)
    def test_context_epoch_changes_after_preview(self):
        p=self.f.prepare();self.f.sql("UPDATE runtime_epoch SET epoch=3,instance_id='third'")
        self.f.service.context=dataclasses.replace(self.f.context,epoch=3,instance_id='third');self.refusal(p)
    def test_live_old_pid_refused(self):
        p=self.f.prepare();self.f.live_owner=True;self.refusal(p)
    def test_missing_original_owner_refused(self):
        self.f.sql('UPDATE run_idempotency SET owner_pid=0',replay=True);self.refusal(self.f.prepare())
    def test_active_native_maintenance_refusal(self):
        p=self.f.prepare()
        @contextmanager
        def held():raise ResolutionError('gateway_or_maintenance_active');yield
        self.f.service._maintenance=held;self.refusal(p)
    def test_unknown_canonical_work_never_abandoned(self):
        p=self.f.prepare();self.f.sql('INSERT INTO session_admissions VALUES(?,?,?,?)',('b'*32,self.f.run_id,'api',self.f.run_id));self.refusal(p)
    def test_other_principal_record_is_not_absence(self):
        p=self.f.prepare();self.f.sql('INSERT INTO session_admissions VALUES(?,?,?,?)',('b'*32,self.f.run_id,'other',self.f.run_id));self.refusal(p)
    def test_related_session_refused(self):
        p=self.f.prepare();self.f.sql('INSERT INTO sessions VALUES(?)',(self.f.run_id,));self.refusal(p)
    def test_related_history_refused(self):
        p=self.f.prepare();self.f.sql('INSERT INTO messages VALUES(?)',(self.f.run_id,));self.refusal(p)
    def test_related_worker_refused(self):
        p=self.f.prepare();self.f.sql('INSERT INTO worker_executions VALUES(?)',(self.f.run_id,));self.refusal(p)
    def test_closed_request_does_not_prepare_again(self):
        self.f.apply(self.f.prepare())
        with self.assertRaises(ResolutionError):self.f.prepare(command_id='d'*32)
    def test_retention_expired_not_pruned(self):
        p=self.f.prepare();self.f.sql('UPDATE run_idempotency SET retention_until=1',replay=True);self.refusal(p)
    def test_no_store_created_when_missing(self):
        (self.f.home/'runs_idempotency.db').unlink()
        with self.assertRaises(ResolutionError):self.f.prepare()
        self.assertFalse((self.f.home/'runs_idempotency.db').exists())
    def test_explicit_session_target_unsupported(self):
        with self.assertRaises(ResolutionError):self.f.prepare(body=self.f.body|{'session_id':'existing'})
    def test_bad_command_id(self):
        with self.assertRaises(ResolutionError):self.f.prepare(command_id=True)
    def test_refuse_trigger_in_written_table(self):
        p=self.f.prepare();self.f.sql("CREATE TRIGGER surprise AFTER INSERT ON state_meta BEGIN INSERT INTO sessions VALUES('extra'); END");self.refusal(p)
    def test_first_insert_failure_rolls_back(self):
        p=self.f.prepare();original=sqlite3.connect
        class Failing(sqlite3.Connection):
            def execute(self,statement,*args):
                if statement.startswith('INSERT INTO state_meta') and str(args[0][0]).startswith(INDEX):raise sqlite3.OperationalError('synthetic second write failure')
                return super().execute(statement,*args)
        with patch('operator_resolution.sqlite3.connect',lambda *a,**kw:original(*a,**kw,factory=Failing)):self.refusal(p)
    def test_commit_failure_before_publication_rolls_back(self):
        p=self.f.prepare();original=sqlite3.connect
        class Failing(sqlite3.Connection):
            def commit(self):raise sqlite3.OperationalError('synthetic commit failure')
        with patch('operator_resolution.sqlite3.connect',lambda *a,**kw:original(*a,**kw,factory=Failing)):self.refusal(p)
    def test_lost_commit_acknowledgement_recovers_same_receipt(self):
        p=self.f.prepare();original=sqlite3.connect
        class LostAck(sqlite3.Connection):
            def commit(self):super().commit();raise sqlite3.OperationalError('lost commit reply')
        with patch('operator_resolution.sqlite3.connect',lambda *a,**kw:original(*a,**kw,factory=LostAck)):
            with self.assertRaisesRegex(ResolutionError,'storage_or_commit_unconfirmed'):self.f.apply(p)
        self.assertEqual(len(self.f.audit()),2);self.assertEqual(self.f.apply(p)['status'],'already_recorded')
    def test_two_callers_one_receipt(self):
        p=self.f.prepare()
        with ThreadPoolExecutor(max_workers=2) as ex:results=list(ex.map(lambda _:self.f.apply(p),range(2)))
        self.assertEqual(sorted(x['status'] for x in results),['already_recorded','recorded']);self.assertEqual(len(self.f.audit()),2)
    def test_reader_rejects_missing_audit_record(self):
        r=self.f.apply(self.f.prepare());self.f.sql('DELETE FROM state_meta WHERE key=?',(PREFIX+r['receipt']['commandId'],))
        self.assertEqual(self.f.inspect()['classification'],'unverified')
    def test_reader_rejects_modified_audit_digest(self):
        r=self.f.apply(self.f.prepare());record=r['receipt']|{'recordDigest':'f'*64}
        self.f.sql('UPDATE state_meta SET value=? WHERE key=?',(json.dumps(record),PREFIX+record['commandId']))
        self.assertEqual(self.f.inspect()['classification'],'unverified')
    def test_reader_rejects_related_history_after_closure(self):
        self.f.apply(self.f.prepare());self.f.sql('INSERT INTO messages VALUES(?)',(self.f.run_id,));self.assertEqual(self.f.inspect()['classification'],'unverified')

if __name__=='__main__':unittest.main()
