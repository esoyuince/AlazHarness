#!/usr/bin/env python3
"""SCRIPTED TEST PEER: real Hermes transport/budget, no AIAgent/model/terminal/network.

The scenarios intentionally inject protocol failures. This file is not an agent
implementation and must never be advertised as general-purpose task execution.
"""
from __future__ import annotations
import importlib.util
import json
import os
from pathlib import Path
import sys
import threading
import time

ROOT = Path(__file__).resolve().parents[2]

def load(name: str, relative: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module

transport_module = load('alaz_fixture_transport', 'packages/upstream/hermes/transport.py')
budget_module = load('alaz_fixture_budget', 'packages/upstream/hermes/iteration_budget.py')

class ScriptedPeer:
    def __init__(self, scenario: str, maximum: int):
        self.scenario = scenario
        self.budget = budget_module.IterationBudget(maximum)
        self.transport = transport_module.StdioTransport(lambda: sys.stdout, threading.Lock())
        self.sid = None
        self.stop = threading.Event()
        self.worker = None
        self.server_replies = {}
        self.reply_received = threading.Event()
        self.handlers = {'client.capabilities': self.capabilities, 'session.create': self.create,
                         'prompt.submit': self.submit, 'session.interrupt': self.interrupt}

    def write(self, obj):
        if not self.transport.write(obj):
            self.stop.set()

    def result(self, rid, value):
        self.write({'jsonrpc': '2.0', 'id': rid, 'result': value})

    def event(self, kind, value, sid=None):
        self.write({'jsonrpc': '2.0', 'method': 'event', 'params': {
            'type': kind, 'session_id': sid or self.sid, 'payload': value}})

    def complete(self, text, status='complete', **extra):
        self.event('message.complete', {'text': text, 'status': status, **extra})

    def capabilities(self, rid, params):
        self.result(rid, {'ok': True})

    def create(self, rid, params):
        self.sid = 'fixture-' + params['idempotency_key']
        self.result(rid, {'session_id': self.sid, 'stored_session_id': self.sid,
                          'message_count': 0, 'messages': [], 'info': {}})

    def interrupt(self, rid, params):
        if self.scenario not in ('ignore-interrupt', 'settlement-hang'):
            self.stop.set()
        self.result(rid, {'status': 'interrupted', 'interrupted': True})

    def submit(self, rid, params):
        if params.get('session_id') != self.sid:
            raise ValueError('wrong fixture session')
        if self.scenario == 'queued':
            self.result(rid, {'status': 'queued'})
            return
        if self.scenario == 'early-terminal':
            self.complete(params['text'])
            self.result(rid, {'status': 'streaming'})
            return
        self.result(rid, {'status': 'streaming'})
        self.worker = threading.Thread(target=self.work, args=(params['text'],))
        self.worker.start()

    def work(self, text):
        scenario = self.scenario
        if scenario == 'crash':
            os._exit(7)
        if scenario == 'malformed':
            sys.stdout.write('not-json\n'); sys.stdout.flush(); return
        if scenario == 'oversized':
            sys.stdout.write('x' * (70 * 1024) + '\n'); sys.stdout.flush(); return
        if scenario == 'frame-flood':
            for _ in range(140): self.event('status.update', {'kind': 'status', 'text': 'fixture'})
            return
        if scenario == 'wrong-session':
            self.event('message.complete', {'text': 'wrong', 'status': 'complete'}, 'foreign'); return
        if scenario == 'no-status':
            self.event('message.complete', {'text': 'not proof'}); return
        if scenario == 'partial':
            self.complete('partial', partial=True); return
        if scenario in ('hang', 'ignore-interrupt'):
            self.event('status.update', {'kind': 'status', 'text': 'fixture waiting'})
            self.stop.wait(30)
            self.complete('', status='interrupted'); return
        if scenario in ('approval', 'unsupported-request'):
            method = 'approval' if scenario == 'approval' else 'sudo'
            self.write({'jsonrpc': '2.0', 'id': 'srq-1', 'method': method,
                        'params': {'session_id': self.sid, 'request_id': 'fixture-request',
                                   'command': 'SCRIPTED_NO_COMMAND_EXECUTED', 'choices': ['deny']}})
            if not self.reply_received.wait(2):
                self.complete('', 'error', error='no reply'); return
            reply = self.server_replies['srq-1']
            self.complete(json.dumps({'reply': reply, 'executed': False})); return
        if scenario == 'environment':
            self.complete(json.dumps({'credential_present': 'ALAZ_TEST_SECRET' in os.environ,
                                      'home': os.environ.get('HOME'),
                                      'hermes_home': os.environ.get('HERMES_HOME'),
                                      'cwd': str(Path.cwd()),
                                      'upstream_entry_imported': 'run_agent' in sys.modules})); return
        if scenario == 'untrusted-event-name':
            self.event('do-not-log-untrusted-text', {'text': text})
        if scenario == 'tool-round':
            if not self.budget.consume():
                self.complete('', 'error', error='iteration budget'); return
            self.event('tool.start', {'name': 'scripted-add'})
            value = sum((2, 3))  # Fixed in-process fixture; not model-selected tool execution.
            self.event('tool.complete', {'name': 'scripted-add'})
            if not self.budget.consume():
                self.complete('', 'error', error='iteration budget'); return
            self.complete(json.dumps({'value': value, 'iterations': self.budget.used,
                                      'model_calls': 0, 'scripted': True})); return
        self.complete(text)
        if scenario == 'duplicate-terminal': self.complete(text)
        if scenario == 'conflicting-terminal': self.complete('conflicting')
        if scenario == 'exit-nonzero': os._exit(9)

    def main(self):
        self.write({'jsonrpc': '2.0', 'method': 'event', 'params': {'type': 'gateway.ready',
                   'payload': {'skin': {}, 'change_events': False, 'replay_epoch': 'fixture',
                               'session_authority': self.scenario == 'canonical-wire'}}})
        for line in sys.stdin:
            request = json.loads(line)
            if 'method' not in request:
                self.server_replies[request['id']] = request
                self.reply_received.set()
                continue
            handler = self.handlers.get(request['method'])
            if handler is None:
                self.write({'jsonrpc': '2.0', 'id': request.get('id'),
                            'error': {'code': -32601, 'message': 'fixture method absent'}})
            else: handler(request['id'], request.get('params', {}))
        if self.scenario in ('ignore-interrupt', 'settlement-hang'):
            time.sleep(30)  # The harness must reap its fixed child, not trust an interrupt ACK.
        self.stop.set()
        if self.worker is not None: self.worker.join(timeout=2)
        self.transport.close()

if __name__ == '__main__':
    ScriptedPeer(sys.argv[1], int(sys.argv[2])).main()
