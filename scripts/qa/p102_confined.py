"""Fixed post-exec confined dummy SQLite target. Never a Hermes Gateway."""
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
    data=json.loads(os.environ['P102_TEST']);receipt=json.loads(os.environ['P102_RECEIPT'])
    home=Path(receipt['profile']);work=Path(data['work']);checks={};stores={}
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
    try:fd=os.open('/proc/self/mountinfo',os.O_RDONLY)
    except OSError as exc:checks['baseline_mountinfo_denial_unchanged']=exc.errno in (errno.EPERM,errno.EACCES)
    else:os.close(fd);checks['baseline_mountinfo_denial_unchanged']=False
    lib=ctypes.CDLL(None,use_errno=True)
    checks['new_namespace_denied']=lib.unshare(ctypes.c_int(0x40000000))==-1 and ctypes.get_errno()==errno.EPERM
    with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as listener:
        path=work/'own.sock';listener.bind(str(path));listener.listen(1)
        checks['private_runtime_socket_works']=denied_connect(socket.AF_UNIX,str(path))==0
    path.unlink()
    result={'state':'RESULT','result':'PASS_CONFINED_DUMMY_STORAGE' if all(checks.values()) else 'FAIL',
            'mode':data['mode'],'pid':os.getpid(),'checks':checks,'checkCount':len(checks),
            'stores':stores,'namespaces':ns,'receipt':receipt,'connectionErrnos':errors,
            'realHermesGateway':False,'nativeProfileLease':False,'providerSends':0,'fullD3BAccepted':False}
    print(json.dumps(result),flush=True)
    assert select.select([sys.stdin],[],[],20)[0] and sys.stdin.readline()=='EXIT\n'
    return 0 if all(checks.values()) else 1

if __name__=='__main__':raise SystemExit(main())
