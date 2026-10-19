"""PLAT-002C fixed cancel protocol contracts; standard CI starts no WSL.

The Windows/WSL native one-shot is an independent explicit opt-in test,
not implicitly replayed by this collection.
"""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
GUEST_PATH=ROOT/'scripts/qa/wsl2_cancel_guest.py'
HOST_PATH=ROOT/'scripts/qa/wsl2_cancel_windows_once.py'

def read_module(file,name):
    spec=importlib.util.spec_from_file_location(name,file)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

GUEST=read_module(GUEST_PATH,'plat002c_guest')
HOST=read_module(HOST_PATH,'plat002c_host')
ID='a'*24
NONCE='b'*64
SHA='c'*64
EXPECTED={'runId':ID,'nonce':NONCE,'sha':SHA,'uid':1000}

def req(action,**changes):
    data={'version':1,'action':action,'runId':ID,'nonce':NONCE}
    if action=='cancel':data['reason']='user_cancel'
    data.update(changes)
    return (json.dumps(data,separators=(',',':'))+'\n').encode('utf-8')

def reply(phase):
    data={'version':1,'type':HOST.TYPE,'phase':phase,'runId':ID,
          'nonce':NONCE,'sourceSha256':SHA,'guestUid':1000,
          'workerPid':12345,'secureExecutionAccepted':False,
          'hostFilesystemIsolated':False,'realModelCalls':0}
    if phase=='CANCELLED':
        for key in ('workerIgnoredTerm','workerKilled','workerReaped',
                    'sourceCopyRemoved','ownedTempRootRemoved'):
            data[key]=True
    return data

class GuestProtocol(unittest.TestCase):
    def test_exact_start(self):
        data=GUEST.parse_frame(req('start'),'start',ID)
        self.assertEqual(data['nonce'],NONCE)
    def test_exact_cancel(self):
        data=GUEST.parse_frame(req('cancel'),'cancel',ID,NONCE)
        self.assertEqual(data['reason'],'user_cancel')
    def test_changed_cancel_nonce(self):
        with self.assertRaisesRegex(GUEST.Reject,'NONCE_CHANGED'):
            GUEST.parse_frame(req('cancel',nonce='f'*64),'cancel',ID,NONCE)
    def test_wrong_run_id(self):
        with self.assertRaises(GUEST.Reject):
            GUEST.parse_frame(req('cancel',runId='f'*24),'cancel',ID,NONCE)
    def test_wrong_phase(self):
        with self.assertRaises(GUEST.Reject):
            GUEST.parse_frame(req('start'),'cancel',ID,NONCE)
    def test_wrong_cancel_reason(self):
        with self.assertRaises(GUEST.Reject):
            GUEST.parse_frame(req('cancel',reason='shell'),'cancel',ID,NONCE)
    def test_request_command_field_rejected(self):
        with self.assertRaises(GUEST.Reject):
            GUEST.parse_frame(req('start',command='whoami'),'start',ID)
    def test_bool_version_rejected(self):
        with self.assertRaises(GUEST.Reject):
            GUEST.parse_frame(req('start',version=True),'start',ID)
    def test_duplicate_json_fields(self):
        raw=b'{"version":1,"version":1,"action":"start","runId":"'+(b'a'*24)+b'","nonce":"'+(b'b'*64)+b'"}\n'
        with self.assertRaisesRegex(GUEST.Reject,'DUPLICATE_FIELD'):
            GUEST.parse_frame(raw,'start',ID)
    def test_wrong_case_nonce(self):
        with self.assertRaises(GUEST.Reject):
            GUEST.parse_frame(req('start',nonce='B'*64),'start',ID)
    def test_empty_frame(self):
        with self.assertRaises(GUEST.Reject):
            GUEST.parse_frame(b'','start',ID)
    def test_nonutf8_frame(self):
        with self.assertRaises(GUEST.Reject):
            GUEST.parse_frame(b'\xff\n','start',ID)
    def test_missing_newline(self):
        with self.assertRaises(GUEST.Reject):
            GUEST.parse_frame(req('start').strip(),'start',ID)
    def test_two_frames(self):
        with self.assertRaises(GUEST.Reject):
            GUEST.parse_frame(req('start')+req('cancel'),'start',ID)
    def test_nul_byte(self):
        with self.assertRaises(GUEST.Reject):
            GUEST.parse_frame(req('start').replace(b'start',b'\x00start'),'start',ID)
    def test_oversized(self):
        with self.assertRaises(GUEST.Reject):
            GUEST.parse_frame(b'x'*1100,'start',ID)
    def test_nonlinux_guard(self):
        with patch.object(GUEST.sys,'platform','win32'):
            with self.assertRaisesRegex(GUEST.Reject,'LINUX_X64_REQUIRED'):
                GUEST.assert_guest()
    def test_guest_worker_only_fixed_script(self):
        self.assertIn("WORKER_READY",GUEST.WORKER_SCRIPT)
        self.assertIn('SIGTERM,signal.SIG_IGN',GUEST.WORKER_SCRIPT.replace(' ',''))
        self.assertLess(len(GUEST.WORKER_SCRIPT),400)
    def test_no_process_group_zero_kill(self):
        class Fake:
            pid=0
            def poll(self):return None
        with self.assertRaisesRegex(GUEST.Reject,'OWNED_CHILD_PROCESS_GROUP_MISMATCH'):
            GUEST.owned_stop(Fake())

class HostProtocol(unittest.TestCase):
    def test_ready_exact(self):
        self.assertTrue(HOST.validate_frame(reply('READY'),EXPECTED,'READY'))
    def test_cancelled_exact_after_ready(self):
        ready=reply('READY')
        self.assertTrue(HOST.validate_frame(reply('CANCELLED'),EXPECTED,'CANCELLED',ready))
    def test_ready_forged_nonce_rejected(self):
        rec=reply('READY');rec['nonce']='f'*64
        with self.assertRaises(HOST.Rejected):
            HOST.validate_frame(rec,EXPECTED,'READY')
    def test_ready_wrong_sha_rejected(self):
        rec=reply('READY');rec['sourceSha256']='f'*64
        with self.assertRaises(HOST.Rejected):
            HOST.validate_frame(rec,EXPECTED,'READY')
    def test_ready_foreign_uid_rejected(self):
        rec=reply('READY');rec['guestUid']=0
        with self.assertRaises(HOST.Rejected):
            HOST.validate_frame(rec,EXPECTED,'READY')
    def test_extra_guest_field_rejected(self):
        rec=reply('READY');rec['shell']='bash'
        with self.assertRaises(HOST.Rejected):
            HOST.validate_frame(rec,EXPECTED,'READY')
    def test_ready_security_upgrade_rejected(self):
        rec=reply('READY');rec['secureExecutionAccepted']=True
        with self.assertRaises(HOST.Rejected):
            HOST.validate_frame(rec,EXPECTED,'READY')
    def test_done_pid_changed_rejected(self):
        rec=reply('CANCELLED');rec['workerPid']=54321
        with self.assertRaises(HOST.Rejected):
            HOST.validate_frame(rec,EXPECTED,'CANCELLED',reply('READY'))
    def test_done_not_reaped_rejected(self):
        rec=reply('CANCELLED');rec['workerReaped']=False
        with self.assertRaises(HOST.Rejected):
            HOST.validate_frame(rec,EXPECTED,'CANCELLED',reply('READY'))
    def test_done_missing_temp_cleanup_rejected(self):
        rec=reply('CANCELLED');rec['ownedTempRootRemoved']=False
        with self.assertRaises(HOST.Rejected):
            HOST.validate_frame(rec,EXPECTED,'CANCELLED',reply('READY'))
    def test_done_inflated_model_calls_rejected(self):
        rec=reply('CANCELLED');rec['realModelCalls']=1
        with self.assertRaises(HOST.Rejected):
            HOST.validate_frame(rec,EXPECTED,'CANCELLED',reply('READY'))
    def test_done_without_ready_rejected(self):
        with self.assertRaises(HOST.Rejected):
            HOST.validate_frame(reply('CANCELLED'),EXPECTED,'CANCELLED')
    def test_pinned_windows_source_map(self):
        if sys.platform=='win32':
            actual=HOST.fixed_linux_path(HOST.GUEST)
            self.assertTrue(actual.startswith('/mnt/'))
            self.assertTrue(actual.endswith('/scripts/qa/wsl2_cancel_guest.py'))
    def test_no_optin_refuses_without_wsl(self):
        env=dict(os.environ)
        env.pop('ALAZ_PLAT002C_TEST_CANCEL',None)
        z=subprocess.run([sys.executable,'-B',str(HOST_PATH),
           '--explicit-test-cancel'],cwd=ROOT,env=env,
           capture_output=True,text=True,timeout=10)
        self.assertEqual(z.returncode,2)
        self.assertEqual(json.loads(z.stdout)['code'],'ONE_SHOT_QA_OPT_IN_REQUIRED')
    def test_unknown_cli_flag_refused_without_wsl(self):
        env=dict(os.environ)
        env.pop('ALAZ_PLAT002C_TEST_CANCEL',None)
        z=subprocess.run([sys.executable,'-B',str(HOST_PATH),
           '--explicit-test-cancel','--tool=/bin/sh'],
           cwd=ROOT,env=env,capture_output=True,text=True,timeout=10)
        self.assertEqual(z.returncode,2)

if __name__=='__main__':unittest.main()
