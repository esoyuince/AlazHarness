"""Post-exec gate unit tests; privileged kernel state is explicitly mocked."""
from contextlib import ExitStack, redirect_stderr
import copy
import io
import json
import hashlib
from pathlib import Path
import sys
import unittest
from unittest.mock import patch, Mock, AsyncMock
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'packages/claw-hermes')]
import principal_target as target
import run_principal_broker_target as cli


def principal():
    return {'version':1,'enabled':True,'gatewayUid':1000,'brokerUid':1101,
            'socketGroupGid':1102,'hostUserNamespace':'user:[4026531837]'}


def state():
    return {'pid':31,'uids':(1101,)*4,'gids':(1102,)*4,'groups':(),
            'threads':1,'nnp':1,'caps':{k:0 for k in target.launch.CAPS},
            'userns':principal()['hostUserNamespace'],
            'uidMap':['0','0','4294967295'],'gidMap':['0','0','4294967295']}


class KernelGate(unittest.TestCase):
    def check(self, change=None, mode=2):
        s=state();s.update(change or {})
        with (patch.object(target.launch,'observation',return_value=s),
              patch.object(target,'seccomp_mode',return_value=mode)):
            return target.restricted_kernel(principal())

    def test_exact_restricted_kernel_observation_passes(self):
        self.assertEqual(self.check(),state())

    def test_each_real_effective_saved_filesystem_id_is_required(self):
        for field in ('uids','gids'):
            for index in range(4):
                for wrong in (0,1000,True):
                    values=list(state()[field]);values[index]=wrong
                    with self.subTest(field=field,index=index,wrong=wrong),self.assertRaises(target.TargetRejected):
                        self.check({field:tuple(values)})

    def test_initial_namespace_and_both_maps_are_required(self):
        for fields in ({'userns':'user:[99]'},{'uidMap':['0','1000','1']},
                       {'gidMap':['0','1000','1']}):
            with self.subTest(fields=fields),self.assertRaises(target.TargetRejected):self.check(fields)

    def test_each_capability_set_must_be_zero(self):
        for cap in target.launch.CAPS:
            caps=state()['caps'];caps[cap]=1
            with self.subTest(cap=cap),self.assertRaises(target.TargetRejected):self.check({'caps':caps})

    def test_incomplete_or_boolean_capability_sets_rejected(self):
        for caps in ({},dict(state()['caps'],CapEff=False),dict(state()['caps'],unknown=0)):
            with self.subTest(caps=caps),self.assertRaises(target.TargetRejected):self.check({'caps':caps})

    def test_groups_threads_and_no_new_privs_required(self):
        for fields in ({'groups':(1102,)},{'groups':[]},{'nnp':0},{'nnp':True},
                       {'threads':2},{'threads':True},{'pid':0}):
            with self.subTest(fields=fields),self.assertRaises(target.TargetRejected):self.check(fields)

    def test_python_thread_count_also_required(self):
        with patch.object(target.threading,'active_count',return_value=2),self.assertRaises(target.TargetRejected):self.check()

    def test_missing_strict_or_boolean_filter_mode_refused(self):
        for mode in (0,1,-1,True,'2'):
            with self.subTest(mode=mode),self.assertRaises(target.TargetRejected):self.check(mode=mode)

    def test_prctl_failure_is_not_filter_success(self):
        lib=Mock();lib.prctl.return_value=-1
        with patch.object(target.ctypes,'CDLL',return_value=lib),self.assertRaises(target.TargetRejected):target.seccomp_mode()


class Preparation(unittest.TestCase):
    def setUp(self):
        self.events=[];self.s=state();self.principal=principal()
        self.raw=json.dumps({'principal_contract':principal()}).encode()
        self.digest=hashlib.sha256(self.raw).hexdigest()
        self.cfg=object();self.stack=ExitStack();self.addCleanup(self.stack.close)
        def step(name,result):
            def run(*args,**kwargs):self.events.append(name);return result
            return run
        self.observe=self.stack.enter_context(patch.object(target,'restricted_kernel',side_effect=step('kernel',self.s)))
        self.load=self.stack.enter_context(patch.object(target.net,'_load_seccomp',side_effect=step('load',object())))
        self.close=self.stack.enter_context(patch.object(target.launch,'close_ambient_fds',side_effect=step('close',None)))
        self.filter=self.stack.enter_context(patch.object(target.net,'_filter',side_effect=step('filter',None)))
        self.read=self.stack.enter_context(patch.object(target.launch,'file_bytes',side_effect=step('read',self.raw)))
        self.parse=self.stack.enter_context(patch('provider_egress.BrokerConfig',side_effect=step('config',self.cfg)))
        self.deployment=self.stack.enter_context(patch.object(target.launch,'deployment',side_effect=step('deployment',{})))

    def run_prepare(self,**change):
        args={'principal':self.principal,'config_path':'/srv/alaz/private/broker.json',
              'config_sha256':self.digest,'output':'/srv/alaz/socket'}
        args.update(change);return target.prepare(**args)

    def test_exact_order_kernel_filter_config_deployment_recheck(self):
        self.assertIs(self.run_prepare(),self.cfg)
        self.assertEqual(self.events,['kernel','load','close','filter','kernel','read','config','deployment','kernel'])
        self.filter.assert_called_once()
        self.read.assert_called_once_with('/srv/alaz/private/broker.json',1101,0o600,32768)
        value=self.deployment.call_args.args[0]
        self.assertEqual(value['principalContract'],principal())
        self.assertEqual(value['configSha256'],self.digest)

    def test_unrestricted_process_cannot_read_config_or_install_filter(self):
        self.observe.side_effect=target.TargetRejected('wrong_kernel')
        with self.assertRaisesRegex(target.TargetRejected,'wrong_kernel'):self.run_prepare()
        self.read.assert_not_called();self.load.assert_not_called();self.deployment.assert_not_called()

    def test_filter_setup_or_fd_cleanup_failure_prevents_config_read(self):
        for mock in (self.load,self.close,self.filter):
            old=mock.side_effect;mock.side_effect=RuntimeError('injected')
            with self.assertRaises(RuntimeError):self.run_prepare()
            self.read.assert_not_called();mock.side_effect=old

    def test_kernel_change_after_filter_prevents_config_read(self):
        self.observe.side_effect=[self.s,dict(self.s,pid=32)]
        with self.assertRaisesRegex(target.TargetRejected,'kernel_changed'):self.run_prepare()
        self.read.assert_not_called()

    def test_digest_mismatch_refuses_before_config_parse(self):
        with self.assertRaisesRegex(target.TargetRejected,'config_changed'):self.run_prepare(config_sha256='0'*64)
        self.parse.assert_not_called();self.deployment.assert_not_called()

    def test_hash_matching_wrong_principal_refused(self):
        raw=json.dumps({'principal_contract':dict(principal(),brokerUid=1201)}).encode()
        self.read.side_effect=None;self.read.return_value=raw
        with self.assertRaisesRegex(target.TargetRejected,'principal_mismatch'):
            self.run_prepare(config_sha256=hashlib.sha256(raw).hexdigest())
        self.parse.assert_not_called()

    def test_invalid_config_still_uses_actual_config_validator(self):
        self.parse.side_effect=ValueError('invalid_private_configuration')
        with self.assertRaises(ValueError):self.run_prepare()
        self.deployment.assert_not_called()

    def test_private_budget_or_output_rejection_is_fatal(self):
        self.deployment.side_effect=target.launch.LaunchRejected('not_provisioned')
        with self.assertRaises(target.launch.LaunchRejected):self.run_prepare()

    def test_kernel_change_after_deployment_prevents_return(self):
        self.observe.side_effect=[self.s,self.s,dict(self.s,pid=32)]
        with self.assertRaisesRegex(target.TargetRejected,'kernel_changed'):self.run_prepare()

    def test_paths_digests_and_overlap_checked_before_kernel_calls(self):
        for change in ({'config_sha256':'A'*64},{'config_sha256':True},
                       {'output':'/'+('a'*101)},
                       {'config_path':'/srv/alaz/socket/private.json'}):
            with self.subTest(change=change),self.assertRaises(target.TargetRejected):self.run_prepare(**change)
        self.observe.assert_not_called()

    def test_duplicate_json_keys_rejected_even_with_matching_hash(self):
        raw=b'{"principal_contract":null,"principal_contract":null}'
        self.read.side_effect=None;self.read.return_value=raw
        with self.assertRaises(ValueError):self.run_prepare(config_sha256=hashlib.sha256(raw).hexdigest())
        self.parse.assert_not_called()

    def test_detached_principal_survives_caller_mutation(self):
        def changing(*args):
            self.principal['brokerUid']=2200
            return self.s
        self.observe.side_effect=changing
        self.assertIs(self.run_prepare(),self.cfg)
        self.read.assert_called_once_with('/srv/alaz/private/broker.json',1101,0o600,32768)


class EntryPoint(unittest.TestCase):
    def arguments(self):
        return ['run_principal_broker_target.py','--principal',json.dumps(principal()),
                '--config','/srv/alaz/private/broker.json','--config-sha256','a'*64,
                '--output','/srv/alaz/socket']

    def test_refusal_never_starts_event_loop_or_broker(self):
        stream=io.StringIO()
        with (patch.object(cli.sys,'argv',self.arguments()),redirect_stderr(stream),
              patch.object(cli.target,'prepare',side_effect=RuntimeError('secret-fixture-never-print')),
              patch.object(cli.asyncio,'run') as loop,patch('run_provider_broker.serve') as serve):
            self.assertEqual(cli.main(),2)
        loop.assert_not_called();serve.assert_not_called()
        record=json.loads(stream.getvalue());self.assertIs(record['fallback'],False)
        self.assertEqual(record['phase'],'principal_broker_target')
        self.assertNotIn('secret-fixture-never-print',stream.getvalue())

    def test_only_admitted_configuration_reaches_broker_lifecycle(self):
        cfg=object()
        with (patch.object(cli.sys,'argv',self.arguments()),
              patch.object(cli.target,'prepare',return_value=cfg) as prepare,
              patch('run_provider_broker.serve',new_callable=AsyncMock) as serve):
            self.assertEqual(cli.main(),0)
        prepare.assert_called_once();serve.assert_awaited_once_with(cfg,Path('/srv/alaz/socket'))

    def test_malformed_principal_never_reaches_prepare(self):
        args=self.arguments();args[2]='{\"version\":'
        with (patch.object(cli.sys,'argv',args),redirect_stderr(io.StringIO()),
              patch.object(cli.target,'prepare') as prepare,
              patch.object(cli.asyncio,'run') as loop):
            self.assertEqual(cli.main(),2)
        loop.assert_not_called();prepare.assert_not_called()

if __name__=='__main__':unittest.main()
