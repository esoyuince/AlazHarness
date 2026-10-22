# L113F6 - native three-store startup, read-only response preflight and close

## Scope and selected sources

The optional response_store.db path is integrated into the EXISTING
NativeStoreStartup, not a second startup owner. Parent commit aeff7a0 provides
the unchanged R113Q8 cold-response checker and fixed helper. Original base is
a3951d764df291bebbf20f0452119a3d461d8832. The selected native feature remains
cc16c10b16a0ca8d80b23fd9be3f0e59ee605075 and the two explicit J112 patches.
Installed vendor, native gitlink and sources.lock are NOT changed or activated.

The new argument response_expected is optional. With no argument, the original
two-store startup order and finite layout remain selected. Including the third
file is explicit; no arbitrary filenames, directories, auth or config payloads
are admitted. The original P102 projected profile has NOT been widened for the
third store. Existing storage diagnostic HTTP explicitly refuses a startup
configured with response_expected; its two-store policy cannot certify three.
No native agent listener, work route, model/provider send or deployment occurs.

## One startup and shutdown sequence

The sequence is finite layout, canonical pair cold preflight, response cold
preflight, native state/replay constructors, pair live validation, source-checked
native response constructor borrowing the same state connection, response live
validation, one clean-only epoch advance, then both live validations again.
The caller supplies trusted prepared identities; no trust is learned from a
suspect candidate. Response feature verification currently precedes its own
constructor but follows canonical pair construction/live validation.

The fixed response helper uses a separate process and normal read-only SQLite
locks. It checks exact native schema/feature, expected private regular file and
inode, DELETE journal/header, no recovery sidecars, bounded SQL and data sizes,
known constructor limits, no unsettled response key, and valid/nonorphan data.
It refuses known settlement/eviction pressure instead of letting constructors
repair or delete the evidence. The parent holds its profile lease and checks the
third file's actual expected mount, while opening no raw SQLite descriptors.

The live response observer opens no SQLite connection or DB/sidecar descriptor.
It verifies the exact native class, borrowed canonical handle/mutex, actor,
profile path, file/mount/schema and retention settings. Startup-only mode checks
response total_changes is zero after construction. Pending identities and active
transactions are refused; observations are not cross-store replay authority.

Close prechecks ALL returned handles for active transactions before closing any.
Response closes first, replay second, canonical state last. A replaced handle,
active response transaction or unconfirmed/swallowed native close error retains
ownership and refuses blind retries. The startup never releases the caller's
profile/image lease. This remains a cooperative, process-bound ownership model,
not protection from malicious host root/same-process mutation or ABA races.

## Actual native ordinary-Linux run

native-002 is a complete successful run using genuine pinned Hermes classes,
real native profile ownership and real SQLite files on ordinary P71C UID23001.
A separate provisioner finishes and closes the files before each target process.
The current unchanged two-store path also runs as a control. No native class,
factory or policy method is replaced in this genuine experiment.

Nine target executions cover a clean three-store start; a second process reopening
that same profile with preserved three file inodes and response body, epoch1->2;
the default two-store control; five response-file refusals (schema, unsettled key,
retention pressure, sidecar, public mode); and a canonical-pending refusal.
There are83 nested checks across these cases, not83 distinct native executions.

Clean three-store targets record exactly three parent SQLite connects and two
fixed cold helpers, with zero raw parent DB opens during preflight and zero
network activity. Both report all six ordered product checks. Response bytes
remain identical after start/close; the native borrowed canonical connection is
unchanged. Opening a response transaction blocks every store close, leaves the
transaction intact and preserves all three usable handles. Explicit fixture
rollback precedes successful close; only the caller releases its lease.

The five response-file negatives reject before ANY parent writable connection;
all three file byte hashes remain unchanged, epoch is not advanced, and a retry
on the same startup object is refused. The canonical-pending case is later:
existing state/replay constructors execute, then live pending-work validation
refuses before response construction or new epoch. Admission and epoch rows
are exactly unchanged; replay and response bytes are unchanged. HOWEVER, the
existing native SessionDB constructor updates helper metadata in state.db.
Canonical file-byte identity is therefore NOT claimed after this later refusal.

native-001 correctly refused pending work but the QA wrongly asserted whole-file
byte equality after the existing canonical constructor. Its FAIL and traceback
remain preserved. native-002 changed only the QA observation scope to compare
exact semantic rows and to report the metadata/byte change, not product behavior.
No native repair, queue recovery, automatic retry or suppression was introduced.

This run used no root, mount changes or full namespace confinement. It is NOT a
three-store P102 isolation/loop detach/power-loss acceptance. Both runs removed
their owned temporary code/profiles; existing labs were not stopped or changed.

## Complementary and standard test scopes

R113Q8 independently supplies44 focused query/parent-contract methods, repeated
on Windows/Linux, and47 real-native checks including13 refusal cases. Its real
SQLite contender stays BUSY before and after the read-only helper, and acquires
only after owner close. That separate proof is retained at its original source.
The lifecycle/live/default focused selection has126 methods; it includes26 live
checks and18 optional startup tests with declared native/mount/lease doubles.
Four additional layout methods verify explicit inclusion, no raw third-file open
and unchanged default rejection. Seven offline tests bind native002 to current
source and inspect cases, source provenance, cleanup and limitations. These and
six cold receipt methods are STANDARD SUITE MEMBERS, not extra native runs.

Four older receipt test modules formerly required all future product bytes to
remain identical to their historical execution. They now pin ONLY the three
intentionally changed files to their exact preserved pre-change snapshots.
Every other source hash remains checked against current bytes. A strict helper
also binds those snapshots to the original baseline hash. Thus earlier F111,
H110, L106 and A109 runs remain historical evidence, not falsely promoted into
current-code full-confinement acceptance. Original raw receipts were untouched.
The new native002 separately checks the new current product bytes.

The new complete Windows standard suite and before/after source manifests are
recorded here only after terminal completion. The historical binding selection
passed29 methods; the native-receipt/layout selection passed17. Selections and
nested checks must NOT be summed with the full suite. The existing23 Windows
platform/opt-in skips are not new Linux executions or current full isolation.

## Tool boundary and interruption

Request00021 proposed moving the feature check before both canonical constructors
and running another native fixture. The tool safety check blocked it. It was NOT
reissued using another tool, encoding or route. Read-only00022 confirmed no source
changes or native003 files; successful native002 remains the exact current
product. blocked-refinement.json preserves this boundary. Source verification
currently happens before response construction, NOT the proposed earlier point.

The later interrupted message00026 never obtained a receipt or produced full-run
artifacts. Read-only00027 verified absence before the new standard run00028.
This recovery did not repeat any native work or the blocked refinement.

## Remaining acceptance gates

Use the existing fixed three-store sequence, never a replacement engine, to
qualify finite third-store projection, restart/drain and default regression under
full isolation. Define legitimate healthy/busy policy separately: quiescent cold
checks and close refusal alone are not a work-serving readiness policy. Native
borrowed connect remains refused. The response preparation shown here is a fresh
owned QA provisioner, not a general migration tool for user data.

Source-pin installation and HTTP/work activation remain disabled. Cross-store
terminal equivalence, atomic two/three-store recovery and power-loss safety have
not been accepted. No partial/unknown work is replayed. LegacyIPCv2 stays CLOSED
and fullD3B OPEN. Published main, remote push, CI queues, production and the old
root worktree are untouched. Current status.md records the exact terminal or
pending step; summary.json and delivery.json are written only for verified work.

## Complete combined regression - terminal

NEW Windows standard suite:2918 discovered/run =2895 PASS /23 SKIP /0 ERROR /
0 FAIL, exit0. All446 source/config/test files and both native patch hashes
match before/after.427 of434 original source files are unchanged; three product
modules and four historical receipt tests changed deliberately. All2512 original
evidence files and17 qualified cold-parent evidence files are preserved.
Native002 is separately exact-source matched:9 target executions/83 overlapping
checks, no full namespace/root/mount/API activation claim. Static-final.txt is
the final local repository gate; no remote CI result is inferred.

## Canonical development delivery

Tested source commit `9d383cf506dbb516b052d5b266c0562a2628e9f9`, review-preserving merge `02e5d24b737c4613e8c076422b3039275de230f7`, fast-forward from `a3951d764df291bebbf20f0452119a3d461d8832` into `alaz/d3b-principal-launch-21oct`. All446 tested source/config/test hashes and both patches remain exact. Installed native stays `eb75627faf532fa6ffbdae59a0d14b0b385fc780`; no listener or source-pin activation. Final delivery is documentation/static only, not another native or full namespace run. Current status.md is the continuation.
