"""PLAT-001: actual Node cross-platform planner, offline and side-effect free."""
import json
from pathlib import Path
import shutil
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
        if not version.startswith('v24.'):
            raise RuntimeError('Node 24 required: ' + version)

    def scenario(self, name):
        result = subprocess.run([self.node,str(ROOT/'tests/node/platform-cases.mjs'),name],
            cwd=ROOT,capture_output=True,text=True,encoding='utf-8',
            errors='replace',timeout=15)
        self.assertEqual(result.returncode,0,
                         (result.stdout+result.stderr)[-6000:])
        obj=json.loads(result.stdout.strip())
        self.assertEqual(obj['result'],'PASS')
        self.assertEqual(obj['cases'],1)
        self.assertEqual(obj['scenarios'],[name])
        self.assertEqual(obj['realModelCalls'],0)
        self.assertEqual(obj['privilegedActions'],0)
        self.assertIs(obj['secureAdapterAccepted'],False)

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
