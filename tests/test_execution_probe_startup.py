"""Probe launcher contracts only, not live Gateway scenarios."""
import inspect
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from run_gateway_gap_qa import Generation

class StartupBudgetTests(unittest.TestCase):
    def test_legacy_default_remains_seventy(self):
        self.assertEqual(inspect.signature(Generation).parameters['ready_timeout'].default,70)
    def refuse(self,value):
        with tempfile.TemporaryDirectory() as tmp, patch('run_gateway_gap_qa.subprocess.Popen') as spawn:
            root=Path(tmp)
            with self.assertRaises(ValueError):Generation(None,None,root,{},1,ready_timeout=value)
            spawn.assert_not_called();self.assertEqual(list(root.iterdir()),[])
    def test_zero_rejected_before_spawn(self):self.refuse(0)
    def test_negative_rejected_before_spawn(self):self.refuse(-1)
    def test_excessive_rejected_before_spawn(self):self.refuse(181)
    def test_boolean_rejected_before_spawn(self):self.refuse(True)
    def test_float_rejected_before_spawn(self):self.refuse(90.0)
    def test_string_rejected_before_spawn(self):self.refuse('90')
if __name__=='__main__':unittest.main()
