"""Retain executed native counter/request-worker evidence; no new native execution."""
from pathlib import Path
import hashlib,json,unittest
ROOT=Path(__file__).resolve().parents[1]
E=ROOT/'evidence/d3b-worker-lifetime-e118r1'
class WorkerLifetimeReceipt(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.counter=json.loads((E/'selected-counter-001/result.json').read_text(encoding='utf-8'))
        cls.workers=json.loads((E/'selected-workers-001/result.json').read_text(encoding='utf-8'))
        cls.custody=json.loads((E/'selected-source-custody.json').read_text(encoding='utf-8'))
    def test_native_bug_reproduced_and_same_probe_changed_result(self):
        before=json.loads((E/'queued-cancel-before.json').read_text(encoding='utf-8'))
        after=json.loads((E/'queued-cancel-after.json').read_text(encoding='utf-8'))
        for r in (before,after):
            self.assertEqual((r['before'],r['submitted'],r['actualWorkCalls']),(0,1,0));self.assertTrue(r['asyncFutureCancelled']);self.assertFalse(r['rootWslAction']);self.assertEqual(r['providerCalls'],0)
        self.assertEqual(before['afterAllThreadsDrained'],1);self.assertEqual(after['afterAllThreadsDrained'],0)
        self.assertNotEqual(before['nativeSubmitModuleSha256'],after['nativeSubmitModuleSha256'])
        commit=json.loads((E/'counter-native-commit.json').read_text(encoding='utf-8'))
        self.assertEqual(after['nativeSubmitModuleSha256'],commit['changedModuleSha256'])
        self.assertEqual(commit['commit'],self.custody['counterAncestor'])
    def test_current_twelve_counter_cases_retain_real_executor_and_zero_count(self):
        r=self.counter;self.assertEqual(r['result'],'PASS_NATIVE_WORKER_CANCELLATION')
        self.assertEqual((r['total'],r['passed'],r['errors'],r['failures'],r['skipped']),(12,12,0,0,0))
        self.assertTrue(r['realExecutorUsed']);self.assertFalse(r['nativeWorkerFunctionReplaced']);self.assertFalse(r['counterManuallyReset'])
        self.assertTrue(r['temporaryBootstrapRemoved']);self.assertEqual(r['newNetworkAttempts'],0)
        self.assertEqual(len(r['observations']),12)
        for observation in r['observations']:self.assertEqual(observation['workerCountAfterDrain'],0)
    def test_ten_current_native_request_cases_have_no_manual_worker_publication(self):
        r=self.workers;self.assertEqual(r['result'],'PASS_INDEPENDENT_NATIVE_WORKER_REQUESTS')
        self.assertEqual((r['total'],r['passed'],r['errors'],r['failures'],r['skipped']),(10,10,0,0,0))
        self.assertTrue(r['realNativeHandlerTaskWorkerAndCounter']);self.assertFalse(r['manualWorkerPublication']);self.assertTrue(r['dummyModelComputation'])
        self.assertTrue(r['profileOwnershipReleased']);self.assertTrue(r['bootstrapRemoved'])
        for name in ('canonicalSessionAuthorityVerified','serviceHealthAccepted','httpListenerStarted','kernelIsolationTested','rootWslAction'):self.assertFalse(r[name])
        self.assertEqual(r['providerCalls'],0);self.assertEqual(r['newNetworkAttempts'],0)
    def test_current_sources_and_all_native_imports_bound_to_selected_commit(self):
        c=self.custody;self.assertEqual(c['nativeCommit'],'943210584828ccfcfd6adc8eb966ecaa8ca18429')
        for name,h in c['sourceSha256'].items():self.assertEqual(hashlib.sha256((ROOT/name).read_bytes()).hexdigest(),h,name)
        for r in (self.counter,self.workers):
            for name,h in r['nativeImports'].items():self.assertEqual(c['actualNativeImports'][name]['sha256'],h)
        self.assertEqual(self.counter['qaSha256'],hashlib.sha256((ROOT/'scripts/qa/e118r1_worker_counter.py').read_bytes()).hexdigest())
        for name,h in self.workers['sources'].items():self.assertEqual(hashlib.sha256((ROOT/name).read_bytes()).hexdigest(),h)
        self.assertEqual(c['nativeImportCount'],len(c['actualNativeImports']))
        self.assertFalse(c['nativeFeatureInstalled']);self.assertFalse(c['newNativeRunByVerification'])
    def test_raw_cancelled_carrier_survivor_then_actual_exit(self):
        rows=[r for r in self.workers['observations'] if r['case']=='test_cancelled_carrier_record_survives_until_actual_worker_exit']
        self.assertEqual(len(rows),2)
        self.assertEqual(rows[0]['workerStates'],['RUNNING']);self.assertEqual(rows[0]['public']['workersOutlivingCarrier'],1)
        self.assertEqual(rows[1]['workerStates'],[]);self.assertEqual(rows[1]['public']['workersOutlivingCarrier'],0)
        for r in rows:self.assertFalse(r['public']['storeReleaseAuthorized']);self.assertFalse(r['public']['serviceReadinessVerified'])
    def test_queue_and_unattributed_work_not_falsely_healthy(self):
        q=[r for r in self.workers['observations'] if r['case']=='test_queued_carrier_cancel_never_runs_and_leaves_no_owner']
        self.assertEqual([r['workerStates'] for r in q],[['SUBMITTED'],[]])
        u=next(r for r in self.workers['observations'] if r['case']=='test_untracked_other_ingress_is_visible_not_counted_as_complete')
        self.assertEqual(u['public']['unattributedNativeWorkers'],1);self.assertFalse(u['public']['allAgentWorkObserved'])
        for r in self.workers['observations']:
            self.assertFalse(r['newConnectionsAndRowWritesDuringCapture']);self.assertTrue(r['nativeRequestAndWorkerPublicationAutomatic'])
            for field in ('canonicalExecutorVerified','serviceReadinessVerified','runtimeAdmissionAuthorized','retryAuthorized','storeReleaseAuthorized'):self.assertFalse(r['public'][field])
    def test_first_compatibility_timeout_not_erased_or_relabelled(self):
        first=json.loads((E/'producer-compat-001/result.json').read_text(encoding='utf-8'))
        retry=json.loads((E/'producer-compat-002/result.json').read_text(encoding='utf-8'))
        self.assertEqual((first['passed'],first['errors']),(19,1));self.assertEqual(first['result'],'FAIL')
        self.assertEqual((retry['passed'],retry['errors']),(20,0))
        self.assertEqual(first['sources'],retry['sources']);self.assertEqual(first['nativeImports'],retry['nativeImports'])
        log=(E/'producer-compat-001/tests.txt').read_text(encoding='utf-8');self.assertIn('TimeoutError',log)
        intent=json.loads((E/'compatibility-retry-intent.json').read_text(encoding='utf-8'));self.assertTrue(intent['singleFreshRetry']);self.assertTrue(intent['priorFailureRetained'])
        self.assertEqual(first['profileOwnershipReleased'],True);self.assertEqual(retry['profileOwnershipReleased'],True)
if __name__=='__main__':unittest.main()
