"""Offline validation of crash evidence; these tests do not start a native Gateway."""
from __future__ import annotations
import copy
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from gateway_recovery_contract import validate
from gateway_recovery_support import snapshot
from gateway_recovery_worker import reservation_line

class RecoveryEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.cases=json.loads((ROOT/'tests/fixtures/gateway_recovery_receipts.json').read_text(encoding='utf-8'))['cases']
        self.r=copy.deepcopy(self.cases['completed'])
    def bad(self,mutate):
        mutate(self.r);self.assertTrue(validate(self.r))
    def test_completed_receipt(self):self.assertEqual(validate(self.r),[])
    def test_before_model_quarantine(self):self.assertEqual(validate(self.cases['before-model']),[])
    def test_after_real_tool_quarantine(self):self.assertEqual(validate(self.cases['after-tool']),[])
    def test_pre_reservation_explicit_retry(self):self.assertEqual(validate(self.cases['before-reserve']),[])
    def test_orphan_is_characterization_only(self):self.assertEqual(validate(self.cases['after-reserve']),[])
    def test_missing_evidence(self):self.assertTrue(validate({}))
    def test_unknown_case(self):self.bad(lambda r:r.update(scenario='other'))
    def test_wrong_source(self):self.bad(lambda r:r.update(source_commit='0'*40))
    def test_no_crash(self):self.bad(lambda r:r['first_exit'].update(hard_kill=False))
    def test_boolean_exit_code(self):self.bad(lambda r:r['second_exit'].update(exit_code=False))
    def test_alive_native(self):self.bad(lambda r:r['first_exit'].update(native_reaped=False))
    def test_foreign_ancestry(self):self.bad(lambda r:r['first_exit'].update(chain=[999,888]))
    def test_ancestry_cycle(self):self.bad(lambda r:r['first_exit']['chain'].append(r['first_exit']['chain'][0]))
    def test_old_epoch(self):self.bad(lambda r:r['second_ready'].update(epoch=r['first_ready']['epoch']))
    def test_wrong_nonce(self):self.bad(lambda r:r['second_exit']['shutdown'].update(nonce='0'*32))
    def test_no_final_shutdown(self):self.bad(lambda r:r['second_exit']['shutdown'].update(native_result=False))
    def test_unverified_store(self):self.bad(lambda r:r['after_restart'].update(read_only=False))
    def test_corrupt_store(self):self.bad(lambda r:r['after_restart'].update(integrity='damaged'))
    def test_duplicate_admission(self):self.bad(lambda r:r['after_restart']['admissions'].append(r['after_restart']['admissions'][0]))
    def test_wrong_payload_digest(self):self.bad(lambda r:r['after_restart']['admissions'][0].update(payload_digest='wrong'))
    def test_tool_replayed(self):self.bad(lambda r:r['after_restart'].update(tool_count=2))
    def test_model_replayed(self):self.bad(lambda r:r['model_calls'].append(dict(r['model_calls'][0])))
    def test_marker_in_prompt(self):self.bad(lambda r:r['before_restart'].update(marker_in_user=True))
    def test_final_changed(self):self.bad(lambda r:r['recovered_status']['value'].update(output='invented'))
    def test_missing_conflict(self):self.bad(lambda r:r['conflict'].update(ok=True))
    def test_program_drift(self):self.bad(lambda r:r.update(program_drift=True))
    def test_config_changed(self):self.bad(lambda r:r.update(profile_config_unchanged=False))
    def test_model_inference_not_fixture(self):self.bad(lambda r:r.update(model_inference_calls=1))
    def test_zero_boolean_rejected(self):self.bad(lambda r:r.update(paid_calls=False))
    def test_unknown_not_completed(self):
        r=copy.deepcopy(self.cases['after-tool']);r['resumed']['value']['run']['status']='completed';self.assertTrue(validate(r))
    def test_unknown_must_require_operator(self):
        r=copy.deepcopy(self.cases['before-model']);r['resumed']['value']['requiresOperator']=False;self.assertTrue(validate(r))
    def test_no_invented_orphan_admission(self):
        r=copy.deepcopy(self.cases['after-reserve']);r['after_restart']['admissions']=[self.r['after_restart']['admissions'][0]];self.assertTrue(validate(r))
    def test_pre_reservation_not_a_replay(self):
        r=copy.deepcopy(self.cases['before-reserve']);r['reoffered']['value']['replayed']=True;self.assertTrue(validate(r))

class RecoveryCheckpointTests(unittest.TestCase):
    SOURCE='async def _handle_runs():\n    outcome, record = store.reserve()\n    if outcome != "created":\n        return None\n'
    def test_before_line(self):self.assertEqual(reservation_line(self.SOURCE,'before-reserve'),2)
    def test_after_line(self):self.assertEqual(reservation_line(self.SOURCE,'after-reserve'),3)
    def test_unknown_phase(self):
        with self.assertRaises(ValueError):reservation_line(self.SOURCE,'bad')
    def test_ambiguous_reservation(self):
        with self.assertRaises(ValueError):reservation_line(self.SOURCE+'    x = other.reserve()\n','before-reserve')
    def test_missing_database_not_created(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)
            with self.assertRaises(sqlite3.OperationalError):snapshot(path,'marker')
            self.assertEqual(list(path.iterdir()),[])

if __name__=='__main__':unittest.main()
