import hashlib,os,pathlib,sys
assert os.getresuid()==(23001,)*3 and os.getresgid()==(23003,)*3
assert os.environ.get('WSL_DISTRO_NAME')=='AlazHarness-D3B-P71C'
assert pathlib.Path('/etc/alaz-p71c-lab-id').read_text().strip()=='AlazHarness-D3B-P71C'
source=pathlib.Path('/opt/alaz-r154a1-input/scripts/install_projected_candidate.py')
assert hashlib.sha256(source.read_bytes()).hexdigest()=='a56782d4e09bed38983c387d4b882e3db3866409e8e96e1f092d36517fc53525'
os.execve('/usr/bin/python3.12',['/usr/bin/python3.12','-I','-B',str(source),
'--candidate-directory','/opt/alaz-r154a1-input/candidate','--destination','/opt/alaz-r154a1',
'--dependencies','/opt/alaz-f126c1a6/dependencies',
'--expected-manifest-sha256','182b9d0198e4c7f39bd28e194bfe7fc6cfca844ed4a653e9d209b0db8d77eef9',
'--expected-archive-sha256','e036fba503130b3b259ec727439089c8fa3d88408359618fa5c7df77a6b5513b',
'--expected-harness-commit','e03f7fd4e47fea6a58b749564ab350aeb4237a26',
'--expected-python-sha256','e50d468e8b0adfb05733f5b87b3cff34829c4a8c1aea50c865aa8bdfe4bb150f',
'--verify-installed'],{'PATH':'/usr/bin:/bin','LANG':'C.UTF-8','HOME':'/'})
