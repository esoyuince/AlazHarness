"""Pure bounded finite work/result schema; no claimed native acceptance."""
import copy
import hashlib
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'packages/claw-hermes'))
import gateway_finite_protocol as protocol
from test_supervised_finite_launch import qualification_work, qualification_result


class WorkContract(unittest.TestCase):
    def test_canonical_digest_and_deep_copy_do_not_open_resources(self):
        work = qualification_work()
        with patch('builtins.open', side_effect=AssertionError('pure contract opens no file')), \
                patch.object(Path, 'stat', side_effect=AssertionError('pure contract stats no file')):
            checked = protocol.validate_work(work)
            digest = protocol.work_digest(work)
        self.assertEqual(digest, hashlib.sha256(protocol.canonical(work)).hexdigest())
        reordered = dict(reversed(list(work.items())))
        self.assertEqual(protocol.work_digest(reordered), digest)
        checked['requestIds']['normal'] = 'changed'
        self.assertNotEqual(checked, work)

    def test_only_exact_work_fields_and_fixed_protocol_are_allowed(self):
        work = qualification_work()
        values = [None, [], {}, {**work, 'prompt': 'text'}, {**work, 'command': ['/bin/sh']},
                  {**work, 'protocol': None}, {**work, 'protocol': 'other-v1'}]
        for key in work:
            value = copy.deepcopy(work)
            value.pop(key)
            values.append(value)
        for value in values:
            with self.subTest(value=value), self.assertRaises(protocol.FiniteProtocolRejected):
                protocol.validate_work(value)

    def test_request_ids_are_unique_exact_and_bounded(self):
        work = qualification_work()
        for invalid in (None, True, 1, '', 'x' * 97, '../path', '/absolute', 'space here', 'line\nfeed', 'nonascii-ç'):
            for key in ('sessionId', 'normal'):
                changed = copy.deepcopy(work)
                if key == 'sessionId':
                    changed[key] = invalid
                else:
                    changed['requestIds'][key] = invalid
                with self.subTest(key=key, invalid=invalid), self.assertRaises(protocol.FiniteProtocolRejected):
                    protocol.validate_work(changed)
        duplicate = copy.deepcopy(work)
        duplicate['requestIds']['new'] = duplicate['requestIds']['normal']
        with self.assertRaises(protocol.FiniteProtocolRejected):
            protocol.validate_work(duplicate)
        for ids in ({'normal': 'a', 'new': 'b'}, {'normal': 'a', 'new': 'b', 'error': 'c', 'replay': 'd'}):
            with self.assertRaises(protocol.FiniteProtocolRejected):
                protocol.validate_work({**work, 'requestIds': ids})
        self.assertEqual(protocol.validate_work({**work, 'sessionId': 'a' * 96})['sessionId'], 'a' * 96)


class ResultContract(unittest.TestCase):
    def setUp(self):
        self.work = qualification_work()
        self.result = qualification_result(self.work)

    def validate(self, result):
        return protocol.validate_result(result, work=self.work, pid=30, previous_epoch=1)

    def refuse(self, change):
        result = copy.deepcopy(self.result)
        change(result)
        with self.assertRaises(protocol.FiniteProtocolRejected):
            self.validate(result)

    def test_complete_receipt_including_logical_error_is_a_deep_copy(self):
        checked = self.validate(self.result)
        self.assertEqual(checked, self.result)
        self.assertEqual(checked['caseReceipts'][-1]['outcome'], 'failed')
        checked['close']['callerLeaseReleased'] = False
        checked['caseReceipts'][0]['requestId'] = 'changed'
        self.assertTrue(self.result['close']['callerLeaseReleased'])
        self.assertEqual(self.result['caseReceipts'][0]['requestId'], self.work['requestIds']['normal'])

    def test_result_is_bound_to_exact_process_epoch_work_and_schema(self):
        for changes in ({'pid': 31}, {'pid': True}, {'epoch': 1}, {'epoch': True},
                        {'protocol': protocol.WORK_PROTOCOL}, {'workSha256': '0' * 64},
                        {'state': 'PROJECTED_RETAINED_OWNER_CLOSED'}, {'extra': 'foreign'}):
            self.refuse(lambda result, changes=changes: result.update(changes))
        for key in self.result:
            self.refuse(lambda result, key=key: result.pop(key))
        self.refuse(lambda result: result.update(completedChecks=list(reversed(protocol.COMPLETED_CHECKS))))
        with self.assertRaises(protocol.FiniteProtocolRejected):
            protocol.validate_result(self.result, work=self.work, pid=True, previous_epoch=1)

    def test_exact_replay_does_not_gain_an_admission_or_computation(self):
        for changes in ({'admissionId': 'other'}, {'requestId': 'other'}, {'computationCount': 2},
                        {'apiResultSha256': '0' * 64}, {'storedResultSha256': '0' * 64}):
            self.refuse(lambda result, changes=changes: result['caseReceipts'][1].update(changes))
        self.refuse(lambda result: result['caseReceipts'][2].update(admissionId='admission-a'))
        self.refuse(lambda result: result['caseReceipts'][-1].update(outcome='completed'))
        self.refuse(lambda result: result['caseReceipts'].reverse())
        self.refuse(lambda result: result['caseReceipts'].pop())

    def test_native_trace_and_declared_model_scope_cannot_be_omitted_or_expanded(self):
        for key in protocol.PROFILE_FUNCTIONS:
            for invalid in (0, True, -1, 10001):
                self.refuse(lambda result, key=key, invalid=invalid:
                    result['nativeProfileCallEvents'].update({key: invalid}))
        for changes in ({'realProviderCalls': 1}, {'modelInvocations': 4},
                        {'factoryComputationCloseDoubled': False}, {'kind': 'real-model'}):
            self.refuse(lambda result, changes=changes: result['model'].update(changes))

    def test_every_original_close_condition_is_required(self):
        for changes in ({'consumerState': 'DRAINING'}, {'ownerState': 'VERIFIED'},
                        {'sameThreeConnections': False}, {'registryRefcounts': 1},
                        {'physicalConnectionsClosed': 2}, {'modelInstancesClosed': False},
                        {'rowsChangedByRetirement': 1}, {'callerLeaseReleased': False},
                        {'registryRefcounts': False}, {'rowsChangedByRetirement': False}):
            self.refuse(lambda result, changes=changes: result['close'].update(changes))

    def test_qualification_flags_are_exact_booleans_without_service_authority(self):
        for key in ('localAdmissionActivated', 'canonicalApiPublished', 'finiteWorkExecuted'):
            for value in (False, 1):
                self.refuse(lambda result, key=key, value=value: result.update({key: value}))
        for key in ('serviceStarted', 'runtimeAdmissionAuthorized', 'fullD3BAccepted'):
            for value in (True, 0):
                self.refuse(lambda result, key=key, value=value: result.update({key: value}))


if __name__ == '__main__':
    unittest.main()
