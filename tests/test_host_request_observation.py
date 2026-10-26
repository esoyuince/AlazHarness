"""Request locator regressions using real SQLite and actual host route code.

The owner and API adapter are synthetic. HTTP handler tests patch only native
source qualification and use aiohttp's mocked requests; no listener, native
Gateway, provider, or production profile is started. These tests do not qualify
the old host source lock for the retained d151 runtime.
"""
from __future__ import annotations

from contextlib import closing
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT_PATH = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_PATH / 'packages/claw-hermes'))
sys.path.insert(0, str(ROOT_PATH / 'tests'))

from host_gate import HostGateError, HostGateLedger
import host_gate_plugin
from test_host_gate_qa import GateFixture

try:
    from aiohttp import web
    from aiohttp.test_utils import make_mocked_request
except ImportError:
    web = None
    make_mocked_request = None


class ObservationFixture(GateFixture):
    """Native replay columns in a temporary SQLite fixture, not native code."""

    def __init__(self, home):
        super().__init__(home)
        self.sql('DROP TABLE run_idempotency', replay=True)
        self.sql('''CREATE TABLE run_idempotency (
            scope TEXT NOT NULL, idempotency_key TEXT NOT NULL,
            fingerprint TEXT NOT NULL, run_id TEXT NOT NULL,
            status_json TEXT NOT NULL, owner_pid INTEGER NOT NULL DEFAULT 0,
            owner_started INTEGER NOT NULL DEFAULT 0,
            retention_until REAL NOT NULL DEFAULT 0, acknowledged_at REAL,
            created_at REAL NOT NULL, updated_at REAL NOT NULL,
            PRIMARY KEY(scope,idempotency_key))''', replay=True)
        self.run_id = 'run_' + 'b' * 32

    def reserve(self, document, *, scope=None, run_id=None):
        rid = run_id or self.run_id
        status = {'run_id': rid, 'status': 'running',
                  'output': 'private-native-output', 'usage': {'total_tokens': 123}}
        self.sql('''INSERT INTO run_idempotency
            (scope,idempotency_key,fingerprint,run_id,status_json,created_at,updated_at)
            VALUES(?,?,?,?,?,?,?)''',
            (self.context.scope if scope is None else scope, document['key'],
             document['fingerprint'], rid, json.dumps(status), self.now, self.now),
            replay=True)

    def accepted(self):
        document = self.issue()
        self.consume(document)
        self.reserve(document)
        return document

    def hashes(self):
        return {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                for p in self.home.iterdir() if p.is_file()}


class HostRequestObservationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.f = ObservationFixture(temporary.name)

    def observe(self, request_id=None):
        return self.f.service.observe(self.f.rid if request_id is None else request_id)

    def assert_contract(self, value, classification, state=None, run_id=None, request_id=None):
        actions = {
            'not_found': 'retain_request_id_no_retry',
            'issued_not_dispatched': 'retain_issued_request_no_retry',
            'handoff_unresolved': 'retain_consumed_request_no_retry',
            'native_run_located': 'observe_existing_run',
        }
        self.assertEqual(value, {
            'hostGateVersion': 1, 'requestObservationVersion': 1,
            'requestId': self.f.rid if request_id is None else request_id,
            'classification': classification, 'dispatchState': state, 'runId': run_id,
            'snapshotOnly': True, 'writesPerformed': False, 'canonicalVerified': False,
            'retryAllowed': False, 'repairAllowed': False,
            'requiresOperator': classification != 'native_run_located',
            'nextAction': actions[classification],
        })

    def rejected(self, operation=None):
        before = self.f.hashes()
        with self.assertRaises(HostGateError) as raised:
            (self.observe if operation is None else operation)()
        self.assertRegex(str(raised.exception), r'^[a-z_]{1,80}$')
        self.assertEqual(before, self.f.hashes())

    def test_absent_namespace_does_not_create_records_or_files(self):
        before = self.f.hashes()
        self.assert_contract(self.observe(), 'not_found')
        self.assertEqual(before, self.f.hashes())
        self.assertEqual(self.f.rows(), [])

    def test_issued_intent_and_another_missing_id_are_observations_only(self):
        self.f.issue()
        before = self.f.hashes()
        self.assert_contract(self.observe(), 'issued_not_dispatched', 'issued')
        other = 'c' * 32
        self.assert_contract(self.observe(other), 'not_found', request_id=other)
        self.assertEqual(before, self.f.hashes())

    def test_consumed_without_native_reservation_is_unresolved(self):
        self.f.consume(self.f.issue())
        self.assert_contract(self.observe(), 'handoff_unresolved', 'consumed')

    def test_independent_native_run_identity_is_located_without_private_fields(self):
        document = self.f.accepted()
        before = self.f.hashes()
        result = self.observe()
        self.assertNotEqual(self.f.run_id, 'run_' + self.f.rid)
        self.assert_contract(result, 'native_run_located', 'consumed', self.f.run_id)
        encoded = json.dumps(result)
        for private in (document['key'], document['fingerprint'], self.f.body['input'],
                        self.f.body['model'], self.f.context.api_token,
                        'private-native-output', str(self.f.home)):
            self.assertNotIn(private, encoded)
        self.assertEqual(before, self.f.hashes())

    def test_consumption_ack_loss_and_pruned_replay_never_grant_resend(self):
        document = self.f.issue()
        self.f.db.lose_ack = True
        with self.assertRaises(HostGateError):
            self.f.consume(document)
        self.f.db.lose_ack = False
        self.assert_contract(self.observe(), 'handoff_unresolved', 'consumed')
        self.f.reserve(document)
        self.assert_contract(self.observe(), 'native_run_located', 'consumed', self.f.run_id)
        self.f.sql('DELETE FROM run_idempotency', replay=True)
        self.assert_contract(self.observe(), 'handoff_unresolved', 'consumed')
        with self.assertRaises(HostGateError):
            self.f.consume(document)

    def test_no_writer_or_replay_helpers_and_connections_are_read_only_and_closed(self):
        self.f.accepted()
        original = sqlite3.connect
        opened, statements, connection_args = [], [], []

        def connect(*args, **kwargs):
            connection_args.append((args, kwargs))
            conn = original(*args, **kwargs)
            conn.set_trace_callback(statements.append)
            opened.append(conn)
            return conn

        with patch('host_gate.sqlite3.connect', connect), \
                patch.object(self.f.db, '_execute_write', side_effect=AssertionError('write')), \
                patch.object(self.f.service, 'issue', side_effect=AssertionError('issue')), \
                patch.object(self.f.service, 'consume', side_effect=AssertionError('consume')), \
                patch.object(self.f.service, '_history', side_effect=AssertionError('history')):
            self.assert_contract(self.observe(), 'native_run_located', 'consumed', self.f.run_id)
        self.assertTrue(opened)
        for args, kwargs in connection_args:
            self.assertIn('mode=ro', str(args[0]))
            self.assertIs(kwargs.get('uri'), True)
        for conn in opened:
            with self.assertRaises(sqlite3.ProgrammingError):
                conn.execute('SELECT 1')
        normalized = [statement.strip().upper() for statement in statements]
        self.assertTrue(any(re.match(r'PRAGMA\s+QUERY_ONLY\s*=\s*ON', s) for s in normalized))
        self.assertFalse(any(s.split()[0] in {'INSERT', 'UPDATE', 'DELETE', 'CREATE',
                                            'DROP', 'ALTER', 'REPLACE', 'VACUUM'}
                             for s in normalized if s))

    def test_missing_stores_are_not_recreated(self):
        self.f.accepted()
        for filename in ('state.db', 'runs_idempotency.db'):
            with self.subTest(filename=filename):
                path = self.f.home / filename
                saved = path.read_bytes()
                path.unlink()
                try:
                    self.rejected()
                    self.assertFalse(path.exists())
                finally:
                    path.write_bytes(saved)

    def test_corrupt_intent_digest_is_rejected(self):
        self.f.accepted()
        row = self.f.get(self.f.intent_key)
        row['fingerprint'] = 'f' * 64
        self.f.set(self.f.intent_key, row)
        self.rejected()

    def test_pruned_intent_or_false_inventory_counter_is_rejected(self):
        self.f.accepted()
        original = self.f.get(self.f.config_key)
        self.f.set(self.f.config_key, original | {'issued': 0})
        self.rejected()
        self.f.set(self.f.config_key, original)
        self.f.sql('DELETE FROM state_meta WHERE key=?', (self.f.intent_key,))
        self.rejected()

    def test_missing_namespace_over_retained_history_is_rejected(self):
        self.f.issue()
        self.f.sql('DELETE FROM state_meta WHERE key=?', (self.f.config_key,))
        self.rejected()

    def test_different_namespace_cannot_rebind_a_validly_sealed_intent(self):
        self.f.accepted()
        row = self.f.get(self.f.intent_key)
        row['key'] = 'ah1-' + 'd' * 32 + '-' + self.f.rid
        self.f.set(self.f.intent_key, self.f.service._seal(row))
        self.rejected()

    def test_native_fingerprint_or_run_identity_mismatch_is_rejected(self):
        document = self.f.accepted()
        for column, value in (
            ('fingerprint', 'f' * 64),
            ('run_id', 'not-a-run-id'),
            ('status_json', json.dumps({'run_id': 'run_' + 'd' * 32, 'status': 'running'})),
            ('status_json', '{"run_id":"private-invalid-json"'),
        ):
            with self.subTest(column=column, value=value):
                self.f.sql('DELETE FROM run_idempotency', replay=True)
                self.f.reserve(document)
                self.f.sql('UPDATE run_idempotency SET ' + column + '=?', (value,), replay=True)
                self.rejected()

    def test_duplicate_replay_identity_is_rejected(self):
        self.f.accepted()
        self.f.sql('ALTER TABLE run_idempotency RENAME TO previous_replay', replay=True)
        self.f.sql('CREATE TABLE run_idempotency AS SELECT * FROM previous_replay', replay=True)
        self.f.sql('INSERT INTO run_idempotency SELECT * FROM previous_replay', replay=True)
        self.rejected()

    def test_native_reservation_for_unconsumed_intent_is_inconsistent(self):
        self.f.reserve(self.f.issue())
        self.rejected()

    def test_foreign_scope_never_discloses_another_native_run(self):
        document = self.f.issue()
        self.f.consume(document)
        self.f.reserve(document, scope='f' * 64)
        self.assert_contract(self.observe(), 'handoff_unresolved', 'consumed')
        self.f.context = replace(self.f.context, api_token='other-fixture-bearer')
        self.f.service = self.f.new()
        self.assert_contract(self.observe(), 'not_found')

    def test_stale_owner_epoch_is_rejected(self):
        self.f.accepted()
        self.f.sql('UPDATE runtime_epoch SET epoch=2,instance_id=?', ('new-owner',))
        self.rejected()

    def test_concurrent_epoch_and_replay_changes_invalidate_snapshot(self):
        self.f.accepted()
        original = sqlite3.connect
        fixture = self.f

        for replay in (False, True):
            with self.subTest(replay=replay):
                fired = []

                class Changing(sqlite3.Connection):
                    def rollback(self):
                        super().rollback()
                        if not fired:
                            fired.append(True)
                            filename = 'runs_idempotency.db' if replay else 'state.db'
                            with closing(original(fixture.home / filename)) as writer:
                                if replay:
                                    writer.execute('UPDATE run_idempotency SET updated_at=updated_at+1')
                                else:
                                    writer.execute('UPDATE runtime_epoch SET epoch=epoch+1')
                                writer.commit()

                def connect(*args, **kwargs):
                    return original(*args, **kwargs, factory=Changing)

                with patch('host_gate.sqlite3.connect', connect):
                    with self.assertRaises(HostGateError) as raised:
                        self.observe()
                self.assertRegex(str(raised.exception), r'^[a-z_]{1,80}$')
                self.assertTrue(fired)
                fixture.sql("UPDATE runtime_epoch SET epoch=1,instance_id='first-owner'")

    def test_sql_read_denial_produces_only_a_bounded_error(self):
        self.f.accepted()
        original = sqlite3.connect

        def connect(*args, **kwargs):
            conn = original(*args, **kwargs)
            conn.set_authorizer(lambda action, name, *_: sqlite3.SQLITE_DENY
                                if action == sqlite3.SQLITE_READ and name == 'run_idempotency'
                                else sqlite3.SQLITE_OK)
            return conn

        with patch('host_gate.sqlite3.connect', connect):
            self.rejected()

    def test_replay_view_is_not_accepted_as_the_native_table(self):
        self.f.accepted()
        self.f.sql('ALTER TABLE run_idempotency RENAME TO original_replay', replay=True)
        self.f.sql('CREATE VIEW run_idempotency AS SELECT * FROM original_replay', replay=True)
        self.rejected()

    def test_invalid_request_id_is_rejected_before_database_access(self):
        with patch('host_gate.sqlite3.connect', side_effect=AssertionError('database opened')):
            for request_id in (None, 'a' * 31, 'A' * 32, '../state.db', 123, 'a' * 32 + '\n'):
                with self.subTest(request_id=request_id):
                    with self.assertRaises(HostGateError):
                        self.f.service.observe(request_id)

    def test_mutating_locator_does_not_change_the_retained_binding(self):
        self.f.accepted()
        before = self.f.hashes()
        response = self.observe()
        response['runId'] = 'run_' + 'e' * 32
        response['retryAllowed'] = True
        self.assert_contract(self.observe(), 'native_run_located', 'consumed', self.f.run_id)
        self.assertEqual(before, self.f.hashes())


@unittest.skipIf(web is None, 'aiohttp unavailable; HTTP handler qualification not run')
class HostRequestObservationRouteTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.f = ObservationFixture(temporary.name)
        self.f.accepted()
        self.native_calls = []

        def forbidden(*args, **kwargs):
            self.native_calls.append('forbidden')
            raise AssertionError('native handler/lookup must not run')

        self.adapter = SimpleNamespace(
            _host='127.0.0.1',
            _expected_api_key=lambda: self.f.context.api_token,
            _room_grant_token=lambda request: request.headers.get('X-Test-Room'),
            _handle_get_run=forbidden, _durable_run_status=forbidden,
            _handle_runs=forbidden,
            _run_idempotency_store=SimpleNamespace(lookup=forbidden, status_for_run=forbidden),
            gateway_runner=SimpleNamespace(
                session_authority=SimpleNamespace(db=self.f.db, epoch=1, retiring=False, retired=False),
                session_runtime_descriptor={'state': 'ready', 'instance_id': 'first-owner'}),
        )
        self.readiness_calls = []

        async def readiness():
            self.readiness_calls.append(True)
            raise AssertionError('observation must not initialize execution or ping broker')

        execution = SimpleNamespace(bind=lambda app, adapter: None, require_ready=readiness,
                                    broker=None, isolation=None)
        self.app = web.Application()
        with patch.object(host_gate_plugin, 'validate_native_adapter'):
            host_gate_plugin.bind_host_gate(self.app, self.adapter, self.f.policy, execution=execution)
        self.app.freeze()

    async def get(self, *, path=None, headers=None):
        if headers is None:
            headers = {'Authorization': 'Bearer ' + self.f.context.api_token}
        request = make_mocked_request(
            'GET', path or '/alaz/host/v1/requests/' + self.f.rid,
            headers=headers, app=self.app)
        response = await self.app._handle(request)
        return response.status, json.loads(response.text)

    async def test_route_uses_locator_without_execution_or_native_status_helpers(self):
        before = self.f.hashes()
        with patch.object(self.f.db, '_execute_write', side_effect=AssertionError('writer')):
            status, value = await self.get()
        self.assertEqual(status, 200)
        self.assertEqual(value['classification'], 'native_run_located')
        self.assertEqual(value['runId'], self.f.run_id)
        self.assertFalse(value['canonicalVerified'])
        self.assertEqual(self.readiness_calls, [])
        self.assertEqual(self.native_calls, [])
        self.assertEqual(before, self.f.hashes())

    async def test_route_authentication_precedes_storage_observation(self):
        auth = 'Bearer ' + self.f.context.api_token
        with patch.object(HostGateLedger, 'observe', side_effect=AssertionError('unauthenticated read')):
            for headers in ({}, {'Authorization': 'Bearer wrong'},
                            [('Authorization', auth), ('Authorization', auth)]):
                with self.subTest(headers=headers):
                    status, value = await self.get(headers=headers)
                    self.assertEqual(status, 401)
                    self.assertEqual(value['error']['code'], 'authentication_required')
                    self.assertFalse(value['retryAllowed'])

    async def test_query_session_and_room_scopes_are_rejected(self):
        auth = 'Bearer ' + self.f.context.api_token
        cases = [
            ('/alaz/host/v1/requests/' + self.f.rid + '?scope=other', {'Authorization': auth}),
            (None, {'Authorization': auth, 'X-Hermes-Session-Key': 'foreign'}),
            (None, {'Authorization': auth, 'X-Test-Room': 'foreign-room'}),
        ]
        with patch.object(HostGateLedger, 'observe', side_effect=AssertionError('foreign read')):
            for path, headers in cases:
                with self.subTest(path=path, headers=headers):
                    status, value = await self.get(path=path, headers=headers)
                    self.assertEqual(status, 409)
                    self.assertFalse(value['retryAllowed'])
                    self.assertIn(value['error']['code'],
                                  {'unsupported_host_header_or_query', 'unsupported_host_scope'})

    async def test_storage_error_and_invalid_identifier_do_not_leak_private_text(self):
        status, value = await self.get(path='/alaz/host/v1/requests/INVALID')
        self.assertEqual(status, 409)
        self.assertEqual(value['error']['code'], 'invalid_request_id')
        with patch.object(HostGateLedger, 'observe', side_effect=OSError('private-storage-secret')):
            status, value = await self.get()
        self.assertEqual(status, 503)
        self.assertEqual(value['error']['code'], 'host_gate_unavailable')
        self.assertNotIn('private-storage-secret', json.dumps(value))
        self.assertFalse(value['retryAllowed'])


if __name__ == '__main__':
    unittest.main()
