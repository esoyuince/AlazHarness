"""Offline independent native lifecycle receipts, not a runtime replay."""
from pathlib import Path
import hashlib,json,unittest
ROOT=Path(__file__).resolve().parents[1]
E=ROOT/'evidence/d3b-active-lifecycle-a128c6'
def read(name):return json.loads((E/name).read_text(encoding='utf-8'))
class IndependentAdmissionReceipt(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.r=read('native-003/result.json');cls.c=read('source-custody.json')
    def test_current_twenty_eight_and_cleanup(self):
        r=self.r;self.assertEqual((r['result'],r['total'],r['passed'],r['errors'],r['failures'],r['skipped']),('PASS_INDEPENDENT_NATIVE_ADMISSION_LIFECYCLE',28,28,0,0,0))
        self.assertTrue(r['temporaryRootRemoved']);self.assertEqual(len(r['caseEnd']),28)
        for end in r['caseEnd']:
            self.assertTrue(end['temporaryProfileRemoved']);self.assertTrue(end['ownershipReleased']);self.assertEqual(end['pendingTasks'],0)
            self.assertEqual(end['registry'],{'live_generations':0,'retired_generations':0,'total_refcounts':0})
        text=(E/'native-003/tests.txt').read_text(encoding='utf-8');names={s.split(' ',1)[0] for s in text.splitlines() if s.startswith('test_') and s.endswith(' ... ok')}
        self.assertEqual(len(names),28);self.assertEqual(names,{end['case'] for end in r['caseEnd']})
    def test_native_guard_linearization_and_cancelled_actual_tracked_writer(self):
        rows={x['case']:x for x in self.r['races']};self.assertEqual(len(rows),3)
        before=rows['test_before_guard_blocked_writer_loses_to_nonblocking_drain'];self.assertFalse(before['newRowCommitted']);self.assertTrue(before['drainDidNotWaitForSqlMutex'])
        after=rows['test_after_guard_writer_is_preserved_and_finish_refuses_inflight'];self.assertTrue(after['newRowCommitted']);self.assertTrue(after['finishWhileInFlightRefused']);self.assertTrue(after['acceptedQueuedRowRetained'])
        cancelled=rows['test_cancelled_native_tracked_admission_keeps_commit_owner']
        for key in ('nativeTrackedWrite','cancelledCarrier','nativeWriterRetained','acceptedQueuedRowRetained'):self.assertTrue(cancelled[key],key)
    def test_watched_transitions_are_readonly_and_keep_connections(self):
        self.assertTrue(self.r['checks'])
        for row in self.r['checks']:self.assertEqual((row['newConnections'],row['rawDatabaseOpens'],row['sqlRowChanges']),(0,0,0))
    def test_four_failures_and_identical_tests_pass_after_source_fix(self):
        old=read('review-before/result.json');self.assertEqual((old['total'],old['passed'],old['failures'],old['errors']),(4,0,4,0))
        self.assertEqual(old['qaSha256'],self.r['qaSha256']);self.assertTrue(self.c['sameFourFailingTestBytes'])
        failed={n.rsplit('.',1)[-1] for n in old['failureIds']};self.assertTrue(failed<={v['case'] for v in self.r['caseEnd']})
        self.assertEqual(len(failed),4);self.assertNotEqual(self.c['candidate001Hashes'],self.c['candidate002Hashes'])
    def test_current_qa_and_every_actual_native_source_bound(self):
        self.assertEqual(hashlib.sha256((ROOT/'scripts/qa/q128c6_native_lifecycle_checks.py').read_bytes()).hexdigest(),self.r['qaSha256'])
        self.assertEqual(self.r['qaSha256'],self.c['currentQaSha256']);self.assertEqual(len(self.r['nativeImports']),self.c['currentImportCount'])
        for name,h in self.r['nativeImports'].items():
            expected=self.c['candidate002Hashes'].get(name) or self.c['unchangedNativeGitBlobs'][name]['sha256'];self.assertEqual(h,expected,name)
        for version in ('001','002'):
            for name,h in self.c['candidate'+version+'Hashes'].items():self.assertEqual(hashlib.sha256((E/('candidate'+version+'-'+name.replace('/','__')+'.txt')).read_bytes()).hexdigest(),h,name)
        for name,h in self.c['resultHashes'].items():self.assertEqual(hashlib.sha256((E/name).read_bytes()).hexdigest(),h,name)
        self.assertTrue(self.c['allActualImportedSourcesMatched']);self.assertFalse(self.c['productEditedByIndependentTask'])
    def test_baseline_semantics_not_borrowed_activation_or_agent_execution(self):
        r=read('baseline-native-001/result.json');self.assertEqual(r['result'],'PASS_UNCHANGED_NATIVE_ADMISSION_GATE_CONTROL')
        self.assertEqual(r['controlCount'],9);self.assertTrue(all(r['controls'].values()))
        self.assertTrue(r['ordinaryRunnerFlagsOnlyFixture']);self.assertTrue(r['actualNativeAdmissionGuardAndSql']);self.assertFalse(r['borrowedLifecycleActivated'])
        self.assertFalse(r['admittedAgentOrTaskExecuted']);self.assertTrue(r['profileOwnershipReleased']);self.assertTrue(r['temporaryProfileRemoved'])
        for name,h in r['nativeSources'].items():self.assertEqual(h,self.c['unchangedNativeGitBlobs'][name]['sha256'])
        self.assertEqual(hashlib.sha256((ROOT/'scripts/qa/q128c6_native_admission_baseline.py').read_bytes()).hexdigest(),r['qaSha256'])
    def test_early_twenty_two_and_twenty_four_keep_their_own_source(self):
        for label,count,snapshot in (('native-001',22,'native001-qa.py.txt'),('native-002',24,'native002-qa.py.txt')):
            r=read(label+'/result.json');self.assertEqual((r['total'],r['passed'],r['failures'],r['errors']),(count,count,0,0))
            self.assertEqual(hashlib.sha256((E/snapshot).read_bytes()).hexdigest(),r['qaSha256'])
            for name,h in self.c['candidate001Hashes'].items():self.assertEqual(r['nativeImports'][name],h)
    def test_scope_is_native_leaf_lifecycle_not_complete_runtime(self):
        r=self.r;self.assertTrue(r['actualNativeRunnerAuthorityApiStores']);self.assertTrue(r['ledgerWritesDirectWithRealNativeGuards'])
        self.assertTrue(r['explicitFaultsIncludeCallbackPauseAndNativeRegistryRecords'])
        for name in ('nativeMethodsReplaced','admittedAgentOrHttpExecution','harnessOwnerIntegrationTested','linuxIsolationTested','rootWslAction'):self.assertIs(r[name],False,name)
        self.assertEqual(r['providerCalls'],0);self.assertFalse(self.c['fullHarnessOwnerOrConfinementTested'])
if __name__=='__main__':unittest.main()
