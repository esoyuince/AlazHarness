"""Explicit local Dream D2 candidate review. No automatic retry or memory writes."""
from __future__ import annotations
import argparse
import http.client
import json
from pathlib import Path
import re
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'packages/claw-hermes'))
from dream_once import check_connection, read_private
from recovery_inspector import _json,_load

HEX64=re.compile(r'[a-f0-9]{64}\Z')
CID=re.compile(r'dc_[a-f0-9]{64}\Z')
RID=re.compile(r'rv_[a-f0-9]{64}\Z')
REASONS={
    'evidence_sufficient_to_test','duplicate','conflict','insufficient_evidence',
    'out_of_scope','needs_benchmark','operator_deferred'
}
DECISIONS={'accept_for_testing','reject','defer'}


def invoke(connection, *, batch_id, operation='inspect', candidate_id=None,
           decision=None, reason_code=None, expected_revision=None,
           base_revision=None):
    port,token=check_connection(connection)
    if type(batch_id) is not str or not HEX64.fullmatch(batch_id):
        raise ValueError('invalid_dream_review_batch')
    if operation=='inspect':
        if any(v is not None for v in (candidate_id,decision,reason_code,expected_revision,base_revision)):
            raise ValueError('invalid_dream_review_operation')
        method='GET';path='/alaz/host/v1/dream/review/'+batch_id;body=None
    elif operation=='decide':
        if (type(candidate_id) is not str or not CID.fullmatch(candidate_id) or
            type(decision) is not str or decision not in DECISIONS or
            type(reason_code) is not str or reason_code not in REASONS or
            type(expected_revision) is not str or not RID.fullmatch(expected_revision) or
            base_revision is not None):
            raise ValueError('invalid_dream_review_decision')
        if decision=='accept_for_testing' and reason_code!='evidence_sufficient_to_test':
            raise ValueError('invalid_dream_review_decision')
        method='POST';path='/alaz/host/v1/dream/review'
        body=_json({'batchId':batch_id,'candidateId':candidate_id,
                    'decision':decision,'reasonCode':reason_code,
                    'expectedRevision':expected_revision}).encode('utf-8')
    elif operation=='diff':
        if (type(base_revision) is not str or not RID.fullmatch(base_revision) or
            any(v is not None for v in (candidate_id,decision,reason_code,expected_revision))):
            raise ValueError('invalid_dream_review_baseline')
        method='POST';path='/alaz/host/v1/dream/review/diff'
        body=_json({'batchId':batch_id,'baseRevision':base_revision}).encode('utf-8')
    else:
        raise ValueError('invalid_dream_review_operation')
    client=http.client.HTTPConnection('127.0.0.1',port,timeout=30)
    try:
        client.request(method,path,body=body,headers={
            'Authorization':'Bearer '+token,'Content-Type':'application/json'})
        response=client.getresponse()
        raw=response.read(131073)
        if response.status!=200 or len(raw)>131072:
            raise ValueError('dream_review_request_unconfirmed')
        value=_load(raw.decode('utf-8'),131072)
        if type(value) is not dict or value.get('version')!=1 or value.get('batchId')!=batch_id:
            raise ValueError('dream_review_invalid_response')
        for name in ('activeMemoryChanged','independentOutcomeVerified','skillTransferVerified'):
            if value.get(name) is not False:raise ValueError('dream_review_invalid_response')
        if value.get('additionalModelCalls')!=0:
            raise ValueError('dream_review_invalid_response')
        if operation=='diff':
            if (type(value.get('hasChanges')) is not bool or
                type(value.get('newlyAcceptedForIndependentEvaluation')) is not list or
                value.get('promotableMemoryProposal') is not False or
                type(value.get('currentRevision')) is not str or
                not RID.fullmatch(value['currentRevision'])):
                raise ValueError('dream_review_invalid_response')
        else:
            if (type(value.get('revision')) is not str or
                not RID.fullmatch(value['revision']) or
                type(value.get('decisions')) is not list or
                value.get('evaluationStatus')!='not_run' or
                value.get('grantsExecutionPermission') is not False or
                value.get('conclusionVerified') is not False):
                raise ValueError('dream_review_invalid_response')
        return value
    finally:
        client.close()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--connection',type=Path,required=True)
    parser.add_argument('--batch-id',required=True)
    operations=parser.add_mutually_exclusive_group(required=True)
    operations.add_argument('--inspect',action='store_true')
    operations.add_argument('--decision',choices=sorted(DECISIONS))
    operations.add_argument('--diff-from')
    parser.add_argument('--candidate-id')
    parser.add_argument('--reason-code',choices=sorted(REASONS))
    parser.add_argument('--expected-revision')
    parser.add_argument('--output',type=Path)
    a=parser.parse_args()
    try:
        if a.output is not None and (a.output.exists() or a.output.is_symlink()):
            raise ValueError('dream_review_output_exists')
        operation='decide' if a.decision else ('diff' if a.diff_from else 'inspect')
        result=invoke(read_private(a.connection),batch_id=a.batch_id,
                      operation=operation,candidate_id=a.candidate_id,
                      decision=a.decision,reason_code=a.reason_code,
                      expected_revision=a.expected_revision,base_revision=a.diff_from)
        rendered=json.dumps(result,ensure_ascii=False,indent=2)+'\n'
        if a.output is not None:
            with a.output.open('x',encoding='utf-8',newline='\n') as f:f.write(rendered)
        else:print(rendered,end='')
        return 0
    except Exception:
        # A committed review change could have lost its HTTP acknowledgment.
        # Read status with the same batch ID; never replay the decision blindly.
        print('{"error":"dream_review_not_confirmed","automaticRetry":false}',file=sys.stderr)
        return 2


if __name__=='__main__':
    raise SystemExit(main())
