"""Real post-exec QA target; never send to a model or claim Hermes acceptance."""
import asyncio
import ctypes
import errno
import json
import os
from pathlib import Path
import socket
import sys
INSTALL=Path('/opt/alazharness-broker/802fade')
sys.path.insert(0,str(INSTALL/'packages/claw-hermes'))
CAPS=('CapInh','CapPrm','CapEff','CapBnd','CapAmb')

def observation():
    fields={}
    for line in Path('/proc/self/status').read_text().splitlines():
        key,_,value=line.partition(':')
        if key in ('Uid','Gid','Groups','Threads','NoNewPrivs','Seccomp',*CAPS):fields[key]=value.split()
    return {'pid':os.getpid(),'fields':fields,
            'namespaces':{name:os.readlink('/proc/self/ns/'+name) for name in ('user','mnt','net','ipc')}}

def connect(kind,address):
    with socket.socket(kind,socket.SOCK_STREAM) as s:
        s.settimeout(1)
        try:s.connect(address)
        except OSError as exc:return {'connected':False,'errno':exc.errno,'type':type(exc).__name__}
    return {'connected':True,'errno':None}

async def ping(settings):
    from provider_broker import ProviderBrokerClient,read_frame,write_frame
    from provider_egress import signed,verified,REQUEST_LIMIT,RESPONSE_LIMIT
    from host_principal import socket_peer
    import uuid
    native=await ProviderBrokerClient(settings).ready()
    reader,writer=await asyncio.open_unix_connection(settings['socket_path'])
    try:
        peer=socket_peer(writer.get_extra_info('socket'),settings['principal_contract'],role='gateway')
        nonce=uuid.uuid4().hex
        doc={'version':1,'operation':'ping','brokerId':settings['broker_id'],
             'routeFingerprint':settings['route_fingerprint'],'nonce':nonce}
        await write_frame(writer,signed(doc,settings['signing_key'],'request'),REQUEST_LIMIT)
        reply=verified(await read_frame(reader,RESPONSE_LIMIT),settings['signing_key'],'reply')
        return {'nativeClientReady':native,'peer':peer,'rawReplyOk':reply.get('ok') is True and reply.get('nonce')==nonce}
    finally:writer.close();await writer.wait_closed()

def main():
    receipt=json.loads(os.environ['G84E_ENTRY_RECEIPT']);state=observation()
    print(json.dumps({'phase':'ready','observation':state,'projection':receipt}),flush=True)
    data=json.loads(sys.stdin.buffer.readline(32769));checks={};details={}
    checks['gateway_uid_after_exec']=state['fields']['Uid']==['23001']*4 and state['fields']['Gid']==['23003']*4
    checks['zero_groups_and_capabilities']=not state['fields']['Groups'] and all(int(state['fields'][k][0],16)==0 for k in CAPS)
    checks['nnp_and_filter_inherited']=state['fields']['NoNewPrivs']==['1'] and state['fields']['Seccomp']==['2']
    checks['host_user_namespace_preserved']=state['namespaces']['user']==data['principal']['hostUserNamespace']
    checks['separate_network_mount_ipc']=all(state['namespaces'][k]!=data['parentNamespaces'][k] for k in ('net','mnt','ipc'))
    details['ping']=asyncio.run(ping(data['settings']))
    checks['real_broker_protocol_across_namespace']=details['ping']['nativeClientReady'] is True and details['ping']['rawReplyOk'] is True
    checks['real_broker_peer_uid_pid']=details['ping']['peer']=={'pid':data['brokerPid'],'uid':23002,'gid':23003}
    forbidden={
      'host_tcp':(socket.AF_INET,('127.0.0.1',data['tcpPort'])),
      'host_abstract':(socket.AF_UNIX,'\0'+data['abstractName']),
      'unrelated_path':(socket.AF_UNIX,data['ambientPath']),
      'broker_sibling':(socket.AF_UNIX,data['siblingPath']),
      'late_host_workspace_socket':(socket.AF_UNIX,data['latePath'])}
    for label,(kind,address) in forbidden.items():
        r=connect(kind,address);details[label]=r
        checks[label+'_blocked']=not r['connected'] and r['errno'] in (errno.EACCES,errno.EPERM,errno.ENOENT,errno.ECONNREFUSED,errno.ENETUNREACH)
    for name in ('config.json','budget/budget.sqlite3'):
        path=Path('/srv/alaz-p71c/private')/name
        try:fd=os.open(path,os.O_RDONLY)
        except OSError as exc:checks['private_path_hidden_'+name]=exc.errno==errno.ENOENT
        else:os.close(fd);checks['private_path_hidden_'+name]=False
    denied=[]
    for flags in (os.O_RDONLY,os.O_WRONLY):
        try:fd=os.open(data['canary'],flags)
        except OSError as exc:denied.append(exc.errno)
        else:os.close(fd);denied.append(0)
    details['protectedCanaryErrnos']=denied
    checks['present_canary_denied_read_write']=Path(data['canary']).is_file() and all(e in (errno.EACCES,errno.EPERM) for e in denied)
    inherited=data['inheritedFd']
    try:os.fstat(inherited)
    except OSError as exc:checks['inherited_host_fd_closed']=exc.errno==errno.EBADF
    else:checks['inherited_host_fd_closed']=False
    work=Path(data['workspace']);marker=work/'private-only.txt';marker.write_text('owned ephemeral fixture')
    checks['ephemeral_workspace_read_write']=marker.read_text()=='owned ephemeral fixture'
    with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as local:
        path=work/'own.sock';local.bind(str(path));local.listen(1)
        checks['private_runtime_socket_works']=connect(socket.AF_UNIX,str(path))['connected']
    path.unlink()
    with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as local:
        local.bind(('127.0.0.1',0));local.listen(1)
        checks['private_loopback_works']=connect(socket.AF_INET,local.getsockname())['connected']
    checks['old_root_and_foreign_proc_hidden']=not any(Path(p).exists() for p in ('/.old-root','/proc/1','/mnt/c','/run/WSL'))
    lib=ctypes.CDLL(None,use_errno=True)
    result=lib.unshare(ctypes.c_int(0x40000000));checks['new_namespace_syscall_denied']=result==-1 and ctypes.get_errno()==errno.EPERM
    with socket.socket(socket.AF_UNIX,socket.SOCK_DGRAM) as recv:
        recv.setblocking(False)
        try:recv.recvmsg(1)
        except OSError as exc:checks['descriptor_receive_syscall_denied']=exc.errno==errno.EPERM
        else:checks['descriptor_receive_syscall_denied']=False
    try:fd=os.open('/usr/g84e-never-created',os.O_CREAT|os.O_WRONLY,0o600)
    except OSError as exc:checks['runtime_readonly']=exc.errno in (errno.EACCES,errno.EPERM,errno.EROFS)
    else:os.close(fd);checks['runtime_readonly']=False
    print(json.dumps({'phase':'result','result':'PASS' if all(checks.values()) else 'FAIL',
                      'checks':checks,'details':details,'checkCount':len(checks),'realHermesGateway':False,
                      'providerSend':False,'fullD3B':False}),flush=True)
    return 0 if all(checks.values()) else 1
if __name__=='__main__':raise SystemExit(main())
