"""Offline source/scope receipts, not another Linux run or dependency execution."""
import hashlib,json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
E=ROOT/'evidence/d3b-linux-consumer-qa-l125c6'
class LinuxPrerequisiteReceipt(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.comp=json.loads((E/'linux-compile-001-stdout.txt').read_bytes())
        cls.c=json.loads((E/'source-custody.json').read_text(encoding='utf-8'))
        cls.w=json.loads((E/'wheel-review-final.json').read_text(encoding='utf-8'))
        cls.a=json.loads((E/'audit-controls-003/result.json').read_text(encoding='utf-8'))
    def test_actual_linux_python_syntax_terminal_and_scope(self):
        c=self.comp;self.assertEqual(c['result'],'PASS_LINUX_SYNTAX_ONLY');self.assertEqual((c['total'],c['passed']),(562,562));self.assertEqual(c['failures'],[])
        self.assertTrue(c['python'].startswith('3.12.3 '));self.assertEqual(c['uid'],[23001]*3);self.assertEqual(c['gid'],[23003]*3)
        self.assertEqual(json.loads((E/'linux-compile-001-terminal.json').read_text()),{'exitCode':0})
        for key in ('candidateImportsExecuted','candidateCodeExecuted','candidateFilesWritten','rootUsed','coldStartupTested','mountOrIsolationTested','providerOrModelCalled','serviceActivated'):self.assertIs(c[key],False,key)
    def test_all_native_and_harness_inputs_match_saved_fixed_generation(self):
        sources=self.comp['sourceHashes'];manifest=json.loads((ROOT/'config/prepared-consumer-s124b1-sources.json').read_text(encoding='utf-8'))
        self.assertEqual(self.comp['feature'],manifest['nativeFeature']);self.assertEqual(self.c['feature'],manifest['nativeFeature'])
        self.assertEqual({n.removeprefix('native/'):h for n,h in sources.items() if n.startswith('native/')},manifest['sources'])
        self.assertEqual({n:v['sha256'] for n,v in self.c['nativeSources'].items()},manifest['sources'])
        baseline=json.loads((E/'baseline.json').read_text(encoding='utf-8'))['sources']
        harness={n.removeprefix('harness/'):h for n,h in sources.items() if n.startswith('harness/')}
        self.assertEqual(len(harness),49)
        for n,h in harness.items():self.assertEqual(baseline['packages/claw-hermes/'+n],h,n)
        self.assertEqual(self.comp['payloadSha256'],self.c['payloadSha256'])
    def test_current_qa_bytes_are_bound_to_execution(self):
        for filename,expected in (('l125c6_linux_source_compile.py',self.c['qaSha256']),('l125c6_review_wheels.py',self.w['qaSha256']),('l125c6_wheel_audit_controls.py',self.a['controlsSha256'])):
            self.assertEqual(hashlib.sha256((ROOT/'scripts/qa'/filename).read_bytes()).hexdigest(),expected,filename)
        self.assertEqual(self.a['auditSha256'],self.w['qaSha256'])
    def test_thirty_actual_wheels_and_file_records_reviewed(self):
        r=self.w;self.assertEqual(r['result'],'PASS_WHEEL_INTEGRITY_AND_DECLARED_LINUX_CLOSURE')
        self.assertEqual((r['wheelCount'],r['recordMemberCount'],r['elfFileCount']),(30,1095,13))
        self.assertEqual(sum(w['memberCount'] for w in r['wheels']),1095);self.assertEqual(sum(len(w['elfMembers']) for w in r['wheels']),13)
        names={w['name']:w for w in r['wheels']};self.assertNotIn('pywin32',names)
        for row in r['wheels']:
            self.assertTrue(row['allRecordHashesVerified']);self.assertTrue(all('win_' not in t for t in row['tags']))
        for edge in r['dependencyEdges']:self.assertEqual(names[edge['to']]['version'],edge['version'])
        self.assertEqual(r['target']['sys_platform'],'linux');self.assertEqual(r['target']['python_full_version'],'3.12.3')
    def test_download_and_review_are_exact_same_artifacts(self):
        raw=(E/'reviewed-download-record.json').read_bytes();r=json.loads(raw)
        self.assertEqual(hashlib.sha256(raw).hexdigest(),self.w['downloadManifestSha256']);self.assertEqual(r['exitCode'],0);self.assertFalse(r['installationPerformed'])
        self.assertEqual({v['name']:v['sha256'] for v in r['files']},{v['filename']:v['sha256'] for v in self.w['wheels']})
    def test_negative_controls_pass_and_initial_diagnostics_preserved(self):
        self.assertEqual((self.a['result'],self.a['total'],self.a['failures'],self.a['errors']),('PASS_SYNTHETIC_AUDITOR_CONTRACTS',12,0,0))
        log=(E/'audit-controls-003/tests.txt').read_text(encoding='utf-8');self.assertEqual(sum(l.startswith('test_') and l.endswith(' ... ok') for l in log.splitlines()),12)
        before=json.loads((E/'audit-controls-002/result.json').read_text(encoding='utf-8'));self.assertEqual(before['failures'],1)
        self.assertEqual(before['controlsSha256'],self.a['controlsSha256']);self.assertNotEqual(before['auditSha256'],self.a['auditSha256'])
        self.assertIn('record_membership_mismatch',(E/'audit-controls-002/tests.txt').read_text(encoding='utf-8'))
    def test_static_integrity_not_runtime_security_or_confinement_acceptance(self):
        for key in ('wheelCodeExecuted','wheelExtractionPerformed','installationPerformed','publisherTrustOrVulnerabilityAudited','dynamicAbiOrRuntimeImportsTested','linuxLifecycleOrConfinementAccepted'):self.assertIs(self.w[key],False,key)
        self.assertTrue(self.a['syntheticArchivesOnly']);self.assertFalse(self.a['actualDependencyWheelsExecuted']);self.assertFalse(self.a['linuxRuntimeTested'])
if __name__=='__main__':unittest.main()
