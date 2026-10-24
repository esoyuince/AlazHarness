"""Offline selection and policy contracts; native pieces explicitly doubled here."""
import asyncio,hashlib,json,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'packages/claw-hermes'),str(ROOT/'tests')]
import gateway_store_startup as startup
import gateway_prepared_consumer as consumer
import gateway_consumer_admission as admission
import test_gateway_store_startup as base
import test_three_store_lifecycle_l113f6 as three
import historical_owner_b129d6 as history

class ExplicitOwnerSelection(unittest.IsolatedAsyncioTestCase):
    setUp=three.ThreeStoreLifecycle.setUp
    mark=base.Lifecycle.mark
    make_store=base.Lifecycle.make_store
    obj=three.ThreeStoreLifecycle.obj
    async def test_explicit_generation_reserved_in_original_consumer_slot(self):
        owner=self.obj();owner.start()
        async def prepare(c,*args):
            self.assertIs(owner._prepared_consumer,c)
            self.assertTrue(c._local_admission);self.assertEqual(c._selected_feature,consumer.ADMISSION_FEATURE)
            with self.assertRaises(consumer.PreparedConsumerRejected):owner.close()
        with patch.object(consumer.PreparedRuntimeConsumer,'prepare',new=prepare):
            c=await owner.prepare_runtime(object(),object(),local_admission=True)
        self.assertIs(type(c),consumer.PreparedRuntimeConsumer);self.assertEqual(c._admission_phase,'PREPARED')
    async def test_default_generation_not_silently_changed(self):
        owner=self.obj();owner.start()
        async def prepare(c,*args):
            self.assertFalse(c._local_admission);self.assertEqual(c._selected_feature,consumer.FEATURE)
        with patch.object(consumer.PreparedRuntimeConsumer,'prepare',new=prepare):await owner.prepare_runtime(object(),object())
    async def test_non_boolean_option_has_no_slot_or_constructor_effect(self):
        owner=self.obj();owner.start()
        for value in (0,1,None,'true'):
            with self.assertRaises(startup.StoreStartupRejected):await owner.prepare_runtime(object(),object(),local_admission=value)
            self.assertIsNone(owner._prepared_consumer)

class AdmissionPolicyContracts(unittest.TestCase):
    def test_pre_effect_transition_refusal_retains_known_state(self):
        c=SimpleNamespace(_binding=SimpleNamespace(_stage='PREPARED'),_stage='ATTACHED',_admission_phase='PREPARED')
        def refused():raise RuntimeError('known refusal fixture')
        with self.assertRaises(RuntimeError):admission._call_transition(c,refused,'ACTIVE')
        self.assertEqual((c._stage,c._admission_phase),('ATTACHED','PREPARED'))
    def test_changed_native_transition_retains_unknown(self):
        c=SimpleNamespace(_binding=SimpleNamespace(_stage='PREPARED'),_stage='ATTACHED',_admission_phase='PREPARED')
        def changed():c._binding._stage='ACTIVE';raise RuntimeError('post-effect fixture')
        with self.assertRaises(RuntimeError):admission._call_transition(c,changed,'ACTIVE')
        self.assertEqual((c._stage,c._admission_phase),('ADMISSION_UNKNOWN','UNKNOWN'))
    def test_identity_policy_is_not_a_truthy_coercion(self):
        for value in (0,1,None,'false'):
            with self.assertRaisesRegex(startup.live.LiveStoreRejected,'idle_policy'):
                startup.live.verify_live_stores(None,None,None,None,None,require_idle=value)
        want=startup.response_live.ResponseConnectionExpectation(startup.response_live.FEATURE_COMMIT,'a'*64,(1,2))
        with self.assertRaisesRegex(startup.response_live.ResponseLiveRejected,'idle_policy'):
            startup.response_live.verify_response_connection(None,None,None,None,want,constructor=True,require_idle=False)
    def test_historical_bytes_are_exact_and_unknown_generation_is_not_accepted(self):
        E=ROOT/'evidence/d3b-active-owner-b129d6';base=json.loads((E/'baseline.json').read_text(encoding='utf-8'))
        name='packages/claw-hermes/gateway_live_store_gate.py';old=base['sources'][name]
        self.assertEqual(history.saved_generation_hash(ROOT,name,old),old)
        self.assertIsNone(history.saved_generation_hash(ROOT,name,'0'*64))
        self.assertNotEqual(hashlib.sha256((ROOT/name).read_bytes()).hexdigest(),old)
        self.assertIsNone(history.saved_generation_hash(ROOT,'packages/claw-hermes/not-a-real-module.py',old))
if __name__=='__main__':unittest.main()
