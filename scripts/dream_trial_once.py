"""D2B2 manual trial run/status/score through existing authenticated loopback.

POST has at-most-one attempt; a lost HTTP acknowledgement is NEVER retried.
The answer oracle/HMAC secret stays in ignored local runtime and never reaches
the Gateway, broker or provider endpoint.
"""
from __future__ import annotations

import argparse
import http.client
import json
from pathlib import Path
import re
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'packages/claw-hermes')]
from dream_once import check_connection
from dream_review_once import invoke as review_get
from dream_eval_once import private_json,private_path,key_value,emit
from dream_eval import _validated_plan,grade,ensure
from recovery_inspector import _json,_load

PLAN=re.compile(r'ev_[a-f0-9]{64}\Z')


def transfer(connection, *, plan=None, plan_id=None):
    port,token=check_connection(connection)
    if (plan is None)==(plan_id is None):
        raise ValueError("one_trial_operation_required")
    if plan is not None:
        _validated_plan(plan)
        method="POST"
        path="/alaz/host/v1/dream/trial"
        body=_json({"plan":plan}).encode("utf-8")
        if not 0<len(body)<=131072:
            raise ValueError("invalid_trial_payload_size")
        expected=plan["planId"]
    else:
        if type(plan_id) is not str or not PLAN.fullmatch(plan_id):
            raise ValueError("invalid_trial_plan_id")
        expected=plan_id;method="GET"
        path="/alaz/host/v1/dream/trial/"+expected
        body=None
    client=http.client.HTTPConnection("127.0.0.1",port,timeout=55)
    try:
        client.request(method,path,body=body,headers={
            "Authorization":"Bearer "+token,
            "Content-Type":"application/json"})
        resp=client.getresponse()
        raw=resp.read(131073)
        if len(raw)>131072 or resp.status not in ((200,202) if method=="POST" else (200,)):
            raise ValueError("dream_trial_response_unconfirmed")
        doc=_load(raw.decode("utf-8"),131072)
        if (type(doc) is not dict or doc.get("planId")!=expected or
            doc.get("state") not in ("prepared","running","completed","unknown")):
            raise ValueError("dream_trial_response_invalid")
        for field in ("realModelExecutionVerified","independentOutcomeVerified",
                      "skillTransferVerified","activeMemoryChanged",
                      "grantsExecutionPermission","automaticTrigger",
                      "physicalProviderInferenceVerified"):
            if doc.get(field) is not False:
                raise ValueError("dream_trial_authority_invalid")
        if (doc.get("responseOrigin")!="broker_process_http_response_observed" or
            type(doc.get("results")) is not list):
            raise ValueError("dream_trial_response_invalid")
        if doc["state"]=="completed":
            if (doc.get("providerResponseValidated") is not True or
                len(doc["results"])!=2 or
                [part.get("arm") for part in doc["results"]]!=["baseline","candidate"]):
                raise ValueError("dream_trial_incomplete_pair")
        else:
            if doc.get("providerResponseValidated") is not False:
                raise ValueError("dream_trial_response_invalid")
        return doc
    finally:
        client.close()


def score_existing(*,connection,plan,truth,key):
    _validated_plan(plan)
    info=transfer(connection,plan_id=plan["planId"])
    ensure(info["state"]=="completed" and info["providerResponseValidated"] is True,
           "dream_trial_not_completed")
    assert info["planId"]==plan["planId"]
    review=review_get(connection,batch_id=plan["review"]["batchId"],
                      operation="inspect")
    result=grade(plan,review,private_json(truth),
                 info["results"][0]["answers"],
                 info["results"][1]["answers"],key_value(key))
    assert result["independentOutcomeVerified"] is False
    return {**result,
       # The authenticated local host reports these ledger/request-view links.
       # This CLI does NOT independently verify the broker process or signature.
       "brokerReceiptChainReportedByHost":True,
       "brokerReceiptIndependentlyVerified":False,
       "trialReceiptSummaries":[{
          "arm":part["arm"],"ticket":part["ticket"],
          "requestDigest":part["requestDigest"],
          "requestViewDigest":part["requestViewDigest"],
          "responseSha256":part["responseSha256"],
          "usageOutcome":part["usageOutcome"]
       } for part in info["results"]],
       "trialStatusCheckedThroughHostBearer":True,
       "realModelExecutionVerified":False,
       "candidateLessonAppliedByModelVerified":False,
       "independentOutcomeVerified":False,
       "skillTransferVerified":False,
       "promotableMemoryProposal":False,
       "activeMemoryChanged":False}


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest="cmd",required=True)
    for action in ("run","status","score"):
        part=sub.add_parser(action)
        part.add_argument("--connection",type=Path,required=True)
        part.add_argument("--output",type=Path,required=True)
        if action=="run" or action=="score":
            part.add_argument("--plan",type=Path,required=True)
        if action=="status":
            part.add_argument("--plan-id",required=True)
        if action=="score":
            part.add_argument("--truth",type=Path,required=True)
            part.add_argument("--key",type=Path,required=True)
    args=p.parse_args(argv)
    try:
        private_path(args.output,output=True)
        connection=private_json(args.connection)
        if args.cmd=="run":
            value=transfer(connection,plan=private_json(args.plan))
        elif args.cmd=="status":
            value=transfer(connection,plan_id=args.plan_id)
        else:
            value=score_existing(connection=connection,plan=private_json(args.plan),
                                 truth=args.truth,key=args.key)
        emit(args.output,value)
        print(json.dumps({"state":value.get("state",value.get("assessmentState")),
                          "planId":value["planId"],
                          "realModelExecutionVerified":False,
                          "skillTransferVerified":False},ensure_ascii=False))
        return 0 if args.cmd=="score" or value.get("state")=="completed" else 2
    except Exception:
        print(json.dumps({"error":"dream_trial_outcome_unconfirmed",
                          "automaticRetry":False,
                          "activeMemoryChanged":False}),file=sys.stderr)
        return 2


if __name__=="__main__":
    raise SystemExit(main())
