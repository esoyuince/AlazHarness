"""Actual selected Hermes component behavior and reproducible source provenance."""
from concurrent.futures import ThreadPoolExecutor
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from verify_components import inspect, materialize

def load(name):
    spec = importlib.util.spec_from_file_location('component_' + name, ROOT / 'packages/upstream/hermes' / (name + '.py'))
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module

budget = load('iteration_budget'); keys = load('hermes_state_keys'); mapper = load('terminal_status')

class HermesComponentTests(unittest.TestCase):
    def test_budget_hard_limit(self):
        b = budget.IterationBudget(3)
        self.assertEqual([b.consume() for _ in range(5)], [True, True, True, False, False])
        self.assertEqual((b.used, b.remaining), (3, 0))
    def test_budget_concurrent_consumption(self):
        b = budget.IterationBudget(17)
        with ThreadPoolExecutor(max_workers=8) as pool:
            values = list(pool.map(lambda _: b.consume(), range(200)))
        self.assertEqual(sum(values), 17); self.assertEqual(b.used, 17)
    def test_budget_refund_not_negative(self):
        b = budget.IterationBudget(1); b.refund(); self.assertEqual(b.used, 0)
        b.consume(); b.refund(); self.assertTrue(b.consume())
    def test_nonfinite_budget_warning_off(self):
        for value in [float('nan'), float('inf'), True, -1, 0, 1, 'bad']:
            with self.subTest(value=value): self.assertIsNone(budget.normalize_budget_warning_ratio(value))
        self.assertEqual(budget.normalize_budget_warning_ratio('0.8'), 0.8)
    def test_fingerprint_order_stable(self):
        self.assertEqual(keys.admission_fingerprint(canonical_target='a', payload={'b': 2, 'a': 1}),
                         keys.admission_fingerprint(canonical_target='a', payload={'a': 1, 'b': 2}))
    def test_fingerprint_target_isolated(self):
        self.assertNotEqual(keys.admission_fingerprint(canonical_target='a', payload={'x': 1}),
                            keys.admission_fingerprint(canonical_target='b', payload={'x': 1}))
    def test_fingerprint_rejects_nan(self):
        with self.assertRaises(ValueError): keys.admission_fingerprint(canonical_target='a', payload={'x': float('nan')})
    def test_hermes_partial_never_completed(self):
        state, fields = mapper.terminal_run_status({'partial': True, 'completed': False, 'turn_exit_reason': 'budget'})
        self.assertEqual(state, 'failed'); self.assertFalse(fields['completed'])
        self.assertEqual(fields['turn_exit_reason'], 'budget')
    def test_hermes_interrupted_precedence(self):
        state, fields = mapper.terminal_run_status({'interrupted': True, 'completed': True})
        self.assertEqual(state, 'cancelled'); self.assertFalse(fields['completed'])

class ComponentProvenanceTests(unittest.TestCase):
    def test_selected_hashes_match(self):
        self.assertEqual(inspect(ROOT)['components'], 10)
    def test_missing_symbol_rejected(self):
        with self.assertRaises(ValueError): materialize(b'def other(): pass\n', {'mode': 'function', 'symbol': 'target', 'prefix': ''})
    def test_rewrite_must_be_unique(self):
        with self.assertRaises(ValueError): materialize(b'a a', {'mode': 'rewrite', 'replacements': [['a', 'b']]})
    def test_changed_component_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            shutil.copy(ROOT / 'sources.lock.json', root / 'sources.lock.json')
            (root / 'config').mkdir(); shutil.copy(ROOT / 'config/components.lock.json', root / 'config/components.lock.json')
            shutil.copytree(ROOT / 'packages/upstream', root / 'packages/upstream')
            target = root / 'packages/upstream/openclaw/attempt-cancellation.ts'
            target.write_text('tampered', encoding='utf-8')
            with self.assertRaises(ValueError): inspect(root)

if __name__ == '__main__': unittest.main()
