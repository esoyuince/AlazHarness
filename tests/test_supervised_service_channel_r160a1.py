"""Real owned subprocess pipes; every service/native receipt is synthetic.

No sockets, native stores, model calls, namespace entry or volume release occur.
Only test-owned fixture children are terminated during test teardown.
"""
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'packages/claw-hermes'))
import supervised_service_channel as channel
import gateway_service_control as wire

SID = 'a' * 32

CHILD = r'''
import json, os, pathlib, sys, time
root, mode, journal = sys.argv[1:]
sys.path.insert(0, str(pathlib.Path(root) / 'packages/claw-hermes'))
import gateway_service_control as wire
sid = 'a' * 32
def log(value):
    with open(journal, 'a') as stream:
        stream.write(json.dumps(value) + '\n');stream.flush()
def owner(state):
    return {'protocol':'alaz-borrowed-service-v1','state':state,'pid':os.getpid(),
        'epoch':2,'instanceId':'owned-service-2','endpoint':'http://127.0.0.1:45550',
        'serviceStarted':True,'serviceReady':state=='READY','serviceClosed':state=='CLOSED',
        'admissionOpen':state=='READY',
        'close':{**{name:state=='CLOSED' for name in wire._CLOSE_FLAGS},
                 'physicalStoresClosed':3 if state=='CLOSED' else 0,
                 'callerLeaseReleased':state=='CLOSED','imageLeaseReleasedHere':False},
        'reason':None,'admissionSealReason':None,'retryAllowed':False,
        'nativeStoresOwnedHere':False,'imageLeaseOwnedHere':False,'fullD3BAccepted':False}
def frame(kind,state,sequence=0):
    return {'protocol':wire.PROTOCOL,'type':kind,'serviceId':sid,'sequence':sequence,
        'requestId':wire.request_id(sid,sequence) if sequence else None,'owner':owner(state)}
def emit(value,fragmented=False):
    raw=wire.canonical(value)+b'\n'
    if fragmented:
        os.write(1,raw[:23])
        if mode=='fragment_ready':
            release=pathlib.Path(journal+'.release')
            deadline=time.monotonic()+5
            while not release.exists():
                if time.monotonic()>=deadline:raise SystemExit(3)
                time.sleep(.005)
        else:time.sleep(.12)
        os.write(1,raw[23:])
    else:os.write(1,raw)
if mode=='partial_input':
    time.sleep(.15)
    data=os.read(0,4096);log({'readBytes':len(data)})
    time.sleep(5)
    raise SystemExit(0)
if mode=='premature_ready':
    emit(frame('ready','READY'));time.sleep(5);raise SystemExit(0)
bootstrap=sys.stdin.buffer.readline(131074)
log({'bootstrapBytes':len(bootstrap)})
if mode=='partial_eof':
    os.write(1,b'{');raise SystemExit(0)
if mode=='oversize':
    os.write(1,b'x'*80000);time.sleep(5);raise SystemExit(0)
if mode=='final_before_ready':
    emit(frame('final','CLOSED',1));raise SystemExit(0)
if mode=='stderr_flood':
    data=b'e'*100000
    while data:data=data[os.write(2,data):]
ready=frame('ready','READY')
if mode=='foreign_epoch':ready['owner']['epoch']=99
if mode=='foreign_instance':ready['owner']['instanceId']='replacement'
if mode=='foreign_service':ready['serviceId']='b'*32
if mode=='delayed_ready':time.sleep(.12)
emit(ready,fragmented=mode=='fragment_ready')
if mode in ('ready_exit','foreign_epoch','foreign_service','foreign_instance'):
    raise SystemExit(0)
if mode=='unsolicited_final':
    emit(frame('final','CLOSED',1));time.sleep(5);raise SystemExit(0)
state='READY'
while True:
    raw=sys.stdin.buffer.readline(65538)
    if not raw:raise SystemExit(2)
    request=json.loads(raw);log(request)
    sequence=request['sequence'];action=request['action']
    if mode=='delayed_reply':time.sleep(.12)
    if action=='drain':state='DRAINING'
    if action=='close':
        state='CLOSED'
        emit(frame('final',state,sequence))
        if mode=='nonzero_final':raise SystemExit(7)
        if mode=='trailing_final':os.write(1,b'extra\n')
        if mode=='final_alive_eof':
            os.close(1);os.close(2);time.sleep(.2)
        raise SystemExit(0)
    reply=frame('reply',state,sequence)
    if mode=='wrong_sequence':
        reply['sequence']+=1
        reply['requestId']=wire.request_id(sid,reply['sequence'])
    emit(reply,fragmented=mode=='fragment_reply')
'''


@unittest.skipUnless(os.name == 'posix', 'requires selectable POSIX subprocess pipes')
class ServiceChannelTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.children = []
        self.addCleanup(self.close_children)

    def close_children(self):
        for process in self.children:
            if process.poll() is None:
                process.terminate()
            process.wait(timeout=3)
            for name in ('stdin','stdout','stderr'):
                stream=getattr(process,name)
                if stream is not None and not stream.closed:stream.close()

    def fixture(self, mode='normal'):
        path = self.root / (str(len(self.children)) + '.jsonl')
        process = subprocess.Popen([sys.executable, '-u', '-c', CHILD, str(ROOT), mode, str(path)],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=0)
        self.children.append(process)
        value = channel.ServiceChannel(process, service_id=SID, previous_epoch=1,
                                        instance_id='owned-service-2')
        value.test_journal = path
        return value

    def lines(self, value):
        if not value.test_journal.exists():return []
        return [json.loads(line) for line in value.test_journal.read_text().splitlines()]

    def ready(self, value, timeout=2):
        result=value.start(b'{"fixture":true}',timeout=timeout)
        self.assertEqual(result['state'],'READY')
        return result

    def until(self, value, target, seconds=3):
        deadline=time.monotonic()+seconds
        while time.monotonic()<deadline:
            result=value.observe(timeout=.05)
            if result['state']==target:return result
        self.fail('state did not reach '+target)

    def test_full_ready_status_drain_final_exit_is_not_volume_permission(self):
        value=self.fixture()
        ready=self.ready(value)
        self.assertFalse(ready['childExited'] or ready['volumeMayClose'])
        self.assertEqual(value.command('status',timeout=2)['state'],'READY')
        self.assertEqual(value.command('drain',timeout=2)['state'],'DRAINING')
        final=value.command('close',timeout=2)
        self.assertEqual(final['state'],'COMPLETED')
        self.assertTrue(final['childExited'])
        self.assertFalse(final['volumeMayClose'])
        self.assertFalse(final['owner']['close']['imageLeaseReleasedHere'])
        self.assertEqual(value.process.returncode,0)
        self.assertEqual([x.get('action') for x in self.lines(value)[1:]],['status','drain','close'])
        with self.assertRaises(channel.ServiceChannelRejected):value.command('status')

    def test_start_twice_and_invalid_timeout_do_not_send_or_reserve(self):
        value=self.fixture()
        for timeout in (0,-1,61,True,float('nan'),float('inf')):
            with self.subTest(timeout=timeout),self.assertRaises(channel.ServiceChannelRejected):
                value.start(b'{}',timeout=timeout)
            self.assertFalse(value.input_started)
            self.assertEqual(value.phase,'NEW')
        self.ready(value)
        before=value.stdout_bytes
        with self.assertRaisesRegex(channel.ServiceChannelRejected,'start_once'):
            value.start(b'{}')
        self.assertEqual(value.stdout_bytes,before)
        for timeout in (0,-1,61,True,float('nan')):
            with self.subTest(timeout=timeout),self.assertRaises(channel.ServiceChannelRejected):
                value.command('drain',timeout=timeout)
            self.assertEqual(value.sequence,0)
            self.assertIsNone(value.pending)
        self.assertEqual(len(self.lines(value)),1)
        value.command('close',timeout=2)

    def test_invalid_action_never_consumes_sequence(self):
        value=self.fixture();self.ready(value)
        for action in ('task','restart',None,True):
            with self.assertRaises(wire.ServiceControlRejected):value.command(action)
            self.assertEqual(value.sequence,0)
            self.assertIsNone(value.pending)
        value.command('close',timeout=2)

    def test_ready_timeout_and_response_loss_use_original_frame_without_resend(self):
        value=self.fixture('delayed_ready')
        unknown=value.start(b'{}',timeout=.01)
        self.assertEqual(unknown['state'],'UNKNOWN')
        self.assertFalse(unknown['childExited'] or unknown['volumeMayClose'])
        original=value.input_written
        result=self.until(value,'READY')
        self.assertTrue(result['observedAfterUnknown'])
        self.assertEqual(value.input_written,0)
        self.assertEqual(original,3)
        self.assertEqual(self.lines(value),[{'bootstrapBytes':3}])
        value.command('close',timeout=2)

    def test_reply_timeout_observes_original_command_exactly_once(self):
        value=self.fixture('delayed_reply');self.ready(value)
        result=value.command('drain',timeout=.01)
        self.assertEqual(result['state'],'UNKNOWN')
        self.assertEqual(result['pendingSequence'],1)
        with self.assertRaises(channel.ServiceChannelRejected):value.command('drain')
        result=self.until(value,'DRAINING')
        self.assertEqual(result['pendingSequence'],None)
        self.assertEqual([x.get('action') for x in self.lines(value)[1:]],['drain'])
        value.command('close',timeout=2)

    def test_observe_never_transmits_remaining_partial_bootstrap(self):
        value=self.fixture('partial_input')
        result=value.start(b'x'*channel.MAX_BOOTSTRAP,timeout=.02)
        self.assertEqual(result['state'],'UNKNOWN')
        written=value.input_written
        self.assertTrue(0<written<len(value.input_bytes))
        deadline=time.monotonic()+2
        while not self.lines(value) and time.monotonic()<deadline:time.sleep(.01)
        self.assertEqual(self.lines(value),[{'readBytes':4096}])
        value.observe(timeout=.05)
        self.assertEqual(value.input_written,written)
        self.assertEqual(value.sequence,0)
        self.assertEqual(value.pending['type'],'ready')

    def test_ready_before_complete_bootstrap_cannot_acknowledge_unsent_bytes(self):
        value=self.fixture('premature_ready')
        with self.assertRaises(channel.ServiceChannelRejected):
            value.start(b'x'*channel.MAX_BOOTSTRAP,timeout=2)
        self.assertTrue(0<value.input_written<len(value.input_bytes))
        self.assertFalse(value.ready_seen)
        self.assertIsNone(value.last_frame)
        self.assertIsNotNone(value.failure)
        self.assertFalse(value.status()['volumeMayClose'])

    def test_fragmented_ready_retains_bounded_partial_bytes(self):
        value=self.fixture('fragment_ready')
        result=value.start(b'{}',timeout=.01)
        self.assertEqual(result['state'],'UNKNOWN')
        deadline=time.monotonic()+2
        while not value.stdout and time.monotonic()<deadline:
            value.observe(timeout=.02)
        self.assertEqual(len(value.stdout),23)
        self.assertEqual(value.phase,'UNKNOWN')
        self.assertFalse(value.ready_seen)
        Path(str(value.test_journal)+'.release').touch()
        self.until(value,'READY')
        self.assertEqual(value.stdout,bytearray())
        value.command('close',timeout=2)

    def test_fragmented_reply_does_not_need_resending_input(self):
        value=self.fixture('fragment_reply');self.ready(value)
        value.command('status',timeout=.01)
        self.assertEqual(value.pending['sequence'],1)
        result=self.until(value,'READY')
        self.assertEqual(result['pendingSequence'],None)
        self.assertEqual(len(self.lines(value)),2)
        value.command('close',timeout=2)

    def test_stderr_is_fully_counted_and_hashed_but_tail_is_bounded(self):
        value=self.fixture('stderr_flood');self.ready(value)
        final=value.command('close',timeout=2)
        self.assertEqual(final['stderrBytes'],100000)
        self.assertEqual(final['stderrSha256'],hashlib.sha256(b'e'*100000).hexdigest())
        self.assertEqual(len(value.stderr_tail),channel.STDERR_TAIL)
        self.assertEqual(bytes(value.stderr_tail),b'e'*channel.STDERR_TAIL)

    def test_foreign_epoch_instance_or_service_never_establishes_ready(self):
        for mode in ('foreign_epoch','foreign_instance','foreign_service'):
            with self.subTest(mode=mode):
                value=self.fixture(mode)
                with self.assertRaises(channel.ServiceChannelRejected):value.start(b'{}',timeout=2)
                self.assertFalse(value.ready_seen)
                self.assertEqual(value.phase,'UNKNOWN')
                self.assertIsNotNone(value.failure)
                self.assertFalse(value.status()['volumeMayClose'])

    def test_final_before_ready_and_unsolicited_final_are_rejected(self):
        value=self.fixture('final_before_ready')
        with self.assertRaises(channel.ServiceChannelRejected):value.start(b'{}',timeout=2)
        self.assertIsNone(value.final_frame)
        value=self.fixture('unsolicited_final')
        try:
            value.start(b'{}',timeout=2)
            self.until(value,'COMPLETED')
        except channel.ServiceChannelRejected:
            pass
        else:self.fail('unsolicited final was accepted')
        self.assertIsNone(value.final_frame)

    def test_partial_eof_and_successful_exit_without_final_do_not_close(self):
        for mode in ('partial_eof','ready_exit'):
            with self.subTest(mode=mode):
                value=self.fixture(mode)
                try:
                    value.start(b'{}',timeout=2)
                    self.until(value,'COMPLETED')
                except channel.ServiceChannelRejected:
                    pass
                else:self.fail('exit without final was accepted')
                self.assertFalse(value.status()['childExited'])
                self.assertIsNone(value.final_frame)

    def test_nonzero_exit_and_trailing_bytes_invalidate_final(self):
        for mode in ('nonzero_final','trailing_final'):
            with self.subTest(mode=mode):
                value=self.fixture(mode);self.ready(value)
                with self.assertRaises(channel.ServiceChannelRejected):value.command('close',timeout=2)
                self.assertNotEqual(value.phase,'COMPLETED')
                self.assertFalse(value.status()['volumeMayClose'])

    def test_final_and_eof_are_not_exit_until_original_process_reaped(self):
        value=self.fixture('final_alive_eof');self.ready(value)
        result=value.command('close',timeout=.03)
        self.assertEqual(result['state'],'UNKNOWN')
        self.assertIsNotNone(value.final_frame)
        self.assertIsNone(value.process.poll())
        self.assertFalse(result['childExited'] or result['volumeMayClose'])
        result=self.until(value,'COMPLETED')
        self.assertTrue(result['childExited'])
        self.assertTrue(result['observedAfterUnknown'])

    def test_overlong_frame_is_fatal_with_bounded_memory(self):
        value=self.fixture('oversize')
        with self.assertRaisesRegex(channel.ServiceChannelRejected,'frame_bound'):
            value.start(b'{}',timeout=2)
        self.assertLessEqual(len(value.stdout),channel.MAX_FRAME+16384)
        with self.assertRaises(channel.ServiceChannelRejected):value.observe()
        self.assertFalse(value.status()['volumeMayClose'])

    def test_reply_sequence_must_match_exact_inflight_command(self):
        value=self.fixture('wrong_sequence');self.ready(value)
        with self.assertRaises(channel.ServiceChannelRejected):value.command('status',timeout=2)
        self.assertEqual(value.sequence,1)
        self.assertEqual(value.pending['sequence'],1)
        self.assertIsNotNone(value.failure)

    def test_pid_epoch_and_instance_input_bounds_fail_without_start(self):
        value=self.fixture()
        for epoch in (True,0,-1,2**63-1):
            with self.assertRaises(channel.ServiceChannelRejected):
                channel.ServiceChannel(value.process,service_id=SID,previous_epoch=epoch,
                                       instance_id='owned-service-2')
        for instance in ('bad/instance','line\nsecret','',None):
            with self.assertRaises(channel.ServiceChannelRejected):
                channel.ServiceChannel(value.process,service_id=SID,previous_epoch=1,
                                       instance_id=instance)
        self.assertEqual(self.lines(value),[])


class ObservedExitTests(unittest.TestCase):
    """Known process exit and delayed pipe delivery, without timing races."""
    class Process:
        pid = 12001
        def __init__(self, code):
            self.returncode = code
            self.stdin = io.BytesIO()
            self.waits = 0
        def poll(self):return self.returncode
        def wait(self, timeout):
            if timeout != 0:raise AssertionError('only a known exit may be reaped')
            self.waits += 1
            return self.returncode

    def frame(self, value, kind, state, sequence=0):
        closed = state == 'CLOSED'
        owner = {'protocol':'alaz-borrowed-service-v1','state':state,
            'pid':value.process.pid,'epoch':2,'instanceId':'owned-service-2',
            'endpoint':'http://127.0.0.1:45550','serviceStarted':True,
            'serviceReady':state=='READY','serviceClosed':closed,'admissionOpen':state=='READY',
            'close':{**{name:closed for name in wire._CLOSE_FLAGS},
                'physicalStoresClosed':3 if closed else 0,
                'callerLeaseReleased':closed,'imageLeaseReleasedHere':False},
            'reason':None,'admissionSealReason':None,'retryAllowed':False,
            'nativeStoresOwnedHere':False,'imageLeaseOwnedHere':False,'fullD3BAccepted':False}
        return wire.canonical({'protocol':wire.PROTOCOL,'type':kind,'serviceId':SID,
            'sequence':sequence,'requestId':wire.request_id(SID,sequence) if sequence else None,
            'owner':owner}) + b'\n'

    def make(self, code=0):
        value = channel.ServiceChannel(self.Process(code),service_id=SID,
            previous_epoch=1,instance_id='owned-service-2')
        value.input_started = True
        value.phase = 'STARTING'
        value.pending = {'type':'ready','sequence':0,'requestId':None}
        value.input_bytes = b'{}\n';value.input_written = len(value.input_bytes)
        return value

    def close_pending(self, value):
        value.sequence = 1
        value.pending = {'type':'reply','sequence':1,
            'requestId':wire.request_id(SID,1),'action':'close'}
        value.input_bytes = b'owned-close-frame\n';value.input_written = len(value.input_bytes)

    def test_known_exit_blocks_ready_and_draining_before_both_pipe_eofs(self):
        for state in ('READY','DRAINING'):
            value = self.make()
            ready = self.frame(value,'ready','READY')
            def deliver_ready(timeout, *, allow_write):
                self.assertTrue(allow_write)
                value._frames(ready)
                if state == 'DRAINING':
                    value.sequence = 1
                    value.pending = {'type':'reply','sequence':1,
                        'requestId':wire.request_id(SID,1),'action':'drain'}
                    value.input_bytes = b'owned-drain-frame\n'
                    value.input_written = len(value.input_bytes)
                    value._frames(self.frame(value,'reply','DRAINING',1))
            with patch.object(value,'_pump',side_effect=deliver_ready):
                result = value._wait(.1)
            self.assertEqual(result['state'],'UNKNOWN')
            self.assertEqual(result['owner']['state'],state)
            self.assertTrue(result['observedAfterUnknown'])
            self.assertFalse(result['childExited'] or result['volumeMayClose'])
            self.assertIsNone(value.failure)  # Remaining output is still drainable.
            self.assertFalse(value.stdout_eof or value.stderr_eof)
            sequence = value.sequence
            with self.assertRaisesRegex(channel.ServiceChannelRejected,'command_unavailable'):
                value.command('close')
            self.assertEqual(value.sequence,sequence)
            self.assertIsNone(value.pending)

    def test_nonzero_exit_fences_valid_final_before_pending_stderr_eof(self):
        value = self.make(code=7)
        value._frames(self.frame(value,'ready','READY'))
        self.close_pending(value)
        value._frames(self.frame(value,'final','CLOSED',1))
        value.stdout_eof = True
        value._reap()
        self.assertEqual(value.phase,'UNKNOWN')
        self.assertIsNone(value.failure)
        self.assertFalse(value.status()['childExited'] or value.status()['volumeMayClose'])
        diagnostic = b'fixture final diagnostic'
        def drain_stderr(timeout, *, allow_write):
            self.assertFalse(allow_write)
            value.stderr_bytes += len(diagnostic)
            value.stderr_digest.update(diagnostic)
            value.stderr_eof = True
        with patch.object(value,'_pump',side_effect=drain_stderr), self.assertRaisesRegex(
                channel.ServiceChannelRejected,'child_exit_unconfirmed'):
            value.observe()
        self.assertEqual(value.status()['stderrBytes'],len(diagnostic))
        self.assertEqual(value.status()['stderrSha256'],hashlib.sha256(diagnostic).hexdigest())
        self.assertEqual(value.phase,'UNKNOWN')

    def test_zero_exit_can_complete_after_delayed_buffered_valid_final(self):
        value = self.make()
        value._frames(self.frame(value,'ready','READY'))
        self.close_pending(value)
        final = self.frame(value,'final','CLOSED',1)
        value._reap()
        self.assertEqual(value.phase,'UNKNOWN')
        self.assertIsNone(value.failure)
        self.assertEqual(value.pending['action'],'close')
        written = value.input_written
        def partial(timeout, *, allow_write):
            self.assertFalse(allow_write)
            value._frames(final[:23])
        with patch.object(value,'_pump',side_effect=partial):
            self.assertEqual(value.observe()['state'],'UNKNOWN')
        self.assertEqual(value.input_written,written)
        self.assertEqual(bytes(value.stdout),final[:23])
        def remaining(timeout, *, allow_write):
            self.assertFalse(allow_write)
            value._frames(final[23:])
            value.stdout_eof = True
        with patch.object(value,'_pump',side_effect=remaining):
            result = value.observe()
        self.assertEqual(result['state'],'CHILD_CLOSED')
        self.assertFalse(result['childExited'] or result['volumeMayClose'])
        self.assertIsNone(value.pending)
        def stderr_eof(timeout, *, allow_write):
            self.assertFalse(allow_write)
            value.stderr_eof = True
        with patch.object(value,'_pump',side_effect=stderr_eof):
            result = value.observe()
        self.assertEqual(result['state'],'COMPLETED')
        self.assertTrue(result['childExited'] and result['observedAfterUnknown'])
        self.assertFalse(result['volumeMayClose'])
        self.assertEqual(value.process.returncode,0)


if __name__=='__main__':
    unittest.main()
