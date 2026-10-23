"""Current H114R6 native three-store HTTP receipt; no execution by these checks."""
from historical_startup_s124b1 import executed_source_hash
import hashlib,json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
E=ROOT/'evidence/d3b-three-readiness-h114r6'
class ThreeHttpProof(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.o=json.loads((E/'native-001-stdout.txt').read_bytes());cls.r=json.loads(cls.o['stdout'])
        cls.events=cls.r['events'];cls.listen=[e for e in cls.events if e.get('state')=='LISTENING']
        cls.closed=[e for e in cls.events if e.get('state')=='CLOSED']
    def test_success_executed_sources_with_historical_startup_and_exact_transport(self):
        self.assertEqual(self.o['exitCode'],0);self.assertEqual(self.r['result'],'PASS_NATIVE_THREE_STORE_READINESS_HTTP');self.assertIsNone(self.r['error'])
        self.assertIs(self.o['sourcesUnchanged'],True);self.assertIs(self.o['temporaryRootRemoved'],True)
        self.assertEqual(self.o['sources'],self.r['sourceSha256'])
        self.assertEqual(self.o['sources'],json.loads((E/'native-001-intent.json').read_text(encoding='utf-8'))['sources'])
        expected_native=json.loads((ROOT/'evidence/d3b-api-storage-a112x7d/patch-manifest.json').read_text(encoding='utf-8'))['nativeSources']
        deps=json.loads((ROOT/'evidence/d3b-native-stores-h105e/native-source-inventory.json').read_text(encoding='utf-8'))['dependency']['sourceSha256']
        http={n:h for v in json.loads((ROOT/'evidence/d3b-http-qa-r110x6c2/http-dependency-custody.json').read_text(encoding='utf-8'))['packages'].values() for n,h in v['files'].items()}
        for event in self.closed:
            for n,h in event['sourceHashes'].items():
                self.assertEqual(self.o['sources'][n],h)
                if n.startswith(('packages/','scripts/')):self.assertEqual(executed_source_hash(ROOT,n,h),h)
                elif n.startswith('vendor-native/'):self.assertEqual(expected_native[n.removeprefix('vendor-native/')]['sha256'],h)
                elif n.startswith('http-dependencies/'):self.assertEqual(http[n.removeprefix('http-dependencies/')],h)
                else:self.assertEqual(deps[n.removeprefix('dependencies/')],h)
        name='scripts/qa/h114r6_native_readiness.py'
        self.assertEqual(hashlib.sha256((ROOT/name).read_bytes()).hexdigest(),self.o['sources'][name])
    def test_three_actual_connections_and_same_profile_reopen(self):
        self.assertEqual(len(self.listen),2);self.assertEqual(len(self.closed),2)
        self.assertNotEqual(self.listen[0]['pid'],self.listen[1]['pid'])
        self.assertEqual([e['storage']['epochObserved'] for e in self.listen],[1,2])
        self.assertEqual(self.closed[0]['inodes'],self.closed[1]['inodes'])
        self.assertEqual(set(self.closed[0]['inodes']),{'state.db','runs_idempotency.db','response_store.db'})
        for e in self.listen:
            self.assertEqual(e['http']['scope'],'native_three_store_quiescent_readiness_only')
            self.assertEqual(e['http']['configuredStoreCount'],3);self.assertFalse(e['http']['healthyBusyWorkPolicy'])
            self.assertTrue(e['guard']['selfMountMetadata']);self.assertEqual(e['guard']['metadataReadFileCount'],6)
        for e in self.closed:
            self.assertEqual(e['audit'],{'nativeSqliteConnections':3,'httpPhaseSqliteConnections':0,'httpPhaseRawDatabaseOpens':0,'nonLoopbackAttempts':0})
            self.assertTrue(e['sameNativeStoreObjects']);self.assertTrue(e['responseBodyPreserved']);self.assertTrue(e['nativeProfileReleased'])
    def test_only_response_drift_revokes_and_restore_stays_revoked(self):
        observations=[e for e in self.events if 'httpCase' in e]
        for label,status in (('ready',200),('unsettled-response',503),('restored-but-revoked',503)):
            selected=[e for e in observations if e['httpCase']==label];self.assertEqual(len(selected),2)
            for e in selected:
                self.assertEqual(e['status'],status);self.assertEqual(e['body']['storageReady'],status==200)
                self.assertFalse(e['body']['runtimeAdmissionAuthorized']);self.assertFalse(e['body']['agentRoutesEnabled'])
        self.assertEqual(len([e for e in self.events if e.get('state')=='RESPONSE_PENDING_BY_QA' and e['unsettled']==1]),2)
        self.assertEqual(len([e for e in self.events if e.get('state')=='RESPONSE_RESTORED_BY_QA' and e['readinessRemainsRevoked']]),2)
    def test_response_preopen_and_bind_failure_are_not_zero_effect_confused(self):
        failures={e['case']:e for e in self.events if e.get('state')=='EXPECTED_START_REFUSAL'}
        a,b=failures['preopen-refusal'],failures['bind-conflict']
        self.assertEqual(a['audit']['nativeSqliteConnections'],0);self.assertFalse(a['storageBeforeClose']['epochMayHaveAdvanced'])
        self.assertEqual(b['audit']['nativeSqliteConnections'],3);self.assertTrue(b['storageBeforeClose']['epochMayHaveAdvanced'])
        for e in failures.values():self.assertEqual(e['closed']['state'],'CLOSED');self.assertTrue(e['nativeProfileReleased'])
    def test_http_drain_precedes_response_transaction_settlement(self):
        blocked=[(i,e) for i,e in enumerate(self.events) if e.get('state')=='HTTP_CLOSED_STORES_RETAINED']
        done=[i for i,e in enumerate(self.events) if e.get('state')=='CLOSED'];self.assertEqual(len(blocked),2)
        for (i,e),j in zip(blocked,done):
            self.assertLess(i,j);self.assertEqual(e['http']['state'],'HTTP_CLOSED');self.assertTrue(e['transactionActive']);self.assertTrue(e['nativeLeaseHeld'])
        for case in ('normal','reopen'):
            self.assertTrue(self.r['checks'][case+'::http_closed_before_native_transaction_settlement'])
    def test_scope_counts_no_agent_api_or_full_namespace_claim(self):
        self.assertEqual(self.r['checkCount'],94);self.assertEqual(len(self.r['checks']),94);self.assertTrue(all(v is True for v in self.r['checks'].values()))
        for k in ('rootUsed','fullMountNetworkIsolationTested','realHermesHttpAdapterStarted','runtimeFeatureInstalled','healthyBusyWorkPolicy','fullD3BAccepted'):
            self.assertIs(self.r[k],False)
        self.assertTrue(self.r['readinessHttpActuallyServed']);self.assertEqual(self.r['paidCalls'],0);self.assertEqual(self.r['providerSends'],0)
        self.assertFalse(any(e.get('ownedForcedCleanup') for e in self.events))

if __name__=='__main__':unittest.main()
