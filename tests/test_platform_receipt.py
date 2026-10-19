"""Custody of PLAT-001 read-only Windows and WSL inspector runs.

CI does not rerun physical host observations; it pins their precise
source and data and never calls an external provider or privileged API.
"""
import hashlib
import io
import os
import re
import subprocess
import tarfile
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
EVIDENCE=ROOT/'evidence/plat-001-19oct'
ORIGINAL_CODE='b0178b58714871c63a37ecc3a9af7972e45699a5'

def read(name):
    return json.loads((EVIDENCE/name).read_text(encoding='utf-8'))

class PlatformEvidence(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.summary=read('summary.json')

    def test_scope_is_negative_only_not_a_sandbox_certificate(self):
        record=self.summary
        self.assertEqual(record['gate'],'PLAT-001')
        self.assertEqual(record['status'],'SCOPED_OFFLINE_ROUTER_AND_ACTUAL_WIN_WSL_INSPECTOR_PASS')
        self.assertEqual(record['windowsNodeScenarioCases'],27)
        self.assertEqual(record['wsl2NodeScenarioCases'],27)
        for field in ('physicalMacOrLinuxArmNativeTested',
                      'realD3BGatewayRunWithNewRouter',
                      'guardedAdapterLaunchAuthorized',
                      'hostServicesChanged','testOwnedNativeLinuxNamespaceCreated',
                      'M1Accepted','M2Accepted'):
            self.assertIs(record[field],False,field)
        self.assertEqual(record['realModelCalls'],0)

    def test_original_five_source_shas_match_exact_accepted_code(self):
        # Historical native observations remain bound to the original
        # accepted code commit even when later test harness code improves.
        manifest=self.summary['sourceCanonicalLfSha256']
        self.assertEqual(set(manifest),{
            'packages/hybrid-runtime/platform-routing.mjs',
            'scripts/inspect_platform.mjs','tests/node/platform-cases.mjs',
            'tests/test_platform_routing.py','tests/test_hybrid_slice.py'})
        cmd=['git','archive','--format=tar',ORIGINAL_CODE,*sorted(manifest)]
        record=subprocess.run(cmd,cwd=ROOT,capture_output=True,timeout=30)
        if record.returncode and os.name=='posix' and (ROOT/'.git').is_file():
            # WSL cannot parse a Windows worktree .git pointer without
            # an explicit read-only validated mapping into /mnt/<drive>.
            pointer=(ROOT/'.git').read_text(encoding='utf-8').strip()
            match=re.fullmatch(r'gitdir: ([A-Za-z]):/(.+)',pointer)
            if match:
                mapped=Path('/mnt')/match.group(1).lower()/match.group(2)
                expected=ROOT.parents[2]/'.git'/'worktrees'/ROOT.name
                if (ROOT.parent.name=='worktrees'
                        and ROOT.parent.parent.name=='scratch'
                        and mapped.resolve()==expected.resolve()
                        and expected.is_dir()):
                    cmd=['git','--git-dir='+str(expected),'archive',
                         '--format=tar',ORIGINAL_CODE,*sorted(manifest)]
                    record=subprocess.run(cmd,cwd=ROOT,capture_output=True,timeout=30)
        self.assertEqual(record.returncode,0,
                         'original_PLAT001_code_archive_unavailable')
        with tarfile.open(fileobj=io.BytesIO(record.stdout),mode='r:') as archive:
            names={item.name for item in archive.getmembers() if item.isfile()}
            self.assertEqual(names,set(manifest))
            for name,digest in manifest.items():
                with self.subTest(source=name):
                    self.assertEqual(len(digest),64)
                    member=archive.extractfile(name)
                    self.assertIsNotNone(member)
                    data=member.read()
                    self.assertNotIn(b'\r',data,name)
                    self.assertEqual(hashlib.sha256(data).hexdigest(),digest,name)

    def test_two_real_readonly_observed_hosts(self):
        expected={
            'windows-inspector':('win32','x64','windows-host','windows-wsl2-bridge-pending'),
            'wsl2-inspector':('linux','x64','linux-wsl2-guest','linux-x64-wsl2-guest-candidate'),
        }
        for name,(platform,arch,environment,route) in expected.items():
            with self.subTest(host=name):
                obj=read(name+'.json')
                self.assertEqual(obj['result'],'NOT_ACCEPTED')
                self.assertEqual(obj['observedHost']['platform'],platform)
                self.assertEqual(obj['observedHost']['arch'],arch)
                self.assertEqual(obj['observedHost']['environment'],environment)
                self.assertEqual(obj['executionPlan']['route'],route)
                self.assertEqual(obj['executionPlan']['readiness'],'guarded-not-accepted')
                self.assertIs(obj['observedHost']['kernelAttested'],False)
                self.assertIs(obj['observedHost']['realHostUidIsolationAccepted'],False)
                self.assertIs(obj['executionPlan']['processLaunchAuthorized'],False)
                self.assertIs(obj['executionPlan']['realModelCallAuthorized'],False)
                self.assertIs(obj['executionPlan']['noFallback'],True)
                self.assertEqual(obj['executionPlan']['modelBudgetUsdAuthorized'],0)
                self.assertIs(obj['readOnlyInspector'],True)
                self.assertIs(obj['processStarted'],False)
                self.assertEqual(self.summary['observations'][name]['exitCode'],0)

    def test_two_native_node_suites_separately_27_cases(self):
        first=read('windows-node-cases.json')
        second=read('wsl2-node-cases.json')
        for name,obj in [('win',first),('wsl',second)]:
            with self.subTest(host=name):
                self.assertEqual(obj['result'],'PASS')
                self.assertEqual(obj['suite'],'PLAT-001_NO_LAUNCH')
                self.assertEqual(obj['cases'],27)
                self.assertEqual(len(set(obj['scenarios'])),27)
                self.assertEqual(obj['realModelCalls'],0)
                self.assertEqual(obj['privilegedActions'],0)
                self.assertIs(obj['secureAdapterAccepted'],False)
        self.assertEqual(first['scenarios'],second['scenarios'])
        for scenario in ('macos-arm64','macos-intel','windows-x64',
                         'wsl2-guest','linux-arm64','forged-guard-attestation',
                         'cli-require-accepted'):
            self.assertIn(scenario,first['scenarios'])

    def test_observations_preserve_only_named_files(self):
        expected={'windows-inspector','windows-node-cases',
                  'wsl2-inspector','wsl2-node-cases'}
        self.assertEqual(set(self.summary['observations']),expected)
        for key,obj in self.summary['observations'].items():
            with self.subTest(observation=key):
                self.assertEqual(obj['filename'],key+'.json')
                self.assertEqual(obj['exitCode'],0)
                self.assertEqual(obj['result'],
                                 'NOT_ACCEPTED' if 'inspector' in key else 'PASS')

if __name__=='__main__':unittest.main()
