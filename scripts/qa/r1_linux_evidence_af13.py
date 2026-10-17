"""Read-only corroboration of fresh Linux broker fixtures and R1 evidence views.

Never starts a Gateway, model, tool or container. Native experiments must already
have completed. Only metadata and private CLI input files are written in a fresh
separate output directory. Clock/retention and source stores are never changed.
Docker inspection is explicitly read-only and limited to retained exact IDs.
"""
from __future__ import annotations
import argparse
from contextlib import closing
from dataclasses import asdict, replace
import hashlib
import json
import re
from pathlib import Path
import sqlite3
import subprocess
import sys
import time

CASES = {'normal': (2, 1, 'completed'), 'provider-limit': (1, 1, 'failed'),
         'upstream-disconnect': (1, 0, 'failed')}
MAX_FILE_BYTES = 8 * 1024 * 1024


def require(value, code):
    if not value:
        raise ValueError(code)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read_object(path):
    require(path.is_file() and not path.is_symlink() and path.stat().st_size <= MAX_FILE_BYTES,
            'invalid_input_file')
    data = json.loads(path.read_text(encoding='utf-8'))
    require(type(data) is dict, 'invalid_input_object')
    return data


def snapshot(root):
    result = {}
    for path in sorted(root.rglob('*')):
        require(not path.is_symlink(), 'fixture_symlink_refused')
        if path.is_file():
            with path.open('rb') as stream:
                result[path.relative_to(root).as_posix()] = hashlib.file_digest(stream, 'sha256').hexdigest()
    return result


def readonly(path):
    require(path.is_file() and not path.is_symlink(), 'missing_database')
    db = sqlite3.connect(path.as_uri() + '?mode=ro', uri=True)
    db.execute('PRAGMA query_only=ON')
    return db


def no_authority(report):
    require(all(report[name] is False for name in
                ('writesPerformed', 'executionAllowed', 'retryAllowed', 'repairAllowed')),
            'report_grants_authority')
    require(report['evidenceView']['grantsExecutionPermission'] is False,
            'view_grants_authority')


def private_json(path, data):
    with path.open('x', encoding='utf-8') as stream:
        json.dump(data, stream, ensure_ascii=False)
    path.chmod(0o600)


def check_case(root, code_root, output, case, inspect_containers):
    from recovery_inspector import LocalRecoveryContext, RESULT, _load, _json, PIN
    from execution_budget import ExecutionPolicy
    from host_report import HostReportInspector
    from evidence_view import EvidenceViewInspector, EvidenceSelection, render_evidence_text

    directory = root / case
    record = read_object(directory / 'broker-native-result.json')
    require(record['scenario'] == case and record['source_commit'] == PIN,
            'wrong_native_identity')
    require(record['result'] == 'PASS' and record['errors'] == [] and record['source_drift'] == [],
            'native_not_qualified')
    require(record['gateway_exit'] == record['broker_exit'] == 0, 'unclean_native_exit')
    require(not record.get('forced_gateway_cleanup') and not record.get('forced_broker_cleanup'),
            'forced_cleanup_not_graceful')
    require(all(sha((code_root / path).read_bytes()) == digest
                for path, digest in record['programs'].items()), 'native_code_mismatch')
    before = snapshot(directory)
    home = directory / 'profile'
    cfg = read_object(home / 'config.yaml')
    token = cfg['platforms']['api_server']['key']
    settings = cfg['plugins']['entries']['alaz-host-gate']['settings']['execution']
    policy = ExecutionPolicy(**settings['policy'])
    with closing(readonly(home / 'state.db')) as db:
        epoch, instance = db.execute('SELECT epoch,instance_id FROM runtime_epoch WHERE singleton=1').fetchone()
        require(db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok', 'native_integrity_failed')
        claims = [_load(row[0]) for row in db.execute(
            "SELECT value FROM state_meta WHERE key LIKE 'alaz.execution.claim.v1.%'")]
        grants = [_load(row[0]) for row in db.execute(
            "SELECT value FROM state_meta WHERE key LIKE 'alaz.execution.egress.v1.%'")]
    context = LocalRecoveryContext(home, token, epoch, instance)
    run = record['client']['runId']
    observed = record['client']['final']['run']
    with closing(readonly(home / 'runs_idempotency.db')) as db:
        rows = db.execute('SELECT idempotency_key FROM run_idempotency WHERE scope=? AND run_id=?',
                          (context.scope, run)).fetchall()
    require(len(rows) == 1, 'ambiguous_request')
    request = {'body': {'input': 'Use the indicated file tool and report its result.', 'model': 'alaz-scripted'},
               'idempotency_key': rows[0][0], 'observed': observed}
    inspector = EvidenceViewInspector(context, policy)
    legacy = HostReportInspector(context, policy).inspect(**request)
    report = inspector.inspect(**request)
    require(report['reportStatus'] == 'verified_snapshot', 'fresh_report_unverified')
    without = dict(report)
    section = without.pop('evidenceView')
    require(without == legacy, 'legacy_report_changed')
    require(section['available'] and section['modelVisibility'] == 'unknown', 'unproven_visibility')
    no_authority(report)
    with closing(readonly(home / 'state.db')) as db:
        saved = _load(db.execute('SELECT value FROM state_meta WHERE key=?',
                                (RESULT + observed['admission_id'],)).fetchone()[0])
    require(section['recordDigest'] == sha(_json(saved).encode()), 'terminal_record_digest_mismatch')
    messages = saved['result'].get('messages', [])
    require(type(messages) is list, 'unsupported_native_messages')
    tools = [message for message in messages if message['role'] == 'tool']
    refs = [ref for ref in section['references'] if ref['kind'] == 'retained_tool_result']
    expected_provider, expected_tool, expected_status = CASES[case]
    providers = [claim for claim in claims if claim['kind'] == 'provider']
    reads = [claim for claim in claims if claim['kind'] == 'read_file']
    require(len(providers) == len(grants) == record['origin_accepted'] == expected_provider,
            'provider_counts_disagree')
    require(len(reads) == len(record['bindings']) == expected_tool, 'read_counts_disagree')
    require(report['task']['nativeStatus'] == expected_status, 'native_task_misclassified')
    require(report['task']['taskSucceeded'] is (case == 'normal'), 'failed_task_promoted')
    require(len(tools) == len(refs) == expected_tool, 'stored_tool_count_mismatch')
    for ref in section['references']:
        require(ref['modelView']['status'] == 'unknown' and ref['modelView']['ranges'] is None
                and ref['modelView']['understandingVerified'] is False,
                'invented_wire_or_understanding')
        require(ref['originalSource']['sha256'] is None and ref['originalSource']['coverage'] == 'unknown',
                'invented_source_capture')
        require(ref['executionAttribution'] == 'not_proven' and ref['claimTruthVerified'] is False,
                'invented_effect_or_truth')
    for message, ref in zip(tools, refs):
        raw = message['content'].encode('utf-8')
        require(ref['content']['sha256'] == sha(raw) and ref['content']['utf8Bytes'] == len(raw),
                'tool_output_bytes_mismatch')
    source_checks = []
    for binding in record['bindings']:
        require(binding['runId'] == run and binding['admissionId'] == observed['admission_id']
                and binding['executionGeneration'] == observed['execution_generation'],
                'binding_wrong_execution')
        require(binding['exited'] is True and binding['removed'] is True and binding['outcome'] == 'completed',
                'binding_incomplete')
        ticket = binding['ticket']
        require(re.fullmatch(r'[a-f0-9]{32}', ticket) is not None, 'invalid_ticket')
        captured = list((directory / 'capsules').glob('*/input-' + ticket + '.txt'))
        require(len(captured) == 1, 'missing_or_ambiguous_capsule')
        source = (directory / 'input.txt').read_bytes()
        require(sha(captured[0].read_bytes()) == sha(source) == binding['inputDigest'],
                'source_capsule_mismatch')
        container_id = binding['containerId']
        require(re.fullmatch(r'[a-f0-9]{64}', container_id) is not None, 'invalid_container_id')
        absent = None
        if inspect_containers:
            command = subprocess.run(['sudo', '-n', '/usr/bin/docker', 'inspect', container_id],
                                     capture_output=True, text=True, timeout=10)
            absent = command.returncode == 1 and 'no such' in command.stderr.lower()
            require(absent, 'container_absence_not_verified')
        source_checks.append({'sourceSha256': sha(source), 'sourceBytes': len(source),
                              'capsuleBytesMatch': True, 'containerAbsent': absent,
                              'basis': 'separate_operator_QA_not_product_EvidenceRef'})
    require(not Path(record['broker_ready']['socketPath']).exists(), 'broker_socket_remains')
    require(record['broker_shutdown']['activeRequests'] == 0, 'broker_requests_remain')
    if case == 'normal':
        require(record['explicit_same_grant_replay']['refused'] is True
                and record['explicit_same_grant_replay']['extra_origin_requests'] == 0,
                'same_grant_replayed')
    if case == 'upstream-disconnect':
        require(providers[0]['state'] == 'reserved' and providers[0]['usage'] is None,
                'lost_response_refunded_or_invented_usage')
        require(report['execution']['providerAttempts']['usageUnknown'] == 1,
                'unknown_usage_hidden')
    own = output / case
    own.mkdir()
    private = own / 'private'
    private.mkdir(mode=0o700)
    values = asdict(context)
    values['profile_home'] = str(values['profile_home'])
    values.pop('profile_name')
    for name, data in [('context', values), ('policy', asdict(policy)), ('request', request)]:
        private_json(private / (name + '.json'), data)
    command = [sys.executable, '-B', str(code_root / 'scripts/inspect_host_report.py'),
               '--context', str(private / 'context.json'), '--policy', str(private / 'policy.json'),
               '--request', str(private / 'request.json'), '--include-evidence']
    cli = subprocess.run(command, capture_output=True, text=True, encoding='utf-8', timeout=15)
    require(cli.returncode == 0 and not cli.stderr and json.loads(cli.stdout) == report, 'cli_json_mismatch')
    text = subprocess.run(command + ['--format', 'text'], capture_output=True, text=True,
                          encoding='utf-8', timeout=15)
    require(text.returncode == 0 and not text.stderr and text.stdout == render_evidence_text(report),
            'cli_text_mismatch')
    selections = []
    if refs:
        ref = refs[0]
        raw = tools[0]['content'].encode('utf-8')
        first = len(tools[0]['content'][0].encode('utf-8'))
        require(0 < first < len(raw), 'fixture_not_splittable')
        for label, end in [('partial', first), ('complete', len(raw))]:
            selection = EvidenceSelection(ref['evidenceId'], ref['content']['sha256'], 0, end)
            view = inspector.inspect(**request, selection=selection)
            local = view['evidenceView']['localView']
            require(local['status'] == 'computed_locally_not_dispatched'
                    and local['coverageOfStoredContent'] == label
                    and local['modelVisibility'] == local['originalSourceCoverage'] == 'unknown'
                    and local['contentSha256'] == sha(raw[:end]), 'local_selection_promoted')
            private_json(private / (label + '.json'), asdict(selection))
            result = subprocess.run(command + ['--evidence-selection', str(private / (label + '.json'))],
                                    capture_output=True, text=True, encoding='utf-8', timeout=15)
            require(result.returncode == 0 and json.loads(result.stdout) == view, 'selection_cli_mismatch')
            (own / (label + '-report.json')).write_text(json.dumps(view, indent=2) + '\n', encoding='utf-8')
            selections.append({'coverage': label, 'bytes': end, 'cliExit': result.returncode})
    negatives = []
    wrong_context = EvidenceViewInspector(replace(context, api_token='wrong-private-test-token'), policy)
    old_context = EvidenceViewInspector(replace(context, epoch=context.epoch + 1), policy)
    variants = [
        ('wrong_bearer', wrong_context.inspect(**request)),
        ('wrong_owner_generation', old_context.inspect(**request)),
        ('wrong_request', inspector.inspect(**(request | {'body': request['body'] | {'input': 'not the admitted request'}}))),
        ('wrong_run', inspector.inspect(**(request | {'observed': observed | {'run_id': 'run_' + 'f' * 32}}))),
    ]
    if refs:
        ref = refs[0]
        variants += [
            ('wrong_content_digest', inspector.inspect(**request, selection=EvidenceSelection(
                ref['evidenceId'], '0' * 64, 0, 1))),
            ('range_beyond_stored_output', inspector.inspect(**request, selection=EvidenceSelection(
                ref['evidenceId'], ref['content']['sha256'], 0, ref['content']['utf8Bytes'] + 1))),
        ]
    for name, denied in variants:
        require(denied['evidenceView']['available'] is False and denied['evidenceView']['references'] == [],
                'negative_control_exposed_evidence_' + name)
        no_authority(denied)
        negatives.append({'name': name, 'result': 'REFUSED_AS_EXPECTED',
                          'reason': denied['evidenceView']['reason']})
    forged = inspector.inspect(**(request | {'observed': observed | {
        'evidenceView': {'modelVisibility': 'confirmed'}, 'originalSourceCoverage': 'complete'}}))
    require(forged == report, 'observer_metadata_promoted')
    public = json.dumps(report) + cli.stdout + text.stdout
    for secret in (token, str(home), settings['provider_bearer'], request['idempotency_key'],
                   request['body']['input'], observed.get('output', '')):
        require(not secret or secret not in public, 'private_value_in_report')
    after = snapshot(directory)
    differences = {name: {'before': before.get(name), 'after': after.get(name)}
                   for name in before.keys() | after.keys() if before.get(name) != after.get(name)}
    (own / 'read-only-diff.json').write_text(json.dumps({'before': before, 'after': after,
        'differences': differences}, indent=2) + '\n', encoding='utf-8')
    require(before == after, 'native_evidence_changed_during_readonly_check')
    (own / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (own / 'report.txt').write_text(text.stdout, encoding='utf-8')
    return {'scenario': case, 'result': 'PASS', 'nativeStatus': expected_status,
            'providers': expected_provider, 'isolatedReads': expected_tool,
            'evidenceReferences': len(section['references']), 'toolOutputBytes': [r['content']['utf8Bytes'] for r in refs],
            'recordMembershipVerified': True, 'sourceCoverageInProduct': 'unknown',
            'modelVisibilityInProduct': 'unknown', 'modelUnderstandingVerified': False,
            'sourceCorroboration': source_checks, 'selections': selections, 'negativeControls': negatives,
            'forgedObserverMetadataIgnored': True, 'nativeFilesUnchanged': len(before),
            'nativeManifestSha256': sha(json.dumps(before, sort_keys=True).encode()),
            'nativeReceiptSha256': before['broker-native-result.json'],
            'cliJsonExit': cli.returncode, 'cliTextExit': text.returncode,
            'newGatewayRunsDuringInspection': 0, 'newModelCallsDuringInspection': 0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--code-root', type=Path, required=True)
    parser.add_argument('--native-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--inspect-containers', action='store_true')
    args = parser.parse_args()
    code_root, root, output = args.code_root.resolve(), args.native_root.resolve(), args.output.resolve()
    require(not output.exists() and output != root and not output.is_relative_to(code_root)
            and all(not output.is_relative_to(root / name) for name in CASES), 'fresh_separate_output_required')
    sys.path.insert(0, str(code_root / 'packages/claw-hermes'))
    source_before = snapshot(code_root)
    output.mkdir(parents=True, mode=0o700)
    results, errors = [], []
    for case in CASES:
        try:
            row = check_case(root, code_root, output, case, args.inspect_containers)
            results.append(row)
            print(json.dumps(row), flush=True)
        except Exception as exc:
            # Error text is a fixed local check code or type, never provider/private text.
            reason = str(exc) if isinstance(exc, ValueError) and re.fullmatch(r'[a-z_]{1,100}', str(exc)) else type(exc).__name__
            errors.append({'scenario': case, 'reason': reason})
            print(json.dumps(errors[-1]), flush=True)
    changed = source_before != snapshot(code_root)
    summary = {'scope': 'R1 metadata/CLI on three already-completed fresh native Linux Gateway/broker stores; not three additional runs',
               'productBaseCommit': 'b96a83f545ae12885f025ee0085cb018dad14511',
               'observedAtUnix': time.time(), 'checks': results, 'errors': errors,
               'sourceChanged': changed, 'modelInferenceCalls': 0, 'paidCalls': 0,
               'sourceManifestSha256': sha(json.dumps(source_before, sort_keys=True).encode()),
               'result': 'PASS' if len(results) == len(CASES) and not errors and not changed else 'FAIL'}
    (output / 'verification.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
    return 0 if summary['result'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
