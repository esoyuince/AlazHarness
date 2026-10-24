from historical_api_i133p1 import executed_source_hash
"""Offline executed-source and scope receipts, not more runtime tests."""
from pathlib import Path
import hashlib,json,unittest
ROOT=Path(__file__).resolve().parents[1]
E=ROOT/'evidence/d3b-active-owner-b129d6'
class ActiveOwnerReceipt(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.current=json.loads((E/'native-001/result.json').read_text(encoding='utf-8'))
        cls.compat=json.loads((E/'compat-001/result.json').read_text(encoding='utf-8'))
        cls.custody=json.loads((E/'source-custody.json').read_text(encoding='utf-8'))
    def test_both_current_and_prepared_default_execute_on_current_harness(self):
        for label,r,count in (('native-001',self.current,23),('compat-001',self.compat,20)):
            self.assertEqual((r['total'],r['passed'],r['errors'],r['failures'],r['skipped']),(count,count,0,0,0))
            self.assertTrue(r['temporaryRootRemoved'])
            self.assertEqual(sum(l.startswith('test_') and l.endswith(' ... ok') for l in (E/label/'tests.txt').read_text(encoding='utf-8').splitlines()),count)
            for n,h in r['sourceHashes'].items():self.assertEqual(executed_source_hash(ROOT,n,h),h,n)
    def test_native_imports_exact_for_two_distinct_generations(self):
        for label,r in (('native-001',self.current),('compat-001',self.compat)):
            record=self.custody['runs'][label];self.assertEqual(len(r['nativeImports']),record['importCount'])
            self.assertEqual({n:v['sha256'] for n,v in record['actualNativeImports'].items()},r['nativeImports'])
            self.assertEqual(hashlib.sha256((E/label/'result.json').read_bytes()).hexdigest(),record['resultSha256'])
        self.assertNotEqual(self.custody['runs']['native-001']['feature'],self.custody['runs']['compat-001']['feature'])
        manifest=json.loads((ROOT/'config/admission-consumer-b129d6-sources.json').read_text(encoding='utf-8'))
        self.assertEqual(len(manifest['sources']),517)
        for n,h in self.current['nativeImports'].items():self.assertEqual(manifest['sources'][n],h,n)
        for n,h in self.custody['currentProductModules'].items():self.assertEqual(executed_source_hash(ROOT,n,h),h,n)
    def test_owner_drain_does_not_wait_for_writer_or_drop_cancelled_commit(self):
        races={r['case']:r for r in self.current['races']};self.assertEqual(len(races),2)
        a=races['test_drain_seals_while_real_sql_writer_waits_for_mutex'];self.assertTrue(a['blockedWriterRefused']);self.assertTrue(a['nativeMutexNotWaitedByDrain'])
        b=races['test_cancelled_carrier_does_not_close_original_owner_over_inflight_commit']
        for k in ('nativeTrackedWrite','cancelledCarrier','lateQueuedCommitRetained','originalOwnerCloseRefused'):self.assertTrue(b[k],k)
    def test_transition_observations_never_open_or_mutate_databases(self):
        self.assertTrue(self.current['checks'])
        for r in self.current['checks']:self.assertEqual((r['newConnections'],r['rawDatabaseOpens'],r['rowChanges']),(0,0,0))
    def test_cleanup_and_unknown_stages_remain_explicit(self):
        self.assertEqual(len(self.current['caseEnd']),23)
        for r in self.current['caseEnd']:
            self.assertTrue(r['profileRemoved']);self.assertTrue(r['nativeOwnershipReleased']);self.assertEqual(r['registry']['total_refcounts'],0)
        fault=next(r for r in self.current['caseEnd'] if r['case']=='test_native_transition_uncertainty_keeps_owner_without_retry')
        self.assertEqual(fault['beforeFixtureCleanup']['consumer'],'ADMISSION_UNKNOWN')
        self.assertEqual(fault['beforeFixtureCleanup']['owner'],'VERIFIED')
    def test_old_receipt_source_changes_do_not_relabel_kernel_acceptance(self):
        before=json.loads((E/'historical-receipts-before.json').read_text(encoding='utf-8'));after=json.loads((E/'historical-receipts-after.json').read_text(encoding='utf-8'))
        self.assertEqual((before['total'],before['failures'],after['total'],after['failures']),(426,18,426,0))
        self.assertFalse(after['oldRawResultsOrExpectedHashesModified']);self.assertFalse(after['oldNativeOrKernelTestsRerun'])
        from historical_owner_b129d6 import saved_generation_hash
        baseline=json.loads((E/'baseline.json').read_text(encoding='utf-8'))
        for n in ('gateway_store_startup.py','gateway_prepared_consumer.py','gateway_live_store_gate.py','gateway_response_live.py'):
            name='packages/claw-hermes/'+n;h=baseline['sources'][name]
            self.assertEqual(saved_generation_hash(ROOT,name,h),h)
            self.assertIsNone(saved_generation_hash(ROOT,name,'0'*64))
    def test_native_owner_acceptance_not_whole_agent_or_linux(self):
        r=self.current;self.assertTrue(r['originalOwnerAndNativeConstructorsAndSqlReal']);self.assertTrue(r['linuxActorLeaseMetadataMountColdDoubled']);self.assertTrue(r['explicitPostEffectTransitionFaultDoubled'])
        for n in ('wholeApiTurnOrAgentExecuted','queuedWorkRetiredAutomatically','linuxConfinementTested','rootWslAction'):self.assertFalse(r[n],n)
        self.assertEqual(r['providerCalls'],0);self.assertFalse(self.custody['nativeSourceChanged'])
if __name__=='__main__':unittest.main()
