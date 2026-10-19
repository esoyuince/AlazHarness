"""Run the dual-boundary Gateway test from a verified native Linux code copy."""
from pathlib import Path
import argparse,datetime,hashlib,json,os,re,subprocess,sys,tempfile
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(HERE))
from native_credential_ext4 import source_files,copy_verified,LINUX,PYTHON,SCENARIOS,sha


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id',required=True)
    parser.add_argument('--scenario',choices=SCENARIOS,default='normal')
    parser.add_argument('--ipc',action='store_true')
    args=parser.parse_args()
    if sys.platform!='linux' or not re.fullmatch('[a-z0-9-]{4,40}',args.run_id):
        raise ValueError('fresh_linux_run_id_required')
    evidence=ROOT/('evidence/d3b-ipc-a731' if args.ipc else 'evidence/d3b-combined-dc64')
    target=evidence/('gateway-'+args.run_id+'.json')
    manifest=evidence/('source-'+args.run_id+'.json')
    if not evidence.is_dir() or target.exists() or manifest.exists() or not PYTHON.is_file():
        raise ValueError('prepared_environment_and_new_receipts_required')
    expected=source_files(ROOT)
    with tempfile.TemporaryDirectory(prefix='alaz-dual-src-') as temporary:
        snapshot=Path(temporary)/'code';copy_verified(ROOT,snapshot,expected)
        filesystem=subprocess.check_output(['stat','-f','-c','%T',str(snapshot)],text=True).strip()
        if filesystem in ('v9fs','9p','drvfs'):raise ValueError('native_linux_filesystem_required')
        for folder in ('d2b2-gateway-af21','d3b-combined-dc64','d3b-ipc-a731'):
            (snapshot/'evidence'/folder).mkdir(parents=True)
        env={**os.environ,'PATH':str(LINUX/'tools/bin')+':/usr/bin:/bin',
             'PYTHONDONTWRITEBYTECODE':'1','PYTHONIOENCODING':'utf-8'}
        run=subprocess.run([str(PYTHON),'-I','-B',str(snapshot/'scripts/qa/native_combined_gateway.py'),
            '--run-id',args.run_id,'--scenario',args.scenario,*(['--ipc'] if args.ipc else [])],cwd=snapshot,env=env,capture_output=True,timeout=330)
        inner=snapshot/('evidence/d3b-ipc-a731' if args.ipc else 'evidence/d3b-combined-dc64')/('inner-'+args.run_id+'.json')
        receipt=json.loads(inner.read_text()) if inner.exists() else {}
        original_same=source_files(ROOT)==expected
        snapshot_same=source_files(snapshot)==expected
        value={'observedAt':datetime.datetime.now().astimezone().isoformat(),'runId':args.run_id,
            'scenario':args.scenario,'result':'PASS' if run.returncode==0 and receipt.get('result')=='PASS'
            and original_same and snapshot_same else 'FAIL','exitCode':run.returncode,
            'sourceFiles':len(expected),'sourceUnchanged':original_same,'snapshotBytesMatch':snapshot_same,
            'snapshotFilesystem':filesystem,'sourceManifestSha256':sha(json.dumps(expected,sort_keys=True).encode()),
            'ipcProjectionRequested':args.ipc,'gatewayAcceptance':receipt,'stdoutSha256':sha(run.stdout),'stderrSha256':sha(run.stderr),
            'completeD3B':False,'realModelCalls':0,'upstreamRuntimePatched':False,'mainMerged':False}
        if not receipt:
            value['missingReceipt']=True
            value['failureDiagnostic']=run.stderr.decode('utf-8','replace').splitlines()[-1:]
    value['temporaryCodeCopyRemoved']=not snapshot.exists()
    with manifest.open('x',encoding='utf-8') as stream:json.dump({'files':expected},stream,indent=2);stream.write('\n')
    with target.open('x',encoding='utf-8') as stream:json.dump(value,stream,indent=2);stream.write('\n')
    native=receipt.get('native',{})
    print(json.dumps({'result':value['result'],'runId':args.run_id,'scenario':args.scenario,
        'sourceFiles':len(expected),'sameGatewayPid':receipt.get('sameGatewayPidVerified'),
        'liveNetworkSamples':len(receipt.get('liveNetworkSamples',[])),
        'protectedReadDenials':receipt.get('combined',{}).get('filesystem',{}).get('protectedReadDenials'),
        'provenance':native.get('provenance'),'errors':native.get('errors'),
        'failureDiagnostic':value.get('failureDiagnostic')}),flush=True)
    return 0 if value['result']=='PASS' else 1


if __name__=='__main__':raise SystemExit(main())
