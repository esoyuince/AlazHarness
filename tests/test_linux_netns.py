"""Offline network launcher contracts, plus custody of explicit Linux experiments.
Does not create namespaces or launch Gateway during standard discovery.
"""
import ctypes,errno,importlib.util,json,sys,tempfile,unittest
from contextlib import ExitStack,redirect_stderr
from io import StringIO
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'packages/claw-hermes'))
import linux_netns as n

class Fn:
    def __init__(self,callback):self.callback=callback
    def __call__(self,*args):return self.callback(*args)
class FakeSeccomp:
    def __init__(self,load=0,rule=0):
        self.names=[];self.rules=[];self.released=False
        self.seccomp_init=Fn(lambda _:1)
        self.seccomp_release=Fn(self.release)
        self.seccomp_load=Fn(lambda _:load)
        self.seccomp_syscall_resolve_name=Fn(self.number)
        self.rule_rc=rule
        self.seccomp_rule_add_array=Fn(self.add)
    def number(self,name):
        self.names.append(name.decode());return len(self.names)-1
    def add(self,context,action,number,count,compare):
        condition=None if not count else (compare[0].arg,compare[0].op,compare[0].datum_a,compare[0].datum_b)
        self.rules.append((self.names[number],action,condition));return self.rule_rc
    def release(self,*_):self.released=True

class FilterContracts(unittest.TestCase):
    def test_restricts_namespace_reentry_and_fd_acquisition(self):
        lib=FakeSeccomp();n._filter(lib)
        names={x[0] for x in lib.rules}
        self.assertTrue({'unshare','setns','ptrace','pidfd_getfd','recvmsg','recvmmsg','process_vm_readv'}<=names)
        self.assertNotIn('sendmsg',names)
        self.assertNotIn('sendmmsg',names)
    def test_clone3_returns_enosys_for_safe_thread_fallback(self):
        lib=FakeSeccomp();n._filter(lib)
        self.assertIn(('clone3',n.ERRNO|errno.ENOSYS,None),lib.rules)
    def test_uring_cannot_create_unfiltered_sockets(self):
        lib=FakeSeccomp();n._filter(lib)
        for name in ('io_uring_setup','io_uring_enter','io_uring_register'):
            self.assertIn((name,n.ERRNO|errno.ENOSYS,None),lib.rules)
    def test_clone_namespace_flags_are_blocked(self):
        lib=FakeSeccomp();n._filter(lib)
        masks={x[2][2] for x in lib.rules if x[0]=='clone'}
        self.assertEqual(masks,set(n.NEW_NAMESPACE_FLAGS))
    def test_non_ip_and_unix_socket_families_are_refused(self):
        lib=FakeSeccomp();n._filter(lib)
        blocked=[]
        for family in range(64):
            if any(x[0]=='socket' and x[2][0]==0 and
                   ((x[2][1]==4 and family==x[2][2]) or
                    (x[2][1]==6 and family>x[2][2])) for x in lib.rules):blocked.append(family)
        self.assertEqual(set(range(64))-set(blocked),{1,2,10})
    def test_filter_load_failure_is_fail_closed(self):
        lib=FakeSeccomp(load=-1)
        with self.assertRaisesRegex(n.NetworkBoundaryError,'seccomp_load_failed'):n._filter(lib)
        self.assertTrue(lib.released)
    def test_rule_failure_is_fail_closed(self):
        lib=FakeSeccomp(rule=-1)
        with self.assertRaisesRegex(n.NetworkBoundaryError,'seccomp_rule_failed'):n._filter(lib)
        self.assertTrue(lib.released)
    def test_missing_library_is_not_optional(self):
        with patch.object(n.ctypes.util,'find_library',return_value=None):
            with self.assertRaisesRegex(n.NetworkBoundaryError,'libseccomp_required'):n._load_seccomp()

class AdmissionContracts(unittest.TestCase):
    def test_non_linux_refused_before_any_syscall(self):
        with patch.object(n.platform,'system',return_value='Windows'):
            with self.assertRaisesRegex(n.NetworkBoundaryError,'linux_x86_64_required'):n.enter()
    def test_wrong_architecture_refused(self):
        with patch.object(n.platform,'system',return_value='Linux'),patch.object(n.platform,'machine',return_value='aarch64'):
            with self.assertRaisesRegex(n.NetworkBoundaryError,'linux_x86_64_required'):n.enter()
    def test_root_identity_refused(self):
        with ExitStack() as stack:
            stack.enter_context(patch.object(n.platform,'system',return_value='Linux'))
            stack.enter_context(patch.object(n.platform,'machine',return_value='x86_64'))
            stack.enter_context(patch.object(n.os,'getuid',return_value=0,create=True))
            with self.assertRaisesRegex(n.NetworkBoundaryError,'unprivileged_same_identity_required'):n.enter()
    def test_multithread_process_refused(self):
        with ExitStack() as stack:
            stack.enter_context(patch.object(n.platform,'system',return_value='Linux'))
            stack.enter_context(patch.object(n.platform,'machine',return_value='x86_64'))
            for name in ('getuid','geteuid','getgid','getegid'):
                stack.enter_context(patch.object(n.os,name,return_value=1000,create=True))
            stack.enter_context(patch.object(n.threading,'active_count',return_value=2))
            with self.assertRaisesRegex(n.NetworkBoundaryError,'fresh_single_thread_required'):n.enter()
    def test_launch_never_executes_on_boundary_failure(self):
        spec=importlib.util.spec_from_file_location('nslauncher',ROOT/'scripts/run_in_network_namespace.py')
        mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
        with tempfile.TemporaryDirectory() as d,patch.object(mod,'enter',side_effect=n.NetworkBoundaryError('no_boundary')),patch.object(mod.os,'execv') as execute,redirect_stderr(StringIO()):
            output=Path(d)/'new.json'
            with patch.object(sys,'argv',['launcher','--receipt',str(output),'--',sys.executable,'-c','pass']):self.assertEqual(mod.main(),2)
            execute.assert_not_called();self.assertFalse(output.exists())

class NativeEvidenceCustody(unittest.TestCase):
    def test_real_kernel_probe_and_exec_inheritance_passed(self):
        row=json.loads((ROOT/'evidence/d3b-netns-4e62/native-network-final.json').read_text())
        self.assertEqual(row['result'],'PASS');self.assertEqual(row['exitCode'],0)
        self.assertTrue(all(row['checks'].values()))
        self.assertEqual(row['unexpectedHostTcpConnections'],0)
        self.assertFalse(row['completeD3B'])
    def test_real_gateway_uses_same_filter_with_original_broker(self):
        path=ROOT/'evidence/d3b-netns-4e62'
        run=json.loads((path/'gateway-normal-final.json').read_text())
        bound=json.loads((path/'gateway-normal-final-boundary.json').read_text())
        self.assertEqual(run['result'],'PASS');self.assertEqual(bound['result'],'PASS')
        self.assertTrue(run['nativeHermesGateway']);self.assertTrue(run['originalAiohttpBroker'])
        self.assertEqual(run['origin']['accepted'],4)
        self.assertEqual(run['broker']['activeRequests'],0)
        self.assertTrue(all(all(sample.values()) for sample in bound['gatewayNetworkBoundarySamples']))
        self.assertFalse(bound['hostFilesystemSeparated']);self.assertFalse(bound['completeD3B'])
    def test_failed_first_attempt_is_preserved(self):
        row=json.loads((ROOT/'evidence/d3b-netns-4e62/gateway-normal-initial.json').read_text())
        self.assertEqual(row['result'],'FAIL');self.assertTrue(row['errors'])
        self.assertEqual(row['broker']['exitCode'],0)

    def test_negative_gateway_outcomes_stay_unconfirmed(self):
        directory=ROOT/'evidence/d3b-netns-4e62'
        for case,count in [('budget-limit',3),('candidate-disconnect',4),('review-revoked',3)]:
            with self.subTest(case=case):
                row=json.loads((directory/('gateway-'+case+'-final.json')).read_text())
                guard=json.loads((directory/('gateway-'+case+'-final-boundary.json')).read_text())
                self.assertEqual(row['result'],'PASS');self.assertEqual(guard['result'],'PASS')
                self.assertEqual(row['trial']['state'],'unknown')
                self.assertEqual(row['origin']['accepted'],count)
                self.assertEqual(row['trial']['replayAddedReservations'],0)
                self.assertEqual(row['broker']['exitCode'],0)
                self.assertTrue(row['broker']['socketRemoved'])

if __name__=='__main__':unittest.main()
