"""OS bootstrap contract/file tests; no lab actor, product, child or kernel run.

Filesystem fixtures use owned temporary paths. Only ancestry and the numeric
owner mapping are replaced; production requires the actual root UID and GID.
"""
import copy
import importlib.util
import os
from pathlib import Path, PurePosixPath
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    '_r168_bootstrap_probe_test', ROOT / 'scripts/qa/r168a1_bootstrap_probe.py')
probe = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = probe
SPEC.loader.exec_module(probe)


def snapshot():
    return {
        'modules': {
            'site': {'file': '/usr/lib/python3.12/site.py', 'cached': None,
                     'origin': 'frozen', 'loader': '_frozen_importlib.FrozenImporter'},
            'sitecustomize': {'file': '/usr/lib/python3.12/sitecustomize.py',
                             'cached': '/usr/lib/python3.12/__pycache__/sitecustomize.cpython-312.pyc',
                             'origin': '/usr/lib/python3.12/sitecustomize.py',
                             'loader': '_frozen_importlib_external.SourceFileLoader'},
        },
        'sysPath': list(probe.SYSTEM_PATH),
        'metaPath': ['_frozen_importlib.BuiltinImporter', '_frozen_importlib.FrozenImporter',
                     '_frozen_importlib_external.PathFinder'],
        'pathHooks': ['zipimport.zipimporter', '_frozen_importlib_external.FileFinder.path_hook.<locals>.path_hook'],
        'sitecustomizeNames': ['__builtins__', '__cached__', '__doc__', '__file__',
                               '__loader__', '__name__', '__package__', '__spec__'],
    }


def contract():
    observation = {
        'startup': snapshot(),
        'files': {
            probe.CUSTOMIZER: {'canonicalPath': probe.CUSTOMIZER,
                               'bytes': 155, 'sha256': probe.CUSTOMIZER_SHA256},
            '/usr/lib/python3.12/__pycache__/sitecustomize.cpython-312.pyc': None,
        },
        'siteDirectories': {p: {'present': False, 'pthFiles': []} for p in probe.SITE_DIRECTORIES},
        'apportSpec': None, 'pythonZipPresent': False,
    }
    observations = {}
    for key in probe.CONTEXT_KEYS:
        row = copy.deepcopy(observation)
        # Declared source-only fixture for the observed per-context import.
        # Actual lab contracts are captured separately for every exact context.
        if key in ('root/qa', 'gateway/qa', 'root/worker'):
            row['startup']['modules']['pwd'] = {
                'file': None, 'cached': None, 'origin': 'built-in',
                'loader': '_frozen_importlib.BuiltinImporter'}
        observations[key] = row
    return {'protocol': probe.PROTOCOL, 'observations': observations}


class BootstrapContractTests(unittest.TestCase):
    def setUp(self):
        # These are serialized Linux paths, independent of the test host's OS.
        # Real held-file fixtures below retain their Linux-only boundary.
        paths = patch.object(probe, 'Path', PurePosixPath)
        paths.start()
        self.addCleanup(paths.stop)

    def test_canonical_contract_and_exact_observation(self):
        value = contract()
        parsed = probe.decode_contract(probe.canonical(value))
        self.assertTrue(probe.qualify(copy.deepcopy(value['observations']['root/qa']),
                                     parsed, 'root', 'qa'))
        self.assertEqual(probe.sha256(probe.CUSTOMIZER_SOURCE), probe.CUSTOMIZER_SHA256)
        self.assertEqual(len(probe.CUSTOMIZER_SOURCE), 155)

    def test_duplicate_json_fields_are_refused(self):
        raw = probe.canonical(contract()).replace(
            b'"protocol":', b'"protocol":"duplicate","protocol":', 1)
        with self.assertRaisesRegex(probe.BootstrapRejected, 'duplicate_field'):
            probe.decode_contract(raw)

    def test_extra_contract_fields_are_not_permission(self):
        value = contract()
        value['allowAdditionalModules'] = True
        with self.assertRaisesRegex(probe.BootstrapRejected, 'contract_fields'):
            probe.decode_contract(probe.canonical(value))

    def test_module_origin_outside_stdlib_or_exact_customizer_refused(self):
        value = snapshot()
        value['modules']['external'] = {
            'file': '/usr/local/lib/python3.12/dist-packages/external.py',
            'cached': None, 'origin': '/usr/local/lib/python3.12/dist-packages/external.py',
            'loader': '_frozen_importlib_external.SourceFileLoader'}
        with self.assertRaisesRegex(probe.BootstrapRejected, 'ambient_origin'):
            probe.validate_snapshot(value)

    def test_apport_hook_cannot_be_reclassified_as_stdlib_startup(self):
        value = snapshot()
        value['modules']['apport_python_hook'] = value['modules']['site']
        with self.assertRaisesRegex(probe.BootstrapRejected, 'startup_modules'):
            probe.validate_snapshot(value)

    def test_extra_search_path_refused(self):
        value = snapshot()
        value['sysPath'].append('/tmp/other')
        with self.assertRaisesRegex(probe.BootstrapRejected, 'sys_path'):
            probe.validate_snapshot(value)

    def test_extra_builtin_module_is_observation_drift(self):
        expected = contract()
        observed = copy.deepcopy(expected['observations']['root/qa'])
        observed['startup']['modules']['extra_builtin'] = {
            'file': None, 'cached': None, 'origin': 'built-in',
            'loader': '_frozen_importlib.BuiltinImporter'}
        with self.assertRaisesRegex(probe.BootstrapRejected, 'observation_changed'):
            probe.qualify(observed, expected, 'root', 'qa')

    def test_cache_presence_or_hash_change_refused(self):
        expected = contract()
        observed = copy.deepcopy(expected['observations']['root/qa'])
        cached = '/usr/lib/python3.12/__pycache__/sitecustomize.cpython-312.pyc'
        observed['files'][cached] = {'canonicalPath': cached, 'bytes': 100, 'sha256': 'a' * 64}
        with self.assertRaisesRegex(probe.BootstrapRejected, 'observation_changed'):
            probe.qualify(observed, expected, 'root', 'qa')

    def test_json_boolean_cannot_alias_integer_file_size(self):
        expected = contract()
        expected['observations']['root/qa']['files'][probe.CUSTOMIZER]['bytes'] = 1
        observed = copy.deepcopy(expected['observations']['root/qa'])
        observed['files'][probe.CUSTOMIZER]['bytes'] = True
        with self.assertRaisesRegex(probe.BootstrapRejected, 'observation_changed'):
            probe.qualify(observed, expected, 'root', 'qa')

    def test_changed_import_hook_refused(self):
        expected = contract()
        observed = copy.deepcopy(expected['observations']['root/qa'])
        observed['startup']['pathHooks'].append('external.inject')
        with self.assertRaisesRegex(probe.BootstrapRejected, 'observation_changed'):
            probe.qualify(observed, expected, 'root', 'qa')

    def test_each_home_context_requires_its_exact_snapshot_including_pwd(self):
        value = probe.decode_contract(probe.canonical(contract()))
        for key, observed in value['observations'].items():
            label, context = key.split('/')
            with self.subTest(key=key):
                self.assertTrue(probe.qualify(observed, value, label, context))
                altered = copy.deepcopy(observed)
                modules = altered['startup']['modules']
                if 'pwd' in modules:
                    del modules['pwd']
                else:
                    modules['pwd'] = copy.deepcopy(value['observations']['root/qa']['startup']['modules']['pwd'])
                # The altered snapshot is valid in another declared context.
                # It remains invalid for this actor/context; nothing is ignored.
                with self.assertRaisesRegex(probe.BootstrapRejected, 'observation_changed'):
                    probe.qualify(altered, value, label, context)

    def test_context_map_refuses_missing_extra_old_protocol_and_crossed_actor(self):
        original = contract()
        for mutation in ('missing', 'extra', 'old_protocol', 'old_shape', 'alternative_list'):
            value = copy.deepcopy(original)
            if mutation == 'missing':
                del value['observations']['gateway/preopen']
            elif mutation == 'extra':
                value['observations']['root/preopen'] = copy.deepcopy(value['observations']['root/qa'])
            elif mutation == 'old_protocol':
                value['protocol'] = 'alaz-r168a1-os-bootstrap-contract-v1'
            elif mutation == 'old_shape':
                value = {'protocol': probe.PROTOCOL, 'observation': value['observations']['root/qa']}
            else:
                value['observations']['root/qa'] = [value['observations']['root/qa']]
            with self.subTest(mutation=mutation), self.assertRaises(probe.BootstrapRejected):
                probe.decode_contract(probe.canonical(value))
        for label, context in (('root', 'preopen'), ('gateway', 'worker'),
                               ('gateway', 'supervised'), ('root/qa', ''), (True, 'qa')):
            with self.subTest(label=label, context=context), \
                    self.assertRaisesRegex(probe.BootstrapRejected, 'actor_context'):
                probe.qualify(original['observations']['root/qa'], original, label, context)

    def test_only_explicit_qa_worker_supervised_preopen_contexts(self):
        self.assertEqual(set(probe.CONTEXTS), {'qa', 'worker', 'supervised', 'preopen'})
        for name, (environment, cwd) in probe.CONTEXTS.items():
            with self.subTest(name=name):
                self.assertEqual(probe.execution_context(name, dict(environment), cwd),
                                 {'name': name, 'environment': environment, 'cwd': cwd})

    def test_context_does_not_accept_other_environment_or_cwd(self):
        with self.assertRaisesRegex(probe.BootstrapRejected, 'fixed_environment'):
            probe.execution_context('qa', {**probe.ENVIRONMENT, 'HOME': '/other'}, '/')
        with self.assertRaisesRegex(probe.BootstrapRejected, 'fixed_environment'):
            probe.execution_context('preopen', dict(probe.CONTEXTS['preopen'][0]), '/')


@unittest.skipUnless(sys.platform == 'linux', 'Linux held-descriptor fixture semantics')
class BootstrapFileTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='r168-bootstrap-fixture-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.file = self.root / 'source.py'
        self.file.write_bytes(b'reviewed startup source\n')
        self.file.chmod(0o644)
        # Map only ownership and ancestry to this test's ordinary actor. The
        # descriptor/inode/link/permission/bound/race checks stay unchanged.
        self.ancestry = patch.object(probe, '_ancestry', return_value={})
        self.ancestry.start()
        self.addCleanup(self.ancestry.stop)
        owner = patch.object(probe, '_root_owned',
                             side_effect=lambda info: (info.st_uid, info.st_gid) == (os.getuid(), os.getgid()))
        owner.start()
        self.addCleanup(owner.stop)

    def test_actual_held_regular_file(self):
        raw, row = probe.read_regular(self.file)
        self.assertEqual(raw, self.file.read_bytes())
        self.assertEqual(row, {'bytes': len(raw), 'sha256': probe.sha256(raw)})

    def test_symlink_cannot_stand_in_for_regular_source(self):
        alias = self.root / 'alias.py'
        alias.symlink_to(self.file)
        with self.assertRaisesRegex(probe.BootstrapRejected, 'regular_path'):
            probe.read_regular(alias)

    def test_hard_linked_input_refused(self):
        os.link(self.file, self.root / 'other.py')
        with self.assertRaisesRegex(probe.BootstrapRejected, 'regular_metadata'):
            probe.read_regular(self.file)

    def test_writable_by_other_actor_refused(self):
        self.file.chmod(0o666)
        with self.assertRaisesRegex(probe.BootstrapRejected, 'regular_metadata'):
            probe.read_regular(self.file)

    def test_replacement_path_cannot_hide_behind_held_descriptor(self):
        replacement = self.root / 'replacement.py'
        replacement.write_bytes(self.file.read_bytes())
        replacement.chmod(0o644)
        original_read = os.read
        changed = False

        def read_then_replace(fd, count):
            nonlocal changed
            raw = original_read(fd, count)
            if raw and not changed:
                changed = True
                replacement.replace(self.file)
            return raw

        with patch.object(probe.os, 'read', side_effect=read_then_replace):
            with self.assertRaisesRegex(probe.BootstrapRejected, 'file_changed'):
                probe.read_regular(self.file)

    def test_pth_file_refused_even_without_an_import_line(self):
        (self.root / 'unexpected.pth').write_bytes(b'\n')
        with self.assertRaisesRegex(probe.BootstrapRejected, 'pth_not_qualified'):
            probe.site_directory_observation(str(self.root))

    def test_no_pth_directory_observation(self):
        self.assertEqual(probe.site_directory_observation(str(self.root)),
                         {'present': True, 'pthFiles': []})

    def test_optional_missing_cache_with_absent_parent(self):
        absent = self.root / 'missing-cache' / 'source.pyc'
        with patch.object(probe, '_source_path', return_value=absent):
            self.assertIsNone(probe.file_observation(str(absent), optional=True))


if __name__ == '__main__':
    unittest.main()
