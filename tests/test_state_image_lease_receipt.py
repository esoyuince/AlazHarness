"""Offline verification of V98R real-process tests; never reruns the lab."""
import hashlib
import json
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
E=ROOT/'evidence/d3b-volume-lease-v98r'
class ImageLeaseReceipt(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.r=json.loads((E/'linux-002-stdout.json').read_text(encoding='utf-8'))
    def test_actual_successful_linux_selection_and_source_custody(self):
        self.assertEqual(self.r['unitExitCode'],0)
        count=json.loads(self.r['unitStdout'])
        self.assertEqual((count['total'],count['passed'],count['skipped'],count['errors'],count['failures']),
                         (26,26,0,0,0))
        self.assertEqual(set(self.r['sourceHashes']),{'packages/claw-hermes/state_image_lease.py',
                                                     'tests/test_state_image_lease.py'})
        for name,want in self.r['sourceHashes'].items():
            self.assertEqual(hashlib.sha256((ROOT/name).read_bytes()).hexdigest(),want,name)
    def test_ordinary_identity_cleanup_and_limited_scope(self):
        self.assertEqual(self.r['identityBefore'],self.r['identityAfter'])
        self.assertEqual(self.r['identityBefore']['uid'],23001)
        self.assertEqual(self.r['identityBefore']['gid'],23003)
        for key in ('sourcesUnchanged','temporaryCodeRemoved','ownedFixturesRemoved',
                    'identityUnchanged','mountTableUnchanged'):
            self.assertIs(self.r[key],True,key)
        for key in ('rootCommand','formatPerformed','mountPerformed','gatewayStarted','brokerStarted','fullD3BAccepted'):
            self.assertIs(self.r[key],False,key)
        self.assertEqual(self.r['paidModelCalls'],0)
    def test_failed_invocation_and_scoped_cleanup_records_retained(self):
        original=json.loads((E/'linux-001-result.json').read_text())
        self.assertEqual(original['exitCode'],1)
        self.assertEqual((E/'linux-001-stdout.txt').read_text().strip(),'This account is currently not available.')
        cleanup=json.loads((E/'lab-cleanup.json').read_text(encoding='utf-8'))
        self.assertEqual((cleanup['cleanupExitCode'],cleanup['stopExitCode'],cleanup['listExitCode']),(0,0,0))
        for key in ('stopStdout','stopStderr','finalList'):
            item=cleanup[key];raw=item['text'].encode(item['encoding'])
            self.assertEqual((len(raw),hashlib.sha256(raw).hexdigest()),(item['bytes'],item['sha256']))
        self.assertTrue(any('AlazHarness-D3B-P71C' in line and 'Stopped' in line
                            for line in cleanup['finalList']['text'].splitlines()))
        correction=json.loads((E/'cleanup-scope-review.json').read_text())
        self.assertEqual(correction['priorWrapperExitCode'],1)
        self.assertIs(correction['defaultUbuntuStoppedByThisTask'],False)
        self.assertIs(correction['newNativeRun'],False)
if __name__=='__main__':unittest.main()
