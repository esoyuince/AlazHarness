"""Read-only host report. Inputs are private local host records, never agent authority."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'packages/claw-hermes'))
from recovery_inspector import LocalRecoveryContext,_load
from execution_budget import ExecutionPolicy
from host_report import HostReportInspector,render_text,unavailable_report


def read_object(path:Path,limit:int)->dict:
    if path.is_symlink() or not path.is_file() or path.stat().st_size>limit:
        raise ValueError('invalid_local_input')
    value=_load(path.read_text(encoding='utf-8'),limit)
    if type(value) is not dict:raise ValueError('invalid_local_input')
    return value


def main()->int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--context',required=True,type=Path,help='Private profile_home/api_token/epoch/instance_id record')
    parser.add_argument('--policy',required=True,type=Path,help='Trusted execution policy (not a provider invoice)')
    selection=parser.add_mutually_exclusive_group(required=True)
    selection.add_argument('--request',type=Path,help='Original body/idempotency_key/observed run record')
    selection.add_argument('--scope-only',action='store_true',help='Read profile/principal budget without selecting or inventing a task')
    parser.add_argument('--format',choices=('json','text'),default='json')
    args=parser.parse_args()
    try:
        context=read_object(args.context,32768);policy=read_object(args.policy,32768)
        if set(context)!={'profile_home','api_token','epoch','instance_id'}:raise ValueError('invalid_local_input')
        inspector=HostReportInspector(LocalRecoveryContext(**context),ExecutionPolicy(**policy))
        if args.scope_only:report=inspector.inspect_scope()
        else:
            request=read_object(args.request,2097152)
            if set(request)!={'body','idempotency_key','observed'}:raise ValueError('invalid_local_input')
            report=inspector.inspect(**request)
    except (OSError,ValueError,TypeError,KeyError,RecursionError,OverflowError):
        report=unavailable_report('invalid_local_input')
    print(render_text(report),end='') if args.format=='text' else print(json.dumps(report,indent=2,ensure_ascii=False))
    # Verification status, not task success. An accurately reported failed task
    # may be a valid report; incomplete evidence gets a nonzero exit code.
    return 0 if report['reportStatus'] in ('verified_snapshot','verified_scope_snapshot') else 2

if __name__=='__main__':raise SystemExit(main())
