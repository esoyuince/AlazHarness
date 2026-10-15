"""Fault-only HTTP relay: forward native responses, drop one proved 202 acknowledgement."""
from __future__ import annotations
import http.client
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import json
from pathlib import Path
import socket
import threading

class LostAckRelay:
    def __init__(self,port: int,key: str):
        self.records=[];self.dropped_run=None;self.lock=threading.Lock();owner=self
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def forward(self):
                conn=http.client.HTTPConnection('127.0.0.1',port,timeout=10)
                try:
                    n=int(self.headers.get('Content-Length','0'))
                    if n<0 or n>131072:raise ValueError('Oversized relay request')
                    body=self.rfile.read(n) if n else None
                    headers={k:v for k,v in self.headers.items() if k.lower() not in ('host','connection','content-length')}
                    conn.request(self.command,self.path,body=body,headers=headers)
                    res=conn.getresponse();raw=res.read(4_194_305)
                    if len(raw)>4_194_304:raise ValueError('Oversized native response')
                    with owner.lock:
                        owner.records.append({'method':self.command,'path':self.path,'status':res.status})
                        drop=(owner.dropped_run is None and self.command=='POST' and self.path=='/v1/runs'
                              and self.headers.get('Idempotency-Key')==key and res.status==202)
                        if drop:owner.dropped_run=json.loads(raw)['run_id']
                    if drop:
                        self.close_connection=True
                        self.connection.shutdown(socket.SHUT_RDWR);self.connection.close();return
                    self.send_response(res.status)
                    self.send_header('Content-Type',res.getheader('Content-Type','application/octet-stream'))
                    self.send_header('Content-Length',str(len(raw)))
                    self.end_headers();self.wfile.write(raw)
                except (BrokenPipeError,ConnectionResetError):pass
                finally:conn.close()
            do_GET=forward
            do_POST=forward
        self.server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True)
    @property
    def base_url(self):return f'http://127.0.0.1:{self.server.server_port}'
    def start(self):self.thread.start()
    def close(self):self.server.shutdown();self.server.server_close();self.thread.join(timeout=5)
