"""Offline current-source checks for actual J100C experiments, never launches WSL."""
import hashlib
import json
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
E=ROOT/'evidence/d3b-lease-joint-j100c'

class JointLeaseReceipt(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.outer=json.loads((E/'native-002-stdout.txt').read_text(encoding='utf-8'))
        cls.r=json.loads(cls.outer['nativeStdout'])
        cls.manifest=json.loads((E/'transport-manifest-002.json').read_text(encoding='utf-8'))

    def test_terminal_runs_and_current_source_pins(self):
        terminal=json.loads((E/'native-002-result.json').read_text(encoding='utf-8'))
        self.assertEqual(terminal['exitCode'],0)
        self.assertEqual((self.outer['unitExitCode'],self.outer['nativeExitCode']),(0,0))
        counts=json.loads(self.outer['unitStdout'])
        self.assertEqual((counts['total'],counts['passed'],counts['skipped'],counts['errors'],counts['failures']),(79,79,0,0,0))
        self.assertEqual(self.r['result'],'PASS_JOINT_LEASE_EXPERIMENT')
        self.assertIsNone(self.r['error'])
        self.assertEqual(self.r['checkCount'],28);self.assertEqual(len(self.r['checks']),28)
        self.assertTrue(all(v is True for v in self.r['checks'].values()))
        self.assertEqual(self.r['sourcePin'],'eb75627faf532fa6ffbdae59a0d14b0b385fc780')
        self.assertEqual(self.r['sourceSha256'],self.manifest['files'])
        self.assertEqual(self.outer['sourceHashes'],self.manifest['files'])
        for name,want in self.manifest['files'].items():
            if name.startswith(('packages/','scripts/','tests/')):
                self.assertEqual(hashlib.sha256((ROOT/name).read_bytes()).hexdigest(),want,name)

    def test_two_owner_lifetimes_and_per_process_imports(self):
        events=self.r['events']
        self.assertEqual([e['state'] for e in events],['PROFILE_HELD','EARLY_REFUSED','PROFILE_RELEASED','PROFILE_HELD'])
        self.assertEqual(events[0]['pid'],events[1]['pid']);self.assertEqual(events[0]['pid'],events[2]['pid'])
        self.assertNotEqual(events[0]['pid'],events[3]['pid'])
        self.assertEqual(events[0]['lockInode'],events[3]['lockInode'])
        self.assertEqual(events[1]['reason'],'profile_writers_still_active')
        self.assertIs(events[1]['stillHeld'],True);self.assertIs(events[2]['stillAlive'],True)
        for owner in (events[0],events[3]):
            self.assertIs(owner['nativeOwner'],True)
            for path in ('vendor-native/gateway/runtime_ownership.py','vendor-native/gateway/status.py'):
                self.assertEqual(owner['importedSources'][path],self.manifest['files'][path])
            for name,digest in owner['importedSources'].items():
                self.assertEqual(digest,self.manifest['files'][name])
        children=self.r['contenders']
        self.assertEqual([c['exitCode'] for c in children],[77,77,77,77,0,77,77,77,0,77,0])
        self.assertEqual(len({c['pid'] for c in children}),11)
        for c in children:
            if c['exitCode']==77:
                self.assertEqual(c['reason'],'volume_busy' if c['mode']=='image-contender' else 'profile_already_owned')
        self.assertEqual(children[-1]['state'],'IMAGE_ACQUIRED')
        self.assertEqual(children[4]['state'],'PROFILE_ACQUIRED')

    def test_limited_scope_and_terminal_cleanup(self):
        for key in ('controllerOrderingImplementedInProduction','imageMounted','persistentGatewayQualified',
                    'nativeGatewayStarted','fullD3BAccepted','rootCommand','nativeLockingMocked','forcedCleanup'):
            self.assertIs(self.r[key],False,key)
        self.assertEqual(self.r['providerCalls'],0)
        self.assertEqual((self.r['uid'],self.r['gid']),(23001,23003))
        for key in ('sourcesUnchanged','temporaryCodeRemoved','identityUnchanged','mountTableUnchanged'):
            self.assertIs(self.outer[key],True,key)
        cleanup=json.loads((E/'lab-cleanup.json').read_text(encoding='utf-8'))
        self.assertIs(cleanup['audit']['clean'],True)
        self.assertEqual(cleanup['audit']['ownedProbeProcessIds'],[])
        self.assertEqual((cleanup['stopExitCode'],cleanup['listExitCode']),(0,0))
        self.assertIs(cleanup['defaultUbuntuCommandIssued'],False)
        for key in ('stopStdout','stopStderr','finalList'):
            v=cleanup[key];raw=v['text'].encode(v['encoding'])
            self.assertEqual((len(raw),hashlib.sha256(raw).hexdigest()),(v['bytes'],v['sha256']))
        self.assertTrue(any('AlazHarness-D3B-P71C' in l and 'Stopped' in l for l in cleanup['finalList']['text'].splitlines()))

    def test_original_failed_provenance_trial_remains_failed(self):
        outer=json.loads((E/'native-001-stdout.txt').read_text(encoding='utf-8'))
        old=json.loads(outer['nativeStdout'])
        self.assertEqual(outer['nativeExitCode'],1);self.assertEqual(old['result'],'FAIL')
        self.assertEqual([k for k,v in old['checks'].items() if not v],['native_sources_normally_imported'])
        correction=json.loads((E/'process-provenance-correction.json').read_text(encoding='utf-8'))
        self.assertEqual(hashlib.sha256((E/'probe-before-process-provenance.py.txt').read_bytes()).hexdigest(),correction['beforeSha256'])
        self.assertEqual(hashlib.sha256((ROOT/'scripts/qa/j100c_joint_lease_probe.py').read_bytes()).hexdigest(),correction['afterSha256'])
        self.assertIs(correction['productCodeChanged'],False)
        self.assertIs(correction['R91FModified'],False)

if __name__=='__main__':unittest.main()
