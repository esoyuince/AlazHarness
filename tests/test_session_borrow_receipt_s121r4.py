"""Offline receipts for actual native SessionStore contract; not native re-execution."""
import hashlib,json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
E=ROOT/'evidence/d3b-session-borrow-s121r4'
class SessionBorrowProof(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result=json.loads((E/'native-002/result.json').read_text(encoding='utf-8'))
        cls.custody=json.loads((E/'native-source-custody.json').read_text(encoding='utf-8'))
        cls.config=json.loads((ROOT/'config/hermes-session-borrow-s121r4.json').read_text(encoding='utf-8'))
    def test_native_terminal_and_scope(self):
        r=self.result;self.assertEqual((r['result'],r['total'],r['passed'],r['errors'],r['failures'],r['skipped']),('PASS_NATIVE_SESSION_BORROW',23,23,0,0,0))
        for key in ('ownershipReleased','temporaryImportHomeRemoved'):self.assertIs(r[key],True)
        for key in ('nativeClassesReplaced','callerStateInstalledAfterConstructor','fullGatewayRunnerTested','borrowedApiGuardChanged','httpListenerStarted','rootWslAction'):self.assertIs(r[key],False)
        self.assertEqual(r['providerCalls'],0);self.assertEqual(r['registry'],{'live_generations':0,'retired_generations':0,'total_refcounts':0})
    def test_exact_tested_qa_and_three_patched_source_hashes(self):
        qa=ROOT/'scripts/qa/s121r4_native_session_borrow.py'
        self.assertEqual(hashlib.sha256(qa.read_bytes()).hexdigest(),self.result['qaSha256'])
        intent=json.loads((E/'native-002-intent.json').read_text(encoding='utf-8'))
        self.assertEqual(intent['candidateSources'],self.config['resultHashes'])
        self.assertEqual(intent['qaSha256'],self.result['qaSha256'])
        self.assertEqual(len(self.config['resultHashes']),3)
        for n,h in self.config['resultHashes'].items():self.assertEqual(h,self.result['nativeImports'][n])
    def test_original_native_imports_are_immutable_except_selected_patch(self):
        self.assertEqual(self.custody['nativeBase'],'943210584828ccfcfd6adc8eb966ecaa8ca18429')
        actual={n:v['sha256'] for n,v in self.custody['actualUnchangedImports'].items()}|self.custody['resultHashes']
        self.assertEqual(actual,self.result['nativeImports']);self.assertEqual(len(actual),self.custody['actualImportCount'])
        self.assertTrue(self.custody['borrowedApiGuardUnchanged']);self.assertFalse(self.custody['installedVendorOrSourceLockChanged'])
    def test_fresh_patch_application_and_no_activation(self):
        p=self.config['patchPath'];h=hashlib.sha256((ROOT/p).read_bytes()).hexdigest();self.assertEqual(h,self.config['patchSha256'])
        r=json.loads((E/'patch-application.json').read_text(encoding='utf-8'))
        self.assertTrue(r['exactFreshApply']);self.assertTrue(r['duplicateApplyRefused']);self.assertTrue(r['temporaryExportRemoved'])
        self.assertEqual(r['patchSha256'],h);self.assertEqual(r['resultHashes'],self.config['resultHashes'])
        self.assertEqual(self.config['activation'],'STAGED_NOT_INSTALLED');self.assertFalse(self.config['sharedCanonicalRunnerQualified'])
        self.assertNotEqual(self.config['nativeBase'],self.config['nativeFeature'])
    def test_all_behavior_cases_present_not_added_to_full_count(self):
        log=(E/'native-002/tests.txt').read_text(encoding='utf-8')
        cases=[line.split(' ',1)[0] for line in log.splitlines() if line.startswith('test_') and line.endswith(' ... ok')]
        self.assertEqual(len(cases),23);self.assertEqual(len(set(cases)),23)
        for name in ('test_constructor_selectors_and_detach_have_no_extra_open_or_row_write','test_routing_sql_failure_does_not_fall_back_to_json','test_profile_release_reacquire_is_not_original_ownership','test_default_native_constructor_still_registry_owned','test_real_primary_routing_and_native_admission_share_caller_state'):self.assertIn(name,cases)
    def test_watched_opens_zero_and_import_external_attempts_recorded(self):
        a=self.result['audit'];self.assertEqual(a['connections'],0)
        self.assertEqual(len(a['deniedEvents']),a['networkDenied'])
        # Historic field name covers subprocess attempts too; these are Git version probes.
        self.assertTrue(all(e['event']=='subprocess.Popen' for e in a['deniedEvents']))
        self.assertTrue(all('_git_version_info' in e['callers'] for e in a['deniedEvents']))
    def test_initial_failed_directory_assumption_remains_failed(self):
        old=json.loads((E/'native-001/result.json').read_text(encoding='utf-8'));self.assertEqual((old['total'],old['passed'],old['failures']),(23,21,2))
        record=json.loads((E/'scaffold-expectation-correction.json').read_text(encoding='utf-8'));self.assertFalse(record['nativeProductChanged']);self.assertTrue(record['firstFailureRetained'])
        self.assertEqual(hashlib.sha256((E/'qa-before-scaffold-correction.py.txt').read_bytes()).hexdigest(),old['qaSha256'])
        a=json.loads((E/'native-001-intent.json').read_text(encoding='utf-8'));b=json.loads((E/'native-002-intent.json').read_text(encoding='utf-8'))
        self.assertEqual(a['candidateSources'],b['candidateSources'])
if __name__=='__main__':unittest.main()
