"""Owned ordinary-Linux native three-store startup acceptance, no HTTP dispatch.

Fresh provisioning closes files before a NEW process invokes the product.
Separate current two-store control; no root/mount or full-confinement claim.
"""
from dataclasses import asdict
import hashlib,json,os,sqlite3,subprocess,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'packages/claw-hermes'),str(ROOT/'vendor-native'),str(ROOT/'dependencies')]
import gateway_store_startup as startup

NAMES=('state.db','runs_idempotency.db','response_store.db')

def guard():
    assert os.getresuid()==(23001,)*3 and os.getresgid()==(23003,)*3
    assert ROOT.parent==Path('/tmp') and ROOT.name.startswith('alaz-l113f6-')
    assert os.environ.get('WSL_DISTRO_NAME')=='AlazHarness-D3B-P71C'
    assert Path('/etc/alaz-p71c-lab-id').read_text().strip()=='AlazHarness-D3B-P71C'
    return json.loads((ROOT/'manifest.json').read_text())

def hashes(home):return {n:hashlib.sha256((home/n).read_bytes()).hexdigest() for n in NAMES if (home/n).is_file()}

def canonical_rows(home):
    # QA-only closed-file observation outside the watched product lifecycle.
    conn=sqlite3.connect((home/'state.db').as_uri()+'?mode=ro',uri=True)
    try:
        return {name:[list(row) for row in conn.execute('SELECT * FROM main.'+name+' ORDER BY 1')]
            for name in ('runtime_epoch','session_admissions','state_meta')}
    finally:conn.close()


def prepare(home,case):
    guard();os.environ['HERMES_HOME']=str(home);os.umask(0o077)
    from hermes_state import SessionDB
    from gateway.platforms.api_server_run_idempotency import RunIdempotencyStore
    from gateway.platforms.api_server_response_store import ResponseStore
    from gateway.runtime_ownership import process_ownership
    import hermes_state_runtime as runtime
    process_ownership.reserve([home]);state=SessionDB(home/'state.db');replay=RunIdempotencyStore(str(home/'runs_idempotency.db'))
    response=None
    if case!='two':
        response=ResponseStore(db_path=str(home/'response_store.db'),canonical_state=state,max_size=100,max_identities=1000)
        response.put('resp_owned',{'output':'persistent-fixture'});response.set_conversation('owned','resp_owned')
        r=startup.response_preopen.PreparedResponseExpectation(startup.response_preopen.NATIVE_FEATURE,
            startup.live.schema_digest(response._conn),((home/'response_store.db').stat().st_dev,(home/'response_store.db').stat().st_ino))
    epoch=0;instance=None
    if case=='canonical-pending':
        instance='owned-previous';epoch=runtime.begin_runtime_epoch(state,instance_id=instance)
        state.create_session('session','api')
        runtime.admit_session_input(state,epoch=epoch,principal_id='owned',session_id='session',request_id='pending',payload={'text':'owned'})
    expected=startup.live.PreparedStoreExpectation(startup.live.NATIVE_PIN,startup.live.schema_digest(state._conn),startup.live.schema_digest(replay._conn),
        state._conn.execute("SELECT value FROM state_meta WHERE key='store_instance_id'").fetchone()[0],state._conn.execute('PRAGMA application_id').fetchone()[0],
        ((home/'state.db').stat().st_dev,(home/'state.db').stat().st_ino),((home/'runs_idempotency.db').stat().st_dev,(home/'runs_idempotency.db').stat().st_ino),epoch,instance)
    if response is not None:response.close()
    replay.close();state.close();process_ownership.close()
    if case in ('schema','unsettled','pressure'):
        conn=sqlite3.connect(home/'response_store.db')
        if case=='schema':conn.execute('CREATE TABLE unexpected(v)')
        elif case=='unsettled':conn.execute("INSERT INTO response_keys(request_key,fingerprint,created_at,model_json) VALUES('idem:pending',?,1,'null')",('a'*64,))
        else:conn.executemany('INSERT INTO responses VALUES(?,?,?)',[(str(i),'{}',1) for i in range(100)])
        conn.commit();conn.close()
    if case=='sidecar':(home/'response_store.db-journal').touch(mode=0o600)
    if case=='mode':(home/'response_store.db').chmod(0o644)
    record={'canonical':asdict(expected),'response':asdict(r) if response is not None else None,'case':case}
    (ROOT/(home.name+'.expected.json')).write_text(json.dumps(record))
    print(json.dumps({'state':'PREPARED_CLOSED','case':case,'canonicalEpoch':epoch,'profileLeaseReleased':not process_ownership.homes}),flush=True)

def target(home,case):
    manifest=guard();os.environ['HERMES_HOME']=str(home);os.umask(0o077)
    value=json.loads((ROOT/(home.name+'.expected.json')).read_text());expected=value['canonical']
    for key in ('state_identity','replay_identity'):expected[key]=tuple(expected[key])
    expected=startup.live.PreparedStoreExpectation(**expected)
    response=value['response']
    if response is not None:
        response['response_identity']=tuple(response['response_identity'])
        response=startup.response_preopen.PreparedResponseExpectation(**response)
    m=startup.live.mounts.select_mount(startup.live.mounts.parse_mountinfo(startup.live.mounts._read_mountinfo()),str(home))
    mount=startup.live.mounts.ExpectedMount(m.mount_id,m.device,m.root,m.mount_point,m.filesystem)
    held=startup.live.profiles.reserve_profile(home,mount)
    before=hashes(home)
    prior_rows=canonical_rows(home) if case=='canonical-pending' else None
    obj=startup.NativeStoreStartup(held,mount,expected,instance_id='owned-'+case,response_expected=response)
    # The original two-store HTTP service must not incorrectly certify three stores.
    http_refused=False
    if response is not None:
        import gateway_http_readiness as http
        try:http.StorageReadinessHttp(obj,token='a'*64)
        except http.ReadinessRejected as exc:http_refused=str(exc)=='readiness_three_store_not_qualified'
        assert http_refused
    audit={'connects':[],'coldRawDatabaseOpens':0,'network':0,'helpers':0};watch={'active':True}
    def observed(event,args):
        if event in ('socket.connect','socket.bind','socket.getaddrinfo','os.system'):
            audit['network']+=1;raise PermissionError('no_external_effect')
        if not watch['active']:return
        if event=='subprocess.Popen':
            cmd=args[1];assert cmd[:3]==[sys.executable,'-I','-B'] and cmd[3] in [str(ROOT/'scripts/run_store_preopen.py'),str(ROOT/'scripts/run_response_preopen.py')]
            audit['helpers']+=1
        if event=='sqlite3.connect':audit['connects'].append(str(args[0]))
        if event=='open' and isinstance(args[0],(str,bytes,os.PathLike)):
            path=Path(os.fsdecode(args[0]))
            if path.parent==home and path.name.startswith(NAMES) and obj._stage in ('LAYOUT','PREFLIGHT','RESPONSE_PREFLIGHT'):
                audit['coldRawDatabaseOpens']+=1;raise AssertionError('parent_raw_database_open')
    sys.addaudithook(observed)
    negatives={'schema','unsettled','pressure','sidecar','mode','canonical-pending'}
    events=[];checks={}
    def check(n,ok):checks[n]=bool(ok);assert ok,n
    try:
        result=obj.start()
    except startup.StoreStartupRejected as exc:
        if case not in negatives:raise
        failed=obj.status();cause=str(exc.__cause__) if exc.__cause__ is not None else str(exc)
        check('failure_before_epoch',failed['epochMayHaveAdvanced'] is False and failed['epochObserved']==expected.epoch)
        check('response_constructor_not_reached',obj._response is None)
        check('zero_parent_cold_raw_opens',audit['coldRawDatabaseOpens']==0)
        if case!='canonical-pending':check('no_parent_sqlite_connections',audit['connects']==[])
        else:check('only_two_verified_canonical_connections',len(audit['connects'])==2)
        try:obj.start()
        except startup.StoreStartupRejected as twice:check('cannot_retry',str(twice)=='startup_not_fresh')
        else:raise AssertionError('retry_was_allowed')
        obj.close();watch['active']=False
        after_hash=hashes(home)
        if case=='canonical-pending':
            later_rows=canonical_rows(home)
            check('canonical_epoch_and_admission_rows_unchanged',all(later_rows[n]==prior_rows[n] for n in ('runtime_epoch','session_admissions')))
            check('replay_and_response_bytes_unchanged',all(after_hash[n]==before[n] for n in ('runs_idempotency.db','response_store.db')))
            events.append({'phase':'canonical_constructor_observation','fileHashesBefore':before,'fileHashesAfter':after_hash,
                'logicalMetadataChanged':later_rows['state_meta']!=prior_rows['state_meta'],
                'epochRowsBefore':prior_rows['runtime_epoch'],'epochRowsAfter':later_rows['runtime_epoch'],
                'admissionRowsBefore':prior_rows['session_admissions'],'admissionRowsAfter':later_rows['session_admissions'],
                'allCanonicalFileBytesUnchanged':before['state.db']==after_hash['state.db']})
        else:check('file_bytes_unchanged',after_hash==before)
        held.finish();check('profile_released_by_caller_only',not held._owner.homes)
        report={'state':'EXPECTED_START_REFUSAL','case':case,'pid':os.getpid(),'failure':failed,'reason':cause,'checks':checks,'audit':audit,'httpThirdStoreRefused':http_refused,'events':events}
    else:
        assert case not in negatives
        check('verified_epoch',result['state']=='VERIFIED' and result['epochObserved']==expected.epoch+1)
        check('raw_cold_opens_zero',audit['coldRawDatabaseOpens']==0)
        check('exact_parent_connection_count',len(audit['connects'])==(2 if case=='two' else 3))
        check('separate_helpers',audit['helpers']==(1 if case=='two' else 2))
        check('no_network',audit['network']==0)
        handles=[obj.state_store._conn,obj.replay_store._conn]
        if response is not None:
            store=obj.response_store;handles.append(store._conn)
            check('exact_borrowed_canonical',store._canonical_state._connection is obj.state_store._conn)
            check('constructor_no_changed_rows',store._conn.total_changes==0)
            body=store._conn.execute("SELECT data FROM main.responses WHERE response_id='resp_owned'").fetchone()[0]
            check('persistent_response_body',json.loads(body)=={'output':'persistent-fixture'})
            check('all_six_checks',result['completedChecks']==['preflight','response_preflight','before_epoch','response_before_epoch','after_epoch','response_after_epoch'])
            for name,proof in obj._receipts:
                if name.startswith('response_'):events.append({'phase':name,'proof':proof})
            store._conn.execute('BEGIN IMMEDIATE')
            try:obj.close()
            except startup.StoreStartupRejected as exc:check('transaction_close_refused',str(exc)=='startup_transaction_active')
            else:raise AssertionError('active_tx_closed')
            check('transaction_not_rolled_back',store._conn.in_transaction)
            check('all_three_handles_retained',all(c.execute('SELECT 1').fetchone()[0]==1 for c in handles))
            held.check();store._conn.rollback()
        next_expected=asdict(obj.expectation)
        obj.close();watch['active']=False
        closed=0
        for c in handles:
            try:c.execute('SELECT 1')
            except sqlite3.ProgrammingError:closed+=1
        check('all_returned_handles_closed',closed==len(handles))
        check('caller_lease_still_owned',held.check()['state']=='NATIVE_PROFILE_RESERVED')
        if response is not None:check('response_bytes_unchanged',hashes(home)['response_store.db']==before['response_store.db'])
        ids={n:(home/n).stat().st_ino for n in before}
        held.finish();check('caller_released_profile',not held._owner.homes)
        report={'state':'STARTUP_COMPLETE','case':case,'pid':os.getpid(),'startup':result,'closed':obj.status(),'nextExpected':next_expected,
            'responseExpected':asdict(response) if response is not None else None,'checks':checks,'audit':audit,'events':events,'inodes':ids,'httpThirdStoreRefused':http_refused}
    imported={}
    for module in tuple(sys.modules.values()):
        f=getattr(module,'__file__',None)
        if f:
            p=Path(f).resolve()
            if p.is_relative_to(ROOT) and p.suffix=='.py':
                n=p.relative_to(ROOT).as_posix();h=hashlib.sha256(p.read_bytes()).hexdigest();assert manifest[n]==h,n;imported[n]=h
    report.update(sourceHashes=imported,checkCount=len(checks),nativeClassesMocked=False,fullConfinementTested=False,providerCalls=0)
    print(json.dumps(report),flush=True)

def main():
    sources=guard();mode=sys.argv[1] if len(sys.argv)>1 else 'run'
    if mode!='run':
        home=Path(sys.argv[2]);case=sys.argv[3];assert home.parent==ROOT and home.name.startswith('profile-')
        return prepare(home,case) if mode=='prepare' else target(home,case)
    env={'PATH':'/usr/bin:/bin','LANG':'C.UTF-8','WSL_DISTRO_NAME':'AlazHarness-D3B-P71C','HOME':str(ROOT)}
    events=[];error=None
    def child(mode,home,case):
        p=subprocess.run([sys.executable,'-I','-B',str(Path(__file__)),mode,str(home),case],env=env,cwd=ROOT,capture_output=True,text=True,timeout=35)
        record={'mode':mode,'case':case,'exitCode':p.returncode,'stdout':p.stdout,'stderr':p.stderr};events.append(record)
        assert p.returncode==0,(mode,case,p.stderr[-2000:]);return json.loads(p.stdout)
    try:
        for case in ('clean','two','schema','unsettled','pressure','sidecar','mode','canonical-pending'):
            home=ROOT/('profile-'+case);home.mkdir(mode=0o700)
            child('prepare',home,case);first=child('target',home,case)
            if case=='clean':
                expected=json.loads((ROOT/(home.name+'.expected.json')).read_text());expected['canonical']=first['nextExpected']
                (ROOT/(home.name+'.expected.json')).write_text(json.dumps(expected))
                second=child('target',home,'reopen')
                assert first['pid']!=second['pid'] and first['inodes']==second['inodes']
                assert first['startup']['epochObserved']==1 and second['startup']['epochObserved']==2
    except Exception as exc:error={'type':type(exc).__name__,'reason':str(exc)[:3000]}
    stable=all(hashlib.sha256((ROOT/n).read_bytes()).hexdigest()==h for n,h in sources.items())
    report={'result':'PASS_NATIVE_THREE_STORE_STARTUP' if error is None and stable else 'FAIL','error':error,'events':events,
        'sourceSha256':sources,'sourcesUnchanged':stable,'uid':os.getuid(),'rootUsed':False,'mountChanged':False,
        'twoStoreDefaultAlsoTested':True,'fullConfinementTested':False,'runtimePinActivated':False,'httpListenerStarted':False,'providerCalls':0}
    print(json.dumps(report),flush=True);return 0 if report['result'].startswith('PASS') else 1
if __name__=='__main__':raise SystemExit(main())
