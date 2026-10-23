"""Current source-bound native Windows receipts; Linux boundary doubles stay explicit."""
import hashlib,json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
E=ROOT/'evidence/d3b-startup-consumer-s124b1'
class StartupConsumerReceipt(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r=json.loads((E/'native-002/result.json').read_text(encoding='utf-8'))
        cls.c=json.loads((E/'source-custody.json').read_text(encoding='utf-8'))
    def test_current_twenty_and_exact_sources(self):
        self.assertEqual((self.r['result'],self.r['total'],self.r['passed'],self.r['errors'],self.r['failures'],self.r['skipped']),('PASS_NATIVE_CONSUMER_WITH_WINDOWS_BOUNDARY_DOUBLES',20,20,0,0,0))
        for name,h in self.r['sourceHashes'].items():self.assertEqual(hashlib.sha256((ROOT/name).read_bytes()).hexdigest(),h,name)
        self.assertEqual(self.c['currentResultSha256'],hashlib.sha256((E/'native-002/result.json').read_bytes()).hexdigest())
    def test_all_loaded_native_sources_match_fixed_feature_and_envelope(self):
        manifest=json.loads((ROOT/'config/prepared-consumer-s124b1-sources.json').read_text(encoding='utf-8'))
        self.assertEqual((self.c['actualImportCount'],self.c['manifestCount']),(501,513))
        self.assertEqual(self.c['nativeFeature'],'1e97dd617b81120255304e472ce322befcdb9ccd')
        self.assertTrue(self.c['allActualImportsMatchImmutableGit'])
        for name,h in self.r['nativeImports'].items():
            self.assertEqual(self.c['actualImportedSources'][name]['sha256'],h);self.assertEqual(manifest['sources'][name],h)
        self.assertFalse(self.c['nativeFilesEdited'])
    def test_original_owner_gap_control_not_current_success(self):
        b=json.loads((E/'baseline-001/result.json').read_text(encoding='utf-8'))
        self.assertEqual(b['result'],'BASELINE_OWNER_HAS_NO_CONSUMER_GUARD')
        self.assertEqual(b['closedConnectionCount'],3);self.assertEqual(b['apiRunnerAfterClose'],['ATTACHED','PREPARED'])
        base=json.loads((E/'baseline.json').read_text(encoding='utf-8'))
        self.assertEqual(hashlib.sha256((E/'gateway_store_startup.py.before.txt').read_bytes()).hexdigest(),base['sources']['packages/claw-hermes/gateway_store_startup.py'])
        self.assertTrue(b['windowsLinuxLeaseMountColdBoundariesDoubled']);self.assertTrue(b['profileReleased']);self.assertTrue(b['temporaryHomeRemoved'])
    def test_two_regressions_retained_and_same_tests_pass_after_fix(self):
        old=json.loads((E/'native-001/result.json').read_text(encoding='utf-8'))
        self.assertEqual((old['total'],old['passed'],old['failures'],old['errors']),(20,18,2,0))
        self.assertEqual(old['sourceHashes']['scripts/qa/s124b1_native_consumer.py'],self.r['sourceHashes']['scripts/qa/s124b1_native_consumer.py'])
        self.assertEqual(old['sourceHashes']['packages/claw-hermes/gateway_prepared_consumer.py'],hashlib.sha256((E/'pre-retirement-fix-consumer.py.txt').read_bytes()).hexdigest())
        self.assertNotEqual(old['sourceHashes']['packages/claw-hermes/gateway_prepared_consumer.py'],self.r['sourceHashes']['packages/claw-hermes/gateway_prepared_consumer.py'])
        self.assertEqual(len(old['failureIds']),2)
    def test_real_case_cleanup_not_automatic_product_reconciliation(self):
        self.assertEqual(len(self.r['caseEnd']),20)
        ends={e['case']:e for e in self.r['caseEnd']}
        self.assertEqual(ends['test_api_runner_store_then_external_profile_release']['productStageBeforeFixtureCleanup'],'CLOSED')
        self.assertEqual(ends['test_unknown_cleanup_is_not_retried']['consumerStageBeforeFixtureCleanup'],'CLOSE_UNKNOWN')
        self.assertEqual(ends['test_constructor_failure_holds_slot_and_is_not_replayed']['consumerStageBeforeFixtureCleanup'],'FAILED_UNKNOWN')
        for end in ends.values():
            self.assertTrue(end['temporaryHomeRemoved']);self.assertTrue(end['profileReleased']);self.assertEqual(end['registry'],{'live_generations':0,'retired_generations':0,'total_refcounts':0})
        self.assertTrue(self.r['temporaryRootRemoved'])
    def test_no_new_database_or_write_during_watched_prepare_and_detach(self):
        self.assertGreaterEqual(len(self.r['checks']),3)
        for row in self.r['checks']:self.assertEqual((row['newConnections'],row['rawDatabaseOpens'],row['rowChanges']),(0,0,0))
        text=(E/'native-002/tests.txt').read_text(encoding='utf-8')
        cases=[line.split(' ',1)[0] for line in text.splitlines() if line.startswith('test_') and line.endswith(' ... ok')]
        self.assertEqual(len(cases),20);self.assertEqual(len(set(cases)),20)
        self.assertEqual(set(cases),{e['case'] for e in self.r['caseEnd']})
    def test_native_and_windows_doubled_boundaries_not_conflated(self):
        for key in ('actualNativeStoreStartupAndStores','actualNativeRunnerAndAdapter','linuxLeaseMountColdPreflightMetadataDoubled','nativeSqlLiveChecksReal','productBoundaryDoublesOnlyInExplicitFaultTests'):self.assertIs(self.r[key],True,key)
        for key in ('fullLinuxAcceptance','activeTaskObserversRequalified','serviceStarted','rootWslAction'):self.assertIs(self.r[key],False,key)
        self.assertEqual(self.r['providerCalls'],0)
        self.assertTrue(all(e['event'] in ('socket.bind','subprocess.Popen') for e in self.r['deniedEvents']))
        self.assertTrue(all('_has_ipv6' in e['callers'] for e in self.r['deniedEvents'] if e['event']=='socket.bind'))
if __name__=='__main__':unittest.main()
