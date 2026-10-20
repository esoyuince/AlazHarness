"""PLAT-002D exact Windows CRLF/Git-Linux LF historical evidence QA.

No WSL launch, no live process, no model/provider or filesystem write.
The original two native NO-GO receipts and original six-source snapshot
remain anchored to f18da79; fixes to test code do not falsify them.
"""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
BASE='f18da79d43da6dcafa71ddf43ae9a9a400fe8ad6'
SOURCE=ROOT/'scripts/qa/run_plat002d_windows_once.py'
EVIDENCE=ROOT/'evidence/plat-002d-wrapperloss-20oct'
SECOND_TEST=ROOT/'tests/test_plat002d_second_pilot.py'

def loaded():
    spec=importlib.util.spec_from_file_location('plat002d_ci_recovery_sim',SECOND_TEST)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

class HistoricalCrossOSReceipt(unittest.TestCase):
    def test_six_exact_historical_lf_and_crlf_sha_pairs(self):
        manifest=json.loads((EVIDENCE/'native-no-go-summary.json').read_text(
            encoding='utf-8'))['firstAndSecondNativeSources']
        self.assertEqual(len(manifest),6)
        for name,record in manifest.items():
            with self.subTest(name=name):
                z=subprocess.run(['git','show',BASE+':'+name],
                   cwd=ROOT,capture_output=True,timeout=15)
                self.assertEqual(z.returncode,0,'frozen_commit_missing')
                self.assertNotIn(b'\r',z.stdout)
                self.assertGreater(z.stdout.count(b'\n'),0)
                self.assertEqual(hashlib.sha256(z.stdout).hexdigest(),
                                 record['gitCanonicalLfSha256'])
                self.assertEqual(hashlib.sha256(
                    z.stdout.replace(b'\n',b'\r\n')).hexdigest(),
                    record['windowsRawSha256'])

    def test_linux_lf_simulated_original_seven_second_assertion(self):
        m=loaded()
        native_read=Path.read_bytes
        target=SOURCE.resolve()
        def from_git(self):
            raw=native_read(self)
            return raw.replace(b'\r\n',b'\n') if self.resolve()==target else raw
        with patch.object(Path,'read_bytes',from_git):
            obj=m.TwoIndependentPilots('test_original_seven_second_source_frozen')
            result=unittest.TestResult()
            obj.run(result)
        self.assertTrue(result.wasSuccessful(),
                        result.failures+result.errors)
        self.assertEqual(result.testsRun,1)

    def test_any_content_change_rejected_even_if_lf(self):
        m=loaded()
        native_read=Path.read_bytes
        target=SOURCE.resolve()
        def altered(self):
            raw=native_read(self)
            if self.resolve()==target:
                return raw.replace(b'\r\n',b'\n')+b'\nMUTATION'
            return raw
        with patch.object(Path,'read_bytes',altered):
            obj=m.TwoIndependentPilots('test_original_seven_second_source_frozen')
            result=unittest.TestResult()
            obj.run(result)
        self.assertFalse(result.wasSuccessful())
        self.assertEqual(len(result.failures),1)
        self.assertEqual(len(result.errors),0)

    def test_failed_native_runs_are_still_unknown(self):
        names=['native-wrapperloss-01.json','native-wrapperloss-02.json']
        for name in names:
            with self.subTest(file=name):
                value=json.loads((EVIDENCE/name).read_text(encoding='utf-8'))
                self.assertEqual(value['status'],'FAIL_OR_UNKNOWN_GUEST_LEASE')
                self.assertEqual(value['externalToolOutcome'],'UNKNOWN_DO_NOT_REPLAY')
                self.assertIs(value['fullD3BAccepted'],False)
                self.assertIs(value['automaticRetry'],False)
        record=json.loads((EVIDENCE/'native-no-go-summary.json').read_text(
            encoding='utf-8'))
        self.assertIs(record['guestLeaseExpiredVerified'],False)
        self.assertIs(record['guestProcessTreeReapedVerified'],False)

    def test_nonrunning_wsl_not_mistaken_for_reap_or_acceptance(self):
        doc=json.loads((ROOT/'evidence/plat-002d-recovery-20oct/'
                        'no-running-distro-and-ci-observed.json').read_text(
                            encoding='utf-8'))
        d=doc['latestReadOnlyNonStartingWslQuery']
        self.assertEqual(d['outcome'],'NO_RUNNING_DISTRIBUTIONS_REPORTED')
        self.assertIs(d['linuxGuestProcessDispositionIndependentlyVerified'],False)
        self.assertIs(doc['automaticGuestReplay'],False)
        self.assertIs(doc['nativeAccepted'],False)

if __name__=='__main__':
    unittest.main()
