"""Verified ext4 code snapshot for private-budget + real Gateway native acceptance.

No source installation, production endpoint, or shared profile changes.
"""
from pathlib import Path
import argparse,datetime,json,os,re,subprocess,sys,tempfile
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(HERE))
from native_credential_ext4 import source_files,copy_verified,LINUX,PYTHON,SCENARIOS,sha

def accepted_scope(exit_code, receipt, source_ok, copied_ok, ipc):
    if (exit_code != 0 or receipt.get('result') != 'PASS'
            or not source_ok or not copied_ok):
        return False
    if not ipc:
        return True
    projection = receipt.get('projectedRootProof') or {}
    budget = receipt.get('privateBudget') or {}
    return (receipt.get('ipcProjectionVerified') is True
            and receipt.get('pathnameSocketProjection') is True
            and receipt.get('explicitSelectedBrokerSocketOnly') is True
            and receipt.get('brokerBudgetIndependentFromGateway') is True
            and receipt.get('actualBrokerPersistentBudget') is True
            and receipt.get('actualHermesGatewayWithDualGuard') is True
            and receipt.get('nativeCombinedResult') == 'PASS'
            and receipt.get('realModelCalls') == 0
            and receipt.get('completeD3B') is False
            and projection.get('state') == 'projected'
            and projection.get('explicitHostSocketCount') == 1
            and projection.get('oldRootDetached') is True
            and budget.get('gatewayDatabaseIsBudgetAuthority') is False
            and budget.get('noAutomaticRefunds') is True
            and budget.get('measuredInvoiceVerified') is False)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id',required=True)
    parser.add_argument('--scenario',choices=SCENARIOS,default='normal')
    parser.add_argument('--ipc',action='store_true')
    args=parser.parse_args()
    if sys.platform!='linux' or not re.fullmatch('[a-z0-9-]{4,40}',args.run_id):
        raise ValueError('fresh_linux_run_id_required')
    evidence=ROOT/('evidence/d3b-integration-19oct' if args.ipc else 'evidence/d3b-budget-c84f')
    target=evidence/('gateway-'+args.run_id+'.json')
    manifest=evidence/('source-'+args.run_id+'.json')
    if not evidence.is_dir() or target.exists() or manifest.exists() or not PYTHON.is_file():
        raise ValueError('fresh_evidence_and_prepared_python_required')
    expected=source_files(ROOT)
    with tempfile.TemporaryDirectory(prefix='alaz-budget-src-') as temporary:
        snapshot=Path(temporary)/'code'
        copy_verified(ROOT,snapshot,expected)
        filesystem=subprocess.check_output(['stat','-f','-c','%T',str(snapshot)],text=True).strip()
        if filesystem in ('v9fs','9p','drvfs'):
            raise ValueError('native_linux_filesystem_required')
        for folder in ('d2b2-gateway-af21','d3b-combined-dc64','d3b-budget-c84f',
                       'd3b-ipc-a731','d3b-integration-19oct'):
            (snapshot/'evidence'/folder).mkdir(parents=True)
        env={**os.environ,'PATH':str(LINUX/'tools/bin')+':/usr/bin:/bin',
             'PYTHONDONTWRITEBYTECODE':'1','PYTHONIOENCODING':'utf-8'}
        result=subprocess.run([str(PYTHON),'-I','-B',
            str(snapshot/'scripts/qa/native_budget_gateway.py'),
            '--run-id',args.run_id,'--scenario',args.scenario,*(['--ipc'] if args.ipc else [])],
            cwd=snapshot,env=env,capture_output=True,timeout=330)
        receipt_path=snapshot/'evidence'/evidence.name/('native-'+args.run_id+'.json')
        receipt=json.loads(receipt_path.read_text()) if receipt_path.is_file() else {}
        unchanged=source_files(ROOT)==expected
        copied=source_files(snapshot)==expected
        value={'observedAt':datetime.datetime.now().astimezone().isoformat(),
               'runId':args.run_id,'scenario':args.scenario,
               'result':'PASS' if accepted_scope(result.returncode,receipt,unchanged,copied,args.ipc) else 'FAIL',
               'exitCode':result.returncode,'sourceFiles':len(expected),
               'sourceUnchanged':unchanged,'snapshotBytesMatch':copied,
               'snapshotFilesystem':filesystem,
               'sourceManifestSha256':sha(json.dumps(expected,sort_keys=True).encode()),
               'gatewayPrivateBudgetAcceptance':receipt,
               'stdoutSha256':sha(result.stdout),'stderrSha256':sha(result.stderr),
               'realModelCalls':0,'completeD3B':False,
               'ipcProjectionVerified':bool(args.ipc and receipt.get('ipcProjectionVerified') is True),
               'independentBrokerBudgetVerified':receipt.get('brokerBudgetIndependentFromGateway') is True,
               'separateHostUidVerified':False}
        if not receipt:
            value['missingReceipt']=True
    value['temporaryCodeCopyRemoved']=not snapshot.exists()
    with manifest.open('x',encoding='utf-8') as stream:
        json.dump({'files':expected},stream,indent=2);stream.write('\n')
    with target.open('x',encoding='utf-8') as stream:
        json.dump(value,stream,indent=2);stream.write('\n')
    print(json.dumps({'result':value['result'],'scenario':args.scenario,
                      'sourceFiles':len(expected),'filesystem':filesystem,
                      'privateBudget':receipt.get('privateBudget',{}).get('providerReservations'),
                      'httpObservations':receipt.get('privateBudget',{}).get('observedHttpResponses'),
                      'combinedResult':receipt.get('nativeCombinedResult'),
                       'ipcProjectionVerified':value['ipcProjectionVerified'],
                       'independentBrokerBudgetVerified':value['independentBrokerBudgetVerified'],
                      'missingReceipt':value.get('missingReceipt',False)}),flush=True)
    return 0 if value['result']=='PASS' else 1

if __name__=='__main__':raise SystemExit(main())
