"""Offline process-evidence rejection tests, not additional native executions."""
import copy
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from verify_execution_receipts import verify_exit,digest


def pair():
    ready={'pid':1234,'nonce':'a'*32,'state':'ready','profile_bound':True,'api_host':'127.0.0.1',
       'runner':'gateway.run.GatewayRunner','authority':'gateway.session_authority.SessionAuthority',
       'adapter':'gateway.platforms.api_server.APIServerAdapter'}
    exit={'exit_code':0,'forced':False,'kill_requested':False,'native_reaped':True,'launcher_reaped':True,
       'native_pid':1234,'launcher_pid':1200,'nonce':'a'*32,'ownership_chain':[1234,1200],
       'shutdown':{'native_result':True,'lifecycle_completed':True,'pid':1234,'nonce':'a'*32,'nonloopback_attempts_blocked':0}}
    return ready,exit

class ExecutionExitEvidenceTests(unittest.TestCase):
    def test_complete_synthetic_exit(self):verify_exit(*pair())
    def rejected(self,where,key,value):
        a,b=pair();target={'ready':a,'exit':b,'shutdown':b['shutdown']}[where];target[key]=value
        with self.assertRaises(ValueError):verify_exit(a,b)
    def test_false_pid_rejected(self):self.rejected('ready','pid',True)
    def test_fake_native_class_rejected(self):self.rejected('ready','runner','fake.GatewayRunner')
    def test_nonloopback_listener_rejected(self):self.rejected('ready','api_host','0.0.0.0')
    def test_nonready_state_rejected(self):self.rejected('ready','state','starting')
    def test_missing_profile_binding_rejected(self):self.rejected('ready','profile_bound',False)
    def test_nonzero_exit_rejected(self):self.rejected('exit','exit_code',1)
    def test_bool_zero_exit_rejected(self):self.rejected('exit','exit_code',False)
    def test_forced_exit_rejected(self):self.rejected('exit','forced',True)
    def test_killed_process_rejected(self):self.rejected('exit','kill_requested',True)
    def test_live_native_rejected(self):self.rejected('exit','native_reaped',False)
    def test_live_launcher_rejected(self):self.rejected('exit','launcher_reaped',False)
    def test_foreign_nonce_rejected(self):self.rejected('exit','nonce','b'*32)
    def test_foreign_ownership_chain_rejected(self):self.rejected('exit','ownership_chain',[1234,999])
    def test_repeated_pid_chain_rejected(self):self.rejected('exit','ownership_chain',[1234,1234,1200])
    def test_failed_native_close_rejected(self):self.rejected('shutdown','native_result',False)
    def test_other_shutdown_nonce_rejected(self):self.rejected('shutdown','nonce','b'*32)
    def test_external_network_attempt_rejected(self):self.rejected('shutdown','nonloopback_attempts_blocked',1)
    def test_boolean_network_counter_rejected(self):self.rejected('shutdown','nonloopback_attempts_blocked',False)
    def test_explicit_network_observation_retains_count(self):
        ready,exit=pair();exit['shutdown']['nonloopback_attempts_blocked']=6
        self.assertEqual(verify_exit(ready,exit,allow_blocked_network=True),6)
    def test_truthy_option_does_not_relax_strict_check(self):
        ready,exit=pair();exit['shutdown']['nonloopback_attempts_blocked']=6
        with self.assertRaises(ValueError):verify_exit(ready,exit,allow_blocked_network=1)
    def test_seal_ignores_old_digest_only(self):
        base={'tokens':123,'outcome':'response'}
        self.assertEqual(digest(base),digest(base|{'digest':'old'}))
        self.assertNotEqual(digest(base),digest(base|{'tokens':124}))

if __name__=='__main__':unittest.main()
