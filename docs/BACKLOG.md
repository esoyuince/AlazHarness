# AlazHarness başlangıç iş sırası

Ana hedef: docs/MVP-v0.1.md. Güncel gerçekleşen durum: status.md. Aşağıdaki sıra bir plan; tüm satırlar otomatik tamamlanmış değildir.

| İş | Çıktı | Kabul |
|---|---|---|
| BOOT-001 | Düzenli kök, MVP, Git, iki fork/klon, kaynak kilidi | Hazırlık denetimi ve kayıtları |
| HYB-001 | Sabit commit bazlı modül/bağımlılık haritası | OpenClaw olay girişi ve Hermes programatik yürütme sınırına dosya/simge/test kanıtı |
| HYB-002 | Tek yürütücü protokolü ve sahte model adaptörü | start/events/status/cancel/resume ve unsupported testleri |
| HYB-003 | Gerçek kaynak bileşenlerinden ilk uçtan uca tur | Tek olay, tek iş, tek yetkili durum sahibi |
| HYB-004 | Kalıcılık ve kesinti sonrası uzlaştırma | Restart/duplicate/uncertain-effect negatif testleri |
| HYB-005 | Ayrı state, araç izinleri, iptal ve bütçe | Limit ve yetki ihlali negatif testleri |
| HYB-006 | Yeni oturumda hafıza/beceri kullanımı | Kayıt + bağımsız yeniden kullanım kanıtı |
| HYB-007 | Yerel ve sağlayıcı model adaptörü | Model değişse de kimlik/hedef/hafıza devamı |
| HYB-008 | M1 kabul paketi | Tüm M1 senaryoları; ayrı mock ve gerçek-model raporları |
| AUTO-001 | İhtiyaçtan hedef adayları ve öncelik | M1 sonrası; seçme/sürdürme/bırakma gerekçeleri |
| AUTO-002 | Bağımsız öğrenme deneyi | Aynı model/bütçe ile baseline ve tutulmuş transfer görevleri |

## Integrated checkpoint

HYB-001/002 source layout and transport candidates are reconciled. Both contract
suites are retained; common code has one owner. HYB-003 native-engine acceptance
is tracked separately in CURRENT-STATE.md. Full OpenClaw ingress, real Hermes
HTTP Gateway, crash recovery, isolation, budgeting, memory transfer and M2 are
not closed by the merged mock suites.

## Additional source review — 2026-10-15

Pi and OpenCode are reference candidates only. Source-level assessment:
`docs/research/PI-OPENCODE-REVIEW.md`. Follow REF-PI-001 (native tool parity),
REF-PI-002 (durable crash/replay contract), REF-OC-001 (permission/event contracts)
before adopting components. These are NOT RUN, not replacements for open HYB gates.

## REF-PI-001 local runtime checkpoint

The six low-level Pi Agent/provider/read-tool scenarios passed twice locally (12 runs).
See docs/research/REF-PI-001-NATIVE.md. No Pi SDK-session/Durable or engine replacement
acceptance. Next: REF-PI-002. Standard CI only runs host/launcher unit contracts.

## REF-PI-002 SQLite / ac97 sonucu

Dokuz native senaryo iki tekrarda18/18 PASS;25 yeni offline guard ile171/171 kök test. Süreç kill/reopen ve bağımsız dış etki sayaçları: docs/research/REF-PI-002-SQLITE.md. Bu davranış incelemesidir; aynı-key farklı-payload conflict şartı FAIL ve safe işareti tek dış etki garantisi değil. Sonraki REF-PI-002B: kalıcı içerik parmak izi / dış etki sözleşmesi, tek oturum yazarı. Ürüne benimseme ve M1/M2 açık; paralel dal sonuçları otomatik birleştirilmez.

## REF-PI-002B reconciliation

Both Durable characterization suites are retained with separate historical receipts.
The 4c9f suite adds storage-after-commit/ack-loss and provider identity; the ac97
suite adds a non-idempotent safe negative control and an independent SQLite effect
counter. Prior 169/171 or native18 totals are not added into a new acceptance claim.
All current standard tests will be rerun. status.md is the live handoff owner.

## REF-PI-002B yerel kabul — 2026-10-15

Atomik içerik/iş-kabulü24/24 native ve248/248 birleştirilmiş standart test PASS;
bağımsız owner/atomic QA12/12 ayrıca PASS. Üretim benimsemesi/M1/M2 açık.
Güncel rapor REF-PI-002B-ADMISSION.md; sıradaki seçim kapısı REF-OC-001.
Bu sayılar önceki karakterizasyonlara eklenmez; CI sonucu tam commit'te doğrulanır.

## REF-OC-001 component checkpoint

Selected source Permission/EventFeed behavior:35 cases x2 local passes, explicit fixture dependencies. Full OpenCode HTTP/server/DB acceptance remains open. Report: docs/research/REF-OC-001-COMPONENTS.md. MVP direction: docs/adr/0003-mvp-single-runtime.md. Next HYB-003-GATEWAY uses existing Hermes as the sole runtime, not four stacked agent loops.

## HYB-003-GATEWAY

Native Gateway/Authority/API sınırı için normal, lost-ack ve stop deneyleri eklendi. Exact sonuç: evidence/hyb-003-gateway. Tam M1 kapalı değil. Sonraki kapı HYB-004-GATEWAY-RECOVERY: aynı profilde kill/reopen, epoch ve belirsiz dış etkiyi yeniden uzlaştırma.

## HYB-004 Gateway recovery

Native process recovery characterization is in docs/HYB-004-GATEWAY-RECOVERY.md.
A confirmed orphan reservation between the two native stores blocks general
automatic recovery acceptance. HYB-004B: explicit canonical-admission proof and
orphan/unknown reconciliation, without blind key deletion or POST replay.
External-effect-before-result, retention expiry and multi-process fencing remain open.

## HYB-004B host reconciliation

Readonly host projection and scoped local inspection: docs/HYB-004B-RECONCILIATION.md. No automatic repair; orphan reservation remains an operational blocker. HYB-004C is explicit owner-bound operator reconciliation, never an implicit POST or key deletion.

## HYB-004C explicit closure — 2026-10-15

Dar operator abandon_unadmitted closure uygulandı;604 offline/3native ayrı PASS.
Native interrupted/key retention değişmedi. Sonraki HYB-005-HOST-GATE: tek host
start sınırı closed/unknown/retention kararını uygulamalı; ardından gerçek araç
izinleri ve tüm provider çağrısı bütçesi. Yeni model motoru veya scheduler yok.
Kapsam/kanıt status.md ve HYB-004C raporunda; Git/CI ayrıca doğrulanır.

## HYB-005A continuation

One-use host admission is implemented on the existing native owner; acceptance
status is in status.md and docs/HYB-005A-HOST-GATE.md. Final native probe results
and exact-commit CI must be checked, not inferred from the old604 test total.
Next: HYB-005B execution-boundary model/tool permission and complete provider
budget accounting. No optional-hook exception may be the sole veto.

## HYB-005B final qualification — 2026-10-16

Physical local-provider attempt reservations and guarded native file tools are
implemented. Applied live-config drift correction and final native evidence are
in docs/HYB-005B-EXECUTION-GATE.md. Seven narrow budget/tool scenarios; six strict
outcome rechecks plus one explicitly incomplete iteration-summary characterization.
Full standard and same-commit CI are recorded in status.md after they complete.
Next HYB-005C: distinguish ledger physical usage/reservation from native run
aggregate and incomplete-task outcome; then qualify isolated provider credentials,
remote model/tariff/capability, egress and remaining M1 permission limits.
No new autonomous scheduling starts before M1; memory transfer HYB-006 remains open.

## HYB-005C local reporting — 2026-10-16

Read-only task/native usage/profile-ledger exposure report and explicit scope-only
CLI are implemented in docs/HYB-005C-HOST-REPORT.md. V1 claims are NOT retroactively
attributed to runs. Missing usage remains unknown; reports grant no action/refund.
Final test/publication status is in status.md. Next HYB-005D: credential/egress
isolation and qualified provider capabilities/tariffs, not an autonomous scheduler.
Future HTTP reporting and trusted per-run call binding are explicit follow-ups.

## HYB-005D1 Linux tool-process slice

Opt-in credential-free/network-none Docker tool backend implemented; exact tests
and publication in status.md and HYB-005D-TOOL-ISOLATION.md. Not yet wired to
Hermes native dispatch. Next HYB-005D2: existing admission/budget/tool binding,
no host fallback, cancellation and separate provider credential/egress custody.
Parent hard-crash cleanup, Windows native and full M1/M2 remain OPEN.

## HYB-005D3A local provider broker

Private Unix credential broker and native-owner one-use egress grants implemented;
exact acceptance/publication is in status.md and HYB-005D3-PROVIDER-BROKER.md.
This does not claim whole-Gateway OS/network isolation. Next D3B is the explicit
OS credential/egress boundary, then real-provider model/tariff/token qualification.
Legacy direct mode is not brokered. No new autonomous scheduler starts.

## R1A retained-evidence reporting — 2026-10-17

Opt-in metadata over verified native terminal records is implemented;
see docs/R1-EVIDENCE-VIEW.md. No source-file or provider-wire coverage is
invented. Model visibility remains unknown; selection is local metadata only.
Targeted reader/CLI tests and historical-expiration denials are separate
from fresh native/real-model acceptance. R1B trusted capture/request linkage
and in-retention native evidence remain OPEN. Current full-suite/Git/CI
status is in status.md; D3B/HYB006/M1/M2 are not closed by this slice.

## R1B0 fresh native evidence qualification

R1A positive inventory is qualified on two fresh, in-retention Windows native
profiles; metadata does not establish source coverage or wire visibility.
See docs/R1B0-NATIVE-EVIDENCE-ACCEPTANCE.md. Next R1B1 source-capture binding,
then R1B2 normalized provider-view binding; D3B and M1/M2 remain open.

## R1B1 trusted input capture

Opt-in isolated source snapshot and redacted return binding use the existing
native state owner. Acceptance is in docs/R1B1-SOURCE-CAPTURE.md. Next R1B2 is
provider request-view binding; full capture is not full output or model visibility.
D3B, real provider, HYB006, M1/M2 remain open. Git/CI is tracked in status.md.

## R1B2 normalized provider request views

Opt-in broker request metadata is implemented; see docs/R1B2-REQUEST-VIEW.md.
Prepared canonical content, write-ahead handoff intent, signed broker HTTP response
observation and provider validation are distinct. Source provenance does not
establish request initiator or model processing. Continue D3B OS credential/egress
and qualified real-provider acceptance; R2 independent goal verification and
HYB006 skill transfer must preserve these evidence boundaries. Full M1/M2 open.

## DREAM-D1 manual candidate maintenance

User-prioritized first Dream slice: manual bounded terminal-history synthesis,
exact evidence citations, persistent candidates and no active-memory promotion.
See docs/DREAM-D1-CANDIDATES.md. Reuses one native owner and budgeted broker.
Next DREAM-D2 qualifies real synthesis/candidate review and only then memory
adoption; no automatic triggers or M2 goal selection enabled. D3B, actual
model/price/token bounds and HYB006 transfer remain open. Git/CI in status.md.

## REF-CODEX-001 static Codex desktop/CLI reference — 2026-10-17

Sixth external harness reference, NOT a new runtime adoption. Installed stable
Codex 26.1013.3656.0 and open-source codex Rust pinned source were reviewed
separately. Report: docs/research/REF-CODEX-001-APP-REVIEW.md; metadata evidence:
evidence/ref-codex-001-c7a1/. Main insight for Dream D2 is two-stage
rollout extraction + serialized diff-based consolidation, with an independent
verification and candidate promotion gate unique to Alaz. Also relevant:
ThreadStore single writer and agent mail accepted/consumed/wake distinctions.
No product/CLI/dependency/scheduler changes; candidate acceptance scenarios
are NOT RUN. Continue Dream-D2 minimal usable learning loop, D3B and HYB006.

## DREAM-D2A manual review and net-delta — 2026-10-17

Opt-in candidate review, decision event CAS, no-change diff and loopback CLI
implemented on the existing D1 native state owner. `accept_for_testing` is not
an evidence of truth, independent evaluation, memory adoption or learned skill.
See docs/DREAM-D2-REVIEW.md. Next D2B: locked held-out evaluation, measured
transfer on unseen task, memory conflict reconciliation; D3B OS/network
boundary and provider price/token verification remain open.

## DREAM-D2B1 — paired held-out offline scorer (18 October 2026)

Implemented manual private oracle-key→sealed held-out plan→paired baseline/candidate
answer scoring without new model, DB or scheduler. D2A review revision is reread
from local authenticated Gateway before sealing and scoring; model-response JSON
is explicitly UNVERIFIED. See docs/DREAM-D2B-HELDOUT-EVAL.md. Next D2B2
requires provider provenance and D3B OS egress, then D2B3 actual transfer on
new held-out tasks; no automatic memory/skill promotion.

## DREAM-D2B2 local-broker paired evidence pilot — 2026-10-18

New opt-in trial service reuses existing native ExecutionLedger and request-view
broker response receipts for baseline/candidate two-arm cases, and a private
operator score client. No new model inference truth claims or active memory.
See docs/DREAM-D2B2-PAIRED-BROKER.md. Next: actual Linux native socket and
Gateway acceptance, then D3B/real provider bounded learning/heldout transfer.

## DREAM-D2B2-NATIVE-9C31 — scoped Linux broker acceptance (18 October 2026)

Real Linux Unix-socket broker subprocess, native SQLite ledger and D1/D2A/D2B1/D2B2;
test-only stdlib local HTTP upstream: normal, candidate disconnect and revoked review
PASS. Real Hermes Gateway, production aiohttp upstream, Docker and real model
remain NOT RUN because WSL lacks dependencies and vendor checkout. See
docs/DREAM-D2B2-NATIVE-SOCKET.md. Next: source-pinned isolated native Hermes
Linux environment, full Gateway and production broker acceptance.

## DREAM-D2B2-GATEWAY-AF21 — 18 October 2026

Actual pinned Hermes Gateway + unchanged aiohttp broker now passes normal,
budget-limit, candidate-disconnect and review-revoked scripted localhost
scenarios. D1 source is an actual native terminal response, no seeded DB.
See docs/DREAM-D2B2-FULL-GATEWAY.md and evidence/d2b2-gateway-af21/.
Next: D3B OS/network and real provider contract, controlled actual model
held-out experiment; cross-epoch Dream recovery and Docker combined path
remain OPEN. No active memory/skill promotion.

## D3B-CREDENTIAL-6E42 — complementary filesystem pilot

Opt-in ABI3 Landlock guard, native child denial/read/write checks and isolated
launcher implemented. Prepared full Gateway under guard still FAIL at startup.
Do not conflate with concurrent D3B-NETNS-4E62 network work; own root mirror
not overwritten. See docs/D3B-CREDENTIAL-GUARD.md. Full D3B remains OPEN.

## D3B-CREDENTIAL-FIX-A613 — korumalı Gateway kabulü

4/4 gerçek Gateway+orijinal broker senaryosu dosya koruması açık PASS;
1903/1903 çevrimdışı test (18 yeni dahil). Kaynakları bayt-eşit Linux
kopyasından çalıştırma, isteğe bağlı dar self metadata, özel XDG socket
dizini ve salt-okunur MIME tablosu; önceki FAIL kanıtları korunur.
Sonraki: network+filesystem ortak entegrasyon ve broker-ledger otoritesi.
Tam D3B/gerçek model/öğrenme NOT ACCEPTED. docs/D3B-CREDENTIAL-STARTUP.md.

## WRONGSTACK-REVIEW-AAC6 — seçici uyarlama önerileri (18 Ekim 2026)

Rapor docs/WRONGSTACK-REVIEW.md; upstream ffbd572d,MIT,workspace1.1.8.
Runtime/test/model çalıştırılmadı; üçüncü temel motor eklenmedi. Anti-loop,
mission/plan/settlement ownership, koşullu SAGE geri bildirimi ve verifier
lease aday. Otomatik YOLO yetki artışı, doğrulamasız hedef kapanışı ve
policy-only sandbox Alaz'a taşınmaz. Ortak D3B önceliği korunur.

## D3B1 network namespace — 18 October 2026

Opt-in rootless user/network namespace, zero capabilities, no_new_privs and inherited seccomp added. Direct TCP/UDP/alternate-family and exec-child tests; actual Gateway with original host broker requalified. Host UID/filesystem/path Unix services remain shared: complete D3B NOT ACCEPTED. Next deny-by-default filesystem/PID/credential separation. See docs/D3B1-NETWORK-NAMESPACE.md.

## D3B-JOINT-18D3 — ortak koruma kabulü

Ağ namespace/seccomp ve credential Landlock aynı Gateway sürecinde4/4 native PASS;15 canary türü her koşuda ayrı ölçüldü. Full regresyon/published CI aşağıdaki iş kaydından takip edilir. Primitive kodları değişmedi; rapor docs/D3B-JOINT-BOUNDARY.md. Sonraki kritik iş: Gateway-writable durumdan bağımsız broker bütçe otoritesi; UnixIPC/PID/hostUID sınırları ayrı. WrongStack anti-loop sonraki küçük davranış adayı; fullD3B/gerçekmodel henüz kabul değil.
