# C120A - canonical claim bound to actual native TurnRunner worker

This is one additive read-only observer on top of NativeCanonicalBinding, not a
second scheduler, executor, task registry or ownership authority. The earlier
C119 claim->request check stays unchanged. Native code at optional feature
943210584828ccfcfd6adc8eb966ecaa8ca18429 is executed unchanged; the installed
vendor, source locks, main and remote refs are not activated or updated.

## Closed evidence gap

Earlier C119 acceptance called native adopt_agent from a compute-boundary double.
This fixture invokes the real native GatewayTurnMixin worker starter, native
context-preserving executor coroutine and actual TurnRunner.run_sync. Its native
callback wiring calls SessionAuthority.adopt_agent directly. A Python profile hook
records the exact native call code/caller and thread identity without replacing
native functions. Real API auth, admission, canonical FIFO/claim/settlement and
native worker_done/physical_workers lifecycle are exercised behind that boundary.

The new gateway_canonical_turn_observation binds a named current canonical claim
to the existing authority worker record, exact native executor coroutine, its
native completion-wrapper closure, the bound actual TurnRunner method, TurnContext,
agent holder, route, session generation and native adopted reference. A live Task
or adopted object alone is not enough. Both the canonical claim and worker binding
are bracketed; wrong generation/registry/coroutine relationships fail closed.

The observation does not create/adopt/stop/remove a task, change native registries,
write a row, reopen a database or release ownership. It exposes no health/admission/
retry/release capability. A worker's pending completion flag is not responsiveness
or proof that all work in the process has been observed. It is a cooperative
in-process snapshot, not an attestation against malicious code in the same process.

## Native task and thread distinction

Cancelling the API watcher does not end its canonical task or native worker. The
named observer still identifies the same pending native worker. Cancelling the
executor coroutine itself also does not stop the already running physical call;
the native worker registry retains it until the wrapper's real finally marks
worker_done. The negative fixture explicitly cancels its own leftover API watcher
and then releases its dummy calculation; it does NOT repair/replay canonical state.

A blocked factory has a real claim and pending worker but no adopted agent yet;
that is unavailable, not an invented ownership claim. Native idempotency accepts
an exact retry without creating another worker. Invalid API auth constructs none.
Computation failure propagates through actual native authority settlement and
worker cleanup. Generic adopted-reference fixtures, wrong generation and unrelated
replacement waiters cannot impersonate the genuine TurnRunner path.

## Normal completion race found during review

After the initial14-method native suite passed, an additional bounded race fixture
allowed the real worker to finish DURING observation of its agent scope. The native
wrapper sets worker_done before clearing that scope. The initial observer could
misclassify the scope clear as permanent ownership loss and latch reconciliation.
The original failing one-case receipt and its driver are retained, not rewritten.

The narrow correction rechecks the actual completion event/waiter state after the
scope read and BEFORE classifying a changed scope as corruption. It yields an
unavailable observation on normal completion, never an affirmative active/healthy
result. Wrong live generation/registry/coroutine mismatches still latch. No native
code, admission rule or cleanup permission is weakened. Candidate fixed-source
acceptance and the final full regression are recorded separately; an earlier full
PASS is historical and cannot substitute for qualification after this change.

## Explicit remaining test seams

The runner's credential/configuration/delivery facade, agent factory and model
calculation are explicit fixtures. TurnContext is test-wired; this is NOT a whole
GatewayRunner bootstrap or a complete real AIAgent/tools/provider execution.
The native worker starter/run_sync/adoption/claim boundaries are not replaced.
No native shared-borrowed bootstrap is exercised and borrowed_runner_conflict is
not relaxed. No actual HTTP listener, active-work health endpoint or Linux namespace
scenario is run. Profile/mount/shared-store validation and complete all-work service
readiness remain unaccepted by this named correlation alone.

Actual imports are independently compared with immutable no-replacement Git blobs.
The optional urllib3 IPv6 capability bind at import is DENIED and retained in logs;
that one attempted probe must not be reported as zero network attempts. Framework
loopback wakeup sockets are marked test setup, not a service listener. Provider/model
calls remain zero. Native DELETE-journal fallback warnings and deliberate compute
failure traces stay in stderr; no interpreter/library upgrade is performed here.

## Test accounting and next integration

The original1-method smoke and8-method path suite are historical stages. The later
native suite includes the additive observer and the completion-race regression;
its final exact count/result and SHA256 set are in the current source acceptance.
Pure snapshot-boundary and offline receipt checks belong to the standard suite,
not additional native worker executions. The full suite is a new exact-source
execution after the final product change, with old results retained separately.
Existing platform/opt-in skips are not claimed as freshly executed tests.

Continue with a single caller-owned canonical runner/adapter bootstrap, preserving
borrowed_runner_conflict until that ownership contract is actually qualified.
Then exercise the same path with profile/mount/three-store constraints and real
active-work observation before HTTP or provider/broker send/accounting activation.
No automatic partial/unknown retry, cross-store atomic recovery or powerloss claim.
Legacy IPCv2 remains closed; full D3B remains open. Prior blocked cleanup/refinement
operations are not reissued via any route. This task performs no WSL/root/mount,
production/account/CIqueue/main/remote-push action.

## Exact remaining shared-bootstrap interface

Pinned native SessionStore.__init__(sessions_dir,config,has_active_processes_fn=None) has no existing-state argument and primes _open_session_db_for_active_scope. BorrowedAPIStores requires a caller-owned non-registry canonical SessionDB and deliberately refuses an attached gateway_runner. Assigning a private _db field AFTER SessionStore construction would not prove zero-extra-open ownership. Next work needs an explicit qualified constructor/bootstrap contract, not deletion of borrowed_runner_conflict. These two native source hashes and limits are recorded in next-shared-bootstrap-boundary.json; no change to that guard or constructor was made here.

## Terminal current-source results

Final corrected-source complete Windows3148=3125PASS/23SKIP/0ERROR/0FAIL, exit0.
All490 source/config/test hashes and four existing patch hashes stayed exact;
all487 baseline source files are unchanged. The final15 native fixture cases
match those product/QA bytes exactly. Five pure snapshot tests and nine offline
proof tests are standard-suite members, not14 further native executions.

The earlier full3147=3124PASS/23SKIP applied to the pre-fix source and is retained
as historical evidence only. The extra actual native completion race failed on
that source even though its then-existing standard suite passed. Current final
native and complete standard tests include the correction; old success was not
used as a substitute. The exact candidate bytes tested in a separate source copy
were applied only after the first full suite had reached a terminal result.

Local static follows in static-final.txt; this is not remote CI or a production
release. Current final imported native hashes541 match immutable feature94321058.
All15 case profiles removed, native ownership/physical-worker registries and
executor waiters cleaned. Scratch source/evidence copies are intentionally kept.

## Latest clean delivery-source qualification

Git's whitespace gate stopped the first commit before effect for four trailing
spaces on one blank QA line. The check was not disabled. The exact earlier QA
bytes and identical AST/location proof are retained. Native004-clean15/15 and a
fresh clean-full3148=3125PASS/23SKIP/0ERROR/0FAIL now qualify the cleaned QA and
receipt-test references. Product code is identical to the accepted completion fix.
All490 current source hashes and4patch hashes match. Use native-004-clean/result.json,
native-clean-source-custody.json and clean-full-windows-result.json as current;
earlier result files are historical and are not additional scenario counts.

## Canonical delivery

Tested commit `1a892b1a2f56c9b710f0be6deb33a91df602a449` fast-forwarded from `80e15b4bb525ce1ab9aa0d997252b82f33335a65` into alaz/d3b-principal-launch-21oct. All490 source hashes and4patch hashes match current complete acceptance. Canonical14 selected checks PASS; root/vendor state and main unchanged. No new native/full replay, installed activation or push.
