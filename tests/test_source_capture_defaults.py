"""Requested pagination is evidence only when explicitly present in tool args."""
import hashlib
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tests'))
import test_source_capture as fx
from recovery_inspector import _json
from execution_budget import ExecutionDenied
from test_reconciliation_inspector_qa import RID
class RequestedBounds(unittest.TestCase):
    def fixture(self,**args):
        c=fx.CaptureContracts();c.setUp();self.addCleanup(c.doCleanups)
        c.args={'path':str(c.file),**args};c.fp=hashlib.sha256(_json({'name':'read_file','args':c.args,'session_id':RID}).encode()).hexdigest();c.ticket=c.ledger.claim('read_file',c.fp);return c
    def test_omitted_bounds_are_not_guessed(self):
        c=self.fixture();c.completed();entry=c.query()['evidenceView']['sourceCaptures'][0]
        self.assertIsNone(entry['requestedLines']['offset']);self.assertIsNone(entry['requestedLines']['limit'])
    def test_explicit_limit_is_preserved(self):
        c=self.fixture(offset=1,limit=3);c.completed();entry=c.query()['evidenceView']['sourceCaptures'][0]
        self.assertEqual(entry['requestedLines']['offset'],1);self.assertEqual(entry['requestedLines']['limit'],3)
    def test_explicit_null_does_not_mean_omitted(self):
        c=self.fixture(limit=None)
        with self.assertRaises(ExecutionDenied):c.invoke()
        self.assertEqual(c.runs,[])
    def test_unpublished_guessed_bound_format_is_not_upgraded(self):
        c=self.fixture();c.completed();key,row=c.rows()[0];row.pop('paginationBasis')
        from execution_budget import seal
        c.f.sql('UPDATE state_meta SET value=? WHERE key=?',(_json(seal(row)),key))
        self.assertFalse(c.query()['evidenceView']['available'])
if __name__=='__main__':unittest.main()
