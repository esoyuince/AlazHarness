"""Verified ext4 code snapshot for private-budget + real Gateway native acceptance.

No source installation, production endpoint, or shared profile changes.
"""
from pathlib import Path
import argparse,datetime,json,os,re,subprocess,sys,tempfile
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(HERE))
from native_credential_ext4 import source_files,copy_verified,LINUX,PYTHON,SCENARIOS,sha

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id',required=True)
    parser.add_argument('--scenario',choices=SCENARIOS,default='normal')
    args=parser.parse_args()
    if sys.platform!='linux' or not re.fullmatch('[a-z0-9-]{4,40}',args.run_id):
        raise ValueError('fresh_linux_run_id_required')
    evidence=ROOT/'evidence/d3b-budget-c84f'
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
        for folder in ('d2b2-gateway-af21','d3b-combined-dc64','d3b-budget-c84f'):
            (snapshot/'evidence'/folder).mkdir(parents=True)
        env={**os.environ,'PATH':str(LINUX/'tools/bin')+':/usr/bin:/bin',
             'PYTHONDONTWRITEBYTECODE':'1','PYTHONIOENCODING':'utf-8'}
        result=subprocess.run([str(PYTHON),'-I','-B',
            str(snapshot/'scripts/qa/native_budget_gateway.py'),
            '--run-id',args.run_id,'--scenario',args.scenario],
            cwd=snapshot,env=env,capture_output=True,timeout=330)
        receipt_path=snapshot/'evidence/d3b-budget-c84f'/('native-'+args.run_id+'.json')
        receipt=json.loads(receipt_path.read_text()) if receipt_path.is_file() else {}
        unchanged=source_files(ROOT)==expected
        copied=source_files(snapshot)==expected
        value={'observedAt':datetime.datetime.now().astimezone().isoformat(),
               'runId':args.run_id,'scenario':args.scenario,
               'result':'PASS' if result.returncode==0 and receipt.get('result')=='PASS'
                        and unchanged and copied else 'FAIL',
               'exitCode':result.returncode,'sourceFiles':len(expected),
               'sourceUnchanged':unchanged,'snapshotBytesMatch':copied,
               'snapshotFilesystem':filesystem,
               'sourceManifestSha256':sha(json.dumps(expected,sort_keys=True).encode()),
               'gatewayPrivateBudgetAcceptance':receipt,
               'stdoutSha256':sha(result.stdout),'stderrSha256':sha(result.stderr),
               'realModelCalls':0,'completeD3B':False,
               'ipcProjectionVerified':False,'separateHostUidVerified':False}
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
                      'missingReceipt':value.get('missingReceipt',False)}),flush=True)
    return 0 if value['result']=='PASS' else 1

if __name__=='__main__':raise SystemExit(main())
