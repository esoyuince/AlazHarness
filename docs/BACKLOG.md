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

## Ek kaynak karşılaştırması — 2026-10-15

| İş | Durum | Çıktı / kabul |
|---|---|---|
| REF-000 | STATİK İNCELEME TAMAM | Pi/OpenCode resmî kimliği, sabit kaynakları, seçili kod/test sözleşmeleri ve lisansları kaydedildi; uygulamalar çalıştırılmadı. |
| REF-PI-001 | NOT RUN | Pi Durable gerçek kurucu + betiklenmiş model + gerçek zararsız araç; aynı/değişmiş içerik, güvenli/güvensiz tekrar, gözlem iptali ve tek depolama sahibi. |
| REF-OC-001 | NOT RUN | OpenCode gömülü SDK + betiklenmiş model; gerçek izin reddi, kapanış ve yeniden açma; aynı kabul matrisi. |
| REF-DEC-001 | AÇIK | Hermes/Pi/OpenCode deney sonuçlarını bağımlılık, gerekli yama, model isteği ve kesinti doğruluğuyla karşılaştır; tek yetkili motor seçimi gerekirse güncellensin. |

Ayrıntı: `research/PI-OPENCODE-REVIEW.md`. HYB-003 Gateway zinciri ve HYB-004/005/006 kabulü bu incelemeyle kapanmadı.
