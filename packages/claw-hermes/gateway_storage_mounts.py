"""Read-only Linux mount observations for a trusted Gateway profile.

No database contents are opened. No mount, UID, namespace, service, or storage
configuration is changed. A filesystem name is NOT proof of durable media:
ext4 can itself reside on volatile backing. This observer is not connected to
Gateway admission and does not authorize launching or restoring a workload.
"""
from __future__ import annotations
from dataclasses import dataclass
import hashlib
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys

MAX_MOUNTINFO_BYTES = 2 * 1024 * 1024
MAX_MOUNTS = 4096
MAX_LINE_BYTES = 16384
QUALIFIED_TYPES = frozenset({'ext4', 'xfs', 'btrfs'})
VOLATILE_TYPES = frozenset({'tmpfs', 'ramfs', 'rootfs'})
DATABASE_NAMES = ('state.db', 'runs_idempotency.db')
SIDECAR_NAMES = tuple(name + suffix for name in DATABASE_NAMES
                      for suffix in ('-wal', '-shm', '-journal'))
_ESCAPES = {'040': ' ', '011': '\t', '012': '\n', '134': '\\'}


class StorageMountRejected(ValueError):
    """Bounded code only, without database rows, source names, or paths."""


def require(ok, reason):
    if not ok:
        raise StorageMountRejected(reason)


def _posix_path(value):
    require(type(value) is str and value.startswith('/') and '\0' not in value
            and len(value) <= 4096, 'storage_mount_path_invalid')
    p = PurePosixPath(value)
    require(not value.startswith('//') and str(p) == value
            and '..' not in p.parts and '.' not in value.split('/'),
            'storage_mount_path_invalid')
    return value


def _decode_path(value):
    def replace(match):
        token = match.group(1)
        require(token in _ESCAPES, 'storage_mount_escape_invalid')
        return _ESCAPES[token]
    # Kernel mountinfo uses four specific octal escapes for path fields.
    require(not re.search(r'\\(?![0-7]{3})', value), 'storage_mount_escape_invalid')
    return _posix_path(re.sub(r'\\([0-7]{3})', replace, value))


def _number(value, positive=False):
    require(re.fullmatch(r'0|[1-9][0-9]{0,9}', value) is not None,
            'storage_mount_number_invalid')
    number = int(value)
    require(number <= 2**32 - 1 and (not positive or number > 0),
            'storage_mount_number_invalid')
    return number


def _options(value):
    options = value.split(',')
    require(all(options) and len(set(options)) == len(options)
            and (('rw' in options) != ('ro' in options)),
            'storage_mount_options_invalid')
    return frozenset(options)


@dataclass(frozen=True)
class MountRecord:
    mount_id: int
    parent_id: int
    device: tuple[int, int]
    root: str
    mount_point: str
    mount_options: frozenset[str]
    filesystem: str
    super_options: frozenset[str]


@dataclass(frozen=True)
class ExpectedMount:
    """Per-run expectation from the trusted supervisor, not a user capability.

    Mount IDs may change or be reused. This is only an observation-time match,
    not persistent identity or a lease. Never derive authority from caller JSON.
    """
    mount_id: int
    device: tuple[int, int]
    root: str
    mount_point: str
    filesystem: str

    def __post_init__(self):
        require(type(self.mount_id) is int and 0 < self.mount_id <= 2**32 - 1,
                'storage_expectation_invalid')
        require(type(self.device) is tuple and len(self.device) == 2
                and all(type(n) is int and 0 <= n <= 2**32 - 1 for n in self.device),
                'storage_expectation_invalid')
        _posix_path(self.root)
        _posix_path(self.mount_point)
        require(type(self.filesystem) is str and self.filesystem in QUALIFIED_TYPES,
                'storage_expected_filesystem_unqualified')


def parse_mountinfo(raw):
    """Bounded mountinfo parser; unknown optional tags are deliberately ignored."""
    require(type(raw) is bytes and 0 < len(raw) <= MAX_MOUNTINFO_BYTES
            and raw.endswith(b'\n') and b'\0' not in raw,
            'storage_mountinfo_incomplete')
    lines = raw.splitlines()
    require(0 < len(lines) <= MAX_MOUNTS, 'storage_mountinfo_limit')
    result = []
    identifiers = set()
    try:
        for line in lines:
            require(0 < len(line) <= MAX_LINE_BYTES and line.count(b' - ') == 1,
                    'storage_mountinfo_malformed')
            left, right = line.decode('utf-8').split(' - ')
            before, after = left.split(' '), right.split(' ')
            require(len(before) >= 6 and len(after) == 3
                    and all(before) and all(after), 'storage_mountinfo_malformed')
            mid, parent = _number(before[0], True), _number(before[1], True)
            device = before[2].split(':')
            require(len(device) == 2, 'storage_mountinfo_malformed')
            pair = tuple(_number(n) for n in device)
            require(mid not in identifiers, 'storage_mount_id_duplicate')
            identifiers.add(mid)
            require(re.fullmatch(r'[A-Za-z0-9_.+-]{1,80}', after[0]) is not None,
                    'storage_mountinfo_malformed')
            result.append(MountRecord(mid, parent, pair, _decode_path(before[3]),
                                      _decode_path(before[4]), _options(before[5]),
                                      after[0], _options(after[2])))
    except (UnicodeError, IndexError):
        raise StorageMountRejected('storage_mountinfo_malformed') from None
    return tuple(result)


def select_mount(records, path):
    """Refuse stacked relevant mounts instead of guessing which one is visible."""
    target = PurePosixPath(_posix_path(path))
    candidates = [r for r in records if target.is_relative_to(r.mount_point)]
    require(bool(candidates), 'storage_mount_not_found')
    points = [r.mount_point for r in candidates]
    require(len(points) == len(set(points)), 'storage_mount_stack_ambiguous')
    return max(candidates, key=lambda r: len(PurePosixPath(r.mount_point).parts))


def _is_linux():
    return sys.platform == 'linux'


def _read_mountinfo():
    with open('/proc/self/mountinfo', 'rb') as stream:
        return stream.read(MAX_MOUNTINFO_BYTES + 1)


def _mount_namespace():
    return os.readlink('/proc/self/ns/mnt')


def _device(info):
    return (os.major(info.st_dev), os.minor(info.st_dev))


def _mount_path(path):
    return path.as_posix()


def _canonical_profile(value):
    require(isinstance(value, (str, Path)), 'storage_profile_invalid')
    path = Path(value)
    require(path.is_absolute() and path == path.resolve(strict=True),
            'storage_profile_not_canonical')
    require(not any(p.is_symlink() or getattr(p, 'is_junction', lambda: False)()
                    for p in (path, *path.parents)), 'storage_profile_linked')
    require(path.is_dir(), 'storage_profile_not_directory')
    return path


def _identity(info):
    return (info.st_dev, info.st_ino, info.st_mode, info.st_nlink,
            info.st_uid, info.st_gid, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def _check_mount(record, expected):
    require(record.filesystem not in VOLATILE_TYPES, 'storage_volatile_filesystem')
    require(record.filesystem in QUALIFIED_TYPES, 'storage_filesystem_unqualified')
    require('rw' in record.mount_options and 'rw' in record.super_options,
            'storage_readonly_mount')
    actual = (record.mount_id, record.device, record.root,
              record.mount_point, record.filesystem)
    wanted = (expected.mount_id, expected.device, expected.root,
              expected.mount_point, expected.filesystem)
    require(actual == wanted, 'storage_mount_binding_mismatch')


def _snapshot(profile, records, expected):
    parent = profile.lstat()
    require(stat.S_ISDIR(parent.st_mode), 'storage_profile_not_directory')
    mounted = select_mount(records, _mount_path(profile))
    _check_mount(mounted, expected)
    require(_device(parent) == mounted.device, 'storage_device_mismatch')
    observed = {'profile': _identity(parent)}
    present = []
    for name in DATABASE_NAMES + SIDECAR_NAMES:
        path = profile / name
        try:
            info = path.lstat()
        except FileNotFoundError:
            require(name in SIDECAR_NAMES, 'storage_required_database_missing')
            observed[name] = None
            continue
        require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1,
                'storage_regular_single_file_required')
        candidate = select_mount(records, _mount_path(path))
        _check_mount(candidate, expected)
        require(_device(info) == candidate.device, 'storage_device_mismatch')
        observed[name] = _identity(info)
        present.append(name)
    return observed, tuple(present)


def observe_profile_mounts(profile_home, expected):
    """Observe two stores and present sidecars without opening their contents.

    Fails on changed metadata/table/namespace. This cannot detect an ABA race,
    prove a SQLite connection refers to these inodes, or enforce future writes.
    Even a matching ext4 mount may sit on RAM/loop or an unflushed virtual disk.
    """
    try:
        require(_is_linux(), 'storage_linux_required')
        require(type(expected) is ExpectedMount, 'storage_trusted_expectation_required')
        profile = _canonical_profile(profile_home)
        namespace = _mount_namespace()
        require(re.fullmatch(r'mnt:\[[0-9]+\]', namespace) is not None,
                'storage_namespace_unavailable')
        raw = _read_mountinfo()
        records = parse_mountinfo(raw)
        first, present = _snapshot(profile, records, expected)
        second, present_after = _snapshot(profile, records, expected)
        require(_read_mountinfo() == raw and _mount_namespace() == namespace
                and first == second and present == present_after,
                'storage_observation_changed')
        return {
            'version': 1, 'state': 'CONFIGURED_MOUNT_OBSERVED',
            'filesystem': expected.filesystem,
            'bothStoresAndPresentSidecarsOnExpectedMount': True,
            'presentFiles': len(present), 'sidecarsObserved': len(present) - 2,
            'mountTableSha256': hashlib.sha256(raw).hexdigest(),
            'snapshotOnly': True, 'writesPerformed': False,
            'databaseContentsOpened': False, 'sqliteOpenInodeVerified': False,
            'physicalMediumDurabilityVerified': False,
            'exclusiveWriterVerified': False, 'pairedStoreConsistencyVerified': False,
            'fullGatewayPersistenceAccepted': False, 'launchAuthorized': False,
        }
    except StorageMountRejected:
        raise
    except (OSError, ValueError, TypeError, AttributeError, IndexError, KeyError):
        raise StorageMountRejected('storage_mount_observation_unavailable') from None
