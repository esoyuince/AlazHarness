"""Offline synthetic receipt tests. They DO NOT run/accept Windows AppContainer.

A passing hypothetical schema below is only an input fixture. Actual native
observations retained in evidence fail the stricter explicit-loopback-denial gate.
"""
from __future__ import annotations
from copy import deepcopy
import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location('appcontainer_qa4023',ROOT/'scripts/qa/run_windows_appcontainer_probe.py')
MODULE=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(MODULE)


def fixture():
    sid='S-1-15-2-11-22-33-44-55-66-77'
    value={'result':'PASS','errors':[],'hermesIsolationAccepted':False,'firewallModified':False,
           'loopbackExemptionAdded':False,'listenersStopped':True,'fixtureSecretUnchanged':True,
           'profileDeleteHresult':0,'modelCalls':0,'ipv4ListenerMessages':1,'ipv6ListenerMessages':1,
           'profileName':'AlazHarness.QA.'+'a'*32,'appContainerSid':sid}
    for i,name in enumerate(['baseline','isolated','timeoutProbe'],1):
        restricted=name!='baseline';hang=name=='timeoutProbe'
        identity={'isAppContainer':restricted,'capabilityCount':0,'appContainerSid':sid if restricted else None,
                  'integritySid':'S-1-16-4096' if restricted else 'S-1-16-8192'}
        row={'pid':100+i,'identityBeforeResume':identity,'jobAssignedBeforeResume':True,
             'handlesInherited':False,'processReaped':True,'timedOut':hang,'exitCode':91 if hang else 0}
        if not hang:
            child=dict(identity,parentSecretInEnvironment=not restricted,allowedReadError=0,
                       ipv4Error=10013 if restricted else 0,ipv6Error=10013 if restricted else 0)
            child.update({k:5 if restricted else 0 for k in ['privateReadError','privateWriteError','allowedWriteError','parentMemoryOpenError']})
            if restricted:child['testNetError']=10013
            row['child']=child
        value[name]=row
    return value


class WindowsReceiptContracts(unittest.TestCase):
    def check_change(self,path,new):
        value=fixture();target=value
        for key in path[:-1]:target=target[key]
        target[path[-1]]=new
        self.assertTrue(MODULE.validate_observation(value),path)
    def test_hypothetical_valid_schema_not_native_acceptance(self):
        self.assertEqual(MODULE.validate_observation(fixture()),[])
    def test_nonobject_refused(self):self.assertTrue(MODULE.validate_observation(None))
    def test_missing_parent_observation_refused(self):
        value=fixture();del value['isolated']['identityBeforeResume'];self.assertTrue(MODULE.validate_observation(value))
    def test_loopback_timeout_is_not_explicit_denial(self):self.check_change(['isolated','child','ipv4Error'],10060)
    def test_ipv6_timeout_is_not_explicit_denial(self):self.check_change(['isolated','child','ipv6Error'],10060)
    def test_network_unreachable_not_permission_denied(self):self.check_change(['isolated','child','testNetError'],10051)
    def test_nonloopback_timeout_not_permission_denied(self):self.check_change(['isolated','child','testNetError'],10060)
    def test_parent_memory_access_must_be_denied(self):self.check_change(['isolated','child','parentMemoryOpenError'],0)
    def test_unrestricted_token_cannot_be_success(self):self.check_change(['isolated','identityBeforeResume','isAppContainer'],False)
    def test_child_saying_sandbox_cannot_replace_parent_token(self):self.check_change(['isolated','identityBeforeResume','appContainerSid'],'S-1-15-2-1-1-1-1-1-1-1')
    def test_network_capability_not_zero(self):self.check_change(['isolated','identityBeforeResume','capabilityCount'],1)
    def test_medium_integrity_not_low(self):self.check_change(['isolated','identityBeforeResume','integritySid'],'S-1-16-8192')
    def test_secret_environment_leak_refused(self):self.check_change(['isolated','child','parentSecretInEnvironment'],True)
    def test_private_file_read_leak_refused(self):self.check_change(['isolated','child','privateReadError'],0)
    def test_private_file_write_leak_refused(self):self.check_change(['isolated','child','privateWriteError'],0)
    def test_allowed_directory_write_refused(self):self.check_change(['isolated','child','allowedWriteError'],0)
    def test_allowed_read_must_actually_work(self):self.check_change(['isolated','child','allowedReadError'],5)
    def test_failed_baseline_is_not_isolation(self):self.check_change(['baseline','child','ipv4Error'],10060)
    def test_extra_listener_message_refused(self):self.check_change(['ipv6ListenerMessages'],2)
    def test_no_job_refused(self):self.check_change(['isolated','jobAssignedBeforeResume'],False)
    def test_inherited_handles_refused(self):self.check_change(['isolated','handlesInherited'],True)
    def test_unreaped_process_refused(self):self.check_change(['timeoutProbe','processReaped'],False)
    def test_unenforced_deadline_refused(self):self.check_change(['timeoutProbe','timedOut'],False)
    def test_wrong_timeout_exit_refused(self):self.check_change(['timeoutProbe','exitCode'],0)
    def test_profile_cleanup_error_refused(self):self.check_change(['profileDeleteHresult'],5)
    def test_listener_cleanup_error_refused(self):self.check_change(['listenersStopped'],False)
    def test_false_zero_is_not_numeric_model_count(self):self.check_change(['modelCalls'],False)
    def test_reused_pid_is_not_three_lifetimes(self):self.check_change(['isolated','pid'],101)
    def test_full_hermes_claim_not_allowed(self):self.check_change(['hermesIsolationAccepted'],True)
    def test_no_modification_to_fixture(self):
        value=fixture();before=deepcopy(value);MODULE.validate_observation(value);self.assertEqual(value,before)
    def test_documented_partial_observation_stays_rejected(self):
        value=fixture();value['result']='FAIL';value['errors']=['InvalidOperationException:isolation_ipv4Error']
        value['isolated']['child']['ipv4Error']=10060;value['isolated']['child']['ipv6Error']=10060
        self.assertEqual(MODULE.validate_observation(value),['result','errors','isolated_ipv4Error','isolated_ipv6Error'])
    def test_launcher_whitelist_not_parent_secret_copy(self):
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp);environment={'SystemRoot':str(folder),'LOCALAPPDATA':str(folder),
                     'OPENAI_API_KEY':'synthetic-must-not-transfer','HTTP_PROXY':'synthetic-must-not-transfer',
                     'AWS_SECRET_ACCESS_KEY':'synthetic-must-not-transfer','HOME':str(folder),'PATH':'synthetic-must-not-transfer'}
            with patch.dict(os.environ,environment,clear=True):result=MODULE.environment(folder)
            self.assertEqual(set(result),{'SystemRoot','WINDIR','LOCALAPPDATA','TEMP','TMP'})
            self.assertNotIn('synthetic-must-not-transfer',str(result))
    def test_missing_launcher_profile_path_refused(self):
        with patch.dict(os.environ,{'SystemRoot':'irrelevant'},clear=True):
            with self.assertRaises(ValueError):MODULE.environment(Path('.'))

if __name__=='__main__':unittest.main()
