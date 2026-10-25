"""Offline mapping source and independent unit receipts; not a kernel test."""
import hashlib,json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
E=ROOT/'evidence/d3b-retained-projection-p142c6'
def read(name):return json.loads((E/name).read_text(encoding='utf-8'))
class RetainedProjectionEvidence(unittest.TestCase):
    def test_independent_exact_candidate_twenty_one_contracts(self):
        r=read('independent-c142c6/producer001-independent21-result.json')
        self.assertEqual((r['result'],r['methods'],r['exitCode']),('PASS_UNIT_MAPPING_AND_ORIGINAL_OWNER_HANDOFF',21,0))
        log=(E/'independent-c142c6/producer001-independent21-tests.txt').read_text(encoding='utf-8')
        self.assertEqual(sum(l.startswith('test_') and l.endswith(' ... ok') for l in log.splitlines()),21)
        self.assertIn('Ran 21 tests',log);self.assertTrue(log.rstrip().endswith('OK'))
    def test_source_generation_of_independent_run_is_current(self):
        r=read('independent-c142c6/producer001-independent21-result.json');c=read('source-custody.json')
        self.assertEqual(set(r['sourceHashes']),{'packages/claw-hermes/gateway_state_projection.py','packages/claw-hermes/gateway_retained_projection.py'})
        for name,h in r['sourceHashes'].items():self.assertEqual(c['currentSourceHashes'][name],h);self.assertEqual(hashlib.sha256((ROOT/name).read_bytes()).hexdigest(),h)
    def test_original_independent_driver_and_records_byte_exact(self):
        provenance=read('independent-provenance.json');self.assertTrue(provenance['sameRuntimeHashesAsCurrent']);self.assertTrue(provenance['peerNotEdited']);self.assertTrue(provenance['testsNotReexecutedByCopy'])
        for name,record in provenance['files'].items():self.assertEqual(hashlib.sha256((E/'independent-c142c6'/name).read_bytes()).hexdigest(),record['sha256'])
        r=read('independent-c142c6/producer001-independent21-result.json');self.assertEqual(hashlib.sha256((E/'independent-c142c6/c142c6_projection_checks.py.txt').read_bytes()).hexdigest(),r['qaSha256'])
        old=read('independent-c142c6/producer001-independent-result.json');self.assertEqual(old['methods'],15);self.assertEqual(hashlib.sha256((E/'independent-c142c6/independent15-checks.py.txt').read_bytes()).hexdigest(),old['qaSha256'])
    def test_current_source_and_named_history_binding_remain_distinct(self):
        c=read('source-custody.json');b=read('baseline.json');n='packages/claw-hermes/gateway_state_projection.py'
        for name,h in c['currentSourceHashes'].items():self.assertEqual(hashlib.sha256((ROOT/name).read_bytes()).hexdigest(),h)
        self.assertNotEqual(c['currentSourceHashes'][n],b['sources'][n]);self.assertEqual(hashlib.sha256((E/'gateway_state_projection.before.py.txt').read_bytes()).hexdigest(),b['sources'][n])
        self.assertTrue(c['oldNativeEvidenceRetainsOriginalSource'])
    def test_previous_failure_remains_failure_not_kernel_regression_proof(self):
        before=read('compatibility-before.json');r=next(r for r in before['results'] if r['file']=='test_confined_consumer_receipt_f126c1.py')
        self.assertEqual(r['exitCode'],1);self.assertIn('unexpected historical generation',r['tail'])
        log=(E/'test_confined_consumer_receipt_f126c1.py.after.txt').read_text(encoding='utf-8');self.assertIn('Ran 8 tests',log);self.assertTrue(log.rstrip().endswith('OK'))
        d=read('historical-proof-diagnosis.json');self.assertTrue(d['originalExpectedDigestUnchanged']);self.assertTrue(d['historicalKernelNotRelabelledCurrent']);self.assertFalse(d['runtimeFilesChangedByThisRepair'])
    def test_explicit_unaccepted_runtime_scope(self):
        r=read('independent-c142c6/producer001-independent21-result.json');self.assertTrue(r['kernelMountDropFilterAndStartupDependenciesDoubled']);self.assertFalse(r['actualKernelOrNativeLifecycleAccepted'])
        c=read('source-custody.json');self.assertFalse(c['actualKernelRun']);self.assertFalse(c['nativeRuntimeRun']);self.assertFalse(c['nativeSourceOrManifestChanged'])
if __name__=='__main__':unittest.main()
