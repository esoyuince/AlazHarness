"""Actual AF21 Gateway with existing netns and Landlock together, not full D3B.

The host-only QA controller joins the child's network for its local API.
The broker and scripted HTTP origin remain in the host network. No paid model.
"""
from pathlib import Path
import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'scripts/qa'),str(ROOT/'packages/claw-hermes')]
import native_d2b2_full_gateway as base
import verify_gateway_network_namespace as controller
from combined_guard import command_digest, validate_contract, digest
from native_credential_gateway import LINUX, PREPARED, PYTHON, NODE, PY_BASE


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id',required=True)
    parser.add_argument('--scenario',choices=base.SCENARIOS,default='normal')
    parser.add_argument('--ipc',action='store_true')
    args=parser.parse_args()
    import re
    assert sys.platform=='linux' and re.fullmatch('[a-z0-9-]{4,40}',args.run_id)
    out=LINUX/'source-workspace/runtime'/(('ipc-a731-' if args.ipc else 'combined-dc64-')+args.run_id)
    inner=ROOT/'evidence/d2b2-gateway-af21'/('combined-'+args.run_id+'.json')
    target=ROOT/('evidence/d3b-ipc-a731' if args.ipc else 'evidence/d3b-combined-dc64')/('inner-'+args.run_id+'.json')
    assert not out.exists() and not inner.exists() and not target.exists()
    original_popen=subprocess.Popen
    controller.GATEWAY_PID=None;controller.SAMPLES.clear()
    moves=[];bound_command=None;contract=None;protected_hash=None;broker_socket=None
    guardfile=out/'combined-guard.json'
    with tempfile.TemporaryDirectory(prefix='alaz-dual-private-') as temporary, tempfile.TemporaryDirectory(prefix='alaz-ipc-root-') as ipc_root:
        private=Path(temporary);private.chmod(0o700)
        protected=private/'broker-private.json'
        sockets=private/'sockets';sockets.mkdir(mode=0o700)
        def launch(command,*a,**kw):
            nonlocal bound_command,contract,protected_hash,broker_socket
            argv=list(command)
            if str(ROOT/'scripts/run_provider_broker.py') in argv:
                index=argv.index('--config')+1;source=Path(argv[index])
                assert source==out/'broker-private.json' and not protected.exists()
                source.rename(protected);protected.chmod(0o600);argv[index]=str(protected)
                protected_hash=hashlib.sha256(protected.read_bytes()).hexdigest()
                broker_socket=str(Path(argv[argv.index('--output')+1])/'egress.sock')
                moves.append('broker_bootstrap_moved_outside_gateway_grants')
            elif str(ROOT/'scripts/native_gateway_worker.py') in argv:
                assert protected.is_file() and len(moves)==1 and controller.GATEWAY_PID is None
                roots=[Path('/usr'),Path('/dev/urandom'),ROOT/'packages',ROOT/'scripts',ROOT/'config',
                    LINUX/'source-workspace/vendor/hermes-agent',PREPARED,PY_BASE]
                for item in ('/etc/ld.so.cache','/etc/hosts','/etc/nsswitch.conf','/etc/resolv.conf',
                             '/etc/passwd','/etc/group','/etc/localtime','/etc/ssl/certs','/etc/mime.types'):
                    if Path(item).exists():roots.append(Path(item).resolve())
                unique=sorted(set(str(p.resolve()) for p in roots))
                unique=[p for p in unique if not any(p!=q and Path(p).is_relative_to(q) for q in unique)]
                bound_command=[str(v) for v in argv]
                policy={'version':1,'enabled':True,'self_process_metadata':True,'readonly':unique,
                        'writable':[str(out),str(sockets),'/dev/null'],'protected':[str(protected)]}
                contract=validate_contract({'version':1,'enabled':True,'launchId':args.run_id,
                    'network':'loopback_only','filesystem':policy,'commandSha256':command_digest(bound_command)})
                if args.ipc:
                    assert broker_socket and Path(broker_socket).is_socket()
                    contract=validate_contract({**contract,'ipc':{'version':1,'mode':'projected_root','root':ipc_root,'brokerSocket':broker_socket}})
                cfg=private/'combined-contract.json';cfg.write_text(json.dumps(contract));cfg.chmod(0o600)
                wrapped=[str(PYTHON),'-I','-B',str(ROOT/'scripts/run_combined_guard.py'),
                         '--contract',str(cfg),'--receipt',str(guardfile),'--',*bound_command]
                kw['env']={**kw['env'],'XDG_RUNTIME_DIR':str(sockets)}
                child=original_popen(wrapped,*a,**kw)
                controller.GATEWAY_PID=child.pid
                moves.append('same_gateway_process_wrapped_with_both_layers')
                return child
            return original_popen(argv,*a,**kw)
        previous=sys.argv
        sys.argv=[str(ROOT/'scripts/qa/native_d2b2_full_gateway.py'),'--scenario',args.scenario,
            '--source-workspace',str(LINUX/'source-workspace'),'--python',str(PYTHON),
            '--node',str(NODE),'--output',str(out),'--public-receipt',str(inner)]
        try:
            with patch.object(subprocess,'Popen',side_effect=launch), \
                 patch.object(subprocess,'run',side_effect=controller.run), \
                 patch.object(base,'http_json',side_effect=controller.http):
                result=base.main()
        finally:
            sys.argv=previous
        native=json.loads(inner.read_text()) if inner.exists() else {}
        combined=json.loads(guardfile.read_text()) if guardfile.exists() else {}
        ready=json.loads((out/'ready.json').read_text()) if (out/'ready.json').exists() else {}
        fs=combined.get('filesystem',{})
        identities=(controller.GATEWAY_PID is not None and
            combined.get('pid')==ready.get('pid')==controller.GATEWAY_PID and
            combined.get('network',{}).get('after',{}).get('pid')==controller.GATEWAY_PID)
        bindings=(contract is not None and combined.get('contractSha256')==digest(contract)
                  and combined.get('commandSha256')==command_digest(bound_command))
        unchanged=(protected.is_file() and hashlib.sha256(protected.read_bytes()).hexdigest()==protected_hash)
        passed=(result==0 and native.get('result')=='PASS' and identities and bindings and unchanged
            and combined.get('state')=='enforced' and fs.get('protectedReadDenials')==1
            and fs.get('state')=='enforced' and bool(controller.SAMPLES))
        projected=combined.get('pathnameIpcView') or {}
        if args.ipc:passed=passed and projected.get('state')=='projected' and projected.get('explicitHostSocketCount')==1 and projected.get('oldRootDetached') is True
        report={'result':'PASS' if passed else 'FAIL','scenario':args.scenario,
            'pathnameSocketProjection':bool(args.ipc and passed),'projectedRoot':projected,
            'native':native,'combined':combined,'sameGatewayPidVerified':identities,
            'launchContractAndCommandBound':bindings,'protectedCredentialUnchanged':unchanged,
            'liveNetworkSamples':list(controller.SAMPLES),'wrapping':moves,
            'bothLayersOnSameGateway':bool(passed),'controllerJoinsForLocalApiOnly':True,
            'brokerAndScriptedOriginHostNetwork':True,'broadFilesystemGrantAdded':False,
            'upstreamGatewayCodeChanged':False,'completeD3B':False,'separateHostUid':False,
            'unixSocketAuthorityIsolated':False,'independentBrokerBudgetAuthority':False,
            'realModelCalls':0,'activeMemoryPromotion':False}
        with target.open('x',encoding='utf-8') as stream:json.dump(report,stream,indent=2);stream.write('\n')
        print(json.dumps({'result':report['result'],'scenario':args.scenario,'sameGatewayPid':identities,
            'contractBound':bindings,'guard':fs,'liveNetworkSampleCount':len(controller.SAMPLES),
            'nativeErrors':native.get('errors'),'provenance':native.get('provenance')}),flush=True)
        return 0 if passed else 1


if __name__=='__main__':raise SystemExit(main())
