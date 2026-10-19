"""Strict opt-in host UID boundary for a broker and one Gateway socket.

This does not create accounts or switch identities. Trusted launch controller
must provision a separate real host UID and file geometry before use.
The old same-UID broker contract is unchanged and NOT upgraded by this module.
"""
from __future__ import annotations
import os
import re
from pathlib import Path, PurePosixPath
import socket
import stat
import struct

VERSION=1
POLICY_FIELDS={'version','enabled','gatewayUid','brokerUid','socketGroupGid','hostUserNamespace'}
SOCKET_MODE=0o660
SOCKET_DIR_MODE=0o710
BUDGET_DIR_MODE=0o700
BUDGET_FILE_MODE=0o600

class PrincipalRejected(ValueError):
    pass

def require(test,code):
    if not test:
        raise PrincipalRejected(code)

def policy(value):
    require(type(value) is dict and set(value)==POLICY_FIELDS,'principal_policy_fields')
    require(type(value['version']) is int and value['version']==VERSION
            and value['enabled'] is True,'principal_opt_in_required')
    for key in ('gatewayUid','brokerUid','socketGroupGid'):
        value_part=value[key]
        require(type(value_part) is int and 1<=value_part<=2**31-2,
                'principal_identity_invalid')
    require(value['gatewayUid'] != value['brokerUid'],'principal_same_host_uid_refused')
    namespace=value['hostUserNamespace']
    require(type(namespace) is str and
            re.fullmatch(r'user:\[[0-9]{1,20}\]',namespace) is not None,
            'principal_host_user_namespace_required')
    return dict(value)

def canonical(path):
    require(type(path) is str and 1<=len(path.encode('utf-8'))<=4096 and '\x00' not in path,
            'principal_path_invalid')
    p=PurePosixPath(path)
    require(p.is_absolute() and str(p)==path and '..' not in p.parts
            and not path.startswith('//'), 'principal_path_not_canonical')
    return p

def regular(path,kind,owner,group,mode):
    p=Path(canonical(path))
    require(not any(part.is_symlink() for part in (p,*p.parents)),
            'principal_symlink_refused')
    try:
        s=p.lstat()
    except (OSError,ValueError):
        raise PrincipalRejected('principal_path_unavailable') from None
    required={'dir':stat.S_ISDIR,'file':stat.S_ISREG,'socket':stat.S_ISSOCK}[kind]
    require(required(s.st_mode) and s.st_uid==owner and s.st_gid==group
            and stat.S_IMODE(s.st_mode)==mode and
            (kind=='dir' or s.st_nlink==1), 'principal_path_owner_mode')
    return (s.st_dev,s.st_ino,s.st_uid,s.st_gid,stat.S_IMODE(s.st_mode))

def broker_identity(value):
    v=policy(value)
    require(os.name=='posix' and hasattr(socket,'SO_PEERCRED'),
            'principal_linux_peercred_required')
    require(os.getuid()==v['brokerUid'] and os.geteuid()==v['brokerUid']
            and os.getgid()==v['socketGroupGid']
            and os.getegid()==v['socketGroupGid']
            and not os.getgroups(),'principal_wrong_broker_process')
    # Prevent a fresh user namespace from mapping host UID1000 to the
    # visually different UID65534 and masquerading as a separate owner.
    # The trusted host controller must pin this INITIAL namespace value.
    require(os.readlink('/proc/self/ns/user')==v['hostUserNamespace'],
            'principal_broker_userns_changed')
    return True

def gateway_identity(value):
    v=policy(value)
    require(os.name=='posix' and os.getuid()==v['gatewayUid']
            and os.geteuid()==v['gatewayUid']
            and os.getgid()==v['socketGroupGid']
            and os.getegid()==v['socketGroupGid'],
            'principal_wrong_gateway_process')
    return True

def budget_identity(value,directory):
    v=policy(value)
    p=canonical(directory)
    info=regular(str(p),'dir',v['brokerUid'],v['socketGroupGid'],
                 BUDGET_DIR_MODE)
    db=regular(str(p/'budget.sqlite3'),'file',v['brokerUid'],
               v['socketGroupGid'],BUDGET_FILE_MODE)
    return {'directory':info,'database':db}

def socket_identity(value,socket_path):
    v=policy(value)
    p=canonical(socket_path)
    require(len(str(p).encode())<=100 and p.name=='egress.sock',
            'principal_socket_path')
    parent=regular(str(p.parent),'dir',v['brokerUid'],v['socketGroupGid'],
                   SOCKET_DIR_MODE)
    link=regular(str(p),'socket',v['brokerUid'],v['socketGroupGid'],
                 SOCKET_MODE)
    return {'directory':parent,'socket':link}

def socket_peer(sock,value,*,role):
    v=policy(value)
    require(role in ('broker','gateway') and
            os.name=='posix' and hasattr(socket,'SO_PEERCRED'),
            'principal_peer_contract')
    try:
        pid,uid,gid=struct.unpack('3i',sock.getsockopt(
            socket.SOL_SOCKET,socket.SO_PEERCRED,12))
    except (OSError,ValueError,struct.error):
        raise PrincipalRejected('principal_peer_unavailable') from None
    expected=v['gatewayUid'] if role=='broker' else v['brokerUid']
    require(pid>0 and uid==expected and gid==v['socketGroupGid'],
            'principal_peer_mismatch')
    return {'pid':pid,'uid':uid,'gid':gid}

def pinned_socket(value,path,expected):
    current=socket_identity(value,path)
    require(type(expected) is dict and current==expected,
            'principal_socket_rebound')
    return current
