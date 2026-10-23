"""Independent current native producer receipts; no native execution in this suite."""
import hashlib,json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
E=ROOT/'evidence/d3b-native-producer-p117n1'
class IndependentProducerReceipt(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r=json.loads((E/'selected-native-001/result.json').read_text(encoding='utf-8'))
        cls.c=json.loads((E/'selected-native-source-custody.json').read_text(encoding='utf-8'))
    def test_current_terminal_and_scope(self):
        r=self.r;self.assertEqual((r['total'],r['passed'],r['errors'],r['failures'],r['skipped']),(20,20,0,0,0))
        self.assertEqual(r['result'],'PASS_INDEPENDENT_SELECTED_NATIVE_PRODUCER')
        for k in ('nativeHandlerSchedulerTaskMapsAndRetirementReal','agentComputationIsDummy','externalOwnerBoundaryDoubled','nativeHandlerAuthDecoratorUsed','profileOwnershipReleased','bootstrapRemoved'):self.assertIs(r[k],True)
        for k in ('manualObservationPublicationInTests','httpServerMiddlewareOrListenerTested','executorOwnershipHealthAccepted','rootWslAction'):self.assertIs(r[k],False)
        self.assertEqual(r['newNetworkAttempts'],0);self.assertEqual(r['providerCalls'],0)
    def test_current_product_qa_and_native_bytes_bound(self):
        for name,h in self.r['sources'].items():self.assertEqual(hashlib.sha256((ROOT/name).read_bytes()).hexdigest(),h,name)
        self.assertEqual(self.r['sources'],self.c['sourceHashes'])
        self.assertEqual(self.c['nativeImportCount'],len(self.r['nativeImports']))
        self.assertEqual({n:v['sha256'] for n,v in self.c['nativeSources'].items()},self.r['nativeImports'])
        self.assertEqual(self.c['nativeBase'],'cc16c10b16a0ca8d80b23fd9be3f0e59ee605075')
        self.assertEqual(set(self.c['changedNativeSources']),{'gateway/platforms/api_server_runs.py','gateway/platforms/api_server_run_observation.py'})
        self.assertTrue(self.c['allImportedSourcesMatched'])
    def test_real_lifecycle_replay_and_worker_distinction(self):
        records={r['assertion']:r for r in self.r['observations']}
        lifecycle=records['native_lifecycle_not_fixture']
        self.assertEqual(lifecycle['phases'],['ACCEPTED','CREATED','STARTED','EXECUTION_RETURNED','RETIRED','DONE'])
        self.assertTrue(lifecycle['nativeTaskRemoved']);self.assertEqual(lifecycle['dummyCalls'],1)
        self.assertTrue(all(k=='executor_thread_carrier' for k in lifecycle['kinds']))
        self.assertEqual(records['replay_same_native_task']['newEventsDuringReplay'],0)
        self.assertEqual(records['replay_same_native_task']['calls'],1)
        worker=records['wrapper_not_executor'];self.assertTrue(worker['wrapperDone']);self.assertTrue(worker['nativeWorkerStillAlive'])
        self.assertTrue(records['selected_source_no_executor_health']['nativeHooksAutomatic'])
        self.assertEqual(records['selected_source_no_executor_health']['activeRecordsAfterDone'],0)
    def test_auth_callback_cancellation_and_factory_cases_actually_ran(self):
        log=(E/'selected-native-001/tests.txt').read_text(encoding='utf-8')
        cases={line.split(' ',1)[0] for line in log.splitlines() if line.startswith('test_') and line.endswith(' ... ok')}
        self.assertEqual(len(cases),20)
        required={'test_native_auth_rejects_without_creating_work_or_trace','test_callback_cancellation_does_not_cancel_native_request','test_callback_cancellation_during_retirement_keeps_native_cleanup','test_eager_factory_gaps_trace_but_preserves_native_execution','test_native_borrowed_listener_stays_closed','test_json_cannot_enable_native_observation'}
        self.assertTrue(required<=cases)
    def test_superseded_draft_is_not_selected_product(self):
        choice=json.loads((E/'single-producer-selection.json').read_text(encoding='utf-8'))
        for name,meta in choice['ownHistoricalDrafts'].items():
            self.assertEqual(hashlib.sha256((ROOT/meta['path']).read_bytes()).hexdigest(),meta['sha256'])
        self.assertFalse((ROOT/'packages/claw-hermes/gateway_native_run_source.py').exists())
        self.assertTrue(choice['own20NativeMethodsHistoricalNotSelectedSourceAcceptance'])
        self.assertEqual(choice['selectedNativeAndConsumerOwner'],'H117B')
    def test_first_fixture_error_preserved_and_cancellation_red_green_not_relabelled(self):
        r=json.loads((E/'native-001/result.json').read_text(encoding='utf-8'))
        self.assertEqual((r['result'],r['passed'],r['errors']),('FAIL',3,14))
        self.assertEqual(json.loads((E/'native-001-exit.json').read_text(encoding='utf-8'))['exitCode'],1)
        self.assertEqual(json.loads((E/'cancellation-before.txt').read_text(encoding='utf-8')),{'cancelEscaped':True,'faultLatched':False})
        self.assertEqual(json.loads((E/'cancellation-after.txt').read_text(encoding='utf-8')),{'cancelEscaped':False,'faultLatched':True})
if __name__=='__main__':unittest.main()
