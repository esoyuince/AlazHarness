"""Fixed S101 lab-only SQLite user, never real Gateway or arbitrary workload."""
import argparse
from contextlib import closing
import ctypes
import json
import os
from pathlib import Path
import select
import sqlite3
import stat
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'packages/claw-hermes'))
import state_volume_supervisor as s


def guard():
    assert os.getuid()==os.geteuid()==0
    assert os.environ.get('WSL_DISTRO_NAME')=='AlazHarness-D3B-P71C'
    assert Path('/etc/alaz-p71c-lab-id').read_text().strip()=='AlazHarness-D3B-P71C'
    assert not Path('/mnt/c/Windows').exists()


def main():
    guard()
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--scope',type=Path,required=True)
    p.add_argument('--target',type=Path,required=True)
    p.add_argument('--nsfd',type=int,required=True)
    p.add_argument('--namespace-inode',type=int,required=True)
    p.add_argument('--loop-number',type=int,required=True)
    p.add_argument('--mode',choices=('write','read','hold'),required=True)
    a=p.parse_args()
    assert a.scope.is_relative_to('/sys/fs/cgroup/alaz-s101') and a.scope.name.startswith('volume-')
    assert a.target.is_relative_to('/srv/alaz-s101') and a.target.name.startswith('mount-')
    s.trusted(a.scope,directory=True)
    assert s.fs_type(a.scope)==s.CGROUP2_MAGIC
    assert a.nsfd>=3 and os.fstat(a.nsfd).st_ino==a.namespace_inode
    with (a.scope/'cgroup.procs').open('w') as f:f.write(str(os.getpid()))
    assert str(os.getpid()) in (a.scope/'cgroup.procs').read_text().split()
    lib=ctypes.CDLL(None,use_errno=True)
    lib.setns.argtypes=[ctypes.c_int,ctypes.c_int];lib.setns.restype=ctypes.c_int
    assert lib.setns(a.nsfd,0x00020000)==0,'setns_failed'
    os.close(a.nsfd)
    assert os.readlink('/proc/self/ns/mnt')=='mnt:['+str(a.namespace_inode)+']'
    assert a.target.stat().st_dev==os.makedev(7,a.loop_number) and s.fs_type(a.target)==0xEF53
    home=a.target/'profile'
    if a.mode=='write':
        assert not home.exists()
        home.mkdir(mode=0o700);os.chown(home,23001,23003)
    info=home.lstat();assert stat.S_ISDIR(info.st_mode) and info.st_uid==23001 and info.st_gid==23003
    os.setgroups([]);os.setresgid(23003,23003,23003);os.setresuid(23001,23001,23001)
    assert os.getresuid()==(23001,)*3 and os.getresgid()==(23003,)*3 and os.getgroups()==[]
    os.umask(0o077)
    report={'mode':a.mode,'pid':os.getpid(),'uid':os.getuid(),'gid':os.getgid(),
            'namespace':os.readlink('/proc/self/ns/mnt'),'imageDevice':home.stat().st_dev,
            'stores':{},'realHermesGateway':False}
    if a.mode=='hold':
        connection=sqlite3.connect((home/'state.db').as_uri()+'?mode=rw',uri=True)
        try:
            assert connection.execute('SELECT value FROM owned_record').fetchall()==[('s101-persisted',)]
            print(json.dumps({'state':'HELD',**report}),flush=True)
            assert select.select([sys.stdin],[],[],30)[0],'bounded_hold_expired'
            assert sys.stdin.readline()=='CLOSE\n'
        finally:connection.close()
        return 0
    for name in ('state.db','runs_idempotency.db'):
        path=home/name
        if a.mode=='write':assert not path.exists()
        else:assert path.is_file()
        uri=path.as_uri()+('?mode=rwc' if a.mode=='write' else '?mode=rw')
        with closing(sqlite3.connect(uri,uri=True)) as db:
            db.execute('PRAGMA journal_mode=PERSIST');db.execute('PRAGMA synchronous=FULL')
            duplicate=False
            if a.mode=='write':
                db.execute('CREATE TABLE owned_record(record_id TEXT PRIMARY KEY,value TEXT NOT NULL)')
                db.execute('INSERT INTO owned_record VALUES (?,?)',('s101-run-1','s101-persisted'));db.commit()
            else:
                try:db.execute('INSERT INTO owned_record VALUES (?,?)',('s101-run-1','wrong-duplicate'))
                except sqlite3.IntegrityError:duplicate=True;db.rollback()
                assert duplicate,'duplicate_not_refused'
            rows=db.execute('SELECT record_id,value FROM owned_record').fetchall()
            assert rows==[('s101-run-1','s101-persisted')]
            assert db.execute('PRAGMA integrity_check').fetchone()==('ok',)
            report['stores'][name]={'rows':rows,'duplicateRefused':duplicate,'inode':path.stat().st_ino,
                                    'device':path.stat().st_dev,'sqliteIntegrity':'ok'}
    print(json.dumps({'state':'DONE',**report}),flush=True)
    return 0


if __name__=='__main__':raise SystemExit(main())
