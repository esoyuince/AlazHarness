"""Offline receipts for exact prepared API join; no new native execution."""
import hashlib,json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
E=ROOT/'evidence/d3b-prepared-api-b123a6'
class PreparedJoinReceipt(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r=json.loads((E/'native-002/result.json').read_text(encoding='utf-8'))
        cls.c=json.loads((E/'source-custody.json').read_text(encoding='utf-8'))
        cls.p=json.loads((ROOT/'config/hermes-prepared-api-b123a6.json').read_text(encoding='utf-8'))
    def test_current_twenty_two_and_real_native_cleanup(self):
        self.assertEqual((self.r['result'],self.r['total'],self.r['passed'],self.r['skipped'],self.r['errors'],self.r['failures']),('PASS_NATIVE_PREPARED_THREE_STORE_JOIN',22,22,0,0,0))
        self.assertIs(self.r['actualNativeRunnerAndAdapter'],True);self.assertIs(self.r['sameThreeCallerConnections'],True)
        self.assertTrue(self.r['temporaryRootRemoved']);self.assertEqual(len(self.r['caseEnd']),22)
        for end in self.r['caseEnd']:
            self.assertTrue(end['profileRemoved']);self.assertTrue(end['ownershipReleased']);self.assertEqual(end['pendingTasks'],0)
            self.assertEqual(end['registry'],{'live_generations':0,'retired_generations':0,'total_refcounts':0})
    def test_immutable_imports_current_qa_and_four_native_files(self):
        self.assertEqual(self.c['nativeFeature'],self.p['nativeFeature']);self.assertEqual(self.c['currentNativeFiles'],self.p['resultHashes'])
        self.assertTrue(self.c['allActualImportsMatchImmutableGit']);self.assertEqual(self.c['currentJoinImportCount'],501)
        for name,h in self.r['nativeImports'].items():self.assertEqual(self.c['actualImportedSources'][name]['sha256'],h,name)
        for name,h in self.p['resultHashes'].items():
            self.assertEqual(self.r['nativeImports'][name],h)
            self.assertEqual(hashlib.sha256((E/(name.replace('/','__')+'.current.txt')).read_bytes()).hexdigest(),h)
        self.assertEqual(hashlib.sha256((ROOT/'scripts/qa/b123a6_native_prepared_api.py').read_bytes()).hexdigest(),self.r['qaSha256'])
        self.assertEqual(hashlib.sha256((E/'native-002/result.json').read_bytes()).hexdigest(),self.c['currentJoinResultSha256'])
    def test_readonly_boundary_and_all_real_case_outcomes(self):
        self.assertTrue(self.r['checks'])
        for row in self.r['checks']:
            self.assertEqual((row['sqliteOpens'],row['rawDatabaseOpens'],row['rowChanges']),(0,0,0))
        text=(E/'native-002/tests.txt').read_text(encoding='utf-8')
        cases=[line.split(' ',1)[0] for line in text.splitlines() if line.startswith('test_') and line.endswith(' ... ok')]
        self.assertEqual(len(cases),22);self.assertEqual(set(cases),{e['case'] for e in self.r['caseEnd']})
        for name in ('test_runner_cannot_detach_before_api','test_failed_adapter_cleanup_is_unknown_and_not_retried','test_transaction_in_each_store_refuses_selection_and_disconnect_without_rollback','test_old_bundle_still_rejects_arbitrary_runner_attachment'):
            self.assertIn(name,cases)
    def test_service_drift_failure_preserved_then_same_assertions_pass(self):
        bad=json.loads((E/'service-drift-before/result.json').read_text(encoding='utf-8'))
        self.assertEqual((bad['total'],bad['passed'],bad['failures'],bad['errors']),(2,0,5,0))
        self.assertEqual(bad['qaSha256'],self.r['qaSha256'])
        helper='gateway/platforms/api_server_prepared.py'
        self.assertEqual(hashlib.sha256((E/'api_server_prepared.before-service-drift.py.txt').read_bytes()).hexdigest(),bad['nativeImports'][helper])
        self.assertNotEqual(bad['nativeImports'][helper],self.r['nativeImports'][helper])
        for name,h in self.p['resultHashes'].items():
            if name!=helper:self.assertEqual(bad['nativeImports'][name],h)
        old=json.loads((E/'native-001/result.json').read_text(encoding='utf-8'))
        self.assertEqual((old['total'],old['passed']),(20,20))
        self.assertEqual(hashlib.sha256((E/'native001-qa.py.txt').read_bytes()).hexdigest(),old['qaSha256'])
    def test_prior_native_runner_suite_still_passes_current_source(self):
        r=json.loads((E/'runner-compat/result.json').read_text(encoding='utf-8'))
        self.assertEqual((r['total'],r['passed'],r['skipped'],r['errors'],r['failures']),(28,28,0,0,0))
        self.assertEqual(hashlib.sha256((ROOT/'scripts/qa/r122c4_native_runner.py').read_bytes()).hexdigest(),r['qaSha256'])
        for name,h in r['nativeImports'].items():self.assertEqual(self.c['actualImportedSources'][name]['sha256'],h)
        self.assertIs(r['nativeMethodsReplaced'],False);self.assertIs(r['serviceStarted'],False)
    def test_fresh_patch_bytes_and_failed_fixture_line_endings_not_hidden(self):
        apply=json.loads((E/'patch-application.json').read_text(encoding='utf-8'))
        self.assertEqual(apply['freshApplyExitCode'],0);self.assertNotEqual(apply['duplicateApplyExitCode'],0)
        self.assertEqual(apply['exactResultHashes'],self.p['resultHashes']);self.assertTrue(apply['baseAttributesCopiedUnchanged'])
        self.assertEqual(hashlib.sha256((ROOT/self.p['patchPath']).read_bytes()).hexdigest(),self.p['patchSha256'])
        failed=json.loads((E/'patch-verification-initial-failure.json').read_text(encoding='utf-8'))
        self.assertFalse(failed['byteIdentityPassed']);self.assertFalse(failed['productOrPatchBytesChanged'])
        self.assertTrue(all(v['lineEndingsOnly'] for v in failed['fileDifferences'].values()))
        self.assertEqual(self.p['activation'],'STAGED_NOT_INSTALLED');self.assertTrue(self.p['unqualifiedRunnerConflictPreserved'])
    def test_prepared_only_scope_and_denied_optional_diagnostics(self):
        for key in ('nativeMethodsReplaced','epochAdvancedByAttachment','serviceAdmissionOrListenerActivated','linuxIsolationTested','rootWslAction'):self.assertIs(self.r[key],False,key)
        self.assertIs(self.r['cleanupObjectFaultInjectedExplicitly'],True);self.assertEqual(self.r['providerCalls'],0)
        self.assertFalse(self.p['listenerOrAdmissionQualified']);self.assertFalse(self.p['fullIsolatedServiceQualified'])
        events=self.r['deniedEvents'];self.assertEqual(sum(e['event']=='subprocess.Popen' for e in events),7)
        self.assertEqual(sum(e['event']=='socket.bind' for e in events),1)
        for e in events:
            if e['event']=='socket.bind':self.assertIn('_has_ipv6',e['callers'])
if __name__=='__main__':unittest.main()
