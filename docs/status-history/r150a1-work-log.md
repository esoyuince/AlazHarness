# AlazHarness - status

## R150A1 - R147 self-identity patch Git integration / IN PROGRESS

Own branch alaz/d3b-self-identity-r150a1 from31e0c54. Active worktree
scratch/worktrees/d3b-self-identity-r150a1. Single claim self-identity-integration-r150.
Named Bridge lane resumed and real file reads / Git readback now work; earlier
LANE_EXPIRED not assumed still active. Existing main clean, root33user changes
verified and preserved. No root/WSL/bootstrap/mount/kernel or live service changes.

Integrate exact reviewed R147 patch (3product+2test files) into this own tree,
then full standard regression. Earlier210selected tests are historical, not full
acceptance. Prior kernel evidence must retain exact original source identity;
never relabel an old kernel run as current. Source/comments do not grant privilege.
Only fixed self UID/GID map READ_FILE opt-in, old defaults/capability checks remain.
Full results, immutable source hashes and failures retained before publication.


## Full regression in progress
Exact R147 five-file candidate integrated byte-for-byte. Request32fe6001...000006 runs full001; code/test hashes frozen632files+11patches. Expected3630cases=prior3611+19new. No WSL/root/kernel/service actions. Historical evidence hash failures must be distinguished from functional failures; never change prior expected hashes or relabel old kernel proof. Do not edit code until terminal.


## First full terminal and historical evidence maintenance
Full0013630=3587PASS23SKIP20FAIL0ERROR, command000006 exit1 observed. All19R147 tests passed, source632+patch11 stable.20failures are old-source SHA checks, rawfail log kept. Named31e0c54 exact archives for changed products/tests/helpers now resolve only matching original expected SHA; no arbitrary mismatch bypass, no old receipt digest/result rewritten. Product and original R147 tests unchanged. Targeted history/new negative tests next, then fresh full.


## Fresh final full regression in progress
Request32fe6001...000016 full002:634source/config/test files+11patches frozen. Expected3638cases=3611baseline+19R147+8new historical-binding negatives. Focused126PASS exit0, includes failed historical test files and new tests. Exact R147 five files still byte-identical; all old evidence/results/digests unchanged. One full at a time; do not edit source/test files before terminal. Real kernel/WSL NOT RUN.
