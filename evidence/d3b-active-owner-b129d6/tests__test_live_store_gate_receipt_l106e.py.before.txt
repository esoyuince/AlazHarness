"""Current-source native L106E connection gate proof, not a new execution."""
import hashlib
import json
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
E=ROOT/'evidence/d3b-native-layout-l106e'
class NativeLiveGateReceipt(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.o=json.loads((E/'native-003-stdout.txt').read_bytes())
        cls.r=json.loads(cls.o['stdout'])
        cls.check=next(e for e in cls.r['events'] if e.get('state')=='CHECKED')
    def test_native_execution_matches_current_product_and_immutable_upstream(self):
        self.assertEqual(json.loads((E/'native-003-result.json').read_text())['exitCode'],0)
        self.assertEqual(self.o['exitCode'],0)
        self.assertIs(self.o['sourcesUnchanged'],True)
        self.assertIs(self.o['temporaryRootRemoved'],True)
        intent=json.loads((E/'native-003-intent.json').read_text())
        self.assertEqual(self.r['sourceSha256'],intent['sourceSha256'])
        inv=json.loads((ROOT/'evidence/d3b-native-stores-h105e/native-source-inventory.json').read_text())
        for name,digest in self.r['sourceSha256'].items():
            with self.subTest(source=name):
                if name.startswith(('packages/','scripts/')):
                    self.assertEqual(hashlib.sha256((ROOT/name).read_bytes()).hexdigest(),digest)
                elif name.startswith('vendor-native/'):
                    self.assertEqual(inv['nativeSources'][name.removeprefix('vendor-native/')]['sha256'],digest)
                elif name.startswith('dependencies/'):
                    self.assertEqual(inv['dependency']['sourceSha256'][name.removeprefix('dependencies/')],digest)
                else:self.fail('unexpected source root')
        for name,digest in self.check['sourceHashes'].items():self.assertEqual(digest,intent['sourceSha256'][name])
        self.assertEqual(self.check['nativeClasses'],['hermes_state.SessionDB','gateway.platforms.api_server_run_idempotency.RunIdempotencyStore'])
        self.assertEqual(self.check['nativeConnections'],['hermes_cli.sqlite_safe_read.TrackedConnection','sqlite3.Connection'])
    def test_live_profile_guard_and_bounded_native_result(self):
        self.assertEqual(self.r['result'],'PASS_LIVE_NATIVE_CONNECTION_GATE')
        self.assertIsNone(self.r['error']);self.assertEqual(len(self.r['checks']),8)
        self.assertTrue(all(v is True for v in self.r['checks'].values()))
        self.assertEqual(self.check['checkCount'],37);self.assertEqual(len(self.check['checks']),37)
        self.assertTrue(all(v is True for v in self.check['checks'].values()))
        self.assertIs(self.check['guardReceipt']['selfMountMetadata'],True)
        self.assertEqual(self.check['guardReceipt']['metadataReadFileCount'],6)
        for receipt in self.check['gateReceipts']:
            self.assertEqual(receipt['state'],'NATIVE_STORE_CONNECTIONS_VERIFIED')
            for key in ('sqlWritesPerformed','rawDatabaseFilesOpened','connectionsClosed',
                        'sqliteHandleInodeProven','writeCapabilityProven','preConstructorValidationPerformed',
                        'pairedRecoveryVerified','runtimeAdmissionAuthorized','fullD3BAccepted'):
                self.assertIs(receipt[key],False)
        self.assertEqual([r['epochObserved'] for r in self.check['gateReceipts']],[0,1,1])
    def test_exclusive_sqlite_lock_survives_gate_and_releases_only_after_close(self):
        events=self.r['events'];phases={e['phase']:e for e in events if 'phase' in e}
        for name in ('before-gate','after-gate'):
            self.assertEqual(phases[name]['exitCode'],0)
            self.assertEqual(phases[name]['proof'],{'state':'BUSY','sqliteCode':5})
        self.assertEqual(phases['after-close']['proof'],{'state':'ACQUIRED_AND_ROLLED_BACK'})
        close=next(i for i,e in enumerate(events) if e.get('state')=='STORES_AND_PROFILE_CLOSED')
        reclaimed=next(i for i,e in enumerate(events) if e.get('phase')=='after-close')
        checked=next(i for i,e in enumerate(events) if e.get('state')=='CHECKED')
        self.assertLess(checked,close);self.assertLess(close,reclaimed)
        self.assertIs(events[close]['nativeProfileReleased'],True)
        self.assertEqual(events[close]['pid'],self.check['pid'])
        self.assertEqual(phases['final-child']['exitCode'],0)
        self.assertEqual(self.check['audit'],{'checking':False,'rawDatabaseOpens':0,'newSqliteConnections':0})
        self.assertTrue(all(q.lstrip().startswith(('SELECT ','PRAGMA ')) for q in self.check['queries']))
    def test_ten_native_refusals_no_silent_repair(self):
        self.assertEqual(self.check['denials'],{
            'wrong_schema':'live_store_schema_mismatch','wrong_expected_epoch':'live_store_epoch_mismatch',
            'volatile_refused':'live_store_volatile_replay','weak_sync_refused':'live_store_synchronous',
            'queryonly_refused':'live_store_query_only_connection','active_transaction_refused':'live_store_transaction_active',
            'running_replay_refused':'live_store_unresolved_replay','temp_replay_shadow_refused':'live_store_unresolved_replay','duplicate_json_refused':'live_store_unresolved_replay',
            'queued_admission_refused':'live_store_unresolved_admissions'})
        for key in ('rejection_does_not_rollback','rejected_replay_retained','rejection_does_not_cancel_admission','native_parser_sees_last_running_status','temp_version_does_not_override_main'):
            self.assertIs(self.check['checks'][key],True)
        for key in ('rootUsed','mountsChanged','fullProjectionTested','preConstructorGateImplemented',
                    'nativeProductModified','realGatewayStarted','fullD3BAccepted'):
            self.assertIs(self.r[key],False)
        self.assertEqual(self.r['providerCalls'],0)
    def test_first_source_and_failed_json_regression_not_rewritten(self):
        first=json.loads((E/'native-001-stdout.txt').read_bytes())
        self.assertEqual(first['exitCode'],0)
        name='packages/claw-hermes/gateway_live_store_gate.py'
        oldhash=hashlib.sha256((E/'gate-before-json-hardening.py.txt').read_bytes()).hexdigest()
        self.assertEqual(first['sourceSha256'][name],oldhash)
        self.assertNotEqual(self.r['sourceSha256'][name],oldhash)
        raw=(E/'unit-replay-json-before.txt').read_text()
        self.assertIn('FAIL: test_duplicate_status_key_is_not_a_terminal_decision',raw)
        self.assertIn('FAILED (failures=1)',raw)
        scope=json.loads((E/'scope-selection.json').read_text())
        self.assertIs(scope['candidateExecuted'],False);self.assertIs(scope['otherWorkModified'],False)

if __name__=='__main__':unittest.main()
