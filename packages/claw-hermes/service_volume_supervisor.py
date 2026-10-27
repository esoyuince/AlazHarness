"""Explicit service-lifetime worker on the original volume lease/fence owner.

This opt-in sibling keeps the original begin/attach/stop/finish and every kernel
identity check. The original finite/readiness worker and its 120-second deadline
remain unchanged. A separately requested fixed service child uses this SAME
owner. Retirement requires the same child's complete final/exit/EOF proof and
the original worker's successful normal stop, never a caller-supplied receipt.
"""
from pathlib import Path
import json
import os
import subprocess
import sys

import state_volume_supervisor as volume
from state_volume_supervisor import ROOT, trusted, require, read_line


class ServiceVolumeSupervisor(volume.VolumeSupervisor):
    @classmethod
    def begin(cls, pin, cgroup_parent, mountpoint):
        require(cls is ServiceVolumeSupervisor, 'service_volume_exact_owner')
        instance = super().begin(pin, cgroup_parent, mountpoint)
        instance._service_child = None
        instance._service_child_anchor = None
        return instance

    def launch_service(self, ipc, filesystem, record, *, scratch, instance_id,
                       service_id, timeout=30):
        from gateway_supervised_service import launch_service
        return launch_service(self, ipc, filesystem, record, scratch=scratch,
                              instance_id=instance_id, service_id=service_id,
                              timeout=timeout)

    def observe_service(self, *, timeout=0):
        from gateway_supervised_service import observe_service
        return observe_service(self, timeout=timeout)

    def task_service(self, http, *, timeout=30):
        from gateway_supervised_service import task_service
        return task_service(self, http, timeout=timeout)

    def close_service(self, *, timeout=30):
        from gateway_supervised_service import close_service
        return close_service(self, timeout=timeout)

    def stop(self):
        if getattr(self, '_service_child', None) is None:
            require(getattr(self, '_service_child_anchor', None) is None,
                    'service_volume_child_slot_changed')
            return super().stop()
        from gateway_supervised_service import stop_service_volume
        return stop_service_volume(self)

    def finish(self):
        if getattr(self, '_service_child', None) is None:
            require(getattr(self, '_service_child_anchor', None) is None,
                    'service_volume_child_slot_changed')
            return super().finish()
        from gateway_supervised_service import finish_service_volume
        return finish_service_volume(self)

    def start(self):
        require(type(self) is ServiceVolumeSupervisor, 'service_volume_exact_owner')
        self._owned()
        require(self.stage == 'ATTACHED' and self.worker is None, 'supervisor_start_once')
        require(trusted(self.target, directory=True) == self.target_id
                and not any(self.target.iterdir()), 'supervisor_mountpoint_changed')
        for name in ('packages/claw-hermes/state_volume_supervisor.py',
                     'packages/claw-hermes/service_volume_supervisor.py',
                     'packages/claw-hermes/state_image_lease.py', 'scripts/run_service_volume_worker.py'):
            trusted(ROOT / name)
        python = Path(sys.executable).resolve(); trusted(python)
        self.stage = 'STARTING'; self.spawn_uncertain = True
        self.worker = subprocess.Popen([str(python), '-I', '-B', str(ROOT/'scripts/run_service_volume_worker.py')],
            cwd='/', env={'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8'}, stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=0, close_fds=True)
        self.spawn_uncertain = False
        message = {'version': 2, 'token': self.token, 'controllerPid': self.who[0],
                   'scope': str(self.scope), 'scopeIdentity': list(self.scope_id),
                   'mountpoint': str(self.target), 'targetIdentity': list(self.target_id),
                   'loopNumber': self.loop_number, 'imageDevice': self.pin.device,
                   'imageInode': self.pin.inode}
        self.worker.stdin.write((json.dumps(message)+'\n').encode()); self.worker.stdin.flush()
        ready = read_line(self.worker)
        require(ready.get('state') == 'MOUNTED' and ready.get('pid') == self.worker.pid
                and ready.get('token') == self.token and ready.get('loopNumber') == self.loop_number
                and ready.get('lifetime') == 'owned-service',
                'supervisor_ready_mismatch')
        require(os.readlink('/proc/'+str(self.worker.pid)+'/ns/mnt') == ready['mountNamespace']
                and ready['mountNamespace'] != os.readlink('/proc/self/ns/mnt'), 'supervisor_worker_not_private')
        require(str(self.worker.pid) in (self.scope/'cgroup.procs').read_text().split(),
                'supervisor_worker_outside_scope')
        require(not os.path.ismount(self.target), 'supervisor_mount_leaked_to_host')
        self.stage = 'RUNNING'
        return ready
