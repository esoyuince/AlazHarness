"""Offline source/result custody of actual R113Q8 execution, no native rerun."""
import hashlib,json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
E=ROOT/'evidence/d3b-response-preflight-r113q8'
class NativeResponsePreflightReceipt(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.outer=json.loads((E/'linux-001-stdout.txt').read_bytes())
        cls.proof=json.loads(cls.outer['nativeStdout'])
        cls.intent=json.loads((E/'linux-001-intent.json').read_text(encoding='utf-8'))
    def test_actual_native_focused_success_with_explicit_scope(self):
        self.assertEqual((self.outer['unitExitCode'],self.outer['nativeExitCode']),(0,0))
        self.assertIn('Ran 44 tests',self.outer['unitLog'])
        self.assertEqual(self.proof['result'],'PASS_SCOPED_NATIVE_RESPONSE_PREFLIGHT')
        self.assertEqual(len(self.proof['checks']),47);self.assertEqual(self.proof['checkCount'],47)
        self.assertTrue(all(v is True for v in self.proof['checks'].values()))
        for key in ('fullIsolationTested','A109ThreeStoreStartupTested','httpListenerStarted','nativeMethodsMocked'):self.assertIs(self.proof[key],False)
        self.assertEqual(self.proof['providerCalls'],0)
    def test_current_product_probe_and_pinned_native_sources_match(self):
        self.assertEqual(self.outer['sources'],self.intent['sources']);self.assertEqual(self.proof['sourceSha256'],self.intent['sources'])
        for name,digest in self.proof['importedSourceSha256'].items():self.assertEqual(digest,self.intent['sources'][name])
        for name in ('packages/claw-hermes/gateway_response_preopen.py','scripts/run_response_preopen.py','scripts/qa/r113q8_response_preflight_probe.py','tests/test_gateway_response_preopen.py'):
            self.assertEqual(hashlib.sha256((ROOT/name).read_bytes()).hexdigest(),self.intent['sources'][name])
        for name,info in self.intent['nativeGitSources'].items():
            self.assertEqual(self.intent['sources']['vendor-native/'+name],info['sha256']);self.assertEqual(len(info['blob']),40)
        self.assertEqual(self.intent['nativeFeature'],'cc16c10b16a0ca8d80b23fd9be3f0e59ee605075')
    def test_actual_separate_worker_returns_no_write_no_authority(self):
        for receipt in (self.proof['emptyReceipt'],self.proof['populatedReceipt']):
            self.assertEqual(receipt['state'],'COLD_RESPONSE_PREFLIGHT_VERIFIED')
            self.assertEqual(receipt['parentPid'],self.proof['parentPid']);self.assertNotEqual(receipt['workerPid'],self.proof['parentPid'])
            self.assertEqual(receipt['schemaSha256'],'c4b66ce0c9b2571b17eae2080834e365b3aa526d40157c8c3cf4f353541ae1b4')
            self.assertIs(receipt['contentAndMetadataUnchanged'],True);self.assertIs(receipt['normalSqliteLocks'],True)
            for k in ('nativeConstructorsInvoked','sqlWritesPerformed','sidecarRecoveryPerformed','knownConstructorMutationNeeded','canonicalOutcomeEquivalenceVerified','runtimeAdmissionAuthorized','fullD3BAccepted'):self.assertIs(receipt[k],False)
        self.assertEqual(self.proof['emptyReceipt']['rowsObserved']['responses'],0)
        self.assertEqual(self.proof['populatedReceipt']['rowsObserved']['responses'],2)
        self.assertEqual(self.proof['populatedReceipt']['rowsObserved']['response_keys'],1)
    def test_real_lock_competitor_and_parent_no_raw_database_opens(self):
        self.assertEqual(self.proof['lockSequence'],[{'state':'BUSY','code':5},{'state':'BUSY','code':5},{'state':'ACQUIRED'}])
        self.assertEqual(self.proof['audit'],{'watch':False,'parentSqliteOpens':0,'parentDataOpens':0})
        self.assertIs(self.proof['checks']['qualified_constructor_no_response_row_writes'],True)
        self.assertIs(self.proof['checks']['qualified_constructor_response_bytes_stable'],True)
    def test_thirteen_actual_refusal_cases_no_silent_fix(self):
        cases=self.proof['cases'];self.assertEqual(len(cases),13)
        names={r['case'] for r in cases};self.assertEqual(len(names),13)
        self.assertTrue({'unsettled','retention','old_schema','wrong_inode','mode','missing','symlink','locked'}<=names)
        for case in cases:
            self.assertTrue(case['reason'].startswith('response_preopen_'))
            if case['case'] not in ('missing','symlink','locked'):self.assertIs(case['contentsUnchanged'],True)
    def test_temporary_fixture_removed_and_earlier_setup_failures_retained(self):
        self.assertIs(self.outer['temporaryRootRemoved'],True);self.assertIs(self.outer['sourcesUnchanged'],True)
        self.assertEqual(self.outer['uid'],23001);self.assertIs(self.outer['rootUsed'],False);self.assertIs(self.outer['packageInstalled'],False)
        self.assertIn('FAIL: test_sql_budget_failure',(E/'focused-windows-001.txt').read_text(encoding='utf-8'))
        self.assertIn('OK',(E/'focused-windows-002.txt').read_text(encoding='utf-8'))
        self.assertIn('Path.home()',(E/'native-schema-stderr.txt').read_text(encoding='utf-8'))

if __name__=='__main__':unittest.main()
