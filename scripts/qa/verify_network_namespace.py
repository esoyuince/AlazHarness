"""Explicit Linux network namespace acceptance; only owned loopback canaries."""
import argparse,ctypes,errno,json,os,socket,struct,subprocess,sys,tempfile,threading
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'packages/claw-hermes'))
from linux_netns import enter,status

def raw_connect(port):
    lib=ctypes.CDLL(None,use_errno=True);fd=lib.socket(2,1,0)
    if fd<0:raise RuntimeError('raw_socket_failed')
    addr=struct.pack('H',2)+struct.pack('!H',port)+socket.inet_aton('127.0.0.1')+b'\0'*8
    try:
        rc=lib.connect(fd,addr,len(addr));err=ctypes.get_errno()
        return {'connected':rc==0,'errno':err if rc else 0}
    finally:lib.close(fd)

def child(cfg):
    receipt=enter();tests={}
    tests['different_network_namespace']=receipt['before']['netNamespace']!=receipt['after']['netNamespace']
    tests['capabilities_zero']=all(int(receipt['after'][k],16)==0 for k in ('CapEff','CapPrm','CapBnd','CapInh','CapAmb'))
    tests['filter_and_no_new_privs']=receipt['after']['Seccomp']=='2' and receipt['after']['NoNewPrivs']=='1'
    tests['inherited_host_socket_closed']=True
    try:tests['inherited_host_socket_closed']=not __import__('stat').S_ISSOCK(os.fstat(cfg['inheritedFd']).st_mode)
    except OSError:pass
    result=raw_connect(cfg['tcpPort'])
    tests['raw_libc_host_loopback_blocked']=not result['connected'] and result['errno']==errno.ECONNREFUSED
    with socket.socket() as s:
        s.settimeout(.5);tests['python_host_loopback_blocked']=s.connect_ex(('127.0.0.1',cfg['tcpPort']))!=0
    with socket.socket(socket.AF_INET6) as s:
        s.settimeout(.5);tests['ipv6_host_loopback_blocked']=s.connect_ex(('::1',cfg['v6Port']))!=0
    with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as s:
        try:s.sendto(b'forbidden',('198.51.100.1',9));tests['udp_no_external_route']=False
        except OSError as ex:tests['udp_no_external_route']=ex.errno in (errno.ENETUNREACH,errno.EHOSTUNREACH)
    tests['only_loopback_interface']=all(line.split(':',1)[0].strip()=='lo' for line in Path('/proc/net/dev').read_text().splitlines()[2:])
    lib=ctypes.CDLL(None,use_errno=True)
    tests['setns_blocked']=lib.setns(-1,0)==-1 and ctypes.get_errno()==errno.EPERM
    tests['unshare_blocked']=lib.unshare(0)==-1 and ctypes.get_errno()==errno.EPERM
    tests['io_uring_disabled']=lib.syscall(425,0,0)==-1 and ctypes.get_errno()==errno.ENOSYS
    tests['descriptor_receiving_blocked']=lib.recvmsg(-1,0,0)==-1 and ctypes.get_errno()==errno.EPERM
    p0,p1=socket.socketpair()
    try:
        p0.sendmsg([b'vectored',b'-reply']);tests['asyncio_vectored_write_supported']=p1.recv(32)==b'vectored-reply'
    finally:p0.close();p1.close()
    for domain,label in [(16,'netlink'),(17,'packet'),(40,'vsock')]:
        try:s=socket.socket(domain,socket.SOCK_DGRAM);s.close();tests[label+'_blocked']=False
        except OSError as ex:tests[label+'_blocked']=ex.errno==errno.EPERM
    with socket.socket(socket.AF_UNIX) as s:
        s.connect(cfg['unixPath']);s.sendall(b'broker');tests['explicit_path_unix_ipc_works']=s.recv(16)==b'ack'
    with socket.socket() as server:
        server.bind(('127.0.0.1',0));server.listen()
        with socket.socket() as client:
            client.connect(server.getsockname());peer,_=server.accept();peer.close()
        tests['private_loopback_works']=True
    descendant="import socket,json;from pathlib import Path;s=socket.socket();s.settimeout(.5);r=s.connect_ex(('127.0.0.1',"+str(cfg['tcpPort'])+"));print(json.dumps({'blocked':r!=0,'status':Path('/proc/self/status').read_text()}))"
    r=subprocess.run([sys.executable,'-I','-B','-c',descendant],capture_output=True,text=True,timeout=5)
    data=json.loads(r.stdout) if r.returncode==0 else {}
    tests['exec_child_cannot_reach_host']=data.get('blocked') is True
    tests['exec_child_inherits_filter']='NoNewPrivs:\t1' in data.get('status','') and 'Seccomp:\t2' in data.get('status','')
    print(json.dumps({'result':'PASS' if all(tests.values()) else 'FAIL','checks':tests,'boundary':receipt,'rawLibcConnect':result}),flush=True)
    return 0 if all(tests.values()) else 1

def parent(output):
    assert not output.exists() and output.parent.is_dir()
    with tempfile.TemporaryDirectory(prefix='alaz-netns-') as tmp:
        tcp=socket.socket();tcp.bind(('127.0.0.1',0));tcp.listen();tcp.settimeout(.2)
        v6=socket.socket(socket.AF_INET6);v6.bind(('::1',0));v6.listen()
        unix=socket.socket(socket.AF_UNIX);up=str(Path(tmp)/'ipc');unix.bind(up);unix.listen();unix.settimeout(10)
        def respond():
            c,_=unix.accept()
            with c:
                assert c.recv(16)==b'broker';c.sendall(b'ack')
        t=threading.Thread(target=respond,daemon=True);t.start()
        # Positive control and inherited descriptor challenge.
        inherited=socket.create_connection(tcp.getsockname());peer,_=tcp.accept();peer.close()
        cfg={'tcpPort':tcp.getsockname()[1],'v6Port':v6.getsockname()[1],'unixPath':up,'inheritedFd':inherited.fileno()}
        run=subprocess.run([sys.executable,'-B',str(Path(__file__).resolve()),'--child'],input=json.dumps(cfg),text=True,capture_output=True,timeout=25,pass_fds=(inherited.fileno(),))
        data=json.loads(run.stdout) if run.stdout.strip() else {'result':'FAIL','stderr':run.stderr[-1200:]}
        data['exitCode']=run.returncode;data['unconfinedHostTcpControl']=True
        try:c,_=tcp.accept();c.close();data['unexpectedHostTcpConnections']=1
        except socket.timeout:data['unexpectedHostTcpConnections']=0
        inherited.close();tcp.close();v6.close();unix.close();t.join(timeout=2)
        data['completeD3B']=False;data['hostFilesystemSeparated']=False;data['realModelCalls']=0
        data['scope']='raw libc/Python/exec and protocol tests; no external network contacted; path Unix IPC remains allowed'
        with output.open('x',encoding='utf-8') as f:json.dump(data,f,indent=2);f.write('\n')
        print(json.dumps(data),flush=True)
        return 0 if data['result']=='PASS' and data['unexpectedHostTcpConnections']==0 else 1

def main():
    p=argparse.ArgumentParser();p.add_argument('--child',action='store_true');p.add_argument('--output',type=Path);a=p.parse_args()
    if a.child:return child(json.load(sys.stdin))
    if a.output is None:raise SystemExit('output_required')
    return parent(a.output)
if __name__=='__main__':raise SystemExit(main())
