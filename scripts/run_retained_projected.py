"""Fixed trusted-install post-projection target; no arbitrary entrypoint or shell."""
from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'packages/claw-hermes'),str(ROOT/'native'),str(ROOT/'dependencies')]
from gateway_retained_launch import target_main

def main():
    try:
        if len(sys.argv)!=1:raise ValueError('unexpected arguments')
        result=target_main()
        print(json.dumps(result,sort_keys=True),flush=True)
        return 0
    except Exception as exc:
        # No caller values, retry, fallback, registry cleanup or false success.
        print(json.dumps({'state':'PROJECTED_RETAINED_REFUSED','type':type(exc).__name__}),flush=True)
        return 2
if __name__=='__main__':raise SystemExit(main())
