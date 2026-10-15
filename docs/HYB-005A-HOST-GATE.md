# HYB-005A — one-use host dispatch gate

Status: IMPLEMENTED; final native and exact-commit CI evidence are recorded in
status.md/evidence/hyb-005a. This is a narrowly scoped admission boundary, not full
HYB-005 permission/token/currency acceptance or M1/M2 completion.

## Continuation and provenance

The existing branch alaz/hyb-005-host-gate-6f88 was resumed from main b8ff44f.
The two interrupted source drafts were preserved under the Git-ignored runtime
before editing; they were not discarded or replaced with a new scheduler. The
hook-boundary review from9766d5931f027b83495079fd642cb0ae14e6b3b7 was imported as
exact selected Git blobs, with its previous result scope unchanged. Its status
file was not substituted for this branch's live status.md.

Hermes pin eb75627faf532fa6ffbdae59a0d14b0b385fc780 remains unchanged.
config/host-gate/source-lock.json hashes five selected native boundary files:
SessionDB write ownership, platform registration and actual API admission paths.
A mismatch refuses binding. This is not whole-dependency or runtime attestation.

## Actual product boundary

HostGateClient.prepare({requestId,input,model}) calls POST /alaz/host/v1/intents.
It receives a one-use key bound to the exact body fingerprint, native profile,
API principal, runtime epoch, instance, expiry and persistent namespace. It then
calls POST /alaz/host/v1/dispatch through dispatch(permit). It never falls back to
POST /v1/runs if the plugin is missing, invalid, stale or inaccessible.

The normal native plugin loader invokes register(ctx), then the pre-freeze
platform factory attaches these routes to the existing APIServerAdapter. The
handler calls the actual adapter._handle_runs only after HostGateLedger.consume
returns from the native SessionDB._execute_write commit. There is no second
queue, transcript, agent execution loop, database or scheduler. HTTP forwarding
is a direct in-process native handler call, not a second network hop.

State rows live under alaz.host_gate.config.v1.* and alaz.host_gate.intent.v1.* in
native state_meta. Consumption and namespace counters change in ONE native write
transaction. State rows only describe issuance/dispatch, never native task success.
A consumed request cannot become issued again after a network error, exception,
unknown COMMIT reply, cancellation, process reopen or native replay-key pruning.

The client keeps immutable private input snapshots and only accepts permit object
identities it issued itself. This is convenience protection, not a replacement
for the server's permanent transaction. A new client cannot regain consumption.
At an uncertain request result the client returns retryAllowed=false; it never
resubmits or invents an accepted run ID. Existing HermesRunsClient status/resume/
reconcile are reused for read-only outcome observation. Explicit stop is separate.

## Defensive checks

Only authenticated literal local127.0.0.1 default-profile new-run requests are
supported by this server binding. Input+model are the only dispatch body fields;
keys, JSON types/size, duplicate JSON keys, bearer/header count, query strings,
profile/session headers, model allowlist, current runtime and database ownership
are validated. Readiness is not inferred from an API capability advertisement.

The installed extension refuses alternative native write paths, including raw
/v1/runs and chat-completions. Two native scope prefixes are not silently mapped.
Completed state and unknown execution are not made dispatchable by this plugin.
The existing read-only inspector and explicit operator closure retain their roles.

Issuance and spent counters are checked against ALL bounded retained intents in
the same transaction. Missing intent rows, missing namespace over history,
contradictory counters and foreign namespace values refuse instead of recreating
history. Closure records and the native replay-key database are checked without
calling the pruning lookup. A missing/corrupt store refuses; it is not recreated.

## Independent findings and preserved failures

QA890e identified two ledger defects in the initial draft: removing only a
consumed intent could recreate the same key, and an inconsistent issued count
could admit another key. The retained-history scan fixes both without weakening
the original failing tests. The first34/36 output remains separate from the
corrected36/36 run.

Two further client tests showed that a202 admission could carry contradictory
completed/partial flags or a non-text output. Both are now rejected as
invalid_host_admission without refund; initial10/12 and corrected12/12 records
are separate. Dispatch acknowledgement remains weaker than canonical outcome.

The first missing-plugin native probe correctly sent NO native task, but the
client labeled a plain-text404 as invalid_host_response. The negative-response
classification now preserves the HTTP status even when no JSON error is present.
It still requires JSON for successful responses and never echoes server text.
The initial failed assertion is preserved, not represented as a successful run.

## Verification and reproduction

Ordinary CI uses Python3.11+, Node24 and synthetic SQLite/loopback fixtures; it does
not install Hermes or aiohttp. The new native probes use the already prepared
project Python3.14 environment and native Gateway worker. In these probes only
the provider answers are scripted; plugin loading, HTTP routing, SessionDB,
SessionAuthority, AIAgent and read_file are real.

```powershell
python -B -m unittest discover -s tests -v
python -B scripts/ci_check.py
python -B scripts/run_native_host_gate.py --source-workspace C:\Antigravity\AlazHarness --python C:\Antigravity\AlazHarness\runtime\hyb-gateway-5a5c\prepared\env\Scripts\python.exe --output C:\Antigravity\AlazHarness\runtime\fresh-host-probe --scenario normal
```

Other explicit scenarios: missing-plugin, invalid-policy, lost-ack. Every output
must be a NEW project runtime directory. No dependency is installed by the probe.
The normal case includes ten separate clients attempting the same dispatch; the
lost-ack case drops the REAL202 response, then attempts reconnect from another
client. Positive cases reopen the same profile with a new native epoch and use
read-only status to retain the final result. These are graceful process reopens,
not new hard-kill/power-loss tests. Synthetic commit-failure tests have their own
scope and do not prove all physical storage behavior.

## Deliberate limits and next work

The bearer is a trusted LOCAL OPERATOR credential. There is no delegated-agent
credential, human approval UI, total-cost policy or malicious same-OS-user
sandbox. A party with the raw upstream credential can run unextended Hermes;
this package does not claim to change unextended native endpoints when its
plugin is missing. Safety for the Alaz host path is the dedicated URL with NO
fallback, plus server validation whenever that URL is actually installed.

A caller may create a genuinely new request ID, but must not relabel an uncertain
old action as new. This gate cannot infer semantic equivalence of different IDs.
The finite max_issued/max_dispatches budget is per retained principal namespace,
not a rolling rate, model call count or monetary limit. Rotating credentials,
restoring/deleting all state, or a hostile operator rewriting history is outside
this narrow trust model. Digests detect accidental inconsistency; they are not
signatures against a privileged editor. New namespace recovery requires review.

At-most-once HANDOFF is not exactly-once completion: if commit succeeds but native
admission never happens, the consumed permission stays spent. There is currently
no automatic refund/repair. History checking and later native admission across
separate stores are not one global transaction. Single native writer, no foreign
maintenance writer, no hot plugin unload and the qualified source version are
operational assumptions. GET/WebSocket/native side-effect surfaces outside the
Alaz client are not claimed to be a full service security perimeter.

Next HYB-005B: enforce model/tool permission and request/token/currency checks at
an actual non-bypassable execution boundary, including summary, retry and auxiliary
model calls. Plugin hook exceptions alone are explicitly insufficient (see the
imported boundary review). No paid model or autonomy loop begins at this checkpoint.

## Executed final-code result

Full local standard suite669/669 passed without skips or measured code drift.
Four final-code native scenarios passed: missing plugin, invalid policy, normal
and lost acceptance ACK. Positive cases had one admission, one actual read_file
result and two provider-fixture HTTP calls; the same-profile reopen added none.
Negative cases had zero admissions/messages/provider calls. Real inference and
paid calls were zero. QA48 standard cases are included in669; QA17 component HTTP
cases are a separate fixture scope. Exact-commit server CI is recorded after push.
