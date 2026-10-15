"""Local operator preview/apply. No server endpoint, provider calls or automatic repair.

Use a host-owned private context/request. Preview is default. Apply requires the
EXACT separately inspected plan and confirmation digest, plus native maintenance
ownership and fresh in-transaction evidence. No flag can force a refused action.
"""
import argparse
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'packages/claw-hermes'))
from recovery_inspector import LocalRecoveryContext,_load
from operator_resolution import OperatorResolution,ResolutionError


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source-workspace',required=True,type=Path)
    p.add_argument('--context',required=True,type=Path)
    p.add_argument('--request',required=True,type=Path)
    p.add_argument('--command-id')
    p.add_argument('--apply',action='store_true')
    p.add_argument('--plan',type=Path)
    p.add_argument('--confirm')
    a=p.parse_args()
    try:
        if a.context.stat().st_size>32768 or a.request.stat().st_size>2097152:raise ResolutionError('oversized_local_input')
        context=_load(a.context.read_text(encoding='utf-8'),32768);request=_load(a.request.read_text(encoding='utf-8'))
        if set(context)!={'profile_home','api_token','epoch','instance_id'} or set(request)!={'body','idempotency_key','observed'}:
            raise ResolutionError('invalid_local_shape')
        action=OperatorResolution(LocalRecoveryContext(**context),source_root=a.source_workspace.resolve()/'vendor/hermes-agent')
        if a.apply:
            if a.plan is None or a.confirm is None or a.command_id is not None:raise ResolutionError('explicit_confirmation_required')
            if a.plan.stat().st_size>16384:raise ResolutionError('oversized_local_input')
            result=action.apply(plan=_load(a.plan.read_text(encoding='utf-8'),16384),confirmation=a.confirm,**request)
        else:
            if a.plan is not None or a.confirm is not None:raise ResolutionError('apply_not_requested')
            result={'status':'preview','plan':action.prepare(command_id=a.command_id,**request),'writesPerformed':False,
                    'taskSucceeded':False,'retryAllowed':False,'requiresExplicitConfirmation':True}
        code=0
    except ResolutionError as exc:
        result={'status':'refused','reason':str(exc),'taskSucceeded':False,'retryAllowed':False,'repairAllowed':False};code=2
        if str(exc)=='storage_or_commit_unconfirmed':result['effect']='unknown'
        else:result['effect']='not_applied'
    except (OSError,ValueError,TypeError,KeyError):
        result={'status':'refused','reason':'invalid_local_input','effect':'not_applied','taskSucceeded':False,'retryAllowed':False};code=2
    print(json.dumps(result,indent=2));return code

if __name__=='__main__':raise SystemExit(main())
