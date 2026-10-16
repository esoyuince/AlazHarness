"""Pure protocol/framing and controlled IPC-client contracts; no live provider/network."""
import asyncio
import base64
from pathlib import Path
import struct
import sys
import unittest
from unittest.mock import AsyncMock,patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'packages/claw-hermes'))
from execution_budget import ExecutionDenied
from provider_broker import ProviderBrokerClient,read_frame,write_frame
from provider_egress import signed

SETTINGS={'socket_path':'/tmp/private/egress.sock','broker_id':'a'*32,'route_fingerprint':'c'*64,'signing_key':'b'*64}

class BrokerFrames(unittest.IsolatedAsyncioTestCase):
    async def test_valid_json_frame(self):
        r=asyncio.StreamReader();raw=b'{"ok":true}';r.feed_data(struct.pack('!I',len(raw))+raw);r.feed_eof()
        self.assertEqual(await read_frame(r,32),{'ok':True})
    async def test_duplicate_json_fields_refused(self):
        r=asyncio.StreamReader();raw=b'{"ok":true,"ok":false}';r.feed_data(struct.pack('!I',len(raw))+raw);r.feed_eof()
        with self.assertRaises(ValueError):await read_frame(r,100)
    async def test_oversized_header_before_body(self):
        r=asyncio.StreamReader();r.feed_data(struct.pack('!I',101))
        with self.assertRaises(ExecutionDenied):await read_frame(r,100)
    async def test_zero_length_refused(self):
        r=asyncio.StreamReader();r.feed_data(b'\0\0\0\0')
        with self.assertRaises(ExecutionDenied):await read_frame(r,100)
    async def test_truncated_body(self):
        r=asyncio.StreamReader();r.feed_data(struct.pack('!I',20)+b'{}');r.feed_eof()
        with self.assertRaises(asyncio.IncompleteReadError):await read_frame(r,100)
    async def test_nonfinite_json(self):
        r=asyncio.StreamReader();raw=b'{"n":NaN}';r.feed_data(struct.pack('!I',len(raw))+raw);r.feed_eof()
        with self.assertRaises(ValueError):await read_frame(r,100)
    async def test_invalid_utf8(self):
        r=asyncio.StreamReader();r.feed_data(struct.pack('!I',1)+b'\xff');r.feed_eof()
        with self.assertRaises(UnicodeError):await read_frame(r,100)
    async def test_write_size_guard_before_write(self):
        class Sink:
            def write(self,data):raise AssertionError('must not write oversized')
        with self.assertRaises(ExecutionDenied):await write_frame(Sink(),{'x':'a'*100},32)

class BrokerReplyContracts(unittest.IsolatedAsyncioTestCase):
    def client(self,reply):
        c=ProviderBrokerClient(SETTINGS);c._exchange=AsyncMock(return_value=reply);return c
    def response(self,**changes):
        return dict(version=1,brokerId='a'*32,nonce='d'*32,ok=True,status=200,contentType='application/json',dataBase64=base64.b64encode(b'{}').decode())|changes
    async def send(self,reply):
        with patch('provider_broker.authorize_egress',return_value={'frozen':True}):return await self.client(reply).send(object(),'d'*32,{})
    async def test_exact_raw_body(self):self.assertEqual(await self.send(self.response()),(b'{}',200,'application/json'))
    async def test_header_injection_refused(self):
        with self.assertRaises(ExecutionDenied):await self.send(self.response(contentType='application/json\r\nX:secret'))
    async def test_redirect_status_refused(self):
        with self.assertRaises(ExecutionDenied):await self.send(self.response(status=302))
    async def test_bool_http_status_refused(self):
        with self.assertRaises(ExecutionDenied):await self.send(self.response(status=True))
    async def test_extra_response_data_refused(self):
        with self.assertRaises(ExecutionDenied):await self.send(self.response(secret='not-allowed'))
    async def test_invalid_base64_refused(self):
        with self.assertRaises(ExecutionDenied):await self.send(self.response(dataBase64='@@'))
    async def test_unknown_commit_never_reaches_socket(self):
        c=self.client(self.response())
        with patch('provider_broker.authorize_egress',side_effect=ExecutionDenied('execution_storage_unconfirmed')):
            with self.assertRaises(ExecutionDenied):await c.send(object(),'d'*32,{})
        c._exchange.assert_not_called()
    async def test_request_sender_uses_grant_once(self):
        c=self.client(self.response())
        with patch('provider_broker.authorize_egress',return_value={'signature':'grant'}) as mint:
            await c.send(object(),'d'*32,{})
        mint.assert_called_once();c._exchange.assert_awaited_once()
    async def test_missing_socket_does_not_network_fallback(self):
        c=ProviderBrokerClient(SETTINGS)
        with patch('provider_broker.private_socket',side_effect=FileNotFoundError),patch('asyncio.open_unix_connection',new_callable=AsyncMock,create=True) as opened:
            with self.assertRaisesRegex(ExecutionDenied,'broker_transport_outcome_unknown'):await c.ready()
        opened.assert_not_called()

if __name__=='__main__':unittest.main()
