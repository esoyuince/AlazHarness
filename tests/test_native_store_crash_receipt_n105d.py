"""Independent negative evidence checks; not more native process executions."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts/qa'))
import n105d_receipt_checks as check
E=ROOT/'evidence/d3b-native-stores-n105d'
class NativeCrashReceipt(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report=json.loads((E/'native-windows-001.json').read_text())
        cls.sources={n:v['sha256'] for n,v in json.loads((E/'native-source-custody.json').read_text())['sources'].items()}
        cls.probe=hashlib.sha256((ROOT/'scripts/qa/n105d_recovery_probe.py').read_bytes()).hexdigest()
    def valid(self,r):return check.review(r,self.sources,self.probe)
    def mutate(self,fn,reason,*,case=None,stage='recover'):
        r=deepcopy(self.report)
        if case is None:fn(r)
        else:
            row=next(x for x in r['cases'] if x['case']==case)[stage]
            fn(row['proof']);row['stdout']=json.dumps(row['proof'])
        with self.assertRaisesRegex(check.ReceiptRejected,reason):self.valid(r)
    def test_exact_windows_terminal_receipt(self):
        self.assertEqual(json.loads((E/'native-windows-001-result.json').read_text())['exitCode'],0)
        r=self.valid(self.report);self.assertEqual(r['scenarioCount'],8);self.assertEqual(r['processLifetimes'],17)
    def test_native_git_provenance_not_fake_schema(self):
        c=json.loads((E/'native-source-custody.json').read_text())
        self.assertEqual(c['pin'],check.PIN);self.assertEqual(c['nativeSourceCount'],len(c['sources']))
        self.assertTrue(check.REQUIRED_SOURCES <= c['sources'].keys());self.assertIs(c['noNativePatches'],True)
    def test_source_pin_drift_refused(self):self.mutate(lambda r:r.update(sourcePin='0'*40),'source_pin')
    def test_missing_scenario_refused(self):self.mutate(lambda r:r['cases'].pop(),'case_count')
    def test_reordered_case_refused(self):self.mutate(lambda r:r['cases'].reverse(),'case_order')
    def test_false_cleanup_refused(self):self.mutate(lambda r:r.update(temporaryProfileRemoved=False),'cleanup')
    def test_full_gateway_claim_refused(self):self.mutate(lambda r:r.update(actualGatewayStarted=True),'scope')
    def test_script_drift_refused(self):self.mutate(lambda r:r.update(probeSha256='0'*64),'probe_identity')
    def test_unexecuted_commit_boundary_refused(self):
        self.mutate(lambda r:r.update(timingInjection=False),'commit_boundary',case='before_reservation_commit',stage='crash')
    def test_fake_recovery_to_queued_refused(self):
        self.mutate(lambda r:r.update(nativeAdmissionStatus='queued'),'native_state_transition',case='started')
    def test_fake_atomic_pair_refused(self):
        self.mutate(lambda r:r.update(idempotencyStatus='completed'),'native_state_transition',case='terminal_gap')
    def test_uncommitted_reservation_claim_refused(self):
        self.mutate(lambda r:r.update(idempotencyStatus='running'),'native_state_transition',case='before_reservation_commit')
    def test_missing_unknown_block_refused(self):
        self.mutate(lambda r:r['checks'].pop('unknown_work_not_reclaimed'),'check_set',case='started')
    def test_failed_guard_cannot_be_relabelled_pass(self):
        self.mutate(lambda r:r['checks'].update(old_epoch_refused=False),'failed_check',case='queued')
    def test_native_source_drift_refused(self):
        self.mutate(lambda r:r['nativeSources'].update({'hermes_state.py':'0'*64}),'native_source_mismatch',case='started')
    def test_raw_stdout_must_match_parsed_record(self):
        self.mutate(lambda r:r['cases'][0]['recover']['proof'].update(epoch=33),'raw_stdout_mismatch')
    def test_terminal_recovery_count_not_inflated(self):
        self.mutate(lambda r:r.update(recoveredAdmissions=1),'recovery_count',case='terminal_synced')
    def test_memory_fallback_is_not_qualified_storage(self):
        r=deepcopy(self.report);r['fallback']['proof']['durable']=True
        r['fallback']['stdout']=json.dumps(r['fallback']['proof'])
        with self.assertRaisesRegex(check.ReceiptRejected,'fallback'):self.valid(r)
if __name__=='__main__':unittest.main()
