"""Dedicated profile egress and real registry-handler boundary.

Only the configured local chat-completions route and read-only file tool family
are qualified. Not an OS sandbox or a guarantee about unconfigured clients.
"""
from __future__ import annotations
import asyncio
import hashlib
import hmac
import json
import math
import os
from pathlib import Path
import re
import stat
from urllib.parse import urlsplit
from execution_budget import ExecutionDenied, ExecutionPolicy, ExecutionLedger
from recovery_inspector import LocalRecoveryContext, _json, _load

PROVIDER_BASE='/alaz/provider/v1'
FILE_TOOLS=('read_file','write_file','patch','search_files')


def scoped_file(path,allowed):
    if type(path) is not str or not path or len(path)>4096 or '\x00' in path:
        raise ExecutionDenied('invalid_read_path')
    # Reject network/device prefixes before any resolve/stat could contact them.
    if path.startswith(('\\','//')) or (os.name=='nt' and ':' in path[2:]):
        raise ExecutionDenied('unsupported_read_path')
    candidate=Path(path)
    if not candidate.is_absolute():raise ExecutionDenied('absolute_read_path_required')
    for part in (candidate,*candidate.parents):
        if part.is_symlink() or (hasattr(part,'is_junction') and part.is_junction()):raise ExecutionDenied('linked_read_path')
    canonical=candidate.resolve(strict=True)
    if canonical not in allowed or canonical.suffix.lower()!='.txt':raise ExecutionDenied('read_not_allowed')
    mode=canonical.stat()
    if not stat.S_ISREG(mode.st_mode) or mode.st_nlink!=1 or not 0<=mode.st_size<=65536:
        raise ExecutionDenied('unsupported_read_file')
    return str(canonical)


class GuardedFileTools:
    def __init__(self,allowed_files,ledger,*,isolation=None):
        self.isolation=isolation
        if type(allowed_files) is not list or not 1<=len(allowed_files)<=32 or any(type(x) is not str for x in allowed_files):
            raise ExecutionDenied('explicit_read_allowlist_required')
        self.allowed=frozenset(Path(x) for x in allowed_files)
        if len(self.allowed)!=len(allowed_files):raise ExecutionDenied('duplicate_read_allowlist')
        self.allowed=frozenset(Path(scoped_file(x,self.allowed)) for x in allowed_files)
        self.ledger=ledger;self.handlers={};self.originals={};self.scope=None

    def register(self,ctx):
        from tools import file_tools
        from tools.registry import registry
        source=Path(file_tools.__file__).resolve().parents[1]
        lock=_load((Path(__file__).resolve().parents[2]/'config/execution-gate/source-lock.json').read_text(encoding='utf-8'))
        for item in lock['files']:
            path=source/item['path']
            if path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest()!=item['sha256']:raise ExecutionDenied('unsupported_native_execution_source')
        self.scope=ctx._manager.scope_key
        for name in FILE_TOOLS:
            original=registry.get_entry(name,scope=self.scope)
            expected=getattr(file_tools,{'read_file':'_handle_read_file','write_file':'_handle_write_file','patch':'_handle_patch','search_files':'_handle_search_files'}[name])
            if original is None or original.handler is not expected:raise ExecutionDenied('unexpected_native_file_handler')
            self.originals[name]=original
            def guarded(args,_name=name,**kwargs):
                if _name!='read_file':return _json({'error':{'code':'tool_not_allowed'},'retryAllowed':False})
                try:
                    value=_load(_json(args),16384)
                    if type(value) is not dict or not set(value)<={'path','offset','limit'} or 'path' not in value:raise ExecutionDenied('invalid_read_arguments')
                    canonical=scoped_file(value['path'],self.allowed)
                    for field,default,maximum in [('offset',1,100000),('limit',200,1000)]:
                        n=value.get(field,default)
                        if type(n) is not int or not 1<=n<=maximum:raise ExecutionDenied('invalid_read_pagination')
                    sid=kwargs.get('session_id')
                    if type(sid) is not str or not re.fullmatch('run_[a-f0-9]{32}',sid):raise ExecutionDenied('native_run_identity_required')
                    ledger=self.ledger()
                    def validate_session(c):
                        ledger._epoch(c)
                        row=c.execute('SELECT request_id FROM session_admissions WHERE request_id=? AND target_session_id=?',(sid,sid)).fetchone()
                        if row is None:raise ExecutionDenied('native_admission_required')
                    ledger._write(validate_session)
                    fingerprint=hashlib.sha256(_json({'name':'read_file','args':value,'session_id':sid}).encode()).hexdigest()
                    ticket=ledger.claim('read_file',fingerprint)
                    # Core handler, not an imitation file reader. Guards run after request rewriting.
                    if self.isolation is None:
                        result=self.originals['read_file'].handler(value|{'path':canonical},**kwargs)
                    else:
                        result=self.isolation.invoke(self.originals['read_file'].handler,value,canonical,kwargs,ledger,ticket)
                    ledger.settle(ticket['ticket'],None,'tool_return')
                    return result
                except Exception as exc:
                    code=str(exc) if isinstance(exc,ExecutionDenied) and re.fullmatch('[a-z_]{1,80}',str(exc)) else 'tool_guard_unavailable'
                    return _json({'error':{'code':code},'retryAllowed':False})
            handle=ctx.register_tool(name=name,toolset='file',schema=original.schema,handler=guarded,
                                     check_fn=original.check_fn,override=True)
            if handle is None:raise ExecutionDenied('file_guard_not_registered')
            self.handlers[name]=guarded
        self.verify()

    def verify(self):
        from tools.registry import registry
        for name in FILE_TOOLS:
            entry=registry.get_entry(name,scope=self.scope)
            if entry is None or entry.handler is not self.handlers.get(name):raise ExecutionDenied('file_guard_missing')


class ExecutionBoundary:
    def __init__(self,settings):
        required={'policy','provider_bearer','allowed_read_files'}
        if type(settings) is not dict or not required<=set(settings) or not set(settings)<=required|{'isolated_read','upstream_base_url','provider_broker','record_request_view'}:raise ExecutionDenied('explicit_execution_settings_required')
        value=settings['policy']
        if type(value) is not dict:raise ExecutionDenied('explicit_execution_policy_required')
        try:self.policy=ExecutionPolicy(**value)
        except TypeError:raise ExecutionDenied('invalid_execution_policy') from None
        self.broker=None;self.upstream=None;self.upstream_port=None
        if ('upstream_base_url' in settings)==('provider_broker' in settings):
            raise ExecutionDenied('exactly_one_provider_transport_required')
        if 'provider_broker' in settings:
            from provider_broker import ProviderBrokerClient
            self.broker=ProviderBrokerClient(settings['provider_broker'])
        else:
            u=urlsplit(settings['upstream_base_url'])
            if u.scheme!='http' or u.hostname!='127.0.0.1' or u.username or u.password or u.query or u.fragment or u.path!='/v1' or not u.port:
                raise ExecutionDenied('unsupported_upstream_endpoint')
            self.upstream=settings['upstream_base_url'];self.upstream_port=u.port
        self.record_request_view=settings.get('record_request_view',False)
        if type(self.record_request_view) is not bool:raise ExecutionDenied('invalid_request_view_setting')
        if self.record_request_view and self.broker is None:raise ExecutionDenied('request_view_requires_broker')
        token=settings['provider_bearer']
        if type(token) is not str or not re.fullmatch(r'[\x21-\x7e]{32,256}',token):raise ExecutionDenied('invalid_provider_credential')
        if self.broker is not None and token==self.broker.link.signing_key:raise ExecutionDenied('separate_broker_key_required')
        self.token=token;self.adapter=None;self.service_transport=None;self.service_owner=None;self._service_app=None
        self._service_profile_binding=None
        self._settings_digest=hashlib.sha256(_json(settings).encode()).hexdigest()
        self.isolation=None
        if 'isolated_read' in settings:
            from isolated_read import NativeReadIsolation
            self.isolation=NativeReadIsolation(settings['isolated_read'],self.ledger)
        self.tools=GuardedFileTools(settings['allowed_read_files'],self.ledger,isolation=self.isolation)

    def register(self,ctx):
        # Native plugin discovery can run on a worker while core imports wait.
        # Attach the reviewed file handlers only at the native pre-freeze factory.
        self.context=ctx
        if self.isolation is not None:self.isolation.register(ctx)

    def ledger(self):
        if self.adapter is None:raise ExecutionDenied('execution_boundary_not_bound')
        # Check revocation again at claim/settlement, including the actual tool path.
        self.validate_profile()
        runner=self.adapter.gateway_runner;authority=runner.session_authority;desc=runner.session_runtime_descriptor
        if self.service_transport is not None:
            try:
                # Native file tools call this from a physical worker thread.
                # Existing admitted work may settle during drain; this pure
                # check neither opens admission nor enters the owner loop.
                authority=self.service_transport.check_binding(for_admission=False,
                    app=self._service_app,adapter=self.adapter)
            except Exception:raise ExecutionDenied('execution_owner_unavailable') from None
        elif desc.get('state')!='ready' or getattr(authority,'retired',False) or getattr(authority,'retiring',False):raise ExecutionDenied('execution_owner_unavailable')
        token=self.adapter._expected_api_key()
        if token==self.token:raise ExecutionDenied('separate_provider_credential_required')
        if self.broker is not None and token==self.broker.link.signing_key:raise ExecutionDenied('separate_broker_key_required')
        context=LocalRecoveryContext(Path(authority.db.db_path).resolve().parent,token,authority.epoch,desc['instance_id'])
        return ExecutionLedger(authority.db,context,self.policy)

    def _check_service_config(self):
        binding=self._service_profile_binding
        if binding is None:return
        service_owner,owner,held,actor,receipt=binding
        try:
            # File tools run on native workers. Preserve original owner identity
            # without calling its main-thread-only lease/SQLite checks here.
            if not (self.service_owner is service_owner and service_owner._owner is owner
                    and owner._service_owner is service_owner and service_owner._held is held
                    and owner._held is held and owner._actor==actor and actor[0]==os.getpid()
                    and owner._service_profile is receipt and owner._service_profile_binding is receipt
                    and os.environ.get('HERMES_HOME')==receipt.home):
                raise ExecutionDenied('execution_service_profile_changed')
            from hermes_cli import config
            # Native home overrides outrank HERMES_HOME. A safe-worker snapshot
            # bypasses the selected file entirely, so it is not this protocol.
            if (str(config.get_config_path())!=str(held._home/'config.yaml')
                    or config._worker_config_snapshot() is not None):
                raise ExecutionDenied('execution_service_profile_changed')
            from gateway_service_profile import check_config
            check_config(held._home,uid=actor[1],gid=actor[2],
                         device=receipt.home_identity[0],expectation=receipt)
        except Exception:
            raise ExecutionDenied('execution_service_profile_changed') from None

    def validate_profile(self):
        from hermes_cli.config import load_config_readonly
        # This retains the actual native loader and its existing behavior. The
        # receipt qualifies selected raw bytes, not defaults, overlays or policy.
        self._check_service_config()
        try:cfg=load_config_readonly()
        finally:self._check_service_config()
        try:
            current=self.context.get_config('execution')
            current_digest=hashlib.sha256(_json(current).encode()).hexdigest()
        except Exception:
            raise ExecutionDenied('execution_settings_unavailable') from None
        if current_digest!=self._settings_digest:
            raise ExecutionDenied('execution_settings_changed')
        model=cfg.get('model',{})
        expected=f'http://127.0.0.1:{self.adapter._port}'+PROVIDER_BASE
        if model.get('base_url')!=expected or model.get('provider')!='custom' or model.get('default')!=self.policy.model:
            raise ExecutionDenied('model_route_not_guarded')
        if model.get('api_key')!=self.token:raise ExecutionDenied('explicit_provider_credential_required')
        if cfg.get('platform_toolsets',{}).get('api_server')!=['file']:
            raise ExecutionDenied('unqualified_tool_family')
        if cfg.get('gateway',{}).get('multiplex_profiles') is not False:raise ExecutionDenied('multiple_profiles_not_qualified')
        if self.upstream_port==self.adapter._port:raise ExecutionDenied('provider_routing_cycle')
        if self.isolation is not None:
            from isolated_read import BACKEND
            if cfg.get('terminal',{}).get('backend')!=BACKEND or cfg.get('terminal',{}).get('cwd')!='/workspace':
                raise ExecutionDenied('isolated_terminal_required')
            self.isolation.verify()
        self.tools.verify()

    async def require_ready(self):
        self.validate_profile()
        if self.broker is not None:await self.broker.ready()
        ledger=self.ledger()
        await asyncio.to_thread(ledger.initialize)
        state=await asyncio.to_thread(ledger.snapshot)
        if state['quarantined']:raise ExecutionDenied('execution_budget_quarantined')

    def bind(self,app,adapter,*,service_transport=None,service_owner=None):
        from aiohttp import web, ClientSession, ClientTimeout
        if self.adapter is not None and (self.service_transport is not None or service_transport is not None):
            raise ExecutionDenied('execution_boundary_already_bound')
        if service_transport is not None:
            from gateway.platforms.api_server_borrowed_transport import BorrowedHTTPTransport
            from gateway_service_runtime import BorrowedServiceOwner
            if type(service_transport) is not BorrowedHTTPTransport:raise ExecutionDenied('native_service_transport_required')
            if type(service_owner) is not BorrowedServiceOwner:raise ExecutionDenied('native_service_owner_required')
            owner=service_owner._owner
            receipt=getattr(owner,'_service_profile',None)
            if getattr(owner,'_service_profile_binding',None) is not receipt:
                raise ExecutionDenied('execution_service_profile_changed')
            if receipt is not None:
                from gateway_store_startup import NativeStoreStartup
                from gateway_service_profile import validate_expectation
                try:
                    validate_expectation(receipt)
                    if not (type(owner) is NativeStoreStartup and owner._service_profile_binding is receipt
                            and owner._service_owner is service_owner and owner._held is service_owner._held):
                        raise ExecutionDenied('execution_service_profile_changed')
                    self._service_profile_binding=(service_owner,owner,owner._held,owner._actor,receipt)
                except Exception:
                    raise ExecutionDenied('execution_service_profile_changed') from None
            self.service_transport=service_transport;self.service_owner=service_owner;self._service_app=app
        elif service_owner is not None:raise ExecutionDenied('native_service_transport_required')
        self.adapter=adapter
        self.tools.register(self.context)
        async def metadata(request):
            error=self._authenticate(request)
            if error:return self._error(error)
            try:
                self._require_service_execution()
                await self.require_ready()
                return web.json_response({'object':'list','data':[{'object':'model','id':self.policy.model,
                   'context_length':self.policy.tokens_per_attempt}]})
            except Exception:return self._error('execution_boundary_unavailable',403)

        async def provider(request):
            denied=self._authenticate(request)
            if denied:return self._error(denied)
            ticket=None;ledger=None
            try:
                self._require_service_execution()
                await self.require_ready()
                self._require_service_execution()
                if request.content_type!='application/json' or request.headers.get('Content-Encoding') or request.content_length is None or not 0<request.content_length<=2_000_000:
                    raise ExecutionDenied('unsupported_provider_body')
                body=_load(await request.text(),2_000_000)
                allowed_fields={'model','messages','tools','tool_choice','parallel_tool_calls','max_tokens','max_completion_tokens','temperature','top_p','frequency_penalty','presence_penalty','stop','stream','stream_options','user','seed','reasoning_effort','verbosity','response_format','n'}
                if type(body) is not dict or not set(body)<=allowed_fields or body.get('model')!=self.policy.model or type(body.get('messages')) is not list or not body['messages']:
                    raise ExecutionDenied('unsupported_provider_request')
                if 'parallel_tool_calls' in body and type(body['parallel_tool_calls']) is not bool:raise ExecutionDenied('invalid_parallel_tools')
                for name in ('temperature','top_p','frequency_penalty','presence_penalty'):
                    if name in body and (type(body[name]) not in (int,float) or not math.isfinite(body[name])):raise ExecutionDenied('invalid_sampling_parameter')
                if 'tools' in body:
                    if type(body['tools']) is not list or len(body['tools'])>len(FILE_TOOLS):raise ExecutionDenied('unqualified_provider_tools')
                    for tool in body['tools']:
                        if type(tool) is not dict or tool.get('type')!='function' or type(tool.get('function')) is not dict or tool['function'].get('name') not in FILE_TOOLS:raise ExecutionDenied('unqualified_provider_tools')
                if body.get('n',1)!=1 or type(body.get('n',1)) is not int or type(body.get('stream',False)) is not bool:
                    raise ExecutionDenied('unsupported_provider_multiplicity')
                for k in ('max_tokens','max_completion_tokens'):
                    if k in body and (type(body[k]) is not int or not 1<=body[k]<=self.policy.output_ceiling_tokens):raise ExecutionDenied('output_ceiling_exceeded')
                if 'max_tokens' not in body and 'max_completion_tokens' not in body:body['max_tokens']=self.policy.output_ceiling_tokens
                if 'max_tokens' in body and 'max_completion_tokens' in body:raise ExecutionDenied('ambiguous_output_ceiling')
                # This text-only adapter does not accept hidden remote image/audio retrieval.
                for message in body['messages']:
                    if type(message) is not dict or message.get('role') not in ('system','developer','user','assistant','tool') or (message.get('content') is not None and type(message['content']) is not str):
                        raise ExecutionDenied('unsupported_message_content')
                ledger=self.ledger();ticket=await asyncio.to_thread(ledger.claim,'provider',hashlib.sha256(_json(body).encode()).hexdigest())
                if self.broker is not None:
                    if self.record_request_view:
                        raw,status,content_type=await self.broker.send(ledger,ticket['ticket'],body,record_view=True)
                    else:
                        raw,status,content_type=await self.broker.send(ledger,ticket['ticket'],body)
                else:
                    # One physical HTTP call per durable reservation. No SDK/proxy retries.
                    async with ClientSession(timeout=ClientTimeout(total=30),trust_env=False,auto_decompress=False) as client:
                        async with client.post(self.upstream+'/chat/completions',json=body,headers={'Authorization':'Bearer '+self.token},allow_redirects=False) as response:
                            pieces=[];size=0
                            async for chunk in response.content.iter_chunked(65536):
                                size+=len(chunk)
                                if size>4_194_304:raise ExecutionDenied('provider_response_too_large')
                                pieces.append(chunk)
                            raw=b''.join(pieces);status=response.status;content_type=response.headers.get('Content-Type','')
                            if 300<=status<400:raise ExecutionDenied('provider_redirect_refused')
                usage=None
                if status==200:
                    if body.get('stream') and not content_type.lower().startswith('text/event-stream'):raise ExecutionDenied('invalid_provider_response')
                    if not body.get('stream') and not content_type.lower().startswith('application/json'):raise ExecutionDenied('invalid_provider_response')
                    usage=validate_provider_response(raw,streaming=body.get('stream',False),policy=self.policy)
                    await asyncio.to_thread(ledger.settle,ticket['ticket'],usage,'response' if usage is not None else 'unknown_usage')
                    return web.Response(body=raw,status=200,headers={'Content-Type':content_type})
                await asyncio.to_thread(ledger.settle,ticket['ticket'],None,'transport_error')
                return self._error('upstream_provider_refused',status if 400<=status<=599 else 502)
            except asyncio.CancelledError:
                # Outstanding reservation remains consumed even if response delivery is lost.
                raise
            except Exception as exc:
                code=str(exc) if isinstance(exc,ExecutionDenied) and re.fullmatch('[a-z_]{1,80}',str(exc)) else 'execution_boundary_unavailable'
                if ticket is not None and isinstance(exc,ExecutionDenied):
                    try:await asyncio.to_thread(ledger.quarantine)
                    except Exception:code='execution_storage_unconfirmed'
                return self._error(code,403)

        app.router.add_get(PROVIDER_BASE+'/models',metadata)
        app.router.add_post(PROVIDER_BASE+'/chat/completions',provider)
        app['alaz_execution_boundary_v1']=self

    def _require_service_execution(self):
        if self.service_transport is not None:
            try:
                self.service_owner.require_execution(transport=self.service_transport,
                    app=self._service_app,adapter=self.adapter)
            except Exception:raise ExecutionDenied('execution_service_unavailable') from None

    def _authenticate(self,request):
        if len(request.headers.getall('Authorization',[]))!=1 or not hmac.compare_digest(request.headers.get('Authorization',''),'Bearer '+self.token):return 'provider_authentication_required'
        if request.query_string or any(k.lower().startswith('x-hermes-') for k in request.headers):return 'provider_scope_not_supported'
        return None

    @staticmethod
    def _error(code,status=401):
        from aiohttp import web
        return web.json_response({'error':{'code':code,'message':code,'type':'permission_error'},'retryAllowed':False},status=status)

    @staticmethod
    def _usage(raw):
        if type(raw) is not dict or type(raw.get('prompt_tokens')) is not int or type(raw.get('completion_tokens')) is not int:
            raise ExecutionDenied('invalid_provider_usage')
        if 'total_tokens' in raw and (type(raw['total_tokens']) is not int or raw['total_tokens']!=raw['prompt_tokens']+raw['completion_tokens']):raise ExecutionDenied('contradictory_provider_usage')
        return {'input_tokens':raw['prompt_tokens'],'output_tokens':raw['completion_tokens']}


def validate_provider_response(raw,*,streaming,policy):
    """Validate every buffered SSE event, including compact data: lines and usage."""
    try:
        text=raw.decode('utf-8')
        if not streaming:
            frames=[_load(text,4_194_304)]
        else:
            events=[];parts=[]
            for line in text.replace('\r\n','\n').replace('\r','\n').split('\n'):
                if line=='':
                    if parts:events.append('\n'.join(parts));parts=[]
                elif line.startswith('data:'):parts.append(line[5:].removeprefix(' '))
                elif line.startswith(':') or line.startswith(('event:','id:','retry:')):continue
                else:raise ExecutionDenied('invalid_provider_sse')
            if parts:raise ExecutionDenied('incomplete_provider_sse')
            if not events or events[-1]!='[DONE]' or events.count('[DONE]')!=1:raise ExecutionDenied('incomplete_provider_sse')
            frames=[_load(value,4_194_304) for value in events[:-1]]
            if not frames:raise ExecutionDenied('empty_provider_sse')
        usage=None
        for frame in frames:
            if type(frame) is not dict or frame.get('model')!=policy.model:raise ExecutionDenied('provider_response_model_mismatch')
            if frame.get('usage') is not None:
                observed=ExecutionBoundary._usage(frame['usage'])
                if not 0<=observed['input_tokens']<=policy.input_ceiling_tokens or not 0<=observed['output_tokens']<=policy.output_ceiling_tokens:
                    raise ExecutionDenied('provider_usage_out_of_contract')
                if usage is not None and usage!=observed:raise ExecutionDenied('contradictory_provider_usage_frames')
                usage=observed
        return usage
    except ExecutionDenied:raise
    except Exception:raise ExecutionDenied('invalid_provider_response') from None
