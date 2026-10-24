"""Source-bound P108E actual preconstructor sequence receipts; offline checks."""
import hashlib,json
from historical_owner_b129d6 import executed_source_hash as pre_b129_hash
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
E=ROOT/'evidence/d3b-preopen-p108e'
class NativePreopenReceipt(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.outer=json.loads((E/'native-002-stdout.txt').read_bytes())
        cls.proof=json.loads(cls.outer['stdout'])
        cls.target=json.loads(cls.proof['events'][1]['stdout'])
    def test_current_sources_and_immutable_vendor(self):
        self.assertEqual(json.loads((E/'native-002-result.json').read_text())['exitCode'],0)
        self.assertEqual(self.outer['exitCode'],0);self.assertIs(self.outer['temporaryRootRemoved'],True)
        self.assertIs(self.outer['sourcesUnchanged'],True);self.assertIs(self.proof['sourcesUnchanged'],True)
        manifest=json.loads((E/'native-002-intent.json').read_text())['sources']
        self.assertEqual(self.target['sourceSha256'],manifest)
        vendor=json.loads((ROOT/'evidence/d3b-native-stores-h105e/native-source-inventory.json').read_text())
        for name,digest in manifest.items():
            with self.subTest(source=name):
                if name.startswith(('packages/','scripts/')):
                    self.assertEqual(pre_b129_hash(ROOT,name,digest),digest)
                elif name.startswith('vendor-native/'):
                    self.assertEqual(vendor['nativeSources'][name.removeprefix('vendor-native/')]['sha256'],digest)
                elif name.startswith('dependencies/'):
                    self.assertEqual(vendor['dependency']['sourceSha256'][name.removeprefix('dependencies/')],digest)
                else:self.fail('unknown_source_root')
    def test_real_preflight_before_native_open_and_live_gate(self):
        t=self.target;self.assertEqual(t['result'],'PASS_NATIVE_PREOPEN_SEQUENCE')
        self.assertEqual(t['checkCount'],37);self.assertEqual(len(t['checks']),37)
        self.assertTrue(all(v is True for v in t['checks'].values()))
        self.assertEqual([e['action'] for e in self.proof['events']],['prepare','launch'])
        self.assertEqual([e['exitCode'] for e in self.proof['events']],[0,0])
        self.assertEqual(t['successfulPreflight']['parentPid'],t['parentPid'])
        self.assertNotEqual(t['successfulPreflight']['workerPid'],t['parentPid'])
        self.assertEqual(t['successfulPreflight']['state'],'COLD_STORES_PREFLIGHT_VERIFIED')
        self.assertEqual(t['successfulPreflight']['epochObserved'],0)
        self.assertEqual(t['liveGate']['state'],'NATIVE_STORE_CONNECTIONS_VERIFIED')
        self.assertEqual(t['liveGate']['epochObserved'],0)
        self.assertIs(t['guard']['selfMountMetadata'],True)
    def test_refusals_are_explicit_nonmutating_not_repairs(self):
        t=self.target
        self.assertEqual(t['denials'],{'wrong_digest':'preopen_schema_mismatch','wrong_epoch':'preopen_epoch',
            'old_version':'preopen_schema_version','pending_repair':'preopen_constructor_metadata',
            'incomplete_backfill':'preopen_constructor_metadata','sidecar_present':'preopen_explicit_recovery_required',
            'nonprivate_file':'preopen_file_identity','symlink_file':'preopen_parent_unavailable',
            'busy_live_parent':'preopen_observation_unavailable'})
        for name in t['denials']:
            if name=='busy_live_parent':continue
            self.assertIs(t['checks'][name+'_nonmutating'],True)
            self.assertIs(t['checks'][name+'_lease_retained'],True)
        self.assertIs(t['checks']['sidecar_not_deleted'],True)
        metadata=t['successfulPreflight']['constructorMetadata']
        self.assertEqual(metadata['state'],'KNOWN_CONSTRUCTOR_REPAIR_MARKERS_CLEAR')
        self.assertIs(metadata['allConstructorSideEffectsExcluded'],False)
    def test_parent_locks_survive_child_raw_reads_and_close(self):
        self.assertEqual(self.target['lockSequence'],[{'state':'BUSY','code':5},{'state':'BUSY','code':5},{'state':'ACQUIRED_ROLLED_BACK'}])
        self.assertEqual(self.target['audit'],{'parentRawDatabaseOpens':0,'parentSqliteConnects':0})
        self.assertIs(self.target['checks']['native_profile_released_after_close'],True)
        for key in ('rootUsed','fullProjectionTested','nativeMethodsMocked','nativeConstructorRepairGuaranteedAbsent','runtimeAdmissionAuthorized','fullD3BAccepted'):
            self.assertIs(self.target[key],False)
        self.assertEqual(self.target['providerCalls'],0)
    def test_first_failure_and_unchanged_product_preserved(self):
        self.assertEqual(json.loads((E/'native-001-result.json').read_text())['exitCode'],1)
        first=json.loads((E/'native-001-stdout.txt').read_bytes())
        failed=json.loads(first['stdout'])['events'][1]
        self.assertIn('AssertionError: symlink_file',failed['stderr'])
        patch=json.loads((E/'qa-symlink-correction.json').read_text())
        self.assertIs(patch['productChanged'],False)
        name='packages/claw-hermes/gateway_store_preopen.py'
        self.assertEqual(first['sources'][name],self.outer['sources'][name])
if __name__=='__main__':unittest.main()
