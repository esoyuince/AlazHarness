"""Dream D2 review tests on D1 real state owner, synthetic provider."""
from __future__ import annotations
import copy
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import sys
import threading
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'packages/claw-hermes'),str(ROOT/'tests')]
from test_dream import DreamFixture
from dream_review import DreamReviewService, ReviewPolicy, PREFIX
from dream import digest
from execution_budget import ExecutionDenied, seal
from recovery_inspector import _json, _load, RESULT
from concurrent.futures import ThreadPoolExecutor


class ReviewTests(unittest.TestCase):
    def setUp(self):
        self.f=DreamFixture(self)
        self.settings={'enabled':True, 'max_events':8}
        self.s=DreamReviewService(self.settings, self.f.service,
            config_reader=lambda:self.settings)

    def completed(self):
        r=self.f.run()
        self.assertEqual(r['state'],'completed',r)
        self.assertEqual(len(r['candidates']),1)
        return r['batchId'],r['candidates'][0]['candidateId']

    def decide(self,batch,cid,decision='accept_for_testing',
               reason='evidence_sufficient_to_test',revision=None):
        return self.s.decide(batch,cid,decision,reason,
               revision or self.s.inspect(batch)['revision'])

    def test_read_review_does_not_create_row_or_charge(self):
        batch,cid=self.completed()
        budget=self.f.ledger.snapshot()
        r=self.s.inspect(batch)
        self.assertEqual(r['reviewedCount'],0)
        self.assertTrue(r['revision'].startswith('rv_'))
        self.assertEqual(r['acceptedForIndependentEvaluation'],[])
        self.assertEqual(self.f.ledger.snapshot(),budget)
        with closing(sqlite3.connect(self.f.home/'state.db')) as conn:
            self.assertEqual(conn.execute(
                'SELECT count(*) FROM state_meta WHERE key GLOB ?', (PREFIX+'*',)
            ).fetchone()[0],0)

    def test_manual_accept_is_only_for_testing_not_memory(self):
        batch,cid=self.completed()
        before=self.f.ledger.snapshot()
        initial=self.s.inspect(batch)
        new=self.decide(batch,cid)
        self.assertTrue(new['reviewEventWritten'])
        self.assertNotEqual(new['revision'],initial['revision'])
        self.assertEqual(new['acceptedForIndependentEvaluation'],[cid])
        self.assertEqual(new['evaluationStatus'],'not_run')
        self.assertFalse(new['independentOutcomeVerified'])
        self.assertFalse(new['activeMemoryChanged'])
        self.assertFalse(new['grantsExecutionPermission'])
        self.assertFalse(new['skillTransferVerified'])
        self.assertEqual(self.f.ledger.snapshot(),before)
        self.assertEqual(self.f.memory.read_bytes(),b'user pinned memory\n')
        self.assertEqual(self.f.skill.read_bytes(),b'user pinned skill\n')
        self.assertFalse(self.f.service.status(batch)['candidates'][0]['usableAsMemory'])

    def test_reject_and_defer_stay_non_authoritative(self):
        batch,cid=self.completed()
        rejection=self.decide(batch,cid,'reject','conflict')
        self.assertEqual(rejection['acceptedForIndependentEvaluation'],[])
        defer=self.decide(batch,cid,'defer','operator_deferred')
        self.assertEqual(defer['eventCount'],2)
        self.assertEqual(defer['reviewedCount'],1)
        self.assertEqual(defer['acceptedForIndependentEvaluation'],[])
        self.assertFalse(defer['conclusionVerified'])

    def test_new_revision_required(self):
        batch,cid=self.completed()
        seed=self.s.inspect(batch)['revision']
        new=self.decide(batch,cid)
        with self.assertRaisesRegex(ExecutionDenied,'dream_review_revision_conflict'):
            self.decide(batch,cid,revision=seed)
        self.assertEqual(self.s.inspect(batch)['revision'],new['revision'])

    def test_exact_replay_does_not_duplicate_event(self):
        batch,cid=self.completed()
        r=self.decide(batch,cid)
        b=self.decide(batch,cid,revision=r['revision'])
        self.assertTrue(b['replayed'])
        self.assertFalse(b['reviewEventWritten'])
        self.assertEqual(b['eventCount'],1)

    def test_old_payload_not_auto_replayed(self):
        batch,cid=self.completed()
        old=self.s.inspect(batch)['revision']
        self.decide(batch,cid)
        with self.assertRaisesRegex(ExecutionDenied,'revision_conflict'):
            self.decide(batch,cid,revision=old)

    def test_diff_only_changes_since_known_revision(self):
        batch,cid=self.completed()
        seed=self.s.inspect(batch)['revision']
        first=self.decide(batch,cid)
        delta=self.s.diff(batch,seed)
        self.assertTrue(delta['hasChanges'])
        self.assertEqual(delta['addedCandidateDecisions'],[cid])
        self.assertTrue(delta['independentEvaluationRequired'])
        self.assertEqual(delta['newlyAcceptedForIndependentEvaluation'],[cid])
        self.assertFalse(delta['promotableMemoryProposal'])
        self.assertFalse(delta['activeMemoryChanged'])
        self.assertFalse(self.s.diff(batch,first['revision'])['hasChanges'])

    def test_diff_withdraws_without_becoming_memory(self):
        batch,cid=self.completed()
        accept=self.decide(batch,cid)
        defer=self.decide(batch,cid,'defer','operator_deferred')
        delta=self.s.diff(batch,accept['revision'])
        self.assertEqual(delta['changedCandidateDecisions'],[cid])
        self.assertEqual(delta['withdrawnFromTesting'],[cid])
        self.assertFalse(delta['independentEvaluationRequired'])
        self.assertEqual(self.s.inspect(batch)['revision'],defer['revision'])

    def test_diff_reverting_to_old_decision_can_be_empty(self):
        batch,cid=self.completed()
        first=self.decide(batch,cid)
        self.decide(batch,cid,'reject','conflict')
        self.decide(batch,cid)
        d=self.s.diff(batch,first['revision'])
        self.assertFalse(d['hasChanges'])
        self.assertFalse(d['independentEvaluationRequired'])
        self.assertEqual(d['additionalModelCalls'],0)

    def test_unknown_baseline_does_not_create_model_or_row(self):
        batch,cid=self.completed()
        budget=self.f.ledger.snapshot()
        with self.assertRaisesRegex(ExecutionDenied,'dream_review_unknown_baseline'):
            self.s.diff(batch,'rv_'+'f'*64)
        self.assertEqual(self.f.ledger.snapshot(),budget)

    def test_invalid_ids_and_unknown_candidate_are_rejected(self):
        batch,cid=self.completed()
        for bad in ('../../private',0,'f'*64):
            with self.subTest(bad=bad),self.assertRaises(ExecutionDenied):
                self.s.inspect(bad)
        with self.assertRaisesRegex(ExecutionDenied,'dream_review_unknown_candidate'):
            self.decide(batch,'dc_'+'a'*64)

    def test_cannot_use_candidate_to_modify_permissions(self):
        batch,cid=self.completed()
        for decision,reason in [
            ('grant_permission','evidence_sufficient_to_test'),
            ('promote_to_memory','evidence_sufficient_to_test'),
            ('accept_for_testing','operator_deferred'),
            ('accept_for_testing','not_a_reason'),
        ]:
            with self.subTest(decision=decision,reason=reason),self.assertRaises(ExecutionDenied):
                self.decide(batch,cid,decision,reason)
        self.assertEqual(self.s.inspect(batch)['eventCount'],0)

    def test_cannot_review_rejected_d1_batch(self):
        self.f.change=lambda notes,packet:notes['notes'][0]['citations'][0].update(quote='NOT-IN-SOURCE')
        x=self.f.run()
        self.assertEqual(x['state'],'rejected')
        with self.assertRaisesRegex(ExecutionDenied,'dream_review_terminal_required'):
            self.s.inspect(x['batchId'])

    def test_unknown_d1_batch_refused(self):
        self.f.error=ExecutionDenied('broker_transport_outcome_unknown')
        x=self.f.run()
        self.assertEqual(x['state'],'unknown')
        with self.assertRaisesRegex(ExecutionDenied,'dream_review_terminal_required'):
            self.s.inspect(x['batchId'])

    def test_completed_zero_candidates_only_empty_projection(self):
        self.f.change=lambda notes,packet:notes.update(notes=[])
        x=self.f.run()
        self.assertEqual(x['state'],'completed')
        self.assertEqual(self.s.inspect(x['batchId'])['candidateCount'],0)
        with self.assertRaisesRegex(ExecutionDenied,'dream_review_unknown_candidate'):
            self.decide(x['batchId'],'dc_'+'a'*64)

    def test_disabled_configuration_refuses_all_access(self):
        batch,cid=self.completed()
        no=DreamReviewService({},self.f.service)
        with self.assertRaisesRegex(ExecutionDenied,'dream_review_disabled'):
            no.inspect(batch)
        with self.assertRaisesRegex(ExecutionDenied,'dream_review_disabled'):
            no.decide(batch,cid,'reject','conflict','rv_'+'a'*64)

    def test_requires_d1_and_broker(self):
        with self.assertRaisesRegex(ExecutionDenied,'dream_review_dream_required'):
            DreamReviewService({'enabled':True},None)
        with self.assertRaises(ExecutionDenied):
            ReviewPolicy(max_events=0)
        with self.assertRaises(ExecutionDenied):
            ReviewPolicy(enabled=1)
        with self.assertRaisesRegex(ExecutionDenied,'dream_review_invalid_settings'):
            DreamReviewService({'enabled':True,'automaticScheduler':True},self.f.service)

    def test_settings_changed_after_enablement(self):
        batch,cid=self.completed()
        self.settings['enabled']=False
        with self.assertRaisesRegex(ExecutionDenied,'dream_review_settings_changed'):
            self.s.inspect(batch)

    def test_events_bounded(self):
        batch,cid=self.completed()
        self.settings={'enabled':True,'max_events':1}
        self.s=DreamReviewService(self.settings,self.f.service,
                                  config_reader=lambda:self.settings)
        self.decide(batch,cid)
        with self.assertRaisesRegex(ExecutionDenied,'dream_review_event_limit'):
            self.decide(batch,cid,'reject','conflict')
        self.assertEqual(self.s.inspect(batch)['eventCount'],1)

    def test_review_tamper_cannot_assert_active_memory(self):
        batch,cid=self.completed()
        self.decide(batch,cid)
        key=PREFIX+self.f.context.scope+'.'+batch
        with closing(sqlite3.connect(self.f.home/'state.db')) as conn:
            raw=conn.execute('SELECT value FROM state_meta WHERE key=?',(key,)).fetchone()[0]
        row=_load(raw);row['activeMemoryChanged']=True
        self.f.f.sql('UPDATE state_meta SET value=? WHERE key=?',(_json(seal(row)),key))
        with self.assertRaisesRegex(ExecutionDenied,'dream_review_authority_invalid'):
            self.s.inspect(batch)

    def test_review_tamper_resealed_wrong_revision(self):
        batch,cid=self.completed()
        self.decide(batch,cid)
        key=PREFIX+self.f.context.scope+'.'+batch
        with closing(sqlite3.connect(self.f.home/'state.db')) as conn:
            raw=conn.execute('SELECT value FROM state_meta WHERE key=?',(key,)).fetchone()[0]
        row=_load(raw);row['events'][0]['toRevision']='rv_'+'a'*64
        self.f.f.sql('UPDATE state_meta SET value=? WHERE key=?',(_json(seal(row)),key))
        with self.assertRaisesRegex(ExecutionDenied,'dream_review_history_invalid'):
            self.s.inspect(batch)

    def test_d1_candidate_tamper_refused_even_with_review_record(self):
        batch,cid=self.completed()
        self.decide(batch,cid)
        key='alaz.dream.candidates.v1.'+self.f.context.scope+'.'+batch
        with closing(sqlite3.connect(self.f.home/'state.db')) as conn:
            raw=conn.execute('SELECT value FROM state_meta WHERE key=?',(key,)).fetchone()[0]
        row=_load(raw);row['candidates'][0]['usableAsMemory']=True
        self.f.f.sql('UPDATE state_meta SET value=? WHERE key=?',(_json(seal(row)),key))
        with self.assertRaises(ExecutionDenied):
            self.s.inspect(batch)

    def test_snapshot_diff_does_not_change_d1_or_budget(self):
        batch,cid=self.completed()
        before=self.f.ledger.snapshot()
        self.decide(batch,cid)
        snapshot=self.s.inspect(batch)
        self.s.diff(batch,snapshot['revision'])
        self.assertEqual(self.f.ledger.snapshot(),before)
        self.assertFalse(self.f.service.status(batch)['activeMemoryChanged'])

    def test_no_raw_statements_or_secret_in_review_row(self):
        batch,cid=self.completed()
        self.decide(batch,cid)
        with closing(sqlite3.connect(self.f.home/'state.db')) as conn:
            raw=conn.execute('SELECT value FROM state_meta WHERE key GLOB ?', (PREFIX+'*',)).fetchone()[0]
        self.assertNotIn('statement',raw)
        self.assertNotIn(self.f.context.api_token,raw)
        self.assertNotIn('quote',raw)

    def test_concurrent_same_revision_only_one_write(self):
        batch,cid=self.completed()
        revision=self.s.inspect(batch)['revision']
        def f():
            try:return self.s.decide(batch,cid,'accept_for_testing',
                            'evidence_sufficient_to_test',revision)
            except ExecutionDenied as exc:return str(exc)
        with ThreadPoolExecutor(max_workers=2) as ex:
            results=list(ex.map(lambda _:f(),range(2)))
        self.assertEqual(sum(type(x) is dict and x['reviewEventWritten'] for x in results),1)
        self.assertEqual(sum(x=='dream_review_revision_conflict' for x in results),1)
        self.assertEqual(self.s.inspect(batch)['eventCount'],1)


if __name__=='__main__':
    unittest.main(verbosity=2)
