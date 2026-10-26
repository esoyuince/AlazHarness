import hashlib,json,os,pathlib,pwd,grp,stat,subprocess,sys,time
P=pathlib.Path
assert os.getresuid()==(23001,)*3 and os.getresgid()==(23003,)*3
assert os.environ.get('WSL_DISTRO_NAME')=='AlazHarness-D3B-P71C'
assert P('/etc/alaz-p71c-lab-id').read_text().strip()=='AlazHarness-D3B-P71C'
assert not P('/mnt/c/Windows').exists()
source=P('/opt/alaz-r154a1-input/scripts/install_projected_candidate.py')
assert hashlib.sha256(source.read_bytes()).hexdigest()=='a56782d4e09bed38983c387d4b882e3db3866409e8e96e1f092d36517fc53525'
fresh=['/opt/alaz-r155a1-input','/srv/alaz-r155a1','/sys/fs/cgroup/alaz-r155a1','/tmp/alaz-ipc-r155a1']
existence={p:os.path.lexists(p) for p in fresh}
assert not any(existence.values()),existence
def describe(path):
    p=P(path);s=p.lstat()
    return {'path':str(p),'canonical':str(p.resolve()),'symlink':p.is_symlink(),'uid':s.st_uid,'gid':s.st_gid,'mode':stat.S_IMODE(s.st_mode),'device':s.st_dev,'inode':s.st_ino,'sha256':hashlib.sha256(p.read_bytes()).hexdigest() if stat.S_ISREG(s.st_mode) else None}
identities={'gateway':{'name':pwd.getpwuid(23001).pw_name,'uid':23001,'primaryGid':pwd.getpwuid(23001).pw_gid},'broker':{'name':pwd.getpwuid(23002).pw_name,'uid':23002,'primaryGid':pwd.getpwuid(23002).pw_gid},'socketGroup':{'name':grp.getgrgid(23003).gr_name,'gid':23003}}
argv=['/usr/bin/python3.12','-I','-B',str(source),'--candidate-directory','/opt/alaz-r154a1-input/candidate','--destination','/opt/alaz-r154a1','--dependencies','/opt/alaz-f126c1a6/dependencies','--expected-manifest-sha256','182b9d0198e4c7f39bd28e194bfe7fc6cfca844ed4a653e9d209b0db8d77eef9','--expected-archive-sha256','e036fba503130b3b259ec727439089c8fa3d88408359618fa5c7df77a6b5513b','--expected-harness-commit','e03f7fd4e47fea6a58b749564ab350aeb4237a26','--expected-python-sha256','e50d468e8b0adfb05733f5b87b3cff34829c4a8c1aea50c865aa8bdfe4bb150f','--verify-installed']
start=time.monotonic();r=subprocess.run(argv,cwd='/',env={'PATH':'/usr/bin:/bin','LANG':'C.UTF-8'},stdin=subprocess.DEVNULL,capture_output=True,timeout=60)
assert r.returncode==0,(r.returncode,r.stderr.decode(errors='replace'))
verified=json.loads(r.stdout);assert verified['result']=='PASS' and verified['verifiedInstalledBytesNow']
report={'kind':'R155A1_ORDINARY_INSTALLATION_AND_ENVIRONMENT_PREFLIGHT','result':'PASS','rootUsed':False,'writesPerformed':False,'actor':{'uid':os.getresuid(),'gid':os.getresgid(),'supplementaryGroups':os.getgroups()},'identities':identities,'freshPathsAbsent':existence,'uidMap':P('/proc/self/uid_map').read_text(),'gidMap':P('/proc/self/gid_map').read_text(),'mountNamespace':os.readlink('/proc/self/ns/mnt'),'userNamespace':os.readlink('/proc/self/ns/user'),'cgroup':P('/proc/self/cgroup').read_text(),'cgroupMounts':[line for line in P('/proc/self/mountinfo').read_text().splitlines() if ' - cgroup2 ' in line],'formatter':describe('/usr/sbin/mke2fs'),'python':describe('/usr/bin/python3.12'),'installation':verified,'installedVerifySeconds':round(time.monotonic()-start,3)}
print(json.dumps(report,sort_keys=True))
