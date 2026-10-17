"""Manual D2B sealed held-out scorer; never calls a model or promotes memory.

Key, answer truth, response artifacts and reports MUST live under ignored
runtime/. The only Gateway operation is authenticated D2A status GET.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import re
import secrets
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'packages/claw-hermes'), str(ROOT/'scripts')]
from dream_once import read_private
from dream_review_once import invoke as review_get
from dream_eval import EvaluationRejected, seal, grade, ensure

HEX64=re.compile(r'[a-f0-9]{64}\Z')
CID=re.compile(r'dc_[a-f0-9]{64}\Z')


def private_path(value, *, output=False):
    path=Path(value)
    root=(ROOT/'runtime').resolve()
    resolved=path.resolve(strict=False)
    try:
        resolved.relative_to(root)
    except ValueError:
        raise EvaluationRejected('evaluation_private_runtime_required') from None
    if path.is_symlink() or not path.parent.is_dir():
        raise EvaluationRejected('evaluation_private_path_invalid')
    if output and path.exists():
        raise EvaluationRejected('evaluation_output_exists')
    return path


def private_json(value):
    return read_private(private_path(value))


def key_value(path):
    row=private_json(path)
    ensure(type(row) is dict and set(row)=={'version','oracleKeyHex'}
           and type(row['version']) is int and row['version']==1
           and type(row['oracleKeyHex']) is str
           and HEX64.fullmatch(row['oracleKeyHex']),
           'invalid_oracle_key_file')
    return row['oracleKeyHex']


def emit(path,value):
    dest=private_path(path,output=True)
    text=json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2)+'\n'
    ensure(len(text.encode('utf-8'))<=131072,'evaluation_output_limit')
    with dest.open('x',encoding='utf-8',newline='\n') as out:
        out.write(text)


def key_create(output):
    path=private_path(output,output=True)
    # Never put the key in the plan, Git or terminal output.
    value={'version':1,'oracleKeyHex':secrets.token_hex(32)}
    emit(path,value)
    return {'version':1,'state':'private_oracle_key_created',
            'keyPath':str(path),'keyPrinted':False}


def seal_once(*,connection,batch_id,candidate_id,training,cases,truth,key):
    conn=private_json(connection)
    review=review_get(conn,batch_id=batch_id,operation='inspect')
    t=private_json(training)
    c=private_json(cases)
    ensure(type(t) is dict and set(t)=={'version','prompts'}
           and type(t['version']) is int and t['version']==1,
           'evaluation_invalid_training_file')
    ensure(type(c) is dict and set(c)=={'version','family','cases'}
           and type(c['version']) is int and c['version']==1,
           'evaluation_invalid_case_file')
    secret=key_value(key)
    return seal(review,candidate_id,c['family'],t['prompts'],c['cases'],
                private_json(truth),secret)


def score_once(*,connection,plan,truth,key,baseline,candidate):
    p=private_json(plan)
    batch=p.get('review',{}).get('batchId') if type(p) is dict and type(p.get('review')) is dict else None
    conn=private_json(connection)
    review=review_get(conn,batch_id=batch,operation='inspect')
    return grade(p,review,private_json(truth),private_json(baseline),
                 private_json(candidate),key_value(key))


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest='command',required=True)
    key=sub.add_parser('key')
    key.add_argument('--output',type=Path,required=True)
    seal_cmd=sub.add_parser('seal')
    for name in ('connection','training','cases','truth','key','output'):
        seal_cmd.add_argument('--'+name,type=Path,required=True)
    seal_cmd.add_argument('--batch-id',required=True)
    seal_cmd.add_argument('--candidate-id',required=True)
    score=sub.add_parser('score')
    for name in ('connection','plan','truth','key','baseline','candidate','output'):
        score.add_argument('--'+name,type=Path,required=True)
    args=p.parse_args(argv)
    try:
        if args.command=='key':
            value=key_create(args.output)
            print(json.dumps(value,ensure_ascii=False))
        elif args.command=='seal':
            private_path(args.output,output=True)
            value=seal_once(connection=args.connection,batch_id=args.batch_id,
                candidate_id=args.candidate_id,training=args.training,cases=args.cases,
                truth=args.truth,key=args.key)
            emit(args.output,value)
            print(json.dumps({'state':'plan_sealed','planId':value['planId'],
                              'caseCount':len(value['cases']),
                              'modelCalled':False,'truthPublished':False}))
        elif args.command=='score':
            private_path(args.output,output=True)
            value=score_once(connection=args.connection,plan=args.plan,
                truth=args.truth,key=args.key,baseline=args.baseline,
                candidate=args.candidate)
            emit(args.output,value)
            print(json.dumps({'state':'offline_scored','planId':value['planId'],
                              'modelExecutionVerified':False,
                              'skillTransferVerified':False}))
        return 0
    except Exception:
        # Review status can change during evaluation; do not replay any mutation
        # or claim that a local score establishes actual inference.
        print(json.dumps({'error':'evaluation_not_confirmed',
                          'automaticRetry':False,
                          'activeMemoryChanged':False}),file=sys.stderr)
        return 2


if __name__=='__main__':
    raise SystemExit(main())
