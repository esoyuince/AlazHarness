"""Offline native retirement/source custody; no actual Task or database rerun."""
import ast,hashlib,json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
E=ROOT/'evidence/d3b-task-observer-c116a'
class NativeCompletionReceipt(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r=json.loads((E/'native-retirement-001/result.json').read_text(encoding='utf-8'))
    def test_native_completion_result_and_scope(self):
        r=self.r;self.assertEqual(r['result'],'PASS_NATIVE_TASK_RETIREMENT')
        self.assertEqual(tuple(r[k] for k in ('total','passed','errors','failures','skipped')),(8,8,0,0,0))
        exit=json.loads((E/'native-retirement-001-exit.json').read_text(encoding='utf-8'))
        self.assertEqual(exit['exitCode'],0);self.assertTrue(exit['sourcesUnchanged'])
        for k in ('realNativeAdapterStoresAndTasks','realProcessStartIdentity','producerHooksAreTestSeam','profileOwnershipReleased','bootstrapRemoved'):self.assertIs(r[k],True)
        for k in ('nativeIngressHooksIntegrated','profileMountVerified','httpStarted','fullIsolationTested','rootWslAction'):self.assertIs(r[k],False)
        self.assertEqual((r['newNetworkAttempts'],r['providerCalls']),(0,0));self.assertEqual(r['deniedImportProbes'],1)
    def test_current_sources_and_immutable_native_imports(self):
        manifest=json.loads((E/'native-source-custody.json').read_text(encoding='utf-8'))
        intent=json.loads((E/'native-retirement-001-intent.json').read_text(encoding='utf-8'))
        self.assertEqual(self.r['sources'],intent['sources']);self.assertEqual(manifest['currentLocalSources'],self.r['sources'])
        self.assertEqual(manifest['featureCommit'],'cc16c10b16a0ca8d80b23fd9be3f0e59ee605075')
        for n,h in self.r['sources'].items():self.assertEqual(hashlib.sha256((ROOT/n).read_bytes()).hexdigest(),h,n)
        self.assertEqual({n:v['sha256'] for n,v in manifest['actualImports'].items()},self.r['nativeImports'])
        self.assertTrue(manifest['sourceMatchesImmutableGit']);self.assertFalse(manifest['installedVendorChanged'])
    def test_all_eight_native_outcomes_are_in_raw_log(self):
        names=[s.split(' ',1)[0] for s in (E/'native-retirement-001/tests.txt').read_text(encoding='utf-8').splitlines() if s.startswith('test_') and s.endswith(' ... ok')]
        tree=ast.parse((ROOT/'scripts/qa/c116a_native_retirement.py').read_text(encoding='utf-8'))
        self.assertEqual(len(names),8);self.assertEqual(set(names),{n.name for n in ast.walk(tree) if isinstance(n,ast.AsyncFunctionDef) and n.name.startswith('test_')})
    def test_actual_normal_lifecycle_retirement_does_not_release_profile(self):
        r=self.r['records'];self.assertEqual(len(r),1);r=r[0]
        self.assertEqual(r['phases'],['QUEUED','RUNNING','SETTLING']);self.assertTrue(r['emptyTaskInventory']);self.assertTrue(r['profileStillOwned'])
        self.assertEqual(r['retired']['state'],'TASK_OBSERVATION_RETIRED')
        for k in ('nativeTaskRemovedHere','databaseWritesPerformed','runtimeAdmissionAuthorized','storeReleaseAuthorized'):self.assertIs(r['retired'][k],False)
    def test_original_snapshot_is_not_current_execution_claim(self):
        record=json.loads((E/'retirement-refinement.json').read_text(encoding='utf-8'))
        old=hashlib.sha256((E/'observer-before-completed-retirement.py.txt').read_bytes()).hexdigest()
        self.assertEqual(old,record['previousSha256']);self.assertNotEqual(old,record['currentSha256'])
        self.assertEqual(self.r['sources']['packages/claw-hermes/gateway_work_observer.py'],record['currentSha256'])
        self.assertFalse(record['otherWorktreeModified'])
if __name__=='__main__':unittest.main()
