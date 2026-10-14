# AlazHarness — REF-PI-001 checkpoint

Date: 2026-10-15. Default workspace: C:\Antigravity\AlazHarness.
Active branch: alaz/ref-pi-001.
Active worktree: C:\Antigravity\AlazHarness\scratch\worktrees\review-pi-opencode-46cc.
Base: 3bf5305f9cadab584429ca4d97a941f394c0522f (contains integration 99d6fe1).
The old directory name is retained deliberately; no new worktree was necessary.
Read live git status/HEAD before proceeding. Other lanes/worktrees are preserved.

## Earned result

M0 bootstrap/publication accepted historically. Existing root suite 128 tests;
this package adds 26 offline tests (16 HTTP gate + 10 Python guards), totaling154.
Pi direct Agent core, native read and native HTTP provider: eleven distinct
scenarios passed on Windows with scripted loopback model responses. No real
model inference, paid calls, social network or autonomy loop ran.

Pi source pin: b06c1f2cf1dea6af8748ddeee18c23587d2cb7c6.
Runtime OpenClaw/Hermes submodule pins and their ten copied payloads unchanged.
OpenCode reference pin remains3943b84ef00e83dbc3c48e6a92b02f0d88fb35f9; not executed.

## New files and ownership

- packages/hybrid-runtime/provider-request-gate.mjs: Alaz-owned per-fetch HTTP
  request cap, used by the Pi probe only; not production currency/token enforcement.
- scripts/probes/native-pi-worker.mjs: actual upstream constructor/loop/read/HTTP
  imports through the upstream source resolver; only provider responses scripted.
- scripts/prepare_native_pi.py: explicit isolated npm ci, dry-run by default.
- scripts/run_native_pi_probe.py: fresh output/profile, exact source validation,
  eleven independent bounded child runs, true cleanup and error evidence.
- config/pi-native-probe.lock.json:1922 file manifest pin + npm lock + source pin.
- docs/research/REF-PI-001-NATIVE.md and evidence/ref-pi-001/: scope and receipts.

Native outcomes: read success; missing read; external cancel; test-controller
100ms cancellation; one-HTTP cap; retry cap after503; truncated SSE error;
same-process scripted-model-ID switch; awaited agent_end listener; denied read;
concurrent prompt rejection. All native results require idle and zero open sockets.
A normal stop with a failed tool does not prove task success. Native scenarios
are separate from the154 default CI tests and are not added to that count.

## Reproduce

python -B -m unittest discover -s tests -v
python -B scripts/ci_check.py
python -B scripts/verify_components.py --with-vendor --source-workspace C:\Antigravity\AlazHarness

Prepared local Pi runtime: C:\Antigravity\AlazHarness\runtime\ref-pi-001-4eb7.
The scripted native runner requires --prepared-root plus a fresh --output.
Read docs/research/REF-PI-001-NATIVE.md before installing/running. Personal model
credentials, proxy and Node injection variables are not inherited.
Preparation source-manifest serialization bug was fixed with a canonical map
hash; all individual source-file checks remain. Failed initial root log retained.

## Next

REF-PI-002: bounded native Pi Durable admission/restart/replay experiments,
including same-key/different-input conflict and unknown side effects. Do not
add it as a second writer to Hermes session state. REF-OC-001 stays queued for
OpenCode permission/event contracts. Hybrid Gateway qualification also remains
open. No engine replacement, main merge or M1/M2 acceptance is implied.

## Git/CI

Public MIT repository esoyuince/AlazHarness; existing alaz-server Local CI,
GitHub Actions disabled. This package needs no server profile changes.
Final commit/status must be checked live after push. Original dirty root on
alaz/hyb-001-component-slice, other feature worktrees and all source refs remain
untouched. No broad staging, source updates or force pushes.

## Local package acceptance

154/154 root tests PASS. The packaged preparation helper completed from a fresh
source archive with lifecycle scripts disabled; all eleven native cases were
then rerun successfully in that independent environment. They remain eleven
distinct scenarios, not twenty-two. Final local receipts: evidence/ref-pi-001/
native-reproduced.json, preparation-reproduced.json, local-validation.json.
Prepared reproduction: runtime/ref-pi-001-repro2-4eb7 under the default workspace.
