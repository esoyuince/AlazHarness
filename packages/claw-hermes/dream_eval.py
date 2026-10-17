"""D2B bounded paired held-out scorer. Does not call a model or promote memory.

Sealing locks an answer key digest before response artifacts are accepted. The
scorer is purely deterministic and NEVER treats untrusted response artifacts as
authenticated model trials.
"""
from __future__ import annotations
import hashlib
import hmac
import json
import re
from pathlib import Path

HEX64 = re.compile(r"[a-f0-9]{64}\Z")
CASE_ID = re.compile(r"[a-z][a-z0-9_-]{2,31}\Z")
CANDIDATE_ID = re.compile(r"dc_[a-f0-9]{64}\Z")
REVISION_ID = re.compile(r"rv_[a-f0-9]{64}\Z")
PLAN_ID = re.compile(r"ev_[a-f0-9]{64}\Z")
POLICY = {"scorer": "exact_strip_v1", "minimumCases": 12,
          "minimumWins": 3, "maximumRegressions": 0}
PLAN_FIELDS = {"version", "family", "review", "cases", "trainingPromptDigests",
               "truthCommitment", "evaluatorSourceSha256", "policy", "planId"}
REVIEW_FIELDS = {"batchId", "batchDigest", "candidateId", "revision"}


class EvaluationRejected(ValueError):
    pass


def ensure(condition, reason):
    if not condition:
        raise EvaluationRejected(reason)


def canonical(value):
    try:
        result = json.dumps(value, ensure_ascii=False, sort_keys=True,
                            separators=(",", ":"), allow_nan=False).encode("utf-8")
    except (TypeError, ValueError, UnicodeError):
        raise EvaluationRejected("invalid_evaluation_json") from None
    return result


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def text(value, maximum=2048):
    ensure(type(value) is str and 0 < len(value.encode("utf-8")) <= maximum
           and "\x00" not in value and value.strip() != "",
           "invalid_evaluation_text")
    return value


def review_binding(review, candidate_id):
    """The caller must obtain review from the live authenticated D2A read.

    This pure function cannot authenticate a caller-supplied review snapshot.
    """
    ensure(type(review) is dict and type(review.get("version")) is int
           and review["version"] == 1,
           "unverified_review_snapshot")
    ensure(type(candidate_id) is str and CANDIDATE_ID.fullmatch(candidate_id),
           "invalid_review_candidate")
    binding = {"batchId": review.get("batchId"),
               "batchDigest": review.get("batchDigest"),
               "candidateId": candidate_id, "revision": review.get("revision")}
    ensure(type(binding["batchId"]) is str
           and HEX64.fullmatch(binding["batchId"])
           and type(binding["batchDigest"]) is str
           and HEX64.fullmatch(binding["batchDigest"])
           and type(binding["revision"]) is str
           and REVISION_ID.fullmatch(binding["revision"]),
           "unverified_review_identity")
    for field in ("activeMemoryChanged", "conclusionVerified",
                  "skillTransferVerified", "grantsExecutionPermission",
                  "independentOutcomeVerified", "modelInferenceQualityVerified",
                  "automaticTrigger"):
        ensure(review.get(field) is False, "review_misstates_authority")
    ensure(review.get("evaluationStatus") == "not_run"
           and type(review.get("additionalModelCalls")) is int
           and review["additionalModelCalls"] == 0,
           "review_misstates_evaluation")
    accepted = review.get("acceptedForIndependentEvaluation")
    decisions = review.get("decisions")
    ensure(type(accepted) is list and candidate_id in accepted
           and len(accepted) == len(set(accepted))
           and type(decisions) is list,
           "candidate_not_accepted_for_testing")
    matches = [d for d in decisions if type(d) is dict
               and d.get("candidateId") == candidate_id
               and d.get("decision") == "accept_for_testing"
               and d.get("reasonCode") == "evidence_sufficient_to_test"]
    ensure(len(matches) == 1, "review_decision_not_confirmed")
    return binding


def check_training(training):
    ensure(type(training) is list and 4 <= len(training) <= 128,
           "invalid_training_sample_count")
    hashes = []
    for prompt in training:
        hashes.append(digest(text(prompt)))
    ensure(len(set(hashes)) == len(hashes), "duplicate_training_prompt")
    return sorted(hashes)


def check_cases(cases, training_hashes):
    ensure(type(cases) is list and 12 <= len(cases) <= 48,
           "invalid_heldout_size")
    validated = []
    for case in cases:
        ensure(type(case) is dict and set(case) == {"caseId", "prompt"},
               "invalid_heldout_shape")
        case_id = case["caseId"]
        ensure(type(case_id) is str and CASE_ID.fullmatch(case_id),
               "invalid_heldout_case_id")
        prompt = text(case["prompt"])
        validated.append({"caseId": case_id, "prompt": prompt})
    ids = [c["caseId"] for c in validated]
    hashes = [digest(c["prompt"]) for c in validated]
    ensure(len(ids) == len(set(ids)), "duplicate_heldout_case_id")
    ensure(len(hashes) == len(set(hashes)), "duplicate_heldout_prompt")
    ensure(not set(hashes).intersection(training_hashes),
           "heldout_contaminated_by_training")
    return sorted(validated, key=lambda c: c["caseId"])


def check_truth(truth, case_ids):
    ensure(type(truth) is dict and set(truth) == {"version", "answers"}
           and type(truth["version"]) is int and truth["version"] == 1
           and type(truth["answers"]) is list, "invalid_truth_shape")
    entries = []
    for item in truth["answers"]:
        ensure(type(item) is dict and set(item) == {"caseId", "answer"},
               "invalid_truth_item")
        cid = item["caseId"]
        ensure(type(cid) is str and CASE_ID.fullmatch(cid),
               "invalid_truth_case_id")
        entries.append({"caseId": cid, "answer": text(item["answer"], 128)})
    ids = [e["caseId"] for e in entries]
    ensure(len(ids) == len(set(ids)) and set(ids) == set(case_ids),
           "truth_coverage_mismatch")
    # A constant oracle would make an apparently successful comparison trivial.
    ensure(len({e["answer"] for e in entries}) >= 3,
           "truth_labels_insufficiently_varied")
    return {"version": 1, "answers": sorted(entries, key=lambda e: e["caseId"])}


def oracle_commitment(truth, oracle_key):
    # The random key stays ONLY in the operator's private oracle-key file.
    # Publishing a plain digest of 3-label answers makes brute-force cheap.
    ensure(type(oracle_key) is str and HEX64.fullmatch(oracle_key),
           "invalid_oracle_key")
    return hmac.new(bytes.fromhex(oracle_key), canonical(truth),
                    hashlib.sha256).hexdigest()


def evaluator_source_digest():
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def seal(review, candidate_id, family, training, cases, truth, oracle_key):
    binding = review_binding(review, candidate_id)
    family = text(family, 64)
    ensure(CASE_ID.fullmatch(family), "invalid_evaluation_family")
    training_hashes = check_training(training)
    cases = check_cases(cases, training_hashes)
    checked_truth = check_truth(truth, [c["caseId"] for c in cases])
    draft = {"version": 1, "family": family, "review": binding,
             "cases": cases, "trainingPromptDigests": training_hashes,
             "truthCommitment": oracle_commitment(checked_truth, oracle_key),
             "evaluatorSourceSha256": evaluator_source_digest(),
             "policy": POLICY.copy()}
    ensure(len(canonical(draft)) <= 65536, "evaluation_plan_limit")
    return draft | {"planId": "ev_" + digest(draft)}


def _validated_plan(plan):
    ensure(type(plan) is dict and set(plan) == PLAN_FIELDS
           and type(plan["version"]) is int and plan["version"] == 1,
           "invalid_evaluation_plan")
    ensure(type(plan["policy"]) is dict and plan["policy"] == POLICY,
           "unsupported_evaluator_policy")
    ensure(type(plan["planId"]) is str and PLAN_ID.fullmatch(plan["planId"]),
           "invalid_evaluation_plan_id")
    raw = {k: v for k, v in plan.items() if k != "planId"}
    ensure(plan["planId"] == "ev_" + digest(raw), "evaluation_plan_tampered")
    ensure(type(plan["family"]) is str and CASE_ID.fullmatch(plan["family"]),
           "invalid_evaluation_family")
    ensure(type(plan["review"]) is dict and set(plan["review"]) == REVIEW_FIELDS,
           "invalid_plan_review_binding")
    assert_ids = plan["review"]
    ensure(type(assert_ids["batchId"]) is str and HEX64.fullmatch(assert_ids["batchId"])
           and type(assert_ids["candidateId"]) is str
           and CANDIDATE_ID.fullmatch(assert_ids["candidateId"])
           and type(assert_ids["revision"]) is str
           and REVISION_ID.fullmatch(assert_ids["revision"])
           and type(assert_ids["batchDigest"]) is str
           and HEX64.fullmatch(assert_ids["batchDigest"]),
           "invalid_plan_review_binding")
    digests = plan["trainingPromptDigests"]
    ensure(type(digests) is list and 4 <= len(digests) <= 128
           and all(type(h) is str and HEX64.fullmatch(h) for h in digests)
           and len(digests) == len(set(digests)) and digests == sorted(digests),
           "invalid_plan_training_digests")
    expected = check_cases(plan["cases"], digests)
    ensure(plan["cases"] == expected
           and type(plan["truthCommitment"]) is str
           and HEX64.fullmatch(plan["truthCommitment"])
           and type(plan["evaluatorSourceSha256"]) is str
           and HEX64.fullmatch(plan["evaluatorSourceSha256"]),
           "invalid_plan_cases")
    ensure(len(canonical(plan)) <= 65536, "evaluation_plan_limit")
    ensure(plan["evaluatorSourceSha256"] == evaluator_source_digest(),
           "evaluator_code_changed_after_seal")
    return plan


def responses(answer_file, arm, plan):
    ensure(type(answer_file) is dict
           and set(answer_file) == {"version", "planId", "arm", "answers"}
           and type(answer_file["version"]) is int and answer_file["version"] == 1
           and answer_file["planId"] == plan["planId"]
           and answer_file["arm"] == arm and type(answer_file["answers"]) is list,
           "invalid_trial_artifact")
    selected = {}
    for entry in answer_file["answers"]:
        ensure(type(entry) is dict and set(entry) == {"caseId", "answer"},
               "invalid_trial_answer")
        case_id = entry["caseId"]
        ensure(type(case_id) is str and CASE_ID.fullmatch(case_id)
               and case_id not in selected, "duplicate_trial_answer")
        selected[case_id] = text(entry["answer"], 512).strip()
    ensure(set(selected) == {c["caseId"] for c in plan["cases"]},
           "trial_response_coverage_mismatch")
    return selected


def grade(plan, review, truth, baseline, candidate, oracle_key):
    """Score external answer artifacts. Authentic model execution NOT established."""
    _validated_plan(plan)
    current = review_binding(review, plan["review"]["candidateId"])
    ensure(current == plan["review"], "review_changed_after_plan_sealed")
    checked_truth = check_truth(truth, [c["caseId"] for c in plan["cases"]])
    ensure(hmac.compare_digest(oracle_commitment(checked_truth, oracle_key),
                               plan["truthCommitment"]),
           "sealed_truth_commitment_mismatch")
    actual = {a["caseId"]: a["answer"] for a in checked_truth["answers"]}
    base = responses(baseline, "baseline", plan)
    treatment = responses(candidate, "candidate", plan)
    bc = tc = wins = regressions = both_wrong = 0
    for case in plan["cases"]:
        key = case["caseId"]
        before = base[key] == actual[key]
        after = treatment[key] == actual[key]
        bc += int(before)
        tc += int(after)
        wins += int(after and not before)
        regressions += int(before and not after)
        both_wrong += int(not before and not after)
    delta = tc - bc
    observed_gain = (wins >= POLICY["minimumWins"] and
                     regressions <= POLICY["maximumRegressions"] and delta > 0)
    # An operator can write arbitrary response JSON. There is no broker receipt,
    # model version attestation, original task-gold secrecy attestation, or
    # execution isolation proof. Never assert genuine learned skill from this.
    return {"version": 1, "planId": plan["planId"], "batchId": current["batchId"],
            "candidateId": current["candidateId"],
            "reviewRevision": current["revision"], "taskCount": len(plan["cases"]),
            "baselineCorrect": bc, "candidateCorrect": tc, "netGain": delta,
            "wins": wins, "regressions": regressions, "bothWrong": both_wrong,
            "tiesCorrect": bc - regressions,
            "observedLocalGainAgainstLockedOracle": observed_gain,
            "assessmentState": "offline_artifact_score_only",
            "responseOrigin": "unverified_external_artifacts",
            "answerKeyCommitmentVerified": True, "evaluatorSourceVerified": True,
            "pairedCoverageVerified": True,
            "trainingOverlapChecked": True,
            "realModelExecutionVerified": False,
            "independentOutcomeVerified": False, "skillTransferVerified": False,
            "modelInferenceQualityVerified": False, "conclusionVerified": False,
            "promotableMemoryProposal": False, "usableAsMemory": False,
            "activeMemoryChanged": False, "grantsExecutionPermission": False,
            "automaticTrigger": False, "additionalModelCalls": 0}
