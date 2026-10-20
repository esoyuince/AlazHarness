"""Current-source actual CLI evidence; not a positive split-UID certificate."""
import hashlib
import json
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
class PrincipalStartupReceipt(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r=json.loads((ROOT/'evidence/d3b-principal-startup-20oct/native-cli-001.json').read_text())
    def test_current_source_custody(self):
        self.assertEqual(self.r['sourceSha256'],self.r['sourceAfterSha256'])
        self.assertEqual(set(self.r['sourceSha256']),{
            'scripts/run_provider_broker.py','packages/claw-hermes/provider_broker.py',
            'packages/claw-hermes/provider_egress.py','packages/claw-hermes/host_principal.py',
            'scripts/qa/native_principal_startup.py'})
        for name,want in self.r['sourceSha256'].items():
            with self.subTest(source=name):
                raw=(ROOT/name).read_bytes()
                if hashlib.sha256(raw).hexdigest()!=want:
                    # Only the two unchanged, historical CRLF checkout files.
                    self.assertIn(name,{'packages/claw-hermes/provider_egress.py',
                                        'packages/claw-hermes/host_principal.py'})
                    self.assertNotIn(b'\r',raw)
                    self.assertEqual(hashlib.sha256(raw.replace(b'\n',b'\r\n')).hexdigest(),want)
    def test_real_process_ping_refusal_and_cleanup(self):
        self.assertEqual(self.r['result'],'PASS_SCOPED')
        self.assertEqual(self.r['checkCount'],23)
        self.assertEqual(len(self.r['checks']),23)
        self.assertTrue(all(v is True for v in self.r['checks'].values()))
        self.assertIsNone(self.r['errorType'])
        self.assertIs(self.r['forcedCleanup'],False)
    def test_no_broader_acceptance_from_cli_ping(self):
        self.assertEqual(self.r['realModelCalls'],0)
        for key in ('realGatewayTested','separateHostUidVerified','ipcV2ProjectionTested','fullD3BAccepted'):
            self.assertIs(self.r[key],False)
if __name__=='__main__':unittest.main()
