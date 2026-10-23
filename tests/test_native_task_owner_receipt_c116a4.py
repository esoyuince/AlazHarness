"""Offline custody of independent real native Task observations, not a rerun."""
from pathlib import Path
import ast,hashlib,json,unittest
ROOT=Path(__file__).resolve().parents[1]
E=ROOT/'evidence/d3b-task-owner-c116a4'
class NativeOwnerReceipt(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.r=json.loads((E/'native-003/result.json').read_text(encoding='utf-8'))
    def test_terminal_28_cases_and_exact_current_sources(self):
        self.assertEqual(self.r['result'],'PASS_NATIVE_ADAPTER_TASK_OBSERVATION_ONLY')
        self.assertEqual(tuple(self.r[n] for n in ('total','passed','errors','failures','skipped')),(28,28,0,0,0))
        end=json.loads((E/'native-003-exit.json').read_text(encoding='utf-8'));self.assertEqual(end['exitCode'],0);self.assertTrue(end['sourcesUnchanged'])
        intent=json.loads((E/'native-003-intent.json').read_text(encoding='utf-8'));self.assertEqual(self.r['sources'],intent['sources'])
        for n,h in self.r['sources'].items():self.assertEqual(hashlib.sha256((ROOT/n).read_bytes()).hexdigest(),h,n)
    def test_immutable_native_sources_are_bound_to_actual_imports(self):
        custody=json.loads((E/'native003-source-custody.json').read_text(encoding='utf-8'))
        self.assertEqual(custody['feature'],'cc16c10b16a0ca8d80b23fd9be3f0e59ee605075')
        self.assertTrue(custody['allActualImportsMatchImmutableGit'])
        self.assertEqual({n:v['sha256'] for n,v in custody['imports'].items()},self.r['nativeImports'])
        self.assertEqual(len(self.r['nativeImports']),custody['importCount'])
    def test_actual_cases_match_log_and_code_not_aggregate_only(self):
        log=(E/'native-003/tests.txt').read_text(encoding='utf-8')
        names=[line.split(' ',1)[0] for line in log.splitlines() if line.startswith('test_') and line.endswith(' ... ok')]
        tree=ast.parse((ROOT/'scripts/qa/c116a4_native_owner.py').read_text(encoding='utf-8'))
        methods={n.name for n in ast.walk(tree) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name.startswith('test_')}
        self.assertEqual(len(names),28);self.assertEqual(set(names),methods)
    def test_actual_worker_outliving_cancelled_task_is_observed(self):
        records=[v for v in self.r['observations'] if v['case']=='test_native_worker_survives_cancelled_wrapper_and_refuses_idle']
        self.assertEqual(len(records),1)
        for key in ('cancelledTaskDone','actualNativeWorkerStillLive','positiveProofRefused'):self.assertIs(records[0][key],True)
        self.assertIs(self.r['actualNativeExecutorThreadTested'],True)
    def test_real_liveness_is_not_full_producer_or_service_acceptance(self):
        for n in ('nativeAdapterStoresAndTasksReal','osProcessStartReal','producerRegistrationIsExplicitFixture','profileOwnershipReleased','bootstrapRemoved'):self.assertIs(self.r[n],True)
        for n in ('nativeIngressHooksIntegrated','serviceReadinessProven','fullIsolationTested','nativeListenerStarted','rootWslAction'):self.assertIs(self.r[n],False)
        self.assertEqual(self.r['providerCalls'],0);self.assertEqual(self.r['newNetworkAttemptsInCases'],0)
        for event in self.r['observations']:
            if 'boundTasks' in event:self.assertTrue(event['noSQLiteConnectOrWrite']);self.assertTrue(event['noServicePermission'])
    def test_first_import_failure_retained_not_changed_to_pass(self):
        old=json.loads((E/'native-001-exit.json').read_text(encoding='utf-8'));self.assertEqual(old['exitCode'],1)
        self.assertIn('Could not determine home directory',(E/'native-001-stderr.txt').read_text(encoding='utf-8'))
        correction=json.loads((E/'import-fixture-correction.json').read_text(encoding='utf-8'))
        self.assertFalse(correction['productSourcesChanged']);self.assertTrue(correction['firstFailurePreserved'])
    def test_successful_retirement_requires_real_task_and_native_cleanup(self):
        rows=[v for v in self.r['observations'] if v['case']=='test_successful_native_retirement_returns_to_empty_observation' and 'allThreeCommitted' in v]
        self.assertEqual(len(rows),1)
        for k in ('realTaskFinishedSuccessfully','nativeRetireFunctionUsed','allThreeCommitted','observerOnlyEntryRemoved','storesRemainOpen'):self.assertIs(rows[0][k],True)
        old=json.loads((E/'native-002/result.json').read_text(encoding='utf-8'))
        self.assertEqual(old['passed'],22)
        self.assertNotEqual(old['sources']['packages/claw-hermes/gateway_work_observer.py'],self.r['sources']['packages/claw-hermes/gateway_work_observer.py'])

if __name__=='__main__':unittest.main()
