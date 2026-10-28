"""Verify exact P2 service source inputs without installing or running them.

All four externally reviewed pins are mandatory. This tool verifies source
bytes and dependency REFERENCES only. It neither probes runtimes nor verifies
installed dependencies, and provides no installation or execution operation.
prepare_bytes operates on in-memory bytes. The file-reading CLI reuses the
Linux/POSIX descriptor reader; Windows file-CLI support is not qualified.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import stat
import sys
import tarfile
import types
from dataclasses import dataclass
from functools import lru_cache
from types import MappingProxyType

BUILDER_SHA256 = '54c83be327e3e9e08e0a149b096f5a4f873364461069711a4c2d3f20e862f6cf'
MANIFEST_LIMIT = 2 * 1024 * 1024


class VerificationRejected(ValueError):
    pass


@lru_cache(maxsize=1)
def _builder():
    path = Path(__file__).absolute().with_name('build_service_candidate.py')
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise VerificationRejected('service_builder_symlink')
    fd = os.open(path, os.O_RDONLY | getattr(os, 'O_CLOEXEC', 0) | getattr(os, 'O_NOFOLLOW', 0))
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or before.st_size > MANIFEST_LIMIT:
            raise VerificationRejected('service_builder_file')
        with os.fdopen(fd, 'rb', closefd=False) as stream:
            raw = stream.read(MANIFEST_LIMIT + 1)
        stamp = lambda s: (s.st_dev, s.st_ino, s.st_mode, s.st_uid, s.st_gid,
                           s.st_nlink, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
        if len(raw) != before.st_size or stamp(before) != stamp(os.fstat(fd)) or hashlib.sha256(raw).hexdigest() != BUILDER_SHA256:
            raise VerificationRejected('service_builder_changed')
    finally:
        os.close(fd)
    module = types.ModuleType('_alaz_reviewed_service_builder')
    module.__file__ = str(path)
    exec(compile(raw, str(path), 'exec'), module.__dict__)
    return module


@dataclass(frozen=True)
class PreparedCandidate:
    manifest_sha256: str
    archive_sha256: str
    harness_commit: str
    native_feature: str
    source: object
    source_modes: object
    dependencies: object
    dependency_inventory_sha256: str


def prepare_bytes(manifest_raw, archive_raw, *, expected_manifest_sha256,
                  expected_archive_sha256, expected_harness_commit, expected_native_feature):
    b = _builder()
    try:
        for value, length in ((expected_manifest_sha256, 64), (expected_archive_sha256, 64),
                              (expected_harness_commit, 40), (expected_native_feature, 40)):
            b._hex(value, length, 'service_external_pin')
        b.require(expected_native_feature == b.NATIVE_FEATURE, 'service_native_generation_pin')
        b.require(type(manifest_raw) is bytes and 0 < len(manifest_raw) <= MANIFEST_LIMIT
            and b.digest(manifest_raw) == expected_manifest_sha256, 'service_manifest_pin')
        b.require(type(archive_raw) is bytes and 0 < len(archive_raw) <= b.MAX_ARCHIVE
            and b.digest(archive_raw) == expected_archive_sha256, 'service_archive_pin')
        value = b.unique_json(manifest_raw)
        header = {'schemaVersion': 1, 'kind': b.KIND, 'harnessCommit': expected_harness_commit,
            'nativeFeature': expected_native_feature, 'archive': b.ARCHIVE, 'prefix': b.PREFIX,
            'scanScope': b.SCAN_SCOPE}
        fields = set(header) | set(b.boundaries()) | {'sourceFileCount', 'sourceBytes', 'archiveBytes',
            'archiveSha256', 'nativeSourceFileCount', 'harnessSourceFileCount', 'fileManifest',
            'dependencies', 'credentialScan'}
        b.require(type(value) is dict and set(value) == fields, 'service_manifest_fields')
        b.require(all(type(value[k]) is type(v) and value[k] == v for k, v in header.items()),
                  'service_manifest_header')
        b.require(b.canonical({k: value[k] for k in b.boundaries()}) == b.canonical(b.boundaries()),
                  'service_acceptance_claim')
        metadata = value['fileManifest']
        b.validate_metadata(metadata)
        checked = b.verify_archive(archive_raw, metadata, expected_harness_commit)
        counts = {**checked, 'nativeSourceFileCount': b.NATIVE_COUNT,
                  'harnessSourceFileCount': len(metadata) - b.NATIVE_COUNT - 1}
        b.require(all(type(value[k]) is type(v) and value[k] == v for k, v in counts.items()),
                  'service_manifest_counts')
        source = {}
        # verify_archive has already rejected all links, sparse entries, extra
        # members, oversized data and nonzero trailing payload. Never extract.
        with tarfile.open(fileobj=io.BytesIO(archive_raw), mode='r:') as archive:
            for member in archive:
                with archive.extractfile(member) as handle:
                    source[member.name[len(b.PREFIX):]] = handle.read(b.MAX_FILE + 1)
        dependencies, reviews = b.validate_payload(source, metadata, value['dependencies'])
        expected_scan = {'existingPatternsApplied': True, 'reviewedNativeMarkerCount': len(reviews),
                         'reviewedNativeMarkers': reviews}
        b.require(b.canonical(value['credentialScan']) == b.canonical(expected_scan),
                  'service_credential_scan_claim')
        return PreparedCandidate(expected_manifest_sha256, expected_archive_sha256,
            expected_harness_commit, expected_native_feature, MappingProxyType(source),
            MappingProxyType({name: row['mode'] for name, row in metadata.items()}),
            MappingProxyType(dependencies), b.digest(source['accepted-dependencies.json']))
    except (b.CandidateRejected, b._legacy().InstallationRejected) as exc:
        raise VerificationRejected(str(exc)) from None
    except (ValueError, TypeError, KeyError, UnicodeError, OverflowError, RecursionError, tarfile.TarError):
        raise VerificationRejected('service_input_parse_or_structure') from None


def verify_files(manifest_path, archive_path, **pins):
    b = _builder()
    manifest, _ = b._legacy()._read_path(manifest_path, MANIFEST_LIMIT)
    archive, _ = b._legacy()._read_path(archive_path, b.MAX_ARCHIVE)
    return prepare_bytes(manifest, archive, **pins)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', required=True)
    parser.add_argument('--archive', required=True)
    parser.add_argument('--expected-manifest-sha256', required=True)
    parser.add_argument('--expected-archive-sha256', required=True)
    parser.add_argument('--expected-harness-commit', required=True)
    parser.add_argument('--expected-native-feature', required=True)
    args = vars(parser.parse_args())
    try:
        candidate = verify_files(args.pop('manifest'), args.pop('archive'), **args)
    except (OSError, ValueError) as exc:
        print(json.dumps({'result': 'REFUSED', 'reason': str(exc) if isinstance(exc, VerificationRejected)
            else 'service_local_io_or_parse_failed', 'installed': False, 'executionAuthorized': False}), file=sys.stderr)
        return 2
    print(json.dumps({'result': 'VERIFIED_SERVICE_SOURCE_ONLY', 'harnessCommit': candidate.harness_commit,
        'nativeFeature': candidate.native_feature, 'manifestSha256': candidate.manifest_sha256,
        'archiveSha256': candidate.archive_sha256, 'sourceFileCount': len(candidate.source),
        **_builder().boundaries()}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
