from historical_self_identity_r150a1 import source_path
"""Historical F104X proof; changed projection is pinned to its original bytes."""
import hashlib
import json
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
E=ROOT/'evidence/d3b-profile-admission-f104x'

class NativeProfileAdmissionReceipt(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.outer=json.loads((E/'native-002-stdout.txt').read_bytes())
        cls.r=json.loads(cls.outer['nativeStdout'])
        cls.targets=[row for row in cls.r['events'] if row.get('state')=='RESULT']
        cls.phases={row['phase']:row for row in cls.r['events'] if 'phase' in row}
    def test_terminal_outcomes_and_original_transport(self):
        self.assertEqual(json.loads((E/'native-002-result.json').read_text())['exitCode'],0)
        self.assertEqual((self.outer['unitExitCode'],self.outer['nativeExitCode']),(0,0))
        self.assertEqual(self.outer['nativeStderr'],'');self.assertIs(self.outer['sourceUnchanged'],True)
        self.assertEqual(self.r['result'],'PASS_SCOPED_NATIVE_PROFILE_ADMISSION')
        self.assertEqual((self.r['checkCount'],len(self.r['checks'])),(41,41))
        self.assertTrue(all(v is True for v in self.r['checks'].values()))
        self.assertIsNone(self.r['error']);self.assertIs(self.r['forcedCleanup'],False)
        manifest=json.loads((E/'native-002-manifest.json').read_text())
        self.assertEqual(manifest,self.outer['sourceHashes']);self.assertEqual(manifest,self.r['sourceSha256'])
        for name,want in manifest.items():
            if name.startswith(('packages/','scripts/','tests/')):
                with self.subTest(source=name):
                    source=(ROOT/'evidence/d3b-native-layout-l106r/gateway_state_projection.before.py.txt'
                            if name=='packages/claw-hermes/gateway_state_projection.py' else source_path(ROOT,name,want))
                    self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(),want)
    def test_exact_native_dependency_pin_and_each_target_imports(self):
        prior=json.loads((ROOT/'evidence/d3b-profile-lease-l99d/native-dependency-inventory.json').read_text())
        self.assertEqual(self.outer['nativePin'],prior['pin'])
        expected={'vendor-native/'+n:h for n,h in prior['nativeSources'].items()}
        expected.update({'dependencies/'+n:h for n,h in prior['dependency']['sourceSha256'].items()})
        for name,want in expected.items():self.assertEqual(self.outer['sourceHashes'][name],want)
        self.assertEqual([t['mode'] for t in self.targets],['write','read'])
        self.assertNotEqual(self.targets[0]['pid'],self.targets[1]['pid'])
        for target in self.targets:
            imported=target['nativeSources']
            for name in ('vendor-native/gateway/runtime_ownership.py','vendor-native/gateway/status.py',
                         'packages/claw-hermes/gateway_profile_lease.py','packages/claw-hermes/gateway_storage_mounts.py'):
                self.assertIn(name,imported)
            for name,digest in imported.items():self.assertEqual(digest,self.outer['sourceHashes'][name])
    def test_optin_is_one_read_file_and_default_remains_denied(self):
        default=[e for e in self.r['events'] if e.get('negative')=='default_metadata']
        self.assertEqual(len(default),1);d=default[0]
        self.assertEqual(d['exitCode'],0)
        for key in ('mountinfoDenied','nativeLeaseRefused','lockUnchanged'):self.assertIs(d['diagnostic'][key],True)
        for target in self.targets:
            meta=target['receipt']['filesystem']
            self.assertIs(meta['selfMountMetadata'],True);self.assertEqual(meta['metadataReadFileCount'],6)
            self.assertEqual(len(target['metadataDenials']),6)
            self.assertEqual(set(target['metadataDenials'].values()),{13})
            self.assertIs(target['checks']['foreign_process_mountinfo_hidden'],True)
        audit=json.loads((E/'independent-rule-audit.json').read_text())
        self.assertEqual(audit['exitCode'],0);self.assertIs(audit['sourceUnchanged'],True)
        self.assertEqual(audit['candidateSha256'],self.outer['sourceHashes']['packages/claw-hermes/credential_guard.py'])
    def test_profile_ownership_occurs_after_final_uid_and_exec(self):
        for target in self.targets:
            self.assertEqual(target['pid'],target['receipt']['pid'])
            state=target['receipt']['afterDrop']
            self.assertEqual(state['uids'],[23001]*4);self.assertEqual(state['gids'],[23003]*4)
            self.assertEqual(state['groups'],[]);self.assertTrue(all(v==0 for v in state['caps'].values()))
            self.assertEqual((target['checkCount'],len(target['checks'])),(38,38))
            self.assertTrue(all(v is True for v in target['checks'].values()))
            self.assertIs(target['nativeProfileLease'],True)
            # Projection precedes exec; its receipt must not retrospectively
            # claim ownership that the target acquired later.
            self.assertIs(target['receipt']['profileOwnershipAcquired'],False)
            for key in ('native_lease_after_final_exec','unchanged_native_mount_observer_ran',
                        'observer_did_not_open_database_contents','reservation_did_not_mutate_databases',
                        'native_held_fd_is_not_inheritable','native_owner_record_has_final_pid',
                        'registered_live_writer_keeps_native_lease','lease_still_held'):
                self.assertIs(target['checks'][key],True)
    def test_real_contenders_and_volume_retention_after_profile_release(self):
        for target in self.targets:
            mode=target['mode'];refused=self.phases[mode+'-native-contender']
            self.assertEqual(refused['exitCode'],77)
            self.assertEqual(refused['proof']['reason'],'profile_already_owned')
            self.assertIs(refused['proof']['lockUnchanged'],True)
            released=self.phases[mode+'-profile-released']
            self.assertEqual(released['state'],'PROFILE_RELEASED_PROCESS_ALIVE')
            self.assertEqual(released['pid'],target['pid'])
            acquired=self.phases[mode+'-native-after-release']
            self.assertEqual(acquired['exitCode'],0)
            self.assertEqual(acquired['proof']['state'],'ACQUIRED_THEN_RELEASED')
            self.assertEqual(acquired['proof']['inode'],target['lockInode'])
            self.assertEqual(released['lockInode'],target['lockInode'])
            self.assertEqual(len({target['pid'],refused['proof']['pid'],acquired['proof']['pid']}),3)
            self.assertIs(self.r['checks'][mode+'_image_retained_after_profile_release'],True)
            closed=self.phases[mode+'-closed']
            self.assertTrue(all(closed[k] is True for k in ('ownedUsersGone','loopAttachmentGone','fenceRemovedAfterCleanup','leaseReleasedLast')))
    def test_dummy_store_persistence_and_bounded_claims(self):
        a,b=self.targets
        for name in ('state.db','runs_idempotency.db'):
            self.assertEqual(a['stores'][name]['rows'],[['p102-run','persisted-in-confinement']])
            self.assertEqual(a['stores'][name]['rows'],b['stores'][name]['rows'])
            self.assertEqual(a['stores'][name]['inode'],b['stores'][name]['inode'])
            self.assertIs(b['stores'][name]['duplicateRefused'],True)
            self.assertEqual(b['stores'][name]['integrity'],'ok')
        self.assertIs(self.r['nativeProfileLease'],True)
        for key in ('nativeHermesGatewayStarted','epochRecoveryTested','legacyIpcV2Enabled','fullD3BAccepted'):
            self.assertIs(self.r[key],False)
        self.assertEqual(self.r['paidModelCalls'],0)
        self.assertIs(self.r['checks']['exactly_two_authenticated_pings'],True)
        self.assertIs(self.r['checks']['zero_physical_provider_attempts'],True)
    def test_first_failure_historical_proof_and_own_cleanup_retained(self):
        self.assertEqual(json.loads((E/'native-001-result.json').read_text())['exitCode'],1)
        original=json.loads((E/'native-001-stdout.txt').read_bytes())
        self.assertEqual(json.loads(original['nativeStdout'])['error']['reason'],'broker_not_ready')
        old=json.loads((E/'native-001-manifest.json').read_text());new=self.outer['sourceHashes']
        for name,h in old.items():self.assertEqual(new[name],h)
        self.assertTrue(set(new)-set(old))
        self.assertTrue(all(n.startswith('packages/upstream/hermes/') for n in set(new)-set(old)))
        history=json.loads((E/'historical-source-custody.json').read_text())
        self.assertEqual(history['base'],'1207d37b5bb92bd107e5ec419cd3b4cac46d12f9')
        self.assertEqual(hashlib.sha256((E/history['snapshot']).read_bytes()).hexdigest(),history['sha256'])
        cleanup=json.loads((E/'cleanup-audit.json').read_text())
        self.assertEqual(cleanup['exitCode'],0);self.assertIs(cleanup['audit']['ownClean'],True)
        self.assertEqual(cleanup['audit']['ownLivePids'],[]);self.assertEqual(len(cleanup['audit']['images']),2)
        for item in cleanup['audit']['images']:
            self.assertEqual(item['loops'],[]);self.assertEqual(item['hostMounts'],[])
            self.assertIs(item['fencePresent'],False);self.assertIs(item['brokerSocketPresent'],False)
if __name__=='__main__':unittest.main()
