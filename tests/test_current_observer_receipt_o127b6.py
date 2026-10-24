"""Offline custody of source-qualified native observer runs, not runtime replay."""
import hashlib,json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
E=ROOT/'evidence/d3b-current-observers-o127b6'
class CurrentObserverReceipt(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.c=json.loads((E/'current-source-custody.json').read_text(encoding='utf-8'))
        cls.r={n:json.loads((E/n/'result.json').read_text(encoding='utf-8')) for n in cls.c['runs']}
    def test_two_generations_native_fifteen_each(self):
        for name,feature in (('current-native-002','1e97dd617b81120255304e472ce322befcdb9ccd'),('legacy-native-002','943210584828ccfcfd6adc8eb966ecaa8ca18429')):
            r=self.r[name];self.assertEqual(r['nativeFeature'],feature)
            self.assertEqual((r['result'],r['total'],r['passed'],r['errors'],r['failures'],r['skipped']),('PASS_EXPLICIT_SOURCE_NATIVE_TURN_OBSERVATION',15,15,0,0,0))
            self.assertTrue(r['originalC120TestBodiesUnchanged']);self.assertTrue(r['actualNativeTurnRunnerAdoptionAndPhysicalTracking'])
            self.assertFalse(r['nativeMethodsOrObserverMethodsReplaced']);self.assertTrue(r['runnerFacadeAndModelComputationDoubled'])
    def test_every_current_source_and_native_git_blob_bound(self):
        for label,r in self.r.items():
            c=self.c['runs'][label]
            self.assertEqual(c['resultSha256'],hashlib.sha256((E/label/'result.json').read_bytes()).hexdigest())
            self.assertEqual({n:v['sha256'] for n,v in c['nativeImports'].items()},r['nativeImports'])
            self.assertEqual(len(c['nativeImports']),c['nativeImportCount'])
            for n,h in r['sourceHashes'].items():self.assertEqual(hashlib.sha256((ROOT/n).read_bytes()).hexdigest(),h,(label,n))
        self.assertEqual([self.c['runs'][n]['nativeImportCount'] for n in ('current-native-002','legacy-native-002','prepared-003')],[541,541,501])
    def test_normal_worker_cancellation_and_cleanup_retained(self):
        for label in ('current-native-002','legacy-native-002'):
            r=self.r[label];self.assertTrue(r['ownershipReleased']);self.assertTrue(r['temporaryImportHomeRemoved'])
            self.assertEqual(r['registry'],{'live_generations':0,'retired_generations':0,'total_refcounts':0})
            self.assertEqual(len(r['caseEnd']),15)
            for end in r['caseEnd']:
                for key in ('allPhysicalWorkersDone','allExecutorTasksDone','nativePhysicalRegistryEmpty','candidateHomeRemoved'):self.assertTrue(end[key],(label,end['case'],key))
            rows=[v for v in r['observations'] if v.get('cancelledExecutorTask')];self.assertEqual(len(rows),1)
            self.assertFalse(rows[0]['workerDone']);self.assertTrue(rows[0]['nativePhysicalRegistryRetained']);self.assertFalse(rows[0]['positiveHealthClaim'])
    def test_prepared_fourteen_current_and_cleanup(self):
        r=self.r['prepared-003'];self.assertEqual((r['result'],r['total'],r['passed'],r['errors'],r['failures'],r['skipped']),('PASS_NATIVE_PREPARED_OBSERVER_ATTACHMENT_WINDOWS_BOUNDARIES',14,14,0,0,0))
        self.assertTrue(r['temporaryRootRemoved']);self.assertEqual(len(r['caseEnd']),14)
        for end in r['caseEnd']:
            self.assertTrue(end['temporaryProfileRemoved']);self.assertTrue(end['nativeOwnershipReleased']);self.assertEqual(end['registry']['total_refcounts'],0)
        for row in r['checks']:self.assertEqual((row['newConnections'],row['rawDatabaseOpens'],row['sqlRowChanges']),(0,0,0))
        names={v['case'] for v in r['caseEnd']};self.assertIn('test_source_gate_does_not_import_unqualified_worker_modules',names)
    def test_attachment_never_admits_work_and_real_boundaries_are_explicit(self):
        r=self.r['prepared-003'];self.assertTrue(r['realNativeRunnerAuthorityApiChannelStores']);self.assertTrue(r['nativeSqlChecksReal'])
        self.assertTrue(r['linuxProfileLayoutMountColdBoundariesDoubled']);self.assertTrue(r['unexpectedTaskAndEventAreExplicitFaultFixtures'])
        for k in ('nativeMethodsReplaced','activeBorrowedWorkQualified','httpListenerStarted','kernelConfinementRerun','rootOrWslAction'):self.assertFalse(r[k],k)
        self.assertEqual(r['modelOrProviderCalls'],0)
        status=next(row['status'] for row in r['checks'] if 'status' in row)
        self.assertEqual((status['attachmentMode'],status['namedRequestsObserved']),('PREPARED_ONLY',0))
        for k in ('activeBorrowedWorkQualified','allAgentWorkObserved','serviceReadinessVerified','runtimeAdmissionAuthorized','retryAuthorized','storeReleaseAuthorized'):self.assertIs(status[k],False,k)
    def test_failed_first_import_and_fixture_runs_preserved_not_pass(self):
        text=(E/'prepared-001/tests.txt').read_text(encoding='utf-8')
        self.assertIn('FAILED (errors=12)',text);self.assertIn('consumer_import_outside_manifest',text)
        self.assertFalse((E/'prepared-001/result.json').exists())
        self.assertIn('WinError 32',(E/'prepared-001-stderr.txt').read_text(encoding='utf-8'))
        old=json.loads((E/'prepared-002/result.json').read_text(encoding='utf-8'));self.assertEqual((old['total'],old['passed'],old['errors']),(14,13,1));self.assertEqual(old['result'],'FAIL')
        self.assertTrue(old['temporaryRootRemoved']);self.assertIn('socketpair',(E/'prepared-002/tests.txt').read_text(encoding='utf-8'))
        self.assertEqual(old['sourceHashes']['packages/claw-hermes/gateway_canonical_run_binding.py'],hashlib.sha256((E/'generation002-gateway_canonical_run_binding.py.txt').read_bytes()).hexdigest())
    def test_old_successes_remain_old_source_generation(self):
        for label in ('current-native-001','legacy-native-001'):
            r=json.loads((E/label/'result.json').read_text(encoding='utf-8'));self.assertEqual((r['total'],r['passed']),(15,15))
            for n in ('gateway_canonical_run_binding.py','gateway_canonical_turn_observation.py'):
                self.assertEqual(r['sourceHashes']['packages/claw-hermes/'+n],hashlib.sha256((E/('generation001-'+n+'.txt')).read_bytes()).hexdigest())
        before=json.loads((E/'baseline-current-source-refusal.json').read_text(encoding='utf-8'));self.assertEqual(before['reason'],'canonical_native_source_unqualified')
        self.assertTrue(before['temporaryHomeRemoved']);self.assertFalse(before['nativeTasksExecuted'])
    def test_historical_generations_strictly_saved_and_old_raw_results_unchanged(self):
        before=json.loads((E/'historical-before-result.json').read_text(encoding='utf-8'));after=json.loads((E/'historical-final-result.json').read_text(encoding='utf-8'))
        self.assertEqual((before['total'],before['failures']),(402,5));self.assertEqual((after['total'],after['errors'],after['failures']),(402,0,0))
        bindings=json.loads((E/'historical-bindings.json').read_text(encoding='utf-8'));baseline=json.loads((E/'baseline.json').read_text(encoding='utf-8'))
        self.assertEqual(bindings['base'],baseline['base']);self.assertEqual(len(bindings['sources']),6)
        for n,v in bindings['sources'].items():
            self.assertEqual(v['sha256'],baseline['sources'][n]);self.assertEqual(hashlib.sha256((ROOT/v['path']).read_bytes()).hexdigest(),v['sha256'])
        self.assertFalse(after['rawHistoricalOutcomeChanged']);self.assertFalse(after['oldExpectedHashesChanged'])
if __name__=='__main__':unittest.main()
