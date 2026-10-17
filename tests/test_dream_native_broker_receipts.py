"""Read-only custody checks for three native Linux broker/socket receipts.

These tests do not replay the broker or infer a real model from a local HTTP
server. The native subprocess/origin experiment runs only by explicit operator
invocation of scripts/qa/native_d2b2_linux_socket.py under Linux.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
EVIDENCE=ROOT/'evidence/dream-d2b2-native-9c31'
CASES={
    'normal':('completed',['dream','baseline','candidate'],3,3,2),
    'candidate-disconnect':('unknown',['dream','baseline','candidate'],3,2,1),
    'review-revoked':('unknown',['dream','baseline'],2,2,0),
}


class NativeBrokerCustody(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records={}
        for scenario in CASES:
            path=EVIDENCE/(scenario+'-initial.json')
            raw=path.read_bytes()
            cls.records[scenario]=json.loads(raw)

    def test_three_scoped_native_scenarios_pass(self):
        self.assertEqual(set(self.records),set(CASES))
        for scenario,record in self.records.items():
            with self.subTest(scenario=scenario):
                self.assertEqual(record['scenario'],scenario)
                self.assertEqual(record['result'],'PASS')
                self.assertEqual(record['errors'],[])

    def test_expected_origin_requests_by_case(self):
        for scenario,record in self.records.items():
            expected=CASES[scenario]
            with self.subTest(scenario=scenario):
                self.assertEqual(record['origin']['kinds'],expected[1])
                self.assertEqual(record['origin']['authenticatedRequests'],expected[2])
                self.assertEqual(record['origin']['originExceptions'],[])

    def test_physical_http_attempts_and_responses(self):
        for scenario,record in self.records.items():
            with self.subTest(scenario=scenario):
                expected=CASES[scenario]
                counter=record['broker']['counters']
                self.assertEqual(counter['physicalAttempts'],expected[2])
                self.assertEqual(counter['responses'],expected[3])
                self.assertEqual(counter['pings'],1)

    def test_native_separate_pid_and_socket_cleanup(self):
        for scenario,record in self.records.items():
            with self.subTest(scenario=scenario):
                broker=record['broker']
                self.assertTrue(record['nativeBrokerSocket'])
                self.assertTrue(broker['pidSeparate'])
                self.assertEqual(broker['exitCode'],0)
                self.assertTrue(broker['socketRemoved'])
                self.assertEqual(broker['activeRequests'],0)
                self.assertTrue(record['privateTemporaryProfileRemoved'])

    def test_request_view_origin_sha_matches_and_budget(self):
        for scenario,record in self.records.items():
            with self.subTest(scenario=scenario):
                proof=record['provenance']
                count=record['origin']['authenticatedRequests']
                self.assertEqual(proof['preparedRequestRows'],count)
                self.assertEqual(proof['nativeEgressGrantCount'],count)
                self.assertEqual(proof['exactWireHashMatches'],count)
                self.assertTrue(proof['requestViewTiedToProviderClaim'])
                self.assertEqual(record['budget']['providerReservations'],count)
                self.assertFalse(record['budget']['separateBudget'])

    def test_profile_guardrails_no_real_model_or_gateway(self):
        for scenario,record in self.records.items():
            with self.subTest(scenario=scenario):
                self.assertFalse(record['nativeGateway'])
                self.assertFalse(record['originalAiohttpUpstream'])
                self.assertFalse(record['docker'])
                self.assertFalse(record['physicalModelInferenceVerified'])
                self.assertFalse(record['modelComprehensionVerified'])
                self.assertFalse(record['independentSkillTransferVerified'])
                self.assertFalse(record['activeMemoryChanged'])
                self.assertEqual(record['paidCalls'],0)
                self.assertEqual(record['actualModelCalls'],0)

    def test_outcome_and_retained_arms_distinct(self):
        for scenario,record in self.records.items():
            expected=CASES[scenario]
            with self.subTest(scenario=scenario):
                self.assertEqual(record['trial']['state'],expected[0])
                self.assertEqual(record['trial']['recordedArmCount'],expected[4])
                self.assertEqual(record['trial']['requestedArms'],
                   ['baseline','candidate'][:expected[4]])
                self.assertFalse(record['trial']['providerInferenceVerified'])
                self.assertFalse(record['trial']['skillTransferVerified'])

    def test_disconnect_never_promotes_unreturned_candidate(self):
        record=self.records['candidate-disconnect']
        self.assertEqual(record['provenance']['observedResponseRows'],2)
        self.assertEqual(record['trial']['recordedArmCount'],1)
        self.assertEqual(record['trial']['requestedArms'],['baseline'])
        self.assertEqual(record['broker']['counters']['responses'],2)

    def test_revocation_suppresses_candidate_http(self):
        record=self.records['review-revoked']
        self.assertEqual(record['origin']['kinds'],['dream','baseline'])
        self.assertEqual(record['trial']['recordedArmCount'],0)
        self.assertEqual(record['provenance']['observedResponseRows'],2)

    def test_valid_scenario_broker_replay_refused(self):
        record=self.records['normal']
        self.assertTrue(record['provenance']['replayRefused'])
        self.assertEqual(record['broker']['counters']['refused'],1)
        self.assertEqual(record['origin']['authenticatedRequests'],3)
        self.assertEqual(record['trial']['syntheticLocalScore'],
            {'baselineCorrect':8,'candidateCorrect':12,'learnedSkillProven':False})

    def test_all_memory_and_skill_files_untouched(self):
        for scenario,record in self.records.items():
            with self.subTest(scenario=scenario):
                self.assertTrue(record['memoryAndSkillUnchanged'])
                self.assertFalse(record['trial']['evaluatorTruthSent'])

    def test_origin_has_bounded_hashes_not_raw_requests(self):
        for scenario,record in self.records.items():
            with self.subTest(scenario=scenario):
                origin=record['origin']
                self.assertEqual(len(origin['requestSha256']),len(origin['kinds']))
                self.assertEqual(len(set(origin['requestSha256'])),len(origin['kinds']))
                self.assertTrue(all(len(h)==64 for h in origin['requestSha256']))
                self.assertTrue(all(type(n) is int and 0<n<100000
                                    for n in origin['requestBytes']))
                self.assertNotIn('rawBody',json.dumps(record))
                self.assertNotIn('origin_key',json.dumps(record))
                self.assertNotIn('signing_key',json.dumps(record))


if __name__=='__main__':
    unittest.main(verbosity=2)
