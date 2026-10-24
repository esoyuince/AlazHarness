"""Publication portability fixes do not relax runtime actor or data checks."""
from pathlib import Path
from types import SimpleNamespace
import hashlib,json,stat,unittest
from unittest.mock import patch
import test_gateway_native_layout as fixture
import historical_ci_p132l1 as history
ROOT=Path(__file__).resolve().parents[1]
class PublicationPortability(unittest.TestCase):
    def info(self,**overrides):
        values=dict(st_dev=7,st_ino=8,st_mode=stat.S_IFREG|0o600,st_uid=0,st_gid=0,
                    st_nlink=1,st_size=512,st_mtime_ns=1,st_ctime_ns=2)
        values.update(overrides);return SimpleNamespace(**values)
    def test_real_loopback_fixture_fully_stops_after_context(self):
        from test_hybrid_wire import FIXTURE
        with FIXTURE.Fixture() as server:
            self.assertTrue(server.thread.is_alive())
        self.assertFalse(server.thread.is_alive())
    def test_only_root_fixture_owner_ids_change(self):
        old=self.info();new=fixture.fixture_owner_info(old,0,0,1000,1000)
        self.assertEqual((new.st_uid,new.st_gid),(1000,1000))
        for name in vars(old):
            if name not in ('st_uid','st_gid'):self.assertEqual(getattr(new,name),getattr(old,name))
        self.assertEqual(fixture.layout._private(new,1000,1000,7,False)[1],8)
    def test_foreign_owner_and_modes_still_fail_real_guard(self):
        for changes in ({'st_uid':1001},{'st_gid':1001},{'st_mode':stat.S_IFREG|0o644},{'st_nlink':2},{'st_dev':9}):
            new=fixture.fixture_owner_info(self.info(**changes),0,0,1000,1000)
            with self.subTest(changes=changes),self.assertRaises(fixture.layout.NativeLayoutRejected):fixture.layout._private(new,1000,1000,7,False)
    def test_nonroot_metadata_not_rewritten(self):
        old=self.info(st_uid=1234,st_gid=5678);new=fixture.fixture_owner_info(old,1234,5678,1000,1000)
        self.assertEqual(vars(old),vars(new))
    def test_production_root_actor_still_rejected_before_io(self):
        for uid,gid in ((0,1000),(1000,0)):
            with patch.object(fixture.layout,'_snapshot') as call,self.assertRaisesRegex(fixture.layout.NativeLayoutRejected,'identity'):
                fixture.layout.inspect_profile(ROOT,uid=uid,gid=gid,device=7)
            call.assert_not_called()
    def test_pinned_csharp_checkout_matches_existing_native_receipts(self):
        raw=(ROOT/'scripts/qa/windows_appcontainer_probe.cs').read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(),'b6ca63ae024ae42fd237a18442a75effd65603dfba03954a801ea23e41ba7025')
        self.assertEqual(raw.count(b'\r\n'),229)
        self.assertIn('scripts/qa/windows_appcontainer_probe.cs text eol=crlf',(ROOT/'.gitattributes').read_text())
    def test_saved_old_generations_exact_and_unknown_not_bypassed(self):
        source=json.loads((ROOT/'evidence/d3b-canonical-api-joint-j131d6/full-sources-after.json').read_text())
        for name in history.NAMES:
            self.assertEqual(history.saved_generation_hash(ROOT,name,source[name]),source[name])
            self.assertIsNone(history.saved_generation_hash(ROOT,name,'0'*64))
        self.assertIsNone(history.saved_generation_hash(ROOT,'packages/not-real.py','0'*64))
if __name__=='__main__':unittest.main()
