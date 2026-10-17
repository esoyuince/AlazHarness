"""D2B local operator CLI: synthetic integration, no real model or Gateway."""
import contextlib
import http.server
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'tests')]
import dream_eval_once as cli
from test_dream_eval import fixture
from dream_eval import EvaluationRejected


class OperatorClientTests(unittest.TestCase):
    def setUp(self):
        (ROOT/'runtime').mkdir(exist_ok=True)
        self.tmp=tempfile.TemporaryDirectory(dir=ROOT/'runtime')
        self.addCleanup(self.tmp.cleanup)
        self.home=Path(self.tmp.name)
        self.review,self.train,self.cases,self.truth,self.plan,self.base,self.trial=fixture()
        self.conn=self.write('connection.json',{'base_url':'http://127.0.0.1:19376',
                                                'token':'synthetic-test-bearer'})
        self.training=self.write('train.json',{'version':1,'prompts':self.train})
        self.casefile=self.write('cases.json',{'version':1,'family':'synthetic_triage',
                                               'cases':self.cases})
        self.truthfile=self.write('truth.json',self.truth)
        self.key=self.home/'key.json'
        self.baseline=self.home/'baseline.json'
        self.candidate=self.home/'candidate.json'
        self.client=patch.object(cli,'review_get',return_value=self.review)
        self.mock=self.client.start()
        self.addCleanup(self.client.stop)

    def write(self,name,value):
        path=self.home/name
        path.write_text(json.dumps(value,ensure_ascii=False),encoding='utf-8')
        return path

    def create_plan(self):
        cli.key_create(self.key)
        return cli.seal_once(connection=self.conn,batch_id=self.review['batchId'],
                candidate_id=self.review['decisions'][0]['candidateId'],
                training=self.training,cases=self.casefile,truth=self.truthfile,key=self.key)

    def trial_files(self,plan):
        before=dict(self.base,planId=plan['planId'])
        after=dict(self.trial,planId=plan['planId'])
        self.write('baseline.json',before)
        self.write('candidate.json',after)

    def test_key_created_exclusive_without_stdout_secret(self):
        value=cli.key_create(self.key)
        data=json.loads(self.key.read_text())
        self.assertTrue(value['keyPrinted'] is False)
        self.assertEqual(len(data['oracleKeyHex']),64)
        self.assertNotIn(data['oracleKeyHex'],str(value))
        with self.assertRaises(EvaluationRejected):
            cli.key_create(self.key)

    def test_valid_plan_via_operator_review(self):
        plan=self.create_plan()
        self.assertTrue(plan['planId'].startswith('ev_'))
        self.assertEqual(len(plan['cases']),12)
        self.assertEqual(self.mock.call_count,1)
        self.assertEqual(self.mock.call_args.kwargs['operation'],'inspect')
        self.assertEqual(plan['review']['revision'],self.review['revision'])
        self.assertNotIn('oracleKeyHex',json.dumps(plan))
        self.assertNotIn('RED',json.dumps(plan['truthCommitment']))

    def test_score_uses_fresh_review_not_snapshot(self):
        plan=self.create_plan()
        self.trial_files(plan)
        result=cli.score_once(connection=self.conn,plan=self.write('plan.json',plan),
            truth=self.truthfile,key=self.key,baseline=self.baseline,candidate=self.candidate)
        self.assertEqual(self.mock.call_count,2)
        self.assertEqual(result['netGain'],4)
        self.assertTrue(result['observedLocalGainAgainstLockedOracle'])
        self.assertFalse(result['independentOutcomeVerified'])

    def test_d2a_revocation_refuses_score(self):
        plan=self.create_plan()
        self.trial_files(plan)
        self.mock.return_value=self.review|{'revision':'rv_'+'f'*64}
        with self.assertRaisesRegex(EvaluationRejected,'review_changed_after_plan_sealed'):
            cli.score_once(connection=self.conn,plan=self.write('plan.json',plan),
                truth=self.truthfile,key=self.key,baseline=self.baseline,candidate=self.candidate)

    def test_review_not_accepted_cannot_seal(self):
        self.review['acceptedForIndependentEvaluation']=[]
        self.mock.return_value=self.review
        cli.key_create(self.key)
        with self.assertRaisesRegex(EvaluationRejected,'candidate_not_accepted_for_testing'):
            cli.seal_once(connection=self.conn,batch_id=self.review['batchId'],
                candidate_id=self.review['decisions'][0]['candidateId'],
                training=self.training,cases=self.casefile,truth=self.truthfile,key=self.key)

    def test_training_shape_invalid(self):
        self.training.write_text(json.dumps({'version':1,'prompts':self.train,'untrustedWrite':True}))
        cli.key_create(self.key)
        with self.assertRaisesRegex(EvaluationRejected,'evaluation_invalid_training_file'):
            cli.seal_once(connection=self.conn,batch_id=self.review['batchId'],
                candidate_id=self.review['decisions'][0]['candidateId'],
                training=self.training,cases=self.casefile,truth=self.truthfile,key=self.key)

    def test_cases_shape_invalid(self):
        self.casefile.write_text(json.dumps({'version':True,'family':'synthetic_triage','cases':self.cases}))
        cli.key_create(self.key)
        with self.assertRaisesRegex(EvaluationRejected,'evaluation_invalid_case_file'):
            cli.seal_once(connection=self.conn,batch_id=self.review['batchId'],
                candidate_id=self.review['decisions'][0]['candidateId'],
                training=self.training,cases=self.casefile,truth=self.truthfile,key=self.key)

    def test_changed_truth_after_seal_refused(self):
        plan=self.create_plan()
        self.trial_files(plan)
        altered=self.truth.copy()
        altered['answers']=list(self.truth['answers'])
        altered['answers'][0]={'caseId':'case_00','answer':'AMBER'}
        self.write('wrong_truth.json',altered)
        with self.assertRaisesRegex(EvaluationRejected,'sealed_truth_commitment_mismatch'):
            cli.score_once(connection=self.conn,plan=self.write('plan.json',plan),
                truth=self.home/'wrong_truth.json',key=self.key,
                baseline=self.baseline,candidate=self.candidate)

    def test_changed_key_after_seal_refused(self):
        plan=self.create_plan()
        self.trial_files(plan)
        self.write('wrong_key.json',{'version':1,'oracleKeyHex':'5'*64})
        with self.assertRaisesRegex(EvaluationRejected,'sealed_truth_commitment_mismatch'):
            cli.score_once(connection=self.conn,plan=self.write('plan.json',plan),
                truth=self.truthfile,key=self.home/'wrong_key.json',
                baseline=self.baseline,candidate=self.candidate)

    def test_wrong_arm_refused(self):
        plan=self.create_plan()
        self.trial_files(plan)
        self.candidate.write_text(json.dumps(self.trial|{'planId':plan['planId'],'arm':'baseline'}))
        with self.assertRaisesRegex(EvaluationRejected,'invalid_trial_artifact'):
            cli.score_once(connection=self.conn,plan=self.write('plan.json',plan),
                truth=self.truthfile,key=self.key,
                baseline=self.baseline,candidate=self.candidate)

    def test_no_outside_runtime_output(self):
        with self.assertRaisesRegex(EvaluationRejected,'evaluation_private_runtime_required'):
            cli.private_path(ROOT/'docs/DO-NOT-WRITE.json',output=True)

    def test_no_symlinked_output(self):
        target=self.home/'target.json'
        target.write_text('{}')
        alias=self.home/'link.json'
        try:
            alias.symlink_to(target)
        except (OSError,NotImplementedError):
            # Windows may refuse creating symlinks without developer privileges.
            # Verify the explicit path-refusal branch without claiming an OS link test.
            with patch.object(Path,'is_symlink',return_value=True):
                with self.assertRaises(EvaluationRejected):
                    cli.private_path(alias,output=True)
        else:
            with self.assertRaises(EvaluationRejected):
                cli.private_path(alias,output=True)
        self.assertEqual(target.read_text(),'{}')

    def test_existing_file_not_overwritten(self):
        output=self.write('out.json',{'original':True})
        with self.assertRaisesRegex(EvaluationRejected,'evaluation_output_exists'):
            cli.emit(output,{'new':True})
        self.assertEqual(json.loads(output.read_text()),{'original':True})

    def test_corrupt_key_format_refused(self):
        self.write('key.json',{'version':1,'oracleKeyHex':'x'*64})
        with self.assertRaisesRegex(EvaluationRejected,'invalid_oracle_key_file'):
            cli.key_value(self.key)

    def test_connection_not_read_for_key_command(self):
        output=self.home/'output.json'
        with patch.object(cli,'review_get',side_effect=AssertionError('unexpected network')):
            with contextlib.redirect_stdout(io.StringIO()) as capture:
                code=cli.main(['key','--output',str(output)])
        self.assertEqual(code,0)
        self.assertNotIn(json.loads(output.read_text())['oracleKeyHex'],capture.getvalue())

    def test_main_rejects_bad_output_before_any_network(self):
        output=self.write('output.json',{'private':'data'})
        with patch.object(cli,'review_get',side_effect=AssertionError('unexpected')):
            with contextlib.redirect_stderr(io.StringIO()):
                code=cli.main(['seal','--connection',str(self.conn),
                    '--batch-id',self.review['batchId'],
                    '--candidate-id',self.review['decisions'][0]['candidateId'],
                    '--training',str(self.training),'--cases',str(self.casefile),
                    '--truth',str(self.truthfile),'--key',str(self.key),
                    '--output',str(output)])
        self.assertEqual(code,2)
        self.assertEqual(json.loads(output.read_text()),{'private':'data'})

    def test_key_symlink_parent_escape_refused(self):
        external=Path(tempfile.gettempdir())/'public-outside-runtime-for-test'
        path=external/'key.json'
        if not path.resolve().is_relative_to((ROOT/'runtime').resolve()):
            with self.assertRaisesRegex(EvaluationRejected,'evaluation_private_runtime_required'):
                cli.private_path(path,output=True)

    def test_live_loopback_subprocess_seal_score_no_model(self):
        requests=[]
        outer=self
        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def do_GET(self):
                requests.append(('GET',self.path))
                raw=json.dumps(outer.review).encode()
                self.send_response(200)
                self.send_header('Content-Type','application/json')
                self.send_header('Content-Length',str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)
            def do_POST(self):
                requests.append(('POST',self.path))
                self.send_error(405)
        server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Handler)
        thread=threading.Thread(target=server.serve_forever,daemon=True)
        thread.start()
        try:
            self.conn.write_text(json.dumps({'base_url':f'http://127.0.0.1:{server.server_port}',
                                              'token':'synthetic-test-bearer'}))
            cmd=[sys.executable,'-B',str(ROOT/'scripts/dream_eval_once.py')]
            def run(*args):
                return subprocess.run(cmd+list(args),cwd=ROOT,capture_output=True,timeout=20)
            first=run('key','--output',str(self.key))
            self.assertEqual(first.returncode,0,first.stderr)
            secret=json.loads(self.key.read_text())['oracleKeyHex']
            planfile=self.home/'plan.json'
            second=run('seal','--connection',str(self.conn),'--batch-id',self.review['batchId'],
                '--candidate-id',self.review['decisions'][0]['candidateId'],
                '--training',str(self.training),'--cases',str(self.casefile),
                '--truth',str(self.truthfile),'--key',str(self.key),'--output',str(planfile))
            self.assertEqual(second.returncode,0,second.stderr)
            plan=json.loads(planfile.read_text())
            self.trial_files(plan)
            output=self.home/'score.json'
            third=run('score','--connection',str(self.conn),'--plan',str(planfile),
                '--truth',str(self.truthfile),'--key',str(self.key),
                '--baseline',str(self.baseline),'--candidate',str(self.candidate),
                '--output',str(output))
            self.assertEqual(third.returncode,0,third.stderr)
            report=json.loads(output.read_text())
            self.assertTrue(report['observedLocalGainAgainstLockedOracle'])
            self.assertFalse(report['realModelExecutionVerified'])
            self.assertFalse(report['skillTransferVerified'])
            self.assertFalse(report['activeMemoryChanged'])
            self.assertEqual(len(requests),2)
            self.assertTrue(all(method=='GET' for method,_ in requests))
            for stdout in (first.stdout,second.stdout,third.stdout):
                self.assertNotIn(secret.encode(),stdout)
            fourth=run('score','--connection',str(self.conn),'--plan',str(planfile),
                '--truth',str(self.truthfile),'--key',str(self.key),
                '--baseline',str(self.baseline),'--candidate',str(self.candidate),
                '--output',str(output))
            self.assertEqual(fourth.returncode,2)
            self.assertEqual(len(requests),2)
        finally:
            server.shutdown();server.server_close();thread.join(timeout=3)


if __name__=='__main__':
    unittest.main(verbosity=2)
