"""Owned wrapper around the unmodified public Gateway lifecycle; not an alternate runtime."""
from __future__ import annotations
import asyncio
import json
import os
from pathlib import Path
import sys

source, work, nonce = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve(), sys.argv[3]
assert work == Path.cwd().resolve() and Path(os.environ['HERMES_HOME']).resolve() == work/'profile'
assert len(nonce)==32 and all(c in '0123456789abcdef' for c in nonce)
blocked=[]
def audit(event,args):
    host=None
    if event=='socket.connect' and isinstance(args[1],tuple):host=args[1][0]
    elif event=='socket.getaddrinfo':host=args[0]
    if host is not None and host not in ('127.0.0.1','::1','localhost',b'localhost'):
        blocked.append(event)
        raise PermissionError('Native Gateway probe denies non-loopback Python networking')
sys.addaudithook(audit)
sys.path.insert(0,str(source))

def record(name,value):
    p=work/name;tmp=p.with_suffix(p.suffix+'.tmp')
    tmp.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8');os.replace(tmp,p)

async def run():
    record('spawn.json',{'nonce':nonce,'pid':os.getpid(),'ppid':os.getppid()})
    from gateway import run as native
    from gateway.config import Platform
    # Dependency guard precedes all owned Gateway state and sockets.
    import aiohttp
    lifecycle=asyncio.create_task(native.start_gateway(idle_exit=True))
    observed=None
    try:
        async with asyncio.timeout(90):
            while not lifecycle.done():
                ref=getattr(native,'_gateway_runner_ref',None);runner=ref() if ref else None
                if runner is not None:
                    stop=work/'stop.json'
                    if stop.exists() and json.loads(stop.read_text(encoding='utf-8'))=={'nonce':nonce,'pid':os.getpid()}:
                        await runner.stop();break
                    descriptor=getattr(runner,'session_runtime_descriptor',{})
                    adapter=runner.adapters.get(Platform.API_SERVER)
                    if descriptor.get('state')=='ready' and adapter is not None:
                        authority=getattr(runner,'session_authority',None)
                        observed={'pid':os.getpid(),'nonce':nonce,'runner':type(runner).__module__+'.'+type(runner).__name__,
                                  'adapter':type(adapter).__module__+'.'+type(adapter).__name__,
                                  'authority':type(authority).__module__+'.'+type(authority).__name__,
                                  'profile_bound':Path(authority.db.db_path).resolve().parent==work/'profile',
                                  'aiohttp_version':aiohttp.__version__,
                                  'epoch':authority.epoch,'instance_id':descriptor['instance_id'],
                                  'state':descriptor['state'],'api_host':adapter._host,'api_port':adapter._port}
                        assert observed['profile_bound'] and observed['api_host']=='127.0.0.1'
                        record('ready.json',observed);break
                await asyncio.sleep(.05)
        if observed is None:
            result=await lifecycle
            raise RuntimeError('Native Gateway ended before readiness: '+str(result))
        async with asyncio.timeout(120):
            while not lifecycle.done():
                stop=work/'stop.json'
                if stop.exists():
                    value=json.loads(stop.read_text(encoding='utf-8'))
                    if value!={'nonce':nonce,'pid':os.getpid()}:raise RuntimeError('Unowned stop request')
                    await runner.stop()
                    break
                await asyncio.sleep(.05)
        async with asyncio.timeout(35):result=await lifecycle
        record('shutdown.json',{'pid':os.getpid(),'nonce':nonce,'native_result':result,
               'lifecycle_completed':True,'nonloopback_attempts_blocked':len(blocked)})
        return 0 if result else 1
    finally:
        if not lifecycle.done():
            ref=getattr(native,'_gateway_runner_ref',None);runner=ref() if ref else None
            if runner is not None:
                try:
                    async with asyncio.timeout(20):await runner.stop()
                except Exception:pass
            lifecycle.cancel()
            try:await lifecycle
            except (Exception,asyncio.CancelledError):pass

if __name__=='__main__':
    code=1
    try:code=asyncio.run(run())
    except Exception as exc:
        record('failure.json',{'type':type(exc).__name__,'message':str(exc),'pid':os.getpid(),'nonce':nonce,
                             'nonloopback_attempts_blocked':len(blocked)})
        raise
    finally:sys.stdout.flush();sys.stderr.flush()
    raise SystemExit(code)
