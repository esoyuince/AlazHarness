"""Fixed trusted mount worker. No arbitrary command/workload dispatch.

The root supervisor owns the image lease; this worker joins its dedicated
cgroup, creates a private mount namespace and holds only that ext4 mount.
Gateway admission/projection is NOT implemented by this worker.
"""
from __future__ import annotations
import ctypes
import json
import os
from pathlib import Path
import re
import select
import signal
import sys
import time
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'packages/claw-hermes'))
import state_volume_supervisor as supervisor


def line(seconds=120):
    require = supervisor.require
    deadline = time.monotonic()+seconds; data = bytearray()
    while len(data) < 16384:
        left = deadline-time.monotonic()
        require(left > 0 and select.select([0], [], [], left)[0], 'volume_worker_input_timeout')
        b = os.read(0, 1)
        require(b, 'volume_worker_controller_gone')
        data.extend(b)
        if b == b'\n':return data.decode('utf-8').strip()
    raise supervisor.SupervisorRejected('volume_worker_input_bound')


def emit(value, config):
    print(json.dumps({'pid': os.getpid(), 'token': config['token'], **value}), flush=True)


def main():
    supervisor.actor()
    value = json.loads(line(15))
    require = supervisor.require
    require(type(value) is dict and set(value) == {'version','token','controllerPid','scope',
        'scopeIdentity','mountpoint','targetIdentity','loopNumber','imageDevice','imageInode'},
        'volume_worker_contract')
    require(value['version'] == 1 and type(value['controllerPid']) is int
            and value['controllerPid'] == os.getppid()
            and re.fullmatch(r'[a-f0-9]{32}', value['token']) is not None, 'volume_worker_controller')
    lib = ctypes.CDLL(None, use_errno=True)
    lib.prctl.argtypes = [ctypes.c_int, ctypes.c_ulong, ctypes.c_ulong, ctypes.c_ulong, ctypes.c_ulong]
    lib.prctl.restype = ctypes.c_int
    require(lib.prctl(1, signal.SIGKILL, 0, 0, 0) == 0, 'volume_worker_parent_death')
    require(os.getppid() == value['controllerPid'], 'volume_worker_parent_changed')
    scope, target = Path(value['scope']), Path(value['mountpoint'])
    require(scope.is_relative_to('/sys/fs/cgroup') and scope.name == 'volume-'+value['token']
            and supervisor.trusted(scope,directory=True) == tuple(value['scopeIdentity'])
            and supervisor.fs_type(scope) == supervisor.CGROUP2_MAGIC, 'volume_worker_scope')
    require(supervisor.trusted(target,directory=True) == tuple(value['targetIdentity'])
            and not os.path.ismount(target) and not any(target.iterdir()), 'volume_worker_target')
    with (scope/'cgroup.procs').open('w') as stream:stream.write(str(os.getpid()))
    relative = str(scope.relative_to('/sys/fs/cgroup'))
    require('0::/'+relative in Path('/proc/self/cgroup').read_text().splitlines(), 'volume_worker_membership')
    before = os.readlink('/proc/self/ns/mnt')
    lib.unshare.argtypes = [ctypes.c_int];lib.unshare.restype = ctypes.c_int
    lib.mount.argtypes = [ctypes.c_char_p,ctypes.c_char_p,ctypes.c_char_p,ctypes.c_ulong,ctypes.c_char_p]
    lib.mount.restype = ctypes.c_int
    lib.umount2.argtypes = [ctypes.c_char_p,ctypes.c_int];lib.umount2.restype = ctypes.c_int
    require(lib.unshare(0x00020000) == 0, 'volume_worker_namespace')
    require(lib.mount(None,b'/',None,0x4000|0x40000,None) == 0, 'volume_worker_propagation')
    after = os.readlink('/proc/self/ns/mnt')
    require(before != after, 'volume_worker_namespace_unchanged')
    fd = supervisor.open_loop(value['loopNumber'])
    try:
        status = supervisor.loop_status(fd)
        require(status is not None and (status['device'],status['inode']) ==
                (value['imageDevice'],value['imageInode']) and status['flags'] == supervisor.AUTOCLEAR
                and status['offset'] == status['sizeLimit'] == status['encryption'] == 0,
                'volume_worker_loop_identity')
        device = '/dev/loop'+str(value['loopNumber'])
        require(lib.mount(os.fsencode(device),os.fsencode(target),b'ext4',2|4|8,b'errors=remount-ro') == 0,
                'volume_worker_mount:'+str(ctypes.get_errno()))
        require(os.path.ismount(target) and os.stat(target).st_dev == os.makedev(7,value['loopNumber'])
                and supervisor.fs_type(target) == 0xEF53, 'volume_worker_mounted_identity')
        emit({'state':'MOUNTED','loopNumber':value['loopNumber'],'mountNamespace':after,
              'filesystem':'ext4','gatewayStarted':False},value)
        while True:
            require(line() == 'STOP '+value['token'], 'volume_worker_stop_contract')
            peers = (scope/'cgroup.procs').read_text().split()
            nested = any(p.is_dir() for p in scope.iterdir())
            if set(peers) != {str(os.getpid())} or nested:
                emit({'state':'BUSY','reason':'volume_users_remain'},value)
                continue
            if lib.umount2(os.fsencode(target),0) != 0:
                emit({'state':'BUSY','reason':'unmount_refused','errno':ctypes.get_errno()},value)
                continue
            require(not os.path.ismount(target) and supervisor.trusted(target,directory=True)
                    == tuple(value['targetIdentity']), 'volume_worker_unmount_unverified')
            emit({'state':'UNMOUNTED'},value)
            return 0
    finally:
        os.close(fd)
    # No lazy detach/forced umount. Process death tears down only its private
    # namespace; parent still must prove cgroup empty and loop gone.


if __name__ == '__main__':
    try:raise SystemExit(main())
    except Exception as exc:
        print(json.dumps({'result':'REFUSED','type':type(exc).__name__,
                          'reason':str(exc)[:160]}),file=sys.stderr,flush=True)
        raise SystemExit(2)
