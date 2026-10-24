"""Offline custody of current native work-guard cases; no runtime replay."""
import ast,hashlib,json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
E=ROOT/'evidence/d3b-prepared-work-c127a6'
def read(name):return json.loads((E/name).read_text(encoding='utf-8'))
def cases(raw):
    return {n.name:ast.dump(n,include_attributes=False) for n in ast.walk(ast.parse(raw)) if isinstance(n,ast.FunctionDef) and n.name.startswith('test_')}
class PreparedWorkReceipt(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.r=read('native-final-002/result.json');cls.c=read('current-source-custody.json')
    def test_current_complete_native_scope_forty(self):
        r=self.r;self.assertEqual((r['total'],r['passed'],r['errors'],r['failures'],r['skipped']),(40,40,0,0,0))
        self.assertEqual((r['ownMethods'],r['compatMethods']),(17,23));self.assertTrue(r['temporaryRootRemoved'])
        self.assertEqual(sum(l.startswith('test_') and l.endswith(' ... ok') for l in (E/'native-final-002/tests.txt').read_text(encoding='utf-8').splitlines()),40)
    def test_current_source_bytes_and_exact_native_envelope(self):
        for n,h in self.r['sourceHashes'].items():self.assertEqual(hashlib.sha256((ROOT/n).read_bytes()).hexdigest(),h,n)
        self.assertEqual(self.c['nativeFeature'],'1e97dd617b81120255304e472ce322befcdb9ccd')
        self.assertEqual(self.c['actualNativeImportCount'],501);self.assertEqual({n:v['sha256'] for n,v in self.c['actualNativeImports'].items()},self.r['nativeImports'])
        envelope=json.loads((ROOT/'config/prepared-consumer-s124b1-sources.json').read_text(encoding='utf-8'))['sources']
        for n,h in self.r['nativeImports'].items():self.assertEqual(envelope[n],h,n)
        self.assertEqual(self.c['currentResultSha256'],hashlib.sha256((E/'native-final-002/result.json').read_bytes()).hexdigest())
    def test_all_known_work_refused_before_detach_effects(self):
        self.assertEqual(len(self.r['detachObservations']),8)
        for row in self.r['detachObservations']:
            self.assertEqual(row['stages'],['ATTACHED','ATTACHED','PREPARED']);self.assertEqual(row['refusalType'],'PreparedConsumerRejected')
        self.assertTrue(self.r['checks'])
        for row in self.r['checks']:self.assertEqual((row['sqliteOpens'],row['rawDatabaseOpens'],row['sqlRowChanges']),(0,0,0))
    def test_initial_and_additional_failures_preserved_same_assertions(self):
        first=read('native-before-corrected/result.json');extra=read('review-before/result.json')
        self.assertEqual((first['total'],first['passed'],first['failures'],first['errors']),(12,2,10,0))
        self.assertEqual((extra['total'],extra['passed'],extra['failures'],extra['errors']),(5,0,5,0))
        current=cases((ROOT/'scripts/qa/c127a6_native_prepared_work.py').read_text(encoding='utf-8'))
        previous=cases((E/'fixed001-qa.py.txt').read_text(encoding='utf-8'))
        self.assertEqual(len(previous),12)
        for name,body in previous.items():self.assertEqual(current[name],body,name)
        self.assertEqual(extra['sourceHashes']['scripts/qa/c127a6_native_prepared_work.py'],self.r['sourceHashes']['scripts/qa/c127a6_native_prepared_work.py'])
        helper='packages/claw-hermes/gateway_prepared_consumer.py'
        self.assertEqual(hashlib.sha256((E/'consumer-before.py.txt').read_bytes()).hexdigest(),first['sourceHashes'][helper])
        self.assertEqual(hashlib.sha256((E/'fixed001-consumer.py.txt').read_bytes()).hexdigest(),extra['sourceHashes'][helper])
        self.assertNotEqual(extra['sourceHashes'][helper],self.r['sourceHashes'][helper])
    def test_each_fixture_task_and_native_owner_cleaned(self):
        self.assertEqual(len(self.r['caseEnd']),40)
        for end in self.r['caseEnd']:
            self.assertTrue(end['profileRemoved']);self.assertTrue(end['nativeOwnerReleased']);self.assertEqual(end['pendingAsyncTasks'],0)
            self.assertEqual(end['registry'],{'live_generations':0,'retired_generations':0,'total_refcounts':0})
        race=next(x for x in self.r['caseEnd'] if x['case']=='test_work_arriving_during_api_cleanup_retains_unknown')
        self.assertEqual(race['consumerStageBeforeIsolatedFixtureCleanup'],'CLOSE_UNKNOWN')
    def test_source_import_fixture_error_not_hidden_or_bypassed(self):
        old=read('native-before/result.json');self.assertEqual((old['total'],old['passed'],old['errors'],old['failures']),(12,2,3,7))
        correction=read('fixture-source-scope-correction.json');self.assertFalse(correction['manifestOrProductChanged']);self.assertTrue(correction['expectedAssertionsUnchanged'])
        self.assertEqual(hashlib.sha256((E/'native-before-qa.py.txt').read_bytes()).hexdigest(),old['sourceHashes']['scripts/qa/c127a6_native_prepared_work.py'])
    def test_historical_linux_results_remain_at_original_consumer(self):
        from historical_prepared_c127a6 import saved_generation_hash
        b=read('baseline.json');h=b['sources']['packages/claw-hermes/gateway_prepared_consumer.py']
        self.assertEqual(saved_generation_hash(ROOT,'packages/claw-hermes/gateway_prepared_consumer.py',h),h)
        self.assertIsNone(saved_generation_hash(ROOT,'packages/claw-hermes/gateway_prepared_consumer.py','0'*64))
        self.assertNotEqual(h,self.r['sourceHashes']['packages/claw-hermes/gateway_prepared_consumer.py'])
        old=read('historical-receipts-before.json');new=read('historical-receipts-after.json')
        self.assertEqual((old['total'],old['failures'],new['total'],new['failures']),(388,6,388,0))
        self.assertFalse(new['rawOldResultsOrExpectedHashesChanged']);self.assertTrue(new['noOldNativeOrKernelRunsReexecuted'])
    def test_native_fault_fixtures_are_not_active_job_or_linux_acceptance(self):
        r=self.r
        for name in ('realTasksThreadsAndNativeWorkerRecord','taskRegistryFaultInjectionExplicit','windowsActorLeaseMountColdBoundariesDoubled'):self.assertIs(r[name],True,name)
        for name in ('nativeProductMethodsReplaced','completeAgentOrTurnRunnerExecuted','linuxConfinementRerun','serviceAdmissionActivated'):self.assertIs(r[name],False,name)
        self.assertEqual(r['providerCalls'],0);self.assertFalse(self.c['nativeOrManifestChanged']);self.assertFalse(self.c['newKernelAcceptance'])
if __name__=='__main__':unittest.main()
