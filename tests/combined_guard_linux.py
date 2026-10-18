"""Explicit dual-boundary kernel probe; owned canaries only, no real credentials.

Default unittest discovery does not launch this file. An intentionally reachable
owned pathname Unix socket records the residual gap, NOT an isolation success.
"""
from pathlib import Path
import argparse,datetime,hashlib,json,os,socket,subprocess,sys,tempfile,threading
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'packages/claw-hermes'))
from combined_guard import command_digest

CHILD=r"""
from pathlib import Path
import ctypes,errno,json,os,socket,sqlite3,stat,struct,subprocess,sys
c=json.loads(sys.argv[1]);work=Path(c['work']);checks={}
def denied(label,call):
 try:
  v=call()
  if type(v) is int:os.close(v)
 except OSError as e:checks[label]=e.errno in (errno.EPERM,errno.EACCES,errno.EXDEV)
 else:checks[label]=False
checks['readonly_canary_read']=Path(c['readonly']).read_text()=='owned-ro-canary'
(work/'value').write_text('owned-rw-canary')
checks['private_state_write']=(work/'value').read_text()=='owned-rw-canary'
with sqlite3.connect(work/'state.db') as db:
 db.execute('create table value(x)');db.execute('insert into value values (7)')
 checks['sqlite_write']=db.execute('select x from value').fetchone()[0]==7
for label,path,flags in [('secret_read',c['secret'],os.O_RDONLY),('secret_write',c['secret'],os.O_WRONLY),
                        ('readonly_write',c['readonly'],os.O_WRONLY),('parent_mem','/proc/'+str(c['parent'])+'/mem',os.O_RDONLY),
                        ('self_environ','/proc/self/environ',os.O_RDONLY)]:
 denied(label,lambda p=path,f=flags:os.open(p,f))
link=work/'alias';link.symlink_to(c['secret']);denied('symlink_secret_read',lambda:os.open(link,os.O_RDONLY))
denied('hardlink_secret',lambda:os.link(c['secret'],work/'linked'))
for label,descriptor in c['inherited'].items():
 try:s=os.fstat(descriptor['fd']);closed=(s.st_dev,s.st_ino)!=(descriptor['dev'],descriptor['ino'])
 except OSError:closed=True
 checks['inherited_'+label+'_closed']=closed
for family,address,label in [(socket.AF_INET,('127.0.0.1',c['tcp']),'ipv4'),(socket.AF_INET6,('::1',c['v6']),'ipv6')]:
 with socket.socket(family) as s:
  s.settimeout(.5);checks['host_'+label+'_blocked']=s.connect_ex(address)!=0
lib=ctypes.CDLL(None,use_errno=True);fd=lib.socket(2,1,0)
addr=struct.pack('H',2)+struct.pack('!H',c['tcp'])+socket.inet_aton('127.0.0.1')+b'\0'*8
try:checks['raw_libc_host_tcp_blocked']=lib.connect(fd,addr,len(addr))==-1 and ctypes.get_errno()==errno.ECONNREFUSED
finally:lib.close(fd)
checks['setns_blocked']=lib.setns(-1,0)==-1 and ctypes.get_errno()==errno.EPERM
checks['unshare_blocked']=lib.unshare(0)==-1 and ctypes.get_errno()==errno.EPERM
checks['recvmsg_blocked']=lib.recvmsg(-1,0,0)==-1 and ctypes.get_errno()==errno.EPERM
checks['process_vm_blocked']=lib.syscall(310,0,0,0,0,0,0)==-1 and ctypes.get_errno()==errno.EPERM
checks['no_new_privs']=lib.prctl(39,0,0,0,0)==1
checks['seccomp_active']=lib.prctl(21,0,0,0,0)==2
with socket.socket() as server:
 server.bind(('127.0.0.1',0));server.listen()
 with socket.socket() as client:
  client.connect(server.getsockname());peer,_=server.accept();peer.close()
 checks['private_loopback_works']=True
with socket.socket(socket.AF_UNIX) as unix:
 unix.connect(c['unix']);unix.sendall(b'owned-test');residual=unix.recv(32)==b'owned-ack'
script='import os,socket,sys,json\na=False\ntry:fd=os.open(sys.argv[1],os.O_RDONLY)\nexcept PermissionError:a=True\nelse:os.close(fd)\ns=socket.socket();s.settimeout(.5);b=s.connect_ex(("127.0.0.1",int(sys.argv[2])))!=0;s.close();print(json.dumps({"fileDenied":a,"hostDenied":b}))'
r=subprocess.run([sys.executable,'-I','-B','-c',script,c['secret'],str(c['tcp'])],capture_output=True,text=True,timeout=10)
d=json.loads(r.stdout) if r.returncode==0 else {}
checks['exec_descendant_filesystem_denial']=d.get('fileDenied') is True
checks['exec_descendant_network_denial']=d.get('hostDenied') is True
(work/'probe-finished').write_text('completed')
print(json.dumps({'result':'PASS' if all(checks.values()) else 'FAIL','pid':os.getpid(),'checks':checks,
 'residualObserved':{'ownedPathUnixSocketOutsideFileGrantsReachable':residual},'realModelCalls':0}))
raise SystemExit(0 if all(checks.values()) else 1)
"""


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',required=True,type=Path)
    output=parser.parse_args().output.resolve()
    assert sys.platform=='linux' and output.parent==(ROOT/'evidence/d3b-combined-dc64').resolve() and not output.exists()
    with tempfile.TemporaryDirectory(prefix='alaz-dual-kernel-') as temporary:
        root=Path(temporary);ro=root/'read';rw=root/'work';private=root/'private'
        for d in (ro,rw,private):d.mkdir(mode=0o700)
        secret=private/'secret';secret.write_bytes(os.urandom(48));secret.chmod(0o600)
        secret_hash=hashlib.sha256(secret.read_bytes()).hexdigest()
        readonly=ro/'source';readonly.write_text('owned-ro-canary')
        child=ro/'worker.py';child.write_text(CHILD)
        tcp=socket.socket();tcp.bind(('127.0.0.1',0));tcp.listen();tcp.settimeout(.2)
        v6=socket.socket(socket.AF_INET6);v6.bind(('::1',0));v6.listen();v6.settimeout(.2)
        inherited=socket.create_connection(tcp.getsockname());peer,_=tcp.accept();peer.close()
        v6test=socket.create_connection(v6.getsockname()[:2]);peer,_=v6.accept();peer.close();v6test.close()
        unix=socket.socket(socket.AF_UNIX);unix.bind(str(private/'ipc'));unix.listen();unix.settimeout(30)
        thread_errors=[]
        def respond():
            try:
                peer,_=unix.accept()
                with peer:
                    if peer.recv(32)!=b'owned-test':raise ValueError('unexpected fixture packet')
                    peer.sendall(b'owned-ack')
            except Exception as ex:thread_errors.append(type(ex).__name__)
        thread=threading.Thread(target=respond,daemon=True);thread.start()
        secret_fd=os.open(secret,os.O_RDONLY)
        fds={label:{'fd':fd,'dev':os.fstat(fd).st_dev,'ino':os.fstat(fd).st_ino}
             for label,fd in [('secret',secret_fd),('host_socket',inherited.fileno())]}
        config={'secret':str(secret),'readonly':str(readonly),'work':str(rw),'parent':os.getpid(),
                'tcp':tcp.getsockname()[1],'v6':v6.getsockname()[1],'unix':str(private/'ipc'),'inherited':fds}
        policy={'version':1,'enabled':True,'readonly':['/usr',str(ro),'/etc/ld.so.cache'],
                'writable':[str(rw),'/dev/null'],'protected':[str(secret)]}
        command=[sys.executable,'-I','-B',str(child),json.dumps(config)]
        contract={'version':1,'enabled':True,'launchId':'dual-kernel-owned','network':'loopback_only',
                  'filesystem':policy,'commandSha256':command_digest(command)}
        cfg=private/'contract.json';cfg.write_text(json.dumps(contract))
        receipt=rw/'combined.json'
        launch=[sys.executable,'-I','-B',str(ROOT/'scripts/run_combined_guard.py'),
                '--contract',str(cfg),'--receipt',str(receipt),'--',*command]
        env={'PATH':'/usr/bin:/bin','LANG':'C.UTF-8','HOME':str(rw),'TMPDIR':str(rw),'PYTHONDONTWRITEBYTECODE':'1'}
        try:
            run=subprocess.run(launch,cwd=rw,capture_output=True,text=True,timeout=40,env=env,
                               pass_fds=(secret_fd,inherited.fileno()))
        finally:os.close(secret_fd);inherited.close()
        result=json.loads(run.stdout) if run.stdout else {}
        record=json.loads(receipt.read_text()) if receipt.exists() else {}
        unexpected=0
        for server in (tcp,v6):
            try:peer,_=server.accept();peer.close();unexpected+=1
            except socket.timeout:pass
            server.close()
        thread.join(timeout=2);unix.close()
        negative_checks={}
        marker=rw/'must-not-execute'
        denied_command=[sys.executable,'-I','-B','-c','from pathlib import Path;Path(__import__("sys").argv[1]).write_text("bad")',str(marker)]
        for name,change in [('wrong_command_hash',{'commandSha256':'0'*64}),
                            ('network_disabled',{'network':'off'}),
                            ('unknown_authority',{'allowFallback':True}),
                            ('protected_in_writable',{'filesystem':policy|{'protected':[str(rw/'value')]}}),
                            ('secret_hardlink',{})]:
            altered={**contract,'commandSha256':command_digest(denied_command),**change}
            cfg.write_text(json.dumps(altered));refused_receipt=rw/(name+'.json')
            if name=='secret_hardlink':os.link(secret,private/'alias')
            try:
                refused=subprocess.run([*launch[:4],'--contract',str(cfg),'--receipt',str(refused_receipt),'--',*denied_command],
                                       cwd=rw,env=env,capture_output=True,timeout=15)
                negative_checks[name]=refused.returncode==2 and not refused_receipt.exists() and not marker.exists()
            finally:
                if name=='secret_hardlink':(private/'alias').unlink()
        unchanged=hashlib.sha256(secret.read_bytes()).hexdigest()==secret_hash
        samepid=result.get('pid')==record.get('pid')==record.get('network',{}).get('after',{}).get('pid') and bool(record)
        value={'observedAt':datetime.datetime.now().astimezone().isoformat(),
            'result':'PASS' if run.returncode==0 and result.get('result')=='PASS' and samepid and unchanged
                     and unexpected==0 and all(negative_checks.values()) and not thread_errors else 'FAIL',
            'exitCode':run.returncode,'probe':result,'launch':record,'startupRefusals':negative_checks,
            'samePidAcrossExec':samepid,'hostTcpAndIpv6PositiveControls':True,'unexpectedHostConnections':unexpected,
            'protectedUnchanged':unchanged,'secretContentPrinted':False,'unixProbeThreadErrors':thread_errors,
            'stderrDiagnostic':run.stderr[-1000:],'completeD3B':False,'independentBrokerBudgetAuthority':False,
            'unixSocketAuthorityIsolated':False,'realModelCalls':0,
            'sourceSha256':{p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in
                (ROOT/'packages/claw-hermes/combined_guard.py',ROOT/'scripts/run_combined_guard.py',Path(__file__))}}
    value['temporaryProbeRemoved']=not root.exists()
    with output.open('x',encoding='utf-8') as f:json.dump(value,f,indent=2);f.write('\n')
    print(json.dumps(value),flush=True)
    return 0 if value['result']=='PASS' else 1


if __name__=='__main__':raise SystemExit(main())
