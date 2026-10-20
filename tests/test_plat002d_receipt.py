"""Immutable PLAT-002D two native NO-GO receipts and offline source QA.

Never launches WSL, scans Linux, terminates processes, or retries a
native test during standard CI. Windows CRLF->Git LF is exactly bounded.
"""
import hashlib
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
EV=ROOT/'evidence/plat-002d-wrapperloss-20oct'
def read(name):
    return json.loads((EV/name).read_text(encoding='utf-8'))

def original_windows_sha(name,expected):
    raw=(ROOT/name).read_bytes()
    if hashlib.sha256(raw).hexdigest()==expected:return True
    if b'\r' in raw.replace(b'\r\n',b''):return False
    if b'\r' in raw:return False
    return bool(raw.count(b'\n') and
                hashlib.sha256(raw.replace(b'\n',b'\r\n')).hexdigest()==expected)

class WrapperLossNoGoEvidence(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.summary=read('native-no-go-summary.json')
        cls.first=read('native-wrapperloss-01.json')
        cls.second=read('native-wrapperloss-02.json')
        cls.frozen=read('native01-failure-custody.json')
        cls.firstPost=read('postfail-readonly.json')

    def test_exact_scope_does_not_certify_d3b(self):
        s=self.summary
        self.assertEqual(s['status'],'NO_GO_UNKNOWN_GUEST_CLOSURE')
        self.assertEqual(s['attemptCount'],2)
        self.assertIs(s['noAutomaticRetry'],True)
        self.assertIs(s['fullPLAT002Accepted'],False)
        self.assertIs(s['fullD3BAccepted'],False)
        self.assertEqual(s['realModelCalls'],0)
        self.assertIs(s['mainMerged'],False)

    def test_first_ready_timeout_is_fail(self):
        x=self.first
        self.assertEqual(x['status'],'FAIL_OR_UNKNOWN_GUEST_LEASE')
        self.assertEqual(x['errorCode'],'READY_TIMEOUT_UNKNOWN')
        self.assertIs(x['readyBindingVerified'],False)
        self.assertIs(x['wrapperOwnedProcessTerminated'],False)
        self.assertIs(x['automaticRetry'],False)
        self.assertEqual(x['observedResult']['state'],'NO_OWNED_ROOT')

    def test_second_wrapper_was_actually_terminated(self):
        y=self.second
        self.assertEqual(y['status'],'FAIL_OR_UNKNOWN_GUEST_LEASE')
        self.assertIs(y['readyBindingVerified'],True)
        self.assertIs(y['wrapperOwnedProcessTerminated'],True)
        self.assertEqual(y['wrapperExitCode'],1)
        self.assertEqual(y['observedResult']['state'],'NO_OWNED_ROOT')
        self.assertIsNone(y['cleanupResult'])
        self.assertIsNone(y['postCleanupObserved'])

    def test_native_two_distinct_run_identifiers(self):
        self.assertNotEqual(self.first['runId'],self.second['runId'])
        self.assertEqual(self.first['runId'],self.summary['first']['runId'])
        self.assertEqual(self.second['runId'],self.summary['second']['runId'])

    def test_failed_external_effect_is_never_replayed(self):
        for x in (self.first,self.second):
            self.assertEqual(x['externalToolOutcome'],'UNKNOWN_DO_NOT_REPLAY')
            self.assertIs(x['automaticRetry'],False)
            self.assertEqual(x['realModelCalls'],0)
            self.assertIs(x['fullD3BAccepted'],False)
        self.assertIs(self.summary['unknownExternalEffectReplayed'],False)

    def test_first_global_postfailure_proved_no_residue(self):
        p=self.firstPost
        self.assertEqual(p['scannedProcEntries'],72)
        self.assertEqual(p['unreadable'],0)
        self.assertEqual(p['matchingLegacyTestProcesses'],[])
        self.assertEqual(p['testOwnedRootsPresent'],[])
        self.assertIs(p['noResidues'],True)

    def test_second_global_linux_postcheck_timed_out(self):
        g=self.summary['globalAfterSecond']
        self.assertEqual(g['result'],'UNKNOWN_TIMEOUT')
        self.assertEqual(g['deadlineSeconds'],22)
        self.assertIs(g['resultFileWritten'],False)
        self.assertIs(g['noBlindRetry'],True)

    def test_windows_process_snapshot_does_not_imply_guest_reap(self):
        p=self.summary['windowsProcessSnapshotAfterSecond']
        self.assertIs(p['readOnly'],True)
        self.assertEqual(p['wslExeCount'],0)
        self.assertEqual(p['wslHostExeCount'],0)
        self.assertEqual(p['wslServiceCount'],1)
        self.assertIs(self.summary['guestProcessTreeReapedVerified'],False)

    def test_native_receipt_01_sha_frozen_across_os(self):
        x=self.summary['first']
        self.assertTrue(original_windows_sha(
           'evidence/plat-002d-wrapperloss-20oct/'+x['file'],
            x['windowsRawSha256']))

    def test_native_receipt_02_sha_frozen_across_os(self):
        x=self.summary['second']
        self.assertTrue(original_windows_sha(
           'evidence/plat-002d-wrapperloss-20oct/'+x['file'],
            x['windowsRawSha256']))

    def test_six_source_immutable_canonical_git_lf(self):
        m=self.summary['firstAndSecondNativeSources']
        expected={
          'scripts/qa/wsl2_wrapperloss_guest.py',
          'scripts/qa/wsl2_wrapperloss_observe.py',
          'scripts/qa/run_plat002d_windows_once.py',
          'scripts/qa/run_plat002d_windows_once_v2.py',
          'tests/test_plat002d_wrapperloss.py',
          'tests/test_plat002d_second_pilot.py'}
        self.assertEqual(set(m),expected)
        for name,entry in m.items():
            with self.subTest(file=name):
                raw=(ROOT/name).read_bytes()
                self.assertEqual(
                    hashlib.sha256(raw.replace(b'\r\n',b'\n')).hexdigest(),
                    entry['gitCanonicalLfSha256'])
                self.assertTrue(original_windows_sha(name,entry['windowsRawSha256']))

    def test_first_sources_not_mutated_for_second_run(self):
        for name,entry in self.frozen['firstSourceHashes'].items():
            self.assertTrue(original_windows_sha(name,entry['windowsRawSha256']))
        self.assertIs(self.frozen['originalFirstRunResultChanged'],False)

    def test_second_readiness_acceptance_is_not_guest_cleanup(self):
        s=self.summary
        self.assertIs(s['guestLeaseExpiredVerified'],False)
        self.assertIs(s['guestProcessTreeReapedVerified'],False)
        self.assertIs(s['testTempRootRemovedVerified'],False)
        self.assertIs(s['second']['independentLinuxLeaseJournalFound'],False)

    def test_console_receipt_filename_mismatch_not_confused(self):
        self.assertEqual(self.summary['second']['actualSavedReceiptFile'],
                         'native-wrapperloss-02.json')
        self.assertIs(self.summary['second']['consoleReceiptPathTextStale'],True)

    def test_previous_inband_cancel_not_falsified(self):
        x=json.loads((ROOT/'evidence/plat-002c-cancel-20oct/native-cancel-handshake-01.json')
            .read_text(encoding='utf-8'))
        self.assertEqual(x['result'],'PASS_EXPLICIT_CANCEL_HANDSHAKE_TEST_OWNED')
        self.assertIs(x['hostWslWrapperForcedCancelVerified'],False)

if __name__=='__main__':
    unittest.main()
