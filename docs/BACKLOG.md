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
