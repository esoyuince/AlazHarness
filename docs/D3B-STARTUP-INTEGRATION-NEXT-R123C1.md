# R123C1 - recovered prepared API delivery and next startup boundary

## Verified recovery, not repeated execution

The interrupted native request b123a607-4c31-40f2-9f12-781230000016 was terminal
exit0 with22/22 current native methods. Both original histories and the complete
union were already delivered: native1e97dd61, tested harness merge379977c, canonical
handoff1d6564d. This recovery did NOT repeat native work, the full suite or the merge.
The recorded complete run is3190=3167PASS/23SKIP/0ERROR/0FAIL, and all512 source/
config/test files plus7patches still match its after-manifest exactly.

This recovery re-ran59 selected checks:14 offline original/independent native
receipt methods and45 existing startup lifecycle unit contracts with explicit
dependency doubles. All59 PASS. They are standard-suite subsets, not additional
native or Linux acceptance. The same original23 skipped tests remain unexecuted.
Local static result is stored here separately from test execution.

## Source comparison resolves one ambiguity, not the whole acceptance

Immutable Git comparisons between response featurecc16c10 and prepared feature
1e97dd61 show identical bytes for hermes_state.py, hermes_state_runtime.py,
api_server_run_idempotency.py, api_server_response_store.py and
api_server_response_state.py. Existing storage behavior can therefore be examined
without rewriting those five core implementations. Exact hashes are recorded in
startup-source-boundary.json; no expected value was learned from candidate DBs.

However16 other native Python modules differ, including runner/session/authority,
API and task observation code. The storage gate still declares baseeb75627 and
the response gate declares featurecc16c10. Those declarations must NOT simply be
relabeled or treated as evidence of the complete newer runner import closure.
The five-file equality is not proof of schemas, profile/mount ownership, runtime
isolation, hostile-process protection or the full service's readiness.

## Concrete next implementation contract

Use the existing NativeStoreStartup as the only store lifecycle owner. A prepared
runtime is a CONSUMER of its already verified state/replay/response objects and
accepted epoch, not a second constructor/registry or replacement state owner.
Preparation must validate the current native source closure explicitly, then use
the real prepared runner/API constructors without assigning private handles after
an eager constructor. Do not relax the ordinary listener/admission guards.

Current NativeStoreStartup.close validates its lease/writers/transactions and
closes the owned handles, but it has not been connected to the new prepared API/
runner consumer. Therefore integration must first add a close-order invariant:
API detached -> runner detached -> response/replay/state closed -> caller lease
released. A direct close must refuse while a consumer is attached, constructing
or has an unknown outcome. A convenience wrapper alone is insufficient if it
leaves the original owner close path unaware of its live consumer.

At every transition retain original objects, connection identity and accepted
epoch; do not open a fourth SQLite connection, bump the epoch again, derive
trusted expectations from live candidate files, recover pending jobs, rollback
someone else's transaction or manufacture successful cleanup. Revalidate after
awaited detach steps. Unknown constructor/cleanup outcomes remain non-retryable
and preserve ownership for explicit reconciliation/process termination policy.

Acceptance must distinguish finite unit/mocked lifecycle tests, genuine native
Windows data/object integration, and actual Linux profile/mount/confinement.
A Windows fixture replacing the Linux lease/mount checks cannot close the last
category. Requalify updated-source task observers before any real admission, and
keep active-work HTTP unavailable until the same path passes isolation gates.
This document does NOT claim that integration has been implemented or tested.

## Preserved operational state

Installed native/vendor remains eb75627 and main remains cc7ceba. Native1e97dd61
is STAGED_NOT_INSTALLED. The root's preexisting user changes are left alone.
No production account, root/WSL, provider/model, CIqueue, push or main merge action.
Earlier blocked cleanup/refinement and the C120P9 frame probe stay BLOCKED/HOLD;
none was retried by changing tools or routes. Original failures and accepted
receipts stay immutable. This checkpoint changes documentation/evidence only.

Current status.md plus evidence/d3b-prepared-api-joint-j123c6/resume-r123c1 contain
this recovery's intent, selected result, source boundary, summary and static gate.
