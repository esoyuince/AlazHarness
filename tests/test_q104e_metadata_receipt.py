"""Offline Q104E native metadata proof, separate from F104X profile acceptance."""
import hashlib
import json
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
E=ROOT/'evidence/d3b-native-profile-q104e'
class MetadataInheritanceReceipt(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.o=json.loads((E/'native-001-stdout.txt').read_bytes())
        cls.r=json.loads(cls.o['nativeStdout'])
        cls.cases={x['case']:x for x in cls.r['cases']}
    def test_terminal_result_and_exact_sources(self):
        self.assertEqual(json.loads((E/'native-001-result.json').read_text())['exitCode'],0)
        self.assertEqual((self.o['unitExitCode'],self.o['nativeExitCode']),(0,0))
        self.assertEqual(self.o['nativeStderr'],'')
        self.assertIs(self.o['sourcesUnchanged'],True)
        self.assertEqual(self.r['result'],'PASS_SCOPED_METADATA_INHERITANCE')
        self.assertTrue(all(v is True for v in self.r['checks'].values()))
        self.assertEqual(self.o['sourceSha256'],json.loads((E/'native-001-intent.json').read_text())['files'])
        for name,want in self.o['sourceSha256'].items():
            with self.subTest(name=name):
                self.assertEqual(hashlib.sha256((ROOT/name).read_bytes()).hexdigest(),want)
        pin=json.loads((E/'candidate-001.json').read_text())['files']['packages/claw-hermes/credential_guard.py']
        self.assertEqual(self.r['candidateSha256'],pin['sha256'])
        self.assertEqual(self.r['probeSha256'],self.o['sourceSha256']['scripts/qa/q104e_metadata_probe.py'])
    def test_default_false_optin_after_actual_exec(self):
        self.assertEqual(set(self.cases),{'default','explicit_false','opt_in_true'})
        for name,entry in self.cases.items():
            enabled=name=='opt_in_true';p=entry['proof']
            self.assertEqual(entry['exitCode'],0);self.assertEqual(entry['stderr'],'')
            self.assertEqual(p['result'],'PASS');self.assertEqual((p['checkCount'],len(p['checks'])),(21,21))
            self.assertTrue(all(v is True for v in p['checks'].values()))
            self.assertTrue(all(v['allowed'] is True for v in p['beforeControls'].values()))
            self.assertEqual(p['receipt']['metadataReadFileCount'],6 if enabled else 5)
            self.assertIs(p['receipt']['selfMountMetadata'],enabled)
            for key in ('selfMountOpen','numericMountOpen'):
                self.assertIs(p['details'][key]['allowed'],enabled)
                self.assertEqual(p['details'][key]['errno'],None if enabled else 13)
            for key in ('self_environ','self_mem','self_maps','self_mounts','self_mountstats',
                        'self_fd_directory','parent_mountinfo','protected_canary','mountWrite'):
                self.assertEqual(p['details'][key],{'allowed':False,'errno':13})
    def test_descendants_retain_only_original_numeric_grant(self):
        pids=[]
        for name,entry in self.cases.items():
            p=entry['proof'];pids.append(p['pid']);enabled=name=='opt_in_true'
            for mode in ('fork','execDescendant'):
                child=p['details'][mode];pids.append(child['pid'])
                self.assertEqual(child['grantPid'],p['pid']);self.assertNotEqual(child['pid'],p['pid'])
                self.assertTrue(all(v is True for v in child['checks'].values()))
                self.assertEqual(child['ownMountOpen'],{'allowed':False,'errno':13})
                self.assertEqual(child['originalMountOpen'],{'allowed':enabled,'errno':None if enabled else 13})
                if mode=='fork':self.assertEqual(child['exitCode'],0)
        self.assertEqual(len(pids),9);self.assertEqual(len(set(pids)),9)
    def test_scoped_limits_and_cleanup(self):
        self.assertIs(self.o['temporaryCodeRemoved'],True)
        self.assertEqual((self.r['uid'],self.r['gid']),(23001,23003))
        for key in ('rootUsed','mountsChanged','namespacesChanged','actualNativeProfileTested',
                    'realHermesGatewayStarted','fullD3BAccepted'):
            self.assertIs(self.r[key],False)
        self.assertEqual(self.r['providerCalls'],0)
        for entry in self.cases.values():
            self.assertIs(entry['proof']['contentOfSensitiveMetadataRead'],False)
            self.assertIs(entry['proof']['fullGatewayIsolationTested'],False)
        first=json.loads((E/'rule-tests-windows-001-result.json').read_text())
        self.assertEqual(first['exitCode'],1)
        correction=json.loads((E/'rule-fixture-correction.json').read_text())
        self.assertIs(correction['productOrSnapshotChanged'],False)
        self.assertIs(correction['assertionsUnchanged'],True)
if __name__=='__main__':unittest.main()
