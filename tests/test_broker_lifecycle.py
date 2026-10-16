"""Actual broker shutdown ordering with synthetic server/transports; no sockets opened."""
import asyncio
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'packages/claw-hermes'))
from provider_broker import ProviderBrokerServer
from provider_egress import BrokerConfig

class Writer:
    def __init__(self):self.closed=False;self.parts=[]
    def close(self):self.closed=True
    async def wait_closed(self):pass
    def write(self,data):self.parts.append(data)
    async def drain(self):pass

class BrokerLifecycle(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);self.root=Path(tmp.name)
        cfg=BrokerConfig('http://127.0.0.1:19777/v1','test','p'*48,'b'*64,str(self.root/'state.db'),'a'*64,'c'*64,'d'*64)
        self.broker=ProviderBrokerServer(cfg,self.root/'broker')
    async def test_active_request_cancelled_before_server_wait(self):
        stopped=asyncio.Event();called=[]
        async def connected_request():
            try:await asyncio.Future()
            finally:stopped.set();self.broker.tasks.discard(asyncio.current_task())
        async def wait_closed():
            called.append('wait');await stopped.wait()
        task=asyncio.create_task(connected_request());await asyncio.sleep(0)
        self.broker.tasks.add(task);writer=Writer();self.broker.connections.add(writer)
        self.broker.server=SimpleNamespace(close=lambda:called.append('close'),wait_closed=wait_closed)
        try:
            result=await asyncio.wait_for(self.broker.close(),.5)
            self.assertTrue(task.cancelled());self.assertTrue(writer.closed);self.assertEqual(result['activeRequests'],0)
        finally:
            task.cancel();await asyncio.gather(task,return_exceptions=True)
        self.assertEqual(called,['close','wait'])
    async def test_late_handler_closed_without_read_or_response(self):
        await self.broker.close();writer=Writer();reader=asyncio.StreamReader()
        with patch('provider_broker.peer',side_effect=AssertionError('must not authenticate after close')):
            await self.broker._handle(reader,writer)
        self.assertTrue(writer.closed);self.assertEqual(writer.parts,[]);self.assertEqual(self.broker.counts['refused'],0)
    async def test_empty_close_has_no_dispatch(self):
        value=await self.broker.close();self.assertEqual(value['counters']['physicalAttempts'],0)
        self.assertTrue(value['socketRemoved']);self.assertFalse((self.root/'state.db').exists())

if __name__=='__main__':unittest.main()
