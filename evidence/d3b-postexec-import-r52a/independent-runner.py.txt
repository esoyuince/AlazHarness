"""Independent source-pinned post-exec adversarial tests; kernel state MOCKED.

Run explicitly with --source-root pointing at the reviewed post-exec checkout.
No privileged transition, real broker or file modification occurs in that source.
"""
from __future__ import annotations
import argparse
import copy
from contextlib import ExitStack, redirect_stderr
import datetime
import hashlib
import io
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch, Mock, AsyncMock

ROOT=Path(__file__).resolve().parents[2]
PINS=('packages/claw-hermes/principal_target.py','packages/claw-hermes/principal_launch.py',
      'packages/claw-hermes/host_principal.py','packages/claw-hermes/linux_netns.py',
      'packages/claw-hermes/combined_guard.py','packages/claw-hermes/credential_guard.py',
      'packages/claw-hermes/provider_egress.py','scripts/run_principal_broker_target.py',
      'scripts/run_provider_broker.py')


def principal():
    return {'version':1,'enabled':True,'gatewayUid':23001,'brokerUid':23002,
            'socketGroupGid':23003,'hostUserNamespace':'user:[4026531837]'}


def state():
    p=principal()
    return {'pid':910,'uids':(p['brokerUid'],)*4,'gids':(p['socketGroupGid'],)*4,
            'groups':(),'nnp':1,'threads':1,'caps':{k:0 for k in target.launch.CAPS},
            'userns':p['hostUserNamespace'],'uidMap':['0','0','4294967295'],
            'gidMap':['0','0','4294967295']}


def contract():
    v={'version':1,'enabled':True,'role':'broker','principalContract':principal(),
       'python':'/usr/bin/python3.14','config':'/srv/alaz/private/broker.json',
       'configSha256':'a'*64,'output':'/srv/alaz/socket','commandSha256':''}
    v['commandSha256']=target.launch.command_digest(target.launch.command(v))
    return v


class BindingQA(unittest.TestCase):
    def test_fixed_target_and_isolated_interpreter(self):
        argv=target.launch.command(contract())
        self.assertEqual(Path(argv[3]).name,'run_principal_broker_target.py')
        self.assertEqual(argv[1:3],['-I','-B'])
        self.assertEqual(argv[4::2],['--principal','--config','--config-sha256','--output'])

    def test_hash_and_principal_in_exact_bound_argv(self):
        v=contract();argv=target.launch.command(v)
        self.assertEqual(argv[argv.index('--config-sha256')+1],v['configSha256'])
        self.assertEqual(json.loads(argv[argv.index('--principal')+1]),principal())

    def test_changed_config_digest_requires_new_command_binding(self):
        v=contract();v['configSha256']='b'*64
        with self.assertRaises(target.launch.LaunchRejected):target.launch.validate(v)

    def test_changed_broker_identity_requires_new_command_binding(self):
        v=contract();v['principalContract']['brokerUid']=23004
        with self.assertRaises(target.launch.LaunchRejected):target.launch.validate(v)

    def test_no_arbitrary_gateway_or_shell_role(self):
        for role in ('gateway','shell',None,True):
            with self.subTest(role=role),self.assertRaises(target.launch.LaunchRejected):
                target.launch.validate(contract()|{'role':role})

    def test_reordered_policy_keys_not_a_new_command(self):
        a=contract();b=copy.deepcopy(a)
        b['principalContract']=dict(reversed(list(b['principalContract'].items())))
        self.assertEqual(target.launch.command(a),target.launch.command(b))


class KernelQA(unittest.TestCase):
    def observed(self,value,mode=2):
        with (patch.object(target.launch,'observation',return_value=value),
              patch.object(target,'seccomp_mode',return_value=mode)):
            return target.restricted_kernel(principal())

    def test_positive_mock_observation(self):
        self.assertEqual(self.observed(state()),state())

    def test_each_of_eight_identity_slots_rejects_root_wrong_uid_and_bool(self):
        for key in ('uids','gids'):
            for position in range(4):
                for value in (0,1,True,-1):
                    s=state();ids=list(s[key]);ids[position]=value;s[key]=tuple(ids)
                    with self.subTest(key=key,position=position,value=value),self.assertRaises(target.TargetRejected):
                        self.observed(s)

    def test_any_capability_or_incomplete_capability_inventory_refused(self):
        for k in target.launch.CAPS:
            s=state();s['caps'][k]=1
            with self.subTest(cap=k),self.assertRaises(target.TargetRejected):self.observed(s)
        for caps in ({},{'CapEff':0},dict(state()['caps'],CapPrm=False)):
            with self.subTest(caps=caps),self.assertRaises(target.TargetRejected):self.observed(state()|{'caps':caps})

    def test_identity_maps_and_namespace_must_be_host_initial(self):
        for change in ({'userns':'user:[99]'},{'uidMap':['0','23002','1']},
                       {'gidMap':['0','23003','1']},{'uidMap':None}):
            with self.subTest(change=change),self.assertRaises(target.TargetRejected):self.observed(state()|change)

    def test_groups_threads_nnp_and_pid_fail_closed(self):
        for change in ({'groups':(23003,)},{'groups':[]},{'threads':2},{'threads':True},
                       {'nnp':0},{'nnp':True},{'pid':0},{'pid':True}):
            with self.subTest(change=change),self.assertRaises(target.TargetRejected):self.observed(state()|change)

    def test_seccomp_modes_and_missing_mode_not_accepted(self):
        for mode in (0,1,-1,False,'2',None):
            with self.subTest(mode=mode),self.assertRaises(target.TargetRejected):self.observed(state(),mode)


class PreparationQA(unittest.TestCase):
    def setUp(self):
        self.events=[];self.policy=principal();self.raw=json.dumps({'principal_contract':principal()}).encode()
        self.sha=hashlib.sha256(self.raw).hexdigest();self.expected=object()
        self.stack=ExitStack();self.addCleanup(self.stack.close);self.mocks={}
        def call(name,value):
            def work(*args,**kw):self.events.append(name);return copy.deepcopy(value) if name=='kernel' else value
            return work
        for obj,attr,name,value in ((target,'restricted_kernel','kernel',state()),
              (target.net,'_load_seccomp','load',object()),(target.launch,'close_ambient_fds','fds',None),
              (target.net,'_filter','rules',None),(target.launch,'file_bytes','bytes',self.raw),
              (target.launch,'deployment','deployment',{})):
            self.mocks[name]=self.stack.enter_context(patch.object(obj,attr,side_effect=call(name,value)))
        self.constructor=self.stack.enter_context(patch('provider_egress.BrokerConfig',
            side_effect=call('config',self.expected)))

    def run_prepare(self,sha=None):
        return target.prepare(self.policy,'/srv/alaz/private/broker.json',sha or self.sha,'/srv/alaz/socket')

    def test_admitted_sequence_is_exact(self):
        self.assertIs(self.run_prepare(),self.expected)
        self.assertEqual(self.events,['kernel','load','fds','rules','kernel','bytes','config','deployment','kernel'])

    def test_unknown_filter_mode_is_not_enough_known_filter_must_load(self):
        self.mocks['rules'].side_effect=RuntimeError('known_filter_failed')
        with self.assertRaises(RuntimeError):self.run_prepare()
        self.mocks['bytes'].assert_not_called();self.constructor.assert_not_called()

    def test_every_early_failure_prevents_secret_read(self):
        for step in ('kernel','load','fds','rules'):
            saved=self.mocks[step].side_effect
            self.mocks[step].side_effect=RuntimeError(step)
            with self.subTest(step=step),self.assertRaises(RuntimeError):self.run_prepare()
            self.mocks['bytes'].assert_not_called()
            self.mocks[step].side_effect=saved

    def test_mismatched_digest_is_rejected_before_parsing(self):
        with self.assertRaisesRegex(target.TargetRejected,'config_changed'):self.run_prepare('f'*64)
        self.constructor.assert_not_called();self.mocks['deployment'].assert_not_called()

    def test_hash_correct_duplicate_json_keys_still_refused(self):
        raw=b'{"principal_contract":null,"principal_contract":null}'
        self.mocks['bytes'].side_effect=lambda *a:raw
        with self.assertRaises(ValueError):self.run_prepare(hashlib.sha256(raw).hexdigest())
        self.constructor.assert_not_called()

    def test_matching_hash_wrong_principal_is_not_adopted(self):
        bad=principal();bad['brokerUid']=23004
        raw=json.dumps({'principal_contract':bad}).encode();self.mocks['bytes'].side_effect=lambda *a:raw
        with self.assertRaisesRegex(target.TargetRejected,'principal_mismatch'):self.run_prepare(hashlib.sha256(raw).hexdigest())
        self.constructor.assert_not_called()

    def test_reprovisioning_is_not_a_fallback(self):
        self.mocks['deployment'].side_effect=target.launch.LaunchRejected('not_prepared')
        with self.assertRaises(target.launch.LaunchRejected):self.run_prepare()
        self.assertEqual(self.mocks['deployment'].call_count,1)

    def test_changed_final_kernel_state_prevents_admission(self):
        self.mocks['kernel'].side_effect=[state(),state(),state()|{'pid':911}]
        with self.assertRaisesRegex(target.TargetRejected,'kernel_changed'):self.run_prepare()


class CLIQA(unittest.TestCase):
    def args(self):
        return ['target','--principal',json.dumps(principal()),'--config','/srv/private/fixture.json',
                '--config-sha256','a'*64,'--output','/srv/socket']

    def test_error_diagnostic_never_contains_secret_or_calls_broker(self):
        for error in (RuntimeError,PermissionError,ValueError,target.TargetRejected):
            out=io.StringIO()
            with (self.subTest(error=error.__name__),patch.object(cli.sys,'argv',self.args()),
                  redirect_stderr(out),patch.object(cli.target,'prepare',side_effect=error('PRIVATE_DUMMY_78')),
                  patch.object(cli.asyncio,'run') as loop,patch('run_provider_broker.serve') as serve):
                self.assertEqual(cli.main(),2)
            loop.assert_not_called();serve.assert_not_called()
            record=json.loads(out.getvalue());self.assertIs(record['fallback'],False)
            self.assertNotIn('PRIVATE_DUMMY_78',out.getvalue())

    def test_only_returned_configuration_reaches_existing_lifecycle(self):
        cfg=object()
        with (patch.object(cli.sys,'argv',self.args()),patch.object(cli.target,'prepare',return_value=cfg),
              patch('run_provider_broker.serve',new_callable=AsyncMock) as serve):
            self.assertEqual(cli.main(),0)
        serve.assert_awaited_once_with(cfg,Path('/srv/socket'))


def main():
    global target,cli
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    a=parser.parse_args();source=a.source_root.resolve();out=a.output.resolve()
    if out.parent!=(ROOT/'evidence/d3b-launch-qa-b72d').resolve() or out.exists() or a.output.is_symlink():
        raise SystemExit('fresh_own_output_required')
    def hashes():return {p:hashlib.sha256((source/p).read_bytes()).hexdigest() for p in PINS}
    before=hashes()
    sys.path[:0]=[str(source/'packages/claw-hermes'),str(source/'scripts')]
    import principal_target as target
    import run_principal_broker_target as cli
    suite=unittest.TestSuite()
    for cls in (BindingQA,KernelQA,PreparationQA,CLIQA):suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(cls))
    log=out.with_suffix('.txt')
    with log.open('x',encoding='utf-8',newline='\n') as stream:
        result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
    after=hashes()
    report={'result':'PASS_SCOPED_MOCKED_BOUNDARIES' if result.wasSuccessful() and result.testsRun>0 and before==after else 'FAIL',
            'testsRun':result.testsRun,'passed':result.testsRun-len(result.failures)-len(result.errors)-len(result.skipped),
            'failures':len(result.failures),'errors':len(result.errors),'skipped':len(result.skipped),
            'observedAt':datetime.datetime.now().astimezone().isoformat(),'sourceRoot':str(source),
            'sourceSha256':before,'sourceAfterSha256':after,'sourceUnchanged':before==after,
            'runnerSha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'privilegedKernelStateMocked':True,'targetSourceModified':False,'positiveUidTransitionTested':False,
            'fullD3BAccepted':False,'realModelCalls':0}
    with out.open('x',encoding='utf-8') as f:json.dump(report,f,indent=2);f.write('\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('sourceSha256','sourceAfterSha256','sourceRoot')}))
    if report['result']=='FAIL':print(log.read_text(encoding='utf-8')[-10000:])
    return 0 if report['result'].startswith('PASS') else 1


if __name__=='__main__':raise SystemExit(main())
