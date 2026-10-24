"""Current selection contracts and exact native receipts; no runtime replay here."""
import asyncio,hashlib,inspect,json,sys,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'packages/claw-hermes'),str(ROOT/'tests')]
import gateway_prepared_consumer as consumer
import gateway_store_startup as startup
import test_gateway_store_startup as base
import test_three_store_lifecycle_l113f6 as three
import historical_api_i133p1 as history
E=ROOT/'evidence/d3b-api-owner-i133p1'
def read(name):return json.loads((E/name).read_text(encoding='utf-8'))

class SelectionContracts(unittest.IsolatedAsyncioTestCase):
    setUp=three.ThreeStoreLifecycle.setUp
    mark=base.Lifecycle.mark
    make_store=base.Lifecycle.make_store
    obj=three.ThreeStoreLifecycle.obj
    async def test_explicit_canonical_selection_uses_same_reserved_consumer(self):
        owner=self.obj();owner.start()
        async def prepare(c,*args):
            self.assertIs(owner._prepared_consumer,c);self.assertTrue(c._local_admission);self.assertTrue(c._canonical_api)
            self.assertEqual(c._selected_feature,consumer.CANONICAL_API_FEATURE);self.assertEqual(c._publication_phase,'NEW')
        with patch.object(consumer.PreparedRuntimeConsumer,'prepare',new=prepare):
            c=await owner.prepare_runtime(object(),object(),local_admission=True,canonical_api=True)
        self.assertIs(type(c),consumer.PreparedRuntimeConsumer);self.assertIs(c._owner,owner)
    async def test_invalid_or_unpaired_canonical_selection_no_slot_effect(self):
        owner=self.obj();owner.start()
        for value in (0,1,None,'yes',{}):
            with self.assertRaises(startup.StoreStartupRejected):await owner.prepare_runtime(object(),object(),local_admission=True,canonical_api=value)
            self.assertIsNone(owner._prepared_consumer)
        with self.assertRaises(startup.StoreStartupRejected):await owner.prepare_runtime(object(),object(),canonical_api=True)
        self.assertIsNone(owner._prepared_consumer)
    async def test_both_legacy_defaults_remain_exact(self):
        for selected,expected in ((False,consumer.FEATURE),(True,consumer.ADMISSION_FEATURE)):
            owner=self.obj();owner.start()
            async def prepare(c,*args):
                self.assertEqual(c._selected_feature,expected);self.assertFalse(c._canonical_api)
            with patch.object(consumer.PreparedRuntimeConsumer,'prepare',new=prepare):
                c=await owner.prepare_runtime(object(),object(),local_admission=selected)
            self.assertEqual(c._publication_phase,'NEW')
    async def test_new_flag_defaults_false_at_both_boundaries(self):
        self.assertIs(inspect.signature(startup.NativeStoreStartup.prepare_runtime).parameters['canonical_api'].default,False)
        self.assertIs(inspect.signature(consumer.PreparedRuntimeConsumer).parameters['canonical_api'].default,False)

class NativeReceipt(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.r=read('native-002/result.json');cls.c=read('current-source-custody.json')
    def test_all_thirty_nine_terminal_and_profiles_clean(self):
        r=self.r;self.assertEqual((r['total'],r['passed'],r['skipped'],r['errors'],r['failures']),(39,39,0,0,0))
        self.assertTrue(r['temporaryRootRemoved']);self.assertEqual(len(r['caseEnd']),39)
        text=(E/'native-002/tests.txt').read_text(encoding='utf-8');self.assertEqual(sum(x.startswith('test_') and x.endswith(' ... ok') for x in text.splitlines()),39)
        for end in r['caseEnd']:
            self.assertTrue(end['profileRemoved']);self.assertTrue(end['nativeOwnershipReleased']);self.assertEqual(end['registry']['total_refcounts'],0)
    def test_post_effect_failure_preserved_same_test_then_passes(self):
        old=read('native-001/result.json');self.assertEqual((old['total'],old['passed'],old['errors'],old['failures']),(39,38,0,1))
        self.assertTrue(old['failureIds'][0].endswith('test_posteffect_retirement_error_retains_unknown'))
        before=read('native-001-intent.json');after=read('native-002-intent.json');qa='scripts/qa/i133p1_native_api_owner.py'
        self.assertEqual(before['files'][qa],after['files'][qa]);self.assertEqual(hashlib.sha256((ROOT/qa).read_bytes()).hexdigest(),after['files'][qa])
        name='packages/claw-hermes/gateway_consumer_api.py'
        self.assertNotEqual(before['files'][name],after['files'][name]);self.assertEqual(hashlib.sha256((E/'native001-gateway_consumer_api.py.txt').read_bytes()).hexdigest(),before['files'][name])
        end=next(x for x in self.r['caseEnd'] if x['case']=='test_posteffect_retirement_error_retains_unknown')
        self.assertEqual(end['beforeFixtureCleanup']['consumer'],'ADMISSION_UNKNOWN')
    def test_true_api_and_retirement_scopes_are_explicit(self):
        observations={x['case']:x for x in self.r['observations']}
        api=observations['test_actual_api_admits_once_and_keeps_owner_identity'];self.assertTrue(api['realNativeApiAdmission']);self.assertTrue(api['exactRetryOneRow']);self.assertTrue(api['sameOwnerThreeConnections']);self.assertFalse(api['payloadExecuted'])
        retirement=observations['test_native_retirement_preserves_durable_history_then_ordered_close'];self.assertTrue(retirement['nativeLeafSettlementIsFixture']);self.assertTrue(retirement['durableHistoryUnchanged']);self.assertTrue(retirement['orderedClose'])
        for key in ('fullFiniteTurnExecuted','linuxConfinementTested','httpListenerStarted'):self.assertFalse(self.r[key])
        self.assertTrue(self.r['actualOwnerNativeApiSql']);self.assertTrue(self.r['windowsLinuxBoundaryDoubles']);self.assertEqual(self.r['providerCalls'],0)
    def test_exact_current_loaded_sources_and_manifest(self):
        raw=(ROOT/'config/canonical-api-consumer-i133p1-sources.json').read_bytes();manifest=json.loads(raw)
        self.assertEqual(hashlib.sha256(raw).hexdigest(),consumer.CANONICAL_API_MANIFEST_SHA256);self.assertEqual(len(manifest['sources']),522)
        self.assertEqual(manifest['nativeFeature'],consumer.CANONICAL_API_FEATURE)
        for name,h in self.r['nativeImports'].items():self.assertEqual(manifest['sources'][name],h,name);self.assertEqual(self.c['nativeFiles'][name]['sha256'],h,name)
        for name,h in self.r['harnessImports'].items():self.assertEqual(history.executed_source_hash(ROOT,name,h),h,name)
        for name,h in self.c['resultHashes'].items():self.assertEqual(hashlib.sha256((E/name).read_bytes()).hexdigest(),h,name)
    def test_legacy_modes_actually_retested_current_harness(self):
        for label,count,feature in (('compat-admission',23,consumer.ADMISSION_FEATURE),('compat-prepared',20,consumer.FEATURE)):
            r=read(label+'/result.json');self.assertEqual((r['total'],r['passed'],r['errors'],r['failures'],r['skipped']),(count,count,0,0,0))
            self.assertTrue(r['temporaryRootRemoved']);self.assertEqual(self.c['compatibility'][label]['feature'],feature)
            for name,h in r['sourceHashes'].items():self.assertEqual(history.executed_source_hash(ROOT,name,h),h,name)
        self.assertTrue(all(r['exitCode']==0 for r in read('compatibility-terminal.json')))
    def test_readonly_transitions_and_real_writer_races_retained(self):
        for x in self.r['checks']:self.assertEqual((x['newConnections'],x['rawDatabaseOpens'],x['rowChanges']),(0,0,0))
        self.assertEqual(len(self.r['races']),2)
        for r in self.r['races']:
            if 'cancelledCarrier' in r:self.assertTrue(r['cancelledCarrier']);self.assertTrue(r['lateQueuedCommitRetained']);self.assertTrue(r['originalOwnerCloseRefused'])
            else:self.assertTrue(r['blockedWriterRefused']);self.assertTrue(r['nativeMutexNotWaitedByDrain'])
    def test_exact_historical_redirect_never_unknown_generation(self):
        baseline=read('baseline.json')
        for name in history.NAMES:
            self.assertEqual(history.saved_generation_hash(ROOT,name,baseline['sources'][name]),baseline['sources'][name])
            self.assertIsNone(history.saved_generation_hash(ROOT,name,'0'*64))
        self.assertIsNone(history.saved_generation_hash(ROOT,'not/qualified.py','0'*64))
    def test_current_native_sources_not_installed_or_main_promoted(self):
        self.assertFalse(self.c['nativeFilesModified']);self.assertFalse(self.c['installedNativeModified']);self.assertFalse(self.c['fullRuntimeOrKernelAccepted'])
        self.assertEqual(self.c['nativeFeature'],consumer.CANONICAL_API_FEATURE)
if __name__=='__main__':unittest.main()
