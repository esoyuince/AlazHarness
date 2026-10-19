"""Offline custody checks for four native broker-private-budget Gateway receipts.

Historic D2B2 receipts are checked against their immutable original commit in
test_d2b2_gateway_acceptance; THESE receipts pin the current source bytes.
No network, Gateway, or provider is launched by this module.
"""
import hashlib
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
EVIDENCE=ROOT/'evidence/d3b-budget-c84f'
CASES={
    'normal':('bgta19-normal4',4,4),
    'budget-limit':('bgta19-limit1',3,3),
    'candidate-disconnect':('bgta19-disconnect1',4,3),
    'review-revoked':('bgta19-revoke1',3,3),
}


def read(name):
    return json.loads((EVIDENCE/name).read_text(encoding='utf-8'))


class PrivateBudgetNativeEvidence(unittest.TestCase):
    def test_four_gateway_scenarios_and_independent_authority(self):
        for scenario,(run_id,attempts,responses) in CASES.items():
            with self.subTest(scenario=scenario):
                record=read('gateway-'+run_id+'.json')
                native=record['gatewayPrivateBudgetAcceptance']
                state=native['privateBudget']
                self.assertEqual(record['result'],'PASS')
                self.assertEqual(record['exitCode'],0)
                self.assertTrue(record['sourceUnchanged'])
                self.assertTrue(record['snapshotBytesMatch'])
                self.assertTrue(record['temporaryCodeCopyRemoved'])
                self.assertNotIn(record['snapshotFilesystem'],('v9fs','9p','drvfs'))
                self.assertEqual(native['result'],'PASS')
                self.assertEqual(native['nativeCombinedResult'],'PASS')
                self.assertIs(native['actualHermesGatewayWithDualGuard'],True)
                self.assertIs(native['actualBrokerPersistentBudget'],True)
                self.assertEqual(native['scenario'],scenario)
                self.assertEqual(state['providerReservations'],attempts)
                self.assertEqual(state['observedHttpResponses'],responses)
                self.assertEqual(state['reservedTokens'],attempts*163840)
                self.assertIs(state['gatewayDatabaseIsBudgetAuthority'],False)
                self.assertIs(state['noAutomaticRefunds'],True)
                self.assertIs(state['measuredInvoiceVerified'],False)
                self.assertIs(state['hostFilesystemConfinementVerified'],False)
                self.assertIs(native['completeD3B'],False)
                self.assertIs(native['ipcProjectionVerified'],False)
                self.assertIs(native['separateHostUidVerified'],False)
                self.assertEqual(native['realModelCalls'],0)

    def test_new_native_receipts_pin_current_code_source(self):
        first=None
        for run_id,*_ in CASES.values():
            record=read('gateway-'+run_id+'.json')
            manifest=read('source-'+run_id+'.json')
            self.assertEqual(set(manifest),{'files'})
            files=manifest['files']
            self.assertIs(type(files),dict)
            self.assertEqual(len(files),record['sourceFiles'])
            self.assertEqual(len(files),188)
            digest=hashlib.sha256(json.dumps(files,sort_keys=True).encode()).hexdigest()
            self.assertEqual(digest,record['sourceManifestSha256'])
            if first is None:first=files
            else:self.assertEqual(files,first)
        for relative,digest in first.items():
            path=Path(relative)
            self.assertFalse(path.is_absolute())
            self.assertNotIn('..',path.parts)
            self.assertTrue(relative=='sources.lock.json' or
                            relative.startswith(('packages/','scripts/','config/')))
            actual=ROOT/path
            self.assertTrue(actual.is_file() and not actual.is_symlink(),relative)
            source_bytes=actual.read_bytes()
            if relative=='scripts/qa/windows_appcontainer_probe.cs':
                # The original evidence is the Windows CRLF checkout.
                # The canonical Git/Linux checkout stores LF (text=auto).
                # Two exact, known content hashes, and this path ONLY.
                current=hashlib.sha256(source_bytes).hexdigest()
                if current!=digest:
                    self.assertEqual(
                        current,
                        '4c1050700bd01dfb73468ac3a266e8d2edf07212a9f75641379a59b3a02f7f8c',
                        relative)
                    self.assertEqual(hashlib.sha256(
                        source_bytes.replace(b'\n',b'\r\n')).hexdigest(),
                        digest,relative)
                else:
                    self.assertEqual(source_bytes.count(b'\r\n'),
                                     source_bytes.count(b'\n'),relative)
            else:
                self.assertEqual(hashlib.sha256(source_bytes).hexdigest(),digest,relative)

    def test_failed_receipts_retained_not_passed_off_as_success(self):
        self.assertEqual(read('gateway-bgta19-normal2.json')['result'],'FAIL')
        self.assertEqual(read('gateway-bgta19-normal3.json')['result'],'FAIL')
        self.assertEqual(read('native-bgta19-normal1.json')['result'],'FAIL')


if __name__=='__main__':
    unittest.main(verbosity=2)
