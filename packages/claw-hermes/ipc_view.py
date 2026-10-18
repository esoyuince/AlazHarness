"""Opt-in mount projection for Linux pathname IPC, before privilege drop.

Only declared filesystem roots, protected regular-file canaries, the current
process's proc view, and ONE pinned broker socket are mounted. New private
runtime sockets are allowed. Exported directory trees must be trusted and
must contain no pre-existing sockets/devices/FIFOs. Not independent broker
budget authority or protection against privileged host mutation/kernel bugs.
"""
from __future__ import annotations
import ctypes
import errno
import os
from pathlib import Path, PurePosixPath
import stat
from credential_guard import validate_policy

BIND=4096; REMOUNT=32; RDONLY=1; NOSUID=2; NODEV=4; NOEXEC=8
REC=16384; PRIVATE=1<<18; NEWNS=0x00020000; DETACH=2
FIELDS={'version','mode','root','brokerSocket'}
MAX_ENTRIES=200000

class IPCViewRejected(RuntimeError):
    pass


def require(ok,reason):
    if not ok:raise IPCViewRejected(reason)


def canonical(value):
    require(type(value) is str and 1<=len(value.encode())<=4096 and '\x00' not in value,
            'ipc_path_type')
    p=PurePosixPath(value)
    require(p.is_absolute() and str(p)==value and '..' not in p.parts and not value.startswith('//'),
            'ipc_path_not_canonical')
    return value


def validate(value,filesystem):
    require(type(value) is dict and set(value)==FIELDS,'ipc_contract_fields')
    require(type(value['version']) is int and value['version']==1 and
            value['mode']=='projected_root','ipc_mode')
    fs=validate_policy(filesystem)
    root=canonical(value['root']);sock=canonical(value['brokerSocket'])
    require(root.startswith('/tmp/alaz-ipc-') and len(PurePosixPath(root).parts)==3,
            'ipc_owned_tmp_anchor_required')
    require(len(sock.encode())<=100 and len(PurePosixPath(sock).parts)>=4 and
            not any(PurePosixPath(sock).is_relative_to(x) for x in ('/proc','/sys','/dev','/usr','/etc')),
            'ipc_broker_path')
    exports=fs['readonly']+fs['writable']+fs['protected']
    require(len(exports)==len(set(exports)),'ipc_duplicate_export')
    for i,left in enumerate(exports):
        for right in exports[i+1:]:
            require(not PurePosixPath(left).is_relative_to(right) and
                    not PurePosixPath(right).is_relative_to(left),'ipc_overlapping_exports')
    for path in exports:
        require(not PurePosixPath(path).is_relative_to(root) and
                not PurePosixPath(root).is_relative_to(path),'ipc_root_overlap')
        require(not PurePosixPath(sock).is_relative_to(path) and
                not PurePosixPath(path).is_relative_to(sock),'ipc_socket_overlap')
    return {**value},fs


def identity(path):
    st=os.stat(path,follow_symlinks=False)
    return (st.st_dev,st.st_ino,stat.S_IFMT(st.st_mode),st.st_uid,st.st_gid)


def _regular_path(path):
    p=Path(path)
    require(p.exists() and not p.is_symlink() and str(p.resolve())==path,'ipc_path_changed')
    return p


def inspect_tree(root):
    """Bounded, no symlink following, no mount traversal, reject ambient IPC."""
    count=0;dev=Path(root).stat().st_dev;hidden=[]
    def scan_error(error):
        raise IPCViewRejected('ipc_tree_scan_incomplete') from None
    for current,dirs,names in os.walk(root,followlinks=False,onerror=scan_error):
        for name in list(dirs)+names:
            count+=1
            require(count<=MAX_ENTRIES,'ipc_tree_scan_limit')
            p=Path(current)/name;st=p.lstat()
            if st.st_dev!=dev or stat.S_ISDIR(st.st_mode) and os.path.ismount(p):
                require(stat.S_ISDIR(st.st_mode),'ipc_file_submount_unsupported')
                if name in dirs:dirs.remove(name)
                hidden.append(str(p));continue
            require(stat.S_ISREG(st.st_mode) or stat.S_ISDIR(st.st_mode) or stat.S_ISLNK(st.st_mode),
                    'ipc_special_file_in_export')
    return count,hidden


def prepare(value,filesystem):
    ipc,fs=validate(value,filesystem)
    root=_regular_path(ipc['root']);info=root.stat()
    require(root.is_dir() and info.st_uid==os.getuid() and stat.S_IMODE(info.st_mode)==0o700
            and not any(root.iterdir()),'ipc_anchor_not_owned_empty')
    sock=_regular_path(ipc['brokerSocket']);st=sock.stat();parent=sock.parent.stat()
    require(stat.S_ISSOCK(st.st_mode) and st.st_uid==os.getuid() and st.st_nlink==1
            and stat.S_IMODE(st.st_mode)&0o077==0 and parent.st_uid==os.getuid()
            and stat.S_IMODE(parent.st_mode)&0o077==0,'ipc_broker_identity_or_permissions')
    objects={};count=0;hidden=[]
    for path in fs['readonly']+fs['writable']+fs['protected']:
        p=_regular_path(path);st=p.stat()
        if p.is_dir():
            entries,masks=inspect_tree(p);count+=entries;hidden.extend(masks)
        else:require(stat.S_ISREG(st.st_mode) or path in ('/dev/null','/dev/urandom')
                     and stat.S_ISCHR(st.st_mode),'ipc_special_export')
        require(count<=MAX_ENTRIES,'ipc_total_scan_limit')
        objects[path]=identity(path)
    return {'ipc':ipc,'filesystem':fs,'objects':objects,'anchorIdentity':identity(root),
            'socketIdentity':identity(sock),'scannedEntries':count,'hiddenSubmounts':hidden}


def project(plan):
    """Only called after user+network namespaces, while mount capabilities exist."""
    ipc,fs=validate(plan['ipc'],plan['filesystem']);root=Path(ipc['root'])
    require(identity(root)==tuple(plan['anchorIdentity']) and not any(root.iterdir()),'ipc_anchor_changed')
    require(identity(ipc['brokerSocket'])==tuple(plan['socketIdentity']),'ipc_broker_changed')
    for path,expected in plan['objects'].items():
        require(identity(path)[:3]==tuple(expected)[:3] and str(Path(path).resolve())==path,'ipc_export_changed')
    libc=ctypes.CDLL(None,use_errno=True)
    libc.mount.argtypes=[ctypes.c_char_p,ctypes.c_char_p,ctypes.c_char_p,ctypes.c_ulong,ctypes.c_char_p]
    libc.mount.restype=ctypes.c_int;libc.unshare.argtypes=[ctypes.c_int]
    def check(rc,where):
        if rc<0:raise IPCViewRejected(where+':'+str(ctypes.get_errno()))
    def mount(src,dest,kind=None,flags=0,data=None):
        check(libc.mount(os.fsencode(src) if src else None,os.fsencode(dest),
                        kind.encode() if kind else None,flags,data.encode() if data else None),'ipc_mount')
    before=os.readlink('/proc/self/ns/mnt');cwd=os.getcwd();pid=os.getpid()
    check(libc.unshare(NEWNS),'ipc_unshare_mount')
    mount(None,'/',flags=REC|PRIVATE)
    mount('tmpfs',root,'tmpfs',NOSUID|NODEV,'size=16m,mode=755')
    mount_ids=[]
    def bind(source,*,write=False,device=False):
        target=root/str(source).lstrip('/')
        target.parent.mkdir(parents=True,exist_ok=True)
        if Path(source).is_dir():target.mkdir(exist_ok=True)
        else:target.touch(exist_ok=False)
        try:mount(str(source),target,flags=BIND|(REC if Path(source).is_dir() else 0))
        except IPCViewRejected as exc:raise IPCViewRejected("ipc_bind_"+str(len(mount_ids))+":"+str(exc)) from None
        flags=BIND|REMOUNT|NOSUID|(0 if device else NODEV)|(0 if write else RDONLY)
        # Never clear locked source-mount flags inherited from the host.
        flags |= os.statvfs(source).f_flag & (RDONLY|NOSUID|NODEV|NOEXEC)
        if write and not device:flags|=NOEXEC
        mount(None,target,flags=flags)
        mount_ids.append(identity(target))
        require(identity(source)==identity(target),'ipc_bind_identity_changed')
    # Locked inherited submounts require recursive cloning. Every observed
    # nested mount is covered with an empty readonly mount before target exec.
    for source in fs['readonly']:bind(source,device=source=='/dev/urandom')
    for source in fs['writable']:bind(source,write=True,device=source=='/dev/null')
    for source in fs['protected']:bind(source)
    for hidden in plan['hiddenSubmounts']:
        target=root/hidden.lstrip('/')
        require(target.is_dir() and not target.is_symlink(),'ipc_submount_mask_missing')
        mount('tmpfs',target,'tmpfs',RDONLY|NOSUID|NODEV|NOEXEC,'size=4k,mode=000')
    bind(ipc['brokerSocket'])
    # Broker client requires a private directory even though only its socket
    # inode, never its directory contents or private bootstrap, is exported.
    (root/str(Path(ipc['brokerSocket']).parent).lstrip('/')).chmod(0o700)
    # Only the launcher's own proc subtree is visible, not other process roots.
    bind('/proc/'+str(pid));bind('/proc/stat')
    (root/'proc/self').symlink_to(str(pid))
    for alias,target in (('bin','usr/bin'),('sbin','usr/sbin'),('lib','usr/lib'),('lib64','usr/lib64')):
        if (root/target).exists() and not (root/alias).exists():(root/alias).symlink_to(target)
    if Path('/etc/localtime').is_symlink():
        target=Path('/etc/localtime').resolve()
        if (root/str(target).lstrip('/')).exists() and not (root/'etc/localtime').exists():
            (root/'etc').mkdir(exist_ok=True);(root/'etc/localtime').symlink_to(target)
    # Move root and detach ALL original host mount paths before capability drop.
    (root/'.old-root').mkdir()
    os.chdir(root)
    check(libc.syscall(ctypes.c_long(155),ctypes.c_char_p(b'.'),ctypes.c_char_p(b'.old-root')),'ipc_pivot_root')
    os.chdir('/')
    check(libc.umount2(ctypes.c_char_p(b'/.old-root'),ctypes.c_int(DETACH)),'ipc_detach_old_root')
    os.rmdir('/.old-root')
    os.chdir(cwd)
    require(os.readlink('/proc/self/ns/mnt')!=before,'ipc_mount_namespace_unchanged')
    require(identity(ipc['brokerSocket'])==tuple(plan['socketIdentity']),'ipc_socket_inode_changed')
    require(not Path('/mnt/c').exists() and not Path('/run/WSL').exists() and
            not Path('/proc/1').exists() and not Path('/.old-root').exists(),'ipc_ambient_root_visible')
    return {'version':1,'state':'projected','pid':pid,'mountNamespaceChanged':True,
        'oldRootDetached':True,'explicitHostSocketCount':1,'procView':'launching_pid_only',
        'bindCount':len(mount_ids),'scannedEntries':plan['scannedEntries'],
        'hiddenNestedMountCount':len(plan['hiddenSubmounts']),
        'filesystemRootsTrustedNotImmutable':True,'sameHostUid':True,
        'independentBrokerBudgetAuthority':False,'fullD3B':False}
