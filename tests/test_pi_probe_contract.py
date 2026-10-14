"""Offline gate and probe-launch contracts; these do not run Pi or install it."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from run_native_pi_probe import isolated_environment, safe_source_path, source_manifest_sha256, validate_result
from prepare_native_pi import NPM_FLAGS, npm_command
CASES=('success','zero-budget','invalid-limits','invalid-endpoints','wrong-target','wrong-method',
       'pre-abort','concurrent-reservation','uncertain-not-refunded','http-error-consumes','redirect-denied',
       'closed-no-revival','snapshot-isolated','request-object','request-signal','invalid-fetch')

class RequestGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.node=shutil.which('node')
        if not cls.node:raise RuntimeError('Node is required; never skip gate tests')
    def run_case(self,name):
        env={k:v for k,v in os.environ.items() if k.upper() in ('PATH','SYSTEMROOT','WINDIR','TEMP','TMP')}
        p=subprocess.run([self.node,str(ROOT/'tests/node/provider-gate-cases.mjs'),name],env=env,cwd=ROOT,
                         capture_output=True,text=True,encoding='utf-8',timeout=10)
        self.assertEqual(p.returncode,0,p.stdout+p.stderr)
        value=json.loads(p.stdout);self.assertEqual(value['result'],'PASS');self.assertEqual(value['case'],name)

for name in CASES:
    def generated(self,case=name):self.run_case(case)
    generated.__name__='test_'+name.replace('-','_')
    setattr(RequestGateTests,generated.__name__,generated)

class NativeProbeGuards(unittest.TestCase):
    def test_no_credentials_or_node_injection(self):
        with tempfile.TemporaryDirectory() as tmp,patch.dict(os.environ,{'OPENAI_API_KEY':'synthetic','NODE_OPTIONS':'synthetic','HTTPS_PROXY':'synthetic','PI_CODING_AGENT_DIR':'synthetic'}):
            env=isolated_environment(Path(tmp))
            for key in ('OPENAI_API_KEY','NODE_OPTIONS','HTTPS_PROXY'):self.assertNotIn(key,env)
            self.assertEqual(env['PI_CODING_AGENT_DIR'],str(Path(tmp)/'profile'))
    def test_os_homes_are_isolated(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);env=isolated_environment(root)
            for key in ('HOME','USERPROFILE','APPDATA','LOCALAPPDATA','TEMP','TMP','XDG_CONFIG_HOME','PI_CODING_AGENT_DIR'):
                self.assertTrue(Path(env[key]).resolve().is_relative_to(root.resolve()))
    def test_path_traversal_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            for name in ('../x','/etc/x','C:/x','a\\b','.git/config',''):
                with self.subTest(name=name),self.assertRaises(ValueError):safe_source_path(Path(tmp),name)
    def test_manifest_hash_ignores_serialization_not_content(self):
        left={'b':'22','a':'11'};right=json.loads('{\r\n  \"a\":\"11\",\r\n  \"b\":\"22\"\r\n}')
        self.assertEqual(source_manifest_sha256(left),source_manifest_sha256(right))
        right['a']='different';self.assertNotEqual(source_manifest_sha256(left),source_manifest_sha256(right))
    def test_regular_source_path_accepted(self):
        with tempfile.TemporaryDirectory() as tmp:self.assertEqual(safe_source_path(Path(tmp),'packages/agent/src/agent.ts'),Path(tmp)/'packages/agent/src/agent.ts')
    def test_complete_receipt_passes(self):
        validate_result(self.receipt(),'file-read',0)
    def receipt(self):return {'scenario':'file-read','result':'PASS','serverClosed':True,'openServerSockets':0,'settled':True,'modelInferenceCalls':0,'paidCalls':0}
    def test_false_success_rejected(self):
        for updates in ({'openServerSockets':1},{'settled':False},{'paidCalls':1},{'modelInferenceCalls':1},{'result':'FAIL'},{'scenario':'other'},{'serverClosed':False}):
            value=self.receipt();value.update(updates)
            with self.subTest(updates=updates),self.assertRaises(ValueError):validate_result(value,'file-read',0)
    def test_nonzero_exit_rejected(self):
        with self.assertRaises(ValueError):validate_result(self.receipt(),'file-read',1)
    def test_install_flags_are_nonexecuting(self):
        self.assertIn('--ignore-scripts',NPM_FLAGS);self.assertIn('--omit=dev',NPM_FLAGS)
        self.assertEqual(NPM_FLAGS[0],'ci');self.assertNotIn('install',NPM_FLAGS)
    def test_npm_cli_requires_existing_explicit_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);node=root/'node';cli=root/'npm-cli.js'
            with self.assertRaises(ValueError):npm_command(node,cli)
            cli.write_text('// test fixture',encoding='utf-8')
            command=npm_command(node,cli);self.assertEqual(command[:2],[str(node),str(cli.resolve())]);self.assertIn('--ignore-scripts',command)

if __name__=='__main__':unittest.main()
