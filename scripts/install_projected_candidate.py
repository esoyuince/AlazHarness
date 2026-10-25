"""Verify and exclusively install a reviewed source candidate on Linux.

No candidate code, dependency code, service, model, mount or package manager is
executed. The caller supplies exact approved hashes. Failed staging trees remain
for inspection; there is no overwrite, resume, rollback or cleanup operation.
"""
from __future__ import annotations

import argparse
import ctypes
import errno
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import platform
import re
import stat
import sys
import tarfile
import types
import uuid
from dataclasses import dataclass
from functools import lru_cache
from types import MappingProxyType

BUILDER_SHA256 = '97be4be2a0aec7a045fd099b1f56b12c58501e312777e1ad67fee45cbe601cc7'
PYTHON = '/usr/bin/python3.12'
MANIFEST_LIMIT = 2 * 1024 * 1024
DEPENDENCY_FILE_LIMIT = 32 * 1024 * 1024
DEPENDENCY_TOTAL_LIMIT = 256 * 1024 * 1024
RECEIPT = '.alaz-installation.json'
INITIAL_MAP = ['0', '0', '4294967295']


class InstallationRejected(ValueError):
    def __init__(self, reason, *, partial_path=None):
        super().__init__(reason)
        self.partial_path = partial_path


def require(ok, reason):
    if not ok:
        raise InstallationRejected(reason)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=True,
                       allow_nan=False) + '\n').encode('ascii')


def _hex(value, length, reason):
    require(type(value) is str and re.fullmatch('[0-9a-f]{' + str(length) + '}', value), reason)
    return value


def _absolute(value):
    raw = str(value)
    path = PurePosixPath(raw)
    require(path.is_absolute() and str(path) == raw and '..' not in path.parts
            and '\x00' not in raw and '\\' not in raw, 'installation_path_not_canonical')
    return path


def _stamp(info):
    return (info.st_dev, info.st_ino, info.st_mode, info.st_uid, info.st_gid,
            info.st_nlink, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def _trusted(info, directory):
    require((stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode))
            and info.st_uid == info.st_gid == 0 and not info.st_mode & 0o022,
            'installation_untrusted_ancestry_or_entry')
    if not directory:
        require(info.st_nlink == 1, 'installation_hardlink_refused')


def _directory(path, *, trusted):
    """Walk from / with nofollow directory descriptors, including every parent."""
    path = _absolute(path)
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW
    fd = os.open('/', flags)
    try:
        if trusted:
            _trusted(os.fstat(fd), True)
        for part in path.parts[1:]:
            child = os.open(part, flags, dir_fd=fd)
            os.close(fd)
            fd = child
            if trusted:
                _trusted(os.fstat(fd), True)
        return fd
    except BaseException:
        os.close(fd)
        raise


def _read_at(parent, name, maximum, *, trusted=False):
    fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK,
                 dir_fd=parent)
    try:
        before = os.fstat(fd)
        require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1,
                'installation_regular_single_link_required')
        require(0 <= before.st_size <= maximum, 'installation_file_limit')
        if trusted:
            _trusted(before, False)
        chunks = []
        remaining = maximum + 1
        while remaining:
            part = os.read(fd, min(1024 * 1024, remaining))
            if not part:
                break
            chunks.append(part)
            remaining -= len(part)
        data = b''.join(chunks)
        require(len(data) == before.st_size and len(data) <= maximum
                and _stamp(before) == _stamp(os.fstat(fd)), 'installation_file_changed')
        return data, before
    finally:
        os.close(fd)


def _read_path(path, maximum, *, trusted=False):
    path = _absolute(path)
    parent = _directory(path.parent, trusted=trusted)
    try:
        return _read_at(parent, path.name, maximum, trusted=trusted)
    finally:
        os.close(parent)


@lru_cache(maxsize=1)
def _builder():
    # -I omits the script directory. Import only the exact reviewed sibling,
    # using the already verified bytes rather than a second mutable file read.
    path = Path(__file__).absolute().with_name('build_projected_candidate.py')
    require(not any(p.is_symlink() for p in (path, *path.parents)),
            'installation_builder_symlink')
    flags = os.O_RDONLY | getattr(os, 'O_CLOEXEC', 0) | getattr(os, 'O_NOFOLLOW', 0)
    fd = os.open(path, flags)
    try:
        before = os.fstat(fd)
        require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1
                and before.st_size <= MANIFEST_LIMIT, 'installation_builder_file')
        with os.fdopen(fd, 'rb', closefd=False) as stream:
            raw = stream.read(MANIFEST_LIMIT + 1)
        require(len(raw) == before.st_size and _stamp(before) == _stamp(os.fstat(fd)),
                'installation_builder_file_changed')
    finally:
        os.close(fd)
    require(digest(raw) == BUILDER_SHA256, 'installation_builder_changed')
    module = types.ModuleType('_alaz_reviewed_candidate_builder')
    module.__file__ = str(path)
    exec(compile(raw, str(path), 'exec'), module.__dict__)
    return module


def _expected_directories(files):
    result = set()
    for name in files:
        for parent in PurePosixPath(name).parents:
            if str(parent) != '.':
                result.add(str(parent))
    return result


def _namespace(files):
    directories = _expected_directories(files)
    require(not set(files) & directories, 'installation_file_directory_collision')
    names = set(files) | directories
    require(len({name.casefold() for name in names}) == len(names),
            'installation_path_case_collision')
    return directories


def _tree(fd, expected, *, trusted, modes=None, maximum=DEPENDENCY_FILE_LIMIT,
          total_limit=DEPENDENCY_TOTAL_LIMIT):
    """Read exact files by descriptors; reject extras, links and empty extras."""
    allowed_dirs = _namespace(expected)
    result = {}
    folded = set()
    total = 0
    visited = 0

    def visit(directory, prefix):
        nonlocal total, visited
        if trusted:
            _trusted(os.fstat(directory), True)
        with os.scandir(directory) as entries:
            components = []
            for entry in entries:
                visited += 1
                require(visited <= len(expected) + len(allowed_dirs),
                        'installation_extra_entry_limit')
                components.append(entry.name)
        for component in sorted(components):
            name = prefix + component
            require(_builder().safe_name(name) == name, 'installation_entry_name')
            require(name.casefold() not in folded, 'installation_case_collision')
            folded.add(name.casefold())
            info = os.stat(component, dir_fd=directory, follow_symlinks=False)
            if stat.S_ISDIR(info.st_mode):
                require(name in allowed_dirs, 'installation_extra_directory')
                child = os.open(component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
                                | os.O_CLOEXEC, dir_fd=directory)
                try:
                    require((info.st_dev, info.st_ino) ==
                            (os.fstat(child).st_dev, os.fstat(child).st_ino),
                            'installation_directory_changed')
                    visit(child, name + '/')
                finally:
                    os.close(child)
            else:
                require(name in expected, 'installation_extra_file')
                data, actual = _read_at(directory, component, maximum, trusted=trusted)
                require(digest(data) == expected[name], 'installation_file_digest')
                if modes is not None:
                    require(stat.S_IMODE(actual.st_mode) == modes[name],
                            'installation_file_mode')
                total += len(data)
                require(total <= total_limit, 'installation_tree_limit')
                result[name] = data
    visit(fd, '')
    require(set(result) == set(expected), 'installation_missing_file')
    return result


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
                  expected_archive_sha256, expected_harness_commit):
    """Pure bounded verification. Does not inspect trust or authorize execution."""
    b = _builder()
    _hex(expected_manifest_sha256, 64, 'installation_manifest_pin')
    _hex(expected_archive_sha256, 64, 'installation_archive_pin')
    _hex(expected_harness_commit, 40, 'installation_commit_pin')
    require(type(manifest_raw) is bytes and len(manifest_raw) <= MANIFEST_LIMIT
            and digest(manifest_raw) == expected_manifest_sha256, 'installation_manifest_digest')
    require(type(archive_raw) is bytes and len(archive_raw) <= b.MAX_ARCHIVE
            and digest(archive_raw) == expected_archive_sha256, 'installation_archive_digest')
    manifest = b.unique_json(manifest_raw)
    require(type(manifest) is dict and type(manifest.get('schemaVersion')) is int
            and manifest['schemaVersion'] == 1
            and manifest.get('kind') == 'PROJECTED_STARTUP_SOURCE_CANDIDATE_NOT_INSTALLED'
            and manifest.get('harnessCommit') == expected_harness_commit
            and manifest.get('nativeFeature') == b.NATIVE_FEATURE
            and manifest.get('archive') == b.ARCHIVE and manifest.get('prefix') == b.PREFIX,
            'installation_manifest_schema')
    require(all(manifest.get(k) is False for k in ('installed', 'executionAuthorized',
        'privilegedExecutionTested', 'positiveProjectedReadinessAccepted',
        'finiteWorkExecuted', 'pythonIncluded')) and type(manifest.get('realModelCalls')) is int
        and manifest['realModelCalls'] == 0, 'installation_manifest_claims')
    metadata = manifest.get('fileManifest')
    require(type(metadata) is dict and 0 < len(metadata) <= b.MAX_FILES,
            'installation_source_inventory')
    required = b.EXACT | b.REQUIRED_MODULES | {'accepted-dependencies.json'}
    require(required <= set(metadata), 'installation_required_sources')
    native = {}
    harness = 0
    folded = set()
    for name, row in metadata.items():
        b.safe_name(name)
        require(name.casefold() not in folded, 'installation_source_collision')
        folded.add(name.casefold())
        require(type(row) is dict and set(row) == {'gitBlob', 'mode', 'bytes', 'repository', 'sha256'},
                'installation_source_row')
        require(type(row['mode']) is int and row['mode'] in (0o644, 0o755)
                and type(row['bytes']) is int and 0 <= row['bytes'] <= b.MAX_FILE,
                'installation_source_metadata')
        _hex(row['sha256'], 64, 'installation_source_digest')
        if name == 'accepted-dependencies.json':
            require(row['repository'] == 'generated-reference' and row['gitBlob'] is None,
                    'installation_reference_metadata')
        else:
            _hex(row['gitBlob'], 40, 'installation_source_blob')
            if name.startswith('native/'):
                require(row['repository'] == 'native', 'installation_native_metadata')
                native[name.removeprefix('native/')] = row['sha256']
            else:
                require(b.selected(name) and row['repository'] == 'harness',
                        'installation_harness_metadata')
                harness += 1
    checked = b.verify_archive(archive_raw, metadata, expected_harness_commit)
    _namespace(metadata)
    require(all(type(manifest.get(k)) is type(v) and manifest.get(k) == v
                for k, v in checked.items()) and len(native) == b.NATIVE_COUNT
            and manifest.get('nativeSourceFileCount') == b.NATIVE_COUNT
            and manifest.get('harnessSourceFileCount') == harness,
            'installation_inventory_count')
    source = {}
    with tarfile.open(fileobj=io.BytesIO(archive_raw), mode='r:') as archive:
        for member in archive:
            with archive.extractfile(member) as stream:
                source[member.name.removeprefix(b.PREFIX)] = stream.read(b.MAX_FILE + 1)
    envelope = b.unique_json(source[b.NATIVE_MANIFEST])
    require(type(envelope) is dict and type(envelope.get('schema')) is int
            and envelope.get('schema') == 1
            and envelope.get('nativeFeature') == b.NATIVE_FEATURE
            and envelope.get('sources') == native, 'installation_native_envelope')
    reference = source['accepted-dependencies.json']
    dependencies = b.unique_json(reference)
    require(type(dependencies) is dict and len(dependencies) == b.DEPENDENCY_COUNT,
            'installation_dependency_inventory')
    for name, value in dependencies.items():
        b.safe_name(name)
        _hex(value, 64, 'installation_dependency_digest')
    require(len({name.casefold() for name in dependencies}) == len(dependencies),
            'installation_dependency_collision')
    _namespace(dependencies)
    proof = manifest.get('dependencies')
    require(type(proof) is dict and set(proof) == {'sourceRecord', 'recordGitBlob',
            'recordSha256', 'inventoryFile', 'inventorySha256', 'fileCount',
            'bytesIncluded', 'installedBytesVerifiedNow', 'target'}
            and proof.get('sourceRecord') == b.DEPENDENCY_RECORD
            and proof.get('inventoryFile') == 'accepted-dependencies.json'
            and proof.get('inventorySha256') == digest(reference)
            and proof.get('fileCount') == b.DEPENDENCY_COUNT
            and proof.get('bytesIncluded') is False
            and proof.get('installedBytesVerifiedNow') is False
            and proof.get('target') == 'Linux x86_64 CPython 3.12',
            'installation_dependency_proof')
    _hex(proof['recordGitBlob'], 40, 'installation_dependency_record_blob')
    _hex(proof['recordSha256'], 64, 'installation_dependency_record_digest')
    return PreparedCandidate(expected_manifest_sha256, expected_archive_sha256,
        expected_harness_commit, b.NATIVE_FEATURE, MappingProxyType(source),
        MappingProxyType({name: row['mode'] for name, row in metadata.items()}),
        MappingProxyType(dependencies), digest(reference))


def _python(expected):
    _hex(expected, 64, 'installation_python_pin')
    raw, info = _read_path(PYTHON, 64 * 1024 * 1024, trusted=True)
    require(digest(raw) == expected and info.st_mode & 0o111,
            'installation_interpreter_digest_or_mode')
    return {'path': PYTHON, 'sha256': expected, 'device': info.st_dev, 'inode': info.st_ino,
            'uid': info.st_uid, 'gid': info.st_gid, 'mode': stat.S_IMODE(info.st_mode)}


def _actor():
    require(sys.platform == 'linux' and platform.machine() == 'x86_64'
            and sys.version_info[:2] == (3, 12) and sys.executable == PYTHON
            and sys.flags.isolated == 1 and sys.dont_write_bytecode
            and not sys.flags.optimize, 'installation_fixed_interpreter_required')
    require(os.getresuid() == (0, 0, 0) and os.getresgid() == (0, 0, 0),
            'installation_root_actor_required')
    require(Path('/proc/self/uid_map').read_text().split() == INITIAL_MAP
            and Path('/proc/self/gid_map').read_text().split() == INITIAL_MAP
            and os.readlink('/proc/self/ns/user') == os.readlink('/proc/1/ns/user'),
            'installation_initial_user_namespace_required')


def _absent(parent, name):
    try:
        os.stat(name, dir_fd=parent, follow_symlinks=False)
    except FileNotFoundError:
        return
    raise InstallationRejected('installation_destination_exists')


def _write_at(parent, name, data, mode):
    fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
                 | os.O_CLOEXEC, 0o600, dir_fd=parent)
    try:
        view = memoryview(data)
        while view:
            written = os.write(fd, view)
            require(written > 0, 'installation_short_write')
            view = view[written:]
        os.fchmod(fd, mode)
        os.fsync(fd)
    finally:
        os.close(fd)


def _materialize(root, files, modes):
    """Exclusive owned-tree byte writer, also used by explicitly unprivileged fixtures.

    This helper neither checks the privileged actor nor creates an installation
    receipt. Its caller must own an empty directory descriptor and validated data.
    """
    require(type(files) is dict and type(modes) is dict and set(files) == set(modes)
            and 0 < len(files) <= _builder().MAX_FILES + _builder().DEPENDENCY_COUNT,
            'installation_materialization_inventory')
    folded = set()
    for name, data in files.items():
        _builder().safe_name(name)
        require(name.casefold() not in folded and type(data) is bytes
                and type(modes[name]) is int and modes[name] in (0o644, 0o755),
                'installation_materialization_entry')
        folded.add(name.casefold())
    directories_needed = _namespace(files)
    with os.scandir(root) as entries:
        require(next(entries, None) is None, 'installation_stage_not_empty')
    directories = {}
    try:
        for name in sorted(directories_needed, key=lambda n: (n.count('/'), n)):
            parent, _, leaf = name.rpartition('/')
            pfd = directories[parent] if parent else root
            os.mkdir(leaf, 0o700, dir_fd=pfd)
            fd = os.open(leaf, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
                         | os.O_CLOEXEC, dir_fd=pfd)
            directories[name] = fd
            os.fchmod(fd, 0o755)
        for name, data in sorted(files.items()):
            parent, _, leaf = name.rpartition('/')
            _write_at(directories[parent] if parent else root, leaf, data, modes[name])
        for fd in directories.values():
            os.fsync(fd)
        os.fsync(root)
        _tree(root, {n: digest(data) for n, data in files.items()}, trusted=False,
              modes=modes, total_limit=DEPENDENCY_TOTAL_LIMIT + _builder().MAX_TOTAL)
    finally:
        for fd in directories.values():
            os.close(fd)


def _rename_noreplace(parent, source, destination):
    lib = ctypes.CDLL(None, use_errno=True)
    try:
        rename = lib.renameat2
    except AttributeError as exc:
        raise InstallationRejected('installation_atomic_publish_unavailable') from exc
    rename.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p,
                       ctypes.c_uint]
    rename.restype = ctypes.c_int
    if rename(parent, os.fsencode(source), parent, os.fsencode(destination), 1):
        code = ctypes.get_errno()
        raise InstallationRejected('installation_destination_exists' if code == errno.EEXIST
                                   else 'installation_atomic_publish_failed')


def preflight(candidate_directory, dependencies, *, expected_manifest_sha256,
              expected_archive_sha256, expected_harness_commit, expected_python_sha256):
    candidate_directory = _absolute(candidate_directory)
    raw, _ = _read_path(candidate_directory / 'manifest.json', MANIFEST_LIMIT)
    archive, _ = _read_path(candidate_directory / 'projected-source.tar', _builder().MAX_ARCHIVE)
    prepared = prepare_bytes(raw, archive, expected_manifest_sha256=expected_manifest_sha256,
        expected_archive_sha256=expected_archive_sha256,
        expected_harness_commit=expected_harness_commit)
    python = _python(expected_python_sha256)
    fd = _directory(dependencies, trusted=True)
    try:
        dependency_bytes = _tree(fd, prepared.dependencies, trusted=True)
    finally:
        os.close(fd)
    return prepared, dependency_bytes, python


def _receipt(prepared, dependency_bytes, python, destination, info):
    return {'schemaVersion': 1, 'kind': 'VERIFIED_PROJECTED_INSTALLATION',
        'destination': str(destination), 'sourceManifestSha256': prepared.manifest_sha256,
        'archiveSha256': prepared.archive_sha256, 'harnessCommit': prepared.harness_commit,
        'nativeFeature': prepared.native_feature, 'sourceFileCount': len(prepared.source),
        'dependencyFileCount': len(dependency_bytes),
        'dependencyInventorySha256': prepared.dependency_inventory_sha256,
        'python': python, 'rootDevice': info.st_dev, 'rootInode': info.st_ino,
        'sourceAndDependenciesReadBack': True, 'rootControlledAncestryVerified': True,
        'installed': True, 'executionAuthorized': False, 'projectedReadinessAccepted': False,
        'finiteWorkExecuted': False, 'realModelCalls': 0}


def _verify_receipt(raw, expected):
    receipt = _builder().unique_json(raw)
    require(canonical(receipt) == canonical(expected), 'installation_receipt_identity')


def install(candidate_directory, destination, dependencies, **pins):
    _actor()
    destination = _absolute(destination)
    require(destination.name and destination.parent != destination,
            'installation_destination_root_refused')
    prepared, dependency_bytes, python = preflight(candidate_directory, dependencies, **pins)
    parent = _directory(destination.parent, trusted=True)
    stage = '.' + destination.name + '.partial-' + uuid.uuid4().hex
    partial = str(destination.parent / stage)
    created = False
    published = False
    root = None
    try:
        _absent(parent, destination.name)
        os.mkdir(stage, 0o700, dir_fd=parent)
        created = True
        root = os.open(stage, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
                       dir_fd=parent)
        _trusted(os.fstat(root), True)
        files = dict(prepared.source)
        modes = dict(prepared.source_modes)
        files.update({'dependencies/' + n: data for n, data in dependency_bytes.items()})
        modes.update({'dependencies/' + n: 0o644 for n in dependency_bytes})
        _materialize(root, files, modes)
        _tree(root, {n: digest(data) for n, data in files.items()}, trusted=True, modes=modes,
              total_limit=DEPENDENCY_TOTAL_LIMIT + _builder().MAX_TOTAL)
        source_fd = _directory(dependencies, trusted=True)
        try:
            _tree(source_fd, prepared.dependencies, trusted=True)
        finally:
            os.close(source_fd)
        require(_python(pins['expected_python_sha256']) == python,
                'installation_interpreter_changed')
        info = os.fstat(root)
        receipt = _receipt(prepared, dependency_bytes, python, destination, info)
        receipt_raw = canonical(receipt)
        os.fchmod(root, 0o755)
        os.fsync(root)
        _rename_noreplace(parent, stage, destination.name)
        published = True
        os.fsync(parent)
        # Only a fully read-back, atomically published destination can receive
        # an accepted receipt. A failure keeps a receipt-less stage/final tree,
        # or a pending receipt that verification explicitly refuses as extra.
        pending_receipt = RECEIPT + '.pending'
        _write_at(root, pending_receipt, receipt_raw, 0o644)
        readback, _ = _read_at(root, pending_receipt, MANIFEST_LIMIT, trusted=True)
        require(readback == receipt_raw, 'installation_receipt_readback')
        os.fsync(root)
        _rename_noreplace(root, pending_receipt, RECEIPT)
        os.fsync(root)
        return {**receipt, 'receiptSha256': digest(receipt_raw)}
    except BaseException as exc:
        # Never delete or overwrite uncertain evidence, including a possible
        # final receipt if durability confirmation failed after its publication.
        if isinstance(exc, (KeyboardInterrupt, SystemExit)):
            raise
        reason = str(exc) if isinstance(exc, InstallationRejected) else 'installation_local_io_failed'
        raise InstallationRejected(reason, partial_path=(str(destination) if published else partial)
                                   if created else None) from exc
    finally:
        if root is not None:
            os.close(root)
        os.close(parent)


def verify_installed(candidate_directory, destination, dependencies, **pins):
    """Read-only installed-byte acceptance; no root actor or execution required."""
    prepared, dependency_bytes, python = preflight(candidate_directory, dependencies, **pins)
    destination = _absolute(destination)
    fd = _directory(destination, trusted=True)
    try:
        info = os.fstat(fd)
        require(stat.S_IMODE(info.st_mode) == 0o755, 'installation_root_mode')
        raw, _ = _read_at(fd, RECEIPT, MANIFEST_LIMIT, trusted=True)
        expected = _receipt(prepared, dependency_bytes, python, destination, info)
        _verify_receipt(raw, expected)
        files = dict(prepared.source)
        modes = dict(prepared.source_modes)
        files.update({'dependencies/' + n: data for n, data in dependency_bytes.items()})
        modes.update({'dependencies/' + n: 0o644 for n in dependency_bytes})
        files[RECEIPT] = raw
        modes[RECEIPT] = 0o644
        # The receipt filename is the sole dot-prefixed file added by installer.
        _tree(fd, {n: digest(data) for n, data in files.items()}, trusted=True,
              modes=modes, total_limit=DEPENDENCY_TOTAL_LIMIT + _builder().MAX_TOTAL + MANIFEST_LIMIT)
        return {**expected, 'receiptSha256': digest(raw), 'verifiedInstalledBytesNow': True}
    finally:
        os.close(fd)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate-directory', required=True)
    parser.add_argument('--destination', required=True)
    parser.add_argument('--dependencies', required=True)
    for name in ('manifest-sha256', 'archive-sha256', 'harness-commit', 'python-sha256'):
        parser.add_argument('--expected-' + name, required=True)
    actions = parser.add_mutually_exclusive_group()
    actions.add_argument('--verify-only', action='store_true')
    actions.add_argument('--verify-installed', action='store_true')
    args = parser.parse_args()
    pins = {key: getattr(args, key) for key in ('expected_manifest_sha256',
            'expected_archive_sha256', 'expected_harness_commit', 'expected_python_sha256')}
    try:
        if args.verify_only:
            prepared, deps, python = preflight(args.candidate_directory, args.dependencies, **pins)
            destination = _absolute(args.destination)
            fd = _directory(destination.parent, trusted=True)
            try:
                _absent(fd, destination.name)
            finally:
                os.close(fd)
            result = {'kind': 'VERIFIED_INSTALLATION_INPUTS',
                'harnessCommit': prepared.harness_commit, 'archiveSha256': prepared.archive_sha256,
                'sourceFileCount': len(prepared.source), 'dependencyFileCount': len(deps),
                'python': python, 'installed': False, 'executionAuthorized': False,
                'projectedReadinessAccepted': False, 'realModelCalls': 0}
        elif args.verify_installed:
            result = verify_installed(args.candidate_directory, args.destination,
                                      args.dependencies, **pins)
        else:
            result = install(args.candidate_directory, args.destination, args.dependencies, **pins)
    except (InstallationRejected, OSError, ValueError, tarfile.TarError) as exc:
        print(json.dumps({'result': 'REFUSED', 'reasonType': type(exc).__name__,
            'reason': str(exc) if isinstance(exc, InstallationRejected) else 'installation_io_or_format_failed',
            'partialPath': getattr(exc, 'partial_path', None), 'installed': False,
            'executionAuthorized': False, 'projectedReadinessAccepted': False,
            'realModelCalls': 0}), file=sys.stderr)
        return 2
    print(json.dumps({'result': 'PASS', **result}, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
