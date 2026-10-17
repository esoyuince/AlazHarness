"""G03 regression from actual 250-line native observation; native-call default=2000.
No native application is launched; actual Alaz invoke must reconcile its effective
args with the stored capture. Defaults below are the inspected pinned native ABI.
"""
from pathlib import Path
import hashlib
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'packages/claw-hermes'));sys.path.insert(0,str(ROOT/'tests'))
import test_source_capture_qa_c72e as qa
import recovery_inspector as ri
from test_reconciliation_inspector_qa import RID


class SourcePaginationIndependentQA(unittest.TestCase):
    def setUp(self):qa.CaptureIndependentQA.setUp(self)
    def original(self,args,**kwargs):return qa.CaptureIndependentQA.original(self,args,**kwargs)
    def invoke(self,original=None,**kwargs):return qa.CaptureIndependentQA.invoke(self,original,**kwargs)
    def captures(self):return qa.CaptureIndependentQA.captures(self)

    def check(self, raw):
        self.args=raw.copy()
        self.fp=hashlib.sha256(ri._json({'name':'read_file','args':self.args,'session_id':RID}).encode()).hexdigest()
        self.ticket=self.ledger.claim('read_file',self.fp)
        called={}
        def native(args,**kwargs):
            # Exact inspected Hermes _handle_read_file default, not Alaz's
            # metadata default. Missing limit genuinely means 2000 upstream.
            called.update(offset=args.get('offset',1),limit=args.get('limit',2000))
            return self.original(args,**kwargs)
        self.invoke(native)
        row=self.captures()[0][1]
        self.assertEqual(row['requestedLimit'],raw.get('limit'),'omitted request must remain null, not a guessed native default')
        self.assertEqual(row['requestedOffset'],raw.get('offset'))
        self.assertEqual(called['limit'],raw.get('limit',2000),'do not silently change original native call while recording it')
        self.assertEqual(called['offset'],raw.get('offset',1))
        self.assertEqual(row['fingerprint'],self.fp,'bind original omitted/explicit request identity')
        self.assertEqual(self.args,raw,'do not mutate caller request to hide default mismatch')

    def test_omitted_pagination_matches_effective_native_values(self):
        self.check({'path':str(self.file)})

    def test_explicit_offset_and_limit_preserved(self):
        self.check({'path':str(self.file),'offset':3,'limit':17})

    def test_explicit_maximum_is_not_replaced_by_native_default(self):
        self.check({'path':str(self.file),'limit':1000})
