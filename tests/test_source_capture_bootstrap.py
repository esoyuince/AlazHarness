"""Native plugin loader removes its temporary import path after registration."""
from pathlib import Path
import subprocess
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1]
class SourceBootstrap(unittest.TestCase):
    def test_source_module_available_after_plugin_path_removed(self):
        product=str(ROOT/'packages/claw-hermes')
        code="import sys,importlib; p="+repr(product)+"; sys.path.insert(0,p); import isolated_read; sys.path.remove(p); m=importlib.import_module('source_capture'); assert m.PREFIX=='alaz.evidence.source.v1.'"
        result=subprocess.run([sys.executable,'-I','-B','-c',code],capture_output=True,text=True,timeout=15)
        self.assertEqual(result.returncode,0,result.stderr)
if __name__=='__main__':unittest.main()
