"""S101 actual mounted-image experiment, only the approved disposable P71C.

Creates one fresh 64MiB image, formats ONLY that file, uses existing test UID.
Never touch existing P71C/G84E data, default Ubuntu, accounts or providers.
"""
from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import select
import signal
import stat
import subprocess
import sys
import time
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'packages/claw-hermes'))
import state_volume_supervisor as s
from state_image_lease import ImagePin,acquire_image_lease,VolumeLeaseRejected
D='AlazHarness-D3B-P71C';PY='/usr/bin/python3.12'
BASE=Path('/srv/alaz-s101');CG=Path('/sys/fs/cgroup/alaz-s101')
ENV={'PATH':'/usr/bin:/bin','LANG':'C.UTF-8','HOME':'/','WSL_DISTRO_NAME':D}


def guard():
    s.actor()
    assert os.environ.get('WSL_DISTRO_NAME')==D and Path('/etc/alaz-p71c-lab-id').read_text().strip()==D
    assert ROOT==Path('/opt/alaz-s101') and not Path('/mnt/c/Windows').exists()
    s.trusted(ROOT,directory=True)
    manifest=json.loads((ROOT/'input-manifest.json').read_text())
    for name,digest in manifest['files'].items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest
    return manifest


def pin_for(path):
    f=path.stat();p=path.parent.stat()
    return ImagePin(str(path),f.st_dev,f.st_ino,f.st_size,f.st_uid,f.st_gid,p.st_dev,p.st_ino)


def empty_group(scope):
    end=time.monotonic()+5
    while scope.exists() and s.populated((scope/'cgroup.events').read_text()):
        if time.monotonic()>end:raise RuntimeError('owned_scope_not_drained')
        time.sleep(.02)


def dummy_user(volume,mode):
    assert volume.worker.poll() is None
    ns=Path('/proc')/str(volume.worker.pid)/'ns/mnt'
    fd=os.open(ns,os.O_RDONLY|os.O_CLOEXEC)
    try:
        inode=os.fstat(fd).st_ino
        assert os.readlink(ns)=='mnt:['+str(inode)+']'
        assert str(volume.worker.pid) in (volume.scope/'cgroup.procs').read_text().split()
        proc=subprocess.Popen([PY,'-I','-B',str(ROOT/'scripts/qa/s101_volume_user.py'),
            '--scope',str(volume.scope),'--target',str(volume.target),'--nsfd',str(fd),
            '--namespace-inode',str(inode),'--loop-number',str(volume.loop_number),'--mode',mode],
            pass_fds=(fd,),stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
            cwd='/',env=ENV,bufsize=0)
    finally:os.close(fd)
    return proc


def done_user(volume,mode):
    proc=dummy_user(volume,mode)
    try:
        out,err=proc.communicate(timeout=15)
        assert proc.returncode==0 and not err,('owned_user_failed',proc.returncode,err.decode()[:200])
        result=json.loads(out);assert result['state']=='DONE' and result['pid']==proc.pid
        return result
    finally:
        if proc.poll() is None:proc.kill();proc.communicate(timeout=5)


def crash_controller():
    guard();image=BASE/'images/state.img';target=BASE/'mount-orphan'
    assert target.is_dir() and not any(target.iterdir())
    pin=pin_for(image);v=s.VolumeSupervisor.begin(pin,CG,target)
    # A crash AFTER durable preparation but BEFORE attach still must fence reuse.
    print(json.dumps({'pid':os.getpid(),'state':'FENCED','scope':str(v.scope),
                      'fenceSha256':hashlib.sha256(v.fence.read_bytes()).hexdigest(),
                      'scopeIdentity':v.scope_id,'token':v.token}),flush=True)
    os._exit(73)


def main():
    manifest=guard()
    if sys.argv[1:]==['--owned-crash-controller']:return crash_controller()
    assert len(sys.argv)==1 and not BASE.exists() and not CG.exists(),'fresh_paths_required'
    mount_before=Path('/proc/self/mountinfo').read_bytes()
    BASE.mkdir(mode=0o755);(BASE/'images').mkdir(mode=0o700)
    image=BASE/'images/state.img'
    with image.open('xb') as stream:stream.truncate(64*1024*1024)
    image.chmod(0o600)
    mkfs=Path('/usr/sbin/mke2fs');s.trusted(mkfs)
    r=subprocess.run([str(mkfs),'-t','ext4','-q','-F','-E','lazy_itable_init=0,lazy_journal_init=0',str(image)],
        cwd='/',env=ENV,stdin=subprocess.DEVNULL,capture_output=True,timeout=30)
    assert r.returncode==0,('owned_image_format_failed',r.stderr.decode()[:200])
    CG.mkdir(mode=0o755);assert s.fs_type(CG)==s.CGROUP2_MAGIC
    for name in ('mount-one','mount-two','mount-three','mount-orphan'):(BASE/name).mkdir(mode=0o700)
    pin=pin_for(image);checks={};events=[];volumes=[];reader=None;error=None;cleanup=[];forced=False
    initial_pin=asdict(pin)
    def record(name,ok):
        checks[name]=bool(ok)
        if not ok:raise AssertionError(name)
    def denied(call,reason):
        try:call()
        except (s.SupervisorRejected,VolumeLeaseRejected) as exc:return reason in str(exc)
        return False
    try:
        v=s.VolumeSupervisor.begin(pin,CG,BASE/'mount-one');volumes.append(v)
        record('fence_durable_before_attachment',v.fence.exists() and v.stage=='PREPARED' and not s.attachments(pin))
        record('cooperating_image_rival_refused',denied(lambda:acquire_image_lease(pin),'volume_busy'))
        v.attach();ready=v.start();events.append({'phase':'first-mounted',**ready})
        record('actual_ext4_private_mount',ready['filesystem']=='ext4' and not os.path.ismount(v.target))
        record('finish_refuses_live_worker',denied(v.finish,'worker_alive') and v.fence.exists())
        written=done_user(v,'write');events.append({'phase':'write',**written})
        record('both_sqlite_stores_committed_as_gateway_uid',written['uid']==23001 and len(written['stores'])==2)
        reader=dummy_user(v,'hold');held=s.read_line(reader);events.append({'phase':'reader-held',**held})
        record('independent_volume_user_alive',held['state']=='HELD' and held['pid']==reader.pid and reader.poll() is None)
        record('normal_stop_refuses_live_group_user',denied(v.stop,'users_still_active') and v.stage=='STOP_REFUSED')
        record('lease_and_fence_retained_while_user_lives',v.fence.exists() and denied(lambda:acquire_image_lease(pin),'volume_busy'))
        out,err=reader.communicate(b'CLOSE\n',timeout=10)
        record('reader_reaped_before_unmount',reader.returncode==0 and not err);reader=None
        stopped=v.stop();record('normal_unmount_confirmed',stopped['state']=='UNMOUNTED')
        empty_group(v.scope);closed=v.finish();events.append({'phase':'first-closed',**closed})
        record('first_scope_and_loop_gone_before_unlock',not v.fence.exists() and not v.scope.exists() and not s.attachments(pin))
        v2=s.VolumeSupervisor.begin(pin,CG,BASE/'mount-two');volumes.append(v2)
        v2.attach();ready2=v2.start();events.append({'phase':'second-mounted',**ready2})
        read=done_user(v2,'read');events.append({'phase':'read-after-new-mount',**read})
        record('committed_rows_survive_complete_detach_reattach',all(read['stores'][n]['rows']==written['stores'][n]['rows'] for n in written['stores']))
        record('both_stores_refuse_duplicate_after_new_mount',all(row['duplicateRefused'] for row in read['stores'].values()))
        record('database_inodes_survive_new_mount',all(read['stores'][n]['inode']==written['stores'][n]['inode'] for n in written['stores']))
        v2.stop();empty_group(v2.scope);v2.finish()
        record('second_cycle_clean',not s.attachments(pin) and not v2.fence.exists())
        v3=s.VolumeSupervisor.begin(pin,CG,BASE/'mount-three');volumes.append(v3)
        v3.attach();ready3=v3.start();events.append({'phase':'third-mounted',**ready3})
        reader=dummy_user(v3,'hold');held3=s.read_line(reader)
        assert held3['state']=='HELD' and held3['pid']==reader.pid
        v3.worker.kill();v3.worker.wait(timeout=10)  # intentional owned helper crash
        record('owned_worker_abrupt_exit_observed',v3.worker.returncode==-signal.SIGKILL)
        record('surviving_user_blocks_finish_after_worker_exit',denied(v3.finish,'users_still_active'))
        record('orphaned_namespace_keeps_attachment_visible',bool(s.attachments(pin)) and v3.fence.exists())
        record('image_still_locked_after_worker_crash',denied(lambda:acquire_image_lease(pin),'volume_busy'))
        out,err=reader.communicate(b'CLOSE\n',timeout=10)
        record('last_surviving_user_reaped',reader.returncode==0 and not err);reader=None
        empty_group(v3.scope);v3.finish()
        record('abrupt_worker_cleanup_detaches_before_unlock',not s.attachments(pin) and not v3.scope.exists() and not v3.fence.exists())
        crash=subprocess.run([PY,'-I','-B',str(Path(__file__).resolve()),'--owned-crash-controller'],
              cwd='/',env=ENV,capture_output=True,timeout=15)
        assert crash.returncode==73 and not crash.stderr
        abandoned=json.loads(crash.stdout);events.append({'phase':'controller-crash',**abandoned})
        fence=Path(pin.path+'.volume-owner.json');fencebytes=fence.read_bytes()
        record('actual_controller_crash_leaves_fence',hashlib.sha256(fencebytes).hexdigest()==abandoned['fenceSha256'])
        lease=acquire_image_lease(pin);lease.confirm();lease.close()
        record('advisory_lease_free_but_restart_fenced',True)
        try:s.VolumeSupervisor.begin(pin,CG,BASE/'mount-orphan')
        except FileExistsError:record('stale_fence_refuses_new_controller',True)
        else:record('stale_fence_refuses_new_controller',False)
        record('stale_fence_never_auto_repaired',fence.read_bytes()==fencebytes)
        # Explicit QA-only cleanup for the just-reaped exact crash fixture.
        # Product exposes no auto-reconcile or force-unlock operation.
        orphan=Path(abandoned['scope'])
        assert orphan.parent==CG and s.trusted(orphan,directory=True)==tuple(abandoned['scopeIdentity'])
        assert not s.populated((orphan/'cgroup.events').read_text()) and not (orphan/'cgroup.procs').read_text().strip()
        assert not s.attachments(pin) and not os.path.ismount(BASE/'mount-orphan')
        orphan.rmdir();assert fence.read_bytes()==fencebytes;fence.unlink()
        fd=os.open(fence.parent,os.O_RDONLY|os.O_DIRECTORY);os.fsync(fd);os.close(fd)
        record('only_owned_stale_fixture_reconciled_after_proof',not fence.exists() and not orphan.exists())
    except BaseException as exc:
        error={'type':type(exc).__name__,'reason':str(exc)[:250]}
    finally:
        if reader is not None and reader.poll() is None:
            try:reader.communicate(b'CLOSE\n',timeout=5)
            except Exception:reader.kill();reader.communicate(timeout=5);forced=True
        for volume in reversed(volumes):
            if volume.stage=='CLOSED':continue
            try:
                if volume.worker is not None and volume.worker.poll() is None:
                    if volume.stage in ('RUNNING','STOP_REFUSED'):volume.stop()
                    else:volume.worker.terminate();volume.worker.wait(timeout=5);forced=True
                empty_group(volume.scope);volume.finish()
                cleanup.append({'stage':'CLOSED','token':volume.token})
            except BaseException as exc:
                cleanup.append({'stage':volume.stage,'token':volume.token,'error':type(exc).__name__+':'+str(exc)[:160]})
    checks['parent_mount_table_unchanged']=Path('/proc/self/mountinfo').read_bytes()==mount_before
    checks['source_files_unchanged']=all(hashlib.sha256((ROOT/n).read_bytes()).hexdigest()==h for n,h in manifest['files'].items())
    checks['image_identity_not_replaced']=asdict(pin_for(image))==initial_pin
    checks['no_remaining_image_loop']=not s.attachments(pin)
    checks['no_live_owned_cgroup']=not s.populated((CG/'cgroup.events').read_text())
    checks['all_owned_scopes_removed']=not any(p.is_dir() for p in CG.iterdir())
    checks['no_unexpected_force_cleanup']=not forced
    if checks['no_live_owned_cgroup'] and checks['all_owned_scopes_removed']:CG.rmdir()
    report={'result':'PASS_SCOPED_MOUNTED_VOLUME' if error is None and all(checks.values()) else 'FAIL',
        'checks':checks,'checkCount':len(checks),'error':error,'events':events,'cleanup':cleanup,
        'sourceSha256':manifest['files'],'imagePin':initial_pin,'imageBytes':image.stat().st_size,
        'imageRetainedForInspection':True,'originalHostMountsChanged':False,
        'realImageFormatted':True,'realExt4Mounted':any(e.get('state')=='MOUNTED' for e in events),
        'realHermesGatewayStarted':False,'providerCalls':0,'powerLossTested':False,
        'fullD3BAccepted':False,'defaultUbuntuTouched':False}
    with (BASE/'acceptance.json').open('x',encoding='utf-8') as f:json.dump(report,f,indent=2);f.write('\n')
    print(json.dumps(report),flush=True)
    return 0 if report['result']=='PASS_SCOPED_MOUNTED_VOLUME' else 1


if __name__=='__main__':raise SystemExit(main())
