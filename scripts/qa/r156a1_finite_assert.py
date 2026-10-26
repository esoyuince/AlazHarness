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

INSTALLATION_RECEIPT_SHA = 'a4bcc0f27d29f27f08c55d3a65eaa102a503a7da12d4672253f0245fd5d4f845'
HARNESS_COMMIT = 'e641a5000810efb2a453ae847f689b422f7d41a7'


WORK = {'protocol': 'alaz-finite-qualification-v1', 'sessionId': 'r156a1-session',
        'requestIds': {'normal': 'r156a1-normal', 'new': 'r156a1-new', 'error': 'r156a1-error'}}


def validate_supervised(value):
    require(type(value) is dict and set(value) == {
        'state', 'pid', 'childStartTicks', 'owner', 'inputSha256', 'stdoutSha256',
        'stderrSha256', 'stderrBytes', 'observedAfterUnknown', 'childExited',
        'volumeMayClose', 'finiteWorkExecuted', 'fullD3BAccepted'}, 'accept_finite_supervisor_fields')
    require(value['state'] == 'SUPERVISED_PROJECTED_FINITE_OWNER_CLOSED'
            and value['childExited'] is True and value['volumeMayClose'] is True
            and value['finiteWorkExecuted'] is True and value['fullD3BAccepted'] is False
            and value['observedAfterUnknown'] is False, 'accept_finite_supervisor_close')
    require(type(value['pid']) is int and value['pid'] > 0
            and type(value['childStartTicks']) is int and value['childStartTicks'] > 0
            and type(value['stderrBytes']) is int and 0 <= value['stderrBytes'] <= 65536
            and all(_sha(value[name]) for name in ('inputSha256', 'stdoutSha256', 'stderrSha256')),
            'accept_finite_supervisor_identity')
    owner = validate_result(value['owner'], work=WORK, pid=value['pid'], previous_epoch=1)
    require(hashlib.sha256(canonical(owner) + b'\n').hexdigest() == value['stdoutSha256'],
            'accept_finite_owner_output_binding')
    return copy.deepcopy(value)


def validate_caller(value, manifest_sha):
    require(type(value) is dict and value.get('kind') == 'R156A1_SAME_IMAGE_SEED_FINITE'
            and value.get('result') == 'PASS' and value.get('state') == 'SAME_IMAGE_SEED_FINITE_CLOSED'
            and value.get('manifestSha256') == manifest_sha and _sha(manifest_sha),
            'accept_finite_caller_identity')
    require(all(value.get(name) is True for name in (
        'projectedFiniteAccepted', 'sameImageSeedAndFinite', 'sameOriginalSupervisor',
        'allOwnedChildrenTerminal', 'hostMountNamespaceUnchanged', 'hostMountTableUnchanged',
        'brokerMetadataFixtureOnly', 'finiteWorkExecuted')), 'accept_finite_caller_close')
    require(all(value.get(name) is False for name in (
        'realBrokerExchangeAccepted', 'serviceStarted', 'runtimeAdmissionAuthorized',
        'fullD3BAccepted', 'm1Accepted', 'productionReady', 'automaticCleanup', 'automaticRetry')),
        'accept_finite_caller_excluded_scope')
    require(all(type(value.get(name)) is int and value[name] == count for name, count in (
        ('executedTasks', 3), ('scriptedModelInvocations', 3), ('realModelCalls', 0),
        ('realProviderCalls', 0))), 'accept_finite_caller_work_scope')
    seed = value.get('seedResult')
    installed = value.get('installation')
    require(type(seed) is dict and seed.get('installationReceiptSha256') == INSTALLATION_RECEIPT_SHA
            and seed.get('harnessCommit') == HARNESS_COMMIT and seed.get('previousEpoch') == 1
            and type(installed) is dict and installed.get('receiptSha256') == INSTALLATION_RECEIPT_SHA
            and installed.get('harnessCommit') == HARNESS_COMMIT
            and installed.get('destination') == '/opt/alaz-r156a1'
            and installed.get('verifiedInstalledBytesNow') is True,
            'accept_finite_installed_binding')
    finite = validate_supervised(value.get('finite'))
    observations = value.get('observations')
    child = observations.get('retained') if type(observations) is dict else None
    require(type(child) is dict and child.get('phase') == 'COMPLETED'
            and child.get('pid') == finite['pid'] and child.get('startTicks') == finite['childStartTicks']
            and type(child.get('exitCode')) is int and child['exitCode'] == 0
            and child.get('complete') is True and child.get('overflowed') is False
            and type(child.get('inputWritten')) is int and 0 < child['inputWritten'] <= 65536
            and child.get('payloadSha256') == finite['inputSha256'],
            'accept_finite_original_child_observation')
    import base64
    for name in ('stdout', 'stderr'):
        row = child.get(name)
        require(type(row) is dict and set(row) == {'bytes', 'sha256', 'base64'}
                and type(row['bytes']) is int and 0 <= row['bytes'] <= 65536
                and type(row['base64']) is str and len(row['base64']) <= 87384,
                'accept_finite_observed_output_fields')
        try:
            raw = base64.b64decode(row['base64'], validate=True)
        except (ValueError, UnicodeError):
            raise FiniteProtocolRejected('accept_finite_observed_output_encoding') from None
        require(base64.b64encode(raw).decode('ascii') == row['base64']
                and len(raw) == row['bytes'] and hashlib.sha256(raw).hexdigest() == row['sha256']
                and row['sha256'] == finite[name + 'Sha256'], 'accept_finite_observed_output_binding')
        if name == 'stdout':
            require(raw == canonical(finite['owner']) + b'\n', 'accept_finite_original_owner_frame')
        else:
            require(len(raw) == finite['stderrBytes'], 'accept_finite_stderr_count')
    closure = value.get('closure')
    finish = closure.get('finish') if type(closure) is dict else None
    require(type(finish) is dict and finish.get('state') == 'CLOSED'
            and all(finish.get(name) is True for name in (
                'ownedUsersGone', 'loopAttachmentGone', 'fenceRemovedAfterCleanup', 'leaseReleasedLast')),
            'accept_finite_original_volume_close')
    return copy.deepcopy(value)
