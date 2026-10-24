"""Offline bounded-flow evidence receipts, not more native executions."""
import hashlib,json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
E=ROOT/'evidence/d3b-finite-turn-qa-f134c6'
def read(name):return json.loads((E/name).read_text(encoding='utf-8'))
class FiniteFlowReceipt(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.r=read('independent-run-001/result.json');cls.o=read('independent-run-001-witness.json');cls.c=read('source-custody.json')
    def test_computed_and_native_stored_value_match(self):
        r=self.r;self.assertEqual(r['verdict'],'NATIVE_COMPUTED_RESULT_OBSERVED');self.assertIsNone(r['error']);self.assertEqual(len(r['computation']),1)
        item=r['computation'][0];self.assertEqual(item['input'],[17,25,8]);self.assertEqual(item['result'],str(sum(item['input'])));self.assertFalse(item['onMainThread'])
        self.assertEqual(r['savedResult']['result']['final_response'],'50');self.assertTrue(r['savedResult']['result']['completed']);self.assertEqual(r['admissions'][0]['status'],'terminal');self.assertEqual(r['admissions'][0]['outcome'],'completed')
    def test_observed_native_flow_is_not_manually_settled(self):
        o=self.o;self.assertEqual(o['result'],'PASS_OBSERVED_NATIVE_FINITE_FLOW');self.assertEqual(o['driverExitCode'],0);self.assertIsNone(o['observationError']);self.assertFalse(o['truncated'])
        self.assertTrue(o['checks']['flowObserved']);self.assertFalse(o['checks']['manualSettlementStackObserved']);self.assertTrue(o['checks']['computationOffMainThread'])
        self.assertTrue(any(e['function']=='run_sync' and e['thread']!=o['mainThread'] for e in o['events']))
        for e in o['events']:
            if e['function']=='settle_session_input':self.assertTrue(any(f['function']=='commit_and_publish' and f['path']=='gateway/session_settlement_recovery.py' for f in e['stack']))
        self.assertFalse(o['nativeMethodsReplacedByWitness'])
    def test_goal_extra_connection_blocks_full_ownership_claim(self):
        extra=[e for e in self.r['sqliteOpens'] if e['phase']=='ACTUAL_NATIVE_API_TURN'];self.assertEqual(len(extra),1);self.assertTrue(extra[0]['path'].endswith('state.db'))
        events=[e for e in self.o['events'] if e['path']=='hermes_state_registry.py' and e['function']=='_open_session_db'];self.assertTrue(events)
        self.assertTrue(all(any(f['path']=='hermes_cli/goals.py' and f['function']=='_acquire_session_db' for f in e['stack']) for e in events))
        self.assertFalse(self.c['fullOwnerCloseAccepted']);self.assertEqual(self.r['closeOutcome']['reason'],'consumer_import_outside_manifest')
        self.assertTrue(self.r['temporaryHomeRemoved']);self.assertTrue(self.c['testOnlyFixtureCleanupRemovedProfile'])
    def test_exact_native_and_driver_source_identity(self):
        for mapping in (self.r['nativeImports'],self.r['nativeExecutedSources']):
            for name,h in mapping.items():self.assertEqual(h,self.c['actualNativeFiles'][name]['sha256'],name)
        self.assertTrue(self.c['allActualNativeSourceBytesMatchGit']);self.assertEqual(self.c['actualNativeFileCount'],744)
        for name,h in self.c['runtimeSnapshotHashes'].items():self.assertEqual(hashlib.sha256((E/('candidate001-'+name.replace('/','__')+'.txt')).read_bytes()).hexdigest(),h)
        self.assertEqual(hashlib.sha256((ROOT/'scripts/qa/f134c6_flow_witness.py').read_bytes()).hexdigest(),self.o['qaSha256'])
        self.assertEqual(hashlib.sha256((ROOT/'scripts/qa/f134c6_observed_driver.py').read_bytes()).hexdigest(),self.o['driverSha256']);self.assertTrue(self.o['driverBytesUnchanged'])
    def test_driver_adapter_only_chains_instrumentation_and_proof_location(self):
        raw=(E/'producer003-driver.py.txt').read_bytes();self.assertEqual(hashlib.sha256(raw).hexdigest(),self.c['originalDriverSha256'])
        text=raw.decode('utf-8').replace("ROOT/'evidence/d3b-finite-turn-f134r1/probe-source-closure.json'","ROOT/'evidence/d3b-finite-turn-qa-f134c6/producer-source-closure.json'")
        text=text.replace('    def profile(frame,event,arg):\n','    def profile(frame,event,arg):\n        outer = previous if threading.get_ident()==mainthread else threadprevious\n        if outer is not None:outer(frame,event,arg)\n')
        self.assertEqual(text,(ROOT/'scripts/qa/f134c6_observed_driver.py').read_text(encoding='utf-8'))
        self.assertEqual(hashlib.sha256((E/'producer-source-closure.json').read_bytes()).hexdigest(),self.c['sourceProofSha256'])
    def test_explicit_fixture_and_unaccepted_scope(self):
        r=self.r;self.assertEqual(r['nativeMethodsReplaced'],['run_agent.AIAgent (explicit model factory/computation only)']);self.assertTrue(r['windowsOsBoundariesDoubled'])
        for key in ('manualSettlementPerformed','productionManifestWidened','httpListenerStarted','linuxIsolationTested'):self.assertFalse(r[key],key)
        self.assertEqual(r['realProviderCalls'],0);self.assertFalse(self.o['fullAgentOrProviderAcceptance']);self.assertFalse(self.c['nativeSourceEdited'])
if __name__=='__main__':unittest.main()
