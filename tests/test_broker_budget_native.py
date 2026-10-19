"""Actual Linux broker IPC and loopback HTTP with broker-owned persistent budget.

A constructed Gateway state is used for deterministic authority fixtures; this
does NOT claim a native Hermes Gateway, mount namespace or paid provider test.
"""
import asyncio
from contextlib import closing
from dataclasses import asdict, replace
import json
import os
from pathlib import Path
import socket
import sqlite3
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'packages/claw-hermes'))
from execution_budget import CLAIM, CONFIG, ExecutionDenied, ExecutionPolicy, seal
from provider_broker import ProviderBrokerClient, ProviderBrokerServer
from provider_egress import BrokerConfig, EGRESS, hashed, signed
from recovery_inspector import _json
from broker_budget import BrokerBudget, initialize


@unittest.skipUnless(
    os.name == 'posix' and hasattr(socket, 'SO_PEERCRED')
    and os.environ.get('ALAZ_BROKER_NATIVE_TESTS') == '1',
    'native IPC/HTTP requires explicit opt-in and a prepared Linux runtime')
class NativeBudgetTransport(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='alaz-budget-native-')
        self.root = Path(self.tmp.name)
        self.gateway = self.root / 'gateway'
        self.gateway.mkdir()
        self.db = self.gateway / 'state.db'
        self.calls = []
        self.reply_status = 200
        self.origin = await asyncio.start_server(self._origin, '127.0.0.1', 0)
        port = self.origin.sockets[0].getsockname()[1]
        self.policy = ExecutionPolicy('owned-fixture', 3, 0, 2048, 16, 6192,
                                      1000000, 1000000, 1000000)
        self.config = BrokerConfig(
            f'http://127.0.0.1:{port}/v1', self.policy.model, 'p'*48, 'b'*64,
            str(self.db), 'c'*64, 'd'*64, self.policy.fingerprint,
            {'version': 1, 'enabled': True, 'directory': str(self.root/'authority'),
             'budget_id': 'a'*32, 'policy': asdict(self.policy)})
        self._init_gateway()
        initialize(self.config)
        self.broker = None
        self.link = None
        await self._new_broker()

    async def asyncTearDown(self):
        try:
            if self.broker is not None:
                await self.broker.close()
        finally:
            self.origin.close()
            await self.origin.wait_closed()
            self.tmp.cleanup()

    async def _origin(self, reader, writer):
        try:
            header = await asyncio.wait_for(reader.readuntil(b'\r\n\r\n'), 5)
            first = header.split(b'\r\n')[0]
            fields = {}
            for line in header.split(b'\r\n')[1:]:
                if b':' in line:
                    key, value = line.split(b':', 1)
                    fields[key.lower()] = value.strip()
            length = int(fields[b'content-length'])
            await asyncio.wait_for(reader.readexactly(length), 5)
            self.calls.append(first.decode('ascii'))
            data = b'{}'
            writer.write(
                f'HTTP/1.1 {self.reply_status} Fixture\r\n'.encode('ascii') +
                b'Content-Type: application/json\r\nContent-Length: 2\r\n'
                b'Connection: close\r\n\r\n' + data)
            await writer.drain()
        finally:
            writer.close()
            await writer.wait_closed()

    def _init_gateway(self):
        with closing(sqlite3.connect(self.db)) as c:
            c.execute('CREATE TABLE runtime_epoch(singleton INTEGER PRIMARY KEY, epoch INTEGER, instance_id TEXT)')
            c.execute('INSERT INTO runtime_epoch VALUES(1,1,?)', ('test-instance',))
            c.execute('CREATE TABLE state_meta(key TEXT PRIMARY KEY, value TEXT)')
            self._reset_gateway_rows(c)
            c.commit()

    def _reset_gateway_rows(self, c):
        # Simulate a mutable/rolled-back Gateway-owned ledger: it is NOT the cap.
        c.execute('DELETE FROM state_meta')
        public = seal({'version': 1, 'scope': self.config.scope,
                       'binding': self.config.binding, 'policy': self.policy.fingerprint,
                       'providerCalls': 0, 'toolCalls': 0, 'reservedTokens': 0,
                       'reservedCostMicrousd': 0, 'quarantined': False})
        c.execute('INSERT INTO state_meta VALUES(?,?)',
                  (CONFIG + self.config.scope, _json(public)))

    async def _new_broker(self):
        index = getattr(self, 'broker_index', 0) + 1
        self.broker_index = index
        self.broker = ProviderBrokerServer(self.config, self.root / f'broker-{index}')
        ready = await self.broker.start()
        self.link = ProviderBrokerClient({
            'socket_path': ready['socketPath'], 'broker_id': ready['brokerId'],
            'route_fingerprint': ready['routeFingerprint'],
            'signing_key': self.config.signing_key})

    def _grant(self):
        body = {'model': self.policy.model,
                'messages': [{'role': 'user', 'content': 'owned local fixture'}],
                'max_tokens': 8, 'stream': False}
        ticket = uuid.uuid4().hex
        grant = {'version': 1, 'brokerId': self.broker.identifier,
                 'routeFingerprint': self.config.route, 'scope': self.config.scope,
                 'binding': self.config.binding, 'policy': self.policy.fingerprint,
                 'ticket': ticket, 'fingerprint': hashed(body),
                 'epoch': 1, 'instance': 'test-instance',
                 'expiresAtMs': int(time.time()*1000)+20000}
        claim = seal({'version': 1, 'scope': self.config.scope,
                      'binding': self.config.binding, 'policy': self.policy.fingerprint,
                      'ticket': ticket, 'kind': 'provider', 'fingerprint': grant['fingerprint'],
                      'epoch': 1, 'instance': 'test-instance', 'state': 'reserved',
                      'tokens': self.policy.tokens_per_attempt,
                      'costMicrousd': self.policy.cost_per_attempt,
                      'usage': None, 'outcome': None})
        with closing(sqlite3.connect(self.db)) as c:
            c.execute('INSERT INTO state_meta VALUES(?,?)',
                      (CLAIM + self.config.scope + '.' + ticket, _json(claim)))
            c.execute('INSERT INTO state_meta VALUES(?,?)',
                      (EGRESS + self.config.scope + '.' + ticket, _json(seal(grant))))
            c.commit()
        envelope = signed({'version': 1, 'operation': 'send',
                           'grant': grant, 'payload': body},
                          self.config.signing_key, 'request')
        return envelope, ticket

    async def _send(self):
        envelope, ticket = self._grant()
        return await self.link._exchange(envelope, ticket)

    async def test_private_cap_survives_gateway_ledger_reset(self):
        for _ in range(3):
            result = await self._send()
            self.assertTrue(result['ok'])
        with closing(sqlite3.connect(self.db)) as c:
            self._reset_gateway_rows(c)
            c.commit()
        with self.assertRaisesRegex(ExecutionDenied, 'private_budget_attempt_limit'):
            await self._send()
        self.assertEqual(len(self.calls), 3)
        self.assertTrue(all(x == 'POST /v1/chat/completions HTTP/1.1' for x in self.calls))
        self.assertEqual(self.broker.budget.snapshot()['providerReservations'], 3)

    async def test_private_cap_survives_broker_restart(self):
        await self._send()
        first = self.broker.identifier
        await self.broker.close()
        await self._new_broker()
        self.assertNotEqual(first, self.broker.identifier)
        await self._send()
        await self._send()
        with self.assertRaisesRegex(ExecutionDenied, 'private_budget_attempt_limit'):
            await self._send()
        self.assertEqual(len(self.calls), 3)
        self.assertEqual(self.broker.budget.snapshot()['observedHttpResponses'], 3)

    async def test_unknown_commit_ack_does_not_send_http(self):
        def ack_lost(c):
            c.commit()
            raise sqlite3.OperationalError('owned simulated ACK loss')
        with patch.object(self.broker.budget, '_commit', side_effect=ack_lost):
            with self.assertRaisesRegex(ExecutionDenied, 'private_budget_storage_unconfirmed'):
                await self._send()
        self.assertEqual(self.calls, [])
        self.assertEqual(self.broker.budget.snapshot()['providerReservations'], 1)
        self.assertEqual(self.broker.counts['physicalAttempts'], 0)
        await self._send()
        self.assertEqual(len(self.calls), 1)

    async def test_http_500_is_observed_without_refund(self):
        self.reply_status = 500
        result = await self._send()
        self.assertEqual(result['status'], 500)
        state = self.broker.budget.snapshot()
        self.assertEqual((state['providerReservations'], state['observedHttpResponses']), (1, 1))

    async def test_missing_private_authority_never_opens_socket(self):
        new = replace(self.config, budget_authority={
            **self.config.budget_authority,
            'directory': str(self.root / 'absent-private')})
        denied = ProviderBrokerServer(new, self.root / 'should-not-exist')
        with self.assertRaises(ExecutionDenied):
            await denied.start()
        self.assertFalse(denied.path.exists())
        self.assertFalse(denied.directory.exists())


if __name__ == '__main__':
    unittest.main(verbosity=2)
