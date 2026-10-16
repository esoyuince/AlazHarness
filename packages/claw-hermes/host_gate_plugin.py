"""Required Alaz HTTP endpoints around native admission, not observer-based vetoes.

HostGateClient only posts to our dedicated dispatch URL. An unloaded/broken
plugin therefore causes404; it never falls back to raw /v1/runs. The bearer is
still a trusted local operator credential. No OS sandbox or whole-Gateway
multi-tenant security perimeter is claimed.
"""
from __future__ import annotations
import asyncio
import hashlib
import hmac
import inspect
import json
from pathlib import Path
import re
from host_gate import HostGateLedger, HostGatePolicy, HostGateError
from recovery_inspector import LocalRecoveryContext, _load

BASE='/alaz/host/v1'


def validate_native_adapter(adapter):
    if type(adapter).__module__!='gateway.platforms.api_server' or type(adapter).__name__!='APIServerAdapter':
        raise ValueError('native_api_adapter_required')
    source=Path(inspect.getfile(type(adapter))).resolve().parents[2]
    manifest=json.loads((Path(__file__).resolve().parents[2]/'config/host-gate/source-lock.json').read_text(encoding='utf-8'))
    for item in manifest['files']:
        p=source/item['path']
        if p.is_symlink() or hashlib.sha256(p.read_bytes()).hexdigest()!=item['sha256']:
            raise ValueError('unsupported_native_host_boundary')


def register(ctx):
    """Native PluginContext entrypoint; missing/invalid policy installs no routes."""
    value=ctx.get_config('policy')
    if type(value) is not dict or set(value)!={'allowed_models','max_issued','max_dispatches','validity_seconds'}:
        raise ValueError('explicit_host_policy_required')
    models=value['allowed_models']
    if type(models) is not list or any(type(m) is not str for m in models) or len(set(models))!=len(models):
        raise ValueError('invalid_model_allowlist')
    policy=HostGatePolicy(frozenset(models),value['max_issued'],value['max_dispatches'],value['validity_seconds'])
    execution_settings=ctx.get_config('execution')
    execution=None
    if execution_settings is not None:
        from execution_boundary import ExecutionBoundary
        execution=ExecutionBoundary(execution_settings)
        execution.register(ctx)
    ctx.register_platform_handler('api_server',lambda app,adapter:bind_host_gate(app,adapter,policy,execution=execution))


def bind_host_gate(app, adapter, policy: HostGatePolicy, *, execution=None):
    from aiohttp import web
    validate_native_adapter(adapter)
    if type(policy) is not HostGatePolicy or app.frozen or adapter._host!='127.0.0.1':
        raise ValueError('unsupported_host_listener')
    if 'alaz_host_gate_v1' in app:raise ValueError('duplicate_host_gate')
    if execution is not None:execution.bind(app,adapter)

    def current(request):
        # Never infer privilege from a room token, profile prefix, cookie or session header.
        if request.path.startswith('/p/') or adapter._room_grant_token(request):
            raise HostGateError('unsupported_host_scope')
        if len(request.headers.getall('Authorization',[]))!=1:raise HostGateError('authentication_required')
        token=adapter._expected_api_key()
        if type(token) is not str or not token or not hmac.compare_digest(request.headers['Authorization'],'Bearer '+token):
            raise HostGateError('authentication_required')
        if any(k.lower().startswith('x-hermes-') for k in request.headers) or request.query_string:
            raise HostGateError('unsupported_host_header_or_query')
        runner=adapter.gateway_runner;authority=runner.session_authority;desc=runner.session_runtime_descriptor
        if desc.get('state')!='ready' or getattr(authority,'retiring',False) or getattr(authority,'retired',False):
            raise HostGateError('native_owner_unavailable')
        context=LocalRecoveryContext(Path(authority.db.db_path).resolve().parent,token,authority.epoch,desc['instance_id'])
        return HostGateLedger(authority.db,context,policy)

    def error(exc):
        code=str(exc) if isinstance(exc,HostGateError) and re.fullmatch('[a-z_]{1,80}',str(exc)) else 'host_gate_unavailable'
        status=401 if code=='authentication_required' else (503 if code=='host_gate_unavailable' or code=='gate_storage_or_commit_unknown' else 409)
        return web.json_response({'hostGateVersion':1,'error':{'code':code},'retryAllowed':False},status=status)

    async def body(request):
        if request.content_type!='application/json' or request.headers.get('Content-Encoding') or request.charset not in (None,'utf-8','UTF-8'):
            raise HostGateError('unsupported_body_encoding')
        if request.content_length is None or not 0<request.content_length<=131072:
            raise HostGateError('bounded_body_required')
        try:return _load(await request.text(),131072)
        except (ValueError,TypeError,UnicodeError):raise HostGateError('invalid_host_json') from None

    async def issue(request):
        try:
            ledger=current(request);value=await body(request)
            if execution is not None:await execution.require_ready()
            if type(value) is not dict or set(value)!={'requestId','body'}:raise HostGateError('invalid_intent_request')
            row=await asyncio.to_thread(ledger.issue,value['requestId'],value['body'])
            return web.json_response({'hostGateVersion':1,'requestId':row['requestId'],'idempotencyKey':row['key'],
                'dispatchState':row['dispatchState'],'expiresAtMs':row['expiresAtMs'],'replayed':row['replayed'],
                'retryAllowed':False},status=201)
        except Exception as exc:return error(exc)

    async def dispatch(request):
        try:
            ledger=current(request);frozen=await body(request)
            if execution is not None:await execution.require_ready()
            if len(request.headers.getall('Idempotency-Key',[]))!=1:raise HostGateError('host_intent_required')
            await asyncio.to_thread(ledger.consume,request.headers['Idempotency-Key'],frozen)
            # Returning from _execute_write proves COMMIT. No forward on unknown commit.
            # Subsequent native refusal, timeout, disconnect or cancellation never refunds.
            return await adapter._handle_runs(request)
        except Exception as exc:return error(exc)

    async def capabilities(request):
        try:
            current(request)
            if execution is not None:await execution.require_ready()
            return web.json_response({'hostGateVersion':1,'dispatchPath':BASE+'/dispatch','nativeStoreOwner':True,
                'dispatchAtMostOnce':True,'automaticRetry':False,'modelTokenOrCostBudget':False,
                'toolSandbox':False,'scope':'default_profile_new_run','executionBoundaryVersion':1 if execution is not None else None,
                'providerBrokerVersion':1 if execution is not None and getattr(execution,'broker',None) is not None else None,
                'providerBrokerBackend':'linux_unix_credential_broker' if execution is not None and getattr(execution,'broker',None) is not None else None,
                'isolatedReadBoundaryVersion':1 if execution is not None and getattr(execution,'isolation',None) is not None else None,
                'isolatedReadBackend':'linux_docker_native_terminal' if execution is not None and getattr(execution,'isolation',None) is not None else None})
        except Exception as exc:return error(exc)

    @web.middleware
    async def gate(request,handler):
        # An installed extension also refuses alternative native write paths. This
        # does not claim to gate raw upstream when the extension is not installed.
        broker=request.headers.getall('X-Alaz-Provider-Broker-Version',[])
        if broker and (broker!=['1'] or execution is None or getattr(execution,'broker',None) is None):
            return error(HostGateError('provider_broker_required'))
        isolated=request.headers.getall('X-Alaz-Isolated-Read-Version',[])
        if isolated and (isolated!=['1'] or execution is None or getattr(execution,'isolation',None) is None):
            return error(HostGateError('isolated_read_boundary_required'))
        required=request.headers.getall('X-Alaz-Execution-Version',[])
        if required and (required!=['1'] or execution is None):
            return error(HostGateError('execution_boundary_required'))
        if request.method in ('GET','HEAD','OPTIONS'):return await handler(request)
        if execution is not None and request.method=='POST' and request.path=='/alaz/provider/v1/chat/completions':return await handler(request)
        if request.method=='POST' and request.path in (BASE+'/intents',BASE+'/dispatch'):
            return await handler(request)
        try:
            current(request)
            if request.method=='POST' and re.fullmatch(r'/v1/runs/run_[a-f0-9]{32}/stop',request.path):
                return await handler(request)
            raise HostGateError('host_route_not_enabled')
        except Exception as exc:return error(exc)

    app.middlewares.append(gate)
    app.router.add_post(BASE+'/intents',issue)
    app.router.add_post(BASE+'/dispatch',dispatch)
    app.router.add_get(BASE+'/capabilities',capabilities)
    app['alaz_host_gate_v1']=True
