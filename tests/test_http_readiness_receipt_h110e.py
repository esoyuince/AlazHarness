"""Historical-source native storage/real aiohttp readiness acceptance receipts."""
from historical_sources_l113f6 import receipt_source_hash
import hashlib,json
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
E=ROOT/'evidence/d3b-http-readiness-h110e'
class NativeHttpReadinessReceipt(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.outer=json.loads((E/'native-003-stdout.txt').read_bytes())
        cls.proof=json.loads(cls.outer['stdout'])
        cls.events=cls.proof['events']
    def test_historical_sources_and_immutable_native_dependencies(self):
        self.assertEqual(json.loads((E/'native-003-result.json').read_text())['exitCode'],0)
        self.assertEqual(self.outer['exitCode'],0);self.assertIs(self.outer['temporaryRootRemoved'],True)
        self.assertIs(self.outer['sourcesUnchanged'],True)
        sources=json.loads((E/'native-003-intent.json').read_text())['sources']
        self.assertEqual(sources,self.proof['sourceSha256'])
        native=json.loads((ROOT/'evidence/d3b-native-stores-h105e/native-source-inventory.json').read_text())
        http=json.loads((E/'http-dependency-inventory.json').read_text())
        deps={n:h for item in http['packages'].values() for n,h in item['files'].items()}
        for n,h in sources.items():
            with self.subTest(source=n):
                if n.startswith(('packages/','scripts/')):self.assertEqual(receipt_source_hash(ROOT,n,h),h)
                elif n.startswith('vendor-native/'):self.assertEqual(native['nativeSources'][n.removeprefix('vendor-native/')]['sha256'],h)
                elif n.startswith('dependencies/'):self.assertEqual(native['dependency']['sourceSha256'][n.removeprefix('dependencies/')],h)
                elif n.startswith('http-dependencies/'):self.assertEqual(deps[n.removeprefix('http-dependencies/')],h)
                else:self.fail('unexpected source root')
        closed=next(e for e in self.events if e.get('state')=='CLOSED')
        for n,h in closed['sourceHashes'].items():self.assertEqual(sources[n],h)
        for name in ('vendor-native/hermes_state.py','vendor-native/gateway/platforms/api_server_run_idempotency.py','http-dependencies/aiohttp/web.py'):
            self.assertIn(name,closed['sourceHashes'])
    def test_preflight_failure_and_bind_conflict_are_not_ready(self):
        refuses={e['case']:e for e in self.events if e.get('state')=='EXPECTED_START_REFUSAL'}
        self.assertEqual(set(refuses),{'preopen-refusal','bind-conflict'})
        bad=refuses['preopen-refusal'];self.assertEqual(bad['audit']['nativeSqliteConnections'],0)
        self.assertIs(bad['storageBeforeClose']['epochMayHaveAdvanced'],False)
        self.assertIs(bad['httpBeforeClose']['listenerBindConfirmed'],False)
        conflict=refuses['bind-conflict'];self.assertIs(conflict['storageBeforeClose']['epochMayHaveAdvanced'],True)
        self.assertIs(conflict['httpBeforeClose']['listenerBindConfirmed'],False)
        for row in refuses.values():
            self.assertEqual(row['closed']['state'],'CLOSED');self.assertIs(row['nativeProfileReleased'],True)
        first=next(e for e in self.events if e.get('state')=='LISTENING')
        self.assertEqual(first['uid'],23001);self.assertEqual(first['storage']['state'],'VERIFIED')
        self.assertEqual(first['storage']['epochObserved'],1)
        self.assertEqual(first['http']['host'],'127.0.0.1');self.assertTrue(first['guard']['selfMountMetadata'])
    def test_actual_wire_auth_scope_and_monotonic_revocation(self):
        replies={e['httpCase']:e for e in self.events if 'httpCase' in e}
        expected={'missing-auth':401,'wrong-auth':401,'duplicate-auth':401,'bad-origin':400,'duplicate-host':400,
                  'agent-disabled':404,'query-refused':404,'encoded-refused':404,'post-refused':405,'body-refused':400,
                  'live':200,'ready':200,'stale-epoch':503,'restored-but-revoked':503}
        self.assertEqual({n:r['status'] for n,r in replies.items()},expected)
        self.assertIs(replies['ready']['body']['storageReady'],True)
        self.assertIs(replies['stale-epoch']['body']['storageReady'],False)
        self.assertIs(replies['restored-but-revoked']['body']['storageReady'],False)
        self.assertNotIn('storageReady',replies['live']['body'])
        for label,row in replies.items():
            if row['parserRefusal']:
                self.assertEqual(label,'duplicate-host');self.assertIsNone(row['body'])
            else:
                self.assertEqual(row['cache'],'no-store');self.assertIsNot(row['body'].get('runtimeAdmissionAuthorized'),True)
        ready=next(e for e in self.events if e.get('state')=='LISTENING')
        self.assertEqual(ready['storage']['completedChecks'],['preflight','before_epoch','after_epoch'])
    def test_http_stops_before_transaction_and_profile_are_released(self):
        stages=[e.get('state') for e in self.events]
        self.assertLess(stages.index('HTTP_CLOSED_STORES_RETAINED'),stages.index('CLOSED'))
        held=next(e for e in self.events if e.get('state')=='HTTP_CLOSED_STORES_RETAINED')
        self.assertTrue(held['transactionActive']);self.assertTrue(held['nativeLeaseHeld'])
        self.assertEqual(held['http']['state'],'HTTP_CLOSED');self.assertFalse(held['http']['httpCleanupPending'])
        closed=next(e for e in self.events if e.get('state')=='CLOSED')
        self.assertEqual(closed['http']['state'],'CLOSED');self.assertTrue(closed['nativeProfileReleased'])
        self.assertTrue(closed['sameNativeStoreObjects'])
        self.assertEqual(closed['audit'],{'nativeSqliteConnections':2,'httpPhaseSqliteConnections':0,'httpPhaseRawDatabaseOpens':0,'nonLoopbackAttempts':0})
        self.assertEqual(self.proof['result'],'PASS_NATIVE_STORAGE_READINESS_HTTP')
        self.assertEqual(self.proof['checkCount'],55);self.assertEqual(len(self.proof['checks']),55)
        self.assertTrue(all(v is True for v in self.proof['checks'].values()))
        for key in ('rootUsed','fullMountNetworkIsolationTested','realHermesHttpAdapterStarted','fullD3BAccepted'):
            self.assertIs(self.proof[key],False)
        self.assertEqual(self.proof['providerSends'],0);self.assertEqual(self.proof['paidCalls'],0)
    def test_first_failures_and_independent_current_http_proof_preserved(self):
        for run in ('001','002'):self.assertEqual(json.loads((E/('native-'+run+'-result.json')).read_text())['exitCode'],1)
        before=(E/'runtime-before-mime-configuration.py.txt').read_bytes()
        first=json.loads((E/'native-001-intent.json').read_text())['sources']
        self.assertEqual(hashlib.sha256(before).hexdigest(),first['packages/claw-hermes/gateway_http_readiness.py'])
        previous=json.loads((E/'native-002-intent.json').read_text())['sources']
        self.assertEqual(previous['packages/claw-hermes/gateway_http_readiness.py'],self.proof['sourceSha256']['packages/claw-hermes/gateway_http_readiness.py'])
        self.assertEqual(hashlib.sha256((E/'native-probe-before-parser-refusal.py.txt').read_bytes()).hexdigest(),previous['scripts/qa/h110e_native_readiness.py'])
        wire=json.loads((E/'wire-windows-current/result.json').read_text())
        self.assertEqual((wire['total'],wire['passed'],wire['failures'],wire['errors']),(29,29,0,0))
        self.assertTrue(wire['runtimeSourceUnchanged']);self.assertFalse(wire['nativeStorageTested'])
        self.assertEqual(wire['runtimeSha256'],self.proof['sourceSha256']['packages/claw-hermes/gateway_http_readiness.py'])
        self.assertEqual(wire['qaSha256'],hashlib.sha256((E/'independent-http-audit.py.txt').read_bytes()).hexdigest())
if __name__=='__main__':unittest.main()
