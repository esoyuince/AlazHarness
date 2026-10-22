"""Cold read-only store preflight in a FIXED separate interpreter.

Use under the held final native ProfileLease, before writable constructors.
Trusted preparation supplies expectations; no learning trust from candidate DBs.
Only closed DELETE-mode files without sidecars are supported. Never immutable,
nolock, native constructors, migration, recovery, listener or provider calls.
Parent observes mounts/lease; child needs no new /proc grants. Snapshot checks
assume cooperative exclusive lifecycle, not protection from malicious host root
or same-UID replacement/ABA. A result is NOT durable launch/retry authority.
"""
from __future__ import annotations
from dataclasses import asdict, fields
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import stat
import subprocess
import sys
import time

import gateway_live_store_gate as live
import gateway_constructor_metadata as metadata

ROOT=Path(__file__).resolve().parents[2]
MAX_REQUEST=16384
MAX_REPLY=8192
MAX_DB_BYTES=256*1024*1024
MAX_SQL_STEPS=1000000
SQL_SECONDS=6.0
FILES=('state.db','runs_idempotency.db')
SUFFIXES=('-journal','-wal','-shm')

class PreopenRejected(RuntimeError):
    pass

def require(ok,code):
    if not ok:raise PreopenRejected(code)

def _json(raw):
    def pairs(items):
        out={}
        for key,value in items:
            require(key not in out,'preopen_duplicate_field');out[key]=value
        return out
    try:
        return json.loads(raw,object_pairs_hook=pairs,
            parse_constant=lambda _:(_ for _ in ()).throw(PreopenRejected('preopen_nonfinite')))
    except (ValueError,TypeError,RecursionError):
        raise PreopenRejected('preopen_json') from None

def _expectation(value):
    require(type(value) is dict and set(value)=={f.name for f in fields(live.PreparedStoreExpectation)},'preopen_expectation_fields')
    value=dict(value)
    for key in ('state_identity','replay_identity'):
        require(type(value[key]) is list and len(value[key])==2,'preopen_file_identity')
        value[key]=tuple(value[key])
    expected=live.PreparedStoreExpectation(**value)
    require(expected.journal_mode=='delete','preopen_cold_delete_only')
    return expected

def _meta(info):
    return (info.st_dev,info.st_ino,info.st_mode,info.st_uid,info.st_gid,info.st_nlink,
            info.st_size,info.st_mtime_ns,info.st_ctime_ns)

def _path(home,uid,gid):
    require(type(home) is str and len(home)<=4096,'preopen_home')
    path=Path(home)
    require(path.is_absolute() and path==path.resolve(strict=True)
            and not any(p.is_symlink() for p in (path,*path.parents)),'preopen_canonical_home')
    info=path.lstat()
    require(stat.S_ISDIR(info.st_mode) and stat.S_IMODE(info.st_mode)==0o700
            and (info.st_uid,info.st_gid)==(uid,gid),'preopen_private_home')
    return path,_meta(info)

def _no_sidecars(home):
    for name in FILES:
        for suffix in SUFFIXES:
            require(not os.path.lexists(home/(name+suffix)),'preopen_explicit_recovery_required')

def _hash_file(path,identity,uid,gid):
    info=path.lstat()
    require(stat.S_ISREG(info.st_mode) and stat.S_IMODE(info.st_mode)==0o600
            and info.st_nlink==1 and (info.st_uid,info.st_gid)==(uid,gid)
            and (info.st_dev,info.st_ino)==identity,'preopen_file_identity')
    require(512<=info.st_size<=MAX_DB_BYTES,'preopen_file_size')
    before=_meta(info)
    fd=os.open(path,os.O_RDONLY|os.O_CLOEXEC|os.O_NOFOLLOW)
    try:
        require(_meta(os.fstat(fd))==before,'preopen_changed')
        head=os.read(fd,100)
        require(len(head)==100 and head[:16]==b'SQLite format 3\x00','preopen_header')
        require(head[18:20]==b'\x01\x01','preopen_cold_delete_only')
        digest=hashlib.sha256(head);size=len(head)
        while True:
            block=os.read(fd,min(65536,info.st_size-size+1))
            if not block:break
            size+=len(block);require(size<=info.st_size,'preopen_changed');digest.update(block)
        require(size==info.st_size and _meta(os.fstat(fd))==before,'preopen_changed')
    finally:os.close(fd)
    require(_meta(path.lstat())==before,'preopen_changed')
    return {'identity':before,'sha256':digest.hexdigest()}

def _one(conn,sql,args=()):
    rows=conn.execute(sql,args).fetchmany(2)
    require(len(rows)==1 and len(rows[0])==1,'preopen_single_value')
    return rows[0][0]

def _readonly(path,want,expected,*,state):
    # NEVER use immutable/nolock: normal locks must report busy or hot recovery.
    conn=sqlite3.connect(path.as_uri()+'?mode=ro',uri=True,timeout=0,isolation_level=None)
    try:
        conn.enable_load_extension(False)
        conn.setlimit(sqlite3.SQLITE_LIMIT_LENGTH,2*1024*1024)
        conn.setlimit(sqlite3.SQLITE_LIMIT_SQL_LENGTH,65536)
        conn.execute('PRAGMA query_only=ON')
        conn.execute('PRAGMA trusted_schema=OFF')
        conn.execute('PRAGMA mmap_size=0')
        budget=[0];start=time.monotonic()
        def progress():
            budget[0]+=1000
            return int(budget[0]>MAX_SQL_STEPS or time.monotonic()-start>SQL_SECONDS)
        conn.set_progress_handler(progress,1000)
        def authorizer(action,a,b,db,trigger):
            if action==sqlite3.SQLITE_SELECT:return sqlite3.SQLITE_OK
            if action==sqlite3.SQLITE_READ and db=='main':return sqlite3.SQLITE_OK
            if action==sqlite3.SQLITE_FUNCTION and b in ('count','length','typeof'):return sqlite3.SQLITE_OK
            if action==sqlite3.SQLITE_PRAGMA and b is None and a in (
                'query_only','trusted_schema','database_list','journal_mode','data_version','application_id','quick_check'):
                return sqlite3.SQLITE_OK
            return sqlite3.SQLITE_DENY
        conn.set_authorizer(authorizer)
        rows=conn.execute('PRAGMA database_list').fetchall()
        require(len(rows)==1 and rows[0][:2]==(0,'main') and Path(rows[0][2])==path,'preopen_connection_path')
        require(_one(conn,'PRAGMA query_only')==1 and _one(conn,'PRAGMA trusted_schema')==0,'preopen_readonly_policy')
        require(_one(conn,'PRAGMA main.journal_mode')=='delete','preopen_cold_delete_only')
        version=_one(conn,'PRAGMA main.data_version')
        require(live.schema_digest(conn)==want,'preopen_schema_mismatch')
        require(conn.execute('PRAGMA main.quick_check').fetchmany(2)==[('ok',)],'preopen_integrity')
        marker=None
        if state:
            require(_one(conn,'SELECT version FROM main.schema_version')==live.SCHEMA_VERSION,'preopen_schema_version')
            require(_one(conn,'PRAGMA main.application_id')==expected.application_id,'preopen_application_id')
            require(_one(conn,"SELECT value FROM main.state_meta WHERE key='store_instance_id'")==expected.store_instance_id,'preopen_store_instance')
            rows=conn.execute('SELECT epoch,instance_id FROM main.runtime_epoch WHERE singleton=1').fetchmany(2)
            require(rows==([] if expected.epoch==0 else [(expected.epoch,expected.instance_id)]),'preopen_epoch')
            marker=metadata.verify_constructor_metadata(conn,native_pin=expected.native_pin)
        require(conn.total_changes==0 and not conn.in_transaction
                and _one(conn,'PRAGMA main.data_version')==version,'preopen_changed')
        return marker
    finally:conn.close()

def inspect_cold(request):
    """Worker-only entry. Separate process is essential to preserve parent locks."""
    try:
        require(type(request) is dict and set(request)=={'version','parentPid','uid','gid','home','expected'},'preopen_request_fields')
        require(type(request['version']) is int and request['version']==1,'preopen_version')
        require(sys.platform=='linux' and all(type(request[k]) is int and request[k]>0 for k in ('uid','gid','parentPid')),'preopen_linux_identity')
        require(os.getresuid()==(request['uid'],)*3 and os.getresgid()==(request['gid'],)*3
                and os.getppid()==request['parentPid'],'preopen_actor')
        expected=_expectation(request['expected'])
        home,parent=_path(request['home'],request['uid'],request['gid'])
        _no_sidecars(home)
        identities=(expected.state_identity,expected.replay_identity)
        first=[_hash_file(home/n,i,request['uid'],request['gid']) for n,i in zip(FILES,identities)]
        marker=None
        for n,digest,is_state in ((FILES[0],expected.state_schema_sha256,True),(FILES[1],expected.replay_schema_sha256,False)):
            result=_readonly(home/n,digest,expected,state=is_state)
            if is_state:marker=result
        _no_sidecars(home)
        after=[_hash_file(home/n,i,request['uid'],request['gid']) for n,i in zip(FILES,identities)]
        require(first==after and _meta(home.lstat())==parent and os.getppid()==request['parentPid'],'preopen_changed')
        return {'version':1,'state':'COLD_STORES_PREFLIGHT_VERIFIED','workerPid':os.getpid(),
            'parentPid':request['parentPid'],'uid':request['uid'],'nativePin':expected.native_pin,
            'requestSha256':hashlib.sha256(json.dumps(request,sort_keys=True,separators=(',',':')).encode()).hexdigest(),
            'epochObserved':expected.epoch,'fileSha256':dict(zip(FILES,(r['sha256'] for r in first))),
            'constructorMetadata':marker,'sqlWritesPerformed':False,'nativeConstructorsInvoked':False,
            'sidecarRecoveryPerformed':False,'normalSqliteLocks':True,'contentAndMetadataUnchanged':True,
            'allConstructorEffectsExcluded':False,'cooperativeSnapshotOnly':True,
            'runtimeAdmissionAuthorized':False,'fullD3BAccepted':False}
    except PreopenRejected:raise
    except metadata.ConstructorMetadataRejected:
        raise PreopenRejected('preopen_constructor_metadata') from None
    except (OSError,sqlite3.Error,ValueError,TypeError,AttributeError,KeyError,IndexError,OverflowError):
        raise PreopenRejected('preopen_observation_unavailable') from None

def verify_preopen(held,expected_mount,expected,*,timeout_seconds=12):
    """Parent: fixed worker, native lease/mount held, no raw DB descriptors.

    Does not close caller connections or release the lease on failure. Worker
    exit/reaping precedes post-observation. No new metadata permissions needed.
    Caller must separately apply the finite layout and keep all other writers
    drained. Content cannot grant permission; trusted local expectations only.
    """
    process=None
    try:
        require(type(held) is live.profiles.ProfileLease,'preopen_native_lease_required')
        require(type(expected) is live.PreparedStoreExpectation and expected.journal_mode=='delete','preopen_trusted_cold_expectation')
        require(type(expected_mount) is live.mounts.ExpectedMount,'preopen_mount_expectation')
        require(type(timeout_seconds) in (int,float) and 0<timeout_seconds<=30,'preopen_timeout')
        held.check();actor=live.profiles._actor()
        require(actor==held._actor,'preopen_actor')
        before=live.mounts.observe_profile_mounts(held._home,expected_mount)
        request={'version':1,'parentPid':actor[0],'uid':actor[1],'gid':actor[2],
            'home':str(held._home),'expected':asdict(expected)}
        raw=json.dumps(request,sort_keys=True,separators=(',',':')).encode()
        require(len(raw)<=MAX_REQUEST,'preopen_request_size')
        command=[sys.executable,'-I','-B',str(ROOT/'scripts/run_store_preopen.py')]
        process=subprocess.Popen(command,cwd=ROOT,env={'PATH':'/usr/bin:/bin','LANG':'C.UTF-8','HOME':'/'},
            stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,close_fds=True)
        try:out,err=process.communicate(raw,timeout=timeout_seconds)
        except subprocess.TimeoutExpired:
            process.kill();process.communicate()
            raise PreopenRejected('preopen_worker_timeout') from None
        require(len(out)<=MAX_REPLY and not err,'preopen_worker_output')
        report=_json(out)
        require(type(report) is dict,'preopen_worker_output')
        if process.returncode!=0:
            code=report.get('reason','')
            require(type(code) is str and re.fullmatch('preopen_[a-z_]{1,60}',code) is not None,'preopen_worker_failed')
            raise PreopenRejected(code)
        require(report.get('state')=='COLD_STORES_PREFLIGHT_VERIFIED'
                and report.get('workerPid')==process.pid and report.get('parentPid')==actor[0]
                and report.get('uid')==actor[1] and report.get('requestSha256')==hashlib.sha256(raw).hexdigest(),
                'preopen_worker_binding')
        for key in ('sqlWritesPerformed','nativeConstructorsInvoked','sidecarRecoveryPerformed','runtimeAdmissionAuthorized','fullD3BAccepted'):
            require(report.get(key) is False,'preopen_worker_scope')
        held.check()
        after=live.mounts.observe_profile_mounts(held._home,expected_mount)
        require(before==after and live.profiles._actor()==actor,'preopen_parent_changed')
        return report
    except PreopenRejected:raise
    except (OSError,ValueError,TypeError,AttributeError,KeyError,live.profiles.ProfileLeaseRejected,live.mounts.StorageMountRejected):
        raise PreopenRejected('preopen_parent_unavailable') from None
    finally:
        if process is not None and process.poll() is None:
            process.kill();process.communicate()
