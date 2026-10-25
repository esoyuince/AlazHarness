"""Historical integration proof plus still-current unchanged metadata guard."""
import hashlib
import json
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
Q=ROOT/'evidence/d3b-native-profile-q104e'
F=ROOT/'evidence/d3b-profile-admission-f104x'
class IntegratedProfileSource(unittest.TestCase):
    def test_original_permission_files_equal_independent_snapshot(self):
        files=json.loads((Q/'candidate-001.json').read_text())['files']
        self.assertEqual(set(files),{'packages/claw-hermes/credential_guard.py','packages/claw-hermes/gateway_state_projection.py'})
        for path,pin in files.items():
            with self.subTest(path=path):
                source=(ROOT/'evidence/d3b-native-layout-l106r/gateway_state_projection.before.py.txt'
                        if path=='packages/claw-hermes/gateway_state_projection.py' else ROOT/path)
                self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(),pin['sha256'])
                self.assertEqual(source.read_bytes(),(Q/pin['snapshot']).read_bytes())
    def test_distinct_native_trials_share_actual_guard_source(self):
        independent=json.loads(json.loads((Q/'native-001-stdout.txt').read_bytes())['nativeStdout'])
        profile=json.loads(json.loads((F/'native-002-stdout.txt').read_bytes())['nativeStdout'])
        self.assertEqual(independent['result'],'PASS_SCOPED_METADATA_INHERITANCE')
        self.assertEqual(profile['result'],'PASS_SCOPED_NATIVE_PROFILE_ADMISSION')
        digest=hashlib.sha256((ROOT/'packages/claw-hermes/credential_guard.py').read_bytes()).hexdigest()
        self.assertEqual(independent['candidateSha256'],digest)
        self.assertEqual(profile['sourceSha256']['packages/claw-hermes/credential_guard.py'],digest)
        self.assertIs(independent['actualNativeProfileTested'],False)
        self.assertTrue(all(t['nativeProfileLease'] is True for t in profile['events'] if t.get('state')=='RESULT'))
        self.assertFalse(profile['fullD3BAccepted']);self.assertFalse(independent['fullD3BAccepted'])
if __name__=='__main__':unittest.main()
