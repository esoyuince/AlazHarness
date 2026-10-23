"""Saved native thread/count proof; no new executor or network execution here."""
import hashlib,json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
E=ROOT/'evidence/d3b-worker-owner-e118w2'
class WorkerNativeReceipt(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r=json.loads((E/'native-001/result.json').read_text(encoding='utf-8'))
        cls.c=json.loads((E/'native-source-custody.json').read_text(encoding='utf-8'))
        cls.patch=json.loads((E/'native-patch-custody.json').read_text(encoding='utf-8'))
    def test_actual_native_run_scope_and_cleanup(self):
        r=self.r;self.assertEqual(r['result'],'PASS_NATIVE_WORKER_LIFETIME_BINDINGS')
        self.assertEqual((r['total'],r['passed'],r['errors'],r['failures'],r['skipped']),(34,34,0,0,0))
        self.assertEqual(r['inheritedProducerCompatibilityMethods'],20)
        for k in ('realExecutorThreadsObserved','nativeEntryAndTaskLifecycleReal','nativeAuthDecoratorTested','sourcesUnchanged','profileReleased','bootstrapRemoved'):self.assertIs(r[k],True)
        for k in ('workerStateManuallyPublished','nativeTaskMapsWrittenByFixture','httpListenerStarted','canonicalExecutorHealthProven','fullIsolationTested','rootWslAction'):self.assertIs(r[k],False)
        self.assertTrue(r['agentExecutionDoubled']);self.assertTrue(r['authorityAndBotDeliveryBoundariesDoubled'])
        self.assertEqual((r['providerCalls'],r['newNetworkAttempts']),(0,0))
    def test_current_sources_match_executed_committed_native(self):
        for name,h in self.r['sources'].items():self.assertEqual(hashlib.sha256((ROOT/name).read_bytes()).hexdigest(),h,name)
        self.assertEqual({n:v['sha256'] for n,v in self.c['nativeImports'].items()},self.r['nativeImports'])
        self.assertTrue(self.c['allExecutedNativeImportsMatchCommittedBlobs'])
        self.assertEqual(hashlib.sha256((E/'native-001/result.json').read_bytes()).hexdigest(),self.c['resultSha256'])
        self.assertEqual(self.c['featureCommit'],self.patch['featureCommit'])
        for name,h in self.patch['resultHashes'].items():self.assertEqual(self.r['nativeImports'][name],h)
    def test_queued_cancelled_work_never_executes_and_counter_clears(self):
        name='test_worker_queued_cancellation_does_not_leak_count_or_call_function'
        case=next(c for c in self.r['cases'] if c['case']==name)
        self.assertEqual((case['dummyAgentCalls'],case['nativeWorkersRemaining']),(0,0))
        rows=[v for v in self.r['workerProofs'] if v['case']==name]
        self.assertEqual(rows[0]['states'],['SUBMITTED']);self.assertEqual(rows[0]['nativeWorkerCount'],1)
        self.assertEqual(rows[-1]['states'],[]);self.assertEqual(rows[-1]['nativeWorkerCount'],0)
    def test_carrier_done_cannot_clear_running_native_worker(self):
        name='test_worker_survives_cancelled_carrier_without_task_retention'
        rows=[v for v in self.r['workerProofs'] if v['case']==name]
        self.assertEqual(rows[0]['states'],['RUNNING']);self.assertEqual(rows[0]['carrierDone'],[True]);self.assertEqual(rows[0]['carrierCancelled'],[True])
        self.assertEqual(rows[0]['public']['workersOutlivingCarrier'],1);self.assertEqual(rows[0]['nativeWorkerCount'],1)
        self.assertEqual(rows[-1]['states'],[]);self.assertEqual(rows[-1]['nativeWorkerCount'],0)
    def test_multiple_real_requests_and_no_positive_health_grant(self):
        cases={v['case']:v for v in self.r['cases']}
        self.assertEqual(cases['test_worker_two_requests_do_not_share_identity_or_thread']['dummyAgentCalls'],2)
        self.assertTrue(all(v['nativeWorkersRemaining']==0 for v in self.r['cases']))
        for row in self.r['workerProofs']:
            self.assertEqual(row['policyWrites'],0)
            for key in ('canonicalExecutorVerified','allAgentWorkObserved','storageIntegrityVerified','serviceReadinessVerified','runtimeAdmissionAuthorized','retryAuthorized','storeReleaseAuthorized'):self.assertFalse(row['public'][key])
        log=(E/'native-001/tests.txt').read_text(encoding='utf-8')
        lines=[l for l in log.splitlines() if l.startswith('test_') and l.endswith(' ... ok')]
        self.assertEqual(len(lines),34);self.assertEqual(len({l.split(' ',1)[0] for l in lines}),34)
    def test_exact_patch_apply_counter_ancestry_and_no_activation(self):
        c=json.loads((ROOT/'config/hermes-worker-owner-e118w2.json').read_text(encoding='utf-8'))
        self.assertEqual(c['activation'],'NOT_INSTALLED');self.assertFalse(c['nativeListenerAuthorized'])
        self.assertEqual(c['nativeFeatureCommit'],self.patch['featureCommit'])
        self.assertEqual(hashlib.sha256((ROOT/c['patchPath']).read_bytes()).hexdigest(),c['patchSha256'])
        for key in ('freshApplyMatches','repeatApplyRefused','temporaryApplyRemoved','mergeTreeIdenticalToTestedFeature'):self.assertTrue(self.patch[key])
        self.assertEqual(self.patch['preservedCounterCommit'],'24165690b15f479f90f4bb7ac8751ae65c6f21fe')
if __name__=='__main__':unittest.main()
