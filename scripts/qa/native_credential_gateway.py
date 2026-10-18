"""Complementary credential confinement around real AF21 Gateway acceptance.

Only this test's private broker bootstrap is moved outside Gateway grants.
The original Gateway/broker/ledger/Dream modules are unmodified. Network is
NOT confined by Landlock ABI3; this does not certify the netns branch.
"""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2]
LINUX=Path('/home/ender/alaz-harness-d2b2-gateway-af21')
PREPARED=LINUX/'source-workspace/runtime/gateway-env-af21/env'
PYTHON=PREPARED/'bin/python-local'
NODE=LINUX/'tools/bin/node'
PY_BASE=LINUX/'tools/python/cpython-3.14.3-linux-x86_64-gnu'


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--run-id',required=True)
    parser.add_argument('--scenario', choices=('normal','budget-limit','candidate-disconnect','review-revoked'), default='normal')
    args=parser.parse_args()
    import re
    assert re.fullmatch('[a-z0-9-]{4,40}',args.run_id)
    assert sys.platform=='linux'
    out=LINUX/'source-workspace/runtime'/('credential-6e42-'+args.run_id)
    inner=ROOT/'evidence/d2b2-gateway-af21'/('credential-6e42-'+args.run_id+'.json')
    target=ROOT/'evidence/d3b-credential-6e42'/('gateway-'+args.run_id+'.json')
    assert not out.exists() and not inner.exists() and not target.exists()
    spec=importlib.util.spec_from_file_location('alaz_owned_fs_gateway_qa',ROOT/'scripts/qa/native_d2b2_full_gateway.py')
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    original_popen=subprocess.Popen
    moves=[];private=None;guardfile=out/'credential-guard.json'
    protected_hash=[]
    with tempfile.TemporaryDirectory(prefix='alaz-gw-credential-') as temp:
        controller=Path(temp);controller.chmod(0o700)
        protected=controller/'broker-private.json'
        control_runtime=controller/'xdg'
        control_runtime.mkdir(mode=0o700)
        assert len(str(control_runtime/'hermes-gw-0123456789abcdef/control.sock').encode()) <= 100
        def confined_popen(command,*a,**kw):
            argv=list(command)
            if any(str(x).endswith('/scripts/run_provider_broker.py') for x in argv):
                idx=argv.index('--config')+1;src=Path(argv[idx])
                assert src==out/'broker-private.json' and src.is_file() and not protected.exists()
                src.rename(protected);protected.chmod(0o600)
                protected_hash.append(hashlib.sha256(protected.read_bytes()).hexdigest())
                argv[idx]=str(protected);moves.append('owned_broker_bootstrap_outside_grant')
            elif any(str(x).endswith('/scripts/native_gateway_worker.py') for x in argv):
                assert protected.is_file() and moves==['owned_broker_bootstrap_outside_grant']
                ro=[Path('/usr'),Path('/dev/urandom'),ROOT/'packages',ROOT/'scripts',ROOT/'config',
                    LINUX/'source-workspace/vendor/hermes-agent',PREPARED,PY_BASE]
                for file in ('/etc/ld.so.cache','/etc/hosts','/etc/nsswitch.conf','/etc/resolv.conf',
                             '/etc/passwd','/etc/group','/etc/localtime','/etc/ssl/certs','/etc/mime.types'):
                    if Path(file).exists():ro.append(Path(file).resolve())
                # Remove nested duplicate read roots; grants are explicit and additive.
                roots=sorted(set(str(p.resolve()) for p in ro))
                roots=[p for p in roots if not any(p!=q and Path(p).is_relative_to(q) for q in roots)]
                policy={'version':1,'enabled':True,'readonly':roots,
                        'writable':[str(out),str(control_runtime),'/dev/null'],'protected':[str(protected)],
                        'self_metadata':['status','stat','cmdline']}
                cfg=controller/'guard-policy.json';cfg.write_text(json.dumps(policy));cfg.chmod(0o600)
                argv=[str(PYTHON),'-I','-B',str(ROOT/'scripts/run_credential_guard.py'),
                      '--policy',str(cfg),'--receipt',str(guardfile),'--',*argv]
                kw['env'] = dict(kw.get('env', {}), XDG_RUNTIME_DIR=str(control_runtime))
                moves.append('gateway_wrapped_before_native_imports')
            return original_popen(argv,*a,**kw)
        previous=sys.argv
        sys.argv=[str(ROOT/'scripts/qa/native_d2b2_full_gateway.py'),'--scenario',args.scenario,
            '--source-workspace',str(LINUX/'source-workspace'),'--python',str(PYTHON),
            '--node',str(NODE),'--output',str(out),'--public-receipt',str(inner)]
        try:
            with patch.object(subprocess,'Popen',side_effect=confined_popen):
                result=mod.main()
        finally:sys.argv=previous
        native=json.loads(inner.read_text()) if inner.exists() else {}
        guard=json.loads(guardfile.read_text()) if guardfile.exists() else {}
        if not guard:
            print('GUARD_DIAGNOSTIC', (out/'gateway-stderr.log').read_text()[-1200:])
        protected_same=(len(protected_hash)==1 and protected.is_file() and
            hashlib.sha256(protected.read_bytes()).hexdigest()==protected_hash[0])
        control_sockets_removed=not list(control_runtime.rglob('*.sock'))
        value={'result':'PASS' if result==0 and native.get('result')=='PASS'
            and guard.get('state')=='enforced' and guard.get('protectedReadDenials')==1
            and protected_same and control_sockets_removed else 'FAIL',
            'native':native,'guard':guard,'wrapping':moves,
            'publicInnerReceipt':inner.relative_to(ROOT).as_posix(),
            'sourceSha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in
                [ROOT/'packages/claw-hermes/credential_guard.py',ROOT/'scripts/run_credential_guard.py',Path(__file__)]},
            'protectedBootstrapUnchanged':protected_same,
            'controlSocketsRemoved':control_sockets_removed,
            'nativeLinuxCodeSnapshotRequired':True,
            'networkBoundaryVerified':False,'separateHostUid':False,
            'realModelInferenceVerified':False,'protectedCredentialPrinted':False}
        target.write_text(json.dumps(value,indent=2)+'\n')
        print('CREDENTIAL_GATEWAY',json.dumps({'result':value['result'],'guard':guard,'errors':native.get('errors'),
            'provenance':native.get('provenance')}))
        return 0 if value['result']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
