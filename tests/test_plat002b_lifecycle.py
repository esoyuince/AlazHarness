"""PLAT-002B offline fixed Windows/WSL owned lifecycle contract.

Default Python CI never runs WSL or a Linux child. Native one-shot
testing uses an explicit QA command and opt-in from a developer.
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
HOST_PATH=ROOT/'scripts/qa/run_plat002b_windows_once.py'
GUEST_PATH=ROOT/'scripts/qa/wsl2_owned_lifecycle.py'

def load(path,key):
    spec=importlib.util.spec_from_file_location(key,path)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

HOST=load(HOST_PATH,'plat002b_host')
GUEST=load(GUEST_PATH,'plat002b_guest')

def proof():
    return {
        'result':'PASS_SCOPED_LINUX_OWNED_CHILD_LIFECYCLE',
        'runId':'a'*12,'guestUid':1000,
        'sourceSha256':'b'*64,'linuxFilesystem':'ext2/ext3',
        'sourceCopyExt4ShaVerified':True,'sourceCopyRemoved':True,
        'guestChildChecks':{name:True for name in HOST.CHECK_NAMES},
        'guestChildChecksCount':len(HOST.CHECK_NAMES),
        'guestOwnedChildrenReaped':True,
        'hostWslWrapperCancelVerified':False,
        'hostFilesystemIsolated':False,
        'separateHostUidVerified':False,
        'secureAdapterActivated':False,
        'fullD3BAccepted':False,'realModelCalls':0,
        'automaticRetry':False,
    }

class OfflineLifecycleContracts(unittest.TestCase):
    def test_validate_exact_positive_proof(self):
        self.assertTrue(HOST.validate_native(proof(),'a'*12,'b'*64))

    def test_disallowed_hostfilesystem_claim(self):
        p=proof();p['hostFilesystemIsolated']=True
        self.assertFalse(HOST.validate_native(p,'a'*12,'b'*64))

    def test_wrong_guest_sha_refused(self):
        self.assertFalse(HOST.validate_native(proof(),'a'*12,'c'*64))

    def test_wrong_run_id_refused(self):
        self.assertFalse(HOST.validate_native(proof(),'f'*12,'b'*64))

    def test_root_identity_refused(self):
        p=proof();p['guestUid']=0
        self.assertFalse(HOST.validate_native(p,'a'*12,'b'*64))

    def test_guest_unreaped_refused(self):
        p=proof();p['guestOwnedChildrenReaped']=False
        self.assertFalse(HOST.validate_native(p,'a'*12,'b'*64))

    def test_missing_one_child_test_refused(self):
        p=proof();p['guestChildChecks'].pop('term_reaped')
        self.assertFalse(HOST.validate_native(p,'a'*12,'b'*64))

    def test_failed_one_child_test_refused(self):
        p=proof();p['guestChildChecks']['kill_exit_code']=False
        self.assertFalse(HOST.validate_native(p,'a'*12,'b'*64))

    def test_wrong_check_count_refused(self):
        p=proof();p['guestChildChecksCount']=1
        self.assertFalse(HOST.validate_native(p,'a'*12,'b'*64))

    def test_claimed_wsl_wrapper_cancel_refused(self):
        p=proof();p['hostWslWrapperCancelVerified']=True
        self.assertFalse(HOST.validate_native(p,'a'*12,'b'*64))

    def test_model_or_full_d3b_claim_refused(self):
        for key,value in (('realModelCalls',1),('fullD3BAccepted',True),
                          ('secureAdapterActivated',True),
                          ('automaticRetry',True)):
            with self.subTest(key=key):
                p=proof();p[key]=value
                self.assertFalse(HOST.validate_native(p,'a'*12,'b'*64))

    def test_native_guest_requires_linux(self):
        with patch.object(GUEST.sys,'platform','win32'):
            with self.assertRaisesRegex(GUEST.Refused,'linux_x64_required'):
                GUEST.require_environment()

    def test_own_child_group_cleanup_rejects_nonowned_pid(self):
        class Fake:
            pid=0
            returncode=None
            def poll(self):return None
        with self.assertRaisesRegex(GUEST.Refused,'owned_process_group_required'):
            GUEST.terminate_owned(Fake())

    def test_guest_script_source_sha_64_hex(self):
        digest=GUEST.source_sha(GUEST_PATH)
        self.assertEqual(len(digest),64)
        self.assertTrue(all(c in '0123456789abcdef' for c in digest))

    def test_guest_tmp_stage_does_not_create_files_in_default_test(self):
        self.assertIn('alaz-plat002b-',GUEST_PATH.read_text(encoding='utf-8'))
        self.assertFalse((ROOT/'runtime/plat002b-sandbox-executed').exists())

    def test_windows_host_fixed_script_location(self):
        self.assertTrue(HOST.GUEST.is_file())
        self.assertEqual(HOST.GUEST.resolve(),GUEST_PATH.resolve())
        self.assertEqual(HOST.RECEIPT.name,'native-owned-lifecycle-01.json')

    def test_fixed_wsl_path_mapping(self):
        if sys.platform=='win32':
            converted=HOST.fixed_wsl_mount(GUEST_PATH)
            self.assertTrue(converted.startswith('/mnt/'))
            self.assertTrue(converted.endswith('/scripts/qa/wsl2_owned_lifecycle.py'))

    def test_readonly_no_optin_cli_refuses_before_wsl(self):
        env=dict(os.environ)
        env.pop('ALAZ_PLAT002B_TEST_OWNED',None)
        proc=subprocess.run([sys.executable,'-B',str(HOST_PATH),
                '--run-owned-once'],cwd=ROOT,env=env,
                capture_output=True,text=True,timeout=8)
        self.assertEqual(proc.returncode,2)
        self.assertEqual(json.loads(proc.stdout)['code'],
                         'EXPLICIT_OWNED_QA_REQUIRED')

    def test_unknown_host_option_never_starts_wsl(self):
        env=dict(os.environ)
        env.pop('ALAZ_PLAT002B_TEST_OWNED',None)
        proc=subprocess.run([sys.executable,'-B',str(HOST_PATH),
               '--run-owned-once','--execute=sh'],cwd=ROOT,env=env,
               capture_output=True,text=True,timeout=8)
        self.assertEqual(proc.returncode,2)
        self.assertEqual(json.loads(proc.stdout)['result'],'REFUSED')

if __name__=='__main__':
    unittest.main()
