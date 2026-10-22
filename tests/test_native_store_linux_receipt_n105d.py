"""Platform repeat of actual native crash proof, with typed provenance."""
import hashlib
import json
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts/qa'))
import n105d_receipt_checks as check
E=ROOT/'evidence/d3b-native-stores-n105d'
class LinuxNativeCrashReceipt(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.outer=json.loads((E/'linux-001-stdout.txt').read_bytes())
        cls.report=cls.outer['native'];cls.provenance=json.loads((E/'linux-source-custody.json').read_text())
        cls.sources={n:v['sha256'] for group in ('nativeGitSources','dependencySources')
                     for n,v in cls.provenance[group].items()}
    def test_real_ordinary_linux_terminal_and_cleanup(self):
        self.assertEqual(json.loads((E/'linux-001-result.json').read_text())['exitCode'],0)
        self.assertEqual(self.outer['exitCode'],0);self.assertEqual(self.outer['stderr'],'')
        self.assertEqual((self.outer['uid'],self.outer['gid']),(23001,23003))
        for key in ('rootUsed','dependencyInstalled'):self.assertIs(self.outer[key],False)
        for key in ('scriptUnchanged','temporaryCodeRemoved'):self.assertIs(self.outer[key],True)
        self.assertEqual(self.report['platform'],'linux')
        result=check.review(self.report,self.sources,hashlib.sha256((ROOT/'scripts/qa/n105d_recovery_probe.py').read_bytes()).hexdigest())
        self.assertEqual(result['scenarioCount'],8);self.assertEqual(result['processLifetimes'],17)
    def test_exact_native_and_dependency_provenance_kept_separate(self):
        p=self.provenance;self.assertEqual(p['result'],'PASS_TYPED_SOURCE_CUSTODY')
        self.assertEqual(p['nativePin'],check.PIN)
        self.assertEqual((p['nativeCount'],p['dependencyCount']),(210,29))
        self.assertEqual(len(p['nativeGitSources']),210);self.assertEqual(len(p['dependencySources']),29)
        transport=json.loads((E/'linux-001-source-manifest.json').read_text())['files']
        prior=json.loads((ROOT/'evidence/d3b-profile-lease-l99d/native-dependency-inventory.json').read_text())['dependency']
        for name,row in p['nativeGitSources'].items():
            self.assertEqual(row['sha256'],transport['vendor-native/'+name])
            self.assertEqual(len(row['gitBlob']),40)
        for name,row in p['dependencySources'].items():
            self.assertTrue(name.startswith('ruamel/'))
            self.assertNotIn('gitBlob',row)
            self.assertEqual(row['sha256'],prior['sourceSha256'][name])
            self.assertEqual(row['sha256'],transport['dependencies/'+name])
            self.assertEqual(row['packageVersion'],prior['version'])
    def test_same_probe_and_same_transitions_on_both_platforms(self):
        windows=json.loads((E/'native-windows-001.json').read_text())
        windows_sources={n:v['sha256'] for n,v in json.loads((E/'native-source-custody.json').read_text())['sources'].items()}
        sha=hashlib.sha256((ROOT/'scripts/qa/n105d_recovery_probe.py').read_bytes()).hexdigest()
        a=check.review(windows,windows_sources,sha);b=check.review(self.report,self.sources,sha)
        self.assertEqual(a['transitions'],b['transitions'])
        self.assertIs(self.provenance['probeMatchesWindows'],True)
        for name,digest in windows_sources.items():
            if name in self.provenance['nativeGitSources']:
                self.assertEqual(digest,self.provenance['nativeGitSources'][name]['sha256'])
    def test_journal_observation_not_wal_or_power_loss_acceptance(self):
        for report in (self.report,json.loads((E/'native-windows-001.json').read_text())):
            self.assertIs(report['powerLossTested'],False)
            self.assertIs(report['pairedStoreAtomicRecoveryAccepted'],False)
            for case in report['cases']:
                for stage in ('crash','recover'):
                    self.assertEqual(case[stage]['proof']['journalModes'],{'state':'delete','idempotency':'delete'})
if __name__=='__main__':unittest.main()
