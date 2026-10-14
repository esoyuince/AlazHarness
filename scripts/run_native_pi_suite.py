"""Run all six explicitly scoped Pi native scenarios, preserving every child receipt."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import subprocess
import sys
from pi_probe_support import ROOT,check_source,digest,fresh_runtime_path
from run_native_pi_probe import SCENARIOS


def main() -> int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source-workspace',type=Path,required=True)
    p.add_argument('--prepared',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--repeats',type=int,choices=range(1,4),default=1)
    a=p.parse_args();out=fresh_runtime_path(a.source_workspace,a.output)
    pin=check_source(a.prepared.resolve()/'source');out.mkdir(parents=True)
    results=[]
    for n in range(1,a.repeats+1):
        for scenario in SCENARIOS:
            target=out/f'{n:02}-{scenario}'
            cmd=[sys.executable,'-B',str(ROOT/'scripts/run_native_pi_probe.py'),'--source-workspace',str(a.source_workspace),'--prepared',str(a.prepared),'--output',str(target),'--scenario',scenario]
            child=subprocess.run(cmd,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=45)
            data=json.loads((target/'receipt.json').read_text(encoding='utf-8')) if (target/'receipt.json').exists() else None
            execution=json.loads((target/'execution.json').read_text(encoding='utf-8')) if (target/'execution.json').exists() else None
            accepted=child.returncode==0 and bool(data and data.get('result')=='PASS') and bool(execution and execution['direct_child_reaped'] and not execution['timed_out'])
            results.append({'repeat':n,'scenario':scenario,'accepted':accepted,'exit_code':child.returncode,'receipt':data,'execution':execution})
            print(scenario,n,'PASS' if accepted else 'FAIL',flush=True)
            if not accepted:print(child.stdout[-1000:]+child.stderr[-1000:])
            summary={'scope':'real Pi low-level Agent/provider/native read tool; scripted model, not production harness acceptance','source_commit':pin,'scenario_count':len(SCENARIOS),'requested_repeats':a.repeats,'runs':results,'passed':sum(x['accepted'] for x in results),'failed':sum(not x['accepted'] for x in results),'complete':len(results)==a.repeats*len(SCENARIOS),'worker_sha256':digest(ROOT/'scripts/native_pi_probe_worker.mjs'),'contract_sha256':digest(ROOT/'scripts/pi_probe_contract.mjs'),'model_inference_calls':0,'paid_calls':0}
            (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in summary.items() if k!='runs'},indent=2))
    return 0 if summary['complete'] and summary['failed']==0 else 1

if __name__=='__main__':raise SystemExit(main())
