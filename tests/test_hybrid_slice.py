"""Each test exercises a real Node/Python pipe, with an explicitly SCRIPTED peer."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
ROOT = Path(__file__).resolve().parents[1]
CASES = ('tool_round','budget','unicode_echo','idempotency_and_busy','cancel_before_start',
         'cooperative_cancel','uncooperative_cancel','deadline','settlement_deadline','crash_is_unknown',
         'nonzero_exit_is_not_success','malformed','oversized','frame_flood','wrong_session',
         'missing_terminal_status','partial_is_not_success','duplicate_terminal','conflicting_terminal',
         'queued_is_not_completed','approval_denied','unsupported_request_denied','terminal_before_ack',
         'isolated_environment','snapshots_and_capabilities','input_validation','spawn_failure',
         'openclaw_cancellation_contract','openclaw_deadline_contract',
         'canonical_wire_rejected','untrusted_event_name_not_logged','bounded_records')
class HybridSliceTests(unittest.TestCase):
    def test_node_sources_parse(self):
        node=shutil.which('node')
        self.assertIsNotNone(node)
        sources=[*ROOT.glob('packages/hybrid-runtime/*.mjs'),
                 *ROOT.glob('packages/upstream/openclaw/*.ts'),ROOT/'tests/hybrid/cases.mjs',
                 ROOT/'scripts/check_node_syntax.mjs']
        self.assertEqual(len(sources),12)
        for source in sources:
            with self.subTest(source=source.name):
                r=subprocess.run([node,str(ROOT/'scripts/check_node_syntax.mjs'),str(source)],capture_output=True,text=True,
                                 encoding='utf-8',errors='replace',timeout=10)
                self.assertEqual(r.returncode,0,r.stdout+r.stderr)

def case_test(name):
    def test(self):
        node = shutil.which('node')
        self.assertIsNotNone(node, 'Node 24+ is required; a missing runner is not a passing skip')
        with tempfile.TemporaryDirectory(prefix='alaz-hybrid-') as work:
            env = dict(os.environ, ALAZ_PYTHON=sys.executable, ALAZ_TEST_WORK=work)
            result = subprocess.run([node, str(ROOT/'tests/hybrid/cases.mjs'), name],
                                    cwd=ROOT, env=env, capture_output=True, text=True,
                                    encoding='utf-8', errors='replace', timeout=20)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn('"result":"PASS"', result.stdout)
    return test
for name in CASES:
    setattr(HybridSliceTests, 'test_' + name, case_test(name))
if __name__ == '__main__': unittest.main()
