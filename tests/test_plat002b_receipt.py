"""PLAT-002B native test-owned lifecycle and immutable status custody.

No WSL subprocess is launched by these offline CI tests. The earlier
PLAT-002A native FAIL is preserved, not rewritten as a new successful run.
"""
import hashlib
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
EV=ROOT/'evidence/plat-002b-lifecycle-19oct'

def read(name):
    return json.loads((EV/name).read_text(encoding='utf-8'))

class NativeOwnedLifecycleCustody(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.summary=read('summary.json')
        cls.native=read('native-owned-lifecycle-01.json')
        cls.pre=read('read-only-recovery-preflight.json')
        cls.post=read('post-run-readonly.json')

    def test_native_scoped_pass_exactly_eight_checks(self):
        self.assertEqual(self.native['status'],'PASS_SCOPED_TEST_OWNED_CHILDREN')
        self.assertEqual(self.native['windowsWslWrapperExit'],0)
        guest=self.native['guestReport']
        self.assertEqual(guest['result'],'PASS_SCOPED_LINUX_OWNED_CHILD_LIFECYCLE')
        checks=guest['guestChildChecks']
        self.assertEqual(set(checks),{
            'clean_exit_zero','clean_exit_reaped','term_exit_code','term_reaped',
            'kill_required_after_ignored_term','kill_exit_code','kill_reaped',
            'all_children_reaped'})
        self.assertEqual(guest['guestChildChecksCount'],8)
        self.assertEqual(set(checks.values()),{True})
        self.assertIs(self.native['guestChildLifeCycleVerified'],True)

    def test_windows_vs_guest_source_shas_are_pinned(self):
        measured=self.native['guestSourceSha256']
        self.assertEqual(self.native['guestReport']['sourceSha256'],measured)
        self.assertEqual(self.summary['guestScriptNativeRawSha256'],measured)
        file=ROOT/'scripts/qa/wsl2_owned_lifecycle.py'
        raw=file.read_bytes()
        actual=hashlib.sha256(raw).hexdigest()
        if actual!=measured:
            # Windows original checkout was CRLF; Git/Linux stores LF.
            # One exact, path-scoped LF->CRLF reconstruction only.
            self.assertNotIn(b'\r',raw)
            self.assertGreater(raw.count(b'\n'),0)
            self.assertEqual(hashlib.sha256(
                raw.replace(b'\n',b'\r\n')).hexdigest(),measured)

    def test_exact_three_current_source_shas(self):
        expected={
            'scripts/qa/wsl2_owned_lifecycle.py',
            'scripts/qa/run_plat002b_windows_once.py',
            'tests/test_plat002b_lifecycle.py'
        }
        m=self.summary['sourceCanonicalLfSha256']
        self.assertEqual(set(m),expected)
        for name,digest in m.items():
            with self.subTest(path=name):
                path=ROOT/name
                self.assertTrue(path.is_file() and not path.is_symlink())
                raw=path.read_bytes()
                self.assertNotIn(b'\r',raw.replace(b'\r\n',b''))
                self.assertEqual(hashlib.sha256(
                    raw.replace(b'\r\n',b'\n')).hexdigest(),digest)

    def test_native_rootless_ext_family_and_cleanup(self):
        guest=self.native['guestReport']
        self.assertEqual(guest['guestUid'],1000)
        self.assertIn(guest['linuxFilesystem'],('ext2/ext3','ext4'))
        self.assertEqual(self.summary['nativeLinuxGuestUid'],1000)
        for field in ('sourceCopyExt4ShaVerified','sourceCopyRemoved',
                      'guestOwnedChildrenReaped'):
            self.assertIs(guest[field],True)
        self.assertEqual(self.summary['nativeGuestChecksPass'],8)

    def test_real_process_cleanup_post_snapshot(self):
        self.assertEqual(self.post['result'],
            'PASS_NO_OWNED_PROCESS_OR_TEMP_ROOT_AT_SNAPSHOT')
        self.assertEqual(self.post['matchedOldOrNewLifecycleProcesses'],0)
        self.assertEqual(self.post['ownedTempRootsRemaining'],0)
        self.assertEqual(self.post['procCmdlinesRead'],72)
        self.assertIs(self.post['readOnly'],True)
        self.assertEqual(self.post['queryExitCode'],0)

    def test_prior_owned_process_clear_before_run(self):
        self.assertEqual(self.pre['wslGuestProcSnapshot']['oldBridgeProbeMatches'],0)
        self.assertEqual(self.pre['wslGuestProcSnapshot']['unreadable'],0)
        self.assertIs(self.pre['wslListRunning']['ubuntuRunning'],True)
        self.assertIs(self.pre['oldGuestTerminationProvenAtSnapshot'],True)
        self.assertIs(self.pre['linuxGuestProcessTeardownHistoryFullyKnown'],False)

    def test_not_a_windows_wsl_cancel_or_d3b_certificate(self):
        guest=self.native['guestReport']
        for field in ('hostWslWrapperCancelVerified','hostFilesystemIsolated',
                      'separateHostUidVerified','secureAdapterActivated',
                      'fullD3BAccepted'):
            self.assertIs(guest[field],False)
        for field in ('wslWrapperCancellationNativeVerified',
                      'fullD3BAccepted','noAutomaticRetry'):
            self.assertIs(self.native[field],False if field!='noAutomaticRetry' else True)
        for field in ('hostWslWrapperCancellationVerified','hostFilesystemIsolated',
                      'separateHostUidVerified','brokerBudgetAuthorityJoined',
                      'fullPLAT002Accepted','fullD3BAccepted','mainMerged'):
            self.assertIs(self.summary[field],False)
        self.assertEqual(self.summary['modelCalls'],0)

    def test_previous_native_fail_still_recorded(self):
        old=ROOT/'evidence/plat-002a-wsl-19oct/native-win-wsl-identity-01.json'
        self.assertEqual(json.loads(old.read_text(encoding='utf-8'))['result'],'FAIL')
        self.assertIs(self.summary['priorPlat002aNativeFailurePreserved'],True)

if __name__=='__main__':unittest.main()
