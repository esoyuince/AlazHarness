"""PLAT-002D-RECOVERY default-OFF persistent test-lease ledger tests.

Every test is pure Python parsing/state reconciliation or a temporary,
fixture-owned POSIX dirfd test. No WSL, model, provider, paid API,
production file, agent or host-UID change is performed by CI.
"""
from __future__ import annotations
import copy
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
MODULE=ROOT/'scripts/qa/wsl2_persistent_lease.py'
sp=importlib.util.spec_from_file_location('plat002d_persistent_lease',MODULE)
L=importlib.util.module_from_spec(sp)
sp.loader.exec_module(L)

BOOT='01234567-89ab-cdef-0123-456789abcdef'
OTHER_BOOT='abcdef01-2345-6789-abcd-0123456789ab'
RUN='a'*24
NONCE='b'*64
SOURCE='c'*64
ISSUED=11_000_000_000
EXPIRES=ISSUED+L.TTL_SECONDS*1_000_000_000

def record(phase='PREPARED'):
    value={
        'version':1,'kind':L.KIND,'phase':phase,
        'runId':RUN,'nonceSha256':NONCE,'sourceSha256':SOURCE,
        'bootId':BOOT,'guestUid':1000,
        'issuedBoottimeNs':ISSUED,'expiresBoottimeNs':EXPIRES,
        'issuerPid':1010,'issuerStartTick':450,
        'externalEffectOutcome':L.EXTERNAL_OUTCOME,
        'agentToolStarted':False,'realModelCalls':0,'fullD3BAccepted':False,
    }
    if phase in ('READY','TERMINAL'):
        value.update({
            'guardianPid':2201,'guardianStartTick':701,
            'workerPid':2202,'workerStartTick':702,
            'grandchildPid':2203,'grandchildStartTick':703,
        })
    if phase=='TERMINAL':
        value.update({
            'terminalBoottimeNs':EXPIRES+200,
            'terminalState':'LEASE_EXPIRED_EXTERNAL_OUTCOME_UNKNOWN',
            'leaseExpired':True,'ownedWorkerReaped':True,
            'ownedGrandchildReaped':True,'cleanupVerified':True,
        })
    return value

def observation(**kwargs):
    value={'bootId':BOOT,'boottimeNs':EXPIRES+300,
           'trackedPidsInspected':True,'processes':{
               '2201':None,'2202':None,'2203':None},
           'fsType':'ext4'}
    value.update(kwargs)
    return value

def must_reject(fn, code=None):
    try:fn()
    except L.LedgerRejected as exc:
        if code is not None:
            assert exc.code==code,(exc.code,code)
        return
    raise AssertionError('expected fail-closed ledger rejection')

class WireContract(unittest.TestCase):
    def test_prepared_strict_roundtrip(self):
        value=record()
        self.assertEqual(L.validate_record(value,'PREPARED'),value)
        self.assertEqual(L.decode_frame(L.encode_frame(value)),value)
        self.assertEqual(L.encode_frame(value)[-1:],b'\n')

    def test_ready_roundtrip(self):
        value=record('READY')
        self.assertEqual(L.validate_record(L.decode_frame(
            L.encode_frame(value)),'READY'),value)

    def test_terminal_roundtrip(self):
        value=record('TERMINAL')
        self.assertEqual(L.validate_record(
            L.decode_frame(L.encode_frame(value)),'TERMINAL'),value)

    def test_duplicate_json_keys_refused(self):
        raw=b'{"version":1,"version":1}\n'
        must_reject(lambda:L.decode_frame(raw),'DUPLICATE_RECORD_KEY')

    def test_bom_and_bad_utf8_refused(self):
        for raw in (b'\xef\xbb\xbf{}\n',b'\xff\n'):
            with self.subTest(raw=raw):
                must_reject(lambda:L.decode_frame(raw),'INVALID_RECORD_JSON')

    def test_crlf_and_double_lf_refused(self):
        for raw in (b'{}\r\n',b'{}\n\n',b'{}\r\r\n'):
            with self.subTest(raw=raw):
                must_reject(lambda:L.decode_frame(raw),'INVALID_FRAME_TERMINATOR')

    def test_missing_line_and_null_byte_refused(self):
        for raw in (b'{}',b'{\x00}\n'):
            must_reject(lambda raw=raw:L.decode_frame(raw),'INVALID_FRAME_TERMINATOR')

    def test_empty_and_oversize_refused(self):
        for raw in (b'',b'A'*(L.MAX_FRAME+1)):
            must_reject(lambda raw=raw:L.decode_frame(raw),'INVALID_FRAME_SIZE')

    def test_json_array_string_and_null_refused(self):
        for raw in (b'[]\n',b'"value"\n',b'null\n'):
            must_reject(lambda raw=raw:L.decode_frame(raw),'RECORD_OBJECT_REQUIRED')

    def test_nonfinite_numbers_refused(self):
        for raw in (b'{"a":NaN}\n',b'{"a":Infinity}\n'):
            must_reject(lambda raw=raw:L.decode_frame(raw),'NONFINITE_JSON_NOT_ALLOWED')

    def test_invalid_top_level_fails_encounter(self):
        for value in ([],None,'hi',0):
            must_reject(lambda value=value:L.encode_frame(value),'FRAME_OBJECT_REQUIRED')

    def test_encoded_object_over_budget_refused(self):
        must_reject(lambda:L.encode_frame({'a':'x'*L.MAX_FRAME}),
                    'FRAME_TOO_LARGE')

    def test_phase_unknown_and_extra_fields_refused(self):
        must_reject(lambda:L.validate_record(record(),'MISSING'),'UNSUPPORTED_LEDGER_PHASE')
        bad={**record(),'osCommand':'bash'}
        must_reject(lambda:L.validate_record(bad,'PREPARED'),'RECORD_SCHEMA_FIELDS')

    def test_exact_phase_not_implicit(self):
        must_reject(lambda:L.validate_record(record('READY'),'PREPARED'),
                    'RECORD_SCHEMA_FIELDS')

    def test_wrong_version_bool_and_kind_refused(self):
        for key,val in (('version',True),('version',2),
                        ('kind','agent.live'),('phase','READY')):
            with self.subTest(key=key,val=val):
                bad={**record(),key:val}
                must_reject(lambda bad=bad:L.validate_record(bad,'PREPARED'))

    def test_guest_uid_root_bool_or_nonnumeric_refused(self):
        for val in (0,True,'1000',None,-1):
            with self.subTest(value=val):
                bad={**record(),'guestUid':val}
                must_reject(lambda bad=bad:L.validate_record(bad,'PREPARED'),
                            'RECORD_LEASE_INVALID')

    def test_unknown_run_nonce_boot_source_rejected(self):
        values={'runId':['a'*23,'A'*24],
                'nonceSha256':['b'*63,'B'*64],
                'sourceSha256':['c'*63,'Z'*64],
                'bootId':['no-boot','ABCDEF01-2345-6789-abcd-0123456789ab']}
        for key,items in values.items():
            for item in items:
                with self.subTest(key=key,value=item):
                    bad={**record(),key:item}
                    must_reject(lambda bad=bad:L.validate_record(bad,'PREPARED'),
                                'RECORD_IDENTITY_INVALID')

    def test_lease_exact_duration_and_nonfinite_invalid(self):
        for field,value in [('expiresBoottimeNs',EXPIRES+1),
                            ('issuedBoottimeNs',True),
                            ('issuerPid',0),('issuerStartTick',0)]:
            bad={**record(),field:value}
            must_reject(lambda bad=bad:L.validate_record(bad,'PREPARED'),
                        'RECORD_LEASE_INVALID')

    def test_real_tool_or_d3b_authority_cannot_be_forged(self):
        for key,value in [('agentToolStarted',True),('realModelCalls',1),
                          ('realModelCalls',True),('fullD3BAccepted',True),
                          ('externalEffectOutcome','SUCCESS')]:
            with self.subTest(field=key):
                bad={**record(),key:value}
                must_reject(lambda bad=bad:L.validate_record(bad,'PREPARED'),
                            'RECORD_AUTHORITY_WIDENING')

    def test_process_group_pids_and_birth_ticks_required(self):
        for key,value in [('workerPid',2201),('grandchildPid',True),
                          ('guardianStartTick',0),('workerPid',0)]:
            with self.subTest(key=key):
                bad={**record('READY'),key:value}
                must_reject(lambda bad=bad:L.validate_record(bad,'READY'))

    def test_terminal_cannot_assert_premature_or_fake_closure(self):
        for key,value in [('terminalBoottimeNs',EXPIRES-1),
                          ('terminalState','SUCCESS'),('leaseExpired',False),
                          ('ownedWorkerReaped',False),
                          ('ownedGrandchildReaped',False),
                          ('cleanupVerified',False)]:
            with self.subTest(key=key):
                bad={**record('TERMINAL'),key:value}
                must_reject(lambda bad=bad:L.validate_record(bad,'TERMINAL'),
                            'TERMINAL_CLOSURE_NOT_PROVEN')

    def test_boot_and_nonce_crossrun_binding_rejected(self):
        prepared=record()
        for key,value in [('runId','f'*24),('bootId',OTHER_BOOT),
                          ('nonceSha256','d'*64),('guestUid',2000),
                          ('issuerStartTick',999)]:
            with self.subTest(key=key):
                ready={**record('READY'),key:value}
                must_reject(lambda ready=ready:L.assert_bound(prepared,ready),
                            'RUN_OR_LEASE_IDENTITY_DRIFT')

    def test_is_hex_wrong_required_length_never_aliases_sha(self):
        self.assertTrue(L.is_hex(RUN,24))
        self.assertTrue(L.is_hex(NONCE,64))
        self.assertFalse(L.is_hex(NONCE,20))
        self.assertFalse(L.is_hex(True,64))

class IndependentReconciliation(unittest.TestCase):
    def evaluate(self,ready=True,terminal=True,view=None):
        return L.snapshot_state(record(),record('READY') if ready else None,
                                record('TERMINAL') if terminal else None,
                                observation() if view is None else view)

    def test_absent_frozen_pid_set_not_full_orphan_clearance(self):
        reply=self.evaluate()
        self.assertEqual(reply['state'],
                         'RECORDED_PIDS_ABSENT_ORPHAN_CLOSURE_UNPROVEN')
        self.assertIs(reply['nativeSecurityAccepted'],False)
        self.assertIs(reply['independentOrphanClosureVerified'],False)
        self.assertIs(reply['processLaunchAuthorized'],False)
        self.assertIs(reply['automaticRetry'],False)
        self.assertEqual(reply['externalEffectOutcome'],L.EXTERNAL_OUTCOME)

    def test_boot_change_is_unknown_even_with_terminal(self):
        self.assertEqual(self.evaluate(view=observation(bootId=OTHER_BOOT))['state'],
                         'BOOT_CHANGED_UNKNOWN')

    def test_incomplete_pid_scan_never_success(self):
        self.assertEqual(self.evaluate(view=observation(
            trackedPidsInspected=False))['state'],
            'INCOMPLETE_TRACKED_PID_INSPECTION_UNKNOWN')

    def test_lease_active_unknown(self):
        self.assertEqual(self.evaluate(view=observation(
             boottimeNs=EXPIRES-1))['state'],
             'LEASE_ACTIVE_OR_CLOCK_UNKNOWN')

    def test_prepared_without_terminal_stays_unknown(self):
        self.assertEqual(self.evaluate(ready=False,terminal=False)['state'],
                         'LEASE_EXPIRED_TERMINAL_MISSING_UNKNOWN')

    def test_ready_without_terminal_stays_unknown(self):
        self.assertEqual(self.evaluate(ready=True,terminal=False)['state'],
                         'LEASE_EXPIRED_TERMINAL_MISSING_UNKNOWN')

    def test_terminal_without_ready_refused(self):
        must_reject(lambda:self.evaluate(ready=False,terminal=True),
                    'TERMINAL_WITHOUT_READY')

    def test_same_birth_tick_alive_unknown(self):
        obs=observation()
        obs['processes']['2202']={'state':'S','startTick':702}
        self.assertEqual(self.evaluate(view=obs)['state'],
                         'TEST_OWNED_PROCESS_STILL_PRESENT_UNKNOWN')

    def test_zombie_same_birth_tick_is_unknown(self):
        obs=observation()
        obs['processes']['2203']={'state':'Z','startTick':703}
        self.assertEqual(self.evaluate(view=obs)['state'],
                         'TEST_OWNED_PROCESS_STILL_PRESENT_UNKNOWN')

    def test_pid_reuse_never_certifies_closure(self):
        obs=observation()
        obs['processes']['2201']={'state':'S','startTick':999}
        self.assertEqual(self.evaluate(view=obs)['state'],
                         'PID_REUSED_CLOSURE_UNKNOWN')

    def test_terminal_timestamp_future_from_scan(self):
        self.assertEqual(self.evaluate(view=observation(
             boottimeNs=EXPIRES+100))['state'],
             'TERMINAL_AFTER_INSPECTION_UNKNOWN')

    def test_ready_and_terminal_pid_birth_mismatch_refused(self):
        prepared=record()
        ready=record('READY')
        terminal=record('TERMINAL')
        terminal['workerStartTick']+=1
        must_reject(lambda:L.snapshot_state(prepared,ready,terminal,observation()),
                    'PID_BIRTH_TICK_CHANGED')

    def test_missing_observed_pid_refused(self):
        obs=observation()
        obs['processes'].pop('2202')
        must_reject(lambda:self.evaluate(view=obs),
                    'PROCESS_SCAN_NOT_BOUND_TO_PIDS')

    def test_untrusted_proc_state_refused(self):
        for state in ('X','',5,False):
            obs=observation()
            obs['processes']['2201']={'state':state,'startTick':701}
            must_reject(lambda obs=obs:self.evaluate(view=obs),
                        'PROC_IDENTITY_UNTRUSTED')

    def test_observed_start_tick_bool_rejected(self):
        obs=observation()
        obs['processes']['2201']={'state':'S','startTick':True}
        must_reject(lambda:self.evaluate(view=obs),'PROC_IDENTITY_UNTRUSTED')

    def test_overlay_or_drvfs_not_an_accepted_native_ledger(self):
        for fs in ('overlay','9p','drvfs','ext3','tmpfs'):
            obs=observation(fsType=fs)
            must_reject(lambda obs=obs:self.evaluate(view=obs),
                        'UNTRUSTED_INSPECTION')

    def test_malformed_boot_inspection_rejected(self):
        obs=observation(bootId='not-a-boot-id')
        must_reject(lambda:self.evaluate(view=obs),'UNTRUSTED_INSPECTION')

    def test_unexpected_observation_fields_rejected(self):
        obs=observation(extraCloudApproval=True)
        must_reject(lambda:self.evaluate(view=obs),'INSPECTION_FIELDS')

    def test_ready_same_run_changed_nonce_refused(self):
        ready=record('READY')
        ready['nonceSha256']='d'*64
        must_reject(lambda:L.snapshot_state(record(),ready,None,observation()),
                    'RUN_OR_LEASE_IDENTITY_DRIFT')

class CliFailClosed(unittest.TestCase):
    def call(self,args,withoptin=False):
        env=dict(os.environ)
        env.pop('ALAZ_PLAT002D_PERSISTENT_QA',None)
        if withoptin:
            env['ALAZ_PLAT002D_PERSISTENT_QA']='1'
        return subprocess.run([sys.executable,'-B',str(MODULE),*args],
            cwd=ROOT,capture_output=True,text=True,env=env,timeout=9)

    def test_unknown_user_provided_path_refused_without_open(self):
        z=self.call(['--mode','inspect','--run-id',RUN,
                     '--nonce-sha256',NONCE,'--source-sha256',SOURCE,
                     '--directory','C:\\Users\\Public'])
        self.assertEqual(z.returncode,2)

    def test_prepare_no_optin_never_writes_guest(self):
        z=self.call(['--mode','prepare','--run-id',RUN,
                     '--nonce-sha256',NONCE,'--source-sha256',SOURCE])
        self.assertEqual(z.returncode,2)
        self.assertEqual(json.loads(z.stdout)['state'],'REFUSED')
        self.assertNotIn('C:\\',z.stdout)

    def test_inspect_windows_no_start(self):
        if sys.platform=='win32':
            z=self.call(['--mode','inspect','--run-id',RUN,
                         '--nonce-sha256',NONCE,'--source-sha256',SOURCE])
            self.assertEqual(z.returncode,2)
            self.assertEqual(json.loads(z.stdout)['state'],'REFUSED')

    def test_bad_run_id_with_qa_optin_refuses(self):
        z=self.call(['--mode','prepare','--run-id','../home',
                     '--nonce-sha256',NONCE,'--source-sha256',SOURCE],
                    withoptin=True)
        self.assertEqual(z.returncode,2)
        self.assertEqual(json.loads(z.stdout)['externalEffectOutcome'],
                         'UNKNOWN_DO_NOT_REPLAY')

    def test_main_optin_parser_no_guest_mutation(self):
        out=io.StringIO()
        with redirect_stdout(out),patch.dict(os.environ,
                 {'ALAZ_PLAT002D_PERSISTENT_QA':'0'}):
            code=L.main(['--mode','prepare','--run-id',RUN,
                         '--nonce-sha256',NONCE,'--source-sha256',SOURCE])
        self.assertEqual(code,2)
        self.assertEqual(json.loads(out.getvalue())['state'],'REFUSED')

    def test_source_module_import_does_not_create_run_directory(self):
        self.assertTrue(MODULE.is_file())
        self.assertFalse((ROOT/'runtime/plat002d-persistent-production').exists())

if __name__=='__main__':
    unittest.main()
