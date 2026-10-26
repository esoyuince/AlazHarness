import json,subprocess,base64,time
started=time.monotonic()
p=subprocess.Popen(["wsl.exe","--distribution","AlazHarness-D3B-P71C","--user","alazgateway","--cd","/","--exec","/usr/bin/python3.12","-I","-B","-c","import pathlib,os,json\nP=pathlib.Path\nassert os.getresuid()==(23001,)*3\nassert P('/etc/alaz-p71c-lab-id').read_text().strip()=='AlazHarness-D3B-P71C'\nprint(json.dumps({'kind':'R155A1_READONLY_LAB_AFTER_HCS_TIMEOUT','uid':os.getuid(),'pid':os.getpid(),'rootUsed':False,'nativeImportsAttempted':False,'writesPerformed':False,'ordinary006Exists':P('/tmp/alaz-r155a1-ordinary006').exists(),'rootPaths':{n:os.path.lexists(n) for n in ['/opt/alaz-r155a1-input','/srv/alaz-r155a1','/sys/fs/cgroup/alaz-r155a1','/tmp/alaz-ipc-r155a1']},'userNamespace':os.readlink('/proc/self/ns/user')},sort_keys=True))"],stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
try:
 out,err=p.communicate(timeout=70)
 print(json.dumps({'kind':'R155A1_POST_HCS_READONLY_CARRIER','exitCode':p.returncode,'pid':p.pid,'elapsedMillis':int((time.monotonic()-started)*1000),'stdoutBase64':base64.b64encode(out).decode(),'stdout':out.decode('utf-16-le' if b'\x00' in out else 'utf8','replace'),'stderrBase64':base64.b64encode(err).decode()},sort_keys=True))
except subprocess.TimeoutExpired as e:
 print(json.dumps({'kind':'R155A1_POST_HCS_READONLY_CARRIER','state':'READONLY_OUTCOME_UNKNOWN','pid':p.pid,'elapsedMillis':int((time.monotonic()-started)*1000),'stdoutBase64':base64.b64encode(e.output or b'').decode(),'stderrBase64':base64.b64encode(e.stderr or b'').decode()},sort_keys=True))
