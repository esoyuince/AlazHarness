"""Benign two-UID QA client for the explicitly approved P71C lab only."""
import asyncio
import errno
import hashlib
import json
import os
from pathlib import Path
import sys
import uuid

INSTALL=Path('/opt/alazharness-broker/802fade')
STATE=Path('/srv/alaz-p71c')

def require(ok,reason):
    if not ok:raise RuntimeError(reason)

def self_observed():
    fields={}
    for line in Path('/proc/self/status').read_text().splitlines():
        key,_,value=line.partition(':')
        if key in ('Uid','Gid','Groups','NoNewPrivs','CapEff'):fields[key]=value.split()
    return {'pid':os.getpid(),'uid':os.getuid(),'gid':os.getgid(),'fields':fields,
            'userns':os.readlink('/proc/self/ns/user')}

def accesses():
    out=[]
    for name in ('private/config.json','private/budget/budget.sqlite3'):
        for label,flags in (('read',os.O_RDONLY),('write_open_only',os.O_WRONLY)):
            try:
                fd=os.open(STATE/name,flags|os.O_CLOEXEC|os.O_NOFOLLOW)
            except OSError as exc:out.append({'path':name,'action':label,'opened':False,'errno':exc.errno})
            else:
                try:
                    digest=None
                    if flags==os.O_RDONLY:
                        h=hashlib.sha256()
                        while True:
                            data=os.read(fd,8192)
                            if not data:break
                            h.update(data)
                        digest=h.hexdigest()
                    out.append({'path':name,'action':label,'opened':True,'errno':None,'readSha256':digest})
                finally:os.close(fd)
    return out

async def ping(settings,mode):
    from provider_broker import ProviderBrokerClient,write_frame,read_frame
    from provider_egress import signed,verified,REQUEST_LIMIT,RESPONSE_LIMIT
    from host_principal import socket_peer
    from execution_budget import ExecutionDenied
    if mode=='client_denial':
        try:await ProviderBrokerClient(settings).ready()
        except ExecutionDenied as exc:return {'localClientReason':str(exc)}
        return {'localClientReason':None}
    reader,writer=await asyncio.wait_for(asyncio.open_unix_connection(settings['socket_path']),5)
    try:
        peer=socket_peer(writer.get_extra_info('socket'),settings['principal_contract'],role='gateway')
        nonce=uuid.uuid4().hex
        value={'version':1,'operation':'ping','brokerId':settings['broker_id'],
               'routeFingerprint':settings['route_fingerprint'],'nonce':nonce}
        await write_frame(writer,signed(value,settings['signing_key'],'request'),REQUEST_LIMIT)
        reply=verified(await asyncio.wait_for(read_frame(reader,RESPONSE_LIMIT),5),settings['signing_key'],'reply')
        out={'peer':peer,'reply':reply,'requestedNonce':nonce}
    finally:
        writer.close();await writer.wait_closed()
    if mode=='positive':
        require(reply.get('ok') is True and reply.get('nonce')==nonce,'raw_ping_failed')
        out['actualProviderBrokerClientReady']=await ProviderBrokerClient(settings).ready()
    return out

def main():
    require(sys.platform=='linux' and os.getuid() in (23001,23002) and os.getgid()==23003,'wrong_client_identity')
    require(Path('/etc/alaz-p71c-lab-id').read_text().strip()=='AlazHarness-D3B-P71C','wrong_lab')
    require(not Path('/mnt/c/Windows').exists(),'windows_mounted')
    data=sys.stdin.buffer.read(16385);require(len(data)<=16384,'input_bound')
    value=json.loads(data);mode=value['mode']
    require(mode in ('access','positive','wrong_peer','stale','client_denial'),'mode')
    sys.path.insert(0,str(INSTALL/'packages/claw-hermes'))
    result={'self':self_observed(),'mode':mode,'writesPerformed':False,'modelCalls':0}
    if mode=='access':result['accesses']=accesses()
    else:
        settings=value['settings']
        require(settings['socket_path'] in (str(STATE/'sock1/egress.sock'),str(STATE/'sock2/egress.sock')),'wrong_socket')
        result['transport']=asyncio.run(ping(settings,mode))
    print(json.dumps(result))

if __name__=='__main__':main()
