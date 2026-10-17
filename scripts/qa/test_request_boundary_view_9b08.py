"""Independent opt-in R1B2 actual HTTP-handler integration, synthetic aiohttp/IPC.
This runs against ALAZ_R1B2_QA_SOURCE; no server, dependency or model is started.
"""
import asyncio
from contextlib import closing
import importlib.util
import json
import os
from pathlib import Path
import sqlite3
import sys
import unittest
from unittest.mock import patch
TARGET=Path(os.environ['ALAZ_R1B2_QA_SOURCE']).resolve()
sys.path[:0]=[str(TARGET/'packages/claw-hermes'),str(TARGET/'tests')]
import execution_boundary as eb
import provider_broker as pb
import provider_egress as pe
import request_view as rv
import test_execution_budget
from execution_budget import ExecutionDenied
from recovery_inspector import _json
QA=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('boundary_fixture_9b08',QA/'tests/test_request_boundary_qa_9b08.py')
fixture=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixture)
assert Path(eb.__file__).resolve().is_relative_to(TARGET)
assert Path(test_execution_budget.__file__).resolve().is_relative_to(TARGET)


class RequestBoundaryViewIndependentQA(unittest.TestCase):
    def setUp(self):
        self.h=fixture.BoundaryHarness(self)
        self.h.boundary.record_request_view=True
    def body(self):return {'model':'test','messages':[{'role':'user','content':'Işık\r\nβ😀'}]}
    def rows(self):
        with closing(sqlite3.connect(self.h.f.home/'state.db')) as c:
            return [json.loads(v) for (v,) in c.execute('SELECT value FROM state_meta WHERE key GLOB ?',(rv.PREFIX+'*',))]
    def projected(self):
        section={'references':[]}
        with closing(sqlite3.connect((self.h.f.home/'state.db').as_uri()+'?mode=ro',uri=True)) as c:
            c.execute('PRAGMA query_only=ON')
            rv.enrich_request_views(c,section,self.h.f.context,self.h.f.policy)
        return section['providerRequestViews']['requests'][0]

    def test_normalized_wire_request_is_exact_recorded_manifest(self):
        result=self.h.send(self.body());self.assertEqual(result.status,200)
        row=self.rows()[0];sent=self.h.docs[0]['payload']
        self.assertEqual(sent['max_tokens'],20)
        self.assertEqual(row['requestDigest'],pe.hashed(sent))
        self.assertEqual(row['requestBytes'],len(_json(sent).encode()))
        self.assertEqual(row['state'],'broker_response_observed')
        self.assertTrue(self.projected()['providerResponseValidated'])

    def test_wrong_model_response_observed_but_never_validated(self):
        self.h.response['model']='wrong-model'
        result=self.h.send(self.body());self.assertNotEqual(result.status,200)
        self.assertEqual(self.rows()[0]['state'],'broker_response_observed')
        projected=self.projected();self.assertTrue(projected['brokerHttpResponseObserved'])
        self.assertFalse(projected['providerResponseValidated'])
        self.assertTrue(self.h.f.ledger.snapshot()['quarantined'])

    def test_prepare_failure_stops_handler_before_any_ipc(self):
        with patch.object(rv,'prepare_in_transaction',side_effect=ExecutionDenied('request_test_preparation_refused')):
            result=self.h.send(self.body())
        self.assertNotEqual(result.status,200);self.assertEqual(self.h.docs,[])
        self.assertEqual(self.rows(),[]);self.assertEqual(self.h.f.ledger.snapshot()['providerCalls'],1)

    def test_unknown_after_handoff_never_becomes_response_observation(self):
        async def lost(*args):raise ExecutionDenied('broker_transport_outcome_unknown')
        self.h.boundary.broker._exchange=lost
        result=self.h.send(self.body());self.assertNotEqual(result.status,200)
        self.assertEqual(self.rows()[0]['state'],'handoff_armed')
        self.assertFalse(self.projected()['brokerHttpResponseObserved'])
        self.assertEqual(self.h.f.ledger.snapshot()['reservedTokens'],120)

    def test_nonboolean_setting_refused_at_construction(self):
        for value in [1,'true',None,[],{}]:
            with self.subTest(value=value),self.assertRaises(ExecutionDenied):
                eb.ExecutionBoundary(self.h.cfg|{'record_request_view':value})

    def test_recording_requires_qualified_broker_not_direct_route(self):
        cfg={k:v for k,v in self.h.cfg.items() if k!='provider_broker'}
        cfg.update(upstream_base_url='http://127.0.0.1:19229/v1',record_request_view=True)
        with self.assertRaisesRegex(ExecutionDenied,'request_view_requires_broker'):eb.ExecutionBoundary(cfg)

if __name__=='__main__':unittest.main(verbosity=2)
