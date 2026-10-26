"""Pure bounded contract for one scripted native finite qualification lifecycle.

The model factory/computation/close is an explicit fixture. These records never
authorize an external provider, arbitrary prompt, command, listener or replay
after restart. Parsing a record is not proof that its claimed effects occurred.
Only the original supervisor observes the fixed installed child which emits it.
"""
import copy
import hashlib
import json
import re

WORK_PROTOCOL = 'alaz-finite-qualification-v1'
RESULT_PROTOCOL = 'alaz-projected-finite-qualification-v1'
MAX_WORK = 2048
MAX_RESULT = 16384
KINDS = ('normal', 'replay', 'new', 'error')
MESSAGES = {'normal': 'SUM:17,25,8', 'new': 'SUM:3,4',
            'error': 'FAIL:controlled-native-finite'}
ANSWERS = {'normal': '50', 'new': '7'}
COMPLETED_CHECKS = ['preflight', 'response_preflight', 'before_epoch',
                    'response_before_epoch', 'after_epoch', 'response_after_epoch']
PROFILE_FUNCTIONS = ('run_api_turn', 'execute_finite_admission', 'run_sync',
                     'commit_and_publish', 'settle_session_input')


class FiniteProtocolRejected(RuntimeError):
    """A bounded non-secret diagnostic; no work payload is interpolated."""


def require(ok, reason):
    if not ok:
        raise FiniteProtocolRejected(reason)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=True, allow_nan=False).encode('ascii')


def _id(value):
    return (type(value) is str
            and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,95}', value) is not None)


def _sha(value):
    return type(value) is str and re.fullmatch('[0-9a-f]{64}', value) is not None


def validate_work(work):
    """No paths, executable names, secrets or model configuration are accepted."""
    require(type(work) is dict and set(work) == {'protocol', 'sessionId', 'requestIds'},
            'finite_work_fields')
    require(work['protocol'] == WORK_PROTOCOL and _id(work['sessionId']),
            'finite_work_protocol_or_session')
    ids = work['requestIds']
    require(type(ids) is dict and set(ids) == {'normal', 'new', 'error'}
            and all(_id(value) for value in ids.values())
            and len(set(ids.values())) == 3, 'finite_request_identities')
    require(len(canonical(work)) <= MAX_WORK, 'finite_work_size')
    return copy.deepcopy(work)


def work_digest(work):
    return hashlib.sha256(canonical(validate_work(work))).hexdigest()


def validate_result(result, *, work, pid, previous_epoch):
    """Validate the fixed child's entire completion, including original close.

    A failed *application case* is required here. A crashed/malformed child is
    never a completion. The supervisor additionally checks/reaps the actual
    process and verifies its original worker and cgroup before allowing close.
    """
    expected = validate_work(work)
    require(type(pid) is int and pid > 0 and type(previous_epoch) is int
            and previous_epoch >= 0, 'finite_observer_identity')
    require(type(result) is dict and set(result) == {
        'protocol', 'state', 'pid', 'epoch', 'completedChecks', 'workSha256',
        'caseReceipts', 'nativeProfileCallEvents', 'close', 'model',
        'localAdmissionActivated', 'canonicalApiPublished', 'serviceStarted',
        'runtimeAdmissionAuthorized', 'finiteWorkExecuted', 'fullD3BAccepted'},
        'finite_result_fields')
    require(result['protocol'] == RESULT_PROTOCOL
            and result['state'] == 'PROJECTED_FINITE_OWNER_CLOSED'
            and type(result['pid']) is int and result['pid'] == pid
            and type(result['epoch']) is int and result['epoch'] == previous_epoch + 1,
            'finite_result_identity')
    require(result['completedChecks'] == COMPLETED_CHECKS
            and type(result['completedChecks']) is list
            and result['workSha256'] == work_digest(expected), 'finite_result_binding')
    for name in ('localAdmissionActivated', 'canonicalApiPublished', 'finiteWorkExecuted'):
        require(result[name] is True, 'finite_result_work_scope')
    for name in ('serviceStarted', 'runtimeAdmissionAuthorized', 'fullD3BAccepted'):
        require(result[name] is False, 'finite_result_excluded_scope')
    cases = result['caseReceipts']
    require(type(cases) is list and len(cases) == 4, 'finite_result_cases')
    for index, (kind, count) in enumerate(zip(KINDS, (1, 1, 2, 3))):
        case = cases[index]
        require(type(case) is dict and set(case) == {
            'kind', 'requestId', 'admissionId', 'outcome', 'apiResultSha256',
            'storedResultSha256', 'computationCount'}, 'finite_case_fields')
        request_kind = 'normal' if kind == 'replay' else kind
        require(case['kind'] == kind
                and case['requestId'] == expected['requestIds'][request_kind]
                and type(case['admissionId']) is str
                and re.fullmatch(r'[A-Za-z0-9._:-]{1,128}', case['admissionId']) is not None
                and case['outcome'] == ('failed' if kind == 'error' else 'completed')
                and type(case['computationCount']) is int and case['computationCount'] == count
                and _sha(case['apiResultSha256']) and _sha(case['storedResultSha256']),
                'finite_case_result')
    require(all(cases[0][name] == cases[1][name] for name in (
                'requestId', 'admissionId', 'outcome', 'apiResultSha256',
                'storedResultSha256', 'computationCount')),
            'finite_exact_replay_changed')
    require(len({cases[i]['admissionId'] for i in (0, 2, 3)}) == 3,
            'finite_new_identity_reused')
    counts = result['nativeProfileCallEvents']
    require(type(counts) is dict and set(counts) == set(PROFILE_FUNCTIONS)
            and all(type(v) is int and 1 <= v <= 10000 for v in counts.values()),
            'finite_native_trace_missing')
    close = result['close']
    require(type(close) is dict and set(close) == {
        'consumerState', 'ownerState', 'sameThreeConnections', 'registryRefcounts',
        'physicalConnectionsClosed', 'modelInstancesClosed',
        'rowsChangedByRetirement', 'callerLeaseReleased'}, 'finite_close_fields')
    require(close['consumerState'] == 'DETACHED' and close['ownerState'] == 'CLOSED'
            and close['sameThreeConnections'] is True
            and type(close['registryRefcounts']) is int and close['registryRefcounts'] == 0
            and type(close['physicalConnectionsClosed']) is int
            and close['physicalConnectionsClosed'] == 3
            and close['modelInstancesClosed'] is True
            and type(close['rowsChangedByRetirement']) is int
            and close['rowsChangedByRetirement'] == 0
            and close['callerLeaseReleased'] is True, 'finite_original_close_incomplete')
    model = result['model']
    require(type(model) is dict and set(model) == {
        'kind', 'factoryComputationCloseDoubled', 'realProviderCalls', 'modelInvocations'}
        and model['kind'] == 'scripted-factory-fixture'
        and model['factoryComputationCloseDoubled'] is True
        and type(model['realProviderCalls']) is int and model['realProviderCalls'] == 0
        and type(model['modelInvocations']) is int and model['modelInvocations'] == 3,
        'finite_model_scope')
    try:
        encoded = canonical(result)
    except (TypeError, ValueError, RecursionError, OverflowError):
        raise FiniteProtocolRejected('finite_result_encoding') from None
    require(len(encoded) <= MAX_RESULT, 'finite_result_size')
    return copy.deepcopy(result)
