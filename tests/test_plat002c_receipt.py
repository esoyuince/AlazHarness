"""PLAT-002C exact native test-owned explicit cancel receipt and safety bounds.

Does NOT run WSL in CI; native preflight and one-shot are immutable.
Windows CRLF raw guest SHA and Git/Linux LF source are normalized only
by the exact source-specific full-file newline transform.
"""
import hashlib
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
EVIDENCE=ROOT/'evidence/plat-002c-cancel-20oct'

def read(name):
    return json.loads((EVIDENCE/name).read_text(encoding='utf-8'))

class TestOwnedCancelCustody(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.summary=read('summary.json')
        cls.native=read('native-cancel-handshake-01.json')
        cls.pre=read('preflight-readonly.json')
        cls.post=read('post-run-readonly.json')

    def test_exact_positive_native_scope(self):
        n=self.native
        self.assertEqual(n['result'],'PASS_EXPLICIT_CANCEL_HANDSHAKE_TEST_OWNED')
        self.assertEqual(n['hostWslWrapperExit'],0)
        self.assertEqual(n['guestUid'],1000)
        self.assertIs(n['readyRunNonceSourceMatched'],True)
        self.assertIs(n['cancelAckRunNonceSourceMatched'],True)

    def test_worker_cancel_term_kill_reaped(self):
        for key in ('workerIgnoredTerm','workerKilled','workerReaped',
                    'nativeCopyRemoved','nativeRootRemoved'):
            self.assertIs(self.native[key],True,key)

    def test_initial_guest_state_checked_previously(self):
        self.assertEqual(self.pre['matchingPriorTestProcesses'],0)
        self.assertEqual(self.pre['matchingTempRoots'],0)
        self.assertEqual(self.pre['unreadable'],0)
        self.assertEqual(self.pre['uid'],1000)
        self.assertIs(self.pre['safeToStart'],True)
        self.assertGreater(self.pre['seenProc'],0)

    def test_independent_guest_post_snapshot_clean(self):
        self.assertEqual(self.post['result'],'PASS_ZERO_MATCHES')
        self.assertEqual(self.post['guestUid'],1000)
        self.assertEqual(self.post['unreadable'],0)
        self.assertEqual(self.post['matchingTestProcesses'],0)
        self.assertEqual(self.post['ownedTempRoots'],0)
        self.assertGreater(self.post['scannedProc'],0)

    def test_current_three_canonical_source_digest(self):
        manifest=self.summary['sourceCanonicalLfSha256']
        self.assertEqual(set(manifest),{
            'scripts/qa/wsl2_cancel_guest.py',
            'scripts/qa/wsl2_cancel_windows_once.py',
            'tests/test_plat002c_cancel.py',
        })
        for name,want in manifest.items():
            with self.subTest(file=name):
                p=ROOT/name
                self.assertTrue(p.is_file() and not p.is_symlink())
                raw=p.read_bytes()
                self.assertNotIn(b'\r',raw.replace(b'\r\n',b''),name)
                self.assertEqual(hashlib.sha256(
                    raw.replace(b'\r\n',b'\n')).hexdigest(),want,name)

    def test_native_windows_sha_and_linux_lf_pair(self):
        name='scripts/qa/wsl2_cancel_guest.py'
        wanted=self.summary['nativeGuestRawSha256']
        raw=(ROOT/name).read_bytes()
        digest=hashlib.sha256(raw).hexdigest()
        if digest != wanted:
            self.assertNotIn(b'\r',raw,name)
            self.assertGreater(raw.count(b'\n'),0)
            self.assertEqual(hashlib.sha256(
                raw.replace(b'\n',b'\r\n')).hexdigest(),wanted,name)
        self.assertEqual(self.summary['nativeGuestRawSha256'],wanted)

    def test_no_false_host_wrapper_force_cancel_claim(self):
        s=self.summary
        for key in ('hostWslWrapperForceCancelNativeTested',
                    'disconnectAfterReadyNativeTested',
                    'fullPLAT002Accepted','fullD3BAccepted',
                    'hostFilesystemIsolated','separateBrokerHostUidVerified',
                    'mainMerged'):
            self.assertIs(s[key],False,key)
        self.assertIs(self.native['hostWslWrapperForcedCancelVerified'],False)
        self.assertIs(self.native['fullPLAT002Accepted'],False)
        self.assertIs(self.native['fullD3BAccepted'],False)
        self.assertEqual(self.native['realModelCalls'],0)
        self.assertEqual(s['liveModelCalls'],0)
        self.assertIs(s['lostAckAutomaticReplayAllowed'],False)
        self.assertIs(self.native['automaticRetry'],False)

    def test_old_plat002a_fail_not_relabelled(self):
        p=ROOT/'evidence/plat-002a-wsl-19oct/native-win-wsl-identity-01.json'
        self.assertEqual(json.loads(p.read_text(encoding='utf-8'))['result'],'FAIL')

    def test_previous_plat002b_native_did_not_expand_scope(self):
        p=ROOT/'evidence/plat-002b-lifecycle-19oct/native-owned-lifecycle-01.json'
        old=json.loads(p.read_text(encoding='utf-8'))
        self.assertEqual(old['status'],'PASS_SCOPED_TEST_OWNED_CHILDREN')
        self.assertIs(old['wslWrapperCancellationNativeVerified'],False)

if __name__=='__main__':
    unittest.main()
