"""Explicit third-file layout; old minimal/native profile defaults unchanged."""
import sys,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tests'))
import test_gateway_native_layout as existing
layout=existing.layout
class ThirdLayout(unittest.TestCase):
    setUp=existing.LayoutFixtures.setUp
    def third(self):return layout.inspect_profile(self.home,uid=self.uid,gid=self.gid,device=self.device,include_response=True)
    def add(self):
        p=self.home/'response_store.db';p.write_bytes(b'0'*512);p.chmod(0o600);return p
    def test_explicit_third_required_but_default_refuses(self):
        with self.assertRaisesRegex(layout.NativeLayoutRejected,'required_entry'):self.third()
        self.add();self.assertIn('response_store.db',self.third())
        with self.assertRaisesRegex(layout.NativeLayoutRejected,'unexpected_entry'):
            layout.inspect_profile(self.home,uid=self.uid,gid=self.gid,device=self.device)
    def test_third_is_never_raw_opened_by_layout(self):
        self.add();opened=[];original=layout.os.open
        def observe(p,*a,**k):opened.append(Path(p).name);return original(p,*a,**k)
        with patch.object(layout.os,'open',side_effect=observe):self.third()
        self.assertEqual(opened,['SOUL.md','schema_columns.json'])
    def test_third_must_be_prepared_and_no_extra_file_granted(self):
        p=self.add();p.write_bytes(b'')
        with self.assertRaisesRegex(layout.NativeLayoutRejected,'unprepared'):self.third()
        p.write_bytes(b'0'*512);(self.home/'response_secrets.json').write_text('{}')
        with self.assertRaisesRegex(layout.NativeLayoutRejected,'unexpected_entry'):self.third()
    def test_response_option_not_truthy_coercion(self):
        for bad in (1,'yes',None,{}):
            with self.assertRaisesRegex(layout.NativeLayoutRejected,'response_option'):
                layout.inspect_profile(self.home,uid=self.uid,gid=self.gid,device=self.device,include_response=bad)
if __name__=='__main__':unittest.main()
