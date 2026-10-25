"""Historical source binding tests: old receipts never qualify changed kernel code."""
import hashlib,json,shutil,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import historical_self_identity_r149a9 as h
ROOT=Path(__file__).resolve().parents[1]
E=ROOT/'evidence/self-identity-r149a9'
class ExactHistoricalBinding(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory(prefix='r149-history-');self.addCleanup(t.cleanup)
        self.root=Path(t.name);self.e=self.root/'evidence/self-identity-r149a9';self.e.mkdir(parents=True)
        for name in ('baseline.json','historical-source-bindings.json'):shutil.copyfile(E/name,self.e/name)
        shutil.copytree(E/'historical-src',self.e/'historical-src')
        self.name='packages/claw-hermes/credential_guard.py';self.expected=h.PINS[self.name]
    def record(self):return json.loads((self.e/'historical-source-bindings.json').read_text(encoding='utf-8'))
    def write_record(self,value):(self.e/'historical-source-bindings.json').write_text(json.dumps(value),encoding='utf-8')
    def test_all_nine_names_equal_exact_baseline_and_archived_bytes(self):
        self.assertEqual(len(h.PINS),9);baseline=json.loads((E/'baseline.json').read_text(encoding='utf-8'))
        self.assertEqual(baseline['base'],h.BASE)
        for name,digest in h.PINS.items():
            self.assertEqual(baseline['sources'][name],digest)
            self.assertEqual(h.saved_generation_hash(ROOT,name,digest),digest)
            self.assertEqual(hashlib.sha256(h.historical_source_path(ROOT,name,digest).read_bytes()).hexdigest(),digest)
    def test_unknown_path_never_becomes_archive_authority(self):
        with patch.object(Path,'read_text',side_effect=AssertionError('must not read')):
            self.assertIsNone(h.saved_generation_hash(self.root,'unrelated.py',self.expected))
            self.assertIsNone(h.saved_generation_hash(self.root,'../credential_guard.py',self.expected))
    def test_unknown_expected_digest_never_redirects(self):
        with patch.object(Path,'read_text',side_effect=AssertionError('must not read')):
            self.assertIsNone(h.saved_generation_hash(self.root,self.name,'0'*64))
    def test_current_r147_product_never_inherits_historical_acceptance(self):
        r=json.loads((E/'r147-original-source-custody.json').read_text(encoding='utf-8'))
        for name,row in r['files'].items():
            self.assertEqual(hashlib.sha256((ROOT/name).read_bytes()).hexdigest(),row['afterSha256'])
            if row['beforeSha256'] is not None:
                self.assertNotEqual(row['afterSha256'],row['beforeSha256'])
                self.assertIsNone(h.saved_generation_hash(ROOT,name,row['afterSha256']))
    def test_tampered_archive_is_refused(self):
        path=h.saved_generation_path(self.root,self.name,self.expected);path.write_bytes(path.read_bytes()+b'\n# changed')
        with self.assertRaisesRegex(AssertionError,'source bytes changed'):h.saved_generation_hash(self.root,self.name,self.expected)
    def test_archive_path_cannot_be_replaced_with_other_location(self):
        r=self.record();r['sources'][self.name]['path']='../elsewhere';self.write_record(r)
        with self.assertRaisesRegex(AssertionError,'mapping changed'):h.saved_generation_hash(self.root,self.name,self.expected)
    def test_manifest_digest_cannot_replace_immutable_pin(self):
        r=self.record();r['sources'][self.name]['sha256']='0'*64;self.write_record(r)
        with self.assertRaisesRegex(AssertionError,'mapping changed'):h.saved_generation_hash(self.root,self.name,self.expected)
    def test_base_mutation_is_refused(self):
        r=self.record();r['base']='0'*40;self.write_record(r)
        with self.assertRaisesRegex(AssertionError,'base changed'):h.saved_generation_hash(self.root,self.name,self.expected)
    def test_missing_or_extra_source_set_is_refused(self):
        original=self.record()
        for changed in ('missing','extra'):
            r=json.loads(json.dumps(original))
            if changed=='missing':r['sources'].pop(self.name)
            else:r['sources']['unknown.py']={'sha256':self.expected,'path':'anywhere'}
            self.write_record(r)
            with self.assertRaisesRegex(AssertionError,'source set changed'):h.saved_generation_hash(self.root,self.name,self.expected)
    def test_baseline_pin_mutation_is_refused(self):
        p=self.e/'baseline.json';r=json.loads(p.read_text(encoding='utf-8'));r['sources'][self.name]='0'*64;p.write_text(json.dumps(r),encoding='utf-8')
        with self.assertRaisesRegex(AssertionError,'baseline digest changed'):h.saved_generation_hash(self.root,self.name,self.expected)
    def test_missing_archive_is_not_current_source_fallback(self):
        h.saved_generation_path(self.root,self.name,self.expected).unlink()
        with self.assertRaises(FileNotFoundError):h.saved_generation_hash(self.root,self.name,self.expected)
    def test_failed_full_and_old_kernel_receipt_remain_historical(self):
        first=json.loads((E/'full001/result.json').read_text(encoding='utf-8'))
        self.assertEqual((first['result'],first['failures'],first['errors'],first['exitCode']),('FAIL',20,0,1))
        self.assertEqual(hashlib.sha256((E/'full001/tests.txt').read_bytes()).hexdigest(),first['rawLogSha256'])
        q=ROOT/'evidence/d3b-native-profile-q104e';r=json.loads((q/'candidate-001.json').read_text(encoding='utf-8'))
        self.assertEqual(r['files'][self.name]['sha256'],self.expected)
        self.assertEqual(hashlib.sha256((q/r['files'][self.name]['snapshot']).read_bytes()).hexdigest(),self.expected)
        self.assertNotEqual(hashlib.sha256((ROOT/self.name).read_bytes()).hexdigest(),self.expected)
if __name__=='__main__':unittest.main()
