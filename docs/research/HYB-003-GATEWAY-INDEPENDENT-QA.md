# HYB-003-GATEWAY — Independent QA208f

Status: **9/9 actual HTTP refusal cases PASS**, with native GatewayRunner,
SessionAuthority and APIServerAdapter. This supplement owns tests only; it is
not a second executor or another product runtime. Primary implementation stays
on alaz/hyb-003-gateway-5a5c. Source Hermes commit:
eb75627faf532fa6ffbdae59a0d14b0b385fc780.

## Actual boundary

A fresh programmatic native GatewayRunner, canonical authority, real API adapter
and real aiohttp listener are created in an isolated profile. No Gateway,
authority or executor method is monkeypatched. A native local session is created
through create_local_session; HTTP /v1/runs must refuse to adopt that different
surface. The API is also proven to borrow the authority's same database object.
This QA is NOT the full start_gateway lifecycle. The primary integration runs
that lifecycle separately; its acceptance is not inferred from these refusals.

Nine cases: missing/wrong/Unicode authorization, oversized/space-containing
idempotency keys, native-session refusal and exact-key refusal retry, unknown
run status and unknown run stop. Every request leaves canonical admission,
in-memory run status and active run counts unchanged. Final state.db is read
with SQLite mode=ro after both worker processes are known to have exited:
zero admissions and tool messages, integrity ok. There is no model execution.

The parent uses the shared OwnedGatewayProcess OS ancestry + held process handle
helper because the Windows virtual-environment launcher and native worker have
different PIDs. A nonce/PID ready/continue barrier confirms ownership while the
worker is live. Parent exit alone is insufficient; native-handle exit is also
required. The worker's receipt is written only after native API/worker/database
cleanup completes. These processes were NOT intentionally killed in the accepted
run; no crash-resume guarantee is claimed.

## Dependency and network boundary

The earlier direct-agent environment lacked aiohttp. A new isolated environment
was prepared by the pinned Hermes pm.build_environment with frozen inputs,
no_install_project and the sms extra (that pinned extra declares only aiohttp
3.14.3). This did NOT activate an SMS service. Existing profiles and global
Python were not changed. The runtime probe itself never installs packages.

No real provider secret is inherited. The provider URL is a closed loopback port9
which the Python audit hook also refuses; actual HTTP targets the selected API
port only. One Windows asyncio self-pipe connection is recognized by its exact
socket.py socketpair/_fallback_socketpair stack. This hook is not an OS sandbox.
The first instrumented runs failed on that runtime self-pipe, not on a model call;
the specific classification was corrected and the old logs remain preserved.
Native SQLite chose journal_mode=DELETE; no WAL/powerloss claim is made here.

## Independent persistence corroboration

The primary trial-03's captured launcher/native-exit and shutdown receipts were
read, then its retained state.db was inspected read-only. Exactly one canonical
API admission was terminal/completed with the same run/session/admission IDs as
the HTTP result. Exactly one real read_file message held the unpredictable marker;
the marker was absent from the user message. The recorded final assistant output
matched HTTP output. There were two scripted model HTTP requests and no inference.
This is retrospective independent corroboration, not a rerun of the lifecycle.

## Evidence and reproduction

Tracked sanitized evidence: evidence/hyb-gateway-qa/native-refusals.json,
native-record-corroboration.json, dependency-preparation.json, initial-failures.json.
Raw profiles/logs remain ignored under runtime/hyb-gateway-qa-208f.

```powershell
python -B scripts/run_gateway_refusal_qa.py --source-workspace C:\Antigravity\AlazHarness --python C:\Antigravity\AlazHarness\runtime\hyb-gateway-qa-208f\prepared-http\env\Scripts\python.exe --output C:\Antigravity\AlazHarness\runtime\gateway-refusal-new
```

Output must be new.16 offline receipt/reader tests are separate from the9 actual
HTTP cases, including missing/duplicate evidence rejection and explicit SQLite
connection-close verification. Standard CI runs offline tests only.

This closes only the measured no-admission HTTP refusal boundary. Paid inference,
all native ingress surfaces, hard currency budgets, process isolation, external
effect exactly-once, memory transfer, crash recovery and full M1/M2 remain open.
The main integration's loss-of-ACK/cancellation results must be read separately.

## Final supplementary acceptance

The full local offline suite passed321/321, no skips, no measured code drift.
root-validation.json and root-unittest.txt are independent actual-run receipts.
This standard count already includes the16 new refusal-receipt tests.

The primary's six accepted runs (normal/lost-ack/stop, each twice) were separately
read through the declared contract and directly from their retained databases.
Each has exactly one matching canonical admission and persistent idempotency row.
Normal/lost-ack have one native read_file result and two model HTTP requests;
stop has zero tool results and one model request, with native interrupted outcome.
The user prompt never contained the unpredictable fixture marker. Native records,
client identity, shutdown and collected-process receipts agree. See
six-run-store-recheck.json; these are NOT additional executions or restart tests.
