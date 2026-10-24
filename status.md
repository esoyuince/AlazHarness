# AlazHarness - status

## PUBLICATION-24OCT-P132L1 - IN PROGRESS

User explicitly approved publication review, push of the reviewed development
branch and main fast-forward only after exact-SHA alaz/local-ci SUCCESS, followed
by resuming same-owner API/finite-turn integration. Active branch
alaz/d3b-principal-launch-21oct, worktree scratch/worktrees/d3b-principal-launch-21oct.
Starting code d0418ad, previous main cc7ceba,164 pending commits. Existing J131D6
full3395=3372PASS/23SKIP/0ERROR/0FAIL and584sources/10patches are preserved.

Current work is publication only: scan reachable historical blobs/commit texts
and all pending trees, verify component provenance and existing tested hashes,
commit selected docs/evidence, push ONLY this branch. Require actual exact pushed
SHA GitHub alaz/local-ci success before remote main. Re-read remote main and use
non-forced history-preserving fast-forward; root dirty legacy tree is untouched.
No fork-main, installednative/source-lock/runtime/provider/service activation.
Do not start runtime work until publication passes. Prior handoff archived at
docs/status-history/p132l1-before-publication.md. Current commands/status receipts
in evidence/publication-24oct-p132l1. Push/main/remoteCI NOT RUN at this checkpoint.


### Publication review completed

All164 commits/3248newblobs and5365historicalpaths reviewed,92795880bytes; no configured credential/path/binary/size/mode finding.10upstream components reproduced.584current source/config/test files+10patches match full3395=3372PASS23SKIP. No runtime/test/source edit; only selected publication docs/evidence. Next local static then branch push. Remote main may advance only on exact pushed-SHA alaz/local-ci SUCCESS.


### Branch push complete, exact CI still required

Remote alaz/d3b-principal-launch-21oct verified at ea7b48257ae741c81ff385bac596ceb884d02caf. Push command exit0, no tags/submodule pushes/force. Entire original164commit history plus publication docs delta checked. Main remainscc7ceba. First GitHub status lookup for pushedSHA returned no status yet; oldmain alaz/local-ci isSUCCESS. Do not substitute old/main/local success for newSHA. RemoteCI and main update remain pending actual evidence.


### First Linux CI failure retained; test portability repair in progress

Exact ea7b482 alaz/local-ci FAILURE57166391620,3395tests with33failure assertions/8errors/5Linuxskips; no timeout/OOM. Main remainscc7ceba. Root-CI positive fixtures suppliedUID/GID0 and real runtime correctly refused; explicit root-only unit ownership metadata now mapped while mode/device/link and productionzeroID rejection stay real. Empty Git env positive control separated from platform-specific emptyflag parsing. Single C# probe checkout pinnedCRLF to exact existing native bytes. Three changed old test/helper sources archived by exactname+hash, raw historical results unchanged. No packages/runtime/native/CI policy or limits changed. Fresh focused/full tests required before nextpush.


### Repair focused checks passed; new complete regression started

71targeted Windows methods PASS including6new portability controls. Root productionidentity still refused, only unitfixturemetadata adapts; original modes/device/linkchecks retained. All packages/scripts/config/nativepatch bytes unchanged. Three oldtest/helper source versions archived, two newtest/helper files, singleC#checkout rule. Request9f220e48... owns full standard on frozen586source+10patch hashes; no source/test edits until terminal. Main stillblocked on remoteCI success.


### Portability repair complete locally; exact second remote CI next

New full3401=3378PASS/23SKIP/0ERROR/0FAIL exit0,586source/config/test+10patches stable, original23Windows skipIDs/reasons unchanged.71targeted PASS. Only3existing test/helper sources changed,2test/helper files added and singleC#checkout attribute. Runtime packages/scripts/config/nativepatches unchanged. First remote ea7b482 failure preserved; no main advancement. Next commit selected repair/docs, push same developmentbranch, require exact newSHA CI.


### Second CI timeout; bounded fixture throughput correction

Remote df121d5 failedrc124 at180seconds, not test failure. Actual structured report has3401executed/3396passed/5skipped/0failed; full gate did not complete so no main. CI image/CPU/RAM/time limits remain unchanged. Measured repeated HTTP test fixture shutdown waited default0.5s across30wire cases; only polling interval lowered to0.01, no client deadline/expected result changed. Five real idle cycles before/after and full thread exit recorded. Added explicit real-thread cleanup control; oldfixture archived and exact history binding extended. No server policy/privateinfra write or product source change. New full required.


### Full throughput-fixed suite PASS; third exact-SHA CI required

Complete Windows3402=3379PASS/23SKIP/0ERROR/0FAIL exit0,134.445seconds,586source/config/test+10patches fixed. Wire30same scenarios and51focused methodsPASS;7new portability/cleanup controls total. Runtime/CI configuration/time/cpu/memory limits unchanged. Previous secondCI has3396PASS5SKIP but overallrc124, remainsFAIL and mainunchanged. New actual loopback fixture polling removes repeated idle shutdown waits, not assertions or deadlines. Next push exact committed source and await full remote gate.
