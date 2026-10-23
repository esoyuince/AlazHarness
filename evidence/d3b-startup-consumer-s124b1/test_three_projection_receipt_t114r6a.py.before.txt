"""Actual T114R6A full-isolation receipts, not a new native run or cleanup query."""
import hashlib,json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
E=ROOT/'evidence/d3b-three-projection-t114r6a'
class ThreeStoreProjectionReceipt(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.o=json.loads((E/'native-003-stdout.txt').read_bytes());cls.r=json.loads(cls.o['nativeStdout'])
        cls.targets=[e for e in cls.r['events'] if e.get('state')=='RESULT']
    def test_current_source_and_native_feature_hashes_match_execution(self):
        self.assertEqual((self.o['unitsExitCode'],self.o['nativeExitCode']),(0,0));self.assertTrue(self.o['sourcesUnchanged'])
        self.assertEqual(self.r['result'],'PASS_SCOPED_NATIVE_STORE_LAYOUT');self.assertIsNone(self.r['error'])
        self.assertEqual(self.o['sources'],self.r['sourceSha256'])
        self.assertEqual(self.o['sources'],json.loads((E/'native-003-intent.json').read_text(encoding='utf-8'))['sourceSha256'])
        inventory=json.loads((E/'source-inventory.json').read_text(encoding='utf-8'))
        for name,h in self.o['sources'].items():
            if name.startswith(('packages/','scripts/','tests/')):self.assertEqual(hashlib.sha256((ROOT/name).read_bytes()).hexdigest(),h,name)
            elif name.startswith('vendor-native/'):self.assertEqual(inventory['nativeSources'][name.removeprefix('vendor-native/')]['sha256'],h)
            else:self.assertEqual(inventory['dependencySources'][name.removeprefix('dependencies/')],h)
        self.assertEqual(self.o['nativePin'],'cc16c10b16a0ca8d80b23fd9be3f0e59ee605075')
        for t in self.targets:
            for n,h in t['nativeSources'].items():self.assertEqual(self.o['sources'][n],h)
            for n in ('gateway/platforms/api_server_response_store.py','gateway/platforms/api_server_response_state.py'):
                self.assertIn('vendor-native/'+n,t['nativeSources'])
    def test_private_ready_host_refusal_bound_to_same_live_pid_and_port(self):
        self.assertEqual([t['mode'] for t in self.targets],['write','read'])
        for t in self.targets:
            phase=t['mode'];events=self.r['events']
            a=next((i,e) for i,e in enumerate(events) if e.get('phase')==phase+'-http-listening')
            b=next((i,e) for i,e in enumerate(events) if e.get('phase')==phase+'-host-http-probe')
            self.assertLess(a[0],b[0]);self.assertLess(b[0],events.index(t))
            self.assertEqual(a[1]['pid'],t['pid']);self.assertEqual(a[1]['localReadyStatus'],200)
            self.assertEqual(a[1]['port'],b[1]['port']);self.assertEqual(b[1]['port'],t['httpStartup']['port'])
            self.assertEqual(b[1]['errno'],111)
            s=t['httpStartup'];self.assertEqual(s['configuredStoreCount'],3);self.assertTrue(s['responseIncluded'])
            self.assertEqual(s['scope'],'native_three_store_quiescent_readiness_only')
            self.assertFalse(s['healthyBusyWorkPolicy']);self.assertFalse(s['agentRoutesEnabled'])
    def test_third_only_faults_and_monotonic_503_have_raw_http_outcomes(self):
        for t in self.targets:
            self.assertEqual([r['status'] for r in t['httpResults']],[200,401,401,404,404,405,200,200,503,503,200])
            for row in (t['httpResults'][0],t['httpResults'][8],t['httpResults'][9]):
                self.assertEqual(row['body']['storageReady'],row['status']==200)
                self.assertEqual(row['body']['scope'],'native_three_store_quiescent_readiness_only')
                self.assertFalse(row['body']['runtimeAdmissionAuthorized']);self.assertFalse(row['body']['agentRoutesEnabled'])
            self.assertEqual(t['httpResults'][-1]['body']['scope'],'process_liveness_only')
            for k in ('response_fault_revokes_http','response_restore_does_not_reenable_http','canonical_epoch_unchanged_by_response_fault'):
                self.assertIs(t['checks'][k],True)
    def test_all_three_persist_across_complete_detach_and_new_epoch(self):
        a,b=self.targets;self.assertNotEqual(a['pid'],b['pid']);self.assertEqual([a['epoch'],b['epoch']],[1,2])
        self.assertEqual(set(a['stores']),{'state.db','runs_idempotency.db','response_store.db'})
        for name in a['stores']:
            self.assertEqual(a['stores'][name]['rows'],b['stores'][name]['rows']);self.assertEqual(a['stores'][name]['inode'],b['stores'][name]['inode'])
        self.assertEqual(a['responseExpectation'],b['responseExpectation'])
        events=self.r['events'];end=next(i for i,e in enumerate(events) if e.get('phase')=='write-closed');start=next(i for i,e in enumerate(events) if e.get('phase')=='read-http-listening')
        self.assertLess(end,start);self.assertTrue(events[end]['loopAttachmentGone']);self.assertTrue(events[end]['leaseReleasedLast'])
        self.assertTrue(self.r['checks']['rows_and_inodes_survive_detach'])
    def test_actual_final_identity_is_confined_not_root(self):
        for t in self.targets:
            r=t['receipt'];d=r['afterDrop']
            self.assertEqual(r['profileLayout'],'hermes-native-three-stores-cold-v1');self.assertEqual(r['stateDirectoryCount'],1)
            self.assertEqual(r['ambientHostDirectoriesBound'],0);self.assertEqual(d['uids'],[23001]*4);self.assertEqual(d['gids'],[23003]*4)
            self.assertEqual(d['groups'],[]);self.assertTrue(all(x==0 for x in d['caps'].values()))
            self.assertEqual(d['nnp'],1);self.assertTrue(t['checks']['nnp_seccomp_after_exec']);self.assertTrue(t['checks']['private_namespace_preserved'])
            self.assertTrue(t['checks']['other_host_endpoints_denied']);self.assertTrue(t['checks']['broker_ping'])
            self.assertTrue(r['filesystem']['selfMountMetadata'])
    def test_http_drains_before_response_transaction_and_all_three_close(self):
        for t in self.targets:
            for k in ('http_closed_even_when_storage_transaction_blocks','http_close_retains_native_transaction',
                      'private_http_port_closed_before_storage','all_three_handles_closed_before_lease',
                      'response_borrows_same_connection','response_constructor_zero_writes','response_content_after_fault_and_close'):
                self.assertTrue(t['checks'][k],k)
            self.assertEqual(t['httpClosed']['state'],'CLOSED');self.assertFalse(t['httpClosed']['httpCleanupPending'])
            self.assertTrue(t['httpClosed']['callerLeaseMayBeReleased'])
    def test_cold_negative_and_old_layout_do_not_silently_opt_in(self):
        self.assertTrue(self.r['checks']['old_two_store_layout_refuses_response'])
        neg=next(e for e in self.r['events'] if e.get('negative')=='two_store_layout')
        self.assertEqual(neg['exitCode'],2);self.assertEqual(neg['diagnostic']['reason'],'native_layout_unexpected_entry')
        for t in self.targets:
            self.assertTrue(t['checks']['bad_pair_zero_parent_opens']);self.assertTrue(t['checks']['bad_response_no_bind_epoch_or_parent_open'])
    def test_recorded_teardown_and_blocked_independent_query_are_not_conflated(self):
        for k in ('broker_clean_exit','no_remaining_loop','no_remaining_fence','no_remaining_scopes','no_forced_cleanup','parent_mount_table_unchanged','broker_private_files_unchanged'):
            self.assertTrue(self.r['checks'][k],k)
        self.assertTrue(self.r['checks']['exactly_two_authenticated_pings']);self.assertTrue(self.r['checks']['zero_physical_provider_attempts'])
        blocked=json.loads((E/'independent-cleanup-blocked.json').read_text(encoding='utf-8'))
        self.assertEqual(blocked['status'],'BLOCKED_TOOL_SAFETY_CHECK');self.assertFalse(blocked['reissuedOrBypassed']);self.assertFalse(blocked['independentCleanupVerified'])
        self.assertFalse((E/'cleanup-final-stdout.txt').exists())
    def test_original_transport_failures_remain_failures_not_product_success(self):
        for run in ('001','002'):
            old=json.loads((E/('native-'+run+'-stdout.txt')).read_bytes());r=json.loads(old['nativeStdout'])
            self.assertNotEqual(old['nativeExitCode'],0);self.assertEqual(r['result'],'FAIL');self.assertEqual(r['error']['reason'],'broker_not_ready')
            self.assertFalse(any(e.get('state')=='RESULT' for e in r['events']))
            self.assertEqual(old['sources']['packages/claw-hermes/gateway_http_readiness.py'],self.o['sources']['packages/claw-hermes/gateway_http_readiness.py'])
            self.assertEqual(old['sources']['packages/claw-hermes/gateway_state_projection.py'],self.o['sources']['packages/claw-hermes/gateway_state_projection.py'])
    def test_scope_and_nested_counts(self):
        self.assertEqual((self.r['checkCount'],len(self.r['checks'])),(45,45));self.assertTrue(all(v is True for v in self.r['checks'].values()))
        self.assertEqual([t['checkCount'] for t in self.targets],[58,63])
        for t in self.targets:self.assertTrue(all(v is True for v in t['checks'].values()));self.assertFalse(t['fullD3BAccepted'])
        self.assertTrue(self.r['threeStoreReadiness']);self.assertFalse(self.r['nativeAgentHttpAdapterStarted']);self.assertFalse(self.r['fullD3BAccepted']);self.assertEqual(self.r['paidModelCalls'],0)

if __name__=='__main__':unittest.main()
