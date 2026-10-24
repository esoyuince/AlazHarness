"""Finite source selection contracts and actual current lifecycle records."""
import asyncio,hashlib,inspect,json,sys,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'packages/claw-hermes'),str(ROOT/'tests')]
import gateway_prepared_consumer as consumer
import gateway_store_startup as startup
import test_api_owner_i133p1 as old
import historical_finite_close_f135c6 as history
E=ROOT/'evidence/d3b-finite-close-f135c6'
def read(name):return json.loads((E/name).read_text(encoding='utf-8'))
class FiniteSelection(unittest.IsolatedAsyncioTestCase):
    setUp=old.SelectionContracts.setUp
    mark=old.SelectionContracts.mark
    make_store=old.SelectionContracts.make_store
    obj=old.SelectionContracts.obj
    async def test_explicit_finite_uses_same_reserved_owner(self):
        o=self.obj();o.start()
        async def prepare(c,*args):
            self.assertIs(o._prepared_consumer,c);self.assertIs(c._owner,o)
            self.assertTrue(c._finite_turn);self.assertTrue(c._canonical_api);self.assertTrue(c._local_admission)
            self.assertEqual(c._selected_feature,consumer.FINITE_FEATURE)
        with patch.object(consumer.PreparedRuntimeConsumer,'prepare',new=prepare):
            await o.prepare_runtime(object(),object(),local_admission=True,canonical_api=True,finite_turn=True)
    async def test_invalid_finite_options_do_not_reserve_slot(self):
        o=self.obj();o.start()
        for value in (0,1,None,'true',{}):
            with self.assertRaises(startup.StoreStartupRejected):
                await o.prepare_runtime(object(),object(),local_admission=True,canonical_api=True,finite_turn=value)
            self.assertIsNone(o._prepared_consumer)
        with self.assertRaises(startup.StoreStartupRejected):
            await o.prepare_runtime(object(),object(),local_admission=True,finite_turn=True)
        self.assertIsNone(o._prepared_consumer)
    async def test_defaults_stay_false_and_three_legacy_generations_distinct(self):
        self.assertIs(inspect.signature(startup.NativeStoreStartup.prepare_runtime).parameters['finite_turn'].default,False)
        self.assertIs(inspect.signature(consumer.PreparedRuntimeConsumer).parameters['finite_turn'].default,False)
        self.assertNotIn(consumer.FINITE_FEATURE,(consumer.FEATURE,consumer.ADMISSION_FEATURE,consumer.CANONICAL_API_FEATURE))
class FiniteLifecycleReceipt(unittest.TestCase):
    def test_normal_real_result_and_idempotent_retry(self):
        r=read('final-normal/result.json');self.assertIsNone(r['error'])
        self.assertEqual(r['savedResult']['result']['final_response'],'50');self.assertTrue(r['savedResult']['result']['completed'])
        self.assertEqual(len(r['computation']),1);self.assertFalse(r['computation'][0]['onMainThread']);self.assertTrue(r['computation'][0]['samePrimarySessionDb'])
        self.assertEqual(r['exactRetry'],{'sameResult':True,'computationCountBefore':1,'computationCountAfter':1});self.assertTrue(r['changedPayload']['rejected'])
    def test_actual_compute_exception_also_closes_without_retry_execution(self):
        r=read('final-compute-failure/result.json');self.assertTrue(r['computeFailureSelected']);self.assertIsNone(r['error']);self.assertEqual(r['verdict'],'NATIVE_FAILURE_AND_RETRY_OBSERVED')
        self.assertTrue(r['result'][0]['failed']);self.assertFalse(r['result'][0]['completed']);self.assertEqual(len(r['computation']),1)
        self.assertEqual(r['exactRetry']['computationCountAfter'],1);self.assertTrue(r['changedPayload']['rejected'])
    def test_both_original_owner_closures_real_not_fixture_cleanup(self):
        for label in ('final-normal','final-compute-failure'):
            r=read(label+'/result.json');self.assertEqual(r['closeOutcome'],'ORIGINAL_OWNER_CLEAN_CLOSE');self.assertTrue(r['fullLifecycleAccepted']);self.assertTrue(r['temporaryHomeRemoved'])
            self.assertEqual(r['additionalStateDbOpensDuringTurn'],0);l=r['lifecycle']
            for key in ('allThreeOriginalConnectionsClosed','profileStillOwnedByCaller','modelCloseCalled','noSqlRowsChangedByRetireDetach'):self.assertTrue(l[key],key)
            self.assertEqual(l['registryRefsBeforeFixtureCleanup'],0);self.assertEqual(l['normalOwnerStage'],'CLOSED');self.assertEqual(l['consumerStage'],'DETACHED')
            self.assertFalse(l['resourceReceipt']['callerStoresClosed']);self.assertFalse(l['sessionReceipt']['durableDataChanged'])
    def test_native_pipeline_is_present_and_never_manually_settled(self):
        for label in ('final-normal','final-compute-failure'):
            r=read(label+'/result.json');self.assertFalse(r['manualSettlementPerformed'])
            methods={e['method'] for e in r['nativeTrace']}
            self.assertTrue({'run_api_turn','execute_finite_admission','run_sync','settle_session_input'}<=methods)
            api_threads={e['thread'] for e in r['nativeTrace'] if e['method']=='run_api_turn'}
            worker_threads={e['thread'] for e in r['nativeTrace'] if e['method']=='run_sync'}
            self.assertEqual(len(api_threads),1)
            self.assertTrue(worker_threads)
            self.assertTrue(api_threads.isdisjoint(worker_threads))
            self.assertIn(r['computation'][0]['thread'],worker_threads)
            self.assertFalse(r['computation'][0]['onMainThread'])
    def test_earlier_failures_are_preserved(self):
        for label,reason in (('actual-close-001','retirement_live_obligation'),('actual-close-003','retirement_fast_receipt_not_durable')):
            r=read(label+'/result.json');self.assertFalse(r['fullLifecycleAccepted']);self.assertEqual(r['closeOutcome']['reason'],reason)
        self.assertEqual(read('actual-close-005/result.json')['closeOutcome'],'ORIGINAL_OWNER_CLEAN_CLOSE')
    def test_exact_selection_and_patch_match_native(self):
        c=json.loads((ROOT/'config/hermes-finite-close-f135c6.json').read_text(encoding='utf-8'))
        raw=(ROOT/c['sourceManifest']).read_bytes();m=json.loads(raw)
        self.assertEqual(hashlib.sha256(raw).hexdigest(),consumer.FINITE_MANIFEST_SHA256);self.assertEqual(m['nativeFeature'],consumer.FINITE_FEATURE);self.assertEqual(c['nativeFeature'],consumer.FINITE_FEATURE)
        self.assertEqual(len(m['sources']),755);self.assertEqual(len(c['resultHashes']),8)
        self.assertEqual(hashlib.sha256((ROOT/c['patchPath']).read_bytes()).hexdigest(),c['patchSha256'])
        self.assertTrue(read('patch-application.json')['appliedExactEightFiles']);self.assertTrue(read('patch-application.json')['secondApplyRefused'])
        for label in ('final-normal','final-compute-failure'):
            r=read(label+'/result.json');self.assertEqual(r['nativeFeature'],c['nativeFeature'])
            for name,h in (r['nativeImports']|r['nativeExecutedSources']).items():self.assertEqual(m['sources'][name],h,name)
            self.assertEqual(hashlib.sha256((ROOT/'scripts/qa/f135c6_native_finite_close.py').read_bytes()).hexdigest(),r['driverSha256'])
    def test_historical_redirect_exact_bytes_only(self):
        b=read('baseline.json')
        for name in history.NAMES:
            self.assertEqual(history.saved_generation_hash(ROOT,name,b['sourceHashes'][name]),b['sourceHashes'][name])
            self.assertIsNone(history.saved_generation_hash(ROOT,name,'0'*64))
        self.assertIsNone(history.saved_generation_hash(ROOT,'unknown.py','0'*64))
    def test_scope_remains_bounded_model_and_declared_os_doubles(self):
        for label in ('final-normal','final-compute-failure'):
            r=read(label+'/result.json');self.assertTrue(r['windowsOsBoundariesDoubled']);self.assertFalse(r['httpListenerStarted']);self.assertFalse(r['linuxIsolationTested']);self.assertEqual(r['realProviderCalls'],0)
            self.assertEqual(r['nativeMethodsReplaced'],['run_agent.AIAgent (explicit model factory/computation only)'])
        c=json.loads((ROOT/'config/hermes-finite-close-f135c6.json').read_text(encoding='utf-8'));self.assertEqual(c['activation'],'STAGED_NOT_INSTALLED')
if __name__=='__main__':unittest.main()
