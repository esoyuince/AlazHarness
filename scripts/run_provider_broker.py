"""Explicit private provider-broker lifecycle. No source install, automatic restart or model call on boot."""
import argparse
import asyncio
import json
import os
from pathlib import Path
import signal
import stat
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'packages/claw-hermes'))
from provider_broker import ProviderBrokerServer
from provider_egress import BrokerConfig,require
from recovery_inspector import _load


def private_config(path):
    require(os.name=='posix','linux_broker_required')
    p=Path(path)
    require(p.is_file() and not any(x.is_symlink() for x in (p,*p.parents)),'invalid_private_broker_config')
    info=p.stat()
    require(info.st_uid==os.getuid() and stat.S_IMODE(info.st_mode)==0o600 and info.st_nlink==1 and info.st_size<=32768,'invalid_private_broker_config')
    return BrokerConfig(**_load(p.read_text(encoding='utf-8'),32768))


async def serve(config,output):
    require(not output.exists() and output.is_absolute(),'fresh_broker_output_required')
    server=ProviderBrokerServer(config,output)
    ready=await server.start()
    (output/'ready.json').write_text(json.dumps(ready))
    stop=asyncio.Event();loop=asyncio.get_running_loop()
    for sig in (signal.SIGINT,signal.SIGTERM):loop.add_signal_handler(sig,stop.set)
    try:await stop.wait()
    finally:
        closed=await server.close()
        (output/'shutdown.json').write_text(json.dumps(closed))


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--config',required=True,type=Path);p.add_argument('--output',required=True,type=Path);a=p.parse_args()
    try:asyncio.run(serve(private_config(a.config),a.output))
    except Exception:
        print(json.dumps({'result':'refused','reason':'provider_broker_start_or_shutdown_unconfirmed'}));return 2
    return 0

if __name__=='__main__':raise SystemExit(main())
