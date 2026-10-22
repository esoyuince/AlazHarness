# A112X7D - borrowed canonical state for native ResponseStore

Opt-in native fork patch on eb75627faf532fa6ffbdae59a0d14b0b385fc780.
The installed vendor main, submodule pin and sources.lock are NOT updated.
Native fork commit is recorded in evidence/d3b-api-storage-a112x7d/native-fork-commit.json.
Only api_server_response_store.py and the new api_server_response_state.py change.
The complementary B112X9 patch owns API adapter constructor/selection/shutdown;
this patch deliberately does not create another adapter or listener.

## Ownership behavior

ResponseStore(..., db_path=explicit_same_home_path, canonical_state=live_state)
checks the native SessionDB, exact home and connection before opening its own
response database. Unlike the default mode, failed response disk open cannot
fall back to memory. The caller remains responsible for preflight, profile lease,
full response-schema qualification and eventual store closure.

Canonical terminal/tombstone settlement uses the already-open SessionDB writer
connection under its existing native mutex. It does NOT call _read_ctx because
that upstream helper may create pooled read connections or reopen a closed
writer. It never opens or closes another canonical connection, changes the
caller's transaction, advances epoch or synthesizes a terminal result.

The binding retains process/thread, handle, mutex, file identity and application
generation. Busy lock, active transaction, foreign path, replacement or closed
connection fail with bounded errors; no adoption, retry or fallback. SQL targets
main.session_admissions/main.state_meta explicitly, so TEMP tables cannot pretend
pending work is complete. Queued, started and unknown admissions remain unsettled;
terminal rows and native terminal tombstones retain their existing semantics.
Before/after total_changes/data_version checks catch observed concurrent drift.
These are cooperative snapshots, not proof against malicious same-process code.

ResponseStore closes only its own response connection. It never closes the caller
SessionDB or releases the profile. The original default still opens its separate
read-only canonical connection; default body/cache/conversation behavior remains.
This change is an explicit ownership extension, not a claim that the default
SQLite path was corrupting locks. The separate comparison observes no lock
corruption and identifies the unwanted extra connection, which this path removes.

## Actual tests and patch application

24 real-native behavioral methods pass Windows and ordinary P71C Linux. They
use the native SessionDB, ResponseStore, runtime transactions and ProfileOwnership,
not replacements for those classes/functions. SQLite audit proves one response
open during borrowed construction and zero new canonical connections during
settlement; the unchanged default is the positive extra-reader control.

Cases cover terminal/tombstone settlement, queued/started/unknown preservation,
active transactions, native mutex contention, wrong thread/home, closed/swapped
handles, generation mismatch, TEMP shadowing, memory/disk-failure refusal,
response body/conversation behavior, same-key conflict and reopen/close ownership.
The same24 methods repeated on two platforms are not48 distinct scenarios.
No full native pytest suite, agent HTTP listener, network request, model/provider,
full confinement or healthy/busy HTTP policy is claimed by this acceptance.

The patch applies to a fresh immutable source export and reproduces exact tested
hashes. A second application is rejected. Windows autocrlf initially changed
line endings in the temporary apply fixture; this stopped before native commit.
With autocrlf disabled ONLY in that temporary repository the raw bytes match.
The original mismatch remains recorded. Global/user/native configuration was
not changed. Missing native Git author configuration also stopped before commit;
the existing harness identity was supplied only to the subsequent local commit.

Seven offline receipt/source checks validate the artifact and original results.
They are not additional native tests. Full harness regression is deferred to the
one combined branch once complementary adapter work is terminal; focused/static
success is not substituted for that full run. The native dependency installation
was reused without downloads or updates. Linux temp code/profiles were removed.
All427 existing harness source files remain unchanged.

## What remains before activation

The current strict profile/startup covers two stores, not response_store.db.
Prepare that third schema, identity and cold preflight under the same ownership
contract before altering A109 or the projection list. ResponseStore constructors
still perform native schema/settlement/eviction work on their OWN file; this
patch does not make an unidentified response database safe to open. Expected
input must come from trusted preparation, not be learned from suspect state.

Borrowed adapter selection and drain must be tested with this exact binding.
Listener/work routes stay disabled until a separately reviewed healthy/busy
policy and same-path three-store start/drain/restart are accepted. No automatic
retry of partial/unknown pairs, two/three-store atomic recovery or power-loss
claims. Published main, CI queues, production, source pins and legacyIPC gate
are unchanged. Full D3B remains open.
