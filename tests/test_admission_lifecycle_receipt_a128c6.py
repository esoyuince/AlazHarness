"""Offline custody of a staged native admission patch, not runtime replay."""
import ast,hashlib,json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
E=ROOT/'evidence/d3b-admission-lifecycle-a128c6'
def read(name):return json.loads((E/name).read_text(encoding='utf-8'))
class NativeAdmissionReceipt(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.r=read('native-004/result.json');cls.c=read('source-custody.json')
    def test_current_native46_and_original_prepared_compatibility(self):
        r=self.r;self.assertEqual((r['total'],r['passed'],r['errors'],r['failures'],r['skipped']),(46,46,0,0,0))
        self.assertEqual(r['result'],'PASS_NATIVE_LOCAL_ADMISSION_LIFECYCLE')
        self.assertEqual((r['newAdmissionMethods'],r['preparedCompatibilityMethods']),(24,22))
        text=(E/'native-004/tests.txt').read_text(encoding='utf-8')
        names=[line.split(' ',1)[0] for line in text.splitlines() if line.startswith('test_') and line.endswith(' ... ok')]
        self.assertEqual(len(names),46);self.assertEqual(len(set(names)),46)
        self.assertEqual(set(names),{row['case'] for row in r['caseEnd']})
    def test_actual508_imports_and_candidate_exact_immutable_native_feature(self):
        self.assertEqual(self.c['nativeImportCount'],508);self.assertEqual(len(self.r['nativeImports']),508)
        self.assertEqual(self.c['nativeFeature'],'1b7b31e14451baf1d56c3edbfa2cea69a8f7940c')
        self.assertEqual(self.c['nativeBase'],'1e97dd617b81120255304e472ce322befcdb9ccd')
        self.assertEqual({n:v['sha256'] for n,v in self.c['nativeImports'].items()},self.r['nativeImports'])
        self.assertEqual(self.c['candidateSources'],self.r['candidateSources'])
        for n,h in self.r['candidateSources'].items():
            self.assertEqual(hashlib.sha256((E/('candidate002-'+n.replace('/','__')+'.txt')).read_bytes()).hexdigest(),h,n)
        self.assertEqual(hashlib.sha256((E/'native-004/result.json').read_bytes()).hexdigest(),self.c['resultSha256'])
    def test_current_qa_source_and_no_hidden_native_replacement(self):
        for n,h in self.r['sourceHashes'].items():self.assertEqual(hashlib.sha256((ROOT/n).read_bytes()).hexdigest(),h,n)
        self.assertEqual(self.r['qaSha256'],self.r['sourceHashes']['scripts/qa/b123a6_native_prepared_api.py'])
        self.assertFalse(self.r['nativeMethodsReplaced']);self.assertFalse(self.c['nativeProductMethodsReplaced'])
        self.assertTrue(self.r['waitingWriteBarrierIsExplicitFixture']);self.assertTrue(self.r['cleanupObjectFaultInjectedExplicitly'])
    def test_watched_transitions_keep_existing_connections_and_rows(self):
        self.assertTrue(self.r['sameThreeCallerConnections']);self.assertFalse(self.r['epochAdvancedByAttachment'])
        self.assertTrue(self.r['checks'])
        for row in self.r['checks']:self.assertEqual((row['sqliteOpens'],row['rawDatabaseOpens'],row['rowChanges']),(0,0,0))
        self.assertTrue(self.r['temporaryRootRemoved']);self.assertEqual(len(self.r['caseEnd']),46)
        for row in self.r['caseEnd']:
            self.assertTrue(row['profileRemoved']);self.assertTrue(row['ownershipReleased']);self.assertEqual(row['pendingTasks'],0)
            self.assertEqual(row['registry'],{'live_generations':0,'retired_generations':0,'total_refcounts':0})
    def test_five_native_red_tests_and_response_fixture_failure_retained(self):
        first=read('native-001/result.json');self.assertEqual((first['total'],first['passed'],first['errors'],first['failures']),(39,38,1,0))
        correction=read('fixture-response-correction.json');self.assertFalse(correction['productChanged'])
        self.assertEqual(hashlib.sha256((E/'native001-qa.py.txt').read_bytes()).hexdigest(),correction['oldQaSha256'])
        second=read('native-002/result.json');self.assertEqual((second['total'],second['passed']),(39,39))
        self.assertEqual(first['candidateSources'],second['candidateSources']);self.assertNotEqual(second['candidateSources'],self.r['candidateSources'])
        bad=read('drained-regressions-before/result.json');self.assertEqual((bad['total'],bad['passed'],bad['failures'],bad['errors']),(5,0,5,0))
        old=(E/'native003-qa.py.txt').read_text(encoding='utf-8');new=(ROOT/'scripts/qa/a128c6_native_admission.py').read_text(encoding='utf-8')
        self.assertEqual(hashlib.sha256(old.encode()).hexdigest(),bad['sourceHashes']['scripts/qa/a128c6_native_admission.py'])
        def bodies(text):return {a.name:ast.get_source_segment(text,a) for a in ast.walk(ast.parse(text)) if isinstance(a,ast.FunctionDef) and a.name.startswith('test_')}
        oldmethods,newmethods=bodies(old),bodies(new)
        for test in bad['failureIds']:
            name=test.rsplit('.',1)[-1];self.assertEqual(oldmethods[name],newmethods[name]);self.assertIn(name,{v['case'] for v in self.r['caseEnd']})
    def test_awaited_unknown_retains_caller_and_new_transaction_gate_refuses(self):
        rows={v['case']:v for v in self.r['notes']}
        race=rows['test_active_admission_waiting_inside_native_write_refused_after_drain']
        self.assertEqual((race['nativeTransactionGateAfterDrain'],race['newRows']),('REFUSED',0))
        late=rows['test_drained_cleanup_await_new_replay_retains_unknown']
        self.assertEqual(late['bundleState'],'CLOSE_UNKNOWN');self.assertTrue(late['allCallerConnectionsOpen']);self.assertTrue(late['retryRefused'])
        names={v['case'] for v in self.r['caseEnd']}
        for name in ('test_active_cancelled_waiter_is_not_finished_native_write','test_drained_cleanup_cancelled_await_cannot_be_retried','test_active_queued_native_admission_is_retained_after_drain','test_active_existing_native_claim_can_settle_during_drain'):self.assertIn(name,names)
    def test_staged_patch_reproduces_bytes_without_installing(self):
        config=json.loads((ROOT/'config/hermes-admission-lifecycle-a128c6.json').read_text(encoding='utf-8'))
        self.assertEqual(config['activation'],'STAGED_NOT_INSTALLED');self.assertEqual(config['nativeFeature'],self.c['nativeFeature'])
        self.assertEqual(config['resultHashes'],self.r['candidateSources'])
        self.assertEqual(hashlib.sha256((ROOT/config['patchPath']).read_bytes()).hexdigest(),config['patchSha256'])
        self.assertEqual(config['patchSha256'],self.c['patchSha256'])
        proof=read('patch-application.json');self.assertTrue(proof['fiveFilesReproduced']);self.assertNotEqual(proof['duplicateApplyExitCode'],0)
        self.assertTrue(proof['firstFailurePreserved']);self.assertFalse(proof['productOrPatchChangedByCorrection'])
        before=read('patch-first-application-review.json');self.assertFalse(before['firstAttemptPassed'])
        self.assertTrue(all(v['nativeMatches'] and v['blobMatches'] and v['appliedMatchesAfterCRLFNormalization'] for v in before['rows']))
    def test_no_harness_agent_http_or_linux_acceptance_claimed(self):
        self.assertTrue(self.r['localNativeAdmissionGateExercised']);self.assertTrue(self.r['actualGuardedAdmissionAndClaimRows'])
        for key in ('fullAgentOrTurnRunnerExecuted','httpListenerActivated','harnessConsumerIntegrated','linuxIsolationTested','rootWslAction'):self.assertFalse(self.r[key],key)
        self.assertEqual(self.r['providerCalls'],0)
        config=json.loads((ROOT/'config/hermes-admission-lifecycle-a128c6.json').read_text(encoding='utf-8'))
        for key in ('harnessConsumerIntegrated','fullApiTurnWorkerQualified','httpListenerQualified','linuxIsolationQualified','providerExecutionQualified','sourceEnvelopePromoted'):self.assertFalse(config[key],key)
if __name__=='__main__':unittest.main()
