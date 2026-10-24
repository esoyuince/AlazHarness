"""Offline evidence binding of native publication tests; no new native execution."""
import hashlib,json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
E=ROOT/'evidence/d3b-api-publication-c131p1'
def read(name):return json.loads((E/name).read_text(encoding='utf-8'))
class PublicationReceipt(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.r=read('native-003/publication-result.json');cls.c=read('source-custody.json')
    def test_current_twenty_one_pass_and_owned_fixture_cleanup(self):
        r=self.r;self.assertEqual((r['result'],r['total'],r['passed'],r['errors'],r['failures'],r['skipped']),('PASS_INDEPENDENT_NATIVE_API_PUBLICATION',21,21,0,0,0))
        self.assertTrue(r['temporaryRootRemoved']);self.assertEqual(len(r['caseEnd']),21)
        for e in r['caseEnd']:
            self.assertTrue(e['temporaryProfileRemoved']);self.assertTrue(e['ownershipReleased']);self.assertEqual(e['pendingTasks'],0)
            self.assertEqual(e['registry'],{'live_generations':0,'retired_generations':0,'total_refcounts':0})
        log=(E/'native-003/tests.txt').read_text(encoding='utf-8');names={line.split(' ',1)[0] for line in log.splitlines() if line.startswith('test_') and line.endswith(' ... ok')}
        self.assertEqual(len(names),21);self.assertEqual(names,{e['case'] for e in r['caseEnd']})
    def test_native_api_retry_and_retirement_cases_in_actual_execution(self):
        observations=self.r['apiAdmissionObservations'];self.assertTrue(observations)
        for e in observations:self.assertEqual(e['status'],'queued');self.assertTrue(e['sameAuthority']);self.assertFalse(e['wholeTurnScheduled'])
        self.assertEqual(sum(e['case']=='test_real_api_admission_then_exact_retry_is_one_row' for e in observations),2)
        for name in ('test_same_request_changed_payload_refused','test_same_request_other_target_refused','test_settled_native_leaf_retirement_preserves_history_then_detaches'):
            self.assertIn(name,{e['case'] for e in observations})
        settled=next(e for e in self.r['caseEnd'] if e['case']=='test_settled_native_leaf_retirement_preserves_history_then_detaches')
        self.assertEqual(settled['productBeforeFixtureCleanup'],{'binding':'DETACHED','api':'DETACHED'})
    def test_publication_observation_does_not_dispatch_recovery_voice_or_status(self):
        p={e['case']:e for e in self.r['publicationObservations']}
        self.assertEqual(p['test_publication_never_recovers_or_wires_voice']['recoveryOrVoiceCalls'],[])
        self.assertEqual(p['test_publication_never_recovers_or_wires_voice']['pendingTasks'],0)
        current=p['test_native_async_admission_does_not_publish_unowned_gateway_status'];self.assertEqual(current['runtimeStatusCalls'],[]);self.assertFalse(current['statusFileCreated'])
        self.assertTrue(self.r['checks'])
        for e in self.r['checks']:self.assertEqual((e['newConnections'],e['rawDatabaseOpens'],e['sqlRowChanges']),(0,0,0))
    def test_same_two_failing_assertions_pass_without_qa_change(self):
        before=read('regression-before/publication-result.json');self.assertEqual((before['total'],before['passed'],before['errors'],before['failures']),(2,0,0,2))
        self.assertEqual(before['driverSha256'],self.r['driverSha256']);self.assertTrue(self.c['sameBeforeFixRegressionDriver'])
        bad=before['publicationObservations'][0];self.assertEqual(bad['runtimeStatusCalls'],['publish_runtime_status']*3);self.assertTrue(bad['statusFileCreated'])
        old=read('native-001/publication-result.json');self.assertEqual((old['total'],old['passed'],old['errors'],old['failures']),(20,13,6,1))
        self.assertEqual(hashlib.sha256((E/'native001-driver.py.txt').read_bytes()).hexdigest(),old['driverSha256'])
    def test_final_native_and_qa_bytes_pinned(self):
        self.assertEqual(self.c['sourceCount'],len(self.r['nativeImports']))
        for name,h in self.r['nativeImports'].items():self.assertEqual(h,self.c['finalCandidateHashes'].get(name) or self.c['unchangedNativeGitBlobs'][name]['sha256'],name)
        for name,h in self.c['finalCandidateHashes'].items():self.assertEqual(hashlib.sha256((E/('candidate003-'+name.replace('/','__')+'.txt')).read_bytes()).hexdigest(),h,name)
        self.assertEqual(hashlib.sha256((ROOT/'scripts/qa/q131p1_native_publication_checks.py').read_bytes()).hexdigest(),self.r['driverSha256'])
        self.assertEqual(hashlib.sha256((ROOT/'scripts/qa/q128c6_native_lifecycle_checks.py').read_bytes()).hexdigest(),self.r['fixtureSha256'])
        for name,h in self.c['resultHashes'].items():self.assertEqual(hashlib.sha256((E/name).read_bytes()).hexdigest(),h,name)
        self.assertTrue(self.c['allActualImportedSourcesVerified']);self.assertFalse(self.c['productCodeChangedByIndependentQa'])
    def test_annotation_only_source_version_not_conflated(self):
        prior=read('native-002/publication-result.json');self.assertEqual((prior['total'],prior['passed'],prior['errors'],prior['failures']),(21,21,0,0))
        self.assertEqual(prior['driverSha256'],self.r['driverSha256'])
        final=read('candidate-003.json');self.assertEqual(final['priorDifferences'],['gateway/run_adapters.py']);self.assertFalse(final['runtimeLogicChangedFromCandidate002'])
        a=read('candidate-002.json')['sources'];b=final['sources'];self.assertEqual({n for n in a if a[n]!=b[n]},{'gateway/run_adapters.py'})
    def test_scope_not_authenticated_http_or_agent_or_harness_acceptance(self):
        r=self.r;self.assertTrue(r['realNativeAsyncApiAdmission']);self.assertTrue(r['actualNativeRunnerAuthorityApiStores'])
        self.assertTrue(r['publicationAndDetachFaultObjectsExplicit'])
        for key in ('nativeMethodsReplaced','completeTurnOrModelExecuted','harnessSourceEnvelopeQualified','harnessOwnerIntegrationTested','linuxIsolationTested','rootWslAction'):self.assertIs(r[key],False,key)
        self.assertEqual(r['providerCalls'],0)
        unknown=next(e for e in r['caseEnd'] if e['case']=='test_adapter_map_drift_during_awaited_cleanup_never_deletes_foreign_entry')
        self.assertEqual(unknown['productBeforeFixtureCleanup']['api'],'CLOSE_UNKNOWN')
if __name__=='__main__':unittest.main()
