# HYB-003: integrated components and native-engine boundary

## Merge inputs

- Reviewed stdio: c637380706232eb49f835b45da7da1f4fa3573a0.
- HTTP candidate: eb20b2e7559750db3c61f0b8450b393ae96f6368.

The integration uses its own worktree. Original worktrees, unpublished primary
checkout files and upstream submodule pins remain untouched. Seven duplicate
payloads had equal canonical Git content; Windows license CRLF was normalized
back to the recorded LF bytes. The union has ten files, including two licenses.
Both adapters import shared packages/upstream; config/components.lock.json and
scripts/verify_components.py are the only active provenance owners.

## Responsibility boundaries

The stdio scripted harness remains a protocol fixture. HermesRunsClient remains
a native /v1/runs client candidate; it does not own model execution, transcripts
or another scheduler. Never connect both as competing writers to one session.
The actual native test enters AIAgent through its public constructor and real
conversation loop; only HTTP model responses are scripted. A real read_file
result must be delivered back to the scripted provider before final output.

## Environment

Hermes dependencies were prepared using pm.build_environment with frozen source
inputs, no extras and no project installation. Home, profile, cache, temporary
files and tool store are isolated under the project runtime directory. The
experiment does not use existing model keys. Dependency preparation is separate
from runtime testing. No source lifecycle installer or user-profile migration is
run manually.

run_native_hermes_probe.py requires --source-workspace, --python and a fresh
--output directory. It never installs dependencies. Its worker refuses
non-loopback Python socket connects. This is a narrowly scoped benign test,
not a claim that Python audit hooks provide an operating-system sandbox.

## Evidence scope

Current results and blockers live in CURRENT-STATE.md; sanitized receipts live
under evidence/hyb-003. Legacy evidence remains historical and keeps its exact
original commit/count scope. Mock tests do not prove full M1, real OpenClaw
Gateway ingress, Hermes HTTP Gateway execution, production isolation, currency
budgeting, persistent memory transfer or autonomous goal selection.

## Actual native probes (Windows)

`file-read`: public AIAgent constructor -> real conversation loop -> native
read_file -> tool result in the next model request -> completed output. An
unpredictable marker written only to a fresh fixture file is asserted in that
real tool result. Two loopback model HTTP calls, one native read, zero inference
or paid-provider calls. No AIAgent, tool handler or context engine monkeypatch.

`budget-summary`: max_iterations=1 still makes one extra model call to summarize.
The real native turn remains completed=false with max_iterations_reached(1/1),
and exactly one read_file result is recorded. This is behavior characterization,
NOT acceptance of an API-request or monetary cap. The original false one-request
hypothesis is preserved as FAIL in budget-initial-hypothesis.json. That fixture
returned tool-only/empty summary content; native summary retry produced three
HTTP calls. A compliant text summary produces two. Pinned sources:
agent/turn_finalizer.py:124-195 and agent/chat_completion_helpers.py:2309-2363.
HYB-005 must reserve/account for summary, retry and auxiliary calls at the actual
model dispatch boundary; max_iterations alone cannot do that.

The first positive probe attempt was refused because its mock provider advertised
32768 context, below the source's 64000 minimum. The fixture now advertises131072;
the native guard was not removed. This says nothing about a real model's limits.

## Reproduce preparation and the native boundary

From this integration worktree, using Python 3.14 for native preparation:

```powershell
python -B scripts/prepare_native_hermes.py --source-workspace C:\Antigravity\AlazHarness --output C:\Antigravity\AlazHarness\runtime\hermes-new
# Add --apply to explicitly install the pinned dependencies into that NEW output.
python -B scripts/run_native_hermes_probe.py --source-workspace C:\Antigravity\AlazHarness --python C:\Antigravity\AlazHarness\runtime\hermes-hyb003-46cc\env\Scripts\python.exe --output C:\Antigravity\AlazHarness\runtime\native-read-new --scenario file-read
```

Preparation is dry-run by default and the plan path was checked to create no
files. The actual dependency build was executed through the same
pm.build_environment API before packaging the helper; the new helper's --apply
entrypoint has not been independently rerun. It uses no raw pip/uv mutation.
Every probe output must be new. The prepared environment from this session is
retained locally. Full ordinary CI does not run these opt-in native probes.

## Remaining acceptance

No full OpenClaw Gateway or actual Hermes /v1/runs endpoint has yet been qualified.
The next boundary is the native Gateway/SessionAuthority/API adapter with the same
scripted model, not another imitation HTTP server. Real engine/tool interruption,
crash-recovery, hard provider budgets, isolated-memory transfer and M2 remain open.
