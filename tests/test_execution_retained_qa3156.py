"""Offline receipt-checker guards. All files/receipts are SYNTHETIC temp fixtures.
No native Gateway, provider, network, real profile or subprocess is used here.
"""
from pathlib import Path
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts/qa'))
from execution_retained_qa3156 import REQUIRED_PROGRAMS,validate_programs,validate_client,filehash

class MeasuredProgramsTests(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup);self.root=Path(t.name)
        self.programs={}
        for name in REQUIRED_PROGRAMS:
            p=self.root/name;p.parent.mkdir(parents=True,exist_ok=True)
            p.write_text('synthetic source fixture, never executed',encoding='utf-8')
            self.programs[name]=filehash(p)
    def test_complete_unchanged_manifest(self):validate_programs(self.programs,self.root)
    def test_empty_manifest_is_not_acceptance(self):
        with self.assertRaisesRegex(ValueError,'incomplete'):validate_programs({},self.root)
    def test_missing_measured_dependency_refuses(self):
        del self.programs['scripts/native_gateway_worker.py']
        with self.assertRaisesRegex(ValueError,'incomplete'):validate_programs(self.programs,self.root)
    def test_changed_measured_source_refuses(self):
        (self.root/'scripts/native_gateway_worker.py').write_text('different fixture',encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'changed'):validate_programs(self.programs,self.root)
    def test_escape_path_refuses(self):
        self.programs['../outside.py']='a'*64
        with self.assertRaisesRegex(ValueError,'escaping'):validate_programs(self.programs,self.root)
    def test_malformed_sha_refuses(self):
        self.programs['scripts/native_gateway_worker.py']=True
        with self.assertRaisesRegex(ValueError,'malformed'):validate_programs(self.programs,self.root)

class ClientIdentityTests(unittest.TestCase):
    def sdk(self):return dict(success=False,exception='PermissionDeniedError',error_code='provider_attempt_limit',nonce='a'*32,sdk_invocations=1)
    def test_exact_sdk_limit_receipt(self):validate_client(self.sdk(),'sdk-retry-limit','a'*32)
    def test_any_403_not_accepted_as_budget_limit(self):
        d=self.sdk();d['error_code']='provider_authentication_required'
        with self.assertRaisesRegex(ValueError,'specifically'):validate_client(d,'sdk-retry-limit','a'*32)
    def test_success_not_accepted_as_retry_denial(self):
        d=self.sdk();d['success']=True
        with self.assertRaises(ValueError):validate_client(d,'sdk-retry-limit','a'*32)
    def test_wrong_nonce_refuses(self):
        with self.assertRaisesRegex(ValueError,'identity'):validate_client(self.sdk(),'sdk-retry-limit','b'*32)
    def test_missing_nonce_refuses(self):
        d=self.sdk();del d['nonce']
        with self.assertRaises(ValueError):validate_client(d,'sdk-retry-limit','a'*32)
    def test_repeated_invocation_not_single_sdk_retry(self):
        d=self.sdk();d['sdk_invocations']=2
        with self.assertRaises(ValueError):validate_client(d,'sdk-retry-limit','a'*32)
    def test_exact_unknown_price_refusal(self):validate_client(dict(nonce='a'*32,refusal='host_http_404'),'unknown-price','a'*32)
    def test_connection_failure_not_unknown_price_acceptance(self):
        with self.assertRaisesRegex(ValueError,'not proven'):validate_client(dict(nonce='a'*32,refusal='host_timeout'),'unknown-price','a'*32)

if __name__=='__main__':unittest.main()
