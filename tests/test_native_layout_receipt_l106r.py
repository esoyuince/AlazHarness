"""Actual L106R historical-source native layout/restart proof, not full admission."""
from historical_sources_l113f6 import receipt_source_hash
import hashlib
import json
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
E=ROOT/'evidence/d3b-native-layout-l106r'
class NativeLayoutReceipt(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.o=json.loads((E/'native-002-stdout.txt').read_bytes())
        cls.r=json.loads(cls.o['nativeStdout'])
        cls.targets=[x for x in cls.r['events'] if x.get('state')=='RESULT']
        cls.phases={x['phase']:x for x in cls.r['events'] if 'phase' in x}
    def test_terminal_native_checks_and_framed_provenance(self):
        self.assertEqual(json.loads((E/'native-002-result.json').read_text())['exitCode'],0)
        self.assertEqual([u['exitCode'] for u in self.o['units']],[0,0])
        self.assertEqual(self.o['nativeExitCode'],0);self.assertEqual(self.o['nativeStderr'],'')
        self.assertIs(self.o['sourcesUnchanged'],True)
        self.assertEqual(self.r['result'],'PASS_SCOPED_NATIVE_STORE_LAYOUT')
        self.assertIsNone(self.r['error']);self.assertIs(self.r['forcedCleanup'],False)
        self.assertEqual((self.r['checkCount'],len(self.r['checks'])),(42,42))
        self.assertTrue(all(v is True for v in self.r['checks'].values()))
        self.assertEqual([t['mode'] for t in self.targets],['write','read'])
        self.assertEqual([t['checkCount'] for t in self.targets],[24,27])
        for t in self.targets:
            self.assertTrue(all(v is True for v in t['checks'].values()))
            self.assertEqual(t['sourceCount'],len(t['nativeSources']))
            self.assertTrue(0<t['sourceChunks']<=16)
            raw=json.dumps(t['nativeSources'],sort_keys=True,separators=(',',':')).encode()
            self.assertEqual(hashlib.sha256(raw).hexdigest(),t['sourceDigest'])
    def test_exact_historical_sources_and_pinned_native_files(self):
        manifest=json.loads((E/'native-002-source-manifest.json').read_text())
        self.assertEqual(manifest,self.o['sources']);self.assertEqual(manifest,self.r['sourceSha256'])
        native=json.loads((ROOT/'evidence/d3b-native-stores-h105e/native-source-inventory.json').read_text())
        for name,want in manifest.items():
            with self.subTest(source=name):
                if name.startswith(('packages/','scripts/','tests/','evidence/')):
                    self.assertEqual(receipt_source_hash(ROOT,name,want),want)
                elif name.startswith('vendor-native/'):
                    self.assertEqual(native['nativeSources'][name[len('vendor-native/'):]]['sha256'],want)
                else:
                    self.assertTrue(name.startswith('dependencies/'))
                    self.assertEqual(native['dependency']['sourceSha256'][name[len('dependencies/'):]],want)
        for t in self.targets:
            for n,h in t['nativeSources'].items():self.assertEqual(manifest[n],h)
            for n in ('hermes_state.py','hermes_state_runtime.py','gateway/platforms/api_server_run_idempotency.py','gateway/runtime_ownership.py'):
                self.assertIn('vendor-native/'+n,t['nativeSources'])
    def test_true_native_epoch_recovery_after_complete_detach(self):
        first,second=self.targets
        self.assertEqual((first['epoch'],first['stateStatus'],first['recovered']),(1,'started',0))
        self.assertEqual((second['epoch'],second['stateStatus'],second['recovered']),(2,'unknown',1))
        self.assertNotEqual(first['pid'],second['pid'])
        for name in ('state.db','runs_idempotency.db'):
            self.assertEqual(first['stores'][name]['rows'],second['stores'][name]['rows'])
            self.assertEqual(first['stores'][name]['inode'],second['stores'][name]['inode'])
            self.assertIs(second['stores'][name]['duplicateRefused'],True)
        for key in ('unknown_not_replayed','stale_epoch_refused','duplicate_native_request_reused'):
            self.assertIs(second['checks'][key],True)
        for mode in ('write','read'):
            self.assertTrue(all(self.phases[mode+'-closed'][k] is True for k in ('ownedUsersGone','loopAttachmentGone','fenceRemovedAfterCleanup','leaseReleasedLast')))
    def test_final_identity_guard_and_no_database_open_by_layout(self):
        for t in self.targets:
            self.assertEqual(t['pid'],t['receipt']['pid'])
            self.assertEqual(t['receipt']['profileLayout'],'hermes-native-stores-cold-v1')
            after=t['receipt']['afterDrop']
            self.assertEqual(after['uids'],[23001]*4);self.assertEqual(after['gids'],[23003]*4)
            self.assertEqual(after['groups'],[]);self.assertTrue(all(c==0 for c in after['caps'].values()))
            self.assertEqual(t['auxiliaryOpensWhileDbTransaction'],['/run/alaz-state/profile/SOUL.md','/run/alaz-state/profile/cache/schema_columns.json'])
            for key in ('layout_preserves_active_sql_transaction','no_raw_database_or_lock_open',
                        'native_connections_are_real_disk','native_aux_inventory_survives_open_close',
                        'private_namespace_preserved','other_host_endpoints_denied','host_paths_private_state_hidden',
                        'canary_read_write_denied','inherited_fd_closed','live_writer_retains_profile'):
                self.assertIs(t['checks'][key],True)
    def test_real_native_owner_contention_and_last_user_drain(self):
        for t in self.targets:
            mode=t['mode'];refused=self.phases[mode+'-native-contender']
            self.assertEqual(refused['exitCode'],77);self.assertEqual(refused['proof']['reason'],'profile_already_owned')
            self.assertIs(refused['proof']['lockUnchanged'],True)
            released=self.phases[mode+'-profile-released'];accepted=self.phases[mode+'-native-after-release']
            self.assertEqual(accepted['exitCode'],0);self.assertEqual(accepted['proof']['inode'],released['lockInode'])
            self.assertEqual(released['pid'],t['pid'])
            self.assertIs(self.r['checks'][mode+'_image_retained_after_profile_release'],True)
    def test_minimal_defaults_and_claim_limits(self):
        negatives={x['negative']:x for x in self.r['events'] if 'negative' in x}
        self.assertEqual(negatives['minimal_layout']['exitCode'],2)
        self.assertEqual(negatives['minimal_layout']['diagnostic']['reason'],'state_projection_profile_inventory')
        self.assertIs(negatives['default_metadata']['diagnostic']['mountinfoDenied'],True)
        self.assertIs(self.r['nativeStoreLayoutTested'],True);self.assertIs(self.r['epochRecoveryTested'],True)
        for k in ('nativeHermesGatewayStarted','fullAdmissionGateImplemented','legacyIpcV2Enabled','fullD3BAccepted'):self.assertIs(self.r[k],False)
        for t in self.targets:
            self.assertIs(t['realHermesGateway'],False);self.assertIs(t['fullAdmissionGateImplemented'],False)
            self.assertEqual(t['providerSends'],0)
        self.assertEqual(self.r['paidModelCalls'],0)
        self.assertIs(self.r['checks']['zero_physical_provider_attempts'],True)
    def test_first_failure_and_historical_snapshots_cleanup_retained(self):
        first=json.loads(json.loads((E/'native-001-stdout.txt').read_bytes())['nativeStdout'])
        self.assertEqual(first['result'],'FAIL');self.assertEqual(first['error']['reason'],'supervisor_worker_output_bound')
        correction=json.loads((E/'qa-source-framing-correction.json').read_text())
        self.assertIs(correction['productionSupervisorLimitUnchanged'],True);self.assertIs(correction['productSourcesUnchanged'],True)
        old=json.loads((E/'historical-source-custody.json').read_text())
        self.assertEqual(hashlib.sha256((E/old['snapshot']).read_bytes()).hexdigest(),old['sourceSha256'])
        self.assertNotEqual(old['sourceSha256'],self.o['sources'][old['sourcePath']])
        cleanup=json.loads((E/'cleanup.json').read_text())
        self.assertEqual(cleanup['exitCode'],0);self.assertIs(cleanup['audit']['ownClean'],True)
        self.assertEqual(cleanup['audit']['ownLivePids'],[])
        self.assertEqual(len(cleanup['audit']['images']),2)
        for image in cleanup['audit']['images']:
            self.assertEqual(image['loops'],[]);self.assertIs(image['mountTargetsEmpty'],True)
            self.assertIs(image['fence'],False);self.assertIs(image['socket'],False)

if __name__=='__main__':unittest.main()
