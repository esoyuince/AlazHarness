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
