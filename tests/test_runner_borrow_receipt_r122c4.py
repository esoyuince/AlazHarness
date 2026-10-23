"""Offline source/receipt checks; actual native constructor was run separately."""
import hashlib,json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
E=ROOT/'evidence/d3b-runner-borrow-r122c4'
class RunnerBorrowReceipt(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r=json.loads((E/'native-002/result.json').read_text(encoding='utf-8'))
        cls.c=json.loads((E/'source-custody.json').read_text(encoding='utf-8'))
        cls.cfg=json.loads((ROOT/'config/hermes-runner-borrow-r122c4.json').read_text(encoding='utf-8'))
    def test_current_native_28_and_complete_cleanup(self):
        self.assertEqual((self.r['result'],self.r['total'],self.r['passed'],self.r['errors'],self.r['failures'],self.r['skipped']),('PASS_NATIVE_CALLER_RUNNER_CONSTRUCTION',28,28,0,0,0))
        self.assertTrue(self.r['temporaryRootRemoved']);self.assertEqual(len(self.r['caseEnd']),28)
        for end in self.r['caseEnd']:
            self.assertTrue(end['profileRemoved']);self.assertTrue(end['profileReleased']);self.assertEqual(end['pendingTasks'],0)
            self.assertEqual(end['registry'],{'live_generations':0,'retired_generations':0,'total_refcounts':0})
    def test_existing_epoch_and_no_new_sqlite_in_watched_native_paths(self):
        self.assertTrue(self.r['checks'])
        for row in self.r['checks']:
            self.assertEqual(row['sqliteOpens'],0);self.assertEqual(row['sqlWrites'],0);self.assertIs(row['epochChanged'],False)
        log=(E/'native-002/tests.txt').read_text(encoding='utf-8');names=[line.split(' ',1)[0] for line in log.splitlines() if line.startswith('test_') and line.endswith(' ... ok')]
        self.assertEqual(len(names),28);self.assertEqual(set(names),{e['case'] for e in self.r['caseEnd']})
        self.assertIn('test_native_admission_gate_is_closed',names)
        self.assertIn('test_detach_keeps_caller_state_and_profile_open',names)
    def test_native_imports_and_exact_current_qa(self):
        self.assertTrue(self.c['allActualImportsVerified']);self.assertEqual(self.c['actualNativeImportCount'],len(self.r['nativeImports']))
        self.assertEqual(hashlib.sha256((ROOT/'scripts/qa/r122c4_native_runner.py').read_bytes()).hexdigest(),self.r['qaSha256'])
        for name,h in self.r['nativeImports'].items():
            expected=self.c['sourceHashes'].get(name) or self.c['unmodifiedImports'][name]['sha256']
            self.assertEqual(h,expected,name)
        self.assertEqual(self.c['sourceHashes'],self.cfg['resultHashes'])
        self.assertEqual(hashlib.sha256((E/'native-002/result.json').read_bytes()).hexdigest(),self.c['resultSha256'])
    def test_staged_patch_application_and_api_boundary_unchanged(self):
        cfg=self.cfg;self.assertEqual(cfg['activation'],'STAGED_NOT_INSTALLED')
        self.assertEqual(hashlib.sha256((ROOT/cfg['patchPath']).read_bytes()).hexdigest(),cfg['patchSha256'])
        app=json.loads((E/'patch-application.json').read_text(encoding='utf-8'))
        self.assertTrue(app['exactFreshApply']);self.assertTrue(app['duplicateApplyRefused']);self.assertTrue(app['temporaryExportRemoved'])
        self.assertEqual(app['resultHashes'],cfg['resultHashes']);self.assertEqual(app['nativeFeature'],self.c['nativeFeature'])
        self.assertTrue(cfg['borrowedApiGuardUnchanged']);self.assertFalse(cfg['threeStoreApiIntegrated']);self.assertFalse(cfg['admissionOrServiceQualified'])
        self.assertIn('gateway/platforms/api_server_borrowed.py',self.c['unchangedBoundaries'])
    def test_initial_prepared_drift_regression_retained(self):
        before=json.loads((E/'owner-drift-before/result.json').read_text(encoding='utf-8'))
        self.assertEqual((before['total'],before['passed'],before['failures'],before['errors']),(4,1,3,0))
        old=json.loads((E/'native-001/result.json').read_text(encoding='utf-8'));self.assertEqual((old['total'],old['passed']),(24,24))
        self.assertEqual(hashlib.sha256((E/'initial-native-runner-qa.py.txt').read_bytes()).hexdigest(),old['qaSha256'])
        for name,h in json.loads((E/'candidate-sources.json').read_text(encoding='utf-8')).items():
            self.assertEqual(hashlib.sha256((E/('initial-'+name.replace('/','__')+'.txt')).read_bytes()).hexdigest(),h)
            self.assertEqual(old['nativeImports'][name],h)
        self.assertNotEqual(old['nativeImports']['gateway/run_borrowed_state.py'],self.r['nativeImports']['gateway/run_borrowed_state.py'])
    def test_framework_failure_and_import_probe_denials_not_hidden(self):
        first=json.loads((E/'smoke-001/result.json').read_text(encoding='utf-8'));self.assertEqual(first['result'],'FAIL')
        diagnosis=json.loads((E/'smoke-fixture-diagnosis.json').read_text(encoding='utf-8'));self.assertFalse(diagnosis['nativeProductChanged']);self.assertFalse(diagnosis['toolSafetyDenied'])
        self.assertTrue(self.r['frameworkLoopInitializedBeforeAudit'])
        events=self.r['deniedEventDetails'];self.assertTrue(events)
        self.assertEqual([e['event'] for e in events],self.r['blockedImportOrNativeEvents'])
        for event in events:
            self.assertEqual(event['phase'],'imports')
            self.assertIn(event['event'],('subprocess.Popen','socket.bind'))
        self.assertTrue(any(e['event']=='socket.bind' for e in events))
    def test_real_constructor_not_a_running_shared_service(self):
        self.assertTrue(self.r['fullNativeConstructorCalled']);self.assertTrue(self.r['realAuthorityClassUsed'])
        for name in ('nativeMethodsReplaced','threeStoreApiIntegrated','authorityAdmissionEnabled','serviceStarted','httpListenerStarted','rootWslAction'):
            self.assertIs(self.r[name],False,name)
        self.assertEqual(self.r['providerCalls'],0);self.assertFalse(self.c['serviceOrRuntimeActivated'])
if __name__=='__main__':unittest.main()
