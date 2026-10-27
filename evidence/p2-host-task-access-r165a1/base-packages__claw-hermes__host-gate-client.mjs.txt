/** One-use host admission client. No raw-start fallback, provider or task queue. */
import {HermesRunsClient, HarnessError} from './hermes-runs.mjs';
const BASE='/alaz/host/v1';
const ID=/^[a-f0-9]{32}$/;
const KEY=/^ah1-[a-f0-9]{32}-[a-f0-9]{32}$/;
const RUN=/^run_[a-f0-9]{32}$/;
const STATUSES=new Set(['queued','started','running','stopping','waiting_for_approval','completed','failed','cancelled','interrupted','unknown']);
function fail(code, details={}) { throw new HarnessError(code, details); }
function plain(value) { return value && typeof value==='object' && !Array.isArray(value) && Object.getPrototypeOf(value)===Object.prototype; }
function text(value,limit) {return typeof value==='string' && value.trim().length>0 && Buffer.byteLength(value)<=limit;}

export class HostGateClient {
  #base; #token; #timeout; #limit; #runs; #permits=new WeakMap(); #attempted=new Set(); #executionRequired; #isolatedReadRequired; #providerBrokerRequired;
  constructor(options={}) {
    // Reuse the proven endpoint/credential/timeout guards and readonly run observer.
    if(options.requireExecution!==undefined&&typeof options.requireExecution!=='boolean')fail('invalid_execution_requirement');
    if(options.requireIsolatedRead!==undefined&&typeof options.requireIsolatedRead!=='boolean')fail('invalid_isolation_requirement');
    if(options.requireProviderBroker!==undefined&&typeof options.requireProviderBroker!=='boolean')fail('invalid_provider_broker_requirement');
    this.#providerBrokerRequired=options.requireProviderBroker===true;
    if(this.#providerBrokerRequired&&options.requireExecution===false)fail('broker_requires_execution_boundary');
    this.#isolatedReadRequired=options.requireIsolatedRead===true;
    if(this.#isolatedReadRequired&&options.requireExecution===false)fail('isolation_requires_execution_boundary');
    this.#executionRequired=options.requireExecution===true||this.#isolatedReadRequired||this.#providerBrokerRequired;
    this.#runs=new HermesRunsClient(options);
    this.#base=new URL(options.baseUrl).origin;this.#token=options.token;
    this.#timeout=options.requestTimeoutMs??5000;this.#limit=options.maxResponseBytes??1048576;
  }
  async #request(method,path,{body,key,signal,expected=200,requireBoundaries=true}={}) {
    if(signal?.aborted) fail('aborted_before_request',{mayHaveBeenAccepted:false});
    const timeout=new AbortController();const timer=setTimeout(()=>timeout.abort(),this.#timeout);
    const write=method!=='GET';
    try {
      const response=await fetch(this.#base+path,{method,redirect:'error',
        signal:signal?AbortSignal.any([signal,timeout.signal]):timeout.signal,
        headers:{Authorization:'Bearer '+this.#token,Accept:'application/json',
          ...(requireBoundaries&&this.#executionRequired?{'X-Alaz-Execution-Version':'1'}:{}),
          ...(requireBoundaries&&this.#isolatedReadRequired?{'X-Alaz-Isolated-Read-Version':'1'}:{}),
          ...(requireBoundaries&&this.#providerBrokerRequired?{'X-Alaz-Provider-Broker-Version':'1'}:{}),
          ...(body===undefined?{}:{'Content-Type':'application/json'}),...(key?{'Idempotency-Key':key}:{})},
        ...(body===undefined?{}:{body:JSON.stringify(body)})});
      const reader=response.body?.getReader();const chunks=[];let total=0;
      try {
        if(!reader) fail('invalid_host_response');
        if(Number(response.headers.get('content-length')||0)>this.#limit) fail('host_response_too_large');
        while(true) {
          const {value,done}=await reader.read();if(done)break;
          total+=value.length;if(total>this.#limit)fail('host_response_too_large');chunks.push(value);
        }
      } finally {await reader?.cancel().catch(()=>{});}
      const isJson=/^application\/json(?:;|$)/i.test(response.headers.get('content-type')||'');
      let value=null;
      if(isJson) {try {value=JSON.parse(Buffer.concat(chunks).toString('utf8'));}
        catch {if(response.status===expected)fail('invalid_host_json');}}
      if(response.status!==expected) {
        const code=plain(value)&&value.hostGateVersion===1&&plain(value.error)&&/^[a-z_]{1,80}$/.test(value.error.code)?value.error.code:null;
        fail('host_http_'+response.status,{httpStatus:response.status,hostCode:code,
          mayHaveBeenAccepted:write&&response.status>=500,retryAllowed:false});
      }
      if(!isJson)fail('invalid_host_response');
      return value;
    } catch(error) {
      if(error instanceof HarnessError) {
        if(error.mayHaveBeenAccepted===undefined)error.mayHaveBeenAccepted=write;
        error.retryAllowed=false;throw error;
      }
      fail(write?'host_write_outcome_unknown':'host_transport_error',{mayHaveBeenAccepted:write,retryAllowed:false});
    } finally {clearTimeout(timer);}
  }
  async capabilities({signal}={}) {
    const c=await this.#request('GET',BASE+'/capabilities',{signal});
    if(!plain(c)||c.hostGateVersion!==1||c.dispatchPath!==BASE+'/dispatch'||c.nativeStoreOwner!==true
      ||c.dispatchAtMostOnce!==true||c.automaticRetry!==false||c.scope!=='default_profile_new_run')fail('host_gate_required');
    if(this.#executionRequired&&c.executionBoundaryVersion!==1)fail('execution_boundary_required');
    if(this.#providerBrokerRequired&&(c.providerBrokerVersion!==1||c.providerBrokerBackend!=='linux_unix_credential_broker'))fail('provider_broker_required');
    if(this.#isolatedReadRequired&&(c.isolatedReadBoundaryVersion!==1||c.isolatedReadBackend!=='linux_docker_native_terminal'))fail('isolated_read_boundary_required');
    return Object.freeze(structuredClone(c));
  }
  async prepare(request,{signal}={}) {
    if(!plain(request))fail('invalid_host_intent',{mayHaveBeenAccepted:false});
    const fields=Object.getOwnPropertyDescriptors(request),keys=Reflect.ownKeys(fields);
    if(keys.some(k=>typeof k!=='string')||keys.sort().join(',')!=='input,model,requestId'
      ||keys.some(k=>!Object.hasOwn(fields[k],'value')))fail('invalid_host_intent',{mayHaveBeenAccepted:false});
    const requestId=fields.requestId.value,body=Object.freeze({input:fields.input.value,model:fields.model.value});
    if(typeof requestId!=='string'||!ID.test(requestId)||!text(body.input,65536)||!text(body.model,200))
      fail('invalid_host_intent',{mayHaveBeenAccepted:false});
    if(this.#attempted.has(requestId))fail('host_dispatch_already_attempted',{mayHaveBeenAccepted:true});
    if(this.#executionRequired)await this.capabilities({signal});
    const row=await this.#request('POST',BASE+'/intents',{body:{requestId,body},signal,expected:201});
    if(!plain(row)||row.hostGateVersion!==1||row.requestId!==requestId||typeof row.idempotencyKey!=='string'
      ||!KEY.test(row.idempotencyKey)||!row.idempotencyKey.endsWith('-'+requestId)||row.retryAllowed!==false
      ||typeof row.replayed!=='boolean'||!Number.isSafeInteger(row.expiresAtMs)||row.expiresAtMs<=0
      ||!['issued','consumed'].includes(row.dispatchState))fail('invalid_host_permit',{mayHaveBeenAccepted:true});
    if(row.dispatchState!=='issued')fail('host_dispatch_already_attempted',{mayHaveBeenAccepted:true,retryAllowed:false});
    const permit=Object.freeze({requestId,idempotencyKey:row.idempotencyKey,expiresAtMs:row.expiresAtMs});
    this.#permits.set(permit,{requestId,body,key:row.idempotencyKey});return permit;
  }
  async dispatch(permit,{signal}={}) {
    const value=this.#permits.get(permit);
    if(!value)fail('foreign_host_permit',{mayHaveBeenAccepted:false});
    if(signal?.aborted)fail('aborted_before_request',{mayHaveBeenAccepted:false});
    if(this.#attempted.has(value.requestId))fail('host_dispatch_already_attempted',{mayHaveBeenAccepted:true,retryAllowed:false});
    if(this.#executionRequired)await this.capabilities({signal});
    // A per-client guard adds no retry authority: durable enforcement is server-owned.
    this.#attempted.add(value.requestId);
    const result=await this.#request('POST',BASE+'/dispatch',{body:value.body,key:value.key,signal,expected:202});
    if(!plain(result)||typeof result.run_id!=='string'||!RUN.test(result.run_id)||!STATUSES.has(result.status)
      ||result.replayed!==false||(result.output!==undefined&&typeof result.output!=='string')
      ||(result.status==='completed'&&(result.completed===false||result.partial===true||result.interrupted===true||result.failed===true)))
      fail('invalid_host_admission',{mayHaveBeenAccepted:true,retryAllowed:false});
    return structuredClone(result);
  }
  async observeRequest(requestId,{signal}={}) {
    if(typeof requestId!=='string'||!ID.test(requestId))
      fail('invalid_request_id',{mayHaveBeenAccepted:false,retryAllowed:false});
    // Reading an existing reference does not require provider readiness, issue
    // another intent, or recreate a budget. Native run status is separate.
    const value=await this.#request('GET',BASE+'/requests/'+requestId,
      {signal,requireBoundaries:false});
    const states={
      not_found:[null,'retain_request_id_no_retry'],
      issued_not_dispatched:['issued','retain_issued_request_no_retry'],
      handoff_unresolved:['consumed','retain_consumed_request_no_retry'],
      native_run_located:['consumed','observe_existing_run'],
    };
    const fields=['hostGateVersion','requestObservationVersion','requestId','classification',
      'dispatchState','runId','snapshotOnly','writesPerformed','canonicalVerified',
      'retryAllowed','repairAllowed','requiresOperator','nextAction'];
    if(!plain(value)||Object.keys(value).sort().join(',')!==fields.sort().join(',')
      ||value.hostGateVersion!==1||value.requestObservationVersion!==1||value.requestId!==requestId
      ||typeof value.classification!=='string'||!Object.hasOwn(states,value.classification)||value.snapshotOnly!==true
      ||value.writesPerformed!==false||value.canonicalVerified!==false
      ||value.retryAllowed!==false||value.repairAllowed!==false)
      fail('invalid_request_observation',{mayHaveBeenAccepted:false,retryAllowed:false});
    const located=value.classification==='native_run_located';
    const [dispatchState,nextAction]=states[value.classification];
    if(value.dispatchState!==dispatchState||value.nextAction!==nextAction
      ||value.requiresOperator!==!located
      ||(located?typeof value.runId!=='string'||!RUN.test(value.runId):value.runId!==null))
      fail('invalid_request_observation',{mayHaveBeenAccepted:false,retryAllowed:false});
    return Object.freeze(structuredClone(value));
  }
  status(id,options) {return this.#runs.status(id,options);}
  resume(id,options) {return this.#runs.resume(id,options);}
  reconcile(id,options) {return this.#runs.reconcile(id,options);}
  stop(id,options) {return this.#runs.stop(id,options);}
}
