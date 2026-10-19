"""PLAT-002A source custody and deliberate native NO-GO assertions.

Original Windows/WSL read-only native acceptance FAILED after timeout.
Tests verify this evidence exactly without rerunning any WSL command.
"""
import hashlib
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
EVIDENCE=ROOT/'evidence/plat-002a-wsl-19oct'

def read(name):
    return json.loads((EVIDENCE/name).read_text(encoding='utf-8'))

class WslReadonlyCustody(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.native=read('native-win-wsl-identity-01.json')
        cls.review=read('native-stability-observed.json')

    def test_native_timeout_must_not_be_false_positive(self):
        self.assertEqual(self.native['result'],'FAIL')
        self.assertEqual(self.native['gate'],'PLAT-002A-WINDOWS-WSL2-READONLY')
        self.assertEqual(self.native['nativeCheckCount'],5)
        positive=self.native['nativeCases']['positive']
        self.assertEqual(positive['exitCode'],2)
        self.assertEqual(positive['report']['result'],'REFUSED')
        self.assertEqual(positive['report']['code'],
                         'GUEST_PROCESS_OUTCOME_UNKNOWN_TIMEOUT')

    def test_native_four_policy_refusals(self):
        reasons={
            'wrongExpectedUid':'BRIDGE_REPLY_VERIFICATION_FAILED',
            'missingQaOptIn':'EXPLICIT_QA_OPT_IN_REQUIRED',
            'unknownCommand':'INVALID_READONLY_PROBE_ARGUMENTS',
            'missingArgs':'INVALID_READONLY_PROBE_ARGUMENTS'
        }
        self.assertEqual(set(self.native['nativeCases']),
                         set(reasons)|{'positive'})
        for name,reason in reasons.items():
            with self.subTest(scenario=name):
                record=self.native['nativeCases'][name]
                self.assertEqual(record['exitCode'],2)
                self.assertEqual(record['report']['result'],'REFUSED')
                self.assertEqual(record['report']['code'],reason)
                self.assertIs(record['report']['fallback'],False)
                self.assertEqual(record['report']['realModelCalls'],0)

    def test_explicit_unknown_native_process_state(self):
        r=self.review
        self.assertEqual(r['result'],
              'NOT_ACCEPTED_WSL2_GUEST_RESPONSIVENESS_UNKNOWN')
        self.assertEqual(r['exactNativeBatch']['result'],'FAIL')
        self.assertEqual(r['independentGuestProcessInspection']['result'],
                         'UNKNOWN')
        self.assertEqual(r['windowsTasklistInspection']['result'],'UNKNOWN')
        self.assertIs(r['noBlindNativeRetry'],True)
        self.assertIs(r['guestCancelKillNativeVerified'],False)
        self.assertIs(r['fullD3BAccepted'],False)
        self.assertEqual(r['realModelCalls'],0)

    def test_native_failure_immutable_sha(self):
        actual=hashlib.sha256(
            (EVIDENCE/'native-win-wsl-identity-01.json').read_bytes()).hexdigest()
        self.assertEqual(self.review['exactNativeBatch']['receiptRawSha256'],
                         actual)
        self.assertEqual(self.review['exactNativeBatch']['file'],
                         'native-win-wsl-identity-01.json')

    def test_canonical_source_manifest_pin(self):
        manifest=self.native['sourceCanonicalLfSha256']
        expected={
           'packages/hybrid-runtime/wsl2-readonly-bridge.mjs',
           'scripts/qa/wsl2_bridge_host_probe.mjs',
           'scripts/qa/wsl2_bridge_guest_probe.py',
           'scripts/qa/capture_wsl2_bridge_identity.py',
           'tests/node/wsl2-bridge-cases.mjs',
           'tests/test_wsl2_bridge.py',
           'tests/test_wsl2_guest_protocol.py'
        }
        self.assertEqual(set(manifest),expected)
        for name,digest in manifest.items():
            with self.subTest(path=name):
                file=ROOT/name
                self.assertTrue(file.is_file() and not file.is_symlink())
                raw=file.read_bytes()
                self.assertNotIn(b'\r',raw.replace(b'\r\n',b''))
                self.assertEqual(
                    hashlib.sha256(raw.replace(b'\r\n',b'\n')).hexdigest(),
                    digest,name)

    def test_no_prod_or_model_claims(self):
        for key in ('independentHostUidVerified',
                    'hostFilesystemIsolated','fullD3BAccepted',
                    'agentOrToolStarted','guestProcessCancellationNativeTested',
                    'guestRestartOrReplayNativeTested',
                    'secureAdapterActivated','mainMerged'):
            self.assertIs(self.native[key],False,key)
        self.assertEqual(self.native['realModelCalls'],0)
        self.assertEqual(self.native['privilegedCommands'],0)

if __name__=='__main__':unittest.main()
