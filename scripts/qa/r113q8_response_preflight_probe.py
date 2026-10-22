"""Actual native-response read-only preflight with owned Linux files/lease.

Ordinary dedicated lab UID. No root/mount/namespace or provider/listener work.
Trusted fresh preparation is separate from the read-only check. Fault mutations
below are explicit QA, never product repair or native method replacement.
"""
from dataclasses import asdict,replace
from pathlib import Path
import hashlib,json,os,sqlite3,subprocess,sys,tempfile
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'packages/claw-hermes'),str(ROOT/'vendor-native'),str(ROOT/'dependencies')]
import gateway_response_preopen as p

def main():
    assert os.getresuid()==(23001,)*3 and os.getresgid()==(23003,)*3
    assert os.environ.get('WSL_DISTRO_NAME')=='AlazHarness-D3B-P71C'
    assert ROOT.parent==Path('/tmp') and ROOT.name.startswith('alaz-r113q8-code-')
    manifest=json.loads((ROOT/'input.json').read_text())['sources']
    assert all(hashlib.sha256((ROOT/n).read_bytes()).hexdigest()==h for n,h in manifest.items())
    home=ROOT/'profile';home.mkdir(mode=0o700);os.environ.update(HERMES_HOME=str(home),HOME=str(home));os.umask(0o077)
    audit={'watch':False,'parentSqliteOpens':0,'parentDataOpens':0}
    def observed(event,args):
        if event in ('socket.connect','socket.bind','socket.getaddrinfo'):raise PermissionError('offline_native_fixture')
        if audit['watch'] and event=='sqlite3.connect':audit['parentSqliteOpens']+=1;raise AssertionError('parent_open')
        if audit['watch'] and event=='open' and isinstance(args[0],(str,bytes,os.PathLike)):
            q=Path(os.fsdecode(args[0]))
            if q.parent==home and q.name.startswith(('state.db','runs_idempotency.db','response_store.db')):
                audit['parentDataOpens']+=1;raise AssertionError('parent_raw_open')
    sys.addaudithook(observed)
    from hermes_state import SessionDB
    from gateway.platforms.api_server_response_store import ResponseStore
    from gateway.platforms.api_server_run_idempotency import RunIdempotencyStore
    from gateway.runtime_ownership import process_ownership as owner
    owner.reserve([home]);state=SessionDB(home/'state.db');replay=RunIdempotencyStore(str(home/'runs_idempotency.db'))
    response=ResponseStore(db_path=str(home/p.FILENAME),canonical_state=state)
    ids=[(q.stat().st_dev,q.stat().st_ino) for q in (home/'state.db',home/'runs_idempotency.db',home/p.FILENAME)]
    canonical=p.live.PreparedStoreExpectation(p.live.NATIVE_PIN,p.live.schema_digest(state._conn),p.live.schema_digest(replay._conn),
        state._conn.execute("SELECT value FROM state_meta WHERE key='store_instance_id'").fetchone()[0],
        state._conn.execute('PRAGMA application_id').fetchone()[0],ids[0],ids[1],0,None)
    expected=p.PreparedResponseExpectation(p.NATIVE_FEATURE,p.live.schema_digest(response._conn),ids[2])
    response.close();replay.close();state.close();owner.close()
    row=p.live.mounts.select_mount(p.live.mounts.parse_mountinfo(p.live.mounts._read_mountinfo()),str(home))
    mount=p.live.mounts.ExpectedMount(row.mount_id,row.device,row.root,row.mount_point,row.filesystem)
    held=p.live.profiles.reserve_profile(home,mount);path=home/p.FILENAME;original=path.read_bytes()
    checks={};cases=[]
    def check(name,value):checks[name]=bool(value);assert value,name
    def call(want=expected):
        audit['watch']=True
        try:return p.verify_response_preopen(held,mount,want,canonical)
        finally:audit['watch']=False
    def refused(name,mutation,restore,want=expected,code=None):
        mutation();before=path.read_bytes() if path.is_file() and not path.is_symlink() else None
        try:
            try:call(want)
            except p.ResponsePreopenRejected as exc:
                reason=str(exc);check(name+'_refused',code is None or reason==code)
            else:raise AssertionError(name+'_accepted')
            if before is not None:check(name+'_unchanged',path.read_bytes()==before)
            check(name+'_lease_retained',held.check()['state']=='NATIVE_PROFILE_RESERVED')
            cases.append({'case':name,'reason':reason,'contentsUnchanged':before is not None and path.read_bytes()==before})
        finally:restore()
    def mutate(sql,args=()):
        c=sqlite3.connect(path);c.execute(sql,args);c.commit();c.close()
    def restore():path.write_bytes(original);path.chmod(0o600)
    good=call();check('empty_preflight_actual_worker',good['state']=='COLD_RESPONSE_PREFLIGHT_VERIFIED' and good['workerPid']!=os.getpid())
    check('empty_bytes_unchanged',path.read_bytes()==original)
    refused('unsettled',lambda:mutate('INSERT INTO response_keys VALUES(?,?,?,?,?,?)',('idem:x','a'*64,1,'null',None,None)),restore,code='response_preopen_unsettled_identity')
    refused('old_schema',lambda:mutate('ALTER TABLE response_keys DROP COLUMN model_json'),restore,code='response_preopen_schema_mismatch')
    refused('bad_body',lambda:mutate('INSERT INTO responses VALUES(?,?,?)',('r','not-json',1)),restore,code='response_preopen_invalid_body')
    refused('orphan',lambda:mutate('INSERT INTO conversations VALUES(?,?)',('c','absent')),restore,code='response_preopen_orphan_conversation')
    def overfull():
        c=sqlite3.connect(path);c.executemany('INSERT INTO responses VALUES(?,?,?)',[(str(i),'{}',1) for i in range(101)]);c.commit();c.close()
    refused('retention',overfull,restore,code='response_preopen_retention_pressure')
    for suffix in p.cold.SUFFIXES:
        side=home/(p.FILENAME+suffix);refused('sidecar'+suffix,lambda:side.touch(mode=0o600),side.unlink,code='response_preopen_recovery_required')
    refused('wrong_inode',lambda:None,lambda:None,want=replace(expected,response_identity=(ids[2][0],ids[2][1]+100000)),code='response_preopen_identity')
    refused('mode',lambda:path.chmod(0o644),lambda:path.chmod(0o600),code='response_preopen_identity')
    backup=home/'response-fixture-backup'
    def missing():path.rename(backup)
    def return_file():backup.rename(path)
    refused('missing',missing,return_file)
    def link():path.rename(backup);path.symlink_to(backup)
    def unlink():path.unlink();backup.rename(path)
    refused('symlink',link,unlink,code='response_preopen_identity')
    # Populate using real native methods, not a substituted constructor.
    state=SessionDB(home/'state.db');response=ResponseStore(db_path=str(path),canonical_state=state)
    response.put('resp_owned',{'output':[]});response.bind_request_key('idem:owned','a'*64)
    response.put('idem:owned',{'response':{'id':'resp_owned','status':'completed'}})
    response.set_conversation('owned','resp_owned');response.close();state.close()
    populated=path.read_bytes();good2=call();check('real_populated_preflight',good2['rowsObserved']['responses']==2 and good2['rowsObserved']['response_keys']==1)
    check('populated_bytes_unchanged',path.read_bytes()==populated)
    state=SessionDB(home/'state.db');response=ResponseStore(db_path=str(path),canonical_state=state)
    check('qualified_constructor_no_response_row_writes',response._conn.total_changes==0)
    response.close();state.close();check('qualified_constructor_response_bytes_stable',path.read_bytes()==populated)
    # Independent process owns raw response lock. Helper's opens/closes cannot
    # cancel this parent's SQLite lock; competitor is a separate interpreter.
    lock=sqlite3.connect(path);lock.execute('PRAGMA locking_mode=EXCLUSIVE');lock.execute('BEGIN EXCLUSIVE');lock.commit()
    def competitor():
        code="import sqlite3,sys,json;c=sqlite3.connect(sys.argv[1],timeout=.1)\ntry:\n c.execute('BEGIN IMMEDIATE');c.rollback();print(json.dumps({'state':'ACQUIRED'}))\nexcept sqlite3.OperationalError as e:\n print(json.dumps({'state':'BUSY','code':e.sqlite_errorcode}))\nfinally:c.close()"
        r=subprocess.run([sys.executable,'-I','-B','-c',code,str(path)],capture_output=True,text=True,timeout=5)
        assert r.returncode==0,r.stderr;return json.loads(r.stdout)
    a=competitor();check('competitor_before_busy',a=={'state':'BUSY','code':5})
    try:
        try:call()
        except p.ResponsePreopenRejected as exc:cases.append({'case':'locked','reason':str(exc)});check('busy_helper_refused',True)
        else:raise AssertionError('busy helper accepted')
        b=competitor();check('competitor_after_helper_busy',b=={'state':'BUSY','code':5})
    finally:lock.close()
    c=competitor();check('competitor_after_owner_close_acquired',c=={'state':'ACQUIRED'})
    check('parent_never_opens_during_verification',audit['parentSqliteOpens']==audit['parentDataOpens']==0)
    held.finish();check('native_lease_released',not owner.homes)
    imported={}
    for mod in tuple(sys.modules.values()):
        f=getattr(mod,'__file__',None)
        if f:
            q=Path(f).resolve()
            if q.is_relative_to(ROOT) and q.suffix=='.py':
                n=q.relative_to(ROOT).as_posix();h=hashlib.sha256(q.read_bytes()).hexdigest();assert manifest[n]==h,n;imported[n]=h
    check('source_bytes_stable',all(hashlib.sha256((ROOT/n).read_bytes()).hexdigest()==h for n,h in manifest.items()))
    print(json.dumps({'result':'PASS_SCOPED_NATIVE_RESPONSE_PREFLIGHT','checks':checks,'checkCount':len(checks),'cases':cases,
        'emptyReceipt':good,'populatedReceipt':good2,'lockSequence':[a,b,c],'sourceSha256':manifest,'importedSourceSha256':imported,
        'parentPid':os.getpid(),'uid':os.getuid(),'gid':os.getgid(),'audit':audit,'nativeMethodsMocked':False,
        'fullIsolationTested':False,'A109ThreeStoreStartupTested':False,'httpListenerStarted':False,'providerCalls':0}),flush=True)
    return 0
if __name__=='__main__':raise SystemExit(main())
