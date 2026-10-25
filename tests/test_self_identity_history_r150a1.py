"""New-source custody and exact historic code resolution. No kernel acceptance."""
from pathlib import Path
import hashlib,json,tempfile,unittest
import historical_self_identity_r150a1 as h
ROOT=Path(__file__).resolve().parents[1]
E=ROOT/'evidence/d3b-self-identity-r150a1'
def read(name):return json.loads((E/name).read_text(encoding='utf-8'))
class SelfIdentityHistory(unittest.TestCase):
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
        base=read('baseline.json');current=read('integration.json')['sourceHashes']
        for name,want in current.items():
            self.assertEqual(hashlib.sha256((ROOT/name).read_bytes()).hexdigest(),want)
            if name.startswith('packages/'):
                self.assertNotEqual(want,base['sources'][name]);self.assertIsNone(h.saved_generation_hash(ROOT,name,want))
                self.assertEqual(h.source_hash(ROOT,name,want),want)
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
        original=read('r147-original/summary.json');current=read('integration.json')
        self.assertEqual(hashlib.sha256((E/'R147-self-identity.patch').read_bytes()).hexdigest(),original['patchSha256'])
        self.assertTrue(current['allFiveAppliedFilesEqualTestedR147']);self.assertEqual(len(current['sourceHashes']),5)
        for name,want in current['sourceHashes'].items():self.assertEqual(hashlib.sha256((ROOT/name).read_bytes()).hexdigest(),want)
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
