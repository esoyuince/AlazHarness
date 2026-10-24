"""Loopback-only contract fixture. NO AIAgent, real model, tool process, or profile.
The real extracted Hermes pure mapper/budget run here. Admission/state storage is
an in-memory fixture; its tests do not prove native Hermes persistence or locking.
"""
from __future__ import annotations
import hashlib
import importlib.util
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import threading
import uuid

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'packages/upstream/hermes'

def load(name):
    spec = importlib.util.spec_from_file_location('fixture_' + name, SOURCE / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

mapper = load('terminal_status')
budgets = load('iteration_budget')
keys = load('hermes_state_keys')
TOKEN = 'local-contract-fixture-only'

class Fixture:
    def __init__(self):
        self.lock = threading.RLock()
        self.runs = {}; self.keys = {}; self.request_log = []; self.foreign_hits = 0
        owner = self
        class Handler(BaseHTTPRequestHandler):
            protocol_version = 'HTTP/1.1'
            def log_message(self, *args):
                pass
            def handle(self):
                try: super().handle()
                except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError): pass  # deliberate client-abort scenarios
            def send_json(self, status, body):
                raw = json.dumps(body).encode()
                self.send_response(status); self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(raw))); self.end_headers()
                try: self.wfile.write(raw)
                except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError): pass
            def authorized(self):
                if self.headers.get('Authorization') != 'Bearer ' + TOKEN:
                    self.send_json(401, {'error': {'code': 'unauthorized'}}); return False
                return True
            def do_POST(self):
                if not self.authorized(): return
                length = int(self.headers.get('Content-Length', 0))
                if not 0 < length <= 70000: self.send_json(400, {}); return
                body = json.loads(self.rfile.read(length))
                with owner.lock:
                    owner.request_log.append(('POST', self.path))
                    if self.path == '/v1/runs':
                        key = self.headers.get('Idempotency-Key', '')
                        digest = keys.admission_fingerprint(canonical_target='fixture', payload=body)
                        prior = owner.keys.get(key)
                        if prior:
                            if prior[0] != digest: self.send_json(409, {'error': {'code': 'idempotency_key_conflict'}}); return
                            row = owner.runs[prior[1]]
                            self.send_json(202, {'run_id': row['id'], 'status': row['status'], 'replayed': True}); return
                        rid = 'run_' + uuid.uuid4().hex
                        row = {'id': rid, 'mode': body['input'], 'status': 'running', 'reads': 0, 'stop_reads': 0,
                               'stops': 0, 'budget': budgets.IterationBudget(2), 'fields': {}, 'output': ''}
                        owner.runs[rid] = row; owner.keys[key] = (digest, rid)
                        if row['mode'] == 'lost-ack':
                            self.close_connection = True
                            self.connection.shutdown(2); self.connection.close(); return
                        self.send_json(202, {'run_id': rid, 'status': 'started', 'replayed': False}); return
                    rid = self.path.split('/')[3] if self.path.startswith('/v1/runs/') else ''
                    row = owner.runs.get(rid)
                    if not row: self.send_json(404, {'error': {'code': 'run_not_found'}}); return
                    if self.path.endswith('/stop'):
                        row['stops'] += 1
                        if row['mode'] != 'ignore-stop': row['status'] = 'stopping'
                        self.send_json(200, {'run_id': rid, 'status': 'stopping'}); return
                    self.send_json(404, {})
            def do_GET(self):
                if not self.authorized(): return
                with owner.lock:
                    owner.request_log.append(('GET', self.path))
                    if self.path == '/forbidden-redirect': owner.foreign_hits += 1; self.send_json(200, {}); return
                    rid = self.path.split('/')[-1]; row = owner.runs.get(rid)
                    if not row: self.send_json(404, {'error': {'code': 'run_not_found'}}); return
                    mode = row['mode']; row['reads'] += 1
                    if mode == 'redirect':
                        self.send_response(302); self.send_header('Location', '/forbidden-redirect')
                        self.send_header('Content-Length', '0'); self.end_headers(); return
                    if mode == 'oversized': self.send_json(200, {'data': 'X' * 20000}); return
                    if mode == 'unknown': row['status'] = 'unknown'
                    elif mode == 'approval' and not row['stops']: row['status'] = 'waiting_for_approval'
                    elif row['status'] == 'stopping':
                        row['stop_reads'] += 1
                        if row['stop_reads'] >= 2: row['status'] = 'cancelled'
                    elif mode not in ('hold', 'ignore-stop') and row['reads'] >= 2:
                        if mode == 'budget':
                            row['budget'].consume(); row['budget'].consume()
                            assert row['budget'].consume() is False
                            response = {'completed': False, 'partial': True, 'turn_exit_reason': 'iteration_budget'}
                        elif mode == 'partial': response = {'partial': True, 'completed': False}
                        else: response = {'completed': True}
                        row['status'], row['fields'] = mapper.terminal_run_status(response)
                        row['output'] = str(6 * 7) if row['status'] == 'completed' else ''
                    payload = {'object': 'hermes.run', 'run_id': rid, 'status': row['status'], 'output': row['output'],
                               'session_id': 'fixture-session', 'admission_id': rid[4:], 'execution_generation': 1,
                               'created_at': 0.0, 'model': 'scripted-fixture', **row['fields']}
                    if mode == 'unverified-terminal':
                        payload.update(status='interrupted'); payload.pop('admission_id'); payload.pop('execution_generation')
                    if mode == 'wrong-id': payload['run_id'] = 'run_' + 'f' * 32
                    if mode == 'contradictory': payload.update(status='completed', completed=False, partial=True)
                    self.send_json(200, payload)
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.server.daemon_threads = True
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
    def __enter__(self):
        self.thread.start(); return self
    def __exit__(self, *args):
        self.server.shutdown(); self.server.server_close(); self.thread.join(2)
    @property
    def url(self):
        return 'http://127.0.0.1:' + str(self.server.server_port)
