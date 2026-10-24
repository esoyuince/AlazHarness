"""Current union native proof, no additional runtime execution by these tests."""
import hashlib,json,unittest
from historical_owner_b129d6 import executed_source_hash as pre_b129_hash
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
E=ROOT/'evidence/d3b-observer-work-joint-j127b6'
class JointObserverReceipt(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r=json.loads((E/'prepared-joint-001/result.json').read_text(encoding='utf-8'))
        cls.c=json.loads((E/'joint-source-custody.json').read_text(encoding='utf-8'))
    def test_same14_plus_two_real_task_composition_cases(self):
        r=self.r;self.assertEqual((r['total'],r['passed'],r['errors'],r['failures'],r['skipped']),(16,16,0,0,0))
        self.assertEqual((r['originalPreparedMethods'],r['jointCompositionMethods']),(14,2));self.assertTrue(r['testClassExtendedOnly'])
        text=(E/'prepared-joint-001/tests.txt').read_text(encoding='utf-8')
        names={l.split(' ',1)[0] for l in text.splitlines() if l.startswith('test_') and l.endswith(' ... ok')}
        self.assertEqual(len(names),16);self.assertEqual(names,{v['case'] for v in r['caseEnd']})
        self.assertIn('test_joint_real_authority_task_is_seen_by_attached_observer',names);self.assertIn('test_joint_real_runner_task_is_seen_by_attached_observer',names)
    def test_actual_current_three_product_sources_and_all_native_imports(self):
        for n,h in self.r['sourceHashes'].items():self.assertEqual(pre_b129_hash(ROOT,n,h),h,n)
        self.assertEqual(self.c['currentSourceHashes'],self.r['sourceHashes'])
        self.assertEqual(self.c['nativeImports'],self.r['nativeImports']);self.assertEqual(self.c['nativeImportCount'],501)
        manifest=json.loads((ROOT/'config/prepared-consumer-s124b1-sources.json').read_text(encoding='utf-8'))
        self.assertEqual(manifest['nativeFeature'],self.r['nativeFeature'])
        for n,h in self.r['nativeImports'].items():self.assertEqual(manifest['sources'][n],h,n)
        self.assertEqual(hashlib.sha256((E/'prepared-joint-001/result.json').read_bytes()).hexdigest(),self.c['nativeResultSha256'])
    def test_current_normal_observer_and_forty_work_guard_sources_remain_exact(self):
        for name in ('evidence/d3b-current-observers-o127b6/current-native-002/result.json','evidence/d3b-current-observers-o127b6/legacy-native-002/result.json','evidence/d3b-prepared-work-c127a6/native-final-002/result.json'):
            r=json.loads((ROOT/name).read_text(encoding='utf-8'))
            for n,h in r['sourceHashes'].items():self.assertEqual(pre_b129_hash(ROOT,n,h),h,n)
        self.assertTrue(self.c['normal15andLegacy15SourceUnchanged']);self.assertTrue(self.c['native40ConsumerSourcesUnchanged'])
    def test_old_prepared_result_not_relabelled_current_owner(self):
        old=json.loads((ROOT/'evidence/d3b-current-observers-o127b6/prepared-003/result.json').read_text(encoding='utf-8'));n='packages/claw-hermes/gateway_prepared_consumer.py'
        self.assertNotEqual(old['sourceHashes'][n],self.r['sourceHashes'][n])
        from historical_prepared_c127a6 import saved_generation_hash
        self.assertEqual(saved_generation_hash(ROOT,n,old['sourceHashes'][n]),old['sourceHashes'][n]);self.assertTrue(self.c['oldPrepared003ConsumerVersionHistorical'])
    def test_readonly_composition_and_successful_cleanup(self):
        for row in self.r['checks']:self.assertEqual((row['newConnections'],row['rawDatabaseOpens'],row['sqlRowChanges']),(0,0,0))
        self.assertTrue(self.r['temporaryRootRemoved'])
        for end in self.r['caseEnd']:
            self.assertTrue(end['temporaryProfileRemoved']);self.assertTrue(end['nativeOwnershipReleased']);self.assertEqual(end['registry']['total_refcounts'],0)
    def test_no_new_linux_or_active_borrowed_work_acceptance(self):
        r=self.r;self.assertTrue(r['linuxProfileLayoutMountColdBoundariesDoubled']);self.assertTrue(r['realTasksAreExplicitFaultFixtures']);self.assertTrue(r['realNativeRunnerAuthorityApiChannelStores'])
        for key in ('activeBorrowedWorkQualified','httpListenerStarted','kernelConfinementRerun','rootOrWslAction','nativeMethodsReplaced'):self.assertFalse(r[key],key)
        self.assertEqual(r['modelOrProviderCalls'],0)
if __name__=='__main__':unittest.main()
