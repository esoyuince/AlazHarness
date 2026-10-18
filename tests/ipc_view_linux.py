"""Opt-in owned-socket kernel proof; never touches existing host services."""
from pathlib import Path
import argparse,datetime,hashlib,json,os,socket,stat,subprocess,sys,tempfile,threading
ROOT=Path(__file__).resolve().parents[1]

CHILD=r"""
import sys,json,os,socket,ctypes,errno,subprocess
from pathlib import Path
sys.path.insert(0,sys.argv[1]);from combined_guard import enforce
c=json.loads(sys.argv[2]);contract=c['contract'];record=enforce(contract,c['command']);checks={}
checks['source_read']=Path(c['source']).read_text()=='source-canary'
Path(c['work']+'/write.txt').write_text('owned-runtime')
checks['runtime_write']=Path(c['work']+'/write.txt').read_text()=='owned-runtime'
checks['parent_process_hidden']=not Path('/proc/'+str(c['parent'])).exists()
checks['host_mounts_hidden']=not Path('/mnt/c').exists() and not Path('/run/WSL').exists()
checks['old_root_detached']=not Path('/.old-root').exists()
checks['broker_parent_private']=(Path(c['broker']).parent.stat().st_mode&0o777)==0o700
try:Path(c['secret']).read_bytes()
except PermissionError:checks['secret_unreadable']=True
else:checks['secret_unreadable']=False
for name,address in [('original_path',c['blocked']),('proc_parent_root','/proc/'+str(c['parent'])+'/root'+c['blocked'])]:
 with socket.socket(socket.AF_UNIX) as s:
  s.settimeout(.6);checks[name+'_blocked']=s.connect_ex(address)!=0
alias=Path(c['work'])/'alias';alias.symlink_to(c['blocked'])
with socket.socket(socket.AF_UNIX) as s:checks['symlink_blocked']=s.connect_ex(str(alias))!=0
with socket.socket(socket.AF_UNIX) as s:
 s.connect(c['broker']);s.sendall(b'owned');checks['explicit_broker_works']=s.recv(16)==b'ack'
with socket.socket(socket.AF_UNIX) as s:checks['host_abstract_blocked']=s.connect_ex('\0'+c['abstract'])!=0
with socket.socket() as s:s.settimeout(.6);checks['host_tcp_blocked']=s.connect_ex(('127.0.0.1',c['tcp']))!=0
with socket.socket() as a:
 a.bind(('127.0.0.1',0));a.listen()
 with socket.socket() as b:b.connect(a.getsockname());peer,_=a.accept();peer.close()
 checks['private_loopback_works']=True
with socket.socket(socket.AF_UNIX) as a:
 a.bind(c['work']+'/local.sock');a.listen()
 with socket.socket(socket.AF_UNIX) as b:b.connect(c['work']+'/local.sock');peer,_=a.accept();peer.close()
 checks['runtime_socket_works']=True
lib=ctypes.CDLL(None,use_errno=True)
checks['mount_forbidden']=lib.mount(None,b'/',None,0,None)==-1 and ctypes.get_errno()==errno.EPERM
checks['chroot_forbidden']=lib.chroot(b'/')==-1 and ctypes.get_errno()==errno.EPERM
checks['namespace_join_forbidden']=lib.setns(-1,0)==-1 and ctypes.get_errno()==errno.EPERM
checks['fd_receive_forbidden']=lib.recvmsg(-1,None,0)==-1 and ctypes.get_errno()==errno.EPERM
fd=lib.socket(1,1,0)
raw=__import__('struct').pack('H',1)+c['blocked'].encode()+b'\0'
try:checks['raw_connect_blocked']=lib.connect(fd,raw,len(raw))==-1
finally:lib.close(fd)
for name,item in c['inherited'].items():
 try:s=os.fstat(item['fd']);checks['inherited_'+name+'_closed']=(s.st_dev,s.st_ino)!=(item['dev'],item['ino'])
 except OSError:checks['inherited_'+name+'_closed']=True
code='import socket,sys,json\ns=socket.socket(socket.AF_UNIX);blocked=s.connect_ex(sys.argv[1])!=0;s.close();s=socket.socket(socket.AF_UNIX);s.connect(sys.argv[2]);s.sendall(b"owned");allowed=s.recv(16)==b"ack";s.close();print(json.dumps({"blocked":blocked,"allowed":allowed}))'
r=subprocess.run([sys.executable,'-I','-B','-c',code,c['blocked'],c['broker']],capture_output=True,text=True,timeout=8)
a=json.loads(r.stdout) if r.returncode==0 else {}
checks['exec_child_host_denied']=a.get('blocked') is True
checks['exec_child_broker_allowed']=a.get('allowed') is True
print(json.dumps({'result':'PASS' if all(checks.values()) else 'FAIL','pid':os.getpid(),'checks':checks,'guard':record}))
raise SystemExit(0 if all(checks.values()) else 1)
"""


def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);args=p.parse_args()
 out=args.output.resolve();assert sys.platform=='linux' and not out.exists() and out.parent==(ROOT/'evidence/d3b-ipc-a731').resolve()
 with tempfile.TemporaryDirectory(prefix='alaz-ipc-case-') as td, tempfile.TemporaryDirectory(prefix='alaz-ipc-root-') as rd:
  base=Path(td);anchor=Path(rd);anchor.chmod(0o700)
  ro=base/'ro';rw=base/'rw';bro=base/'broker';private=base/'private'
  for d in (ro,rw,bro,private):d.mkdir(mode=0o700)
  source=ro/'source';source.write_text('source-canary');secret=private/'secret';secret.write_bytes(os.urandom(40));secret_hash=hashlib.sha256(secret.read_bytes()).hexdigest()
  count={'broker':0,'blocked':0,'tcp':0,'abstract':0};servers={};errors=[];stop=threading.Event();threads=[]
  for label,path in [('broker',str(bro/'b.sock')),('blocked',str(private/'h.sock')),('abstract','\0alaz-ipc-'+str(os.getpid()))]:
   s=socket.socket(socket.AF_UNIX);s.bind(path);s.listen();s.settimeout(.1);servers[label]=s
   if not path.startswith('\0'):Path(path).chmod(0o600)
  tcp=socket.socket();tcp.bind(('127.0.0.1',0));tcp.listen();tcp.settimeout(.1);servers['tcp']=tcp
  # Positive controls prove every test endpoint was live BEFORE sandboxing.
  for label,s in servers.items():
   with socket.socket(s.family) as c:c.connect(s.getsockname());peer,_=s.accept();peer.close()
  def serve(label,s):
   while not stop.is_set():
    try:peer,_=s.accept()
    except socket.timeout:continue
    except OSError:return
    count[label]+=1
    with peer:
     peer.settimeout(1)
     try:
      if peer.recv(16)==b'owned':peer.sendall(b'ack')
     except OSError:pass
  for label,s in servers.items():
   th=threading.Thread(target=serve,args=(label,s),daemon=True);threads.append(th);th.start()
  inherited=os.open(secret,os.O_RDONLY);carry=socket.socket(socket.AF_UNIX);carry.connect(str(private/'h.sock'))
  # Carrying an already connected socket is a separate explicit negative.
  import time;time.sleep(.15);count['blocked']=0
  descriptors={name:{'fd':fd,'dev':os.fstat(fd).st_dev,'ino':os.fstat(fd).st_ino} for name,fd in [('secret',inherited),('host_socket',carry.fileno())]}
  fs={'version':1,'enabled':True,'readonly':['/usr',str(ro),'/dev/urandom','/etc/ld.so.cache'],'writable':[str(rw),'/dev/null'],'protected':[str(secret)]}
  cmd=[sys.executable,'-I','-B','-c','test-owned-kernel-probe']
  sys.path.insert(0,str(ROOT/'packages/claw-hermes'));from combined_guard import command_digest
  contract={'version':1,'enabled':True,'launchId':'ipc-kernel-owned','network':'loopback_only','filesystem':fs,'commandSha256':command_digest(cmd),'ipc':{'version':1,'mode':'projected_root','root':str(anchor),'brokerSocket':str(bro/'b.sock')}}
  cfg={'contract':contract,'command':cmd,'source':str(source),'work':str(rw),'secret':str(secret),'broker':str(bro/'b.sock'),'blocked':str(private/'h.sock'),'parent':os.getpid(),'tcp':tcp.getsockname()[1],'abstract':'alaz-ipc-'+str(os.getpid()),'inherited':descriptors}
  refusals={}
  refused_probe="import sys,json;sys.path.insert(0,sys.argv[1]);from combined_guard import enforce;c=json.loads(sys.argv[2]);enforce(c['contract'],c['command']);from pathlib import Path;Path(c['marker']).write_text('executed')"
  marker=rw/'must-not-start'
  for label in ('extra_socket_in_runtime','symlink_broker','wide_broker_permissions','nonempty_anchor','command_mismatch'):
   alternative=json.loads(json.dumps(contract));aux=None
   if label=='extra_socket_in_runtime':
    aux=socket.socket(socket.AF_UNIX);aux.bind(str(rw/'ambient.sock'))
   elif label=='symlink_broker':
    (bro/'alias').symlink_to(bro/'b.sock');alternative['ipc']['brokerSocket']=str(bro/'alias')
   elif label=='wide_broker_permissions':(bro/'b.sock').chmod(0o666)
   elif label=='nonempty_anchor':(anchor/'unexpected').write_text('must refuse')
   elif label=='command_mismatch':alternative['commandSha256']='0'*64
   try:
    attempt={'contract':alternative,'command':cmd,'marker':str(marker)}
    denied=subprocess.run([sys.executable,'-I','-B','-c',refused_probe,str(ROOT/'packages/claw-hermes'),json.dumps(attempt)],cwd=rw,env={'PATH':'/usr/bin:/bin','HOME':str(rw)},capture_output=True,text=True,timeout=25)
    refusals[label]={'refused':denied.returncode!=0 and not marker.exists(),'exitCode':denied.returncode,'reason':denied.stderr.splitlines()[-1:]}
   finally:
    if aux is not None:aux.close();(rw/'ambient.sock').unlink()
    if label=='symlink_broker':(bro/'alias').unlink()
    if label=='wide_broker_permissions':(bro/'b.sock').chmod(0o600)
    if label=='nonempty_anchor':(anchor/'unexpected').unlink()
  try:r=subprocess.run([sys.executable,'-I','-B','-c',CHILD,str(ROOT/'packages/claw-hermes'),json.dumps(cfg)],cwd=rw,env={'PATH':'/usr/bin:/bin','HOME':str(rw),'TMPDIR':str(rw)},pass_fds=(inherited,carry.fileno()),capture_output=True,text=True,timeout=70)
  finally:os.close(inherited);carry.close();stop.set();[th.join(timeout=2) for th in threads];[s.close() for s in servers.values()]
  data=json.loads(r.stdout) if r.stdout else {};protected_same=hashlib.sha256(secret.read_bytes()).hexdigest()==secret_hash
  value={'observedAt':datetime.datetime.now().astimezone().isoformat(),'result':'PASS' if r.returncode==0 and data.get('result')=='PASS' and count=={'broker':2,'blocked':0,'tcp':0,'abstract':0} and protected_same and all(v['refused'] for v in refusals.values()) else 'FAIL','exitCode':r.returncode,'probe':data,'ownedServerCounts':count,'positiveControlsAllLive':True,'protectedUnchanged':protected_same,'startupRefusals':refusals,'stderr':r.stderr[-2200:],'completeD3B':False,'realModelCalls':0,'sourceSha256':{n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in ['packages/claw-hermes/ipc_view.py','packages/claw-hermes/combined_guard.py','packages/claw-hermes/linux_netns.py']}}
 value['temporaryRootsRemoved']=not base.exists() and not anchor.exists()
 with out.open('x',encoding='utf-8') as f:json.dump(value,f,indent=2);f.write('\n')
 print(json.dumps(value));return 0 if value['result']=='PASS' else 1


if __name__=='__main__':raise SystemExit(main())
