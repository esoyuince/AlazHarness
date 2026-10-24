"""Independent I133 native records: offline source/case checks, no native rerun."""
from pathlib import Path
import hashlib,json,unittest
ROOT=Path(__file__).resolve().parents[1]
E=ROOT/'evidence/d3b-api-owner-qa-i133c6'
def read(name):return json.loads((E/name).read_text(encoding='utf-8'))
class ApiOwnerIndependentReceipt(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.r=read('native-002/independent-result.json');cls.old=read('native-001/independent-result.json');cls.c=read('source-custody.json')
    def test_current_twenty_three_cases_terminal(self):
        r=self.r;self.assertEqual((r['result'],r['total'],r['passed'],r['errors'],r['failures'],r['skipped']),('PASS_INDEPENDENT_CANONICAL_API_OWNER_WITH_OS_DOUBLES',23,23,0,0,0))
        log=(E/'native-002/tests.txt').read_text(encoding='utf-8');names={s.split(' ',1)[0] for s in log.splitlines() if s.startswith('test_') and s.endswith(' ... ok')}
        self.assertEqual(len(names),23);self.assertEqual(names,{v['case'] for v in r['caseEnd']})
    def test_original_failure_same_tests_now_pass(self):
        self.assertEqual((self.old['total'],self.old['passed'],self.old['errors'],self.old['failures']),(23,22,0,1))
        self.assertEqual(self.old['driverSha256'],self.r['driverSha256']);self.assertEqual(self.old['failureIds'],['__main__.OwnerPublication.test_trace_fault_after_native_retirement_retains_unknown'])
        log=(E/'native-001/tests.txt').read_text(encoding='utf-8');self.assertIn("('ATTACHED', 'DRAINING')",log);self.assertIn("('ADMISSION_UNKNOWN', 'UNKNOWN')",log)
        self.assertEqual(self.c['oneActualFailurePreserved'],self.old['failureIds'])
    def test_native_source_matches_immutable_feature(self):
        self.assertEqual(self.r['nativeFeature'],'5ff88189832c3ff71bf8fd2f6b2ff05bb8bb4979');self.assertEqual(self.c['nativeFeature'],self.r['nativeFeature'])
        self.assertEqual(self.r['nativeImports'],{k:v['sha256'] for k,v in self.c['nativeImports'].items()});self.assertEqual(self.r['nativeImports'],self.old['nativeImports'])
        self.assertEqual(len(self.r['nativeImports']),self.c['nativeImportCount']);self.assertTrue(self.c['allNativeImportsWithinQualifiedManifest']);self.assertFalse(self.c['nativeSourceEdited'])
    def test_exact_candidate_generations_and_driver_bound(self):
        for version,r in (('001',self.old),('002',self.r)):
            m=read('candidate-'+version+'.json')
            for name,h in m['sourceHashes'].items():
                self.assertEqual(r['currentSourceHashes'][name],h)
                self.assertEqual(hashlib.sha256((E/('candidate'+version+'-'+name.replace('/','__')+'.txt')).read_bytes()).hexdigest(),h)
        a=read('candidate-001.json')['sourceHashes'];b=read('candidate-002.json')['sourceHashes'];self.assertEqual([k for k in a if a[k]!=b[k]],['packages/claw-hermes/gateway_consumer_api.py'])
        self.assertEqual(hashlib.sha256((ROOT/'scripts/qa/i133c6_native_owner_publication.py').read_bytes()).hexdigest(),self.r['driverSha256'])
        self.assertEqual(self.c['currentResultSha256'],hashlib.sha256((E/'native-002/independent-result.json').read_bytes()).hexdigest())
        self.assertEqual(self.c['previousResultSha256'],hashlib.sha256((E/'native-001/independent-result.json').read_bytes()).hexdigest())
    def test_actual_api_acceptance_and_memory_only_retirement_scope(self):
        cases={r['case']:r for r in self.r['observations']};self.assertEqual(len(cases),2)
        queued=cases['test_actual_api_admission_stays_queued_and_blocks_clean_finish'];self.assertTrue(queued['realApiAdmission']);self.assertTrue(queued['actualOwnerSame']);self.assertTrue(queued['queuedRowRetained']);self.assertFalse(queued['queuedPayloadExecuted'])
        retired=cases['test_leaf_settlement_native_retirement_preserves_durable_history'];self.assertTrue(retired['actualApiAdmitted']);self.assertTrue(retired['leafSettlementExplicitNotPayloadExecution']);self.assertTrue(retired['nativeRetirementOnlyMemory']);self.assertTrue(retired['originalOwnerClosesAfterDetach'])
    def test_watched_transition_boundaries_no_new_store_or_write(self):
        self.assertTrue(self.r['checks'])
        for row in self.r['checks']:self.assertEqual((row['newConnections'],row['rawDatabaseOpens'],row['rowChanges']),(0,0,0))
    def test_all_owned_fixtures_removed_and_references_released(self):
        self.assertTrue(self.r['temporaryRootRemoved']);self.assertEqual(len(self.r['caseEnd']),23)
        for end in self.r['caseEnd']:
            self.assertTrue(end['profileRemoved']);self.assertTrue(end['nativeOwnershipReleased']);self.assertEqual(end['registry'],{'live_generations':0,'retired_generations':0,'total_refcounts':0})
    def test_boundaries_not_full_agent_http_or_linux_proof(self):
        self.assertTrue(self.r['originalOwnerAndNativeConstructorsAndSqlReal']);self.assertTrue(self.r['linuxActorLeaseMetadataMountColdDoubled']);self.assertTrue(self.r['actualProgrammaticApiAdmission']);self.assertTrue(self.r['traceFaultsAndMemoryCleanupFixtureExplicit'])
        for key in ('nativeProductMethodsReplaced','wholeApiTurnOrAgentExecuted','linuxConfinementTested','rootWslAction','queuedWorkRetiredAutomatically'):self.assertFalse(self.r[key],key)
        self.assertEqual(self.r['providerCalls'],0);self.assertFalse(self.c['producerSourceEditedByIndependentReview'])
        # Reused old scaffold metadata is retained, not silently used as current native identity.
        raw=read('native-002/result.json');self.assertEqual(raw['nativeFeature'],'1b7b31e14451baf1d56c3edbfa2cea69a8f7940c')
        self.assertEqual(raw['nativeImports'],self.r['nativeImports']);self.assertNotEqual(raw['nativeFeature'],self.r['nativeFeature'])
if __name__=='__main__':unittest.main()
