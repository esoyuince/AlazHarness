"""Offline historical P102 proof checks; no new privileged/native run."""
import hashlib
import json
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
E=ROOT/'evidence/d3b-state-projection-p102'
NEW_SOURCES={'packages/claw-hermes/gateway_state_projection.py',
             'tests/test_gateway_state_projection.py','scripts/qa/p102_projection_child.py',
             'scripts/qa/p102_confined.py','scripts/qa/p102_projection_accept.py'}

class StateProjectionReceipt(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.outer=json.loads((E/'native-003-stdout.txt').read_text(encoding='utf-8'))
        cls.r=json.loads(cls.outer['nativeStdout'])
        cls.targets=[v for v in cls.r['events'] if v.get('state')=='RESULT']
    def test_terminal_historical_source_trial(self):
        terminal=json.loads((E/'native-003-result.json').read_text(encoding='utf-8'))
        self.assertEqual(terminal['exitCode'],0)
        self.assertEqual((self.outer['unitExitCode'],self.outer['nativeExitCode']),(0,0))
        self.assertEqual(self.outer['nativeStderr'],'')
        self.assertIs(self.outer['sourceUnchanged'],True)
        self.assertEqual(self.r['result'],'PASS_SCOPED_PERSISTENT_PROJECTION')
        self.assertIsNone(self.r['error']);self.assertIs(self.r['forcedCleanup'],False)
        self.assertEqual((self.r['checkCount'],len(self.r['checks'])),(32,32))
        self.assertTrue(all(v is True for v in self.r['checks'].values()))
        self.assertEqual(self.outer['sourceHashes'],self.r['sourceSha256'])
        intended=json.loads((E/'native-003-intent.json').read_text())['sources']
        self.assertEqual(intended,self.r['sourceSha256'])
        for name in NEW_SOURCES:
            # The original P102 receipt stays bound to its original Git blob.
            # F104X has a fresh current-source execution and independent receipt.
            source=(ROOT/'evidence/d3b-profile-admission-f104x/gateway_state_projection.py.before.txt'
                    if name=='packages/claw-hermes/gateway_state_projection.py' else ROOT/name)
            self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(),intended[name],name)
    def test_two_confined_processes_and_persistent_rows(self):
        self.assertEqual([r['mode'] for r in self.targets],['write','read'])
        self.assertNotEqual(self.targets[0]['pid'],self.targets[1]['pid'])
        for r in self.targets:
            self.assertEqual(r['pid'],r['receipt']['pid'])
            self.assertEqual((r['checkCount'],len(r['checks'])),(26,26))
            self.assertTrue(all(v is True for v in r['checks'].values()))
            self.assertEqual(r['receipt']['profile'],'/run/alaz-state/profile')
            self.assertEqual(r['receipt']['stateDirectoryCount'],1)
            self.assertEqual(r['receipt']['ambientHostDirectoriesBound'],0)
            self.assertEqual(r['receipt']['afterDrop']['uids'],[23001]*4)
            self.assertEqual(r['receipt']['afterDrop']['gids'],[23003]*4)
            self.assertEqual(r['receipt']['afterDrop']['groups'],[])
            self.assertTrue(all(v==0 for v in r['receipt']['afterDrop']['caps'].values()))
        a,b=self.targets
        for name in ('state.db','runs_idempotency.db'):
            self.assertEqual(a['stores'][name]['rows'],[['p102-run','persisted-in-confinement']])
            self.assertEqual(a['stores'][name]['rows'],b['stores'][name]['rows'])
            self.assertEqual(a['stores'][name]['inode'],b['stores'][name]['inode'])
            self.assertEqual(b['stores'][name]['integrity'],'ok')
            self.assertIs(b['stores'][name]['duplicateRefused'],True)
        closed=[e for e in self.r['events'] if e.get('state')=='CLOSED']
        self.assertEqual(len(closed),2)
        self.assertTrue(all(e['leaseReleasedLast'] and e['ownedUsersGone'] and e['loopAttachmentGone'] for e in closed))
    def test_no_stronger_acceptance_or_permission_claim(self):
        for key in ('nativeHermesGatewayStarted','nativeProfileLease','epochRecoveryTested',
                    'legacyIpcV2Enabled','fullD3BAccepted'):
            self.assertIs(self.r[key],False,key)
        self.assertEqual(self.r['paidModelCalls'],0)
        for r in self.targets:
            self.assertIs(r['checks']['baseline_mountinfo_denial_unchanged'],True)
            for key in ('profileOwnershipAcquired','nativeHermesStoresOpened',
                        'realHermesGatewayTested','legacyIpcV2Activated','fullD3BAccepted'):
                self.assertIs(r['receipt'][key],False,key)
        negative=[e for e in self.r['events'] if 'negative' in e]
        self.assertEqual([e['exitCode'] for e in negative],[2,2])
        self.assertEqual(negative[0]['diagnostic']['reason'],'state_projection_profile_identity')
        self.assertEqual(negative[1]['diagnostic']['reason'],'lab_volume_device_mismatch')
    def test_failures_preserved_and_scoped_lab_cleanup(self):
        for i in ('001','002'):
            self.assertEqual(json.loads((E/('native-'+i+'-result.json')).read_text())['exitCode'],1)
            old=json.loads((E/('native-'+i+'-stdout.txt')).read_text())
            self.assertEqual(json.loads(old['nativeStdout'])['result'],'FAIL')
            self.assertEqual(json.loads(old['nativeStdout'])['error']['reason'],'broker_not_ready')
        cleanup=json.loads((E/'cleanup-final.json').read_text())
        self.assertEqual((cleanup['auditExitCode'],cleanup['stopExitCode'],cleanup['listExitCode']),(0,0,0))
        self.assertIs(cleanup['audit']['ownClean'],True)
        self.assertEqual(cleanup['audit']['matchingLivePids'],[])
        self.assertEqual(len(cleanup['audit']['images']),3)
        self.assertTrue(all(not row['loops'] and not row['fencePresent'] and not row['hostMounts']
                            for row in cleanup['audit']['images']))
        self.assertIs(cleanup['onlyNamedLabStopRequested'],True)
        self.assertIs(cleanup['defaultUbuntuCommandIssued'],False)
        for key in ('stopStdout','stopStderr','finalList'):
            item=cleanup[key];raw=item['text'].encode(item['encoding'])
            self.assertEqual((len(raw),hashlib.sha256(raw).hexdigest()),(item['bytes'],item['sha256']))
        self.assertTrue(any('AlazHarness-D3B-P71C' in line and 'Stopped' in line
                            for line in cleanup['finalList']['text'].splitlines()))

if __name__=='__main__':unittest.main()
