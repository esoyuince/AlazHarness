# R154A1 - Verified source and dependency installation

## Result

The exact R153 runtime candidate is now installed in the existing dedicated
AlazHarness-D3B-P71C laboratory at `/opt/alaz-r154a1`. The source-only installer
completed with exit 0. A separate ordinary `alazgateway` process then ran the
read-only installed verifier and passed, exit 0.

This closes the current source/dependency/interpreter installation sub-gate of P1.
Projected startup, retained seeding on the supervised image, finite work, full D3B,
M1 and production acceptance remain NOT RUN / NOT ACCEPTED for this installation.
No native application, service, provider, model, image, mount or cgroup was started
or created by this package.

## Exact installation

| Item | Observed identity |
|---|---|
| Harness base for this development | 16830bd56e8c9b6a23e1bd60435ffb4b04793a9d |
| Packaged runtime source | e03f7fd4e47fea6a58b749564ab350aeb4237a26 |
| Native source | d1516731308de8e87130dc68124e69aad35d6911 |
| Source archive SHA256 | e036fba503130b3b259ec727439089c8fa3d88408359618fa5c7df77a6b5513b |
| Source manifest SHA256 | 182b9d0198e4c7f39bd28e194bfe7fc6cfca844ed4a653e9d209b0db8d77eef9 |
| Source-package files | 834: 77 harness, 756 native, one dependency inventory |
| Installed dependency files | 1162, copied from the verified existing laboratory dependency installation |
| Python | /usr/bin/python3.12, CPython 3.12.3, root 0:0, mode 0755 |
| Python SHA256 | e50d468e8b0adfb05733f5b87b3cff34829c4a8c1aea50c865aa8bdfe4bb150f |
| Installation directory | /opt/alaz-r154a1; device2096, inode27339 |
| Installation receipt SHA256 | 137cbe59427813b50f8c8581a7dbc3b81db9e514e2e57784cee91baa4cc17ae2 |
| Provisioning inputs | /opt/alaz-r154a1-input, retained for inspection |
| Frozen four-file transport bundle | d043a57a87e2c6f75a02e4295e316bbba899dec40b14df6e9e9a2b2d4e0519a2; 19989136 bytes |

The new installer and operator are provisioning tools outside the unchanged
77-file packaged harness inventory. Source correspondence is checked against
immutable Git blobs. The candidate has not silently advanced to a new native pin.
The accepted archive is the same archive produced by R153; dependency bytes are
now present in the new installation as well as its source inventory.

## Implementation

`scripts/install_projected_candidate.py` accepts explicit manifest/archive/source
and interpreter identities. It imports only the exact reviewed sibling builder
bytes, reuses its archive verifier, and never imports candidate or dependency code.

Preflight verifies the complete archive, native envelope, dependency inventory,
actual existing dependency bytes, trusted Python and root-controlled ancestry.
Descriptor-relative no-follow reads reject symbolic/hard links, special files,
unexpected or missing entries, case/path collisions and untrusted permissions.
Reads and inventories are bounded; a FIFO cannot stall an ordinary preflight.

Apply additionally requires the fixed isolated Linux x86_64 Python 3.12 interpreter,
host root credentials and the initial user namespace. It writes a new staging
tree exclusively, sets exact modes, reads back all source/dependency copies,
rechecks original dependencies and Python, and publishes into an absent final
directory using `renameat2(RENAME_NOREPLACE)`. The accepted receipt is published
after final-directory publication and readback. Partial or uncertain trees are
preserved; no resume, overwrite, deletion, repair or automatic retry is provided.

`--verify-only` and `--verify-installed` are read-only and can run as the ordinary
laboratory account. The latter checks the actual installed source/dependency
bytes, permissions, interpreter, destination identity and exact receipt.

`scripts/qa/r154a1_install_candidate.py` is a fixed one-shot operator for this
candidate and laboratory. Preparation freezes four hash-bound inputs; an exclusive
execution-start record precedes apply. It stages only those reviewed inputs under
the new root-controlled input directory, then invokes the fixed installer. Unknown
inner outcomes remain UNKNOWN at the host boundary with known PIDs retained.
It does not turn its installation receipt into runtime execution authority.

## Verification

| Check | Observed result | Scope |
|---|---|---|
| Existing laboratory environment | PASS, exit 0 | Ordinary-user read; all 1162 existing dependency hashes and trusted Python/ancestry |
| Installer Linux suite | 36 PASS, 0 SKIP, exit 0 | Owned fixtures; actual descriptors, links, FIFO, partial-write and atomic-publication checks; no privileged install |
| Installer Windows suite | 16 PASS, 20 Linux-only SKIP; raw unittest exit 0 | Same 36 cases; portable input/receipt checks |
| Operator Linux suite | 11 PASS, 0 SKIP, exit 0 | Receipt propagation, optimized-execution refusal and actual owned mode helpers under umask 077 |
| Operator Windows suite | 10 PASS, 1 Linux-only SKIP, exit 0 | Same 11 cases |
| Real-candidate preflight | PASS, exit 0 | Actual834-file candidate, 1162 existing dependencies and Python; ordinary user, no install |
| Actual source-only installation002 | PASS, exit 0 | Fresh root-controlled input and installation paths; installer process terminal |
| Separate installed verification | PASS, exit 0 | Ordinary user; all installed bytes/modes/receipt, no writes |
| Staged repository static gate | PASS, exit 0: 6,348 files, two gitlinks, 3,745 tests discovered | Static/JSON/syntax/credential-pattern checks and discovery; no test execution |
| Full repository regression | Exact final commit CI required before main | No new full Windows run or remote numeric count inferred |
| Projected readiness / retained image seed / finite work | NOT RUN | Remains P1 continuation |

Focused suites overlap across platforms; their counts are not added into a full
regression total. The Linux installer fixture materializes 1,996 synthetic files;
those are fixture source/dependency copies, not additional product runs.

Both independent source reviews found no remaining blocker in their exact scope.
The installer review binds SHA a56782d4e09bed38983c387d4b882e3db3866409e8e96e1f092d36517fc53525.
The operator review binds SHA 06755f6d866a30b208c80ce23dab30e99326077d0b632211b42d9f6dcac18a14.
Reviewers did not rerun tests or perform the installation; those observations are
the primary command records. An incomplete separate native-runtime review is
not used as corroboration of runtime acceptance.

## Preserved corrections and custody

The first operator draft lost inner timeout uncertainty at the host terminal and
left new input permissions dependent on umask. Both were corrected before any
root application. Optimized host invocation is also refused and the installed
success receipt is checked against exact source/destination/count/false-flag
expectations. Attempt001 was prepared and passed ordinary input verification but
was never applied. Attempt002 uses the revised operator with identical four
payloads; the original input verification remains scoped to those unchanged bytes.

The first Windows test wrapper miscounted CRLF-terminated skip lines and exited 1
after a successful raw 36-case run. Its original summary and raw output remain.
The summary was corrected to 16 PASS / 20 SKIP from that output without replaying tests.

A closure comparison initially compared Windows checkout bytes directly with raw
archive bytes. Its failed assertion and completed diagnostic are retained. All
77 immutable HEAD Git blobs match the archive manifest. The sole raw checkout
difference is LICENSE; CRLF-to-LF conversion exactly reproduces the archive bytes.
Git source identity and checkout text conversion are qualified separately; no
source, archive, Git attributes or installed file was rewritten.

The first local static invocation reached its 120-second tool deadline. Its
partial stage was inspected: all 57 selected files remained staged, no unstaged
change existed, and no matching wrapper/scanner process remained in the later
snapshot. No success was inferred from that attempt. The standalone scanner
then completed in 198.379 seconds with exit 0 under an expanded deadline.
static001-timeout.json preserves the first observation; static002.json records
the accepted scan. Newly added closure metadata is checked before commit and
the exact final commit still requires the remote CI gate.

The final pre-publication custody check passed: the original root worktree and
all 33 existing file contents are unchanged, the native source remains clean at
d151673, and main remains clean at the accepted 16830bd baseline. Exact observations
are in protected-state.json. Only this isolated R154 branch is changed. Earlier denied operations are not replayed; this was a new,
reviewed source-only installation in the already designated dedicated laboratory.

## Remaining product gate

1. Use the qualified installation to prepare the original supervisor's dedicated
   ext4 image and live caller context through the existing product contracts.
2. Produce a real retained receipt via the original native owner/finite lifecycle
   on that same image, while retaining the original lease. A copied QA profile or
   rewritten device/inode/owner record is invalid.
3. Derive the real supervisor/fence/cgroup/mount namespace/loop/principal bindings,
   then run the fixed supervised projected readiness and normal ordered close.
   The 120-second mount-worker lifetime and child timeout/stop margin still apply.
4. Accept normal/error, replay/new-work and a finite task through this complete
   product path before advancing to P2's selected real provider and budget.

The source installer changes no launcher, owner, source envelope or kernel guard.
Its positive receipt does not establish any of these later runtime results.

## Evidence and publication

Evidence: `evidence/m1-install-readiness-r154a1/`.
Key records: `installation002/`, `installed-verify001/`,
`real-candidate-preflight001/`, `independent-reviews.json`,
the Windows/Linux focused transcripts, protected-state and native terminal records.

The exact final commit must pass `alaz/local-ci` before ordinary fast-forward
publication. Live Git refs and exact-SHA CI are authoritative; the ignored final
publication journal in this worktree records the final SHA/CI/ref observations
after publication. Git publication does not start a runtime service.
