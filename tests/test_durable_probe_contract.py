"""Offline evidence/identity guards. These tests do NOT execute Pi Durable."""
from __future__ import annotations
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from run_durable_sqlite_probe import CRASH, evaluate, read_external, validate_ready


def fixture(scenario='unsafe-effect'):
    totals={'unsafe-effect':(1,1),'safe-effect':(2,2),'idempotent-effect':(2,1),'before-effect':(1,1),'after-result':(1,1)}
    a,e=totals[scenario]
    ready={'scenario':scenario,'phase':'seed','nonce':'a'*32,'pid':10,'rootId':1,'submissionId':2,'boundary':CRASH[scenario]}
    last={'scenario':scenario,'result':'PASS','modelInferenceCalls':0,'paidCalls':0,'liveIdle':True,
          'rootId':1,'submissionId':2,'sameSubmissionAfterReopen':True,'attempts':a,'effects':e,
          'toolResults':1,'toolErrors':1 if scenario=='unsafe-effect' else 0,'interrupted':scenario=='unsafe-effect',
          'submissionStatus':'done'}
    seed={'phase':'seed','pid':10,'exit_code':1,'intentional_kill':True,'timed_out':False,'barrier':ready,
          'post_exit_external':{'attempts':0 if scenario=='before-effect' else 1,'effects':0 if scenario=='before-effect' else 1,'logical_keys':1}}
    resume={'phase':'resume','pid':11,'exit_code':0,'intentional_kill':False,'timed_out':False,'receipt':last}
    return [seed,resume],{'attempts':a,'effects':e,'logical_keys':1}


class CrashIdentityTests(unittest.TestCase):
    def test_valid_boundary(self):
        phases,_=fixture();validate_ready(phases[0]['barrier'],'unsafe-effect','a'*32,10)
    def test_wrong_pid(self):
        phases,_=fixture()
        with self.assertRaises(ValueError):validate_ready(phases[0]['barrier'],'unsafe-effect','a'*32,99)
    def test_wrong_nonce(self):
        phases,_=fixture()
        with self.assertRaises(ValueError):validate_ready(phases[0]['barrier'],'unsafe-effect','b'*32,10)
    def test_wrong_boundary(self):
        phases,_=fixture();phases[0]['barrier']['boundary']='unverified'
        with self.assertRaises(ValueError):validate_ready(phases[0]['barrier'],'unsafe-effect','a'*32,10)
    def test_non_crash_scenario(self):
        phases,_=fixture()
        with self.assertRaises(ValueError):validate_ready(phases[0]['barrier'],'duplicate-reopen','a'*32,10)
    def test_ids_are_numeric(self):
        phases,_=fixture();phases[0]['barrier']['rootId']='1'
        with self.assertRaises(ValueError):validate_ready(phases[0]['barrier'],'unsafe-effect','a'*32,10)


class DurableEvidenceTests(unittest.TestCase):
    def test_dedup_characterization_is_not_strict_conflict(self):
        p,e=fixture();p[0]['intentional_kill']=False;p[0]['exit_code']=0
        e={'attempts':0,'effects':0,'logical_keys':0}
        p[1]['receipt'].update(scenario='duplicate-reopen',attempts=0,effects=0,
            changedPayloadSameId=True,payloadConflictEnforced=False,typeMismatchRejected=True,
            inputChangedPayloadSameId=True,inputOriginalPreserved=True,newModelCallsOnInputRetry=0)
        self.assertEqual(evaluate('duplicate-reopen',p,e),[])
        p[1]['receipt']['payloadConflictEnforced']=True
        self.assertTrue(evaluate('duplicate-reopen',p,e))
    def test_multiple_logical_keys_rejected(self):
        p,e=fixture('idempotent-effect');e['logical_keys']=2
        self.assertTrue(evaluate('idempotent-effect',p,e))
    def test_valid_unsafe_interruption(self):
        p,e=fixture();self.assertEqual(evaluate('unsafe-effect',p,e),[])
    def test_idempotent_external_effect(self):
        p,e=fixture('idempotent-effect');self.assertEqual(evaluate('idempotent-effect',p,e),[])
    def test_safe_does_not_imply_single_effect(self):
        p,e=fixture('safe-effect');self.assertEqual(evaluate('safe-effect',p,e),[])
        e['effects']=1;self.assertTrue(evaluate('safe-effect',p,e))
    def test_fake_process_restart_rejected(self):
        p,e=fixture();p[1]['pid']=10;self.assertTrue(evaluate('unsafe-effect',p,e))
    def test_successful_seed_exit_is_not_crash(self):
        p,e=fixture();p[0]['exit_code']=0;self.assertTrue(evaluate('unsafe-effect',p,e))
    def test_changed_admission_identity_rejected(self):
        p,e=fixture();p[1]['receipt']['submissionId']=99;self.assertTrue(evaluate('unsafe-effect',p,e))
    def test_false_idle_rejected(self):
        p,e=fixture();p[1]['receipt']['liveIdle']=False;self.assertTrue(evaluate('unsafe-effect',p,e))
    def test_native_claim_cannot_override_external_counter(self):
        p,e=fixture();e['effects']=2;self.assertTrue(evaluate('unsafe-effect',p,e))
    def test_missing_pre_resume_counter_rejected(self):
        p,e=fixture();del p[0]['post_exit_external'];self.assertTrue(evaluate('unsafe-effect',p,e))
    def test_missing_interrupted_result_rejected(self):
        p,e=fixture();p[1]['receipt']['interrupted']=False;self.assertTrue(evaluate('unsafe-effect',p,e))
    def test_unknown_scenario_rejected(self):
        p,e=fixture();self.assertTrue(evaluate('unknown',p,e))
    def test_partial_phases_rejected(self):
        p,e=fixture();self.assertTrue(evaluate('unsafe-effect',p[:1],e))
    def test_malformed_input_fails_closed(self):
        for p,e in ((None,{}),([None],{}),([],None),([],{})):
            self.assertTrue(evaluate('unsafe-effect',p,e))
    def test_nan_counter_rejected(self):
        p,e=fixture();e['effects']=float('nan');self.assertTrue(evaluate('unsafe-effect',p,e))
    def test_timeout_not_success(self):
        p,e=fixture();p[1]['timed_out']=True;self.assertTrue(evaluate('unsafe-effect',p,e))


class IndependentDatabaseTests(unittest.TestCase):
    def test_reads_real_counter_and_unique_key(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);db=sqlite3.connect(root/'external.sqlite')
            try:
                db.executescript("CREATE TABLE attempts(task_key TEXT); CREATE TABLE effects(effect_key TEXT); INSERT INTO attempts VALUES('same'),('same'); INSERT INTO effects VALUES('once');")
                db.commit()
            finally:db.close()
            self.assertEqual(read_external(root),{'attempts':2,'effects':1,'logical_keys':1})
    def test_missing_database_is_not_created(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(sqlite3.OperationalError):read_external(Path(tmp))
            self.assertFalse((Path(tmp)/'external.sqlite').exists())

if __name__=='__main__':unittest.main()
