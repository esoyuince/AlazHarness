"""Co-located read-only inspection. Context file is trusted LOCAL host configuration, not peer input."""
import argparse
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'packages/claw-hermes'))
from recovery_inspector import LocalRecoveryContext,LocalRecoveryInspector,_load


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--context',type=Path,required=True,help='Private host-owned profile/token/epoch context; never commit it')
    p.add_argument('--request',type=Path,required=True,help='Original body/key and observed HTTP run JSON')
    a=p.parse_args()
    try:
        if a.context.stat().st_size>32768 or a.request.stat().st_size>2097152:raise ValueError('oversized')
        c=_load(a.context.read_text(encoding='utf-8'),32768);r=_load(a.request.read_text(encoding='utf-8'))
        if set(c)!={'profile_home','api_token','epoch','instance_id'} or set(r)!={'body','idempotency_key','observed'}:raise ValueError('shape')
        result=LocalRecoveryInspector(LocalRecoveryContext(**c)).inspect(**r)
    except (OSError,ValueError,TypeError,KeyError):
        result={'classification':'unverified','reason':'invalid_local_input','canonicalVerified':False,
                'requiresOperator':True,'retryAllowed':False,'repairAllowed':False,'writesPerformed':False}
    print(json.dumps(result,indent=2))
    return 2 if result['classification']=='unverified' else 0

if __name__=='__main__':raise SystemExit(main())
