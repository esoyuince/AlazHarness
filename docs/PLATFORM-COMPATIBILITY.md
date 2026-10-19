# AlazHarness platform compatibility — scoped engineering matrix

Last updated: 19 October 2026. ADR-0004 is the architecture decision.
States PLANNED, CANDIDATE, MOCK_TESTED and NATIVE_ACCEPTED are NOT interchangeable.

| Host/runtime | Control plane | Guarded execution target | Current status |
|---|---|---|---|
| Windows x64 | Native Node24 scripted fixture; read-only inspector tested | Explicit verified WSL2 Linux x64 guest | Host/guest bridge NOT IMPLEMENTED; guard D3B PARTIAL |
| WSL2 Linux x64 guest | Linux Node24 PLAT-001 inspector tested | Linux x64 projected broker and worker | D3B scoped PARTIAL; two host UID NOT ACCEPTED |
| Linux x64 native | Planner simulations exercised | Same-host Linux x64 isolated worker | CANDIDATE; full D3B NOT ACCEPTED |
| Linux ARM64 | Route simulation only | Future ARM64-specific confinement | NOT IMPLEMENTED / NOT TESTED |
| macOS Apple Silicon ARM64 | Future Node coordinator, route simulated | Approved remote Linux x64 or proven Linux ARM64 VM adapter | NOT IMPLEMENTED / NO PHYSICAL MAC TEST |
| macOS Intel x64 | Future Node coordinator, route simulated | Linux x64 VM or approved remote worker | NOT IMPLEMENTED / NO PHYSICAL MAC TEST |
| Windows ARM64 | Route simulation only | Future ARM64 WSL2 guest or remote | NOT IMPLEMENTED / NOT TESTED |

## Negative guarantees

- No automatic WSL invocation, VM creation, remote connection, model,
  token spend, provider request, privileged host command, account change
  or daemon installation.
- Linux Node process.platform inside WSL is a guest and not a Windows
  security boundary. WSL2 classification does NOT imply acceptably
  isolated host files, socket, kernel or provider spend.
- No parser-supplied kernelAttested/realHostUidIsolationAccepted flag
  or fabricated route plans authorize execution.
- Scripted-mock is a development fixture and not a native Hermes real
  Gateway or complete operating system sandbox.
- Nothing falls back to less isolated or unconfined host execution.

## Safe developer CLI examples

These commands inspect and test; they do not execute a model/agent.

~~~sh
node scripts/inspect_platform.mjs
node scripts/inspect_platform.mjs --mode=guarded
node scripts/inspect_platform.mjs --mode=guarded --require-accepted
node tests/node/platform-cases.mjs all
python -B -m unittest discover -s tests -p test_platform_routing.py -q
~~~

The require-accepted guarded command MUST exit 2 (REFUSED) in PLAT-001,
including on Linux x64 and on a Windows host with WSL2 installed.

## Future native acceptance

A new platform adapter needs a uniquely owned run/session ID, single
scheduler, broker budget authority outside Gateway writes, exact native
principal/IPC/network and filesystem boundary, and an independent
host/guest endpoint and process-lifecycle acceptance. Reconnect only
observes unknown prior effects. No silent retry, unguarded fallback,
credential export or budget reset. Real provider and M1/M2 remain
independent later gates.

Next: PLAT-002 Windows/WSL2 guest bridge tests without altering host
configuration. D3B-HOST-PRINCIPAL-001 and full D3B remain separate.


## PLAT-001 19 October native read-only evidence

Stored in evidence/plat-001-19oct:
- windows-inspector.json: observed real Windows win32/x64 host;
  guarded route windows-wsl2-bridge-pending and NOT_ACCEPTED.
- wsl2-inspector.json: observed real Linux x64 WSL2 guest;
  guarded route linux-x64-wsl2-guest-candidate and NOT_ACCEPTED.
- windows-node-cases.json: 27/27 actual Node scenario assertions.
- wsl2-node-cases.json: 27/27 actual Linux Node scenario assertions.
- summary.json: 5 current-source normalized Git-LF SHA256 values,
  zero real model/provider calls or privileged actions.

This is native *read-only classification and offline tests* only.
The guest and host inspections do not prove production readiness or
a complete D3B isolated Gateway.

## PLAT-001 full local regression

Windows Python full root regression: 2,096 tests discovered/executed,
exit 0; five Linux-only skips, 171.127 seconds. This runs the new
platform unit tests and all existing mock/broker/gate test contracts;
it does NOT native-test production macOS, VM, WSL bridge or real model.
Log is evidence/plat-001-19oct/full-standard-windows.txt and its
SHA-256 is included in evidence/plat-001-19oct/summary.json.

Final staged-root static gate: PASS, 2,096 tests discovered,
1,503 tracked files checked, two upstream gitlinks preserved, exit0.
This is not a full native sandbox or model/provider acceptance.

## Exact code commit and CI observation

Published on origin/alaz/platform-routing-001-19oct:
b0178b58714871c63a37ecc3a9af7972e45699a5.
Parent remains 46766bef55e0fb3f3a93dfb1356536400ba2b4d7.
GitHub alaz/local-ci: **SUCCESS**, status id 56702830465 at
2026-10-19T15:26:59Z. Its source manifest has 5 exact matching Git
source blobs. Windows full 2096 tests exit0 skip5, two 27-case
Windows/WSL2 Node read-only suites PASS. No model/guard activation,
real Mac native test, remote dispatch or whole M1/M2 certificate
follows from this status. Follow-up documentation CI is separate.
