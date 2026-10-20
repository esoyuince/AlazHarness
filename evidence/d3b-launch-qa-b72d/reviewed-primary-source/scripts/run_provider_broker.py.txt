"""Explicit private provider-broker lifecycle. No source install, automatic restart or model call on boot."""
import argparse
import asyncio
import json
import os
from pathlib import Path
import signal
import stat
import sys
import tempfile
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


def output_preflight(config,output):
    """No provisioning or adoption: principal directories are host prepared."""
    require(type(config) is BrokerConfig,'trusted_broker_config_required')
    require(output.is_absolute() and output==output.resolve()
            and not any(p.is_symlink() for p in (output,*output.parents)),
            'fresh_broker_output_required')
    principal=config.principal_contract
    if principal is None:
        require(not output.exists(),'fresh_broker_output_required')
    else:
        from host_principal import broker_identity,regular,SOCKET_DIR_MODE
        broker_identity(principal)
        require(output.is_dir(),'principal_prepared_output_required')
        regular(str(output),'dir',principal['brokerUid'],
                principal['socketGroupGid'],SOCKET_DIR_MODE)
        require(not any(output.iterdir()),'principal_fresh_output_required')


def publish_receipt(output,name,value):
    """Publish complete private JSON without replacing any existing entry.

    Hard-link publication is atomic and no-clobber on the required local
    filesystem. Unsupported filesystems fail closed; no replace fallback.
    The containing directory must remain under trusted host control.
    """
    require(name in ('ready.json','shutdown.json'),'broker_receipt_name')
    data=(json.dumps(value,sort_keys=True)+'\n').encode('utf-8')
    require(len(data)<=262144,'broker_receipt_size')
    temporary=None
    try:
        with tempfile.NamedTemporaryFile(mode='wb',prefix='.'+name+'-',
                                         dir=output,delete=False) as stream:
            temporary=Path(stream.name)
            stream.write(data);stream.flush();os.fsync(stream.fileno())
        os.link(temporary,output/name,follow_symlinks=False)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


async def serve(config,output):
    output=Path(output)
    output_preflight(config,output)
    server=ProviderBrokerServer(config,output)
    stop=asyncio.Event();loop=asyncio.get_running_loop()
    registered=[];published=False
    try:
        ready=await server.start()
        for sig in (signal.SIGINT,signal.SIGTERM):
            loop.add_signal_handler(sig,stop.set)
            registered.append(sig)
        publish_receipt(output,'ready.json',ready)
        published=True
        await stop.wait()
    finally:
        try:
            # A failure before acquiring a listener does not authorize cleanup
            # of an old path or a different process's socket.
            if server.server is not None:
                closed=await server.close()
                if published:publish_receipt(output,'shutdown.json',closed)
        finally:
            for sig in registered:loop.remove_signal_handler(sig)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--config',required=True,type=Path);p.add_argument('--output',required=True,type=Path);a=p.parse_args()
    try:asyncio.run(serve(private_config(a.config),a.output))
    except Exception:
        print(json.dumps({'result':'refused','reason':'provider_broker_start_or_shutdown_unconfirmed'}));return 2
    return 0

if __name__=='__main__':raise SystemExit(main())
