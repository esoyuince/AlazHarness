"""Offline receipt checks for16 native-data policy cases; NOT a native rerun."""
import ast,hashlib,json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
E=ROOT/'evidence/d3b-work-health-b115w6'
class WorkHealthProof(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r=json.loads((E/'windows-native-001/result.json').read_text(encoding='utf-8'))
        cls.c=json.loads((E/'native-001-source-custody.json').read_text(encoding='utf-8'))
    def test_terminal_sixteen_native_cases_not_collector_acceptance(self):
        r=self.r;self.assertEqual(r['result'],'PASS_NATIVE_DATA_MAPPING_ONLY')
        self.assertEqual((r['total'],r['passed'],r['errors'],r['failures'],r['skipped']),(16,16,0,0,0))
        for k in ('profileReleased','temporaryProfilesRemoved','realNativeDatabases','liveTaskInventoryIsTestFixture','storageVerificationFlagIsFixture'):self.assertIs(r[k],True)
        for k in ('nativeMethodsReplaced','realAdapterCollectorTested','healthyBusyHttpIntegrated','kernelIsolationTested','rootOrWslAction'):self.assertIs(r[k],False)
        self.assertEqual(r['providerCalls'],0)
    def test_exact_current_selected_policy_and_probe(self):
        names={'policySha256':'packages/claw-hermes/gateway_work_health.py','qaSha256':'scripts/qa/b115w6_native_work_health.py','fixtureSourceSha256':'scripts/qa/a112x7d_response_probe.py'}
        intent=json.loads((E/'native-001-intent.json').read_text(encoding='utf-8'))
        for field,name in names.items():
            digest=hashlib.sha256((ROOT/name).read_bytes()).hexdigest()
            self.assertEqual(digest,self.r[field]);self.assertEqual(digest,intent['sources'][name])
        selected=json.loads((E/'single-policy-owner-confirmed.json').read_text(encoding='utf-8'))
        self.assertEqual(selected['selectedPolicySha256'],self.r['policySha256'])
        self.assertIs(selected['duplicateRuntimePolicyPresent'],False)
    def test_all_imported_native_source_bytes_match_immutable_commit(self):
        self.assertEqual(self.c['feature'],'cc16c10b16a0ca8d80b23fd9be3f0e59ee605075')
        self.assertIs(self.c['allActualImportsMatchedImmutableGit'],True)
        self.assertEqual(self.c['count'],len(self.r['nativeImports']))
        self.assertEqual({n:v['sha256'] for n,v in self.c['actualImportedSources'].items()},self.r['nativeImports'])
        for name in ('hermes_state.py','hermes_state_runtime.py','gateway/platforms/api_server_run_idempotency.py','gateway/platforms/api_server_response_store.py'):
            self.assertIn(name,self.r['nativeImports'])
    def test_all_native_case_lines_and_no_policy_writes(self):
        log=(E/'windows-native-001/tests.txt').read_text(encoding='utf-8')
        names=[l.split(' ',1)[0] for l in log.splitlines() if l.startswith('test_') and l.endswith(' ... ok')]
        self.assertEqual(len(names),16);self.assertEqual(len(set(names)),16)
        self.assertEqual({o['case'] for o in self.r['observations']},set(names))
        for o in self.r['observations']:
            self.assertIs(o['observedTaskInventoryIsFixture'],True);self.assertEqual(o['sqlChangesByPolicy'],0)
            self.assertIs(o['noFileOrConnectionOpenByPolicy'],True)
    def test_committed_settlement_sequence_and_failure_states_are_retained(self):
        rows=self.r['observations']
        seq=[o['state'] for o in rows if o['case']=='test_real_complete_settlement_chain_to_idle']
        self.assertEqual(seq,['BUSY','BUSY','BUSY','BUSY','IDLE'])
        self.assertEqual([o['state'] for o in rows if o['case']=='test_real_response_transaction_not_rolled_back_by_observer'],['UNOBSERVABLE','BUSY'])
        for case in ('test_real_unowned_queue_requires_reconciliation','test_real_partial_settlement_owner_gone_is_not_idle','test_real_dead_owner_does_not_get_rebuilt_from_rows'):
            self.assertEqual([o['state'] for o in rows if o['case']==case],['RECONCILE_REQUIRED'])
        self.assertEqual([o['state'] for o in rows if o['case']=='test_real_drain_does_not_turn_completed_owner_into_new_capacity'],['DRAINING','DRAINING'])
if __name__=='__main__':unittest.main()
