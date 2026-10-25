"""Build an exact-source projected-startup candidate; never install or run it.

The candidate contains fixed product entrypoints, current harness modules and the
756 pinned retained-native sources. It references the accepted dependency bytes;
it does not download, install or include those dependencies, Python or live state.
Git objects are read with replacement disabled. No packaged code is executed.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import tarfile

ROOT = Path(__file__).resolve().parents[1]
NATIVE_FEATURE = 'd1516731308de8e87130dc68124e69aad35d6911'
NATIVE_COUNT = 756
DEPENDENCY_COUNT = 1162
NATIVE_MANIFEST = 'config/retained-profile-r140c6-sources.json'
DEPENDENCY_RECORD = 'evidence/d3b-confined-consumer-f126c1/native-006-result.json'
PREFIX = 'alazharness-projected/'
ARCHIVE = 'projected-source.tar'
MAX_FILE = 2 * 1024 * 1024
MAX_TOTAL = 32 * 1024 * 1024
MAX_ARCHIVE = 64 * 1024 * 1024
MAX_FILES = 1600
EXACT = frozenset((
    'LICENSE', 'SECURITY.md', 'docs/THIRD-PARTY.md', 'sources.lock.json',
    'packages/claw-hermes/UPSTREAM.md', 'packages/upstream/hermes/LICENSE',
    'packages/upstream/openclaw/LICENSE', 'config/components.lock.json',
    'config/prepared-consumer-s124b1-sources.json',
    'config/admission-consumer-b129d6-sources.json',
    'config/canonical-api-consumer-i133p1-sources.json',
    'config/finite-close-f135c6-sources.json', NATIVE_MANIFEST,
    'config/hermes-finite-close-f135c6.json',
    'config/linux-prepared-dependencies-l125p1.json',
    'scripts/run_supervised_retained.py', 'scripts/run_retained_projected.py',
    'scripts/run_state_volume_worker.py', 'scripts/run_store_preopen.py',
    'scripts/run_response_preopen.py',
))
REQUIRED_MODULES = frozenset('packages/claw-hermes/' + name for name in (
    'gateway_supervised_launch.py', 'gateway_retained_launch.py',
    'gateway_retained_handoff.py', 'gateway_retained_profile.py',
    'gateway_retained_projection.py', 'gateway_state_projection.py',
    'state_volume_supervisor.py', 'state_image_lease.py', 'supervised_pipe_capture.py',
    'gateway_store_startup.py', 'gateway_prepared_consumer.py',
))
# The sole real-source detector hit was reviewed as a conventional URL-userinfo
# placeholder in the first-statement docstring of resolve_proxy_url. This table
# binds that occurrence to exact immutable native bytes, not a path exemption.
# No matched text is stored here. Every other occurrence remains a refusal.
REVIEWED_NATIVE_MARKERS = ({
    'nativeFeature': 'd1516731308de8e87130dc68124e69aad35d6911',
    'path': 'gateway/platforms/base.py',
    'gitBlob': '39f810e91264aee5f7d6bfcda5deffca816e7f14',
    'fileSha256': 'ba558db13e29bd29b7b7ecb7e39c2830972104839f9fa6798ace32c722a04525',
    'detector': 'credential-url', 'byteStart': 15806, 'byteEnd': 15823,
    'matchSha256': 'f8c7f2987069485166a19282090fd6bfda8b12c5ccf46c99846068ed92369f32',
    'classification': 'documentation-placeholder',
    'context': 'first-statement function docstring',
    'symbol': 'resolve_proxy_url', 'line': 337,
},)


class CandidateRejected(ValueError):
    """Bounded refusal; no private data or Git stderr is exposed."""


def require(ok, reason):
    if not ok:
        raise CandidateRejected(reason)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=True,
                       allow_nan=False) + '\n').encode('ascii')


def safe_name(name):
    require(type(name) is str and 0 < len(name) <= 1024
            and re.fullmatch(r'[A-Za-z0-9_./-]+', name) is not None,
            'candidate_path_characters')
    path = PurePosixPath(name)
    require(not path.is_absolute() and str(path) == name
            and '..' not in path.parts and '.' not in name.split('/'),
            'candidate_path_not_canonical')
    return name


def selected(name):
    return name in EXACT or (name.startswith('packages/claw-hermes/')
                             and name.endswith('.py'))


def git(repo, *args, data=None):
    env = dict(os.environ)
    # A caller's Git environment must not redirect the explicit repository.
    for key in ('GIT_DIR', 'GIT_WORK_TREE', 'GIT_COMMON_DIR', 'GIT_INDEX_FILE',
                'GIT_OBJECT_DIRECTORY', 'GIT_ALTERNATE_OBJECT_DIRECTORIES',
                'GIT_NAMESPACE', 'GIT_REPLACE_REF_BASE'):
        env.pop(key, None)
    result = subprocess.run(['git', '--no-replace-objects', '-C', str(repo), *args],
                            input=data, capture_output=True, timeout=60,
                            env=env, check=False)
    require(result.returncode == 0, 'candidate_git_failed')
    return result.stdout


def commit(repo, revision):
    require(type(revision) is str and re.fullmatch('[0-9a-f]{40}', revision) is not None,
            'candidate_full_commit_required')
    require(git(repo, 'rev-parse', '--verify', revision + '^{commit}').decode().strip()
            == revision, 'candidate_commit_mismatch')


def tree(repo, revision, choose):
    rows = git(repo, 'ls-tree', '-r', '-l', '-z', revision).split(b'\0')
    result = {}; folded = set(); total = 0
    for row in rows:
        if not row:
            continue
        metadata, encoded = row.split(b'\t', 1)
        name = encoded.decode('utf-8')
        if not choose(name):
            continue
        safe_name(name)
        mode, kind, oid, size = metadata.decode('ascii').split()
        require(kind == 'blob' and mode in ('100644', '100755'),
                'candidate_regular_source_only')
        require(name.casefold() not in folded, 'candidate_case_collision')
        require(re.fullmatch('[0-9a-f]{40}', oid) is not None,
                'candidate_git_object_format')
        length = int(size)
        require(0 <= length <= MAX_FILE, 'candidate_file_limit')
        total += length
        require(total <= MAX_TOTAL and len(result) < MAX_FILES, 'candidate_source_limit')
        folded.add(name.casefold())
        result[name] = {'gitBlob': oid, 'mode': int(mode, 8) & 0o777, 'bytes': length}
    return dict(sorted(result.items()))


def _marker_key(marker):
    return tuple(marker[k] for k in ('nativeFeature', 'path', 'gitBlob', 'fileSha256',
        'detector', 'byteStart', 'byteEnd', 'matchSha256'))


def _native_reviews(native_feature):
    if native_feature is None:
        return ()  # Harness blobs never have a reviewed-marker exception.
    require(type(native_feature) is str and native_feature == NATIVE_FEATURE
            and all(m['nativeFeature'] == native_feature for m in REVIEWED_NATIVE_MARKERS),
            'candidate_reviewed_native_revision')
    return REVIEWED_NATIVE_MARKERS


def _scan_credentials(name, row, data, *, native_feature=None):
    """Keep the original scan; review only exact immutable native occurrences."""
    from ci_check import PATTERNS, credential_hits
    hits = credential_hits(data)
    reviewed = [m for m in _native_reviews(native_feature) if m['path'] == name]
    wanted = {_marker_key(m): m for m in reviewed}
    require(len(wanted) == len(reviewed), 'candidate_reviewed_marker_duplicate')
    file_hash = digest(data)
    require(all(m['gitBlob'] == row['gitBlob'] and m['fileSha256'] == file_hash
                for m in reviewed), 'candidate_reviewed_source_changed')
    seen = set()
    for detector in hits:
        # credential_hits summarizes names; finditer checks EVERY occurrence,
        # including a second match of a detector already represented above.
        require(detector in PATTERNS, 'candidate_credential_detector_changed')
        for match in PATTERNS[detector].finditer(data):
            identity = (native_feature, name, row['gitBlob'], file_hash, detector,
                        match.start(), match.end(), digest(match.group()))
            require(identity in wanted and identity not in seen,
                    'candidate_credential_pattern')
            seen.add(identity)
    require(seen == set(wanted), 'candidate_reviewed_marker_missing')
    # Only fixed safe metadata is returned. Neither matched bytes nor context
    # snippets from source are written into the manifest or diagnostics.
    return [dict(wanted[key]) for key in sorted(seen)]


def blobs(repo, entries, *, native_feature=None, scan_private=True):
    # Same bounded public-source scanners used by the existing exporter/CI.
    from ci_check import private_path
    expected = [_marker_key(m) for m in _native_reviews(native_feature)]
    request = ''.join(row['gitBlob'] + '\n' for row in entries.values()).encode('ascii')
    raw = git(repo, 'cat-file', '--batch', data=request)
    require(len(raw) <= MAX_TOTAL + MAX_FILES * 100, 'candidate_batch_limit')
    cursor = 0; result = {}; reviewed = []
    for name, row in entries.items():
        end = raw.find(b'\n', cursor)
        require(end != -1, 'candidate_blob_header')
        header = raw[cursor:end].decode('ascii').split()
        require(header == [row['gitBlob'], 'blob', str(row['bytes'])],
                'candidate_blob_identity')
        cursor = end + 1
        data = raw[cursor:cursor + row['bytes']]; cursor += row['bytes']
        require(len(data) == row['bytes'] and raw[cursor:cursor + 1] == b'\n',
                'candidate_blob_length')
        cursor += 1
        require(b'\0' not in data, 'candidate_binary_source')
        require(not scan_private or not private_path(name), 'candidate_private_path')
        reviewed.extend(_scan_credentials(name, row, data, native_feature=native_feature))
        result[name] = data
    require(cursor == len(raw), 'candidate_extra_blob_output')
    require(sorted(_marker_key(m) for m in reviewed) == sorted(expected),
            'candidate_reviewed_marker_inventory')
    return result, reviewed


def unique_json(raw):
    def pairs(items):
        value = {}
        for key, item in items:
            require(key not in value, 'candidate_duplicate_json_key')
            value[key] = item
        return value
    return json.loads(raw, object_pairs_hook=pairs,
                      parse_constant=lambda _: (_ for _ in ()).throw(
                          CandidateRejected('candidate_nonfinite_json')))


def source(repo, revision, native_repo):
    commit(repo, revision); commit(native_repo, NATIVE_FEATURE)
    inventory = tree(repo, revision, lambda n: selected(n) or n == DEPENDENCY_RECORD)
    require(EXACT | REQUIRED_MODULES | {DEPENDENCY_RECORD} <= set(inventory),
            'candidate_required_source_missing')
    harness, harness_reviews = blobs(repo, inventory)
    require(not harness_reviews, 'candidate_harness_marker_review_forbidden')
    record_raw = harness.pop(DEPENDENCY_RECORD)
    record_meta = inventory.pop(DEPENDENCY_RECORD)
    record = unique_json(record_raw)
    require(type(record) is dict and type(record.get('nativeExitCode')) is int
            and record.get('nativeExitCode') == 0
            and record.get('sourceBytesUnchanged') is True
            and record.get('installedBytesMatchPriorAcceptedTarget') is True
            and type(record.get('sources')) is dict, 'candidate_dependency_record')
    dependencies = {}
    for name, value in record['sources'].items():
        if not name.startswith('dependencies/'):
            continue
        name = safe_name(name.removeprefix('dependencies/'))
        require(type(value) is str and re.fullmatch('[0-9a-f]{64}', value) is not None,
                'candidate_dependency_digest')
        dependencies[name] = value
    require(len(dependencies) == DEPENDENCY_COUNT
            and len({n.casefold() for n in dependencies}) == DEPENDENCY_COUNT,
            'candidate_dependency_inventory')
    envelope = unique_json(harness[NATIVE_MANIFEST])
    require(type(envelope) is dict and type(envelope.get('schema')) is int
            and envelope.get('schema') == 1
            and envelope.get('nativeFeature') == NATIVE_FEATURE
            and type(envelope.get('sources')) is dict
            and len(envelope['sources']) == NATIVE_COUNT, 'candidate_native_envelope')
    expected = envelope['sources']
    for name, value in expected.items():
        safe_name(name)
        require(type(value) is str and re.fullmatch('[0-9a-f]{64}', value) is not None,
                'candidate_native_digest')
    native_inventory = tree(native_repo, NATIVE_FEATURE, lambda n: n in expected)
    require(set(native_inventory) == set(expected), 'candidate_native_sources_missing')
    native, native_reviews = blobs(native_repo, native_inventory, native_feature=NATIVE_FEATURE)
    require({name: digest(data) for name, data in native.items()} == expected,
            'candidate_native_source_changed')
    payload = dict(harness)
    metadata = {n: {**row, 'repository': 'harness', 'sha256': digest(harness[n])}
                for n, row in inventory.items()}
    for name, data in native.items():
        payload['native/' + name] = data
        metadata['native/' + name] = {**native_inventory[name], 'repository': 'native',
                                      'sha256': digest(data)}
    dependency_bytes = canonical(dependencies)
    payload['accepted-dependencies.json'] = dependency_bytes
    metadata['accepted-dependencies.json'] = {
        'repository': 'generated-reference', 'gitBlob': None, 'mode': 0o644,
        'bytes': len(dependency_bytes), 'sha256': digest(dependency_bytes)}
    require(len(payload) <= MAX_FILES and sum(map(len, payload.values())) <= MAX_TOTAL,
            'candidate_source_limit')
    dependency_proof = {
        'sourceRecord': DEPENDENCY_RECORD, 'recordGitBlob': record_meta['gitBlob'],
        'recordSha256': digest(record_raw), 'inventoryFile': 'accepted-dependencies.json',
        'inventorySha256': digest(dependency_bytes), 'fileCount': DEPENDENCY_COUNT,
        'bytesIncluded': False, 'installedBytesVerifiedNow': False,
        'target': 'Linux x86_64 CPython 3.12',
    }
    return (dict(sorted(payload.items())), dict(sorted(metadata.items())),
            dependency_proof, native_reviews)


def stamp(revision):
    return json.dumps({'harnessCommit': revision, 'nativeFeature': NATIVE_FEATURE},
                      sort_keys=True, separators=(',', ':'))


def archive_bytes(payload, metadata, revision):
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode='w', format=tarfile.PAX_FORMAT,
                      pax_headers={'comment': stamp(revision)}) as archive:
        for name, data in sorted(payload.items()):
            safe_name(name)
            info = tarfile.TarInfo(PREFIX + name)
            info.mode = metadata[name]['mode']; info.size = len(data)
            info.uid = info.gid = info.mtime = 0
            info.uname = info.gname = ''
            archive.addfile(info, io.BytesIO(data))
    return stream.getvalue()


def verify_archive(raw, expected, revision):
    """Inspect exact bytes; no extraction or execution, including archive links."""
    require(type(raw) is bytes and 0 < len(raw) <= MAX_ARCHIVE, 'candidate_archive_size')
    require(0 < len(expected) <= MAX_FILES, 'candidate_archive_inventory')
    found = set(); folded = set(); total = 0
    try:
        with tarfile.open(fileobj=io.BytesIO(raw), mode='r:') as archive:
            require(archive.pax_headers == {'comment': stamp(revision)},
                    'candidate_archive_revision')
            for member in archive:
                name = safe_name(member.name)
                require(name.startswith(PREFIX), 'candidate_archive_prefix')
                name = name[len(PREFIX):]
                require(name in expected and name.casefold() not in folded,
                        'candidate_archive_members')
                require(member.type in (tarfile.REGTYPE, tarfile.AREGTYPE)
                        and not member.linkname and not member.sparse,
                        'candidate_archive_regular_only')
                require(set(member.pax_headers) <= {'comment', 'path'}
                        and member.pax_headers.get('comment') == stamp(revision)
                        and member.pax_headers.get('path', member.name) == member.name,
                        'candidate_archive_pax')
                row = expected[name]
                require(member.mode == row['mode'] and member.mode in (0o644, 0o755)
                        and member.uid == member.gid == member.mtime == 0
                        and not member.uname and not member.gname
                        and member.size == row['bytes'] and member.size <= MAX_FILE,
                        'candidate_archive_metadata')
                handle = archive.extractfile(member)
                require(handle is not None, 'candidate_archive_missing_data')
                with handle:
                    data = handle.read(MAX_FILE + 1)
                require(len(data) == member.size and digest(data) == row['sha256'],
                        'candidate_archive_digest')
                found.add(name); folded.add(name.casefold()); total += member.size
                require(total <= MAX_TOTAL, 'candidate_archive_total')
            require(len(raw) - archive.offset >= 1024 and not any(raw[archive.offset:]),
                    'candidate_archive_trailing_payload')
    except (tarfile.TarError, OSError, UnicodeError) as exc:
        raise CandidateRejected('candidate_archive_unreadable') from exc
    require(found == set(expected), 'candidate_archive_incomplete')
    return {'sourceFileCount': len(found), 'sourceBytes': total, 'archiveBytes': len(raw),
            'archiveSha256': digest(raw)}


def build(repo, revision, native_repo, destination):
    repo = Path(repo).resolve(); native_repo = Path(native_repo).resolve()
    destination = Path(destination)
    require(destination.is_absolute() and destination == destination.resolve()
            and not any(p.is_symlink() for p in (destination, *destination.parents)),
            'candidate_destination_canonical')
    base = repo / 'scratch' / 'projected-candidates'
    require(destination.is_relative_to(base) and destination != base,
            'candidate_ignored_scratch_only')
    require(not destination.exists(), 'candidate_destination_must_be_absent')
    # Confirm the repository actually ignores the destination, not merely its name.
    relative = destination.relative_to(repo).as_posix() + '/'
    require(git(repo, 'check-ignore', '--no-index', '--stdin', data=(relative + '\n').encode()).strip(),
            'candidate_destination_not_ignored')
    payload, metadata, dependency_proof, native_reviews = source(repo, revision, native_repo)
    raw = archive_bytes(payload, metadata, revision)
    checked = verify_archive(raw, metadata, revision)
    manifest = {
        'schemaVersion': 1, 'kind': 'PROJECTED_STARTUP_SOURCE_CANDIDATE_NOT_INSTALLED',
        'harnessCommit': revision, 'nativeFeature': NATIVE_FEATURE,
        'archive': ARCHIVE, 'prefix': PREFIX, **checked,
        'nativeSourceFileCount': NATIVE_COUNT,
        'harnessSourceFileCount': len(payload) - NATIVE_COUNT - 1,
        'fileManifest': metadata, 'dependencies': dependency_proof,
        'installed': False, 'executionAuthorized': False,
        'privilegedExecutionTested': False, 'positiveProjectedReadinessAccepted': False,
        'finiteWorkExecuted': False, 'pythonIncluded': False, 'realModelCalls': 0,
        'credentialScan': {'existingPatternsApplied': True,
                           'reviewedNativeMarkerCount': len(native_reviews),
                           'reviewedNativeMarkers': native_reviews},
        'scanScope': 'Existing bounded credential/private-path scanners; not a complete security audit',
    }
    plan = {
        'schemaVersion': 1, 'state': 'REVIEW_REQUIRED_NOT_EXECUTABLE',
        'harnessCommit': revision, 'nativeFeature': NATIVE_FEATURE,
        'archiveSha256': checked['archiveSha256'],
        'installed': False, 'executionAuthorized': False,
        'fixedEntrypoints': ['scripts/run_supervised_retained.py',
                             'scripts/run_retained_projected.py',
                             'scripts/run_state_volume_worker.py'],
        'interpreterRequired': '/usr/bin/python3.12',
        'targetPlatform': 'Linux x86_64; initial host user namespace',
        'freshWorkerRequired': True,
        'deadlineLimitsSeconds': {'workerIdle': 120, 'maximumChildWait': 60,
                                 'reservedStopMargin': 15},
        'suggestedFreshPaths': {'installation': '/opt/alaz-r153a1',
                                'state': '/srv/alaz-r153a1',
                                'cgroupParent': '/sys/fs/cgroup/alaz-r153a1'},
        'unmetGates': [
            'Designate and authorize exact disposable installation and invocation',
            'Verify installed source bytes and root-controlled ancestry',
            'Supply and verify all accepted dependency bytes and trusted interpreter',
            'Produce retained receipt via original finite owner on the exact ext4 image',
            'Derive live supervisor, namespace, cgroup, fence, mount and principal binding',
            'Start a fresh mount worker; child deadline plus stop margin must fit its remaining lifetime',
            'Qualify fixed supervised projected readiness before enabling work',
        ],
        'failurePolicy': 'Retain uncertain image/lease/fence/evidence; no replay, forced detach or automatic repair',
        'historicalDeniedOperationsMayBeRetried': False,
        'privateStateOrCredentialsIncluded': False,
    }
    # Exclusive publication. Partial output is retained and never overwritten.
    destination.mkdir(parents=True, exist_ok=False)
    outputs = {ARCHIVE: raw, 'manifest.json': canonical(manifest),
               'install-plan.json': canonical(plan)}
    for name, data in outputs.items():
        with (destination / name).open('xb') as handle:
            handle.write(data)
        require((destination / name).read_bytes() == data, 'candidate_readback_mismatch')
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--commit', required=True)
    parser.add_argument('--native-repository', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        manifest = build(ROOT, args.commit, args.native_repository, args.output)
    except (CandidateRejected, OSError, ValueError, subprocess.SubprocessError) as exc:
        print(json.dumps({'result': 'REFUSED', 'reasonType': type(exc).__name__,
                          'reason': str(exc) if isinstance(exc, CandidateRejected)
                          else 'candidate_local_io_or_parse_failed',
                          'installed': False, 'executionAuthorized': False}), file=sys.stderr)
        return 2
    keys = ('harnessCommit', 'nativeFeature', 'sourceFileCount', 'nativeSourceFileCount',
            'archiveSha256', 'installed', 'executionAuthorized')
    print(json.dumps({'result': 'EXPORTED_SOURCE_ONLY', **{k: manifest[k] for k in keys}}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
