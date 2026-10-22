"""Owned actual aiohttp + A109 readiness checks on approved ordinary-user P71C.
No root/mount, native code mutation, full Gateway routes or provider requests.
"""
import asyncio
from dataclasses import asdict,replace
import errno,hashlib,json,os,secrets,select,socket,subprocess,sys
from http.client import HTTPConnection
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/n) for n in ('packages/claw-hermes','vendor-native','dependencies','http-dependencies')]
import gateway_http_readiness as http

def guard():
    assert os.getresuid()==(23001,)*3 and os.getresgid()==(23003,)*3
    assert ROOT.parent==Path('/tmp') and ROOT.name.startswith('alaz-h110e-code-')
    assert os.environ.get('WSL_DISTRO_NAME')=='AlazHarness-D3B-P71C'
    assert Path('/etc/alaz-p71c-lab-id').read_text().strip()=='AlazHarness-D3B-P71C'
    manifest=json.loads((ROOT/'manifest.json').read_text())
    assert all(hashlib.sha256((ROOT/n).read_bytes()).hexdigest()==h for n,h in manifest.items())
    return manifest

def native():
    from hermes_state import SessionDB
    from gateway.platforms.api_server_run_idempotency import RunIdempotencyStore
    from gateway import runtime_ownership
    return SessionDB,RunIdempotencyStore,runtime_ownership

def expectation(home,state,replay):
    return http.startup.live.PreparedStoreExpectation(http.startup.live.NATIVE_PIN,
        http.startup.live.schema_digest(state._conn),http.startup.live.schema_digest(replay._conn),
        state._conn.execute("SELECT value FROM state_meta WHERE key='store_instance_id'").fetchone()[0],
        state._conn.execute('PRAGMA application_id').fetchone()[0],
        (home.joinpath('state.db').stat().st_dev,home.joinpath('state.db').stat().st_ino),
        (home.joinpath('runs_idempotency.db').stat().st_dev,home.joinpath('runs_idempotency.db').stat().st_ino),0,None)

def prepare(home,case):
    os.environ['HERMES_HOME']=str(home);os.umask(0o077)
    State,Replay,owner=native();owner.process_ownership.reserve([home])
    state=State(home/'state.db');replay=Replay(str(home/'runs_idempotency.db'))
    try:want=expectation(home,state,replay)
    finally:replay.close();state.close();owner.process_ownership.close()
    with (ROOT/'control'/(case+'.json')).open('x') as f:json.dump(asdict(want),f)
    print(json.dumps({'state':'OWNED_PROFILE_PREPARED','case':case,'epoch':0}),flush=True)

def load_expected(case):
    obj=json.loads((ROOT/'control'/(case+'.json')).read_text())
    for n in ('state_identity','replay_identity'):obj[n]=tuple(obj[n])
    return http.startup.live.PreparedStoreExpectation(**obj)

async def command():
    loop=asyncio.get_running_loop();ready=loop.create_future()
    def readable():
        if not ready.done():ready.set_result(None)
    loop.add_reader(sys.stdin.fileno(),readable)
    try:await asyncio.wait_for(ready,20)
    finally:loop.remove_reader(sys.stdin.fileno())
    value=sys.stdin.buffer.readline(4097);assert value and len(value)<=4096
    return value.decode().strip()

async def target(home,case):
    manifest=guard();os.environ['HERMES_HOME']=str(home);os.umask(0o077)
    config=json.loads(sys.stdin.buffer.readline(4097));token=config['token'];port=config['port']
    counts={'nativeSqliteConnections':0,'httpPhaseSqliteConnections':0,'httpPhaseRawDatabaseOpens':0,'nonLoopbackAttempts':0}
    watching=False
    def audit(event,args):
        if event=='sqlite3.connect':
            counts['nativeSqliteConnections']+=1
            if watching:counts['httpPhaseSqliteConnections']+=1;raise AssertionError('http_opened_sqlite')
        if event=='open' and watching and isinstance(args[0],(str,bytes,os.PathLike)):
            p=Path(os.fsdecode(args[0]))
            if p.parent==home and p.name.startswith(('state.db','runs_idempotency.db')):
                counts['httpPhaseRawDatabaseOpens']+=1;raise AssertionError('http_raw_db_open')
        if event in ('socket.bind','socket.connect') and isinstance(args[1],tuple) and args[1][0]!='127.0.0.1':
            counts['nonLoopbackAttempts']+=1;raise PermissionError('only_owned_loopback')
    sys.addaudithook(audit)
    m=http.startup.live.mounts
    r=m.select_mount(m.parse_mountinfo(m._read_mountinfo()),str(home))
    mount=m.ExpectedMount(r.mount_id,r.device,r.root,r.mount_point,r.filesystem)
    held=http.startup.live.profiles.reserve_profile(home,mount)
    want=load_expected(case)
    if case=='preopen-refusal':want=replace(want,state_schema_sha256='f'*64)
    stores=http.startup.NativeStoreStartup(held,mount,want,instance_id='h110e-'+case)
    service=http.StorageReadinessHttp(stores,token=token,port=port)
    try:receipt=await service.start()
    except http.ReadinessRejected as exc:
        assert case in ('preopen-refusal','bind-conflict')
        if case=='bind-conflict':assert isinstance(exc.__cause__,OSError) and exc.__cause__.errno==errno.EADDRINUSE
        before=stores.status();http_before=service.status()
        closed=await service.close();held.finish()
        from gateway import runtime_ownership
        print(json.dumps({'state':'EXPECTED_START_REFUSAL','case':case,'reason':str(exc),
            'storageBeforeClose':before,'httpBeforeClose':http_before,'closed':closed,'audit':counts,
            'nativeProfileReleased':not runtime_ownership.process_ownership.homes,
            'runtimeAdmissionAuthorized':False}),flush=True)
        return
    assert case=='normal'
    state,replay=stores.state_store,stores.replay_store
    refs=(id(state),id(replay),id(state._conn),id(replay._conn))
    watching=True
    print(json.dumps({'state':'LISTENING','case':case,'pid':os.getpid(),'uid':os.getuid(),
        'http':receipt,'storage':stores.status(),'guard':json.loads(os.environ['H110E_GUARD'])}),flush=True)
    assert await command()=='MUTATE_EPOCH'
    state._conn.execute("UPDATE main.runtime_epoch SET epoch=epoch+1 WHERE singleton=1");state._conn.commit()
    print(json.dumps({'state':'EPOCH_CHANGED_BY_QA','epoch':state._conn.execute('SELECT epoch FROM main.runtime_epoch').fetchone()[0]}),flush=True)
    assert await command()=='RESTORE_EPOCH'
    state._conn.execute("UPDATE main.runtime_epoch SET epoch=? WHERE singleton=1",(stores.expectation.epoch,));state._conn.commit()
    print(json.dumps({'state':'EPOCH_RESTORED_BY_QA','readinessRemainsRevoked':service.status()['readinessRevoked']}),flush=True)
    assert await command()=='CLOSE_WITH_TRANSACTION'
    watching=False;state._conn.execute('BEGIN IMMEDIATE')
    try:await service.close()
    except http.ReadinessRejected as exc:assert str(exc)=='readiness_storage_close_refused'
    else:raise AssertionError('active_transaction_closed')
    assert state._conn.in_transaction
    print(json.dumps({'state':'HTTP_CLOSED_STORES_RETAINED','http':service.status(),'transactionActive':True,
                     'nativeLeaseHeld':held.check()['state']=='NATIVE_PROFILE_RESERVED'}),flush=True)
    assert await command()=='SETTLE_AND_CLOSE'
    state._conn.rollback();closed=await service.close()
    held.finish()
    from gateway import runtime_ownership
    imported={}
    for module in tuple(sys.modules.values()):
        file=getattr(module,'__file__',None)
        if file:
            p=Path(file).resolve()
            if p.is_relative_to(ROOT) and p.suffix=='.py':
                n=p.relative_to(ROOT).as_posix();sha=hashlib.sha256(p.read_bytes()).hexdigest();assert manifest.get(n)==sha,n;imported[n]=sha
    import aiohttp
    print(json.dumps({'state':'CLOSED','http':closed,'nativeProfileReleased':not runtime_ownership.process_ownership.homes,
        'sameNativeStoreObjects':refs[:2]==(id(state),id(replay)), 'audit':counts,
        'sourceHashes':imported,'aiohttpVersion':aiohttp.__version__,'sourceCount':len(imported),
        'realHermesHttpAdapterStarted':False,'fullIsolationTested':False,'providerCalls':0}),flush=True)

def launch(home,case):
    import credential_guard
    policy={'version':1,'enabled':True,
        'readonly':[str(ROOT/n) for n in ('packages','scripts','vendor-native','dependencies','http-dependencies','control','manifest.json')]+['/usr/bin','/usr/lib','/usr/lib64','/etc/alaz-p71c-lab-id'],
        'writable':[str(home),'/dev/null'],'protected':[str(ROOT/'canary')],'self_process_metadata':True}
    receipt=credential_guard.apply(policy,self_mount_metadata=True)
    env={'PATH':'/usr/bin:/bin','LANG':'C.UTF-8','HOME':str(home),'HERMES_HOME':str(home),'WSL_DISTRO_NAME':'AlazHarness-D3B-P71C',
         'H110E_GUARD':json.dumps(receipt),'AIOHTTP_NO_EXTENSIONS':'1','MULTIDICT_NO_EXTENSIONS':'1','FROZENLIST_NO_EXTENSIONS':'1','YARL_NO_EXTENSIONS':'1','PROPCACHE_NO_EXTENSIONS':'1'}
    os.execve(sys.executable,[sys.executable,'-I','-B',str(Path(__file__)),'target',case],env)

def read_line(proc):
    assert select.select([proc.stdout],[],[],25)[0],'child_output_timeout'
    line=proc.stdout.readline(262145);assert line and len(line)<=262144,'child_output_missing'
    return json.loads(line)

def request(port,token,*,path='/health/ready',method='GET',extra=(),auth=True,body=None):
    conn=HTTPConnection('127.0.0.1',port,timeout=3)
    try:
        conn.putrequest(method,path,skip_host=True,skip_accept_encoding=True)
        conn.putheader('Host','127.0.0.1:'+str(port))
        if auth:conn.putheader('Authorization','Bearer '+token)
        for k,v in extra:conn.putheader(k,v)
        if body is not None:conn.putheader('Content-Length',str(len(body)))
        conn.endheaders(body)
        res=conn.getresponse();raw=res.read(4097);assert len(raw)<=4096
        kind=res.getheader('Content-Type','')
        parser_refusal=not kind.startswith('application/json')
        if parser_refusal:
            assert res.status==400 and kind.startswith('text/plain'), 'unexpected_nonjson_response'
            body_value=None
        else:body_value=json.loads(raw)
        return {'status':res.status,'body':body_value,'parserRefusal':parser_refusal,
                'cache':res.getheader('Cache-Control'),'connection':res.getheader('Connection')}
    finally:conn.close()

def main():
    manifest=guard();mode=sys.argv[1] if len(sys.argv)>1 else 'run'
    if mode!='run':
        case=sys.argv[2];assert case in ('preopen-refusal','bind-conflict','normal');home=ROOT/'profiles'/case
        if mode=='prepare':prepare(home,case)
        elif mode=='launch':launch(home,case)
        elif mode=='target':asyncio.run(target(home,case))
        else:raise ValueError('bad_mode')
        return
    (ROOT/'profiles').mkdir(mode=0o700);(ROOT/'control').mkdir(mode=0o700);(ROOT/'canary').write_text('owned fixture')
    env={'PATH':'/usr/bin:/bin','LANG':'C.UTF-8','HOME':str(ROOT),'WSL_DISTRO_NAME':'AlazHarness-D3B-P71C'}
    events=[];checks={};error=None;children=[]
    def check(key,value):checks[key]=bool(value);assert value,key
    def send(p,line):p.stdin.write((line+'\n').encode());p.stdin.flush();r=read_line(p);events.append(r);return r
    try:
        for case in ('preopen-refusal','bind-conflict','normal'):
            home=ROOT/'profiles'/case;home.mkdir(mode=0o700)
            prep=subprocess.run([sys.executable,'-I','-B',str(Path(__file__)),'prepare',case],cwd=ROOT,env=env,capture_output=True,text=True,timeout=35)
            events.append({'phase':'prepare-'+case,'exitCode':prep.returncode,'stdout':prep.stdout,'stderr':prep.stderr})
            check(case+'_prepared',prep.returncode==0)
            token=secrets.token_hex(32)
            with socket.socket() as occupied:
                occupied.bind(('127.0.0.1',0));port=occupied.getsockname()[1]
                if case=='bind-conflict':occupied.listen(1)
                else:occupied.close()
                proc=subprocess.Popen([sys.executable,'-I','-B',str(Path(__file__)),'launch',case],cwd=ROOT,env=env,
                    stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,bufsize=0)
                children.append(proc);proc.stdin.write((json.dumps({'token':token,'port':port})+'\n').encode());proc.stdin.flush()
                first=read_line(proc);events.append(first)
                if case!='normal':
                    check(case+'_refused_and_closed',first['state']=='EXPECTED_START_REFUSAL' and first['closed']['state']=='CLOSED' and first['nativeProfileReleased'])
                    if case=='preopen-refusal':
                        check('preopen_no_parent_native_connections',first['audit']['nativeSqliteConnections']==0)
                        check('preopen_no_epoch_advance',first['storageBeforeClose']['epochMayHaveAdvanced'] is False)
                        with socket.socket() as probe:check('preopen_port_never_bound',probe.connect_ex(('127.0.0.1',port))!=0)
                    else:
                        check('bind_conflict_epoch_effect_reported',first['storageBeforeClose']['epochMayHaveAdvanced'] is True)
                        check('foreign_listener_not_closed',occupied.fileno()>=0 and occupied.getsockname()[1]==port)
                else:
                    check('listener_after_native_verified',first['state']=='LISTENING' and first['storage']['state']=='VERIFIED' and first['storage']['epochObserved']==1)
                    check('fixed_loopback_address',first['http']['host']=='127.0.0.1' and first['http']['port']==port)
                    cases=[('missing-auth',{'auth':False},401),('wrong-auth',{'token':'f'*64},401),
                        ('duplicate-auth',{'extra':[('Authorization','Bearer '+token)]},401),
                        ('bad-origin',{'extra':[('Origin','https://example.invalid')]},400),
                        ('duplicate-host',{'extra':[('Host','example.invalid')]},400),
                        ('agent-disabled',{'path':'/v1/runs','method':'POST'},404),
                        ('query-refused',{'path':'/health/ready?x=1'},404),
                        ('encoded-refused',{'path':'/health/%72eady'},404),
                        ('post-refused',{'method':'POST'},405),('body-refused',{'body':b'x'},400),
                        ('live',{'path':'/health/live'},200),('ready',{},200)]
                    for label,args,want in cases:
                        args=dict(args);use=args.pop('token',token);reply=request(port,use,**args);events.append({'httpCase':label,**reply})
                        check('http_'+label,reply['status']==want and (reply['cache']=='no-store' or (label=='duplicate-host' and reply['parserRefusal'] is True and want==400)))
                        check('no_dispatch_'+label,(reply['body'] or {}).get('runtimeAdmissionAuthorized') is not True)
                    changed=send(proc,'MUTATE_EPOCH');check('qa_epoch_changed',changed['epoch']==2)
                    reply=request(port,token);events.append({'httpCase':'stale-epoch',**reply});check('stale_returns503',reply['status']==503 and reply['body']['storageReady'] is False)
                    send(proc,'RESTORE_EPOCH');reply=request(port,token);events.append({'httpCase':'restored-but-revoked',**reply});check('readiness_never_auto_recovers',reply['status']==503)
                    check('revoked_liveness_separate',request(port,token,path='/health/live')['status']==200)
                    blocked=send(proc,'CLOSE_WITH_TRANSACTION');check('close_retains_transaction_and_lease',blocked['transactionActive'] and blocked['nativeLeaseHeld'] and blocked['http']['state']=='HTTP_CLOSED')
                    with socket.socket() as probe:check('http_closed_before_native_transaction_settlement',probe.connect_ex(('127.0.0.1',port))!=0)
                    closed=send(proc,'SETTLE_AND_CLOSE');check('normal_closed',closed['state']=='CLOSED' and closed['http']['state']=='CLOSED' and closed['nativeProfileReleased'])
                    check('no_http_database_reopens',closed['audit']['httpPhaseSqliteConnections']==0 and closed['audit']['httpPhaseRawDatabaseOpens']==0)
                    check('two_native_connections_only',closed['audit']['nativeSqliteConnections']==2)
                    check('no_nonloopback_activity',closed['audit']['nonLoopbackAttempts']==0)
                out,err=proc.communicate(timeout=8);events.append({'phase':'exit-'+case,'exitCode':proc.returncode,'stdout':out.decode(),'stderr':err.decode()})
                check(case+'_exit_zero',proc.returncode==0 and not out)
                check(case+'_token_absent_from_output',token not in json.dumps(events) and token not in err.decode())
    except Exception as exc:error={'type':type(exc).__name__,'reason':str(exc)[:400]}
    finally:
        for proc in children:
            if proc.poll() is None:
                proc.kill();out,err=proc.communicate(timeout=5);events.append({'ownedForcedCleanup':True,'stderr':err.decode('utf-8','replace')[-4000:],'stdout':out.decode('utf-8','replace')[-1000:]})
            elif proc.stderr and not proc.stderr.closed:
                out,err=proc.communicate(timeout=2);events.append({'remainingChildDiagnostic':err.decode('utf-8','replace')[-4000:]})
    checks['sources_unchanged']=all(hashlib.sha256((ROOT/n).read_bytes()).hexdigest()==h for n,h in manifest.items())
    checks['no_live_children']=all(p.poll() is not None for p in children)
    checks['no_forced_cleanup']=not any(e.get('ownedForcedCleanup') for e in events)
    result={'result':'PASS_NATIVE_STORAGE_READINESS_HTTP' if error is None and all(checks.values()) else 'FAIL',
        'checks':checks,'checkCount':len(checks),'events':events,'error':error,'sourceSha256':manifest,
        'uid':os.getuid(),'rootUsed':False,'fullMountNetworkIsolationTested':False,'realHermesHttpAdapterStarted':False,
        'readinessHttpActuallyServed':any('httpCase' in e for e in events),'paidCalls':0,'providerSends':0,'fullD3BAccepted':False}
    print(json.dumps(result),flush=True);raise SystemExit(0 if result['result'].startswith('PASS') else 1)
if __name__=='__main__':main()
