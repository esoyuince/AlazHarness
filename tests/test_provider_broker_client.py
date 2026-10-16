"""Real HostGateClient with controlled fetch responses, no native Gateway."""
from pathlib import Path
import shutil
import subprocess
import unittest
ROOT=Path(__file__).resolve().parents[1]
BASE=r"""
import assert from 'node:assert/strict';
import {HostGateClient} from './packages/claw-hermes/host-gate-client.mjs';
const cap={hostGateVersion:1,dispatchPath:'/alaz/host/v1/dispatch',nativeStoreOwner:true,
 dispatchAtMostOnce:true,automaticRetry:false,scope:'default_profile_new_run',executionBoundaryVersion:1,
 providerBrokerVersion:1,providerBrokerBackend:'linux_unix_credential_broker'};
const calls=[];
globalThis.fetch=async(url,options)=>{calls.push({url:String(url),...options});assert.equal(options.method,'GET');return new Response(JSON.stringify(cap),{status:200,headers:{'Content-Type':'application/json'}});};
const options={baseUrl:'http://127.0.0.1:19777',token:'test-bearer',requireProviderBroker:true};
const request={requestId:'a'.repeat(32),input:'fixture',model:'test'};
"""
class BrokerClientContracts(unittest.TestCase):
    def js(self,code):
        p=subprocess.run([shutil.which('node') or 'node','--input-type=module','-e',BASE+code],cwd=ROOT,capture_output=True,text=True,encoding='utf-8',timeout=15)
        self.assertEqual(p.returncode,0,p.stderr)
    def test_required_capability(self):self.js("assert.equal((await new HostGateClient(options).capabilities()).providerBrokerVersion,1);")
    def test_broker_and_execution_headers(self):self.js("await new HostGateClient(options).capabilities();assert.equal(calls[0].headers['X-Alaz-Execution-Version'],'1');assert.equal(calls[0].headers['X-Alaz-Provider-Broker-Version'],'1');")
    def test_missing_no_post(self):self.js("delete cap.providerBrokerVersion;await assert.rejects(new HostGateClient(options).prepare(request),{code:'provider_broker_required'});assert.equal(calls.length,1);")
    def test_wrong_backend_no_post(self):self.js("cap.providerBrokerBackend='direct';await assert.rejects(new HostGateClient(options).prepare(request),{code:'provider_broker_required'});")
    def test_bool_version(self):self.js("cap.providerBrokerVersion=true;await assert.rejects(new HostGateClient(options).capabilities(),{code:'provider_broker_required'});")
    def test_string_version(self):self.js("cap.providerBrokerVersion='1';await assert.rejects(new HostGateClient(options).capabilities(),{code:'provider_broker_required'});")
    def test_missing_execution(self):self.js("cap.executionBoundaryVersion=null;await assert.rejects(new HostGateClient(options).capabilities(),{code:'execution_boundary_required'});")
    def test_explicit_execution_false(self):self.js("assert.throws(()=>new HostGateClient({...options,requireExecution:false}),{code:'broker_requires_execution_boundary'});assert.equal(calls.length,0);")
    def test_invalid_option(self):self.js("for(const v of [1,'true',{},null])assert.throws(()=>new HostGateClient({...options,requireProviderBroker:v}),{code:'invalid_provider_broker_requirement'});")
    def test_legacy_not_claimed_brokered(self):self.js("delete cap.providerBrokerVersion;await new HostGateClient({...options,requireProviderBroker:false}).capabilities();assert.equal(calls[0].headers['X-Alaz-Provider-Broker-Version'],undefined);")
    def test_no_raw_fallback_on_network_error(self):self.js("globalThis.fetch=async(url,o)=>{calls.push({url:String(url),...o});throw Error('offline');};await assert.rejects(new HostGateClient(options).prepare(request),{code:'host_transport_error'});assert.equal(calls.length,1);assert.ok(calls[0].url.endsWith('/capabilities'));")
    def test_recheck_before_dispatch(self):self.js("let n=0;globalThis.fetch=async(url,o)=>{calls.push({url:String(url),...o});let v=cap,status=200;if(o.method==='POST'){assert.ok(String(url).endsWith('/intents'));status=201;v={hostGateVersion:1,requestId:request.requestId,idempotencyKey:'ah1-'+ 'b'.repeat(32)+'-'+request.requestId,retryAllowed:false,replayed:false,expiresAtMs:999999,dispatchState:'issued'};}return new Response(JSON.stringify(v),{status,headers:{'Content-Type':'application/json'}});};const c=new HostGateClient(options);const p=await c.prepare(request);cap.providerBrokerVersion=null;await assert.rejects(c.dispatch(p),{code:'provider_broker_required'});assert.equal(calls.filter(x=>x.method==='POST').length,1);")

if __name__=='__main__':unittest.main()
