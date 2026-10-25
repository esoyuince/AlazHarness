"""Offline exec/native/source receipts, not new Linux executions."""
from pathlib import Path
import hashlib,json,unittest
ROOT=Path(__file__).resolve().parents[1];E=ROOT/'evidence/d3b-retained-exec-t143a7'
def read(name):return json.loads((E/name).read_text(encoding='utf-8'))
class ExecHandoffReceipt(unittest.TestCase):
    def scenarios(self):
        return [('exec001',False),('exec002-error',True)]
    def test_normal_and_error_native_reopen_same_stores_new_generation(self):
        for prefix,error in self.scenarios():
            r=read(prefix+'-result.json');self.assertEqual(r['result'],'PASS_REAL_LINUX_EXEC_RETAINED_NATIVE_LIFECYCLE');self.assertIsNone(r['error']);self.assertEqual(r['computeFailure'],error)
            a=r['restartReport'];self.assertEqual((a['epochBefore'],a['epochAfter'],a['beforeExecComputationCount'],a['afterExecComputationCount']),(1,2,1,1))
            self.assertEqual([v['generation'] for v in a['admissions']],[1,2]);self.assertEqual([v['owner_epoch'] for v in a['admissions']],[1,2])
            self.assertTrue(all(v['status']=='terminal' and v['outcome']==('failed' if error else 'completed') for v in a['admissions']))
            for name in ('sameDatabaseIdentities','helperFilesKeptAndUnchangedAtStartup','savedResultUnchanged','savedRequestNotRecomputed','newRequestComputedExactlyOnce','sameRequestConflictRefused','originalOwnerClosedAllThree','secondTrustedReceiptCaptured','callerReleasedLease'):self.assertTrue(a[name],name)
    def test_actual_exec_event_pid_and_fresh_interpreter_observations(self):
        for prefix,_ in self.scenarios():
            r=read(prefix+'-result.json');t=read(prefix+'-transport-result.json');pre=read(prefix+'-pre-exec.json')
            events=[json.loads(v.removeprefix('T143_EXECVE_REQUEST ')) for v in t['stdout'].splitlines() if v.startswith('T143_EXECVE_REQUEST ')]
            self.assertEqual(len(events),1);self.assertEqual(events[0]['pid'],pre['pid']);self.assertTrue(events[0]['fixedInterpreter']);self.assertTrue(events[0]['noShell'])
            self.assertEqual(pre,r['preExec']);self.assertTrue(r['freshInterpreterRole']);self.assertTrue(r['checks']['actualExecPidAndStartPreserved']);self.assertTrue(r['checks']['freshInterpreterCountersAndRegistry'])
            self.assertTrue(r['restartReport']['freshInterpreterAfterExecve']);self.assertTrue(r['restartReport']['pidPreserved']);self.assertFalse(r['restartReport']['sameInterpreterReopen'])
    def test_native_settlement_stacks_and_computation_are_not_fixture_terminalization(self):
        for prefix,_ in self.scenarios():
            r=read(prefix+'-result.json');self.assertFalse(r['manualSqlSettlement'])
            for phase in (r['preExec'],r):
                self.assertEqual(len(phase['computation']),1);self.assertTrue(phase['computation'][0]['sameCallerState']);self.assertFalse(phase['computation'][0]['onMainThread'])
                self.assertTrue(any(v['function']=='run_sync' for v in phase['nativeTrace']))
                settled=[v for v in phase['nativeTrace'] if v['function']=='settle_session_input'];self.assertTrue(settled)
                for v in settled:self.assertTrue(any(s['function']=='commit_and_publish' for s in v['stack']))
    def test_owner_release_and_real_helpers_no_additional_turn_db(self):
        for prefix,_ in self.scenarios():
            r=read(prefix+'-result.json');self.assertTrue(all(r['preExec']['checks'].values()));self.assertTrue(r['preExec']['allOwnersClosedBeforeExec'])
            self.assertEqual(r['restartReport']['registryRefsBeforeFixtureCleanup'],0);self.assertFalse(r['failureFixtureCleanupUsed']);self.assertTrue(r['temporaryProfileRemoved'])
            self.assertEqual(len(r['preExec']['coldHelperCalls']),2);self.assertEqual(len(r['coldHelperCalls']),2)
            self.assertEqual(len(r['sqliteOpens']),3);self.assertTrue(all(v['phase']=='RESTART_AFTER_NORMAL_CLOSE' for v in r['sqliteOpens']))
    def test_exact_same_bundle_driver_and_original_transport_results(self):
        a=read('exec001-intent.json');b=read('exec002-error-intent.json');self.assertEqual(a['bundleSha256'],b['bundleSha256']);self.assertEqual(a['driverSha256'],b['driverSha256']);self.assertEqual(a['codecSha256'],b['codecSha256'])
        for prefix,_ in self.scenarios():
            t=read(prefix+'-transport-result.json');self.assertEqual(t['childExitCode'],0);self.assertEqual(t['bundleSha256'],a['bundleSha256']);self.assertTrue(t['inputBytesUnchanged']);self.assertTrue(t['temporaryTransportRemoved']);self.assertEqual(json.loads(t['artifacts']['result.json']),read(prefix+'-result.json'))
    def test_all_native_and_current_code_hashes_bound(self):
        c=read('source-custody.json');self.assertTrue(c['allImportedNativeBytesMatchGit']);self.assertTrue(c['allWithinCurrent756SourceManifest']);self.assertFalse(c['nativeSourceChanged'])
        for name,h in c['currentSourceHashes'].items():self.assertEqual(hashlib.sha256((ROOT/name).read_bytes()).hexdigest(),h)
        for prefix,_ in self.scenarios():
            r=read(prefix+'-result.json')
            for m in (r['nativeImports'],r['preExec']['nativeImports']):
                for name,h in m.items():self.assertEqual(c['nativeSources'][name]['sha256'],h)
    def test_same_independent_failures_now_pass_without_test_rewrite(self):
        a=read('independent-h143c7/independent001/result.json');b=read('independent-h143c7/independent002/result.json')
        self.assertEqual((a['total'],a['passed'],a['errors'],a['failures']),(21,16,0,5));self.assertEqual((b['total'],b['passed'],b['errors'],b['failures']),(21,21,0,0));self.assertEqual(a['qaSha256'],b['qaSha256'])
        self.assertEqual(hashlib.sha256((E/'independent-h143c7/qa.py.txt').read_bytes()).hexdigest(),b['qaSha256']);self.assertEqual(hashlib.sha256((ROOT/'packages/claw-hermes/gateway_retained_handoff.py').read_bytes()).hexdigest(),b['sourceSha256'])
        for name,row in read('independent-provenance.json')['files'].items():self.assertEqual(hashlib.sha256((E/'independent-h143c7'/name).read_bytes()).hexdigest(),row['sha256'])
    def test_scope_is_orderly_exec_not_crash_or_current_kernel_acceptance(self):
        for prefix,_ in self.scenarios():
            r=read(prefix+'-result.json');self.assertEqual(r['uid'],[23001]*3);self.assertEqual(r['gid'],[23003]*3);self.assertTrue(r['actualOsBoundaries']);self.assertFalse(r['osOrProductMethodsDoubled']);self.assertTrue(r['modelFactoryComputationCloseDoubled']);self.assertEqual(r['realProviderCalls'],0);self.assertFalse(r['rootUsed']);self.assertFalse(r['confinementOrHttpTested']);self.assertFalse(r['restartReport']['processCrashOrPowerLossTested'])
        self.assertFalse(read('source-custody.json')['kernelProjectionAccepted'])
if __name__=='__main__':unittest.main()
