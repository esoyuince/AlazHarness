"""Fixed-process cold response-store observation; never repair or run constructors.

Trusted provisioner supplies identity; schema and constructor limits are pinned
here. A successful check is a cooperative snapshot, NOT admission or proof of
cross-store settlement. Existing two-store startup remains independent until
explicit integration. Parent never opens SQLite/data descriptors.
"""
from __future__ import annotations
from dataclasses import asdict, dataclass, fields
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

import gateway_store_preopen as cold
import gateway_live_store_gate as live

NATIVE_FEATURE='cc16c10b16a0ca8d80b23fd9be3f0e59ee605075'
SCHEMA_SHA256='c4b66ce0c9b2571b17eae2080834e365b3aa526d40157c8c3cf4f353541ae1b4'
FILENAME='response_store.db'
MAX_OUTPUT_ROWS=10000
ROOT=Path(__file__).resolve().parents[2]

class ResponsePreopenRejected(RuntimeError):
    pass

def require(ok,reason):
    if not ok:raise ResponsePreopenRejected(reason)

@dataclass(frozen=True)
class PreparedResponseExpectation:
    native_feature: str
    schema_sha256: str
    response_identity: tuple[int,int]
    max_size: int = 100
    max_identities: int = 1000

    def __post_init__(self):
        require(self.native_feature==NATIVE_FEATURE,'response_preopen_feature')
        require(self.schema_sha256==SCHEMA_SHA256,'response_preopen_schema_pin')
        require(type(self.response_identity) is tuple and len(self.response_identity)==2
                and all(type(n) is int and 0<n<2**64 for n in self.response_identity),
                'response_preopen_identity')
        require(type(self.max_size) is int and self.max_size==100
                and type(self.max_identities) is int and self.max_identities==1000,
                'response_preopen_constructor_limits')

def _expected(value):
    require(type(value) is dict and set(value)=={f.name for f in fields(PreparedResponseExpectation)},
            'response_preopen_expectation_fields')
    value=dict(value)
    require(type(value['response_identity']) is list and len(value['response_identity'])==2,
            'response_preopen_identity')
    value['response_identity']=tuple(value['response_identity'])
    return PreparedResponseExpectation(**value)

def _pair(expected,canonical):
    require(type(expected) is PreparedResponseExpectation
            and type(canonical) is live.PreparedStoreExpectation
            and canonical.journal_mode=='delete','response_preopen_trusted_expectation')
    require(expected.response_identity[0]==canonical.state_identity[0]
            and expected.response_identity not in (canonical.state_identity,canonical.replay_identity),
            'response_preopen_distinct_store')

def _no_sidecars(home):
    cold._no_sidecars(home)
    require(not any(os.path.lexists(home/(FILENAME+s)) for s in cold.SUFFIXES),
            'response_preopen_recovery_required')

def _none(conn,sql,reason):
    require(conn.execute(sql).fetchone() is None,reason)

def verify_response_connection(conn,expected):
    """Read from an already configured read-only helper connection; don't close it.

    Reject data that would trigger known constructor settlement/eviction. This
    does NOT assert settled response records match canonical outcome history.
    Native response bodies may be absent after LRU eviction; identities remain.
    """
    require(type(expected) is PreparedResponseExpectation,'response_preopen_trusted_expectation')
    require(type(conn) is sqlite3.Connection and not conn.in_transaction
            and conn.total_changes==0,'response_preopen_readonly_connection')
    require(cold._one(conn,'PRAGMA query_only')==1 and cold._one(conn,'PRAGMA trusted_schema')==0,
            'response_preopen_readonly_policy')
    require(cold._one(conn,'PRAGMA main.journal_mode')=='delete','response_preopen_delete_only')
    require(cold._one(conn,'PRAGMA main.application_id')==0
            and cold._one(conn,'PRAGMA main.user_version')==0,'response_preopen_version')
    require(live.schema_digest(conn)==expected.schema_sha256,'response_preopen_schema_mismatch')
    require(conn.execute('PRAGMA main.quick_check').fetchmany(2)==[('ok',)],'response_preopen_integrity')
    version=cold._one(conn,'PRAGMA main.data_version')
    counts={}
    for name,limit in (('responses',expected.max_size),('response_keys',expected.max_identities),
                       ('conversations',1000),('response_admissions',expected.max_identities),
                       ('response_output_order',MAX_OUTPUT_ROWS)):
        count=cold._one(conn,'SELECT count(*) FROM main.'+name)
        require(type(count) is int and 0<=count<=limit,'response_preopen_retention_pressure')
        counts[name]=count
    _none(conn,'SELECT 1 FROM main.response_keys WHERE settled_at IS NULL LIMIT 1',
          'response_preopen_unsettled_identity')
    _none(conn,"""SELECT 1 FROM main.response_keys WHERE
        typeof(request_key)!='text' OR length(request_key) NOT BETWEEN 1 AND 1024
        OR typeof(fingerprint)!='text' OR length(fingerprint)!=64
        OR typeof(created_at)!='integer' OR created_at<0
        OR typeof(settled_at) NOT IN ('real','integer') OR settled_at<0 OR abs(settled_at)>9007199254740991
        OR typeof(response_id)!='text' OR length(response_id) NOT BETWEEN 1 AND 1024
        OR typeof(model_json)!='text' OR length(CAST(model_json AS BLOB))>2097152
        OR NOT json_valid(model_json) LIMIT 1""",'response_preopen_invalid_identity')
    _none(conn,"""SELECT 1 FROM main.responses WHERE CASE
        WHEN typeof(response_id)!='text' OR length(response_id) NOT BETWEEN 1 AND 1024 THEN 1
        WHEN typeof(accessed_at) NOT IN ('real','integer') OR accessed_at<0 OR abs(accessed_at)>9007199254740991 THEN 1
        WHEN typeof(data)!='text' OR length(CAST(data AS BLOB))>2097152 THEN 1
        WHEN NOT json_valid(data) THEN 1
        WHEN json_type(data)!='object' THEN 1
        ELSE 0 END=1 LIMIT 1""",'response_preopen_invalid_body')
    _none(conn,"""SELECT 1 FROM main.response_admissions a WHERE
        typeof(a.request_key)!='text' OR typeof(a.admission_id)!='text'
        OR length(a.admission_id) NOT BETWEEN 1 AND 1024
        OR NOT EXISTS(SELECT 1 FROM main.response_keys k WHERE k.request_key=a.request_key)
        LIMIT 1""",'response_preopen_orphan_admission')
    _none(conn,"""SELECT 1 FROM main.response_output_order o WHERE
        typeof(o.item_id)!='text' OR length(o.item_id) NOT BETWEEN 1 AND 1024
        OR typeof(o.output_index)!='integer' OR o.output_index<0
        OR NOT EXISTS(SELECT 1 FROM main.response_keys k WHERE k.request_key=o.request_key)
        LIMIT 1""",'response_preopen_orphan_output')
    _none(conn,"""SELECT 1 FROM main.conversations c WHERE
        typeof(c.name)!='text' OR length(c.name) NOT BETWEEN 1 AND 1024
        OR NOT EXISTS(SELECT 1 FROM main.responses r WHERE r.response_id=c.response_id)
        LIMIT 1""",'response_preopen_orphan_conversation')
    require(conn.total_changes==0 and not conn.in_transaction
            and cold._one(conn,'PRAGMA main.data_version')==version,'response_preopen_changed')
    return counts

def _readonly(path,expected):
    conn=sqlite3.connect(path.as_uri()+'?mode=ro',uri=True,timeout=0,isolation_level=None)
    try:
        conn.enable_load_extension(False)
        conn.setlimit(sqlite3.SQLITE_LIMIT_LENGTH,2*1024*1024)
        conn.setlimit(sqlite3.SQLITE_LIMIT_SQL_LENGTH,65536)
        conn.execute('PRAGMA query_only=ON');conn.execute('PRAGMA trusted_schema=OFF');conn.execute('PRAGMA mmap_size=0')
        start=time.monotonic();steps=[0]
        def progress():
            steps[0]+=1000
            return int(steps[0]>cold.MAX_SQL_STEPS or time.monotonic()-start>cold.SQL_SECONDS)
        conn.set_progress_handler(progress,1000)
        def authorizer(action,a,b,db,trigger):
            if action==sqlite3.SQLITE_SELECT:return sqlite3.SQLITE_OK
            if action==sqlite3.SQLITE_READ and db=='main':return sqlite3.SQLITE_OK
            if action==sqlite3.SQLITE_FUNCTION and b in ('count','length','typeof','abs','json_valid','json_type'):
                return sqlite3.SQLITE_OK
            if action==sqlite3.SQLITE_PRAGMA and b is None and a in ('query_only','trusted_schema',
                    'database_list','journal_mode','data_version','application_id','user_version','quick_check'):
                return sqlite3.SQLITE_OK
            return sqlite3.SQLITE_DENY
        conn.set_authorizer(authorizer)
        rows=conn.execute('PRAGMA database_list').fetchall()
        require(len(rows)==1 and rows[0][:2]==(0,'main') and Path(rows[0][2])==path,
                'response_preopen_connection_path')
        return verify_response_connection(conn,expected)
    finally:conn.close()

def inspect_cold(request):
    """Fixed child-process entry. Never call on live parent SQLite file handles."""
    try:
        require(type(request) is dict and set(request)=={'version','parentPid','uid','gid','home','expected','canonical'},
                'response_preopen_request_fields')
        require(type(request['version']) is int and request['version']==1,'response_preopen_version')
        require(sys.platform=='linux' and all(type(request[k]) is int and request[k]>0 for k in ('parentPid','uid','gid')),
                'response_preopen_linux_identity')
        require(os.getresuid()==(request['uid'],)*3 and os.getresgid()==(request['gid'],)*3
                and os.getppid()==request['parentPid'],'response_preopen_actor')
        expected=_expected(request['expected']);canonical=cold._expectation(request['canonical']);_pair(expected,canonical)
        home,metadata=cold._path(request['home'],request['uid'],request['gid'])
        _no_sidecars(home)
        before=cold._hash_file(home/FILENAME,expected.response_identity,request['uid'],request['gid'])
        counts=_readonly(home/FILENAME,expected)
        _no_sidecars(home)
        after=cold._hash_file(home/FILENAME,expected.response_identity,request['uid'],request['gid'])
        require(before==after and cold._meta(home.lstat())==metadata
                and os.getppid()==request['parentPid'],'response_preopen_changed')
        return {'version':1,'state':'COLD_RESPONSE_PREFLIGHT_VERIFIED','workerPid':os.getpid(),
            'parentPid':request['parentPid'],'uid':request['uid'],'nativeFeature':expected.native_feature,
            'schemaSha256':expected.schema_sha256,'responseIdentity':list(expected.response_identity),
            'constructorLimits':{'max_size':expected.max_size,'max_identities':expected.max_identities},
            'requestSha256':hashlib.sha256(json.dumps(request,sort_keys=True,separators=(',',':')).encode()).hexdigest(),
            'fileSha256':before['sha256'],'rowsObserved':counts,'sqlWritesPerformed':False,
            'nativeConstructorsInvoked':False,'sidecarRecoveryPerformed':False,'normalSqliteLocks':True,
            'contentAndMetadataUnchanged':True,'knownConstructorMutationNeeded':False,
            'allConstructorEffectsExcluded':False,'canonicalOutcomeEquivalenceVerified':False,
            'runtimeAdmissionAuthorized':False,'fullD3BAccepted':False}
    except ResponsePreopenRejected:raise
    except cold.PreopenRejected as exc:
        raise ResponsePreopenRejected('response_'+str(exc)) from None
    except (OSError,sqlite3.Error,ValueError,TypeError,AttributeError,KeyError,IndexError,OverflowError):
        raise ResponsePreopenRejected('response_preopen_observation_unavailable') from None

def _parent_snapshot(held,mount,expected):
    home=held._home;actor=held._actor
    observation=live.mounts.observe_profile_mounts(home,mount)
    _no_sidecars(home)
    raw=live.mounts._read_mountinfo()
    require(hashlib.sha256(raw).hexdigest()==observation['mountTableSha256'],'response_preopen_mount_changed')
    record=live.mounts.select_mount(live.mounts.parse_mountinfo(raw),(home/FILENAME).as_posix())
    live.mounts._check_mount(record,mount)
    info=(home/FILENAME).lstat()
    require(stat.S_ISREG(info.st_mode) and info.st_nlink==1 and stat.S_IMODE(info.st_mode)==0o600
            and (info.st_dev,info.st_ino)==expected.response_identity
            and (info.st_uid,info.st_gid)==actor[1:3],'response_preopen_identity')
    require((os.major(info.st_dev),os.minor(info.st_dev))==record.device,'response_preopen_mount_changed')
    return observation,cold._meta(info)

def verify_response_preopen(held,expected_mount,expected,canonical_expected,*,timeout_seconds=12):
    """Parent holds native lease; fixed helper exits before metadata recheck.

    No DB contents opened here; child inherits existing confinement. No arbitrary
    command/path/source/callback accepted. Constructors must remain closed until
    ALL cold checks pass. Success does not install or activate the native patch.
    """
    process=None
    try:
        require(type(held) is live.profiles.ProfileLease,'response_preopen_native_lease_required')
        require(type(expected_mount) is live.mounts.ExpectedMount,'response_preopen_mount_expectation')
        _pair(expected,canonical_expected)
        require(type(timeout_seconds) in (int,float) and 0<timeout_seconds<=30,'response_preopen_timeout')
        held.check();actor=live.profiles._actor()
        require(actor==held._actor,'response_preopen_actor')
        before=_parent_snapshot(held,expected_mount,expected)
        request={'version':1,'parentPid':actor[0],'uid':actor[1],'gid':actor[2],
                 'home':str(held._home),'expected':asdict(expected),'canonical':asdict(canonical_expected)}
        raw=json.dumps(request,sort_keys=True,separators=(',',':')).encode()
        require(len(raw)<=cold.MAX_REQUEST,'response_preopen_request_size')
        process=subprocess.Popen([sys.executable,'-I','-B',str(ROOT/'scripts/run_response_preopen.py')],
            cwd=ROOT,env={'PATH':'/usr/bin:/bin','LANG':'C.UTF-8','HOME':'/'},
            stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,close_fds=True)
        try:out,err=process.communicate(raw,timeout=timeout_seconds)
        except subprocess.TimeoutExpired:
            process.kill();process.communicate()
            raise ResponsePreopenRejected('response_preopen_worker_timeout') from None
        require(len(out)<=cold.MAX_REPLY and not err,'response_preopen_worker_output')
        report=cold._json(out);require(type(report) is dict,'response_preopen_worker_output')
        if process.returncode!=0:
            code=report.get('reason','')
            require(type(code) is str and re.fullmatch('response_preopen_[a-z_]{1,65}',code) is not None,
                    'response_preopen_worker_failed')
            raise ResponsePreopenRejected(code)
        require(report.get('state')=='COLD_RESPONSE_PREFLIGHT_VERIFIED' and report.get('workerPid')==process.pid
                and report.get('parentPid')==actor[0] and report.get('uid')==actor[1]
                and report.get('requestSha256')==hashlib.sha256(raw).hexdigest()
                and report.get('nativeFeature')==expected.native_feature and report.get('schemaSha256')==expected.schema_sha256
                and report.get('responseIdentity')==list(expected.response_identity)
                and report.get('constructorLimits')=={'max_size':expected.max_size,'max_identities':expected.max_identities},
                'response_preopen_worker_binding')
        for k in ('sqlWritesPerformed','nativeConstructorsInvoked','sidecarRecoveryPerformed',
                  'runtimeAdmissionAuthorized','fullD3BAccepted','knownConstructorMutationNeeded','canonicalOutcomeEquivalenceVerified'):
            require(report.get(k) is False,'response_preopen_worker_scope')
        require(report.get('contentAndMetadataUnchanged') is True and report.get('normalSqliteLocks') is True,
                'response_preopen_worker_scope')
        require(type(report.get('fileSha256')) is str and re.fullmatch('[0-9a-f]{64}',report['fileSha256']) is not None,
                'response_preopen_worker_output')
        held.check()
        require(before==_parent_snapshot(held,expected_mount,expected) and live.profiles._actor()==actor,
                'response_preopen_parent_changed')
        return report
    except ResponsePreopenRejected:raise
    except (OSError,ValueError,TypeError,AttributeError,KeyError,cold.PreopenRejected,
            live.profiles.ProfileLeaseRejected,live.mounts.StorageMountRejected):
        raise ResponsePreopenRejected('response_preopen_parent_unavailable') from None
    finally:
        if process is not None and process.poll() is None:
            process.kill();process.communicate()
