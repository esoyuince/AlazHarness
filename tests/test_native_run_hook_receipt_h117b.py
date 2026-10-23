"""Offline custody of native H117 producer tests; not another native run."""
import hashlib,json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
E=ROOT/'evidence/d3b-native-run-hooks-h117b'
class NativeProducerReceipt(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r=json.loads((E/'native-002/result.json').read_text(encoding='utf-8'))
        cls.cfg=json.loads((ROOT/'config/hermes-run-hooks-h117b.json').read_text(encoding='utf-8'))
    def test_terminal_twenty_native_methods_and_scope(self):
        r=self.r;self.assertEqual(r['result'],'PASS_NATIVE_PRODUCER_HOOKS_SCOPED')
        self.assertEqual((r['total'],r['passed'],r['errors'],r['failures'],r['skipped']),(20,20,0,0,0))
        for key in ('nativeEntryAndTaskLifecycleReal','nativeAuthDecoratorTested','agentExecutionDoubled','authorityAndBotDeliveryBoundariesDoubled','profileReleased','bootstrapRemoved','sourcesUnchanged'):self.assertIs(r[key],True)
        for key in ('nativeTaskMapsWrittenByFixture','authenticationMiddlewareTested','httpListenerStarted','canonicalExecutorHealthProven','fullIsolationTested','rootWslAction'):self.assertIs(r[key],False)
        self.assertEqual(r['providerCalls'],0);self.assertEqual(r['newNetworkAttempts'],0);self.assertEqual(r['deniedImportProbes'],1)
    def test_executed_local_sources_and_native_imports_match(self):
        for name,h in self.r['sources'].items():self.assertEqual(hashlib.sha256((ROOT/name).read_bytes()).hexdigest(),h,name)
        c=json.loads((E/'native-source-custody.json').read_text(encoding='utf-8'))
        self.assertEqual(c['nativeFeatureCommit'],self.cfg['nativeFeatureCommit']);self.assertTrue(c['allActualImportsMatched'])
        self.assertEqual(c['count'],len(self.r['nativeImports']))
        self.assertEqual({n:v['sha256'] for n,v in c['sources'].items()},self.r['nativeImports'])
        for n,h in self.cfg['resultHashes'].items():self.assertEqual(self.r['nativeImports'][n],h)
    def test_patch_exact_apply_and_duplicate_refusal_without_activation(self):
        patch=ROOT/self.cfg['patchPath'];h=hashlib.sha256(patch.read_bytes()).hexdigest()
        proof=json.loads((E/'patch-application.json').read_text(encoding='utf-8'))
        self.assertEqual(h,self.cfg['patchSha256']);self.assertEqual(h,proof['patchSha256'])
        self.assertEqual(proof['outputHashes'],self.cfg['resultHashes']);self.assertEqual(proof['checkAndApplyExitCode'],0)
        self.assertNotEqual(proof['repeatApplicationExitCode'],0);self.assertTrue(proof['temporaryExportRemoved'])
        self.assertEqual(self.cfg['activation'],'NOT_INSTALLED');self.assertFalse(self.cfg['nativeListenerAuthorized'])
        self.assertFalse(self.cfg['canonicalExecutorHealthVerified'])
    def test_all_twenty_actual_outcomes_match_log(self):
        log=(E/'native-002/tests.txt').read_text(encoding='utf-8')
        names={line.split(' ',1)[0] for line in log.splitlines() if line.startswith('test_') and line.endswith(' ... ok')}
        self.assertEqual(len(names),20);self.assertEqual({case['case'] for case in self.r['cases']},names)
        self.assertTrue(all(case['nativeWorkersRemaining']==0 for case in self.r['cases']))
    def test_native_event_order_roles_and_no_duplicate_acceptance(self):
        cases={r['case']:r for r in self.r['cases']}
        exact=['ACCEPTED','CREATED','STARTED','EXECUTION_RETURNED','RETIRED','DONE']
        for name in ('test_native_complete_lifecycle_and_immutable_ingress_identity','test_idempotent_replay_does_not_emit_another_admission'):
            self.assertEqual(cases[name]['eventPhases'],exact);self.assertEqual(cases[name]['dummyAgentCalls'],1)
        self.assertEqual(cases['test_default_disabled_preserves_native_run']['eventPhases'],[])
        self.assertEqual(cases['test_native_bearer_rejection_precedes_any_notification']['eventPhases'],[])
        self.assertEqual(cases['test_canonical_authority_path_is_labelled_watcher_not_executor']['roles'],['canonical_authority_observer'])
        self.assertEqual(cases['test_external_owner_path_is_labelled_watcher']['roles'],['external_owner_observer'])
        self.assertEqual(cases['test_native_complete_lifecycle_and_immutable_ingress_identity']['roles'],['executor_thread_carrier'])
        cancelled=cases['test_cancelled_carrier_done_does_not_hide_live_native_thread']['eventPhases']
        self.assertEqual(cancelled,['ACCEPTED','CREATED','STARTED','RETIRED','DONE'])
    def test_first_auth_fixture_failure_retained_and_product_unchanged(self):
        old=json.loads((E/'native-001/result.json').read_text(encoding='utf-8'))
        self.assertEqual(old['result'],'FAIL');self.assertEqual(old['errors'],15)
        correction=json.loads((E/'auth-fixture-correction.json').read_text(encoding='utf-8'));self.assertFalse(correction['productSourceChanged'])
        before=json.loads((E/'native-001-intent.json').read_text(encoding='utf-8'))['sources']
        after=json.loads((E/'native-002-intent.json').read_text(encoding='utf-8'))['sources']
        for n,h in self.cfg['resultHashes'].items():self.assertEqual(before['native:'+n],h);self.assertEqual(after['native:'+n],h)
        self.assertNotEqual(old['sources']['scripts/qa/h117b_native_producer.py'],self.r['sources']['scripts/qa/h117b_native_producer.py'])
if __name__=='__main__':unittest.main()
