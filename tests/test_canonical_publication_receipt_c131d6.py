"""Offline current canonical-publication receipts, not new native executions."""
from pathlib import Path
import ast,hashlib,json,unittest
ROOT=Path(__file__).resolve().parents[1]
E=ROOT/'evidence/d3b-canonical-api-c131d6'
def read(name):return json.loads((E/name).read_text(encoding='utf-8'))
class CanonicalPublicationReceipt(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.r=read('native-004/publication-result.json');cls.c=read('source-custody.json');cls.cfg=json.loads((ROOT/'config/hermes-canonical-api-c131d6.json').read_text(encoding='utf-8'))
    def test_final_fifty_three_native_methods_and_cleanup(self):
        r=self.r;self.assertEqual((r['result'],r['total'],r['passed'],r['failures'],r['errors'],r['skipped']),('PASS_NATIVE_CANONICAL_API_PUBLICATION',53,53,0,0,0))
        names={l.split(' ',1)[0] for l in (E/'native-004/tests.txt').read_text(encoding='utf-8').splitlines() if l.startswith('test_') and l.endswith(' ... ok')}
        self.assertEqual(len(names),53);self.assertEqual(names,{x['case'] for x in r['caseEnd']});self.assertEqual(len(r['caseEnd']),53)
        self.assertTrue(r['temporaryRootRemoved'])
        for x in r['caseEnd']:
            self.assertTrue(x['temporaryProfileRemoved']);self.assertTrue(x['ownershipReleased']);self.assertEqual(x['pendingTasks'],0);self.assertEqual(x['registry']['total_refcounts'],0)
    def test_native_source_driver_and_existing_fixture_bytes(self):
        self.assertEqual({n:v['sha256'] for n,v in self.c['actualImportedSources'].items()},self.r['nativeImports'])
        self.assertEqual(self.c['actualNativeImportCount'],len(self.r['nativeImports']));self.assertTrue(self.c['allMatchImmutableGit'])
        self.assertEqual(self.c['nativeFeature'],self.cfg['nativeFeature'])
        for n,h in self.cfg['resultHashes'].items():self.assertEqual(self.r['nativeImports'][n],h,n)
        self.assertEqual(hashlib.sha256((ROOT/'scripts/qa/c131d6_native_publication.py').read_bytes()).hexdigest(),self.r['driverSha256'])
        self.assertEqual(hashlib.sha256((ROOT/self.r['fixturePath']).read_bytes()).hexdigest(),self.r['qaSha256'])
        self.assertEqual(hashlib.sha256((E/'native-004/publication-result.json').read_bytes()).hexdigest(),self.c['currentNativeResultSha256'])
    def test_patch_reproduces_six_sources_without_activation(self):
        p=read('patch-application.json');self.assertTrue(p['freshApplyMatchesExactNativeBytes']);self.assertTrue(p['duplicateApplyRefused']);self.assertTrue(p['temporaryPatchDirectoryRemoved'])
        self.assertEqual(p['sixResultHashes'],self.cfg['resultHashes']);self.assertEqual(len(self.cfg['resultHashes']),6)
        self.assertEqual(hashlib.sha256((ROOT/self.cfg['patchPath']).read_bytes()).hexdigest(),self.cfg['patchSha256'])
        self.assertEqual(self.cfg['activation'],'STAGED_NOT_INSTALLED');self.assertFalse(self.cfg['preparedSourceEnvelopesChanged'])
    def test_actual_api_uses_existing_resolver_and_keeps_retirement_history(self):
        observations={x['case']:x for x in self.r['publicationObservations']}
        a=observations['test_actual_native_api_admission_uses_published_owner_and_same_stores'];self.assertTrue(a['nativeApiAdmissionAccepted']);self.assertTrue(a['sameAuthority']);self.assertFalse(a['queuedPayloadExecuted'])
        b=observations['test_publication_resolver_same_adapter_without_recovery_callbacks'];self.assertTrue(b['sameNativeResolverAdapter']);self.assertEqual(b['recoveryOrVoiceCalls'],[]);self.assertTrue(b['sqlDumpsUnchanged'])
        c=observations['test_api_admit_leaf_settlement_retirement_and_detach_preserve_history'];self.assertTrue(c['guardedLeafManuallySettledNotExecuted']);self.assertTrue(c['sqlDumpsUnchangedByRetireAndDetach']);self.assertTrue(c['publishedEntryWithdrawnAfterApi'])
        for x in self.r['checks']:self.assertEqual((x['newConnections'],x['rawDatabaseOpens'],x['sqlRowChanges']),(0,0,0))
    def test_before_after_failures_preserved_and_four_assertions_unchanged(self):
        old=read('regression-before/publication-result.json');self.assertEqual((old['total'],old['passed'],old['failures'],old['errors']),(4,0,4,0))
        self.assertTrue(self.c['fourFailingRegressionBodiesUnchanged'])
        text=(ROOT/'scripts/qa/c131d6_native_publication.py').read_text(encoding='utf-8')
        current={a.name:hashlib.sha256(ast.get_source_segment(text,a).encode()).hexdigest() for a in ast.walk(ast.parse(text)) if isinstance(a,ast.FunctionDef) and a.name.startswith('test_regression_')}
        self.assertEqual(current,self.c['sameFourRegressionsBodySha256'])
        oldobs=next(x for x in old['publicationObservations'] if 'statusPublishCallStacks' in x);self.assertEqual(len(oldobs['statusPublishCallStacks']),3)
        newobs=next(x for x in self.r['publicationObservations'] if 'statusPublishCallStacks' in x);self.assertEqual(newobs['statusPublishCallStacks'],[])
    def test_default_writer_control_fixture_failure_not_relabelled(self):
        r=read('native003-fixture-diagnostic.json');self.assertEqual(r['exitCode'],1);self.assertFalse(r['resultJsonWritten']);self.assertFalse(r['failedTempRootRemovedByRun']);self.assertTrue(r['nativeHashesUnchanged'])
        self.assertIn('FAILED (failures=21, errors=1)',(E/'native-003/tests.txt').read_text(encoding='utf-8'))
        self.assertEqual(hashlib.sha256((E/'native003-driver.py.txt').read_bytes()).hexdigest(),r['oldDriverSha256'])
        self.assertEqual(self.r['driverSha256'],r['newDriverSha256'])
        self.assertIn('test_ordinary_native_runner_keeps_default_status_file_writer',{x['case'] for x in self.r['caseEnd']})
    def test_partial_outcome_cases_and_cancelled_work_are_real_tests(self):
        names={x['case'] for x in self.r['caseEnd']}
        for name in ('test_trace_exception_after_real_publication_retains_unknown','test_trace_exception_after_real_withdrawal_does_not_report_success','test_cancelled_cleanup_retains_entry_and_blocks_retry','test_cancelled_native_tracked_admission_keeps_commit_owner','test_queued_api_request_blocks_finish_and_keeps_publication'):self.assertIn(name,names)
        self.assertTrue(self.r['traceFaultInjectedExplicitly']);self.assertFalse(self.r['nativeMethodsReplaced'])
    def test_programmatic_api_is_not_http_agent_or_full_harness_acceptance(self):
        self.assertTrue(self.r['actualNativeApiAdmissionTested']);self.assertFalse(self.r['httpAuthenticationOrListenerTested']);self.assertFalse(self.r['payloadOrModelExecuted'])
        for key in ('harnessOwnerIntegrationTested','linuxIsolationTested','rootWslAction'):self.assertFalse(self.r[key],key)
        self.assertEqual(self.r['providerCalls'],0)
        d=read('readonly-review-disposition.json');self.assertEqual(d['state'],'COMPLETED_AND_ARCHIVED');self.assertTrue(d['reviewNotFinalAcceptance'])
if __name__=='__main__':unittest.main()
