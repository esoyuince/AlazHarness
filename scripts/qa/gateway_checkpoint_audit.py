"""Read-only independent audit of recovered, stopped AF21 Gateway checkpoints.

No product imports, Gateway start, provider request, live review change or
inference. Verifies stored native rows against each other and published receipts.
Hashes are consistency checks, not adversarial remote attestations.
"""
from __future__ import annotations
import argparse
from contextlib import closing
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3

ROOT = Path(__file__).resolve().parents[2]
PIN = "eb75627faf532fa6ffbdae59a0d14b0b385fc780"
PREFIX = {
    "config": "alaz.execution.config.v1.", "claim": "alaz.execution.claim.v1.",
    "egress": "alaz.execution.egress.v1.", "view": "alaz.evidence.request.v1.",
    "dream": "alaz.dream.candidates.v1.", "review": "alaz.dream.review.v1.",
    "trial": "alaz.dream.trial.v1.",
}
CASES = {
    "completed": ("gateway-d2b2-normal4-af21", "normal-budget4-4.json", 4, 2),
    "budget-refused": ("gateway-d2b2-normal3-af21", "normal-auth-3.json", 3, 1),
}

class AuditRejected(ValueError):
    pass

def require(value, reason):
    if not value:
        raise AuditRejected(reason)

def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def _pairs(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "duplicate_json_key")
        result[key] = value
    return result

def parse(raw):
    require(len(raw) <= 262144, "json_byte_limit")
    return json.loads(raw, object_pairs_hook=_pairs,
                      parse_constant=lambda _: (_ for _ in ()).throw(AuditRejected("nonfinite_json")))

def sealed(row):
    require(type(row) is dict, "invalid_native_record")
    require(row.get("digest") == sha(canonical({k:v for k,v in row.items() if k != "digest"})),
            "native_record_digest_mismatch")
    require(type(row.get("version")) is int and row["version"] == 1, "invalid_native_version")

def validate(records, receipt, ready, shutdown, task, admission, *, scenario):
    """Pure join validation; unit tests can mutate records without touching a DB."""
    require(scenario in CASES, "unsupported_case")
    _, _, count, arm_count = CASES[scenario]
    require(set(records) == set(PREFIX), "record_groups_incomplete")
    for name, rows in records.items():
        require(type(rows) is list and len(rows) == (count if name in ("claim", "egress", "view") else 1),
                "record_count_mismatch")
        for row in rows:
            sealed(row)
    cfg, dream, review, trial = (records[k][0] for k in ("config","dream","review","trial"))
    for rows in records.values():
        for row in rows:
            require(all(row.get(k) == cfg[k] for k in ("scope","binding","policy")), "native_scope_mismatch")
            if "epoch" in row:
                require(row["epoch"] == ready["epoch"] and row["instance"] == ready["instance_id"],
                        "native_owner_mismatch")
    require(type(ready.get("pid")) is int and ready["pid"] == shutdown.get("pid") and
            ready["nonce"] == shutdown["nonce"] and ready["profile_bound"] is True and
            shutdown["native_result"] is True and shutdown["lifecycle_completed"] is True and
            shutdown["nonloopback_attempts_blocked"] == 0, "native_shutdown_unverified")
    require(receipt["nativeHermesGateway"] is True and receipt["originalAiohttpBroker"] is True and
            receipt["sourcePin"] == PIN, "native_surface_unverified")
    require(receipt["broker"]["exitCode"] == 0 and receipt["broker"]["socketRemoved"] is True and
            receipt["broker"]["activeRequests"] == 0 and receipt["broker"]["counters"]["physicalAttempts"] == count and
            receipt["broker"]["counters"]["responses"] == count, "broker_lifecycle_mismatch")
    claims = {r["ticket"]: r for r in records["claim"]}
    grants = {r["ticket"]: r for r in records["egress"]}
    views = {r["ticket"]: r for r in records["view"]}
    require(len(claims) == len(grants) == len(views) == count and set(claims) == set(grants) == set(views),
            "ticket_sets_mismatch")
    for ticket, claim in claims.items():
        grant, view = grants[ticket], views[ticket]
        require(claim["kind"] == "provider" and claim["state"] == "settled" and claim["outcome"] == "response",
                "unsettled_or_nonprovider_claim")
        require(claim["fingerprint"] == grant["fingerprint"] == view["requestDigest"] and
                view["egressDigest"] == grant["digest"] and
                view["brokerId"] == grant["brokerId"] and view["routeFingerprint"] == grant["routeFingerprint"],
                "request_grant_join_mismatch")
        require(view["state"] == "broker_response_observed" and view["httpStatus"] == 200 and
                view["responseContentType"] == "application/json" and
                re.fullmatch("[a-f0-9]{64}",view["responseSha256"]), "unobserved_provider_response")
    require(cfg["providerCalls"] == count and cfg["toolCalls"] == 0 and cfg["quarantined"] is False,
            "budget_counter_mismatch")
    require(cfg["reservedTokens"] == sum(r["tokens"] for r in claims.values()) == count * 163840 and
            cfg["reservedCostMicrousd"] == sum(r["costMicrousd"] for r in claims.values()) == count * 196608,
            "budget_exposure_mismatch")
    require(task["status"] == "completed" and task["observed"]["status"] == "completed" and
            admission["request_id"] == admission["target_session_id"] == task["runId"] and
            admission["status"] == "terminal" and admission["outcome"] == "completed",
            "native_task_join_mismatch")
    require(dream["state"] == "completed" and len(dream["candidates"]) == 1 and
            dream["providerTicket"] in claims and
            dream["requestDigest"] == views[dream["providerTicket"]]["requestDigest"], "dream_provider_join_mismatch")
    note = dream["candidates"][0]
    require(note["status"] == "candidate" and note["usableAsMemory"] is False and
            all(note[k] is False for k in ("conclusionVerified","skillTransferVerified","grantsExecutionPermission")),
            "candidate_authority_claim")
    require(all(c["quote"] and c["quote"] in task["observed"]["output"] for c in note["citations"]),
            "quote_not_in_native_output")
    require(review["batchId"] == dream["batchId"] and review["batchDigest"] == dream["digest"] and
            review["decisions"] == [{"candidateId":note["candidateId"],"decision":"accept_for_testing",
                                      "reasonCode":"evidence_sufficient_to_test"}], "review_join_mismatch")
    require(trial["batchId"] == dream["batchId"] and trial["batchDigest"] == dream["digest"] and
            trial["reviewRevision"] == review["revision"] and trial["candidateId"] == note["candidateId"],
            "trial_review_join_mismatch")
    require(len(trial["results"]) == arm_count and len(set(trial["caseIds"])) == 12 and
            [r["arm"] for r in trial["results"]] == ["baseline","candidate"][:arm_count],
            "trial_arm_mismatch")
    for result in trial["results"]:
        require(result["ticket"] in views, "trial_ticket_missing")
        view = views[result["ticket"]]
        require(result["requestViewDigest"] == view["digest"] and result["requestDigest"] == view["requestDigest"] and
                result["responseSha256"] == view["responseSha256"] and result["responseBytes"] == view["responseBytes"],
                "trial_response_join_mismatch")
        answers = result["answers"]
        require(answers["planId"] == trial["planId"] and answers["arm"] == result["arm"] and
                len(answers["answers"]) == 12 and
                {a["caseId"] for a in answers["answers"]} == set(trial["caseIds"]) and
                result["responseTextSha256"] == sha(canonical(answers)), "trial_answer_digest_mismatch")
    for row in (dream,review,trial):
        require(row["activeMemoryChanged"] is False, "memory_promotion_claim")
    require(all(trial[k] is False for k in ("enabledAutomaticWake","realModelExecutionVerified",
            "independentOutcomeVerified","skillTransferVerified","grantsExecutionPermission")),
            "unsupported_learning_claim")
    if scenario == "completed":
        require(trial["state"] == "completed" and trial["reason"] is None and
                receipt["result"] == "PASS" and receipt["errors"] == [] and
                sha(task["runId"].encode()) == receipt["task"]["runIdSha256"], "completed_receipt_mismatch")
        require(set(receipt["origin"]["requestSha256"]) == {v["requestDigest"] for v in views.values()},
                "origin_request_hash_mismatch")
    else:
        require(trial["state"] == "unknown" and trial["reason"] == "token_exposure_limit" and
                receipt["result"] == "FAIL" and "token_exposure_limit" in str(receipt["errors"]),
                "refusal_was_upgraded")
    return {"scenario":scenario, "storedChainConsistent":True,
            "providerClaims":count,"retainedArms":arm_count,
            "reservedTokens":cfg["reservedTokens"],"reservedCostMicrousd":cfg["reservedCostMicrousd"],
            "budgetIsDeclaredExposureNotInvoice":True,"nativeTaskAndQuoteJoinVerified":True,
            "nativeRowDigestAndOwnerJoinsVerified":True,"dbTrialState":trial["state"],
            "responseBytesRehashedFromOriginalWire":False,"numericScoreIndependentlyRegraded":False,
            "realModelInferenceVerified":False,"independentLearningVerified":False}

def read_case(case, receipt_path, scenario):
    db = case / "profile/state.db"
    before = {n:sha((case/n).read_bytes()) for n in ("profile/state.db","ready.json","shutdown.json","task-result.json")}
    ready, shutdown, task = (parse((case/n).read_bytes()) for n in ("ready.json","shutdown.json","task-result.json"))
    with closing(sqlite3.connect(db.as_uri()+"?mode=ro",uri=True)) as conn:
        conn.execute("PRAGMA query_only=ON")
        require(conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok", "native_db_integrity_failed")
        records = {name:[parse(raw) for raw, in conn.execute(
            "SELECT value FROM state_meta WHERE key GLOB ?",(prefix+"*",))] for name,prefix in PREFIX.items()}
        conn.row_factory = sqlite3.Row
        admissions = [dict(r) for r in conn.execute(
            "SELECT request_id,target_session_id,status,outcome FROM session_admissions")]
    require(len(admissions) == 1,"unexpected_native_admissions")
    result = validate(records,parse(receipt_path.read_bytes()),ready,shutdown,task,admissions[0],scenario=scenario)
    after = {n:sha((case/n).read_bytes()) for n in before}
    require(before == after,"native_source_changed_during_audit")
    return result | {"nativeInputSha256":before,"nativeInputsByteUnchanged":True,
                     "originalReceiptSha256":sha(receipt_path.read_bytes())}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-root",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    evidence=ROOT/"evidence/d2b2-gateway-custody-73c9"
    dest=args.output.resolve()
    require(dest.parent==evidence.resolve() and not dest.exists(),"new_scoped_output_required")
    runtime=args.runtime_root.resolve()
    require(runtime.name=="runtime" and runtime.parent.name=="source-workspace" and
            runtime.parent.parent.name=="alaz-harness-d2b2-gateway-af21", "unexpected_runtime_root")
    results={}
    for scenario,(dirname,filename,_,_) in CASES.items():
        case=runtime/dirname
        require(case.is_dir() and not case.is_symlink(),"native_case_missing")
        results[scenario]=read_case(case,evidence/filename,scenario)
    report={"auditVersion":1,"observedAt":datetime.now(timezone.utc).isoformat(),
            "result":"PASS_RECOVERED_RECORD_CONSISTENCY","cases":results,
            "newGatewayRuns":0,"newProviderCalls":0,"productSourceModified":False,
            "sourceRunnerAtOriginalExecutionIndependentlyAttested":False,
            "databaseHashesAreConsistencyNotCryptographicAttestation":True,
            "personalMemoryOrSkillFilesInspected":False,
            "verifierSha256":sha(Path(__file__).read_bytes())}
    with dest.open("x",encoding="utf-8") as f:json.dump(report,f,ensure_ascii=False,indent=2);f.write("\n")
    print(json.dumps({"result":report["result"],"cases":{k:(v["providerClaims"],v["dbTrialState"]) for k,v in results.items()},"newProviderCalls":0}))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
