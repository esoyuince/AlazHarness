"""Independent HTTP proof custody; offline checks do not repeat network tests."""
import ast
import hashlib
import json
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
E=ROOT/'evidence/d3b-http-qa-r110x6c2'

class IndependentHttpReceipts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.windows=json.loads((E/'windows-current/result.json').read_text(encoding='utf-8'))
        cls.linux=json.loads((E/'linux-http-stdout.txt').read_bytes())
    def test_same_pinned_runtime_and_audit_in_both_platforms(self):
        runtime=hashlib.sha256((E/'http-runtime-snapshot-002.py.txt').read_bytes()).hexdigest()
        qa=hashlib.sha256((ROOT/'scripts/qa/r110x_http_audit.py').read_bytes()).hexdigest()
        for report in (self.windows,self.linux['testResult']):
            self.assertEqual(report['runtimeSha256'],runtime)
            self.assertEqual(report['qaSha256'],qa)
            self.assertIs(report['runtimeSourceUnchanged'],True)
        self.assertEqual(self.linux['sourceSha256']['packages/claw-hermes/gateway_http_readiness.py'],runtime)
        self.assertEqual(self.linux['sourceSha256']['scripts/qa/r110x_http_audit.py'],qa)
    def test_twenty_nine_real_http_cases_not_native_store_acceptance(self):
        for report in (self.windows,self.linux['testResult']):
            self.assertEqual(report['result'],'PASS_HTTP_ONLY_EXPLICIT_STORAGE_DOUBLES')
            self.assertEqual((report['total'],report['passed'],report['skipped'],report['errors'],report['failures']),(29,29,0,0,0))
            self.assertIs(report['actualLoopbackHttp'],True)
            self.assertIs(report['profileAndIdentityDoubled'],True)
            for key in ('nativeStorageTested','fullConfinementTested','fullD3BAccepted'):self.assertIs(report[key],False)
            self.assertEqual(report['providerCalls'],0)
        self.assertEqual(self.linux['exitCode'],0)
        self.assertEqual((self.linux['uid'],self.linux['gid']),(23001,23003))
        self.assertIs(self.linux['temporaryRootRemoved'],True)
        self.assertIs(self.linux['sourcesUnchanged'],True)
        self.assertIs(self.linux['rootUsed'],False)
    def test_every_case_has_unique_pass_in_both_logs(self):
        tree=ast.parse((ROOT/'scripts/qa/r110x_http_audit.py').read_text(encoding='utf-8'))
        case=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='RealHttpAudit')
        methods={n.name for n in case.body if isinstance(n,ast.AsyncFunctionDef) and n.name.startswith('test_')}
        self.assertEqual(len(methods),29)
        for log in ((E/'windows-current/unittest.txt').read_text(encoding='utf-8'),self.linux['testLog']):
            found=[line.split(' ',1)[0] for line in log.splitlines() if line.startswith('test_') and line.endswith(' ... ok')]
            self.assertEqual(set(found),methods);self.assertEqual(len(found),29)
    def test_actual_malformed_header_failure_then_narrow_rejection(self):
        old=json.loads((E/'windows-003/result.json').read_text(encoding='utf-8'))
        self.assertEqual((old['total'],old['passed'],old['failures'],old['errors']),(29,28,1,0))
        self.assertEqual(old['failureIds'],['__main__.RealHttpAudit.test_non_utf8_authorization_rejects_as_auth_not_server_error'])
        self.assertEqual(old['runtimeSha256'],hashlib.sha256((E/'http-runtime-snapshot-001.py.txt').read_bytes()).hexdigest())
        self.assertIn('500 != 401',(E/'windows-003/unittest.txt').read_text(encoding='utf-8'))
        self.assertIn('UnicodeEncodeError',(E/'windows-003-stderr.txt').read_text(encoding='utf-8'))
        self.assertNotEqual(old['runtimeSha256'],self.windows['runtimeSha256'])
        fixed=json.loads((E/'windows-ascii-fixed/result.json').read_text(encoding='utf-8'))
        self.assertEqual(fixed['passed'],29)
        finding=json.loads((E/'authorization-ascii-finding.json').read_text(encoding='utf-8'))
        self.assertIs(finding['otherWorktreeModified'],False)
    def test_dependency_transport_matches_independently_verified_records(self):
        inventory=json.loads((E/'http-dependency-custody.json').read_text(encoding='utf-8'))
        expected={}
        for package,details in inventory['packages'].items():
            self.assertEqual(len(details['recordSha256']),64)
            for name,digest in details['files'].items():expected['dependencies/'+name]=digest
        actual={n:h for n,h in self.linux['sourceSha256'].items() if n.startswith('dependencies/')}
        self.assertEqual(actual,expected);self.assertEqual(len(expected),108)
        self.assertIs(inventory['nativeExtensionsTransferred'],False)
        self.assertIs(self.linux['compiledExtensionsTransferred'],False)
        baseline=json.loads((E/'baseline.json').read_text(encoding='utf-8'))['sources']
        for name,digest in self.linux['sourceSha256'].items():
            if name.startswith('packages/') and not name.endswith('/gateway_http_readiness.py'):
                self.assertEqual(digest,baseline[name])
    def test_initial_harness_errors_retained_not_product_bugs(self):
        old=json.loads((E/'windows-001/result.json').read_text(encoding='utf-8'))
        self.assertEqual(old['errors'],4);self.assertEqual(len(set(old['errorIds'])),2)
        self.assertEqual(old['failures'],0)
        self.assertIn("object attribute 'cleanup' is read-only",(E/'windows-001/unittest.txt').read_text(encoding='utf-8'))
        repair=json.loads((E/'test-fixture-correction.json').read_text(encoding='utf-8'))
        self.assertIs(repair['runtimeProductChanged'],False)
        passed=json.loads((E/'windows-002/result.json').read_text(encoding='utf-8'))
        self.assertEqual((passed['total'],passed['passed']),(25,25))
        self.assertEqual(passed['runtimeSha256'],old['runtimeSha256'])

if __name__=='__main__':unittest.main()
