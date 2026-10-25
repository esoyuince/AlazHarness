"""Recorded R154 ordinary-user validation of the frozen real install candidate."""
import hashlib
import json
from pathlib import Path
import subprocess

WORK = Path(r'C:\Antigravity\AlazHarness\scratch\worktrees\m1-install-readiness-r154a1')
ATTEMPT = WORK / 'scratch/install-candidates/r154a1-install-001'
INSTALLER = 'a56782d4e09bed38983c387d4b882e3db3866409e8e96e1f092d36517fc53525'
BUILDER = '97be4be2a0aec7a045fd099b1f56b12c58501e312777e1ad67fee45cbe601cc7'

LINUX = r'''
import hashlib,io,json,os,pathlib,subprocess,sys,tempfile,zipfile
assert os.getresuid()==(23001,)*3 and os.getresgid()==(23003,)*3
assert os.environ.get('WSL_DISTRO_NAME')=='AlazHarness-D3B-P71C'
assert pathlib.Path('/etc/alaz-p71c-lab-id').read_text().strip()=='AlazHarness-D3B-P71C'
assert sys.executable=='/usr/bin/python3.12' and sys.flags.isolated and sys.dont_write_bytecode
assert not pathlib.Path('/mnt/c/Windows').exists()
intent=json.loads(sys.argv[1]);raw=sys.stdin.buffer.read(24*1024*1024+1)
sha=lambda data:hashlib.sha256(data).hexdigest()
assert len(raw)==intent['bundleBytes']<=24*1024*1024 and sha(raw)==intent['bundleSha256']
expected={
 'scripts/install_projected_candidate.py':'a56782d4e09bed38983c387d4b882e3db3866409e8e96e1f092d36517fc53525',
 'scripts/build_projected_candidate.py':'97be4be2a0aec7a045fd099b1f56b12c58501e312777e1ad67fee45cbe601cc7',
 'candidate/manifest.json':'182b9d0198e4c7f39bd28e194bfe7fc6cfca844ed4a653e9d209b0db8d77eef9',
 'candidate/projected-source.tar':'e036fba503130b3b259ec727439089c8fa3d88408359618fa5c7df77a6b5513b'}
files={}
with zipfile.ZipFile(io.BytesIO(raw)) as archive:
 infos=archive.infolist()
 assert len(infos)==4 and {i.filename for i in infos}==set(expected)
 for info in infos:
  assert info.compress_type==zipfile.ZIP_STORED and 0<info.file_size==info.compress_size<=24*1024*1024
  data=archive.read(info);assert sha(data)==expected[info.filename];files[info.filename]=data
root=pathlib.Path(tempfile.mkdtemp(prefix='alaz-r154a1-preflight-'))
root.chmod(0o700);identity=(root.stat().st_dev,root.stat().st_ino,root.stat().st_uid)
for folder in ('scripts','candidate'):(root/folder).mkdir(mode=0o700)
for name,data in files.items():
 with (root/name).open('xb') as stream:stream.write(data)
 (root/name).chmod(0o600)
 assert sha((root/name).read_bytes())==expected[name]
command=['/usr/bin/python3.12','-I','-B',str(root/'scripts/install_projected_candidate.py'),
 '--candidate-directory',str(root/'candidate'),'--destination','/opt/alaz-r154a1',
 '--dependencies','/opt/alaz-f126c1a6/dependencies',
 '--expected-manifest-sha256',expected['candidate/manifest.json'],
 '--expected-archive-sha256',expected['candidate/projected-source.tar'],
 '--expected-harness-commit','e03f7fd4e47fea6a58b749564ab350aeb4237a26',
 '--expected-python-sha256','e50d468e8b0adfb05733f5b87b3cff34829c4a8c1aea50c865aa8bdfe4bb150f','--verify-only']
proc=subprocess.Popen(command,cwd='/',env={'PATH':'/usr/bin:/bin','LANG':'C.UTF-8','HOME':'/'},
 stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,close_fds=True)
try:out,err=proc.communicate(timeout=60)
except subprocess.TimeoutExpired:
 print(json.dumps({'state':'UNKNOWN','pid':proc.pid,'temporaryInput':str(root),'rootUsed':False,'installed':False}),flush=True)
 raise SystemExit(2)
assert len(out)<65536 and len(err)<65536
unchanged=all(sha((root/name).read_bytes())==value for name,value in expected.items())
assert identity==(root.stat().st_dev,root.stat().st_ino,root.stat().st_uid)
result=json.loads(out) if proc.returncode==0 else None
passed=proc.returncode==0 and not err and unchanged and result.get('kind')=='VERIFIED_INSTALLATION_INPUTS'
passed=passed and result.get('installed') is False and result.get('sourceFileCount')==834 and result.get('dependencyFileCount')==1162
report={'state':'PASS_REAL_CANDIDATE_PREFLIGHT' if passed else 'NOT_ACCEPTED','exitCode':proc.returncode,
 'stdout':out.decode(),'stderr':err.decode(),'result':result,'temporaryInput':str(root),'temporaryIdentity':identity,
 'inputSourcesUnchanged':unchanged,'temporaryInputRetained':True,'rootUsed':False,'installed':False,
 'projectedReadinessAccepted':False,'finiteWorkExecuted':False,'realModelCalls':0}
print(json.dumps(report,sort_keys=True),flush=True)
raise SystemExit(0 if passed else 2)
'''


def put(name, data):
    with (ATTEMPT / name).open('xb') as stream:
        stream.write(data)


intent = json.loads((ATTEMPT / 'intent.json').read_bytes())
assert intent['installerSha256'] == INSTALLER and intent['builderSha256'] == BUILDER
raw = (ATTEMPT / 'input.zip').read_bytes()
assert len(raw) == intent['bundleBytes'] and hashlib.sha256(raw).hexdigest() == intent['bundleSha256']
put('preflight-start.json', (json.dumps({'state': 'READONLY_PREFLIGHT_STARTED_NO_REPLAY',
    'bundleSha256': intent['bundleSha256'], 'rootRequested': False}) + '\n').encode())
command = ['wsl.exe', '--distribution', 'AlazHarness-D3B-P71C', '--user', 'alazgateway',
           '--cd', '/', '--exec', '/usr/bin/python3.12', '-I', '-B', '-c', LINUX, json.dumps(intent)]
proc = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
try:
    out, err = proc.communicate(raw, timeout=90)
except subprocess.TimeoutExpired:
    put('preflight-terminal.json', (json.dumps({'state': 'UNKNOWN', 'hostPid': proc.pid,
        'processMayBeRunning': True, 'rootUsed': False, 'installed': False}) + '\n').encode())
    raise SystemExit(2)
put('preflight-stdout.txt', out)
put('preflight-stderr.txt', err)
result = json.loads(out) if proc.returncode == 0 else None
terminal = {'state': 'PASS_REAL_CANDIDATE_PREFLIGHT' if proc.returncode == 0 and not err else 'NOT_ACCEPTED',
            'exitCode': proc.returncode, 'rootUsed': False, 'installed': False,
            'stdoutSha256': hashlib.sha256(out).hexdigest(), 'stderrSha256': hashlib.sha256(err).hexdigest()}
put('preflight-terminal.json', (json.dumps(terminal, indent=2) + '\n').encode())
if result is not None:
    put('preflight-result.json', (json.dumps(result, indent=2) + '\n').encode())
print(json.dumps(terminal, sort_keys=True))
raise SystemExit(0 if terminal['state'] == 'PASS_REAL_CANDIDATE_PREFLIGHT' else 2)
