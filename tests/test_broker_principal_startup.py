"""Real broker entrypoint and client gates; mocked kernel/principal boundaries."""
import asyncio
from contextlib import ExitStack
from pathlib import Path
import signal
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'packages/claw-hermes')]
import run_provider_broker as cli
import provider_broker as broker
import host_principal as hp
from execution_budget import ExecutionDenied
from provider_egress import BrokerConfig


def principal():
    return {'version':1,'enabled':True,'gatewayUid':1000,'brokerUid':1101,
            'socketGroupGid':1000,'hostUserNamespace':'user:[4026531837]'}


class Startup(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory(prefix='alaz-startup-unit-')
        self.addCleanup(temp.cleanup)
        self.root=Path(temp.name).resolve()
        self.output=self.root/'broker'
        self.events=[]
        self.on_start=None
        self.on_close=None
        self.acquire_before_failure=True
        self.start_failure=False
        self.constructed=[]
        owner=self
        class Server:
            def __init__(self,config,output):
                self.config=config;self.output=output;self.server=None
                owner.constructed.append(self)
            async def start(self):
                owner.events.append('start')
                if owner.start_failure and not owner.acquire_before_failure:
                    raise RuntimeError('fixture_start_failure')
                self.output.mkdir(exist_ok=True)
                self.server=object()
                if owner.on_start:owner.on_start()
                if owner.start_failure:raise RuntimeError('fixture_start_failure')
                return {'brokerId':'a'*32,'pid':123,'socketPath':str(self.output/'egress.sock')}
            async def close(self):
                owner.events.append('close')
                if owner.on_close:owner.on_close()
                return {'socketRemoved':True,'activeRequests':0,'counters':{'physicalAttempts':0}}
        self.Server=Server

    def config(self,split=False):
        return BrokerConfig('http://127.0.0.1:19440/v1','test','p'*48,'b'*64,
                            str(self.root/'state.db'),'c'*64,'d'*64,'e'*64,
                            principal_contract=principal() if split else None)

    async def invoke(self,split=False,signal_failure=False):
        loop=asyncio.get_running_loop()
        def add(sig,callback):
            self.events.append(('add',sig))
            if signal_failure and sig==signal.SIGTERM:
                raise RuntimeError('fixture_signal_failure')
            callback()
        def remove(sig):self.events.append(('remove',sig));return True
        with (patch.object(cli,'ProviderBrokerServer',self.Server),
              patch.object(loop,'add_signal_handler',side_effect=add),
              patch.object(loop,'remove_signal_handler',side_effect=remove)):
            await asyncio.wait_for(cli.serve(self.config(split),self.output),1)

    def allowed_principal(self):
        stack=ExitStack()
        stack.enter_context(patch.object(hp,'broker_identity',return_value=True))
        stack.enter_context(patch.object(hp,'regular',return_value=(1,2,1101,1000,0o710)))
        return stack

    async def test_legacy_fresh_directory_still_starts_and_stops(self):
        await self.invoke()
        self.assertEqual([x for x in self.events if isinstance(x,str)],['start','close'])
        self.assertTrue((self.output/'ready.json').is_file())
        self.assertTrue((self.output/'shutdown.json').is_file())

    async def test_legacy_existing_directory_remains_refused(self):
        self.output.mkdir()
        with self.assertRaises(ExecutionDenied):await self.invoke()
        self.assertFalse(self.constructed)
        self.assertFalse(list(self.output.iterdir()))

    async def test_principal_preprovisioned_directory_reaches_real_entrypoint(self):
        self.output.mkdir()
        with self.allowed_principal():await self.invoke(split=True)
        self.assertEqual([x for x in self.events if isinstance(x,str)],['start','close'])

    async def test_principal_missing_directory_is_not_auto_created(self):
        with self.allowed_principal(),self.assertRaises(ExecutionDenied):
            await self.invoke(split=True)
        self.assertFalse(self.constructed)
        self.assertFalse(self.output.exists())

    async def test_principal_identity_checked_before_server_construction(self):
        self.output.mkdir()
        with (patch.object(hp,'broker_identity',side_effect=hp.PrincipalRejected('fixture_wrong_uid')),
              self.assertRaisesRegex(hp.PrincipalRejected,'fixture_wrong_uid')):
            await self.invoke(split=True)
        self.assertFalse(self.constructed)

    async def test_principal_directory_permissions_checked_before_start(self):
        self.output.mkdir()
        with (patch.object(hp,'broker_identity',return_value=True),
              patch.object(hp,'regular',side_effect=hp.PrincipalRejected('fixture_wrong_mode')),
              self.assertRaisesRegex(hp.PrincipalRejected,'fixture_wrong_mode')):
            await self.invoke(split=True)
        self.assertFalse(self.constructed)

    async def test_principal_nonempty_directory_is_never_adopted(self):
        self.output.mkdir();(self.output/'ready.json').write_text('previous-owner')
        with self.allowed_principal(),self.assertRaises(ExecutionDenied):
            await self.invoke(split=True)
        self.assertFalse(self.constructed)
        self.assertEqual((self.output/'ready.json').read_text(),'previous-owner')

    async def test_ready_collision_is_not_overwritten_and_owned_server_closes(self):
        self.on_start=lambda:(self.output/'ready.json').write_text('foreign-ready')
        with self.assertRaises(FileExistsError):await self.invoke()
        self.assertIn('close',self.events)
        self.assertEqual((self.output/'ready.json').read_text(),'foreign-ready')
        self.assertFalse((self.output/'shutdown.json').exists())

    async def test_ready_publication_failure_closes_owned_server(self):
        self.on_start=lambda:(self.output/'ready.json').mkdir()
        with self.assertRaises(OSError):await self.invoke()
        self.assertIn('close',self.events)
        self.assertTrue((self.output/'ready.json').is_dir())

    async def test_partial_start_failure_closes_acquired_server(self):
        self.start_failure=True
        with self.assertRaisesRegex(RuntimeError,'fixture_start_failure'):await self.invoke()
        self.assertEqual(self.events,['start','close'])
        self.assertFalse((self.output/'ready.json').exists())

    async def test_unacquired_start_failure_does_not_clean_foreign_socket(self):
        self.start_failure=True;self.acquire_before_failure=False
        with self.assertRaisesRegex(RuntimeError,'fixture_start_failure'):await self.invoke()
        self.assertEqual(self.events,['start'])
        self.assertFalse(self.output.exists())

    async def test_signal_setup_failure_closes_and_removes_installed_handler(self):
        with self.assertRaisesRegex(RuntimeError,'fixture_signal_failure'):
            await self.invoke(signal_failure=True)
        self.assertIn('close',self.events)
        self.assertIn(('remove',signal.SIGINT),self.events)
        self.assertNotIn(('remove',signal.SIGTERM),self.events)

    async def test_success_removes_only_installed_handlers(self):
        await self.invoke()
        self.assertEqual([x[1] for x in self.events if isinstance(x,tuple) and x[0]=='remove'],
                         [signal.SIGINT,signal.SIGTERM])

    async def test_shutdown_collision_is_not_overwritten(self):
        self.on_close=lambda:(self.output/'shutdown.json').write_text('foreign-shutdown')
        with self.assertRaises(FileExistsError):await self.invoke()
        self.assertEqual((self.output/'shutdown.json').read_text(),'foreign-shutdown')
        self.assertIn(('remove',signal.SIGINT),self.events)


class ClientIdentity(unittest.IsolatedAsyncioTestCase):
    def client(self,split=True):
        value={'socket_path':'/tmp/alaz-owned/broker/egress.sock','broker_id':'a'*32,
               'route_fingerprint':'b'*64,'signing_key':'c'*64}
        if split:value['principal_contract']=principal()
        return broker.ProviderBrokerClient(value)

    async def refused(self,own_error=None,namespace='user:[4026531837]',ns_error=None):
        with (patch.object(hp,'gateway_identity',side_effect=own_error,return_value=True) as own,
              patch.object(broker.os,'readlink',side_effect=ns_error,return_value=namespace),
              patch.object(broker,'private_socket') as inspect,
              patch.object(broker.asyncio,'open_unix_connection',create=True,new_callable=AsyncMock) as connect,
              self.assertRaisesRegex(ExecutionDenied,'broker_gateway_principal_refused')):
            await self.client()._exchange({},'a'*32)
        own.assert_called_once_with(principal())
        inspect.assert_not_called();connect.assert_not_called()

    async def test_wrong_local_gateway_identity_refuses_before_any_socket(self):
        await self.refused(own_error=hp.PrincipalRejected('wrong_uid'))

    async def test_same_numeric_uid_in_other_namespace_refuses_before_any_socket(self):
        await self.refused(namespace='user:[99]')

    async def test_unreadable_namespace_refuses_before_any_socket(self):
        await self.refused(ns_error=PermissionError('unreadable'))

    async def test_valid_identity_reaches_transport_without_claiming_connection(self):
        with (patch.object(hp,'gateway_identity',return_value=True) as own,
              patch.object(broker.os,'readlink',return_value=principal()['hostUserNamespace']),
              patch.object(broker,'private_socket',return_value=(1,2)),
              patch.object(broker.asyncio,'open_unix_connection',create=True,
                           side_effect=ExecutionDenied('fixture_connection_reached')) as connect,
              self.assertRaisesRegex(ExecutionDenied,'fixture_connection_reached')):
            await self.client()._exchange({},'a'*32)
        own.assert_called_once_with(principal());connect.assert_called_once()

    async def test_legacy_does_not_require_principal_or_namespace(self):
        with (patch.object(hp,'gateway_identity') as own,
              patch.object(broker.os,'readlink') as ns,
              patch.object(broker,'private_socket',side_effect=ExecutionDenied('fixture_legacy')),
              self.assertRaisesRegex(ExecutionDenied,'fixture_legacy')):
            await self.client(False)._exchange({},'a'*32)
        own.assert_not_called();ns.assert_not_called()


if __name__=='__main__':unittest.main()
