"""Offline exact-source evidence of30 real prepared join tests; not native replay."""
import hashlib,json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
E=ROOT/'evidence/d3b-three-runner-a123c6'
class ThreePreparedReceipt(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r=json.loads((E/'native-002/extended-result.json').read_text(encoding='utf-8'))
        cls.c=json.loads((E/'source-custody-current.json').read_text(encoding='utf-8'))
        cls.b=json.loads((E/'baseline-native-001/result.json').read_text(encoding='utf-8'))
    def test_thirty_current_methods_and_cleanup_not_service_acceptance(self):
        r=self.r;self.assertEqual((r['result'],r['total'],r['passed'],r['failures'],r['errors'],r['skipped']),('PASS_NATIVE_PREPARED_THREE_STORE_JOIN',30,30,0,0,0))
        self.assertTrue(r['temporaryRootRemoved']);self.assertEqual(len(r['cleanup']),30)
        for c in r['cleanup']:
            self.assertTrue(c['temporaryProfileRemoved']);self.assertTrue(c['profileReleased']);self.assertEqual(c['pendingTasks'],0)
            self.assertEqual(c['registry'],{'live_generations':0,'retired_generations':0,'total_refcounts':0})
    def test_actual_imports_and_four_source_snapshots_exact(self):
        for name,h in self.r['nativeImports'].items():
            want=self.c['candidateHashes'].get(name) or self.c['unalteredImports'][name]['sha256'];self.assertEqual(h,want,name)
        for name,h in self.c['candidateHashes'].items():
            self.assertEqual(hashlib.sha256((E/'native-source-current'/(name.replace('/','__')+'.txt')).read_bytes()).hexdigest(),h)
        self.assertEqual(self.c['actualNativeImportCount'],len(self.r['nativeImports']));self.assertTrue(self.c['allUnchangedImportsMatchImmutableGit'])
        self.assertEqual(hashlib.sha256((E/'native-002/extended-result.json').read_bytes()).hexdigest(),self.c['currentNativeResultSha256'])
    def test_current_qa_identical_to_before_fix(self):
        old=json.loads((E/'service-drift-before/extended-result.json').read_text(encoding='utf-8'))
        for field,name in (('baseQaSha256','a123c6_native_shared_checks.py'),('extendedQaSha256','a123c6_service_drift.py')):
            h=hashlib.sha256((ROOT/'scripts/qa'/name).read_bytes()).hexdigest();self.assertEqual(h,self.r[field]);self.assertEqual(h,old[field])
        self.assertEqual(self.r['qaSha256'],self.r['baseQaSha256'])
    def test_initial_native_success_and_extra_failed_assertions_retained(self):
        initial=json.loads((E/'native-001/result.json').read_text(encoding='utf-8'));self.assertEqual((initial['total'],initial['passed']),(27,27))
        before=json.loads((E/'service-drift-before/extended-result.json').read_text(encoding='utf-8'))
        self.assertEqual((before['total'],before['passed'],before['failedMethods'],before['failures'],before['errors']),(30,27,3,11,0))
        parents={n.split(' (',1)[0] for n in before['failureIds']};self.assertEqual(len(parents),3)
        for name,h in json.loads((E/'candidate-snapshot-001.json').read_text(encoding='utf-8'))['candidateHashes'].items():
            self.assertEqual(before['nativeImports'][name],h)
            self.assertEqual(hashlib.sha256((E/'native-source-before'/(name.replace('/','__')+'.txt')).read_bytes()).hexdigest(),h)
        changed=[n for n in self.c['candidateHashes'] if self.c['candidateHashes'][n]!=before['nativeImports'][n]]
        self.assertEqual(changed,['gateway/platforms/api_server_prepared.py'])
    def test_default_conflict_baseline_is_preserved_and_not_called_bug(self):
        b=self.b;self.assertEqual(b['result'],'PREPARED_RUNNER_CONFLICT_BASELINE_CONFIRMED')
        self.assertEqual(b['refusalReason'],'borrowed_runner_conflict');self.assertFalse(b['defaultConflictIsBug'])
        for key in ('sameCallerStateOnBothSides','authorityStillRetiring','allCallerStoresOpenAfterFacadeDetach','epochAndRowsUnchanged','temporaryProfileRemoved','profileReleased'):self.assertTrue(b[key])
        self.assertFalse(b['localEpochMapPresent']);self.assertEqual(b['sqliteOpensInConstructionAndSelection'],0)
        self.assertEqual(hashlib.sha256((ROOT/'scripts/qa/a123c6_original_guard.py').read_bytes()).hexdigest(),b['qaSha256'])
    def test_watched_readonly_boundaries_and_raw_case_coverage(self):
        self.assertTrue(self.r['observations'])
        for o in self.r['observations']:
            self.assertEqual((o['newConnections'],o['rawDatabaseOpens'],o['sqlRowChanges']),(0,0,0))
        text=(E/'native-002/tests.txt').read_text(encoding='utf-8');names=[line.split(' ',1)[0] for line in text.splitlines() if line.startswith('test_') and line.endswith(' ... ok')]
        self.assertEqual(len(names),30);self.assertEqual(len(set(names)),30);self.assertEqual(set(names),{x['case'] for x in self.r['cleanup']})
        self.assertIn('test_prepared_selection_refuses_real_new_task_without_cancelling_it',names)
        self.assertIn('test_cleanup_fault_retains_unknown_ownership_no_retry',names)
    def test_scope_and_import_diagnostic_denials_not_hidden(self):
        self.assertTrue(self.r['actualNativeRunnerAndAdapterAndThreeStores']);self.assertTrue(self.r['oneCleanupObjectReplacedForExplicitFault'])
        for key in ('nativeProductMethodsReplaced','profileMountOrLinuxIsolationTested','activeWorkOrModelTested','httpListenerStarted','rootWslAction'):self.assertIs(self.r[key],False)
        self.assertEqual(self.r['providerCalls'],0)
        denied=self.r['deniedImportProbes'];self.assertTrue(denied)
        self.assertTrue(any(e['event']=='socket.bind' and '_has_ipv6' in e['callers'] for e in denied))
        stop=json.loads((E/'qa-compile-stop.json').read_text(encoding='utf-8'));self.assertFalse(stop['nativeTestExecuted']);self.assertFalse(stop['productChanged'])
if __name__=='__main__':unittest.main()
