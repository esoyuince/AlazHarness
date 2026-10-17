"""D2 manual review of evidence-linked D1 candidates. Not active memory."""
from __future__ import annotations
from dataclasses import dataclass
from dream import DreamService, digest, hexid, require
from execution_budget import ExecutionDenied, seal
from recovery_inspector import _json, _load

PREFIX = "alaz.dream.review.v1."
DECISIONS = ("accept_for_testing", "reject", "defer")
REASONS = ("evidence_sufficient_to_test", "duplicate", "conflict",
           "insufficient_evidence", "out_of_scope", "needs_benchmark",
           "operator_deferred")
EVENT_KEYS = {"seq", "candidateId", "decision", "reasonCode", "fromRevision", "toRevision"}
RECORD_KEYS = {"version", "scope", "binding", "policy", "batchId", "batchDigest",
               "epoch", "instance", "mode", "sequence", "events", "decisions",
               "revision", "activeMemoryChanged", "conclusionVerified",
               "skillTransferVerified", "grantsExecutionPermission"}


@dataclass(frozen=True)
class ReviewPolicy:
    enabled: bool = False
    max_events: int = 32

    def __post_init__(self):
        require(type(self.enabled) is bool, "dream_review_boolean_required")
        require(type(self.max_events) is int and 1 <= self.max_events <= 64,
                "dream_review_event_limit")


def _is_revision(value):
    return type(value) is str and hexid(value, prefix="rv_")


def _decision(decision, reason):
    require(type(decision) is str and decision in DECISIONS,
            "dream_review_invalid_decision")
    require(type(reason) is str and reason in REASONS,
            "dream_review_invalid_reason")
    if decision == "accept_for_testing":
        require(reason == "evidence_sufficient_to_test",
                "dream_review_insufficient_reason")


def _seed(ledger, batch):
    return "rv_" + digest(["alaz-review-v1", ledger.context.scope,
                           ledger.context.binding, ledger.policy.fingerprint,
                           batch["batchId"], batch["digest"]])


def _next(previous, seq, cid, decision, reason):
    return "rv_" + digest([previous, seq, cid, decision, reason])


class DreamReviewService:
    """Explicit operator-credential review only, no model or tool calls."""
    def __init__(self, settings, dream, *, config_reader=None):
        require(type(settings) is dict, "dream_review_settings_required")
        settings = _load(_json(settings), 4096)
        try:
            self.policy = ReviewPolicy(**settings)
        except TypeError:
            raise ExecutionDenied("dream_review_invalid_settings") from None
        self.settings_digest = digest(settings)
        self.config_reader = config_reader or (lambda: settings)
        self.dream = dream
        if self.policy.enabled:
            require(type(dream) is DreamService and dream.policy.enabled,
                    "dream_review_dream_required")
            require(dream.boundary is not None and dream.boundary.broker is not None,
                    "dream_review_broker_required")

    def check_config(self):
        require(self.policy.enabled, "dream_review_disabled")
        self.dream.check_config()
        try:
            actual = digest(_load(_json(self.config_reader()), 4096))
        except Exception:
            actual = ""
        require(actual == self.settings_digest, "dream_review_settings_changed")

    def _batch(self, conn, ledger, batch_id):
        require(hexid(batch_id), "dream_review_invalid_batch")
        # D1 validates owner/epoch, all candidate IDs, native provider claim,
        # candidate flags and quotation metadata in this SAME DB transaction.
        history = self.dream._history(conn, ledger)
        batch = next((r for r in history if r["batchId"] == batch_id), None)
        require(batch is not None, "dream_review_batch_missing")
        require(batch["state"] == "completed", "dream_review_terminal_required")
        ids = sorted(n["candidateId"] for n in batch["candidates"])
        require(len(ids) == len(set(ids)), "dream_review_duplicate_candidate")
        return batch, ids

    def _stored(self, conn, ledger, batch, ids):
        key = PREFIX + ledger.context.scope + "." + batch["batchId"]
        existing = conn.execute("SELECT value FROM state_meta WHERE key=?", (key,)).fetchone()
        seed = _seed(ledger, batch)
        if existing is None:
            return {"sequence": 0, "events": [], "decisions": [], "revision": seed}, key, seed
        row = _load(existing[0], 65536)
        require(type(row) is dict and set(row) == RECORD_KEYS | {"digest"} and
                row["digest"] == seal(row)["digest"], "dream_review_history_invalid")
        require((row["version"], row["scope"], row["binding"], row["policy"],
                 row["batchId"], row["batchDigest"], row["epoch"],
                 row["instance"], row["mode"]) ==
                (1, ledger.context.scope, ledger.context.binding,
                 ledger.policy.fingerprint, batch["batchId"], batch["digest"],
                 ledger.context.epoch, ledger.context.instance_id,
                 "manual_candidate_review_only"), "dream_review_history_invalid")
        require(all(row[k] is False for k in
                    ("activeMemoryChanged", "conclusionVerified",
                     "skillTransferVerified", "grantsExecutionPermission")),
                "dream_review_authority_invalid")
        events = row["events"]
        require(type(events) is list and len(events) <= self.policy.max_events and
                type(row["sequence"]) is int and row["sequence"] == len(events),
                "dream_review_history_invalid")
        rev, decisions = seed, {}
        for seq, e in enumerate(events, start=1):
            require(type(e) is dict and set(e) == EVENT_KEYS and
                    type(e["seq"]) is int and e["seq"] == seq and
                    type(e["candidateId"]) is str and e["candidateId"] in ids and
                    e["fromRevision"] == rev and _is_revision(e["toRevision"]),
                    "dream_review_history_invalid")
            _decision(e["decision"], e["reasonCode"])
            rev = _next(rev, seq, e["candidateId"], e["decision"], e["reasonCode"])
            require(e["toRevision"] == rev, "dream_review_history_invalid")
            decisions[e["candidateId"]] = {"candidateId": e["candidateId"],
                 "decision": e["decision"], "reasonCode": e["reasonCode"]}
        require(type(row["decisions"]) is list and
                row["decisions"] == [decisions[k] for k in sorted(decisions)] and
                row["revision"] == rev, "dream_review_history_invalid")
        return row, key, seed

    @staticmethod
    def _view(row, batch, ids):
        accepted = sorted(d["candidateId"] for d in row["decisions"]
                          if d["decision"] == "accept_for_testing")
        return {"version": 1, "batchId": batch["batchId"],
                "batchDigest": batch["digest"], "revision": row["revision"],
                "candidateCount": len(ids), "reviewedCount": len(row["decisions"]),
                "eventCount": row["sequence"], "decisions": list(row["decisions"]),
                "acceptedForIndependentEvaluation": accepted,
                "evaluationStatus": "not_run", "independentOutcomeVerified": False,
                "modelInferenceQualityVerified": False,
                "activeMemoryChanged": False, "conclusionVerified": False,
                "skillTransferVerified": False, "grantsExecutionPermission": False,
                "automaticTrigger": False, "additionalModelCalls": 0}

    def inspect(self, batch_id):
        self.check_config()
        ledger = self.dream.boundary.ledger()
        def tx(conn):
            self.check_config()
            batch, ids = self._batch(conn, ledger, batch_id)
            row, _, _ = self._stored(conn, ledger, batch, ids)
            return self._view(row, batch, ids)
        return ledger._write(tx)

    def decide(self, batch_id, candidate_id, decision, reason_code, expected_revision):
        self.check_config()
        require(hexid(batch_id), "dream_review_invalid_batch")
        require(hexid(candidate_id, prefix="dc_"), "dream_review_invalid_candidate")
        require(_is_revision(expected_revision), "dream_review_invalid_revision")
        _decision(decision, reason_code)
        ledger = self.dream.boundary.ledger()
        def tx(conn):
            self.check_config()
            batch, ids = self._batch(conn, ledger, batch_id)
            require(candidate_id in ids, "dream_review_unknown_candidate")
            row, key, _ = self._stored(conn, ledger, batch, ids)
            require(row["revision"] == expected_revision,
                    "dream_review_revision_conflict")
            earlier = next((d for d in row["decisions"]
                            if d["candidateId"] == candidate_id), None)
            if earlier is not None and (earlier["decision"], earlier["reasonCode"]) == (decision, reason_code):
                return self._view(row, batch, ids) | {"replayed": True, "reviewEventWritten": False}
            require(row["sequence"] < self.policy.max_events,
                    "dream_review_event_limit")
            seq = row["sequence"] + 1
            revision = _next(row["revision"], seq, candidate_id, decision, reason_code)
            event = {"seq": seq, "candidateId": candidate_id, "decision": decision,
                     "reasonCode": reason_code, "fromRevision": row["revision"],
                     "toRevision": revision}
            decisions = {d["candidateId"]: dict(d) for d in row["decisions"]}
            decisions[candidate_id] = {"candidateId": candidate_id,
                 "decision": decision, "reasonCode": reason_code}
            update = seal({"version": 1, "scope": ledger.context.scope,
                "binding": ledger.context.binding, "policy": ledger.policy.fingerprint,
                "batchId": batch_id, "batchDigest": batch["digest"],
                "epoch": ledger.context.epoch, "instance": ledger.context.instance_id,
                "mode": "manual_candidate_review_only", "sequence": seq,
                "events": row["events"] + [event],
                "decisions": [decisions[k] for k in sorted(decisions)],
                "revision": revision, "activeMemoryChanged": False,
                "conclusionVerified": False, "skillTransferVerified": False,
                "grantsExecutionPermission": False})
            require(len(_json(update).encode("utf-8")) <= 65536,
                    "dream_review_record_limit")
            if row["sequence"]:
                conn.execute("UPDATE state_meta SET value=? WHERE key=?",
                             (_json(update), key))
            else:
                conn.execute("INSERT INTO state_meta(key,value) VALUES(?,?)",
                             (key, _json(update)))
            return self._view(update, batch, ids) | {"replayed": False, "reviewEventWritten": True}
        return ledger._write(tx)

    def diff(self, batch_id, base_revision):
        """No model call: compare against a *known* prior revision only."""
        self.check_config()
        require(_is_revision(base_revision), "dream_review_invalid_revision")
        ledger = self.dream.boundary.ledger()
        def tx(conn):
            self.check_config()
            batch, ids = self._batch(conn, ledger, batch_id)
            row, _, initial = self._stored(conn, ledger, batch, ids)
            before, matched = {}, initial == base_revision
            for e in row["events"]:
                if matched:
                    break
                before[e["candidateId"]] = {"candidateId": e["candidateId"],
                    "decision": e["decision"], "reasonCode": e["reasonCode"]}
                if e["toRevision"] == base_revision:
                    matched = True
            require(matched, "dream_review_unknown_baseline")
            after = {d["candidateId"]: d for d in row["decisions"]}
            added = sorted(k for k in after if k not in before)
            changed = sorted(k for k in before if k in after and before[k] != after[k])
            unchanged = sorted(k for k in before if k in after and before[k] == after[k])
            withdrawn = sorted(k for k in before if
                before[k]["decision"] == "accept_for_testing" and
                (k not in after or after[k]["decision"] != "accept_for_testing"))
            newly_accepted = sorted(k for k in set(added + changed)
                if after[k]["decision"] == "accept_for_testing")
            return {"version": 1, "batchId": batch_id,
                "baseRevision": base_revision, "currentRevision": row["revision"],
                "hasChanges": bool(added or changed),
                "addedCandidateDecisions": added, "changedCandidateDecisions": changed,
                "unchangedCandidateDecisions": unchanged,
                "withdrawnFromTesting": withdrawn,
                "newlyAcceptedForIndependentEvaluation": newly_accepted,
                "independentEvaluationRequired": bool(newly_accepted),
                "evaluationStatus": "not_run", "independentOutcomeVerified": False,
                "promotableMemoryProposal": False, "activeMemoryChanged": False,
                "skillTransferVerified": False, "additionalModelCalls": 0}
        return ledger._write(tx)
