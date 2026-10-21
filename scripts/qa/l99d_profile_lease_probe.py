"""Ordinary-user native Hermes profile ownership proof in disposable P71C.

Only new temporary profiles/code; no Gateway, replay collector, provider, root,
accounts, mounts or restore. Real native locks, contenders and child exit; no
mocking of kernel/native lock boundaries. SQLite schemas are dummy fixtures.
"""
from __future__ import annotations
import argparse
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import threading

ROOT=Path(__file__).resolve().parents[2]
PIN='eb75627faf532fa6ffbdae59a0d14b0b385fc780'


def setup(home):
    if sys.platform!='linux' or os.getuid()!=os.geteuid()!=23001:
        raise ValueError('designated_linux_user_required')
    assert os.getuid()==os.geteuid()==23001 and os.getgid()==23003
    assert ROOT.parent==Path('/tmp') and ROOT.name.startswith('alaz-l99d-code-')
    data=json.loads((ROOT/'input-manifest.json').read_text())
    assert data['sourcePin']==PIN
    for name,digest in data['files'].items():
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest
    os.environ['HERMES_HOME']=str(home)
    sys.path[:0]=[str(ROOT/'packages/claw-hermes'),str(ROOT/'vendor-native'),str(ROOT/'dependencies')]
    from gateway import runtime_ownership as native
    import gateway_profile_lease as lease
    import gateway_storage_mounts as mounts
    return native,lease,mounts,data


def expected_for(home,mounts):
    r=subprocess.run(['/usr/bin/findmnt','--json','--target',str(home),
        '--output','ID,MAJ:MIN,FSROOT,TARGET,FSTYPE'],capture_output=True,text=True,timeout=5,check=True)
    row=json.loads(r.stdout)['filesystems'];assert len(row)==1;row=row[0]
    assert row['fstype']=='ext4'
    return mounts.ExpectedMount(int(row['id']),tuple(map(int,row['maj:min'].split(':'))),
                                 row['fsroot'],row['target'],row['fstype'])


def stats(home):
    return {name:{'sha256':hashlib.sha256((home/name).read_bytes()).hexdigest(),
                  'inode':(home/name).stat().st_ino,'device':(home/name).stat().st_dev}
            for name in ('state.db','runs_idempotency.db')}


def child(home,mode):
    assert home.is_absolute() and home==home.resolve() and home.parent==Path('/tmp')
    assert home.name.startswith('alaz-l99d-profile-') and (home/'.l99d-owned').read_text()=='owned-fixture-only'
    native,lease,mounts,manifest=setup(home)
    expected=expected_for(home,mounts)
    try:
        held=lease.reserve_profile(home,expected)
    except lease.ProfileLeaseRejected as exc:
        print(json.dumps({'state':'REFUSED','reason':str(exc),'pid':os.getpid()}),flush=True)
        return 77
    assert native.process_ownership.owns(home)
    print(json.dumps({'state':'ACQUIRED','pid':os.getpid(),'lockInode':(home/'gateway.lock').stat().st_ino}),flush=True)
    if mode=='hold':
        assert sys.stdin.readline()=='ABRUPT\n'
        # Deliberate OWNED child-only abrupt termination: no native close/finalizers.
        os._exit(73)
    held.finish();return 0


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode',choices=('main','contend','hold'),default='main')
    parser.add_argument('--home',type=Path)
    args=parser.parse_args()
    if args.mode!='main':return child(args.home,args.mode)
    before_identity=(os.getresuid(),os.getresgid(),tuple(os.getgroups()),
                     os.readlink('/proc/self/ns/user'),os.readlink('/proc/self/ns/mnt'))
    before_mounts=Path('/proc/self/mountinfo').read_bytes();checks={};details={};children=[]
    temp_path=None;error=None;owned_child=None;held=None;writer_done=threading.Event();writer=None
    with tempfile.TemporaryDirectory(prefix='alaz-l99d-profile-',dir='/tmp') as tmp:
        home=Path(tmp).resolve();temp_path=home;home.chmod(0o700)
        (home/'.l99d-owned').write_text('owned-fixture-only')
        (home/'gateway.lock').write_bytes(b'');(home/'gateway.lock').chmod(0o600)
        for name in ('state.db','runs_idempotency.db'):
            with closing(sqlite3.connect(home/name)) as db:
                db.execute('CREATE TABLE owned_fixture(marker TEXT)')
                db.execute("INSERT INTO owned_fixture VALUES ('l99d')");db.commit()
            (home/name).chmod(0o600)
        original=stats(home);lock_inode=(home/'gateway.lock').stat().st_ino
        native,lease,mounts,manifest=setup(home);expected=expected_for(home,mounts)
        env={'PATH':'/usr/bin:/bin','LANG':'C.UTF-8','HOME':str(ROOT),'HERMES_HOME':str(home)}
        command=[sys.executable,'-I','-B',str(Path(__file__).resolve()),'--home',str(home)]
        def contender():
            r=subprocess.run(command+['--mode','contend'],cwd=ROOT,env=env,
                             capture_output=True,text=True,timeout=12)
            value=json.loads(r.stdout);children.append({'exitCode':r.returncode,**value})
            return r.returncode,value
        try:
            held=lease.reserve_profile(home,expected)
            checks['same_native_singleton_used']=held._owner is native.process_ownership
            checks['actual_profile_lock_reserved']=held.check()['state']=='NATIVE_PROFILE_RESERVED'
            checks['actual_lock_fd_noninheritable']=not os.get_inheritable(held._handle.fileno())
            lock_bytes=(home/'gateway.lock').read_bytes()
            code,value=contender()
            checks['competing_process_refused']=code==77 and value.get('reason')=='profile_already_owned'
            checks['contender_did_not_rewrite_owner_record']=(home/'gateway.lock').read_bytes()==lock_bytes
            try:lease.reserve_profile(home,expected)
            except lease.ProfileLeaseRejected as exc:checks['same_process_second_lease_refused']=str(exc)=='profile_native_owner_already_used'
            else:checks['same_process_second_lease_refused']=False
            (home/'legitimate-new-directory').mkdir()
            checks['normal_profile_directory_growth_supported']=held.check()['state']=='NATIVE_PROFILE_RESERVED'
            fork_pid=os.fork()
            if fork_pid==0:
                try:
                    held.finish()
                except lease.ProfileLeaseRejected as exc:
                    os._exit(0 if str(exc)=='profile_lease_other_process_or_thread' else 5)
                os._exit(6)
            _,exit_status=os.waitpid(fork_pid,0)
            checks['fork_child_cannot_release_parent_lease']=os.waitstatus_to_exitcode(exit_status)==0
            code,value=contender()
            checks['parent_os_lock_survives_child_exit']=code==77 and value.get('reason')=='profile_already_owned'
            writer=threading.Thread(target=writer_done.wait,name='owned-l99d-writer',daemon=True)
            native.process_ownership.start_writer(writer)
            try:held.finish()
            except lease.ProfileLeaseRejected as exc:checks['native_live_writer_prevents_release']=str(exc)=='profile_writers_still_active'
            else:checks['native_live_writer_prevents_release']=False
            code,value=contender()
            checks['writer_retention_excludes_second_process']=code==77 and value.get('reason')=='profile_already_owned'
            writer_done.set();writer.join(3);assert not writer.is_alive()
            held.finish();held.finish()
            checks['clean_close_releases_native_lock']=not native.process_ownership.homes
            checks['lock_inode_not_unlinked_on_close']=(home/'gateway.lock').stat().st_ino==lock_inode
            code,value=contender()
            checks['fresh_process_can_acquire_after_close']=code==0 and value.get('state')=='ACQUIRED'
            owned_child=subprocess.Popen(command+['--mode','hold'],cwd=ROOT,env=env,
                stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
            # Child readiness is bounded by selector, not an unbounded readline.
            import selectors
            with selectors.DefaultSelector() as selector:
                selector.register(owned_child.stdout,selectors.EVENT_READ)
                assert selector.select(12),'child_not_ready'
                ready=json.loads(owned_child.stdout.readline())
            assert ready['state']=='ACQUIRED' and ready['pid']==owned_child.pid
            code,value=contender()
            checks['second_owner_lifetime_excludes_contender']=code==77 and value.get('reason')=='profile_already_owned'
            rest,stderr=owned_child.communicate('ABRUPT\n',timeout=12)
            details['abruptOwner']={'pid':owned_child.pid,'exitCode':owned_child.returncode,'stderr':stderr,'ready':ready}
            checks['actual_owner_abrupt_exit']=owned_child.returncode==73
            code,value=contender()
            checks['kernel_releases_lock_after_abrupt_exit']=code==0 and value.get('state')=='ACQUIRED'
            checks['same_lock_inode_after_owner_restart']=(home/'gateway.lock').stat().st_ino==lock_inode
            checks['dummy_database_bytes_unchanged']=stats(home)==original
            checks['no_gateway_pid_or_new_database_created']=not (home/'gateway.pid').exists() and {
                p.name for p in home.iterdir()}=={'gateway.lock','state.db','runs_idempotency.db','.l99d-owned','legitimate-new-directory'}
            obs=held._observation
            checks['no_false_durability_or_admission_claim']=obs['fullGatewayPersistenceAccepted'] is False and obs['launchAuthorized'] is False
        except BaseException as exc:
            error=type(exc).__name__+':'+str(exc)[:200]
        finally:
            writer_done.set()
            if writer is not None:writer.join(3)
            if owned_child is not None and owned_child.poll() is None:
                owned_child.kill();owned_child.communicate(timeout=5)
            native.process_ownership.close()
        imported={}
        for module in list(sys.modules.values()):
            name=getattr(module,'__file__',None)
            if name:
                path=Path(name).resolve()
                if path.is_relative_to(ROOT) and path.suffix=='.py':
                    relative=path.relative_to(ROOT).as_posix()
                    assert relative in manifest['files']
                    digest=hashlib.sha256(path.read_bytes()).hexdigest();assert digest==manifest['files'][relative]
                    imported[relative]=digest
        checks['normal_native_imports_verified']=all('vendor-native/'+name in imported for name in (
            'gateway/runtime_ownership.py','gateway/status.py','gateway/__init__.py'))
        checks['sources_unchanged']=all(hashlib.sha256((ROOT/n).read_bytes()).hexdigest()==h for n,h in manifest['files'].items())
        details['importedSources']=imported;details['databaseBefore']=original;details['databaseAfter']=stats(home)
    checks['owned_profile_removed']=temp_path is not None and not temp_path.exists()
    checks['identity_and_namespaces_unchanged']=before_identity==(os.getresuid(),os.getresgid(),tuple(os.getgroups()),
                     os.readlink('/proc/self/ns/user'),os.readlink('/proc/self/ns/mnt'))
    checks['mount_table_unchanged']=before_mounts==Path('/proc/self/mountinfo').read_bytes()
    details['children']=children
    report={'result':'PASS_NATIVE_PROFILE_OWNERSHIP' if error is None and all(checks.values()) else 'FAIL',
            'checks':checks,'checkCount':len(checks),'details':details,'error':error,
            'sourcePin':PIN,'sourceSha256':manifest['files'],'uid':os.getuid(),'gid':os.getgid(),
            'nativeLockingMocked':False,'nativeGatewayStarted':False,'providerCalls':0,
            'rootCommand':False,'uidChanged':False,'persistentVolumeIntegrated':False,
            'fullD3BAccepted':False,'scope':'native profile reservation only; dummy SQLite stores, no replay/Gateway execution'}
    print(json.dumps(report,sort_keys=True))
    return 0 if report['result']=='PASS_NATIVE_PROFILE_OWNERSHIP' else 1

if __name__=='__main__':raise SystemExit(main())
