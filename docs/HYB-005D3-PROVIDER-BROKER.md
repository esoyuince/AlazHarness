# HYB-005D3A — provider credential broker and one-use egress grants

Status: implemented and locally qualified;1273 standard tests and five native
Gateway/broker cases passed. Exact-commit publication remains separately recorded. Base 2ee705ec6427d9af9bd695e132d82e198dc20b0a.
This is the local authenticated-provider transport slice, NOT complete OS egress
isolation, a hostile-Gateway security boundary, or full M1/M2 acceptance.

## The actual path

HostGateClient(requireProviderBroker=true, requireIsolatedRead=true) -> required
host capabilities -> existing native admission -> existing ExecutionLedger claim
-> native-owner egress grant COMMIT -> private Unix socket -> separate credential
broker -> fixed authenticated loopback provider -> validated response -> existing
ledger settlement -> native agent/result. The D2 native read tool stays in its
no-network Docker process. A second task queue, transcript, budget DB or agent
engine was not added.

The real upstream credential is supplied only to the separately started broker's
private bootstrap file. Gateway configuration/environment gets a local SDK
credential and a different signing key, not the upstream account credential.
The operator bearer, SDK bearer, signing key and upstream bearer are distinct in
native tests. A properly configured origin rejects the first three. This is not
a claim that a malicious same-UID Gateway cannot read another host file: the
Gateway, broker, kernel, operator and provider remain trusted in this slice.
The isolated tool does not receive the broker config, socket, keys or native DB.

## Existing writer, new bounded grant

provider_egress.authorize_egress uses the ORIGINAL ExecutionLedger native
_execute_write owner. An existing provider reservation must be present, unspent
as a response, current-generation, not quarantined and match the exact canonical
payload. A sealed egress record is inserted in existing state_meta under
alaz.execution.egress.v1.<scope>.<ticket>. It is not a job or accounting reset.
The returned envelope is signed only AFTER the native COMMIT returns.

The signed grant binds ticket, payload fingerprint, profile/principal scope,
profile binding, policy, native epoch/instance, broker lifetime ID, fixed route
fingerprint and a short expiry. A duplicate native authorization is refused.
A lost authorization acknowledgement retains both grant and full reservation;
no automatic resend, refund, deletion or replacement grant is permitted.

The broker reads, but NEVER writes, the same native state database. Before send
it verifies the live epoch, exact grant, reserved provider claim and nonquarantined
budget. The read is query-only, rejects table/view substitution, and rechecks
owner/data_version/store identity and expiry before returning. A second expiry
check runs on the broker event loop before forwarding. This is an authorization
snapshot, not a lock/lease preventing privileged revocation after the check.

Replay memory is consumed synchronously before an awaited read/send. It is
bounded to 1000 tickets for one broker lifetime. Every broker launch generates a
fresh ID; old grants do not become valid in the new process. No automatic broker
discovery, silent profile rewrite or grant re-signing occurs. The broker is not
a new durable budget writer. Existing profile-wide usage attribution remains
unchanged; egress records do not invent a per-run invoice.

## Mandatory selected transport, not a universal firewall

Broker mode and legacy direct mode are mutually exclusive configuration shapes.
When broker mode is selected, an IPC error never falls back to direct HTTP.
requireProviderBroker implies the execution boundary and sends a version header;
missing/wrong capabilities are rejected before intent/dispatch. Capability is
checked again before dispatch. A server without the requested broker refuses it.
Legacy direct mode is preserved for earlier explicitly configured callers; it
must not be advertised as brokered or retroactively accepted as isolated.

The qualified broker target is a literal http://127.0.0.1:<port>/v1 endpoint,
selected in trusted configuration and bound by fingerprint. No caller URL,
proxy, credential source, forwarding header or alternate route is accepted.
There is one outbound POST per consumed grant, no redirects or automatic retry.
Ambient proxy/netrc settings are disabled. Credentials are attached by the broker,
not copied from the caller. Response sizes/types are bounded, non-success bodies
and arbitrary response headers are not forwarded.

The supported JSON/SSE response guard checks literal and JSON-decoded strings,
JSON keys and same-path streaming fragments for an echoed upstream credential.
Malformed/duplicate-key JSON, incomplete SSE, wrong type and encoded response
bodies are refused. This is not a universal content-exfiltration detector: an
untrusted provider could invent other encodings. Do not promise confidentiality
against a malicious origin from these bounded checks alone.

## Private IPC and lifecycle

Only Linux Unix sockets are supported. A fresh private directory is0700; its
socket is0600. Parent/socket ownership, symlinks, socket identity around connect
and SO_PEERCRED same-UID identity are checked. The framed protocol uses bounded
lengths, request/reply signature domains and exact broker/nonce matching. At most
eight concurrent connections and finite read/send/response deadlines are allowed.
Neither an arbitrary same-UID process with host privileges nor kernel compromise
is excluded by this permission check; it is not a separate OS account sandbox.

The explicit run_provider_broker.py launcher requires a private0600 regular
single-link config file and a fresh output directory. It starts no model on boot.
Shutdown stops acceptance, closes/cancels active streams FIRST, then waits for
server closure. Late queued handlers close without issuing a reply or outbound
request. The owned socket is removed only under its recorded identity. Main
process termination/host crash recovery remains outside this gate.

## Tests and preserved first failures

Existing ledger tests are used with their synthetic SQLite owner for deterministic
native-transaction failure/ack-loss, twenty-way grant contention, changed payload,
wrong kind, epoch, scope, expiry, quarantine and replay cases. Protocol/client
checks use explicitly synthetic fetch/stream/aiohttp ports; they are not OS tests.

Separate QA7e1b introduced20 tests. Five failures in the9-case snapshot set showed
expiry not being rechecked after queueing and changed epoch/instance/grant not
invalidating a completed read. Product corrections pass the same unmodified
assertions. Eleven other tests cover IPC identity, domain, nonce, cancellation
and close behavior. Their source and initial/recheck evidence remain separate.

Fifteen response-guard tests initially exposed seven failures in decoded-credential
and malformed payload handling. The same tests pass after the semantic guard.
A real Linux idle-socket test additionally found delayed close; three synthetic
lifecycle regressions preserved that error and late-handler behavior before the
shutdown-order correction. Initial JS-edit syntax and Windows mock-port setup
errors are retained, not repurposed as runtime vulnerabilities or successful runs.

## Native qualification plan and scope

run_native_provider_broker.py uses existing prepared Linux Hermes/Python/Node and
the already cached D2 Docker image. Nothing is installed or pulled. Native
Gateway, SessionAuthority, AIAgent, SDK, file registry, isolated read process,
Unix broker transport and separate broker process are real. Only the external
provider is an authenticated scripted loopback fixture; no inference is purchased.

The five final scenarios are normal, missing broker, stale broker identity,
provider-attempt limit and upstream disconnect. Normal includes explicit replay
of the exact previously authorized payload/grant: it must be refused with no
additional origin request. Missing/stale broker must create no admission or
provider/tool reservation. Disconnect must keep its unknown reservation, not
refund or silently resend it. Native process IDs, owner generations, grant/claim
matches, origin counts, SQLite integrity and Docker binding exits are re-read.

Each fixture also directly rejects the three non-provider credentials with401.
Those authentication probes are not model invocations. Literal secret canaries
are checked against Gateway configuration, logs, result and tool capsules; this
is a bounded content check, not proof of all host-access isolation.

verify_broker_socket_shutdown.py separately opens a real idle Unix client and
checks the same0.3-second close expectation used to reproduce the initial issue.
It makes no TCP/provider request and is not another Gateway scenario. Historical
normal-v3 and import-failed-v2 receipts are not final-v4 native acceptance.

## Reproduce with explicit private inputs

```bash
python3 -B scripts/run_provider_broker.py --config /private/broker-bootstrap.json --output /private/fresh-broker
python3 -B -m unittest discover -s tests -v
python3 -B scripts/verify_broker_socket_shutdown.py --output /tmp/fresh-socket-check
```

The first command is an operator-owned daemon lifecycle, not an automatic agent
schedule. Its bootstrap must NOT be committed. Gateway's provider_broker settings
use socket_path, broker_id, route_fingerprint and signing_key from the trusted
operator setup. Ordinary CI does not start this service, import optional aiohttp,
start native Hermes, execute Docker or require retained private profiles.

## Remaining work

D3B: separate OS identities/credential store and mandatory network authority for
the whole configured provider path, including hostile code on a host. Qualified
remote HTTPS/DNS/redirect policy and real-provider tariff/token/context bounds are
still open. Do not turn on paid calls from the fixture-price tests. Broker loss
before/during send, host hard-crash takeover, cross-principal deployment and key
rotation need explicit acceptance beyond the included conservative no-replay rules.
Windows network acceptance, per-run usage binding, independent goal validation,
HYB006 memory/skill transfer and overall M1/M2 remain separate open work.

## Pre-publication v4 results

The frozen-v4 full standard suite executed1273 tests, exit0, no skips and no
changes/additions across210 measured code/config/test files. The110 added cases
are included, not added again to1273. Earlier1270 and concurrent QA suite records
are retained under their own source/qualification status.

Five native Gateway/broker scenarios passed on the same final product/launcher:
normal2provider/1isolated-read, missing0job/0provider, stale0job/0provider,
provider-limit1provider/1read with failed task, upstream-disconnect1provider/
unknown usage/no read with failed task. All five Gateway and broker processes
exited0; both Docker read containers were removed. The same-grant normal replay
was refused without another origin request. Three wrong-credential401 checks
per scenario are authentication probes, not paid model calls.

The idle-client real Unix socket test also passed its original0.3-second close
expectation, with zero active requests and the socket removed. It is separate
from the five Gateway cases. Retrospective native SQLite/grant/budget/process/
socket/container comparisons corroborated all five; they are not five new runs.
Canary secrets were absent from selected evidence. No paid/inference invocation,
new dependency, firewall/daemon modification or source-pin update occurred.

Evidence: evidence/hyb-005d3/full-final.json, native-suite.json, native-*.json,
native-store-corroboration.json and unix-socket-final.json. Code/CI receipt is
added only after the exact published commit finishes, never inferred from local
PASS. This does not close the broader D3B OS boundary or overall M1/M2.

## Publication-source requalification

The publication hygiene gate found one extra terminal blank line in
provider_egress.py. It was removed, with identical Python AST including source
positions; publication-whitespace.json preserves both exact hashes. No product
whitespace exception was introduced. Nevertheless all final checks were rerun
on the exact v5 publication bytes: full standard1273/1273, no skips, no source
changes/additions over210 files; five NEW native Gateway/broker scenarios PASS;
the idle-socket close check PASS. These results supersede v4 as final-source
qualification; old runs are preserved, not counted as extra unique scenarios.

Authoritative final receipts: full-publication.json/.txt, native-suite-final.json,
native-final-<scenario>.json, publication-native-corroboration.json and
unix-socket-publication.json under evidence/hyb-005d3. Gateway/broker processes
all exited normally, exact Docker read IDs and sockets are absent, and the
retained native databases remained unchanged by the corroboration read.
Same-code-commit CI is still read separately after push.
