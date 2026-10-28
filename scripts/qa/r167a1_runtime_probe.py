"""Read-only inventory of existing runtime inputs in the dedicated P71C lab.

No candidate/dependency code is imported, and no Node binary, service, package
manager or model is started. This observation does not accept runtime ABI,
dependency completeness, installation, service readiness or confinement.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import platform
import stat
import sys

LAB = 'AlazHarness-D3B-P71C'
PYTHON = '/usr/bin/python3.12'
DEPENDENCIES = '/opt/alaz-f126c1a6/dependencies'
PRIOR_INSTALLATION = '/opt/alaz-r156a1'
BINARY_LIMIT = 256 * 1024 * 1024


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def stamp(info):
    return (info.st_dev, info.st_ino, info.st_mode, info.st_uid, info.st_gid,
            info.st_nlink, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def identity(info):
    return {'device': info.st_dev, 'inode': info.st_ino,
            'uid': info.st_uid, 'gid': info.st_gid,
            'mode': stat.S_IMODE(info.st_mode), 'links': info.st_nlink,
            'bytes': info.st_size, 'mtimeNs': info.st_mtime_ns,
            'ctimeNs': info.st_ctime_ns}


def observe_path(raw, *, hash_file=False, maximum=BINARY_LIMIT):
    path = Path(raw)
    result = {'requestedPath': str(path), 'exists': os.path.lexists(path)}
    if not result['exists']:
        return result
    try:
        initial = path.lstat()
        result['requestedIdentity'] = identity(initial)
        result['requestedIsSymlink'] = stat.S_ISLNK(initial.st_mode)
        # Resolve only to describe a candidate; executing a symlink is not
        # authorized by this inventory. The installer selects a canonical path.
        resolved = path.resolve(strict=True)
        result['resolvedPath'] = str(resolved)
        info = resolved.lstat()
        result['resolvedIdentity'] = identity(info)
        result['rootControlledAncestry'] = all(
            stat.S_ISDIR(p.lstat().st_mode)
            and p.lstat().st_uid == p.lstat().st_gid == 0
            and not p.lstat().st_mode & 0o022
            for p in resolved.parents)
        result['regularFile'] = stat.S_ISREG(info.st_mode)
        result['directory'] = stat.S_ISDIR(info.st_mode)
        if not hash_file:
            return result
        require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1,
                'inventory_regular_single_link_required')
        require(0 < info.st_size <= maximum, 'inventory_file_size')
        fd = os.open(resolved, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC
                     | os.O_NONBLOCK)
        try:
            before = os.fstat(fd)
            require(stamp(before) == stamp(info), 'inventory_open_identity')
            digest = hashlib.sha256()
            total = 0
            while True:
                part = os.read(fd, min(1024 * 1024, maximum + 1 - total))
                if not part:
                    break
                total += len(part)
                require(total <= maximum, 'inventory_read_bound')
                digest.update(part)
            require(total == before.st_size
                    and stamp(before) == stamp(os.fstat(fd))
                    and stamp(before) == stamp(resolved.lstat())
                    and path.resolve(strict=True) == resolved
                    and stamp(initial) == stamp(path.lstat()),
                    'inventory_file_changed')
            result.update(sha256=digest.hexdigest(), readbackStable=True)
        finally:
            os.close(fd)
    except (OSError, ValueError) as exc:
        result['observationError'] = str(exc) if isinstance(exc, ValueError) else type(exc).__name__
    return result


def inventory():
    require(os.environ.get('WSL_DISTRO_NAME') == LAB
            and Path('/etc/alaz-p71c-lab-id').read_text().strip() == LAB,
            'inventory_wrong_lab')
    require(sys.platform == 'linux' and platform.machine() == 'x86_64'
            and sys.executable == PYTHON and sys.version_info[:2] == (3, 12)
            and sys.flags.isolated == 1 and sys.dont_write_bytecode
            and not sys.flags.optimize, 'inventory_python_actor')
    require(os.getresuid() == (23001,) * 3 and os.getresgid() == (23003,) * 3,
            'inventory_ordinary_actor')
    require(not Path('/mnt/c/Windows').exists(), 'inventory_windows_mount_present')
    candidates = {'/usr/bin/node', '/usr/local/bin/node', '/opt/node/bin/node',
                  '/opt/node24/bin/node'}
    opt = list(Path('/opt').iterdir())
    require(len(opt) <= 512, 'inventory_opt_entry_bound')
    for entry in opt:
        if 'node' in entry.name.lower() and entry.is_dir():
            candidates.add(str(entry / 'bin/node'))
    require(len(candidates) <= 32, 'inventory_node_candidate_bound')
    return {'schema': 1, 'kind': 'R167A1_READ_ONLY_LAB_RUNTIME_INVENTORY',
            'result': 'OBSERVED_RUNTIME_INPUTS_ONLY', 'lab': LAB,
            'uid': list(os.getresuid()), 'gid': list(os.getresgid()),
            'groups': os.getgroups(), 'platform': sys.platform,
            'machine': platform.machine(), 'pythonVersion': sys.version,
            'pythonVersionInfo': list(sys.version_info),
            'pythonProcessExecutable': os.readlink('/proc/self/exe'),
            'python': observe_path(PYTHON, hash_file=True),
            'nodeCandidates': [observe_path(p, hash_file=True)
                               for p in sorted(candidates)],
            'dependencyRoot': observe_path(DEPENDENCIES),
            'priorInstallation': observe_path(PRIOR_INSTALLATION),
            'priorReceipt': observe_path(PRIOR_INSTALLATION + '/.alaz-installation.json',
                                         hash_file=True, maximum=2 * 1024 * 1024),
            'nodeExecuted': False, 'dependencyCodeImported': False,
            'dependencyBytesVerified': False, 'serviceStarted': False,
            'realModelCalls': 0, 'filesWritten': False,
            'runtimeOrAbiAcceptance': False, 'kernelAcceptance': False}


def main():
    try:
        result = inventory()
    except (OSError, ValueError) as exc:
        print(json.dumps({'result': 'REFUSED', 'kind': 'R167A1_READ_ONLY_LAB_RUNTIME_INVENTORY',
                          'reason': str(exc) if isinstance(exc, ValueError) else type(exc).__name__,
                          'filesWritten': False, 'serviceStarted': False, 'realModelCalls': 0}),
              flush=True)
        return 2
    print(json.dumps(result, sort_keys=True), flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
