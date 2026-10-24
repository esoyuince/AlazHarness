"""Joint observer/guard actual-native Windows compatibility, no active service."""
import asyncio,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/qa'))
import o127b6_native_prepared_observer as original

class JointPreparedObserverCases(original.PreparedObserverCases):
    def work_guard(self,target,field):
        observer=self.attach();event=asyncio.Event()
        async def create():return asyncio.create_task(event.wait())
        task=original.LOOP.run_until_complete(create())
        existed=hasattr(target,field);old=getattr(target,field,None);setattr(target,field,{task})
        try:
            with self.observed(),self.assertRaises(original.b.CanonicalBindingRejected):self.run_async(observer.attachment_status)
            self.assertFalse(task.done());self.assertFalse(task.cancelled())
            self.assertEqual((self.consumer._stage,self.consumer._bundle._stage,self.consumer._binding._stage),('ATTACHED','ATTACHED','PREPARED'))
        finally:
            event.set();original.LOOP.run_until_complete(task)
            if existed:setattr(target,field,old)
            else:delattr(target,field)
        self.run_async(observer.attachment_status)
    def test_joint_real_authority_task_is_seen_by_attached_observer(self):
        self.work_guard(self.authority,'_mutation_tasks')
    def test_joint_real_runner_task_is_seen_by_attached_observer(self):
        self.work_guard(self.consumer._runner,'_background_tasks')

def main():
    original.PreparedObserverCases=JointPreparedObserverCases  # QA class extension only
    code=original.main()
    out=Path(sys.argv[sys.argv.index('--output')+1]);p=out/'result.json';r=json.loads(p.read_text(encoding='utf-8'))
    r['sourceHashes']['scripts/qa/j127b6_native_joint_observer.py']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    r.update(originalPreparedMethods=14,jointCompositionMethods=2,testClassExtendedOnly=True,realTasksAreExplicitFaultFixtures=True)
    p.write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8')
    print('JOINT_RESULT',r['total'],r['passed'],r['errors'],r['failures'],flush=True)
    return code
if __name__=='__main__':raise SystemExit(main())
