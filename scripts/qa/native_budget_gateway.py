"""Opt-in private-budget check with actual Hermes Gateway, aiohttp broker and dual guard.

Uses only the existing local scripted HTTP origin. Does not contact paid models.
Tests broker-private persisted exposure independently of Gateway-owned SQLite.
IPC visibility and separate Linux identity are NOT certified by this pilot.
"""
import argparse
from dataclasses import asdict
import json
from pathlib import Path
import re
import sys
import tempfile
import uuid
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'scripts/qa'),str(ROOT/'packages/claw-hermes')]
import native_combined_gateway as combined
import native_d2b2_full_gateway as base
from broker_budget import BrokerBudget,initialize
from provider_egress import BrokerConfig

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run-id',required=True)
    p.add_argument('--scenario',choices=base.SCENARIOS,default='normal')
    p.add_argument('--ipc',action='store_true')
    args=p.parse_args()
    assert re.fullmatch(r'[a-z0-9-]{4,40}',args.run_id)
    assert sys.platform=='linux'
    evidence=ROOT/('evidence/d3b-integration-19oct' if args.ipc else 'evidence/d3b-budget-c84f')
    assert evidence.is_dir()
    target=evidence/('native-'+args.run_id+'.json')
    assert not target.exists()
    previous=base.safe_json
    initialized=[];private_config=[];inner_result=None
    with tempfile.TemporaryDirectory(prefix='alaz-budget-host-') as temp:
        private=Path(temp)
        private.chmod(0o700)
        budget_root=private/'broker-budget'
        def trusted_config(path,body):
            if path.name=='broker-private.json':
                assert isinstance(body,dict) and body.get('budget_authority') is None
                assert not initialized
                policy=base.scenario_policy(args.scenario)
                body=dict(body)|{'budget_authority':{
                    'version':1,'enabled':True,
                    'directory':str(budget_root),
                    'budget_id':uuid.uuid4().hex,
                    'policy':asdict(policy)}}
                cfg=BrokerConfig(**body)
                private_config.append(cfg)
                initialized.append(initialize(cfg))
            return previous(path,body)
        argv=sys.argv
        sys.argv=[str(ROOT/'scripts/qa/native_combined_gateway.py'),
                  '--run-id',args.run_id,'--scenario',args.scenario,*(['--ipc'] if args.ipc else [])]
        try:
            with patch.object(base,'safe_json',side_effect=trusted_config):
                inner_result=combined.main()
        finally:
            sys.argv=argv
        combined_dir='d3b-ipc-a731' if args.ipc else 'd3b-combined-dc64'
        inner=evidence.parent/combined_dir/('inner-'+args.run_id+'.json')
        prior=json.loads(inner.read_text(encoding='utf-8')) if inner.exists() else {}
        snapshot=BrokerBudget(private_config[0]).snapshot() if private_config else {}
        expected=base.expected_scenario(args.scenario)
        projected=prior.get('projectedRoot') or {}
        ipc_verified=(args.ipc and prior.get('pathnameSocketProjection') is True
                      and projected.get('state')=='projected'
                      and projected.get('explicitHostSocketCount')==1
                      and projected.get('oldRootDetached') is True)
        pass_result=(inner_result==0 and prior.get('result')=='PASS'
                     and len(initialized)==1
                     and snapshot.get('providerReservations')==expected[1]
                     and snapshot.get('observedHttpResponses')==expected[2]
                     and snapshot.get('gatewayDatabaseIsBudgetAuthority') is False
                     and snapshot.get('measuredInvoiceVerified') is False
                     and (not args.ipc or ipc_verified))
        report={'result':'PASS' if pass_result else 'FAIL',
                'scenario':args.scenario,'localScriptedProviderOnly':True,
                'actualHermesGatewayWithDualGuard':prior.get('bothLayersOnSameGateway',False),
                'nativeCombinedResult':prior.get('result'),
                'actualBrokerPersistentBudget':bool(private_config),
                'privateBudget':snapshot,
                'expectedPhysicalAttempts':expected[1],
                'expectedObservedHttpResponses':expected[2],
                'gatewayDatabaseBudgetAuthority':False,
                'ipcProjectionVerified':bool(ipc_verified),
                'pathnameSocketProjection':prior.get('pathnameSocketProjection') is True,
                'projectedRootProof':{
                    key:projected.get(key) for key in
                    ('state','explicitHostSocketCount','oldRootDetached')},
                'explicitSelectedBrokerSocketOnly':bool(ipc_verified),
                'brokerBudgetIndependentFromGateway':snapshot.get('gatewayDatabaseIsBudgetAuthority') is False,
                'separateHostUidVerified':False,
                'completeD3B':False,'realModelCalls':0}
        with target.open('x',encoding='utf-8') as stream:
            json.dump(report,stream,indent=2)
            stream.write('\n')
        print(json.dumps({'result':report['result'],
                          'scenario':args.scenario,
                          'combined':report['nativeCombinedResult'],
                          'privateReservations':snapshot.get('providerReservations'),
                          'httpObservations':snapshot.get('observedHttpResponses'),
                          'expectedAttempts':expected[1],
                          'ipcProjectionVerified':bool(ipc_verified)}),flush=True)
        return 0 if pass_result else 1

if __name__=='__main__':
    raise SystemExit(main())
