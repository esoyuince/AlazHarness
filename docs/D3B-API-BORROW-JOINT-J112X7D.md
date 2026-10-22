# J112X7D - one staged native API borrowed-store patch series

This union selects A112X7D response canonical-state borrowing and B112X9 native
API constructor/selection/drain. Exact harness/native commits are in inputs.json.
Native feature cc16c10b16a0ca8d80b23fd9be3f0e59ee605075 descends from response
feature e19a945342c94138c685ac919b208d558ddcc53a, on immutable eb75627. The
active native gitlink, sources.lock, installed runtime and production stay pinned
as before. This is tested optional source, NOT a running agent HTTP service.

## Product contract

The native APIServerAdapter may receive one exact BorrowedAPIStores bundle with
real native SessionDB, RunIdempotencyStore and ResponseStore handles. Constructor
and profile selection reuse those handles instead of silently opening another
store. Bundle claim is one-shot and process/thread/home/connection-bound. Foreign
profile fallback, injected runner conflicts, changed references and hidden store
caches are refused. No second adapter/runtime engine is introduced.

ResponseStore's canonical_state option is the complementary inner requirement.
Terminal/tombstone reads reuse the caller's writer connection under its native
mutex. The generic upstream _read_ctx helper is not used because it may open
pooled readers or reopen closed state. Busy/active/closed/foreign/replaced state
fails, no transaction rollback or new canonical connection. Main-qualified reads
prevent TEMP tables from pretending pending work is terminal. Queued, started
and unknown identities remain unsettled; the owning response file retains its
native cache/identity behavior. Default unborrowed behavior remains tested.

Borrowed disconnect drains adapter resources, never closes caller stores or
releases its profile/image lease. Active workers/tasks/transactions block detach;
unknown counters are not mistaken for zero. Cancellation or uncertain cleanup
leaves the bundle CLOSE_UNKNOWN and refuses blind retries. Native status-writer
startup is avoided on the borrowed teardown path. The existing default adapter
continues to own/close its separately constructed stores.

Most importantly, borrowed connect() currently raises
borrowed_listener_not_qualified BEFORE network activation. Retaining the handles
is not sufficient authorization to expose work/model routes.

## Genuine tests versus standard receipts

A112X7D executes24 real-native behavioral methods on Windows and ordinary P71C
Linux: construction/open counters, actual settlement, queued/started/unknown,
tombstones, caller transactions/mutex/handle generation, TEMP shadow, disk or
memory failure, reuse, response body/conversation behavior and close ownership.
No native class/factory is replaced. Both platform repetitions are24 distinct
methods, not48 scenarios. Borrowed settlement observes zero canonical connects;
unchanged default is the positive extra-reader control.

B112X9 adapter004 executes27 methods with the actual native adapter and all three
native store classes. Only explicit shutdown failure/await-order fixtures are
doubled. Watched construction/selection/drain observes zero new SQLite connects.
A separate Linux original-versus-borrowed response experiment uses real competing
SQLite processes: both original and new preserve the EXCLUSIVE owner lock, and
only owner close permits acquisition. Borrowed settlement uses0 extra canonical
connections and can settle committed terminal state under that lock; uncommitted
state/TEMP fiction stays unsettled. No upstream lock corruption was observed.

The adapter fixture's Windows event-loop wakeup sockets are isolated test
framework setup. One optional urllib3 IPv6 feature bind was BLOCKED during import;
that denied event remains in the raw evidence. No new network attempts occurred
during test cases; no provider/model request or borrowed HTTP listener ran.
First fixture failures and earlier aggregate classifications are retained.

The native feature's309 actually imported modules were independently reread from
Git and matched to the actual adapter receipt. Fresh sequential application of
both patch files to immutable native originals reproduces exactly the five
modified-module hashes. There is no unversioned product monkeypatch. Source
snapshots in evidence are historical; config/hermes-api-borrow-series-j112x7d.json
is the single ordered, source-locked STAGED selection with activation disabled.

15 offline receipt tests (7 response +8 adapter) are members of the standard
suite, NOT new native trials. The new combined complete harness regression is
recorded separately. Native upstream full pytest, full isolated API adapter and
three-store A109 restart/ingress are NOT RUN/accepted by these patch proofs.
The old23 platform/opt-in Windows skips are not rerun here.

## Compatibility and provenance

All427 existing harness source files remain unchanged. The union freezes434
source/config/test files and the two separate patch hashes. Both original branch
histories and evidence blobs are preserved. Only status.md conflicted, and both
handoffs are archived. The native patches are not copied wholesale as a new engine
or silently installed by changing source pins.

Windows line-ending conversion initially prevented a raw-byte patch check; only
the temporary repository's autocrlf setting was disabled to establish exact-byte
application, with the earlier mismatch retained. Native author-identity absence
stopped a commit before effects; the existing harness identity was supplied only
to the successful local commit command. No global/repository user configuration
was changed. All temporary native data/code was removed; the shared lab and
existing production/account/CI/defaultUbuntu settings were not modified.

## Remaining activation gate

1. Prepare and pin response_store.db schema/identity and finite profile inventory;
   verify existing response data read-only BEFORE any native constructors/migration.
2. Integrate ownership of all THREE files into the sole A109 startup and close
   order, including failure rollback/unknown-effect handling. The borrowed reader
   protects canonical state only; ResponseStore still writes its OWN cache and
   retains native migration/eviction/close semantics. No cross-file atomicity.
3. Define healthy/busy observation using current native ownership/generation and
   legitimate in-flight work. Do not simply reuse the quiescent diagnostic gate
   or treat every pending record as safe to replay. Busy shutdown refusal alone
   is NOT the completed healthy/busy HTTP policy.
4. Qualify that same fixed three-store/adapter path under full isolation before
   listener activation, then broker live-ledger and dummy-provider accounting.

Native connect remains refused until these gates are accepted. No automatic
partial/unknown retry, paired atomic recovery or power-loss guarantee is inferred.
Legacy IPCv2 stays CLOSED and full D3B OPEN. Main/push remain unchanged.

## Terminal combined standard result

NEW fullWindows2813 =2790PASS /23SKIP /0ERROR /0FAIL, exit0. All434 source/config
hashes and both patch hashes stayed exact. All427 original source files unchanged.
79 parent evidence Git blobs preserved.15 offline receipts are standard-suite
members, not extra native runs. Actual24 response methods on two platforms and
27 Windows adapter methods remain distinct scoped proofs. The union itself
performs no new native runtime or provider action. Static-final.txt records the
local static gate, not remote CI. Installation/source-pin promotion is disabled.
