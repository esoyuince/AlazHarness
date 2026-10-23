"""Explicit prepared-profile contracts; Windows fixture metadata is doubled.
No kernel/native confinement is executed by these unit methods.
"""
import inspect,os,stat,sys,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import test_gateway_native_layout as base
import test_gateway_store_startup as startup_base
layout=base.layout;projection=base.projection;s=startup_base.s

class PreparedScaffold(unittest.TestCase):
    def setUp(self):
        base.LayoutFixtures.setUp(self)
        p=self.home/'response_store.db';p.write_bytes(b'0'*512);p.chmod(0o600)
    def check(self,**kw):
        return layout.inspect_profile(self.home,uid=self.uid,gid=self.gid,device=self.device,include_response=True,**kw)
    def scaffold(self):
        (self.home/'platforms').mkdir(mode=0o700);(self.home/'platforms/pairing').mkdir(mode=0o700)
    def test_new_mode_accepts_fresh_three_store_without_creating_scaffold(self):
        before={p.relative_to(self.home).as_posix() for p in self.home.rglob('*')}
        result=self.check(include_prepared=True)
        self.assertNotIn('platforms',result)
        self.assertEqual({p.relative_to(self.home).as_posix() for p in self.home.rglob('*')},before)
    def test_explicit_two_empty_directories_accepted(self):
        self.scaffold();result=self.check(include_prepared=True)
        self.assertEqual(set(result)-{'profile'},set(layout.REQUIRED)|{'response_store.db','platforms','platforms/pairing'})
    def test_default_three_store_rejects_same_new_directories(self):
        self.scaffold()
        with self.assertRaisesRegex(layout.NativeLayoutRejected,'unexpected_entry'):self.check()
    def test_false_option_does_not_enable_scaffold(self):
        self.scaffold()
        with self.assertRaisesRegex(layout.NativeLayoutRejected,'unexpected_entry'):self.check(include_prepared=False)
    def test_parent_only_without_pairing_refused(self):
        (self.home/'platforms').mkdir(mode=0o700)
        with self.assertRaisesRegex(layout.NativeLayoutRejected,'required_entry'):self.check(include_prepared=True)
    def test_pairing_files_and_hidden_auth_never_accepted(self):
        self.scaffold()
        for name in ('auth.json','pairings.json','.env','payload.py'):
            p=self.home/'platforms/pairing'/name;p.write_text('{}');p.chmod(0o600)
            try:
                with self.subTest(name=name),self.assertRaisesRegex(layout.NativeLayoutRejected,'unexpected_entry'):self.check(include_prepared=True)
            finally:p.unlink()
    def test_pairing_nested_directory_refused(self):
        self.scaffold();(self.home/'platforms/pairing/nested').mkdir(mode=0o700)
        with self.assertRaisesRegex(layout.NativeLayoutRejected,'unexpected_entry'):self.check(include_prepared=True)
    def test_platform_sibling_directory_refused(self):
        self.scaffold();(self.home/'platforms/telegram').mkdir(mode=0o700)
        with self.assertRaisesRegex(layout.NativeLayoutRejected,'unexpected_entry'):self.check(include_prepared=True)
    def test_pairing_regular_file_refused(self):
        (self.home/'platforms').mkdir(mode=0o700);(self.home/'platforms/pairing').write_bytes(b'')
        with self.assertRaises(layout.NativeLayoutRejected):self.check(include_prepared=True)
    def test_prepared_option_requires_actual_bool(self):
        for value in (1,0,None,'yes',[]):
            with self.subTest(value=value),patch.object(layout,'_snapshot') as snap,self.assertRaisesRegex(layout.NativeLayoutRejected,'prepared_option'):
                self.check(include_prepared=value)
            snap.assert_not_called()
    def test_prepared_option_requires_response_store(self):
        with patch.object(layout,'_snapshot') as snap,self.assertRaisesRegex(layout.NativeLayoutRejected,'prepared_requires_response'):
            layout.inspect_profile(self.home,uid=self.uid,gid=self.gid,device=self.device,include_prepared=True)
        snap.assert_not_called()
    def test_only_original_aux_files_opened(self):
        self.scaffold();opened=[];original=layout.os.open
        def observe(path,*args,**kw):opened.append(Path(path).relative_to(self.home).as_posix());return original(path,*args,**kw)
        with patch.object(layout.os,'open',side_effect=observe):self.check(include_prepared=True)
        self.assertEqual(opened,['SOUL.md','cache/schema_columns.json'])

class StartupSelection(unittest.TestCase):
    setUp=startup_base.Lifecycle.setUp
    mark=startup_base.Lifecycle.mark
    make_store=startup_base.Lifecycle.make_store
    def response(self):return s.response_preopen.PreparedResponseExpectation(s.response_preopen.NATIVE_FEATURE,s.response_preopen.SCHEMA_SHA256,(7,13))
    def test_default_remains_unselected(self):
        self.assertFalse(inspect.signature(s.NativeStoreStartup).parameters['prepared_layout'].default)
        o=s.NativeStoreStartup(self.held,self.mount,self.expected,instance_id='fixture');o.start()
        self.assertNotIn('include_prepared',self.layout.call_args.kwargs);o.close()
    def test_selected_mode_requires_response_and_no_lease_effect(self):
        self.lease.reset_mock()
        with self.assertRaisesRegex(s.StoreStartupRejected,'prepared_layout_requires_response'):
            s.NativeStoreStartup(self.held,self.mount,self.expected,instance_id='fixture',prepared_layout=True)
        self.lease.assert_not_called();self.native.assert_not_called()
    def test_nonboolean_prepared_mode_refused(self):
        for value in (None,1,'true'):
            with self.subTest(value=value),self.assertRaisesRegex(s.StoreStartupRejected,'prepared_layout_option'):
                s.NativeStoreStartup(self.held,self.mount,self.expected,instance_id='fixture',prepared_layout=value)
    def test_owner_forwards_optin_before_cold_helpers(self):
        self.layout.side_effect=ValueError('test stop after selected layout call')
        o=s.NativeStoreStartup(self.held,self.mount,self.expected,instance_id='fixture',response_expected=self.response(),prepared_layout=True)
        with self.assertRaises(s.StoreStartupRejected):o.start()
        self.assertIs(self.layout.call_args.kwargs['include_prepared'],True)
        self.assertIs(self.layout.call_args.kwargs['include_response'],True)
        self.pre.assert_not_called();self.native.assert_not_called();o.close()

class ProjectionSelection(unittest.TestCase):
    def test_new_selector_explicit_old_defaults_unchanged(self):
        self.assertEqual(projection.validate_layout(projection.NATIVE_PREPARED_LAYOUT),'hermes-native-prepared-three-stores-cold-v1')
        self.assertEqual(inspect.signature(projection.enter).parameters['profile_layout'].default,projection.MINIMAL_LAYOUT)
        self.assertFalse(inspect.signature(layout.inspect_profile).parameters['include_prepared'].default)
        self.assertNotIn('platforms',layout.DIRECTORIES);self.assertNotIn('platforms',layout.ALLOWED)
    def test_unknown_selector_still_refuses_before_kernel(self):
        with patch.object(projection.gp,'inspect') as called,self.assertRaises(projection.StateProjectionRejected):
            projection.enter({}, {},None,profile_layout='prepared')
        called.assert_not_called()
if __name__=='__main__':unittest.main()
