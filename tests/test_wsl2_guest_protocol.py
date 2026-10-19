"""Fixed WSL2 read-only guest protocol input refusals, no WSL startup."""
import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location(
    'plat002_guest',ROOT/'scripts/qa/wsl2_bridge_guest_probe.py')
GUEST=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GUEST)

def frame(**updates):
    body={'version':1,'operation':'identify',
          'nonce':'a'*64,'requestId':'b'*32}
    body.update(updates)
    return (json.dumps(body,separators=(',',':'))+'\n').encode('utf-8')

class GuestWireSafety(unittest.TestCase):
    def test_exact_bounded_valid_request(self):
        r=GUEST.parse(frame())
        self.assertEqual(r['version'],1)
        self.assertEqual(r['operation'],'identify')
        self.assertEqual(r['nonce'],'a'*64)
        self.assertEqual(r['requestId'],'b'*32)
    def test_missing_fields_refused(self):
        with self.assertRaises(GUEST.Refused):
            GUEST.parse(b'{"version":1}\n')
    def test_unknown_fields_refused(self):
        with self.assertRaises(GUEST.Refused):
            GUEST.parse(frame(cmd='date'))
    def test_unknown_operation_refused(self):
        for value in ('execute','connect','pay','delegate','shell'):
            with self.subTest(value=value),self.assertRaises(GUEST.Refused):
                GUEST.parse(frame(operation=value))
    def test_duplicate_json_key_refused(self):
        raw=b'{"version":1,"version":1,"operation":"identify","nonce":"' + (
            b'a'*64)+b'","requestId":"'+(b'b'*32)+b'"}\n'
        with self.assertRaisesRegex(GUEST.Refused,'duplicate_json_key'):
            GUEST.parse(raw)
    def test_nonfinite_number_refused(self):
        raw=frame().replace(b'1,',b'NaN,',1)
        with self.assertRaises(GUEST.Refused):
            GUEST.parse(raw)
    def test_bool_version_refused(self):
        with self.assertRaises(GUEST.Refused):
            GUEST.parse(frame(version=True))
    def test_unsupported_version_refused(self):
        with self.assertRaises(GUEST.Refused):
            GUEST.parse(frame(version=2))
    def test_nonce_validation(self):
        for bad in ('', 'A'*64,'z'*64,'a'*63,1,True,None):
            with self.subTest(bad=bad),self.assertRaises(GUEST.Refused):
                GUEST.parse(frame(nonce=bad))
    def test_request_id_validation(self):
        for bad in ('', 'B'*32,'b'*31,12,None):
            with self.subTest(bad=bad),self.assertRaises(GUEST.Refused):
                GUEST.parse(frame(requestId=bad))
    def test_empty_frame_refused(self):
        with self.assertRaises(GUEST.Refused):
            GUEST.parse(b'')
    def test_oversized_frame_refused(self):
        with self.assertRaises(GUEST.Refused):
            GUEST.parse(b'A'*1200)
    def test_missing_newline_refused(self):
        with self.assertRaises(GUEST.Refused):
            GUEST.parse(frame().strip())
    def test_two_lines_refused(self):
        with self.assertRaises(GUEST.Refused):
            GUEST.parse(frame()+frame())
    def test_null_byte_refused(self):
        with self.assertRaises(GUEST.Refused):
            GUEST.parse(frame().replace(b'identify',b'\x00identify'))
    def test_bad_utf8_refused(self):
        with self.assertRaises(GUEST.Refused):
            GUEST.parse(b'\xff\n')
    def test_json_list_refused(self):
        with self.assertRaises(GUEST.Refused):
            GUEST.parse(b'[]\n')
    def test_nondict_request_refused(self):
        with self.assertRaises(GUEST.Refused):
            GUEST.parse(b'null\n')
    def test_linux_requirement_does_not_fake_wsl(self):
        with patch.object(GUEST.platform,'system',return_value='Windows'):
            with self.assertRaisesRegex(GUEST.Refused,'linux_x64_required'):
                GUEST.respond(GUEST.parse(frame()))
    def test_native_linux_without_wsl2_refused(self):
        with patch.object(GUEST.platform,'system',return_value='Linux'),\
             patch.object(GUEST.platform,'machine',return_value='x86_64'),\
             patch.object(GUEST.platform,'release',return_value='6.6.0-generic'):
            with self.assertRaisesRegex(GUEST.Refused,'verified_wsl2_guest_required'):
                GUEST.respond(GUEST.parse(frame()))

if __name__=='__main__':unittest.main()
