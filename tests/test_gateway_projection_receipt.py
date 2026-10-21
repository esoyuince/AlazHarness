"""Pinned real G84E projection observations; not full Hermes acceptance."""
import ast
import hashlib
import io
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
ROOT=Path(__file__).resolve().parents[1]
E=ROOT/'evidence/d3b-gateway-projection-g84e'
SOURCES={'packages/claw-hermes/gateway_projection.py','scripts/qa/g84e_accept.py',
         'scripts/qa/g84e_child.py','scripts/qa/g84e_target.py'}

class NativeProjectionReceipt(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.r=json.loads((E/'native-n03.json').read_text())
    def test_current_source_custody(self):
        hashes=json.loads((E/'native-n03-source.json').read_text())
        self.assertEqual(set(hashes),SOURCES)
        for name,expected in hashes.items():
            with self.subTest(path=name):
                self.assertEqual(hashlib.sha256((ROOT/name).read_bytes()).hexdigest(),expected)
                self.assertEqual(self.r['sourceBefore'][Path(name).name],expected)
                self.assertEqual(self.r['sourceAfter'][Path(name).name],expected)
    def test_real_terminal_native_outcomes(self):
        r=self.r;t=r['details']['target']
        self.assertEqual(r['result'],'PASS_SCOPED_GATEWAY_PROJECTION')
        self.assertEqual(len(r['checks']),18);self.assertEqual(r['checkCount'],18)
        self.assertTrue(all(v is True for v in r['checks'].values()))
        self.assertEqual(t['result'],'PASS');self.assertEqual(len(t['checks']),23)
        self.assertTrue(all(v is True for v in t['checks'].values()))
        self.assertEqual(r['gatewayExitCode'],0);self.assertIsNone(r['error'])
        self.assertIs(r['forcedCleanup'],False)
    def test_identity_peer_and_actual_network_denials(self):
        r=self.r;s=r['details']['supervisorObservation'];t=r['details']['target']['details']
        self.assertEqual(s['fields']['Uid'],['23001']*4)
        self.assertEqual(s['fields']['Gid'],['23003']*4)
        self.assertEqual(s['uidMap'],['0','0','4294967295'])
        self.assertEqual(t['ping']['peer'],{'pid':r['shutdown']['pid'],'uid':23002,'gid':23003})
        self.assertEqual(t['host_tcp']['errno'],111);self.assertEqual(t['host_abstract']['errno'],111)
        for name in ('unrelated_path','broker_sibling','late_host_workspace_socket'):
            self.assertEqual(t[name]['errno'],2)
        self.assertEqual(t['protectedCanaryErrnos'],[13,13])
    def test_host_positive_controls_and_private_file_preservation(self):
        r=self.r
        for name in ('hostPositiveControls','latePositiveControl'):
            c=r['details'][name];self.assertEqual(c['uid'],23001)
            self.assertTrue(c['connections']);self.assertTrue(all(c['connections']))
        self.assertEqual(r['privateBefore'],r['privateAfter'])
        self.assertEqual(r['shutdown']['counters']['pings'],2)
        self.assertEqual(r['shutdown']['counters']['physicalAttempts'],0)
    def test_scope_never_claims_persistent_state_or_real_hermes(self):
        for key in ('realHermesGateway','persistentGatewayState','providerDispatchTested',
                    'legacyIpcV2Activated','fullD3BAccepted'):
            self.assertIs(self.r[key],False)
        receipt=self.r['details']['entry']['projection']
        self.assertEqual(receipt['explicitHostSocketCount'],1)
        self.assertEqual(receipt['hostWritableDirectoriesBound'],0)
        self.assertEqual(self.r['modelCalls'],0)

class CleanupDiagnosticRegression(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Load only the pure diagnostic helper, never the Linux-only lab main.
        tree=ast.parse((ROOT/'scripts/qa/g84e_accept.py').read_text())
        nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='remaining_stderr']
        if len(nodes)!=1:raise AssertionError('missing exact helper')
        module=ast.fix_missing_locations(ast.Module(body=nodes,type_ignores=[]));ns={}
        exec(compile(module,'owned-cleanup-helper','exec'),ns)
        cls.helper=staticmethod(ns['remaining_stderr'])
    def test_closed_empty_stream_after_communicate(self):
        stream=io.BytesIO();stream.close()
        self.assertEqual(self.helper(SimpleNamespace(stderr=stream),''),'')
    def test_existing_diagnostic_not_read_twice(self):
        stream=io.BytesIO(b'never read')
        self.assertEqual(self.helper(SimpleNamespace(stderr=stream),'kept'),'kept')
        self.assertEqual(stream.tell(),0)
    def test_remaining_open_stream_read(self):
        self.assertEqual(self.helper(SimpleNamespace(stderr=io.BytesIO(b'error')),''),'error')
    def test_absent_stream_is_not_cleanup_failure(self):
        self.assertEqual(self.helper(SimpleNamespace(stderr=None),''),'')
    def test_diagnostic_io_error_cannot_abort_cleanup(self):
        class Broken:
            closed=False
            def read(self):raise OSError('fixture')
        self.assertEqual(self.helper(SimpleNamespace(stderr=Broken()),''),'qa_stderr_read_unavailable:OSError')

if __name__=='__main__':unittest.main()
