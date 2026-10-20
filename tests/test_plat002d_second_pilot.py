"""PLAT-002D second independent one-shot pilot, no automatic replay.

The first native READY timeout is immutable and is not mistaken for
a successful wrapper-loss test. CI tests never launch WSL.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
ORIGINAL=ROOT/'scripts/qa/run_plat002d_windows_once.py'
SECOND=ROOT/'scripts/qa/run_plat002d_windows_once_v2.py'
EVIDENCE=ROOT/'evidence/plat-002d-wrapperloss-20oct'

spec=importlib.util.spec_from_file_location('plat002d_second',SECOND)
V2=importlib.util.module_from_spec(spec)
spec.loader.exec_module(V2)

class TwoIndependentPilots(unittest.TestCase):
    def test_second_receipt_never_overwrites_first(self):
        self.assertEqual(V2.RECEIPT.name,'native-wrapperloss-02.json')
        self.assertNotEqual(V2.RECEIPT,EVIDENCE/'native-wrapperloss-01.json')

    def test_second_ready_timeout_still_bounded(self):
        self.assertEqual(V2.READY_TIMEOUT_SECONDS,20)
        self.assertLessEqual(V2.READY_TIMEOUT_SECONDS,20)

    def test_original_seven_second_source_frozen(self):
        doc=json.loads((EVIDENCE/'native01-failure-custody.json').read_text(encoding='utf-8'))
        sha=hashlib.sha256(ORIGINAL.read_bytes()).hexdigest()
        self.assertEqual(doc['firstSourceHashes'][
            'scripts/qa/run_plat002d_windows_once.py']['windowsRawSha256'],sha)
        self.assertEqual(doc['readyTimeoutSeconds'],7)

    def test_original_native_failure_still_fail(self):
        first=json.loads((EVIDENCE/'native-wrapperloss-01.json').read_text(encoding='utf-8'))
        self.assertEqual(first['status'],'FAIL_OR_UNKNOWN_GUEST_LEASE')
        self.assertEqual(first['errorCode'],'READY_TIMEOUT_UNKNOWN')
        self.assertIs(first['wrapperOwnedProcessTerminated'],False)
        self.assertEqual(first['externalToolOutcome'],'UNKNOWN_DO_NOT_REPLAY')

    def test_independent_read_only_zero_residue(self):
        scan=json.loads((EVIDENCE/'postfail-readonly.json').read_text(encoding='utf-8'))
        self.assertIs(scan['noResidues'],True)
        self.assertEqual(scan['unreadable'],0)
        self.assertEqual(len(scan['matchingLegacyTestProcesses']),0)
        self.assertEqual(len(scan['testOwnedRootsPresent']),0)

    def test_no_v2_optin_no_guest_start(self):
        env=dict(os.environ)
        env.pop('ALAZ_PLAT002D_TEST_WRAPPER_LOSS_V2',None)
        result=subprocess.run([sys.executable,'-B',str(SECOND),
               '--explicit-owned-wrapper-loss-v2'],cwd=ROOT,env=env,
               capture_output=True,text=True,timeout=10)
        self.assertEqual(result.returncode,2)
        self.assertEqual(json.loads(result.stdout)['code'],
                         'ONE_SHOT_QA_OPT_IN_REQUIRED')

    def test_unknown_v2_cli_flag_refuses_before_wsl(self):
        env=dict(os.environ)
        env.pop('ALAZ_PLAT002D_TEST_WRAPPER_LOSS_V2',None)
        result=subprocess.run([sys.executable,'-B',str(SECOND),
               '--explicit-owned-wrapper-loss-v2','--shell=sh'],cwd=ROOT,env=env,
               capture_output=True,text=True,timeout=10)
        self.assertEqual(result.returncode,2)

    def test_guest_sha_and_observer_paths_are_fixed(self):
        self.assertEqual(V2.GUEST,ROOT/'scripts/qa/wsl2_wrapperloss_guest.py')
        self.assertEqual(V2.OBSERVER,ROOT/'scripts/qa/wsl2_wrapperloss_observe.py')
        self.assertEqual(V2.RECEIPT.parent,EVIDENCE)

if __name__=='__main__':
    unittest.main()
