import pathlib,subprocess,json,os,stat,hashlib
P=pathlib.Path
assert os.getresuid()==(23001,)*3
argv=['/usr/bin/python3.12','-I','-B','/opt/alaz-r154a1-input/scripts/install_projected_candidate.py','--candidate-directory','/opt/alaz-r154a1-input/candidate','--destination','/opt/alaz-r154a1','--dependencies','/opt/alaz-f126c1a6/dependencies','--expected-manifest-sha256','182b9d0198e4c7f39bd28e194bfe7fc6cfca844ed4a653e9d209b0db8d77eef9','--expected-archive-sha256','e036fba503130b3b259ec727439089c8fa3d88408359618fa5c7df77a6b5513b','--expected-harness-commit','e03f7fd4e47fea6a58b749564ab350aeb4237a26','--expected-python-sha256','e50d468e8b0adfb05733f5b87b3cff34829c4a8c1aea50c865aa8bdfe4bb150f','--verify-installed']
r=subprocess.run(argv,stdin=subprocess.DEVNULL,capture_output=True,timeout=30,env={'PATH':'/usr/bin:/bin','LANG':'C.UTF-8'},cwd='/')
paths={}
for n in ['/opt/alaz-r154a1','/usr/bin/python3.12','/opt/alaz-r154a1/.alaz-installation.json']:
 s=P(n).lstat();paths[n]={'device':s.st_dev,'inode':s.st_ino,'mode':stat.S_IMODE(s.st_mode),'uid':s.st_uid,'gid':s.st_gid,'sha256':hashlib.sha256(P(n).read_bytes()).hexdigest() if P(n).is_file() else None}
print(json.dumps({'kind':'R155A1_READONLY_INSTALLATION_RECHECK_AFTER_ORDINARY003','rootUsed':False,'writesPerformed':False,'exitCode':r.returncode,'stdout':r.stdout.decode('utf8','replace'),'stderr':r.stderr.decode('utf8','replace'),'paths':paths},sort_keys=True))