"""Offline source/results receipts; not new Linux executions."""
from pathlib import Path
import hashlib,json,unittest
from historical_borrowed_service_r159a1 import archived_source
ROOT=Path(__file__).resolve().parents[1]
E=ROOT/'evidence/d3b-retained-profile-r140c6'
def read(name):return json.loads((E/name).read_text(encoding='utf-8'))
class RetainedRestartReceipts(unittest.TestCase):
    def test_normal_and_error_real_linux_restarts_keep_old_result(self):
        for name,error in (('restart003-result.json',False),('restart004-error-result.json',True)):
            r=read(name);self.assertEqual(r['result'],'PASS_RETAINED_REAL_LINUX_RESTART');self.assertIsNone(r['error']);self.assertEqual(r['computeFailure'],error)
            a=r['restartReport'];self.assertEqual((a['epochBefore'],a['epochAfter'],a['computationCount']),(1,2,2))
            for key in ('sameDatabaseIdentities','helperFilesKeptAndUnchangedAtStartup','savedResultUnchanged','savedRequestNotRecomputed','newRequestComputedExactlyOnce','sameRequestConflictRefused','originalOwnerClosedAllThree','secondTrustedReceiptCaptured','callerReleasedLease'):self.assertTrue(a[key],key)
            self.assertEqual(a['registryRefsBeforeFixtureCleanup'],0);self.assertEqual(len(a['admissions']),2)
            self.assertEqual([v['owner_epoch'] for v in a['admissions']],[1,2]);self.assertEqual([v['generation'] for v in a['admissions']],[1,2])
            self.assertTrue(all(v['status']=='terminal' and v['outcome']==('failed' if error else 'completed') for v in a['admissions']))
            self.assertTrue(r['temporaryProfileRemoved']);self.assertFalse(r['failureFixtureCleanupUsed'])
    def test_both_cases_same_driver_bundle_and_live_boundaries(self):
        normal=read('restart003-intent.json');failed=read('restart004-error-intent.json')
        self.assertEqual(normal['bundleSha256'],failed['bundleSha256']);self.assertEqual(normal['driverSha256'],failed['driverSha256'])
        self.assertEqual(normal['driverSha256'],hashlib.sha256((ROOT/'scripts/qa/r140c6_linux_restart.py').read_bytes()).hexdigest())
        for prefix in ('restart003','restart004-error'):
            tr=read(prefix+'-transport-result.json');r=read(prefix+'-result.json')
            self.assertEqual(tr['childExitCode'],0);self.assertTrue(tr['inputBytesUnchanged']);self.assertTrue(tr['temporaryTransportRemoved'])
            self.assertEqual(json.loads(tr['artifacts']['result.json']),r);self.assertEqual(r['uid'],[23001]*3);self.assertEqual(r['gid'],[23003]*3)
            self.assertTrue(r['actualOsBoundaries']);self.assertFalse(r['osOrProductMethodsDoubled']);self.assertEqual(len(r['coldHelperCalls']),4)
            self.assertFalse(any(v['phase'] in ('ACTUAL_TURN','RESTART_NEW_WORK') and v['path'].endswith('state.db') for v in r['sqliteOpens']))
    def test_native_settlement_is_not_driver_written_rows(self):
        r=read('restart003-result.json');self.assertFalse(r['manualSqlSettlement'])
        events=r['nativeTrace'];self.assertTrue(any(v['function']=='run_sync' for v in events))
        settle=[v for v in events if v['function']=='settle_session_input'];self.assertTrue(settle)
        for row in settle:self.assertTrue(any(v['function']=='commit_and_publish' for v in row['stack']))
        self.assertTrue(all(not v['onMainThread'] and v['sameCallerState'] for v in r['computation']))
    def test_initial_failures_not_relabelled_pass(self):
        first=read('restart001-result.json');second=read('restart002-result.json')
        self.assertEqual(first['result'],'NOT_ACCEPTED');self.assertEqual(first['error']['phase'],'RESTART_EXACT_REPLAY')
        self.assertEqual(second['result'],'NOT_ACCEPTED');self.assertEqual(second['error']['phase'],'RESTART_NEW_WORK')
        self.assertIn('agent.agent_runtime_helpers',read('restart002-transport-result.json')['stderr'])
        self.assertTrue(read('restart001-qa-diagnosis.json')['firstFailurePreserved'])
    def test_manifest_extension_is_exact_one_immutable_module(self):
        original=json.loads((ROOT/'config/finite-close-f135c6-sources.json').read_text())
        new=json.loads((ROOT/'config/retained-profile-r140c6-sources.json').read_text())
        extra=set(new['sources'])-set(original['sources']);self.assertEqual(extra,{'agent/agent_runtime_helpers.py'})
        self.assertEqual((len(original['sources']),len(new['sources'])),(755,756));self.assertEqual(original['nativeFeature'],new['nativeFeature'])
        for name,h in original['sources'].items():self.assertEqual(new['sources'][name],h)
        review=read('retained-transcript-source-review.json');self.assertEqual(new['sources'][next(iter(extra))],review['addedSha256']);self.assertFalse(review['newRuntimePermissions'])
    def test_independent_sixteen_negatives_refuse_before_write(self):
        r=read('independent-l140a6/restart-001-result.json');n=r['independentRetainedControls'];self.assertEqual(n['nestedCases'],16);self.assertEqual(len(n['cases']),16)
        for row in n['cases']:
            self.assertEqual(row['parentSqliteOpens'],0);self.assertTrue(row['databaseHashesUnchanged']);self.assertFalse(row['writableStoreConstructed']);self.assertFalse(row['epochAttempted'])
        a=r['restartAcceptance'];self.assertEqual((a['epoch'],a['computationCount'],a['agentInstances']),(2,1,1));self.assertTrue(a['sameAdmissionIdAndGeneration']);self.assertTrue(a['allThreeConnectionsClosed'])
        proof=read('independent-l140a6-provenance.json')
        for name,v in proof['files'].items():self.assertEqual(hashlib.sha256((E/'independent-l140a6'/name).read_bytes()).hexdigest(),v['sha256'])
        self.assertFalse(proof['nativeReexecutionByCopy'])
    def test_native_sources_and_current_selected_code_bound(self):
        c=read('source-custody.json');self.assertTrue(c['allNativeImportsMatchImmutableGit']);self.assertFalse(c['nativeSourceModified'])
        # "currentHarnessHashes" records the source generation at receipt time.
        for name,h in c['currentHarnessHashes'].items():
            selected=archived_source(ROOT,name,h)
            path=ROOT/name if selected is None else selected
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),h,name)
        for scenario in ('restart003-result.json','restart004-error-result.json'):
            for name,h in read(scenario)['nativeImports'].items():self.assertEqual(c['nativeSources'][name]['sha256'],h,name)
    def test_historical_generation_redirect_is_exact_and_named(self):
        import historical_retained_r140c6 as history
        baseline=read('baseline.json')
        for name in history.NAMES:
            expected=baseline['sources'][name]
            self.assertEqual(history.saved_generation_hash(ROOT,name,expected),expected)
            self.assertIsNone(history.saved_generation_hash(ROOT,name,'0'*64))
        self.assertIsNone(history.saved_generation_hash(ROOT,'unlisted.py','0'*64))
    def test_current_changed_sources_do_not_inherit_old_runtime_proof(self):
        import historical_retained_r140c6 as history
        baseline=read('baseline.json');recorded=read('source-custody.json')['currentHarnessHashes']
        for name in history.NAMES:
            self.assertNotEqual(baseline['sources'][name],recorded[name])
            selected=archived_source(ROOT,name,recorded[name])
            path=ROOT/name if selected is None else selected
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),recorded[name],name)
            live=hashlib.sha256((ROOT/name).read_bytes()).hexdigest()
            self.assertNotEqual(live,baseline['sources'][name],name)
            if selected is not None:
                self.assertNotEqual(live,recorded[name],name)
                self.assertIsNone(archived_source(ROOT,name,live))
        first=read('full001/result.json');self.assertEqual(first['failures'],2);self.assertEqual(first['errors'],0)
    def test_restart_scope_not_crash_confinement_or_real_model(self):
        for name in ('restart003-result.json','restart004-error-result.json'):
            r=read(name);self.assertTrue(r['restartReport']['sameProcessColdOwnerRestart']);self.assertFalse(r['restartReport']['processCrashOrPowerLossTested'])
            self.assertTrue(r['modelFactoryComputationCloseDoubled']);self.assertFalse(r['rootUsed']);self.assertEqual(r['realProviderCalls'],0);self.assertFalse(r['confinementOrHttpTested']);self.assertFalse(r['configFileWritten'])
if __name__=='__main__':unittest.main()
