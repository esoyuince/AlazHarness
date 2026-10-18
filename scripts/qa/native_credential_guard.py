"""Explicit Linux Landlock child acceptance; no model/provider/user secret."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
ROOT=Path(__file__).resolve().parents[2]
CHILD = r"""
import os,json,sys,errno,sqlite3,subprocess,ctypes
from pathlib import Path
secret,readonly,runtime,parent=sys.argv[1:]
runtime=Path(runtime);errors=[];checks={}
def denied(name,call):
 try:
  value=call()
  if isinstance(value,int):os.close(value)
 except OSError as ex:
  checks[name]=ex.errno in (errno.EACCES,errno.EPERM,errno.EXDEV)
 else:checks[name]=False
 if not checks[name]:errors.append(name)
checks['allowed_read']=Path(readonly).read_text()=='readonly-canary'
(runtime/'allowed.txt').write_text('state stays writable')
checks['allowed_write']=(runtime/'allowed.txt').read_text()=='state stays writable'
with sqlite3.connect(runtime/'state.db') as c:
 c.execute('create table test(x integer)');c.execute('insert into test values (7)')
 checks['sqlite_native_write']=c.execute('select x from test').fetchone()[0]==7
denied('secret_read',lambda:os.open(secret,os.O_RDONLY))
denied('secret_write',lambda:os.open(secret,os.O_WRONLY))
denied('readonly_write',lambda:os.open(readonly,os.O_WRONLY))
denied('readonly_truncate',lambda:os.open(readonly,os.O_RDONLY|os.O_TRUNC))
link=runtime/'alias';link.symlink_to(secret)
denied('symlink_secret_read',lambda:os.open(link,os.O_RDONLY))
denied('hardlink_secret',lambda:os.link(secret,runtime/'hardlink'))
denied('parent_memory',lambda:os.open('/proc/'+parent+'/mem',os.O_RDONLY))
script='import os,sys;\ntry: f=os.open(sys.argv[1],os.O_RDONLY)\nexcept PermissionError: sys.exit(0)\nelse: os.close(f);sys.exit(9)'
x=subprocess.run([sys.executable,'-I','-B','-c',script,secret],capture_output=True)
checks['exec_descendant_secret_denied']=x.returncode==0
libc=ctypes.CDLL(None,use_errno=True)
checks['no_new_privs']=libc.prctl(39,0,0,0,0)==1
checks['cannot_unset_no_new_privs']=libc.prctl(38,0,0,0,0)!=0
print(json.dumps({'checks':checks,'result':'PASS' if all(checks.values()) and not errors else 'FAIL','errors':errors,'secretPrinted':False}))
sys.exit(0 if all(checks.values()) and not errors else 1)
"""
def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 assert sys.platform=='linux'
 out=a.output.resolve();assert not out.exists() and out.parent==(ROOT/'evidence/d3b-credential-6e42').resolve()
 with tempfile.TemporaryDirectory(prefix='alaz-fsguard-') as tmp:
  root=Path(tmp);ro=root/'readonly';rw=root/'runtime';private=root/'private'
  for d in (ro,rw,private):d.mkdir(mode=0o700)
  secret=private/'broker.json';secret.write_bytes(os.urandom(48));secret.chmod(0o600)
  before=hashlib.sha256(secret.read_bytes()).hexdigest()
  source=ro/'worker.py';source.write_text(CHILD)
  canary=ro/'data.txt';canary.write_text('readonly-canary')
  policy={'version':1,'enabled':True,'readonly':['/usr',str(ro),str((ROOT/'packages').resolve()),str((ROOT/'scripts').resolve()),'/etc/ld.so.cache'],
          'writable':[str(rw),'/dev/null'],'protected':[str(secret)]}
  cfg=private/'policy.json';cfg.write_text(json.dumps(policy));cfg.chmod(0o600)
  receipt=rw/'guard.json'
  command=[sys.executable,'-I','-B',str(ROOT/'scripts/run_credential_guard.py'),'--policy',str(cfg),'--receipt',str(receipt),'--',sys.executable,'-I','-B',str(source),str(secret),str(canary),str(rw),str(os.getpid())]
  run=subprocess.run(command,cwd=rw,capture_output=True,timeout=25,env={'PATH':'/usr/bin:/bin','LANG':'C.UTF-8','PYTHONDONTWRITEBYTECODE':'1'})
  data=json.loads(run.stdout) if run.stdout else {}
  # Ambient capability controls are independent of the successful child probe.
  block_checks={}
  negative=command.copy();negative[negative.index('--receipt')+1]=str(rw/'must-not-exist.json')
  fd=os.open(secret,os.O_RDONLY)
  try:
   trial=subprocess.run(negative,cwd=rw,capture_output=True,timeout=15,pass_fds=(fd,))
   block_checks['preopened_secret_fd_refused']=(trial.returncode==2 and not (rw/'must-not-exist.json').exists()
       and b'credential_guard_inherited_fd' in trial.stderr)
  finally:os.close(fd)
  import socket
  left,right=socket.socketpair()
  try:
   trial=subprocess.run(negative,cwd=rw,capture_output=True,timeout=15,stdin=left)
   block_checks['socket_stdio_refused']=(trial.returncode==2 and not (rw/'must-not-exist.json').exists()
       and b'credential_guard_socket_stdio' in trial.stderr)
  finally:left.close();right.close()
  os.link(secret,private/'preexisting-alias')
  try:
   trial=subprocess.run(negative,cwd=rw,capture_output=True,timeout=15)
   block_checks['preexisting_secret_hardlink_refused']=(trial.returncode==2
       and not (rw/'must-not-exist.json').exists() and b'credential_guard_protected_alias' in trial.stderr)
  finally:(private/'preexisting-alias').unlink()

  result={'result':'PASS' if run.returncode==0 and data.get('result')=='PASS' and all(block_checks.values()) else 'FAIL',
          'exitCode':run.returncode,'startupRefusals':block_checks,'probe':data,'guard':json.loads(receipt.read_text()) if receipt.exists() else None,
          'stderr':run.stderr.decode('utf-8','replace')[-2000:],
          'protectedOriginalUnchanged':hashlib.sha256(secret.read_bytes()).hexdigest()==before,
          'readonlyOriginalUnchanged':canary.read_text()=='readonly-canary',
          'networkBoundaryClaimed':False,'sameHostUid':True,'realModelCalls':0}
 out.write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps(result));return 0 if result['result']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
