"""Pure host fingerprint tests, not Pi runtime/crash evidence."""
import json
from pathlib import Path
import shutil
import subprocess
import unittest
ROOT=Path(__file__).resolve().parents[1]
CASES=['canonical_order', 'array_order', 'unicode_exact', 'unicode_no_normalization', 'scope_changes_fingerprint', 'key_not_fingerprint', 'key_scope_stable', 'default_followup', 'whitespace_matters', 'snapshot_detached', 'reject_undefined', 'reject_nan', 'reject_infinity', 'reject_bigint', 'reject_function', 'reject_symbol', 'reject_date', 'reject_getter_without_call', 'reject_cycle', 'reject_sparse', 'reject_extra_array_property', 'reject_lone_surrogate', 'reject_missing_id', 'reject_empty_id', 'reject_big_id', 'reject_unknown_field', 'reject_type', 'reject_busy_value', 'reject_busy_null', 'reject_depth', 'reject_bytes', 'reject_escaped_byte_overflow', 'reject_hidden_property', 'proto_key_is_data', 'minus_zero_json_semantics', 'reject_nonobject_scope']
CASES += ['reject_foreign_handle','reject_unknown_owned_conversation']
class StrictAdmissionTests(unittest.TestCase):
    pass

def make_case(name):
    def test(self):
        node=shutil.which('node')
        self.assertIsNotNone(node,'Node required; missing tool is not a skip')
        result=subprocess.run([node,str(ROOT/'tests/node/admission-cases.mjs'),name],cwd=ROOT,capture_output=True,text=True,encoding='utf-8',timeout=15)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads(result.stdout),{'case':name,'result':'PASS'})
    return test
for name in CASES:setattr(StrictAdmissionTests,'test_'+name,make_case(name))
if __name__=='__main__':unittest.main()
