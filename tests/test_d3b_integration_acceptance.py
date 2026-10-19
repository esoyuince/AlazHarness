"""Immutable historical custody of four combined native Gateway receipts.

New branches must verify the originally measured Git source commit;
current host-principal work is NOT retroactive IPC/Gateway acceptance.
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
EVIDENCE=ROOT/'evidence/d3b-integration-19oct'
ACCEPTED_CODE_COMMIT='29f6a353799dcdf0279ebcabf44593fbcbcfa160'
CASES={
    'normal':('int19-normal2',4,4),
    'budget-limit':('int19-limit2',3,3),
    'candidate-disconnect':('int19-disconnect2',4,3),
    'review-revoked':('int19-revoke2',3,3),
}

def read(name):
    return json.loads((EVIDENCE/name).read_text(encoding='utf-8'))

class D3BIntegrationEvidence(unittest.TestCase):
    def test_four_live_merged_gateway_cases_and_private_budget(self):
        for scenario,(run_id,attempts,responses) in CASES.items():
            with self.subTest(scenario=scenario):
                record=read('gateway-'+run_id+'.json')
                inner=record['gatewayPrivateBudgetAcceptance']
                budget=inner['privateBudget']
                self.assertEqual((record['result'],record['exitCode']),('PASS',0))
                self.assertEqual((record['runId'],record['scenario']),(run_id,scenario))
                self.assertTrue(record['sourceUnchanged'] and record['snapshotBytesMatch'])
                self.assertTrue(record['temporaryCodeCopyRemoved'])
                self.assertEqual(record['sourceFiles'],189)
                self.assertNotIn(record['snapshotFilesystem'],('v9fs','9p','drvfs'))
                self.assertEqual(inner['result'],'PASS')
                self.assertEqual(inner['nativeCombinedResult'],'PASS')
                self.assertIs(inner['actualHermesGatewayWithDualGuard'],True)
                self.assertIs(inner['actualBrokerPersistentBudget'],True)
                self.assertIs(inner['ipcProjectionVerified'],True)
                self.assertIs(inner['pathnameSocketProjection'],True)
                self.assertIs(inner['explicitSelectedBrokerSocketOnly'],True)
                self.assertIs(inner['brokerBudgetIndependentFromGateway'],True)
                self.assertEqual(inner['projectedRootProof'],
                  {'state':'projected','explicitHostSocketCount':1,'oldRootDetached':True})
                self.assertEqual(budget['providerReservations'],attempts)
                self.assertEqual(budget['observedHttpResponses'],responses)
                self.assertEqual(budget['reservedTokens'],attempts*163840)
                self.assertIs(budget['noAutomaticRefunds'],True)
                self.assertIs(budget['gatewayDatabaseIsBudgetAuthority'],False)
                self.assertIs(budget['measuredInvoiceVerified'],False)
                self.assertIs(inner['separateHostUidVerified'],False)
                self.assertIs(record['ipcProjectionVerified'],True)
                self.assertIs(record['independentBrokerBudgetVerified'],True)
                self.assertIs(record['separateHostUidVerified'],False)
                self.assertIs(record['completeD3B'],False)
                self.assertEqual(record['realModelCalls'],0)
    def test_four_runs_pin_original_189_git_sources(self):
        shared=None
        for run_id,*_ in CASES.values():
            record=read('gateway-'+run_id+'.json')
            manifest=read('source-'+run_id+'.json')
            self.assertEqual(set(manifest),{'files'})
            files=manifest['files']
            self.assertIs(type(files),dict)
            self.assertEqual(len(files),189)
            digest=hashlib.sha256(json.dumps(files,sort_keys=True).encode()).hexdigest()
            self.assertEqual(digest,record['sourceManifestSha256'])
            if shared is None:shared=files
            else:self.assertEqual(shared,files)
        for name in shared:
            path=Path(name)
            self.assertFalse(path.is_absolute())
            self.assertNotIn('..',path.parts)
            self.assertTrue(name=='sources.lock.json' or
                            name.startswith(('packages/','scripts/','config/')))
        cmd=['git','archive','--format=tar',ACCEPTED_CODE_COMMIT,*sorted(shared)]
        record=subprocess.run(cmd,cwd=ROOT,capture_output=True,timeout=30)
        if record.returncode and os.name=='posix' and (ROOT/'.git').is_file():
            # Windows-authored .git worktree pointer is unreadable to Linux Git
            # on WSL. Resolve only this own exact verified Git metadata path.
            pointer=(ROOT/'.git').read_text(encoding='utf-8').strip()
            match=re.fullmatch(r'gitdir: ([A-Za-z]):/(.+)',pointer)
            if match:
                mapped=Path('/mnt')/match.group(1).lower()/match.group(2)
                expected=ROOT.parents[2]/'.git'/'worktrees'/ROOT.name
                if (ROOT.parent.name=='worktrees' and ROOT.parent.parent.name=='scratch'
                        and mapped.resolve()==expected.resolve() and expected.is_dir()):
                    cmd=['git','--git-dir='+str(expected),
                         'archive','--format=tar',ACCEPTED_CODE_COMMIT,*sorted(shared)]
                    record=subprocess.run(cmd,cwd=ROOT,capture_output=True,timeout=30)
        self.assertEqual(record.returncode,0,'original_integrated_git_commit_unavailable')
        with tarfile.open(fileobj=io.BytesIO(record.stdout),mode='r:') as archive:
            names={m.name for m in archive.getmembers() if m.isfile()}
            self.assertEqual(names,set(shared))
            for name,digest in shared.items():
                with self.subTest(source=name):
                    item=archive.extractfile(name)
                    self.assertIsNotNone(item,name)
                    raw=item.read()
                    current=hashlib.sha256(raw).hexdigest()
                    if name=='scripts/qa/windows_appcontainer_probe.cs':
                        expected_lf='4c1050700bd01dfb73468ac3a266e8d2edf07212a9f75641379a59b3a02f7f8c'
                        if current==digest:
                            self.assertEqual(hashlib.sha256(
                                raw.replace(b'\r\n',b'\n')).hexdigest(),
                                expected_lf,name)
                        else:
                            self.assertEqual(current,expected_lf,name)
                            self.assertEqual(hashlib.sha256(
                                raw.replace(b'\n',b'\r\n')).hexdigest(),
                                digest,name)
                    else:
                        self.assertEqual(current,digest,name)
    def test_owned_kernel_socket_and_mount_negatives(self):
        record=read('kernel-int19-final1.json')
        self.assertEqual(record['result'],'PASS')
        self.assertEqual(record['exitCode'],0)
        self.assertTrue(record['positiveControlsAllLive'])
        self.assertEqual(record['ownedServerCounts'],
                         {'broker':2,'blocked':0,'tcp':0,'abstract':0})
        checks=record['probe']['checks']
        self.assertEqual(len(checks),24)
        self.assertTrue(all(value is True for value in checks.values()))
        self.assertEqual(len(record['startupRefusals']),5)
        self.assertTrue(all(v['refused'] is True for v in record['startupRefusals'].values()))
        self.assertIs(record['protectedUnchanged'],True)
        self.assertIs(record['temporaryRootsRemoved'],True)
        self.assertIs(record['completeD3B'],False)
        self.assertEqual(record['realModelCalls'],0)
        for name,digest in record['sourceSha256'].items():
            self.assertEqual(hashlib.sha256((ROOT/name).read_bytes()).hexdigest(),digest,name)

if __name__=='__main__':unittest.main()
