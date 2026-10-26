import hashlib,json,os,sys,types,time,traceback
from pathlib import Path
assert os.getresuid()==(23001,)*3 and sys.flags.isolated and sys.dont_write_bytecode
assert os.environ.get('WSL_DISTRO_NAME')=='AlazHarness-D3B-P71C'
path=Path('/tmp/alaz-r155a1-ordinary003/bootstrap_retained_profile.py')
raw=path.read_bytes()
assert hashlib.sha256(raw).hexdigest()=='f61e48fd52a5f895b63391f214d67c72dc14075a6aa91dbdeb0608e9b67dd279'
module=types.ModuleType('_r155_readonly_verifier_diagnostic')
module.__file__=str(path)
sys.modules[module.__name__]=module
exec(compile(raw,str(path),'exec'),module.__dict__)
os.umask(0o077)
started=time.monotonic()
report={'kind':'R155A1_READONLY_EMBEDDED_VERIFIER_DIAGNOSTIC','rootUsed':False,'nativeImportsAttempted':False,'writesPerformed':False,'producerSha256':hashlib.sha256(raw).hexdigest()}
try:
 result=module.verify_installation()
 report.update(result='PASS',verification=result)
except BaseException as exc:
 report.update(result='NOT_ACCEPTED',reasonType=type(exc).__name__,reason=str(exc),trace=[{'file':x.filename,'line':x.lineno,'function':x.name} for x in traceback.extract_tb(exc.__traceback__)])
report['elapsedMillis']=int((time.monotonic()-started)*1000)
print(json.dumps(report,sort_keys=True))
