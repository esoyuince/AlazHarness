# C131D6 - same-owner canonical API publication without implicit service

## Concrete missing path and selected native change

Prepared APIServerAdapter already borrowed the exact runner/authority/three-store
objects, but the existing native canonical resolver could not find it in the
primary adapter registry. J130 actual API controls established that difference;
this is not a reason to invent another resolver or assign the registry in tests.

The new explicit BorrowedAPIStores.publish_api_adapter() delegates to the EXISTING
GatewayRunner._publish_primary_adapter(..., caller_bundle=bundle). Ordinary
publication keeps its existing behavior. The caller-owned branch validates the
exact native pair and publishes one Platform.API_SERVER key into the original
runner.adapters dictionary. No separate map, scheduler, store owner or lookup path.
It does NOT invoke ordinary API recovery, voice callbacks, a listener or work.

Publication is allowed only while the qualified bundle is PREPARED, idle and
unpublished. Admission remains CLOSED until separate explicit activation. An
already ACTIVE bundle cannot publish late. Native identity-aware idle checks allow
only that exact owned adapter entry, not arbitrary nonempty registries; default
unpublished mode still requires the empty map. This is not a general relaxation
of existing quiescence. Current harness gates/source envelopes remain unchanged,
so their integration is explicitly not yet qualified by this native seam.

The publication pins the original primary and secondary dict objects, exact enum
key and adapter/configuration, primary owner profile and owner event loop. A
replacement dictionary with equal contents or equal string key is not the same
publication. Pure checks run inside the native SQL guard without SQL or recursive
mutex acquisition. Lifecycle loop checks happen before activation/cleanup effects.
Foreign scopes/runner identity/storage generations still use existing native gates.

## Native API acceptance and retained lifetime

Actual admit_api_turn_async now finds the published adapter through the original
_adapter_for_source -> delivery resolver, persists the ordinary API binding and
admits exactly one row under the existing authority/transaction guard. Exact
retries reuse that admission; changed payload or cross-session target conflicts
are refused. These are real programmatic API-function calls, not HTTP ingress,
HTTP authentication, a new listener or completed AIAgent/TurnRunner execution.

Native publication persists while ACTIVE, while draining with queued/unknown work,
and throughout awaited adapter cleanup. It is withdrawn only after successful
current quiescence and SQL checks, by deleting the one identity-matching entry.
Runner then detaches, caller retains stores/profile. Registry/profile/epoch drift
never triggers automatic repair. Trace exceptions after actual insertion/removal
exercise partial effects: UNKNOWN/ADMISSION_UNKNOWN or CLOSE_UNKNOWN retains
caller ownership and refuses blind activation/cleanup replay. Cancellation while
native memory cleanup thread runs similarly keeps the publication and ownership.

A separate case admits through the real API, then directly claims/settles the
leaf using native functions, retires idle API memory and detaches. Persistent
history remains byte-equal across retirement/detach. That leaf's payload was NOT
executed; manual native settlement in a fixture is not an end-to-end model result.
Queued work remains queued and blocks finish; no fake terminalization is product
behavior. Cached routing identities are not erased by withdrawing the map entry;
admission is already sealed, and old references confer no service permission.

## Reproduced native issues and exact corrections

First candidate48 methods:42PASS/6ERROR. Five cleanup errors exposed actual
unowned gateway_state.json publication after native admission; one was a test
expecting later RuntimeStoreError where an earlier valid BorrowedStoreRejected
already refused identity drift. That exception assertion now accepts both refusals,
not success. Actual trace captured tracked native mutation completion invoking
persist_work_count -> _persist_active_agents -> publish_runtime_status three times.

Four stronger tests failed on the original source: unowned status persistence,
changed adapter owner profile, and cross-loop activation/cleanup effects. Same
four test bodies passed the correction. Caller-owned runner mode now skips only
the default status FILE writer in _persist_active_agents and _update_runtime_status;
normal task/mutation ownership still updates. No status writer lifecycle has been
qualified inside the caller-owned profile. Ordinary runner persistence remains and
is separately exercised with an actual ordinary runner and bounded native flush.

The first ordinary positive control omitted its separately owned SessionStore
cache sweep. That fixture leaked one registry reference and caused downstream
teardown failures; raw53-method failure log and missing result artifact are kept.
The native documentation explicitly requires store sweep first, then runner
wrappers. Test cleanup now calls BOTH actual owners, not a registry reset or
ignored error. Product bytes did not change. The failed process ended; its failed
temporary-root cleanup is not labelled successful. Final fresh53/53 run cleans all
53profiles/ownership/registry refs. Earlier48/52/four-failure outcomes stay historical.

## Current qualification and sources

Final native00453/53 PASS=28 unchanged admission lifecycle contracts plus25new
publication/default-compatibility contracts. Actual native classes, stores, tasks,
threads, authority and resolver were not replaced. Explicit trace and memory-close
object faults are fixture inputs. Watched pure transitions have no extra SQLite
connection, raw DB open or row writes; the genuine API call correctly performs
native persistent admission writes outside that observation boundary.

All522 actually imported native files independently match immutable feature
5ff88189832c3ff71bf8fd2f6b2ff05bb8bb4979, which changes6files atop13186a5f. Tenth
patch fresh-applies to exact tested bytes, duplicate application refuses. Native
history is a separate clean feature worktree, installed vendor unchanged. Eight
offline receipt methods bind hashes/outcomes/scope; no extra native executions.
Native SQLite compatibility warning remains in stderr, no dependency upgrade.
Full native upstream pytest and Linux/namespace/seccomp/Landlock tests were NOT run.

Independent reviewer completed/archived without tests/writes. Its source review
recommended the existing registry and no recovery; selected PREPARED publication
uses a narrowly tested own-entry-aware native idle contract rather than its
suggested post-ACTIVE handoff. Existing harness still requires its old empty-registry
contract; this delivery does not pretend that integration has already been changed.
Separate C131P1 QA owns its exact-source negative/awaited-cleanup tests; do not
merge counts as unique cases. Only the eventual immutable union owns a full suite.

## Next boundary and activation limits

Keep current harness manifests and installed native/source locks unchanged. Next
qualify the explicit new source set and publication in the SAME NativeStoreStartup
consumer, including current empty-registry release predicates. Then exercise an
actual accepted API -> finite turn -> real native TurnRunner/physical-worker chain
with bounded dummy computation and owner-controlled cache/session finalization.
A queued-at-seal or unknown head must remain unresolved, not be forced terminal.
Only then rerun exact combined source under Linux isolation and active HTTP.

No provider/model invocation, listener, root/WSL, production/account changes,
remote CI/main merge/push, or prior blocked action retry occurred. C120P9 and the
blocked Q130 QA-copy history sync remain untouched. Installednativeeb75627 and
maincc7ceba stay unchanged. Status/summary/full evidence record exact delivery.
