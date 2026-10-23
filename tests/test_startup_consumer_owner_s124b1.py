"""Original owner consumer-slot contracts; native imports/constructors explicitly doubled."""
import sys,unittest
from pathlib import Path
from unittest.mock import AsyncMock,patch
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'packages/claw-hermes'),str(ROOT/'tests')]
import test_gateway_store_startup as base
import test_three_store_lifecycle_l113f6 as three
import gateway_store_startup as s
import gateway_prepared_consumer as c
class OwnerConsumerContracts(unittest.IsolatedAsyncioTestCase):
    setUp=three.ThreeStoreLifecycle.setUp
    mark=base.Lifecycle.mark
    make_store=base.Lifecycle.make_store
    obj=three.ThreeStoreLifecycle.obj
    async def test_consumer_cannot_attach_before_verified(self):
        o=self.obj()
        with self.assertRaises(s.StoreStartupRejected):await o.prepare_runtime(object(),object())
        self.native.assert_not_called();self.assertIsNone(o._prepared_consumer)
    async def test_default_pair_never_implicitly_becomes_three_store(self):
        o=s.NativeStoreStartup(self.held,self.mount,self.expected,instance_id='pair');o.start()
        with self.assertRaises(s.StoreStartupRejected):await o.prepare_runtime(object(),object())
        self.assertIsNone(o._prepared_consumer);o.close()
    async def test_reservation_precedes_first_consumer_prepare_effect(self):
        o=self.obj();o.start()
        async def observe(consumer,*args):
            self.assertIs(o._prepared_consumer,consumer)
            with self.assertRaises(c.PreparedConsumerRejected):o.close()
            for store in self.created:store.close.assert_not_called()
        with patch.object(c.PreparedRuntimeConsumer,'prepare',new=observe):value=await o.prepare_runtime(object(),object())
        self.assertIs(value,o._prepared_consumer);self.assertEqual(value._stage,'RESERVED')
    async def test_consumer_constructor_failure_cannot_replace_reserved_slot(self):
        o=self.obj();o.start()
        with patch.object(c.PreparedRuntimeConsumer,'prepare',new=AsyncMock(side_effect=RuntimeError('fixture native failure'))):
            with self.assertRaises(RuntimeError):await o.prepare_runtime(object(),object())
        first=o._prepared_consumer
        with self.assertRaises(s.StoreStartupRejected):await o.prepare_runtime(object(),object())
        self.assertIs(o._prepared_consumer,first)
        with self.assertRaises(c.PreparedConsumerRejected):o.close()
        for store in self.created:store.close.assert_not_called()
    async def test_interrupted_prepare_retains_owner_slot(self):
        o=self.obj();o.start()
        import asyncio
        with patch.object(c.PreparedRuntimeConsumer,'prepare',new=AsyncMock(side_effect=asyncio.CancelledError)):
            with self.assertRaises(asyncio.CancelledError):await o.prepare_runtime(object(),object())
        self.assertIsNotNone(o._prepared_consumer)
        with self.assertRaises(c.PreparedConsumerRejected):o.close()
        self.finish.assert_not_called()
    async def test_foreign_actor_refuses_consumer_before_import(self):
        o=self.obj();o.start();self.actor_fn.return_value=(999,23001,23003,5)
        with self.assertRaises(s.StoreStartupRejected):await o.prepare_runtime(object(),object())
        self.assertIsNone(o._prepared_consumer)
    async def test_wrong_consumer_type_never_authorizes_close(self):
        o=self.obj();o.start();o._prepared_consumer=object()
        with self.assertRaisesRegex(s.StoreStartupRejected,'consumer_identity'):o.close()
        for store in self.created:store.close.assert_not_called()
    async def test_detached_label_without_native_proofs_not_enough(self):
        o=self.obj();o.start()
        with patch.object(c.PreparedRuntimeConsumer,'prepare',new=AsyncMock()):consumer=await o.prepare_runtime(object(),object())
        consumer._stage='DETACHED'
        with self.assertRaises((c.PreparedConsumerRejected,AttributeError)):o.close()
        for store in self.created:store.close.assert_not_called()
if __name__=='__main__':unittest.main()
