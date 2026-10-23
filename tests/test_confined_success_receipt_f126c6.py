"""Scoped offline binding of actual two-cycle confinement and real POSIX fixtures."""
from pathlib import Path
import hashlib,json,unittest
ROOT=Path(__file__).resolve().parents[1]
E=ROOT/'evidence/d3b-confined-consumer-f126c6'
class CurrentConfinementReceipt(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r=json.loads((E/'reviewed-confined-success.json').read_text(encoding='utf-8'))
        cls.v=json.loads((E/'confined-success-independent-review.json').read_text(encoding='utf-8'))
    def test_real_posix_ten_checks_without_boundary_doubles(self):
        r=json.loads((E/'linux-layout-stdout.txt').read_bytes());intent=json.loads((E/'linux-layout-intent.json').read_text(encoding='utf-8'))
        self.assertEqual((r['result'],r['total'],r['errors'],r['failures'],r['skipped']),('PASS_REAL_POSIX_FINITE_LAYOUT_ONLY',10,0,0,0))
        self.assertEqual(r['uid'],[23001]*3);self.assertEqual(r['gid'],[23003]*3);self.assertTrue(r['temporaryRootRemoved'])
        self.assertEqual(r['inputSha256'],intent['inputSha256']);self.assertEqual(hashlib.sha256((ROOT/'scripts/qa/f126c6_linux_layout_checks.py').read_bytes()).hexdigest(),r['qaSha256'])
        self.assertEqual(hashlib.sha256((E/'prepared-layout-source.py.txt').read_bytes()).hexdigest(),r['layoutSha256'])
        self.assertEqual(r['layoutSha256'],self.v['harnessSourceHashes']['packages/claw-hermes/gateway_native_layout.py'])
        for key in ('boundaryMethodsReplaced','rootUsed','nativeRunnerExecuted','fullConfinementRerun'):self.assertFalse(r[key],key)
    def test_both_actual_final_exec_cycles_not_relabelled_partial_attempts(self):
        self.assertEqual(self.r['result'],'PASS_SCOPED_CONFINED_PREPARED_CONSUMER');self.assertIsNone(self.r['error']);self.assertFalse(self.r['forcedCleanup'])
        self.assertEqual(self.r['originalRawSha256'],self.v['originalRawSha256']);self.assertEqual(self.v['epochSequence'],[1,2])
        children=self.r['children'];self.assertEqual([c['mode'] for c in children],['write','read']);self.assertEqual([c['epoch'] for c in children],[1,2])
        self.assertEqual(children[0]['stores'],children[1]['stores'])
        for c in children:
            self.assertEqual(c['result'],'PASS_CONFINED_PREPARED_CONSUMER');self.assertEqual(c['checkCount'],41);self.assertTrue(all(v is True for v in c['checks'].values()))
            self.assertEqual(c['pid'],c['receipt']['pid']);self.assertEqual(c['receipt']['profileLayout'],'hermes-native-prepared-three-stores-cold-v1')
            self.assertEqual(c['receipt']['afterDrop']['uids'],[23001]*4);self.assertEqual(c['receipt']['afterDrop']['gids'],[23003]*4)
            self.assertEqual(c['receipt']['afterDrop']['groups'],[]);self.assertTrue(all(v==0 for v in c['receipt']['afterDrop']['caps'].values()))
            self.assertEqual(c['receipt']['filesystem']['landlockAbi'],3);self.assertTrue(c['checks']['seccomp_namespace_reentry_denied'])
    def test_actual_loaded_elf_bytes_match_static_independent_target(self):
        elfs=json.loads((E/'elf-custody.json').read_text(encoding='utf-8'))['elfs']
        self.assertEqual((self.v['nativeCount'],self.v['dependencyFileCount'],self.v['transportFileCount'],self.v['fullRuntimeManifestCount']),(513,1162,677,1805))
        for c in self.r['children']:
            self.assertEqual(c['sourceCount'],820);self.assertEqual(len(c['actualBinaryImports']),13)
            self.assertEqual({n.removeprefix('dependencies/'):h for n,h in c['actualBinaryImports'].items()},{n:v['elfSha256'] for n,v in elfs.items()})
            self.assertEqual(c['sourceDigest'],self.r['actualLoadedSourceDigest'])
        for n in self.v['changedPreviousHarnessSources']:
            p=E/(Path(n).name+'.prepared-source.txt');self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(),self.v['harnessSourceHashes'][n])
    def test_current_success_keeps_provider_service_and_cleanup_scope_explicit(self):
        r=self.r;self.assertEqual(r['checkCount'],44);self.assertTrue(all(v is True for v in r['checks'].values()))
        for name in ('no_remaining_loop','no_remaining_fence','no_remaining_scopes','no_forced_cleanup','broker_private_files_unchanged','parent_mount_table_unchanged','exactly_two_authenticated_pings','zero_physical_provider_attempts','old_three_store_layout_still_rejects_prepared_scaffold'):
            self.assertTrue(r['checks'][name])
        for c in r['children']:
            for name in ('nativeMethodsReplaced','coldHelpersDoubled','kernelBoundaryDoubled','activeTaskObserversQualified','serviceOrAdmissionEnabled','fullD3BAccepted'):self.assertFalse(c[name],name)
            self.assertEqual(c['providerSends'],0)
        self.assertFalse(self.v['newPrivilegedRunByThisReview']);self.assertFalse(self.v['newFilesystemOrSyscallRights']);self.assertFalse(r['fullD3BAccepted'])
    def test_postfix_failures_retain_same_product_and_require_explicit_scratch(self):
        r=json.loads((E/'reviewed-postfix-failures.json').read_text(encoding='utf-8'));self.assertTrue(r['productSameInAttempts004005006']);self.assertFalse(r['persistentScratchAllowlistAdded'])
        self.assertEqual([x['attempt'] for x in r['records']],['004','005'])
        for x in r['records']:
            self.assertEqual(x['result'],'FAIL');self.assertEqual(x['phase'],'ORIGINAL_OWNER_CLOSE');self.assertFalse(x['forcedCleanup'])
            for n,h in x['productHashes'].items():self.assertEqual(h,self.v['harnessSourceHashes'][n])
        self.assertIn('cache/scratch/.last_prune',r['records'][1]['newProfilePaths'])
        for c in self.r['children']:self.assertTrue(c['checks']['explicit_tmp_uses_projected_scratch']);self.assertTrue(c['checks']['private_scratch_fresh'])
if __name__=='__main__':unittest.main()
