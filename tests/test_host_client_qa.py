"""Real client, fixture fetch; one Node case per standard unittest, no provider/Gateway."""
from pathlib import Path
import subprocess
import unittest
ROOT=Path(__file__).resolve().parents[1]
CASES=['missing_plugin_no_fallback','foreign_permit_no_network','mutation_after_prepare_snapshotted',
 'foreign_client_permit_no_dispatch','one_permit_not_twice','two_permits_one_local_dispatch',
 'transport_loss_never_refunds','abort_before_dispatch_does_not_consume','consumed_document_cannot_dispatch',
 'invalid_key_binding_refused','contradictory_completed_admission_refused','invalid_output_type_refused']
class HostClientIndependentTests(unittest.TestCase):pass

def make(name):
    def case(self):
        p=subprocess.run(['node',str(ROOT/'tests/node/host_gate_qa.mjs'),name],cwd=ROOT,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=15)
        self.assertEqual(p.returncode,0,p.stdout+p.stderr)
    return case
for name in CASES:setattr(HostClientIndependentTests,'test_'+name,make(name))
if __name__=='__main__':unittest.main()
