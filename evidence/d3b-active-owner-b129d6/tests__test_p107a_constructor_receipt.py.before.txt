"""Original native constructor effects + current read-only marker prerequisite."""
import hashlib
import json
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
E=ROOT/'evidence/d3b-preopen-p107a'
class ConstructorReceipt(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.o=json.loads((E/'marker-native-stdout.txt').read_bytes())
        cls.r=json.loads(cls.o['stdout'])
        cls.cases={e['case']:json.loads(e['stdout']) for e in cls.r['events']}
    def test_terminal_execution_and_exact_source_custody(self):
        self.assertEqual(json.loads((E/'marker-native-result.json').read_text())['exitCode'],0)
        self.assertEqual(self.o['exitCode'],0);self.assertIs(self.o['sourceUnchanged'],True);self.assertIs(self.o['temporaryRootRemoved'],True)
        self.assertEqual(self.r['result'],'OBSERVATIONS_COMPLETE');self.assertIs(self.r['sourcesUnchanged'],True)
        manifest=json.loads((E/'marker-native-intent.json').read_text())['sources']
        self.assertEqual(self.o['sources'],manifest);self.assertEqual(self.r['manifest']['files'],manifest)
        inv=json.loads((ROOT/'evidence/d3b-native-stores-h105e/native-source-inventory.json').read_text())
        for name,digest in manifest.items():
            with self.subTest(source=name):
                if name.startswith(('packages/','scripts/')):self.assertEqual(hashlib.sha256((ROOT/name).read_bytes()).hexdigest(),digest)
                elif name.startswith('vendor-native/'):self.assertEqual(inv['nativeSources'][name.removeprefix('vendor-native/')]['sha256'],digest)
                else:self.assertEqual(inv['dependency']['sourceSha256'][name.removeprefix('dependencies/')],digest)
        for child in self.cases.values():
            for name,digest in child['sourceHashes'].items():self.assertEqual(manifest[name],digest)
            self.assertIs(child['nativeMethodsReplaced'],False);self.assertIs(child['ownedMutationOnly'],True);self.assertIs(child['profileReleased'],True)
    def test_current_markers_reject_known_preconstructor_risks(self):
        expected={'untouched':None,'old_version':'constructor_metadata_schema_version','fts_stale':'constructor_metadata_repair_pending','missing_backfill':'constructor_metadata_backfill_incomplete'}
        self.assertEqual(set(self.cases),set(expected))
        for name,reason in expected.items():
            case=self.cases[name]
            self.assertIsNone(case['constructorFailure'])
            self.assertIs(case['initial']['markerGate']['accepted'],True)
            gate=case['beforeWritableConstructor']['markerGate'];self.assertIs(gate['accepted'],reason is None)
            if reason:self.assertEqual(gate['reason'],reason)
            self.assertIs(case['afterWritableConstructor']['markerGate']['accepted'],True)
            for key in ('initial','beforeWritableConstructor','afterWritableConstructor'):
                self.assertEqual(case[key]['observerTotalChanges'],0)
    def test_schema_identity_alone_misses_actual_repairs(self):
        identity=('schemaSha256','schemaVersion','applicationId','storeInstanceId','epochs','inode')
        for name in ('fts_stale','missing_backfill'):
            case=self.cases[name]
            self.assertTrue(all(case['initial'][k]==case['beforeWritableConstructor'][k] for k in identity))
            self.assertIs(case['preopenIdentityAndSchemaEqualToInitial'],True)
            self.assertIs(case['constructorChangedBytes'],True)
            self.assertNotEqual(case['beforeWritableConstructor']['migrationMarkers'],case['afterWritableConstructor']['migrationMarkers'])
        stale=self.cases['fts_stale'];self.assertIn(['fts_stale','1'],stale['beforeWritableConstructor']['migrationMarkers'])
        self.assertNotIn(['fts_stale','1'],stale['afterWritableConstructor']['migrationMarkers'])
        backfill=self.cases['missing_backfill'];self.assertEqual(backfill['beforeWritableConstructor']['migrationMarkers'],[])
        self.assertEqual(backfill['afterWritableConstructor']['migrationMarkers'],[['message_uid_backfill','1']])
    def test_clear_marker_result_does_not_claim_zero_write_constructor(self):
        untouched=self.cases['untouched'];self.assertIs(untouched['constructorChangedBytes'],True)
        self.assertIs(untouched['constructorChangedSchema'],False)
        receipt=untouched['beforeWritableConstructor']['markerGate']['receipt']
        self.assertIs(receipt['nativeConstructorMayWrite'],True)
        for key in ('allConstructorSideEffectsExcluded','schemaDigestVerifiedHere','runtimeAdmissionAuthorized','fullD3BAccepted','sqlWritesPerformed','connectionCreated','connectionClosed'):self.assertIs(receipt[key],False)
        self.assertIs(self.r['candidatePreopenGateRun'],False)
        self.assertIs(self.r['rootUsed'],False);self.assertIs(self.r['fullGatewayRun'],False)
        self.assertEqual((self.r['modelCalls'],self.r['providerCalls']),(0,0))
    def test_first_native_observation_not_rewritten(self):
        first=json.loads((E/'effects-stdout.txt').read_bytes());self.assertEqual(first['exitCode'],0)
        name='scripts/qa/p107a_constructor_effects.py'
        self.assertEqual(first['sources'][name],hashlib.sha256((E/'effects-before-marker-check.py.txt').read_bytes()).hexdigest())
        self.assertNotEqual(first['sources'][name],self.o['sources'][name])
        self.assertNotIn('packages/claw-hermes/gateway_constructor_metadata.py',first['sources'])

if __name__=='__main__':unittest.main()
