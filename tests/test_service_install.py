"""Owned service-install fixtures; never privileged installation acceptance.

Runtime tests use declared filesystem metadata/parent-reader doubles and a
captured-version double. Those tests never execute the synthetic ELF bytes.
Separate bounded-process tests run only the current Python with owned snippets.
The original finite builder/installer and R166 source verifier remain unchanged.
"""
from contextlib import ExitStack, contextmanager, redirect_stderr
from copy import deepcopy
from dataclasses import replace
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import MappingProxyType, SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(ROOT / 'tests'))
import install_service_candidate as installer
import test_service_candidate as source_tests


FROZEN_HELPERS = {
    'build_projected_candidate.py':
        '7b26916aec3c806ef2debf77e9e9c728ec473d8c8d2689bbbdcfc4cd7223a64b',
    'install_projected_candidate.py':
        'f261fd22c641a1ffdd6fb9694fec0c7d3cb0c8dba788cb7549c142fd1e4dcef6',
    'build_service_candidate.py':
        '54c83be327e3e9e08e0a149b096f5a4f873364461069711a4c2d3f20e862f6cf',
    'verify_service_candidate.py':
        'ddd8fb60dc030c36c0aefcf2790c788d012dc13e39e37f1a14f5bcd0725e3288',
}


def runtime_fixture(kind='node'):
    version = [24, 2, 1] if kind == 'node' else [3, 12, 3]
    displayed = ('v' if kind == 'node' else 'Python ') + '.'.join(map(str, version))
    return {'path': '/opt/owned-version-fixture/' + kind, 'sha256': 'd' * 64,
            'bytes': 256, 'device': 9, 'inode': 17, 'uid': 0, 'gid': 0,
            'mode': 0o755, 'version': '.'.join(map(str, version)),
            'versionTuple': version, 'observedVersion': displayed,
            'versionStdoutSha256': installer.digest((displayed + '\n').encode())}


def receipt_fixture():
    prepared = SimpleNamespace(manifest_sha256='a' * 64, archive_sha256='b' * 64,
        harness_commit='c' * 40, native_feature='e' * 40,
        source={'scripts/owned.py': b'raise RuntimeError("must not execute")\n'},
        dependency_inventory_sha256='f' * 64)
    return installer._receipt(prepared, {'pkg/owned.py': b'owned'},
        {'python': runtime_fixture('python'), 'node': runtime_fixture()},
        '/opt/owned-service-fixture', SimpleNamespace(st_dev=21, st_ino=27))


class FixedServiceInstallerTests(unittest.TestCase):
    def test_all_existing_helper_bytes_and_generation_remain_pinned(self):
        self.assertEqual(installer.VERIFIER_SHA256,
                         FROZEN_HELPERS['verify_service_candidate.py'])
        for name, expected in FROZEN_HELPERS.items():
            with self.subTest(helper=name):
                self.assertEqual(installer.digest((ROOT / 'scripts' / name).read_bytes()), expected)
        self.assertEqual(installer._verifier()._builder().NATIVE_COUNT, 760)
        self.assertEqual(installer._legacy()._builder().NATIVE_COUNT, 756)

    def test_changed_verifier_pin_refuses_before_loading(self):
        with patch.object(installer, 'VERIFIER_SHA256', '0' * 64):
            with self.assertRaisesRegex(ValueError, 'verifier_changed'):
                installer._verifier.__wrapped__()

    def test_exact_python_and_node_version_outputs(self):
        for kind, raw, expected in [('python', b'Python 3.12.3\n', [3, 12, 3]),
                                    ('node', b'v24.2.1\n', [24, 2, 1])]:
            with self.subTest(kind=kind):
                actual = installer._parse_runtime_version(kind, raw)
                self.assertEqual(actual['versionTuple'], expected)
                self.assertEqual(actual['versionStdoutSha256'], installer.digest(raw))
                self.assertEqual(actual['observedVersion'], raw.decode().rstrip('\n'))

    def test_wrong_runtime_generations_and_extra_output_refuse(self):
        rows = [('python', b'Python 3.11.9\n'), ('python', b'Python 3.13.0\n'),
                ('python', b'Python 3.12.3\nextra\n'), ('python', b'Python 3.12.3'),
                ('python', b'Python 3.12.03\n'), ('node', b'v22.1.0\n'),
                ('node', b'v25.0.0\n'), ('node', b'v24.0.0-rc.1\n'),
                ('node', b' v24.1.0\n'), ('node', b'v24.1.0\r\n'),
                ('node', b'v24.1.0\n\x00')]
        for kind, raw in rows:
            with self.subTest(kind=kind, raw=raw), self.assertRaises(ValueError):
                installer._parse_runtime_version(kind, raw)

    def test_runtime_output_types_and_bound_are_strict(self):
        for kind, raw in [('node', 'v24.1.0\n'), ('node', bytearray(b'v24.1.0\n')),
                          ('node', b''), ('node', b'x' * 129),
                          ('other', b'v24.1.0\n')]:
            with self.subTest(kind=kind, raw_type=type(raw)), self.assertRaises(ValueError):
                installer._parse_runtime_version(kind, raw)

    def test_receipt_claims_only_source_dependency_and_executable_readback(self):
        receipt = receipt_fixture()
        self.assertEqual(receipt['kind'], 'VERIFIED_SERVICE_INSTALLATION')
        self.assertTrue(receipt['installed'])
        self.assertTrue(receipt['sourceAndDependenciesReadBack'])
        self.assertTrue(receipt['runtimeExecutableBytesVerified'])
        self.assertTrue(receipt['runtimeVersionReadback'])
        for key in ('executionAuthorized', 'dependenciesAcceptedForService',
                    'serviceReadinessAccepted', 'nativeRuntimeAccepted',
                    'kernelAcceptance', 'realModelAcceptance'):
            with self.subTest(claim=key):
                self.assertIs(receipt[key], False)
        self.assertIs(type(receipt['realModelCalls']), int)
        self.assertEqual(receipt['realModelCalls'], 0)

    def test_receipt_rejects_wrong_identity_claims_types_and_extra_fields(self):
        receipt = receipt_fixture()
        installer._verify_receipt(installer.canonical(receipt), receipt)
        changes = [('rootInode', 28), ('harnessCommit', '0' * 40),
                   ('destination', '/opt/other-fixture'), ('installed', 1),
                   ('realModelCalls', False), ('serviceReadinessAccepted', True),
                   ('unreviewedClaim', True)]
        for key, value in changes:
            altered = dict(receipt, **{key: value})
            with self.subTest(field=key), self.assertRaisesRegex(ValueError, 'receipt_identity'):
                installer._verify_receipt(installer.canonical(altered), receipt)
        altered = deepcopy(receipt)
        altered['runtimes']['node']['versionTuple'][0] = 25
        with self.assertRaisesRegex(ValueError, 'receipt_identity'):
            installer._verify_receipt(installer.canonical(altered), receipt)
        raw = b'{"schemaVersion": 1,' + installer.canonical(receipt)[1:]
        with self.assertRaises(ValueError):
            installer._verify_receipt(raw, receipt)

    def test_runtime_recheck_compares_full_identity_and_strict_types(self):
        expected = {'python': runtime_fixture('python'), 'node': runtime_fixture()}
        pins = {'expected_python_sha256': 'd' * 64, 'node_path': expected['node']['path'],
                'expected_node_sha256': 'd' * 64}
        with patch.object(installer, '_runtimes', return_value=deepcopy(expected)):
            installer._reread_runtimes(pins, expected)
        for key, value in [('inode', 18), ('sha256', '0' * 64), ('uid', False)]:
            changed = deepcopy(expected); changed['node'][key] = value
            with self.subTest(field=key), patch.object(installer, '_runtimes', return_value=changed):
                with self.assertRaisesRegex(ValueError, 'runtimes_changed'):
                    installer._reread_runtimes(pins, expected)

    def test_cli_requires_all_runtime_and_native_pins(self):
        args = ['install_service_candidate.py', '--candidate-directory', '/owned/candidate',
                '--destination', '/owned/install', '--dependencies', '/owned/dependencies',
                '--node-path', '/owned/node', '--expected-manifest-sha256', 'a' * 64,
                '--expected-archive-sha256', 'b' * 64, '--expected-harness-commit', 'c' * 40,
                '--expected-native-feature', 'd' * 40, '--expected-python-sha256', 'e' * 64,
                '--expected-node-sha256', 'f' * 64, '--verify-only']
        for key in ('--node-path', '--expected-native-feature', '--expected-python-sha256',
                    '--expected-node-sha256'):
            missing = list(args); index = missing.index(key); del missing[index:index + 2]
            with self.subTest(missing=key), patch.object(sys, 'argv', missing), \
                    redirect_stderr(io.StringIO()), patch.object(installer, 'preflight') as preflight:
                with self.assertRaises(SystemExit) as caught:
                    installer.main()
                self.assertEqual(caught.exception.code, 2)
                preflight.assert_not_called()


class ServicePayloadTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.stack = ExitStack(); cls.addClassCleanup(cls.stack.close)
        cls.repo, cls.native, cls.revision = cls.stack.enter_context(source_tests.fixture())
        cls.stack.enter_context(patch.object(installer, '_verifier', return_value=source_tests.verifier))
        cls.candidate_directory = cls.repo / 'scratch/service-candidates/install-fixture'
        cls.manifest = source_tests.candidate.build(cls.repo, cls.revision, cls.native,
                                                   cls.candidate_directory)
        cls.raw = source_tests.candidate.canonical(cls.manifest)
        cls.archive = (cls.candidate_directory / source_tests.candidate.ARCHIVE).read_bytes()
        cls.pins = {'expected_manifest_sha256': installer.digest(cls.raw),
                    'expected_archive_sha256': installer.digest(cls.archive),
                    'expected_harness_commit': cls.revision,
                    'expected_native_feature': source_tests.candidate.NATIVE_FEATURE}
        cls.prepared = installer.prepare_bytes(cls.raw, cls.archive, **cls.pins)
        cls.dependencies = {}
        for name, expected in cls.prepared.dependencies.items():
            index = int(Path(name).stem.rsplit('_', 1)[1])
            raw = ('dependency fixture ' + str(index)).encode()
            if installer.digest(raw) != expected:
                raise AssertionError('source fixture dependency derivation mismatch')
            cls.dependencies[name] = raw

    def test_delegate_requires_each_external_candidate_pin(self):
        for key, value in [('expected_manifest_sha256', '0' * 64),
                           ('expected_archive_sha256', '0' * 64),
                           ('expected_harness_commit', '0' * 40),
                           ('expected_native_feature', '0' * 40)]:
            pins = dict(self.pins, **{key: value})
            with self.subTest(pin=key), self.assertRaises(ValueError):
                installer.prepare_bytes(self.raw, self.archive, **pins)

    def test_complete_service_and_dependency_payload_has_exact_namespace(self):
        files, modes = installer._installation_files(self.prepared, self.dependencies)
        self.assertEqual(set(files), set(self.prepared.source) |
                         {'dependencies/' + name for name in self.dependencies})
        self.assertEqual(set(files), set(modes))
        self.assertEqual(len(self.dependencies), 1162)
        self.assertEqual(sum(name.startswith('native/') for name in files), 760)
        self.assertTrue(all(modes['dependencies/' + name] == 0o644 for name in self.dependencies))
        self.assertNotIn(installer.RECEIPT, files)
        for name in source_tests.candidate.SERVICE_ENTRIES:
            self.assertIn(name, files)

    def test_missing_extra_changed_or_nonbytes_dependency_refuses(self):
        first = next(iter(self.dependencies))
        missing = dict(self.dependencies); del missing[first]
        extra = dict(self.dependencies, **{'unexpected.py': b'extra'})
        changed = dict(self.dependencies, **{first: b'changed'})
        nonbytes = dict(self.dependencies, **{first: bytearray(self.dependencies[first])})
        for label, values in [('missing', missing), ('extra', extra),
                              ('changed', changed), ('nonbytes', nonbytes)]:
            with self.subTest(case=label), self.assertRaisesRegex(ValueError, 'dependency_bytes'):
                installer._installation_files(self.prepared, values)

    def test_source_dependency_namespace_collision_refuses(self):
        name = 'dependencies/' + next(iter(self.dependencies))
        source = dict(self.prepared.source, **{name: b'collision'})
        modes = dict(self.prepared.source_modes, **{name: 0o644})
        prepared = replace(self.prepared, source=MappingProxyType(source),
                           source_modes=MappingProxyType(modes))
        with self.assertRaisesRegex(ValueError, 'namespace_collision'):
            installer._installation_files(prepared, self.dependencies)

    def test_receipt_retains_candidate_identity_and_actual_counts(self):
        runtimes = {'python': runtime_fixture('python'), 'node': runtime_fixture()}
        receipt = installer._receipt(self.prepared, self.dependencies, runtimes,
            '/opt/owned-service-fixture', SimpleNamespace(st_dev=31, st_ino=37))
        self.assertEqual(receipt['harnessCommit'], self.revision)
        self.assertEqual(receipt['nativeFeature'], self.pins['expected_native_feature'])
        self.assertEqual(receipt['sourceManifestSha256'], self.pins['expected_manifest_sha256'])
        self.assertEqual(receipt['sourceFileCount'], self.manifest['sourceFileCount'])
        self.assertEqual(receipt['dependencyFileCount'], 1162)

    @unittest.skipUnless(sys.platform == 'linux', 'owned descriptor materialization requires Linux')
    def test_all_service_and_dependency_bytes_materialize_without_execution_or_receipt(self):
        with tempfile.TemporaryDirectory(prefix='r167-owned-materialize-') as directory:
            root = Path(directory); fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY)
            try:
                files, modes = installer._installation_files(self.prepared, self.dependencies)
                legacy = installer._legacy()
                legacy._materialize(fd, files, modes)
                actual = legacy._tree(fd, {n: installer.digest(v) for n, v in files.items()},
                                      trusted=False, modes=modes)
                self.assertEqual(actual, files)
                self.assertFalse((root / installer.RECEIPT).exists())
                self.assertFalse((root / '.alaz-installation.json').exists())
                name = 'dependencies/' + next(iter(self.dependencies))
                (root / name).write_bytes(b'altered installed dependency')
                with self.assertRaisesRegex(ValueError, 'file_digest'):
                    legacy._tree(fd, {n: installer.digest(v) for n, v in files.items()},
                                 trusted=False, modes=modes)
            finally:
                os.close(fd)


def elf_fixture():
    header = bytearray(64)
    header[:6] = b'\x7fELF\x02\x01'
    header[16:20] = b'\x03\x00\x3e\x00'
    return bytes(header) + b'owned bytes; never executed\n'


@unittest.skipUnless(sys.platform == 'linux', 'held-descriptor runtime fixtures require Linux')
class RuntimeReadbackTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='r167-owned-runtime-')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.file = self.root / 'node'
        self.file.write_bytes(elf_fixture()); self.file.chmod(0o755)
        self.parent_fd = os.open(self.root, os.O_RDONLY | os.O_DIRECTORY)
        self.addCleanup(os.close, self.parent_fd)
        self.legacy = installer._legacy()
        self.uid = self.gid = 0
        self.virtual_parent = '/opt/owned-r167-runtime-fixture'
        self.virtual_path = self.virtual_parent + '/node'

    @contextmanager
    def filesystem_reader(self):
        """Model a root-owned input boundary; no real root path is accessed."""
        actual_fstat, actual_stat = os.fstat, os.stat
        test = self
        class Reader:
            def __getattr__(self, name):
                return getattr(test.legacy, name)
            def _directory(self, path, *, trusted):
                test.assertTrue(trusted)
                test.assertEqual(str(path), test.virtual_parent)
                return os.dup(test.parent_fd)
        def metadata(value):
            fields = {name: getattr(value, name) for name in dir(value)
                      if name.startswith('st_')}
            fields.update(st_uid=self.uid, st_gid=self.gid)
            return SimpleNamespace(**fields)
        def fstat(fd):
            return metadata(actual_fstat(fd))
        def stat_read(path, *args, **kwargs):
            value = actual_stat(path, *args, **kwargs)
            return metadata(value) if kwargs.get('dir_fd') is not None else value
        with patch.object(installer, '_legacy', return_value=Reader()), \
                patch.object(os, 'fstat', side_effect=fstat), \
                patch.object(os, 'stat', side_effect=stat_read):
            yield

    def readback(self, **overrides):
        args = {'path': self.virtual_path, 'expected_sha256': installer.digest(self.file.read_bytes()),
                'kind': 'node'}
        args.update(overrides)
        return installer._runtime_readback(**args)

    def test_probe_uses_held_descriptor_and_clean_environment(self):
        seen = []
        def capture(command, **kwargs):
            fd, = kwargs['pass_fds']
            self.assertEqual(command, ['/proc/self/fd/' + str(fd), '--version'])
            self.assertEqual(os.pread(fd, 64, 0), elf_fixture()[:64])
            self.assertEqual(kwargs['env'], {'PATH': '/usr/bin:/bin', 'LANG': 'C', 'LC_ALL': 'C'})
            seen.append(fd)
            return subprocess.CompletedProcess(command, 0, b'v24.2.1\n', b'')
        with self.filesystem_reader(), patch.object(installer, '_capture_bounded', side_effect=capture):
            actual = self.readback()
        self.assertEqual(len(seen), 1)
        self.assertEqual(actual['versionTuple'], [24, 2, 1])
        self.assertEqual(actual['path'], self.virtual_path)
        self.assertEqual(actual['sha256'], installer.digest(elf_fixture()))

    def test_python_probe_has_isolation_no_site_and_no_bytecode_flags(self):
        def capture(command, **kwargs):
            self.assertEqual(command[1:], ['-I', '-S', '-B', '--version'])
            return subprocess.CompletedProcess(command, 0, b'Python 3.12.3\n', b'')
        with self.filesystem_reader(), patch.object(installer, '_capture_bounded', side_effect=capture):
            self.assertEqual(self.readback(kind='python')['versionTuple'], [3, 12, 3])

    def test_digest_mismatch_refuses_before_version_execution(self):
        with self.filesystem_reader(), patch.object(installer, '_capture_bounded') as capture:
            with self.assertRaisesRegex(ValueError, 'executable_digest'):
                self.readback(expected_sha256='0' * 64)
            capture.assert_not_called()

    def test_untrusted_owner_and_privileged_or_nonexecutable_modes_refuse(self):
        for uid, gid, mode in [(1000, 0, 0o755), (0, 1000, 0o755), (0, 0, 0o777),
                               (0, 0, 0o4755), (0, 0, 0o2755), (0, 0, 0o1755),
                               (0, 0, 0o644)]:
            self.uid, self.gid = uid, gid; self.file.chmod(mode)
            with self.subTest(uid=uid, gid=gid, mode=oct(mode)), self.filesystem_reader(), \
                    patch.object(installer, '_capture_bounded') as capture:
                with self.assertRaises(ValueError):
                    self.readback()
                capture.assert_not_called()

    def test_wrong_elf_architecture_and_link_inputs_refuse_without_execution(self):
        altered = bytearray(elf_fixture()); altered[18:20] = b'\xb7\x00'
        self.file.write_bytes(altered)
        with self.filesystem_reader(), patch.object(installer, '_capture_bounded') as capture:
            with self.assertRaisesRegex(ValueError, 'linux_x86_64_elf_required'):
                self.readback()
            capture.assert_not_called()
        self.file.write_bytes(elf_fixture()); os.link(self.file, self.root / 'second-name')
        with self.filesystem_reader(), patch.object(installer, '_capture_bounded') as capture:
            with self.assertRaisesRegex(ValueError, 'hardlink'):
                self.readback()
            capture.assert_not_called()

    def test_nonzero_stderr_and_wrong_version_refuse(self):
        for code, out, err in [(1, b'v24.2.1\n', b''), (0, b'v24.2.1\n', b'warning'),
                               (0, b'v22.2.1\n', b'')]:
            with self.subTest(code=code, stdout=out, stderr=err), self.filesystem_reader(), \
                    patch.object(installer, '_capture_bounded',
                        return_value=subprocess.CompletedProcess([], code, out, err)):
                with self.assertRaises(ValueError):
                    self.readback()

    def test_binary_change_during_probe_refuses(self):
        def capture(command, **kwargs):
            self.file.write_bytes(elf_fixture() + b'changed')
            return subprocess.CompletedProcess(command, 0, b'v24.2.1\n', b'')
        with self.filesystem_reader(), patch.object(installer, '_capture_bounded', side_effect=capture):
            with self.assertRaisesRegex(ValueError, 'executable_changed'):
                self.readback()

    def test_same_bytes_under_replaced_path_refuse(self):
        def capture(command, **kwargs):
            self.file.rename(self.root / 'retained-original')
            self.file.write_bytes(elf_fixture()); self.file.chmod(0o755)
            return subprocess.CompletedProcess(command, 0, b'v24.2.1\n', b'')
        with self.filesystem_reader(), patch.object(installer, '_capture_bounded', side_effect=capture):
            with self.assertRaisesRegex(ValueError, 'executable_changed|executable_path_changed'):
                self.readback()


@unittest.skipUnless(sys.platform == 'linux', 'owned bounded process probes require Linux')
class BoundedProbeTests(unittest.TestCase):
    def command(self, code):
        return [sys.executable, '-I', '-S', '-B', '-c', code]

    def test_both_streams_and_actual_nonzero_exit_are_preserved(self):
        result = installer._capture_bounded(self.command(
            "import os; os.write(1,b'out'); os.write(2,b'err'); raise SystemExit(7)"))
        self.assertEqual((result.returncode, result.stdout, result.stderr), (7, b'out', b'err'))

    def test_ambient_runtime_injection_environment_is_not_inherited(self):
        with patch.dict(os.environ, {'NODE_OPTIONS': '--unapproved',
                                     'PYTHONPATH': '/unapproved', 'LD_PRELOAD': '/unapproved'}):
            result = installer._capture_bounded(self.command(
                "import os,json; print(json.dumps(sorted(os.environ)))"))
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stderr, b'')
        keys = json.loads(result.stdout)
        self.assertFalse({'NODE_OPTIONS', 'PYTHONPATH', 'LD_PRELOAD'} & set(keys))
        self.assertTrue({'PATH', 'LANG', 'LC_ALL'} <= set(keys))

    def capture_processes(self):
        actual = subprocess.Popen
        processes = []
        def spawn(*args, **kwargs):
            process = actual(*args, **kwargs); processes.append(process)
            return process
        def ensure_stopped():
            for process in processes:
                if process.poll() is None:
                    installer._stop_probe(process)
        self.addCleanup(ensure_stopped)
        return processes, spawn

    def test_combined_output_bound_refuses_and_reaps_owned_process(self):
        processes, spawn = self.capture_processes()
        with patch.object(subprocess, 'Popen', side_effect=spawn):
            with self.assertRaisesRegex(ValueError, 'output_limit'):
                installer._capture_bounded(self.command(
                    "import os,time; os.write(1,b'a'*32); os.write(2,b'b'*32); time.sleep(60)"), limit=48)
        self.assertEqual(len(processes), 1)
        self.assertIsNotNone(processes[0].poll())

    def test_timeout_refuses_and_reaps_owned_process(self):
        processes, spawn = self.capture_processes()
        with patch.object(subprocess, 'Popen', side_effect=spawn):
            with self.assertRaisesRegex(ValueError, 'probe_timeout'):
                installer._capture_bounded(self.command('import time; time.sleep(60)'), timeout=0.1)
        self.assertEqual(len(processes), 1)
        self.assertIsNotNone(processes[0].poll())

    def test_selector_construction_failure_reaps_owned_process(self):
        processes, spawn = self.capture_processes()
        with patch.object(subprocess, 'Popen', side_effect=spawn), \
                patch.object(installer.selectors, 'DefaultSelector', side_effect=OSError('owned FD failure')):
            with self.assertRaises(OSError):
                installer._capture_bounded(self.command('import time; time.sleep(60)'))
        self.assertEqual(len(processes), 1)
        self.assertIsNotNone(processes[0].poll())

    def test_invalid_capture_arguments_refuse_before_spawning(self):
        rows = [([], {}), ([b'bytes'], {}), (['owned'], {'limit': True}),
                (['owned'], {'limit': 4097}), (['owned'], {'timeout': 0}),
                (['owned'], {'timeout': float('nan')})]
        for command, arguments in rows:
            with self.subTest(command=command, arguments=arguments), \
                    patch.object(subprocess, 'Popen') as spawn:
                with self.assertRaisesRegex(ValueError, 'probe_arguments'):
                    installer._capture_bounded(command, **arguments)
                spawn.assert_not_called()


if __name__ == '__main__':
    unittest.main()
