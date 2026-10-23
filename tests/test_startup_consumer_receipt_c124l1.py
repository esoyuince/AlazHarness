"""Current independent native evidence; neither a kernel nor new native run."""
from pathlib import Path
import hashlib,json,unittest
ROOT=Path(__file__).resolve().parents[1]
E=ROOT/'evidence/d3b-startup-consumer-c124l1'
class IndependentConsumerReceipt(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r=json.loads((E/'native-002/result.json').read_text(encoding='utf-8'))
        cls.c=json.loads((E/'current-source-custody.json').read_text(encoding='utf-8'))
    def test_terminal_native23_and_all_actual_case_lines(self):
        self.assertEqual((self.r['result'],self.r['total'],self.r['passed'],self.r['failures'],self.r['errors'],self.r['skipped']),('PASS_INDEPENDENT_NATIVE_OWNER_CONSUMER_WITH_WINDOWS_DOUBLES',23,23,0,0,0))
        log=(E/'native-002/tests.txt').read_text(encoding='utf-8');names=[s.split(' ',1)[0] for s in log.splitlines() if s.startswith('test_') and s.endswith(' ... ok')]
        self.assertEqual(len(names),23);self.assertEqual(len(set(names)),23);self.assertEqual(set(names),{e['case'] for e in self.r['caseEnd']})
        self.assertTrue(self.r['temporaryRootRemoved'])
    def test_current_sources_and_native_immutable_imports(self):
        for name,h in self.r['sourceHashes'].items():self.assertEqual(hashlib.sha256((ROOT/name).read_bytes()).hexdigest(),h,name)
        self.assertEqual(self.c['feature'],'1e97dd617b81120255304e472ce322befcdb9ccd')
        self.assertEqual(self.c['actualNativeImportCount'],len(self.r['nativeImports']))
        self.assertEqual({n:v['sha256'] for n,v in self.c['actualNativeImports'].items()},self.r['nativeImports'])
        self.assertTrue(self.c['allActualImportsMatchImmutableFeature']);self.assertFalse(self.c['productEditedByIndependentTask'])
        self.assertEqual(self.c['currentResultSha256'],hashlib.sha256((E/'native-002/result.json').read_bytes()).hexdigest())
    def test_watched_no_fourth_connection_database_open_or_row_write(self):
        self.assertTrue(self.r['checks'])
        for row in self.r['checks']:self.assertEqual((row['sqliteOpens'],row['rawDatabaseOpens'],row['sqlRowChanges']),(0,0,0))
        self.assertIn('test_borrower_reuses_exact_handles_once_and_owner_close_refuses',{e['case'] for e in self.r['checks']})
        self.assertIn('test_ordered_detach_leaves_handles_until_owner_and_lease_until_caller',{e['case'] for e in self.r['checks']})
    def test_fixture_cleanup_never_relabels_unknown_product_state(self):
        ends={e['case']:e for e in self.r['caseEnd']}
        self.assertEqual(ends['test_cancelled_real_api_cleanup_await_is_unknown_not_retryable']['consumerStageBeforeIsolatedFixtureCleanup'],'CLOSE_UNKNOWN')
        self.assertEqual(ends['test_cancelled_preparation_after_real_authority_holds_unfinished_consumer']['consumerStageBeforeIsolatedFixtureCleanup'],'FAILED_UNKNOWN')
        self.assertEqual(ends['test_ordered_detach_leaves_handles_until_owner_and_lease_until_caller']['productStageBeforeIsolatedFixtureCleanup'],'CLOSED')
        for e in ends.values():
            self.assertTrue(e['profileRemoved']);self.assertTrue(e['nativeOwnerReleased']);self.assertEqual(e['pendingAsyncTasks'],0)
            self.assertEqual(e['registry'],{'live_generations':0,'retired_generations':0,'total_refcounts':0})
    def test_original_close_gap_control_has_exact_old_source(self):
        b=json.loads((E/'original-close-control/result.json').read_text(encoding='utf-8'))
        self.assertEqual(b['result'],'ORIGINAL_CLOSE_AWARENESS_GAP_CONFIRMED');self.assertEqual(b['closedStoreHandles'],3)
        self.assertEqual(b['after'],{'api':'ATTACHED','runner':'PREPARED','stores':'CLOSED'})
        self.assertEqual(hashlib.sha256((E/'gateway_store_startup.original.py.txt').read_bytes()).hexdigest(),b['sourceHashes']['packages/claw-hermes/gateway_store_startup.py'])
        self.assertEqual(hashlib.sha256((ROOT/'scripts/qa/c124l1_original_close_control.py').read_bytes()).hexdigest(),b['sourceHashes']['scripts/qa/c124l1_original_close_control.py'])
        self.assertTrue(b['temporaryProfileRemoved']);self.assertTrue(b['nativeOwnershipReleased'])
        self.assertTrue(b['linuxActorLeaseLayoutColdLiveBoundariesDoubled']);self.assertFalse(b['upstreamDefaultBugClaimed'])
    def test_real_five_defects_fixed_without_weakening_same_assertions(self):
        b=json.loads((E/'postdetach-before/result.json').read_text(encoding='utf-8'))
        self.assertEqual((b['total'],b['passed'],b['failures'],b['errors']),(5,0,5,0))
        self.assertTrue(b['temporaryRootRemoved']);self.assertTrue(self.c['sameQaAsFiveFailingReproduction'])
        self.assertEqual(b['sourceHashes']['scripts/qa/c124l1_native_consumer_checks.py'],self.r['sourceHashes']['scripts/qa/c124l1_native_consumer_checks.py'])
        helper='packages/claw-hermes/gateway_prepared_consumer.py'
        self.assertEqual(b['sourceHashes'][helper],hashlib.sha256((E/('candidate001-'+helper.replace('/','__')+'.txt')).read_bytes()).hexdigest())
        self.assertNotEqual(b['sourceHashes'][helper],self.r['sourceHashes'][helper])
        failures={name.rsplit('.',1)[-1] for name in b['failureIds']}
        self.assertEqual(len(failures),5);self.assertTrue(failures.issubset({e['case'] for e in self.r['caseEnd']}))
    def test_scope_and_failed_first_fixture_remain_explicit(self):
        for key in ('realNativeStoreStartupRunnerApiStores','nativeSqlLiveGatesReal','linuxActorLeaseLayoutColdMountMetadataDoubled','explicitFaultsIncludePausedInitializerAndMemoryCleanup'):self.assertTrue(self.r[key],key)
        for key in ('fullLinuxAcceptance','serviceAdmissionOrListenerActivated','activeTaskObserverRequalified','rootWslAction'):self.assertFalse(self.r[key],key)
        self.assertEqual(self.r['providerCalls'],0)
        self.assertTrue(all(e['event'] in ('socket.bind','subprocess.Popen') for e in self.r['deniedEvents']))
        correction=json.loads((E/'fixture-correction001.json').read_text(encoding='utf-8'))
        self.assertEqual(correction['priorExitCode'],1);self.assertTrue(correction['priorJsonResultAbsent']);self.assertTrue(correction['productUntouched'])
        self.assertTrue(correction['terminalProcessOwnTempCleanup']['removedAfterChildTerminal']);self.assertTrue(correction['firstPassNotClaimed'])
        self.assertEqual(hashlib.sha256((E/'native001-qa.py.txt').read_bytes()).hexdigest(),correction['oldQaSha256'])
if __name__=='__main__':unittest.main()
