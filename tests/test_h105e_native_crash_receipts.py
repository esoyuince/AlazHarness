"""Raw native H105E receipts and adversarial tampering; not new native runs."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts/qa'))
import h105e_receipt as validator
E=ROOT/'evidence/d3b-native-stores-h105e'

class NativeCrashEvidence(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original=json.loads((E/'native-002-stdout.txt').read_bytes())
        cls.manifest=json.loads((E/'native-002-intent.json').read_text())['sourceSha256']
    def outer(self):return deepcopy(self.original)
    def changed(self,change,*,event=None):
        outer=self.outer();r=validator.load(outer['stdout'])
        if event is None:change(r)
        else:
            child=validator.load(r['events'][event]['stdout']);change(child)
            r['events'][event]['stdout']=json.dumps(child)
        outer['stdout']=json.dumps(r)
        return outer
    def refuse(self,outer):
        with self.assertRaises(validator.ReceiptRejected):validator.verify(outer,self.manifest)
    def test_complete_raw_native_run(self):
        result=validator.verify(self.original,self.manifest)
        self.assertEqual(result['cases'],6);self.assertEqual(result['childProcesses'],12)
        self.assertIs(result['launchAuthorized'],False)
    def test_probe_matches_actual_native_execution(self):
        name='scripts/qa/h105e_store_crash_probe.py'
        self.assertEqual(hashlib.sha256((ROOT/name).read_bytes()).hexdigest(),self.manifest[name])
        self.assertEqual(json.loads((E/'native-002-result.json').read_text())['exitCode'],0)
    def test_native_and_dependency_hashes_match_separate_git_inventory(self):
        inventory=json.loads((E/'native-source-inventory.json').read_text())
        self.assertEqual(inventory['pin'],validator.PIN)
        for name,item in inventory['nativeSources'].items():
            self.assertEqual(self.manifest['vendor-native/'+name],item['sha256'])
        for name,want in inventory['dependency']['sourceSha256'].items():
            self.assertEqual(self.manifest['dependencies/'+name],want)
    def test_first_success_retained_separately(self):
        first=json.loads((E/'native-001-stdout.txt').read_bytes())
        self.assertEqual(first['exitCode'],0)
        old=E/'crash-probe-first.py.txt';name='scripts/qa/h105e_store_crash_probe.py'
        self.assertEqual(hashlib.sha256(old.read_bytes()).hexdigest(),first['sourceSha256'][name])
        self.assertNotEqual(first['sourceSha256'][name],self.manifest[name])
    def test_missing_scenario_refused(self):self.refuse(self.changed(lambda r:r['events'].pop()))
    def test_wrong_case_order_refused(self):
        self.refuse(self.changed(lambda r:r['events'].reverse()))
    def test_crash_not_normal_close(self):
        self.refuse(self.changed(lambda r:r['events'][0].update(exitCode=0)))
    def test_recovery_nonzero_refused(self):
        self.refuse(self.changed(lambda r:r['events'][1].update(exitCode=73)))
    def test_pid_reuse_refused(self):
        r=validator.load(self.original['stdout']);pid=validator.load(r['events'][0]['stdout'])['pid']
        self.refuse(self.changed(lambda c:c.update(pid=pid),event=1))
    def test_changed_epoch_refused(self):
        self.refuse(self.changed(lambda c:c['epochRows'][0].update(epoch=1),event=3))
    def test_wrong_epoch_instance_refused(self):
        self.refuse(self.changed(lambda c:c['epochRows'][0].update(instanceId='foreign'),event=3))
    def test_unknown_cannot_be_queued(self):
        self.refuse(self.changed(lambda c:c['stateRows'][0].update(status='queued'),event=3))
    def test_terminal_replay_cannot_imply_terminal_state(self):
        self.refuse(self.changed(lambda c:c['stateRows'][0].update(status='terminal'),event=7))
    def test_no_synthesized_state_for_replay_only(self):
        self.refuse(self.changed(lambda c:c['stateRows'].append({'status':'queued'}),event=1))
    def test_other_replay_store_not_rewritten(self):
        self.refuse(self.changed(lambda c:c['replayRows'][0]['status'].update(status='completed'),event=5))
    def test_admission_identity_not_substituted(self):
        self.refuse(self.changed(lambda c:c['stateRows'][0].update(admission_id='f'*32),event=3))
    def test_unsafe_retry_claim_refused(self):
        self.refuse(self.changed(lambda c:c['data'].update(retryAuthorized=True),event=7))
    def test_uncommitted_native_transaction_required(self):
        self.refuse(self.changed(lambda c:c.update(replayTransactionOpen=False),event=8))
    def test_timing_checkpoint_source_pinned(self):
        self.refuse(self.changed(lambda c:c['data'].update(checkpointSourceSha256='f'*64),event=8))
    def test_memory_case_may_not_advance_epoch(self):
        self.refuse(self.changed(lambda c:c['epochRows'].append({'epoch':1,'instanceId':'foreign'}),event=11))
    def test_memory_loss_cannot_be_called_durable(self):
        self.refuse(self.changed(lambda c:c['data']['journals'].update(replay='wal'),event=11))
    def test_native_profile_required(self):
        self.refuse(self.changed(lambda c:c['checks'].update(real_native_profile_owned=False),event=3))
    def test_integer_true_not_success(self):
        self.refuse(self.changed(lambda c:c['checks'].update(real_native_profile_owned=1),event=3))
    def test_missing_import_refused(self):
        self.refuse(self.changed(lambda c:c['sourceHashes'].pop('vendor-native/hermes_state.py'),event=3))
    def test_import_hash_drift_refused(self):
        self.refuse(self.changed(lambda c:c['sourceHashes'].update({'vendor-native/hermes_state.py':'f'*64}),event=3))
    def test_changed_lock_inode_refused(self):
        self.refuse(self.changed(lambda c:c.update(lockInode=c['lockInode']+1),event=3))
    def test_parent_or_child_broader_scope_refused(self):
        for key in ('rootUsed','mountsChanged','pairedTransactionAtomicityClaimed','fullConfinementTested','fullD3BAccepted'):
            with self.subTest(key=key):self.refuse(self.changed(lambda r:r.update({key:True})))
    def test_cleanup_required(self):
        outer=self.outer();outer['temporaryRootRemoved']=False;self.refuse(outer)
    def test_manifest_drift_refused(self):
        outer=self.outer();outer['sourceSha256']['vendor-native/hermes_state.py']='f'*64;self.refuse(outer)
    def test_duplicate_keys_refused(self):
        outer=self.outer();outer['stdout']='{"result":"PASS","result":"PASS"}';self.refuse(outer)
    def test_null_and_nonfinite_refused(self):
        for text in ('null','NaN','[]','not-json'):
            with self.subTest(text=text):
                outer=self.outer();outer['stdout']=text;self.refuse(outer)
    def test_native_inventory_gap_is_pinned_to_historical_baseline(self):
        comparison=json.loads((E/'projection-inventory-comparison.json').read_text())
        baseline=json.loads((E/'baseline.json').read_text())
        self.assertEqual(comparison['baseCommit'],baseline['base'])
        self.assertEqual(comparison['projectionSourceSha256'],baseline['sources'][comparison['projectionSourcePath']])
        proof=validator.load(self.original['stdout']);child=validator.load(proof['events'][0]['stdout'])
        inventory=set(child['profileInventory'])-{'.h105e-owned'}
        self.assertEqual(set(comparison['observedNativeInventory']),inventory)
        self.assertEqual(set(comparison['unacceptedNativeEntries']),inventory-set(comparison['allowedAtBaseline']))
        self.assertIs(comparison['comparisonCompatible'],False)
        self.assertIs(comparison['productPolicyChanged'],False)

if __name__=='__main__':unittest.main()
