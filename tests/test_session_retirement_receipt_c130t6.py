"""Offline native-retirement evidence binding; no native or kernel replay."""
import ast,hashlib,json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
E=ROOT/'evidence/d3b-native-turn-c130a6'
def read(name):return json.loads((E/name).read_text(encoding='utf-8'))
def tests(raw):return {n.name:ast.dump(n,include_attributes=False) for n in ast.walk(ast.parse(raw)) if isinstance(n,ast.FunctionDef) and n.name.startswith('test_')}
class RetirementReceipt(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.r=read('native-003/result.json');cls.c=read('source-custody.json');cls.config=json.loads((ROOT/'config/hermes-session-retirement-c130t6.json').read_text(encoding='utf-8'))
    def test_current_twenty_eight_and_retained_failure_state(self):
        r=self.r;self.assertEqual((r['result'],r['total'],r['passed'],r['errors'],r['failures'],r['skipped']),('PASS_NATIVE_MEMORY_RETIREMENT_ONLY',28,28,0,0,0))
        names={l.split(' ',1)[0] for l in (E/'native-003/tests.txt').read_text(encoding='utf-8').splitlines() if l.startswith('test_') and l.endswith(' ... ok')}
        self.assertEqual(len(names),28);self.assertEqual(names,{v['case'] for v in r['caseEnd']})
        partial=next(v for v in r['caseEnd'] if v['case']=='test_trace_interruption_after_first_memory_effect_retains_unknown')
        self.assertEqual(partial['nativeBeforeFixtureCleanup'],'ADMISSION_UNKNOWN');self.assertEqual(partial['remainingLiveSessions'],1)
        self.assertTrue(r['explicitPartialEffectTraceFault']);self.assertFalse(r['nativeProductMethodsReplaced'])
    def test_all_three_database_digests_preserved_across_observed_operations(self):
        self.assertTrue(self.r['observations'])
        for v in self.r['observations']:
            self.assertEqual((v['newConnections'],v['rawDatabaseOpens'],v['sqlRowChanges']),(0,0,0));self.assertTrue(v['allThreeLogicalDatabaseDigestsUnchanged'])
        self.assertTrue(self.r['temporaryRootRemoved'])
        for v in self.r['caseEnd']:
            self.assertTrue(v['temporaryProfileRemoved']);self.assertTrue(v['profileReleased']);self.assertEqual(v['registry'],{'live_generations':0,'retired_generations':0,'total_refcounts':0})
    def test_unchanged_old_twenty_eight_admission_contracts(self):
        r=read('compat-001/result.json');self.assertEqual((r['total'],r['passed'],r['errors'],r['failures'],r['skipped']),(28,28,0,0,0))
        self.assertEqual(hashlib.sha256((ROOT/'scripts/qa/q128c6_native_lifecycle_checks.py').read_bytes()).hexdigest(),r['qaSha256'])
        self.assertEqual(len(r['races']),3);self.assertFalse(r['admittedAgentOrHttpExecution']);self.assertFalse(r['linuxIsolationTested'])
    def test_original_four_failures_preserved_and_same_assertions_now_pass(self):
        first=read('native-001/result.json');extra=read('review-before/result.json');fixed=read('native-002/result.json')
        self.assertEqual((first['total'],first['passed'],first['failures'],first['errors']),(24,23,1,0))
        self.assertEqual((extra['total'],extra['passed'],extra['failures'],extra['errors']),(3,0,3,0))
        self.assertEqual((fixed['total'],fixed['passed'],fixed['failures'],fixed['errors']),(27,27,0,0));self.assertEqual(extra['qaSha256'],fixed['qaSha256'])
        current=tests((ROOT/'scripts/qa/c130t6_native_session_retirement.py').read_text(encoding='utf-8'))
        for name in ('native001-qa.py.txt','native002-qa.py.txt'):
            previous=tests((E/name).read_text(encoding='utf-8'))
            for method,body in previous.items():self.assertEqual(current[method],body,method)
    def test_every_actual_native_generation_and_current_qa_bound(self):
        c=self.c
        for label,digest in c['resultHashes'].items():
            raw=(E/label/'result.json').read_bytes();self.assertEqual(hashlib.sha256(raw).hexdigest(),digest);r=json.loads(raw)
            self.assertEqual(len(r['nativeImports']),c['nativeImportCounts'][label])
            for name,h in r['nativeImports'].items():
                if label=='api-baseline-002':want=c['nativeGitBlobs'][c['nativeBase']][name]['sha256']
                elif label in ('native-001','review-before'):want=c['candidate001Hashes'].get(name) or c['nativeGitBlobs'][c['nativeBase']][name]['sha256']
                else:want=c['nativeGitBlobs'][c['nativeFeature']][name]['sha256']
                self.assertEqual(h,want,(label,name))
        self.assertEqual(hashlib.sha256((ROOT/'scripts/qa/c130t6_native_session_retirement.py').read_bytes()).hexdigest(),self.r['qaSha256'])
        self.assertTrue(c['allActualNativeImportsVerified'])
    def test_api_manifest_refusal_is_not_false_full_request_success(self):
        r=read('api-baseline-002/result.json');self.assertEqual(r['phase'],'PREPARE');self.assertEqual(r['outerRefusal']['reason'],'consumer_import_outside_manifest')
        self.assertEqual(r['retainedAfterRefusal'],{'owner':'VERIFIED','consumer':'FAILED_UNKNOWN','profileHeld':True,'allConnectionsOpen':True})
        self.assertEqual(set(r['loadedOutsideDeclaredEnvelope']),{'gateway/session_api.py','gateway/session_results.py','gateway/session_api_turn.py'})
        self.assertEqual(r['loadedHashMismatches'],{});self.assertFalse(r['observeOrScheduleTurnCalled']);self.assertEqual(r['modelOrProviderCalls'],0)
        self.assertIn('consumer_import_outside_manifest',(E/'api-baseline-001-stderr.txt').read_text(encoding='utf-8'))
        self.assertEqual(hashlib.sha256((ROOT/'scripts/qa/q130t6_native_api_baseline.py').read_bytes()).hexdigest(),r['sourceHashes']['scripts/qa/q130t6_native_api_baseline.py'])
    def test_fresh_patch_identity_and_duplicate_refusal(self):
        config=self.config;a=read('native-artifact.json');self.assertEqual(config['nativeFeature'],self.c['nativeFeature']);self.assertEqual(config['nativeBase'],self.c['nativeBase'])
        self.assertEqual(config['resultHashes'],self.c['candidate002Hashes']);self.assertEqual(hashlib.sha256((ROOT/config['patchPath']).read_bytes()).hexdigest(),config['patchSha256'])
        self.assertEqual(a['freshAppliedHashes'],config['resultHashes']);self.assertEqual(a['freshApplyExitCode'],0);self.assertTrue(a['duplicateApplyRefused'])
        for version in ('001','002'):
            for name,h in self.c['candidate'+version+'Hashes'].items():self.assertEqual(hashlib.sha256((E/('candidate'+version+'-'+name.replace('/','__')+'.txt')).read_bytes()).hexdigest(),h)
        first=read('patch-application-first-diagnostic.json');self.assertEqual(first['exitCode'],1);self.assertTrue(first['all572HarnessOriginalFilesUnchanged'])
    def test_scope_retains_default_harness_and_no_execution_authority(self):
        self.assertTrue(self.r['actualNativeApiBindingAndStores']);self.assertTrue(self.r['directNativeLeafSettlementNotAgentExecution'])
        for key in ('completeApiRequestOrWorkerExecuted','sameHarnessOwnerQualified','newLinuxIsolationAccepted','rootWslAction'):self.assertIs(self.r[key],False,key)
        self.assertEqual(self.r['providerCalls'],0);self.assertEqual(self.config['activation'],'STAGED_NOT_INSTALLED')
        for key in ('durableHistoryChanged','queuedWorkExecuted','currentHarnessSourceEnvelopePromoted','fullActiveRequestWorkerQualified','currentLinuxIsolationAccepted'):self.assertIs(self.config[key],False,key)
if __name__=='__main__':unittest.main()
