"""R1: metadata-only evidence views over an existing native terminal record.

One existing recovery/ledger snapshot; no new persistence, file opening by model
paths, provider calls, or dispatch permission. A retained transcript is not a
provider wire manifest, a source-file capture, or independent proof of an effect.
"""
from __future__ import annotations
from dataclasses import dataclass
import hashlib
import re
from host_report import HostReportInspector, unavailable_report, render_text
from recovery_inspector import EvidenceError, RESULT, _load, _json

_MAX_MESSAGES = 1024
_MAX_REFERENCES = 256
_MAX_BYTES = 2_097_152


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _require(condition: bool, reason: str) -> None:
    if not condition:
        raise EvidenceError(reason)


@dataclass(frozen=True)
class EvidenceSelection:
    """A local metadata view request, never a provider dispatch or capability."""
    evidence_id: str
    content_sha256: str
    start_byte: int
    end_byte: int

    def __post_init__(self):
        _require(type(self.evidence_id) is str and
                 re.fullmatch(r'ev_[a-f0-9]{64}', self.evidence_id) is not None,
                 'invalid_evidence_selection')
        _require(type(self.content_sha256) is str and
                 re.fullmatch(r'[a-f0-9]{64}', self.content_sha256) is not None,
                 'invalid_evidence_selection')
        _require(type(self.start_byte) is int and type(self.end_byte) is int and
                 0 <= self.start_byte <= self.end_byte <= _MAX_BYTES,
                 'invalid_evidence_range')


def unavailable_evidence(reason: str) -> dict:
    # Never carry arbitrary exception/provider/user text into the host report.
    if type(reason) is not str or (reason != 'split_utf8_boundary' and
                                   re.fullmatch(r'[a-z_]{1,80}', reason) is None):
        reason = 'evidence_unavailable'
    return {'evidenceViewVersion': 1, 'status': 'unavailable', 'reason': reason,
            'available': False, 'references': [], 'localView': None,
            'modelVisibility': 'unknown', 'writesPerformed': False,
            'grantsExecutionPermission': False, 'goalAchievementVerified': False}


def _pairing(messages: list) -> dict:
    """Structural correspondence ONLY; no current-run execution attribution."""
    calls, results = {}, {}
    for index, message in enumerate(messages):
        if message.get('role') == 'assistant':
            raw = message.get('tool_calls', [])
            if raw is None:
                raw = []
            _require(type(raw) is list and len(raw) <= _MAX_REFERENCES,
                     'unsupported_tool_call_shape')
            for call in raw:
                _require(type(call) is dict, 'unsupported_tool_call_shape')
                key = call.get('id')
                if type(key) is str and 0 < len(key) <= 256:
                    calls.setdefault(key, []).append(index)
        elif message.get('role') == 'tool':
            key = message.get('tool_call_id')
            if type(key) is str and 0 < len(key) <= 256:
                results.setdefault(key, []).append(index)
    paired = {}
    for index, message in enumerate(messages):
        if message.get('role') != 'tool':
            continue
        key = message.get('tool_call_id')
        if type(key) is not str or not 0 < len(key) <= 256:
            paired[index] = 'missing_or_invalid_id'
        elif len(calls.get(key, [])) > 1 or len(results.get(key, [])) > 1:
            paired[index] = 'ambiguous_id'
        elif len(calls.get(key, [])) != 1 or calls[key][0] >= index:
            paired[index] = 'no_preceding_call'
        else:
            paired[index] = 'structurally_paired_not_execution_proof'
    return paired


def _record_projection(record: dict, checked: dict, context, selection) -> dict:
    value = record['result']
    _require(type(value) is dict, 'unsupported_terminal_evidence')
    record_digest = _sha(_json(record).encode('utf-8'))
    messages = value.get('messages')
    if messages is not None:
        _require(type(messages) is list and len(messages) <= _MAX_MESSAGES,
                 'unsupported_message_history')
        _require(all(type(m) is dict for m in messages), 'unsupported_message_history')
    pairs = _pairing(messages) if messages is not None else {}
    # Only known record fields. Text is hashed as opaque UTF-8, never parsed as
    # proof metadata or opened as a local path. Historical suffix flags are ignored.
    items = []
    if messages is not None:
        for index, message in enumerate(messages):
            if message.get('role') == 'tool':
                items.append(('retained_tool_result', index, message.get('content'), pairs[index]))
    _require(len(items) + 1 <= _MAX_REFERENCES, 'too_many_evidence_references')
    items.append(('native_final_response', None, value.get('final_response'), 'not_applicable'))
    identity = {'profileBinding': context.binding, 'scope': context.scope,
                'runId': checked['runId'], 'sessionId': checked['sessionId'],
                'admissionId': checked['admissionId'],
                'executionGeneration': checked['executionGeneration'],
                'recordDigest': record_digest}
    refs, selected = [], None
    for kind, index, content, pairing in items:
        raw = content.encode('utf-8') if type(content) is str else None
        _require(raw is None or len(raw) <= _MAX_BYTES, 'evidence_content_too_large')
        sha = _sha(raw) if raw is not None else None
        eid = 'ev_' + _sha(_json(dict(identity, kind=kind, index=index,
                                     contentSha256=sha)).encode('utf-8'))
        ref = {'evidenceId': eid, 'kind': kind, 'messageIndex': index,
               'source': 'native_terminal_record', 'recordMembershipVerified': True,
               'content': {'availability': 'retained' if raw is not None else 'not_retained_as_text',
                           'sha256': sha, 'digestBasis': 'stored_content_utf8' if raw is not None else None,
                           'utf8Bytes': len(raw) if raw is not None else None},
               'pairing': pairing, 'executionAttribution': 'not_proven',
               'originalSource': {'sha256': None, 'coverage': 'unknown', 'availability': 'unknown'},
               'modelView': {'status': 'unknown', 'requestDigest': None, 'ranges': None,
                             'understandingVerified': False},
               'claimTruthVerified': False, 'grantsExecutionPermission': False}
        refs.append(ref)
        if selection is not None and selection.evidence_id == eid:
            _require(raw is not None, 'evidence_content_unavailable')
            _require(selection.content_sha256 == sha, 'evidence_digest_mismatch')
            start, end = selection.start_byte, selection.end_byte
            _require(end <= len(raw) and (start < end or len(raw) == 0), 'invalid_evidence_range')
            # Boundaries are UTF-8 bytes, not characters or platform newlines.
            try:
                raw[:start].decode('utf-8'); raw[start:end].decode('utf-8')
            except UnicodeError:
                raise EvidenceError('split_utf8_boundary') from None
            selected = {'evidenceId': eid, 'status': 'computed_locally_not_dispatched',
                        'range': {'unit': 'utf8_bytes', 'start': start, 'end': end, 'endExclusive': True},
                        'contentSha256': _sha(raw[start:end]), 'utf8Bytes': end-start,
                        'coverageOfStoredContent': 'complete' if start == 0 and end == len(raw) else 'partial',
                        'originalSourceCoverage': 'unknown', 'modelVisibility': 'unknown',
                        'payloadIncluded': False, 'grantsExecutionPermission': False}
    _require(selection is None or selected is not None, 'evidence_reference_unavailable')
    return {'evidenceViewVersion': 1, 'status': 'verified_record_snapshot', 'available': True,
            'inventoryScope': 'retained_tool_text_and_final_response',
            'recordDigest': record_digest, 'recordDigestBasis': 'canonical_current_terminal_record_json',
            'historyAvailability': 'not_recorded' if messages is None else 'retained',
            'historyCompleteness': 'not_proven', 'references': refs, 'localView': selected,
            'modelVisibility': 'unknown', 'writesPerformed': False,
            'grantsExecutionPermission': False, 'goalAchievementVerified': False,
            'warnings': ['record_membership_is_not_independent_content_verification',
                         'retained_text_is_not_original_file_coverage',
                         'no_provider_request_view_manifest',
                         'historical_tool_messages_not_attributed_to_this_execution']}


class _EvidenceSnapshot(HostReportInspector):
    """A fresh instance per call; no mutable selection shared between readers."""
    def __init__(self, context, policy, *, clock, selection):
        super().__init__(context, policy, clock=clock)
        self.selection = selection

    def _classify(self, conn, row, reservation, saved, body, http, target):
        checked = super()._classify(conn, row, reservation, saved, body, http, target)
        report = checked['_report']
        if checked.get('classification') != 'canonical_terminal_verified':
            report['evidenceView'] = unavailable_evidence('terminal_record_not_verified')
            report['reportStatus'] = 'partial_snapshot'
            return checked
        try:
            record = conn.execute('SELECT value FROM state_meta WHERE key=?',
                                  (RESULT + checked['admissionId'],)).fetchone()
            _require(record is not None, 'terminal_evidence_missing')
            section = _record_projection(_load(record[0]), checked, self.context, self.selection)
        except EvidenceError as exc:
            section = unavailable_evidence(str(exc))
        except (ValueError, TypeError, KeyError, IndexError, UnicodeError, OverflowError, RecursionError):
            section = unavailable_evidence('malformed_terminal_evidence')
        report['evidenceView'] = section
        if not section['available']:
            report['reportStatus'] = 'partial_snapshot'
        return checked


class EvidenceViewInspector(HostReportInspector):
    """Opt-in read-only extension; the legacy HostReportInspector is unchanged."""
    def inspect(self, *, body: dict, idempotency_key: str, observed: dict,
                selection: EvidenceSelection | None = None) -> dict:
        if selection is not None and type(selection) is not EvidenceSelection:
            report = unavailable_report('invalid_evidence_selection')
        else:
            report = _EvidenceSnapshot(self.context, self.policy, clock=self.clock,
                                       selection=selection).inspect(
                body=body, idempotency_key=idempotency_key, observed=observed)
        if 'evidenceView' not in report:
            report['evidenceView'] = unavailable_evidence(report.get('reason', 'evidence_unavailable'))
        return report

    def inspect_scope(self) -> dict:
        report = super().inspect_scope()
        report['evidenceView'] = unavailable_evidence('no_task_selected')
        return report


def render_evidence_text(report: dict) -> str:
    lines = [render_text(report).rstrip('\n')]
    section = report.get('evidenceView', unavailable_evidence('not_requested'))
    lines += ['Evidence: ' + section['status'],
              'Model-visible ranges: UNKNOWN (no provider request view manifest).']
    if section['available']:
        lines.append('Retained text references: ' + str(len(section['references'])))
        for ref in section['references']:
            content = ref['content']; size = content['utf8Bytes']
            lines.append(ref['evidenceId'] + ' ' + ref['kind'] + ' stored UTF-8 bytes=' +
                         ('UNKNOWN' if size is None else str(size)) + '; original source coverage=UNKNOWN')
        view = section['localView']
        if view is not None:
            lines.append('Local metadata view: ' + view['coverageOfStoredContent'] +
                         '; NOT DISPATCHED; bytes=' + str(view['utf8Bytes']))
    else:
        lines.append('Evidence reason: ' + section['reason'])
    lines.append('Retained content and local views do NOT verify an effect, comprehension or goal.')
    return '\n'.join(lines) + '\n'
