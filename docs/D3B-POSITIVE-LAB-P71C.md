# D3B positive broker host-UID acceptance â€” P71C

Status: **SCOPED REAL TWO-UID BROKER PASS**; full D3B remains OPEN.
Branch: `alaz/d3b-principal-launch-21oct`.
Development starting commit: `2358d5dad7c7a0b98c1c494f30d69fc0572977c2`.
Exact installed product source: `802fade74d5b08b26f975738d4aa8d7546dc9cac`.
No product source was changed to make this native acceptance pass.

## Authorization and isolated target

The user explicitly continued in response to the proposal for a separate,
disposable Linux installation, two test users and one root-controller acceptance
run, with the existing Ubuntu and production server untouched. The bounded scope
is recorded in authorization-scope.json and the starting status entry. Previous
privilege denials against other scopes were not bypassed. Every new privileged
operation targeted ONLY the newly created `AlazHarness-D3B-P71C` distribution.
No sudo policy, setuid helper, existing account, Windows default distro, global
WSL setting, production server or personal-agent state was modified.

An official Ubuntu Base24.04.5 rootfs was downloaded from cdimage.ubuntu.com,
checked against its HTTPS SHA256SUMS and the independently retrieved checksum.
No detached GPG-signature verification is claimed. The rootfs SHA256 is
`e77b6f10c2590cef872b33ee9f635a0e3fd1f57fb074c0e52b5c7f56147a0c86`.
The reviewed initial overlay disables Windows-drive automount and Windows
program interop before first boot; systemd is disabled and policy-rc.d blocks
automatic package service activation. Only the new distro receives the minimal
Python3/libseccomp/strace/CA packages through normal authenticated apt metadata.
Actual package versions, image hash, overlay hashes and command outcomes are kept.

This is a controlled WSL2 Linux installation sharing the WSL kernel, not a
separate-hypervisor isolation certification. Test payloads are benign and use
no real credentials. The acceptance subprocess additionally creates a fresh
network namespace with only lo and no route. It does NOT create a user namespace:
the initial UID/GID maps and user:[4026531837] identity remain unchanged.

## Exact installation and provisioning

The 57-file source archive SHA256 is
`8c0bbad498ccc877edbce85af535dd0fcd68b2dbf21b72858487577942424451`.
Every file was checked against the original manifest, manually copied as a
regular file to `/opt/alazharness-broker/802fade`, and made root-controlled under
root-controlled ancestors. No archive link/owner metadata was blindly applied.
The actual interpreter is `/usr/bin/python3.12`; its installed hash is recorded.

Only two new locked/nologin test accounts and one group were created:

| Role | Actual UID | Primary GID |
|---|---:|---:|
| Gateway-identity QA client (`alazgateway`) | 23001 | 23003 |
| Broker (`alazbroker`) | 23002 | 23003 |

The private config and budget are broker-owned0600 inside broker-owned0700
private storage. Fresh socket directories sock1/sock2 are broker/group-owned0710;
the running broker creates each egress.sock0660. The root-only0600 contracts
pin the installed argv, exact config hash and initial host namespace. Budget
creation uses the existing explicit initializer under the actual broker UID,
not an implicit runtime-create fallback. The declared maximum provider calls
is **zero**; the dummy provider route is loopback port1 and no send is attempted.
Gateway state.db is not provisioned for a dispatch test; ping does not need it.

## Real native results (not mocks)

Two actual broker lifetimes completed under installed, unchanged product code:
PID49 (untraced) and PID60 (strace-observed restart). The root launcher enters
the broker target in the same process. `/proc/<pid>/status` shows all four UID
slots23002, all four GID slots23003, no supplementary groups, one thread,
all five capability sets zero, NoNewPrivs1 and Seccomp2. The observed executable
and command line identify the fixed isolated-Python target from the installation.
The initial user namespace/maps and the owned network namespace are preserved.

The native trace confirms successful setgroups(0,[]), setresgid and setresuid,
then exec of the fixed target. Actual server getsockopt(SO_PEERCRED) observations
show the Gateway child UID23001/GID23003; the client's actual SO_PEERCRED shows
broker UID23002/GID23003 and the live broker PID. Both protocol checks run in
the unchanged product path. No peer, kernel identity, config admission or
broker lifecycle is monkeypatched in these runs.

Each lifetime receives one independently framed authenticated ping and one
actual ProviderBrokerClient.ready() call: four successful pings in total.
A validly signed request arriving from the broker UID (wrong Gateway identity)
is rejected by the server. The actual client likewise refuses to send when
its own identity is not the declared Gateway. After restart a request carrying
the first broker ID is rejected as stale_broker_identity.

For BOTH present private files (config and budget), the Gateway identity attempts
O_RDONLY and O_WRONLY opens. All four attempts per lifetime fail with explicit
EACCES/EPERM, not missing-file or timeout outcomes. The broker identity can open
the same files in both modes and reads their matching hashes. Write-open positive
controls close without writing: no database contents are changed just for QA.
This establishes ordinary read/write-open denial by host permissions; it does
not assert proof against a trusted root administrator or every possible IPC path.

Both brokers exit0 after owned SIGTERM, remove their sockets, leave zero active
requests, preserve the initial private budget and record zero physical provider
attempts/responses. Private file contents, inode identities and all57 installed
source hashes remain unchanged. No forced cleanup was needed.

## Preserved test-tool failures and reviewed result

The first probe stopped BEFORE a broker started because it expected a header in
an empty /proc/net/route file. This WSL kernel reports an empty route table as
zero bytes. The QA preflight now accepts either zero bytes or only the expected
header; route entries remain forbidden. Both socket directories were confirmed
empty before the corrected run. Product code was not modified.

The second native execution completed both lifetimes and all product checks,
but its collector reported19/20 and exit1: it expected strace to print
`setgroups(0, NULL)`, while the successful syscall was printed as
`setgroups(0, []) = 0`. Original native JSON, trace and executed QA source are
retained unchanged. The executed source snapshot is
`accept-executed-before-trace-fix.py.txt`; trace-parser-correction.json binds it.
The final reusable QA script handles both representations; it was not falsely
reported as having performed a new native run.

A separate read-only reviewer verifies exact kernel state, source/file custody,
all access attempts/owner controls, both identities, signed-ping outcomes,
restart/counter/cleanup evidence and six PID-bound syscall/peer patterns in
strict transition order. It accepts only this specific original parser failure.
It cannot convert an unrelated native failure to success. The reviewed outcome
is **20/20 native checks confirmed**, not a new execution. Sixteen offline
positive/negative review controls pass, including wrong UID/capabilities/maps,
missing files, failed owner controls, changed bytes, wrong peer PID, failed
syscalls, wrong trace order, nonempty groups and real provider-attempt rejection.

Controlling evidence:
- `native-acceptance-001.json`: ORIGINAL collector FAIL, preserved.
- `native-broker2-strace.txt`: actual trace, not reconstructed.
- `native-acceptance-reviewed.json`: reconciled positive scope, hashes of originals.
- `review-controls.txt`:16 offline controls; not16 native UID transitions.
- `native-sock1-lifetime.json` and `native-sock2-lifetime.json`: raw observations.
- `native-provision.json`, `final-lab-audit.json`, `cleanup-summary.json`.

All repeat/native/standard counts overlap where noted and are never summed
into a fictitious total. The fresh Windows standard run and static gates are
recorded separately after terminal completion.

## Cleanup and exact next gate

No test broker process remains and both sockets are absent. Only the named
new distribution was terminated; `wsl --shutdown` was NOT used. The original
Ubuntu remains default and stopped, exactly as observed before setup. The new
P71C distribution is also stopped. Its disposable virtual disk and dummy state
are retained under this worktree's ignored scratch/principal-lab-p71c for
inspection/next-stage work; they are not committed or installed on production.
Do not blindly rerun the one-shot provision/accept commands over their existing
paths; inspect and use a separately reviewed fresh run scope.

This closes the previously missing **positive broker root-to-host-UID exec and
two-UID test-client IPC/private-file boundary** for these exact sources. It
DOES NOT close full D3B or the real Hermes Gateway boundary. The client used the
Gateway UID and actual broker protocol; it was not the Hermes Gateway process.

Next: implement the trusted Gateway network/mount projection while preserving
host identity, then qualify real Hermes Gateway with only the selected socket,
private-file access denials and unrelated network/IPC rejection. IPCv2 prepare
and project gates remain CLOSED until that implementation and acceptance exist.
A separate provider-dispatch gate must provision the broker's read-only access
to live Gateway state.db/epochs/grants and exercise dummy-provider budgeting,
replay/rebind and ACK-loss. Ping and an unchanged zero budget do not prove send
accounting or replay protection. No real model or production activation occurred.

## Reference material used for setup

Official Microsoft WSL import and per-distribution configuration documentation:
https://learn.microsoft.com/en-us/windows/wsl/use-custom-distro
https://learn.microsoft.com/en-us/windows/wsl/wsl-config
Official Ubuntu image/checksum directory:
https://cdimage.ubuntu.com/ubuntu-base/releases/noble/release/
These references explain the setup mechanisms, not this project's acceptance.

## WSL output representation

The first static scan flagged three UTF16 Windows WSL command outputs as binary. They were inspected: two Turkish success messages and the final distro list. Their UTF8 views are tracked alongside exact original bytes in wsl-output-lossless-transcoding.json (Base64, SHA256, round-trip verification). Unmodified raw copies also remain in ignored scratch. No scanner exception was introduced; native Linux JSON and syscall trace bytes remain unchanged. The first static failure is retained.

## Final regression and delivery

Fresh standard Windows regression: **2236 total / 2231 PASS / 5 SKIP / 0 failures /
0 errors**, exit0. Results were collected directly from unittest's result object.
The16 offline receipt-review controls are a subset of the full suite, not16 new
native launches. The native acceptance remains two real broker lifetimes and20
reviewed checks, with4 authenticated pings,8 private read/write-open denials and
8 positive owner-open controls. These overlapping counts are not added together.
All338 source/config/test hashes stayed unchanged during the full suite and were
rechecked afterward; the333 pre-existing sources were never modified. All57
installed product blobs match the source candidate and current development base.

The local static gate passes with2236 discovered tests after explicit lossless
review of the three UTF16 WSL outputs; no scanner rule was weakened. Discovery
is separate from executed tests, and local static PASS is not remote CI. Original
QA failures, executed-runner source, syscall trace and original native collector
FAIL remain preserved alongside the separate, strict reconciliation record.

All test/setup/cleanup operations are terminal. There is no running broker or
pending native acceptance. The new distro remains STOPPED with its disk retained
under ignored scratch; existing Ubuntu remains default/stopped. This local
commit contains only own QA tools/tests, evidence, report and status, not changed
product logic. Read Git HEAD for its exact identifier. No push or main update.
