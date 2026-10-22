"""Source-bound native F111E274 proof and negative receipt mutation tests."""
from copy import deepcopy
import hashlib,json
from pathlib import Path
import sys,unittest
ROOT=Path(__file__).resolve().parents[1];E=ROOT/'evidence/d3b-http-confined-f111e274'
sys.path.insert(0,str(ROOT/'scripts/qa'))
import f111e274_receipt as v
class ConfinedReadinessEvidence(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.outer=json.loads((E/'native-001-stdout.txt').read_bytes())
        cls.manifest=json.loads((E/'native-001-intent.json').read_text())['sourceSha256']
    def mutate(self,fn):
        outer=deepcopy(self.outer);result=json.loads(outer['nativeStdout']);fn(result)
        outer['nativeStdout']=json.dumps(result);return outer
    def refuse(self,outer):
        with self.assertRaises(v.InvalidReceipt):v.verify(outer,self.manifest)
    @staticmethod
    def targets(result):return [e for e in result['events'] if e.get('state')=='RESULT']
    def test_actual_complete_receipt(self):
        got=v.verify(self.outer,self.manifest);self.assertEqual(got['httpResponses'],22);self.assertIs(got['launchAuthorized'],False)
        self.assertEqual(json.loads((E/'native-001-result.json').read_text())['exitCode'],0)
    def test_current_code_matches_executed_code(self):
        for name,digest in self.manifest.items():
            if name.startswith(('packages/','scripts/','tests/')):self.assertEqual(hashlib.sha256((ROOT/name).read_bytes()).hexdigest(),digest,name)
        baseline=json.loads((E/'baseline.json').read_text())['sources']
        for name in ('packages/claw-hermes/gateway_http_readiness.py','packages/claw-hermes/gateway_store_startup.py','packages/claw-hermes/gateway_state_projection.py'):
            self.assertEqual(self.manifest[name],baseline[name])
    def test_native_dependencies_are_pinned(self):
        inventory=json.loads((E/'source-inventory.json').read_text());self.assertEqual(inventory['files'],self.manifest)
        self.assertEqual(inventory['nativePin'],'eb75627faf532fa6ffbdae59a0d14b0b385fc780')
        self.assertEqual(inventory['nativeCount'],276)
        for name,item in inventory['nativeSources'].items():self.assertEqual(self.manifest['vendor-native/'+name],item['sha256'])
    def test_cleanup_is_separate_and_complete(self):
        c=json.loads((E/'cleanup.json').read_text());self.assertEqual(c['result'],'CLEAN')
        self.assertTrue(all(x is True for x in c['checks'].values()));self.assertEqual(c['matchingProcesses'],[])
        self.assertEqual(c['imageBytes'],64*1024*1024);self.assertIs(c['imageRetained'],True)
    def test_host_reachability_cannot_be_called_isolated(self):
        def change(r):next(e for e in r['events'] if e.get('phase')=='write-host-http-probe')['errno']=0
        self.refuse(self.mutate(change))
    def test_ready_after_revocation_is_rejected(self):
        def change(r):self.targets(r)[0]['httpResults'][9]['status']=200
        self.refuse(self.mutate(change))
    def test_fake_native_or_broader_gateway_acceptance_is_rejected(self):
        self.refuse(self.mutate(lambda r:r.update(nativeAgentHttpAdapterStarted=True)))
        def change(r):self.targets(r)[0]['httpStartup']['runtimeAdmissionAuthorized']=True
        self.refuse(self.mutate(change))
    def test_missing_second_lifetime_is_rejected(self):
        def change(r):r['events']=[e for e in r['events'] if not(e.get('state')=='RESULT' and e.get('mode')=='read')]
        self.refuse(self.mutate(change))
    def test_wrong_process_or_root_identity_is_rejected(self):
        for field in ('pid','uids'):
            def change(r):self.targets(r)[0]['receipt']['afterDrop'][field]=0 if field=='pid' else [0]*4
            self.refuse(self.mutate(change))
    def test_changed_persistent_inode_is_rejected(self):
        def change(r):self.targets(r)[1]['stores']['state.db']['inode']+=1
        self.refuse(self.mutate(change))
    def test_pending_work_epoch_advance_is_rejected(self):
        def change(r):self.targets(r)[1]['blockedStartup']['epochMayHaveAdvanced']=True
        self.refuse(self.mutate(change))
    def test_false_check_integer_success_or_import_hash_is_rejected(self):
        for val in (False,1):self.refuse(self.mutate(lambda r:r['checks'].update(zero_physical_provider_attempts=val)))
        def change(r):self.targets(r)[0]['nativeSources']['packages/claw-hermes/gateway_http_readiness.py']='f'*64
        self.refuse(self.mutate(change))
if __name__=='__main__':unittest.main()
