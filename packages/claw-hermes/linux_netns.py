"""D3B1 opt-in rootless network boundary. NOT a complete host sandbox.

Invoke once in a fresh, single-threaded Linux process before Gateway imports.
Uses a new user/network namespace, loopback only, zero capabilities and an
inherited seccomp filter. Host UID, filesystem and path-based Unix sockets
remain shared; credential/filesystem separation is a distinct open gate.
"""
from __future__ import annotations
import ctypes
import ctypes.util
import errno
import os
from pathlib import Path
import platform
import socket
import stat
import struct
import threading

VERSION=1
# sendmsg stays available for asyncio vectored writes. Descriptor RECEIVING
# stays blocked via recvmsg/recvmmsg and pidfd_getfd; inherited sockets close.
DENIED_SYSCALLS=("setns","unshare","mount","umount2","pivot_root","chroot",
    "ptrace","process_vm_readv","process_vm_writev","pidfd_getfd",
    "bpf","userfaultfd","open_by_handle_at","name_to_handle_at",
    "fsopen","fsconfig","fsmount","move_mount","open_tree","mount_setattr",
    "recvmsg","recvmmsg")
NEW_NAMESPACE_FLAGS=(0x00020000,0x02000000,0x04000000,0x08000000,
                     0x10000000,0x20000000,0x40000000)
ALLOW=0x7fff0000
ERRNO=0x00050000

class NetworkBoundaryError(RuntimeError):
    pass

def require(condition,reason):
    if not condition:raise NetworkBoundaryError(reason)

def status():
    rows=Path('/proc/self/status').read_text().splitlines()
    keys=('NoNewPrivs','Seccomp','CapInh','CapPrm','CapEff','CapBnd','CapAmb')
    values={line.split(':',1)[0]:line.split(':',1)[1].strip()
            for line in rows if line.split(':',1)[0] in keys}
    return {'pid':os.getpid(),'uid':os.getuid(),'gid':os.getgid(),
            'netNamespace':os.readlink('/proc/self/ns/net'),
            'userNamespace':os.readlink('/proc/self/ns/user'),**values}

def _check_rc(value,label):
    if value<0:raise NetworkBoundaryError(label+':'+str(ctypes.get_errno()))

def _load_seccomp():
    name=ctypes.util.find_library('seccomp')
    require(bool(name),'libseccomp_required')
    lib=ctypes.CDLL(name,use_errno=True)
    lib.seccomp_init.argtypes=[ctypes.c_uint32];lib.seccomp_init.restype=ctypes.c_void_p
    lib.seccomp_release.argtypes=[ctypes.c_void_p]
    lib.seccomp_load.argtypes=[ctypes.c_void_p];lib.seccomp_load.restype=ctypes.c_int
    lib.seccomp_syscall_resolve_name.argtypes=[ctypes.c_char_p]
    lib.seccomp_syscall_resolve_name.restype=ctypes.c_int
    return lib

class ArgCmp(ctypes.Structure):
    _fields_=[('arg',ctypes.c_uint),('op',ctypes.c_uint),
              ('datum_a',ctypes.c_uint64),('datum_b',ctypes.c_uint64)]

def _filter(lib):
    lib.seccomp_rule_add_array.argtypes=[ctypes.c_void_p,ctypes.c_uint32,
                           ctypes.c_int,ctypes.c_uint,ctypes.POINTER(ArgCmp)]
    lib.seccomp_rule_add_array.restype=ctypes.c_int
    ctx=lib.seccomp_init(ALLOW)
    require(bool(ctx),'seccomp_init_failed')
    def rule(name,code=errno.EPERM,comparison=None):
        nr=lib.seccomp_syscall_resolve_name(name.encode('ascii'))
        require(nr>=0,'seccomp_syscall_missing:'+name)
        values=(ArgCmp*1)(comparison) if comparison is not None else None
        rc=lib.seccomp_rule_add_array(ctx,ERRNO|code,nr,1 if values is not None else 0,values)
        require(rc==0,'seccomp_rule_failed:'+name+':'+str(rc))
    try:
        for name in DENIED_SYSCALLS:rule(name)
        # glibc and Node can fall back to ordinary clone without new namespaces.
        for name in ('clone3','io_uring_setup','io_uring_enter','io_uring_register'):
            rule(name,errno.ENOSYS)
        for mask in NEW_NAMESPACE_FLAGS:
            rule('clone',comparison=ArgCmp(0,7,mask,mask)) # MASKED_EQ
        # Native x86_64 only. Allow AF_UNIX=1, INET=2, INET6=10; block
        # AF_VSOCK/NETLINK/PACKET and all other address families.
        for domain in (0,3,4,5,6,7,8,9):
            rule('socket',comparison=ArgCmp(0,4,domain,0)) # EQ
        rule('socket',comparison=ArgCmp(0,6,10,0)) # GT
        rule('socket',comparison=ArgCmp(1,7,15,3)) # SOCK_RAW with flags masked
        rule('socketpair',comparison=ArgCmp(0,1,1,0)) # NE AF_UNIX
        rc=lib.seccomp_load(ctx)
        require(rc==0,'seccomp_load_failed:'+str(rc))
    finally:lib.seccomp_release(ctx)

class CapHeader(ctypes.Structure):
    _fields_=[('version',ctypes.c_uint32),('pid',ctypes.c_int)]
class CapData(ctypes.Structure):
    _fields_=[('effective',ctypes.c_uint32),('permitted',ctypes.c_uint32),
              ('inheritable',ctypes.c_uint32)]

def enter():
    """Irreversible for this process. Caller MUST exit on any failure.

    This is a launch primitive, not authorization to invoke an arbitrary task.
    No unconfined fallback is provided. Filesystem and Unix IPC are not isolated.
    """
    require(platform.system()=='Linux' and platform.machine()=='x86_64',
            'linux_x86_64_required')
    require(os.getuid()!=0 and os.getuid()==os.geteuid() and os.getgid()==os.getegid(),
            'unprivileged_same_identity_required')
    require(threading.active_count()==1 and len(list(Path('/proc/self/task').iterdir()))==1,
            'fresh_single_thread_required')
    before=status()
    require(before.get('NoNewPrivs')=='0','already_restricted_process')
    lib=_load_seccomp()
    libc=ctypes.CDLL(None,use_errno=True)
    libc.prctl.restype=ctypes.c_int
    libc.unshare.argtypes=[ctypes.c_int];libc.unshare.restype=ctypes.c_int
    libc.capset.argtypes=[ctypes.POINTER(CapHeader),ctypes.POINTER(CapData)]
    libc.capset.restype=ctypes.c_int
    # Never carry an already connected socket across network namespaces.
    for fd in (0,1,2):
        try:require(not stat.S_ISSOCK(os.fstat(fd).st_mode),'socket_stdio_refused')
        except OSError:pass
    for name in os.listdir('/proc/self/fd'):
        fd=int(name)
        if fd>2:
            try:os.close(fd)
            except OSError:pass
    uid,gid=os.getuid(),os.getgid()
    _check_rc(libc.unshare(0x10000000|0x40000000),'unshare_failed')
    Path('/proc/self/setgroups').write_text('deny')
    Path('/proc/self/uid_map').write_text(f'{uid} {uid} 1')
    Path('/proc/self/gid_map').write_text(f'{gid} {gid} 1')
    # Bring up only the namespace's own loopback, before dropping capabilities.
    import fcntl
    with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as ctl:
        req=struct.pack('16sH',b'lo',0)
        flags=struct.unpack('16sH',fcntl.ioctl(ctl.fileno(),0x8913,req))[1]
        fcntl.ioctl(ctl.fileno(),0x8914,struct.pack('16sH',b'lo',flags|1))
    _check_rc(libc.prctl(38,1,0,0,0),'no_new_privs_failed')
    for cap in range(64):
        valid=libc.prctl(23,cap,0,0,0)
        if valid<0 and ctypes.get_errno()==errno.EINVAL:break
        _check_rc(valid,'capability_read_failed')
        _check_rc(libc.prctl(24,cap,0,0,0),'capability_drop_failed')
    header=CapHeader(0x20080522,0);caps=(CapData*2)()
    _check_rc(libc.capset(ctypes.byref(header),caps),'capset_failed')
    _filter(lib)
    after=status()
    require(after['netNamespace']!=before['netNamespace'] and
            after['userNamespace']!=before['userNamespace'],'namespace_not_changed')
    require(after['NoNewPrivs']=='1' and after['Seccomp']=='2','filter_not_active')
    require(all(int(after[k],16)==0 for k in
                ('CapInh','CapPrm','CapEff','CapBnd','CapAmb')),'capabilities_remain')
    return {'version':VERSION,'mode':'linux_netns_loopback_only',
            'before':before,'after':after,'inheritedRestrictions':True,
            'hostFilesystemIsolated':False,'separateHostUid':False,
            'unixSocketAuthorityIsolated':False,'completeD3BAcceptance':False}
