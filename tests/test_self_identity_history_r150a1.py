"""New-source custody and exact historic code resolution. No kernel acceptance."""
from pathlib import Path
import hashlib,json,tempfile,unittest
import historical_self_identity_r150a1 as h
import historical_service_profile_r161a1 as service_history
ROOT=Path(__file__).resolve().parents[1]
E=ROOT/'evidence/d3b-self-identity-r150a1'
INTEGRATION='evidence/d3b-self-identity-r150a1/integration.json'
INTEGRATION_SHA='36043f10b69134707367a97a3c02bfe97375abc586f523e7adca16d464e03aba'
PREPUBLICATION='evidence/m1-finite-product-r156a1/pre-publication-checks.json'
PREPUBLICATION_SHA='8fc6fe74c974ac8736f8293a12ef93f44514c499da7f41379fe3d8b0b43fcae0'
CURRENT_SOURCE='e641a5000810efb2a453ae847f689b422f7d41a7'
LAUNCHER='packages/claw-hermes/gateway_retained_launch.py'
PROJECTION='packages/claw-hermes/gateway_state_projection.py'
CURRENT_LAUNCHER_SHA='4140c06d74e9603664ababb97955cd04779bf9a0494fb1361ae8a426d23a90e2'
APPLIED_LAUNCHER='evidence/m1-finite-product-r156a1/r150-integrated-gateway_retained_launch.py.txt'
APPLIED_NAMES=frozenset(('packages/claw-hermes/credential_guard.py',LAUNCHER,
    'packages/claw-hermes/gateway_state_projection.py',
    'tests/test_projected_launch_l145a8.py','tests/test_self_identity_r147.py'))
def read(name):return json.loads((E/name).read_text(encoding='utf-8'))
class SelfIdentityHistory(unittest.TestCase):
    def integration(self,root):
        raw=(root/INTEGRATION).read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(),INTEGRATION_SHA,'original R150 integration changed')
        value=json.loads(raw)
        self.assertEqual(set(value['sourceHashes']),APPLIED_NAMES)
        return value
    def assert_current_sources(self,root):
        # Three R150 applied files remain exact. The launcher advanced in R156;
        # projection advanced independently in R161 and has a current-source pin.
        # Expected bytes come from fixed records/pins, never from the live file.
        current=dict(self.integration(root)['sourceHashes'])
        raw=(root/PREPUBLICATION).read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(),PREPUBLICATION_SHA,'R156 source binding changed')
        accepted=json.loads(raw)
        self.assertEqual(accepted['sourceCommit'],CURRENT_SOURCE)
        self.assertEqual(accepted['sourceHashes'][LAUNCHER],CURRENT_LAUNCHER_SHA)
        current[LAUNCHER]=CURRENT_LAUNCHER_SHA
        service_history.assert_current_sources(root,names=(PROJECTION,))
        current[PROJECTION]=service_history.CURRENT_SOURCES[PROJECTION]
        base=json.loads((root/'evidence/d3b-self-identity-r150a1/baseline.json').read_bytes())
        for name,want in current.items():
            self.assertEqual(hashlib.sha256((root/name).read_bytes()).hexdigest(),want,
                             'current product bytes changed: '+name)
            if name.startswith('packages/'):
                self.assertNotEqual(want,base['sources'][name])
                self.assertIsNone(h.saved_generation_hash(root,name,want))
                self.assertEqual(h.source_path(root,name,want),root/name)
                self.assertEqual(h.source_hash(root,name,want),want)
    def assert_applied_sources(self,root):
        applied=self.integration(root)
        self.assertIs(applied['allFiveAppliedFilesEqualTestedR147'],True)
        for name,want in applied['sourceHashes'].items():
            # This is one fixed historical generation, not a fallback for live code.
            if name==LAUNCHER:path=root/APPLIED_LAUNCHER
            elif name==PROJECTION:
                path=service_history.archived_source(root,name,want)
                self.assertIsNotNone(path,'R150 applied projection must be archived')
            else:path=root/name
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),want,
                             'R150 applied bytes changed: '+name)
    def source_fixture(self,directory):
        root=Path(directory)
        names=(*APPLIED_NAMES,INTEGRATION,PREPUBLICATION,APPLIED_LAUNCHER,
            'evidence/d3b-self-identity-r150a1/baseline.json',
            'evidence/d3b-self-identity-r150a1/historical-source-bindings.json',
            service_history.BINDING,service_history.SOURCES[PROJECTION]['path'])
        for name in names:
            path=root/name;path.parent.mkdir(parents=True,exist_ok=True)
            path.write_bytes((ROOT/name).read_bytes())
        return root
    def test_exact_old_path_and_digest_bind_archived_bytes(self):
        base=read('baseline.json');binding=read('historical-source-bindings.json')
        self.assertEqual(base['base'],h.BASE);self.assertEqual(binding['base'],h.BASE)
        self.assertEqual(set(binding['sources']),h.NAMES);self.assertEqual(len(h.NAMES),9)
        for name,row in binding['sources'].items():
            want=base['sources'][name];self.assertEqual(row['sha256'],want)
            self.assertEqual(h.saved_generation_hash(ROOT,name,want),want)
            self.assertEqual(hashlib.sha256((ROOT/row['path']).read_bytes()).hexdigest(),want)
    def test_unknown_paths_or_generations_are_not_redirected(self):
        self.assertIsNone(h.saved_generation_hash(ROOT,'unknown.py','0'*64))
        for name in h.NAMES:
            self.assertIsNone(h.saved_generation_hash(ROOT,name,'0'*64))
            self.assertEqual(h.source_path(ROOT,name,'0'*64),ROOT/name)
    def test_current_product_is_checked_live_not_old_kernel_snapshot(self):
        self.assert_current_sources(ROOT)
    def test_tampered_current_launcher_cannot_be_hidden_by_applied_archive(self):
        with tempfile.TemporaryDirectory() as d:
            root=self.source_fixture(d)
            (root/LAUNCHER).write_bytes(b'# altered current launcher\n')
            self.assert_applied_sources(root)
            with self.assertRaisesRegex(AssertionError,'current product bytes changed'):
                self.assert_current_sources(root)
    def test_tampered_applied_launcher_cannot_be_hidden_by_current_source(self):
        with tempfile.TemporaryDirectory() as d:
            root=self.source_fixture(d)
            (root/APPLIED_LAUNCHER).write_bytes(b'# altered R150 integrated launcher\n')
            self.assert_current_sources(root)
            with self.assertRaisesRegex(AssertionError,'R150 applied bytes changed'):
                self.assert_applied_sources(root)
    def test_tampered_current_projection_cannot_be_hidden_by_parent_archive(self):
        with tempfile.TemporaryDirectory() as d:
            root=self.source_fixture(d)
            (root/PROJECTION).write_bytes(b'# altered current projection\n')
            self.assert_applied_sources(root)
            with self.assertRaisesRegex(AssertionError,'current product bytes changed'):
                self.assert_current_sources(root)
    def test_tampered_applied_projection_cannot_be_hidden_by_current_source(self):
        with tempfile.TemporaryDirectory() as d:
            root=self.source_fixture(d)
            (root/service_history.SOURCES[PROJECTION]['path']).write_bytes(b'# altered R150 projection\n')
            self.assert_current_sources(root)
            with self.assertRaisesRegex(AssertionError,'archived source bytes changed'):
                self.assert_applied_sources(root)
    def test_tampered_archive_is_never_accepted(self):
        name='packages/claw-hermes/credential_guard.py';binding=read('historical-source-bindings.json');want=binding['sources'][name]['sha256']
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);folder=root/'evidence/d3b-self-identity-r150a1';folder.mkdir(parents=True)
            for file in ('baseline.json','historical-source-bindings.json'):(folder/file).write_bytes((E/file).read_bytes())
            (root/binding['sources'][name]['path']).write_text('altered',encoding='utf-8')
            with self.assertRaisesRegex(AssertionError,'executed bytes changed'):h.saved_generation_hash(root,name,want)
    def test_manifest_cannot_point_to_another_file(self):
        name='packages/claw-hermes/credential_guard.py';binding=read('historical-source-bindings.json');want=binding['sources'][name]['sha256']
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);folder=root/'evidence/d3b-self-identity-r150a1';folder.mkdir(parents=True)
            (folder/'baseline.json').write_bytes((E/'baseline.json').read_bytes())
            binding['sources'][name]['path']='elsewhere.py'
            (folder/'historical-source-bindings.json').write_text(json.dumps(binding),encoding='utf-8')
            with self.assertRaisesRegex(AssertionError,'archived source path'):h.saved_generation_hash(root,name,want)
    def test_r147_patch_and_all_five_tested_candidate_bytes_preserved(self):
        original=read('r147-original/summary.json')
        self.assertEqual(hashlib.sha256((E/'R147-self-identity.patch').read_bytes()).hexdigest(),original['patchSha256'])
        self.assert_applied_sources(ROOT)
        proof=read('r147-original/red-green.json')
        self.assertEqual(proof['red-final']['testSha256'],proof['green-final']['testSha256'])
        self.assertEqual((proof['red-final']['exitCode'],proof['green-final']['exitCode']),(1,0))
    def test_prior_outcomes_remain_historical_and_first_full_fail_kept(self):
        full=read('full001/result.json');self.assertEqual((full['total'],full['failures'],full['errors'],full['exitCode']),(3630,20,0,1))
        self.assertEqual(hashlib.sha256((E/'full001/tests.txt').read_bytes()).hexdigest(),full['rawLogSha256'])
        original=read('r147-original/summary.json');self.assertFalse(original['kernelOrLinuxAcceptancePerformed']);self.assertFalse(original['fullRepositorySuiteRun'])
        guard='packages/claw-hermes/credential_guard.py';b=read('baseline.json')
        prior=json.loads((ROOT/'evidence/d3b-native-profile-q104e/candidate-001.json').read_text())
        self.assertEqual(prior['files'][guard]['sha256'],b['sources'][guard])
    def test_original_evidence_copy_provenance_and_scope(self):
        p=read('original-evidence-provenance.json');self.assertTrue(p['copiedNotReexecuted']);self.assertTrue(p['noKernelAcceptanceImplied'])
        for name,r in p['records'].items():self.assertEqual(hashlib.sha256((E/'r147-original'/name).read_bytes()).hexdigest(),r['sha256'])
        r=read('r147-original/compatibility.json');self.assertEqual((r['total'],r['passed'],r['errors'],r['failures'],r['skipped']),(210,210,0,0,0))
        self.assertTrue(r['selectionNotFullSuite']);self.assertEqual(r['newTestsIncluded'],19)
if __name__=='__main__':unittest.main()
