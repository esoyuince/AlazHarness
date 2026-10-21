"""Current-source P71C observer receipt checks, NOT a new Linux execution."""
import hashlib
import json
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
E=ROOT/'evidence/d3b-storage-native-n97k'

class NativeMountReceipt(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.outer=json.loads((E/'native-001-stdout.json').read_bytes())
        cls.r=json.loads(cls.outer['nativeStdout'])
        cls.result=json.loads((E/'native-001-result.json').read_bytes())
    def test_actual_terminal_and_current_source_custody(self):
        self.assertEqual(self.result['exitCode'],0)
        self.assertEqual(self.outer['unitExitCode'],0)
        self.assertEqual(self.outer['nativeExitCode'],0)
        self.assertEqual(self.r['result'],'PASS_SCOPED_NATIVE_MOUNT_OBSERVER')
        self.assertEqual(self.r['checkCount'],21)
        self.assertEqual(len(self.r['checks']),21)
        self.assertTrue(all(v is True for v in self.r['checks'].values()))
        self.assertEqual(set(self.r['sourceSha256']),{
            'packages/claw-hermes/gateway_storage_mounts.py',
            'tests/test_gateway_storage_mounts.py','scripts/qa/n97k_storage_mount_probe.py'})
        self.assertEqual(self.r['sourceSha256'],self.outer['sourceHashes'])
        for name,sha in self.r['sourceSha256'].items():
            with self.subTest(name=name):
                self.assertEqual(hashlib.sha256((ROOT/name).read_bytes()).hexdigest(),sha)
    def test_native_mount_metadata_and_no_content_open(self):
        r=self.r;o=r['details']['observation'];f=r['details']['independentFindmnt'];e=r['expected']
        self.assertEqual(r['identity']['uid'],23001);self.assertEqual(r['identity']['gid'],23003)
        self.assertEqual(o['filesystem'],'ext4')
        self.assertEqual((o['presentFiles'],o['sidecarsObserved']),(4,2))
        self.assertEqual((f['id'],f['fsroot'],f['target'],f['fstype']),
                         (e['mount_id'],e['root'],e['mount_point'],e['filesystem']))
        self.assertEqual(list(map(int,f['maj:min'].split(':'))),e['device'])
        self.assertEqual(r['details']['volatileFilesystem'],'tmpfs')
        self.assertEqual(r['observerForbiddenEvents'],[])
        self.assertGreater(r['observerOpenEvents'],0)
        self.assertEqual(r['details']['filesBefore'],r['details']['filesAfter'])
        self.assertEqual(o['mountTableSha256'],r['mountinfoBeforeSha256'])
    def test_scope_cleanup_and_no_durability_or_launch_claim(self):
        self.assertIs(self.outer['temporaryCodeRemoved'],True)
        self.assertIs(self.outer['sourcesUnchanged'],True)
        for key in ('rootCommand','mountsChanged','uidChanged','gatewayStarted','brokerStarted',
                    'powerLossTested','persistentGatewayQualified','fullD3BAccepted'):
            self.assertIs(self.r[key],False,key)
        self.assertEqual(self.r['modelCalls'],0)
        for key in ('writesPerformed','databaseContentsOpened','sqliteOpenInodeVerified',
                    'physicalMediumDurabilityVerified','exclusiveWriterVerified',
                    'pairedStoreConsistencyVerified','fullGatewayPersistenceAccepted','launchAuthorized'):
            self.assertIs(self.r['details']['observation'][key],False,key)

if __name__=='__main__':unittest.main()
