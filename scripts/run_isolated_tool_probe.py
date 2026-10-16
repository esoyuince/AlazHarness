"""Opt-in real Linux/Docker acceptance with synthetic host canaries only.

No model, Gateway, registry pull, host firewall or daemon configuration change.
The host owns the listener/canary; the container is intentionally network=none.
"""
from __future__ import annotations
import argparse
from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import secrets
import socket
import sys
import threading
import time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'packages/claw-hermes'))
if not (ROOT/'packages/claw-hermes/isolated_tool.py').exists():
    sys.path.insert(0,str(Path(__file__).resolve().parent))
from isolated_tool import ToolSandboxPolicy, IsolatedToolRunner, IsolationError

PROBE=r"""
import ctypes, errno, json, os, socket, subprocess, sys
from pathlib import Path
info=json.loads(Path('/workspace/probe.json').read_text())
answer={'marker':Path('/workspace/input.txt').read_text(), 'uid':os.getuid(), 'gid':os.getgid()}
answer['namespace']={x:os.readlink('/proc/self/ns/'+x) for x in ('net','pid','mnt')}
answer['interfaces']=sorted(p.name for p in Path('/sys/class/net').iterdir())
status={line.split(':',1)[0]:line.split(':',1)[1].strip() for line in Path('/proc/self/status').read_text().splitlines() if ':' in line}
answer['privilege']={k:status[k] for k in ('NoNewPrivs','CapEff','Seccomp')}
answer['environment_canary_absent']='ALAZ_OWNER_CANARY' not in os.environ
answer['parent_proxy_absent']='HTTPS_PROXY' not in os.environ
answer['docker_endpoint_absent']='DOCKER_HOST' not in os.environ
answer['docker_socket_absent']=not Path('/var/run/docker.sock').exists()
try:
    Path(info['hostCanaryPath']).read_bytes();answer['host_canary_read']='UNEXPECTED_SUCCESS'
except OSError as e:answer['host_canary_read']=e.errno
try:
    Path('/workspace/forbidden.txt').write_text('attempt');answer['capsule_write']='UNEXPECTED_SUCCESS'
except OSError as e:answer['capsule_write']=e.errno
try:
    Path('/root/write-probe').write_text('attempt');answer['root_write']='UNEXPECTED_SUCCESS'
except OSError as e:answer['root_write']=e.errno
Path('/tmp/local.txt').write_text('local scratch')
answer['private_scratch_writable']=Path('/tmp/local.txt').read_text()=='local scratch'
connections={}
for name,family,address in [('host_loopback',socket.AF_INET,('127.0.0.1',info['port'])),
                            ('external_v4',socket.AF_INET,('192.0.2.1',443)),
                            ('external_v6',socket.AF_INET6,('2001:db8::1',443))]:
    s=socket.socket(family,socket.SOCK_STREAM);s.settimeout(.5)
    try:s.connect(address);connections[name]='UNEXPECTED_SUCCESS'
    except OSError as e:connections[name]=e.errno
    finally:s.close()
s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
try:s.sendto(b'probe',('192.0.2.1',9));connections['udp_v4']='UNEXPECTED_SUCCESS'
except OSError as e:connections['udp_v4']=e.errno
finally:s.close()
answer['connections']=connections
try:
    s=socket.socket(socket.AF_INET,socket.SOCK_RAW,socket.IPPROTO_ICMP);s.close();answer['raw_socket']='UNEXPECTED_SUCCESS'
except OSError as e:answer['raw_socket']=e.errno
libc=ctypes.CDLL(None,use_errno=True)
answer['setuid_root_result']=libc.setuid(0);answer['setuid_root_errno']=ctypes.get_errno()
# Separate child process makes the same request; no Python audit hook is installed.
childcode='import socket,sys; s=socket.socket();s.settimeout(.5); print(s.connect_ex(("127.0.0.1",int(sys.argv[1]))));s.close()'
p=subprocess.run([sys.executable,'-I','-B','-c',childcode,str(info['port'])],capture_output=True,text=True,timeout=3)
answer['descendant_connection_errno']=int(p.stdout.strip());answer['descendant_exit']=p.returncode
answer['cgroups']={name:Path('/sys/fs/cgroup/'+name).read_text().strip() for name in ('memory.max','pids.max','cpu.max')}
print(json.dumps(answer),flush=True)
"""
SLEEPER="import subprocess,sys,time,json\nchild=subprocess.Popen([sys.executable,'-c','import time;time.sleep(60)'])\nprint(json.dumps({'spawned_child':True}),flush=True)\ntime.sleep(60)\n"


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,required=True)
    p.add_argument('--image',required=True)
    p.add_argument('--sudo',action='store_true')
    a=p.parse_args();root=a.root
    if not root.is_absolute() or root.exists():raise ValueError('Fresh absolute test directory required')
    root.mkdir(parents=True,mode=0o755)
    secret=secrets.token_hex(32);canary=root/'host-only-canary.txt';canary.write_text(secret);canary.chmod(0o444)
    # Prove the host marker is readable; hiding it is the mount boundary, not its permissions.
    assert canary.read_text()==secret
    old_env={name:os.environ.get(name) for name in ('ALAZ_OWNER_CANARY','HTTPS_PROXY','DOCKER_HOST')}
    os.environ.update(ALAZ_OWNER_CANARY=secret,HTTPS_PROXY='http://unused.invalid:9',DOCKER_HOST='tcp://unused.invalid:2375')
    listener=socket.socket();listener.bind(('127.0.0.1',0));listener.listen();listener.settimeout(.1)
    port=listener.getsockname()[1];accepted=[];stop=threading.Event()
    def listen():
        while not stop.is_set():
            try:
                c,addr=listener.accept();accepted.append(addr);c.close()
            except socket.timeout:pass
            except OSError:break
    server=threading.Thread(target=listen,daemon=True);server.start()
    with socket.create_connection(('127.0.0.1',port),timeout=1):pass
    until=time.monotonic()+2
    while len(accepted)!=1 and time.monotonic()<until:time.sleep(.01)
    assert len(accepted)==1
    native_ns={x:os.readlink('/proc/self/ns/'+x) for x in ('net','pid','mnt')}
    source=[Path(__file__),Path(sys.modules['isolated_tool'].__file__)]
    hashes={x.name:hashlib.sha256(x.read_bytes()).hexdigest() for x in source}
    results=[]
    try:
        for name in ('isolation-1','isolation-2','timeout','cancel','output-limit','tool-failure'):
            capsule=root/(name+'-capsule');capsule.mkdir(mode=0o755)
            policy=ToolSandboxPolicy(a.image,timeout_seconds=2 if name=='timeout' else 10,
                                     output_limit_bytes=1024 if name=='output-limit' else 65536)
            code=PROBE if name.startswith('isolation') else SLEEPER if name in ('timeout','cancel') else "print('x'*40000)\n" if name=='output-limit' else "raise ValueError('controlled tool failure')\n"
            (capsule/'program.py').write_text(code)
            marker='ISOLATED_'+secrets.token_hex(12);(capsule/'input.txt').write_text(marker)
            (capsule/'probe.json').write_text(json.dumps({'hostCanaryPath':str(canary),'port':port}))
            event=threading.Event();timer=None
            if name=='cancel':timer=threading.Timer(3,event.set);timer.start()
            result=IsolatedToolRunner(root=root,capsule=capsule,receipt_dir=root/(name+'-receipt'),policy=policy,use_sudo=a.sudo).run(cancel_event=event)
            if timer:timer.cancel();timer.join()
            checks={'no_errors':result['errors']==[], 'capsule_unchanged':result['capsuleUnchanged'],
                    'native_exit_confirmed':result.get('exit',{}).get('exited') is True,
                    'owned_container_removed':result.get('exit',{}).get('removed') is True,
                    'no_secret_in_output':secret not in result.get('stdout','')+result.get('stderr','')}
            detail=None
            if name.startswith('isolation') and result['result']=='completed':
                detail=json.loads(result['stdout']);checks.update(
                    isolated_namespace=all(detail['namespace'][x]!=native_ns[x] for x in native_ns),
                    marker_read=detail['marker']==marker,
                    nonroot=detail['uid']==detail['gid']==65534,
                    no_inherited_secrets=detail['environment_canary_absent'] and detail['parent_proxy_absent'] and detail['docker_endpoint_absent'],
                    socket_not_mounted=detail['docker_socket_absent'],
                    host_canary_hidden=detail['host_canary_read'] in (2,13),
                    read_only_capsule=detail['capsule_write'] in (13,30) and not (capsule/'forbidden.txt').exists(),
                    root_write_denied=detail['root_write'] in (13,30),
                    scratch_works=detail['private_scratch_writable'],
                    only_loopback=detail['interfaces']==['lo'],
                    network_unreachable=all(type(v) is int and v!=0 for v in detail['connections'].values()),
                    descendant_isolated=detail['descendant_exit']==0 and detail['descendant_connection_errno']!=0,
                    raw_socket_denied=detail['raw_socket']==1,
                    cannot_elevate=detail['setuid_root_result']==-1 and detail['setuid_root_errno']==1,
                    no_new_privileges=detail['privilege']['NoNewPrivs']=='1',
                    capabilities_empty=int(detail['privilege']['CapEff'],16)==0,
                    seccomp_enabled=detail['privilege']['Seccomp']=='2',
                    memory_bound=detail['cgroups']['memory.max']==str(policy.memory_bytes),
                    pids_bound=detail['cgroups']['pids.max']==str(policy.pids_limit),
                    cpu_bound=detail['cgroups']['cpu.max']=='50000 100000')
            else:
                expected={'timeout':'timeout','cancel':'cancelled','output-limit':'output_limit','tool-failure':'tool_failed'}.get(name)
                checks['expected_outcome']=result['result']==expected
                if name in ('timeout','cancel'):checks['descendant_was_started']='spawned_child' in result.get('stdout','')
                if name=='output-limit':checks['bounded_output']=len(result.get('stdout','').encode())<=1024 and result['outputTruncated']
            checks['host_listener_not_reached']=len(accepted)==1
            row={'scenario':name,'result':'PASS' if all(checks.values()) else 'FAIL','checks':checks,
                 'runner_outcome':result['result'],'errors':result['errors'],'exit':result.get('exit'),
                 'new_model_calls':0,'hermes_gateway_executed':False}
            if detail:row['observed_container']=detail
            results.append(row)
            print(json.dumps({'scenario':name,'result':row['result'],'failed_checks':[k for k,v in checks.items() if not v]}),flush=True)
            if row['result']!='PASS':break
    finally:
        stop.set();server.join(timeout=1);listener.close()
        for key,value in old_env.items():
            if value is None:os.environ.pop(key,None)
            else:os.environ[key]=value
    drift=[x.name for x in source if hashlib.sha256(x.read_bytes()).hexdigest()!=hashes[x.name]]
    outcome={'scope':'real Docker/Linux isolated TOOL processes on alaz-server; not native Hermes or provider integration',
             'results':results,'passed':sum(x['result']=='PASS' for x in results),'expected':6,
             'source_hashes':hashes,'source_drift':drift,'host_canary_unchanged':canary.read_text()==secret,
             'host_listener_positive_control':len(accepted)==1,'real_model_calls':0,'paid_calls':0,
             'pulled_or_built_images':False,'firewall_or_daemon_changed':False,'secret_value_recorded':False}
    outcome['result']='PASS' if outcome['passed']==6 and not drift and outcome['host_canary_unchanged'] else 'FAIL'
    (root/'isolation-evidence.json').write_text(json.dumps(outcome,indent=2)+'\n')
    print(json.dumps({'result':outcome['result'],'passed':outcome['passed'],'expected':6}),flush=True)
    return 0 if outcome['result']=='PASS' else 1

if __name__=='__main__':raise SystemExit(main())
