"""Fixed final-exec F111E274 actual native store/layout experiment, same canonical readiness-only HTTP; agent routes remain closed."""
import asyncio
import ctypes
import errno
import hashlib
import json
import os
from pathlib import Path
import select
import socket
import sys
import sqlite3
import secrets
from dataclasses import asdict,replace
import threading
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'packages/claw-hermes'),str(ROOT/'vendor-native'),str(ROOT/'dependencies')]
from provider_broker import ProviderBrokerClient
import gateway_native_layout as layout
import gateway_profile_lease as lease
import gateway_storage_mounts as mounts
import gateway_store_startup as startup
import gateway_http_readiness as http
from gateway import runtime_ownership as native


def connect(kind,address):
    with socket.socket(kind,socket.SOCK_STREAM) as sock:
        sock.settimeout(1)
        try:sock.connect(address)
        except OSError as exc:return exc.errno
    return 0


async def main():
    assert ROOT==Path('/opt/alaz-f111e274') and sys.flags.isolated==1
    data=json.loads(os.environ['F111E274_TEST']);receipt=json.loads(os.environ['F111E274_RECEIPT'])
    home=Path(receipt['profile']);work=Path(data['work']);checks={};stores={}
    if data['mode']=='deny':
        before=(home/'gateway.lock').read_bytes();denied=False
        try:mounts._read_mountinfo()
        except PermissionError:denied=True
        expected=mounts.ExpectedMount(1,(7,0),'/profile',str(home),'ext4')
        try:lease.reserve_profile(home,expected)
        except lease.ProfileLeaseRejected as exc:reason=str(exc)
        else:raise AssertionError('default_profile_admitted')
        assert denied and reason=='profile_reservation_unavailable' and before==(home/'gateway.lock').read_bytes()
        print(json.dumps({'state':'DEFAULT_REFUSED','pid':os.getpid(),'mountinfoDenied':True,'nativeLeaseRefused':True,'lockUnchanged':True}),flush=True)
        return 0
    record=mounts.select_mount(mounts.parse_mountinfo(mounts._read_mountinfo()),str(home))
    expected=mounts.ExpectedMount(record.mount_id,record.device,record.root,record.mount_point,record.filesystem)
    held=lease.reserve_profile(home,expected);lock_inode=(home/'gateway.lock').stat().st_ino
    checks['native_lease_after_exec']=held.check()['state']=='NATIVE_PROFILE_RESERVED' and held._owner is native.process_ownership
    checks['explicit_native_layout_only']=receipt['profileLayout']==layout.PROFILE_LAYOUT
    checks['same_profile_inode']=home.stat().st_ino==receipt['profileInode']
    before=layout.inspect_profile(home,uid=23001,gid=23003,device=home.stat().st_dev)
    checks['actual_complete_native_layout']=set(before)==layout.REQUIRED|{'profile'}
    trusted=dict(data['prepared'])
    for key in ('state_identity','replay_identity'):trusted[key]=tuple(trusted[key])
    prepared=startup.live.PreparedStoreExpectation(**trusted)
    bad=startup.NativeStoreStartup(held,expected,replace(prepared,state_schema_sha256='f'*64),instance_id='f111e274-reject-'+data['mode'])
    bad_http=http.StorageReadinessHttp(bad,token=secrets.token_hex(32))
    try:await bad_http.start()
    except http.ReadinessRejected:
        checks['wrong_schema_no_bind_or_epoch']=bad_http.status()['port'] is None and bad.status()['epochMayHaveAdvanced'] is False
    else:raise AssertionError('wrong_schema_http_started')
    await bad_http.close()
    checks['refused_http_preserves_caller_lease']=held.check()['state']=='NATIVE_PROFILE_RESERVED'
    owner=startup.NativeStoreStartup(held,expected,prepared,instance_id='f111e274-'+data['mode'])
    token=secrets.token_hex(32);service=http.StorageReadinessHttp(owner,token=token)
    http_start=await service.start();startup_receipt=owner.status()
    checks['same_product_http_serving']=http_start['state']=='SERVING' and http_start['agentRoutesEnabled'] is False
    port=http_start['port'];http_results=[]
    async def query(path='/health/ready',method='GET',authorization=None):
        reader,writer=await asyncio.wait_for(asyncio.open_connection('127.0.0.1',port),2)
        try:
            auth=('Bearer '+token).encode('ascii') if authorization is None else authorization
            packet=(method+' '+path+' HTTP/1.1\r\nHost: 127.0.0.1:'+str(port)+'\r\nConnection: close\r\nAuthorization: ').encode()+auth+b'\r\n\r\n'
            writer.write(packet);await writer.drain()
            head=await asyncio.wait_for(reader.readuntil(b'\r\n\r\n'),3)
            lines=head.decode('iso-8859-1').split('\r\n');status=int(lines[0].split()[1])
            headers={k.lower():v.strip() for line in lines[1:] if ':' in line for k,v in [line.split(':',1)]}
            count=int(headers['content-length']);assert 0<count<4096
            raw=await asyncio.wait_for(reader.readexactly(count),3);body=json.loads(raw)
            assert token not in raw.decode() and token not in head.decode('iso-8859-1')
            assert headers['cache-control']=='no-store'
            assert await asyncio.wait_for(reader.read(1),3)==b''
            http_results.append({'path':path,'method':method,'status':status,'body':body})
            return status,body
        finally:writer.close();await writer.wait_closed()
    status,body=await query()
    checks['ready_inside_private_netns']=status==200 and body['storageReady'] is True and body['runtimeAdmissionAuthorized'] is False
    checks['bad_credentials_401']=(await query(authorization=b'Bearer wrong'))[0]==401
    checks['invalid_auth_bytes_401']=(await query(authorization=b'Bearer '+bytes([255])))[0]==401
    checks['agent_route_closed']=(await query('/v1/runs',method='POST'))[0]==404
    checks['query_route_closed']=(await query('/health/ready?probe=1'))[0]==404
    checks['mutation_method_closed']=(await query(method='POST'))[0]==405
    print(json.dumps({'state':'HTTP_LISTENING','pid':os.getpid(),'port':port,'localReadyStatus':status}),flush=True)
    assert select.select([sys.stdin],[],[],10)[0] and sys.stdin.readline()=='HTTP_PROBED\n'
    checks['ready_after_host_probe']=(await query())[0]==200
    checks['product_startup_verified']=startup_receipt['state']=='VERIFIED' and startup_receipt['completedChecks']==['preflight','before_epoch','after_epoch']
    checks['clean_only_no_replay']=startup_receipt['recoveryPolicy']=='REFUSE_PENDING_NO_REPLAY' and startup_receipt['automaticRecoveryPerformed'] is False
    checks['storage_not_http_authority']=startup_receipt['runtimeAdmissionAuthorized'] is False
    db=owner.state_store;replay=owner.replay_store
    import hermes_state_runtime as runtime
    checks['native_connections_are_real_disk']=Path(db._conn.execute('PRAGMA database_list').fetchone()[2])==home/'state.db' and replay.durable is True and Path(replay._conn.execute('PRAGMA database_list').fetchone()[2])==home/'runs_idempotency.db'
    assert checks['native_connections_are_real_disk'],'memory_or_wrong_db_refused_before_epoch'
    opened=[];watch=False
    def audit(event,args):
        if watch and event=='open':opened.append(str(args[0]))
    sys.addaudithook(audit)
    db._conn.execute('BEGIN IMMEDIATE')
    try:owner.close()
    except startup.StoreStartupRejected as exc:checks['active_transaction_blocks_product_close']=str(exc)=='startup_transaction_active'
    else:checks['active_transaction_blocks_product_close']=False
    checks['refused_close_keeps_transaction_and_store']=db._conn.in_transaction and owner.state_store is db
    watch=True
    try:layout.inspect_profile(home,uid=23001,gid=23003,device=home.stat().st_dev)
    finally:watch=False
    checks['layout_preserves_active_sql_transaction']=db._conn.in_transaction is True
    checks['no_raw_database_or_lock_open']=opened==[str(home/'SOUL.md'),str(home/'cache/schema_columns.json')]
    db._conn.rollback()
    epoch=owner.expectation.epoch
    session='f111e274-session';request='f111e274-request';scope='f111e274-scope';key='f111e274-key';rid='run_'+('4'*32);fp='a'*64
    kwargs=dict(epoch=epoch,principal_id='f111e274',session_id=session,request_id=request,payload={'text':'owned native test'})
    if data['mode']=='write':
        checks['initial_epoch_one']=epoch==1
        db.create_session(session,'api')
        admitted=runtime.admit_session_input(db,**kwargs)
        row=runtime.claim_session_input(db,epoch=epoch,session_id=session)
        outcome,rep=replay.reserve(scope,key,fp,rid,{'status':'running'},owner_pid=os.getpid(),owner_started=1)
        checks['native_first_admission_started']=admitted['status']=='queued' and row['status']=='started' and outcome=='created'
        row=runtime.settle_session_input(db,epoch=epoch,admission_id=row['admission_id'],generation=row['generation'],outcome='completed')
        replay.update_status(rid,{'status':'completed'})
        checks['explicit_test_work_settled']=row['status']=='terminal'
        duplicate=False;recovery=0
    else:
        checks['new_epoch_two']=epoch==2
        recovery=0
        saved=db._conn.execute('SELECT admission_id FROM main.session_admissions WHERE request_id=?',(request,)).fetchone()[0]
        row=runtime.get_session_admission(db,admission_id=saved)
        again=runtime.admit_session_input(db,**kwargs)
        outcome,rep=replay.reserve(scope,key,fp,'run_'+('5'*32),{'status':'running'})
        duplicate=again['admission_id']==row['admission_id'] and outcome=='reused' and rep['run_id']==rid
        checks['terminal_state_retained_without_recovery']=row['status']=='terminal' and recovery==0
        checks['no_finished_job_replayed']=runtime.claim_session_input(db,epoch=epoch,session_id=session) is None
        try:runtime.admit_session_input(db,**(kwargs|{'epoch':1,'request_id':'stale-new'}))
        except runtime.RuntimeStoreError as exc:checks['stale_epoch_refused']=str(exc)=='stale_epoch'
        else:checks['stale_epoch_refused']=False
        checks['duplicate_native_request_reused']=duplicate
    stores={'state.db':{'rows':[[row['admission_id'],request]],'inode':(home/'state.db').stat().st_ino,'duplicateRefused':duplicate},
            'runs_idempotency.db':{'rows':[[rep['run_id'],key]],'inode':(home/'runs_idempotency.db').stat().st_ino,'duplicateRefused':duplicate}}
    checks['native_integrity_ok']=db._conn.execute('PRAGMA integrity_check').fetchone()[0]=='ok' and replay._conn.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
    journals={n:x._conn.execute('PRAGMA journal_mode').fetchone()[0] for n,x in (('state',db),('replay',replay))}
    checks['ready_after_explicit_fixture_settlement']=(await query())[0]==200
    db._conn.execute('UPDATE main.runtime_epoch SET epoch=? WHERE singleton=1',(epoch+100,));db._conn.commit()
    checks['epoch_drift_revokes_http']=(await query())[0]==503
    db._conn.execute('UPDATE main.runtime_epoch SET epoch=? WHERE singleton=1',(epoch,));db._conn.commit()
    checks['epoch_restore_does_not_reenable_http']=(await query())[0]==503
    live_status,live_body=await query('/health/live')
    checks['liveness_remains_process_only']=live_status==200 and live_body['scope']=='process_liveness_only' and live_body['runtimeAdmissionAuthorized'] is False
    next_expectation=asdict(owner.expectation)
    pending_id=None
    if data['mode']=='read':
        pending=runtime.admit_session_input(db,epoch=epoch,principal_id='f111e274',session_id=session,
            request_id='f111e274-intentionally-unfinished',payload={'text':'no dispatch test'})
        pending=runtime.claim_session_input(db,epoch=epoch,session_id=session);pending_id=pending['admission_id']
    db._conn.execute('BEGIN IMMEDIATE')
    try:await service.close()
    except http.ReadinessRejected:checks['http_closed_even_when_storage_transaction_blocks']=service.status()['state']=='HTTP_CLOSED'
    else:checks['http_closed_even_when_storage_transaction_blocks']=False
    checks['http_close_retains_native_transaction']=db._conn.in_transaction and held.check()['state']=='NATIVE_PROFILE_RESERVED'
    checks['private_http_port_closed_before_storage']=connect(socket.AF_INET,('127.0.0.1',port))==errno.ECONNREFUSED
    db._conn.rollback()
    http_closed=await service.close()
    checks['same_http_product_closes_native_stores']=http_closed['state']=='CLOSED' and http_closed['callerLeaseMayBeReleased'] is True
    checks['product_closes_both_connections_before_lease']=owner.status()['callerLeaseMayBeReleased'] is True and held.check()['state']=='NATIVE_PROFILE_RESERVED'
    blocked_receipt=None
    if pending_id is not None:
        obj=dict(next_expectation)
        for key in ('state_identity','replay_identity'):obj[key]=tuple(obj[key])
        blocked=startup.NativeStoreStartup(held,expected,startup.live.PreparedStoreExpectation(**obj),instance_id='f111e274-must-not-start')
        try:blocked.start()
        except startup.StoreStartupRejected:
            blocked_receipt=blocked.status()
            checks['pending_work_blocks_product_start']=blocked_receipt['state']=='FAILED' and blocked_receipt['epochMayHaveAdvanced'] is False
        else:raise AssertionError('unfinished_work_accepted')
        try:blocked.start()
        except startup.StoreStartupRejected as exc:checks['failed_start_cannot_repeat']=str(exc)=='startup_not_fresh'
        else:checks['failed_start_cannot_repeat']=False
        blocked.close()
        with sqlite3.connect((home/'state.db').as_uri()+'?mode=ro',uri=True) as checkdb:
            checks['refused_start_preserves_epoch_and_started_row']=checkdb.execute('SELECT epoch FROM main.runtime_epoch').fetchone()[0]==epoch and checkdb.execute('SELECT status FROM main.session_admissions WHERE admission_id=?',(pending_id,)).fetchone()[0]=='started'
        checkdb.close()
    after=layout.inspect_profile(home,uid=23001,gid=23003,device=home.stat().st_dev)
    checks['native_aux_inventory_survives_open_close']=set(after)==set(before)
    fields={}
    for line in Path('/proc/self/status').read_text().splitlines():
        k,_,v=line.partition(':');fields[k]=v.split()
    checks['final_uid_gid']=fields['Uid']==['23001']*4 and fields['Gid']==['23003']*4
    checks['no_groups_or_caps']=not fields['Groups'] and all(int(fields[k][0],16)==0 for k in ('CapInh','CapPrm','CapEff','CapBnd','CapAmb'))
    checks['nnp_seccomp_after_exec']=fields['NoNewPrivs']==['1'] and fields['Seccomp']==['2']
    ns={k:os.readlink('/proc/self/ns/'+k) for k in ('mnt','net','ipc','user')}
    checks['private_namespace_preserved']=all(ns[k]!=data['parentNamespaces'][k] for k in ('mnt','net','ipc')) and ns['user']==data['parentNamespaces']['user']
    checks['self_mountinfo_exact_optin']=receipt['filesystem']['selfMountMetadata'] is True
    checks['broker_ping']=await ProviderBrokerClient(data['settings']).ready() is True
    errors={}
    for name,kind,address in (('host_tcp',socket.AF_INET,('127.0.0.1',data['tcpPort'])),('host_abstract',socket.AF_UNIX,'\0'+data['abstract']),('ambient',socket.AF_UNIX,data['ambient']),('sibling',socket.AF_UNIX,data['sibling'])):
        errors[name]=connect(kind,address)
    checks['other_host_endpoints_denied']=all(n in (errno.ENOENT,errno.EACCES,errno.EPERM,errno.ECONNREFUSED) for n in errors.values())
    checks['host_paths_private_state_hidden']=not any(Path(p).exists() for p in ('/srv/alaz-p71c/private/config.json','/srv/alaz-p71c/private/budget/budget.sqlite3','/mnt/c','/sys/fs/cgroup','/proc/1','/.old-root',data['source']))
    checks['scratch_starts_fresh']=not (work/'ephemeral-marker').exists();(work/'ephemeral-marker').write_text('owned private scratch')
    errors_canary=[]
    for flags in (os.O_RDONLY,os.O_WRONLY):
        try:fd=os.open(data['canary'],flags)
        except OSError as exc:errors_canary.append(exc.errno)
        else:os.close(fd);errors_canary.append(0)
    checks['canary_read_write_denied']=Path(data['canary']).exists() and all(e in (errno.EPERM,errno.EACCES) for e in errors_canary)
    try:os.fstat(data['inheritedFd'])
    except OSError as exc:checks['inherited_fd_closed']=exc.errno==errno.EBADF
    else:checks['inherited_fd_closed']=False
    done=threading.Event();writer=threading.Thread(target=done.wait,daemon=True);native.process_ownership.start_writer(writer)
    try:held.finish()
    except lease.ProfileLeaseRejected as exc:checks['live_writer_retains_profile']=str(exc)=='profile_writers_still_active'
    else:checks['live_writer_retains_profile']=False
    manifest=json.loads((ROOT/'input-manifest.json').read_text())['sources'];imported={}
    for module in tuple(sys.modules.values()):
        f=getattr(module,'__file__',None)
        if f:
            p=Path(f).resolve()
            if p.is_relative_to(ROOT) and p.suffix=='.py':
                n=p.relative_to(ROOT).as_posix();h=hashlib.sha256(p.read_bytes()).hexdigest();assert manifest[n]==h,n;imported[n]=h
    checks['native_sources_pinned']=all('vendor-native/'+n in imported for n in ('hermes_state.py','hermes_state_runtime.py','gateway/runtime_ownership.py','gateway/platforms/api_server_run_idempotency.py'))
    source_items=sorted(imported.items())
    source_digest=hashlib.sha256(json.dumps(imported,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    chunks=[dict(source_items[i:i+32]) for i in range(0,len(source_items),32)]
    assert 0<len(chunks)<=16
    for index,part in enumerate(chunks):
        line=json.dumps({'state':'SOURCE_CHUNK','pid':os.getpid(),'index':index,'total':len(chunks),'sources':part})
        assert len(line.encode())<8192
        print(line,flush=True)
    print(json.dumps({'state':'RESULT','result':'PASS_CONFINED_NATIVE_STORE_LAYOUT' if all(checks.values()) else 'FAIL',
        'mode':data['mode'],'pid':os.getpid(),'receipt':receipt,'checks':checks,'checkCount':len(checks),'stores':stores,
        'epoch':epoch,'recovered':recovery,'productStartup':startup_receipt,'blockedStartup':blocked_receipt,'nextExpectation':next_expectation,'stateStatus':row['status'],'journals':journals,'sourceCount':len(imported),'sourceDigest':source_digest,
        'auxiliaryOpensWhileDbTransaction':opened,'hostEndpointErrnos':errors,'nativeProfileLease':True,
        'productStorageStartup':True,'httpStartup':http_start,'httpClosed':http_closed,'httpResults':http_results,'fullIsolationReadinessHttp':True,'realHermesGateway':False,'fullAdmissionGateImplemented':False,'providerSends':0,'fullD3BAccepted':False}),flush=True)
    assert select.select([sys.stdin],[],[],25)[0] and sys.stdin.readline()=='RELEASE\n'
    done.set();writer.join(3);held.finish();assert not native.process_ownership.homes
    print(json.dumps({'state':'PROFILE_RELEASED_PROCESS_ALIVE','pid':os.getpid(),'lockInode':lock_inode}),flush=True)
    assert select.select([sys.stdin],[],[],25)[0] and sys.stdin.readline()=='EXIT\n'
    return 0 if all(checks.values()) else 1

if __name__=='__main__':raise SystemExit(asyncio.run(main()))
