# R110X6C2 — independent HTTP readiness wire and lifecycle audit

Base82a8c3e. This branch adds no duplicate HTTP/store runtime. Concurrent H110E
owns gateway_http_readiness.py. A fresh-worktree collision was rejected BEFORE
any write; another task's uncommitted files were never changed by this task.

## Actual HTTP, explicitly doubled storage

The audit loads an exact local runtime snapshot by SHA256 and uses real aiohttp
listeners and TCP requests to127.0.0.1 only. NativeStoreStartup identity, native
ProfileLease actor and live-store verification are explicit test doubles. These
are NOT real Hermes connections or full P102 network/mount/cgroup acceptance.
The real native lifecycle test belongs to H110E and must be verified separately.

29 methods check auth failures/duplicates/invalid byte encodings, strict Host
and Origin behavior, query/encoded/path aliases, non-GET and model/job/session
routes, body/chunked/conflicting framing, oversized/excess headers, monotonic
readiness revocation after storage faults, handle/epoch replacement, listener
port collision, start-once, delayed header clients, HTTP close before storage,
refused storage close and cancellation/uncertain HTTP cleanup. Only test-owned
runner cleanup is forced by the fixture after deliberately injected failures;
that is not a product retry or a release of actual native data ownership.

Current source9612d3c passed29/29 on Windows with installed aiohttp3.14.3 and
29/29 on ordinary P71C Linux using the identical108 pure-Python dependency files.
The source inventory was independently checked against each installed package's
RECORD hashes and byte sizes. No pip/download/system dependency update occurred.
Compiled extensions are used where available in Windows, not transferred to
Linux. Platform repeat means29 unique methods, not58 independent scenarios.

## Reproduced product defect and corrected candidate

Original sourcec8d8ff1 returned HTTP500 for an Authorization value with one raw
0xff byte. aiohttp preserves an undecodable header byte as a surrogate; the
application's unguarded UTF8 re-encoding raised UnicodeEncodeError. Authentication
was NOT bypassed and no state/model work ran, but the intended bounded401 path
failed. The real wire failure and traceback remain in windows-003.

A one-condition ASCII guard in an OWN scratch copy passed the entire29-method
audit. Concurrent H110E independently incorporated ASCII-only plus nonempty
credential validation and ASCII comparison. Its current9612d3c bytes were then
copied without alteration and the whole audit rerun on both platforms. No old
success is attributed to changed source and no uncommitted parallel file was
patched. authorization-ascii.patch is the narrow proposed delta, not evidence
that this task wrote H110E's implementation. Current-source native/full gates
remain H110E's responsibility until terminal integration is verified.

## Test-harness failures retained

The first25-case run tried assigning AppRunner.cleanup on a slotted instance.
Two methods each emitted a body and teardown error (four error events).23
methods actually passed; the initial raw passed21 counter subtracted events
rather than distinct failed methods. This is explicitly corrected in the review,
not rewritten in the original receipt. Test doubles now patch the CLASS method
and restore it before actual test-owned runner cleanup; assertions were not
weakened. A corrected unchanged-runtime25/25 run preceded the expanded wire test.
Malformed HTTP parser diagnostics in stderr are expected negative fixtures,
not silently deleted and not confused with test runner failure.

## Native API integration caveat found in immutable upstream

At Hermespin eb75627faf532fa6ffbdae59a0d14b0b385fc780, APIServerAdapter initializes
ResponseStore plus another RunIdempotencyStore; simple /health unconditionally
returns status ok. That is not an adoption of A109's existing verified handles
and is not storage qualification. The relevant source hashes/function ranges
are in native-http-integration-review.json. No upstream code was modified.
The diagnostic readiness endpoint must not be presented as the full Hermes API.

## Evidence and scope

Runtime snapshots and original failures are retained in this directory. The
standard suite gains six OFFLINE source/log/evidence consistency methods; they
do not rerun the29 real HTTP tests and require no aiohttp installation. A full
standard regression is recorded separately after terminal completion. Its
result is not proof of a native Gateway launch. All414 original source files
remain unchanged; only QA executable and receipt tests are new source files.

Separate cleanup audit finds no owned Linux temp directory or HTTP test process.
Shared P71C is not terminated, defaultUbuntu/production/CI/accounts/main/remote
are untouched. No root/mount/provider/model call was made. Any canonical merge
must retain one H110E implementation, preserve its native source proof and run
a NEW combined regression. HTTP storage-readiness does not grant work dispatch,
paired recovery, power-loss safety or full D3B. Legacy IPCv2 stays closed.

## Next integration constraint

The current live-store check is intentionally quiescent: pending admissions, running replay records, active transactions and writers revoke diagnostic readiness. It must not be reused unchanged as a healthy/busy agent-serving readiness test once work routes are added. Future native HTTP adoption needs a separately reviewed distinction between valid in-flight work and ownership/epoch drift, plus one authority for borrowed SessionDB/replay/ResponseStore lifecycle. The current limited service does not solve that broader policy.

## Terminal independent branch result

Fresh fullWindows2700=2677PASS/23SKIP/0ERROR/0FAIL, exit0. All416 source hashes stable; all414 baseline source files unchanged. The6 offline checks are part of that total. The29 real-wire methods were run separately with actualaiohttp on each platform and are not full-suite/native Gateway methods. Local static follows in static-final.txt; no remote CI or product publication is implied.
