"""Independent audit contracts. Synthetic records only; no agents or databases."""
import copy
import importlib.util
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("gateway_checkpoint_audit",ROOT/"scripts/qa/gateway_checkpoint_audit.py")
a=importlib.util.module_from_spec(spec)
spec.loader.exec_module(a)

def stamp(row):
    row.pop("digest",None)
    row["digest"]=a.sha(a.canonical(row))
    return row

def fixture(scenario="completed"):
    count,arms=(4,2) if scenario=="completed" else (3,1)
    common={"version":1,"scope":"synthetic-scope","binding":"synthetic-binding","policy":"synthetic-policy"}
    owned={**common,"epoch":1,"instance":"synthetic-instance"}
    claims=[];grants=[];views=[]
    for i in range(count):
        ticket=f"{i+1:032x}";fingerprint=a.sha(f"test-request-{i}".encode())
        claims.append(stamp({**owned,"ticket":ticket,"kind":"provider","state":"settled","outcome":"response",
                             "fingerprint":fingerprint,"tokens":163840,"costMicrousd":196608}))
        grant=stamp({**owned,"ticket":ticket,"fingerprint":fingerprint,"brokerId":"synthetic-broker",
                     "routeFingerprint":"synthetic-route"})
        grants.append(grant)
        views.append(stamp({**owned,"ticket":ticket,"requestDigest":fingerprint,"egressDigest":grant["digest"],
                            "brokerId":"synthetic-broker","routeFingerprint":"synthetic-route",
                            "state":"broker_response_observed","httpStatus":200,"responseContentType":"application/json",
                            "responseSha256":a.sha(f"test-response-{i}".encode()),"responseBytes":88}))
    note={"candidateId":"dc_"+"a"*64,"status":"candidate","usableAsMemory":False,"conclusionVerified":False,
          "skillTransferVerified":False,"grantsExecutionPermission":False,"citations":[{"quote":"SYNTHETIC"}]}
    dream=stamp({**owned,"state":"completed","candidates":[note],"batchId":"b"*64,
                 "providerTicket":claims[1]["ticket"],"requestDigest":claims[1]["fingerprint"],"activeMemoryChanged":False})
    review=stamp({**owned,"batchId":dream["batchId"],"batchDigest":dream["digest"],"revision":"rv_"+"c"*64,
                  "decisions":[{"candidateId":note["candidateId"],"decision":"accept_for_testing",
                                "reasonCode":"evidence_sufficient_to_test"}],"activeMemoryChanged":False})
    case_ids=[f"case_{i:02d}" for i in range(12)]
    results=[]
    for i,arm in enumerate(("baseline","candidate")[:arms],start=2):
        answer={"version":1,"arm":arm,"planId":"ev_"+"d"*64,
                "answers":[{"caseId":cid,"answer":"SCRIPTED"} for cid in case_ids]}
        v=views[i]
        results.append({"arm":arm,"ticket":v["ticket"],"answers":answer,"requestDigest":v["requestDigest"],
                        "requestViewDigest":v["digest"],"responseSha256":v["responseSha256"],
                        "responseBytes":v["responseBytes"],"responseTextSha256":a.sha(a.canonical(answer))})
    trial=stamp({**owned,"batchId":dream["batchId"],"batchDigest":dream["digest"],"reviewRevision":review["revision"],
                 "candidateId":note["candidateId"],"caseIds":case_ids,"results":results,"planId":"ev_"+"d"*64,
                 "state":"completed" if scenario=="completed" else "unknown",
                 "reason":None if scenario=="completed" else "token_exposure_limit",
                 **{k:False for k in ("activeMemoryChanged","enabledAutomaticWake","realModelExecutionVerified",
                                      "independentOutcomeVerified","skillTransferVerified","grantsExecutionPermission")}})
    records={"config":[stamp({**common,"providerCalls":count,"toolCalls":0,"quarantined":False,
                              "reservedTokens":count*163840,"reservedCostMicrousd":count*196608})],
             "claim":claims,"egress":grants,"view":views,"dream":[dream],"review":[review],"trial":[trial]}
    run_id="run_"+"e"*32
    receipt={"nativeHermesGateway":True,"originalAiohttpBroker":True,"sourcePin":a.PIN,
             "broker":{"exitCode":0,"socketRemoved":True,"activeRequests":0,
                       "counters":{"physicalAttempts":count,"responses":count}},
             "result":"PASS" if scenario=="completed" else "FAIL",
             "errors":[] if scenario=="completed" else ["token_exposure_limit"],
             "task":{"runIdSha256":a.sha(run_id.encode())},
             "origin":{"requestSha256":[v["requestDigest"] for v in views]}}
    ready={"epoch":1,"instance_id":"synthetic-instance","pid":42,"nonce":"synthetic-nonce","profile_bound":True}
    shutdown={"pid":42,"nonce":"synthetic-nonce","native_result":True,
              "lifecycle_completed":True,"nonloopback_attempts_blocked":0}
    task={"runId":run_id,"status":"completed","observed":{"status":"completed","output":"SYNTHETIC final answer"}}
    admission={"request_id":run_id,"target_session_id":run_id,"status":"terminal","outcome":"completed"}
    return records,receipt,ready,shutdown,task,admission

class AuditContracts(unittest.TestCase):
    def setUp(self):
        self.args=fixture()
        self.r=self.args[0]
    def verify(self):return a.validate(*self.args,scenario="completed")
    def test_complete_chain_is_consistent_not_learning(self):
        result=self.verify()
        self.assertTrue(result["storedChainConsistent"])
        self.assertEqual(result["providerClaims"],4)
        self.assertEqual(result["reservedTokens"],655360)
        self.assertFalse(result["independentLearningVerified"])
        self.assertFalse(result["responseBytesRehashedFromOriginalWire"])
        self.assertFalse(result["numericScoreIndependentlyRegraded"])
    def test_previous_budget_refusal_stays_unknown(self):
        result=a.validate(*fixture("budget-refused"),scenario="budget-refused")
        self.assertEqual((result["providerClaims"],result["retainedArms"],result["dbTrialState"]),(3,1,"unknown"))
        self.assertEqual(result["reservedTokens"],491520)
    def test_admission_status_distinct_from_outcome(self):
        self.args[-1]["status"]="completed"
        with self.assertRaisesRegex(a.AuditRejected,"native_task_join_mismatch"):self.verify()
    def test_missing_claim_rejected(self):
        self.r["claim"].pop()
        with self.assertRaisesRegex(a.AuditRejected,"record_count_mismatch"):self.verify()
    def test_unsealed_record_rejected(self):
        self.r["config"][0]["reservedTokens"]=0
        with self.assertRaisesRegex(a.AuditRejected,"digest_mismatch"):self.verify()
    def test_resealed_wrong_exposure_rejected(self):
        stamp(self.r["config"][0].__ior__({"reservedTokens":1}))
        with self.assertRaisesRegex(a.AuditRejected,"budget_exposure_mismatch"):self.verify()
    def test_request_grant_fingerprint_mismatch_rejected(self):
        stamp(self.r["view"][0].__ior__({"requestDigest":"f"*64}))
        with self.assertRaisesRegex(a.AuditRejected,"request_grant_join_mismatch"):self.verify()
    def test_origin_wire_hash_mismatch_rejected(self):
        self.args[1]["origin"]["requestSha256"][0]="f"*64
        with self.assertRaisesRegex(a.AuditRejected,"origin_request_hash_mismatch"):self.verify()
    def test_response_hash_substitution_rejected(self):
        stamp(self.r["view"][2].__ior__({"responseSha256":"f"*64}))
        with self.assertRaisesRegex(a.AuditRejected,"trial_response_join_mismatch"):self.verify()
    def test_answer_file_mutation_rejected(self):
        self.r["trial"][0]["results"][0]["answers"]["answers"][0]["answer"]="FORGED"
        stamp(self.r["trial"][0])
        with self.assertRaisesRegex(a.AuditRejected,"trial_answer_digest_mismatch"):self.verify()
    def test_wrong_epoch_rejected(self):
        stamp(self.r["claim"][0].__ior__({"epoch":2}))
        with self.assertRaisesRegex(a.AuditRejected,"native_owner_mismatch"):self.verify()
    def test_review_revision_mismatch_rejected(self):
        stamp(self.r["trial"][0].__ior__({"reviewRevision":"rv_"+"f"*64}))
        with self.assertRaisesRegex(a.AuditRejected,"trial_review_join_mismatch"):self.verify()
    def test_quote_not_in_native_terminal_rejected(self):
        self.r["dream"][0]["candidates"][0]["citations"][0]["quote"]="NEVER OBSERVED"
        stamp(self.r["dream"][0])
        with self.assertRaisesRegex(a.AuditRejected,"quote_not_in_native_output"):self.verify()
    def test_fake_learning_flag_rejected(self):
        stamp(self.r["trial"][0].__ior__({"skillTransferVerified":True}))
        with self.assertRaisesRegex(a.AuditRejected,"unsupported_learning_claim"):self.verify()
    def test_wrong_shutdown_nonce_rejected(self):
        self.args[3]["nonce"]="different"
        with self.assertRaisesRegex(a.AuditRejected,"native_shutdown_unverified"):self.verify()
    def test_duplicate_json_key_rejected(self):
        with self.assertRaisesRegex(a.AuditRejected,"duplicate_json_key"):a.parse('{"n":1,"n":2}')
    def test_unknown_cannot_be_upgraded(self):
        values=fixture("budget-refused");values[1]["result"]="PASS"
        with self.assertRaisesRegex(a.AuditRejected,"refusal_was_upgraded"):
            a.validate(*values,scenario="budget-refused")
    def test_recovered_source_receipts_are_unchanged(self):
        ev=ROOT/"evidence/d2b2-gateway-custody-73c9"
        refs=json.loads((ev/"source-references.json").read_text(encoding="utf-8"))
        for name,expected in refs["originalPublicSha256"].items():
            self.assertEqual(a.sha((ev/name).read_bytes()),expected)

if __name__ == "__main__":
    unittest.main(verbosity=2)
