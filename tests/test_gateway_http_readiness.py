"""Lifecycle tests with explicit HTTP/native doubles; genuine HTTP is separate."""
import asyncio
from contextlib import ExitStack
from dataclasses import replace
import json,os,sys,threading,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock,PropertyMock,patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'packages/claw-hermes'))
import gateway_http_readiness as h
class Headers:
    def __init__(self,items):self.items=items
    def getall(self,name,default=None):
        v=[v for k,v in self.items if k.lower()==name.lower()];return v if v else default
    def __contains__(self,name):return any(k.lower()==name.lower() for k,_ in self.items)
class Response:
    def __init__(self,body,*,status,headers):self.body,self.status,self.headers=body,status,headers;self.closed=False
    def force_close(self):self.closed=True
class ReadinessTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.stack=ExitStack();self.addCleanup(self.stack.close);self.events=[]
        self.actor=(os.getpid(),23001,23003,threading.get_ident())
        self.actor_fn=self.stack.enter_context(patch.object(h.startup.live.profiles,'_actor',return_value=self.actor))
        self.stores=h.startup.NativeStoreStartup.__new__(h.startup.NativeStoreStartup)
        self.stores._stage='NEW';self.stores._held=object();self.stores._mount=object()
        self.state=SimpleNamespace(_conn=object());self.replay=SimpleNamespace(_conn=object())
        self.expected=h.startup.live.PreparedStoreExpectation(h.startup.live.NATIVE_PIN,'a'*64,'b'*64,'12345678-1234-4234-8234-123456789012',123,(7,11),(7,12),1,'h110e')
        self.stack.enter_context(patch.object(h.startup.NativeStoreStartup,'state_store',new_callable=PropertyMock,return_value=self.state))
        self.stack.enter_context(patch.object(h.startup.NativeStoreStartup,'replay_store',new_callable=PropertyMock,return_value=self.replay))
        self.expectation=self.stack.enter_context(patch.object(h.startup.NativeStoreStartup,'expectation',new_callable=PropertyMock,return_value=self.expected))
        self.owned=self.stack.enter_context(patch.object(h.startup.NativeStoreStartup,'_owned'))
        self.drained=self.stack.enter_context(patch.object(h.startup.NativeStoreStartup,'_drained'))
        self.stack.enter_context(patch.object(h.startup.NativeStoreStartup,'status',side_effect=lambda:{'state':self.stores._stage,'storageReady':self.stores._stage=='VERIFIED','callerLeaseMayBeReleased':self.stores._stage=='CLOSED'}))
        def start():self.events.append('storage-start');self.stores._stage='VERIFIED';return self.stores.status()
        def close():self.events.append('storage-close');self.stores._stage='CLOSED'
        self.start=self.stack.enter_context(patch.object(h.startup.NativeStoreStartup,'start',side_effect=start))
        self.close=self.stack.enter_context(patch.object(h.startup.NativeStoreStartup,'close',side_effect=close))
        def probe(*a):self.events.append('live-probe');return {'state':'NATIVE_STORE_CONNECTIONS_VERIFIED','epochObserved':self.expected.epoch,'runtimeAdmissionAuthorized':False}
        self.probe=self.stack.enter_context(patch.object(h.startup.live,'verify_live_stores',side_effect=probe))
        self.routes=[];self.runner=None;self.site=None;owner=self
        class App:
            def __init__(self,**kw):owner.events.append('http-app');self.router=SimpleNamespace(add_route=lambda *a:owner.routes.append(a));owner.app_kw=kw
        class Runner:
            def __init__(self,app,**kw):owner.events.append('http-runner');owner.runner=self;owner.runner_kw=kw;self.addresses=[]
            async def setup(self):owner.events.append('http-setup')
            async def cleanup(self):owner.events.append('http-cleanup')
        class Site:
            def __init__(self,runner,host,port,**kw):owner.events.append('http-site');owner.site=self;owner.site_args=(host,port,kw);self.runner=runner
            async def start(self):owner.events.append('http-bind');self.runner.addresses=[('127.0.0.1',45678)]
        self.web=self.stack.enter_context(patch.object(h,'_web',return_value=SimpleNamespace(Application=App,AppRunner=Runner,TCPSite=Site,json_response=Response)))
        self.token='0123456789abcdef'*4
    def obj(self,**kw):return h.StorageReadinessHttp(self.stores,token=self.token,**kw)
    def request(self,path='/health/ready',method='GET',headers=None,body=False,length=0):
        if headers is None:headers=[('Authorization','Bearer '+self.token),('Host','127.0.0.1:45678')]
        return SimpleNamespace(headers=Headers(headers),raw_path=path,method=method,can_read_body=body,content_length=length)
    async def serving(self):o=self.obj();await o.start();return o
    async def test_storage_then_probe_before_http_bind(self):
        o=await self.serving()
        self.assertEqual(self.events,['storage-start','live-probe','http-app','http-runner','http-setup','http-site','http-bind'])
        self.assertEqual(self.site_args,('127.0.0.1',0,{'backlog':16,'reuse_address':False,'reuse_port':False}))
        self.assertIsNone(self.runner_kw['access_log']);self.assertEqual(self.runner_kw['shutdown_timeout'],2)
        self.assertEqual(len(self.routes),1);self.assertEqual(self.routes[0][:2],('*','/{tail:.*}'))
        self.assertNotIn(self.token,json.dumps(o.status()))
    async def test_ready_reprobes_no_dispatch_authority(self):
        o=await self.serving();r=await o._handle(self.request())
        self.assertEqual(r.status,200);self.assertTrue(r.body['storageReady']);self.assertFalse(r.body['runtimeAdmissionAuthorized'])
        self.assertFalse(r.body['agentRoutesEnabled']);self.assertEqual(self.probe.call_count,2)
        self.assertEqual(r.headers['Cache-Control'],'no-store');self.assertTrue(r.closed)
    async def test_storage_failure_never_constructs_http(self):
        self.start.side_effect=RuntimeError('private error');o=self.obj()
        with self.assertRaisesRegex(h.ReadinessRejected,'start_failed'):await o.start()
        self.web.assert_not_called();self.close.assert_not_called();self.assertEqual(o.status()['state'],'FAILED')
    async def test_live_prebind_failure_no_socket(self):
        self.probe.side_effect=RuntimeError('private error');o=self.obj()
        with self.assertRaises(h.ReadinessRejected):await o.start()
        self.web.assert_not_called();self.close.assert_not_called()
    async def test_cancelled_start_not_replayed(self):
        self.start.side_effect=asyncio.CancelledError;o=self.obj()
        with self.assertRaises(asyncio.CancelledError):await o.start()
        with self.assertRaisesRegex(h.ReadinessRejected,'not_fresh'):await o.start()
        self.assertEqual(self.start.call_count,1);self.web.assert_not_called()
    async def test_start_twice_not_advance_again(self):
        o=await self.serving()
        with self.assertRaisesRegex(h.ReadinessRejected,'not_fresh'):await o.start()
        self.assertEqual(self.start.call_count,1)
    async def test_non_new_startup_refused(self):
        self.stores._stage='VERIFIED'
        with self.assertRaisesRegex(h.ReadinessRejected,'fresh_startup'):self.obj()
    async def test_exact_startup_required(self):
        with self.assertRaisesRegex(h.ReadinessRejected,'native_startup'):h.StorageReadinessHttp({},token=self.token)
    async def test_invalid_token_or_port_no_effect(self):
        for token in ('',self.token+'x',self.token.upper(),None,True,'token'+chr(10)):
            with self.subTest(token=repr(token)),self.assertRaises(h.ReadinessRejected):h.StorageReadinessHttp(self.stores,token=token)
        for port in (-1,65536,True,'80'):
            with self.subTest(port=port),self.assertRaises(h.ReadinessRejected):self.obj(port=port)
        self.start.assert_not_called();self.web.assert_not_called()
    async def test_auth_missing_wrong_or_duplicate_no_probe(self):
        o=await self.serving();n=self.probe.call_count
        for auth in ([],[('Authorization','Bearer wrong')],[('Authorization','Bearer '+self.token),('authorization','Bearer '+self.token)]):
            self.assertEqual((await o._handle(self.request(headers=auth+[('Host','127.0.0.1:45678')]))).status,401)
        self.assertEqual(self.probe.call_count,n)
    async def test_nonascii_authorization_refused_without_exception(self):
        o=await self.serving()
        for value in ('Bearer '+chr(255),'Bearer '+chr(0xdcff)):
            reply=await o._handle(self.request(headers=[('Authorization',value),('Host','127.0.0.1:45678')]))
            self.assertEqual(reply.status,401)
        self.assertEqual(self.probe.call_count,1)
    async def test_host_origin_body_refused(self):
        o=await self.serving();base=[('Authorization','Bearer '+self.token)]
        for headers in ([('Host','evil.example')],[('Host','127.0.0.1:45678')]*2,[('Host','127.0.0.1:45678'),('Origin','https://example.invalid')]):
            self.assertEqual((await o._handle(self.request(headers=base+headers))).status,400)
        for body,length in ((True,None),(False,1),(True,0)):
            self.assertEqual((await o._handle(self.request(body=body,length=length))).status,400)
        self.assertEqual(self.probe.call_count,1)
    async def test_agent_query_and_encoded_routes_not_served(self):
        o=await self.serving()
        for path in ('/v1/runs','/v1/chat/completions','/api/sessions','/health/ready?x=1','/health/%72eady','//health/ready','/p/user/health/ready'):
            self.assertEqual((await o._handle(self.request(path=path))).status,404,path)
        self.assertEqual(self.probe.call_count,1)
    async def test_get_only(self):
        o=await self.serving()
        for method in ('POST','HEAD','OPTIONS','TRACE','DELETE'):self.assertEqual((await o._handle(self.request(method=method))).status,405)
        self.assertEqual(self.probe.call_count,1)
    async def test_liveness_does_not_claim_storage(self):
        o=await self.serving();self.probe.side_effect=AssertionError('must not probe')
        r=await o._handle(self.request(path='/health/live'))
        self.assertEqual(r.status,200);self.assertEqual(r.body['scope'],'process_liveness_only');self.assertNotIn('storageReady',r.body)
    async def test_lease_loss_monotonic_revocation(self):
        o=await self.serving();self.owned.side_effect=RuntimeError('sensitive path')
        r=await o._handle(self.request());self.assertEqual(r.status,503);self.assertFalse(r.body['storageReady']);self.assertNotIn('sensitive',json.dumps(r.body))
        self.owned.side_effect=None;n=self.probe.call_count
        self.assertEqual((await o._handle(self.request())).status,503);self.assertEqual(self.probe.call_count,n)
    async def test_epoch_probe_failure_never_closes_or_mutates(self):
        o=await self.serving();self.probe.side_effect=ValueError('drift')
        self.assertEqual((await o._handle(self.request())).status,503);self.close.assert_not_called();self.assertEqual(self.start.call_count,1)
    async def test_handle_replacement_refused_before_probe(self):
        o=await self.serving();self.state._conn=object();n=self.probe.call_count
        self.assertEqual((await o._handle(self.request())).status,503);self.assertEqual(self.probe.call_count,n)
    async def test_expectation_replacement_refused(self):
        o=await self.serving();self.expectation.return_value=replace(self.expected,epoch=2)
        self.assertEqual((await o._handle(self.request())).status,503)
    async def test_false_live_success_refused(self):
        o=await self.serving();self.probe.side_effect=None;self.probe.return_value={'state':'NATIVE_STORE_CONNECTIONS_VERIFIED','epochObserved':999,'runtimeAdmissionAuthorized':False}
        self.assertEqual((await o._handle(self.request())).status,503)
    async def test_stop_revokes_before_await_then_drains_before_stores(self):
        o=await self.serving();observed=[]
        async def cleanup():
            self.events.append('cleanup-begin');observed.append(await o._handle(self.request()))
            self.close.assert_not_called();await asyncio.sleep(0);self.events.append('cleanup-end')
        self.runner.cleanup=cleanup;await o.close()
        self.assertEqual(observed[0].status,503);self.assertEqual(self.events[-3:],['cleanup-begin','cleanup-end','storage-close'])
        self.assertTrue(o.status()['callerLeaseMayBeReleased']);self.assertFalse(o.status()['httpCleanupPending'])
    async def test_http_cleanup_failure_retains_stores_no_retry(self):
        o=await self.serving();self.runner.cleanup=AsyncMock(side_effect=RuntimeError('unknown'))
        with self.assertRaisesRegex(h.ReadinessRejected,'http_close_unconfirmed'):await o.close()
        self.close.assert_not_called();self.assertEqual(o.status()['state'],'CLOSE_UNKNOWN')
        with self.assertRaisesRegex(h.ReadinessRejected,'close_unknown'):await o.close()
        self.assertEqual(self.runner.cleanup.call_count,1)
    async def test_cancelled_cleanup_retains_stores(self):
        o=await self.serving();self.runner.cleanup=AsyncMock(side_effect=asyncio.CancelledError)
        with self.assertRaises(asyncio.CancelledError):await o.close()
        self.close.assert_not_called();self.assertEqual(o.status()['state'],'CLOSE_UNKNOWN')
    async def test_storage_close_refusal_leaves_http_closed(self):
        o=await self.serving();runner=self.runner;runner.cleanup=AsyncMock();self.close.side_effect=RuntimeError('transaction')
        with self.assertRaisesRegex(h.ReadinessRejected,'storage_close_refused'):await o.close()
        self.assertEqual(o.status()['state'],'HTTP_CLOSED');self.assertFalse(o.status()['httpCleanupPending'])
        self.close.side_effect=lambda:setattr(self.stores,'_stage','CLOSED');await o.close()
        self.assertEqual(runner.cleanup.call_count,1)
    async def test_close_once_and_secret_not_returned(self):
        o=await self.serving();await o.close();await o.close()
        self.assertEqual(self.close.call_count,1);self.assertNotIn(self.token,json.dumps(o.status()));self.assertEqual(o._authorization,b'')
    async def test_wrong_actor_and_loop_cannot_operate(self):
        o=await self.serving();self.actor_fn.return_value=(999,23001,23003,1)
        for fn in (o.start,o.close):
            with self.assertRaisesRegex(h.ReadinessRejected,'other_actor'):await fn()
        self.actor_fn.return_value=self.actor
        with patch.object(h.asyncio,'get_running_loop',return_value=object()):
            with self.assertRaisesRegex(h.ReadinessRejected,'other_loop'):o.status()
    async def test_setup_failure_requires_explicit_cleanup(self):
        async def fail(runner):raise RuntimeError('setup')
        self.web.return_value.AppRunner.setup=fail;o=self.obj()
        with self.assertRaises(h.ReadinessRejected):await o.start()
        self.close.assert_not_called();await o.close();self.assertEqual(self.events[-2:],['http-cleanup','storage-close'])
class MimeConfigurationTests(unittest.TestCase):
    def test_cold_stdlib_mime_does_not_read_known_system_files(self):
        import subprocess
        code="""import sys,mimetypes
from pathlib import Path
sys.path.insert(0,sys.argv[1])
import gateway_http_readiness as runtime
from types import SimpleNamespace
expected=object();sys.modules['aiohttp']=SimpleNamespace(web=expected)
assert not mimetypes.inited
original=mimetypes.knownfiles
opened=[]
def audit(event,args):
 if event=='open' and isinstance(args[0],str) and args[0] in original:
  opened.append(args[0]);raise AssertionError('unexpected_system_mime_read')
sys.addaudithook(audit)
assert runtime._web() is expected
assert mimetypes.inited and mimetypes.knownfiles is original and not opened
assert mimetypes.guess_type('owned.json')[0]=='application/json'
"""
        r=subprocess.run([sys.executable,'-I','-B','-c',code,str(ROOT/'packages/claw-hermes')],capture_output=True,text=True,timeout=10)
        self.assertEqual(r.returncode,0,r.stderr)
    def test_existing_mime_database_is_not_reconfigured(self):
        import mimetypes
        sentinel=object()
        with patch.object(mimetypes,'inited',True),patch.object(mimetypes,'init') as init,patch.dict(sys.modules,{'aiohttp':SimpleNamespace(web=sentinel)}):
            self.assertIs(h._web(),sentinel)
        init.assert_not_called()
    def test_failed_mime_initialization_restores_public_configuration(self):
        import mimetypes
        original=mimetypes.knownfiles
        with patch.object(mimetypes,'inited',False),patch.object(mimetypes,'init',side_effect=RuntimeError('owned-init-fail')):
            with self.assertRaises(RuntimeError):h._web()
        self.assertIs(mimetypes.knownfiles,original)

if __name__=='__main__':unittest.main()
