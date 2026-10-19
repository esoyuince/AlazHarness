# PLAT-002A — Fixed Windows -> WSL2 read-only identity bridge

Date: 2026-10-19. Branch: alaz/plat-002-wsl-readonly-19oct.
Base: 90074e12cf6edbf3e00b7319af6b1bf4f174dfb2
(PLAT-001 scoped GitHub local-ci SUCCESS, not whole D3B).
**Status: COMPONENT CONTRACT PASS / NATIVE ACCEPTANCE BLOCKED.**
**Full PLAT-002, D3B, M1, M2: NOT ACCEPTED.**

## What is actually implemented

- Windows Node control process runs the absolute Windows system WSL binary
  with shell:false; fixed distribution Ubuntu; fixed Python 3 isolated
  startup, one pinned repository QA responder. No caller-specified command,
  executable, WSL distribution, mount or tool action.
- Read-only exact JSON request: version 1, fixed operation identify,
  a fresh 64-hex nonce and 32-hex requestId. The guest accepts only one
  line and a small bounded frame; unknown, duplicate, malformed and
  command-like request fields are refused.
- Guest response reports Linux x64/WSL2, real POSIX UID/EUID/GID,
  namespace visibility, no_new_privs and seccomp information.
  Response binds the exact nonce/requestId and host-observed guest
  source-file SHA-256. Host refuses unknown fields, UID/platform
  mismatch, changed source, unexpected process exit, extra output,
  timeout or cancellation without another attempt.
- Explicit CLI QA opt-in is required. Even a successful read-only
  reply **never** marks the secure execution adapter accepted, never
  invokes Hermes or a provider, and never changes the run/session owner.
- Guest script reads its own source on the Windows-mounted worktree.
  SHA equality proves matching observed bytes in this local QA,
  **not a cryptographic remote attestation**, immutability of DrvFs,
  WSL host filesystem confinement or trusted host UID isolation.
- The host process duration is bounded; unknown child outcome
  is fail-closed and not automatically retried. Linux guest process
  termination cannot be inferred solely from a closed Windows WSL
  wrapper. Host/Wsl process cancellation and restart native acceptance
  therefore remain open.

## Evidence: keep PASS, FAIL and NOT RUN separate

Earlier exploratory single read-only CLI invocation returned a
self-reported WSL2 Linux x64 identity (UID1000) with matching nonce,
requestId and guest source SHA, exit0. This was before final probe source,
so it is a diagnostic, **not final-source acceptance**.

One-shot final-source Windows native batch:
evidence/plat-002a-wsl-19oct/native-win-wsl-identity-01.json
returned **FAIL** across 5 attempted cases:
- Positive: GUEST_PROCESS_OUTCOME_UNKNOWN_TIMEOUT at 15s.
- Wrong expected guest UID: refused.
- Missing explicit QA opt-in: refused without WSL launch.
- Arbitrary shell flag: refused without WSL launch.
- Missing arguments: refused without WSL launch.

The 4 refusals do NOT turn the 5-case group into PASS.
Independent WSL read-only process-list inspection subsequently
exceeded 35s and returned exit124 with outcome unknown. A read-only
Windows tasklist inspection also exceeded 10s. Neither proved the
test-owned Linux guest process was gone. No blind repetition,
production-level kill, WSL shutdown/restart, service change, new
system account, privileged command or external model was used.
See evidence/plat-002a-wsl-19oct/native-stability-observed.json.

Default CI exercises only host/guest parsers and safe Node contract
fixtures; never launches WSL, a model, a native agent, or privileged
commands. New offline checks:
- tests/test_wsl2_bridge.py — 36 Node scenarios, 37 Python test
  methods including syntax, one real Node subprocess for all cases.
- tests/test_wsl2_guest_protocol.py — 20 strict guest parsing/
  wrong-platform refusal cases.
- tests/test_plat002_readonly_receipt.py — 6 immutable native
  FAIL+diagnostic/source-custody assertions.
- The existing hybrid and D3B tests remain required.

## Security boundaries intentionally NOT qualified

- WSL2 guest still sees Windows-mounted filesystem paths;
  host-filesystem isolation is false. The read-only probe does not
  itself invoke Landlock/netns/seccomp or the D3B private-budget broker.
- In the exploratory response no_new_privs=0 and seccomp=0; it is
  not a confined Gateway. It only identifies an unprivileged Python
  probe, not an isolated Linux tool process.
- Different real host UIDs and broker UID/IPC permissions remain
  D3B-HOST-PRINCIPAL-001 requirements. Guest UID1000 does not mean a
  different Windows account or a separate broker principal.
- No authenticated transport between different computers, remote
  worker, macOS ARM64, real provider rate, actual model/tokenizer
  or invoice reconcilation is implemented.
- No automatic cancellation/kill/stop/reconnect/replay in production.
  A lost acknowledgement or unknown guest lifecycle cannot be
  treated as a successful tool result or safely retried.

## Next precise gate: PLAT-002B

First independently diagnose host/WSL responsiveness and prove the
previous test-owned guest process is gone using an authorized local
inspection. Until then do not start another native WSL pilot.
Then stage a read-only source frozen under trusted Linux ext4,
qualify cancellation/host-wrapper/guest PID lifetime with **only
owned subprocesses**, test endpoint identity and replay/timeout
negative conditions, and separately integrate the FULL D3B
UID/broker/socket guard. Any real Gateway execution needs a
separate explicit acceptance, then optional paid-model limits.
M2/autonomous learning remains disabled until M1 accepted.

## Reproduction — safe offline only

    python -B -m unittest discover -s tests -p test_wsl2_bridge.py -q
    python -B -m unittest discover -s tests -p test_wsl2_guest_protocol.py -q
    python -B -m unittest discover -s tests -p test_plat002_readonly_receipt.py -q

The native read-only CLI requires explicit QA opt-in and is NOT to
be automatically rerun while WSL process state is unknown.


## GitHub Linux canonical LF compatibility — scoped QA fix

The first published code commit aff4689546b90d0602016b0698626b4a59c16b3c
was rejected by GitHub alaz/local-ci (rc=1, status56722358622 at
2026-10-19T19:04:58Z). Per-test logs are unavailable, so do not assert
this was its only failing test.

One definite Linux checkout incompatibility was found in the
native FAIL evidence verifier: the retained Windows original file
native-win-wsl-identity-01.json is CRLF, while Git commits/CI check out
LF. The two raw SHA256 values differ, but exactly converting every LF
byte in that ONE canonical file back to CRLF reproduces the original
Windows hash. The verifier now allows ONLY that one bounded exact
transformation, refusing stray CR bytes, missing line breaks and all
other content changes. The original native FAIL evidence and hash
remain immutable. Linux LF simulation of the six evidence tests PASS;
the Windows CRLF six tests PASS. This does NOT repair actual WSL
responsiveness or claim any secure process isolation.

Windows default full suite on the first commit 2159/2159 exit0,
5 Linux-only skips, 241.012s; static check 2159 discovered, 1519
tracked files, 2 gitlinks, exit0. Exact CI of the follow-up QA
repair remains independently pending. See
evidence/plat-002a-wsl-19oct/ci-failure-crossos-observed.json.


## Exact PLAT-002A repair code CI observation

The cross-OS native FAIL evidence verifier repair was published as
8088b11e722377cb8988ccb03583648030bc1fa3 on the isolated
alaz/plat-002-wsl-readonly-19oct branch. GitHub alaz/local-ci
**SUCCESS**, status id 56723417225 at 2026-10-19T19:16:55Z.
This CI qualifies default-discovered/offline code contracts, NOT
the separate WSL native 5-case acceptance (still FAIL) or full D3B.
The first aff4689 CI failure remains an immutable historical record.
Production bridge, real model and host principal isolation remain
NOT ACCEPTED. The documentation-only follow-up commit requires its
own exact CI observation.
