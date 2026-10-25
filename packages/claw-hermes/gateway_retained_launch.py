"""One explicit retained projection -> fixed exec -> original startup path.

The trusted supervisor has already joined the existing volume namespace/cgroup.
No elevation, provisioning, arbitrary command, shell, retry or workload callback.
Any error after projection begins terminates the dedicated child. JSON/context
are trusted launch data, not signatures or proof of a claimed kernel boundary.
"""
from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import sys

import gateway_retained_handoff as handoff
import gateway_retained_projection as mapping
import gateway_state_projection as state
import gateway_storage_mounts as mounts

ROOT = Path(__file__).resolve().parents[2]
PYTHON = '/usr/bin/python3.12'
ENTRY = 'scripts/run_retained_projected.py'
WIRE_ENV = 'ALAZ_RETAINED_WIRE'
CONTEXT_ENV = 'ALAZ_RETAINED_CONTEXT'
PROTOCOL = 'alaz-projected-exec-context-v1'
MAX_CONTEXT = 16384

class ProjectedLaunchRejected(RuntimeError):
    """Bounded diagnostics: no caller payload or secret contents."""

def require(ok, reason):
    if not ok:raise ProjectedLaunchRejected(reason)

def _bytes(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True,
                      allow_nan=False).encode('ascii')

def _instance(value, previous):
    require(type(value) is str and re.fullmatch('[A-Za-z0-9._-]{1,128}',value) is not None
            and value != previous, 'projected_new_instance_required')

def _namespaces():
    return {name:os.readlink('/proc/self/ns/'+name) for name in ('user','mnt','net','ipc')}

def _mount():
    row=mounts.select_mount(mounts.parse_mountinfo(mounts._read_mountinfo()),handoff.TARGET)
    return mounts.ExpectedMount(row.mount_id,row.device,row.root,row.mount_point,row.filesystem)

def _live(principal, namespaces, pid):
    state.gp.hp.gateway_identity(principal)
    current=state.gp.launch.observation()
    require(current['pid']==pid==os.getpid() and current['uids']==(principal['gatewayUid'],)*4
            and current['gids']==(principal['socketGroupGid'],)*4 and current['groups']==()
            and current['threads']==1 and current['nnp']==1
            and all(current['caps'][k]==0 for k in state.gp.launch.CAPS),
            'projected_live_identity')
    require(current['userns']==principal['hostUserNamespace']==namespaces['user']
            and current['uidMap']==['0','0','4294967295']
            and current['gidMap']==['0','0','4294967295'] and _namespaces()==namespaces,
            'projected_live_namespaces')
    require(state.gp.net.status()['Seccomp']=='2','projected_live_filter')

def _mount_shape(value, retained):
    require(type(value) is mounts.ExpectedMount,'projected_mount_type')
    value.__post_init__()
    require(value.mount_point==handoff.TARGET and value.root=='/profile'
            and value.filesystem=='ext4'
            and os.makedev(*value.device)==retained.home_identity[0],
            'projected_mount_identity')

def _environment(wire, context):
    scratch=context['scratch']
    return {'PATH':'/usr/bin:/bin','LANG':'C.UTF-8','HOME':handoff.TARGET,
            'HERMES_HOME':handoff.TARGET,'TMPDIR':scratch,'TMP':scratch,'TEMP':scratch,
            WIRE_ENV:wire.decode('ascii'),CONTEXT_ENV:_bytes(context).decode('ascii')}

def launch(value, filesystem, binding, record, *, scratch, instance_id):
    """Dedicated joined supervisor child only. Does not return on success.

    Caller must terminate after any exception; projection may have irreversible
    partial effects. The original root/controller/export guards execute in enter.
    """
    require(type(record) is handoff.RetainedStartup,'projected_record_type')
    handoff.validate(record,expected_home=record.retained.home)
    _instance(instance_id,record.state.instance_id)
    view,fs=state.gp.validate(value,filesystem)
    principal=view['principalContract']
    mapping.RetainedProjection(binding,record.retained,principal)
    scratch=handoff._home(scratch)
    require(scratch!='/dev/null' and scratch in fs['writable'],'projected_scratch_not_exported')
    target=str(ROOT/ENTRY)
    # Actual root-owned metadata/read-only export verification remains in enter.
    for path in (str(ROOT),PYTHON,target):
        handoff._home(path)
        require(any(PurePosixPath(path).is_relative_to(root) for root in fs['readonly']),
                'projected_entry_not_readonly')
    projected=state.enter(view,fs,binding,observe_self_mount=True,observe_self_identity=True,
                          profile_layout=state.NATIVE_RETAINED_LAYOUT,
                          retained_profile=record.retained)
    wire=handoff.encode_projected(projected,record.state,record.response)
    decoded=handoff.decode_projected(wire)
    namespaces=_namespaces();_live(principal,namespaces,os.getpid())
    expected=_mount();_mount_shape(expected,decoded.retained)
    context={'protocol':PROTOCOL,'pid':os.getpid(),'principal':principal,
             'namespaces':namespaces,'mount':asdict(expected),'scratch':scratch,
             'instanceId':instance_id,'wireSha256':hashlib.sha256(wire).hexdigest()}
    require(len(_bytes(context))<=MAX_CONTEXT,'projected_context_size')
    env=_environment(wire,context)
    # Neither argv nor executable is taken from JSON. Never inherit host environment.
    os.execve(PYTHON,[PYTHON,'-I','-B',target],env)
    raise ProjectedLaunchRejected('projected_exec_returned')

def receive(environment):
    """Validate trusted transfer/live inherited confinement before ANY lease/SQL.

    Returns existing typed expectations and the exact mount observation. It does
    not create another owner, open stores, start work or authenticate remote JSON.
    """
    try:
        require(sys.platform=='linux' and sys.flags.isolated==1 and sys.dont_write_bytecode
                and sys.executable==PYTHON,'projected_fixed_interpreter')
        require(type(environment) is dict and set(environment)=={
            'PATH','LANG','HOME','HERMES_HOME','TMPDIR','TMP','TEMP',WIRE_ENV,CONTEXT_ENV},
            'projected_environment_fields')
        raw=environment[WIRE_ENV];context_raw=environment[CONTEXT_ENV]
        require(type(raw) is str and 0<len(raw)<=handoff.MAX_BYTES
                and type(context_raw) is str and 0<len(context_raw)<=MAX_CONTEXT,
                'projected_transfer_bounds')
        wire=raw.encode('ascii');record=handoff.decode_projected(wire)
        context=handoff._json(context_raw)
        require(type(context) is dict and set(context)=={'protocol','pid','principal',
            'namespaces','mount','scratch','instanceId','wireSha256'},'projected_context_fields')
        require(_bytes(context).decode('ascii')==context_raw and context['protocol']==PROTOCOL,
                'projected_context_canonical')
        require(type(context['pid']) is int and context['pid']==os.getpid()
                and context['wireSha256']==hashlib.sha256(wire).hexdigest(),
                'projected_context_binding')
        principal=state.gp.hp.policy(context['principal'])
        ns=context['namespaces']
        require(type(ns) is dict and set(ns)=={'user','mnt','net','ipc'}
                and all(type(v) is str and re.fullmatch(k+r':\[[0-9]{1,20}\]',v)
                        for k,v in ns.items()),'projected_context_namespaces')
        _instance(context['instanceId'],record.state.instance_id)
        scratch=handoff._home(context['scratch'])
        require(scratch not in ('/', '/dev/null') and
                not PurePosixPath(scratch).is_relative_to(handoff.TARGET) and
                not PurePosixPath(handoff.TARGET).is_relative_to(scratch),
                'projected_context_scratch')
        require(environment==_environment(wire,context),'projected_environment_mismatch')
        m=context['mount']
        require(type(m) is dict and set(m)=={'mount_id','device','root','mount_point','filesystem'}
                and type(m['device']) is list and len(m['device'])==2,'projected_context_mount')
        expected=mounts.ExpectedMount(**{**m,'device':tuple(m['device'])})
        _mount_shape(expected,record.retained)
        _live(principal,ns,context['pid'])
        require(_mount()==expected,'projected_mount_changed_after_exec')
        return record,expected,context['instanceId']
    except ProjectedLaunchRejected:raise
    except (ValueError,TypeError,KeyError,AttributeError,OverflowError,RecursionError,UnicodeError,OSError):
        raise ProjectedLaunchRejected('projected_target_invalid') from None

def target_main():
    """Fixed readiness-only target: original owner start, close, caller release.

    No listener, model, finite admission or automatic recovery is enabled. Errors
    propagate to the dedicated entrypoint which exits, never retries or force-clears
    native ownership. If startup/close effects are unknown, the result is failure.
    """
    record,expected,instance=receive(dict(os.environ))
    import gateway_profile_lease as lease
    import gateway_store_startup as startup
    held=lease.reserve_profile(Path(handoff.TARGET),expected)
    owner=startup.NativeStoreStartup(held,expected,record.state,instance_id=instance,
        response_expected=record.response,prepared_layout=True,retained_profile=record.retained)
    opened=owner.start()
    epoch=owner.expectation.epoch  # Original owner exposes expectation only while verified.
    owner.close()
    require(owner.status()['callerLeaseMayBeReleased'] is True,'projected_owner_not_closeable')
    held.finish()
    return {'state':'PROJECTED_RETAINED_OWNER_CLOSED','pid':os.getpid(),
            'epoch':epoch,'completedChecks':opened['completedChecks'],
            'serviceStarted':False,'runtimeAdmissionAuthorized':False,
            'finiteWorkExecuted':False,'fullD3BAccepted':False}
