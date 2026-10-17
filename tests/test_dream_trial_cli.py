"""D2B2 operator client, private paired scoring and at-most-once POST."""
import asyncio
import contextlib
import copy
import http.server
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
import dream_trial_once as cli
from test_dream_trial import TrialFixture
from test_dream_eval import KEY
from dream_eval import EvaluationRejected


class ClientTests(unittest.TestCase):
    def setUp(self):
        self.t=TrialFixture(self)
        self.pair=self.t.run()
        self.assertEqual(self.pair["state"],"completed")
        (ROOT/'runtime').mkdir(exist_ok=True)
        self.tmp=tempfile.TemporaryDirectory(dir=ROOT/'runtime')
        self.addCleanup(self.tmp.cleanup)
        self.home=Path(self.tmp.name)
        self.connection={"base_url":"http://127.0.0.1:18001",
                         "token":"synthetic-test-bearer"}
        self.write("plan.json",self.t.plan)
        self.write("connection.json",self.connection)
        self.write("truth.json",self.t.truth)
        self.write("key.json",{"version":1,"oracleKeyHex":KEY})

    def write(self,name,value):
        path=self.home/name
        path.write_text(json.dumps(value,ensure_ascii=False),encoding="utf-8")
        return path

    def mocked_http(self,response,status=200):
        outer=self
        class Conn:
            def __init__(this,*a,**kw):pass
            def request(this,*args,**kwargs):
                outer.calls.append((args,kwargs))
            def getresponse(this):
                class Reply:
                    def read(self,n):return json.dumps(response).encode("utf-8")
                Reply.status=status
                return Reply()
            def close(this):outer.closed+=1
        self.calls=[];self.closed=0
        self.mock=patch.object(cli.http.client,"HTTPConnection",Conn)
        self.mock.start();self.addCleanup(self.mock.stop)

    def test_status_exact_get_only(self):
        self.mocked_http(self.pair)
        result=cli.transfer(self.connection,plan_id=self.t.plan["planId"])
        self.assertEqual(result["state"],"completed")
        self.assertEqual(self.calls[0][0][:2],
                         ("GET","/alaz/host/v1/dream/trial/"+self.t.plan["planId"]))
        self.assertEqual(self.closed,1)

    def test_run_one_post_and_no_oracle_in_payload(self):
        self.mocked_http(self.pair)
        result=cli.transfer(self.connection,plan=self.t.plan)
        self.assertEqual(result["state"],"completed")
        self.assertEqual(len(self.calls),1)
        args,kwargs=self.calls[0]
        self.assertEqual(args[:2],("POST","/alaz/host/v1/dream/trial"))
        self.assertNotIn(KEY,kwargs["body"].decode())
        self.assertNotIn("answer",kwargs["body"].decode())
        self.assertEqual(self.closed,1)

    def test_unknown_partial_is_never_success(self):
        unknown=self.pair|{"state":"unknown","providerResponseValidated":False,
                            "results":self.pair["results"][:1]}
        self.mocked_http(unknown,202)
        result=cli.transfer(self.connection,plan=self.t.plan)
        self.assertEqual(result["state"],"unknown")
        self.assertFalse(result["providerResponseValidated"])

    def test_redirect_refused(self):
        self.mocked_http(self.pair,302)
        with self.assertRaisesRegex(ValueError,"dream_trial_response_unconfirmed"):
            cli.transfer(self.connection,plan_id=self.t.plan["planId"])
        self.assertEqual(len(self.calls),1)

    def test_status_404_not_emptied_or_replayed(self):
        self.mocked_http(self.pair,404)
        with self.assertRaises(ValueError):
            cli.transfer(self.connection,plan_id=self.t.plan["planId"])
        self.assertEqual(len(self.calls),1)

    def test_fake_success_flags_refused(self):
        for flag in ("realModelExecutionVerified","independentOutcomeVerified",
                     "skillTransferVerified","activeMemoryChanged",
                     "grantsExecutionPermission","automaticTrigger",
                     "physicalProviderInferenceVerified"):
            response=copy.deepcopy(self.pair)
            response[flag]=True
            self.mocked_http(response)
            with self.subTest(flag=flag),self.assertRaisesRegex(ValueError,"authority_invalid"):
                cli.transfer(self.connection,plan_id=self.t.plan["planId"])
            self.mock.stop();self.addCleanup(lambda:None)

    def test_missing_second_result_is_not_completed(self):
        bad=self.pair|{"results":self.pair["results"][:1]}
        self.mocked_http(bad)
        with self.assertRaisesRegex(ValueError,"incomplete_pair"):
            cli.transfer(self.connection,plan_id=self.t.plan["planId"])

    def test_invalid_plan_id_refuses_without_network(self):
        self.mocked_http(self.pair)
        with self.assertRaises(ValueError):
            cli.transfer(self.connection,plan_id="../private")
        self.assertEqual(self.calls,[])

    def test_wrong_connection_refused(self):
        self.mocked_http(self.pair)
        with self.assertRaises(ValueError):
            cli.transfer(self.connection|{"base_url":"https://external.example"},
                         plan_id=self.t.plan["planId"])
        self.assertEqual(self.calls,[])

    def test_multiple_operation_arguments_refused(self):
        self.mocked_http(self.pair)
        with self.assertRaisesRegex(ValueError,"one_trial_operation_required"):
            cli.transfer(self.connection,plan_id=self.t.plan["planId"],plan=self.t.plan)

    def test_live_loopback_only_get_for_status_and_score(self):
        outer=self
        calls=[]
        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self,*a):pass
            def do_GET(self):
                calls.append(("GET",self.path))
                if self.path.endswith(outer.t.plan["planId"]):
                    value=outer.pair
                elif self.path.endswith(outer.t.d1["batchId"]):
                    value=outer.t.review.inspect(outer.t.d1["batchId"])
                else:
                    self.send_error(404);return
                raw=json.dumps(value).encode()
                self.send_response(200)
                self.send_header("Content-Type","application/json")
                self.send_header("Content-Length",str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)
            def do_POST(self):
                calls.append(("POST",self.path))
                self.send_error(405)
        server=http.server.ThreadingHTTPServer(("127.0.0.1",0),Handler)
        t=threading.Thread(target=server.serve_forever,daemon=True)
        t.start()
        try:
            self.write("connection.json",
                {"base_url":f"http://127.0.0.1:{server.server_port}",
                 "token":"synthetic-test-bearer"})
            cmd=[sys.executable,"-B",str(ROOT/'scripts/dream_trial_once.py')]
            out=self.home/'score.json'
            run=subprocess.run(cmd+["score","--connection",str(self.home/'connection.json'),
                "--plan",str(self.home/'plan.json'),"--truth",str(self.home/'truth.json'),
                "--key",str(self.home/'key.json'),"--output",str(out)],
                capture_output=True,timeout=15)
            self.assertEqual(run.returncode,0,run.stderr)
            result=json.loads(out.read_text(encoding="utf-8"))
            self.assertTrue(result["brokerReceiptChainReportedByHost"])
            self.assertFalse(result["brokerReceiptIndependentlyVerified"])
            self.assertTrue(result["observedLocalGainAgainstLockedOracle"])
            self.assertFalse(result["realModelExecutionVerified"])
            self.assertFalse(result["independentOutcomeVerified"])
            self.assertFalse(result["skillTransferVerified"])
            self.assertEqual((result["baselineCorrect"],result["candidateCorrect"]),(8,12))
            self.assertEqual(len(result["trialReceiptSummaries"]),2)
            self.assertEqual(len(calls),2)
            self.assertTrue(all(method=="GET" for method,_ in calls))
            self.assertNotIn(KEY.encode(),run.stdout)
            again=subprocess.run(cmd+["score","--connection",str(self.home/'connection.json'),
                "--plan",str(self.home/'plan.json'),"--truth",str(self.home/'truth.json'),
                "--key",str(self.home/'key.json'),"--output",str(out)],
                capture_output=True,timeout=15)
            self.assertEqual(again.returncode,2)
            self.assertEqual(len(calls),2)
        finally:
            server.shutdown();server.server_close();t.join(timeout=3)

    def test_review_stale_after_trial_refuses_score(self):
        self.mocked_http(self.pair)
        with patch.object(cli,'review_get',return_value=self.t.review.inspect(self.t.d1["batchId"])|
              {"revision":"rv_"+"f"*64}):
            with self.assertRaisesRegex(EvaluationRejected,"review_changed_after_plan_sealed"):
                cli.score_existing(connection=self.connection,plan=self.t.plan,
                      truth=self.home/'truth.json',key=self.home/'key.json')

    def test_hidden_oracle_file_never_sent_to_gateway(self):
        self.mocked_http(self.pair)
        with patch.object(cli,'review_get',return_value=self.t.review.inspect(self.t.d1["batchId"])):
            result=cli.score_existing(connection=self.connection,plan=self.t.plan,
                           truth=self.home/'truth.json',key=self.home/'key.json')
            self.assertNotIn(KEY,str(self.calls))
            self.assertFalse(result["promotableMemoryProposal"])

    def test_cannot_write_outside_ignored_runtime(self):
        with self.assertRaises(EvaluationRejected):
            cli.private_path(ROOT/'docs/forbidden-score.json',output=True)


if __name__=="__main__":
    unittest.main(verbosity=2)
