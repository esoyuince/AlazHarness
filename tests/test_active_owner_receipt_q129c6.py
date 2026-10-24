"""Offline source/outcome receipts for independent active-owner integration.
These checks do not execute native or claim Linux/agent/HTTP acceptance.
"""
import hashlib,json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
E=ROOT/'evidence/d3b-active-owner-b129c6'
def read(name):return json.loads((E/name).read_text(encoding='utf-8'))
class ActiveOwnerIndependentReceipt(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.r=read('native-001/result.json');cls.c=read('source-custody.json');cls.snapshot=read('candidate-001.json');cls.base=read('baseline.json')
    def test_twenty_four_terminal_outcomes_and_cleanup(self):
        r=self.r;self.assertEqual((r['result'],r['total'],r['passed'],r['errors'],r['failures'],r['skipped']),('PASS_INDEPENDENT_ACTIVE_OWNER_WITH_OS_DOUBLES',24,24,0,0,0))
        self.assertTrue(r['temporaryRootRemoved']);self.assertEqual(len(r['caseEnd']),24)
        text=(E/'native-001/tests.txt').read_text(encoding='utf-8');names={l.split(' ',1)[0] for l in text.splitlines() if l.startswith('test_') and l.endswith(' ... ok')}
        self.assertEqual(len(names),24);self.assertEqual(names,{v['case'] for v in r['caseEnd']})
        for end in r['caseEnd']:
            self.assertTrue(end['temporaryProfileRemoved']);self.assertTrue(end['ownershipReleased']);self.assertEqual(end['registry'],{'live_generations':0,'retired_generations':0,'total_refcounts':0})
    def test_original_native_owner_close_order_was_actually_exercised(self):
        ends={v['case']:v['beforeFixtureCleanup'] for v in self.r['caseEnd']}
        for name in ('test_full_empty_lifecycle_closes_only_original_owner_then_lease','test_claimed_leaf_settles_during_drain_and_owner_can_close'):
            self.assertEqual(ends[name],{'owner':'CLOSED','consumer':'DETACHED','phase':'DETACHED'})
        self.assertEqual(ends['test_queued_work_passes_identity_but_not_finish']['owner'],'VERIFIED')
        self.assertEqual(ends['test_queued_work_passes_identity_but_not_finish']['phase'],'DRAINING')
    def test_two_real_writer_races_keep_same_owner(self):
        rows={v['case']:v for v in self.r['races']};self.assertEqual(len(rows),2)
        blocked=rows['test_seal_does_not_wait_for_blocked_native_writer'];self.assertTrue(blocked['drainReturnedWithMutexHeld']);self.assertFalse(blocked['newAdmissionCommitted'])
        cancelled=rows['test_cancelled_tracked_writer_preserved_through_original_owner']
        for key in ('nativeTrackedWriter','callerCancelled','acceptedQueuedRowRetained','ownerCloseRefused'):self.assertTrue(cancelled[key],key)
    def test_watched_observations_readonly_and_unknowns_preserved(self):
        self.assertTrue(self.r['checks'])
        for row in self.r['checks']:self.assertEqual((row['newConnections'],row['rawDatabaseOpens'],row['rowChanges']),(0,0,0))
        ends={v['case']:v['beforeFixtureCleanup'] for v in self.r['caseEnd']}
        self.assertEqual(ends['test_native_completed_transition_then_error_retains_unknown']['consumer'],'ADMISSION_UNKNOWN')
        for name in ('test_cancelled_cleanup_retains_unknown_and_all_connections','test_new_replay_during_cleanup_await_is_not_successful_detach'):
            self.assertEqual(ends[name]['consumer'],'CLOSE_UNKNOWN');self.assertEqual(ends[name]['owner'],'VERIFIED')
    def test_immutable_native_and_harness_source_custody(self):
        native=read('native-envelope-review.json');self.assertEqual(native['fixedManifestSourceCount'],517);self.assertTrue(native['old513ManifestUnchanged'])
        self.assertEqual(len(self.r['nativeImports']),self.c['actualNativeImportCount']);self.assertEqual(len(self.r['harnessImports']),self.c['actualHarnessImportCount'])
        for n,h in self.r['nativeImports'].items():self.assertEqual(h,native['fixedNativeBlobs'][n]['sha256'],n)
        for n,h in self.r['harnessImports'].items():
            self.assertEqual(h,self.snapshot['allCopiedHashes'][n]);self.assertEqual(h,self.c['selectedProductHashes'].get(n,self.base['sources'].get(n)))
        for n,h in self.c['selectedProductHashes'].items():self.assertEqual(hashlib.sha256((E/('candidate001-'+n.replace('/','__')+'.txt')).read_bytes()).hexdigest(),h,n)
        self.assertFalse(self.c['productEditedByThisIndependentTask'])
    def test_actual_qa_and_result_bytes_preserved(self):
        self.assertEqual(hashlib.sha256((ROOT/'scripts/qa/q129c6_native_active_owner.py').read_bytes()).hexdigest(),self.r['qaSha256'])
        self.assertEqual(self.r['qaSha256'],self.c['qaSha256'])
        for n,h in self.c['resultHashes'].items():self.assertEqual(hashlib.sha256((E/n).read_bytes()).hexdigest(),h,n)
    def test_original_default_and_clean_gates_remain_intentional(self):
        r=read('baseline-native-001/result.json');self.assertEqual(r['result'],'PASS_ORIGINAL_OWNER_BOUNDARY_CONTROL');self.assertEqual(len(r['checks']),6);self.assertTrue(all(r['checks'].values()))
        self.assertTrue(r['sourceDefaultNotBug']);self.assertFalse(r['activeWorkExecuted']);self.assertTrue(r['profileReleased']);self.assertTrue(r['temporaryProfileRemoved'])
        self.assertEqual(hashlib.sha256((ROOT/'scripts/qa/q129c6_owner_baseline.py').read_bytes()).hexdigest(),self.c['baselineQaSha256'])
        for n,h in r['sourceHashes'].items():
            if n in self.base['sources']:self.assertEqual(h,self.base['sources'][n])
        for n,h in r['nativeImports'].items():self.assertEqual(h,read('native-envelope-review.json')['fixedNativeBlobs'][n]['sha256'])
    def test_explicit_windows_boundary_and_fault_scope(self):
        self.assertTrue(self.r['actualNativeStartupOwnerAndConsumer']);self.assertTrue(self.r['nativeSqlAndAdmissionGuardsReal'])
        self.assertTrue(self.r['windowsLinuxActorLeaseMountColdBoundariesDoubled']);self.assertTrue(self.r['unknownTransitionAndMemoryCleanupFaultsExplicit'])
        for key in ('fullNativeAgentOrHttpExecution','fullLinuxIsolationAccepted','rootWslAction'):self.assertIs(self.r[key],False,key)
        self.assertEqual(self.r['providerCalls'],0)
if __name__=='__main__':unittest.main()
