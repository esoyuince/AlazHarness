"""Opt-in actual pinned Hermes interrupt-module observation, no Gateway or tools.
Run with the existing prepared Hermes Python environment. All task contexts are
new threads in this process, never an existing user task or global service.
"""
from __future__ import annotations
import argparse
import contextvars
import hashlib
import json
import os
from pathlib import Path
import sys
import threading

PINS={
 'tools/__init__.py':'7bca460f476ac9ace706c8cfd07e98f8aae34d839862f0f68abafc3a8397cf35',
 'tools/interrupt.py':'3127f53b4ca1431df828015a3eb06d29ffd43ea9b6a51954d3a45bc69483917b',
 'utils.py':'394b44230f13ba608c6ce9b2d143563b2554a73a219567b03884637776a4859a',
 'hermes_yaml.py':'f97f0f08b6474c52434d0cffaa7ba0ecaa5b9279c4abcbb35c11d15f9c89db76'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-workspace',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();root=args.source_workspace.resolve();source=root/'vendor/hermes-agent';out=args.output.resolve()
    if not out.is_relative_to(root/'runtime') or out.exists():raise ValueError('Fresh runtime output required')
    for name,digest in PINS.items():
        p=source/name
        if p.is_symlink() or hashlib.sha256(p.read_bytes()).hexdigest()!=digest:raise ValueError('Source pin mismatch')
    out.mkdir();os.environ['HERMES_HOME']=str(out/'profile')
    sys.path.insert(0,str(source))
    from tools import interrupt as native
    if Path(native.__file__).resolve()!=source/'tools/interrupt.py':raise ValueError('Wrong module')
    results=[];main_tid=threading.get_ident();threads=[]
    def check(name,value):
        results.append({'case':name,'observed':value,'expected':True,'matched':value is True})
    try:
        check('initial_thread_clear',native.is_interrupted() is False)
        native.set_interrupt(True,main_tid,reason='qa_stop')
        check('own_thread_mark_visible',native.is_interrupted() and native.get_interrupt_reason()=='qa_stop')
        calls=[];allowed=native.run_if_not_interrupted(lambda:calls.append(1))
        check('own_thread_atomic_callback_blocked',allowed is False and calls==[])
        ordinary={}
        t=threading.Thread(target=lambda:ordinary.update(cancelled=native.is_interrupted()))
        threads.append(t);t.start();t.join(3)
        if t.is_alive():raise TimeoutError('Unrelated thread not reaped')
        check('unrelated_thread_not_cancelled',ordinary.get('cancelled') is False)
        actor_token=native.acting_for_tid.set(main_tid);ctx=contextvars.copy_context();native.acting_for_tid.reset(actor_token)
        propagated={}
        def worker():
            propagated['cancelled']=native.is_interrupted();invocations=[]
            propagated['allowed']=native.run_if_not_interrupted(lambda:invocations.append('callback'))
            propagated['calls']=invocations
            try:
                native.set_interrupt(True);own=[]
                propagated['direct_blocked']=native.run_if_not_interrupted(lambda:own.append(1)) is False and not own
            finally:native.set_interrupt(False)
        t=threading.Thread(target=lambda:ctx.run(worker));threads.append(t);t.start();t.join(3)
        if t.is_alive():raise TimeoutError('Acting thread not reaped')
        check('acting_for_interrupt_visible',propagated.get('cancelled') is True)
        # Existing native behavior, not approval of using this as the only veto.
        check('atomic_helper_ignores_acting_for_tid',propagated.get('allowed') is True and propagated.get('calls')==['callback'])
        check('direct_worker_mark_blocks_callback',propagated.get('direct_blocked') is True)
    finally:
        native.set_interrupt(False,main_tid)
        for t in threads:t.join(3)
    check('all_owned_threads_closed_and_main_clear',all(not t.is_alive() for t in threads) and not native.is_interrupted())
    stable=all(hashlib.sha256((source/n).read_bytes()).hexdigest()==h for n,h in PINS.items())
    report={'scope':'actual pinned Hermes tools.interrupt module with real threads/contextvars; not Gateway/Docker integration',
      'source_commit':'eb75627faf532fa6ffbdae59a0d14b0b385fc780','source_files':PINS,
      'observations':results,'matched':sum(x['matched'] for x in results),'count':len(results),'source_unchanged':stable,
      'finding':'is_interrupted_checks_acting_for_tid_but_run_if_not_interrupted_only_current_thread',
      'native_tool_executions':0,'gateway_executions':0,'model_calls':0,'paid_calls':0,
      'result':'OBSERVATIONS_CONFIRMED' if stable and all(x['matched'] for x in results) else 'FAIL'}
    (out/'interrupt-observation.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2));return 0 if report['result']=='OBSERVATIONS_CONFIRMED' else 1

if __name__=='__main__':raise SystemExit(main())
