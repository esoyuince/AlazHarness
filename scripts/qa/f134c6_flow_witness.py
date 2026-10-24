"""Observe an explicitly selected, hash-pinned offline probe without replacing native functions.
This is execution evidence, not authorization, scheduling, source trust or isolation.
Coroutine call events may include resumptions; counts are NOT counts of jobs.
"""
from __future__ import annotations
import argparse,hashlib,json,os,runpy,sys,threading,time,traceback
from pathlib import Path

WATCHED={
 'gateway/session_api_turn.py':{'run_api_turn','observe_api_turn','_settled_api_result'},
 'gateway/session_authority.py':{'_schedule','_execute_claimed','_drain'},
 'gateway/session_finite.py':{'execute_finite_admission'},
 'gateway/session_ingress.py':{'execute_admission'},
 'gateway/run_turn_runner.py':{'run_sync','_run_sync_scoped','_run_conversation_with_approval'},
 'gateway/session_runtime_workers.py':{'start_turn_worker','track_turn_worker','physical_workers'},
 'gateway/turn_executor.py':{'submit','_run'},
 'gateway/session_settlement_recovery.py':{'settle_with_retry','commit_and_publish'},
 'hermes_state_runtime.py':{'settle_session_input'},
 'hermes_state_registry.py':{'_open_session_db','acquire'},
}

def verdict(events:list[dict],main_thread:int)->dict:
    native={(r['path'],r['function']) for r in events if r['kind']=='native'}
    required=[('gateway/session_api_turn.py','run_api_turn'),
              ('gateway/session_api_turn.py','observe_api_turn'),
              ('gateway/session_authority.py','_execute_claimed'),
              ('gateway/session_finite.py','execute_finite_admission'),
              ('gateway/session_ingress.py','execute_admission'),
              ('gateway/run_turn_runner.py','run_sync'),
              ('gateway/session_runtime_workers.py','track_turn_worker'),
              ('gateway/session_settlement_recovery.py','commit_and_publish')]
    missing=[list(v) for v in required if v not in native]
    model=[e for e in events if e['kind']=='fixture_computation' and e['function']=='run_conversation']
    real_thread=bool(model) and all(e['thread']!=main_thread for e in model)
    settles=[e for e in events if e['path']=='hermes_state_runtime.py' and e['function']=='settle_session_input']
    manually_settled=any(not any(s['path']=='gateway/session_settlement_recovery.py' and s['function']=='commit_and_publish' for s in e['stack']) for e in settles)
    return {'requiredNativeCallsObserved':not missing,'missing':missing,
            'fixtureComputationCalled':bool(model),'computationOffMainThread':real_thread,
            'nativeSettlementObserved':bool(settles),'manualSettlementStackObserved':manually_settled,
            'flowObserved':not missing and real_thread and bool(settles) and not manually_settled,
            'nativeCallCountsNotTaskCounts':True,'payloadCorrectnessNeedsDriverAssertions':True}

class Witness:
    def __init__(self,native:Path,driver:Path):
        self.native=native.resolve();self.driver=driver.resolve();self.native_prefix=os.path.normcase(str(self.native))+os.sep
        self.driver_path=os.path.normcase(str(self.driver));self.start=time.monotonic();self.main=threading.get_ident()
        self.events=[];self.lock=threading.Lock();self.error=None;self.truncated=False;self.lookups={}
    def path(self,filename):
        cached=self.lookups.get(filename)
        if cached is not None:return cached
        raw=os.path.normcase(os.path.abspath(filename))
        if raw.startswith(self.native_prefix):result=('native',raw[len(self.native_prefix):].replace(os.sep,'/'))
        elif raw==self.driver_path:result=('fixture_computation',self.driver.name)
        else:result=('other','')
        self.lookups[filename]=result;return result
    def observe(self,frame,event,arg):
        if event!='call':return
        try:
            kind,path=self.path(frame.f_code.co_filename);fn=frame.f_code.co_name
            if kind=='native':
                if fn not in WATCHED.get(path,set()):return
            elif kind!='fixture_computation' or fn!='run_conversation':return
            stack=[];current=frame.f_back
            for _ in range(18):
                if current is None:break
                k,p=self.path(current.f_code.co_filename)
                if k in ('native','fixture_computation'):stack.append({'kind':k,'path':p,'function':current.f_code.co_name})
                current=current.f_back
            record={'kind':kind,'path':path,'function':fn,'thread':threading.get_ident(),
                    'elapsed':round(time.monotonic()-self.start,6),'stack':stack}
            with self.lock:
                if len(self.events)<10000:self.events.append(record)
                else:self.truncated=True
        except BaseException as exc:self.error=type(exc).__name__

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--native',type=Path,required=True)
    parser.add_argument('--driver',type=Path,required=True);parser.add_argument('--driver-sha256',required=True)
    parser.add_argument('--witness-output',type=Path,required=True);parser.add_argument('driver_args',nargs=argparse.REMAINDER);a=parser.parse_args()
    driver=a.driver.resolve(strict=True);assert hashlib.sha256(driver.read_bytes()).hexdigest()==a.driver_sha256
    assert not a.witness_output.exists() and sys.getprofile() is None and threading.getprofile() is None
    args=a.driver_args[1:] if a.driver_args[:1]==['--'] else a.driver_args
    assert '--native' in args and Path(args[args.index('--native')+1]).resolve()==a.native.resolve()
    witness=Witness(a.native,driver);code=0;err=None;old_args=sys.argv
    sys.argv=[str(driver),*args];sys.setprofile(witness.observe);threading.setprofile(witness.observe)
    try:runpy.run_path(str(driver),run_name='__main__')
    except SystemExit as exc:code=exc.code if isinstance(exc.code,int) else (0 if exc.code is None else 1)
    except BaseException as exc:code=1;err=type(exc).__name__;traceback.print_exc()
    finally:
        sys.setprofile(None);threading.setprofile(None);sys.argv=old_args
    unchanged=hashlib.sha256(driver.read_bytes()).hexdigest()==a.driver_sha256
    result=verdict(witness.events,witness.main)
    report={'result':'PASS_OBSERVED_NATIVE_FINITE_FLOW' if code==0 and result['flowObserved'] and unchanged and not witness.error and not witness.truncated else 'NOT_ACCEPTED',
            'driverExitCode':code,'driverError':err,'driverSha256':a.driver_sha256,'driverBytesUnchanged':unchanged,
            'mainThread':witness.main,'events':witness.events,'checks':result,'observationError':witness.error,
            'truncated':witness.truncated,'nativeMethodsReplacedByWitness':False,'threadProfileInstalledBeforeDriver':True,
            'fullAgentOrProviderAcceptance':False,'qaSha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    with a.witness_output.open('x',encoding='utf-8',newline='\n') as out:json.dump(report,out,indent=2);out.write('\n')
    print('INDEPENDENT_FLOW_WITNESS '+json.dumps({k:v for k,v in report.items() if k!='events'}),flush=True)
    return 0 if report['result'].startswith('PASS_') else 1
if __name__=='__main__':raise SystemExit(main())
