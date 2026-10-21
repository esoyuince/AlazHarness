"""Offline L99D proof verification, not another native lock or Gateway run."""
import hashlib
import json
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
E=ROOT/'evidence/d3b-profile-lease-l99d'
class ProfileLeaseReceipt(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.outer=json.loads((E/'native-002-stdout.json').read_text(encoding='utf-8'))
        cls.r=json.loads(cls.outer['nativeStdout'])
    def test_terminal_native_result_and_current_own_sources(self):
        self.assertEqual(self.outer['nativeExitCode'],0)
        self.assertEqual(self.outer['unitExitCode'],0)
        self.assertIs(self.outer['sourcesUnchanged'],True)
        self.assertIs(self.outer['temporaryCodeRemoved'],True)
        self.assertEqual(self.r['result'],'PASS_NATIVE_PROFILE_OWNERSHIP')
        self.assertIsNone(self.r['error']);self.assertEqual(self.r['checkCount'],26)
        self.assertEqual(len(self.r['checks']),26)
        self.assertTrue(all(v is True for v in self.r['checks'].values()))
        self.assertEqual(self.r['sourcePin'],'eb75627faf532fa6ffbdae59a0d14b0b385fc780')
        for name,digest in self.r['sourceSha256'].items():
            if name.startswith(('packages/','scripts/','tests/')):
                self.assertEqual(hashlib.sha256((ROOT/name).read_bytes()).hexdigest(),digest,name)
        for name in ('gateway/runtime_ownership.py','gateway/status.py'):
            key='vendor-native/'+name
            self.assertEqual(self.r['details']['importedSources'][key],self.r['sourceSha256'][key])
    def test_real_process_outcomes_and_unchanged_store_bytes(self):
        children=self.r['details']['children']
        self.assertEqual([c['exitCode'] for c in children],[77,77,77,0,77,0])
        self.assertEqual(len({c['pid'] for c in children}),6)
        for child in children:
            if child['exitCode']==77:self.assertEqual(child['reason'],'profile_already_owned')
        abrupt=self.r['details']['abruptOwner']
        self.assertEqual(abrupt['exitCode'],73)
        self.assertEqual(abrupt['pid'],abrupt['ready']['pid'])
        self.assertEqual(children[3]['lockInode'],children[5]['lockInode'])
        self.assertEqual(children[3]['lockInode'],abrupt['ready']['lockInode'])
        self.assertEqual(self.r['details']['databaseBefore'],self.r['details']['databaseAfter'])
    def test_no_full_gateway_or_privileged_acceptance_claim(self):
        for key in ('nativeLockingMocked','nativeGatewayStarted','rootCommand','uidChanged',
                    'persistentVolumeIntegrated','fullD3BAccepted'):
            self.assertIs(self.r[key],False,key)
        self.assertEqual(self.r['uid'],23001);self.assertEqual(self.r['gid'],23003)
        self.assertEqual(self.r['providerCalls'],0)
        self.assertTrue(self.r['checks']['owned_profile_removed'])
        self.assertTrue(self.r['checks']['mount_table_unchanged'])
if __name__=='__main__':unittest.main()
