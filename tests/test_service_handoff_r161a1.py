"""Pure service startup codec tests; no store, exec or confinement acceptance."""
from dataclasses import asdict, replace, FrozenInstanceError
from pathlib import Path, PurePosixPath
import json
import os
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'packages/claw-hermes'))
import gateway_service_handoff as h
import gateway_retained_handoff as finite
import test_service_projection_r161a1 as fixture


class ServiceHandoffContract(unittest.TestCase):
    def setUp(self):
        self.state = h.preopen.live.PreparedStoreExpectation(h.preopen.live.NATIVE_PIN,
            'a' * 64, 'b' * 64, '12345678-1234-4234-8234-123456789012',
            123, (1792, 21), (1792, 22), 1, 'previous-native-owner')
        self.reply = h.response.PreparedResponseExpectation(h.response.NATIVE_FEATURE,
            h.response.SCHEMA_SHA256, (1792, 23))
        self.receipt = fixture.receipt(h.TARGET)
        self.value = h.ServiceStartup(self.state, self.reply, self.receipt)
        self.raw = h.encode(self.value, expected_home=h.TARGET)

    def wire(self):
        return json.loads(self.raw)

    def encoded(self, value):
        return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()

    def refused(self, raw):
        with self.assertRaises(h.HandoffRejected):
            h.decode(raw, expected_home=h.TARGET)

    def test_roundtrip_preserves_exact_typed_source_and_config_expectation(self):
        decoded = h.decode_projected(self.raw)
        self.assertEqual(decoded, self.value); self.assertIsNot(decoded, self.value)
        self.assertIs(type(decoded), h.ServiceStartup)
        self.assertIs(type(decoded.service), h.profile.ServiceProfileExpectation)
        self.assertIs(type(decoded.service.selection), h.ServiceSourceSelection)
        self.assertIs(type(decoded.service.database_identities), tuple)
        self.assertEqual(h.encode(decoded, expected_home=h.TARGET), self.raw)
        with self.assertRaises(FrozenInstanceError): decoded.service = None

    def test_codec_does_not_read_config_manifest_or_filesystem(self):
        with patch('builtins.open', side_effect=AssertionError('no file I/O')), \
                patch.object(Path, 'stat', side_effect=AssertionError('no stat')), \
                patch.object(h.profile.sources, 'load_selection', side_effect=AssertionError('no source I/O')):
            self.assertEqual(h.decode_projected(self.raw), self.value)

    def test_wire_contains_only_config_identity_size_digest_not_content(self):
        config_fields = {k for k in self.wire()['service'] if k.startswith('config')}
        self.assertEqual(config_fields, {'config_identity', 'config_size', 'config_sha256'})
        self.assertNotIn('config', self.wire())

    def test_missing_and_unknown_fields_at_every_nested_level_are_refused(self):
        for level in (None, 'state', 'response', 'service', 'selection'):
            for operation in ('missing', 'unknown'):
                wire = self.wire()
                values = wire if level is None else wire['service']['selection'] if level == 'selection' else wire[level]
                if operation == 'missing': values.pop(next(iter(values)))
                else: values['foreign'] = None
                with self.subTest(level=level, operation=operation): self.refused(self.encoded(wire))

    def test_duplicate_fields_never_last_win(self):
        for raw in (self.raw[:-1] + b',"protocol":"' + h.PROTOCOL.encode() + b'"}',
                    self.raw.replace(b'"config_size":40', b'"config_size":40,"config_size":40'),
                    self.raw.replace(b'"schema":1', b'"schema":1,"schema":1')):
            self.refused(raw)

    def test_nonfinite_float_boolean_and_large_integer_fields_refused(self):
        for number in (b'NaN', b'Infinity', b'-Infinity', b'40.0', b'4e1', b'true', b'9' * 100):
            self.refused(self.raw.replace(b'"config_size":40', b'"config_size":' + number))
        for key, value in (('schema', True), ('epoch', True), ('epoch', 2**63),
                           ('config_size', 0), ('config_size', h.profile.MAX_CONFIG_BYTES + 1)):
            wire = self.wire(); wire['service'][key] = value; self.refused(self.encoded(wire))

    def test_byte_type_length_utf8_depth_and_json_bounds(self):
        for raw in (None, '{}', bytearray(self.raw), b'', b'\xff', self.raw[:-1],
                    b'x' * (h.MAX_BYTES + 1), b'[' * 1500 + b']' * 1500):
            self.refused(raw)

    def test_noncanonical_representation_refused(self):
        for raw in (b' ' + self.raw, self.raw + b'\n', json.dumps(self.wire(), indent=2).encode()):
            self.refused(raw)

    def test_wrong_protocol_and_old_finite_payload_refused(self):
        for value in (None, True, 1, finite.PROTOCOL, 'alaz-service-startup-v2'):
            wire = self.wire(); wire['protocol'] = value; self.refused(self.encoded(wire))
        old = finite.retained.RetainedProfileExpectation(finite.retained.FEATURE, h.TARGET,
            (1792, 12), ((1792, 21), (1792, 22), (1792, 23)),
            1, 'previous-native-owner', 'd' * 64)
        with patch.object(finite.retained, 'Path', PurePosixPath):
            raw = finite.encode(finite.RetainedStartup(self.state, self.reply, old), expected_home=h.TARGET)
        self.refused(raw)
        with self.assertRaises(finite.HandoffRejected): finite.decode(self.raw, expected_home=h.TARGET)

    def test_previous_generation_and_journal_mode_bound(self):
        for key, value in (('epoch', 2), ('instance_id', 'different-owner')):
            wire = self.wire(); wire['service'][key] = value; self.refused(self.encoded(wire))
        for mode in ('wal', 'persist', 'truncate', None):
            wire = self.wire(); wire['state']['journal_mode'] = mode; self.refused(self.encoded(wire))

    def test_config_identity_cannot_alias_database_or_cross_device(self):
        for value in ([1792, 21], [1792, 12], [1793, 24], [True, 24], [1792],
                      [1792, 24, 1], ['1792', 24], [0, 24], [2**64, 24]):
            wire = self.wire(); wire['service']['config_identity'] = value; self.refused(self.encoded(wire))

    def test_database_order_response_schema_and_native_state_pin_bound(self):
        wire = self.wire(); wire['service']['database_identities'].reverse(); self.refused(self.encoded(wire))
        for level, key in (('state', 'native_pin'), ('response', 'schema_sha256'), ('response', 'native_feature')):
            wire = self.wire(); wire[level][key] = '0' * len(wire[level][key]); self.refused(self.encoded(wire))

    def test_malformed_selected_source_and_config_digests_refused(self):
        for key, value in (('native_feature', 'x' * 40), ('manifest_sha256', 'F' * 64),
                           ('selection_sha256', '0' * 63)):
            wire = self.wire(); wire['service']['selection'][key] = value; self.refused(self.encoded(wire))
        for key in ('config_sha256', 'discovery_sha256'):
            wire = self.wire(); wire['service'][key] = 'NOT-A-DIGEST'; self.refused(self.encoded(wire))

    def test_codec_preserves_but_does_not_authenticate_structurally_valid_selection(self):
        changed = replace(self.receipt, selection=replace(self.receipt.selection, selection_sha256='e' * 64))
        value = replace(self.value, service=changed)
        raw = h.encode(value, expected_home=h.TARGET)
        self.assertEqual(h.decode_projected(raw), value)
        # Actual inspect/check compares this data with the installed selection;
        # JSON decoding deliberately grants no admission authority.

    def test_expected_home_is_supplied_by_caller_not_taken_from_payload(self):
        with self.assertRaisesRegex(h.HandoffRejected, 'home_mismatch'):
            h.decode(self.raw, expected_home='/other/profile')
        value = replace(self.value, service=replace(self.receipt, home='/other/profile'))
        raw = h.encode(value, expected_home='/other/profile')
        with self.assertRaises(h.HandoffRejected): h.decode_projected(raw)
        for home in ('relative', '/run//profile', '/run/./profile', '/run/../profile',
                     '//run/alaz-state/profile', h.TARGET + '/', '/run\\profile', '/run\x00/profile'):
            with self.assertRaises(h.HandoffRejected): h.decode(self.raw, expected_home=home)

    def test_raw_dict_subclass_and_mutated_frozen_member_refused(self):
        class Other(h.ServiceStartup): pass
        for value in (asdict(self.value), Other(self.state, self.reply, self.receipt),
                      replace(self.value, service=asdict(self.receipt))):
            with self.assertRaises(h.HandoffRejected): h.encode(value, expected_home=h.TARGET)
        object.__setattr__(self.receipt, 'config_size', True)
        with self.assertRaises(h.HandoffRejected): h.encode(self.value, expected_home=h.TARGET)

    def projected(self):
        return {'version': 1, 'pid': os.getpid(), 'stateDirectoryCount': 1,
            'ambientHostDirectoriesBound': 0, 'hostUserNamespacePreserved': True,
            'legacyIpcV2Activated': False, 'fullD3BAccepted': False,
            'state': 'confined_state_profile', 'profile': h.TARGET,
            'profileLayout': h.profile.SERVICE_LAYOUT, 'serviceProjectionVerified': True,
            'persistentProfileProjected': True, 'rootPrivilegesDropped': True,
            'profileOwnershipAcquired': False, 'nativeHermesStoresOpened': False,
            'serviceProfile': self.receipt, 'profileDevice': 1792, 'profileInode': 12}

    def test_projected_codec_requires_completed_current_process_service_projection(self):
        projected = self.projected()
        self.assertEqual(h.encode_projected(projected, self.state, self.reply), self.raw)
        for key, value in (('pid', os.getpid() + 1), ('rootPrivilegesDropped', 1),
                ('serviceProjectionVerified', False), ('nativeHermesStoresOpened', True),
                ('profileOwnershipAcquired', True), ('profileLayout', 'hermes-native-retained-three-stores-v1'),
                ('profileInode', True), ('profileDevice', 999), ('fullD3BAccepted', True),
                ('ambientHostDirectoriesBound', 1), ('stateDirectoryCount', 2)):
            with self.subTest(key=key), self.assertRaises(h.HandoffRejected):
                h.encode_projected(dict(projected, **{key: value}), self.state, self.reply)

    def test_finite_claims_cannot_be_mixed_into_service_projection(self):
        for extra in ({'retainedProfile': None}, {'retainedProjectionVerified': True}):
            with self.assertRaises(h.HandoffRejected):
                h.encode_projected(dict(self.projected(), **extra), self.state, self.reply)


if __name__ == '__main__':
    unittest.main()
