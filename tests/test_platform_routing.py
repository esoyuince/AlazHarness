"""PLAT-001: actual Node cross-platform planner, offline and side-effect free."""
import json
from pathlib import Path
import shutil
import re
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCENARIOS = (
    'linux-x64','linux-arm64','wsl2-guest','wsl-version-unknown',
    'windows-x64','windows-arm64','macos-arm64','macos-intel',
    'unsupported-os','bad-host-shapes','untrusted-release',
    'bad-platform-arch','missing-mode','unsupported-mode',
    'unknown-request-fields','strict-schema','forged-guard-attestation',
    'unknown-descriptor-fields','mock-only','frozen-results',
    'actual-host-inspector','cli-mock','cli-guarded',
    'cli-require-accepted','cli-os-spoof-refused','cli-duplicate-refused',
    'no-release-or-env-leak',
)

class PlatformRouteContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.node = shutil.which('node')
        if not cls.node:
            raise RuntimeError('Node 24 required for cross-platform route tests')
        version = subprocess.check_output([cls.node,'--version'],text=True).strip()
        found=re.fullmatch(r'v([0-9]+)\.[0-9]+\.[0-9]+',version)
        if not found or int(found.group(1))<24:
            raise RuntimeError('Node 24+ required: ' + version)
        result = subprocess.run(
            [cls.node,str(ROOT/'tests/node/platform-cases.mjs'),'all'],
            cwd=ROOT,capture_output=True,text=True,encoding='utf-8',
            errors='replace',timeout=25)
        if result.returncode!=0:
            raise RuntimeError('PLAT-001 27-case Node assertion group failed: ' +
                               (result.stdout+result.stderr)[-3000:])
        obj=json.loads(result.stdout.strip())
        if (obj.get('result')!='PASS' or obj.get('suite')!='PLAT-001_NO_LAUNCH'
                or obj.get('cases')!=len(SCENARIOS)
                or obj.get('scenarios')!=list(SCENARIOS)
                or obj.get('realModelCalls')!=0
                or obj.get('privilegedActions')!=0
                or obj.get('secureAdapterAccepted') is not False):
            raise RuntimeError('PLAT-001 Node assertion group proof invalid')
        cls.all_proof=obj
        cls.all_scenarios=frozenset(obj['scenarios'])

    def scenario(self, name):
        # Every one of the 27 JS assertions actually executes. Keeping one
        # Node process for their shared, pure scenario group avoids repeated
        # startup under the 180-second CI worker budget.
        self.assertIn(name, self.all_scenarios)
        self.assertEqual(self.all_proof['result'],'PASS')
        self.assertEqual(self.all_proof['realModelCalls'],0)
        self.assertEqual(self.all_proof['privilegedActions'],0)
        self.assertIs(self.all_proof['secureAdapterAccepted'],False)

    def test_new_node_sources_parse(self):
        sources=[
            ROOT/'packages/hybrid-runtime/platform-routing.mjs',
            ROOT/'scripts/inspect_platform.mjs',
            ROOT/'tests/node/platform-cases.mjs',
        ]
        for source in sources:
            with self.subTest(source=source.name):
                result=subprocess.run([self.node,'--check',str(source)],
                    cwd=ROOT,capture_output=True,text=True,encoding='utf-8',timeout=10)
                self.assertEqual(result.returncode,0,result.stdout+result.stderr)

for scenario in SCENARIOS:
    def generated(self, name=scenario):
        self.scenario(name)
    generated.__name__='test_'+scenario.replace('-','_')
    setattr(PlatformRouteContract,generated.__name__,generated)

if __name__=='__main__':unittest.main()
