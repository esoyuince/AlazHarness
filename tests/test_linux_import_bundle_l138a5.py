"""Synthetic transport rejection controls, not Linux or native execution."""
import hashlib,importlib.util,io,json,unittest,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('linux_import_probe_l138a5',ROOT/'scripts/qa/l138a5_linux_import_probe.py');probe=importlib.util.module_from_spec(spec);spec.loader.exec_module(probe)
class LinuxImportBundleContract(unittest.TestCase):
    def bundle(self,name='native/a.py',bad_hash=False):
        buf=io.BytesIO();raw=b'x=1\n'
        with zipfile.ZipFile(buf,'w') as z:
            z.writestr(name,raw);z.writestr('transport-manifest.json',json.dumps({'files':{name:'0'*64 if bad_hash else hashlib.sha256(raw).hexdigest()}}))
        return buf.getvalue()
    def test_exact_small_bundle_validates(self):
        raw=self.bundle();z,m=probe.validate_bundle(raw,hashlib.sha256(raw).hexdigest());self.assertEqual(z.read('native/a.py'),b'x=1\n');z.close()
    def test_outer_digest_changed_refuses(self):
        with self.assertRaisesRegex(ValueError,'bundle_digest'):probe.validate_bundle(self.bundle(),'0'*64)
    def test_traversal_and_foreign_sections_refuse(self):
        for name in ('native/../escape.py','/native/a.py','personal/token.txt'):
            raw=self.bundle(name)
            with self.subTest(name=name),self.assertRaises(ValueError):probe.validate_bundle(raw,hashlib.sha256(raw).hexdigest())
    def test_internal_member_digest_changed_refuses(self):
        raw=self.bundle(bad_hash=True)
        with self.assertRaisesRegex(ValueError,'bundle_member_digest'):probe.validate_bundle(raw,hashlib.sha256(raw).hexdigest())
if __name__=='__main__':unittest.main()
