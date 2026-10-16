# HYB-005D1 — Linux isolated tool process prototype

Status: Linux tool-process prototype published; exact-code standard CI1062/1062 PASS.
Native Docker6/6 and Windows strict-network NOT ACCEPTED remain separate scopes.
Base: fadb48acf6ada154497ec7f88b612b0e0fbb54e0. This is the first bounded
HYB-005D slice, NOT full credential/egress isolation of the Hermes runtime.

## Delivered boundary

`packages/claw-hermes/isolated_tool.py` implements ToolSandboxPolicy,
IsolatedToolRunner, capsule validation and actual-container pre-start checks.
It is a trusted operator-facing backend primitive, not an agent permission API.
The original Hermes Gateway, provider gate, budget ledger, read_file registry,
host dispatcher, report module, source pins and transcript writers are unchanged.
No task queue, extra database, agent engine or autonomous scheduler was added.

Only the dedicated staged capsule enters a one-shot Linux container. The capsule
must be a proper child of an operator-selected root, contain program.py, and fit
bounded file/count/total size rules. Symlinks, hardlinked files and special entries
are refused. The bind mount is read-only. Existing provider/operator credentials,
state stores, user HOME, SSH keys, Docker socket and other host paths are not
mounted. The operator must never stage a secret as an allowed input file.

The image must already exist and be pinned by content ID. There is no image pull,
image build, registry login, installed-package fallback or execution on the host
if Docker is unavailable. Image review remains an operator responsibility. The
existing node:24-bookworm image used in the experiment is a cached test image,
not a new universal supported agent distribution or a supply-chain attestation.

| Enforced container setting | Observed test boundary |
|---|---|
| network=none, no published port | Isolated loopback only; host service and IPv4/IPv6/UDP probes denied. |
| UID/GID65534, cap-drop ALL, no-new-privileges | Native process observes empty capabilities and cannot setuid0 or create a raw socket. |
| Default Docker seccomp, private PID/mount/cgroup namespaces | No unconfined override; child process inherits the network restriction. |
| Read-only root and capsule; private tmpfs | Input reads work; capsule/root writes fail; bounded private scratch works. |
| CPU0.5, memory128MiB, pids32 in default policy | Exact Docker inspect and real cgroup values checked; not a memory-OOM benchmark. |
| Environment rebuilt with env -i | Only fixed HOME, PATH, locale reach the tool; parent canary/proxy/Docker endpoint absent. |
| Bounded per-stream raw capture | Excess output is truncated and does not become successful tool output. |
| One-shot identity and explicit cleanup | Exact created ID/name/owner label checked; no prefix cleanup or automatic replay. |

The program is not started until Docker inspect matches the fixed plan. A
random name and owner label establish custody of this attempt. Cleanup is
restricted to that exact container. On timeout/cancel, the owned container is
killed, waited for, observed with Running=false/Pid0, then removed. The runner
retains a private ownership/plan/exit/result record in the supplied receipt dir.
It never deletes the staged source capsule or another container.

`completed` means an observed zero-exit tool process, NOT independent goal
achievement. `tool_failed`, `timeout`, `cancelled`, `output_limit`, `refused`
and `unknown` remain different. An unstarted container's default zero exit is
not success; a lost attach status is unknown even if another field looks clean.
No result grants permission to repeat an earlier effect. No provider is called
by this backend primitive.

## Actual evidence and negative controls

The first real Docker run passed six narrow scenarios. Subsequent simulated
Docker transport tests caught TWO incorrect success classifications: a failed
start left a created container with default exit0; a lost attach status disagreed
with zero container exit. The exact failing tests were retained. Product code
now distinguishes neverStarted from executed and treats attach disagreement as
unknown. The same tests plus initial policy/inspection/capsule contracts pass65.
The first raw Docker receipt is historical, not used as final-code acceptance.

The final-code real Docker experiment creates six new containers: two filesystem/
network/credential checks, one timeout, one cancellation, excessive output and a
controlled tool exception. Both timeout/cancel programs spawn a real child before
termination. The host-only readable synthetic canary remains unchanged, and a
host listener is positively reachable from the host but not from either container
or its child. External-address probes use documentation ranges, not a real paid
service. No Python audit hook is the enforcement mechanism.

Raw server-owned private artifacts remain under the fresh test directory; only
sanitized evidence is copied into the repository. No real account key is used.
Linux adapter implementation and Docker validation are by the same session;
no separately delegated Linux reviewer is claimed. The independent Windows
QA4023 feasibility package is a different scope and is retained alongside it.

## Reproduce without implicit installation

```bash
python3 -B scripts/run_isolated_tool_probe.py --root /tmp/alaz-fresh-isolation-test --image sha256:64af3819f9275802414d7cdc38c27e9d82bd564dec4d4da87d008255d36c63b4 --sudo
python3 -B -m unittest discover -s tests -p 'test_isolated_tool*.py' -v
```

The first command is OPT-IN real Docker execution and needs a trusted Linux
host, its existing daemon and the named cached image. Use a fresh test root.
The second command is65 offline unit/transport-contract cases; it does not
start Docker. Full standard CI includes those cases but not the native Docker
probe. The native probe and ordinary alaz/local-ci are different evidence.

## Source reuse versus new integration

OpenClaw's pinned Docker backend already keeps its Gateway on the host and
isolates tool execution. We reviewed its mount/credential/network validation and
lifecycle source before choosing this boundary. Those files have native registry,
authority and configuration dependencies; they were NOT transplanted or claimed
as executed here. Existing Docker provides the actual OS isolation primitive;
this file is the thin, narrower Alaz adapter with no second sandbox engine.
Reference paths/hashes and official documentation are in
`evidence/hyb-005d/source-reference.json`. The existing hybrid source selections
are unaffected. Hermes DockerEnvironment remains a candidate for later binding;
this packet does not pretend to have moved its live file handler.

## Remaining gates and threat limits

The host kernel, Docker daemon, reviewed image and privileged operator are
trusted. This is a container boundary, not a VM or protection from a compromised
host administrator. Host-side capsule replacement/TOCTOU and arbitrary staging
of secrets are not solved by a read-only bind. Docker defaults inherited from
a trusted daemon/image are not a universal cross-daemon security attestation.
No penetration-test completeness or protection from unknown kernel exploits.

The parent runner must remain alive to enforce the wall timeout. A killed host
controller/host power loss can leave a Docker container alive; its ownership
record is retained, but automatic takeover/recovery is NOT implemented. Unknown
create/start outcomes are not replayed. Parent crash recovery, daemon disconnects,
resource-exhaustion stress and Windows-local execution require separate gates.

**HYB-005D2 remains open:** bind a qualified native Hermes tool call to this process
after canonical admission, policy and budget checks; preserve truthful tool
output and cancellation propagation; prove no host-execution fallback. Then
separate provider credentials and mandatory egress authority for the model-call
path. The current Gateway still runs on the host and is not made credential-safe
against arbitrary code in its own process by adding this optional module.
Full HYB-005D, general HYB-005, M1/M2 and learning-transfer remain OPEN.

## Integrated Windows feasibility evidence (NOT ACCEPTED)

The independently prepared QA4023 source, actual native receipts and report were
read before integration, not overwritten. Two final same-source AppContainer
runs confirm restricted token/file/environment/parent-memory controls and owned
child timeout cleanup, but their strict IPv4/IPv6 loopback denial-code checks
FAIL: they saw10060 timeouts rather than10013. No loopback bypass/exemption or
firewall change was applied to force success. Their passing offline33 receipt
contracts are part of standard1062, NOT33 accepted native Windows scenarios.

See docs/research/HYB-005D-QA4023-WINDOWS.md. Windows evidence remains a candidate,
not the active product backend and not proof for Docker or Hermes integration.
Its earlier1050-test run changed measured file membership and was not accepted as
a stable final snapshot; the subsequent independent1062 run is separately recorded.
No Windows experiment is relabeled to make the scoped Linux checkpoint green.

## Final local validation

Full standard suite1062/1062 PASS, no skips or measured-code drift. The65 Linux
adapter contracts and33 Windows evidence contracts are INCLUDED, not added to1062.
The six final-code actual Docker scenarios PASS with unchanged source hashes.
A separate exact-ID Docker query verifies all six are absent after recorded
shutdown/removal. The initial six runs belong to the earlier code revision.
The final Docker probe performs no Hermes Gateway or model execution. Publication
and same-commit server CI are recorded only after push in status.md.

## Publication and exact-code CI

Code4aaa27f3b6ec9d3da12247b3535c651d43086e51 was pushed to the feature branch.
The server checkout SHA matches it exactly:1062 passed, zero failed/skipped/suite
errors; GitHub alaz/local-ci reports success. Evidence:code-ci.json. Standard CI
does not rerun either native OS experiment. The independent QA4023 final record
also corroborates the six retained Linux server cases, without new containers or
an independent full source audit. All historical failures remain distinct.

The next gate is actual Hermes admission/budget/tool integration, then provider
credential/egress custody. This module alone is not the live harness perimeter.
