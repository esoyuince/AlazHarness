"""Finite layout contract tests; Windows tests double POSIX ownership only.
Linux executes the same fixtures with real modes/UIDs and O_NOFOLLOW semantics.
"""
from contextlib import ExitStack
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'packages/claw-hermes'))
import gateway_native_layout as layout
import gateway_state_projection as projection
E=ROOT/'evidence/d3b-native-layout-l106r'
DATA=json.loads((E/'native-auxiliary-fixture.json').read_text())

class ObjectContracts(unittest.TestCase):
    def info(self,**kw):
        d=dict(st_dev=1,st_ino=3,st_mode=stat.S_IFREG|0o600,st_uid=1000,st_gid=1000,
               st_nlink=1,st_size=512,st_mtime_ns=1,st_ctime_ns=1);d.update(kw);return SimpleNamespace(**d)
    def test_private_regular_object(self):self.assertEqual(layout._private(self.info(),1000,1000,1,False)[1],3)
    def test_object_type_owner_mode_device_and_link_refused(self):
        for kw in ({'st_uid':1001},{'st_gid':1001},{'st_dev':2},{'st_nlink':2},
                   {'st_mode':stat.S_IFREG|0o644},{'st_mode':stat.S_IFLNK|0o600},
                   {'st_mode':stat.S_IFSOCK|0o600},{'st_mode':stat.S_IFIFO|0o600}):
            with self.subTest(kw=kw),self.assertRaises(layout.NativeLayoutRejected):layout._private(self.info(**kw),1000,1000,1,False)
    def test_directory_mode_separate(self):
        self.assertEqual(layout._private(self.info(st_mode=stat.S_IFDIR|0o700,st_nlink=2),1000,1000,1,True)[5],2)
        with self.assertRaises(layout.NativeLayoutRejected):layout._private(self.info(st_mode=stat.S_IFDIR|0o600),1000,1000,1,True)
    def test_large_regular_object_refused(self):
        with self.assertRaisesRegex(layout.NativeLayoutRejected,'file_limit'):layout._private(self.info(st_size=layout.MAX_FILE_BYTES+1),1000,1000,1,False)
    def test_scan_refuses_first_unknown_without_draining_iterator(self):
        class Stream:
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def __iter__(self):
                yield SimpleNamespace(name='unexpected')
                raise AssertionError('unbounded_iterator_was_drained')
        with patch.object(layout.os,'scandir',return_value=Stream()),self.assertRaisesRegex(layout.NativeLayoutRejected,'unexpected_entry'):
            layout._children(Path('/owned'),{'expected'})
    def test_opt_in_is_explicit_and_minimal_default(self):
        import inspect
        self.assertEqual(inspect.signature(projection.enter).parameters['profile_layout'].default,projection.MINIMAL_LAYOUT)
        self.assertEqual(projection.validate_layout(layout.PROFILE_LAYOUT),layout.PROFILE_LAYOUT)
    def test_bad_layout_refuses_before_any_kernel_action(self):
        for value in (None,True,1,{},'native',''):
            with self.subTest(value=value),patch.object(projection.gp,'inspect') as inspect,self.assertRaisesRegex(projection.StateProjectionRejected,'layout_invalid'):
                projection.enter({}, {}, None,profile_layout=value)
            inspect.assert_not_called()
    def test_no_implicit_default_profile_widening(self):
        self.assertNotIn('SOUL.md',projection.ALLOWED)
        self.assertNotIn('cache',projection.ALLOWED)
        self.assertEqual(projection.REQUIRED,{'gateway.lock','state.db','runs_idempotency.db'})

class LayoutFixtures(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory(prefix='l106r-unit-');self.addCleanup(tmp.cleanup)
        self.home=Path(tmp.name).resolve();self.home.chmod(0o700)
        for name in sorted(layout.DIRECTORIES,key=lambda n:len(Path(n).parts)):(self.home/name).mkdir(mode=0o700)
        for name in layout.DATABASES:(self.home/name).write_bytes(b'0'*512)
        for name in layout.LOCKS:(self.home/name).write_bytes(b'')
        (self.home/'SOUL.md').write_bytes(DATA['soul'].encode())
        (self.home/'cache/schema_columns.json').write_text(json.dumps(DATA['cache']),encoding='utf-8')
        for p in self.home.rglob('*'):
            if p.is_file():p.chmod(0o600)
        self.uid=os.getuid() if hasattr(os,'getuid') else 1000
        self.gid=os.getgid() if hasattr(os,'getgid') else 1000
        self.device=self.home.stat().st_dev
        if sys.platform=='win32':
            # Ownership is separately validated above with exact stat fixtures;
            # native Linux execution below does NOT apply these substitutions.
            stack=ExitStack();self.addCleanup(stack.close)
            def private(info,uid,gid,dev,directory):
                layout.require((stat.S_ISDIR if directory else stat.S_ISREG)(info.st_mode) and (directory or info.st_nlink==1),'native_layout_private_object')
                return layout.metadata(info)
            native_metadata=layout.metadata
            # Windows Path.stat ctime is creation, fstat ctime can be change time;
            # simulate consistent POSIX ctime only in these Windows fixtures.
            stack.enter_context(patch.object(layout,'metadata',side_effect=lambda info:native_metadata(info)[:-1]+(info.st_mtime_ns,)))
            stack.enter_context(patch.object(layout,'_private',side_effect=private))
            stack.enter_context(patch.object(layout.os,'O_CLOEXEC',0,create=True))
            stack.enter_context(patch.object(layout.os,'O_NOFOLLOW',0,create=True))
    def check(self):return layout.inspect_profile(self.home,uid=self.uid,gid=self.gid,device=self.device)
    def test_exact_prepared_fixture_passes(self):
        r=self.check();self.assertEqual(set(r),set(layout.REQUIRED)|{'profile'})
    def test_all_required_entries_mandatory(self):
        p=self.home/'state.db.fts_rebuild.lock';p.unlink()
        with self.assertRaisesRegex(layout.NativeLayoutRejected,'required_entry'):self.check()
    def test_forbidden_config_auth_and_unknown_top_level(self):
        for name in ('config.yaml','.env','auth.json','plugins','foreign'):
            p=self.home/name;p.write_bytes(b'owned');p.chmod(0o600)
            with self.subTest(name=name),self.assertRaisesRegex(layout.NativeLayoutRejected,'unexpected_entry'):self.check()
            p.unlink()
    def test_hooks_skills_cron_cannot_hide_payload(self):
        for folder in ('hooks','skills','cron','sessions','logs/curator'):
            p=self.home/folder/'payload.py';p.write_text('owned data');p.chmod(0o600)
            with self.subTest(folder=folder),self.assertRaisesRegex(layout.NativeLayoutRejected,'unexpected_entry'):self.check()
            p.unlink()
    def test_extra_cache_file_refused(self):
        (self.home/'cache/unexpected.json').write_text('{}')
        with self.assertRaisesRegex(layout.NativeLayoutRejected,'unexpected_entry'):self.check()
    def test_unprepared_zero_byte_db_refused(self):
        (self.home/'state.db').write_bytes(b'')
        with self.assertRaisesRegex(layout.NativeLayoutRejected,'unprepared_database'):self.check()
    def test_soul_content_not_only_size_checked(self):
        p=self.home/'SOUL.md';data=p.read_bytes();p.write_bytes(b'X'+data[1:])
        with self.assertRaisesRegex(layout.NativeLayoutRejected,'soul_content'):self.check()
    def test_cache_semantic_hash_not_whitespace_order(self):
        (self.home/'cache/schema_columns.json').write_text(json.dumps(DATA['cache'],indent=4,sort_keys=True),encoding='utf-8')
        self.check()
    def test_cache_schema_tampering_refused(self):
        c=json.loads(json.dumps(DATA['cache']));c['schema_hash']='f'*64
        (self.home/'cache/schema_columns.json').write_text(json.dumps(c),encoding='utf-8')
        with self.assertRaisesRegex(layout.NativeLayoutRejected,'cache_content'):self.check()
    def test_cache_duplicate_keys_refused(self):
        (self.home/'cache/schema_columns.json').write_text('{"tables":{},"tables":{}}')
        with self.assertRaisesRegex(layout.NativeLayoutRejected,'duplicate_key'):self.check()
    def test_cache_nonfinite_refused(self):
        (self.home/'cache/schema_columns.json').write_text('{"x":NaN}')
        with self.assertRaisesRegex(layout.NativeLayoutRejected,'nonfinite'):self.check()
    def test_cache_size_bounded_before_open(self):
        (self.home/'cache/schema_columns.json').write_bytes(b'x'*(layout.MAX_CACHE_BYTES+1))
        with patch.object(layout,'_read_aux') as read,self.assertRaisesRegex(layout.NativeLayoutRejected,'cache_size'):self.check()
        read.assert_not_called()
    def test_only_two_auxiliary_files_are_opened(self):
        original=layout.os.open;opened=[]
        def tracked(path,*a,**k):opened.append(Path(path).relative_to(self.home).as_posix());return original(path,*a,**k)
        with patch.object(layout.os,'open',side_effect=tracked):self.check()
        self.assertEqual(opened,['SOUL.md','cache/schema_columns.json'])
    def test_aux_fd_identity_changed_refused(self):
        original=layout.os.fstat
        def changed(fd):
            result=original(fd);values=list(result);values[1]+=1;return os.stat_result(values)
        with patch.object(layout.os,'fstat',side_effect=changed),self.assertRaises(layout.NativeLayoutRejected):self.check()
    def test_changed_snapshot_refused(self):
        first=layout._snapshot(self.home,self.uid,self.gid,self.device);second=dict(first);second['profile']=tuple([99]+list(first['profile'][1:]))
        with patch.object(layout,'_snapshot',side_effect=[first,second]),self.assertRaisesRegex(layout.NativeLayoutRejected,'changed'):self.check()
    def test_file_size_in_limit_and_sidecar_is_observed_not_opened(self):
        p=self.home/'state.db-journal';p.write_bytes(b'owned-sidecar');p.chmod(0o600)
        self.assertIn('state.db-journal',self.check())
    def test_invalid_identity_fails_before_io(self):
        for uid in (0,True,-1,'1000'):
            with self.subTest(uid=uid),patch.object(layout,'_snapshot') as snap,self.assertRaisesRegex(layout.NativeLayoutRejected,'identity'):
                layout.inspect_profile(self.home,uid=uid,gid=self.gid,device=self.device)
            snap.assert_not_called()

if __name__=='__main__':unittest.main()
