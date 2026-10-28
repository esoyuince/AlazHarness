"""Qualify only the pinned installed Node CLI's help path as the ordinary lab user.

Read back the installation and runtime binaries before and after one bounded
help process. No connection fields, task, lifecycle command or model is selected.
This is startup compatibility evidence, not an operating-system confinement test.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
import tempfile
import traceback
import types

IMPORT_PROBE_SHA256 = '9261a63ab741cefe0df32296cdced122e29e420278075bb8a5f295de2b826bab'
NODE = '/opt/alaz-r167a1-node-24.22.1/bin/node'
NODE_SHA256 = 'e32e2d16081cf644f88392934288086e7662529d0d43277c34f7aad2207cfafb'
SOURCE_LIMIT = 2 * 1024 * 1024


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def stamp(info):
    return (info.st_dev, info.st_ino, info.st_mode, info.st_uid, info.st_gid,
            info.st_nlink, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def trusted_tool(path):
    require(path.is_absolute() and path.resolve(strict=True) == path,
            'cli_probe_tool_path')
    for parent in path.parents:
        info = parent.lstat()
        require(stat.S_ISDIR(info.st_mode) and info.st_uid == info.st_gid == 0
                and not info.st_mode & 0o022, 'cli_probe_tool_ancestry')
    fd = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        info = os.fstat(fd)
        require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1
                and info.st_uid == info.st_gid == 0 and not info.st_mode & 0o022
                and 0 < info.st_size <= SOURCE_LIMIT, 'cli_probe_tool_metadata')
        with os.fdopen(fd, 'rb', closefd=False) as stream:
            raw = stream.read(SOURCE_LIMIT + 1)
        require(len(raw) == info.st_size
                and stamp(info) == stamp(os.fstat(fd)) == stamp(path.lstat()),
                'cli_probe_tool_changed')
        return raw
    finally:
        os.close(fd)


def reviewed_support():
    path = Path(__file__).absolute().with_name('r167a1_import_probe.py')
    raw = trusted_tool(path)
    require(sha(raw) == IMPORT_PROBE_SHA256, 'cli_probe_support_digest')
    module = types.ModuleType('_r167_reviewed_import_support')
    module.__file__ = str(path)
    sys.modules[module.__name__] = module
    exec(compile(raw, str(path), 'exec'), module.__dict__)
    return module


def expected_help(source):
    text = source.decode('utf-8')
    matches = re.findall(r'const HELP = `([^`]*)`;', text)
    require(len(matches) == 1 and '${' not in matches[0] and '\\' not in matches[0],
            'cli_probe_help_literal')
    raw = matches[0].encode('utf-8')
    require(raw.startswith(b'AlazHarness local control (Node 24)\n')
            and 0 < len(raw) < 4096, 'cli_probe_help_shape')
    return raw


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--installer', required=True)
    parser.add_argument('--expected-installer-sha256', required=True)
    parser.add_argument('--candidate-directory', required=True)
    parser.add_argument('--expected-receipt-sha256', required=True)
    args = parser.parse_args()
    report = {'schema': 1, 'kind': 'R167A1_INSTALLED_NODE_CLI_HELP_PROBE',
              'result': 'NOT_ACCEPTED_CLI_PREFLIGHT', 'stage': 'PREFLIGHT',
              'nodeCliHelpAccepted': False, 'nodeExecuted': False,
              'nodeExecutionAttempted': False, 'nodeProcessOutcome': 'NOT_STARTED',
              'serviceReadinessAccepted': False, 'kernelAcceptance': False,
              'realModelCalls': 0, 'serviceLifecycleCommandSelected': False,
              'taskCommandSelected': False, 'runtimeVersionsReexecuted': False,
              'sharedLibraryClosureAccepted': False, 'osConfinementTested': False,
              'installedTreeWritten': False}
    temporary = None
    try:
        probe = reviewed_support()
        probe.actor()
        report['probeSha256'] = sha(trusted_tool(Path(__file__).absolute()))
        report['supportProbeSha256'] = IMPORT_PROBE_SHA256
        require(re.fullmatch('[a-f0-9]{64}', args.expected_receipt_sha256) is not None,
                'cli_probe_receipt_pin')
        installer = probe.load_installer(args.installer, args.expected_installer_sha256)
        p = installer._legacy()
        candidate = p._absolute(args.candidate_directory)
        prepared = installer._verifier().verify_files(candidate / 'manifest.json',
            candidate / 'service-source.tar', expected_manifest_sha256=probe.MANIFEST,
            expected_archive_sha256=probe.ARCHIVE, expected_harness_commit=probe.HARNESS,
            expected_native_feature=probe.NATIVE)
        require(len(prepared.source) == 878 and len(prepared.dependencies) == 1162,
                'cli_probe_expected_inventory')
        before_receipt, before_binaries = probe.installed_bytes(
            installer, prepared, args.expected_receipt_sha256)
        require(before_receipt['runtimes']['node']['path'] == NODE
                and before_receipt['runtimes']['node']['sha256'] == NODE_SHA256,
                'cli_probe_selected_node')
        wanted = expected_help(prepared.source['scripts/alaz_local.mjs'])
        temporary = tempfile.TemporaryDirectory(prefix='alaz-r167a1-cli-help-')
        home = str(Path(temporary.name).resolve())
        environment = {'PATH': '/usr/bin:/bin', 'HOME': home, 'TMPDIR': home,
                       'LANG': 'C.UTF-8', 'LC_ALL': 'C.UTF-8', 'TZ': 'UTC'}
        parent = p._directory(Path(NODE).parent, trusted=True)
        fd = None
        try:
            fd = os.open('node', os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW
                         | os.O_NONBLOCK, dir_fd=parent)
            digest, before = installer._binary_digest(fd)
            require(digest == NODE_SHA256, 'cli_probe_node_digest')
            command = ['/proc/self/fd/' + str(fd),
                       probe.DESTINATION + '/scripts/alaz_local.mjs', '--help']
            report.update(stage='HELP_PROCESS', nodeExecutionAttempted=True,
                          nodeExecuted=None, nodeProcessOutcome='UNKNOWN_UNTIL_TERMINAL_CAPTURE')
            result = installer._capture_bounded(command, pass_fds=(fd,),
                env=environment, timeout=10.0, limit=4096)
            report.update(nodeExecuted=True, nodeProcessOutcome='EXITED', nodeExitCode=result.returncode,
                nodeStdout=result.stdout.decode('utf-8'),
                nodeStderr=result.stderr.decode('utf-8'),
                nodeStdoutSha256=sha(result.stdout), nodeStderrSha256=sha(result.stderr),
                nodeStdoutBytes=len(result.stdout), nodeStderrBytes=len(result.stderr),
                fullNodeOutputCaptured=True)
            after_digest, after = installer._binary_digest(fd)
            require(after_digest == digest and stamp(before) == stamp(after),
                    'cli_probe_node_changed')
            current_parent = p._directory(Path(NODE).parent, trusted=True)
            try:
                require(stamp(before) == stamp(os.stat('node', dir_fd=current_parent,
                                                       follow_symlinks=False)),
                        'cli_probe_node_path_changed')
            finally:
                os.close(current_parent)
            require(result.returncode == 0 and result.stdout == wanted,
                    'cli_probe_help_result')
        finally:
            if fd is not None:
                os.close(fd)
            os.close(parent)
        after_receipt, after_binaries = probe.installed_bytes(
            installer, prepared, args.expected_receipt_sha256)
        require(installer.canonical(before_receipt) == installer.canonical(after_receipt)
                and before_binaries == after_binaries, 'cli_probe_installed_inputs_changed')
        report.update(result='PASS_INSTALLED_NODE_CLI_HELP_ONLY', stage='COMPLETE',
            nodeCliHelpAccepted=True, installation=probe.DESTINATION,
            installationReceiptSha256=args.expected_receipt_sha256,
            installerSha256=args.expected_installer_sha256,
            sourceManifestSha256=probe.MANIFEST, archiveSha256=probe.ARCHIVE,
            harnessCommit=probe.HARNESS, nativeFeature=probe.NATIVE,
            sourceFileCount=len(prepared.source), dependencyFileCount=len(prepared.dependencies),
            sourceAndDependencyBytesReadBackBeforeAndAfter=True,
            runtimeBinaryBytesReadBackBeforeAndAfter=True,
            nodeBinarySha256=NODE_SHA256, nodeVersionFromInstallation=before_receipt['runtimes']['node']['version'],
            uid=list(os.getresuid()), gid=list(os.getresgid()),
            connectionEnvironmentInherited=False)
    except BaseException as exc:
        report.update(error={'type': type(exc).__name__, 'reason': str(exc)[:1000],
                             'traceback': traceback.format_exc()[-6000:]})
    finally:
        if temporary is not None:
            try:
                temporary.cleanup()
                report['ownedTemporaryHomeRemoved'] = not Path(temporary.name).exists()
            except OSError as exc:
                report.update(result='NOT_ACCEPTED_CLI_PREFLIGHT', nodeCliHelpAccepted=False,
                              ownedTemporaryHomeRemoved=False,
                              ownedTemporaryCleanupError=type(exc).__name__)
    print(json.dumps(report, sort_keys=True), flush=True)
    return 0 if report['result'] == 'PASS_INSTALLED_NODE_CLI_HELP_ONLY' else 2


if __name__ == '__main__':
    raise SystemExit(main())
