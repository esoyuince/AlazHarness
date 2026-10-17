"""Offline qualification guards; synthetic receipts are NOT native-run evidence."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import verify_evidence_view_retained as v


def recorded(scenario='normal'):
    end={'exit_code':0,'native_reaped':True,'launcher_reaped':True,
         'forced':False,'kill_requested':False}
    return {'source_commit':v.PIN,'scenario':scenario,'result':'PASS',
            'errors':[],'fixture_errors':[],'code_drift':[],
            'paid_calls':0,'inference_calls':0,'client_exit':0,
            'exit':end.copy(),'restart_exit':end.copy(),'restart_no_refund':True,
            'client':{'final':{'run':{'status':'failed' if scenario!='normal' else 'completed'}}}}


class FixtureReceiptGuards(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name).resolve();self.home=self.root/'runtime/fixture'
        self.home.mkdir(parents=True);self.path=self.home/'execution-result.json'
        self.row=recorded();self.save()
    def save(self):
        self.path.write_text(json.dumps(self.row),encoding='utf-8')
        return hashlib.sha256(self.path.read_bytes()).hexdigest()
    def bad(self,row=None,scenario='normal'):
        with self.assertRaises(ValueError):v.validate_execution_receipt(self.row if row is None else row,scenario)
    def test_valid_normal_receipt(self):self.assertEqual(v.validate_execution_receipt(self.row,'normal'),self.row)
    def test_failed_task_can_be_correctly_qualified(self):
        row=recorded('provider-limit');self.assertEqual(v.validate_execution_receipt(row,'provider-limit'),row)
    def test_missing_positive_result_is_rejected(self):
        del self.row['result'];self.bad()
    def test_wrong_source_pin_is_rejected(self):
        self.row['source_commit']='a'*40;self.bad()
    def test_wrong_scenario_is_rejected(self):self.bad(scenario='provider-limit')
    def test_errors_and_source_drift_are_rejected(self):
        for key in ('errors','fixture_errors','code_drift'):
            for value in (None,['problem']):
                with self.subTest(key=key,value=value):
                    row=recorded();row[key]=value;self.bad(row)
    def test_paid_or_nonzero_client_execution_is_rejected(self):
        for key in ('paid_calls','inference_calls','client_exit'):
            with self.subTest(key=key):
                row=recorded();row[key]=1;self.bad(row)
    def test_bool_is_not_zero_execution_count(self):
        for key in ('paid_calls','inference_calls','client_exit'):
            with self.subTest(key=key):
                row=recorded();row[key]=False;self.bad(row)
    def test_unclosed_or_forced_process_is_rejected(self):
        for key in ('native_reaped','launcher_reaped','forced','kill_requested'):
            with self.subTest(key=key):
                row=recorded();row['exit'][key]=not row['exit'][key];self.bad(row)
    def test_bool_is_not_success_exit_code(self):
        self.row['exit']['exit_code']=False;self.bad()
    def test_normal_requires_restart_evidence(self):
        del self.row['restart_exit'];self.bad()
    def test_normal_requires_budget_preserved_after_restart(self):
        self.row['restart_no_refund']=False;self.bad()
    def test_client_record_required(self):
        self.row['client']=None;self.bad()
    def test_receipt_hash_matches_exact_bytes(self):
        sha=self.save();before=self.path.read_bytes();row,actual=v.read_execution_receipt(self.path,'normal',sha)
        self.assertEqual(actual,sha);self.assertEqual(row,self.row);self.assertEqual(self.path.read_bytes(),before)
    def test_wrong_receipt_hash_rejected(self):
        with self.assertRaisesRegex(ValueError,'fixture_receipt_digest_mismatch'):v.read_execution_receipt(self.path,'normal','0'*64)
    def test_malformed_digest_rejected(self):
        for sha in ('ABC','A'*64,True,12):
            with self.subTest(sha=sha),self.assertRaises(ValueError):v.read_execution_receipt(self.path,'normal',sha)
    def test_malformed_json_rejected(self):
        self.path.write_text('{',encoding='utf-8')
        with self.assertRaises(ValueError):v.read_execution_receipt(self.path,'normal')
    def test_duplicate_json_key_rejected(self):
        raw=json.dumps(self.row);self.path.write_text('{"result":"FAIL",'+raw[1:],encoding='utf-8')
        with self.assertRaises(ValueError):v.read_execution_receipt(self.path,'normal')
    def test_oversized_receipt_rejected(self):
        self.path.write_bytes(b' ' * 2097153)
        with self.assertRaises(ValueError):v.read_execution_receipt(self.path,'normal')
    def test_missing_receipt_not_created(self):
        self.path.unlink()
        with self.assertRaises(ValueError):v.read_execution_receipt(self.path,'normal')
        self.assertFalse(self.path.exists())


class FixturePathGuards(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name).resolve();self.fixture=self.root/'runtime/fixture';self.fixture.mkdir(parents=True)
        self.out=self.root/'runtime/reports'
    def test_explicit_sibling_fixture_accepted(self):
        self.assertEqual(v.validate_paths(self.root,self.out,self.fixture),(self.root,self.out,self.fixture))
    def test_legacy_default_supported(self):
        self.assertEqual(v.validate_paths(self.root,self.out)[2],None)
    def test_existing_output_not_overwritten(self):
        self.out.mkdir();(self.out/'keep').write_text('keep')
        with self.assertRaises(ValueError):v.validate_paths(self.root,self.out,self.fixture)
        self.assertEqual((self.out/'keep').read_text(),'keep')
    def test_output_cannot_be_inside_fixture(self):
        with self.assertRaises(ValueError):v.validate_paths(self.root,self.fixture/'child',self.fixture)
    def test_parent_traversal_cannot_escape_runtime(self):
        with self.assertRaises(ValueError):v.validate_paths(self.root,self.root/'runtime/../outside/report',self.fixture)
    def test_fixture_outside_runtime_rejected(self):
        other=self.root/'outside';other.mkdir()
        with self.assertRaises(ValueError):v.validate_paths(self.root,self.out,other)
    def test_linked_fixture_path_rejected(self):
        original=Path.is_symlink;target=self.fixture
        with patch.object(Path,'is_symlink',lambda p:p==target or original(p)),self.assertRaises(ValueError):
            v.validate_paths(self.root,self.out,self.fixture)
    def test_linked_output_parent_rejected(self):
        original=Path.is_symlink;target=self.out.parent
        with patch.object(Path,'is_symlink',lambda p:p==target or original(p)),self.assertRaises(ValueError):
            v.validate_paths(self.root,self.out,self.fixture)
    def test_cli_requires_all_explicit_identity_fields_before_writing(self):
        command=[sys.executable,'-B',str(ROOT/'scripts/verify_evidence_view_retained.py'),
                 '--source-workspace',str(self.root),'--output',str(self.out),'--fixture',str(self.fixture)]
        completed=subprocess.run(command,capture_output=True,text=True,timeout=10)
        self.assertNotEqual(completed.returncode,0);self.assertFalse(self.out.exists())

if __name__=='__main__':unittest.main()
