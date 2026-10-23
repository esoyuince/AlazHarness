"""Current actual three-store proof, distinct from earlier historical two-store proofs."""
from historical_startup_s124b1 import executed_source_hash
import hashlib,json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
E=ROOT/'evidence/d3b-response-lifecycle-l113f6'
class NativeThreeStoreReceipt(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.o=json.loads((E/'native-002-stdout.txt').read_bytes());cls.r=json.loads(cls.o['stdout'])
        cls.t={e['case']:json.loads(e['stdout']) for e in cls.r['events'] if e['mode']=='target' and e['exitCode']==0}
    def test_executed_sources_with_historical_http_projection_and_startup_snapshots(self):
        self.assertEqual(self.o['exitCode'],0);self.assertEqual(self.r['result'],'PASS_NATIVE_THREE_STORE_STARTUP');self.assertIsNone(self.r['error'])
        self.assertIs(self.o['sourcesUnchanged'],True);self.assertIs(self.o['temporaryRootRemoved'],True)
        self.assertEqual(self.o['sources'],self.r['sourceSha256'])
        self.assertEqual(self.o['sources'],json.loads((E/'native-002-intent.json').read_text(encoding='utf-8'))['sources'])
        native=json.loads((ROOT/'evidence/d3b-api-storage-a112x7d/patch-manifest.json').read_text(encoding='utf-8'))['nativeSources']
        deps=json.loads((ROOT/'evidence/d3b-native-stores-h105e/native-source-inventory.json').read_text(encoding='utf-8'))['dependency']['sourceSha256']
        for name,digest in self.o['sources'].items():
            with self.subTest(source=name):
                if name=='packages/claw-hermes/gateway_http_readiness.py':
                    old=ROOT/'evidence/d3b-three-readiness-h114r6'
                    baseline=json.loads((old/'baseline.json').read_text(encoding='utf-8'))
                    self.assertEqual(baseline['sources'][name],digest)
                    self.assertEqual(hashlib.sha256((old/'gateway_http_readiness.before.py.txt').read_bytes()).hexdigest(),digest)
                elif name=='packages/claw-hermes/gateway_state_projection.py':
                    from historical_sources_l113f6 import receipt_source_hash
                    self.assertEqual(receipt_source_hash(ROOT,name,digest),digest)
                elif name.startswith(('packages/','scripts/')):self.assertEqual(executed_source_hash(ROOT,name,digest),digest)
                elif name.startswith('vendor-native/'):self.assertEqual(native[name.removeprefix('vendor-native/')]['sha256'],digest)
                else:self.assertEqual(deps[name.removeprefix('dependencies/')],digest)
        for t in self.t.values():
            for name,digest in t['sourceHashes'].items():self.assertEqual(self.o['sources'][name],digest)
    def test_two_new_processes_preserve_response_and_advance_once(self):
        a,b=self.t['clean'],self.t['reopen'];self.assertNotEqual(a['pid'],b['pid']);self.assertEqual(a['inodes'],b['inodes'])
        self.assertEqual([t['startup']['epochObserved'] for t in (a,b)],[1,2])
        for t in (a,b):
            self.assertEqual(t['state'],'STARTUP_COMPLETE');self.assertEqual(len(t['audit']['connects']),3)
            self.assertEqual(t['audit']['helpers'],2);self.assertEqual(t['audit']['coldRawDatabaseOpens'],0)
            self.assertIs(t['checks']['constructor_no_changed_rows'],True);self.assertIs(t['checks']['response_bytes_unchanged'],True)
            self.assertIs(t['checks']['persistent_response_body'],True);self.assertIs(t['httpThirdStoreRefused'],True)
            self.assertEqual(t['closed']['state'],'CLOSED');self.assertIs(t['closed']['callerLeaseMayBeReleased'],True)
    def test_default_two_store_control_still_runs(self):
        t=self.t['two'];self.assertEqual(t['startup']['completedChecks'],['preflight','before_epoch','after_epoch'])
        self.assertFalse(t['startup']['responseConfigured']);self.assertEqual(len(t['audit']['connects']),2)
        self.assertEqual(t['audit']['helpers'],1);self.assertEqual(t['startup']['epochObserved'],1)
    def test_response_refusals_precede_any_parent_writable_open(self):
        expected={'schema':'response_preopen_schema_mismatch','unsettled':'response_preopen_unsettled_identity',
                  'pressure':'response_preopen_retention_pressure','sidecar':'response_preopen_recovery_required','mode':'native_layout_private_object'}
        for name,reason in expected.items():
            t=self.t[name];self.assertEqual(t['state'],'EXPECTED_START_REFUSAL');self.assertEqual(t['reason'],reason)
            self.assertEqual(t['audit']['connects'],[]);self.assertEqual(t['audit']['coldRawDatabaseOpens'],0)
            self.assertFalse(t['failure']['epochMayHaveAdvanced']);self.assertTrue(t['checks']['file_bytes_unchanged'])
    def test_later_pending_canonical_refusal_is_not_byte_purity_claim(self):
        t=self.t['canonical-pending'];self.assertEqual(t['reason'],'live_store_unresolved_admissions')
        self.assertEqual(len(t['audit']['connects']),2);self.assertFalse(t['failure']['epochMayHaveAdvanced'])
        detail=t['events'][0];self.assertEqual(detail['epochRowsBefore'],detail['epochRowsAfter'])
        self.assertEqual(detail['admissionRowsBefore'],detail['admissionRowsAfter'])
        self.assertFalse(detail['allCanonicalFileBytesUnchanged']);self.assertTrue(detail['logicalMetadataChanged'])
        for name in ('runs_idempotency.db','response_store.db'):self.assertEqual(detail['fileHashesBefore'][name],detail['fileHashesAfter'][name])
    def test_all_controls_and_scope_are_explicit(self):
        self.assertEqual(set(self.t),{'clean','reopen','two','schema','unsettled','pressure','sidecar','mode','canonical-pending'})
        self.assertEqual(sum(t['checkCount'] for t in self.t.values()),83)
        for t in self.t.values():
            self.assertEqual(len(t['checks']),t['checkCount']);self.assertTrue(all(v is True for v in t['checks'].values()))
            self.assertIs(t['nativeClassesMocked'],False);self.assertIs(t['fullConfinementTested'],False);self.assertEqual(t['providerCalls'],0)
        for key in ('rootUsed','mountChanged','fullConfinementTested','runtimePinActivated','httpListenerStarted'):self.assertIs(self.r[key],False)
        self.assertEqual(self.r['providerCalls'],0)
    def test_first_failure_and_blocked_optional_refinement_retained(self):
        old=json.loads((E/'native-001-stdout.txt').read_bytes());r=json.loads(old['stdout'])
        self.assertEqual(old['exitCode'],1);self.assertEqual(r['result'],'FAIL');self.assertIn('file_bytes_unchanged',r['error']['reason'])
        self.assertEqual(old['sources']['packages/claw-hermes/gateway_store_startup.py'],self.o['sources']['packages/claw-hermes/gateway_store_startup.py'])
        self.assertNotEqual(old['sources']['scripts/qa/l113f6_native_startup.py'],self.o['sources']['scripts/qa/l113f6_native_startup.py'])
        blocked=json.loads((E/'blocked-refinement.json').read_text(encoding='utf-8'));self.assertTrue(blocked['notRetriedViaAnyOtherToolOrEncoding'])
        self.assertTrue(blocked['native003DoesNotExist']);self.assertFalse((E/'native-003-intent.json').exists())

if __name__=='__main__':unittest.main()
