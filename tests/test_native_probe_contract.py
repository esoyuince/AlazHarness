"""Launcher isolation contracts only; real-engine probes are opt-in and separately evidenced."""
import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location('native_probe_runner',ROOT/'scripts/run_native_hermes_probe.py')
MODULE=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

class ProbeEnvironmentTests(unittest.TestCase):
    def test_credentials_and_proxy_not_inherited(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ,{'OPENAI_API_KEY':'synthetic','ANTHROPIC_API_KEY':'synthetic','HTTPS_PROXY':'synthetic','PYTHONPATH':'synthetic','HERMES_HOME':'synthetic'},clear=False):
            env=MODULE.isolated_environment(Path(tmp))
            for name in ('OPENAI_API_KEY','ANTHROPIC_API_KEY','HTTPS_PROXY','PYTHONPATH'):
                self.assertNotIn(name,env)
            self.assertEqual(env['HERMES_HOME'],str(Path(tmp)/'profile'))
    def test_profile_and_os_homes_are_scoped(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);env=MODULE.isolated_environment(root)
            for name in ('HOME','USERPROFILE','LOCALAPPDATA','APPDATA','TEMP','TMP','HERMES_HOME','HERMES_RUNTIME_DIR'):
                self.assertTrue(Path(env[name]).resolve().is_relative_to(root.resolve()))
                self.assertTrue(Path(env[name]).is_dir())
    def test_runtime_cannot_lazily_install(self):
        with tempfile.TemporaryDirectory() as tmp:
            env=MODULE.isolated_environment(Path(tmp))
            self.assertEqual(env['HERMES_DISABLE_LAZY_INSTALLS'],'1')
            self.assertEqual(env['PYTHONDONTWRITEBYTECODE'],'1')

class UnifiedManifestTests(unittest.TestCase):
    def test_both_transports_share_single_manifest(self):
        import sys
        sys.path.insert(0,str(ROOT/'scripts'))
        from verify_components import inspect
        self.assertEqual(inspect(ROOT)['components'],10)
        self.assertFalse((ROOT/'packages/claw-hermes/upstream').exists())
        self.assertFalse((ROOT/'components.lock.json').exists())
    def test_missing_source_entry_rejected(self):
        import json,shutil,sys
        sys.path.insert(0,str(ROOT/'scripts'))
        from verify_components import inspect
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'config').mkdir()
            shutil.copy(ROOT/'sources.lock.json',root/'sources.lock.json')
            manifest=json.loads((ROOT/'config/components.lock.json').read_text(encoding='utf-8'))
            manifest['entries'].pop()
            (root/'config/components.lock.json').write_text(json.dumps(manifest),encoding='utf-8')
            with self.assertRaises(ValueError):inspect(root)


class PreparationPlanTests(unittest.TestCase):
    def test_frozen_builder_code_compiles_without_executing(self):
        import sys
        sys.path.insert(0,str(ROOT/'scripts'))
        from prepare_native_hermes import build_code
        code=build_code(Path('source-with-quote-\'x'),Path('fresh-output'))
        compile(code,'generated-build-code','exec')
        self.assertIn('pm.build_environment',code)
        self.assertIn('frozen=True',code)
        self.assertIn('no_install_project=True',code)
        self.assertNotIn('pip install',code)

if __name__=='__main__':unittest.main()
