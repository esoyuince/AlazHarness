"""P108E: owned real-native cold preflight under final-exec Landlock.

Explicit fresh preparation creates expectations in a previous process. Target
holds native ProfileLease, runs the fixed helper before native construction,
then the live gate. No network/mount/root/full-Gateway or paired recovery claim.
"""
from dataclasses import asdict,replace
import hashlib,json,os,sqlite3,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'packages/claw-hermes'),str(ROOT/'vendor-native'),str(ROOT/'dependencies')]
import gateway_store_preopen as pre

def guard():
    assert os.getresuid()==(23001,)*3 and os.getresgid()==(23003,)*3
    assert ROOT.parent==Path('/tmp') and ROOT.name.startswith('alaz-p108e-')
    assert os.environ.get('WSL_DISTRO_NAME')=='AlazHarness-D3B-P71C'
    assert Path('/etc/alaz-p71c-lab-id').read_text().strip()=='AlazHarness-D3B-P71C'
    m=json.loads((ROOT/'manifest.json').read_text())
    assert all(hashlib.sha256((ROOT/n).read_bytes()).hexdigest()==h for n,h in m.items())
    return m

def native():
    from hermes_state import SessionDB
    from gateway.platforms.api_server_run_idempotency import RunIdempotencyStore
    from gateway import runtime_ownership
    return SessionDB,RunIdempotencyStore,runtime_ownership

def expect(home,state,replay):
    return pre.live.PreparedStoreExpectation(pre.live.NATIVE_PIN,pre.live.schema_digest(state._conn),pre.live.schema_digest(replay._conn),
        state._conn.execute("SELECT value FROM state_meta WHERE key='store_instance_id'").fetchone()[0],
        state._conn.execute('PRAGMA application_id').fetchone()[0],
        (home.joinpath('state.db').stat().st_dev,home.joinpath('state.db').stat().st_ino),
        (home.joinpath('runs_idempotency.db').stat().st_dev,home.joinpath('runs_idempotency.db').stat().st_ino),0,None)

def prepare(home):
    os.environ['HERMES_HOME']=str(home);os.umask(0o077)
    SessionDB,RunStore,owner=native();owner.process_ownership.reserve([home])
    state=SessionDB(home/'state.db');replay=RunStore(str(home/'runs_idempotency.db'))
    try:expected=expect(home,state,replay)
    finally:replay.close();state.close();owner.process_ownership.close()
    with (ROOT/'expected.json').open('x') as f:json.dump(asdict(expected),f)
    print(json.dumps({'state':'FRESH_NATIVE_PREPARED','pid':os.getpid(),'nativePin':pre.live.NATIVE_PIN}),flush=True)

def snapshot(home):
    return {n:{'sha256':hashlib.sha256((home/n).read_bytes()).hexdigest(),
               'metadata':pre._meta((home/n).stat())} for n in pre.FILES}

def competitor(path):
    c=sqlite3.connect(path.as_uri()+'?mode=rw',uri=True,timeout=.1)
    try:
        try:c.execute('BEGIN IMMEDIATE')
        except sqlite3.OperationalError as exc:
            assert exc.sqlite_errorcode==sqlite3.SQLITE_BUSY
            print(json.dumps({'state':'BUSY','code':exc.sqlite_errorcode}));return
        c.rollback();print(json.dumps({'state':'ACQUIRED_ROLLED_BACK'}))
    finally:c.close()

def target(home):
    m=guard();os.environ['HERMES_HOME']=str(home);os.umask(0o077)
    row=pre.live.mounts.select_mount(pre.live.mounts.parse_mountinfo(pre.live.mounts._read_mountinfo()),str(home))
    mount=pre.live.mounts.ExpectedMount(row.mount_id,row.device,row.root,row.mount_point,row.filesystem)
    held=pre.live.profiles.reserve_profile(home,mount)
    obj=json.loads((ROOT/'expected.json').read_text())
    for n in ('state_identity','replay_identity'):obj[n]=tuple(obj[n])
    expected=pre.live.PreparedStoreExpectation(**obj)
    checking=[False];audit_counts={'parentRawDatabaseOpens':0,'parentSqliteConnects':0}
    def audit(event,args):
        if checking[0]:
            if event=='sqlite3.connect':audit_counts['parentSqliteConnects']+=1;raise AssertionError('parent_db_connect')
            if event=='open' and isinstance(args[0],(str,bytes,os.PathLike)):
                p=Path(os.fsdecode(args[0]))
                if p.parent==home and p.name.startswith(('state.db','runs_idempotency.db')):
                    audit_counts['parentRawDatabaseOpens']+=1;raise AssertionError('parent_raw_db_open')
    sys.addaudithook(audit)
    results=[];denials={};checks={}
    def check(name,ok):checks[name]=bool(ok);assert ok,name
    def call(want=expected):
        checking[0]=True
        try:return pre.verify_preopen(held,mount,want)
        finally:checking[0]=False
    def refused(label,reason,want=expected):
        before=snapshot(home)
        try:call(want)
        except pre.PreopenRejected as exc:denials[label]=str(exc);check(label,str(exc)==reason)
        else:raise AssertionError('unexpected_accept_'+label)
        check(label+'_nonmutating',snapshot(home)==before)
        check(label+'_lease_retained',held.check()['state']=='NATIVE_PROFILE_RESERVED')
    def sql(statement,args=()):
        c=sqlite3.connect(home/'state.db');c.execute(statement,args);c.commit();c.close()
    before=snapshot(home);result=call();results.append(result)
    check('clean_preflight_verified',result['state']=='COLD_STORES_PREFLIGHT_VERIFIED')
    check('worker_is_separate_process',result['workerPid']!=os.getpid() and result['parentPid']==os.getpid())
    check('clean_preflight_nonmutating',snapshot(home)==before)
    check('known_markers_checked',result['constructorMetadata']['knownBackfillComplete'] is True)
    refused('wrong_digest','preopen_schema_mismatch',replace(expected,state_schema_sha256='f'*64))
    refused('wrong_epoch','preopen_epoch',replace(expected,epoch=1,instance_id='wrong'))
    sql('UPDATE schema_version SET version=30');refused('old_version','preopen_schema_version');sql('UPDATE schema_version SET version=31')
    sql("INSERT INTO state_meta VALUES('fts_stale','0')");refused('pending_repair','preopen_constructor_metadata');sql("DELETE FROM state_meta WHERE key='fts_stale'")
    sql("DELETE FROM state_meta WHERE key='message_uid_backfill'");refused('incomplete_backfill','preopen_constructor_metadata');sql("INSERT INTO state_meta VALUES('message_uid_backfill','1')")
    journal=home/'state.db-journal';journal.write_bytes(b'owned hot-journal-like fixture')
    saved=journal.read_bytes();refused('sidecar_present','preopen_explicit_recovery_required');check('sidecar_not_deleted',journal.read_bytes()==saved);journal.unlink()
    (home/'state.db').chmod(0o644);refused('nonprivate_file','preopen_file_identity');(home/'state.db').chmod(0o600)
    original=home/'runs_idempotency.db';replacement=home/'replay-displaced.db';original.rename(replacement);original.symlink_to(replacement)
    try:refused('symlink_file','preopen_parent_unavailable')
    finally:original.unlink();replacement.rename(original)
    clean=call();check('original_files_still_accepted',clean['state']=='COLD_STORES_PREFLIGHT_VERIFIED')
    # Known fresh fixture only. This is the explicit positive opening sequence,
    # not a new generic repair/admission API.
    SessionDB,RunStore,owner=native()
    state=SessionDB(home/'state.db');replay=RunStore(str(home/'runs_idempotency.db'))
    live=pre.live.verify_live_stores(held,mount,state,replay,expected)
    check('preflight_then_native_then_live_gate',live['state']=='NATIVE_STORE_CONNECTIONS_VERIFIED')
    check('no_epoch_advanced',state._conn.execute('SELECT COUNT(*) FROM runtime_epoch').fetchone()[0]==0)
    check('native_exclusive_lock',state._conn.execute('PRAGMA locking_mode=EXCLUSIVE').fetchone()[0]=='exclusive')
    state._conn.execute('BEGIN EXCLUSIVE');state._conn.execute('COMMIT')
    env={'PATH':'/usr/bin:/bin','LANG':'C.UTF-8','HOME':str(home),'WSL_DISTRO_NAME':'AlazHarness-D3B-P71C'}
    def contender():
        c=subprocess.run([sys.executable,'-I','-B',str(Path(__file__)),'contend',str(home/'state.db')],cwd=ROOT,env=env,capture_output=True,text=True,timeout=10)
        assert c.returncode==0,c.stderr
        return json.loads(c.stdout)
    locks=[contender()]
    # Do NOT hash/open raw DB files in this parent while its SQLite lock is live.
    try:call()
    except pre.PreopenRejected as exc:denials['busy_live_parent']=str(exc);check('busy_live_parent_rejected',str(exc)=='preopen_observation_unavailable')
    else:raise AssertionError('locked_candidate_accepted')
    locks.append(contender());replay.close();state.close();held.finish();locks.append(contender())
    check('parent_sqlite_lock_survived_worker',locks==[{'state':'BUSY','code':5},{'state':'BUSY','code':5},{'state':'ACQUIRED_ROLLED_BACK'}])
    check('native_profile_released_after_close',not owner.process_ownership.homes)
    check('no_parent_db_opens_by_preflight',audit_counts=={'parentRawDatabaseOpens':0,'parentSqliteConnects':0})
    report={'result':'PASS_NATIVE_PREOPEN_SEQUENCE','checks':checks,'checkCount':len(checks),'denials':denials,
        'successfulPreflight':result,'liveGate':live,'lockSequence':locks,'audit':audit_counts,
        'guard':json.loads(os.environ['P108E_GUARD']),'parentPid':os.getpid(),'uid':os.getuid(),
        'sourceSha256':m,'rootUsed':False,'fullProjectionTested':False,'nativeMethodsMocked':False,
        'nativeConstructorRepairGuaranteedAbsent':False,'runtimeAdmissionAuthorized':False,'providerCalls':0,'fullD3BAccepted':False}
    print(json.dumps(report),flush=True)

def launch(home):
    import credential_guard
    policy={'version':1,'enabled':True,
        'readonly':[str(ROOT/n) for n in ('vendor-native','dependencies','packages','scripts','expected.json','manifest.json')]+['/usr/bin','/usr/lib','/usr/lib64','/etc/alaz-p71c-lab-id'],
        'writable':[str(home),'/dev/null'],'protected':[str(ROOT/'canary')],'self_process_metadata':True}
    receipt=credential_guard.apply(policy,self_mount_metadata=True)
    env={'PATH':'/usr/bin:/bin','LANG':'C.UTF-8','HOME':str(home),'HERMES_HOME':str(home),'WSL_DISTRO_NAME':'AlazHarness-D3B-P71C','P108E_GUARD':json.dumps(receipt)}
    os.execve(sys.executable,[sys.executable,'-I','-B',str(Path(__file__)),'target',str(home)],env)

def main():
    m=guard();mode=sys.argv[1] if len(sys.argv)>1 else 'run';home=ROOT/'profile'
    if mode=='prepare':prepare(home);return
    if mode=='target':target(home);return
    if mode=='launch':launch(home);return
    if mode=='contend':competitor(Path(sys.argv[2]));return
    home.mkdir(mode=0o700);(ROOT/'canary').write_text('owned fixture')
    env={'PATH':'/usr/bin:/bin','LANG':'C.UTF-8','HOME':str(home),'HERMES_HOME':str(home),'WSL_DISTRO_NAME':'AlazHarness-D3B-P71C'}
    events=[]
    for action in ('prepare','launch'):
        c=subprocess.run([sys.executable,'-I','-B',str(Path(__file__)),action,str(home)],cwd=ROOT,env=env,capture_output=True,text=True,timeout=100)
        events.append({'action':action,'exitCode':c.returncode,'stdout':c.stdout,'stderr':c.stderr})
        if c.returncode:break
    result={'result':'PASS' if len(events)==2 and all(e['exitCode']==0 for e in events) else 'FAIL','events':events,
        'sourceSha256':m,'sourcesUnchanged':all(hashlib.sha256((ROOT/n).read_bytes()).hexdigest()==h for n,h in m.items()),'rootUsed':False}
    print(json.dumps(result),flush=True)
    raise SystemExit(0 if result['result']=='PASS' and result['sourcesUnchanged'] else 1)
if __name__=='__main__':main()
