"""Opt-in real local Unix-socket shutdown check; no TCP/model/Gateway or real secret."""
import argparse
import asyncio
import json
import os
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'packages/claw-hermes'))
from provider_broker import ProviderBrokerServer
from provider_egress import BrokerConfig

async def probe(root):
    assert os.name=='posix' and root.is_absolute() and not root.exists()
    cfg=BrokerConfig('http://127.0.0.1:19777/v1','test','p'*48,'b'*64,str(root.parent/'state.db'),'a'*64,'c'*64,'d'*64)
    server=ProviderBrokerServer(cfg,root);await server.start();writer=None;ok=False
    try:
        reader,writer=await asyncio.open_unix_connection(server.path)
        for _ in range(20):
            await asyncio.sleep(.01)
            if server.tasks:break
        assert server.tasks
        try:await asyncio.wait_for(server.close(),.3);ok=True
        except asyncio.TimeoutError:pass
    finally:
        if writer:writer.close();await writer.wait_closed()
        for task in list(server.tasks):task.cancel()
        end=await asyncio.wait_for(server.close(),3)
    result={'scope':'real Unix-socket broker with idle client, no provider/Gateway','prompt_close':ok,
            'deadline_seconds':.3,'cleanup':end,'provider_calls':server.counts['physicalAttempts'],'python':sys.version.split()[0]}
    (root/'lifecycle-observation.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result));return 0 if ok and end['activeRequests']==0 and end['socketRemoved'] else 1

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    return asyncio.run(probe(args.output))
if __name__=='__main__':raise SystemExit(main())
