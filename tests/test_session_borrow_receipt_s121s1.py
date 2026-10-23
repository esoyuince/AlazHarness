"""Offline custody of actual SessionStore ownership checks; no native replay."""
import hashlib,json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
E=ROOT/'evidence/d3b-session-borrow-s121s1'
class IndependentSessionReceipt(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r=json.loads((E/'native-002/result.json').read_text(encoding='utf-8'))
        cls.c=json.loads((E/'source-custody.json').read_text(encoding='utf-8'))
        cls.b=json.loads((E/'baseline-native-001/result.json').read_text(encoding='utf-8'))
    def test_current_native_24_and_cleanup(self):
        self.assertEqual((self.r['total'],self.r['passed'],self.r['errors'],self.r['failures'],self.r['skipped']),(24,24,0,0,0))
        self.assertEqual(self.r['result'],'PASS_NATIVE_BORROWED_SESSION_INDEPENDENT')
        self.assertTrue(self.r['temporaryRootRemoved']);self.assertEqual(len(self.r['caseEnd']),24)
        for end in self.r['caseEnd']:
            self.assertTrue(end['temporaryProfileRemoved']);self.assertTrue(end['profileReleased'])
            self.assertEqual(end['registry'],{'live_generations':0,'retired_generations':0,'total_refcounts':0})
    def test_no_extra_connections_or_json_fallback_in_watched_boundary(self):
        rows=self.r['checks'];self.assertTrue(rows)
        for row in rows:
            self.assertEqual(row['sqliteOpens'],0);self.assertEqual(row['rawDatabaseOrJsonOpens'],0)
            if row.get('allowNativeMutationHeaderRead',False):
                self.assertEqual(row['case'],'test_routing_write_failure_cannot_create_json_fallback')
                self.assertGreater(row['nativeMutationHeaderReads'],0)
            else:self.assertEqual(row.get('nativeMutationHeaderReads',0),0)
    def test_default_comparison_keeps_original_behavior(self):
        self.assertEqual(self.b['result'],'BASELINE_CONFIRMED');self.assertTrue(self.b['originalCreatesDifferentHandle'])
        self.assertEqual(self.b['sqliteOpensDuringSessionStoreConstruction'],1)
        self.assertTrue(self.b['callerStateRetainedAfterDefaultCacheClose']);self.assertFalse(self.b['defaultBehaviorIsBug'])
        self.assertEqual(self.b['registryAfterClose']['total_refcounts'],0)
        self.assertTrue(self.b['temporaryProfileRemoved']);self.assertTrue(self.b['profileOwnerReleased'])
    def test_actual_candidate_and_imported_sources_pinned(self):
        for name,h in self.r['nativeImports'].items():
            expected=self.c['candidateSourceHashes'].get(name) or self.c['unalteredImportedSources'][name]['sha256']
            self.assertEqual(h,expected,name)
        for name,h in self.c['candidateSourceHashes'].items():
            self.assertEqual(hashlib.sha256((E/(Path(name).name+'.candidate001.txt')).read_bytes()).hexdigest(),h)
        self.assertEqual(self.c['nativeBase'],'943210584828ccfcfd6adc8eb966ecaa8ca18429')
        self.assertTrue(self.c['allUnchangedImportsMatchImmutableGit']);self.assertFalse(self.c['productChangesInIndependentTask'])
        self.assertEqual(hashlib.sha256((E/'native-002/result.json').read_bytes()).hexdigest(),self.c['nativeResultSha256'])
    def test_qa_bytes_and_all_case_outcomes(self):
        self.assertEqual(hashlib.sha256((ROOT/'scripts/qa/s121s1_native_session_checks.py').read_bytes()).hexdigest(),self.r['qaSha256'])
        self.assertEqual(hashlib.sha256((ROOT/'scripts/qa/s121s1_session_baseline.py').read_bytes()).hexdigest(),self.b['qaSha256'])
        text=(E/'native-002/tests.txt').read_text(encoding='utf-8');names=[s.split(' ',1)[0] for s in text.splitlines() if s.startswith('test_') and s.endswith(' ... ok')]
        self.assertEqual(len(set(names)),24);self.assertEqual(len(names),24)
        self.assertEqual(set(names),{e['case'] for e in self.r['caseEnd']})
    def test_initial_failed_fixture_and_correction_not_hidden(self):
        old=json.loads((E/'native-001/result.json').read_text(encoding='utf-8'))
        self.assertEqual((old['passed'],old['errors'],old['failures']),(21,1,2))
        correction=json.loads((E/'fixture-correction.json').read_text(encoding='utf-8'));self.assertFalse(correction['nativeCandidateChanged'])
        self.assertEqual(hashlib.sha256((E/'native001-independent-qa.py.txt').read_bytes()).hexdigest(),old['qaSha256'])
        for name in self.c['candidateSourceHashes']:self.assertEqual(old['nativeImports'][name],self.r['nativeImports'][name])
        baseline=json.loads((E/'directory-positive-control-stdout.txt').read_bytes())
        self.assertTrue(baseline[0]['sessionsExists']);self.assertEqual(baseline[-2]['entries'],baseline[-1]['entries'])
    def test_explicit_unaccepted_scope(self):
        for name in ('nativeMethodsReplaced','sharedGatewayRunnerBootstrap','apiListenerStarted','fullIsolationTested','upstreamFullSuiteRun','rootWslAction'):
            self.assertIs(self.r[name],False,name)
        self.assertEqual(self.r['providerCalls'],0)
if __name__=='__main__':unittest.main()
