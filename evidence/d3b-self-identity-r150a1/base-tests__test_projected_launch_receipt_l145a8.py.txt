"""Offline exact-source negative-experiment evidence; not a new runtime execution."""
import hashlib,json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
E=ROOT/'evidence/d3b-projected-launch-l145a8'
def read(n):return json.loads((E/n).read_text(encoding='utf-8'))
class ProjectedLauncherEvidence(unittest.TestCase):
    def test_actual_linux_five_refusals_before_sql_or_lease(self):
        r=read('receiver-refusal001-result.json');self.assertEqual(r['result'],'PASS');self.assertEqual(len(r['cases']),5)
        self.assertEqual({c['case'] for c in r['cases']},{'missing','malformed','extra-environment','foreign-pid','ordinary-unconfined'})
        for c in r['cases']:
            d=c['result'];self.assertEqual(c['exitCode'],0);self.assertEqual(d['targetExitCode'],2);self.assertEqual(d['forbiddenEffects'],[])
            self.assertEqual(d['uid'],[23001]*3);self.assertEqual(d['gid'],[23003]*3)
            self.assertFalse(any(v['function'] in ('reserve_profile','start','_mount') for v in d['calls']))
            self.assertEqual(any(v['function']=='_live' for v in d['calls']),c['case']=='ordinary-unconfined')
    def test_unconfined_state_was_real_not_mocked_kernel_acceptance(self):
        r=read('receiver-refusal001-result.json')
        for c in r['cases']:
            d=c['result'];self.assertTrue(d['mountAndNamespacesUnchanged']);self.assertFalse(d['productOrOsMethodsReplaced']);self.assertFalse(d['profileCreated'])
            self.assertTrue(d['runpyFixedEntrypointExplicit']);self.assertTrue(d['freshIsolatedInterpreter']);self.assertFalse(d['positiveIsolationAccepted']);self.assertFalse(d['nativeWorkExecuted'])
            self.assertEqual(d['actualKernelObservation']['nnp'],0)
        self.assertTrue(r['temporaryOwnedDirectoryRemoved']);self.assertFalse(r['rootUsed']);self.assertFalse(r['kernelOrInstallActions'])
    def test_actual_linux_source_bytes_match_current_and_manifest(self):
        c=read('source-custody.json');m=read('receiver-refusal001-manifest.json')['files'];r=read('receiver-refusal001-result.json')
        self.assertEqual(m,r['sourceHashes']);self.assertTrue(r['allTransferredSourcesUnchanged'])
        for row in r['cases']:
            for name,h in row['result']['loadedSources'].items():self.assertEqual(m[name],h);self.assertEqual(hashlib.sha256((ROOT/name).read_bytes()).hexdigest(),h)
        for name,h in c['currentSourceHashes'].items():self.assertEqual(hashlib.sha256((ROOT/name).read_bytes()).hexdigest(),h)
    def test_original_error_and_same35_tests_preserved(self):
        old=read('unit001-result.json');new=read('unit002-result.json')
        self.assertEqual(old['exitCode'],1);self.assertEqual(new['exitCode'],0)
        self.assertEqual(old['testSha256'],new['sameTestSha256']);self.assertEqual(hashlib.sha256((E/'original35-tests.py.txt').read_bytes()).hexdigest(),new['sameTestSha256'])
        log=(E/'unit001.txt').read_text(encoding='utf-8');self.assertIn('startup_not_verified',log);self.assertIn('FAILED (errors=1)',log)
        fixed=(E/'unit002.txt').read_text(encoding='utf-8');self.assertIn('Ran 35 tests',fixed);self.assertTrue(fixed.rstrip().endswith('OK'))
    def test_independent29_same_test_true_error_then_pass(self):
        a=read('independent-l145c8/independent004/result.json');b=read('independent-l145c8/independent005/result.json')
        self.assertEqual((a['total'],a['passed'],a['errors'],a['failures']),(29,28,1,0));self.assertEqual((b['total'],b['passed'],b['errors'],b['failures']),(29,29,0,0))
        self.assertEqual(a['driverSha256'],b['driverSha256']);self.assertEqual(hashlib.sha256((E/'independent-l145c8/same29-driver.py.txt').read_bytes()).hexdigest(),b['driverSha256'])
        for n,h in b['sourceHashes'].items():self.assertEqual(hashlib.sha256((ROOT/n).read_bytes()).hexdigest(),h)
        self.assertIn('startup_not_verified',(E/'independent-l145c8/independent004/tests.txt').read_text(encoding='utf-8'))
        proof=read('independent-provenance.json')
        for n,v in proof['files'].items():self.assertEqual(hashlib.sha256((E/'independent-l145c8'/n).read_bytes()).hexdigest(),v['sha256'])
        self.assertTrue(proof['peerNotModified']);self.assertTrue(proof['noDuplicateRunByEvidenceCopy'])
    def test_new_code_is_additive_and_scope_not_native_or_kernel(self):
        baseline=read('baseline.json')['sourceHashes'];self.assertEqual(len(baseline),625)
        for name,h in baseline.items():self.assertEqual(hashlib.sha256((ROOT/name).read_bytes()).hexdigest(),h,name)
        r=read('source-custody.json');self.assertFalse(r['nativeSourceOrKernelPositiveAcceptance'])
        actual=read('unit003-result.json');self.assertEqual(actual['total'],39);self.assertTrue(actual['originalOwnerCodeAndSQLiteCloseReal']);self.assertTrue(actual['nativeStoreConstructorsColdBoundariesDoubled']);self.assertFalse(actual['currentKernelAccepted'])
if __name__=='__main__':unittest.main()
