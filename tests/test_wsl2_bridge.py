"""PLAT-002A fixed read-only WSL bridge, 36 independently visible Node assertions.

One real Node process runs all 36 scenarios, keeping the tight CI job
bounded without skipping any assertion. No WSL guest is spawned by CI.
"""
import json
from pathlib import Path
import re
import shutil
import subprocess
import unittest

ROOT=Path(__file__).resolve().parents[1]
SCENARIOS=(
    'valid-bound-guest-self-report','not-a-sandbox-certificate',
    'wrong-nonce-refused','wrong-request-id-refused','wrong-guest-source-refused',
    'invalid-frame-fields-refused','missing-frame-fields-refused',
    'wrong-result-type-refused','fake-windows-as-linux-refused',
    'fake-linux-arm64-refused','fake-wsl2-guest-refused','guest-root-refused',
    'wrong-uid-refused','uid-effective-mismatch-refused',
    'namespace-visibility-required','kernel-hash-required',
    'seccomp-metadata-bounded','extra-observed-fields-refused',
    'secure-launch-claim-refused','host-filesystem-isolation-claim-refused',
    'independent-host-uid-claim-refused','real-model-claim-refused',
    'tool-start-claim-refused','expected-root-refused',
    'expected-extra-field-refused','canonical-fixed-windows-mount',
    'windows-unc-refused','windows-relative-path-refused',
    'windows-parent-traversal-refused','host-gate-not-remote-authority',
    'pre-aborted-no-process','invalid-uid-no-process',
    'invalid-signal-no-process','invalid-timeout-no-process',
    'cli-no-optin-refused','cli-arbitrary-command-refused',
)

class Wsl2BridgeContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.node=shutil.which('node')
        if not cls.node:
            raise RuntimeError('Node 24+ is required; WSL2 bridge cases cannot be skipped')
        version=subprocess.check_output([cls.node,'--version'],text=True).strip()
        m=re.fullmatch(r'v([0-9]+)\.[0-9]+\.[0-9]+',version)
        if not m or int(m.group(1))<24:
            raise RuntimeError('Node 24+ required: '+version)
        result=subprocess.run([cls.node,str(ROOT/'tests/node/wsl2-bridge-cases.mjs'),'all'],
            cwd=ROOT,capture_output=True,text=True,errors='replace',
            encoding='utf-8',timeout=25)
        if result.returncode:
            raise RuntimeError('PLAT-002A bounded Node case group failed: '+
                               (result.stderr+result.stdout)[-2500:])
        try:
            proof=json.loads(result.stdout.strip())
        except (ValueError,TypeError):
            raise RuntimeError('PLAT-002A invalid Node proof') from None
        if (proof.get('result')!='PASS'
                or proof.get('suite')!='PLAT-002A_READONLY_FIXED_GUEST'
                or proof.get('count')!=len(SCENARIOS)
                or proof.get('names')!=list(SCENARIOS)
                or proof.get('agentOrToolStarted') is not False
                or proof.get('realModelCalls')!=0
                or proof.get('guardedExecutionAccepted') is not False):
            raise RuntimeError('PLAT-002A incomplete Node scenario coverage')
        cls.proof=proof

    def case(self,name):
        self.assertIn(name,self.proof['names'])
        self.assertEqual(self.proof['result'],'PASS')
        self.assertEqual(self.proof['count'],len(SCENARIOS))
        self.assertIs(self.proof['guardedExecutionAccepted'],False)
        self.assertEqual(self.proof['realModelCalls'],0)

    def test_source_files_parse(self):
        for name in ('packages/hybrid-runtime/wsl2-readonly-bridge.mjs',
                     'scripts/qa/wsl2_bridge_host_probe.mjs',
                     'tests/node/wsl2-bridge-cases.mjs'):
            with self.subTest(file=name):
                proc=subprocess.run([self.node,'--check',str(ROOT/name)],
                    cwd=ROOT,capture_output=True,text=True,encoding='utf-8',
                    timeout=12)
                self.assertEqual(proc.returncode,0,
                                 proc.stdout+proc.stderr)

def case_test(name):
    def test(self):
        self.case(name)
    test.__name__='test_'+name.replace('-','_')
    return test

for name in SCENARIOS:
    setattr(Wsl2BridgeContracts,'test_'+name.replace('-','_'),
            case_test(name))

if __name__=='__main__':unittest.main()
