"""Trusted-host one-time budget provisioning, no server or provider starts."""
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'packages/claw-hermes'))
from run_provider_broker import private_config
from broker_budget import initialize


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--config',type=Path,required=True)
    a=p.parse_args()
    try:
        cfg=private_config(a.config)
        if cfg.budget_authority is None:raise ValueError('explicit private budget required')
        value=initialize(cfg)
        print(json.dumps({'state':'initialized','budgetId':value['budgetId'],
                          'providerReservations':0,'networkCalls':0}))
        return 0
    except Exception:
        print('{"state":"refused","automaticRetry":false}',file=sys.stderr)
        return 2


if __name__=='__main__':raise SystemExit(main())
