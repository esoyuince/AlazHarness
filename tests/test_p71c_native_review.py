"""Offline evidence-review controls, not additional native UID transitions."""
import copy
import json
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts/qa'))
import p71c_review as review
E=ROOT/'evidence/d3b-positive-lab-p71c'

class PositiveLabReview(unittest.TestCase):
    def setUp(self):
        self.record=json.loads((E/'native-acceptance-001.json').read_text())
        self.trace=(E/'native-broker2-strace.txt').read_text()
    def check(self):return review.review(self.record,self.trace)
    def denied(self):
        with self.assertRaises(ValueError):self.check()
    def test_real_native_observations_pass_strict_review(self):
        value=self.check();self.assertEqual(value['nativeChecks'],20)
        self.assertFalse(value['fullD3BAccepted']);self.assertFalse(value['newNativeExecution'])
    def test_null_and_empty_array_are_equivalent_zero_group_renderings(self):
        self.trace=self.trace.replace('setgroups(0, [])','setgroups(0, NULL)')
        self.assertEqual(self.check()['traceChecks'],6)
    def test_nonempty_groups_not_accepted(self):
        self.trace=self.trace.replace('setgroups(0, [])','setgroups(1, [23003])');self.denied()
    def test_failed_actual_syscall_not_accepted(self):
        self.trace=self.trace.replace('setresuid(23002, 23002, 23002)    = 0',
            'setresuid(23002, 23002, 23002)    = -1 EPERM')
        self.denied()
    def test_wrong_observed_uid_not_accepted(self):
        self.record['lifetimes'][0]['postexec']['fields']['Uid'][2]='0';self.denied()
    def test_remaining_capability_not_accepted(self):
        self.record['lifetimes'][1]['postexec']['fields']['CapBnd']=['0000000000000001'];self.denied()
    def test_remapped_user_namespace_not_accepted(self):
        self.record['lifetimes'][1]['postexec']['uidMap']=['0','23002','1'];self.denied()
    def test_missing_filter_not_accepted(self):
        self.record['lifetimes'][0]['postexec']['fields']['Seccomp']=['0'];self.denied()
    def test_missing_file_is_not_access_denial(self):
        self.record['lifetimes'][0]['gatewayDenials']['accesses'][0]['errno']=2;self.denied()
    def test_failed_owner_control_not_accepted(self):
        self.record['lifetimes'][0]['brokerOwnerControls']['accesses'][0]['opened']=False;self.denied()
    def test_changed_private_file_not_accepted(self):
        self.record['privateFilesAfter']['/srv/alaz-p71c/private/config.json']['sha256']='f'*64;self.denied()
    def test_wrong_server_observed_gateway_pid_not_accepted(self):
        pid=self.record['lifetimes'][1]['positiveClient']['self']['pid']
        self.trace=self.trace.replace('pid='+str(pid)+', uid=23001','pid=999999, uid=23001');self.denied()
    def test_provider_attempt_not_accepted(self):
        self.record['lifetimes'][0]['shutdown']['counters']['physicalAttempts']=1;self.denied()
    def test_stale_broker_identity_must_be_refused(self):
        self.record['lifetimes'][1]['staleClient']['transport']['reply']['ok']=True;self.denied()
    def test_other_original_failure_cannot_be_reconciled_as_parser_issue(self):
        self.record['checks']['all_owned_processes_reaped']=False;self.denied()
    def test_trace_order_must_match_actual_identity_drop_then_exec(self):
        lines=self.trace.splitlines();a=next(i for i,s in enumerate(lines) if 'setresuid(' in s)
        b=next(i for i,s in enumerate(lines) if 'run_principal_broker_target.py' in s)
        lines[a],lines[b]=lines[b],lines[a];self.trace='\n'.join(lines);self.denied()

if __name__=='__main__':unittest.main()
