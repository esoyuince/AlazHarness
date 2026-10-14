"""Root publication/CI contracts, no network or upstream execution."""
import copy
import json
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from ci_check import EXPECTED, credential_hits, private_path, require_nonzero_tests, validate_sources

class HygieneTests(unittest.TestCase):
    def test_github_token_detected_without_echo(self):
        self.assertEqual(credential_hits(('gh' + 'p_' + 'A' * 36).encode()), ['github-token'])
    def test_private_key_detected(self):
        self.assertEqual(credential_hits(('-----BEGIN ' + 'OPENSSH PRIVATE KEY-----').encode()), ['private-key'])
    def test_model_key_detected(self):
        self.assertIn('model-key', credential_hits(('sk-' + 'proj-' + 'A' * 40).encode()))
    def test_credential_url_detected(self):
        self.assertIn('credential-url', credential_hits(('https://' + 'alice:password@example.org').encode()))
    def test_public_text_allowed(self):
        self.assertEqual(credential_hits(b'https://github.com/esoyuince/AlazHarness.git'), [])
    def test_runtime_paths_blocked(self):
        for p in ('runtime/x', 'scratch/x', '.alaz-ci/tests.json', '.env', '.env.local', 'config/secrets.json', 'config/x.pem'):
            with self.subTest(p=p): self.assertTrue(private_path(p))
    def test_examples_allowed(self):
        for p in ('.env.example', 'config/development.example.json', 'docs/CI.md'):
            with self.subTest(p=p): self.assertFalse(private_path(p))
    def test_zero_tests_fail_closed(self):
        with self.assertRaises(ValueError): require_nonzero_tests(0)
    def test_nonzero_tests_allowed(self):
        require_nonzero_tests(1)

class SourceContracts(unittest.TestCase):
    def setUp(self):
        self.lock = {'schema_version': 1, 'project': 'AlazHarness', 'repositories': []}
        self.entries = {}; self.modules = ''
        for n, (p, origin, upstream) in EXPECTED.items():
            self.lock['repositories'].append({'name': n, 'path': p, 'origin': origin, 'upstream': upstream, 'commit': 'a' * 40, 'file_sha256': {'LICENSE': 'b' * 64}})
            self.entries[p] = ('160000', 'a' * 40)
            self.modules += f'[submodule "{n}"]\npath = {p}\nurl = {origin}\n'
    def test_matching_sources_pass(self):
        self.assertEqual(validate_sources(self.lock, self.modules, self.entries), [])
    def test_pin_mismatch_fails(self):
        self.entries['vendor/openclaw'] = ('160000', 'c' * 40)
        self.assertTrue(validate_sources(self.lock, self.modules, self.entries))
    def test_extra_submodule_fails(self):
        self.assertTrue(validate_sources(self.lock, self.modules + '[submodule "extra"]\npath=x\nurl=https://example.org/x\n', self.entries))
    def test_foreign_url_fails(self):
        self.assertTrue(validate_sources(self.lock, self.modules.replace('https://github.com/', 'https://example.org/'), self.entries))
    def test_executable_submodule_update_fails(self):
        self.assertTrue(validate_sources(self.lock, self.modules + 'update = !dangerous\n', self.entries))
    def test_missing_license_digest_fails(self):
        self.lock['repositories'][0]['file_sha256'] = {}
        self.assertTrue(validate_sources(self.lock, self.modules, self.entries))
    def test_duplicate_source_fails(self):
        self.lock['repositories'][1] = copy.deepcopy(self.lock['repositories'][0])
        self.assertTrue(validate_sources(self.lock, self.modules, self.entries))

if __name__ == '__main__': unittest.main()
