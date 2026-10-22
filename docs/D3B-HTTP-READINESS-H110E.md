# H110E — authenticated native-storage readiness HTTP

Base82a8c3e; branch alaz/d3b-http-readiness-h110e. Canonical A109 is the only
NativeStoreStartup. Existing414 sources are unchanged. This adds a small
readiness-only lifecycle using existing aiohttp, not a custom HTTP parser or
second native writer. The actual Hermes API adapter is NOT instantiated: its
constructor independently opens replay/response stores and cannot safely be
assumed to reuse the already verified A109 handles.

## Implemented boundary

`gateway_http_readiness.StorageReadinessHttp` takes one NEW exact A109 startup
object, a local caller-supplied64-hex random bearer token and optional numeric
port. It is bound to the originating process/thread/event loop, not a remote
launch capability. Host is fixed IPv4 loopback; no wildcard/host input, inherited
socket, dynamic route, model hook or user callback. No listener is constructed
until A109 start returns verified and the existing live gate succeeds again.

Only GET /health/live and GET /health/ready are accepted. All diagnostic routes
require exactly one matching Authorization header and exact numeric loopback
Host/port. Origin, body, duplicate credentials and other routes/methods/encoded
aliases/query strings refuse. HTTP parsing and framing are handled by aiohttp;
there is no handwritten parser. Application replies are small JSON, no-store,
nosniff and force-close. Access logging is off and credentials are never returned.
Parser-level malformed messages may be rejected before our JSON handler, with
an aiohttp plain-text400; that is recorded distinctly from application JSON.
This is local diagnostic authentication, not a full public-facing security review.

Liveness proves only that the process serves this route. Readiness checks the
held profile, unchanged A109/native objects and connection identities, trusted
expectation and current live SQLite epoch/settings/schema/work state. It never
opens another store or grants provider/work dispatch. Any observed failure
permanently revokes readiness for that lifecycle; later fixing the dependency
cannot silently return it to ready. Normal task execution is NOT enabled: the
existing live gate intentionally refuses unfinished work and active writers.
This quiescent diagnostic contract is not production readiness for a busy agent.

Shutdown marks readiness stopping BEFORE awaiting cleanup. Existing aiohttp
runner cleanup stops sites and drains handlers, then A109 may close its own
native handles. An uncertain/cancelled HTTP cleanup retains storage and forbids
blind retry. An explicit native transaction/writer refusal leaves HTTP closed
and profile held; caller may settle/drain then request storage close again.
Caller ProfileLease is never released by the HTTP object. Wrong actor/loop and
second start refuse. Failed socket bind is not assumed to undo A109's committed
epoch: the real occupied-port scenario explicitly records that epoch effect.

## Actual native Linux HTTP proof

Approved P71C, ordinary UID23001/GID23003, fresh owned temporary profiles only.
Separate preparation processes create real native schemas and expectations and
close them. New target processes enforce unchanged current Landlock metadata
policy and exec before native profile/store startup. No native class/method or
storage check is doubled in this run. Three scenarios are independently prepared:

1. Wrong schema fails preflight: no parent native SQLite connection, no epoch
   advance and no listening port. Owned resources close without releasing others.
2. Existing loopback listener causes genuine EADDRINUSE after verified startup;
   the foreign owned-test listener is not displaced. The already advanced epoch
   is truthfully reported, not rolled back or retried as if nothing happened.
3. Normal native startup serves real HTTP401/400/404/405 and ready/live200.
   An explicit QA epoch change makes readiness503. Restoring the old epoch still
   yields503. A native transaction then blocks storage close after the HTTP port
   is already unreachable. Explicit QA rollback allows native close and profile
   release. During HTTP observation there are zero new SQLite connections and
   zero raw database opens; the same two native store objects are used.

Native003 has55 overlapping predicates across those three scenarios, not55
independent process runs. It uses real aiohttp3.14.3 pure Python implementation,
real TCP requests and unchanged pinned Hermes sources. It does NOT test a full
private-network/mount/cgroup image lifecycle, external HTTP ingress, native API
adapter, jobs/chat endpoints, broker live-ledger access or provider sends. The
prior A109 full-confinement result is separate and not relabelled a new HTTP run.

## Dependencies and failures retained

The laboratory has no system aiohttp installation.108 pure Python source files
from10 existing prepared-environment distributions were verified against their
installed RECORD SHA256/length and copied only into a fresh temporary code tree.
No package download/install/update, Windows binary transport or global runtime
change occurred. The276 native Hermes and31 pure dependency files reuse prior
immutable Git/dependency inventories. Actual imported hashes are checked and
preserved. RECORD matching is byte custody, not a new publisher-signature audit.

Native001 correctly failed during lazy aiohttp import: its unused file-response
module initializes stdlib mimetypes, which tried /etc/mime.types. A direct
Python3.12 probe showed init(files=[]) still prepended knownfiles. The product
now temporarily sets the documented public knownfiles configuration to empty
while seeding the built-in table and restores it in finally. Existing initialized
maps are left alone. No OS read grant, Landlock/native/aiohttp function change or
file-serving route was added. Original failure and source are retained.

Native002 reached real listening and rejected invalid requests; its QA failed
because it assumed every negative reply was JSON. Duplicate Host was correctly
rejected by the underlying parser as text/plain400. QA now accepts that exact
parser result ONLY for that expected case; other status/cache assertions remain.
Original output and forced owned-child cleanup are preserved. Native003 reran
all scenarios with unchanged product and passed, without forced cleanup.

Independent R110X6C2 real-wire QA exposed invalidUTF8 Authorization500 in an
earlier source snapshot. Current product's ASCII/nonempty validation rejects it
as401; a local surrogate/Unicode regression and independent actual-wire rerun
confirm it. The independent source remains unmodified, and its exact QA bytes
are retained in our evidence. Earlier tests are not attributed to current code.

## Verification accounting

30 local lifecycle/stdlib tests use explicit HTTP/native dependency doubles.
Five offline receipt tests check the genuine native proof, exact current source,
upstream/dependency pins, refusal order, cleanup and bounded claims. These35
methods belong to the standard suite, not additional native runs. Independent
29-method actual aiohttp wire tests use explicit storage/profile doubles and
therefore do not substitute for real-native acceptance. Windows/Linux repeats
are the same methods, not double coverage. New full standard count is recorded
only after a terminal result with before/after418-source hashes.

Both parser implementations are distinguished: prepared Windows has installed
extensions, Linux transport uses verified pure Python fallbacks. Neither result
claims benchmarking or broad public-network DoS/load acceptance. Readiness probes
run synchronous existing SQLite checks on the owning event-loop thread and are
intended for a controlled local quiescent lifecycle, not unbounded public polling.

## Delivery and remaining work

No main/remote push, CI queue/config, production, defaultUbuntu, account, mount or
root action belongs to this task. Original414 files and parallel QA work remain
intact. All private profile/code fixtures are temporary and audited absent;
shared lab is not terminated. Old R91F/G82C denied edits were not retried.

Next compose THIS readiness service in the full canonical isolated launch and
explicitly design ingress; then bridge actual Hermes API dependency injection
without a second response/replay writer and test broker live-ledger/dummy-provider
execution. No automatic partial-pair retry or HTTP dispatch authority is implied.
Legacy IPCv2 CLOSED/fullD3B OPEN. Read status.md/summary.json/delivery.json for the
active local continuation. Reported static CI is local, not remote publication.

Background references (not execution evidence): official aiohttp web_advanced
Graceful shutdown and AppRunner docs; Python3 library/mimetypes documentation.
Installed behavior and native evidence take precedence over a documentation-only
assumption about init(files=[]).

## Terminal qualification

NEW fullWindows2729=2706PASS/23SKIP/0ERROR/0FAIL, exit0. All418 sources stable,414 baseline files unchanged. Linux35/35 selected methods and29/29 real-wire cases PASS; Windows same29/29 current-source real-wire PASS. These repetitions/subsets are not added to full standard count.23 old platform/opt-in skips were not rerun. Actual native00355 predicates PASS; all three scenarios complete, zero forced cleanup, temporaryroot removed. Cleanup audit CLEAN. Current local static and commit are recorded below/in summary; no remote CI or release claim.
