"""S101 supplemental controller death AFTER mount with a surviving reader.

Existing owned S101 image only, fresh mountpoint/scope. No runtime recovery
policy: cleanup of the exact exited fixture is separately checked QA code.
"""
from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import select
import subprocess
import sys
import time
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'packages/claw-hermes'))
sys.path.insert(0,str(ROOT/'scripts/qa'))
import state_volume_supervisor as s
from state_image_lease import acquire_image_lease
import s101_volume_accept as base


def controller():
    base.guard();pin=base.pin_for(base.BASE/'images/state.img')
    v=s.VolumeSupervisor.begin(pin,base.CG,base.BASE/'mount-four')
    v.attach();ready=v.start()
    print(json.dumps({'state':'CONTROLLER_READY','pid':os.getpid(),'workerPid':v.worker.pid,
        'scope':str(v.scope),'scopeIdentity':list(v.scope_id),'mountpoint':str(v.target),
        'namespace':ready['mountNamespace'],'loopNumber':v.loop_number,'fence':str(v.fence),
        'fenceSha256':hashlib.sha256(v.fence.read_bytes()).hexdigest()}),flush=True)
    assert select.select([sys.stdin],[],[],25)[0]
    assert sys.stdin.readline()=='CRASH\n'
    os._exit(74)


def main():
    manifest=base.guard()
    extra=json.loads((ROOT/'supplemental-manifest.json').read_text())
    assert extra['files']=={'scripts/qa/s101_orphan_accept.py':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    if sys.argv[1:]==['--controller']:return controller()
    assert len(sys.argv)==1 and not base.CG.exists() and not (base.BASE/'mount-four').exists()
    report_path=base.BASE/'orphan-acceptance.json';assert not report_path.exists()
    base.CG.mkdir(mode=0o755);(base.BASE/'mount-four').mkdir(mode=0o700)
    pin=base.pin_for(base.BASE/'images/state.img');mounts=Path('/proc/self/mountinfo').read_bytes()
    checks={};events=[];ctrl=None;reader=None;ready=None;error=None;cleanup=[]
    def check(name,ok):
        checks[name]=bool(ok)
        if not ok:raise AssertionError(name)
    try:
        ctrl=subprocess.Popen([base.PY,'-I','-B',str(Path(__file__).resolve()),'--controller'],
            cwd='/',env=base.ENV,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,bufsize=0)
        ready=s.read_line(ctrl);events.append(ready)
        check('real_controller_and_worker_live',ready['pid']==ctrl.pid and ctrl.poll() is None and Path('/proc/'+str(ready['workerPid'])).exists())
        scope=Path(ready['scope']);target=Path(ready['mountpoint']);ns=Path('/proc')/str(ready['workerPid'])/'ns/mnt'
        fd=os.open(ns,os.O_RDONLY|os.O_CLOEXEC)
        try:
            ino=os.fstat(fd).st_ino;assert ready['namespace']=='mnt:['+str(ino)+']'
            reader=subprocess.Popen([base.PY,'-I','-B',str(ROOT/'scripts/qa/s101_volume_user.py'),
                '--scope',str(scope),'--target',str(target),'--nsfd',str(fd),
                '--namespace-inode',str(ino),'--loop-number',str(ready['loopNumber']),'--mode','hold'],
                cwd='/',env=base.ENV,pass_fds=(fd,),stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,bufsize=0)
        finally:os.close(fd)
        held=s.read_line(reader);events.append(held)
        check('independent_gateway_uid_reader_holds_mount',held['pid']==reader.pid and held['uid']==23001 and held['state']=='HELD')
        out,err=ctrl.communicate(b'CRASH\n',timeout=10)
        check('controller_exited_without_cleanup',ctrl.returncode==74 and not err)
        # PID may remain briefly as a zombie. Cgroup population tracks live
        # users recursively; no inference from pid disappearance is needed.
        end=time.monotonic()+5
        while str(ready['workerPid']) in (scope/'cgroup.procs').read_text().split():
            assert time.monotonic()<end,'parent_death_signal_missing';time.sleep(.02)
        check('parent_death_stops_mount_worker',str(ready['workerPid']) not in (scope/'cgroup.procs').read_text().split())
        check('reader_survives_both_controller_and_worker',reader.poll() is None and str(reader.pid) in (scope/'cgroup.procs').read_text().split())
        check('surviving_mount_still_globally_attached',bool(s.attachments(pin)))
        fence=Path(ready['fence']);fence_before=fence.read_bytes()
        check('crash_fence_present_unchanged',hashlib.sha256(fence_before).hexdigest()==ready['fenceSha256'])
        free=acquire_image_lease(pin);free.confirm();free.close()
        check('advisory_lease_alone_is_available',True)
        try:s.VolumeSupervisor.begin(pin,base.CG,base.BASE/'mount-four')
        except s.SupervisorRejected as exc:check('new_supervisor_refuses_live_old_attachment',str(exc)=='supervisor_image_already_attached')
        else:check('new_supervisor_refuses_live_old_attachment',False)
        check('rejected_restart_did_not_change_fence',fence.read_bytes()==fence_before)
        out,err=reader.communicate(b'CLOSE\n',timeout=10)
        check('last_reader_reaped',reader.returncode==0 and not err);reader=None
        base.empty_group(scope)
        check('kernel_clears_loop_after_last_namespace_user',not s.attachments(pin))
        try:s.VolumeSupervisor.begin(pin,base.CG,base.BASE/'mount-four')
        except FileExistsError:check('stale_fence_still_refuses_after_loop_gone',True)
        else:check('stale_fence_still_refuses_after_loop_gone',False)
        assert s.trusted(scope,directory=True)==tuple(ready['scopeIdentity'])
        assert not s.populated((scope/'cgroup.events').read_text()) and not (scope/'cgroup.procs').read_text().strip()
        assert not s.attachments(pin) and not os.path.ismount(target) and not any(target.iterdir())
        assert fence.read_bytes()==fence_before
        scope.rmdir();fence.unlink()
        fd=os.open(fence.parent,os.O_RDONLY|os.O_DIRECTORY);os.fsync(fd);os.close(fd)
        check('exact_owned_crash_fixture_cleaned_after_proof',not scope.exists() and not fence.exists())
    except BaseException as exc:error={'type':type(exc).__name__,'reason':str(exc)[:240]}
    finally:
        if reader is not None and reader.poll() is None:
            try:reader.communicate(b'CLOSE\n',timeout=5)
            except Exception:reader.kill();reader.communicate(timeout=5);cleanup.append('owned_reader_force_cleanup')
        if ctrl is not None and ctrl.poll() is None:
            ctrl.terminate();ctrl.communicate(timeout=5);cleanup.append('owned_controller_terminated')
    checks['parent_mount_table_unchanged']=Path('/proc/self/mountinfo').read_bytes()==mounts
    checks['sources_unchanged']=all(hashlib.sha256((ROOT/n).read_bytes()).hexdigest()==h for n,h in (manifest['files']|extra['files']).items())
    checks['no_remaining_image_loop']=not s.attachments(pin)
    checks['no_remaining_live_owned_group']=not s.populated((base.CG/'cgroup.events').read_text())
    checks['no_extra_cleanup_for_success']=not cleanup
    if not any(p.is_dir() for p in base.CG.iterdir()) and checks['no_remaining_live_owned_group']:base.CG.rmdir()
    report={'result':'PASS_SCOPED_ORPHAN_REFUSAL' if error is None and all(checks.values()) else 'FAIL',
        'checks':checks,'checkCount':len(checks),'error':error,'events':events,'cleanup':cleanup,
        'sourceSha256':manifest['files']|extra['files'],'realImageMounted':True,
        'controllerExitCode':None if ctrl is None else ctrl.returncode,
        'automaticRecoveryImplemented':False,'realHermesGatewayStarted':False,'providerCalls':0,'fullD3BAccepted':False}
    with report_path.open('x',encoding='utf-8') as f:json.dump(report,f,indent=2);f.write('\n')
    print(json.dumps(report),flush=True)
    return 0 if report['result']=='PASS_SCOPED_ORPHAN_REFUSAL' else 1


if __name__=='__main__':raise SystemExit(main())
