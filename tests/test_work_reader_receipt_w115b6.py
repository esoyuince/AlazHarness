"""Offline custody of W115 real-native reads, not new store/worker executions."""
import hashlib,json,ast,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
E=ROOT/'evidence/d3b-work-health-w115b6'
sys.path.insert(0,str(ROOT/'packages/claw-hermes'))
import gateway_work_health_reader as reader

class NativeWorkReceipt(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r=json.loads((E/'native-windows-002/result.json').read_text(encoding='utf-8'))
        cls.intent=json.loads((E/'native-windows-002-intent.json').read_text(encoding='utf-8'))
    def test_actual_native_result_and_scope(self):
        self.assertEqual(self.r['result'],'PASS_SCOPED_NATIVE_WORK_METADATA')
        self.assertEqual(tuple(self.r[k] for k in ('total','passed','failures','errors','skipped')),(28,28,0,0,0))
        result=json.loads((E/'native-windows-002-exit.json').read_text(encoding='utf-8'))
        self.assertEqual(result['exitCode'],0);self.assertTrue(result['sourcesUnchanged']);self.assertTrue(result['nativeSourcesUnchanged'])
        for k in ('ownershipReleased','temporaryProfilesRemoved','producerInventoryIsExplicitFixture','storageVerificationIsFixture'):self.assertIs(self.r[k],True)
        for k in ('nativeClassesMocked','liveWorkerProcessesStarted','httpStarted','fullIsolationTested','rootUsed'):self.assertIs(self.r[k],False)
        self.assertEqual(self.r['providerCalls'],0)
    def test_current_source_bytes_match_tested_inputs(self):
        self.assertEqual(self.r['currentSources'],self.intent['sources'])
        for name,h in self.r['currentSources'].items():self.assertEqual(hashlib.sha256((ROOT/name).read_bytes()).hexdigest(),h,name)
        original=(E/'native-source-manifest.json').read_bytes();self.assertEqual(hashlib.sha256(original).hexdigest(),self.intent['nativeManifestSha256'])
        native=json.loads(original)
        for name,h in self.r['nativeSources'].items():self.assertEqual(native['files'][name]['sha256'],h,name)
        self.assertEqual(native['nativeFeature'],'cc16c10b16a0ca8d80b23fd9be3f0e59ee605075')
    def test_all_28_actual_method_outcomes_are_present(self):
        log=(E/'native-windows-002/tests.txt').read_text(encoding='utf-8')
        names=[s.split(' ',1)[0] for s in log.splitlines() if s.startswith('test_') and s.endswith(' ... ok')]
        tree=ast.parse((ROOT/'scripts/qa/w115b6_native_work_health.py').read_text(encoding='utf-8'))
        methods={n.name for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name.startswith('test_')}
        self.assertEqual(len(names),28);self.assertEqual(set(names),methods)
    def test_prior_candidate_failure_and_fixture_commit_are_preserved(self):
        old=json.loads((E/'native-windows-001/result.json').read_text(encoding='utf-8'))
        self.assertEqual((old['passed'],old['errors']),(22,1))
        self.assertEqual(old['errorIds'],['__main__.NativeWorkHealth.test_settled_native_rows_disappear_without_reader_cleanup'])
        self.assertIn('work_native_transaction_active',(E/'native-windows-001/tests.txt').read_text(encoding='utf-8'))
        correction=json.loads((E/'fixture-correction.json').read_text(encoding='utf-8'))
        self.assertTrue(correction['selectedPolicyChanged']);self.assertFalse(correction['actualProducerCollectorImplemented'])
    def test_discarded_policy_remains_evidence_not_second_engine(self):
        selected=json.loads((E/'single-policy-selection.json').read_text(encoding='utf-8'))
        for name,record in selected['discardedOwnPolicyRetained'].items():
            self.assertEqual(hashlib.sha256((ROOT/record['savedAs']).read_bytes()).hexdigest(),record['sha256'])
        self.assertFalse((ROOT/'packages/claw-hermes/gateway_work_health_policy.py').exists())
        self.assertFalse((ROOT/'tests/test_work_health_policy_w115b6.py').exists())
    def test_reader_output_cannot_mint_live_storage_flags(self):
        fields=set(reader.CommittedWorkRows.__dataclass_fields__)
        self.assertTrue({'identity','admissions','runs','responses','unresolved_workers'}<=fields)
        self.assertFalse(fields&{'storage_verified','task_alive','complete','healthy','runtimeAdmissionAuthorized'})
    def test_owner_selection_is_parameterized_and_empty_is_bounded(self):
        sql,args=reader.NativeWorkReader._selection('run_id',("x') OR 1=1 --",))
        self.assertEqual(sql,' OR run_id IN (?)');self.assertEqual(args,("x') OR 1=1 --",))
        self.assertEqual(reader.NativeWorkReader._selection('run_id',()),('',()))

if __name__=='__main__':unittest.main()
