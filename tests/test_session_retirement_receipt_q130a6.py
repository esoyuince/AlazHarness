"""Offline retirement evidence contracts; no native rerun or runtime promotion."""
import ast,hashlib,json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
E=ROOT/'evidence/d3b-native-drain-c130a6'
def read(n):return json.loads((E/n).read_text(encoding='utf-8'))
class IndependentRetirementReceipt(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.r=read('native-002/retirement-result.json');cls.c=read('source-custody.json')
    def test_final_own_twenty_four_and_real_fixture_cleanup(self):
        r=self.r;self.assertEqual((r['result'],r['total'],r['passed'],r['errors'],r['failures'],r['skipped']),('PASS_INDEPENDENT_NATIVE_SESSION_RETIREMENT',24,24,0,0,0))
        self.assertTrue(r['selectedOwnMethodsOnly']);self.assertEqual(r['newRetirementMethodCount'],24);self.assertTrue(r['temporaryRootRemoved'])
        log=(E/'native-002/tests.txt').read_text(encoding='utf-8');names={line.split(' ',1)[0] for line in log.splitlines() if line.startswith('test_') and line.endswith(' ... ok')}
        self.assertEqual(len(names),24);self.assertEqual(names,{v['case'] for v in r['caseEnd']})
        for end in r['caseEnd']:
            self.assertTrue(end['temporaryProfileRemoved']);self.assertTrue(end['ownershipReleased']);self.assertEqual(end['pendingTasks'],0);self.assertEqual(end['registry']['total_refcounts'],0)
    def test_memory_retirement_keeps_all_durable_data_and_retry(self):
        row=self.r['retirementChecks'][0];self.assertEqual(row['retired'],1)
        for key in ('allThreeDatabaseDumpsUnchanged','nativeRetryIdentityRetained','callerConnectionsAndProfileRemainOpen'):self.assertTrue(row[key])
        for row in self.r['checks']:self.assertEqual((row['newConnections'],row['rawDatabaseOpens'],row['sqlRowChanges']),(0,0,0))
        names={v['case'] for v in self.r['caseEnd']}
        for case in ('test_actual_detached_fanout_writer_is_still_obligation','test_real_physical_thread_retained_after_cancelled_carrier','test_two_sessions_are_preflighted_all_before_any_memory_removal','test_queued_and_unknown_rows_are_not_cleared_to_retire'):self.assertIn(case,names)
    def test_four_actual_refusal_regressions_preserved_then_fixed(self):
        old=read('review-before/retirement-result.json');self.assertEqual((old['total'],old['passed'],old['errors'],old['failures']),(4,0,0,4))
        self.assertEqual(old['retirementQaSha256'],self.r['retirementQaSha256']);self.assertTrue(self.c['sameFourFailingQaBytes'])
        self.assertEqual(len(old['failureIds']),4);self.assertNotEqual(self.c['candidate001Hashes'],self.c['candidate002Hashes'])
        first=read('native-001/retirement-result.json');self.assertEqual((first['total'],first['passed']),(20,20))
        snapshot=(E/'native001-retirement-qa.py.txt').read_bytes();self.assertEqual(hashlib.sha256(snapshot).hexdigest(),first['retirementQaSha256'])
        def bodies(raw):return {n.name:ast.dump(n,include_attributes=False) for n in ast.walk(ast.parse(raw)) if isinstance(n,ast.FunctionDef) and n.name.startswith('test_')}
        current=bodies((ROOT/'scripts/qa/q130a6_native_retirement.py').read_bytes());before=bodies(snapshot)
        self.assertEqual(len(before),20)
        for name,body in before.items():self.assertEqual(current[name],body)
    def test_all_native_and_qa_bytes_match_fixed_generations(self):
        self.assertTrue(self.c['allActualImportsMatched']);self.assertFalse(self.c['nativeProductEditedByIndependentTask'])
        self.assertEqual(len(self.r['nativeImports']),self.c['nativeImportCounts']['native-002/retirement-result.json'])
        for name,h in self.r['nativeImports'].items():self.assertEqual(h,self.c['candidate002Hashes'].get(name) or self.c['baseGitSources'][name]['sha256'])
        for version in ('001','002'):
            for name,h in self.c['candidate'+version+'Hashes'].items():self.assertEqual(hashlib.sha256((E/('candidate'+version+'-'+name.replace('/','__')+'.txt')).read_bytes()).hexdigest(),h)
        for file,h in self.c['resultHashes'].items():self.assertEqual(hashlib.sha256((E/file).read_bytes()).hexdigest(),h)
        for file,h in (('q130a6_native_retirement.py',self.r['retirementQaSha256']),('q128c6_native_lifecycle_checks.py',self.r['fixtureQaSha256'])):self.assertEqual(hashlib.sha256((ROOT/'scripts/qa'/file).read_bytes()).hexdigest(),h)
    def test_original_api_boundary_preserves_partial_session_effects(self):
        r=read('native-api-control-001/result.json');self.assertEqual(r['result'],'OBSERVED_UNCHANGED_NATIVE_API_ROUTE_BOUNDARY')
        self.assertEqual(r['refusal']['reason'],'runtime_draining');self.assertEqual((r['durableSessionRows'],r['durableAdmissionRows'],r['liveSessionCount'],r['runnerAdapterCount']),(1,0,1,0))
        self.assertTrue(r['allConnectionsOpen']);self.assertTrue(r['profileHeld']);self.assertFalse(r['harnessGateBypassed']);self.assertFalse(r['wholeAgentOrWorkerScheduled'])
        self.assertEqual(hashlib.sha256((E/'native-api-control001-qa.py.txt').read_bytes()).hexdigest(),r['qaSha256'])
    def test_native_terminal_leaf_does_not_implicitly_retire_session(self):
        r=read('native-retained-session-001/result.json');self.assertEqual(r['result'],'OBSERVED_NATIVE_TERMINAL_LEAF_WITH_RETAINED_SESSION')
        q=r['completedLeafRetirementBoundary'];self.assertEqual(q['nativePhase'],'DRAINING')
        for key in ('terminalRow','sameAdmissionId','liveSessionRetained','routingEntriesRetained','durableSessionPreserved','terminalAdmissionPreserved','noSqlWritesByDrainObservation'):self.assertTrue(q[key],key)
        self.assertTrue(r['temporaryProfileRemoved']);self.assertTrue(r['profileReleased'])
        self.assertEqual(hashlib.sha256((ROOT/'scripts/qa/q130a6_native_api_control.py').read_bytes()).hexdigest(),r['qaSha256'])
    def test_no_whole_agent_harness_or_kernel_acceptance(self):
        r=self.r
        for key in ('nativeMethodsReplaced','sameOwnerHarnessIntegrationTested','wholeApiAgentTurnExecuted','admittedAgentOrHttpExecution','harnessOwnerIntegrationTested','linuxIsolationTested','rootWslAction'):self.assertFalse(r[key],key)
        self.assertTrue(r['actualApiSessionBinding']);self.assertTrue(r['terminalWorkUsesGuardedNativeLeafSettlement']);self.assertEqual(r['providerCalls'],0)
        review=read('readonly-review-handoff.json');self.assertTrue(review['sourceOnly']);self.assertFalse(review['testsExecutedByReviewer']);self.assertEqual(review['state'],'COMPLETED_ARCHIVED')
        self.assertIn('session agent-cache release completion barrier',review['remainingFullRuntimeGates'])
if __name__=='__main__':unittest.main()
