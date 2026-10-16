# HYB-005D2 — native Hermes read isolation

Status: bounded Linux native read binding published; exact-code CI1163/1163 PASS.
The implementation is not the complete harness security perimeter.
Base: fb3d7ca7fec3b5e0242a8e7c174b553dbfe366d8.

## Delivered integration

The existing GuardedFileTools still owns the file allowlist and durable
ExecutionLedger reservation. When isolated_read is explicitly configured it now
calls NativeReadIsolation, which registers a real native
TerminalEnvironmentProvider through PluginContext. Native read_file_tool,
ShellFileOperations, result formatting, pagination, denylist and redaction are
not replaced with an imitation reader. The native generated shell read runs in
the existing one-shot IsolatedToolRunner, not on the Gateway host.

The trusted host stages only the approved regular .txt input (maximum64KiB) and
a fixed launcher plus the native command into a fresh capsule. File links,
hardlinks, unexpected input types and replacement evidence are rejected. The
original host path still passes the native safety and redaction checks. A unique
capsule basename avoids a stale native dedup cache across snapshots. The actual
run/session/task identities remain unchanged. Only ONE native shell round trip
is allowed for each reserved invocation; a fallback sequence is refused rather
than retried on the host. This is a bounded .txt slice, not every Hermes document,
search/write operation or complete arbitrary-file parity.

## Authority and cancellation

Before execution, the existing native SQLite owner checks the current runtime
epoch/instance, non-quarantined budget, reserved exact ticket/fingerprint,
active api admission, target and owner scope, selected model, admission ID,
execution generation and canonical payload digest. ID/generation/digest/epoch
are frozen for the invocation and compared again immediately before execution
and while the running child is monitored. No second queue or database was added.

The normal pinned read_file dispatcher does NOT pass parent_agent. Native
approval-context IDs and tools.interrupt thread/acting_for_tid are therefore
captured at the actual call boundary. Native stop flags, configuration revocation,
lost authority and quarantine stop the owned tool process. A stopped observer is
not a second execution. A missing/unavailable Docker backend never calls the
local original handler as a fallback. Unknown, refused, timeout, cancelled,
output-limit and mismatched exit/outcome evidence never become successful reads.
Reservations are not refunded automatically. This is not exactly-once arbitrary
external effects or automatic parent-crash cleanup.

## Required client mode

HostGateClient({requireIsolatedRead:true}) requires execution validation AND
isolatedReadBoundaryVersion=1 with the explicitly named Linux backend. It sends
both required headers on its host-gate requests. Missing, changed or malformed
capability stops issue/dispatch; no raw /v1/runs fallback. The mode is explicit;
legacy clients are not silently relabelled isolated. The plugin, native daemon,
operator, image and host kernel remain trusted. Unmodified Hermes access outside
this dedicated Alaz route is not claimed to be disabled by this client mode.

## Preserved failures and review

Independent QAD65F initially found seven failing assertions: quarantine did not
revoke previously reserved tickets (2), invalid/changing admission ID or generation
was not bound (3), and completed/nonzero or failed/zero exit conflicts were
accepted (2). The product was corrected and the same unchanged tests passed.
The original failing receipts are retained. Its source/native dispatch observation
also exposed the missing parent_agent assumption, which is now handled using
native thread contexts. The separate native dispatcher experiment remains FAIL
because imports attempted seven subprocess launches that its audit guard blocked;
it is not a clean Gateway run. Eight actual interrupt-module observations are
recorded separately from synthetic-port unit tests and native Gateway runs.

Two earlier full standard test runs passed their tests but changed measured code
or source membership during execution. They remain NOT_ACCEPTED final snapshots.
A later immutable-source suite is required. Never add subset, rerun and native
scenario counts together to inflate the standard test total.

## Native test environment

The Linux host originally lacked the pinned Hermes application dependencies. A
fresh /tmp/alaz-hyb005d2-247a area contains exact-hash native source and private
Python/dependencies prepared through the native PM frozen API. No system packages,
personal profile, firewall or Docker daemon configuration were changed. The first
preparation failed because the source staging omitted pm/uv.lock. The original
pinned file was added; frozen verification was NOT disabled. Both receipts remain.
A Node executable was copied from an already cached image, not downloaded. An
unnecessary chmod on that root-owned copy failed; its existing755 mode and actual
version/hash were subsequently verified. Its created-only source container was
removed without starting it.

The first real Gateway trial used an incorrect plugin-settings fixture and
returned404; it is preserved as FAIL. Correcting the fixture to the existing
plugins.entries.<id>.settings contract allowed the real native read chain. An
initial normal success is not transferred to later changed probe revisions.

For cancellation/deadline/revocation only, a new test-only image is derived from
the already cached pinned base image with network=none. It delays interpreter
startup8seconds; the product, native read handler and actual admission methods
are not patched to synthesize success. Ownership and source/derived image IDs
are recorded. This is explicit test preparation, never an agent-controlled image
build, installer or runtime fallback. It is not a supply-chain qualification for
a production image.

## Remaining boundaries

The Gateway process and its provider credentials still run on the trusted host.
The read command is OS-isolated; host-side input staging/formatting is not an
isolated Python runtime. Protection from a malicious host operator or arbitrary
code in the Gateway itself is not claimed. Host-source TOCTOU is bounded by
checks, not eliminated against a privileged writer. Parent hard-crash takeover,
Windows network acceptance, general provider credential/egress isolation,
real provider token/price validation, memory/skill transfer, and full M1/M2 remain
OPEN. This test packet uses only scripted model responses and fixture prices;
there are zero paid or real model inference calls.

## Validation and publication

Final counts and exact code/CI commits are appended only after their receipts
are read. Branch: alaz/hyb-005d2-native-tool-247a. Main is unchanged.


## Final local/native validation

The final stable local standard suite passes1163/1163, exit0/no skips; all197
measured code/config/test files stayed byte-identical. The101 added cases consist
of37 bridge,12 client and52 independent QA tests. They are INCLUDED in1163,
not another101 to add to it. Native OS experiments are opt-in and not run by
ordinary server CI. The source-stable targeted79/212/53 groups are also subsets.

The final integration-v3 suite runs EIGHT new native Gateway lifecycles:

| Scenario | Provider HTTP requests | Actual tool-container observation |
|---|---:|---|
| normal | 2 | One native read, one settled tool ticket, exact result marker, container removed. |
| tool-limit | 2 | Native error tool_attempt_limit; zero tool tickets and zero containers. |
| missing-isolation | 0 | Required client refuses; zero jobs/tickets/containers. |
| wrong-backend | 0 | Required client refuses; zero jobs/tickets/containers. |
| missing-image | 2 | No pull or fallback; reserved ticket kept, no container created. |
| cancel-native | 1 | Actual stop through HostGateClient while inspected container was running; cancelled/removed. |
| timeout | 2 | Tool deadline expires before delayed read; timeout/removed, reservation retained. |
| live-revoke | 1 | Allowlist revoked while inspected container was running; cancelled/removed, next provider request blocked. |

All eight scoped expectations pass, no source drift, clean native exit and no
unexpected Python non-loopback attempt. Four physical tool containers were used;
eight Gateway cases are NOT eight successful jobs or eight tool containers. No
real inference occurs at the scripted provider. The native stop case is persisted
as interrupted; live revocation as failed. Tool-limit/missing-image/timeout runs
can end with a completed assistant explanation while the tool itself was refused
or timed out; neither the report nor this table claims goal success in those cases.

A later, separate read-only check rereads both native admissions and execution
claims, actual tool transcripts, private runner ownership/prestart/exit records,
matching input digests and exact container IDs. All eight are corroborated and
all FOUR actual final-case containers are absent. This is corroboration of existing
runs, NOT eight additional executions. The3725 staged native source files and
integration program hashes match. Evidence: native-suite.json, native/*.json,
corroboration.json and full-standard-candidate.json/.txt.

The test-derived slow image was removed by its exact verified ID/owner after its
containers exited; the cached base image was preserved. First fixture/preparation
failures, earlier normal trial, independent failed-import observation and unstable
full-suite snapshots remain separate evidence. Earlier D1/Windows outcomes are
not relabelled by this Linux read acceptance.

## Reproduction

Run scripts/run_native_isolated_read.py with explicit --source, --python, --node,
--output (fresh Linux directory), --image (already-present content ID) and
--scenario. The script requires the verified alaz-source-manifest.json produced
by source staging. The existing native PM preparation is optional and explicit
through scripts/prepare_linux_hermes_d2.py --apply; never use a personal profile.
For cancellation/revocation/timeout, explicitly create a fresh test image with
scripts/qa/prepare_slow_isolation_image.py --apply, retain its receipt and pass
that image ID. Ordinary startup never prepares/pulls an image. Standalone tests:
python -B -m unittest discover -s tests -v.

Exact publication/CI receipts and the next provider-credential boundary are recorded
in status.md. Parent-hard-crash takeover is still a separate unresolved gate.


## Exact-code publication

Code commit e6cb7f16016548c8bea7275f4ac3c987d6fad71b is published on the feature
branch. GitHub alaz/local-ci is success. The alaz-server receipt verifies
sha==checkout_sha at that exact commit, executed1163/passed1163/failed0/skipped0/
suite_errors0, with status delivery posted. Evidence: evidence/hyb-005d2/code-ci.json.
No native Gateway or Docker experiment is silently attributed to standard CI.
The documentation receipt commit changes no tested code/config; its own CI status
must be checked independently, never inferred from this code-commit result.
Next: provider credentials and mandatory network egress boundary (HYB-005D3).
The existing parent-hard-crash and Windows network gates remain separate and open.
