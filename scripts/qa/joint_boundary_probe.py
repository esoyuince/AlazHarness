"""Test-only probe AFTER both kernel boundaries, then exec original Gateway.

Only controller-created localhost and synthetic file canaries are tested.
No inherited sockets, real provider secrets or external destinations are used.
"""
from pathlib import Path
import argparse
import ctypes
import errno
import hashlib
import json
import os
import socket
import subprocess
import sys


def denied_open(path):
    try:
        fd = os.open(path, os.O_RDONLY | os.O_CLOEXEC)
    except OSError as error:
        return error.errno in (errno.EACCES, errno.EPERM)
    else:
        os.close(fd)
        return False


def blocked_host(port):
    try:
        connection = socket.create_connection(('127.0.0.1', port), timeout=1)
    except OSError as error:
        return error.errno in (errno.ECONNREFUSED, errno.ENETUNREACH,
                              errno.EHOSTUNREACH, errno.EACCES, errno.EPERM)
    else:
        connection.close()
        return False


def child(config):
    return {'protected_denied':denied_open(config['protected']),
            'host_tcp_denied':blocked_host(config['hostPort']),
            'namespace_inherited':os.readlink('/proc/self/ns/net') == config['childNamespace']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', required=True, type=Path)
    parser.add_argument('--receipt', type=Path)
    parser.add_argument('--child', action='store_true')
    parser.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    config = json.loads(args.config.read_text())
    if args.child:
        result = child(config)
        print(json.dumps(result));return 0 if all(result.values()) else 1
    command = args.command[1:] if args.command[:1] == ['--'] else args.command
    if not command or not args.receipt or args.receipt.exists():
        raise ValueError('fresh_probe_receipt_and_original_command_required')
    namespace = os.readlink('/proc/self/ns/net')
    flags = {row.split(':',1)[0]:row.split(':',1)[1].strip()
             for row in Path('/proc/self/status').read_text().splitlines() if ':' in row}
    checks = {'separate_netns':namespace != config['hostNamespace'],
        'no_new_privs':flags.get('NoNewPrivs') == '1',
        'seccomp_active':flags.get('Seccomp') == '2',
        'capabilities_zero':all(int(flags[k],16)==0 for k in
            ('CapInh','CapPrm','CapEff','CapBnd','CapAmb')),
        'protected_open_denied':denied_open(config['protected']),
        'host_tcp_denied':blocked_host(config['hostPort']),
        'own_environ_denied':denied_open('/proc/self/environ')}
    alias = args.receipt.with_name('probe-protected-alias')
    alias.symlink_to(config['protected'])
    checks['protected_alias_denied'] = denied_open(str(alias))
    alias.unlink()
    libc = ctypes.CDLL(None, use_errno=True)
    ctypes.set_errno(0)
    rc = libc.setns(-1, 0)
    checks['namespace_reentry_denied'] = rc == -1 and ctypes.get_errno() == errno.EPERM
    # Raw libc socket/connect verifies the outcome outside Python's socket API.
    class Address(ctypes.Structure):
        _fields_=[('family',ctypes.c_ushort),('port',ctypes.c_ushort),
                  ('address',ctypes.c_ubyte*4),('zero',ctypes.c_ubyte*8)]
    address=Address(socket.AF_INET,socket.htons(config['hostPort']),
                    (ctypes.c_ubyte*4)(127,0,0,1),(ctypes.c_ubyte*8)())
    fd=libc.socket(socket.AF_INET,socket.SOCK_STREAM,0)
    if fd<0:raise RuntimeError('raw_probe_socket_unavailable')
    try:
        ctypes.set_errno(0);rc=libc.connect(fd,ctypes.byref(address),ctypes.sizeof(address))
        checks['raw_host_tcp_denied']=rc==-1 and ctypes.get_errno() in (errno.ECONNREFUSED,errno.ENETUNREACH,errno.EHOSTUNREACH,errno.EPERM,errno.EACCES)
    finally:libc.close(fd)
    with socket.socket() as server:
        server.bind(('127.0.0.1',0));server.listen(1)
        with socket.create_connection(server.getsockname(),timeout=1) as client:
            accepted,_=server.accept()
            with accepted:
                client.sendall(b'joint-local');checks['private_loopback_works']=accepted.recv(20)==b'joint-local'
    # This config has synthetic paths/ports, never credential contents.
    next_config=args.receipt.with_name('probe-child.json')
    next_config.write_text(json.dumps({**config,'childNamespace':namespace}))
    result=subprocess.run([sys.executable,'-I','-B',str(Path(__file__).resolve()),
            '--config',str(next_config),'--child'],capture_output=True,text=True,timeout=12)
    sub=json.loads(result.stdout) if result.returncode==0 else {}
    checks.update({'exec_child_'+k:v for k,v in sub.items()})
    checks['exec_child_complete']=result.returncode==0 and len(sub)==3
    receipt={'version':1,'result':'PASS' if all(checks.values()) else 'FAIL',
        'pid':os.getpid(),'checks':checks,'networkNamespace':namespace,
        'protectedReadOnlyProbed':True,'realModelCalls':0,'fullD3B':False,
        'scope':'both layers before exec original Gateway; synthetic canaries only'}
    args.receipt.write_text(json.dumps(receipt,indent=2)+'\n')
    if receipt['result']!='PASS':return 3
    os.execv(command[0],command)


if __name__=='__main__':raise SystemExit(main())
