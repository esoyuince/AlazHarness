# HYB-005D2 independent QA d65f — IN PROGRESS

Primary247a owns product/branch/publication. This reviewer only adds dedicated
QAD65F tests, evidence and this report; no second native runtime or integration.

## Admission, cancellation and result acceptance checklist

The real registry call must reach the isolated executor AFTER native admission
identity, scope, active generation, live policy and budget validation. Data in
model arguments or unverified session_id is not new authority. Denied/missing
backend must not call a local file-handler fallback. No second ledger or queue.
A tool-return record is not independent proof of successful requested effect.

Native tools/interrupt.py is thread scoped. The executing thread and its
acting_for_tid context must be respected; a polling helper must not check only
its own thread. Cancellation of one task cannot stop a sibling. A cancel before
admission must prevent starting; an unknown Docker start/attach/cleanup must stay
unknown rather than default-zero success. No retry or refund from uncertainty.

The full pinned read_file handler has tracking/redaction/pagination semantics;
replacing it with a Python Path.read_text imitation is not native parity. Test
actual bytes, Unicode/pagination, errors and response framing. If source is
staged into a capsule, exact dependency/source/license pins must be preserved.

Previous D1 six Docker checks and1062 tests are not D2 acceptance. Native launch,
synthetic ports, source-only checks and retained-record rereads stay separate.
This initial plan has no test result. No paid/provider invocation or setup.

## Actual native interrupt observation (8 cases)

Loaded the unmodified pinned tools.interrupt module in the already prepared
Hermes interpreter with an explicit credential-free private environment. No mock
interrupt or utils module was installed. Real threads and copied ContextVars
confirm the current-thread and acting_for_tid semantics. All8 expected observations
matched; no Gateway, file tool, container or provider was invoked.

Important difference: is_interrupted() respects acting_for_tid, but
run_if_not_interrupted() checks ONLY the current thread's native flag. An acting
worker can see is_interrupted()==true and still have the latter invoke its
callback. This is a source behavior observation, not proof that the new D2 adapter
has that bug. Do not use the latter as the sole cancellation gate on a copied
worker context. Source bytes and script were stable; all owned threads exited.
Evidence: native-interrupt-observation.json. Repeatable observer:
scripts/qa/native_interrupt_contract_d65f.py.

## Initial actual-bridge regression suite:23 PASS /7 FAIL

Thirty tests ran on the real isolated_read/ExecutionLedger code with temporary
SQLite stores and explicitly synthetic registry/native-handler/Docker ports.
No real Docker or Gateway was used for these cases. Source was unchanged during
execution: isolated_read caa5c966..., test722b7876...; exit1, seven assertion
failures and no setup errors. Evidence initial-run.json and initial-tests.txt.

### QA-I01 — quarantine does not revoke a reserved ticket (2 cases)

After a read ticket is reserved, quarantine is set either before invoke or
between original-handler entry and the shell execution. check_call reads
fresh._state but ignores its quarantined flag. Both cases still reach the
synthetic executor. Existing ledger.claim prevents NEW claims in quarantine,
but an already-held ticket is not revalidated for this revocation. Require
quarantined=false at each real execution/cancellation authority check.

### QA-I02 — admission identity/generation not frozen (3 cases)

An active admission with an arbitrary non-hex admission_id passes. During an
invocation, replacing the admission_id or incrementing its generation also lets
the same reserved ticket continue. validate_admission currently returns a row
that is discarded by check_call. Bind a validated admission ID/generation to the
invocation at entry, then compare it in subsequent checks; do not merely check
that some generation is positive. Mutations are confined to synthetic test DBs,
not a claim that production records have been changed or a remote exploit exists.

### QA-I03 — contradictory backend success/exit states (2 cases)

completed+exit1 and tool_failed+exit0 are both accepted by the new bridge. The
existing runner aims not to emit them, but the consuming boundary must reject
contradictory evidence rather than converting it into a native read result.
Keep unknown/refused/cancelled/timeout/truncated results non-successful.

The assertions and initial failure receipt are preserved unchanged. Primary247a
owns corrections; QA has not edited product or the prior D1 implementation.

## Native dispatch signature mismatch (source-level)

Pinned model_tools._execute_tool(827-839) calls registry.dispatch for read_file
with task_id, session_id and user_task. It does not pass parent_agent. Current
isolated_read.invoke requires parent_agent.is_interrupted; primary unit fixtures
supply this extra field and therefore do not characterize the real native call.
This must be resolved at the actual native contract, not by adding a made-up
keyword solely to the acceptance probe. Native tools.interrupt thread/acting-
thread state is available and characterized above. Real complete Gateway binding
has NOT been confirmed by this source observation.

## Actual dispatcher observation and its explicit limitation

Loaded the real pinned model_tools and called its _execute_tool with actual
approval ContextVars and a recording registry.dispatch port. The recorded kwargs
are exactly task_id/session_id/user_task: parent_agent is absent. The task/session
IDs and tool-call ContextVar match, and ContextVars are restored afterwards.
No native tool handler or Gateway/provider was invoked.

The experiment's overall result intentionally remains FAIL: native module imports
attempted seven subprocess launches, all blocked by the experiment's audit guard.
There were no actual subprocess, network, model or container executions, but this
is NOT a side-effect-free import acceptance. It does corroborate the observed
selected dispatch signature under this blocked-import environment. Do not relabel
that receipt as a fully clean native test. The native interrupt-module8-case
observation above was a different, independently completed experiment.
Evidence native-dispatch-observation.json; script native_dispatch_contract_d65f.py.

## Seven regressions fixed in product and independently rechecked

Primary corrected isolated_read.py. The SAME30 tests, including the same
fixture and seven originally failing assertions, now pass30/30 exit0/drift0.
Test SHA722b7876... is unchanged. Product hash and full log are preserved in
recheck-run.json/recheck-tests.txt. Quarantine revokes reserved tickets; valid
admission ID/generation/payload/epoch are frozen at entry; contradictory backend
status/exit values are rejected. The parent_agent/native cancellation binding
issue remains a separate pending native integration item. No Gateway/container
was started by this recheck, and no original failure has been erased.

## Dispatcher-compatible cancellation bridge —14 additional offline checks

Primary added _NativeInterruptSource. With no parent_agent argument it binds
native approval session/tool-call context, captures current and acting-for thread
IDs, and queries both captured native flags even when another thread polls later.
The previous one-thread-only helper is not used as the sole stop gate.

Fourteen actual bridge tests with explicitly synthetic native context ports pass
14/14 exit0/drift0. Three combine the same real admission/ledger/invocation code
with the exact task_id/session_id/user_task dispatcher shape (no fabricated
parent_agent). They confirm a valid call proceeds, acting-thread cancellation
prevents the executor, and wrong native scope blocks it. Sibling cancellation,
context replacement, cross-thread polling, sticky cancellation and authority loss
are separately checked. These14 are offline contracts, not fourteen native
Gateway runs. Original30 tests remain byte-identical. No full D2 acceptance is
inferred before the real pinned registry/file-handler/container path is exercised.
Evidence cancellation-run.json/cancellation-tests.txt.

## First full suite: tests pass but the snapshot is NOT_ACCEPTED

1143 tests ran with exit0 and no skips, but primary changed host-gate-client.mjs
and host_gate_plugin.py during the run. full-standard.json/.txt retain the exact
measurement and mark NOT_ACCEPTED. This is not stable final-code acceptance.
The44 QA tests are inside1143; they must not be added again. All targeted source-
stable regression results above remain separately scoped, not promoted to final CI.

## Required-isolation client —8 independent loopback contracts

The new requireIsolatedRead mode was checked through the real HostGateClient and
fetch against an independent local HTTP fixture. Eight cases pass with stable
source: untyped option, conflicting disabled execution, missing isolation,
incorrect backend, boolean-as-version, missing execution gate, capability
downgrade between prepare/dispatch, and one permitted dispatch with both required
headers. No test falls back to raw /v1/runs. Reusing the permit does not resend.
These8 are included in future standard discovery and are NOT native Gateway runs.
Evidence client-run.json/client-tests.txt. Our new QA tests now total52 unique
offline cases (30 bridge+14 cancellation+8 client); the old1143 unstable run did
not yet include the new eight cases and must not be relabeled as final proof.

## Second full suite also retained without final-source acceptance

The second run executed1163 tests, exit0/no skips. Its192+ measured file set
changed again: isolated_read.py and execution_model_fixture.py were edited during
execution. second-full-standard.json/.txt therefore remain NOT_ACCEPTED; no
assertion was relaxed. A final full pass is required once implementation and
native probe files are stable. This reviewer will not keep rerunning discovery
while primary actively changes the measured source.

## Linux native preparation and first integrated trial (not accepted)

The first native frozen-PM environment preparation failed because the source
transfer omitted pm/uv.lock. Read-only diagnosis identified the exact nested
file; primary then transferred it with its original hash735e1e98... and kept
frozen=True. The second private environment preparation succeeded (exit0),
without system package modification or model calls. This is environment setup,
not a successful native tool run.

The first actual integrated trial reaches native Gateway ready, but the required
client returns host_http_404. Source and private stderr agree: the probe put
settings at plugins.<id> instead of the actual native PluginContext path
plugins.entries.<id>.settings, so explicit_host_policy_required prevented plugin
registration. The existing B probe already demonstrates the correct config shape
including allow_tool_override=True. No automatic raw host fallback took place;
the native process exited normally, but the trial remains FAIL. QA only read
these receipts and source; primary owns the corrected probe and new trial.
