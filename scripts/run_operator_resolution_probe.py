"""Native operator closure qualification. Uses fresh Gateway-created stores, never historical ones."""
from __future__ import annotations
import argparse
from contextlib import closing
import hashlib
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import json
from pathlib import Path
import secrets
import sqlite3
import subprocess
import sys
import threading
from urllib.parse import urlparse
from run_native_hermes_probe import isolated_environment,pinned_source
from run_gateway_recovery import run as native_recovery
from gateway_recovery_support import Instance,client,dump,snapshot

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'packages/claw-hermes'))
from recovery_inspector import LocalRecoveryContext,LocalRecoveryInspector


def db_hashes(profile):
    return {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in profile.glob('*.db')}


def audit_rows(profile):
    with closing(sqlite3.connect((profile/'state.db').as_uri()+'?mode=ro',uri=True,timeout=3)) as db:
        db.execute('PRAGMA query_only=ON')
        assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
        return db.execute("SELECT key,value FROM state_meta WHERE key LIKE 'alaz.operator_resolution.%' ORDER BY key").fetchall()


def run(root,python,out,scenario):
    source=pinned_source(ROOT,root)
    paths=['packages/claw-hermes/operator_resolution.py','packages/claw-hermes/resolution_receipts.py',
           'packages/claw-hermes/recovery_inspector.py','scripts/resolve_gateway_reservation.py',
           'scripts/run_operator_resolution_probe.py']
    hashes={s:hashlib.sha256((ROOT/s).read_bytes()).hexdigest() for s in paths}
    report={'scope':'native Gateway crash and explicit operator closure; not reexecution or full M1',
            'scenario':scenario,'errors':[],'model_inference_calls':0,'paid_calls':0,'code_sha256':hashes}
    native=native_recovery(source,python,out,scenario)
    report['native_setup_result']=native['result'];report['native_setup_receipt_sha256']=hashlib.sha256((out/'recovery.json').read_bytes()).hexdigest()
    third=None;server=None;thread=None;requests=[]
    try:
        assert native['result']=='PASS' and not native['errors'],native['errors']
        raw=json.loads((out/'client-000-input.json').read_text(encoding='utf-8'))
        ready=native['second_ready'];profile=out/'profile'
        private=out/'operator-local';private.mkdir()
        context={'profile_home':str(profile),'api_token':raw['token'],'epoch':ready['epoch'],'instance_id':ready['instance_id']}
        query={'body':{'input':raw['input']},'idempotency_key':raw['key'],'observed':native['recovered_status']['value']}
        dump(private/'context.json',context);dump(private/'request.json',query)
        env=isolated_environment(out)
        env.update(HERMES_GATEWAY_LOCK_DIR=str(out/'locks'),OPENAI_API_KEY='alaz-loopback-fixture',
            NO_PROXY='127.0.0.1,localhost',AWS_EC2_METADATA_DISABLED='true',PYTHONUNBUFFERED='1',NO_COLOR='1',TERM='dumb',
            XDG_STATE_HOME=str(out/'xdg-state'),XDG_CONFIG_HOME=str(out/'xdg-config'),XDG_DATA_HOME=str(out/'xdg-data'),XDG_CACHE_HOME=str(out/'xdg-cache'))
        cli_count=0
        def call(*extra):
            nonlocal cli_count
            number=cli_count;cli_count+=1
            argv=[str(python),'-I','-B',str(ROOT/'scripts/resolve_gateway_reservation.py'),'--source-workspace',str(root),
                  '--context',str(private/'context.json'),'--request',str(private/'request.json'),*extra]
            p=subprocess.run(argv,cwd=out,env=env,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=45)
            (private/f'cli-{number:02d}-stderr.txt').write_text(p.stderr,encoding='utf-8')
            (private/f'cli-{number:02d}-stdout.txt').write_text(p.stdout,encoding='utf-8')
            try:value=json.loads(p.stdout)
            except ValueError:raise RuntimeError('Operator CLI did not return bounded JSON; inspect private log') from None
            return {'exit_code':p.returncode,'value':value}
        command=secrets.token_hex(16)
        before=db_hashes(profile)
        prepared=call('--command-id',command);report['preview']=prepared
        assert db_hashes(profile)==before,'Preview wrote native stores'
        if scenario!='after-reserve':
            assert prepared['exit_code']==2 and prepared['value']['status']=='refused'
            assert not audit_rows(profile)
            report['asserted']='canonical_work_refused_no_write'
        else:
            assert prepared['exit_code']==0 and prepared['value']['status']=='preview',prepared
            plan=prepared['value']['plan'];dump(private/'plan.json',plan)
            wrong=call('--apply','--plan',str(private/'plan.json'),'--confirm','0'*64)
            assert wrong['exit_code']==2 and wrong['value']['reason']=='explicit_confirmation_required'
            assert db_hashes(profile)==before and not audit_rows(profile)
            report['wrong_confirmation']=wrong
            applied=call('--apply','--plan',str(private/'plan.json'),'--confirm',plan['confirmationDigest']);report['applied']=applied
            assert applied['exit_code']==0 and applied['value']['status']=='recorded',applied
            assert applied['value']['stateMetaRowsAdded']==2 and applied['value']['taskSucceeded'] is False
            after=db_hashes(profile);assert after['runs_idempotency.db']==before['runs_idempotency.db']
            rows=audit_rows(profile);assert len(rows)==2
            repeated=call('--apply','--plan',str(private/'plan.json'),'--confirm',plan['confirmationDigest']);report['repeated']=repeated
            assert repeated['exit_code']==0 and repeated['value']['status']=='already_recorded'
            assert repeated['value']['receipt']==applied['value']['receipt'] and db_hashes(profile)==after
            inspection=LocalRecoveryInspector(LocalRecoveryContext(**context)).inspect(**query)
            assert inspection['classification']=='reservation_abandoned_verified' and inspection['taskSucceeded'] is False,inspection
            report['inspection']=inspection
            assert snapshot(profile,'unused')['admissions']==[] and snapshot(profile,'unused')['user_count']==0
            # Restart same profile and same provider endpoint. Any new model POST is a failure.
            config=json.loads((profile/'config.yaml').read_text(encoding='utf-8'));endpoint=urlparse(config['model']['base_url'])
            class ForbiddenProvider(BaseHTTPRequestHandler):
                def log_message(self,*args):pass
                def do_GET(self):
                    rawbytes=json.dumps({'object':'list','data':[{'id':'alaz-scripted','context_length':131072}]}).encode()
                    self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(rawbytes)));self.end_headers();self.wfile.write(rawbytes)
                def do_POST(self):
                    requests.append(self.path);self.send_error(503,'No model execution authorized')
            server=ThreadingHTTPServer(('127.0.0.1',endpoint.port),ForbiddenProvider)
            thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
            third=Instance(python,source,out,env,secrets.token_hex(16),'third','none')
            report['third_ready']=third.info['ready']
            assert third.info['ready']['epoch']>ready['epoch']
            denied=call('--apply','--plan',str(private/'plan.json'),'--confirm',plan['confirmationDigest']);report['active_owner_refusal']=denied
            assert denied['exit_code']==2 and denied['value']['reason']=='gateway_or_maintenance_active',denied
            observed=client(out,env,raw['baseUrl'],raw['token'],raw['nonce'],'status',run_id=native['run_id'])
            replay=client(out,env,raw['baseUrl'],raw['token'],raw['nonce'],'start',key=raw['key'],input_text=raw['input'])
            assert observed['ok'] is True and observed['value']['status']=='interrupted'
            assert replay['ok'] is True and replay['value']['run_id']==native['run_id'] and replay['value']['replayed'] is True
            report['native_same_key_replay']={k:replay['value'].get(k) for k in ('run_id','status','replayed')}
            report['third_exit']=third.finish();assert third.info['native_reaped'] and third.info['launcher_reaped']
            context.update(epoch=third.info['ready']['epoch'],instance_id=third.info['ready']['instance_id']);dump(private/'context.json',context)
            query['observed']=observed['value'];dump(private/'request.json',query)
            repeated_new_epoch=call('--apply','--plan',str(private/'plan.json'),'--confirm',plan['confirmationDigest']);report['new_epoch_replay']=repeated_new_epoch
            assert repeated_new_epoch['exit_code']==0 and repeated_new_epoch['value']['status']=='already_recorded'
            assert repeated_new_epoch['value']['receipt']==applied['value']['receipt']
            final=LocalRecoveryInspector(LocalRecoveryContext(**context)).inspect(**query)
            assert final['classification']=='reservation_abandoned_verified' and final['retryAllowed'] is False
            report['final_inspection']=final
            assert audit_rows(profile)==rows and not requests
            report['asserted']='explicit_closure_retained_across_native_restart_without_execution'
        report['final_snapshot']=snapshot(profile,'unused')
        report['cli_calls']=cli_count
        report['original_model_http_calls']=len(native['model_calls'])
        report['new_model_http_calls']=len(requests)
        report['native_first_exit']=native['first_exit'];report['native_second_exit']=native['second_exit']
        assert all(hashlib.sha256((ROOT/s).read_bytes()).hexdigest()==v for s,v in hashes.items()),'Code changed during probe'
        pinned_source(ROOT,root)
    except Exception as exc:report['errors'].append(type(exc).__name__+': '+str(exc))
    finally:
        if third is not None and not third.finished:
            try:third.finish()
            except Exception as exc:report['errors'].append('Cleanup '+type(exc).__name__)
        if server is not None:server.shutdown();server.server_close()
        if thread is not None:thread.join(timeout=5)
    report['result']='PASS' if not report['errors'] else 'FAIL'
    dump(out/'operator-probe.json',report)
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source-workspace',required=True,type=Path);p.add_argument('--python',required=True,type=Path)
    p.add_argument('--output',required=True,type=Path);p.add_argument('--scenario',choices=('after-reserve','completed','before-model'),required=True)
    a=p.parse_args();root=a.source_workspace.resolve();out=a.output.resolve();runtime=root/'runtime'
    if out.exists() or out==runtime or not out.is_relative_to(runtime):raise ValueError('Fresh project runtime output required')
    if not a.python.is_file() or not a.python.resolve().is_relative_to(runtime):raise ValueError('Existing project interpreter required')
    report=run(root,a.python.resolve(),out,a.scenario)
    print(json.dumps({k:report.get(k) for k in ('result','scenario','errors','asserted','cli_calls','original_model_http_calls','new_model_http_calls','inspection','final_inspection')},indent=2))
    return int(bool(report['errors']))

if __name__=='__main__':raise SystemExit(main())
