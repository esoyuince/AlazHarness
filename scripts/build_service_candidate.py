"""Build the separate, pinned P2 service SOURCE candidate; never install or run it.

The retained/finite tools remain byte-exact. Their reviewed Git, path and JSON
primitives are reused without changing their globals or generation contracts.
Python, Node, dependency bytes, private state and credentials are not packaged.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import posixpath
import re
import stat
import subprocess
import sys
import tarfile
import types
from functools import lru_cache
from types import MappingProxyType

ROOT = Path(__file__).resolve().parents[1]
LEGACY_INSTALLER_SHA256 = 'f261fd22c641a1ffdd6fb9694fec0c7d3cb0c8dba788cb7549c142fd1e4dcef6'
SCANNER_SHA256 = 'b55871b560f4f30d30fb22869ac63a3b47aaa5928d4aae9dee499c88c9fa94c8'


def _load_reviewed(filename, expected):
    """Execute only already hashed sibling tool bytes, never candidate sources."""
    path = Path(__file__).absolute().with_name(filename)
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError('service_reviewed_tool_symlink')
    fd = os.open(path, os.O_RDONLY | getattr(os, 'O_CLOEXEC', 0)
                 | getattr(os, 'O_NOFOLLOW', 0))
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or before.st_size > 2 * 1024 * 1024:
            raise ValueError('service_reviewed_tool_file')
        with os.fdopen(fd, 'rb', closefd=False) as stream:
            raw = stream.read(2 * 1024 * 1024 + 1)
        after = os.fstat(fd)
        stamp = lambda s: (s.st_dev, s.st_ino, s.st_mode, s.st_uid, s.st_gid,
                           s.st_nlink, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
        if len(raw) != before.st_size or stamp(before) != stamp(after) or hashlib.sha256(raw).hexdigest() != expected:
            raise ValueError('service_reviewed_tool_changed')
    finally:
        os.close(fd)
    name = '_alaz_service_reviewed_' + path.stem + '_' + expected
    module = types.ModuleType(name)
    module.__file__ = str(path)
    # Dataclass annotation resolution needs its own module, not altered legacy
    # globals. The object is populated exclusively from the verified bytes.
    sys.modules[name] = module
    try:
        exec(compile(raw, str(path), 'exec'), module.__dict__)
    except BaseException:
        sys.modules.pop(name, None)
        raise
    return module


@lru_cache(maxsize=1)
def _legacy():
    return _load_reviewed('install_projected_candidate.py', LEGACY_INSTALLER_SHA256)


@lru_cache(maxsize=1)
def _scanner():
    return _load_reviewed('ci_check.py', SCANNER_SHA256)


_base = _legacy()._builder()
CandidateRejected = _base.CandidateRejected
require, digest, canonical = _base.require, _base.digest, _base.canonical
safe_name, unique_json = _base.safe_name, _base.unique_json
git, commit, tree = _base.git, _base.commit, _base.tree
MAX_FILE, MAX_TOTAL = _base.MAX_FILE, _base.MAX_TOTAL
MAX_ARCHIVE, MAX_FILES = _base.MAX_ARCHIVE, _base.MAX_FILES
DEPENDENCY_COUNT, DEPENDENCY_RECORD = _base.DEPENDENCY_COUNT, _base.DEPENDENCY_RECORD

NATIVE_FEATURE = '5e3635c2cdfc2161fd20c089618bd7f2a7c12f2d'
NATIVE_COUNT = 760
NATIVE_MANIFEST = 'config/borrowed-service-r159a1-sources.json'
MANIFEST_SHA256 = '05dee55dede392d10af65fc123969b8f317cf417d1af669b655d2115a2757bd2'
SELECTION = 'config/hermes-borrowed-service-r159a1.json'
HOST_LOCK = 'config/borrowed-service-r159a1-host-lock.json'
HOST_LOCK_FILES = frozenset(('hermes_state.py', 'gateway/platforms/api_server.py',
    'gateway/platforms/api_server_runs.py', 'gateway/platforms/base.py', 'hermes_cli/plugins.py'))
PREFIX, ARCHIVE = 'alazharness-service/', 'service-source.tar'
KIND = 'SERVICE_SOURCE_CANDIDATE_NOT_INSTALLED'
SERVICE_ENTRIES = ('scripts/run_supervised_service.py', 'scripts/run_service_projected.py',
                   'scripts/run_service_volume_worker.py')
# This is a reviewed, fixed import closure, including the indirect TS import.
# Changing CLI source requires an explicit new review of both bytes and closure.
CLI_FILES = MappingProxyType({
    'scripts/alaz_local.mjs': 'd37441853cf31d8fe482bc7f6f2f1d5659ebf4a03de62d6f5e0952a183b56523',
    'packages/claw-hermes/package.json': 'c68b7ffc274b9217ed60907218adc56ca0d9378175340621c6ce81d1ad0d0328',
    'packages/claw-hermes/local-control.mjs': 'a5d9016be5f8e208a3f467d1ed4d26d67b966f8c7ee59d8dc9d8b86f871060b7',
    'packages/claw-hermes/host-gate-client.mjs': 'd319a405e9469dea9e9a5023a004adb0fdd29c65b27a8d8582a0f2f0b7023a51',
    'packages/claw-hermes/hermes-runs.mjs': '54903fc7c9596498d7b6b8a829aa2f8e9c1be9ca9bdb882214dafcaa781b93e8',
    'packages/claw-hermes/run-recovery.mjs': '21793d7583cc2c56e955e85667561f83edfefd72fc219d81cd8469d35f97e748',
    'packages/claw-hermes/service-task.mjs': '20dd9f2fe07ba8b229abc13f891455c17fa5d914a561048a9f1013cfb0c72746',
    'packages/claw-hermes/service-control.mjs': '6cba0cdac5de88990a861d811be6b81c66838784da9d260f32dfb243e45198a3',
    'packages/upstream/openclaw/attempt-cancellation.ts': '8bb3ec23f95054d55a18f5d3d5f124aa2f0e57e6168b976f8c5b73bec5f8e634',
    'packages/upstream/openclaw/attempt-deadlines.ts': 'cdfe9b26f74cd5e0b88e6b29850faac6f2472ca708defbda7419af0aa82bb7e4',
    'packages/upstream/openclaw/number-coercion.ts': '59296d074f0f4c81068c124f0499be87b5f6ed9fc542d5a62a7a864d859549a7',
    'packages/upstream/openclaw/string-coerce.ts': '9d0648121488d3cbbb47716c4b3048faa4c94f607bfaafe7ed6617562d4fc3c3',
})
# execution_boundary imports recovery_inspector's two selected Hermes helpers;
# its original file-tool registration also reads this physical boundary lock.
SUPPORT_FILES = MappingProxyType({
    'packages/upstream/hermes/hermes_state_keys.py': '00311a21ba6fd6388bfc9cbd1d507bef20b85e65ee35287a6c24a0dddfaa97a8',
    'packages/upstream/hermes/terminal_status.py': '9290a3d8ebba3dd9e10788323e712300b5c5aa7b78e1821bd9e84b4513831371',
    'config/execution-gate/source-lock.json': '4a43e5fcd6effc5bc4525a6cf13c1d1d50ca26d05c64f4f3c8b4e7a68351069e',
})
EXACT = _base.EXACT | frozenset((NATIVE_MANIFEST, SELECTION, HOST_LOCK, *SERVICE_ENTRIES,
                               *CLI_FILES, *SUPPORT_FILES))
REQUIRED_MODULES = _base.REQUIRED_MODULES | frozenset('packages/claw-hermes/' + n for n in (
    'gateway_service_sources.py', 'gateway_service_profile.py', 'gateway_service_handoff.py',
    'gateway_service_launch.py', 'gateway_service_runtime.py', 'gateway_service_projection.py',
    'gateway_service_factory.py', 'gateway_service_control.py', 'gateway_supervised_service.py',
    'supervised_service_channel.py', 'service_volume_supervisor.py', 'service_control_server.py',
    'service_task_protocol.py', 'service_task_http.py', 'service_task_server.py'))
# The new native manifest pins the same base.py SHA and Git blob. Carry forward
# only that exact reviewed occurrence; the full tuple is checked again below.
REVIEWED_NATIVE_MARKERS = tuple({**m, 'nativeFeature': NATIVE_FEATURE}
                                for m in _base.REVIEWED_NATIVE_MARKERS)
SCAN_SCOPE = 'Existing bounded credential/private-path scanners; not a complete security audit'


def selected(name):
    return name in EXACT or (name.startswith('packages/claw-hermes/') and name.endswith('.py'))


def boundaries():
    return {**{name: False for name in ('installed', 'executionAuthorized',
        'dependenciesAcceptedForService', 'serviceReadinessAccepted', 'kernelAcceptance',
        'realModelAcceptance', 'pythonIncluded', 'nodeIncluded')}, 'realModelCalls': 0,
        'runtimeRequirements': {'target': 'Linux x86_64', 'selection': 'NOT_RUN',
            'readback': 'NOT_RUN', 'python': {'version': '3.12', 'path': None,
                'sha256': None, 'observedVersion': None},
            'node': {'version': '>=24 <25', 'path': None, 'sha256': None, 'observedVersion': None}}}


def _hex(value, length, reason):
    require(type(value) is str and re.fullmatch('[0-9a-f]{' + str(length) + '}', value), reason)


def _marker_key(marker):
    return _base._marker_key(marker)


def _scan(name, row, data, *, native=False):
    scanner = _scanner()
    require(b'\0' not in data and not scanner.private_path(name), 'service_private_or_binary_source')
    reviews = [m for m in REVIEWED_NATIVE_MARKERS if native and m['path'] == name]
    wanted = {_marker_key(m): m for m in reviews}
    require(len(wanted) == len(reviews) and all(m['nativeFeature'] == NATIVE_FEATURE
        and m['gitBlob'] == row['gitBlob'] and m['fileSha256'] == digest(data) for m in reviews),
        'service_reviewed_source_changed')
    seen = set()
    for detector in scanner.credential_hits(data):
        for match in scanner.PATTERNS[detector].finditer(data):
            identity = (NATIVE_FEATURE if native else None, name, row['gitBlob'], digest(data),
                        detector, match.start(), match.end(), digest(match.group()))
            require(identity in wanted and identity not in seen, 'service_credential_pattern')
            seen.add(identity)
    require(seen == set(wanted), 'service_reviewed_marker_missing')
    return [dict(wanted[key]) for key in sorted(seen)]


def _blobs(repo, inventory):
    raw = git(repo, 'cat-file', '--batch', data=''.join(
        row['gitBlob'] + '\n' for row in inventory.values()).encode('ascii'))
    require(len(raw) <= MAX_TOTAL + MAX_FILES * 100, 'service_batch_limit')
    result = {}; cursor = 0
    for name, row in inventory.items():
        end = raw.find(b'\n', cursor)
        require(end >= 0 and raw[cursor:end].decode('ascii').split() ==
                [row['gitBlob'], 'blob', str(row['bytes'])], 'service_blob_identity')
        cursor = end + 1
        result[name] = raw[cursor:cursor + row['bytes']]; cursor += row['bytes']
        require(len(result[name]) == row['bytes'] and raw[cursor:cursor + 1] == b'\n',
                'service_blob_length')
        cursor += 1
    require(cursor == len(raw), 'service_extra_blob_output')
    return result


def validate_metadata(metadata):
    require(type(metadata) is dict and EXACT | REQUIRED_MODULES | {'accepted-dependencies.json'}
            <= set(metadata) and len(metadata) <= MAX_FILES, 'service_required_source_missing')
    _legacy()._namespace(metadata)
    total = 0
    for name, row in metadata.items():
        safe_name(name)
        require(type(row) is dict and set(row) == {'gitBlob', 'mode', 'bytes', 'repository', 'sha256'},
                'service_file_metadata')
        require(type(row['mode']) is int and row['mode'] in (0o644, 0o755)
            and type(row['bytes']) is int and 0 <= row['bytes'] <= MAX_FILE, 'service_file_limits')
        _hex(row['sha256'], 64, 'service_file_digest')
        total += row['bytes']
        if name == 'accepted-dependencies.json':
            require(row['repository'] == 'generated-reference' and row['gitBlob'] is None
                    and row['mode'] == 0o644, 'service_reference_metadata')
        else:
            _hex(row['gitBlob'], 40, 'service_git_blob')
            require((name.startswith('native/') and row['repository'] == 'native')
                or (selected(name) and row['repository'] == 'harness'), 'service_unselected_source')
    require(total <= MAX_TOTAL, 'service_source_limit')


def _cli(payload):
    require(all(name in payload and digest(payload[name]) == pin for name, pin in CLI_FILES.items()),
            'service_cli_source_changed')
    package = unique_json(payload['packages/claw-hermes/package.json'])
    require(package.get('engines') == {'node': '>=24 <25'}, 'service_node_requirement')
    pattern = rb'(?:import|export)\s+(?:[^;]*?\s+from\s+)?["\x27]([^"\x27]+)["\x27]'
    builtins = {'node:fs', 'node:fs/promises', 'node:net', 'node:crypto',
                'node:path', 'node:timers/promises'}
    pending = ['scripts/alaz_local.mjs']; seen = set()
    while pending:
        name = pending.pop()
        if name in seen:
            continue
        seen.add(name); raw = payload[name]
        require(not re.search(rb'\b(?:import\s*\(|require\s*\()', raw), 'service_dynamic_cli_import')
        for encoded in re.findall(pattern, raw):
            specifier = encoded.decode('ascii')
            if specifier in builtins:
                continue
            require(specifier.startswith('./') or specifier.startswith('../'), 'service_external_cli_import')
            target = posixpath.normpath(posixpath.join(posixpath.dirname(name), specifier))
            require(target in CLI_FILES and target.endswith(('.mjs', '.ts')), 'service_cli_import_missing')
            pending.append(target)
    require(seen == set(CLI_FILES) - {'packages/claw-hermes/package.json'}, 'service_cli_closure')


def _support(payload, native_sources):
    require(all(name in payload and digest(payload[name]) == pin for name, pin in SUPPORT_FILES.items()),
            'service_support_source_changed')
    lock = unique_json(payload['config/execution-gate/source-lock.json'])
    require(type(lock) is dict and set(lock) == {'source_commit', 'scope', 'files'}
            and type(lock['files']) is list and len(lock['files']) == 5, 'service_execution_lock')
    seen = set()
    for row in lock['files']:
        require(type(row) is dict and set(row) == {'path', 'sha256'} and type(row['path']) is str
                and row['path'] in native_sources and row['path'] not in seen
                and row['sha256'] == native_sources[row['path']], 'service_execution_lock_digest')
        seen.add(row['path'])


def validate_payload(payload, metadata, proof):
    validate_metadata(metadata)
    require(type(payload) is dict and set(payload) == set(metadata), 'service_payload_inventory')
    reviews = []
    for name, raw in payload.items():
        row = metadata[name]
        require(type(raw) is bytes and len(raw) == row['bytes'] and digest(raw) == row['sha256'],
                'service_source_digest')
        if row['repository'] != 'generated-reference':
            require(hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
                    == row['gitBlob'], 'service_source_git_blob')
            reviews.extend(_scan(name.removeprefix('native/') if row['repository'] == 'native' else name,
                                 row, raw, native=row['repository'] == 'native'))
    require(sorted(map(_marker_key, reviews)) == sorted(map(_marker_key, REVIEWED_NATIVE_MARKERS)),
            'service_reviewed_marker_inventory')
    require(digest(payload[NATIVE_MANIFEST]) == MANIFEST_SHA256, 'service_native_manifest_pin')
    selection = unique_json(payload[SELECTION]); envelope = unique_json(payload[NATIVE_MANIFEST])
    require(type(selection) is dict and selection == {'schema': 1, 'nativeFeature': NATIVE_FEATURE,
        'sourceManifest': NATIVE_MANIFEST, 'sourceManifestSha256': MANIFEST_SHA256}
        and type(selection['schema']) is int, 'service_source_selection')
    require(type(envelope) is dict and set(envelope) == {'schema', 'nativeFeature', 'purpose', 'sources'}
        and type(envelope['schema']) is int and envelope['schema'] == 1
        and envelope['nativeFeature'] == NATIVE_FEATURE and type(envelope['purpose']) is str
        and 0 < len(envelope['purpose']) <= 1024 and type(envelope['sources']) is dict
        and len(envelope['sources']) == NATIVE_COUNT, 'service_native_envelope')
    expected = envelope['sources']
    for name, pin in expected.items():
        safe_name(name); _hex(pin, 64, 'service_native_digest')
        require(name.endswith('.py'), 'service_native_source_type')
    require({n.removeprefix('native/'): r['sha256'] for n, r in metadata.items()
             if r['repository'] == 'native'} == expected, 'service_native_source_closure')
    host = unique_json(payload[HOST_LOCK])
    require(type(host) is dict and set(host) == {'files', 'native_commit', 'scope'}
        and host['native_commit'] == NATIVE_FEATURE and type(host['scope']) is str
        and 0 < len(host['scope']) <= 1024 and type(host['files']) is list
        and len(host['files']) == len(HOST_LOCK_FILES), 'service_host_lock')
    host_files = {}
    for row in host['files']:
        require(type(row) is dict and set(row) == {'path', 'sha256'} and type(row['path']) is str
                and row['path'] in HOST_LOCK_FILES and row['path'] not in host_files,
                'service_host_lock_entry')
        host_files[row['path']] = row['sha256']
    require(set(host_files) == HOST_LOCK_FILES and all(host_files[n] == expected.get(n)
            for n in HOST_LOCK_FILES), 'service_host_lock_digest')
    _cli(payload); _support(payload, expected)
    reference = payload['accepted-dependencies.json']; dependencies = unique_json(reference)
    require(type(dependencies) is dict and len(dependencies) == DEPENDENCY_COUNT
            and canonical(dependencies) == reference, 'service_dependency_inventory')
    for name, pin in dependencies.items():
        safe_name(name); _hex(pin, 64, 'service_dependency_digest')
    _legacy()._namespace(dependencies)
    expected_proof = {'sourceRecord': DEPENDENCY_RECORD, 'inventoryFile': 'accepted-dependencies.json',
        'inventorySha256': digest(reference), 'fileCount': DEPENDENCY_COUNT, 'bytesIncluded': False,
        'installedBytesVerifiedNow': False, 'target': 'Linux x86_64 CPython 3.12',
        'serviceDependencyCompletenessAccepted': False}
    require(type(proof) is dict and set(proof) == set(expected_proof) | {'recordGitBlob', 'recordSha256'}
        and all(type(proof[k]) is type(v) and proof[k] == v for k, v in expected_proof.items()),
        'service_dependency_proof')
    _hex(proof['recordGitBlob'], 40, 'service_dependency_record_blob')
    _hex(proof['recordSha256'], 64, 'service_dependency_record_digest')
    return dependencies, reviews


def source(repo, revision, native_repo):
    commit(repo, revision); commit(native_repo, NATIVE_FEATURE)
    inventory = tree(repo, revision, lambda n: selected(n) or n == DEPENDENCY_RECORD)
    require(EXACT | REQUIRED_MODULES | {DEPENDENCY_RECORD} <= set(inventory), 'service_required_source_missing')
    payload = _blobs(repo, inventory)
    record_raw = payload.pop(DEPENDENCY_RECORD); record_meta = inventory.pop(DEPENDENCY_RECORD)
    _scan(DEPENDENCY_RECORD, record_meta, record_raw)
    record = unique_json(record_raw)
    require(type(record) is dict and type(record.get('nativeExitCode')) is int
        and record['nativeExitCode'] == 0 and record.get('sourceBytesUnchanged') is True
        and record.get('installedBytesMatchPriorAcceptedTarget') is True
        and type(record.get('sources')) is dict, 'service_dependency_record')
    dependencies = {safe_name(n.removeprefix('dependencies/')): pin for n, pin in record['sources'].items()
                    if n.startswith('dependencies/')}
    envelope = unique_json(payload[NATIVE_MANIFEST])
    require(type(envelope) is dict and type(envelope.get('sources')) is dict, 'service_native_envelope')
    native_inventory = tree(native_repo, NATIVE_FEATURE, lambda n: n in envelope['sources'])
    require(set(native_inventory) == set(envelope['sources']), 'service_native_sources_missing')
    native = _blobs(native_repo, native_inventory)
    metadata = {n: {**row, 'repository': 'harness', 'sha256': digest(payload[n])}
                for n, row in inventory.items()}
    for name, raw in native.items():
        payload['native/' + name] = raw
        metadata['native/' + name] = {**native_inventory[name], 'repository': 'native', 'sha256': digest(raw)}
    reference = canonical(dependencies); payload['accepted-dependencies.json'] = reference
    metadata['accepted-dependencies.json'] = {'repository': 'generated-reference', 'gitBlob': None,
        'mode': 0o644, 'bytes': len(reference), 'sha256': digest(reference)}
    proof = {'sourceRecord': DEPENDENCY_RECORD, 'recordGitBlob': record_meta['gitBlob'],
        'recordSha256': digest(record_raw), 'inventoryFile': 'accepted-dependencies.json',
        'inventorySha256': digest(reference), 'fileCount': DEPENDENCY_COUNT, 'bytesIncluded': False,
        'installedBytesVerifiedNow': False, 'target': 'Linux x86_64 CPython 3.12',
        'serviceDependencyCompletenessAccepted': False}
    _, reviews = validate_payload(payload, metadata, proof)
    return dict(sorted(payload.items())), dict(sorted(metadata.items())), proof, reviews


def stamp(revision):
    return json.dumps({'harnessCommit': revision, 'nativeFeature': NATIVE_FEATURE,
                       'kind': KIND}, sort_keys=True, separators=(',', ':'))


def archive_bytes(payload, metadata, revision):
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode='w', format=tarfile.PAX_FORMAT,
                      pax_headers={'comment': stamp(revision)}) as archive:
        for name, raw in sorted(payload.items()):
            safe_name(name)
            info = tarfile.TarInfo(PREFIX + name)
            info.mode = metadata[name]['mode']; info.size = len(raw)
            info.uid = info.gid = info.mtime = 0; info.uname = info.gname = ''
            archive.addfile(info, io.BytesIO(raw))
    return stream.getvalue()


def verify_archive(raw, expected, revision):
    require(type(raw) is bytes and 0 < len(raw) <= MAX_ARCHIVE, 'service_archive_size')
    require(type(expected) is dict and 0 < len(expected) <= MAX_FILES, 'service_archive_inventory')
    found = []; total = 0; payload = {}
    try:
        with tarfile.open(fileobj=io.BytesIO(raw), mode='r:') as archive:
            require(archive.pax_headers == {'comment': stamp(revision)}, 'service_archive_revision')
            for member in archive:
                safe_name(member.name)
                require(member.name.startswith(PREFIX), 'service_archive_prefix')
                name = member.name[len(PREFIX):]
                require(name in expected and name not in found, 'service_archive_members')
                row = expected[name]
                require(member.type in (tarfile.REGTYPE, tarfile.AREGTYPE) and not member.linkname
                    and not member.sparse and set(member.pax_headers) <= {'comment', 'path'}
                    and member.pax_headers.get('comment') == stamp(revision)
                    and member.pax_headers.get('path', member.name) == member.name,
                    'service_archive_regular_only')
                require(member.mode == row['mode'] and member.mode in (0o644, 0o755)
                    and member.uid == member.gid == member.mtime == 0 and not member.uname
                    and not member.gname and member.size == row['bytes'] and 0 <= member.size <= MAX_FILE,
                    'service_archive_metadata')
                handle = archive.extractfile(member)
                require(handle is not None, 'service_archive_missing_data')
                with handle:
                    data = handle.read(MAX_FILE + 1)
                require(len(data) == member.size and digest(data) == row['sha256'], 'service_archive_digest')
                found.append(name); payload[name] = data; total += member.size
                require(total <= MAX_TOTAL, 'service_archive_total')
            require(len(raw) - archive.offset >= 1024 and not any(raw[archive.offset:]), 'service_archive_trailing_payload')
    except (tarfile.TarError, OSError, UnicodeError) as exc:
        raise CandidateRejected('service_archive_unreadable') from exc
    require(found == sorted(expected), 'service_archive_incomplete_or_order')
    # tarfile ignores header/member padding and some redundant PAX records.
    # Exact deterministic reconstruction rejects those otherwise hidden bytes.
    require(archive_bytes(payload, expected, revision) == raw, 'service_archive_noncanonical')
    return {'sourceFileCount': len(found), 'sourceBytes': total, 'archiveBytes': len(raw), 'archiveSha256': digest(raw)}


def build(repo, revision, native_repo, destination):
    repo = Path(repo).resolve(); native_repo = Path(native_repo).resolve(); destination = Path(destination)
    require(destination.is_absolute() and destination == destination.resolve()
        and not any(p.is_symlink() for p in (destination, *destination.parents)), 'service_destination_canonical')
    base = repo / 'scratch' / 'service-candidates'
    require(destination.is_relative_to(base) and destination != base, 'service_ignored_scratch_only')
    require(not destination.exists(), 'service_destination_must_be_absent')
    require(git(repo, 'check-ignore', '--no-index', '--stdin',
        data=(destination.relative_to(repo).as_posix() + '/\n').encode()).strip(), 'service_destination_not_ignored')
    payload, metadata, proof, reviews = source(repo, revision, native_repo)
    raw = archive_bytes(payload, metadata, revision); checked = verify_archive(raw, metadata, revision)
    manifest = {'schemaVersion': 1, 'kind': KIND, 'harnessCommit': revision,
        'nativeFeature': NATIVE_FEATURE, 'archive': ARCHIVE, 'prefix': PREFIX, **checked,
        'nativeSourceFileCount': NATIVE_COUNT, 'harnessSourceFileCount': len(payload) - NATIVE_COUNT - 1,
        'fileManifest': metadata, 'dependencies': proof, **boundaries(),
        'credentialScan': {'existingPatternsApplied': True, 'reviewedNativeMarkerCount': len(reviews),
                           'reviewedNativeMarkers': reviews}, 'scanScope': SCAN_SCOPE}
    manifest_raw = canonical(manifest)
    plan = {'schemaVersion': 1, 'state': 'SOURCE_PREPARATION_ONLY_NOT_EXECUTABLE',
        'harnessCommit': revision, 'nativeFeature': NATIVE_FEATURE,
        'manifestSha256': digest(manifest_raw), 'archiveSha256': digest(raw),
        'fixedEntrypoints': [*SERVICE_ENTRIES, 'scripts/alaz_local.mjs'], **boundaries(),
        'unmetGates': ['Review exact manifest/archive/commit/native pins from primary Git objects',
            'Select fresh P2 installation target; preserve accepted R156 installation',
            'Select reviewed Python 3.12 and Node 24 binary paths and SHA256; observe their versions and read back exact bytes',
            'Verify referenced dependency bytes and separately establish service dependency completeness',
            'Implement/review installation path, then qualify fresh installed service and kernel behavior',
            'Select and separately authorize model/provider/budget before any real model invocation']}
    destination.mkdir(parents=True, exist_ok=False)
    for name, data in {ARCHIVE: raw, 'manifest.json': manifest_raw, 'install-plan.json': canonical(plan)}.items():
        with (destination / name).open('xb') as handle:
            handle.write(data)
        require((destination / name).read_bytes() == data, 'service_readback_mismatch')
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--commit', required=True)
    parser.add_argument('--native-repository', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        result = build(ROOT, args.commit, args.native_repository, args.output)
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        print(json.dumps({'result': 'REFUSED', 'reason': str(exc) if isinstance(exc, CandidateRejected)
            else 'service_local_io_or_parse_failed', 'installed': False, 'executionAuthorized': False}), file=sys.stderr)
        return 2
    print(json.dumps({'result': 'EXPORTED_SERVICE_SOURCE_ONLY', **{k: result[k] for k in
        ('harnessCommit', 'nativeFeature', 'sourceFileCount', 'nativeSourceFileCount', 'archiveSha256',
         'installed', 'executionAuthorized')}}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
