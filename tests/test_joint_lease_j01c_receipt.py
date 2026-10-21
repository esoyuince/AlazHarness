"""Exact-source new joint native evidence; no historical PASS substitution."""
import hashlib
import json
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
E=ROOT/'evidence/d3b-storage-joint-j01c'

class JointLeaseReceipt(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.transport=json.loads((E/'native-002.json').read_text())
        cls.steps={s['name']:s for s in cls.transport['steps']}
        cls.joint=json.loads(cls.steps['joint-interaction']['stdout'])
        cls.manifest=json.loads((E/'transport-final-manifest.json').read_text())

    def test_terminal_counts_and_current_sources(self):
        self.assertEqual(json.loads((E/'native-002-result.json').read_text())['exitCode'],0)
        self.assertIs(self.transport['success'],True)
        self.assertEqual(set(self.steps),{'selected-units','native-profile','joint-interaction'})
        for step in self.steps.values():self.assertEqual(step['exitCode'],0)
        units=json.loads(self.steps['selected-units']['stdout'])
        self.assertEqual((units['total'],units['passed'],units['skipped'],units['errors'],units['failures']),(79,79,0,0,0))
        self.assertEqual(self.joint['result'],'PASS_JOINT_LEASE_INTERACTION')
        self.assertEqual(self.joint['checkCount'],25)
        self.assertEqual(len(self.joint['checks']),25)
        self.assertTrue(all(v is True for v in self.joint['checks'].values()))
        self.assertIsNone(self.joint['error'])
        for name,digest in self.manifest['files'].items():
            if name.startswith(('packages/','scripts/','tests/')):
                self.assertEqual(hashlib.sha256((ROOT/name).read_bytes()).hexdigest(),digest,name)
        self.assertEqual(self.transport['sourceHashes'],self.manifest['files'])

    def test_acquired_child_pid_and_executed_sources_are_bound(self):
        ready=self.joint['childReadiness'];self.assertEqual(len(ready),3)
        self.assertEqual([r['kind'] for r in ready],['profile','profile','image'])
        self.assertEqual(len({r['pid'] for r in ready}),3)
        self.assertEqual(self.joint['childExitCodes'],[73,73,73])
        for row in ready:
            self.assertEqual(row['state'],'ACQUIRED');self.assertGreater(row['pid'],0)
            required={'packages/claw-hermes/state_image_lease.py'} if row['kind']=='image' else {
                'packages/claw-hermes/gateway_profile_lease.py','vendor-native/gateway/runtime_ownership.py',
                'vendor-native/gateway/status.py'}
            self.assertTrue(required<=set(row['sources']))
            for name,h in row['sources'].items():self.assertEqual(self.manifest['files'][name],h)

    def test_counterexample_never_claims_reconciliation_or_persistence(self):
        for key in ('image_available_after_controller_death','profile_still_owned_when_image_available',
                    'image_lease_survives_profile_exit','image_contender_still_refused_after_profile_exit'):
            self.assertIs(self.joint['checks'][key],True)
        for key in ('controllerReconciliationImplemented','imageMounted','rootCommand',
                    'realHermesGatewayStarted','fullD3BAccepted','lockingMocked'):
            self.assertIs(self.joint[key],False)
        self.assertEqual(self.joint['providerCalls'],0)
        self.assertEqual((self.joint['uid'],self.joint['gid']),(23001,23003))
        for key in ('sourcesUnchanged','temporaryCodeRemoved','identityUnchanged','mountTableUnchanged'):
            self.assertIs(self.transport[key],True)

    def test_first_failure_and_source_correction_preserved(self):
        old=json.loads((E/'native-001.json').read_text())
        first=json.loads(old['steps'][2]['stdout'])
        self.assertEqual(first['result'],'FAIL');self.assertIs(old['success'],False)
        self.assertEqual([n for n,v in first['checks'].items() if not v],['both_native_and_image_sources_imported'])
        repair=json.loads((E/'process-source-correction.json').read_text())
        self.assertEqual(hashlib.sha256((E/'joint-probe-before.py.txt').read_bytes()).hexdigest(),repair['beforeSha256'])
        self.assertEqual(hashlib.sha256((ROOT/'scripts/qa/j01c_joint_lease_probe.py').read_bytes()).hexdigest(),repair['afterSha256'])
        self.assertIs(repair['productCodeChanged'],False)
        self.assertIs(repair['priorR91FCodeChanged'],False)

if __name__=='__main__':unittest.main()
