# Native profile mount observer integration — N97K

Status: native observer, combined full regression and unchanged local static gate PASS.
Active development worktree: scratch/worktrees/d3b-storage-mounts-m96q.
Merge parents: M96Q db25f2549e0cb7ec44b7aa1af09ea77a92f0446d and primary I95P
 e12ff5937bbac22dc0f53fdcecc0ed5eeb17a837; common base80d8548.

## What changed in this slice

Combined the current primary development history and the M96Q observer history.
Only status.md conflicted; both full previous records are retained below the new
active entry. Product sources did not conflict or change. New files contain
one bounded ordinary-user QA runner and three source/receipt regression cases.
No code from the unqualified R91F replay branch or failed G82C projection branch
is merged. Their known failures and denied-action records remain untouched.

## Actual user Linux run

Only the already approved disposable WSL distribution AlazHarness-D3B-P71C was
started. The interpreter ran directly as its existing alazgateway user:
UID/EUID23001, primary GID23003, supplementary groups[23003]. No UID transition,
root command, mount/unmount, namespace setup, account, service, package, config,
provider or broker action occurred. This is NOT the G84E confined process.
Normal Ubuntu remained the default stopped distribution throughout.

A read-only preflight used findmnt to identify the existing root ext4 mount
(ID80, device8:48, root/ and mountpoint/) covering /tmp. This explicit observed
expectation was passed into the separate QA run; it is a test comparator, not
proof of trusted storage-media provenance or a production authority token.
The independent findmnt result inside that run matched the expectation and
the observer's actual kernel data. These IDs are specific to the recorded
mount namespace and must not be reused as persistent mount identities.

The existing test account deliberately has no home. The first read-only
preflight emitted a WSL chdir(/home/alazgateway) diagnostic but exited0 and
produced the expected JSON. Subsequent commands explicitly selected /tmp;
no account/home was created or altered. Original stderr is retained.

The exact product/test/QA bytes were carried through stdin into a fresh
TemporaryDirectory because the lab intentionally lacks a Windows drive mount.
Only the three explicitly named files were accepted and SHA256-verified.
No root installation or source-tree modification occurred. The temp tree and
all fixture trees were removed after the children exited.

## Native results — 21 conditions, not 21 Gateway executions

native-001-result.json records actual command exit0. native-001-stdout.json
contains the full30-name Linux unittest output, the native child stdout and
all source hashes. Unit tests are unchanged M96Q fixtures,30/30 PASS in this
user lab, not the earlier ChatGPT analysis container.

The real native observer run passed21/21 conditions:
- Both names correspond to actual owned SQLite files on the ext4 root; the
  QA uses a trivial synthetic table, NOT the Hermes schema. Each DB used
  synchronous FULL and PERSIST journal mode and retained its actual rollback
  journal. No WAL was enabled. The observer saw4 regular files and2 sidecars.
- External findmnt and the supplied expected mount/device/root agree.
- Wrong expected mount ID, device or filesystem root is refused. Missing
  replay store is refused without creation. Actual hardlink, symlink and a
  directory standing in for a sidecar are refused. After the QA removes those
  owned negative fixtures, a second observation of the good files succeeds.
- Fresh regular files in existing /dev/shm are correctly rejected as tmpfs.
  No new filesystem is mounted and no global state is changed.
- An audit hook active only during observer calls permits opening only
  /proc/self/mountinfo, with read-only flags; content opens, file mutations,
  socket construction and subprocess launch would abort. Eleven such allowed
  opens and zero forbidden events were recorded. The QA itself creates and
  hashes its own fixtures outside this audit scope; the observer does not.
- Original DB/journal bytes, inodes and recorded metadata match after tests.
  Mount table, mount/user namespaces and identity are unchanged. All source
  hashes match before/after. All generated fixture directories are removed.
- The result explicitly denies claims about physical medium durability,
  current SQLite open-inode custody, exclusive writer ownership, paired-store
  consistency, persistent Hermes admission and execution authority.

The21 observations overlap and are not added to unittest totals. The three
new offline receipt tests pin exact current source and terminal results; they
do not run a native child or synthesize a new acceptance from old evidence.

## Cleanup and protected state

The final ordinary-user audit found no alaz-n97k temporary entries and no
matching lab broker/Gateway or owned code processes. The test did not start
any broker/Gateway. Only the named disposable lab was then terminated; the
final WSL list has both it and default Ubuntu stopped. No global shutdown.
Existing P71C/G84E installations, private config/budget and receipts were not
opened or modified by this slice. Existing root-repo user changes were left
alone. Maincc7ceba is not advanced and no push is performed here.

## Remaining actual runtime work

This qualifies the observer on actual ext4/tmpfs and integrates its code into
the development line only. It is NOT a persistent-volume implementation or
Gateway admission wiring. G84E still intentionally uses private ephemeral
writable trees; legacy IPCv2 gates remain closed. Do not bind an ambient
host-writable directory or treat a filesystem label as permission to launch.

The next runtime decision must provide a dedicated persistent storage domain
whose lifecycle does not reintroduce ambient host sockets. Before admission,
both native databases need qualified open backing, writer/epoch ownership and
cross-store crash reconciliation. A read-only pathname observation is not a
substitute. R91F's missing executed-source enumeration remains a separate
unresolved blocked-action boundary; this different passing branch does not
repair that failure or remove its tests from that branch.

No real Hermes process, restart durability, power-failure recovery, provider
dispatch or paid-model behavior was tested in N97K. Complete D3B remains OPEN.

## Reproduction and evidence

Evidence: evidence/d3b-storage-native-n97k/. Source QA is
scripts/qa/n97k_storage_mount_probe.py. Native invocation must run as designated
ordinary lab user with a current independently observed --expected JSON and
exact copied source bytes. transport-bootstrap.py.txt is the exact observed
transfer/test wrapper, not an install script. Use fresh temporary fixtures;
never replay a pending/uncertain operation or reuse historical mount IDs.

The full standard Windows suite uses unittest's result object, not textual
footer parsing. Static scan is deliberately sequenced after full completion.
Their results are appended only after terminal receipts. No old full result
is relabeled as combined validation.

Mechanism references consulted, not acceptance evidence:
https://man7.org/linux/man-pages/man5/proc_pid_mountinfo.5.html
https://www.kernel.org/doc/html/latest/filesystems/tmpfs.html

## Completed combined regression

Fresh full Windows standard selection:2306 total /2301 PASS /5 SKIP /0 errors /
0 failures, exit0;195.480 seconds by the result-object collector. All349 source,
script, test and configuration files match before/after. All345 preexisting
primary source blobs match their original Git content. Nine original M96Q
input evidence files remain unchanged. The30 observer methods and3 new receipt
methods are included in the full total, not added again. Linux30 is a separate
execution of the same methods, and native21 conditions overlap those checks.

The native run and full regression are terminal. Local static inspection runs
after the full suite and is recorded separately in static-final.txt. Neither
that scanner nor this branch's PASS repairs the separate R91F failed branch.
The pending merge preserves both input histories; no squash, force-push or
history rewriting is used. Read the terminal delivery record for final commits.

## Publication-format correction, not a test repair

The first post-suite static check (static-final.txt) correctly refused two
unscanned binary outputs from WSL: final distribution list and terminate stdout.
They are UTF-16LE text. Original bytes were moved, not deleted, into ignored
scratch/n97k-raw-output. Their tracked .bin.txt.json representations contain
exact decoded text, encoding, byte length and SHA256. Re-encoding each decoded
string reproduces every original byte. The scanner sees all decoded content;
no rule, exception list, product source or test assertion is changed. This is
artifact publication hygiene, not new Linux execution or reinterpretation of
the successful native run. The first FAIL is retained; a fresh unchanged static
execution is stored as static-after-format.txt.

## Qualified development merge

Final local static check returned0/PASS with2306 discovered,2054 tracked files
inspected. This scan is separate from the actual full2306 execution. The raw
first static FAIL and exact UTF16 custody correction remain visible. No test
limit, scanner rule, original native outcome or source pin was changed.

Both merge parents and all historical evidence are preserved. The qualified
merge is promoted only by fast-forward to alaz/d3b-principal-launch-21oct after
checking that its source HEAD and working tree are unchanged. Main and origin
are not touched. A following documentation checkpoint records the exact merge
commit and active continuation; no additional runtime result is inferred from
that checkpoint. R91F remains unqualified on its separate branch.
