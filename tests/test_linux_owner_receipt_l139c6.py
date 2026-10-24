"""L139 actual Linux lifecycle evidence. Offline receipts, not fresh native runs."""
import hashlib,json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
E=ROOT/'evidence/d3b-linux-owner-l139c6'
def read(name):return json.loads((E/name).read_text(encoding='utf-8'))
class LinuxFiniteOwnerReceipt(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runs=[read('owner-001-result.json'),read('owner-002-result.json')];cls.c=read('source-custody.json')
    def test_normal_and_error_are_two_real_linux_completed_lifecycles(self):
        for r in self.runs:
            self.assertEqual(r['result'],'PASS_REAL_LINUX_FINITE_OWNER_NOT_CONFINEMENT');self.assertEqual(r['phase'],'COMPLETE');self.assertIsNone(r['error'])
            self.assertEqual(r['uid'],[23001]*3);self.assertEqual(r['gid'],[23003]*3);self.assertEqual(len(r['checks']),15);self.assertTrue(all(r['checks'].values()))
            self.assertTrue(r['actualOsBoundaries']);self.assertFalse(r['osOrProductMethodsDoubled']);self.assertFalse(r['failureFixtureCleanupUsed'])
        normal,error=self.runs;self.assertFalse(normal['computeFailure']);self.assertTrue(error['computeFailure'])
        self.assertEqual(normal['savedResult']['result']['final_response'],'50');self.assertTrue(normal['savedResult']['result']['completed'])
        self.assertEqual(normal['admissions'][0]['outcome'],'completed');self.assertEqual(error['admissions'][0]['outcome'],'failed');self.assertFalse(error['savedResult']['result']['completed'])
    def test_exact_retry_and_native_physical_thread_settlement(self):
        for r in self.runs:
            self.assertEqual(r['exactRetry'],{'sameResult':True,'computationCount':1});self.assertEqual(r['changedPayload'],{'rejected':True,'reason':'admission_conflict'})
            self.assertEqual(len(r['admissions']),1);self.assertEqual(r['admissions'][0]['status'],'terminal');self.assertEqual(len(r['computation']),1)
            task=r['computation'][0];self.assertEqual(task['input'],[17,25,8]);self.assertTrue(task['sameCallerState']);self.assertFalse(task['onMainThread'])
            api={x['thread'] for x in r['nativeTrace'] if x['function']=='run_api_turn'};self.assertEqual(len(api),1);self.assertNotIn(task['thread'],api)
            self.assertTrue(any(x['function']=='run_sync' and x['thread']==task['thread'] for x in r['nativeTrace']))
            settlements=[x for x in r['nativeTrace'] if x['function']=='settle_session_input'];self.assertTrue(settlements)
            for x in settlements:self.assertTrue(any(f['function']=='commit_and_publish' and f['file']=='gateway/session_settlement_recovery.py' for f in x['stack']))
            self.assertFalse(r['manualSqlSettlement'])
    def test_real_cold_helpers_three_handles_and_caller_release(self):
        for r in self.runs:
            self.assertEqual([x['helper'] for x in r['coldHelperCalls']],['run_store_preopen.py','run_response_preopen.py'])
            opened=[x for x in r['sqliteOpens'] if x['phase']=='REAL_COLD_START'];self.assertEqual(len(opened),3)
            self.assertFalse(any(x['phase']=='ACTUAL_TURN' and x['path'].endswith('state.db') for x in r['sqliteOpens']))
            self.assertEqual(r['release']['ownerStage'],'CLOSED');self.assertEqual(r['release']['consumerStage'],'DETACHED')
            for k in ('realSixColdLiveChecks','sameThreeConnections','registryZeroBeforeFixtureCleanup','allThreeConnectionsPhysicallyClosed','callerLeaseRetained','callerReleasedLease','noRowsChangedByRetirement'):self.assertTrue(r['checks'][k],k)
            self.assertFalse(r['release']['runtime']['callerStoresClosed']);self.assertFalse(r['release']['sessions']['durableDataChanged'])
    def test_exact_source_custody_and_same_case_driver(self):
        self.assertEqual(self.c['nativeFeature'],'d1516731308de8e87130dc68124e69aad35d6911');self.assertEqual(self.c['nativeUnion'],721)
        self.assertEqual(self.c['nativeCounts'],{'1':721,'2':718});self.assertTrue(self.c['allActualNativeHashesMatchGitAndSelectedManifest'])
        selected=read('owner-001-transport-manifest.json')['files']
        for i,r in enumerate(self.runs,1):
            for name,h in r['nativeImports'].items():self.assertEqual(h,self.c['sourceFiles'][name]['sha256']);self.assertEqual(h,selected['native/'+name])
            self.assertEqual(hashlib.sha256((E/f'owner-00{i}-result.json').read_bytes()).hexdigest(),self.c['caseResultHashes'][str(i)])
            self.assertEqual(r['qaSha256'],self.c['driverSha256'])
        for filename,key in (('l139c6_linux_owner_finite.py','driverSha256'),('l139c6_linux_transport.py','transportSha256'),('l139c6_linux_restart_probe.py','restartDriverSha256')):
            self.assertEqual(hashlib.sha256((ROOT/'scripts/qa'/filename).read_bytes()).hexdigest(),self.c[key])
        self.assertEqual(read('owner-001-intent.json')['bundleSha256'],read('owner-002-intent.json')['bundleSha256'])
    def test_raw_transport_outcomes_and_temporary_cleanup(self):
        for i,r in enumerate(self.runs,1):
            t=read(f'owner-00{i}-transport-result.json');self.assertEqual(t['childExitCode'],0);self.assertEqual(json.loads(t['artifacts']['result.json']),r)
            self.assertTrue(t['inputBytesUnchanged']);self.assertTrue(t['temporaryTransportRemoved']);self.assertTrue(r['temporaryProfileRemoved'])
            self.assertFalse(t['rootUsed']);self.assertFalse(t['installedPackages'])
    def test_config_and_network_limits_not_kernel_confinement(self):
        for r in self.runs:
            self.assertFalse(r['configFileWritten']);self.assertTrue(r['checks']['noConfigFileBeforeOwner']);self.assertTrue(r['checks']['noConfigFileAtEnd'])
            self.assertTrue(r['modelFactoryComputationCloseDoubled']);self.assertFalse(r['confinementOrHttpTested']);self.assertEqual(r['realProviderCalls'],0)
            self.assertEqual(len(r['deniedEvents']),1);entry=r['deniedEvents'][0];self.assertEqual(entry['event'],'socket.bind');self.assertIn('_has_ipv6',entry['callers'])
            self.assertTrue(r['checks']['sameMountTable']);self.assertTrue(r['checks']['sameNamespaces'])
    def test_actual_restart_refusal_is_not_restart_success(self):
        r=read('restart-002-result.json');self.assertEqual(r['result'],'REPRODUCED_REAL_RESTART_LAYOUT_GAP');self.assertIsNone(r['error'])
        refusal=r['restartRefusal'];self.assertEqual(refusal['cause'],'native_layout_unexpected_entry');self.assertEqual(refusal['causeType'],'NativeLayoutRejected')
        for key in ('noWritableStateOpened','noEpochAttempt','allThreeDatabaseHashesUnchanged','noSqliteOpenDuringRejectedRestart'):self.assertTrue(refusal[key],key)
        self.assertEqual(r['release']['ownerStage'],'CLOSED');self.assertTrue(r['temporaryProfileRemoved']);self.assertFalse(self.c['restartAccepted'])
        self.assertEqual(hashlib.sha256((E/'restart-002-result.json').read_bytes()).hexdigest(),self.c['restartBoundaryResultSha256'])
        paths={x['path'] for x in r['profileInventory']};self.assertIn('cache/tool_discovery_cache.json',paths);self.assertIn('runtime/active_sessions.json',paths)
    def test_failed_restart_fixture_preserved_without_changing_product(self):
        old=read('restart-001-result.json');self.assertEqual(old['result'],'NOT_ACCEPTED');self.assertEqual(old['error']['reason'],'profile_lease_finished');self.assertIsNone(old['restartRefusal'])
        current=read('restart-002-intent.json');self.assertFalse(current['productOrNativeChanged']);self.assertTrue(current['assertionsUnchanged'])
        raw=(E/'restart001-driver.py.txt').read_bytes();self.assertEqual(hashlib.sha256(raw).hexdigest(),read('restart-001-intent.json')['qaSha256'])
        text=raw.decode('utf-8').replace("started=owner.start();checks['realSixColdLiveChecks']","started=owner.start();restart_expected=owner.expectation;checks['realSixColdLiveChecks']")
        text=text.replace("NativeStoreStartup(held,mount,owner.expectation,instance_id='l139c6-restart'","NativeStoreStartup(held,mount,restart_expected,instance_id='l139c6-restart'")
        self.assertEqual(text,(ROOT/'scripts/qa/l139c6_linux_restart_probe.py').read_text(encoding='utf-8'))
    def test_independent_boundary_readback_is_not_an_extra_finite_run(self):
        r=read('independent-q139r6/boundary-001-result.json');p=read('independent-q139r6/provenance.json')
        self.assertEqual(r['result'],'PASS_REAL_LINUX_OWNER_REFUSAL_BOUNDARIES');self.assertEqual(r['commandExitCode'],0);self.assertIsNone(r['error'])
        self.assertEqual(len(r['checks']),18);self.assertTrue(all(r['checks'].values()));self.assertFalse(r['finiteJobExecuted']);self.assertFalse(r['osOrProductMethodsDoubled'])
        self.assertFalse(p['newRuntimeExecutionByReadback']);self.assertFalse(p['originalFilesChanged']);self.assertFalse(p['originalHistoryMerged'])
        for name,info in p['files'].items():self.assertEqual(hashlib.sha256((E/'independent-q139r6'/name).read_bytes()).hexdigest(),info['sha256'])
        for name,h in r['nativeImports'].items():self.assertEqual(h,read('owner-001-transport-manifest.json')['files']['native/'+name])
if __name__=='__main__':unittest.main()
