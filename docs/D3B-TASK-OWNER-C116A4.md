# C116A4 - independent real Task/native adapter acceptance

This branch adds independent tests of the ONE C116A gateway_work_observer,
not another observer, scheduler or storage owner. Original source provenance is
recorded by exact hashes and the original branch/commit when integrated. Existing
B115 policy and W115 committed-row reader remain unchanged.

## What this proves

Actual asyncio.Tasks, the genuine borrowed APIServerAdapter and all three native
SQLite stores are used. OS process-start identity is obtained by the native
platform helper, not a fixture constant. A genuine native executor worker is
started with a bounded local Event wait; after cancelling/awaiting its wrapper
Task the worker is still live. The observer refuses positive ownership evidence
and the fixture releases/joins the worker before teardown. No model is invoked.

Tests also cover cancellation requested before the next loop tick, completed and
failed Tasks left in native registries, Future-vs-Task type, wrong thread, unknown
background/run tasks, replacement Task references, pending ingress, run request
fingerprint/scope/key and response fingerprint mismatches. Database mutations in
these negatives are deliberate owned fault fixtures. Capturing does not repair
them, cancel tasks, consume their exceptions, reopen stores or write rows.

The phase-change case runs the transition from the real registered owner Task;
an unrelated calling Task cannot advance it. The same old native reader supplies
main-qualified committed rows. An actual trace callback alters native metadata
during the read and the final ownership check refuses the sample. Reader mutex
contention and active transactions are unavailable, preserve caller ownership,
and can be re-observed after the fixture explicitly releases them.

## Normal completion is an explicit separate operation

The refined observer retires only its own bookkeeping after a real Task completed
without cancellation/exception, the native producer already removed its Task and
background references, and the exact linked admission/run/response records are
committed and terminal. The test invokes native _retire_live_run rather than
letting the observer remove native map entries. Missing cleanup, a failed Task,
partial response settlement or changed request fingerprint refuses retirement.
An open transaction is not rolled back; an explicit owner rollback allows a new
retirement observation. No result grants store/profile release or new admission.

The original observera2d49ec passed22 independent native cases. Adding explicit
retirement changed source, so those22 results remain historical, not current-code
acceptance. The fresh native003 runs all22 again plus6 retirement cases on80ac827;
only its terminal result establishes current acceptance. Each original outcome
and source is retained. Six receipt tests on the earlier proof are also historical
until updated to the final source and rerun.

## Important unimplemented boundaries

Task publication and immutable request bindings enter through a TRUSTED PRODUCER
SEAM that the QA calls explicitly. Native HTTP/SessionAuthority producer hooks
are NOT instrumented by these tests. The upstream /v1/runs Task can be only an
observer of SessionAuthority/BotChat delivery, not the executor itself; a live
watcher cannot establish remote or thread executor health. The current observer
accordingly grants no serviceReadiness/storageIntegrity/nativeProducerHooks
claim. Unqualified native executor threads and other ingress are rejected.

Real Tasks here are controlled local coroutines, not real model turns. Profile/
mount proof during active work, exact native ingress publication/retirement hooks,
and full-isolation active-work HTTP acceptance remain OPEN. Existing borrowed
connect refusal and quiescent HTTP gates are unchanged. No caller-supplied
storage_verified or healthy flag is accepted as this observer's evidence.

## Reproducibility and environment

The native source is immutable featurecc16c10 in a clean separate worktree. Actual
imports are individually reread from no-replacement Git blobs and SHA256 matched.
Owned temporary homes are used; the first sanitized-process import attempt failed
before tests because it lacked a platform home. The fixture was corrected by
pointing all home/appdata paths at its temporary bootstrap, not the user's home.
That original failure remains FAIL and no product policy was weakened.

One optional urllib3 IPv6 import probe is denied. Windows event-loop wakeup socket
setup is permitted only while unittest constructs its own loop. No test-case
network attempt/provider/model call or native listener is permitted. No WSL/root,
mount, blocked cleanup/refinement retry, source-pin installation, production,
main merge or push is performed. Successful temporary-profile teardown and
native ownership release are part of the actual test result.

## Current terminal native acceptance

Native00328/28PASS,0errors/0failures, exit0 on exact shared observer80ac827. All312 actually imported native modules match immutable Git, including a response-identity module first imported during native retirement. The earlier assumption that the import set was identical to native002 stopped the metadata-finalization command before any new commit; exact current imports were re-read individually, not waived. Current7/7 offline receipt checks pass. Original461 sources remain exact. Complete standard regression and original observer source/focused-test history still require integration. The old22-case run is historical, not additive current coverage.

## Combined terminal standard regression

The original observer/focused-test commit af6cf2f9b8f092d749eb6df4bab6ea4d9616fc4a
was integrated by fast-forward, preserving all16 original evidence Git blobs.
A NEW complete standard Windows run on the union finished3068 total:
3045PASS/23SKIP/0ERROR/0FAIL exit0. All467 source/config/test hashes and both
existing patch hashes stayed unchanged. All461 prior sources are byte-identical.
46 focused methods are34 original unit methods and12 offline receipts inside
that full total, not extra native executions. Original8 native retirement methods
and independent28 native observation methods have overlapping scenarios and are
NOT a single36-case run; the earlier22-case old-source trial remains historical.

The observer original source and independent acceptance now share ONE selected
implementation. Current native source import count is312; every imported module
was matched to immutable featureGit. No native producer hook, profile/mount
verification or active-work HTTP acceptance is inferred. Static-final.txt is a
local static gate, not remote CI or upstream-native full-suite acceptance.

## Canonical delivery

Tested union `578d2edc1aad6fe974d286221f71e84dfa6ed1a1` fast-forwarded from canonical `ec5f1e3ba773550c0c8a1e7fa8381c7b28d4b85a`; original observer source/history and independent acceptance retained. All467 source hashes and2 optional patch hashes match the full run. Final handoff changes documentation/static evidence only; no new native/full execution, source-pin activation, main merge or push. Native producer hooks, active-work profile/mount verification and HTTP acceptance remain OPEN.
