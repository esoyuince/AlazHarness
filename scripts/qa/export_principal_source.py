"""Export a pinned broker source candidate. NEVER install, elevate or execute it.

Uses Git archive; validates every member against immutable Git blobs before
publishing into a new ignored scratch directory. Python/dependencies, accounts,
private configuration and vendor Gateway checkout are NOT part of this bundle.
"""
from __future__ import annotations
import argparse
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import tarfile

ROOT = Path(__file__).resolve().parents[2]
PREFIX = 'alazharness-broker/'
EXPORTS = ('LICENSE', 'SECURITY.md', 'docs/THIRD-PARTY.md', 'sources.lock.json',
           'config/components.lock.json', 'packages',
           'scripts/run_principal_broker.py', 'scripts/run_principal_broker_target.py',
           'scripts/run_provider_broker.py')
REQUIRED = set(EXPORTS) - {'packages'} | {
    'packages/claw-hermes/principal_launch.py',
    'packages/claw-hermes/principal_target.py',
    'packages/claw-hermes/provider_broker.py',
    'packages/claw-hermes/broker_budget.py'}
MAX_FILE = 2 * 1024 * 1024
MAX_TOTAL = 16 * 1024 * 1024
MAX_ARCHIVE = 32 * 1024 * 1024


class ExportRejected(ValueError):
    pass


def require(ok, reason):
    if not ok:
        raise ExportRejected(reason)


def git(repo, *args):
    result = subprocess.run(['git', '-C', str(repo), *args], capture_output=True,
                            timeout=60, check=False)
    require(result.returncode == 0, 'export_git_failed')
    return result.stdout


def safe_name(name):
    require(type(name) is str and bool(name) and len(name) <= 1024
            and re.fullmatch(r'[A-Za-z0-9_./-]+', name) is not None,
            'export_path_characters')
    p = PurePosixPath(name)
    require(not p.is_absolute() and '..' not in p.parts and '.' not in name.split('/')
            and str(p) == name, 'export_path_not_canonical')
    return name


def selected(name):
    return any(name == item or name.startswith(item + '/') for item in EXPORTS)


def source_inventory(repo, revision):
    require(type(revision) is str and re.fullmatch(r'[0-9a-f]{40}', revision) is not None,
            'export_full_commit_required')
    require(git(repo, 'rev-parse', '--verify', revision + '^{commit}').decode().strip()
            == revision, 'export_commit_mismatch')
    sys.path.insert(0, str(ROOT / 'scripts'))
    from ci_check import credential_hits, private_path
    rows = git(repo, 'ls-tree', '-r', '-z', revision, '--', *EXPORTS).split(b'\0')
    expected = {}; case_names = set(); total = 0
    for row in rows:
        if not row:
            continue
        metadata, encoded = row.split(b'\t', 1)
        mode, kind, oid = metadata.decode('ascii').split()
        name = safe_name(encoded.decode('utf-8'))
        require(selected(name) and not private_path(name), 'export_scope_or_private_path')
        require(name.casefold() not in case_names, 'export_duplicate_path')
        case_names.add(name.casefold())
        require(kind == 'blob' and mode in ('100644', '100755'), 'export_regular_source_only')
        data = git(repo, 'cat-file', 'blob', oid)
        require(len(data) <= MAX_FILE and b'\0' not in data, 'export_large_or_binary')
        require(not credential_hits(data), 'export_credential_pattern')
        total += len(data)
        require(total <= MAX_TOTAL, 'export_total_limit')
        expected[name] = {'gitBlob': oid, 'mode': int(mode, 8) & 0o777,
                          'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
    require(REQUIRED <= set(expected), 'export_required_source_missing')
    return dict(sorted(expected.items()))


def verify_archive(raw, expected, revision):
    """Inspect only; no extractall, symlink following or root metadata adoption."""
    require(type(raw) is bytes and 0 < len(raw) <= MAX_ARCHIVE, 'export_archive_size')
    require(bool(expected), 'export_empty_inventory')
    directories = {PREFIX.rstrip('/')}
    for name in expected:
        safe_name(name)
        directories.update(str(p) for p in PurePosixPath(PREFIX + name).parents if str(p) != '.')
    found = set(); all_names = set(); total = 0
    try:
        with tarfile.open(fileobj=io.BytesIO(raw), mode='r:') as archive:
            require(archive.pax_headers.get('comment') == revision, 'export_archive_commit')
            for member in archive:
                name = member.name[:-1] if member.isdir() and member.name.endswith('/') else member.name
                clean = safe_name(name)
                require(clean.casefold() not in all_names, 'export_duplicate_member')
                all_names.add(clean.casefold())
                require(len(all_names) <= len(expected) + len(directories), 'export_member_limit')
                if member.isdir():
                    require(clean in directories and member.mode == 0o755,
                            'export_directory_metadata')
                    continue
                require(member.type in (tarfile.REGTYPE, tarfile.AREGTYPE)
                        and not member.linkname and not member.sparse,
                        'export_archive_regular_only')
                require(clean.startswith(PREFIX), 'export_member_outside_prefix')
                name = clean[len(PREFIX):]
                require(name in expected, 'export_unexpected_member')
                wanted = expected[name]
                require(member.size == wanted['bytes'] and 0 <= member.size <= MAX_FILE
                        and member.mode == wanted['mode'], 'export_member_metadata')
                total += member.size
                require(total <= MAX_TOTAL, 'export_total_limit')
                handle = archive.extractfile(member)
                require(handle is not None, 'export_missing_member_data')
                with handle:
                    data = handle.read(MAX_FILE + 1)
                require(len(data) == member.size and hashlib.sha256(data).hexdigest()
                        == wanted['sha256'], 'export_member_digest')
                found.add(name)
            require(len(raw) - archive.offset >= 1024 and not any(raw[archive.offset:]),
                    'export_trailing_payload')
    except (tarfile.TarError, OSError, UnicodeError) as exc:
        raise ExportRejected('export_archive_unreadable') from exc
    require(found == set(expected), 'export_archive_incomplete')
    return {'files': len(found), 'sourceBytes': total,
            'archiveBytes': len(raw), 'archiveSha256': hashlib.sha256(raw).hexdigest()}


def build(repo, revision, destination):
    repo = Path(repo).resolve()
    destination = Path(destination)
    require(destination.is_absolute() and destination == destination.resolve()
            and not any(p.is_symlink() for p in (destination, *destination.parents)),
            'export_destination_canonical')
    require(destination.is_relative_to(repo / 'scratch' / 'principal-install')
            and destination != repo / 'scratch' / 'principal-install',
            'export_ignored_scratch_only')
    require(not destination.exists(), 'export_destination_must_be_absent')
    expected = source_inventory(repo, revision)
    raw = git(repo, '-c', 'core.autocrlf=false', '-c', 'core.eol=lf',
              '-c', 'tar.umask=0022', 'archive', '--format=tar',
              '--prefix=' + PREFIX, revision, '--', *EXPORTS)
    verified = verify_archive(raw, expected, revision)
    manifest = {'schemaVersion': 1, 'kind': 'BROKER_SOURCE_CANDIDATE_NOT_INSTALLED',
                'sourceCommit': revision, 'archive': 'broker-source.tar', 'prefix': PREFIX,
                **verified, 'fileManifest': expected,
                'scanScope': 'bounded existing credential patterns; not a complete security audit',
                'pythonAndDependenciesIncluded': False, 'vendorGatewayIncluded': False,
                'installed': False, 'privilegedExecutionTested': False,
                'twoHostUidAccepted': False, 'ipcV2Enabled': False, 'realModelCalls': 0}
    # No overwrite and no rollback of partial output. On interruption inspect it.
    destination.mkdir(parents=True, exist_ok=False)
    with (destination / 'broker-source.tar').open('xb') as stream:
        stream.write(raw)
    with (destination / 'manifest.json').open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(manifest, stream, sort_keys=True, indent=2); stream.write('\n')
    require((destination / 'broker-source.tar').read_bytes() == raw, 'export_readback_mismatch')
    require(json.loads((destination / 'manifest.json').read_text(encoding='utf-8'))
            == manifest, 'export_manifest_readback')
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--commit', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        manifest = build(ROOT, args.commit, args.output)
    except (ExportRejected, OSError, subprocess.SubprocessError) as exc:
        print(json.dumps({'result': 'REFUSED', 'reasonType': type(exc).__name__,
                          'installationPerformed': False}), file=sys.stderr)
        return 2
    print(json.dumps({'result': 'EXPORTED_SOURCE_ONLY',
                      **{k: manifest[k] for k in ('sourceCommit', 'files', 'sourceBytes',
                                                 'archiveSha256', 'installed', 'twoHostUidAccepted')}}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
