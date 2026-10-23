"""Retain original failed confinement evidence and exact mismatch, offline only."""
from pathlib import Path
import ast,hashlib,json,unittest
ROOT=Path(__file__).resolve().parents[1]
E=ROOT/'evidence/d3b-confined-consumer-f126c6'
class FailedConfinementReceipt(unittest.TestCase):
    def test_no_success_is_inferred_from_partial_consumer_preparation(self):
        records=json.loads((E/'reviewed-failed-attempts.json').read_text(encoding='utf-8'))['records']
        self.assertEqual([r['attempt'] for r in records],['001','002','003'])
        for r in records:self.assertEqual(r['result'],'FAIL');self.assertEqual(r['completedPreparedConsumerResults'],0)
        self.assertEqual(records[0]['error']['reason'],'broker_not_ready')
        self.assertTrue(records[1]['forcedCleanup']);self.assertFalse(records[2]['forcedCleanup'])
        self.assertEqual(records[2]['error']['reason'],'unexpected_confined_frame')
        frames=[e['unexpectedConfinedFrame'] for e in records[2]['selectedEvents'] if 'unexpectedConfinedFrame' in e]
        self.assertEqual(len(frames),1);self.assertEqual(frames[0]['phase'],'ORIGINAL_OWNER_CLOSE');self.assertEqual(frames[0]['reason'],'native_layout_unexpected_entry')
    def test_only_runner_construction_created_new_pairing_directories(self):
        r=json.loads((E/'layout-incompatibility-independent.json').read_text(encoding='utf-8'))
        additions=[x for x in r['snapshotTransitions'] if x['added'] or x['removed']]
        self.assertEqual(additions,[{'from':'runner_imported','to':'runner_constructed','added':['platforms','platforms/pairing'],'removed':[]}])
        self.assertEqual(set(r['unexpectedPaths']),{'platforms','platforms/pairing'})
        for obj in r['unexpectedPaths'].values():self.assertEqual(obj,{'type':'directory','mode':'0o700','bytes':None})
        self.assertFalse(r['allowedDirectoryListBroadened']);self.assertFalse(r['runtimeSourceChangedHere']);self.assertFalse(r['newFullConfinementAccepted'])
    def test_exact_old_native_sources_remain_archived_not_relabelled(self):
        r=json.loads((E/'layout-incompatibility-independent.json').read_text(encoding='utf-8'))
        self.assertEqual(r['nativeFeature'],'1e97dd617b81120255304e472ce322befcdb9ccd')
        for name,item in r['sourceFiles'].items():self.assertEqual(hashlib.sha256((ROOT/item['archive']).read_bytes()).hexdigest(),item['sha256'],name)
        self.assertEqual(hashlib.sha256((E/'gateway_native_layout.before-f126.txt').read_bytes()).hexdigest(),r['policySha256'])
        native=(E/'gateway__run_runtime_init.py.source.txt').read_text(encoding='utf-8');self.assertIn('self.pairing_store = PairingStore()',native)
        constants=(E/'hermes_constants.py.source.txt').read_text(encoding='utf-8');self.assertIn('return old_path if _legacy_path_has_content(old_path) else home / new_subpath',constants)
    def test_cold_layout_was_intentionally_finite_not_arbitrary_profile(self):
        tree=ast.parse((E/'gateway_native_layout.before-f126.txt').read_text(encoding='utf-8'))
        directories=next(ast.literal_eval(n.value.args[0]) for n in tree.body if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name) and n.targets[0].id=='DIRECTORIES')
        self.assertIn('pairing',directories);self.assertNotIn('platforms',directories);self.assertNotIn('platforms/pairing',directories)
        r=json.loads((E/'layout-incompatibility-independent.json').read_text(encoding='utf-8'));self.assertTrue(r['ordinaryRuntimeDefaultMustStay']);self.assertTrue(r['actualColdLayoutRefuses'])
if __name__=='__main__':unittest.main()
