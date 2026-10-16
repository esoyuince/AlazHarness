"""Independent live-profile consistency tests on real ExecutionBoundary.
Only the config-loader/registry ports are fixtures; no native Gateway, HTTP,
model or actual tool dispatch is performed. Changes affect a detached dict.
"""
import copy
from pathlib import Path
import sys
import tempfile
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'packages/claw-hermes'))
from execution_boundary import ExecutionBoundary, PROVIDER_BASE
from execution_budget import ExecutionDenied


class LiveProfileConsistencyTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        file=Path(tmp.name)/'allowed.txt';file.write_text('nonsecret fixture',encoding='utf-8')
        policy=dict(model='profile-fixture',max_provider_calls=3,max_tool_calls=1,
            input_ceiling_tokens=100,output_ceiling_tokens=20,total_token_limit=360,
            total_cost_microusd=1000,input_rate_microusd_per_million=1000000,
            output_rate_microusd_per_million=2000000)
        settings=dict(policy=policy,upstream_base_url='http://127.0.0.1:45812/v1',
            provider_bearer='p'*32,allowed_read_files=[str(file)])
        self.boundary=ExecutionBoundary(copy.deepcopy(settings))
        self.boundary.adapter=SimpleNamespace(_port=45811)
        self.cfg=dict(model=dict(provider='custom',default='profile-fixture',api_key='p'*32,
                                base_url='http://127.0.0.1:45811'+PROVIDER_BASE),
                      platform_toolsets={'api_server':['file']},gateway={'multiplex_profiles':False},
                      plugins={'enabled':['alaz-host-gate'],'entries':{'alaz-host-gate':{
                          'allow_tool_override':True,'settings':{'execution':copy.deepcopy(settings)}}}})
        self.context=SimpleNamespace(plugin_id='alaz-host-gate',
            get_config=lambda key:self.cfg['plugins']['entries']['alaz-host-gate']['settings'].get(key))
        self.boundary.register(self.context)
        config=ModuleType('hermes_cli.config')
        config.load_config_readonly=lambda:copy.deepcopy(self.cfg)
        package=ModuleType('hermes_cli');package.__path__=[];package.config=config
        self.addCleanup(patch.stopall)
        patch.dict(sys.modules,{'hermes_cli':package,'hermes_cli.config':config}).start()
        self.registry=patch.object(self.boundary.tools,'verify',return_value=None).start()
    def live(self):return self.cfg['plugins']['entries']['alaz-host-gate']['settings']['execution']
    def test_unchanged_profile_is_accepted(self):
        self.assertIsNone(self.boundary.validate_profile());self.registry.assert_called()
    def test_changed_main_route_refuses(self):
        self.cfg['model']['base_url']='http://127.0.0.1:45813/v1'
        with self.assertRaises(ExecutionDenied):self.boundary.validate_profile()
    def test_changed_main_credential_refuses(self):
        self.cfg['model']['api_key']='different-fixture-token'
        with self.assertRaises(ExecutionDenied):self.boundary.validate_profile()
    def test_missing_registry_guard_refuses(self):
        self.registry.side_effect=ExecutionDenied('file_guard_missing')
        with self.assertRaises(ExecutionDenied):self.boundary.validate_profile()
    def test_lowered_live_budget_is_not_silently_ignored(self):
        self.live()['policy']['max_provider_calls']=0
        with self.assertRaises(ExecutionDenied):self.boundary.validate_profile()
    def test_revoked_live_file_allowlist_is_not_silently_ignored(self):
        self.live()['allowed_read_files']=[]
        with self.assertRaises(ExecutionDenied):self.boundary.validate_profile()
    def test_changed_live_upstream_is_not_silently_ignored(self):
        self.live()['upstream_base_url']='http://127.0.0.1:45813/v1'
        with self.assertRaises(ExecutionDenied):self.boundary.validate_profile()
    def test_missing_live_execution_settings_refuses(self):
        del self.cfg['plugins']['entries']['alaz-host-gate']['settings']['execution']
        with self.assertRaises(ExecutionDenied):self.boundary.validate_profile()

if __name__=='__main__':unittest.main()
