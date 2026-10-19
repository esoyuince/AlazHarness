"""Broker wiring contracts for host-principal opt-in; no real sockets or UID switch."""
import asyncio
import os
from pathlib import Path
import socket
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'packages/claw-hermes'))
from execution_budget import ExecutionDenied
import host_principal as hp
import provider_broker as broker
from provider_egress import BrokerLink, BrokerConfig

def spec():
    return {'version':1,'enabled':True,'brokerUid':65534,
            'gatewayUid':1000,'socketGroupGid':1000,
            'hostUserNamespace':'user:[4026531837]'}

def configuration(principal=None):
    return BrokerConfig('http://127.0.0.1:19440/v1','owned-fixture','p'*48,'b'*64,
           str(Path(tempfile.gettempdir())/'alaz-principal-gateway-qa'/'state.db'),
           'c'*64,'d'*64,'e'*64,
           None,principal)

def link(principal=None):
    return BrokerLink('/tmp/alaz-owned/sock/egress.sock','a'*32,'b'*64,'c'*64,principal)

class WiringPolicy(unittest.TestCase):
    def test_default_legacy_config_is_none(self):
        self.assertIsNone(configuration().principal_contract)
        self.assertIsNone(link().principal_contract)
    def test_optin_round_trips_immutable_copy(self):
        x=spec();b=configuration(x);l=link(x)
        x['brokerUid']=1000
        self.assertEqual(b.principal_contract['brokerUid'],65534)
        self.assertEqual(l.principal_contract['brokerUid'],65534)
    def test_same_uid_rejected_at_configuration(self):
        for ctor in (configuration,link):
            with self.subTest(ctor=ctor.__name__),self.assertRaises(hp.PrincipalRejected):
                ctor(spec()|{'brokerUid':1000})
    def test_unknown_fields_denied_not_ignored(self):
        for ctor in (configuration,link):
            with self.subTest(ctor=ctor.__name__),self.assertRaises(hp.PrincipalRejected):
                ctor(spec()|{'fallbackLegacyOnError':True})
    def test_broker_socket_uses_principal_identity_only_in_optin(self):
        with patch.object(broker.os,'name','posix'),\
             patch.object(broker.socket,'SO_PEERCRED',17,create=True),\
             patch.object(hp,'socket_identity',return_value={'socket':(17,42,65534,1000,0o660)}) as check:
            self.assertEqual(broker.private_socket('/tmp/owned/egress.sock',spec()),(17,42))
        check.assert_called_once()
    def test_broker_peer_checks_real_credential_for_gateway(self):
        class Sock:
            def getsockopt(self,*_):return struct.pack('3i',1234,1000,1000)
        class Writer:
            def get_extra_info(self,name):
                assert name=='socket'
                return Sock()
        with patch.object(broker.os,'name','posix'),\
             patch.object(broker.socket,'SO_PEERCRED',17,create=True):
            self.assertEqual(broker.peer(Writer(),spec(),role='broker'),1234)
            with self.assertRaises(hp.PrincipalRejected):
                broker.peer(Writer(),spec(),role='gateway')
    def test_root_peer_refused_even_when_socket_is_group_accessible(self):
        class Sock:
            def getsockopt(self,*_):return struct.pack('3i',10,0,0)
        class Writer:
            def get_extra_info(self,*_):return Sock()
        with patch.object(broker.os,'name','posix'),\
             patch.object(broker.socket,'SO_PEERCRED',17,create=True):
            with self.assertRaises(hp.PrincipalRejected):
                broker.peer(Writer(),spec(),role='broker')
    def test_wrong_uid_broker_cannot_initialize_principal_transport(self):
        # Offline Windows only: simulate Linux SO_PEERCRED check; no socket
        # created or filesystem privilege granted when UID differs.
        with tempfile.TemporaryDirectory(prefix='principal-wire-') as temp:
            directory=Path(temp)/'private-sock'
            server=broker.ProviderBrokerServer(configuration(spec()),directory)
            with patch.object(broker.os,'name','posix'),\
                 patch.object(broker.socket,'SO_PEERCRED',17,create=True),\
                 patch.object(hp,'broker_identity',side_effect=hp.PrincipalRejected('untrusted_uid')):
                with self.assertRaisesRegex(hp.PrincipalRejected,'untrusted_uid'):
                    asyncio.run(server.start())
            self.assertFalse(directory.exists())
            self.assertFalse(server.path.exists())
    def test_broker_lifetime_never_initializes_private_budget_implicitly(self):
        server=broker.ProviderBrokerServer(configuration(spec()),Path('/tmp/alaz-principal-absent'))
        self.assertIsNone(server.budget)
        self.assertIsNone(server.server)
    def test_principal_is_not_automatic_global_setting(self):
        legacy=broker.ProviderBrokerServer(configuration(),Path('/tmp/alaz-legacy-owned'))
        self.assertIsNone(legacy.config.principal_contract)
        self.assertFalse(legacy.started)

if __name__=='__main__':unittest.main()
