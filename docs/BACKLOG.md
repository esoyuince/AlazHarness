# AlazHarness başlangıç iş sırası

Ana hedef: docs/MVP-v0.1.md. Güncel gerçekleşen durum: CURRENT-STATE.md. Aşağıdaki sıra bir plan; tüm satırlar otomatik tamamlanmış değildir.

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

## 2026-10-15 component-slice checkpoint

HYB-001: source/symbol/ownership map and first selected copies are implemented.
HYB-002: start/events/status/cancel and explicit unsupported-resume are implemented
for a bounded process-local SCRIPTED peer. This is a protocol slice, not full
runtime acceptance. HYB-003 remains open: enter the real public AIAgent path with
an isolated mock model and qualify full OpenClaw host integration. HYB-004/005/006
are not closed by fixture cancellation or process-local idempotency tests.

Work is on a separate reviewed branch because parallel changes appeared in the
original checkout. Do not merge or delete that other implementation implicitly.
Compare the branches and choose one owner per responsibility before integration.
See docs/HYB-001-COMPONENT-SLICE.md and CURRENT-STATE.md.
