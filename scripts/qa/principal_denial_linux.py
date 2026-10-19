"""Negative-only Linux principal admission test, unprivileged and offline.

Never acquires another UID or claims positive cross-host-UID acceptance.
Uses only self-owned TemporaryDirectory, Unix socketpair and dummy config.
"""
import argparse
import asyncio
import json
import hashlib
import os
from pathlib import Path
import socket
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'packages/claw-hermes'))
import host_principal as hp
from provider_egress import BrokerConfig
from provider_broker import ProviderBrokerServer

def expected_refusal(action):
    try:action()
    except hp.PrincipalRejected:return True
    return False

def main():
    cli=argparse.ArgumentParser()
    cli.add_argument('--output',type=Path,required=True)
    a=cli.parse_args()
    evidence=ROOT/'evidence/d3b-host-principal-7a19'
    dest=a.output.resolve()
    if (sys.platform!='linux' or os.getuid()==0
            or not evidence.is_dir() or dest.parent!=evidence.resolve()
            or dest.exists() or dest.is_symlink()):
        raise ValueError('unprivileged_owned_evidence_required')
    ns=os.readlink('/proc/self/ns/user')
    spec={'version':1,'enabled':True,'gatewayUid':os.getuid(),
          'brokerUid':65534,'socketGroupGid':os.getgid(),
          'hostUserNamespace':ns}
    hp.policy(spec)
    tests={}
    with tempfile.TemporaryDirectory(prefix='alaz-principal-denial-') as temp:
        owned=Path(temp)
        budget=owned/'budget';budget.mkdir(mode=0o700)
        db=budget/'budget.sqlite3'
        db.write_bytes(b'owned-non-sqlite-test')
        db.chmod(0o600)
        tests['same_uid_budget_file_rejected']=expected_refusal(
            lambda:hp.budget_identity(spec,str(budget)))
        directory=owned/'socket';directory.mkdir(mode=0o700)
        path=directory/'egress.sock'
        with socket.socket(socket.AF_UNIX) as listener:
            listener.bind(str(path));path.chmod(0o660)
            tests['same_uid_socket_owner_rejected']=expected_refusal(
                lambda:hp.socket_identity(spec,str(path)))
            a1,a2=socket.socketpair()
            with a1,a2:
                tests['same_uid_peer_rejected']=expected_refusal(
                    lambda:hp.socket_peer(a1,spec,role='gateway'))
            db_alias=owned/'budget-alias'
            db_alias.symlink_to(db)
            tests['symlink_budget_refused']=expected_refusal(
                lambda:hp.regular(str(db_alias),'file',
                                  spec['brokerUid'],spec['socketGroupGid'],0o600))
        cfg=BrokerConfig('http://127.0.0.1:19440/v1','test',
              'p'*48,'b'*64,str(owned/'gateway/state.db'),
              'c'*64,'d'*64,'e'*64,None,spec)
        server=ProviderBrokerServer(cfg,owned/'new-broker')
        async def invoke():
            try:await server.start()
            except hp.PrincipalRejected:return 'principal_refused'
            except Exception:return 'other_exception'
            return 'unexpected_success'
        actual=asyncio.run(invoke())
        tests['broker_start_fails_closed_same_uid']=actual=='principal_refused'
        tests['no_broker_socket_created']=not server.path.exists() and not server.directory.exists()
        tests['no_physical_provider_attempt']=server.counts['physicalAttempts']==0
    tests['owned_temp_removed']=not owned.exists()
    sources=('packages/claw-hermes/host_principal.py',
             'packages/claw-hermes/provider_broker.py',
             'packages/claw-hermes/provider_egress.py',
             'scripts/qa/principal_denial_linux.py')
    source_hashes={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest()
                   for name in sources}
    value={'result':'PASS_DENIAL_ONLY' if all(tests.values()) else 'FAIL',
           'sourceSha256':source_hashes,
           'scope':'rootless_same_host_uid_negative_only_not_2_uid_native',
           'checks':tests,'checkCount':len(tests),
           'observedUid':os.getuid(),'observedGid':os.getgid(),
           'brokerUidDemanded':spec['brokerUid'],
           'separateHostUidVerified':False,'nativeTwoUidGatewayBrokerTested':False,
           'realModelCalls':0,'fullD3BAccepted':False,'mainMerged':False}
    with dest.open('x',encoding='utf-8') as f:
        json.dump(value,f,indent=2);f.write('\n')
    print(json.dumps({'result':value['result'],
                      'checks':value['checkCount'],
                      'separateHostUidVerified':False,
                      'providerCalls':0}),flush=True)
    return 0 if value['result']=='PASS_DENIAL_ONLY' else 1

if __name__=='__main__':raise SystemExit(main())
