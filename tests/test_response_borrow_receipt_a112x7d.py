"""Offline custody of actual A112X7D native tests; no native rerun here."""
import hashlib
import json
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
E=ROOT/'evidence/d3b-api-storage-a112x7d'
class ResponseBorrowReceipt(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.win=json.loads((E/'windows-001/result.json').read_text(encoding='utf-8'))
        cls.linux=json.loads((E/'linux-001-stdout.txt').read_bytes())
        cls.manifest=json.loads((E/'patch-manifest.json').read_text(encoding='utf-8'))
    def test_actual_native_tests_both_platforms_and_no_activation(self):
        for result in (self.win,self.linux['proof']):
            self.assertEqual(result['result'],'PASS_SCOPED_NATIVE_RESPONSE_BORROW')
            self.assertEqual((result['total'],result['passed'],result['errors'],result['failures'],result['skipped']),(24,24,0,0,0))
            for key in ('nativeMethodsReplaced','httpAdapterStarted','fullIsolationTested','healthyBusyHttpPolicyImplemented','nativeFullSuiteRun'):
                self.assertIs(result[key],False)
            self.assertIs(result['profileOwnerReleased'],True);self.assertIs(result['temporaryProfilesRemoved'],True)
            self.assertEqual(result['providerCalls'],0)
        self.assertEqual(self.linux['exitCode'],0);self.assertEqual(self.linux['uid'],23001)
        self.assertIs(self.linux['sourcesUnchanged'],True);self.assertIs(self.linux['temporaryCodeRemoved'],True)
    def test_exact_probe_and_patch_source_custody(self):
        qa=hashlib.sha256((ROOT/'scripts/qa/a112x7d_response_probe.py').read_bytes()).hexdigest()
        self.assertEqual(self.win['qaSha256'],qa);self.assertEqual(self.linux['proof']['qaSha256'],qa)
        self.assertEqual(self.manifest['qaSha256'],qa)
        self.assertEqual(hashlib.sha256((ROOT/self.manifest['patchPath']).read_bytes()).hexdigest(),self.manifest['patchSha256'])
        for result in (self.win,self.linux['proof']):
            for name,digest in result['nativeSources'].items():
                self.assertEqual(self.manifest['nativeSources'][name]['sha256'],digest)
        for name,digest in self.manifest['patchedFiles'].items():
            self.assertEqual(self.win['nativeSources'][name],digest)
            self.assertEqual(self.linux['proof']['nativeSources'][name],digest)
    def test_exact_patch_application_and_duplicate_refusal(self):
        r=json.loads((E/'patch-application.json').read_text(encoding='utf-8'))
        self.assertEqual((r['checkExit'],r['applyExit']),(0,0));self.assertNotEqual(r['repeatExit'],0)
        self.assertEqual(r['afterSources'],self.manifest['patchedFiles'])
        self.assertEqual(r['patchSha256'],self.manifest['patchSha256'])
        self.assertIs(r['temporaryExportRemoved'],True);self.assertIs(r['secondApplicationRejected'],True)
        self.assertIs(r['originalVendorEdited'],False)
    def test_native_fork_commit_kept_separate_from_active_pin(self):
        commit=json.loads((E/'native-fork-commit.json').read_text(encoding='utf-8'))
        self.assertEqual(commit['sourceSha256'],self.manifest['patchedFiles'])
        self.assertEqual(commit['base'],self.manifest['baseNativePin']);self.assertNotEqual(commit['base'],commit['commit'])
        self.assertIs(commit['pushed'],False);self.assertIs(commit['installedVendorMainUntouched'],True)
        self.assertIs(self.manifest['canonicalSourceLockUpdated'],False)
    def test_all_twenty_four_case_outcomes_present(self):
        logs=[(E/'windows-001/tests.txt').read_text(encoding='utf-8'),self.linux['log']]
        sets=[]
        for log in logs:
            names=[line.split(' ',1)[0] for line in log.splitlines() if line.startswith('test_') and line.endswith(' ... ok')]
            self.assertEqual(len(names),24);self.assertEqual(len(set(names)),24);sets.append(set(names))
        self.assertEqual(sets[0],sets[1])
        self.assertIn('test_default_mode_keeps_native_separate_reader_behavior',sets[0])
        self.assertIn('test_unknown_identity_does_not_become_retryable',sets[0])
    def test_dependency_transport_matches_previous_immutable_inventory(self):
        previous=json.loads((ROOT/'evidence/d3b-native-stores-h105e/native-source-inventory.json').read_text(encoding='utf-8'))
        actual={n.removeprefix('dependencies/'):h for n,h in self.linux['sourceSha256'].items() if n.startswith('dependencies/')}
        self.assertEqual(actual,previous['dependency']['sourceSha256']);self.assertEqual(len(actual),31)
        self.assertIs(self.linux['packageInstall'],False);self.assertIs(self.linux['rootUsed'],False)
    def test_line_endings_never_silently_relabelled_as_original_bytes(self):
        record=json.loads((E/'patch-line-ending-review.json').read_text(encoding='utf-8'))
        self.assertIs(record['attempts'][0]['sourceMatches'],False)
        self.assertIs(record['attempts'][1]['sourceMatches'],True)
        self.assertIs(record['sourcePatchModified'],False)
        self.assertIs(record['onlyTemporaryRepoSettingChanged'],True)

if __name__=='__main__':unittest.main()
