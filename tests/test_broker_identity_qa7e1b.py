"""Real broker reply verifier with explicitly synthetic in-memory IPC streams.
No real socket or service is opened. Tests do not establish OS-level isolation.
"""
import asyncio
import copy
from pathlib import Path
import struct
import sys
import unittest
from unittest.mock import AsyncMock,patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'packages/claw-hermes'))
from provider_broker import ProviderBrokerClient
from provider_egress import signed
from recovery_inspector import _json
from execution_budget import ExecutionDenied

SETTINGS={'socket_path':'/tmp/qa/egress.sock','broker_id':'a'*32,'route_fingerprint':'b'*64,'signing_key':'c'*64}
NONCE='d'*32

class Writer:
    def __init__(self):self.closed=False;self.parts=[];self.drained=False
    def write(self,data):self.parts.append(bytes(data))
    async def drain(self):self.drained=True
    def close(self):self.closed=True
    async def wait_closed(self):return None

class BrokerIdentityQA(unittest.IsolatedAsyncioTestCase):
    def response(self,**changes):
        return {'version':1,'brokerId':SETTINGS['broker_id'],'nonce':NONCE,'ok':True,'routeFingerprint':SETTINGS['route_fingerprint']}|changes
    async def exchange(self,document,*,role='reply',socket_identities=None,peer_error=None):
        raw=_json(signed(document,SETTINGS['signing_key'],role)).encode()
        reader=asyncio.StreamReader();reader.feed_data(struct.pack('!I',len(raw))+raw);reader.feed_eof()
        self.writer=Writer();opened=AsyncMock(return_value=(reader,self.writer));self.opened=opened
        identities=socket_identities or [(1,2),(1,2)]
        with patch('provider_broker.private_socket',side_effect=identities),patch('provider_broker.peer',side_effect=peer_error,return_value=123),patch('asyncio.open_unix_connection',new=opened,create=True):
            return await ProviderBrokerClient(SETTINGS)._exchange({'test_only_request':True},NONCE)
    async def test_exact_signed_response_accepted(self):
        value=self.response();self.assertEqual(await self.exchange(value),value)
        self.assertTrue(self.writer.closed);self.assertTrue(self.writer.drained);self.opened.assert_awaited_once()
    async def test_other_nonce_refused_and_stream_closed(self):
        with self.assertRaisesRegex(ExecutionDenied,'broker_reply_mismatch'):await self.exchange(self.response(nonce='e'*32))
        self.assertTrue(self.writer.closed)
    async def test_previous_broker_id_refused(self):
        with self.assertRaisesRegex(ExecutionDenied,'broker_reply_mismatch'):await self.exchange(self.response(brokerId='f'*32))
        self.assertTrue(self.writer.closed)
    async def test_bool_protocol_version_is_not_one(self):
        with self.assertRaisesRegex(ExecutionDenied,'broker_reply_mismatch'):await self.exchange(self.response(version=True))
    async def test_numeric_ok_not_boolean(self):
        with self.assertRaisesRegex(ExecutionDenied,'invalid_broker_reply'):await self.exchange(self.response(ok=1))
    async def test_request_domain_signature_not_reply(self):
        with self.assertRaisesRegex(ExecutionDenied,'broker_authentication_required'):await self.exchange(self.response(),role='request')
        self.assertTrue(self.writer.closed)
    async def test_peer_denied_before_any_write(self):
        with self.assertRaisesRegex(ExecutionDenied,'broker_peer_mismatch'):await self.exchange(self.response(),peer_error=ExecutionDenied('broker_peer_mismatch'))
        self.assertEqual(self.writer.parts,[]);self.assertTrue(self.writer.closed)
    async def test_socket_replacement_before_any_write(self):
        with self.assertRaisesRegex(ExecutionDenied,'broker_socket_replaced'):await self.exchange(self.response(),socket_identities=[(1,2),(1,3)])
        self.assertEqual(self.writer.parts,[]);self.assertTrue(self.writer.closed)
    async def test_bounded_known_server_refusal_preserved(self):
        with self.assertRaisesRegex(ExecutionDenied,'broker_replay_refused'):await self.exchange(self.response(ok=False,error='broker_replay_refused'))
        self.assertTrue(self.writer.closed)
    async def test_unknown_server_error_text_not_echoed(self):
        with self.assertRaises(ExecutionDenied) as caught:await self.exchange(self.response(ok=False,error='untrusted free text'))
        self.assertEqual(str(caught.exception),'broker_request_refused');self.assertTrue(self.writer.closed)
    async def test_cancelled_read_not_silently_retried(self):
        reader=asyncio.StreamReader();writer=Writer();opened=AsyncMock(return_value=(reader,writer))
        with patch('provider_broker.private_socket',return_value=(1,2)),patch('provider_broker.peer',return_value=123),patch('asyncio.open_unix_connection',new=opened,create=True):
            task=asyncio.create_task(ProviderBrokerClient(SETTINGS)._exchange({'test_only_request':True},NONCE))
            for _ in range(10):
                await asyncio.sleep(0)
                if writer.drained:break
            self.assertTrue(writer.drained);task.cancel()
            with self.assertRaises(asyncio.CancelledError):await task
        opened.assert_awaited_once();self.assertTrue(writer.closed)

if __name__=='__main__':unittest.main()
