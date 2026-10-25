
import hashlib,json,os,pathlib,platform,stat,sys
expected=json.loads(sys.stdin.buffer.read(300000))
assert len(expected)==1162
lab='AlazHarness-D3B-P71C'
assert os.environ.get('WSL_DISTRO_NAME')==lab
assert pathlib.Path('/etc/alaz-p71c-lab-id').read_text().strip()==lab
assert os.getresuid()==(23001,)*3 and os.getresgid()==(23003,)*3
assert sys.executable=='/usr/bin/python3.12' and sys.flags.isolated==1 and sys.dont_write_bytecode
assert not pathlib.Path('/mnt/c/Windows').exists()
root=pathlib.Path('/opt/alaz-f126c1a6/dependencies')
def entry(p):
 s=p.lstat()
 return {'path':str(p),'uid':s.st_uid,'gid':s.st_gid,'mode':oct(stat.S_IMODE(s.st_mode)),'symlink':stat.S_ISLNK(s.st_mode),'device':s.st_dev,'inode':s.st_ino}
ancestry=[entry(p) for p in reversed((root,*root.parents))]
actual={};bad=[];directory_count=0
for p in root.rglob('*'):
 s=p.lstat()
 assert not stat.S_ISLNK(s.st_mode),'dependency_symlink'
 assert stat.S_ISREG(s.st_mode) or stat.S_ISDIR(s.st_mode),'dependency_type'
 if s.st_uid!=0 or s.st_gid!=0 or s.st_mode&0o022:bad.append(p.relative_to(root).as_posix())
 if stat.S_ISREG(s.st_mode):actual[p.relative_to(root).as_posix()]=hashlib.sha256(p.read_bytes()).hexdigest()
 else:directory_count+=1
assert actual==expected,'dependency_hash_mismatch'
py=pathlib.Path(sys.executable)
report={'kind':'R154A1_ORDINARY_READONLY_ENVIRONMENT','lab':lab,'uid':list(os.getresuid()),'gid':list(os.getresgid()),
'pythonVersion':platform.python_version(),'pythonSha256':hashlib.sha256(py.read_bytes()).hexdigest(),'pythonAncestry':[entry(p) for p in reversed((py,*py.parents))],
'kernel':platform.release(),'machine':platform.machine(),'dependencyRoot':str(root),'dependencyFiles':len(actual),'dependencyDirectories':directory_count,
'dependencyHashesMatch':True,'dependencyInventorySha256':hashlib.sha256((json.dumps(expected,sort_keys=True,indent=2,ensure_ascii=True)+'\n').encode()).hexdigest(),
'dependencyAncestry':ancestry,'untrustedDependencyEntryCount':len(bad),'untrustedDependencyPaths':bad[:10],
'freshPathExistence':{n:pathlib.Path(n).exists() for n in ('/opt/alaz-r153a1','/opt/alaz-r154a1','/srv/alaz-r154a1','/sys/fs/cgroup/alaz-r154a1')},
'rootUsed':False,'filesWritten':False,'providerCalls':0,'installed':False,'projectedReadinessAccepted':False}
print(json.dumps(report,sort_keys=True))
