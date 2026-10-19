"""Negative-only native denial receipt, source custody and explicit non-acceptance."""
import hashlib
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
EVIDENCE=ROOT/'evidence/d3b-host-principal-7a19'

class PrincipalNegativeReceipt(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report=json.loads((EVIDENCE/'native-denial-hp7a19b.json').read_text(encoding='utf-8'))
    def test_all_explicit_denials_recorded(self):
        r=self.report
        self.assertEqual(r['result'],'PASS_DENIAL_ONLY')
        self.assertEqual(r['checkCount'],8)
        self.assertEqual(len(r['checks']),8)
        self.assertTrue(all(value is True for value in r['checks'].values()))
    def test_different_host_uid_not_claimed(self):
        r=self.report
        self.assertEqual((r['observedUid'],r['brokerUidDemanded']),(1000,65534))
        self.assertIs(r['separateHostUidVerified'],False)
        self.assertIs(r['nativeTwoUidGatewayBrokerTested'],False)
        self.assertIs(r['fullD3BAccepted'],False)
        self.assertIs(r['mainMerged'],False)
        self.assertEqual(r['realModelCalls'],0)
    def test_current_policy_and_client_source_bytes_pinned(self):
        sources=self.report['sourceSha256']
        self.assertEqual(set(sources),{
            'packages/claw-hermes/host_principal.py',
            'packages/claw-hermes/provider_broker.py',
            'packages/claw-hermes/provider_egress.py',
            'scripts/qa/principal_denial_linux.py'})
        for path,want in sources.items():
            with self.subTest(path=path):
                p=ROOT/path
                self.assertTrue(p.is_file() and not p.is_symlink())
                actual_bytes=p.read_bytes()
                digest=hashlib.sha256(actual_bytes).hexdigest()
                if digest != want:
                    # These four exact Linux native proof files were read
                    # from a Windows CRLF checkout. Git stores LF via .gitattributes.
                    # Only a single exact LF -> CRLF transformation is valid.
                    self.assertNotIn(b'\r',actual_bytes,path)
                    self.assertGreater(actual_bytes.count(b'\n'),0,path)
                    self.assertEqual(
                        hashlib.sha256(actual_bytes.replace(b'\n',b'\r\n')).hexdigest(),
                        want,path)
    def test_previous_no_source_manifest_remains_diagnostic_only(self):
        old=json.loads((EVIDENCE/'native-denial-hp7a19.json').read_text(encoding='utf-8'))
        self.assertEqual(old['result'],'PASS_DENIAL_ONLY')
        self.assertNotIn('sourceSha256',old)
        self.assertIs(old['separateHostUidVerified'],False)

if __name__=='__main__':unittest.main()
