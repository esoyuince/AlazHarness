from historical_prepared_c127a6 import executed_source_hash as pre_c127_hash
"""Exact current confined receipts; offline assertions, never a new root run."""
import hashlib,json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
E=ROOT/'evidence/d3b-confined-consumer-f126c1'
class ConfinedPreparedReceipt(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.o=json.loads((E/'native-006-result.json').read_text(encoding='utf-8'))
        cls.r=json.loads((E/'native-006-acceptance.json').read_text(encoding='utf-8'))
        cls.c=json.loads((E/'current-source-custody.json').read_text(encoding='utf-8'))
        cls.targets=[v for v in cls.r['events'] if v.get('state')=='RESULT']
    def test_terminal_current_pair_exact_scoped_counts(self):
        self.assertEqual(json.loads((E/'native-006-terminal.json').read_text()),{'exitCode':0})
        self.assertEqual(self.o['nativeExitCode'],0);self.assertEqual(self.r,json.loads(self.o['nativeStdout']))
        self.assertEqual(self.r['result'],'PASS_SCOPED_CONFINED_PREPARED_CONSUMER');self.assertIsNone(self.r['error']);self.assertFalse(self.r['forcedCleanup'])
        self.assertEqual((self.r['checkCount'],len(self.r['checks'])),(44,44));self.assertTrue(all(v is True for v in self.r['checks'].values()))
        self.assertEqual([t['mode'] for t in self.targets],['write','read'])
        for t in self.targets:self.assertEqual((t['checkCount'],len(t['checks'])),(41,41));self.assertTrue(all(v is True for v in t['checks'].values()))
    def test_current_native_package_and_qa_bytes(self):
        self.assertTrue(self.o['sourceBytesUnchanged']);self.assertTrue(self.o['installedBytesMatchPriorAcceptedTarget'])
        self.assertEqual(self.r['sourceSha256'],self.o['sources']);self.assertEqual(self.c['nativeEnvelopeCount'],513)
        self.assertEqual(self.c['nativeFeature'],'1e97dd617b81120255304e472ce322befcdb9ccd')
        for n,h in self.o['sources'].items():
            if n.startswith(('packages/','scripts/','config/')):self.assertEqual(pre_c127_hash(ROOT,n,h),h,n)
            elif n.startswith('native/'):self.assertEqual(self.c['nativeGitBlobs'][n.removeprefix('native/')]['sha256'],h,n)
        self.assertEqual(hashlib.sha256((E/'native-006-result.json').read_bytes()).hexdigest(),self.c['native006ResultSha256'])
        self.assertEqual(hashlib.sha256((E/'native-006-acceptance.json').read_bytes()).hexdigest(),self.c['native006AcceptanceSha256'])
    def test_actual_binary_imports_and_source_frames(self):
        self.assertEqual(self.targets[0]['nativeSources'],self.targets[1]['nativeSources'])
        expected=json.loads((ROOT/'evidence/d3b-linux-consumer-l125p1/linux-owner-001-result.json').read_text(encoding='utf-8'))['installedFileHashes']
        for t in self.targets:
            self.assertEqual((t['sourceCount'],len(t['nativeSources'])),(820,820));self.assertEqual(t['sourceChunks'],26)
            self.assertEqual(len(t['actualBinaryImports']),13)
            for n,h in t['nativeSources'].items():self.assertEqual(self.o['sources'][n],h)
            for n,h in t['actualBinaryImports'].items():self.assertEqual(expected[n.removeprefix('dependencies/')],h)
            self.assertEqual(t['sourceDigest'],hashlib.sha256(json.dumps(t['nativeSources'],sort_keys=True,separators=(',',':')).encode()).hexdigest())
    def test_real_kernel_identity_and_no_ambient_escape(self):
        for t in self.targets:
            r=t['receipt'];d=r['afterDrop'];self.assertEqual(d['uids'],[23001]*4);self.assertEqual(d['gids'],[23003]*4)
            self.assertEqual(d['groups'],[]);self.assertTrue(all(v==0 for v in d['caps'].values()));self.assertEqual(d['nnp'],1)
            self.assertEqual(r['profileLayout'],'hermes-native-prepared-three-stores-cold-v1');self.assertEqual(r['ambientHostDirectoriesBound'],0)
            for k in ('inherited_nnp_seccomp','private_namespace_and_original_userns','landlock_abi_enforced','host_endpoints_stay_denied','host_private_paths_hidden','canary_read_write_denied','ambient_fd_closed','seccomp_namespace_reentry_denied'):
                self.assertTrue(t['checks'][k],k)
    def test_restart_and_exact_release_order(self):
        a,b=self.targets;self.assertNotEqual(a['pid'],b['pid']);self.assertEqual([a['epoch'],b['epoch']],[1,2])
        self.assertEqual(a['stores'],b['stores']);self.assertEqual(a['responseExpectation'],b['responseExpectation'])
        for t in self.targets:
            for k in ('same_three_existing_connections','same_accepted_epoch','consumer_no_fourth_connection','consumer_no_row_change','consumer_no_raw_database_open','original_owner_blocks_attached_consumer','all_three_transactions_preserved','api_runner_consumer_ordered_detach','postdetach_header_change_blocks_close','three_handles_closed_before_profile_release','live_writer_retains_profile'):
                self.assertTrue(t['checks'][k],k)
        events=self.r['events'];first=next(i for i,e in enumerate(events) if e.get('phase')=='write-closed');second=next(i for i,e in enumerate(events) if e.get('phase')=='read-consumer-prepared');self.assertLess(first,second)
    def test_explicit_layout_and_private_scratch_no_broader_policy(self):
        self.assertTrue(self.r['checks']['old_three_store_layout_still_rejects_prepared_scaffold'])
        negative=next(e for e in self.r['events'] if e.get('negative')=='old_three_store_after_runner')
        self.assertEqual(negative['exitCode'],2);self.assertEqual(negative['diagnostic']['reason'],'native_layout_unexpected_entry')
        for t in self.targets:
            for k in ('finite_prepared_layout_after_close','pairing_scaffold_empty_private','explicit_tmp_uses_projected_scratch','private_scratch_fresh'):self.assertTrue(t['checks'][k])
        for k in ('default_self_mount_stays_denied','minimal_default_refuses_native_scaffold','old_two_store_layout_refuses_response'):self.assertTrue(self.r['checks'][k])
    def test_no_service_provider_or_full_agent_claim(self):
        self.assertTrue(self.r['preparedConsumerUnderFullIsolation']);self.assertFalse(self.r['readinessHttpUnderFullIsolation']);self.assertFalse(self.r['nativeAgentHttpAdapterStarted'])
        self.assertEqual(self.r['paidModelCalls'],0);self.assertTrue(self.r['checks']['zero_physical_provider_attempts']);self.assertTrue(self.r['checks']['exactly_two_authenticated_pings'])
        for t in self.targets:
            for k in ('nativeMethodsReplaced','coldHelpersDoubled','kernelBoundaryDoubled','activeTaskObserversQualified','serviceOrAdmissionEnabled','fullD3BAccepted'):self.assertFalse(t[k],k)
            self.assertEqual(t['providerSends'],0);self.assertEqual(t['consumerStatus']['state'],'DETACHED')
    def test_recorded_teardown_and_all_prior_failures_remain_historical(self):
        for k in ('broker_clean_exit','parent_mount_table_unchanged','broker_private_files_unchanged','no_remaining_loop','no_remaining_fence','no_remaining_scopes','no_forced_cleanup','source_bytes_unchanged'):self.assertTrue(self.r['checks'][k],k)
        for i in range(1,6):
            old=json.loads((E/('native-%03d-acceptance.json'%i)).read_text(encoding='utf-8'))
            self.assertEqual(old['result'],'FAIL');self.assertIsNotNone(old['error'])
        third=json.loads((E/'native-003-acceptance.json').read_text(encoding='utf-8'))
        f=next(e['unexpectedConfinedFrame'] for e in third['events'] if 'unexpectedConfinedFrame' in e)
        self.assertEqual(f['reason'],'native_layout_unexpected_entry')
        last=json.loads((E/'native-005-acceptance.json').read_text(encoding='utf-8'))
        f=next(e['unexpectedConfinedFrame'] for e in last['events'] if 'unexpectedConfinedFrame' in e)
        self.assertIn('cache/scratch/.last_prune',f['reason'])
        self.assertFalse((E/'independent-root-cleanup.json').exists())
if __name__=='__main__':unittest.main()
