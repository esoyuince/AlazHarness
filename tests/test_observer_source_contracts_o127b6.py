"""Source-selection contracts use explicit fake modules/files, not native work."""
import hashlib,inspect,json,sys,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'packages/claw-hermes'))
import gateway_canonical_run_binding as b
import gateway_canonical_turn_observation as t
PREPARED=('gateway/session_authority.py','gateway/platforms/api_server_run_observation.py','gateway/platforms/api_server_runs.py')

class ObserverSourceContracts(unittest.TestCase):
    def test_legacy_default_and_old_pins_remain_exact(self):
        self.assertEqual(inspect.signature(b.NativeCanonicalBinding).parameters['native_feature'].default,b.NATIVE_FEATURE)
        self.assertEqual(b.NATIVE_FEATURE,'943210584828ccfcfd6adc8eb966ecaa8ca18429')
        self.assertEqual(t.NATIVE_FEATURE,b.NATIVE_FEATURE)
    def test_only_explicit_two_generations_accepted(self):
        for bad in ('',None,True,1,{},[],b.CURRENT_NATIVE_FEATURE[:7],'f'*40):
            with self.subTest(value=bad),patch('importlib.import_module',side_effect=AssertionError('unexpected import')),self.assertRaises(b.CanonicalBindingRejected):b._qualified_source(bad)
    def test_source_tables_return_copies_not_mutable_authority(self):
        d=b.source_hashes(b.CURRENT_NATIVE_FEATURE);d.clear()
        self.assertEqual(len(b.source_hashes(b.CURRENT_NATIVE_FEATURE)),5)
        d=b.source_hashes(b.NATIVE_FEATURE);d['wrong']='0'*64
        self.assertNotIn('wrong',b.source_hashes(b.NATIVE_FEATURE))
    def test_current_pins_equal_immutable_record(self):
        record=json.loads((ROOT/'evidence/d3b-current-observers-o127b6/source-generation-selection.json').read_text())
        self.assertEqual(b.CURRENT_NATIVE_SOURCE_HASHES,record['canonical']);self.assertEqual(t.CURRENT_SOURCE_HASHES,record['turn'])
        self.assertEqual(b.NATIVE_SOURCE_HASHES,record['legacyCanonical']);self.assertEqual(t.SOURCE_HASHES,record['legacyTurn'])
    def test_current_normal_scope_cannot_be_inferred_from_empty_inventory(self):
        s=b.CanonicalClaimSnapshot('a','r','s',1,None,'QUEUED',False,False,False,False,False,False,100).public()
        for name in ('serviceReadinessVerified','runtimeAdmissionAuthorized','storeReleaseAuthorized','physicalWorkerHealthVerified'):self.assertIs(s[name],False)
    def build(self,root,names):
        h={}
        for index,name in enumerate(names):
            p=root/name;p.parent.mkdir(parents=True,exist_ok=True);raw=('# fake source '+str(index)+'\n').encode();p.write_bytes(raw);h[name]=hashlib.sha256(raw).hexdigest()
        return h
    def test_default_normal_check_requires_all_five_sources(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp).resolve();h=self.build(root,b.NATIVE_SOURCE_HASHES)
            def module(name):return SimpleNamespace(__file__=str(root/(name.replace('.','/')+'.py')))
            with patch.object(b,'NATIVE_SOURCE_HASHES',h),patch('importlib.import_module',side_effect=module):self.assertEqual(b._qualified_source(),root)
    def test_hash_mismatch_rejected_instead_of_silent_repin(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp).resolve();h=self.build(root,b.NATIVE_SOURCE_HASHES);h[next(iter(h))]='0'*64
            def module(name):return SimpleNamespace(__file__=str(root/(name.replace('.','/')+'.py')))
            with patch.object(b,'NATIVE_SOURCE_HASHES',h),patch('importlib.import_module',side_effect=module),self.assertRaisesRegex(b.CanonicalBindingRejected,'source_unqualified'):b._qualified_source()
    def test_mixed_root_native_modules_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp).resolve();h=self.build(root/'a',b.NATIVE_SOURCE_HASHES);self.build(root/'b',b.NATIVE_SOURCE_HASHES);first=next(iter(h))
            def module(name):
                rel=name.replace('.','/')+'.py';return SimpleNamespace(__file__=str(root/('b' if rel==first else 'a')/rel))
            with patch.object(b,'NATIVE_SOURCE_HASHES',h),patch('importlib.import_module',side_effect=module),self.assertRaisesRegex(b.CanonicalBindingRejected,'mixed_native_roots'):b._qualified_source()
    def test_prepared_source_check_needs_only_existing_three_manifest_seams(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp).resolve();h=self.build(root,PREPARED)
            h.update({n:'0'*64 for n in b.CURRENT_NATIVE_SOURCE_HASHES if n not in h})
            with patch.object(b,'CURRENT_NATIVE_SOURCE_HASHES',h),patch('importlib.import_module',side_effect=AssertionError('active module import')):
                self.assertEqual(b._qualified_source(b.CURRENT_NATIVE_FEATURE,native_root=root),root)
            self.assertFalse((root/'gateway/session_api_turn.py').exists())
    def test_prepared_root_mode_cannot_use_legacy_generation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp).resolve();h=self.build(root,b.NATIVE_SOURCE_HASHES)
            with patch.object(b,'NATIVE_SOURCE_HASHES',h),self.assertRaises(b.CanonicalBindingRejected):b._qualified_source(b.NATIVE_FEATURE,native_root=root)
    def test_prepared_turn_refusal_precedes_active_native_import(self):
        self.assertIn('turn_prepared_active_path_not_qualified',inspect.getsource(t.NativeTurnWorkerObserver.__init__))
        src=inspect.getsource(t.NativeTurnWorkerObserver.__init__)
        self.assertLess(src.index('turn_prepared_active_path_not_qualified'),src.index('importlib.import_module'))
    def test_prepared_sources_all_within_original_closed_envelope(self):
        source=json.loads((ROOT/'config/prepared-consumer-s124b1-sources.json').read_text())['sources']
        for n in PREPARED:self.assertEqual(source[n],b.CURRENT_NATIVE_SOURCE_HASHES[n])
if __name__=='__main__':unittest.main()
