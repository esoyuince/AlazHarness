# AlazHarness — Güncel durum

Başlangıç: 2026-10-14. Aşama: M0 / kaynak ve çalışma alanı hazırlığı doğrulandı; çalışan hibrit henüz yok.

Varsayılan çalışma klasörü: `C:\Antigravity\AlazHarness`. Bu konuşmanın yerel araç oturumu da bu klasöre ayarlandı.

## Doğrulananlar

- Çalışma klasörü bu görev için yeni oluşturuldu.
- GitHub hesabı: esoyuince (bağlayıcı ve yerel CLI aynı hesabı bildirdi).
- İlk MVP taslağı docs/MVP-v0.1.md içinde yazıldı.
- `esoyuince/openclaw` ve `esoyuince/hermes-agent` public fork'larının doğru upstream parent ilişkileri doğrulandı; kanıt `evidence/bootstrap/forks.json`.
- `vendor/openclaw`: `2dcbb6138d57dccfcd54f2f908ef9f38268b1229`; `vendor/hermes-agent`: `eb75627faf532fa6ffbdae59a0d14b0b385fc780`.
- İki depo alt modül olarak bağlandı. Origin kullanıcı fork'u, upstream resmî kaynak; upstream push yerelde devre dışı. Kaynak kilidi `sources.lock.json`.
- Toplam 75.516 izlenen kaynak dosyası mevcut; iki kaynak çalışma ağacı temiz; Git nesne bağlantısı ve lisans hash'leri kontrol edildi. Klonlar depth=1: HEAD dosyaları yerel, bütün tarihçe/branch/tag arşivi değil.
- Node 24.19.0 ve Python 3.14.3 mevcut. OpenClaw için pnpm 12.9.0 `runtime/toolchains/` altında proje özelinde hazır, SHA512 kaynak piniyle eşleşiyor; genel pnpm 11.6.0 değiştirilmedi.
- Bağımsız kaynak denetimi 24/24 kontrol PASS; çalışma alanı denetimi 65/65 PASS; hazırlık yardımcılarının 21/21 birim testi PASS. Kaynak geri yükleme aracı yalnız plan modunda doğrulandı.
- Bu son doğrulama kanıtları: `evidence/verification-20261014-a7a90059/source-snapshot.json`, `workspace.json`, `commands.json`. Bunlar ürün veya gerçek-model testleri değildir.

## Henüz tamamlanmayanlar

Ajan bağımlılıkları kurulmadı; OpenClaw/Hermes build'i, gerçek model çağrısı, çalışan hibrit ve otonomi testi NOT RUN. Sürekli ajan/cron başlatılmadı; kişisel Hermes/OpenClaw profili kullanılmadı. Örnek ayarlar henüz bir runtime tarafından uygulanmıyor.

Ana AlazHarness deposunun GitHub uzak adresi yok; iki public fork uzaktadır. Kök deponun son commit ve çalışma ağacı durumunu her yeni oturumda `git status` / `git log -1` ile yeniden kontrol et; eşzamanlı dosya eklemelerini topluca commit etme.

Windows PATH'inde Docker yok; WSL Ubuntu mevcut fakat WSL içi runtime ve sandbox kabulü henüz test edilmedi.

## Sıradaki işlem

`HYB-001`: `docs/COMPONENT-MAP.md` başlangıç haritasını sabit kaynak kodundan ayrıntılandır; OpenClaw olay/harness girişi ile Hermes programatik yürütme sınırının dosya, sembol, bağımlılık, izin/iptal/oturum ve mevcut test kanıtlarını çıkar. En dar gerçek bileşen birleşimini seç; ardından sahte modelle tek işin uçtan uca turunu kur. Otonomi katmanı M1 çalışan hibrit kabulünden sonra (M2).
