# AlazHarness continuous integration

## Scope: M0 preparation + selected-component mock tests, not full M1/M2 acceptance

The `alaz/local-ci` GitHub commit status is produced by the existing maintainer
Local CI service. GitHub is the canonical source. The service fetches a bare
mirror, checks out the event's exact SHA and runs a resource-bounded Docker job.
Only status metadata is sent back. No source push or deployment is performed.

Initial profile: immutable infrastructure image, 1 CPU, 512 MiB RAM, 768 MiB total
RAM+swap and a 180-second job timeout. Existing server-wide limits are unchanged.
The actual deployment profile and its image digest are versioned in the private
infrastructure repository; private addresses, keys and backup paths stay there.

The job runs all root `tests/test_*.py` tests through an external read-only
structured unittest reporter, then checks source-lock/gitlink consistency,
exact allowed submodule URLs, required public documents, safe example settings,
root Python syntax, JSON validity and secret/runtime file hygiene. Zero discovered
tests fail the repository gate. Reports use `.alaz-ci/`, which is Git-ignored.

The root publication gate does not initialize or build full vendor applications.
The test suite additionally executes copied OpenClaw cancellation/deadline helpers
and Hermes StdioTransport/IterationBudget with a SCRIPTED Python peer. Node 24+
is now required alongside Python 3.11+ and Git; the existing CI image supplies it.
It does not construct the real Hermes AIAgent or full OpenClaw Gateway. No pip/npm
installs, model calls, live tools, scheduler or autonomous goal loop are involved.

The copied source files are root-tracked, license-preserving components. Their
hashes and transformations are checked against config/components.lock.json in CI without
initializing submodules. `verify_components.py --with-vendor` separately checks the
original pinned local vendor bytes. Test status applies to this scoped component
slice, not to full application, sandbox, persistent recovery or learning acceptance.
Node tests are invoked one case per unittest so structured counts stay inspectable.

## Reproduce locally

```sh
python -B -m unittest discover -s tests -v
python -B scripts/ci_check.py
```

## Full pinned-source check (separate developer gate)

```sh
python -B scripts/restore_sources.py --apply
python -B scripts/verify_workspace.py --deep
python -B scripts/verify-source-snapshot.py
```

`restore_sources.py --apply` downloads only the pinned public submodules and sets
up upstream remotes. It does not install agent dependencies. It refuses dirty
source worktrees. The other two commands verify restored bytes and Git objects.

## Trust and operations

External fork PRs, drafts and PRs changing workflow files are blocked by the
server before running project code. Public contributors run tests locally; a
maintainer reviews them before execution on trusted branches. CI configuration
changes require private infrastructure review, validation, backup and exact-SHA
live acceptance. A written profile alone is not proof of a successful live run.

Do not assume this Docker job can safely execute hostile code: the trust gate is
intentional. Before opening execution to public forks, use separate disposable
workers with a separately reviewed isolation and network policy.

## Portable Node syntax gate

Node's file-extension handling for `--check file.ts` differed between the tested
Windows and Linux binaries. `scripts/check_node_syntax.mjs` now parses erasable
TypeScript with Node's built-in stripTypeScriptTypes and syntax-checks the result
as ESM on stdin, without executing the source. This is a syntax check, not a
TypeScript static type check. Runtime tests still execute the copied .ts modules.

## Integrated stdio and HTTP tests

Ten unique upstream payloads, including both licenses, are checked by the single
verify_components.py implementation. Both suites report individual unittest
cases. Use --with-vendor --source-workspace <original-workspace> to compare the
original pinned files from an isolated worktree.

The real AIAgent probe is explicitly separate: run_native_hermes_probe.py requires
an already prepared Python environment and a fresh output directory. Default CI
never installs Hermes dependencies or invokes a real model. A dependency-build
receipt is not a runtime-acceptance receipt.

## REF-PI-001 distinction

The root suite adds stdlib Python launcher guards and Node host-gate unit tests.
It does NOT install or execute Pi. Actual pinned Pi native runs are an opt-in
Windows gate via scripts/run_native_pi_suite.py and documented separately in
docs/research/REF-PI-001-NATIVE.md. Six native scenarios were repeated twice; their
12 receipts are not added to the root unittest count.

## REF-PI-002 native versus default CI

The default suite now contains171 root tests, including25 offline Durable
evidence/identity/counter guards. It does not import or run native Pi. The9
real SQLite/Harness scenarios (18 runs) are opt-in local Windows evidence and
are not included in the171 count. No server policy, dependency installer or
secret mount was added. Exact commit CI status must still be read after push.
See docs/research/REF-PI-002-SQLITE.md for scope, fault injection and limits.

## REF-PI-002B reconciliation

Both Durable characterization suites are retained with separate historical receipts.
The 4c9f suite adds storage-after-commit/ack-loss and provider identity; the ac97
suite adds a non-idempotent safe negative control and an independent SQLite effect
counter. Prior 169/171 or native18 totals are not added into a new acceptance claim.
All current standard tests will be rerun. status.md is the live handoff owner.

## REF-PI-002B separation

Root CI includes the reconciled previous validator tests and the new strict-JSON,
owner identity and independent-evidence unit tests. Native Pi admission24 runs and
independent SQLite QA12 cases are opt-in local gates, not part of the248 root tests.
The CI image/profile, resource bounds and no-install rule were not changed.

## REF-OC-001 scope

The offline suite adds21 launcher/projection/receipt tests without installing Effect or OpenCode. The35 selected-source component scenarios run twice only through the explicit prepare_opencode_components.py / run_opencode_components.py flow, using pinned Effect and fixture external services. Neither these local70 runs nor TypeScript runtime transpilation are a full OpenCode application build/typecheck/HTTP authorization test. See REF-OC-001-COMPONENTS.md.

The supplementary independent OpenCode QA adds11 offline receipt tests. Its20 source-component observations use explicit fixture ports and are a separate opt-in gate; standard CI does not run them. The final combined root suite count is recorded per exact commit, not inferred by adding native experiment totals.

## Native Gateway opt-in

`run_native_gateway.py` real Gateway boot/authority/API/read_file testidir; model sunucusu kontrollü localhosttur. `test_gateway_probe_contract.py` yalnız makbuz ve process sahiplik kurallarını offline sınar. Standart sunucu CI native Gateway ortamı kurmaz; native koşular ayrı kanıt dosyalarında tutulur. Rapor: docs/HYB-003-GATEWAY.md.

## HYB-004 process recovery

Gateway recovery native kill/reopen trials run explicitly on local Windows using
the prepared Hermes environment. Standard CI executes only offline receipt,
checkpoint, reader and launcher tests. It does not execute/kill a real Gateway.
Characterization PASS is not general recovery acceptance; orphan-reservation
semantics and arbitrary external-effect recovery remain open.

## HYB-004B scope

Standard CI tests the production recovery projection, read-only resume, local SQLite inspector and malformed/scoped evidence using synthetic stores and loopback HTTP. It does not launch the native Gateway recovery scenarios. Final native post-QA evidence is evidence/hyb-004b/final-native-suite.json; pre-QA native-suite.json remains separately versioned historical evidence. Exact standard count and commit status must be read from the actual run receipt.

## HYB-004C

Standart suite operator prepare/apply ve inspector ret kurallarını sentetik
SQLite/test-only lock substitute ile sınar; native ownership iddiası çıkarılmaz.
Native Gateway-created profile probes, gerçek lock primitive koşulları ve
sentetik DB üstündeki gerçek process-kill transaction testleri local evidence
altında ayrı tutulur. CI bunları kurmaz, paid model çağırmaz.

## HYB-005A host gate

The root suite includes real ledger/client logic with synthetic owner/fetch or
loopback fixtures. Native plugin/Gateway and selected aiohttp component probes
are opt-in separate results. No Hermes/aiohttp install is added to standard CI.
At-most-once dispatch is not token/currency budget or full M1 acceptance. See
docs/HYB-005A-HOST-GATE.md and exact evidence/hyb-005a receipts.

## HYB-005B execution slice

Default CI runs the actual policy/ledger/parser/client logic with synthetic owners
and local fixtures. It does not install Hermes/aiohttp or run native Gateway, SDK
wire-count controls or the opt-in27-case aiohttp matrix. The seven final native
scenarios and eight graceful Gateway process lifetimes are local evidence only.
An iteration-limit summary can be charged correctly while the job is incomplete;
its failed strict task-success assertion is preserved, not part of an offline
unittest failure count. Exact suite count is taken from each run receipt.

## HYB-005C read-only reporting

Root discovery exercises real report/ledger/recovery code against fresh synthetic
SQLite stores and private CLI inputs. Existing native profiles are NOT required.
The opt-in retained HYB005B profile reader is a separate check, not a new Gateway
execution. No provider call, dependency installation or sandbox guarantee is added.
Task completion, scope-wide observed usage, unknown measurements and reserved
exposure remain distinct in every report. Exact final counts/CI belong in status.md.

## HYB-005D1 validation scope

Standard discovery includes offline Docker-plan/inspect/capsule/lifecycle tests.
It does NOT require Docker or run the opt-in container probe. Native Docker
acceptance is separately recorded under evidence/hyb-005d; no Hermes Gateway,
paid model or whole-runtime credential perimeter acceptance follows from it.

## HYB-005D3A

Standard CI runs ledger/grant, replay, expiry, scoped read, client, framing,
response and lifecycle contracts with temporary stores and synthetic I/O ports.
Real Unix-socket close and native Gateway/broker/isolated-read cases run only via
explicit Linux probes against an authenticated scripted origin. They are separate
from standard suite counts; no install, Docker, paid call or new daemon is added
to ordinary CI. Final counts and exact-SHA receipts are recorded in status.md.

## R1A retained-evidence views

Standard discovery exercises exact R1 metadata and CLI behavior with fresh
synthetic SQLite fixtures. It does not need historical profiles or start an
agent/provider. Existing-report tests remain intact. The opt-in historical
verifier has explicit positive and retention-refusal expectations; a correct
expiration denial is not positive native inventory acceptance. See
docs/R1-EVIDENCE-VIEW.md and exact evidence/r1-evidence-724a receipts.

## R1B1 source capture

Standard tests cover the opt-in writer/reader and plugin bootstrap using synthetic
ports. Real Linux Gateway/broker/Docker reads remain separate opt-in evidence. No
native installation, real model or source permission is added to CI. Exact source
freeze/counts are in docs/R1B1-SOURCE-CAPTURE.md and status.md.

## R1B2 request-view scope

Standard discovery adds68 primary request/edge cases and16 independent baseline
cases.35 independent opt-in API/HTTP-handler cases are outside the standard total;
run scripts/qa/test_request_view_9b08.py and test_request_boundary_view_9b08.py with
ALAZ_R1B2_QA_SOURCE explicitly set to the reviewed checkout. Native six-case Linux
runs require the already-prepared opt-in environment and are separate from CI.
No model, SDK/Gateway installation, Docker invocation or new permission is added
to default CI. Counts/source freeze/exact commit status are recorded per run.

## DREAM-D1 scope

Default discovery adds40Dream,12CLI and10input tests (62total) with synthetic
SQLite/IPC and loopback fixtures; no native installation/inference/model billing.
32API+16HTTP independent tests are separate opt-in scripts test_dream_61a9.py
and test_dream_http_61a9.py under scripts/qa, with ALAZ_DREAM_QA_SOURCE set.
Four final Linux Gateway/broker/Docker trials use scripted synthesis and are
separate acceptance evidence. Exact counts/freeze/CI are in status.md and
docs/DREAM-D1-CANDIDATES.md, not inferred from old test totals.

## DREAM-D2A tests and accepted scope

Default Python unittest discovery includes25Review state,18host HTTP handler
and14manual loopback CLI tests (57 new cases). These run synthetic state/ports
only: no external model, no real Gateway/Docker, no autonomous scheduler, no
active memory/skills edits. Exact test counts, source SHA, exit and CI reported
in status.md/evidence/dream-d2-4b83. D2B independent task/real-model test
remains NOT RUN. `ci_check.py` static discovery != full test execution.

## DREAM-D2B1 offline evaluation

Default unittest suite adds39 pure scorer contracts +18 manual CLI/loopback
checks (57 new cases) on top of D2A 1714. No real Gateway, model or paid API
required. `ci_check.py` discovers test count but its static check is not full
unittest execution. The synthetic 8→12 result is only scripted numeric QA, not
real learning. Full source, test and CI receipts: evidence/dream-d2b-eval-8d20/.

## DREAM-D2B2 offline trial tests

Current new test scope:34 service SQL +17 HTTP +14 CLI =65 tests (included
in full unittest count ONCE). Synthetic broker `_exchange` and existing ledger
contracts, without real native Linux socket/model billing. Initial red log
preserved. Full tests and source SHA in evidence/dream-d2b2-wire-27af/.

## DREAM-D2B2-NATIVE-9C31 receipt custody and CI

Default unittest discovery adds 12 read-only JSON custody checks for three
WSL native Unix socket/local HTTP scenarios, NOT 12 more native socket runs.
Opt-in runner uses test-only stdlib HTTP upstream, not product aiohttp; actual
product Unix broker/client and native ledger/request-view remain in use.
See evidence/dream-d2b2-native-9c31/ for run and source receipts.

## DREAM-D2B2-GATEWAY-AF21 acceptance

11 offline QA policy/custody tests accompany four separately executed real
Linux Hermes Gateway + original aiohttp broker cases. They do not replay
Gateways during default unittest discovery. Test providers are scripted;
not actual model inference. Evidence and exact source hashes are under
evidence/d2b2-gateway-af21/. Full expected baseline1848+11=1859; use
full-standard.json and root-static.json for actual observed results.

## D3B credential guard checks

26 policy-only unittest cases; separate explicit Linux kernel probe with
13 child checks +3 refusal checks. No real model, no network sandbox claim.
Gateway-under-guard failed attempts retained; a passing offline CI does not
turn them into native acceptance. Evidence: evidence/d3b-credential-6e42/.

## D3B-CREDENTIAL-FIX-A613 doğrulaması

Full1903/1903 PASS,18 yeni benzersiz test dahil;269 kaynak byte-eşit.
4 native Gateway senaryosu,metadata13+17 ve eski kernel13+3 kontrolleri
ayrı çalışmalardır; unittest toplamına eklenmez. Rootstatic1903 discovery
ayrı runtime yürütme değildir. evidence/d3b-credential-fix-a613/.

## D3B1 scope

17 offline tests added; native network probe (21 checks) and four Gateway experiments are separate. No namespace creation or model call in default unittest discovery. Complete D3B and real model gates remain open. Evidence: evidence/d3b-netns-4e62/.

## D3B-JOINT-18D3 kapsamı

20 yeni çevrimdışı composition/refusal testi; network17 ve credential1903 testleri tek keşifte birleşir. Beklenen benzersiz toplam1940; gerçek full log ve exit sonucu evidence/d3b-joint-18d3/full-standard.json içinde ayrıca ölçülür. Aynı PID üzerinde4 gerçek Gateway deneyi ve15 kernel kontrol türü unittest sayısına eklenmez. Windows path choreography testlerindeki sınırlı mock, gerçek Linux kabulünün yerine geçmez.
