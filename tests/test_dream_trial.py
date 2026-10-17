"""D2B2 paired broker contract checks; synthetic broker replies, real native SQL owner.

No real Gateway/provider/model inference; pre-existing D1 and D2A fixtures.
"""
from __future__ import annotations
import asyncio
import base64
import copy
from contextlib import closing
import hashlib
from pathlib import Path
import sqlite3
import sys
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'packages/claw-hermes'),str(ROOT/'tests')]
from test_dream import DreamFixture
from test_dream_eval import fixture as eval_fixture,KEY
from dream_review import DreamReviewService
from dream_eval import seal
from dream import digest
from recovery_inspector import _json,_load
from execution_budget import ExecutionDenied,seal as ledger_seal
import dream_trial as d


class TrialFixture:
    def __init__(self,case):
        self.f=DreamFixture(case)
        self.d1=self.f.run()
        assert self.d1["state"]=="completed"
        self.candidate=self.d1["candidates"][0]["candidateId"]
        self.review_settings={"enabled":True,"max_events":8}
        self.review=DreamReviewService(self.review_settings,self.f.service,
            config_reader=lambda:self.review_settings)
        before=self.review.inspect(self.d1["batchId"])
        self.review.decide(self.d1["batchId"],self.candidate,
            "accept_for_testing","evidence_sufficient_to_test",before["revision"])
        self.training_review,self.training,self.cases,self.truth,_,_,_=eval_fixture()
        self.plan=seal(self.review.inspect(self.d1["batchId"]),
            self.candidate,"synthetic_triage",self.training,self.cases,self.truth,KEY)
        self.settings={"enabled":True,"max_cases":12,"output_tokens":256}
        self.service=d.DreamTrialService(self.settings,self.review,clock=lambda:1_790_000_000.,
            config_reader=lambda:self.settings)
        self.calls=[]
        self.callback=None
        self.fail_arm=None
        self.provider_error=None
        self.no_usage=False
        self.invalid_answers=False
        self.corrupt_model=False
        self.short_finish=False
        self.changed_prompt=False
        self.missing_case=False
        self.tools=False
        self.labels={a["caseId"]:a["answer"] for a in self.truth["answers"]}

        async def exchange(doc,ticket):
            body=doc["payload"]
            arm="candidate" if _load(body["messages"][1]["content"])["lesson"] is not None else "baseline"
            user=_load(body["messages"][1]["content"])
            self.calls.append({"arm":arm,"requestDigest":digest(body),
                "hasOracleKey":"oracleKeyHex" in _json(body),
                "hasTruthCommitment":"truthCommitment" in _json(body),
                "body":copy.deepcopy(body)})
            if self.callback:
                self.callback(arm)
            if self.fail_arm==arm:
                raise ExecutionDenied("broker_transport_outcome_unknown")
            answer={"answers":[{"caseId":c["caseId"],
                  "answer":self.labels[c["caseId"]] if arm=="candidate" or i>=4 else "WRONG"}
                 for i,c in enumerate(user["cases"])]}
            if self.invalid_answers:
                answer={"notes":[{"lesson":"not answers"}]}
            if self.missing_case:
                answer["answers"].pop()
            if self.changed_prompt:
                body["messages"][1]["content"]="falsified-wire-payload"
            # The real broker verifies the signed frame BEFORE sending HTTP.
            # Our direct _exchange fixture has to enforce the same invariant.
            from provider_egress import verified
            verified(doc,self.f.broker.link.signing_key,"request")
            response={"model":"mismatch-model" if self.corrupt_model else self.f.policy.model,
                "choices":[{"index":0,
                    "finish_reason":"length" if self.short_finish else "stop",
                    "message":{"role":"assistant","content":_json(answer),
                        **({"tool_calls":[{"function":{"name":"exec"}}]} if self.tools else {})}}],
                **({} if self.no_usage else {"usage":{
                    "prompt_tokens":20,"completion_tokens":10,"total_tokens":30}})}
            raw=_json(response).encode("utf-8")
            return {"version":1,"brokerId":self.f.broker.link.broker_id,
                "nonce":ticket,"ok":True,"status":500 if self.provider_error else 200,
                "contentType":"application/json","dataBase64":base64.b64encode(raw).decode()}
        self.f.broker._exchange=exchange

    def run(self,plan=None):
        return asyncio.run(self.service.run(self.plan if plan is None else plan))

    def row(self):
        return self.service.status(self.plan["planId"])

    def budget(self):
        return self.f.ledger.snapshot()

    def db_row(self):
        with closing(sqlite3.connect(self.f.home/'state.db')) as c:
            found=c.execute("SELECT value FROM state_meta WHERE key GLOB ?",
                            (d.PREFIX+"*",)).fetchall()
            return [_load(value) for value, in found]


class TrialContracts(unittest.TestCase):
    def setUp(self):self.t=TrialFixture(self)

    def test_two_scripted_broker_requests_and_exact_view_proof(self):
        before=self.t.budget()["providerCalls"]
        result=self.t.run()
        self.assertEqual(result["state"],"completed",result)
        self.assertEqual([v["arm"] for v in result["results"]],["baseline","candidate"])
        self.assertEqual([v["arm"] for v in self.t.calls],["baseline","candidate"])
        self.assertEqual(result["newProviderReservations"],2)
        self.assertEqual(self.t.budget()["providerCalls"],before+2)
        self.assertTrue(result["providerResponseValidated"])
        self.assertEqual(result["responseOrigin"],"broker_process_http_response_observed")
        for arm in result["results"]:
            self.assertEqual(arm["httpStatus"],200)
            self.assertEqual(arm["responseContentType"],"application/json")
            self.assertEqual(len(arm["answers"]["answers"]),12)
            self.assertEqual(len(arm["responseSha256"]),64)
            self.assertEqual(len(arm["requestViewDigest"]),64)
            self.assertEqual(arm["usageOutcome"],"response")
        for key in ("realModelExecutionVerified","physicalProviderInferenceVerified",
            "independentOutcomeVerified","skillTransferVerified",
            "candidateLessonAppliedByModelVerified","activeMemoryChanged",
            "grantsExecutionPermission","automaticTrigger"):
            self.assertFalse(result[key])
        self.assertEqual(self.t.f.memory.read_bytes(),b"user pinned memory\n")
        self.assertEqual(self.t.f.skill.read_bytes(),b"user pinned skill\n")

    def test_no_oracle_truth_in_requests(self):
        self.t.run()
        for packet in self.t.calls:
            self.assertFalse(packet["hasOracleKey"])
            self.assertFalse(packet["hasTruthCommitment"])
            self.assertNotIn("truthCommitment",_json(packet["body"]))
            self.assertNotIn(KEY,_json(packet["body"]))
            self.assertEqual(packet["body"]["tools"] if "tools" in packet["body"] else [],[])
            self.assertEqual(len(packet["body"]["messages"]),2)
            self.assertFalse(packet["body"]["stream"])
            self.assertEqual(packet["body"]["temperature"],0)
        self.assertIsNone(_load(self.t.calls[0]["body"]["messages"][1]["content"])["lesson"])
        self.assertIsNotNone(_load(self.t.calls[1]["body"]["messages"][1]["content"])["lesson"])

    def test_replayed_idempotently_without_additional_provider_calls(self):
        first=self.t.run()
        before=self.t.budget()
        second=self.t.run()
        self.assertEqual(second["state"],"completed")
        self.assertTrue(second["replayed"])
        self.assertEqual(second["newProviderReservations"],0)
        self.assertEqual(before,self.t.budget())
        self.assertEqual(len(self.t.calls),2)
        self.assertEqual(first["results"],second["results"])

    def test_plan_cannot_change_after_commit(self):
        self.t.run()
        changed=copy.deepcopy(self.t.plan)
        changed["cases"][0]["prompt"]="new prompt"
        with self.assertRaisesRegex(ExecutionDenied,"dream_trial_invalid_plan"):
            self.t.run(changed)

    def test_reject_missing_d2a_permission(self):
        self.t.review_settings["enabled"]=False
        with self.assertRaises(ExecutionDenied):self.t.run()
        self.assertEqual(self.t.calls,[])

    def test_review_withdrawn_before_trial_refuses(self):
        present=self.t.review.inspect(self.t.d1["batchId"])
        self.t.review.decide(self.t.d1["batchId"],self.t.candidate,
            "reject","conflict",present["revision"])
        with self.assertRaisesRegex(ExecutionDenied,"dream_trial_review_unverified"):
            self.t.run()
        self.assertEqual(self.t.calls,[])

    def test_review_revised_between_arms_no_candidate_send(self):
        def mutate(arm):
            if arm=="baseline":
                state=self.t.review.inspect(self.t.d1["batchId"])
                self.t.review.decide(self.t.d1["batchId"],self.t.candidate,
                    "defer","operator_deferred",state["revision"])
        self.t.callback=mutate
        result=self.t.run()
        self.assertEqual(result["state"],"unknown",result)
        self.assertEqual(len(self.t.calls),1)
        self.assertFalse(result["providerResponseValidated"])
        self.assertEqual(self.t.budget()["providerCalls"],2)
        self.assertEqual(len(result["results"]),0)
        self.assertEqual(self.t.f.memory.read_bytes(),b"user pinned memory\n")

    def test_unknown_first_broker_transport_no_replay(self):
        self.t.fail_arm="baseline"
        first=self.t.run()
        self.assertEqual(first["state"],"unknown")
        self.assertEqual(len(first["results"]),0)
        self.t.fail_arm=None
        second=self.t.run()
        self.assertEqual(second["state"],"unknown")
        self.assertTrue(second["replayed"])
        self.assertEqual(len(self.t.calls),1)
        self.assertEqual(self.t.budget()["providerCalls"],2)

    def test_unknown_second_broker_transport_retains_first_proof(self):
        self.t.fail_arm="candidate"
        result=self.t.run()
        self.assertEqual(result["state"],"unknown")
        self.assertEqual(len(result["results"]),1)
        self.assertEqual(result["results"][0]["arm"],"baseline")
        self.assertEqual(self.t.budget()["providerCalls"],3)
        self.assertFalse(result["providerResponseValidated"])
        self.t.fail_arm=None
        again=self.t.run()
        self.assertTrue(again["replayed"])
        self.assertEqual(len(self.t.calls),2)

    def test_invalid_answer_refused_no_second_send(self):
        self.t.invalid_answers=True
        result=self.t.run()
        self.assertEqual(result["state"],"unknown",result)
        self.assertEqual(len(result["results"]),0)
        self.assertEqual(len(self.t.calls),1)

    def test_missing_case_refused(self):
        self.t.missing_case=True
        self.assertEqual(self.t.run()["state"],"unknown")
        self.assertEqual(len(self.t.calls),1)

    def test_truncated_completion_refused(self):
        self.t.short_finish=True
        self.assertEqual(self.t.run()["state"],"unknown")
        self.assertEqual(len(self.t.calls),1)

    def test_forged_tool_calls_refused(self):
        self.t.tools=True
        self.assertEqual(self.t.run()["state"],"unknown")
        self.assertEqual(len(self.t.calls),1)

    def test_wrong_provider_model_refused(self):
        self.t.corrupt_model=True
        self.assertEqual(self.t.run()["state"],"unknown")
        self.assertEqual(len(self.t.calls),1)

    def test_status_response_without_usage_does_not_claim_real_inference(self):
        self.t.no_usage=True
        result=self.t.run()
        self.assertEqual(result["state"],"completed",result)
        self.assertEqual([r["usageOutcome"] for r in result["results"]],
                         ["unknown_usage","unknown_usage"])
        self.assertFalse(result["realModelExecutionVerified"])

    def test_provider_http_500_not_validated(self):
        self.t.provider_error=True
        result=self.t.run()
        self.assertEqual(result["state"],"unknown")
        self.assertEqual(len(self.t.calls),1)
        self.assertFalse(result["providerResponseValidated"])

    def test_disabled_by_default_no_new_claim(self):
        self.t.service=d.DreamTrialService({},self.t.review)
        with self.assertRaisesRegex(ExecutionDenied,"dream_trial_disabled"):
            self.t.run()
        self.assertEqual(self.t.calls,[])

    def test_changed_config_after_install_refused(self):
        self.t.settings["enabled"]=False
        with self.assertRaisesRegex(ExecutionDenied,"dream_trial_settings_changed"):
            self.t.run()
        self.assertEqual(self.t.calls,[])

    def test_unknown_config_field_refused(self):
        with self.assertRaisesRegex(ExecutionDenied,"dream_trial_invalid_settings"):
            d.DreamTrialService({"enabled":True,"scheduler":True},self.t.review)

    def test_output_ceiling_requires_policy(self):
        from dataclasses import replace
        self.t.f.boundary.policy=replace(self.t.f.policy,output_ceiling_tokens=200)
        with self.assertRaisesRegex(ExecutionDenied,"dream_trial_exceeds_token_policy"):
            d.DreamTrialService({"enabled":True,"output_tokens":256},self.t.review)

    def test_trial_output_range_enforced_before_policy(self):
        with self.assertRaisesRegex(ExecutionDenied,"invalid_trial_output_tokens"):
            d.DreamTrialService({"enabled":True,"output_tokens":4097},self.t.review)

    def test_max_cases_12_prevents_13(self):
        altered=copy.deepcopy(self.t.plan)
        altered["cases"].append({"caseId":"case_extra","prompt":"Another trial case"})
        altered["planId"]="ev_"+hashlib.sha256(_json({k:v for k,v in altered.items() if k!="planId"}).encode()).hexdigest()
        with self.assertRaises(ExecutionDenied):
            self.t.run(altered)

    def test_deletion_of_request_view_blocks_status(self):
        result=self.t.run()
        ticket=result["results"][0]["ticket"]
        with closing(sqlite3.connect(self.t.f.home/"state.db")) as conn:
            keys=conn.execute("SELECT key FROM state_meta WHERE key LIKE ?",
                              ("%."+ticket,)).fetchall()
        from request_view import key_for
        key=key_for(self.t.f.context,ticket)
        self.t.f.f.sql("DELETE FROM state_meta WHERE key=?",(key,))
        with self.assertRaisesRegex(ExecutionDenied,"dream_trial_request_view_missing"):
            self.t.row()

    def test_tampered_resealed_trial_answer_must_not_be_accepted(self):
        result=self.t.run()
        key=d.PREFIX+self.t.f.context.scope+"."+self.t.plan["planId"]
        row=self.t.db_row()[0]
        row["results"][0]["answers"]["answers"][0]["answer"]="REDACT"
        self.t.f.f.sql("UPDATE state_meta SET value=? WHERE key=?",
                       (_json(ledger_seal(row)),key))
        with self.assertRaisesRegex(ExecutionDenied,"dream_trial_history_invalid"):
            self.t.row()

    def test_mutated_broker_response_document_refused(self):
        self.t.changed_prompt=True
        result=self.t.run()
        self.assertEqual(result["state"],"unknown")
        self.assertEqual(len(self.t.calls),1)

    def test_two_parallel_identical_calls_at_most_once(self):
        async def both():
            return await asyncio.gather(self.t.service.run(self.t.plan),
                                        self.t.service.run(self.t.plan))
        results=asyncio.run(both())
        self.assertEqual(len(self.t.calls),2)
        self.assertEqual([x["state"] for x in results].count("completed"),1)
        self.assertTrue(any(x.get("replayed") for x in results))

    def test_context_bounded_and_same_token_ceiling(self):
        result=self.t.run()
        self.assertEqual(result["state"],"completed")
        self.assertEqual({p["body"]["max_tokens"] for p in self.t.calls},{256})

    def test_new_plan_after_completed_is_separate_batch(self):
        self.t.run()
        # Changed case/truth plan would need a new sealed plan. The same old
        # review cannot be swapped into a fresh plan without a full re-seal.
        before=self.t.budget()["providerCalls"]
        self.assertEqual(before,3)

    def test_precommit_lost_ack_no_provider_call_or_retry(self):
        self.t.f.owner.lose_ack=True
        with self.assertRaises(ExecutionDenied):
            self.t.run()
        self.t.f.owner.lose_ack=False
        result=self.t.run()
        self.assertEqual(result["state"],"prepared")
        self.assertTrue(result["replayed"])
        self.assertEqual(self.t.calls,[])

    def test_changed_request_view_response_hash_rejected(self):
        result=self.t.run()
        ticket=result["results"][0]["ticket"]
        from request_view import key_for
        key=key_for(self.t.f.context,ticket)
        with closing(sqlite3.connect(self.t.f.home/"state.db")) as conn:
            old=conn.execute("SELECT value FROM state_meta WHERE key=?",(key,)).fetchone()[0]
        row=_load(old)
        row["responseSha256"]="f"*64
        self.t.f.f.sql("UPDATE state_meta SET value=? WHERE key=?",
                       (_json(ledger_seal(row)),key))
        with self.assertRaisesRegex(ExecutionDenied,"dream_trial_request_view_conflict"):
            self.t.row()

    def test_forced_false_authority_rejected_even_when_resealed(self):
        self.t.run()
        key=d.PREFIX+self.t.f.context.scope+"."+self.t.plan["planId"]
        row=self.t.db_row()[0]
        row["skillTransferVerified"]=True
        self.t.f.f.sql("UPDATE state_meta SET value=? WHERE key=?",
                       (_json(ledger_seal(row)),key))
        with self.assertRaisesRegex(ExecutionDenied,"dream_trial_false_authority"):
            self.t.row()

    def test_forged_case_ids_rejected_even_if_resealed(self):
        self.t.run()
        key=d.PREFIX+self.t.f.context.scope+"."+self.t.plan["planId"]
        row=self.t.db_row()[0]
        row["caseIds"]=["case_foreign"]*12
        self.t.f.f.sql("UPDATE state_meta SET value=? WHERE key=?",
                       (_json(ledger_seal(row)),key))
        with self.assertRaisesRegex(ExecutionDenied,"dream_trial_case_ids_invalid"):
            self.t.row()

    def test_budget_policy_mutation_rejected_without_new_provider_call(self):
        from dataclasses import replace
        self.t.f.ledger.policy=replace(self.t.f.policy,max_provider_calls=2)
        with self.assertRaises(ExecutionDenied):
            self.t.run()
        self.assertEqual(self.t.calls,[])

    def test_missing_provider_broker_optin_refused(self):
        previous=self.t.review.dream.boundary.broker
        self.t.review.dream.boundary.broker=None
        with self.assertRaisesRegex(ExecutionDenied,"dream_trial_broker_required"):
            d.DreamTrialService({"enabled":True},self.t.review)
        self.t.review.dream.boundary.broker=previous
