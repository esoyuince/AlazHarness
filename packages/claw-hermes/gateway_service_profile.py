"""Explicit selected-file admission for one prepared service profile.

This is a caller-supplied expectation, not a signature or a native config loader.
The caller must already hold the original lease and exclude concurrent foreign
writers. Two snapshots detect observed changes, not every same-UID ABA race.
No SQLite/lock file is opened, no profile content is repaired, and no model,
plugin, secret-source, managed overlay or native loader behavior is qualified.
Historical cold/prepared/retained layout contracts remain unchanged.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import re

import gateway_native_layout as layout
import gateway_retained_profile as retained
import gateway_service_sources as sources


SERVICE_LAYOUT = 'hermes-service-profile-v1'
CONFIG_NAME = 'config.yaml'
MAX_CONFIG_BYTES = 65536
MAX_CONFIG_DEPTH = 16
MAX_CONFIG_NODES = 4096
MAX_CONFIG_STRING = 4096
MAX_INTEGER_DIGITS = 20
MAX_NUMBER_CHARS = 64
_DATABASES = ('state.db', 'runs_idempotency.db', 'response_store.db')
_DIRECTORIES = layout.DIRECTORIES | layout.PREPARED_DIRECTORIES | retained.DIRECTORIES
_REQUIRED = layout.REQUIRED | layout.PREPARED_DIRECTORIES | retained.PATHS | frozenset(
    ('response_store.db', CONFIG_NAME))
_ALLOWED = _REQUIRED | layout.SIDECARS | frozenset(
    'response_store.db' + suffix for suffix in ('-journal', '-wal', '-shm'))


class ServiceProfileRejected(ValueError):
    """Fixed bounded reason; never raw config, paths or native exception text."""


def require(condition, reason):
    if not condition:
        raise ServiceProfileRejected(reason)


@dataclass(frozen=True)
class ServiceProfileExpectation:
    schema: int
    selection: sources.ServiceSourceSelection
    home: str
    home_identity: tuple
    database_identities: tuple
    epoch: int
    instance_id: str
    discovery_sha256: str
    config_identity: tuple
    config_size: int
    config_sha256: str


def _home_field(value):
    require(type(value) is str and 0 < len(value) <= 4096 and '\x00' not in value,
            'service_profile_home_field')
    # Structural wire validation also accepts a POSIX target on Windows. Actual
    # inspection below uses the host filesystem and rejects nonexistent aliases.
    if value.startswith('/'):
        path = PurePosixPath(value)
        require(not value.startswith('//') and '\\' not in value
                and str(path) == value and '..' not in path.parts,
                'service_profile_home_field')
    else:
        path = Path(value)
        require(path.is_absolute() and str(path) == value and '..' not in path.parts,
                'service_profile_home_field')


def _digest(value, length):
    return type(value) is str and re.fullmatch('[0-9a-f]{' + str(length) + '}', value) is not None


def validate_expectation(expectation):
    """Validate exact typed data without filesystem access or source loading."""
    require(type(expectation) is ServiceProfileExpectation,
            'service_profile_expectation_type')
    require(type(expectation.schema) is int and expectation.schema == 1,
            'service_profile_schema')
    selection = expectation.selection
    require(type(selection) is sources.ServiceSourceSelection
            and _digest(selection.native_feature, 40)
            and _digest(selection.manifest_sha256, 64)
            and _digest(selection.selection_sha256, 64),
            'service_profile_selection_fields')
    _home_field(expectation.home)
    require(type(expectation.database_identities) is tuple
            and len(expectation.database_identities) == 3,
            'service_profile_database_identities')
    identities = (expectation.home_identity, *expectation.database_identities,
                  expectation.config_identity)
    require(all(type(pair) is tuple and len(pair) == 2
                and all(type(n) is int and 0 < n < 2**64 for n in pair)
                for pair in identities), 'service_profile_identities')
    require(len(set(identities)) == 5
            and all(pair[0] == identities[0][0] for pair in identities),
            'service_profile_identity_alias_or_device')
    require(type(expectation.epoch) is int and 0 < expectation.epoch < 2**63
            and type(expectation.instance_id) is str
            and re.fullmatch('[A-Za-z0-9._-]{1,128}', expectation.instance_id) is not None,
            'service_profile_generation')
    require(_digest(expectation.discovery_sha256, 64)
            and _digest(expectation.config_sha256, 64)
            and type(expectation.config_size) is int
            and 0 < expectation.config_size <= MAX_CONFIG_BYTES,
            'service_config_expectation')
    return expectation


def _selected(expectation):
    require(sources.load_selection() == expectation.selection,
            'service_profile_source_changed')
    # The declaration's digest must still name the actual selected manifest.
    # Native files/imports themselves are qualified by the existing consumer.
    sources.selected_manifest(expectation.selection)


def _home(profile, uid, gid, device, expectation):
    require(all(type(n) is int and 0 < n < 2**64 for n in (uid, gid, device)),
            'service_profile_actor_identity')
    require(device == expectation.home_identity[0], 'service_profile_device')
    require(isinstance(profile, (str, Path)), 'service_profile_path')
    home = Path(profile)
    require(str(home) == expectation.home and home.is_absolute()
            and home == home.resolve(strict=True)
            and not any(p.is_symlink() or getattr(p, 'is_junction', lambda: False)()
                        for p in (home, *home.parents)),
            'service_profile_canonical_home')
    return home


def _snapshot(home, uid, gid, device):
    observed = {'profile': layout._private(home.lstat(), uid, gid, device, True)}
    pending = [('', home)]
    while pending:
        relative, parent = pending.pop()
        allowed = {Path(name).name for name in _ALLOWED
                   if Path(name).parent.as_posix() == (relative or '.')}
        entries = layout._children(parent, allowed)
        required = {Path(name).name for name in _REQUIRED
                    if Path(name).parent.as_posix() == (relative or '.')}
        require(required <= set(entries), 'service_profile_required_entry')
        for child, info in sorted(entries.items()):
            name = relative + '/' + child if relative else child
            directory = name in _DIRECTORIES
            observed[name] = layout._private(info, uid, gid, device, directory)
            require(not getattr(parent / child, 'is_junction', lambda: False)(),
                    'service_profile_link')
            if directory:
                pending.append((name, parent / child))
            elif name in _DATABASES:
                require(info.st_size >= 512, 'service_profile_unprepared_database')
            elif name in layout.LOCKS:
                require(info.st_size <= 16384, 'service_profile_lock_size')
            elif name == 'SOUL.md':
                require(info.st_size == layout.SOUL_BYTES, 'service_profile_soul_size')
            elif name == 'cache/schema_columns.json':
                require(0 < info.st_size <= layout.MAX_CACHE_BYTES,
                        'service_profile_cache_size')
            elif name in ('auth.lock', 'runtime/active_sessions.lock'):
                require(info.st_size == 0, 'service_profile_retained_lock_nonempty')
            elif name == 'cache/tool_discovery_cache.json':
                require(0 < info.st_size <= retained.MAX_DISCOVERY_BYTES,
                        'service_profile_discovery_size')
            elif name == 'runtime/active_sessions.json':
                require(0 < info.st_size <= retained.MAX_ACTIVE_BYTES,
                        'service_profile_active_size')
            elif name == CONFIG_NAME:
                require(0 < info.st_size <= MAX_CONFIG_BYTES, 'service_config_size')
    return observed


def _config_document(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, 'service_config_duplicate_key')
            result[key] = value
        return result

    def integer(value):
        require(len(value.lstrip('-')) <= MAX_INTEGER_DIGITS, 'service_config_number_limit')
        return int(value)

    def number(value):
        require(len(value) <= MAX_NUMBER_CHARS, 'service_config_number_limit')
        result = float(value)
        require(math.isfinite(result), 'service_config_nonfinite')
        return result

    def nonfinite(_):
        raise ServiceProfileRejected('service_config_nonfinite')

    require(type(raw) is bytes and 0 < len(raw) <= MAX_CONFIG_BYTES, 'service_config_size')
    value = json.loads(raw.decode('utf-8', 'strict'), object_pairs_hook=pairs,
                       parse_int=integer, parse_float=number, parse_constant=nonfinite)
    require(type(value) is dict, 'service_config_root_object')
    pending = [(value, 0)]
    count = 0
    while pending:
        current, depth = pending.pop()
        count += 1
        require(count <= MAX_CONFIG_NODES and depth <= MAX_CONFIG_DEPTH,
                'service_config_structure_limit')
        if type(current) is dict:
            require(count + len(pending) + 2 * len(current) <= MAX_CONFIG_NODES,
                    'service_config_structure_limit')
            for key, item in current.items():
                pending.extend(((key, depth + 1), (item, depth + 1)))
        elif type(current) is list:
            require(count + len(pending) + len(current) <= MAX_CONFIG_NODES,
                    'service_config_structure_limit')
            pending.extend((item, depth + 1) for item in current)
        elif type(current) is str:
            require(len(current) <= MAX_CONFIG_STRING and '\x00' not in current,
                    'service_config_string_limit')
            require('${' not in current, 'service_config_environment_reference')
        else:
            require(current is None or type(current) in (bool, int)
                    or type(current) is float and math.isfinite(current),
                    'service_config_value_type')
    canonical = json.dumps(value, sort_keys=True, separators=(',', ':'),
                           ensure_ascii=False, allow_nan=False).encode('utf-8')
    require(raw == canonical, 'service_config_noncanonical')


def _read_aux(home, name, snapshot, maximum):
    expected = snapshot[name]
    # Keep the historical auxiliary-file exclusion for databases, sidecars and
    # ownership locks, including the two locks admitted by this service layout.
    excluded = (frozenset(_DATABASES) | layout.LOCKS | layout.SIDECARS
                | frozenset(('response_store.db-journal', 'response_store.db-wal',
                             'response_store.db-shm', 'auth.lock',
                             'runtime/active_sessions.lock')))
    require(expected[:2] not in {snapshot[item][:2] for item in excluded if item in snapshot},
            'service_profile_aux_alias')
    # Nonblocking open prevents a regular-file-to-FIFO race from hanging the
    # admission check. The exact private regular-file fstat still must match.
    flags = (os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW
             | getattr(os, 'O_NONBLOCK', 0) | getattr(os, 'O_BINARY', 0))
    fd = os.open(home / name, flags)
    try:
        require(layout.metadata(os.fstat(fd)) == expected, 'service_profile_aux_fd_changed')
        raw = os.read(fd, maximum + 1)
        require(len(raw) == expected[6] and len(raw) <= maximum,
                'service_profile_aux_fd_changed')
        require(layout.metadata(os.fstat(fd)) == expected, 'service_profile_aux_fd_changed')
        return raw
    finally:
        os.close(fd)


def _read_config(home, snapshot):
    return _read_aux(home, CONFIG_NAME, snapshot, MAX_CONFIG_BYTES)


def _config(home, snapshot, expectation):
    metadata = snapshot[CONFIG_NAME]
    require(metadata[:2] == expectation.config_identity
            and metadata[6] == expectation.config_size, 'service_config_identity_or_size')
    raw = _read_config(home, snapshot)
    require(hashlib.sha256(raw).hexdigest() == expectation.config_sha256,
            'service_config_changed')
    _config_document(raw)


def inspect_profile(profile, *, uid, gid, device, expectation):
    """Selected service layout snapshot; does not authorize native startup."""
    try:
        validate_expectation(expectation)
        _selected(expectation)
        home = _home(profile, uid, gid, device, expectation)
        first = _snapshot(home, uid, gid, device)
        require(first['profile'][:2] == expectation.home_identity,
                'service_profile_home_identity')
        require(tuple(first[name][:2] for name in _DATABASES)
                == expectation.database_identities, 'service_profile_database_identity')
        soul = _read_aux(home, 'SOUL.md', first, layout.SOUL_BYTES)
        require(hashlib.sha256(soul).hexdigest() == layout.SOUL_SHA256,
                'service_profile_soul_content')
        layout._cache(_read_aux(home, 'cache/schema_columns.json', first,
                                layout.MAX_CACHE_BYTES))
        raw = _read_aux(home, 'cache/tool_discovery_cache.json', first,
                        retained.MAX_DISCOVERY_BYTES)
        require(hashlib.sha256(raw).hexdigest() == expectation.discovery_sha256,
                'service_profile_discovery_changed')
        retained._discovery_shape(retained._json(raw))
        active = retained._json(_read_aux(home, 'runtime/active_sessions.json', first,
                                         retained.MAX_ACTIVE_BYTES))
        require(type(active) is dict and set(active) == {'entries'}
                and type(active['entries']) is list and not active['entries'],
                'service_profile_active_sessions_not_empty')
        _config(home, first, expectation)
        require(first == _snapshot(home, uid, gid, device), 'service_profile_changed')
        _home(profile, uid, gid, device, expectation)
        _selected(expectation)
        return first
    except ServiceProfileRejected:
        raise
    except sources.ServiceSourcesRejected:
        raise ServiceProfileRejected('service_profile_source_rejected') from None
    except layout.NativeLayoutRejected:
        raise ServiceProfileRejected('service_profile_native_layout_rejected') from None
    except (OSError, ValueError, TypeError, KeyError, AttributeError, OverflowError, RecursionError):
        raise ServiceProfileRejected('service_profile_unavailable') from None


def check_config(profile, *, uid, gid, device, expectation):
    """Pin home/config while allowing ordinary profile and database writes.

    Only the selected config file is opened. This neither enumerates runtime
    files nor treats native backup/default/managed-loader behavior as accepted.
    """
    try:
        validate_expectation(expectation)
        _selected(expectation)
        home = _home(profile, uid, gid, device, expectation)
        before = layout._private(home.lstat(), uid, gid, device, True)
        require(before[:2] == expectation.home_identity, 'service_profile_home_identity')
        config = layout._private((home / CONFIG_NAME).lstat(), uid, gid, device, False)
        require(0 < config[6] <= MAX_CONFIG_BYTES, 'service_config_size')
        _config(home, {'profile': before, CONFIG_NAME: config}, expectation)
        after = layout._private(home.lstat(), uid, gid, device, True)
        require(before[:5] == after[:5], 'service_profile_home_changed')
        require(config == layout._private((home / CONFIG_NAME).lstat(), uid, gid, device, False),
                'service_config_metadata_changed')
        _home(profile, uid, gid, device, expectation)
        _selected(expectation)
        return {'state': 'SERVICE_CONFIG_BOUND', 'schema': 1,
                'profileIdentity': expectation.home_identity,
                'configIdentity': expectation.config_identity,
                'configSize': expectation.config_size,
                'configSha256': expectation.config_sha256,
                'nativeFeature': expectation.selection.native_feature,
                'sourceManifestSha256': expectation.selection.manifest_sha256,
                'sourceSelectionSha256': expectation.selection.selection_sha256,
                'snapshotOnly': True, 'databaseOpened': False,
                'nativeConfigLoaded': False, 'modelPolicyQualified': False,
                'runtimeAdmissionAuthorized': False}
    except ServiceProfileRejected:
        raise
    except sources.ServiceSourcesRejected:
        raise ServiceProfileRejected('service_profile_source_rejected') from None
    except layout.NativeLayoutRejected:
        raise ServiceProfileRejected('service_profile_native_layout_rejected') from None
    except (OSError, ValueError, TypeError, KeyError, AttributeError, OverflowError, RecursionError):
        raise ServiceProfileRejected('service_profile_unavailable') from None
