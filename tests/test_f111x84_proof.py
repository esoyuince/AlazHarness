"""Actual external kernel proof plus offline tamper tests, NOT native reruns."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts/qa'))
import f111x84_receipt as v
E=ROOT/'evidence/d3b-http-confined-f111x84'

class ConfinedHttpProof(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw=(E/'external-native-001.txt').read_bytes()
        cls.original=v.decode(cls.raw.decode('utf-8'))
        cls.custody=json.loads((E/'source-verification.json').read_text(encoding='utf-8'))
        cls.expected=cls.custody['sources']
    def changed(self,fn,mode=None):
        outer=deepcopy(self.original);r=v.decode(outer['nativeStdout'])
        if mode is None:fn(r)
        else:fn(next(e for e in r['events'] if e.get('state')=='RESULT' and e['mode']==mode))
        outer['nativeStdout']=json.dumps(r);return outer
    def denied(self,outer,code):
        with self.assertRaisesRegex(v.ProofRejected,'^'+code+'$'):v.verify(outer,self.expected)
    @staticmethod
    def phase(report,name):return next(e for e in report['events'] if e.get('phase')==name)
    def test_actual_native_receipt_passes_without_new_execution(self):
        r=v.verify(self.original,self.expected)
        self.assertEqual((r['lifetimes'],r['httpObservations'],r['parentChecks']),(2,22,44))
        self.assertEqual(r['targetCheckCounts'],[49,54]);self.assertEqual(r['sourceCount'],467)
        self.assertIs(r['newNativeExecution'],False);self.assertIs(r['launchAuthorized'],False)
    def test_raw_receipt_exact_copy_and_separate_source_expectations(self):
        self.assertEqual(hashlib.sha256(self.raw).hexdigest(),self.custody['nativeReceiptSha256'])
        self.assertEqual(json.loads((E/'external-native-result.json').read_text())['exitCode'],0)
        self.assertEqual(self.custody['nativeSourceCount'],276);self.assertEqual(self.custody['dependencySourceCount'],139)
        self.assertEqual(self.custody['nativePin'],v.PIN)
        self.assertEqual(self.expected,{n:d['sha256'] for n,d in self.custody['custody'].items()})
        self.assertIs(self.custody['parallelWorktreeModified'],False)
        base=json.loads((E/'baseline.json').read_text())['sources']
        for name,item in self.custody['custody'].items():
            if item['origin']=='canonical_baseline':self.assertEqual(base[name],item['sha256'])
    def test_cleanup_independently_captured(self):
        r=json.loads((E/'external-cleanup.json').read_text())
        self.assertEqual(r['result'],'CLEAN');self.assertEqual(r['matchingProcesses'],[])
        self.assertTrue(all(x is True for x in r['checks'].values()))
        self.assertIs(r['imageRetained'],True);self.assertEqual(r['imageBytes'],64*1024*1024)
        self.assertIs(r['labTerminated'],False);self.assertIs(r['defaultUbuntuCommandIssued'],False)
    def test_transport_nonzero_cannot_be_pass(self):
        o=deepcopy(self.original);o['nativeExitCode']=1;self.denied(o,'native_exit')
    def test_boolean_transport_exit_is_not_zero(self):
        o=deepcopy(self.original);o['nativeExitCode']=False;self.denied(o,'native_exit')
    def test_transport_source_mutation_refused(self):
        o=deepcopy(self.original);o['sourcesUnchanged']=False;self.denied(o,'source_drift')
    def test_expected_source_not_taken_from_receipt(self):
        o=deepcopy(self.original);o['sources']['packages/claw-hermes/gateway_http_readiness.py']='f'*64
        self.denied(o,'transport_sources')
    def test_wrong_native_pin_refused(self):
        o=deepcopy(self.original);o['nativePin']='f'*40;self.denied(o,'native_pin')
    def test_failure_not_overridden_by_true_checks(self):
        self.denied(self.changed(lambda r:r.update(result='FAIL')),'native_result')
    def test_integer_success_flag_not_true(self):
        self.denied(self.changed(lambda r:r['checks'].update(exactly_two_authenticated_pings=1)),'check_not_true')
    def test_required_control_missing_even_with_fixed_count(self):
        def edit(r):r['checks'].pop('zero_physical_provider_attempts');r['checkCount']-=1
        self.denied(self.changed(edit),'required_check_missing')
    def test_invented_extra_check_count_refused(self):
        self.denied(self.changed(lambda r:r.update(checkCount=r['checkCount']+1)),'check_count')
    def test_overclaimed_full_gateway_refused(self):
        self.denied(self.changed(lambda r:r.update(nativeAgentHttpAdapterStarted=True)),'scope_expansion')
    def test_provider_call_not_covered_by_zero_flag(self):
        self.denied(self.changed(lambda r:r.update(paidModelCalls=1)),'provider_call')
    def test_different_image_size_refused(self):
        self.denied(self.changed(lambda r:r.update(imageBytes=1024)),'image_scope')
    def test_default_metadata_permission_not_weakened(self):
        def edit(r):next(e for e in r['events'] if e.get('negative')=='default_metadata')['diagnostic']['mountinfoDenied']=False
        self.denied(self.changed(edit),'default_policy_weakened')
    def test_wrong_inode_negative_cannot_be_called_success(self):
        def edit(r):next(e for e in r['events'] if e.get('negative')=='wrong_inode')['exitCode']=0
        self.denied(self.changed(edit),'negative_controls')
    def test_unclean_broker_is_not_hidden_by_parent_check(self):
        def edit(r):next(e for e in r['events'] if 'brokerExit' in e)['brokerExit']=1
        self.denied(self.changed(edit),'broker_cleanup')
    def test_retained_scope_cleanup_refused(self):
        self.denied(self.changed(lambda r:r['events'].append({'cleanupRetained':'error'})),'cleanup_retained')
    def test_two_results_not_one_lifetime_repeated(self):
        def edit(r):
            t=[e for e in r['events'] if e.get('state')=='RESULT'];t[1]['pid']=t[0]['pid']
        self.denied(self.changed(edit),'distinct_target_pid')
    def test_missing_second_target_refused(self):
        def edit(r):r['events']=[e for e in r['events'] if not (e.get('state')=='RESULT' and e['mode']=='read')]
        self.denied(self.changed(edit),'two_lifetimes')
    def test_host_reachable_refused_despite_true_flags(self):
        self.denied(self.changed(lambda r:self.phase(r,'write-host-http-probe').update(errno=0)),'host_http_reachable_or_unknown')
    def test_host_timeout_is_not_connection_refusal(self):
        self.denied(self.changed(lambda r:self.phase(r,'write-host-http-probe').update(errno=110)),'host_http_reachable_or_unknown')
    def test_wrong_host_port_does_not_prove_isolation(self):
        self.denied(self.changed(lambda r:self.phase(r,'write-host-http-probe').update(port=1)),'port_binding')
    def test_ready_must_be_positive_before_host_probe(self):
        self.denied(self.changed(lambda r:self.phase(r,'write-http-listening').update(localReadyStatus=503)),'positive_http_binding')
    def test_detach_must_precede_second_lifetime(self):
        def edit(r):
            a=next(i for i,e in enumerate(r['events']) if e.get('phase')=='write-closed')
            b=next(i for i,e in enumerate(r['events']) if e.get('phase')=='read-http-listening')
            r['events'][a],r['events'][b]=r['events'][b],r['events'][a]
        self.denied(self.changed(edit),'lifecycle_order')
    def test_duplicate_phase_refused(self):
        self.denied(self.changed(lambda r:r['events'].append(deepcopy(self.phase(r,'write-host-http-probe')))),'unique_phase_required')
    def test_live_target_must_not_be_root(self):
        self.denied(self.changed(lambda t:t['receipt']['afterDrop'].update(uids=[0]*4),'write'),'uid_gid_groups')
    def test_remaining_capability_refused(self):
        self.denied(self.changed(lambda t:t['receipt']['afterDrop']['caps'].update(CapEff=1),'write'),'capabilities')
    def test_extra_proc_grants_refused(self):
        self.denied(self.changed(lambda t:t['receipt']['filesystem'].update(metadataReadFileCount=7),'write'),'landlock_scope')
    def test_landlock_is_not_claimed_as_network_proof(self):
        self.denied(self.changed(lambda t:t['receipt']['filesystem'].update(networkConfinementVerified=True),'write'),'landlock_overclaim')
    def test_ambient_host_directory_not_exported(self):
        self.denied(self.changed(lambda t:t['receipt'].update(ambientHostDirectoriesBound=1),'write'),'mount_scope')
    def test_public_bind_rejected(self):
        self.denied(self.changed(lambda t:t['httpStartup'].update(host='0.0.0.0'),'write'),'http_listener')
    def test_monotonic_readiness_cannot_return_200_again(self):
        self.denied(self.changed(lambda t:t['httpResults'][9].update(status=200),'write'),'http_sequence')
    def test_http_body_cannot_grant_dispatch(self):
        self.denied(self.changed(lambda t:t['httpResults'][0]['body'].update(runtimeAdmissionAuthorized=True),'write'),'readiness_body')
    def test_health_cannot_claim_storage(self):
        self.denied(self.changed(lambda t:t['httpResults'][-1]['body'].update(storageReady=True),'write'),'liveness_overclaim')
    def test_http_failure_observation_must_be_kept(self):
        self.denied(self.changed(lambda t:t['httpResults'].pop(2),'write'),'http_observation_count')
    def test_http_cleanup_unknown_not_accepted(self):
        self.denied(self.changed(lambda t:t['httpClosed'].update(httpCleanupPending=True),'write'),'http_close')
    def test_profile_contention_must_really_refuse(self):
        self.denied(self.changed(lambda r:self.phase(r,'write-native-contender').update(exitCode=0)),'profile_exclusion')
    def test_image_lease_not_released_before_cleanup(self):
        self.denied(self.changed(lambda r:self.phase(r,'write-closed').update(leaseReleasedLast=False)),'image_released_too_soon')
    def test_ambient_socket_positive_connection_not_ignored(self):
        self.denied(self.changed(lambda t:t['hostEndpointErrnos'].update(ambient=0),'write'),'ambient_socket_access')
    def test_import_digest_substitution_refused(self):
        self.denied(self.changed(lambda t:t['nativeSources'].update({'vendor-native/hermes_state.py':'f'*64}),'write'),'actual_import_source_drift')
    def test_import_frame_digest_refused(self):
        self.denied(self.changed(lambda t:t.update(sourceDigest='f'*64),'write'),'source_frame_binding')
    def test_epoch_not_advanced_twice(self):
        self.denied(self.changed(lambda t:t.update(epoch=3),'read'),'epoch_or_replay')
    def test_same_schema_but_other_store_uuid_refused(self):
        self.denied(self.changed(lambda t:t['nextExpectation'].update(store_instance_id='12345678-1234-1234-1234-123456789012'),'read'),'prepared_identity_changed')
    def test_persisted_row_cannot_change(self):
        def edit(t):t['stores']['state.db']['rows'][0][0]='f'*32
        self.denied(self.changed(edit,'read'),'persistence_or_duplicate')
    def test_file_inode_binds_to_prepared_identity(self):
        self.denied(self.changed(lambda t:t['stores']['state.db'].update(inode=9999),'read'),'store_identity')
    def test_duplicate_reuse_not_false_success(self):
        self.denied(self.changed(lambda t:t['stores']['runs_idempotency.db'].update(duplicateRefused=False),'read'),'persistence_or_duplicate')
    def test_pending_start_cannot_advance_epoch(self):
        self.denied(self.changed(lambda t:t['blockedStartup'].update(epochMayHaveAdvanced=True),'read'),'pending_not_fenced')
    def test_duplicate_json_and_nonfinite_refused(self):
        for text in ('{"a":1,"a":2}','NaN','{"a":Infinity}'):
            with self.subTest(text=text),self.assertRaises(v.ProofRejected):v.decode(text)
    def test_json_size_and_structure_bound(self):
        with self.assertRaisesRegex(v.ProofRejected,'json_size'):v.decode(' '*(8*1024*1024+1))
        for value in (None,[],{},42):
            with self.subTest(value=value),self.assertRaises(v.ProofRejected):v.verify(value,self.expected)

if __name__=='__main__':unittest.main()
