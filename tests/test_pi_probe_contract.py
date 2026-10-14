"""Pi launcher guards and host contracts; native Pi is an explicitly separate gate."""
from pathlib import Path
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from pi_probe_support import check_source, fresh_runtime_path, isolated_env, pi_record

class PiLauncherTests(unittest.TestCase):
    def test_credentials_not_inherited(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ,{'OPENAI_API_KEY':'synthetic','NODE_OPTIONS':'synthetic','NPM_TOKEN':'synthetic','HTTPS_PROXY':'synthetic'}):
            env=isolated_env(Path(temp))
            for key in ('OPENAI_API_KEY','NODE_OPTIONS','NPM_TOKEN','HTTPS_PROXY'):self.assertNotIn(key,env)
    def test_homes_are_scoped(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);env=isolated_env(root)
            for key in ('HOME','USERPROFILE','LOCALAPPDATA','APPDATA','TEMP','NPM_CONFIG_CACHE','PI_CODING_AGENT_DIR'):
                self.assertTrue(Path(env[key]).resolve().is_relative_to(root.resolve()))
    def test_lifecycle_disabled(self):
        with tempfile.TemporaryDirectory() as temp:self.assertEqual(isolated_env(Path(temp))['NPM_CONFIG_IGNORE_SCRIPTS'],'true')
    def test_runtime_path_outside_refused(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            with self.assertRaises(ValueError):fresh_runtime_path(root,root/'outside')
    def test_runtime_path_existing_refused(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);p=root/'runtime/x';p.mkdir(parents=True)
            with self.assertRaises(FileExistsError):fresh_runtime_path(root,p)
    def test_runtime_path_valid_does_not_create(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);p=root/'runtime/x';self.assertEqual(fresh_runtime_path(root,p),p);self.assertFalse(p.exists())
    def test_wrong_source_pin_refused(self):
        with patch('pi_probe_support.git',return_value='0'*40):
            with self.assertRaises(ValueError):check_source(Path('missing'))
    def test_modified_source_refused(self):
        with patch('pi_probe_support.git',side_effect=[pi_record()['commit'],' M source.ts']):
            with self.assertRaises(ValueError):check_source(Path('missing'))

class PiHostContractTests(unittest.TestCase):
    pass

def case(name):
    def test(self):
        node=shutil.which('node');self.assertIsNotNone(node,'Node is required; never silently skip')
        r=subprocess.run([node,str(ROOT/'tests/node/pi-host-cases.mjs'),name],cwd=ROOT,capture_output=True,text=True,encoding='utf-8',timeout=15)
        self.assertEqual(r.returncode,0,r.stdout+r.stderr)
    return test

for name in ('concurrent_cap','bad_endpoint','bad_limit','wrong_target','redirect_not_followed','valid_receipt','missing_marker_rejected','false_idle_rejected','malformed_receipt_rejected','budget_cause_preserved'):
    setattr(PiHostContractTests,'test_'+name,case(name))

if __name__=='__main__':unittest.main()
