"""Offline receipts for real native borrowed-runner acceptance, no native rerun."""
import hashlib,json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
E=ROOT/'evidence/d3b-runner-qa-r122q6'
class NativeRunnerReceipt(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r=json.loads((E/'native-002/extended-result.json').read_text(encoding='utf-8'))
        cls.c=json.loads((E/'source-custody-current.json').read_text(encoding='utf-8'))
        cls.b=json.loads((E/'default-native-001/result.json').read_text(encoding='utf-8'))
    def test_thirty_current_real_native_methods_and_cleanup(self):
        r=self.r;self.assertEqual((r['result'],r['total'],r['passed'],r['errors'],r['failures'],r['skipped']),('PASS_REAL_BORROWED_RUNNER_INDEPENDENT',30,30,0,0,0))
        self.assertTrue(r['temporaryRootRemoved']);self.assertEqual(len(r['cleanup']),30)
        for item in r['cleanup']:
            self.assertTrue(item['temporaryProfileRemoved']);self.assertTrue(item['profileReleased'])
            self.assertEqual(item['registry'],{'live_generations':0,'retired_generations':0,'total_refcounts':0})
        log=(E/'native-002/tests.txt').read_text(encoding='utf-8');names=[s.split(' ',1)[0] for s in log.splitlines() if s.startswith('test_') and s.endswith(' ... ok')]
        self.assertEqual(len(names),30);self.assertEqual(len(set(names)),30);self.assertEqual(set(names),{item['case'] for item in r['cleanup']})
    def test_watched_boundaries_have_no_extra_connection_or_state_write(self):
        self.assertTrue(self.r['checks'])
        for row in self.r['checks']:
            self.assertEqual(row['newSQLiteConnections'],0);self.assertEqual(row['rawStateOpens'],0);self.assertEqual(row['sqlRowChanges'],0)
    def test_current_native_import_and_source_bytes(self):
        self.assertEqual(self.c['base'],'2bc50496bebe21f948dd2e86f553ef1e22904ed2')
        self.assertEqual(self.c['actualNativeImportCount'],len(self.r['nativeImports']))
        for name,h in self.r['nativeImports'].items():
            self.assertEqual(h,self.c['candidateSourceHashes'].get(name) or self.c['unalteredImportedSources'][name]['sha256'],name)
        for name,h in self.c['candidateSourceHashes'].items():
            self.assertEqual(hashlib.sha256((E/'native-source-current'/(name.replace('/','__')+'.txt')).read_bytes()).hexdigest(),h)
        self.assertEqual(self.c['currentResultSha256'],hashlib.sha256((E/'native-002/extended-result.json').read_bytes()).hexdigest())
    def test_exact_qa_unchanged_before_and_after_native_fix(self):
        files={'qaSha256':'scripts/qa/r122q6_native_runner_checks.py','driverSha256':'scripts/qa/r122q6_owner_drift_checks.py'}
        old=json.loads((E/'drift-before/extended-result.json').read_text(encoding='utf-8'))
        for key,name in files.items():
            self.assertEqual(hashlib.sha256((ROOT/name).read_bytes()).hexdigest(),self.r[key]);self.assertEqual(old[key],self.r[key])
        self.assertTrue(self.c['sameTestDriverAsBefore']);self.assertFalse(self.c['independentProductChanges'])
        self.assertEqual(self.c['changedNativeSourcesFromInitial'],['gateway/run_borrowed_state.py'])
    def test_real_default_control_is_preserved_not_called_a_bug(self):
        b=self.b;self.assertEqual(b['result'],'DEFAULT_RUNNER_BASELINE_CONFIRMED')
        self.assertTrue(b['defaultRunnerIsReal']);self.assertFalse(b['defaultBehaviorIsBug'])
        self.assertEqual((b['callerEpochBefore'],b['defaultAuthorityEpochAfter']),(1,2))
        self.assertEqual(b['constructorSQLiteOpens'],1);self.assertTrue(b['defaultRunnerUsesDifferentState'])
        self.assertTrue(b['runnerAndSessionStoreShareDefaultRegistryState']);self.assertEqual(b['registryAfter']['total_refcounts'],0)
        self.assertTrue(b['profileReleased']);self.assertTrue(b['temporaryProfileRemoved'])
        self.assertEqual(hashlib.sha256((ROOT/'scripts/qa/r122q6_default_baseline.py').read_bytes()).hexdigest(),b['qaSha256'])
    def test_failing_prepared_identity_regression_remains_failure(self):
        old=json.loads((E/'drift-before/extended-result.json').read_text(encoding='utf-8'));count=json.loads((E/'drift-before-accounting.json').read_text(encoding='utf-8'))
        self.assertEqual(old['result'],'FAIL');self.assertEqual((old['total'],old['failures']),(30,15))
        self.assertEqual((count['passedMethods'],count['failedMethods'],count['failedAssertionsIncludingSubtests']),(24,6,15));self.assertTrue(count['rawResultUnchanged'])
        self.assertEqual(len(count['failedMethodIds']),6)
        initial=json.loads((E/'source-custody-initial.json').read_text(encoding='utf-8'))
        for name,h in initial['candidateSourceHashes'].items():
            self.assertEqual(old['nativeImports'][name],h)
            self.assertEqual(hashlib.sha256((E/'native-source-initial'/(name.replace('/','__')+'.txt')).read_bytes()).hexdigest(),h)
    def test_scope_and_denied_diagnostic_probes_not_provider_acceptance(self):
        r=self.r;self.assertTrue(r['actualGatewayRunnerConstructed']);self.assertTrue(r['actualSessionAuthorityConstructed'])
        for key in ('nativeMethodsReplaced','sharedThreeStoreApiIntegrated','fullAgentExecutionTested','httpListenerStarted','fullLinuxIsolationTested','rootWslAction'):self.assertIs(r[key],False,key)
        self.assertEqual(r['providerCalls'],0);self.assertTrue(r['deniedExternalProbes'])
        for event in r['deniedExternalProbes']:
            self.assertIn(event['event'],('subprocess.Popen','socket.bind'))
            if event['event']=='socket.bind':self.assertIn('_has_ipv6',event['callers'])
            else:self.assertTrue(any(name in event['callers'] for name in ('get_version_info','_git_version_info','_run_git')))
if __name__=='__main__':unittest.main()
