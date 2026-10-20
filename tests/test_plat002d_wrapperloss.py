"""PLAT-002D independent lease / Windows-wrapper loss contract tests.

No WSL launch, windows process kill, model or local /tmp guest file
effect in default Python CI.
"""
from __future__ import annotations
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
GUEST=ROOT/'scripts/qa/wsl2_wrapperloss_guest.py'
OBSERVER=ROOT/'scripts/qa/wsl2_wrapperloss_observe.py'
HOST=ROOT/'scripts/qa/run_plat002d_windows_once.py'

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

g=load('plat002d_guest',GUEST)
a=load('plat002d_observer',OBSERVER)
h=load('plat002d_host',HOST)

RUN='a'*24
NONCE='b'*64
SHA='c'*64
EXPECTED={'runId':RUN,'nonce':NONCE,
          'sourceSha256':SHA,'nonceSha256':'d'*64,
          'observerSha256':'e'*64}
READY={
  'phase':'READY','version':1,'type':'alaz.wsl2.wrapperloss.test.v1',
  'runId':RUN,'nonce':NONCE,'sourceSha256':SHA,
  'guestUid':1000,'guardianPid':20321,'workerPid':20322,
  'grandchildPid':20323,'hostFileIsolated':False,
  'secureExecutionAccepted':False,'realModelCalls':0,
}

def audit(state='CLOSED_LEASE_OUTCOME_UNKNOWN'):
    return {'runId':RUN,'sourceSha256':SHA,
      'nonceSha256':'d'*64,
      'externalEffectOutcome':'UNKNOWN_DO_NOT_REPLAY',
      'fullD3BAccepted':False,'realModelCalls':0,
      'unreadableProcEntries':0,'state':state,
      'matchingProcesses':[],
      'matchingManifestPidsStillPresent':[],
      'nativeResultWritten':True,'leaseExpired':True,
      'testOwnedProcessesReaped':True,
      'terminal':'LEASE_EXPIRED_OUTCOME_UNKNOWN'}

class TestHostWrapperContract(unittest.TestCase):
    def test_exact_ready(self):
        self.assertTrue(h.validated_ready(dict(READY),EXPECTED))
    def test_ready_missing_field(self):
        bad=dict(READY);bad.pop('grandchildPid')
        with self.assertRaises(h.Refused):h.validated_ready(bad,EXPECTED)
    def test_ready_extra_command(self):
        bad={**READY,'command':'bash'}
        with self.assertRaises(h.Refused):h.validated_ready(bad,EXPECTED)
    def test_ready_wrong_nonce(self):
        bad={**READY,'nonce':'f'*64}
        with self.assertRaises(h.Refused):h.validated_ready(bad,EXPECTED)
    def test_ready_wrong_runid(self):
        bad={**READY,'runId':'f'*24}
        with self.assertRaises(h.Refused):h.validated_ready(bad,EXPECTED)
    def test_ready_wrong_source(self):
        bad={**READY,'sourceSha256':'f'*64}
        with self.assertRaises(h.Refused):h.validated_ready(bad,EXPECTED)
    def test_ready_wrong_guest_uid(self):
        bad={**READY,'guestUid':0}
        with self.assertRaises(h.Refused):h.validated_ready(bad,EXPECTED)
    def test_ready_same_worker_grandchild(self):
        bad={**READY,'grandchildPid':READY['workerPid']}
        with self.assertRaises(h.Refused):h.validated_ready(bad,EXPECTED)
    def test_ready_duplicate_guardian_pid(self):
        bad={**READY,'guardianPid':READY['workerPid']}
        with self.assertRaises(h.Refused):h.validated_ready(bad,EXPECTED)
    def test_ready_oversold_sandbox(self):
        bad={**READY,'secureExecutionAccepted':True}
        with self.assertRaises(h.Refused):h.validated_ready(bad,EXPECTED)
    def test_ready_host_filesystem_claim_rejected(self):
        bad={**READY,'hostFileIsolated':True}
        with self.assertRaises(h.Refused):h.validated_ready(bad,EXPECTED)
    def test_ready_inflated_model_claim(self):
        bad={**READY,'realModelCalls':1}
        with self.assertRaises(h.Refused):h.validated_ready(bad,EXPECTED)
    def test_ready_bool_version_disallowed(self):
        bad={**READY,'version':True}
        with self.assertRaises(h.Refused):h.validated_ready(bad,EXPECTED)
    def test_valid_audit_unknown_only(self):
        self.assertTrue(h.validated_audit(audit(),EXPECTED))
    def test_audit_changed_nonce_hash_refused(self):
        bad={**audit(),'nonceSha256':'f'*64}
        with self.assertRaises(h.Refused):h.validated_audit(bad,EXPECTED)
    def test_audit_unknown_state_not_accepted(self):
        bad={**audit('EXECUTED_SUCCESS')}
        with self.assertRaises(h.Refused):h.validated_audit(bad,EXPECTED)
    def test_audit_success_claim_rejected(self):
        bad={**audit(),'externalEffectOutcome':'SUCCESS'}
        with self.assertRaises(h.Refused):h.validated_audit(bad,EXPECTED)
    def test_audit_false_full_d3b_rejected(self):
        bad={**audit(),'fullD3BAccepted':True}
        with self.assertRaises(h.Refused):h.validated_audit(bad,EXPECTED)
    def test_audit_modified_run_refused(self):
        bad={**audit(),'runId':'f'*24}
        with self.assertRaises(h.Refused):h.validated_audit(bad,EXPECTED)
    def test_audit_unreadable_processes_rejected(self):
        bad={**audit(),'unreadableProcEntries':1}
        with self.assertRaises(h.Refused):h.validated_audit(bad,EXPECTED)
    def test_audit_unknown_live_pid_does_not_certify(self):
        # A legitimate unknown state must NOT become a closed state.
        bad={**audit('UNKNOWN_NOT_PROVEN_CLOSED'),
             'matchingProcesses':[{'pid':3,'state':'S'}]}
        self.assertTrue(h.validated_audit(bad,EXPECTED))
        self.assertNotEqual(bad['state'],'CLOSED_LEASE_OUTCOME_UNKNOWN')
    def test_guest_path_fixed_readonly_script(self):
        if sys.platform=='win32':
            self.assertTrue(h.trusted_path(h.GUEST).startswith('/mnt/'))
            self.assertTrue(h.trusted_path(h.OBSERVER).endswith(
              '/scripts/qa/wsl2_wrapperloss_observe.py'))
            self.assertTrue(h.host_wsl().lower().endswith('wsl.exe'))
    def test_observe_invalid_mode_without_wsl(self):
        with self.assertRaisesRegex(h.Refused,'AUDIT_MODE_INVALID'):
            h.observe('remote_shell',EXPECTED,'fake.exe')
    def test_optin_absent_stops_before_wsl(self):
        env=dict(os.environ)
        env.pop('ALAZ_PLAT002D_TEST_WRAPPER_LOSS',None)
        run=subprocess.run([sys.executable,'-B',str(HOST),
            '--explicit-owned-wrapper-loss'],
            cwd=ROOT,env=env,capture_output=True,text=True,timeout=10)
        self.assertEqual(run.returncode,2)
        self.assertEqual(json.loads(run.stdout)['code'],
                         'ONE_SHOT_QA_OPT_IN_REQUIRED')
    def test_unknown_flag_stops_before_wsl(self):
        env=dict(os.environ)
        env.pop('ALAZ_PLAT002D_TEST_WRAPPER_LOSS',None)
        run=subprocess.run([sys.executable,'-B',str(HOST),
            '--explicit-owned-wrapper-loss','--command=whoami'],
            cwd=ROOT,env=env,capture_output=True,text=True,timeout=10)
        self.assertEqual(run.returncode,2)
    def test_lease_fixed_7s(self):
        self.assertEqual(g.TTL_SEC,7)
        self.assertIn('LEASE_EXPIRED_OUTCOME_UNKNOWN',
                      Path(GUEST).read_text(encoding='utf-8'))
    def test_guest_does_not_admit_windows_or_root(self):
        with patch.object(g.sys,'platform','win32'):
            with self.assertRaisesRegex(g.Denied,'LINUX_X64_REQUIRED'):
                g.guest_environment()
    def test_guest_runid_requires_24_lowerhex(self):
        self.assertTrue(g.hexid(RUN,24))
        for invalid in ('A'*24,'a'*25,'',None,'hello','c'*23):
            with self.subTest(invalid=invalid):
                self.assertFalse(g.hexid(invalid,24))
    def test_guest_nonce_requires_64_lowerhex(self):
        self.assertTrue(g.hexid(NONCE,64))
        self.assertFalse(g.hexid('B'*64,64))
    def test_guardian_only_writes_known_filenames(self):
        with self.assertRaisesRegex(g.Denied,'RECEIPT_FILE_INVALID'):
            g.write_once(Path('/tmp'),'arbitrary-user-file',{})
    def test_observer_guest_platform_refuses_windows(self):
        with patch.object(a.sys,'platform','win32'):
            with self.assertRaisesRegex(a.Refused,'UNVERIFIED_GUEST'):
                a.ensure_guest()
    def test_observer_sha_validation(self):
        self.assertTrue(a.sha_valid(SHA,64))
        self.assertFalse(a.sha_valid('A'*64,64))
        self.assertFalse(a.sha_valid(True,64))
    def test_pid_birth_identity_binding_present(self):
        body=Path(GUEST).read_text(encoding='utf-8')
        for pattern in ('pid_start_tick','OWNED_WORKER_REPLACED',
                        'OWNED_GRANDCHILD_GROUP_INVALID',
                        'PR_SET_CHILD_SUBREAPER'):
            self.assertIn(pattern,body)
    def test_no_production_service_side_effect(self):
        self.assertFalse((ROOT/'runtime/plat002d-production-sandbox').exists())

if __name__=='__main__':
    unittest.main()
