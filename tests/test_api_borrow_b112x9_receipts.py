"""Offline custody of real native borrowed-store tests, not extra native runs."""
import ast
import hashlib
import json
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
E=ROOT/'evidence/d3b-api-borrow-b112x9'
def read(name):return json.loads((E/name).read_text(encoding='utf-8'))
class BorrowedAPIEvidence(unittest.TestCase):
    def test_actual_native_adapter_twenty_seven_methods_pass(self):
        r=read('adapter-004/result.json')
        self.assertEqual(r['result'],'PASS_NATIVE_BORROWED_API_LIFECYCLE')
        self.assertEqual((r['total'],r['passed'],r['failures'],r['errors'],r['skipped']),(27,27,0,0,0))
        self.assertEqual(r['audit']['connects'],0);self.assertEqual(r['newNetworkAttemptsDuringTests'],0)
        self.assertIs(r['sourcesUnchanged'],True)
        self.assertIs(r['nativeAdapterAndThreeStoresReal'],True)
        for k in ('nativeListenerStarted','A109ThirdStoreIntegrated','healthyBusyPolicyImplemented','fullD3BAccepted'):
            self.assertIs(r[k],False)
        self.assertEqual(r['qaSha256'],hashlib.sha256((ROOT/'scripts/qa/b112x9_adapter_probe.py').read_bytes()).hexdigest())
    def test_each_method_has_unique_success_record(self):
        tree=ast.parse((ROOT/'scripts/qa/b112x9_adapter_probe.py').read_text(encoding='utf-8'))
        c=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='NativeBorrowTests')
        names={n.name for n in c.body if isinstance(n,ast.AsyncFunctionDef) and n.name.startswith('test_')}
        log=(E/'adapter-004/tests.txt').read_text(encoding='utf-8')
        seen=[line.split(' ',1)[0] for line in log.splitlines() if line.startswith('test_') and line.endswith(' ... ok')]
        self.assertEqual(len(names),27);self.assertEqual(set(seen),names);self.assertEqual(len(seen),27)
    def test_tested_patch_matches_native_feature_and_current_artifact(self):
        m=json.loads((ROOT/'config/hermes-api-borrow-b112x9.json').read_text(encoding='utf-8'))
        r=read('adapter-004/result.json');commit=read('native-commit.json')
        self.assertEqual(hashlib.sha256((ROOT/m['patchPath']).read_bytes()).hexdigest(),m['patchSha256'])
        self.assertEqual(m['nativeFeatureCommit'],commit['combinedNativeCommit'])
        self.assertEqual(m['requiredResponseParentCommit'],commit['responseParentCommit'])
        self.assertEqual(r['sourceSha256'],m['resultHashes']|m['requiredResponseFiles'])
        self.assertEqual(r['nativeImportedSources'],{n:v['sha256'] for n,v in commit['imports'].items()})
        self.assertEqual(len(r['nativeImportedSources']),309)
        self.assertIs(commit['installedVendorMainUnchanged'],True)
        self.assertIs(commit['sourceLockUpdated'],False)
        self.assertEqual(m['borrowedConnect'],'REFUSED')
        self.assertEqual(m['activation'],'NOT_INSTALLED_SOURCE_LOCK_UNCHANGED')
    def test_linux_baseline_and_borrowed_are_separate_actual_comparisons(self):
        base=read('baseline-response-002-stdout.txt');new=read('borrowed-response-001-stdout.txt')
        for o in (base,new):
            self.assertEqual(o['exitCode'],0);self.assertIs(o['sourceUnchanged'],True);self.assertIs(o['temporaryRootRemoved'],True)
            q=json.loads(o['stdout']);self.assertTrue(all(v is True for v in q['checks'].values()))
            self.assertIs(q['nativeFunctionsMocked'],False);self.assertIs(q['rootUsed'],False)
            self.assertIs(q['httpAdapterStarted'],False);self.assertEqual(q['providerCalls'],0)
            self.assertEqual(q['sourceSha256']['scripts/qa/b112x9_response_probe.py'],hashlib.sha256((ROOT/'scripts/qa/b112x9_response_probe.py').read_bytes()).hexdigest())
        b=json.loads(base['stdout']);n=json.loads(new['stdout'])
        self.assertEqual(b['mode'],'baseline');self.assertEqual(n['mode'],'borrowed')
        self.assertFalse(b['initialCommittedResponseSettled']);self.assertTrue(n['initialCommittedResponseSettled'])
        self.assertEqual(next(e for e in b['events'] if e['phase']=='settle-committed-under-lock')['newSqliteConnections'],1)
        self.assertEqual(next(e for e in n['events'] if e['phase']=='settle-committed-under-lock')['newSqliteConnections'],0)
    def test_actual_sqlite_lock_survives_both_paths_and_response_close(self):
        for name in ('baseline-response-002-stdout.txt','borrowed-response-001-stdout.txt'):
            q=json.loads(read(name)['stdout']);events=[e for e in q['events'] if e['phase']=='competitor']
            self.assertEqual([e['state'] for e in events],['BUSY','BUSY','BUSY','ACQUIRED'])
            self.assertTrue(all(e['code']==5 for e in events[:3]))
        q=json.loads(read('borrowed-response-001-stdout.txt')['stdout'])
        event=next(e for e in q['events'] if e['phase']=='settle-uncommitted-canonical')
        self.assertEqual(event['error']['code'],'response_canonical_transaction_active')
        self.assertEqual(event['newSqliteConnections'],0)
        self.assertIs(q['checks']['temp_terminal_not_settled'],True)
        self.assertIs(q['checks']['caller_transaction_retained'],True)
    def test_response_sources_are_exact_complementary_patch(self):
        expected=read('response-source-snapshot-001.json')['sources']
        q=json.loads(read('borrowed-response-001-stdout.txt')['stdout'])
        for name,digest in expected.items():
            self.assertEqual(q['sourceSha256']['vendor-native/'+name],digest)
            self.assertEqual(q['actualImportedSources']['vendor-native/'+name],digest)
        self.assertNotEqual(json.loads(read('baseline-response-002-stdout.txt')['stdout'])['sourceSha256']['vendor-native/gateway/platforms/api_server_response_store.py'],expected['gateway/platforms/api_server_response_store.py'])
    def test_initial_failed_attempts_not_relabelled(self):
        self.assertEqual(read('adapter-001/result.json')['errors'],26)
        self.assertEqual(read('adapter-002/result.json')['errors'],2)
        r=read('adapter-003/result.json');self.assertEqual(r['passed'],27);self.assertEqual(r['result'],'FAIL')
        self.assertEqual(read('baseline-response-stdout.txt')['exitCode'],1)
        self.assertFalse(read('windows-loop-fixture-correction.json')['nativeProductChanged'])
        self.assertFalse(read('denied-import-probe-accounting.json')['networkPermissionBroadened'])
        self.assertTrue((E/'borrowed-before-status-writer-fix.py.txt').is_file())
    def test_optional_ipv6_probe_denied_not_a_started_api_listener(self):
        r=read('adapter-004/result.json')
        self.assertEqual(r['networkDeniedDuringKnownImportProbe'],1)
        self.assertEqual(r['audit']['network'],1)
        self.assertEqual(r['newNetworkAttemptsDuringTests'],0)
        e=r['audit']['deniedNetworkEvents'];self.assertEqual(len(e),1)
        self.assertEqual(e[0]['event'],'socket.bind');self.assertIn('connection.py:_has_ipv6',e[0]['stack'])
        self.assertEqual(r['audit']['frameworkSocketEvents'],54)
        self.assertIs(r['cleanupFaultAwaitablesDoubled'],True)

if __name__=='__main__':unittest.main()
