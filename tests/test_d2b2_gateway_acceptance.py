"""QA policy checks and custody of four separately executed native Gateway runs.

These offline tests never start a Gateway, call a model or replay broker traffic.
"""
import hashlib
import importlib.util
import json
from functools import lru_cache
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/d2b2-gateway-af21"
# This is historical D2B2 acceptance, not an assertion that every future
# development branch must retain byte-identical current sources. New code has
# its own source-frozen native acceptance and SHA checks.
ACCEPTED_CODE_COMMIT = '35099bda644ebe042a4fab40649604fb837bb367'

@lru_cache(maxsize=128)
def historical_sha256(relative):
    path=Path(relative)
    if (path.is_absolute() or '..' in path.parts or not relative.startswith(('packages/','scripts/'))):
        raise AssertionError('invalid_historical_source_path')
    raw=subprocess.check_output(['git','show',ACCEPTED_CODE_COMMIT+':'+relative],
                                cwd=ROOT,stderr=subprocess.DEVNULL)
    return hashlib.sha256(raw).hexdigest()
SPEC = importlib.util.spec_from_file_location("gateway_qa_acceptance", ROOT / "scripts/qa/native_d2b2_full_gateway.py")
qa = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(qa)


def read(name):
    return json.loads((EVIDENCE/name).read_text(encoding="utf-8"))


class GatewayAcceptanceTests(unittest.TestCase):
    def test_normal_policy_accounts_for_four_reservations(self):
        policy = qa.scenario_policy("normal")
        self.assertEqual(policy.max_provider_calls, 4)
        self.assertEqual(policy.tokens_per_attempt, 163840)
        self.assertEqual(policy.total_token_limit, 4 * policy.tokens_per_attempt)
        self.assertEqual(policy.total_cost_microusd, 1_000_000)
        self.assertGreaterEqual(policy.total_cost_microusd, 4 * policy.cost_per_attempt)

    def test_negative_budget_preserves_per_attempt_limits(self):
        normal = qa.scenario_policy("normal")
        limited = qa.scenario_policy("budget-limit")
        self.assertEqual(limited.max_provider_calls, normal.max_provider_calls)
        self.assertEqual(limited.tokens_per_attempt, normal.tokens_per_attempt)
        self.assertEqual(limited.total_token_limit, 3 * normal.tokens_per_attempt)
        self.assertLess(limited.total_token_limit, 4 * normal.tokens_per_attempt)

    def test_unknown_scenario_refused(self):
        for value in ("", "production", "unlimited"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                qa.scenario_policy(value)
            with self.subTest(value=value), self.assertRaises(ValueError):
                qa.expected_scenario(value)

    def test_failure_expectations_never_promote_pair(self):
        self.assertEqual(qa.expected_scenario("normal"), ("completed", 4, 4, 2))
        self.assertEqual(qa.expected_scenario("budget-limit"), ("unknown", 3, 3, 1))
        self.assertEqual(qa.expected_scenario("candidate-disconnect"), ("unknown", 4, 3, 1))
        self.assertEqual(qa.expected_scenario("review-revoked"), ("unknown", 3, 3, 0))

    def test_four_final_runs_use_real_gateway_and_original_broker(self):
        for name in qa.SCENARIOS:
            record = read(name + "-final.json")
            with self.subTest(name=name):
                self.assertEqual(record["result"], "PASS")
                self.assertEqual(record["errors"], [])
                self.assertIs(record["nativeHermesGateway"], True)
                self.assertIs(record["originalAiohttpBroker"], True)
                self.assertEqual(record["sourcePin"], "eb75627faf532fa6ffbdae59a0d14b0b385fc780")
                self.assertEqual(record["gateway"]["nativeApiAdapter"], "gateway.platforms.api_server.APIServerAdapter")
                self.assertEqual(record["gateway"]["aiohttpVersion"], "3.14.3")
                self.assertEqual(record["origin"]["rejectedWrongCredentials"], 3)

    def test_receipts_remain_bound_to_exact_measured_source(self):
        for name in qa.SCENARIOS:
            record = read(name + "-final.json")
            launch = read(name + "-launch.json")
            with self.subTest(name=name):
                self.assertEqual(launch["exitCode"], 0)
                raw = (EVIDENCE / (name + "-final.json")).read_bytes()
                self.assertEqual(hashlib.sha256(raw).hexdigest(), launch["reportSha256"])
                self.assertEqual(record["codeDrift"], [])
                for relative, expected in record["programSha256"].items():
                    self.assertEqual(historical_sha256(relative), expected, relative)

    def test_origin_wire_hash_counts_match_existing_ledger(self):
        for name in qa.SCENARIOS:
            record = read(name + "-final.json")
            state, calls, replies, arms = qa.expected_scenario(name)
            with self.subTest(name=name):
                proof = record["provenance"]
                self.assertEqual(record["trial"]["state"], state)
                self.assertEqual(len(record["trial"]["arms"]), arms)
                self.assertEqual(record["origin"]["accepted"], calls)
                for key in ("providerReservations", "egressGrants", "requestViewRows", "originRawByteMatches"):
                    self.assertEqual(proof[key], calls)
                self.assertEqual(proof["brokerResponsesObserved"], replies)
                self.assertEqual(proof["nativeAdmissions"], 1)
                self.assertEqual(proof["nativeToolCalls"], 0)
                self.assertEqual(proof["canonicalDBIntegrity"], "ok")

    def test_shutdown_and_nonpromotion_are_explicit(self):
        for name in qa.SCENARIOS:
            record = read(name + "-final.json")
            with self.subTest(name=name):
                self.assertTrue(record["gateway"]["cleanShutdown"])
                self.assertEqual(record["gateway"]["exitCode"], 0)
                self.assertEqual(record["gateway"]["nonLoopbackAttemptsBlocked"], 0)
                self.assertEqual(record["broker"]["exitCode"], 0)
                self.assertTrue(record["broker"]["socketRemoved"])
                self.assertEqual(record["broker"]["activeRequests"], 0)
                self.assertTrue(record["operatorSentinelsUnchanged"])
                self.assertFalse(record["newModelInferenceVerified"])
                self.assertFalse(record["independentSkillTransferVerified"])
                self.assertFalse(record["activeMemoryChanged"])
                self.assertFalse(record["isolatedToolExecuted"])
                self.assertEqual(record["paidCalls"], 0)

    def test_failure_controls_have_no_extra_dispatch_on_repeat(self):
        for name in ("budget-limit", "candidate-disconnect", "review-revoked"):
            record = read(name + "-final.json")
            with self.subTest(name=name):
                self.assertEqual(record["trial"]["replayAddedReservations"], 0)
                self.assertNotIn("localScore", record["trial"])
                self.assertFalse(record["trial"]["realModelInferenceVerified"])
        self.assertEqual(read("budget-limit-final.json")["trial"]["reason"], "token_exposure_limit")
        self.assertEqual(read("review-revoked-final.json")["trial"]["duplicateRequestStatus"], 409)
        self.assertNotIn("candidate", read("review-revoked-final.json")["origin"]["kinds"])

    def test_private_dependencies_pinned_and_not_system_installed(self):
        environment = read("environment-verified.json")
        self.assertEqual(environment["sourcePin"], "eb75627faf532fa6ffbdae59a0d14b0b385fc780")
        self.assertEqual(environment["runtimePython"], "3.14.3")
        self.assertEqual(environment["nodeVersion"], "v26.7.0")
        self.assertEqual(environment["dependencyVersions"]["aiohttp"], "3.14.3")
        self.assertTrue(environment["dependencyBuild"]["frozen"])
        self.assertFalse(environment["systemWideInstallPerformed"])
        self.assertFalse(environment["dockerInstalledForThisWork"])

    def test_initial_failures_preserved_as_failures(self):
        for name in ("normal-initial.json", "normal-brokerpath-2.json", "normal-auth-3.json"):
            record = read(name)
            with self.subTest(name=name):
                self.assertEqual(record["result"], "FAIL")
                self.assertTrue(record["errors"])
        self.assertEqual(read("normal-budget4-4.json")["result"], "PASS")


if __name__ == "__main__":
    unittest.main(verbosity=2)
