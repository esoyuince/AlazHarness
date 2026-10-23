"""Current actual native receipts; no new native execution or safety-block retry."""
import hashlib,json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
E=ROOT/'evidence/d3b-canonical-binding-c119v1'
class CanonicalReceipt(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r=json.loads((E/'native-002/result.json').read_text(encoding='utf-8'))
        cls.c=json.loads((E/'source-custody.json').read_text(encoding='utf-8'))
    def test_terminal_complete_current27_cases(self):
        r=self.r;self.assertEqual(r['result'],'PASS_SCOPED_CANONICAL_CORRELATION')
        self.assertEqual((r['total'],r['passed'],r['errors'],r['failures'],r['skipped']),(27,27,0,0,0))
        self.assertEqual(json.loads((E/'native-002-terminal.json').read_text()),{'exitCode':0,'sourcesUnchanged':True})
        lines=[l for l in (E/'native-002/tests.txt').read_text(encoding='utf-8').splitlines() if l.startswith('test_') and l.endswith(' ... ok')]
        self.assertEqual(len(lines),27)
    def test_exact_source_and_immutable_native_imports(self):
        self.assertEqual(self.c['resultSha256'],hashlib.sha256((E/'native-002/result.json').read_bytes()).hexdigest())
        self.assertEqual(self.r['sourceHashes'],json.loads((E/'native-002-intent.json').read_text(encoding='utf-8'))['sources'])
        for n,h in self.r['sourceHashes'].items():self.assertEqual(hashlib.sha256((ROOT/n).read_bytes()).hexdigest(),h)
        self.assertEqual(self.c['nativeFeature'],'943210584828ccfcfd6adc8eb966ecaa8ca18429')
        self.assertEqual({n:v['sha256'] for n,v in self.c['actualImportedNativeFiles'].items()},self.r['nativeImports'])
        self.assertEqual(self.c['nativeImportCount'],len(self.r['nativeImports']))
        for n in ('gateway/session_authority.py','gateway/session_api_turn.py','gateway/session_runtime_workers.py','gateway/platforms/api_server_run_observation.py'):
            self.assertIn(n,self.r['nativeImports'])
    def test_actual_api_cancel_leaves_canonical_claim_until_settlement(self):
        rows=[v['result'] for v in self.r['observations'] if v['case']=='test_cancelled_api_waiter_does_not_cancel_actual_authority_task']
        self.assertEqual([r['phase'] for r in rows],['CLAIMED','CLAIMED','SETTLED'])
        self.assertFalse(rows[0]['carrierCancelled']);self.assertTrue(rows[1]['carrierCancelled'])
        self.assertTrue(rows[1]['authorityTaskLive']);self.assertFalse(rows[-1]['authorityTaskLive'])
        for r in rows:
            for k in ('physicalWorkerHealthVerified','allAgentWorkObserved','storageProfileMountVerified','serviceReadinessVerified','runtimeAdmissionAuthorized','retryAuthorized','storeReleaseAuthorized','admissionPayloadDigestVerified'):
                self.assertIs(r[k],False)
    def test_no_observer_opens_writes_or_unreported_network_effect(self):
        self.assertEqual(self.r['audit']['connects'],0);self.assertEqual(self.r['audit']['dbopens'],0)
        self.assertEqual(self.r['audit']['network'],len(self.r['audit']['deniedNetworkEvents']))
        for event in self.r['audit']['deniedNetworkEvents']:
            self.assertEqual(event['event'],'socket.bind');self.assertEqual(event['target'],"('::1', 0)")
            self.assertEqual(event['frames'][-1]['function'],'_has_ipv6')
        for event in self.r['observations']:self.assertEqual(event['databaseWrites'],0);self.assertEqual(event['newDatabaseConnections'],0)
        self.assertTrue(self.r['ownershipReleased']);self.assertTrue(self.r['temporaryImportHomeRemoved'])
        self.assertEqual(self.r['registry'],{'live_generations':0,'retired_generations':0,'total_refcounts':0})
    def test_test_boundary_and_original_controls_remain_explicit(self):
        for k in ('runnerFacadeAndComputeDoubled','adoptionCallSiteIsComputeDouble'):self.assertTrue(self.r[k])
        for k in ('nativeAdmissionClaimTaskMapsDoubled','nativeAdoptionMethodDoubled','httpListenerStarted','fullGatewayTurnRunnerTested','kernelIsolationTested','borrowedRunnerGuardRelaxed','rootOrWslAction'):self.assertFalse(self.r[k])
        self.assertEqual(self.r['providerCalls'],0)
        control=json.loads((E/'native-002/provisioned-schemas.json').read_text(encoding='utf-8'))
        self.assertTrue(control['separateControlClosedBeforeCases']);self.assertEqual(control['schemaHashes'],self.r['schemaPins'])
        base=json.loads((E/'baseline.json').read_text(encoding='utf-8'))['sources'];self.assertEqual(len(base),483)
        for n,h in base.items():self.assertEqual(hashlib.sha256((ROOT/n).read_bytes()).hexdigest(),h,n)
    def test_historical24_and_actual_exponent_failure_not_relabelled(self):
        old=json.loads((E/'native-001/result.json').read_text(encoding='utf-8'));self.assertEqual(old['total'],24)
        for n,h in old['sourceHashes'].items():
            self.assertEqual(hashlib.sha256((E/('native001-executed-'+Path(n).name+'.txt')).read_bytes()).hexdigest(),h)
        self.assertNotEqual(old['sourceHashes'],self.r['sourceHashes'])
        failure=(E/'exponent-regression-before.txt').read_text(encoding='utf-8')
        self.assertIn('FAIL: test_nonfinite_exponent_refused',failure);self.assertIn('FAILED (failures=1)',failure)
if __name__=='__main__':unittest.main()
