"""Real owned subprocess pipes and synthetic service task receipts.

No kernel projection, native store, provider or model runs here. Test teardown
terminates only test-created fixture children that intentionally remain alive.
"""
import base64
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'packages/claw-hermes'))
import supervised_service_channel as channel
import service_task_protocol as task
from test_service_task_protocol_r165a1 import SID, http_request

CHILD = r'''
import base64, json, os, pathlib, sys, time
root, mode, journal = sys.argv[1:]
sys.path.insert(0, str(pathlib.Path(root) / 'packages/claw-hermes'))
import gateway_service_control as wire
import service_task_protocol as task
sid='a'*32
def owner(state='READY'):
 return {'protocol':'alaz-borrowed-service-v1','state':state,'pid':os.getpid(),
  'epoch':2,'instanceId':'owned-service-2','endpoint':'http://127.0.0.1:45550',
  'serviceStarted':True,'serviceReady':state=='READY','serviceClosed':state=='CLOSED',
  'admissionOpen':state=='READY','close':{**{name:state=='CLOSED' for name in wire._CLOSE_FLAGS},
   'physicalStoresClosed':3 if state=='CLOSED' else 0,'callerLeaseReleased':state=='CLOSED',
   'imageLeaseReleasedHere':False},'reason':None,'admissionSealReason':None,
  'retryAllowed':False,'nativeStoresOwnedHere':False,'imageLeaseOwnedHere':False,'fullD3BAccepted':False}
def lifecycle(kind,sequence=0,state='READY'):
 return {'protocol':wire.PROTOCOL,'type':kind,'serviceId':sid,'sequence':sequence,
  'requestId':wire.request_id(sid,sequence) if sequence else None,'owner':owner(state)}
def emit(raw):
 while raw:raw=raw[os.write(1,raw[:16384]):]
def log(value):
 with open(journal,'a') as f:f.write(json.dumps(value)+'\n');f.flush()
sys.stdin.buffer.readline(131074)
emit(wire.canonical(lifecycle('ready'))+b'\n')
if mode=='partial_input':time.sleep(5)
while True:
 raw=sys.stdin.buffer.readline(task.MAX_REQUEST_FRAME+1)
 if not raw:raise SystemExit(2)
 if raw.startswith(task.PREFIX):
  request=task.validate_command(task.decode(raw),service_id=sid)
  sequence=request['sequence']
  log({'action':'http','sequence':sequence})
  if mode=='delayed':time.sleep(.2)
  body=b'{"output":"'+b'x'*(100000 if mode=='large' else 8)+b'"}'
  response={'status':200,'headers':{'content-type':'application/json','content-length':str(len(body))},
   'bodyBase64':base64.b64encode(body).decode('ascii')}
  value={'protocol':task.PROTOCOL,'type':'task-reply','serviceId':sid,'sequence':sequence,
   'requestId':request['requestId'],'owner':owner(),'response':response,'error':None}
  if mode=='http_error':value.update(response=None,error='service_task_http_outcome_unknown')
  if mode=='bad_sequence':
   value['sequence']+=1;value['requestId']=wire.request_id(sid,value['sequence'])
  if mode=='bad_owner':value['owner']['epoch']=3
  data=task.encode(value,reply=True)
  if mode=='trailing_partial':emit(data+b'{')
  elif mode=='fragmented':emit(data[:7]);time.sleep(.02);emit(data[7:])
  else:emit(data)
 else:
  request=wire.validate_command(wire.decode(raw[:-1]),service_id=sid)
  sequence=request['sequence'];action=request['action'];log({'action':action,'sequence':sequence})
  if action=='close':
   emit(wire.canonical(lifecycle('final',sequence,'CLOSED'))+b'\n');raise SystemExit(0)
  reply=lifecycle('reply',sequence)
  if mode=='lifecycle_oversize':reply['extra']='x'*70000
  if mode=='wrong_protocol':
   reply={'protocol':task.PROTOCOL,'type':'task-reply','serviceId':sid,'sequence':sequence,
    'requestId':request['requestId'],'owner':owner(),'response':None,'error':'service_task_http_outcome_unknown'}
   emit(task.encode(reply,reply=True))
  else:emit(wire.canonical(reply)+b'\n')
'''


@unittest.skipUnless(os.name == 'posix', 'requires selectable POSIX subprocess pipes')
class TaskChannelTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.children = []
        self.addCleanup(self.close_children)

    def close_children(self):
        for process in self.children:
            if process.poll() is None:
                process.terminate()
            process.wait(timeout=3)
            for name in ('stdin', 'stdout', 'stderr'):
                stream = getattr(process, name)
                if stream is not None and not stream.closed:
                    stream.close()

    def fixture(self, mode='normal'):
        journal = Path(self.temp.name) / (str(len(self.children)) + '.jsonl')
        process = subprocess.Popen([sys.executable, '-u', '-c', CHILD, str(ROOT), mode, str(journal)],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=0)
        self.children.append(process)
        value = channel.ServiceChannel(process, service_id=SID, previous_epoch=1,
                                       instance_id='owned-service-2')
        value.test_journal = journal
        self.assertEqual(value.start(b'{"fixture":true}', timeout=2)['state'], 'READY')
        return value

    def lines(self, value):
        return [json.loads(line) for line in value.test_journal.read_text().splitlines()]

    def test_task_and_lifecycle_share_original_sequence_and_status_is_sanitized(self):
        value = self.fixture()
        result = value.task(http_request(), timeout=2)
        self.assertEqual(result['state'], 'READY')
        self.assertEqual(value.task_reply['sequence'], 1)
        self.assertEqual(value.task_reply['owner']['pid'], value.process.pid)
        self.assertFalse(any(key in json.dumps(result) for key in ('bodyBase64', 'authorization', 'response')))
        value.command('status', timeout=2)
        self.assertIsNone(value.task_reply)
        value.task(http_request(), timeout=2)
        self.assertEqual(value.task_reply['sequence'], 3)
        final = value.command('close', timeout=2)
        self.assertEqual(final['state'], 'COMPLETED')
        self.assertIsNone(value.task_reply)
        self.assertEqual([x['sequence'] for x in self.lines(value)], [1, 2, 3, 4])

    def test_large_task_response_and_fragmented_prefix_are_accepted(self):
        for mode in ('large', 'fragmented'):
            with self.subTest(mode=mode):
                value = self.fixture(mode)
                self.assertEqual(value.task(http_request(), timeout=2)['state'], 'READY')
                body = task.body_bytes(value.task_reply['response']['bodyBase64'], 1048576)
                self.assertGreater(len(body), 100000 if mode == 'large' else 8)
                self.assertEqual(value.command('close', timeout=2)['state'], 'COMPLETED')

    def test_http_error_retains_ready_and_lifecycle_close(self):
        value = self.fixture('http_error')
        self.assertEqual(value.task(http_request(), timeout=2)['state'], 'READY')
        self.assertEqual(value.task_reply['error'], 'service_task_http_outcome_unknown')
        self.assertIsNone(value.failure)
        self.assertEqual(value.command('close', timeout=2)['state'], 'COMPLETED')

    def test_late_reply_is_observed_without_resending_task(self):
        value = self.fixture('delayed')
        self.assertEqual(value.task(http_request(), timeout=.02)['state'], 'UNKNOWN')
        self.assertIsNone(value.task_reply)
        self.assertEqual(value.pending['type'], 'task-reply')
        with self.assertRaises(channel.ServiceChannelRejected):
            value.task(http_request(), timeout=1)
        end = time.monotonic() + 2
        while value.pending is not None and time.monotonic() < end:
            value.observe(timeout=.05)
        self.assertEqual(value.phase, 'READY')
        self.assertEqual(value.task_reply['sequence'], 1)
        self.assertTrue(value.status()['observedAfterUnknown'])
        self.assertEqual(self.lines(value), [{'action': 'http', 'sequence': 1}])
        value.command('close', timeout=2)

    def test_partial_task_input_observation_never_transmits_remaining_bytes(self):
        value = self.fixture('partial_input')
        request = http_request('POST', '/alaz/host/v1/intents', b'x' * 200000)
        self.assertEqual(value.task(request, timeout=.02)['state'], 'UNKNOWN')
        written = value.input_written
        self.assertGreater(written, 0)
        self.assertLess(written, len(value.input_bytes))
        value.observe(timeout=.02)
        self.assertEqual(value.input_written, written)
        self.assertIsNone(value.task_reply)

    def test_reply_identity_and_protocol_confusion_fail_closed(self):
        for mode in ('bad_sequence', 'bad_owner', 'wrong_protocol'):
            value = self.fixture(mode)
            with self.subTest(mode=mode), self.assertRaises(channel.ServiceChannelRejected):
                if mode == 'wrong_protocol':
                    value.command('status', timeout=2)
                else:
                    value.task(http_request(), timeout=2)
            self.assertEqual(value.phase, 'UNKNOWN')
            self.assertIsNone(value.task_reply)

    def test_lifecycle_frame_limit_remains_small_after_successful_task(self):
        value = self.fixture('lifecycle_oversize')
        value.task(http_request(), timeout=2)
        with self.assertRaisesRegex(channel.ServiceChannelRejected, 'frame_bound'):
            value.command('status', timeout=2)
        self.assertIsNone(value.task_reply)
        self.assertLessEqual(len(value.stdout), channel.MAX_FRAME + 16384)

    def test_unterminated_bytes_after_task_reply_are_fatal_without_replay(self):
        value = self.fixture('trailing_partial')
        original = value.process
        with self.assertRaisesRegex(channel.ServiceChannelRejected, 'unsolicited_task_output'):
            value.task(http_request(), timeout=2)
        self.assertEqual(value.phase, 'UNKNOWN')
        self.assertEqual(value.failure, 'service_channel_unsolicited_task_output')
        self.assertIsNone(value.task_reply)
        for action in (lambda: value.task(http_request(), timeout=1),
                       lambda: value.command('status', timeout=1),
                       lambda: value.observe(timeout=0)):
            with self.assertRaises(channel.ServiceChannelRejected):
                action()
        self.assertEqual(value.sequence, 1)
        self.assertEqual(self.lines(value), [{'action': 'http', 'sequence': 1}])
        self.assertIs(value.process, original)
        self.assertIsNone(original.poll())


if __name__ == '__main__':
    unittest.main()
