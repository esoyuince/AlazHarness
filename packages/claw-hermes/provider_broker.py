"""Private Linux Unix-socket broker for a fixed authenticated provider route.

Only the trusted broker receives the upstream credential. The trusted Gateway
owns budget writes/signatures. Same-UID administrators remain trusted; this is
not isolation from arbitrary Python inside the Gateway or a whole-OS firewall.
"""
from __future__ import annotations
import asyncio
import base64
import os
from pathlib import Path
import socket
import stat
import struct
import uuid
from execution_budget import ExecutionDenied
from provider_egress import (BrokerLink,BrokerConfig,PermitVerifier,REQUEST_LIMIT,RESPONSE_LIMIT,
                             authorize_egress,signed,verified,require)
from recovery_inspector import _json,_load

BACKEND='linux_unix_credential_broker'


def private_socket(path):
    require(os.name=='posix' and hasattr(socket,'SO_PEERCRED'),'linux_broker_required')
    p=Path(path)
    require(not any(x.is_symlink() for x in (p,*p.parents)),'linked_broker_socket')
    parent=p.parent.stat();info=p.stat()
    require(stat.S_ISDIR(parent.st_mode) and parent.st_uid==os.getuid() and stat.S_IMODE(parent.st_mode)==0o700,'unsafe_broker_directory')
    require(stat.S_ISSOCK(info.st_mode) and info.st_uid==os.getuid() and stat.S_IMODE(info.st_mode)==0o600,'unsafe_broker_socket')
    return (info.st_dev,info.st_ino)


def peer(writer):
    sock=writer.get_extra_info('socket')
    require(sock is not None,'broker_peer_unavailable')
    pid,uid,gid=struct.unpack('3i',sock.getsockopt(socket.SOL_SOCKET,socket.SO_PEERCRED,12))
    require(pid>0 and uid==os.getuid(),'broker_peer_mismatch')
    return pid


async def read_frame(reader,limit):
    count=struct.unpack('!I',await reader.readexactly(4))[0]
    require(0<count<=limit,'broker_frame_too_large')
    return _load((await reader.readexactly(count)).decode('utf-8'),limit)


async def write_frame(writer,value,limit):
    data=_json(value).encode()
    require(0<len(data)<=limit,'broker_frame_too_large')
    writer.write(struct.pack('!I',len(data))+data)
    await writer.drain()



def reject_sensitive_response(raw,content_type,secret):
    """Reject literal/JSON-decoded or same-path streamed credential echoes.

    This guards supported JSON/SSE representations, not every encoding a malicious
    remote service could invent. Remote providers and the operator remain trusted.
    """
    require(secret.encode() not in raw,'broker_sensitive_response')
    try:
        text=raw.decode('utf-8')
        if content_type=='application/json':frames=[_load(text,4_194_304)]
        else:
            events=[];parts=[]
            for line in text.replace('\r\n','\n').replace('\r','\n').split('\n'):
                if line=='':
                    if parts:events.append('\n'.join(parts));parts=[]
                elif line.startswith('data:'):parts.append(line[5:].removeprefix(' '))
                elif line.startswith(':') or line.startswith(('event:','id:','retry:')):continue
                else:raise ValueError('invalid SSE')
            require(not parts and events and events[-1]=='[DONE]' and events.count('[DONE]')==1,'broker_upstream_error')
            frames=[_load(value,4_194_304) for value in events[:-1]]
            require(bool(frames),'broker_upstream_error')
        streams={};count=0
        pending=[((),x) for x in reversed(frames)]
        while pending:
            path,value=pending.pop();count+=1
            require(count<=100000 and len(path)<=64,'broker_upstream_error')
            if type(value) is str:
                require(secret not in value,'broker_sensitive_response')
                streams.setdefault(path,[]).append(value)
            elif type(value) is dict:
                for key,child in reversed(list(value.items())):
                    require(secret not in key,'broker_sensitive_response');pending.append((path+(key,),child))
            elif type(value) is list:
                for index in reversed(range(len(value))):pending.append((path+(index,),value[index]))
        for parts in streams.values():require(secret not in ''.join(parts),'broker_sensitive_response')
    except ExecutionDenied:raise
    except Exception:raise ExecutionDenied('broker_upstream_error') from None

class ProviderBrokerClient:
    def __init__(self,settings):
        require(type(settings) is dict,'invalid_broker_settings')
        try:self.link=BrokerLink(**settings)
        except TypeError:raise ExecutionDenied('invalid_broker_settings') from None

    async def _exchange(self,document,nonce):
        writer=None
        try:
            async with asyncio.timeout(35):
                before=private_socket(self.link.socket_path)
                reader,writer=await asyncio.open_unix_connection(self.link.socket_path,limit=65536)
                peer(writer)
                require(before==private_socket(self.link.socket_path),'broker_socket_replaced')
                await write_frame(writer,document,REQUEST_LIMIT)
                reply=verified(await read_frame(reader,RESPONSE_LIMIT),self.link.signing_key,'reply')
                require(type(reply.get('version')) is int and reply['version']==1 and reply.get('brokerId')==self.link.broker_id
                        and reply.get('nonce')==nonce,'broker_reply_mismatch')
                require(type(reply.get('ok')) is bool,'invalid_broker_reply')
                if not reply['ok']:
                    code=reply.get('error')
                    require(type(code) is str and code in {'broker_replay_refused','stale_broker_identity','egress_grant_expired',
                        'stale_egress_owner','unconfirmed_egress_grant','broker_budget_unavailable','broker_claim_unavailable',
                        'broker_sensitive_response','provider_redirect_refused','broker_upstream_error','broker_request_refused',
                        'broker_lifetime_limit'},'broker_request_refused')
                    raise ExecutionDenied(code)
                return reply
        except asyncio.CancelledError:raise
        except ExecutionDenied:raise
        except Exception:raise ExecutionDenied('broker_transport_outcome_unknown') from None
        finally:
            if writer is not None:
                writer.close()
                try:await asyncio.wait_for(writer.wait_closed(),2)
                except Exception:pass

    async def ready(self):
        nonce=uuid.uuid4().hex
        value={'version':1,'operation':'ping','brokerId':self.link.broker_id,
               'routeFingerprint':self.link.route_fingerprint,'nonce':nonce}
        reply=await self._exchange(signed(value,self.link.signing_key,'request'),nonce)
        require(set(reply)=={'version','brokerId','nonce','ok','routeFingerprint'} and reply['routeFingerprint']==self.link.route_fingerprint,'broker_reply_mismatch')
        return True

    async def send(self,ledger,ticket,payload):
        # All IPC errors retain this native grant and the original full reservation.
        document=await asyncio.to_thread(authorize_egress,ledger,self.link,ticket,payload)
        reply=await self._exchange(document,ticket)
        require(set(reply)=={'version','brokerId','nonce','ok','status','contentType','dataBase64'},'invalid_broker_reply')
        status=reply['status'];ctype=reply['contentType'];encoded=reply['dataBase64']
        require(type(status) is int and (status==200 or 400<=status<=599),'invalid_broker_status')
        require(ctype in ('application/json','text/event-stream'),'invalid_broker_content_type')
        require(type(encoded) is str and len(encoded)<=5_592_408,'broker_frame_too_large')
        try:raw=base64.b64decode(encoded,validate=True)
        except (ValueError,TypeError):raise ExecutionDenied('invalid_broker_body') from None
        require(len(raw)<=4_194_304,'broker_frame_too_large')
        return raw,status,ctype


class ProviderBrokerServer:
    """Fresh lifetime, private socket, bounded frames, one physical send per grant.

    A restart has a new ID. There is no caller-selectable route, HTTP forwarding,
    credential endpoint, general proxy, retry queue or budget writer.
    """
    def __init__(self,config:BrokerConfig,directory:Path):
        require(type(config) is BrokerConfig,'trusted_broker_config_required')
        self.config=config;self.directory=Path(directory);self.identifier=uuid.uuid4().hex
        self.path=self.directory/'egress.sock';self.verifier=PermitVerifier(config,self.identifier)
        self.server=None;self.tasks=set();self.connections=set();self.started=False;self.socket_identity=None;self.closing=False
        self.counts={'physicalAttempts':0,'refused':0,'pings':0,'responses':0}

    async def start(self):
        require(os.name=='posix' and hasattr(socket,'SO_PEERCRED'),'linux_broker_required')
        require(not self.started,'broker_already_started');self.started=True
        require(self.directory.is_absolute() and not self.directory.exists() and len(str(self.path).encode())<=100,'fresh_broker_directory_required')
        require(not any(p.is_symlink() for p in self.directory.parents),'linked_broker_directory')
        self.directory.mkdir(mode=0o700)
        # Do not unlink/adopt any existing server. Expose no socket before permissions.
        self.server=await asyncio.start_unix_server(self._handle,path=str(self.path),start_serving=False,backlog=8,limit=65536)
        self.path.chmod(0o600);self.socket_identity=private_socket(self.path)
        await self.server.start_serving()
        return {'brokerId':self.identifier,'socketPath':str(self.path),'routeFingerprint':self.config.route,'pid':os.getpid(),'backend':BACKEND}

    async def _upstream(self,payload):
        from aiohttp import ClientSession,ClientTimeout,TCPConnector
        # Literal loopback only in this qualified slice. No DNS, env proxy or redirect.
        async with ClientSession(timeout=ClientTimeout(total=25),trust_env=False,auto_decompress=False,
                                 connector=TCPConnector(family=socket.AF_INET,force_close=True)) as client:
            self.counts['physicalAttempts']+=1
            async with client.post(self.config.upstream_base_url+'/chat/completions',data=_json(payload).encode(),
                                   headers={'Authorization':'Bearer '+self.config.upstream_bearer,'Content-Type':'application/json'},
                                   allow_redirects=False) as response:
                require(not 300<=response.status<400,'provider_redirect_refused')
                # Never reflect an error body, cookie, location or arbitrary upstream header.
                if response.status!=200:
                    return b'{}',response.status if 400<=response.status<=599 else 502,'application/json'
                ctype=response.headers.get('Content-Type','').split(';')[0].lower()
                require(ctype in ('application/json','text/event-stream'),'broker_upstream_error')
                require(not response.headers.get('Content-Encoding'),'broker_upstream_error')
                chunks=[];size=0
                async for chunk in response.content.iter_chunked(65536):
                    size+=len(chunk);require(size<=4_194_304,'broker_upstream_error');chunks.append(chunk)
                raw=b''.join(chunks)
                reject_sensitive_response(raw,ctype,self.config.upstream_bearer)
                return raw,200,ctype

    async def _handle(self,reader,writer):
        task=asyncio.current_task()
        if self.closing or len(self.tasks)>=8:
            writer.close()
            try:await writer.wait_closed()
            except Exception:pass
            return
        self.tasks.add(task);self.connections.add(writer);nonce=''
        try:
            async with asyncio.timeout(30):
                peer(writer)
                envelope=await asyncio.wait_for(read_frame(reader,REQUEST_LIMIT),5)
                doc=verified(envelope,self.config.signing_key,'request')
                if doc.get('operation')=='ping':
                    require(set(doc)=={'version','operation','brokerId','routeFingerprint','nonce'} and type(doc['version']) is int and doc['version']==1,'invalid_broker_ping')
                    nonce=doc['nonce'];require(type(nonce) is str and len(nonce)==32,'invalid_broker_ping')
                    require(doc['brokerId']==self.identifier and doc['routeFingerprint']==self.config.route,'stale_broker_identity')
                    self.counts['pings']+=1
                    reply={'version':1,'brokerId':self.identifier,'nonce':nonce,'ok':True,'routeFingerprint':self.config.route}
                else:
                    # Freeze and consume before awaiting DB or outbound I/O.
                    if type(doc.get('grant')) is dict:nonce=doc['grant'].get('ticket','')
                    value=self.verifier.consume(envelope)
                    await asyncio.to_thread(self.verifier.check_authority,value['grant'])
                    self.verifier.check_expiry(value['grant'])
                    raw,status,ctype=await self._upstream(value['payload'])
                    self.counts['responses']+=1
                    reply={'version':1,'brokerId':self.identifier,'nonce':nonce,'ok':True,
                           'status':status,'contentType':ctype,'dataBase64':base64.b64encode(raw).decode('ascii')}
                await write_frame(writer,signed(reply,self.config.signing_key,'reply'),RESPONSE_LIMIT)
        except asyncio.CancelledError:raise
        except Exception as exc:
            self.counts['refused']+=1
            allowed={'broker_replay_refused','stale_broker_identity','egress_grant_expired','stale_egress_owner',
                     'unconfirmed_egress_grant','broker_budget_unavailable','broker_claim_unavailable',
                     'broker_sensitive_response','provider_redirect_refused','broker_upstream_error','broker_lifetime_limit'}
            code=str(exc) if isinstance(exc,ExecutionDenied) and str(exc) in allowed else 'broker_request_refused'
            reply={'version':1,'brokerId':self.identifier,'nonce':nonce if type(nonce) is str and len(nonce)<=32 else '', 'ok':False,'error':code}
            try:
                await asyncio.wait_for(write_frame(writer,signed(reply,self.config.signing_key,'reply'),RESPONSE_LIMIT),2)
            except Exception:pass
        finally:
            writer.close()
            try:await asyncio.wait_for(writer.wait_closed(),2)
            except Exception:pass
            self.connections.discard(writer);self.tasks.discard(task)

    async def close(self):
        self.closing=True
        if self.server is not None:self.server.close()
        # wait_closed may wait for clients. Close/cancel owned requests FIRST.
        for writer in list(self.connections):writer.close()
        tasks=list(self.tasks)
        for task in tasks:task.cancel()
        if tasks:await asyncio.gather(*tasks,return_exceptions=True)
        if self.server is not None:await asyncio.wait_for(self.server.wait_closed(),3)
        # Python 3.13+ may already remove its own Unix socket on server close.
        if self.path.exists():
            require(self.socket_identity==private_socket(self.path),'broker_cleanup_identity_changed')
            self.path.unlink()
        return {'brokerId':self.identifier,'pid':os.getpid(),'socketRemoved':not self.path.exists(),
                'activeRequests':len(self.tasks),'counters':dict(self.counts)}
