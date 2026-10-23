"""Pure boundary contracts, not native/task or full service acceptance."""
from dataclasses import FrozenInstanceError
from pathlib import Path
import json,sys,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'packages/claw-hermes'))
import gateway_canonical_run_binding as binding

class CanonicalBoundaryTests(unittest.TestCase):
    def test_bounded_json_accepts_only_objects(self):
        self.assertEqual(binding.json_object('{"status":"running"}'),{'status':'running'})
        for raw in ('[]','null','true','1','"text"'):
            with self.subTest(raw=raw),self.assertRaises(binding.CanonicalBindingRejected):binding.json_object(raw)
    def test_duplicate_top_and_nested_keys_not_last_wins(self):
        for raw in ('{"a":1,"a":2}','{"nested":{"a":1,"a":2}}'):
            with self.assertRaises(binding.CanonicalBindingRejected):binding.json_object(raw)
    def test_nonfinite_numbers_refused(self):
        for raw in ('{"a":NaN}','{"a":Infinity}','{"a":-Infinity}'):
            with self.assertRaises(binding.CanonicalBindingRejected):binding.json_object(raw)
    def test_nonfinite_exponent_refused(self):
        with self.assertRaises(binding.CanonicalBindingRejected):binding.json_object('{"x":1e9999}')
    def test_json_byte_limit_not_just_character_limit(self):
        for raw in (' '*65537,'{"text":"'+'\u0130'*40000+'"}'):
            with self.assertRaises(binding.CanonicalBindingRejected):binding.json_object(raw)
    def test_json_invalid_types_not_coerced(self):
        for raw in (b'{}',{},None,1):
            with self.assertRaises(binding.CanonicalBindingRejected):binding.json_object(raw)
    def test_snapshot_claim_does_not_authorize_work_or_prove_worker(self):
        s=binding.CanonicalClaimSnapshot('private-a','private-r','private-s',1,1,'CLAIMED',True,True,False,False,False,False,100)
        body=s.public();self.assertTrue(body['canonicalClaimMatched']);self.assertTrue(body['requestBindingMatched'])
        for key in ('physicalWorkerHealthVerified','allAgentWorkObserved','storageProfileMountVerified','serviceReadinessVerified','runtimeAdmissionAuthorized','retryAuthorized','storeReleaseAuthorized'):
            self.assertIs(body[key],False,key)
        self.assertNotIn('private',json.dumps(body));self.assertNotIn('private',repr(s))
    def test_snapshot_immutable(self):
        s=binding.CanonicalClaimSnapshot('a','r','s',1,None,'QUEUED',False,False,False,False,False,False,100)
        self.assertFalse(s.public()['canonicalClaimMatched'])
        with self.assertRaises(FrozenInstanceError):s.phase='CLAIMED'
    def test_source_pin_has_only_exact_critical_native_seams(self):
        self.assertEqual(binding.NATIVE_FEATURE,'943210584828ccfcfd6adc8eb966ecaa8ca18429')
        self.assertEqual(set(binding.NATIVE_SOURCE_HASHES),{'gateway/session_authority.py','gateway/session_api_turn.py','gateway/platforms/api_server_run_observation.py','gateway/platforms/api_server_runs.py','gateway/session_runtime_workers.py'})
        for h in binding.NATIVE_SOURCE_HASHES.values():self.assertTrue(binding.digest(h))
if __name__=='__main__':unittest.main()
