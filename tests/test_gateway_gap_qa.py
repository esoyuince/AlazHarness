"""Offline validator and read-only reader tests; not additional Gateway executions."""
from __future__ import annotations
import copy
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from gateway_gap_contract import validate_gap
from run_gateway_gap_qa import read_state


def fixture():
    return json.loads((ROOT/'evidence/hyb-004-qa/gap-initial-observation.json').read_text(encoding='utf-8'))


class GapEvidenceTests(unittest.TestCase):
    def test_complete_characterization_not_product_acceptance(self):
        data=fixture();self.assertEqual(validate_gap(data),[]);self.assertIs(data['product_recovery_accepted'],False)
    def test_new_projection_preserves_orphan_without_legacy_success_flag(self):
        data=fixture();data['client']['observed'].update(recoveryContractVersion=1,classification='terminal_unverified',
            backendConfirmed=False,requiresOperator=True,transportConfirmed=True,canonicalVerified=False,retryAllowed=False,repairAllowed=False)
        self.assertEqual(validate_gap(data),[])
    def test_new_projection_rejects_unsafe_legacy_flag(self):
        data=fixture();data['client']['observed']['recoveryContractVersion']=1;self.assertTrue(validate_gap(data))
    def test_unknown_projection_version_rejected(self):
        data=fixture();data['client']['observed']['recoveryContractVersion']=2;self.assertTrue(validate_gap(data))
    def test_nonobject_rejected(self):self.assertTrue(validate_gap([]))
    def test_missing_recovery_rejected(self):
        data=fixture();del data['after_recovery'];self.assertTrue(validate_gap(data))
    def test_missing_reservation_rejected(self):
        data=fixture();data['after_crash']['reservations']=[];self.assertTrue(validate_gap(data))
    def test_duplicate_reservation_rejected(self):
        data=fixture();data['barrier']['reservations']*=2;self.assertTrue(validate_gap(data))
    def test_unexpected_admission_rejected(self):
        data=fixture();data['after_recovery']['admissions']=[{'request_id':'other'}];self.assertTrue(validate_gap(data))
    def test_bool_counter_is_not_zero(self):
        data=fixture();data['after_recovery']['messages']=False;self.assertTrue(validate_gap(data))
    def test_unreaped_original_rejected(self):
        data=fixture();data['first_exit']['native_reaped']=False;self.assertTrue(validate_gap(data))
    def test_unreaped_recovery_rejected(self):
        data=fixture();data['second_exit']['launcher_reaped']=False;self.assertTrue(validate_gap(data))
    def test_graceful_shutdown_not_crash(self):
        data=fixture();data['first_exit']['exit_code']=0;self.assertTrue(validate_gap(data))
    def test_same_epoch_rejected(self):
        data=fixture();data['second_ready']['epoch']=data['first_ready']['epoch'];self.assertTrue(validate_gap(data))
    def test_same_instance_rejected(self):
        data=fixture();data['second_ready']['instance_id']=data['first_ready']['instance_id'];self.assertTrue(validate_gap(data))
    def test_wrong_process_nonce_rejected(self):
        data=fixture();data['second_exit']['nonce']='0'*32;self.assertTrue(validate_gap(data))
    def test_unowned_chain_rejected(self):
        data=fixture();data['first_exit']['ownership_chain']=[123];self.assertTrue(validate_gap(data))
    def test_acknowledged_request_different_window(self):
        data=fixture();data['first_request']['http_status']=202;self.assertTrue(validate_gap(data))
    def test_output_success_is_not_this_gap(self):
        data=fixture();data['client']['status']['status']='completed';self.assertTrue(validate_gap(data))
    def test_wrong_replay_identity_rejected(self):
        data=fixture();data['client']['replay']['run_id']='run_'+'a'*32;self.assertTrue(validate_gap(data))
    def test_changed_fingerprint_rejected(self):
        data=fixture();data['after_recovery']['reservations'][0]['fingerprint']='a'*64;self.assertTrue(validate_gap(data))
    def test_bool_model_count_rejected(self):
        data=fixture();data['model_requests']=False;self.assertTrue(validate_gap(data))
    def test_actual_model_request_rejected(self):
        data=fixture();data['model_requests']=1;self.assertTrue(validate_gap(data))
    def test_fake_product_claim_rejected(self):
        data=fixture();data['product_recovery_accepted']=True;self.assertTrue(validate_gap(data))
    def test_source_drift_rejected(self):
        data=fixture();data['source_or_program_drift']=True;self.assertTrue(validate_gap(data))
    def test_no_shutdown_proof_rejected(self):
        data=fixture();data['second_exit']['shutdown']=None;self.assertTrue(validate_gap(data))
    def test_changed_profile_rejected(self):
        data=fixture();data['profile_config_unchanged']=False;self.assertTrue(validate_gap(data))
    def test_malformed_status_json_rejected(self):
        data=fixture();data['after_crash']['reservations'][0]['status_json']='broken';self.assertTrue(validate_gap(data))


class GapReadOnlyTests(unittest.TestCase):
    def test_missing_database_not_created(self):
        with tempfile.TemporaryDirectory() as tmp:
            home=Path(tmp)
            with self.assertRaises(sqlite3.OperationalError):read_state(home)
            self.assertFalse((home/'state.db').exists())
            self.assertFalse((home/'runs_idempotency.db').exists())
    def test_both_readers_explicitly_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            home=Path(tmp)
            one=sqlite3.connect(home/'state.db')
            try:
                one.execute('CREATE TABLE session_admissions(seq INTEGER,admission_id TEXT,request_id TEXT,target_session_id TEXT,status TEXT,outcome TEXT,generation INTEGER,owner_epoch INTEGER)')
                one.execute('CREATE TABLE messages(id INTEGER)');one.commit()
            finally:one.close()
            two=sqlite3.connect(home/'runs_idempotency.db')
            try:
                two.execute('CREATE TABLE run_idempotency(run_id TEXT,status_json TEXT,owner_pid INTEGER,owner_started INTEGER,fingerprint TEXT)');two.commit()
            finally:two.close()
            original=sqlite3.connect;connections=[]
            def capture(*args,**kwargs):
                self.assertIn('?mode=ro',args[0]);self.assertIs(kwargs['uri'],True)
                conn=original(*args,**kwargs);connections.append(conn);return conn
            with patch('run_gateway_gap_qa.sqlite3.connect',capture):data=read_state(home)
            self.assertEqual(data['messages'],0);self.assertEqual(len(connections),2)
            for conn in connections:
                with self.assertRaises(sqlite3.ProgrammingError):conn.execute('SELECT 1')

if __name__=='__main__':unittest.main()
