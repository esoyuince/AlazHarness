"""Actual JS HostGateClient with a recorded fetch port, not a native Gateway."""
from pathlib import Path
import shutil
import subprocess
import unittest
ROOT=Path(__file__).resolve().parents[1]
BASE=r"""
import assert from 'node:assert/strict';
import {HostGateClient} from './packages/claw-hermes/host-gate-client.mjs';
const cap={hostGateVersion:1,dispatchPath:'/alaz/host/v1/dispatch',nativeStoreOwner:true,
 dispatchAtMostOnce:true,automaticRetry:false,scope:'default_profile_new_run',
 executionBoundaryVersion:1,isolatedReadBoundaryVersion:1,isolatedReadBackend:'linux_docker_native_terminal'};
const calls=[];
globalThis.fetch=async(url,options)=>{
 calls.push({url:String(url),...options});
 assert.equal(options.method,'GET','Unexpected write');
 return new Response(JSON.stringify(cap),{status:200,headers:{'Content-Type':'application/json'}});
};
const options={baseUrl:'http://127.0.0.1:19777',token:'test-fixture-bearer',requireIsolatedRead:true};
const request={requestId:'a'.repeat(32),input:'fixture',model:'fixed-model'};
"""
class IsolatedClientTests(unittest.TestCase):
    def js(self,text):
        result=subprocess.run([shutil.which('node') or 'node','--input-type=module','-e',BASE+text],cwd=ROOT,
            capture_output=True,text=True,encoding='utf-8',timeout=20)
        self.assertEqual(result.returncode,0,result.stderr)
    def test_explicit_isolation_capability(self):
        self.js("assert.equal((await new HostGateClient(options).capabilities()).isolatedReadBoundaryVersion,1);")
    def test_both_required_version_headers(self):
        self.js("await new HostGateClient(options).capabilities();assert.equal(calls[0].headers['X-Alaz-Execution-Version'],'1');assert.equal(calls[0].headers['X-Alaz-Isolated-Read-Version'],'1');")
    def test_missing_isolation_refuses_before_issue(self):
        self.js("delete cap.isolatedReadBoundaryVersion;await assert.rejects(new HostGateClient(options).prepare(request),{code:'isolated_read_boundary_required'});assert.equal(calls.length,1);")
    def test_wrong_backend_refuses(self):
        self.js("cap.isolatedReadBackend='local';await assert.rejects(new HostGateClient(options).capabilities(),{code:'isolated_read_boundary_required'});")
    def test_bool_version_not_one(self):
        self.js("cap.isolatedReadBoundaryVersion=true;await assert.rejects(new HostGateClient(options).capabilities(),{code:'isolated_read_boundary_required'});")
    def test_string_version_not_one(self):
        self.js("cap.isolatedReadBoundaryVersion='1';await assert.rejects(new HostGateClient(options).capabilities(),{code:'isolated_read_boundary_required'});")
    def test_execution_version_also_required(self):
        self.js("cap.executionBoundaryVersion=null;await assert.rejects(new HostGateClient(options).capabilities(),{code:'execution_boundary_required'});")
    def test_explicit_execution_false_is_conflict(self):
        self.js("assert.throws(()=>new HostGateClient({...options,requireExecution:false}),{code:'isolation_requires_execution_boundary'});assert.equal(calls.length,0);")
    def test_invalid_isolation_requirement(self):
        self.js("for(const value of [1,'true',{},null])assert.throws(()=>new HostGateClient({...options,requireIsolatedRead:value}),{code:'invalid_isolation_requirement'});")
    def test_legacy_mode_is_not_relabelled_isolated(self):
        self.js("delete cap.isolatedReadBoundaryVersion;delete cap.isolatedReadBackend;await new HostGateClient({...options,requireIsolatedRead:false}).capabilities();assert.equal(calls[0].headers['X-Alaz-Isolated-Read-Version'],undefined);")
    def test_http_unavailable_never_raw_start_fallback(self):
        self.js("globalThis.fetch=async(url,options)=>{calls.push({url:String(url),...options});return new Response('{}',{status:404,headers:{'Content-Type':'application/json'}});};await assert.rejects(new HostGateClient(options).prepare(request),{code:'host_http_404'});assert.equal(calls.length,1);assert.ok(calls[0].url.endsWith('/capabilities'));")
    def test_bad_capability_never_post(self):
        self.js("cap.isolatedReadBackend=null;await assert.rejects(new HostGateClient(options).prepare(request));assert.ok(calls.every(c=>c.method==='GET'));")
if __name__=='__main__':unittest.main()
