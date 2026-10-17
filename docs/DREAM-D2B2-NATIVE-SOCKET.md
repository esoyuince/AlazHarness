# DREAM-D2B2-NATIVE-9C31 — scoped Linux Unix-socket acceptance

Date: 18 October 2026.
Branch: alaz/dream-d2b2-native-9c31.
Base: 7991172a6fc1ac4ec64eb2cdf3cf653bf51f2140.

## Result and its precise limits

Three real Linux broker IPC scenarios passed. This is **NOT full Hermes Gateway acceptance and NOT real model learning**.

The test exercised unmodified product ProviderBrokerServer and ProviderBrokerClient,
PermitVerifier, signed Unix-socket envelopes and peer credential checks, the
existing native SQLite ExecutionLedger, request-view preparation and broker
response metadata, Dream D1, D2A review, D2B1 sealed paired plan and D2B2
two-arm trial validation.

A separate broker OS process communicated over a real chmod-restricted Linux
Unix socket with a local native SQLite test owner. A real 127.0.0.1 HTTP
server returned SCRIPTED outputs. The broker process used a **test-only
stdlib HTTPConnection _upstream override**, because the installed WSL
environment lacks aiohttp. The production aiohttp upstream implementation
was NOT executed. The Hermes web Gateway, actual native source-reading
Docker tool and a real inference backend were also NOT executed. The
initial terminal source was created by a synthetic test fixture. The
D2A acceptance decision was scripted, not an attested human review.

The broker and origin received randomly generated per-run credentials
without reading user production profiles. No external model/paid API call,
scheduler, new database, autonomous behavior, active memory write, or
additional execution permission was introduced.

## Three observed runs

| Scenario | Origin calls | Trial result | Saved result arms | Broker lifecycle |
|---|---:|---|---:|---|
| normal | 3 (Dream, baseline, candidate) | completed | 2 | exit0, socket removed |
| candidate-disconnect | 3, third response disconnected | unknown | 1 | exit0, socket removed |
| review-revoked | 2, review revoked during baseline | unknown | 0 | exit0, socket removed |

All three native broker processes exited cleanly with zero active requests,
their sockets removed and private Linux temporary profiles deleted. Each
origin request's own raw-byte SHA256 matched the existing request-view
digest, along with the corresponding durable provider claim and egress
grant. Shared budget reservation totals were 3, 3 and 2 respectively.

In the normal run the old signed grant was replayed over a second real Unix
connection and refused without a fourth origin request. The broker counted
three physical origin HTTP attempts, three responses, one replay refusal.
The local scripted scores were 8 of 12 without the lesson and 12 of 12
with it, **programmed by the origin**. This is not an independent finding
that a model learned anything.

In candidate-disconnect, the third physical HTTP request was observed but
had no returned response. The trial remained UNKNOWN and preserved only
the baseline answer evidence; no blind retry or refund occurred. In
review-revoked, the candidate-arm HTTP request was never sent; the trial
stayed UNKNOWN even though Dream and the baseline HTTP response had
been observed. No candidate was promoted to active memory or skill.

## Program and public evidence

The Linux-only opt-in runner is:

    scripts/qa/native_d2b2_linux_socket.py

The three original output reports are retained unmodified:

    evidence/dream-d2b2-native-9c31/normal-initial.json
    evidence/dream-d2b2-native-9c31/candidate-disconnect-initial.json
    evidence/dream-d2b2-native-9c31/review-revoked-initial.json

The default read-only receipt tests are in:

    tests/test_dream_native_broker_receipts.py

Those 12 JSON custody tests do **not** constitute 12 more native runs or
an independently signed audit. Public JSON includes only counts, hashes,
trial status, budget counts, scenario and process cleanup flags; private
profile, request body, original file, signing key, oracle key and bearer
are not published. The test checks no raw request body is in the report.
Private source files and memory/skill sentinels remained unchanged.

The opt-in script creates an isolated ephemeral /tmp profile for each
run and accepts output only to a **new file under this repo's evidence
directory**. Any new run is a separate experiment and must use a new
filename, not overwrite an old receipt.

WSL manual example (use a new filename):

    wsl.exe --exec python3 -B /mnt/c/Antigravity/AlazHarness/scratch/worktrees/dream-d2b2-native-9c31/scripts/qa/native_d2b2_linux_socket.py --scenario normal --output /mnt/c/Antigravity/AlazHarness/scratch/worktrees/dream-d2b2-native-9c31/evidence/dream-d2b2-native-9c31/normal-next-unique.json

Other accepted scenarios are candidate-disconnect and review-revoked.

## Known gaps — NOT RUN

WSL Ubuntu Python is 3.12.3 and all relevant Alaz Python modules import
successfully; however Linux aiohttp, Linux Node, Docker, checked-out vendor
Hermes source and prior prepared native Hermes manifest were not present.
No system packages, container images, user services, credentials or personal
profiles were installed or modified to overcome these missing prerequisites.

- Full real Hermes Gateway + production aiohttp broker: **NOT RUN**
- Production broker external egress/OS identity boundary D3B: **OPEN**
- Actual remote model, tariff/token and response provenance: **NOT RUN**
- Genuine improvement on independent new tasks: **NOT RUN**
- Permission promotion and active memory/skill writes: **DISABLED**

The next acceptance should use a fresh source-pinned Linux native Hermes
environment with its real aiohttp, Node and Docker dependencies, isolated
credentials, restart/lost-ack checks and explicit tool/OS/network boundaries.
Run only a scripted localhost provider first, then evaluate whether bounded
real-provider/model experiments satisfy the user's budget and safety gates.
Do not count these Python broker IPC passes as Hermes Gateway passes.

Exact full-test counts, code/test source hashes, root CI and Git publication
must be recorded separately rather than inferred from this report.

## Accepted offline/full root checks — 2026-10-18T01:57:03.892919+03:00

Three real Linux Unix-socket/subprocess cases PASS;12 read-only custody
tests included ONCE in1848 full Windows offline unittest. Full1848/1848
PASS exit0,skip0;258 measured source/test/config files unchanged.
Root static gate PASS,1848 discovered (not additional execution),
1205 checked root files,2 gitlinks. No paid/model or native Hermes Gateway.
Exact logs, source SHA and output counts in evidence/dream-d2b2-native-9c31.
Git branch CI is verified only after an actual exact-source publication.
