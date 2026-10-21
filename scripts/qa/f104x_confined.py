"""Fixed post-exec native Hermes ProfileLease acceptance; not a full Gateway."""
import asyncio
from contextlib import closing
import ctypes
import errno
import json
import os
from pathlib import Path
import select
import socket
import sqlite3
import sys
import hashlib
import threading
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'packages/claw-hermes'))
from provider_broker import ProviderBrokerClient


def denied_connect(kind,address):
    with socket.socket(kind,socket.SOCK_STREAM) as sock:
        sock.settimeout(1)
        try:sock.connect(address)
        except OSError as exc:return exc.errno
    return 0


def main():
    data=json.loads(os.environ['F104X_TEST']);receipt=json.loads(os.environ['F104X_RECEIPT'])
    assert ROOT==Path('/opt/alaz-f104x') and sys.flags.isolated==1
    sys.path[:0]=[str(ROOT/'vendor-native'),str(ROOT/'dependencies')]
    import gateway_storage_mounts as mounts
    import gateway_profile_lease as lease
    from gateway import runtime_ownership as native
    manifest=json.loads((ROOT/'input-manifest.json').read_text())['sources']
    home=Path(receipt['profile']);work=Path(data['work']);checks={};stores={}
    if data['mode']=='deny':
        before=(home/'gateway.lock').read_bytes();denied=False
        try:mounts._read_mountinfo()
        except PermissionError:denied=True
        expected=mounts.ExpectedMount(1,(7,0),'/profile',str(home),'ext4')
        try:lease.reserve_profile(home,expected)
        except lease.ProfileLeaseRejected as exc:reason=str(exc)
        else:raise AssertionError('unqualified_default_reservation')
        assert denied and reason=='profile_reservation_unavailable'
        assert not native.process_ownership.homes and before==(home/'gateway.lock').read_bytes()
        print(json.dumps({'state':'DEFAULT_REFUSED','pid':os.getpid(),'mountinfoDenied':True,
                         'nativeLeaseRefused':True,'lockUnchanged':True,'reason':reason}),flush=True)
        return 0
    raw=mounts._read_mountinfo();records=mounts.parse_mountinfo(raw)
    mounted=mounts.select_mount(records,str(home))
    assert mounted.root=='/profile' and mounted.mount_point==str(home) and mounted.filesystem=='ext4'
    assert mounted.device==(os.major(receipt['profileDevice']),os.minor(receipt['profileDevice']))
    expected=mounts.ExpectedMount(mounted.mount_id,mounted.device,mounted.root,mounted.mount_point,mounted.filesystem)
    before_db={n:hashlib.sha256((home/n).read_bytes()).hexdigest() for n in ('state.db','runs_idempotency.db')}
    held=lease.reserve_profile(home,expected)
    assert held._owner is native.process_ownership
    lock_inode=(home/'gateway.lock').stat().st_ino
    checks['native_lease_after_final_exec']=held.check()['state']=='NATIVE_PROFILE_RESERVED'
    checks['unchanged_native_mount_observer_ran']=held._observation['bothStoresAndPresentSidecarsOnExpectedMount'] is True
    checks['observer_did_not_open_database_contents']=held._observation['databaseContentsOpened'] is False
    checks['reservation_did_not_mutate_databases']=before_db=={n:hashlib.sha256((home/n).read_bytes()).hexdigest() for n in before_db}
    checks['native_held_fd_is_not_inheritable']=not os.get_inheritable(held._handle.fileno())
    native_record=json.loads((home/'gateway.lock').read_text())
    checks['native_owner_record_has_final_pid']=native_record['pid']==os.getpid()
    checks['self_mountinfo_is_narrow_optin']=receipt['filesystem']['selfMountMetadata'] is True and receipt['filesystem']['metadataReadFileCount']==6
    fields={}
    for line in Path('/proc/self/status').read_text().splitlines():
        k,_,v=line.partition(':');fields[k]=v.split()
    checks['real_final_uid_gid']=fields['Uid']==['23001']*4 and fields['Gid']==['23003']*4
    checks['no_groups_or_capabilities']=not fields['Groups'] and all(int(fields[k][0],16)==0 for k in
        ('CapInh','CapPrm','CapEff','CapBnd','CapAmb'))
    checks['nnp_and_filter_survive_exec']=fields['NoNewPrivs']==['1'] and fields['Seccomp']==['2']
    checks['isolated_interpreter']=sys.flags.isolated==1
    ns={k:os.readlink('/proc/self/ns/'+k) for k in ('mnt','net','ipc','user')}
    checks['own_mount_network_ipc']=all(ns[k]!=data['parentNamespaces'][k] for k in ('mnt','net','ipc'))
    checks['host_user_identity_preserved']=ns['user']==data['parentNamespaces']['user']
    checks['same_profile_inode']=home.stat().st_ino==receipt['profileInode'] and home.stat().st_dev==receipt['profileDevice']
    flags=os.statvfs(home).f_flag
    checks['profile_rw_nosuid_nodev_noexec']=flags&(2|4|8)==(2|4|8) and not flags&1
    checks['scratch_fresh_after_each_exec']=not (work/'ephemeral-marker').exists()
    (work/'ephemeral-marker').write_text('not persistent')
    checks['scratch_private_writable']=(work/'ephemeral-marker').read_text()=='not persistent'
    for name in ('state.db','runs_idempotency.db'):
        with closing(sqlite3.connect((home/name).as_uri()+'?mode=rw',uri=True)) as db:
            db.execute('PRAGMA journal_mode=PERSIST');db.execute('PRAGMA synchronous=FULL')
            duplicate=False
            if data['mode']=='write':
                assert db.execute('SELECT COUNT(*) FROM owned_record').fetchone()==(0,)
                db.execute('INSERT INTO owned_record VALUES (?,?)',('p102-run','persisted-in-confinement'));db.commit()
            else:
                try:db.execute('INSERT INTO owned_record VALUES (?,?)',('p102-run','wrong-duplicate'))
                except sqlite3.IntegrityError:duplicate=True;db.rollback()
                assert duplicate
            rows=db.execute('SELECT id,value FROM owned_record').fetchall()
            integrity=db.execute('PRAGMA integrity_check').fetchone()
            checks[name+'_persisted']=rows==[('p102-run','persisted-in-confinement')] and integrity==('ok',)
            stores[name]={'rows':rows,'inode':(home/name).stat().st_ino,'device':(home/name).stat().st_dev,
                          'duplicateRefused':duplicate,'integrity':integrity[0]}
    checks['broker_native_ping']=asyncio.run(ProviderBrokerClient(data['settings']).ready()) is True
    forbidden={'host_tcp':(socket.AF_INET,('127.0.0.1',data['tcpPort'])),
               'host_abstract':(socket.AF_UNIX,'\0'+data['abstract']),
               'ambient_socket':(socket.AF_UNIX,data['ambient']),
               'broker_sibling':(socket.AF_UNIX,data['sibling'])}
    errors={}
    for name,(kind,address) in forbidden.items():
        errors[name]=denied_connect(kind,address)
        checks[name+'_denied']=errors[name] in (errno.EPERM,errno.EACCES,errno.ENOENT,errno.ECONNREFUSED,errno.ENETUNREACH)
    checks['source_volume_path_hidden']=not Path(data['source']).exists()
    checks['image_root_not_exported']=not (home.parent/'image-root-secret').exists()
    checks['broker_private_state_hidden']=not Path('/srv/alaz-p71c/private/config.json').exists() and not Path('/srv/alaz-p71c/private/budget/budget.sqlite3').exists()
    checks['old_root_host_and_foreign_proc_hidden']=not any(Path(p).exists() for p in ('/.old-root','/mnt/c','/run/WSL','/proc/1','/sys/fs/cgroup'))
    canary_errors=[]
    for flags in (os.O_RDONLY,os.O_WRONLY):
        try:fd=os.open(data['canary'],flags)
        except OSError as exc:canary_errors.append(exc.errno)
        else:os.close(fd);canary_errors.append(0)
    checks['present_canary_denied']=Path(data['canary']).is_file() and all(n in (errno.EPERM,errno.EACCES) for n in canary_errors)
    try:os.fstat(data['inheritedFd'])
    except OSError as exc:checks['ambient_fd_closed']=exc.errno==errno.EBADF
    else:checks['ambient_fd_closed']=False
    checks['self_mountinfo_read_succeeds']=mounts._read_mountinfo()==raw
    metadata_denials={}
    for path,flags in (('/proc/self/mountinfo',os.O_WRONLY),('/proc/self/environ',os.O_RDONLY),
                       ('/proc/self/mem',os.O_RDONLY),('/proc/self/fd',os.O_RDONLY|os.O_DIRECTORY),
                       ('/proc/self/mounts',os.O_RDONLY),('/proc/self/limits',os.O_RDONLY)):
        try:fd=os.open(path,flags)
        except OSError as exc:metadata_denials[path+':'+str(flags)]=exc.errno
        else:os.close(fd);metadata_denials[path+':'+str(flags)]=0
    checks['other_proc_and_mountinfo_write_denied']=all(e in (errno.EACCES,errno.EPERM,errno.EROFS) for e in metadata_denials.values())
    checks['foreign_process_mountinfo_hidden']=not Path('/proc/'+str(data['controllerPid'])+'/mountinfo').exists()
    done=threading.Event();writer=threading.Thread(target=done.wait,name='f104x-owned-writer',daemon=True)
    native.process_ownership.start_writer(writer)
    try:held.finish()
    except lease.ProfileLeaseRejected as exc:checks['registered_live_writer_keeps_native_lease']=str(exc)=='profile_writers_still_active'
    else:checks['registered_live_writer_keeps_native_lease']=False
    checks['lease_still_held']=held.check()['state']=='NATIVE_PROFILE_RESERVED'
    imported={}
    for module in tuple(sys.modules.values()):
        filename=getattr(module,'__file__',None)
        if filename:
            path=Path(filename).resolve()
            if path.is_relative_to(ROOT) and path.suffix=='.py':
                name=path.relative_to(ROOT).as_posix();digest=hashlib.sha256(path.read_bytes()).hexdigest()
                assert manifest[name]==digest
                imported[name]=digest
    checks['native_ownership_sources_verified']=all('vendor-native/'+name in imported for name in
        ('gateway/runtime_ownership.py','gateway/status.py','gateway/__init__.py'))
    lib=ctypes.CDLL(None,use_errno=True)
    checks['new_namespace_denied']=lib.unshare(ctypes.c_int(0x40000000))==-1 and ctypes.get_errno()==errno.EPERM
    with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as listener:
        path=work/'own.sock';listener.bind(str(path));listener.listen(1)
        checks['private_runtime_socket_works']=denied_connect(socket.AF_UNIX,str(path))==0
    path.unlink()
    result={'state':'RESULT','result':'PASS_CONFINED_DUMMY_STORAGE' if all(checks.values()) else 'FAIL',
            'mode':data['mode'],'pid':os.getpid(),'checks':checks,'checkCount':len(checks),
            'stores':stores,'namespaces':ns,'receipt':receipt,'connectionErrnos':errors,
            'nativeSources':imported,'metadataDenials':metadata_denials,'lockInode':lock_inode,
            'realHermesGateway':False,'nativeProfileLease':True,'providerSends':0,'fullD3BAccepted':False}
    print(json.dumps(result),flush=True)
    assert select.select([sys.stdin],[],[],20)[0] and sys.stdin.readline()=='RELEASE\n'
    done.set();writer.join(3);assert not writer.is_alive()
    held.finish();assert not native.process_ownership.homes and held._handle.closed
    assert (home/'gateway.lock').stat().st_ino==lock_inode
    print(json.dumps({'state':'PROFILE_RELEASED_PROCESS_ALIVE','pid':os.getpid(),'lockInode':lock_inode}),flush=True)
    assert select.select([sys.stdin],[],[],20)[0] and sys.stdin.readline()=='EXIT\n'
    return 0 if all(checks.values()) else 1

if __name__=='__main__':raise SystemExit(main())
