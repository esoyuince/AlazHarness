"""Retained-profile unit checks; POSIX boundary doubles inherited only on Windows/rootCI."""
from pathlib import Path
from dataclasses import replace
import hashlib,json,inspect,os,unittest
from unittest.mock import patch
import test_gateway_native_layout as original_fixture
import gateway_native_layout as layout
import gateway_retained_profile as retained

class RetainedLayout(unittest.TestCase):
    def setUp(self):
        original_fixture.LayoutFixtures.setUp(self)
        (self.home/'response_store.db').write_bytes(b'r'*512)
        for name in ('platforms','platforms/pairing','runtime','cache/documents'):
            (self.home/name).mkdir(mode=0o700)
        for name in ('auth.lock','runtime/active_sessions.lock'):(self.home/name).write_bytes(b'')
        (self.home/'runtime/active_sessions.json').write_text('{"entries": []}',encoding='utf-8')
        self.discovery={str(self.home/'source/tools/file_tools.py'):[123,456,True]}
        (self.home/'cache/tool_discovery_cache.json').write_text(json.dumps(self.discovery),encoding='utf-8')
        for p in self.home.rglob('*'):
            if p.is_file():p.chmod(0o600)
        identity=lambda p:(p.stat().st_dev,p.stat().st_ino)
        self.receipt=retained.RetainedProfileExpectation(retained.FEATURE,str(self.home),identity(self.home),
            tuple(identity(self.home/n) for n in ('state.db','runs_idempotency.db','response_store.db')),
            1,'previous-owner',hashlib.sha256((self.home/'cache/tool_discovery_cache.json').read_bytes()).hexdigest())
    def check(self,receipt=None):
        return layout.inspect_profile(self.home,uid=self.uid,gid=self.gid,device=self.device,
            include_response=True,include_prepared=True,retained=self.receipt if receipt is None else receipt)
    def write(self,name,data):
        p=self.home/name;p.write_bytes(data);p.chmod(0o600)
    def test_explicit_receipt_accepts_and_keeps_all_helper_bytes(self):
        before={p.relative_to(self.home).as_posix():p.read_bytes() for p in self.home.rglob('*') if p.is_file()}
        self.assertTrue(retained.PATHS<=set(self.check()));self.assertEqual(before,{p.relative_to(self.home).as_posix():p.read_bytes() for p in self.home.rglob('*') if p.is_file()})
    def test_existing_default_still_rejects_same_retained_profile(self):
        with self.assertRaisesRegex(layout.NativeLayoutRejected,'unexpected_entry'):
            layout.inspect_profile(self.home,uid=self.uid,gid=self.gid,device=self.device,include_response=True,include_prepared=True)
        self.assertIsNone(inspect.signature(layout.inspect_profile).parameters['retained'].default)
    def test_missing_any_retained_path_refused(self):
        for name in retained.FILES:
            p=self.home/name;old=p.read_bytes();p.unlink()
            try:
                with self.subTest(path=name),self.assertRaisesRegex(layout.NativeLayoutRejected,'required_entry'):self.check()
            finally:self.write(name,old)
    def test_config_credentials_and_unrelated_runtime_refused(self):
        for name in ('config.yaml','auth.json','.env','runtime/unrelated.json','cache/documents/file.txt'):
            self.write(name,b'private fixture')
            try:
                with self.subTest(path=name),self.assertRaisesRegex(layout.NativeLayoutRejected,'unexpected_entry'):self.check()
            finally:(self.home/name).unlink()
    def test_live_stale_or_extra_active_entries_refused_without_pruning(self):
        for value in ({'entries':[{'pid':99999}]},{'entries':[],'other':1},[],{'entries':{}},{}):
            raw=json.dumps(value).encode();self.write('runtime/active_sessions.json',raw)
            with self.subTest(value=value),self.assertRaisesRegex(layout.NativeLayoutRejected,'not_empty'):self.check()
            self.assertEqual((self.home/'runtime/active_sessions.json').read_bytes(),raw)
    def test_active_duplicate_and_nonfinite_refused(self):
        for raw in (b'{"entries":[],"entries":[]}',b'{"entries":NaN}'):
            self.write('runtime/active_sessions.json',raw)
            with self.assertRaises(layout.NativeLayoutRejected):self.check()
    def test_locks_must_be_empty(self):
        for name in ('auth.lock','runtime/active_sessions.lock'):
            self.write(name,b'not empty')
            try:
                with self.assertRaisesRegex(layout.NativeLayoutRejected,'lock_nonempty'):self.check()
            finally:self.write(name,b'')
    def test_cache_bytes_cannot_change_under_saved_receipt(self):
        value=dict(self.discovery);value[next(iter(value))]=[123,456,False]
        self.write('cache/tool_discovery_cache.json',json.dumps(value).encode())
        with self.assertRaisesRegex(layout.NativeLayoutRejected,'discovery_changed'):self.check()
    def test_receipt_has_strict_feature_and_identity_types(self):
        for receipt in (True,{},replace(self.receipt,native_feature='other'),replace(self.receipt,epoch=True),
                        replace(self.receipt,discovery_sha256='0'*63),replace(self.receipt,home_identity=[1,2])):
            with self.subTest(receipt=receipt),self.assertRaises(layout.NativeLayoutRejected):self.check(receipt)
    def test_other_profile_or_database_identity_refused(self):
        for receipt in (replace(self.receipt,home=str(self.home/'other')),
                        replace(self.receipt,database_identities=((self.device,999999999),*self.receipt.database_identities[1:]))):
            with self.assertRaisesRegex(layout.NativeLayoutRejected,'identity'):self.check(receipt)
    def test_same_path_replaced_database_refused(self):
        p=self.home/'state.db';p.rename(self.home/'old-state')
        self.write('state.db',b'x'*512);(self.home/'old-state').unlink()
        with self.assertRaisesRegex(layout.NativeLayoutRejected,'database_identity'):self.check()
    def test_cache_size_refused_before_open(self):
        self.write('cache/tool_discovery_cache.json',b'x'*(retained.MAX_DISCOVERY_BYTES+1))
        with patch.object(layout,'_read_aux') as reader,self.assertRaisesRegex(layout.NativeLayoutRejected,'discovery_size'):self.check()
        reader.assert_not_called()
    def test_only_four_auxiliary_files_read_no_locks_or_sqlite(self):
        opened=[];original=layout.os.open
        def track(path,*args,**kw):opened.append(Path(path).relative_to(self.home).as_posix());return original(path,*args,**kw)
        with patch.object(layout.os,'open',side_effect=track):self.check()
        self.assertEqual(opened,['SOUL.md','cache/schema_columns.json','cache/tool_discovery_cache.json','runtime/active_sessions.json'])
    def test_link_alias_refused(self):
        p=self.home/'cache/tool_discovery_cache.json';p.unlink();os.link(self.home/'SOUL.md',p)
        with self.assertRaises(layout.NativeLayoutRejected):self.check()
    def test_nonprepared_receipt_never_enables_other_layout(self):
        with patch.object(layout,'_snapshot') as reader,self.assertRaisesRegex(layout.NativeLayoutRejected,'requires_prepared'):
            layout.inspect_profile(self.home,uid=self.uid,gid=self.gid,device=self.device,retained=self.receipt)
        reader.assert_not_called()
    def test_capture_requires_original_closed_owner_before_files(self):
        with patch.object(layout,'_snapshot') as reader,self.assertRaisesRegex(layout.NativeLayoutRejected,'owner_not_closed'):
            retained.capture(object())
        reader.assert_not_called()

class DiscoveryShapes(unittest.TestCase):
    def test_canonical_metadata_and_boolean_only(self):
        self.assertEqual(retained._discovery_shape({'/source/tools/a.py':[1,2,True]}),{'/source/tools/a.py':[1,2,True]})
        for row in ([True,2,True],[1,-1,True],[1,2,1],[1,2,'yes'],[1,2],None):
            with self.subTest(row=row),self.assertRaises(layout.NativeLayoutRejected):retained._discovery_shape({'/source/tools/a.py':row})
    def test_empty_or_unbounded_discovery_refused(self):
        for value in ({},[],{'x'*4097:[1,2,True]}, {str(i):[1,2,True] for i in range(retained.MAX_DISCOVERY_ENTRIES+1)}):
            with self.assertRaises(layout.NativeLayoutRejected):retained._discovery_shape(value)

if __name__=='__main__':unittest.main()
