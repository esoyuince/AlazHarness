# HYB-005B continuation and qualification — 16 October 2026

Status: IN PROGRESS. Existing branch alaz/hyb-005b-execution-0d37 was resumed by
3723 after the old lane expired. This is not a new implementation branch or a
second independent reviewer. Prior QA3193 results retain their original scope.

## Custody and interruption

Forty modified/untracked files were copied byte-for-byte under the ignored
runtime/hyb005b-resume-3723/pre-resume tree before new changes. Thirty-two legacy
root files remain excluded from this delivery. The old state log is preserved in
docs/history/2026-10-16-STATUS-BEFORE-HYB005B-RESUME-3723.md. Live project process
inspection found no surviving earlier native test. Old owner receipts returned
RESULT_UNAVAILABLE; retained files are not inferred to contain missing output.

interruption-inventory.json separates seven failed prior observations, two
incomplete profiles and the not-run unknown-price case. No prior profile is
reused or repaired. Initial compile/401/drift failures remain failures.

## Startup versus execution acceptance

A new sequential cold start still exceeded the ORIGINAL70-second readiness
budget. Its two captured stacks progressed through native Python source imports
and compilation; no model HTTP request happened. Both owned process handles
exited and an exit-observation.json was retained. This is not evidence of a
provider-budget or tool-policy failure, and it does not pass startup performance.

The launcher now accepts an explicit bounded1..180-second readiness budget,
default70 unchanged. The continuation's functional scenarios request180. This
does not change upstream code, native job lifetime, model request deadline,
iteration limit, billing reservation or safety assertions. Startup duration and
chosen bound must accompany every successful record. There is no new70-second
cold-start acceptance claim. No cache/antivirus/service or personal profile
setting was changed.

## Evidence hardening

The existing launcher persists owned exit records even when readiness fails.
Probe program hashes cover core workers, owner helpers, host/native clients and
policy manifests. Node/SDK output must match the current private nonce. The SDK
retry scenario must specifically report provider_attempt_limit, not any generic
403. Unknown-price must see the missing guarded endpoint404 rather than treat a
connection error as a successful policy rejection. Wire records include tool
choice and tool-presence for summary-path inspection.

Product enforcement bytes were not changed during this continuation's initial
qualification. Tests run serially so another native process cannot compete for
the same measured source or confound process reaping. Parallel standard tests
are not started while the native baseline is being established.

## Limits

The executed transport supports one configured loopback chat-completions provider
and one default profile. Proxy buffering is not low-latency streaming; cancellation
may leave charged exposure. Integer micro-USD values are conservative reservations
under explicit fixture ceilings/rates, not verified invoices or tokenizer counts.
The .txt path allowlist, link/size checks and native file wrapper are not an OS
sandbox, arbitrary-format content validation or protection from a hostile same-
process actor. All remote providers, unconfigured auxiliary paths, delegated
credentials, actual-price qualification and irreversible-write effects remain
separate gates. Successful scoped probes do not close all HYB-005 or M1/M2.

## Additional startup observations (historical failures preserved)

The explicit180-second diagnostic run became ready in140.671seconds, then its
60-second task-observation limit expired while native SDK code was still loading.
It is a FAIL with one provider request, not an execution-budget PASS. The native
owner subsequently entered shutdown and rejected further work; no bypass added.

Preloading only the installed OpenAI class before Gateway construction separated
that SDK loading from task time. No client was constructed and no model request
was made by the preload; its nonce/PID/timing receipt is retained per generation.
That first full task completed with two provider calls and a real read, but its
second process exited with Windows code0xC0000005 during a truncated periodic
faulthandler traceback. Causality is not established. Overall result remains FAIL.

The final serial batch runs without the OPTIONAL periodic faulthandler thread.
It retains the parent OS process handles, bounded startup180, task observation60,
provider request30 and native shutdown checks. Source/product code is unchanged.
The default legacy startup remains70 and unrelated native probes do not preload
SDK classes unless their caller explicitly opts in. No antivirus, system-wide
cache, upstream source, interpreter or installed-package configuration changed.

## Post-run verification

scripts/verify_execution_receipts.py independently reopens each retained SQLite
store read-only after recorded process exits and compares admissions, transcript,
provider/tool claims, seals and full fixture reservations. It checks current code
hashes and owned native shutdown receipts. This is retrospective corroboration,
not a new independent agent review or extra native execution. The20 offline
process-evidence rejection tests belong inside the final standard test count.

Reproduction uses run_native_execution_gate.py with --ready-timeout-seconds180.
Final profiles are runtime/hyb005b-resume-3723/final-serial-<scenario>. No case's
PASS is inherited from another source version or startup mode. The review branch
must not claim general HYB-005/M1 acceptance even if these scoped checks pass.
