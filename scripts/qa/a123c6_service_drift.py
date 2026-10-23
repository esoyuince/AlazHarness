"""Unchanged before/after service-closed invariants on the prepared native join."""
from pathlib import Path
import asyncio,hashlib,json,sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
import a123c6_native_shared_checks as q
class PreparedServiceChecks(q.NativeThreeJoin):
    def test_prepared_selection_refuses_service_objects_or_running_flag(self):
        self.build()
        for field,value in (('_running',True),('_app',object()),('_site',object()),('_runner',object())):
            old=getattr(self.adapter,field);setattr(self.adapter,field,value)
            try:
                with self.subTest(field=field),self.observed(),self.assertRaises((q.Rejected,q.RunnerRejected)):self.select()
            finally:setattr(self.adapter,field,old)
        self.alive()
    def test_prepared_selection_refuses_pending_or_malformed_work_counters(self):
        self.build()
        for field in ('_pending_agent_requests','_inflight_agent_runs'):
            for value in (1,True,-1):
                old=getattr(self.adapter,field);setattr(self.adapter,field,value)
                try:
                    with self.subTest(field=field,value=value),self.observed(),self.assertRaises((q.Rejected,q.RunnerRejected)):self.select()
                finally:setattr(self.adapter,field,old)
        self.alive()
    def test_prepared_selection_refuses_real_new_task_without_cancelling_it(self):
        self.build()
        async def scenario():
            done=asyncio.Event();task=asyncio.create_task(done.wait());self.tasks.append(task);self.adapter._background_tasks.add(task)
            try:
                with self.observed(),self.assertRaises((q.Rejected,q.RunnerRejected)):self.select()
                self.assertFalse(task.done());self.assertFalse(task.cancelled())
            finally:done.set();await task;self.adapter._background_tasks.remove(task)
        q.LOOP.run_until_complete(scenario());self.alive()
def main():
    q.NativeThreeJoin=PreparedServiceChecks;code=q.main()
    out=Path(sys.argv[sys.argv.index('--output')+1]);r=json.loads((out/'result.json').read_text(encoding='utf-8'))
    r['extendedQaSha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    r['baseQaSha256']=hashlib.sha256(Path(q.__file__).read_bytes()).hexdigest()
    (out/'extended-result.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8')
    return code
if __name__=='__main__':raise SystemExit(main())
