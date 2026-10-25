"""Ordinary Linux negative receiver only. No fake kernel fields or actual projection.
The selected scenarios must refuse without a lease, SQL, subprocess, or network.
"""
from pathlib import Path
from dataclasses import asdict
import argparse,hashlib,json,os,runpy,sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'packages/claw-hermes'))

def main():
    a=argparse.ArgumentParser();a.add_argument('--case',choices=('missing','malformed','extra-environment','foreign-pid','ordinary-unconfined'),required=True);args=a.parse_args()
    assert sys.platform=='linux' and sys.executable=='/usr/bin/python3.12' and sys.flags.isolated and sys.dont_write_bytecode
    assert os.getresuid()==(23001,)*3 and os.getresgid()==(23003,)*3
    before=Path('/proc/self/mountinfo').read_bytes();namespaces={k:os.readlink('/proc/self/ns/'+k) for k in ('user','mnt','net','ipc')}
    forbidden=[];calls=[]
    def audit(event,values):
        if event in ('sqlite3.connect','subprocess.Popen','os.exec','os.system','socket.connect','socket.bind','socket.getaddrinfo'):
            forbidden.append(event);raise PermissionError('negative_receiver_no_effects')
        if event=='open' and isinstance(values[0],(str,bytes,os.PathLike)):
            path=os.fsdecode(values[0])
            if path.startswith('/run/alaz-state/profile'):
                forbidden.append('profile-open');raise PermissionError('negative_receiver_no_profile')
    def profile(frame,event,arg):
        if event=='call' and frame.f_code.co_name in ('receive','_live','_mount','reserve_profile','start','encode_projected','decode_projected'):
            file=frame.f_code.co_filename
            if file.startswith(str(ROOT/'packages/claw-hermes')):calls.append({'file':Path(file).name,'function':frame.f_code.co_name})
    sys.addaudithook(audit);sys.setprofile(profile)
    import gateway_retained_launch as l
    h=l.handoff
    principal={'version':1,'enabled':True,'gatewayUid':23001,'brokerUid':23002,'socketGroupGid':23003,'hostUserNamespace':namespaces['user']}
    state=h.preopen.live.PreparedStoreExpectation(h.preopen.live.NATIVE_PIN,'a'*64,'b'*64,
        '12345678-1234-4234-8234-123456789012',123,(1792,21),(1792,22),1,'prior-owner')
    response=h.response.PreparedResponseExpectation(h.response.NATIVE_FEATURE,h.response.SCHEMA_SHA256,(1792,23))
    receipt=h.retained.RetainedProfileExpectation(h.retained.FEATURE,h.TARGET,(1792,12),((1792,21),(1792,22),(1792,23)),1,'prior-owner','c'*64)
    raw=h.encode(h.RetainedStartup(state,response,receipt),expected_home=h.TARGET)
    context={'protocol':l.PROTOCOL,'pid':os.getpid(),'principal':principal,'namespaces':namespaces,
        'mount':{'mount_id':40,'device':[7,0],'root':'/profile','mount_point':h.TARGET,'filesystem':'ext4'},
        'scratch':'/srv/test/scratch','instanceId':'new-owner','wireSha256':hashlib.sha256(raw).hexdigest()}
    env=l._environment(raw,context)
    if args.case=='missing':env.pop(l.WIRE_ENV)
    elif args.case=='malformed':env[l.WIRE_ENV]='{'
    elif args.case=='extra-environment':env['PYTHONPATH']='/not-allowed'
    elif args.case=='foreign-pid':context['pid']+=1;env[l.CONTEXT_ENV]=l._bytes(context).decode('ascii')
    observed=l.state.gp.launch.observation()
    # This is intentionally NOT an isolation transition; actual initial state stays unchanged.
    os.environ.clear();os.environ.update(env)
    target=ROOT/'scripts/run_retained_projected.py';sys.argv=[str(target)]
    code=None
    try:runpy.run_path(str(target),run_name='__main__')
    except SystemExit as e:code=e.code
    finally:sys.setprofile(None)
    assert code==2 and not forbidden and not any(c['function'] in ('reserve_profile','start','_mount') for c in calls)
    if args.case=='ordinary-unconfined':assert any(c['function']=='_live' for c in calls)
    else:assert not any(c['function']=='_live' for c in calls)
    assert before==Path('/proc/self/mountinfo').read_bytes() and namespaces=={k:os.readlink('/proc/self/ns/'+k) for k in namespaces}
    loaded={}
    for module in tuple(sys.modules.values()):
        file=getattr(module,'__file__',None)
        if file:
            path=Path(file).resolve()
            if path.is_relative_to(ROOT) and path.is_file():loaded[path.relative_to(ROOT).as_posix()]=hashlib.sha256(path.read_bytes()).hexdigest()
    result={'result':'PASS_ACTUAL_LINUX_RECEIVER_REFUSAL','case':args.case,'targetExitCode':code,'calls':calls,
        'uid':list(os.getresuid()),'gid':list(os.getresgid()),'actualKernelObservation':observed,
        'mountAndNamespacesUnchanged':True,'forbiddenEffects':forbidden,'loadedSources':loaded,
        'productOrOsMethodsReplaced':False,'profileCreated':False,'positiveIsolationAccepted':False,'nativeWorkExecuted':False,
        'runpyFixedEntrypointExplicit':True,'freshIsolatedInterpreter':True}
    print('L145_NEGATIVE '+json.dumps(result,sort_keys=True),flush=True)
    return 0
if __name__=='__main__':raise SystemExit(main())
