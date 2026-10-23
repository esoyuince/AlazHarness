"""Exact Linux result custody; these offline tests do not rerun Linux/native code."""
import ast,hashlib,json,unittest
from historical_layout_f126c1 import executed_source_hash as pre_f126_hash
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
E=ROOT/'evidence/d3b-linux-consumer-l125p1'
def read(n):return json.loads((E/n).read_text(encoding='utf-8'))
class ActualLinuxReceipt(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.p=read('linux-prepared-001-result.json');cls.o=read('linux-owner-001-result.json')
        cls.pc=json.loads(cls.p['artifacts']['result.json']);cls.oc=json.loads(cls.o['artifacts']['result.json'])
        cls.c=read('linux-runtime-source-custody.json')
    def test_actual_linux_identity_and_temporary_only_install(self):
        for result in (self.p,self.o):
            self.assertEqual(result['uid'],[23001]*3);self.assertEqual(result['gid'],[23003]*3)
            self.assertIn('3.12.3',result['python']);self.assertEqual(result['offlineInstall']['exitCode'],0)
            self.assertEqual(result['execution']['exitCode'],0);self.assertTrue(result['temporaryRootRemoved']);self.assertTrue(result['inputBytesUnchanged'])
            self.assertFalse(result['rootUsed']);self.assertFalse(result['globalInstallPerformed']);self.assertFalse(result['namespaceConfinementTested'])
    def test_current_native22_all_cases_and_cleanup(self):
        self.assertEqual((self.pc['total'],self.pc['passed'],self.pc['errors'],self.pc['failures'],self.pc['skipped']),(22,22,0,0,0))
        names=[line.split(' ',1)[0] for line in self.p['artifacts']['tests.txt'].splitlines() if line.startswith('test_') and line.endswith(' ... ok')]
        self.assertEqual(len(names),22);self.assertEqual(set(names),{e['case'] for e in self.pc['caseEnd']})
        for end in self.pc['caseEnd']:
            self.assertTrue(end['profileRemoved']);self.assertTrue(end['ownershipReleased']);self.assertEqual(end['pendingTasks'],0);self.assertEqual(end['registry']['total_refcounts'],0)
        self.assertEqual(hashlib.sha256((ROOT/'scripts/qa/b123a6_native_prepared_api.py').read_bytes()).hexdigest(),self.pc['qaSha256'])
    def test_real_owner_cold_helpers_and_exact_order_not_mocked(self):
        o=self.oc;self.assertEqual(o['result'],'PASS_REAL_LINUX_OWNER_LIFECYCLE_NOT_CONFINEMENT');self.assertIsNone(o['error'])
        self.assertEqual(o['phase'],'COMPLETE');self.assertEqual((o['checkCount'],len(o['checks'])),(23,23));self.assertTrue(all(v is True for v in o['checks'].values()))
        self.assertEqual([e['phase'] for e in o['events']],['owner_started','consumer_attached','consumer_detached','stores_closed'])
        self.assertEqual([e['commandName'] for e in o['coldHelpers']],['run_store_preopen.py','run_store_preopen.py','run_response_preopen.py'])
        self.assertFalse(o['productOrNativeMethodsDoubled']);self.assertTrue(o['actualLinuxActorLeaseMountLayoutColdHelpersAndLiveSql'])
        self.assertFalse(o['fixtureCleanupAfterFailure']);self.assertTrue(o['temporaryProfileRemoved'])
        tree=ast.parse((ROOT/'scripts/qa/l125p1_linux_owner_lifecycle.py').read_text(encoding='utf-8'))
        self.assertFalse(any(isinstance(n,ast.ImportFrom) and n.module=='unittest.mock' for n in ast.walk(tree)))
    def test_source_bytes_native_imports_and_prior_harness_preserved(self):
        self.assertEqual(self.c['nativeFeature'],'1e97dd617b81120255304e472ce322befcdb9ccd')
        self.assertEqual((self.c['preparedImportCount'],self.c['ownerImportCount'],self.c['unionImportCount']),(499,498,499))
        for report in (self.pc,self.oc):
            for name,h in report['nativeImports'].items():self.assertEqual(self.c['actualImportedSources'][name]['sha256'],h)
        for name,h in self.c['qaHashes'].items():self.assertEqual(pre_f126_hash(ROOT,name,h),h,name)
        for name,h in self.c['resultHashes'].items():self.assertEqual(hashlib.sha256((E/name).read_bytes()).hexdigest(),h,name)
        baseline=read('baseline.json');self.assertEqual(len(baseline['sources']),522)
        for name,h in baseline['sources'].items():self.assertEqual(pre_f126_hash(ROOT,name,h),h,name)
    def test_corrected_exact_linux_wheel_lock(self):
        p=ROOT/'config/linux-prepared-dependencies-l125p1.json';lock=json.loads(p.read_text(encoding='utf-8'))
        self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(),self.c['dependencyLockSha256'])
        expected={x['name']:x['version'] for x in lock['wheels'] if x['purpose']!='installer-tool'}
        self.assertEqual(len(expected),30);self.assertEqual(self.p['installedDistributions'],expected);self.assertEqual(self.o['installedDistributions'],expected)
        for name,version in {'aiohttp':'3.14.5','certifi':'2026.10.23','multidict':'6.9.1','urllib3':'2.8.0','yarl':'1.25.1'}.items():self.assertEqual(expected[name],version)
        self.assertNotIn('pywin32',expected);self.assertFalse(lock['globalInstallAllowed']);self.assertFalse(lock['sourceBuildsAllowed'])
        self.assertEqual(len(lock['securityUpdates']),5)
        for row in read('fixed-wheel-provenance.json')['changedReleaseProofs']:self.assertEqual(row['nonWithdrawnAdvisoryCount'],0)
    def test_transport_source_and_package_integrity_binds_both_runs(self):
        for suffix,result in (('001',self.p),('002',self.o)):
            manifest=read('transport-manifest-'+suffix+'.json')
            self.assertEqual(manifest['nativeCount'],513);self.assertEqual(manifest['dependencyLockSha256'],self.c['dependencyLockSha256'])
            for name,h in manifest['files'].items():
                if name.startswith('harness/'):self.assertEqual(pre_f126_hash(ROOT,name.removeprefix('harness/'),h),h,name)
            self.assertEqual(result['installedFileCount'],len(result['installedFileHashes']))
            self.assertEqual(result['installedFileManifestSha256'],hashlib.sha256(json.dumps(result['installedFileHashes'],sort_keys=True,separators=(',',':')).encode()).hexdigest())
        for name,h in read('transport-manifest-001.json')['files'].items():self.assertEqual(read('transport-manifest-002.json')['files'][name],h)
    def test_first_missing_dependency_and_superseded_candidate_remain_historical(self):
        baseline=read('linux-import-baseline-result.json');self.assertEqual(baseline['result'],'DEPENDENCY_OR_COMPATIBILITY_BLOCKER_CONFIRMED')
        self.assertEqual(baseline['imports'][-1]['missingName'],'dotenv');self.assertEqual(baseline['sourceCompileFailures'],[])
        self.assertTrue(baseline['allCopiedNativeSourcesUnchanged']);self.assertTrue(baseline['temporaryRootRemoved'])
        first=read('dependency-lock-before-security-review.json');old={x['name']:x['version'] for x in first['wheels']}
        self.assertEqual(old['aiohttp'],'3.14.3');self.assertEqual(old['urllib3'],'2.7.0')
        plan=read('security-remediation-plan.json');self.assertEqual(len(plan['constraintConflicts']),1)
        self.assertTrue(read('security-remediation-plan-002.json')['oldCandidateNotInstalled'])
    def test_scope_no_admission_model_or_full_isolation(self):
        for k in ('namespaceConfinementTested','physicalDurabilityTested','serviceOrAdmissionActivated','rootUsed'):self.assertIs(self.oc[k],False,k)
        self.assertEqual(self.oc['providerCalls'],0)
        self.assertFalse(self.pc['nativeMethodsReplaced']);self.assertFalse(self.pc['serviceAdmissionOrListenerActivated']);self.assertEqual(self.pc['providerCalls'],0)
        for event in self.oc['events']:self.assertFalse(event['receipt']['runtimeAdmissionAuthorized'])
        self.assertTrue(self.oc['checks']['same_mount_table']);self.assertTrue(self.oc['checks']['no_namespace_reconfiguration'])
if __name__=='__main__':unittest.main()
