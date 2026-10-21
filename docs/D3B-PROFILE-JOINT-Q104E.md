# Native profile admission plus independent metadata QA — Q104E joint

Input implementation:F104X8fdd717, canonical delivery032f2fd.
Input independent QA:Q104Eb8044f2. Full parent IDs:inputs.json.
This merge preserves both histories and selects ONE canonical P102/F104X
runtime. It does not import the alternative P102X projection implementation.

## What is now composed

S101 supervises the existing dedicated ext4 image and retains its image lease
until all users exit and the loop is detached. P102 confines the fixed profile
subtree at /run/alaz-state/profile with scratch ephemeral. F104X provides an
explicit narrow own-PID mountinfo READ_FILE opt-in; after final exec and final
Gateway UID, the unchanged Hermes ProfileOwnership/ProfileLease reserves that
profile with the unchanged real mount observer. Default metadata policy stays
closed. No observer bypass, full proc grant or replacement lock algorithm.

The qualified F104X native trial shows two mounted lifetimes with final real
UID23001/GID23003, native profile lock after exec, registered live-writer release
refusal, other-process lock contention, reuse of the same lock inode after
release, and image lease retained while the releasing process remains alive.
Dummy SQLite records/inodes survive complete image detach/remount. Actual broker
ping works; provider sends remain zero. Native ownership is real pinned Hermes
code; database schemas are still dummy and a real Gateway is NOT started.

The independent Q104E trial exercises the exact same guard bytes as an ordinary
user in P71C. Default/False deny own mountinfo; True allows it across real exec.
Sensitive own metadata and other-process mountinfo stay denied after positive
open controls. Fork/exec children do not gain a new own-PID grant, but inherit
the original numeric grant. Three main cases each21 overlapping checks plus
nested descendant checks are nine process instances, not63 independent runs.
This isolated Landlock audit is not a second full Gateway isolation trial.

## Source/evidence join, not another runtime rewrite

All378 F104X source files are identical to its qualified full/native runs.
The Q104E script/tests and snapshots are unchanged from their own successful
full/native runs. Both input evidence sets are69 exact original Git blobs.
No old receipt is rewritten or attributed to different code. F104X parent41 /
two38-condition native proof and Q104E three21-condition proof are separate
trials with distinct scope. They are not added into a fictitious test total.

Only status.md conflicted. Both histories remain intact below the newest entry.
Two new offline source-join tests explicitly connect CURRENT guard/projection
bytes to the independent snapshots and to both actual native proof manifests.
They do not rerun Linux or replace the required complete combined regression.
No product source changes were needed for this merge.

## Regression and delivery gate

A NEW complete union Windows run is required. Separate F104X2445 and Q104E2444
counts are historical input results, not a sum or substitute. Final combined
result belongs to full-windows-result.json after the process is terminal.
All sources are hashed before/after. Final local static runs separately after
completion; it is not GitHub CI or runtime activation.

Promotion is allowed only if the current canonical worktree is clean and still
an ancestor of the tested merge. No force/reset/squash/main/push operation.
Source/evidence identity must be rechecked after fast-forward. Any concurrent
new code requires reconciliation; do not overwrite it.

## Scope kept open

Real Hermes Gateway startup, actual Hermes state/idempotency database schemas,
epoch/recovery semantics, coordinated two-store recovery and the broker's live
Gateway-ledger read/send path remain unqualified. Power-loss durability was not
tested. The S101 worker is bounded, not an activated perpetual service. R91F
source-collector and G82C blocked work remain untouched; legacy IPCv2 CLOSED,
full D3B OPEN. No model/provider send, production/account/service/defaultUbuntu
or new privileged lab action occurred during this union.

Q104E own temporary fixtures/processes were removed. The lab was shared with
F104X; this task issued no terminate command. Original F104X cleanup evidence
is preserved independently. New union work is Windows offline tests only.

Current pointer:status.md. Evidence:evidence/d3b-profile-joint-q104e/.

## Final combined result

NEW union fullWindows2463 total =2440 PASS /23 SKIP /0 errors /0 failures, exit0.
All382 source/config/test/script hashes match before/after; all378 F104X input
source files are unchanged. The69 source evidence blobs remain exact. New
current-source join tests are included in the full total. Prior separate full
runs and Linux counts are not summed or relabeled. No fresh Linux execution
was required or claimed for this source-identical QA union.

The23 existing platform/explicit-opt-in methods were not newly executed on
Linux by this task. Native F104X ownership proof and ordinary-user Q104E
permission proof apply to the exact unchanged implementation, with distinct
scope. Full Gateway/real store schema/epoch/provider/atomic recovery remains
unqualified. Final local static and delivery are recorded separately.

## Canonical development delivery

Qualified two-parent merge `5001f1a0a2102520ba609d5e0f7d094297e87adf` was fast-forwarded from032f2fd into `alaz/d3b-principal-launch-21oct`. Canonical worktree is `C:\Antigravity\AlazHarness\scratch\worktrees\d3b-principal-launch-21oct`. All382 source hashes remain exact; independent integration/QA/feature branches are preserved. The follow-up delivery commit changes documentation and final static record only. No main/push or new runtime activation. FullD3B remains OPEN.
