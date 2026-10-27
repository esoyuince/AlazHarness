# AlazHarness — status

## R160A1 — servis kontrol bileşenleri: odaklı kaynak PASS, CI düzeltmesi IN PROGRESS

P1 DONE; P2 IN PROGRESS. P3–P5, tam D3B, M1 ve production OPEN.
Bu paket uzun ömürlü servisin kaynak bileşenlerini tamamlar; günlük kurulu
başlat/görev/izle/iptal/kapat kabulü henüz tamamlanmadı.

- Aktif dal: `alaz/p2-supervised-service-r160a1`.
- Aktif çalışma ağacı: `C:\Antigravity\AlazHarness\scratch\worktrees\p2-supervised-service-r160a1`.
- Başlangıç: `60853416eed945fcbecb3c1be9da162020da8014`.
- Native seçim: R159'un değişmemiş 760 dosyası, `5e3635c2cdfc2161fd20c089618bd7f2a7c12f2d`.
- Kesin yayın zinciri: aktif çalışma ağacındaki `scratch/r160a1-publication/`.
  Sonuç dosyası `final-publication.json`; varlığı, hedef SHA ve terminal PASS
  gözlenmeden commit/push/CI tamamlandı sayılmaz.

### Tamamlanan kaynak işi

Özgün BorrowedServiceOwner için bounded ready/reply/final kontrolü, zaten
sahip olunan süreç için pipe gözlemcisi, açık owner kimliğine bağlı CLI
start/close/service-status istemcisi ve ayrı uzun ömürlü volume worker eklendi.
Mevcut finite/readiness worker'ı ve özgün volume begin/attach/stop/finish
sırası korunur. Yeni queue, sonuç store'u veya model çağrısı yoktur.

Kaybolan yanıt otomatik tekrar üretmez. Salt okunur gözlem kalan giriş
byte'larını da göndermez. Native CLOSED kaydı tek başına volume kapama izni
vermez; bu kanal her durumda `volumeMayClose:false` bildirir.

Bağımsız kaynak incelemesinde iki sorun düzeltildi: gözlenmiş child exit
sonrasında eski READY durumu ve supervisor kimliğinin yalnız yanıt sonrasında
kontrol edilmesi. Üç deterministik exit testi eklendi; CLI istekleri artık
sunucunun işlemden önce kontrol etmesi gereken exact expectedOwner taşır.
Dokuz eski owner isteği fixture'da sıfır lifecycle etkisi üretti. Canlı
supervisor sunucusu henüz uygulanmadığından bu sonuç source/fixture kapsamındadır.

### Doğrulanan testler

| Koşu | Sonuç | Kanıt |
|---|---|---|
| Son Linux odaklı koşu | 83/83 PASS; fail/error/skip0, exit0 | `evidence/p2-service-control-r160a1/focused-linux.json` ve `.log` |
| Windows taşınabilir odaklı koşu | 83 toplam: 36 PASS, 47 platform SKIP; fail/error0, exit0 | `evidence/p2-service-control-r160a1/focused-windows.json` ve `.log` |
| Bağımsız inceleme | İki somut bulgu düzeltildi; kaynak sınırları açık | `evidence/p2-service-control-r160a1/review.json` |
| Tam proje CI | İlk420ec0e koşusu FAIL: 4.167 toplam, 1 failure, 22 skip, exit1; fixture düzeltmesi sürüyor | `evidence/p2-service-control-r160a1/initial-ci-failure.json` |
| Yeni kurulu servis / gerçek sağlayıcı | NOT RUN; provider/model çağrısı0 | P2 açık |

Linux toplamı: 26 child +21 parent +24 CLI +12 volume. Gerçek geçici socket,
pipe ve fixture çocukları kullanıldı; native lifecycle ve kernel sınırları
açık doubles ile sınandı. Yeni mount/cgroup/namespace veya gerçek native
kurulum kabulü çıkarılmaz. İlk79 koşusu ayrıca korunur. Scratch ortamındaki
R159 host tanı koşusunun exit124 timeout'u PASS sayılmaz.

### Açık kapılar ve kesin sonraki iş

Mevcut finite/retained allowlist, native model loader'ın beklediği config.yaml
dosyasını kabul etmiyor. Ayrı service profile/config admission sözleşmesi
uygulanmalı; guard sonrasında dosya ekleyerek bu sınır aşılmamalı. Ardından
sabit projected service factory, özgün supervisor Unix sunucusu, child final
ile volume stop/finish bağlantısı ve özel loopback'e host görev erişimi
birlikte bağlanmalı. Sonrasında yeni tek P2 kurulumu ve seçilmiş bütçeli model
kabulü gelir. Model/sağlayıcı ve harcama sınırı henüz seçilmedi.

Rapor: [R160A1](docs/P2-SERVICE-CONTROL-R160A1.md).
Sonraki plan: [R161A1](docs/P2-SERVICE-INTEGRATION-R161A1-PLAN.md).
Yol haritası: [PRODUCT-ROADMAP](docs/PRODUCT-ROADMAP.md).

### İş günlüğü

- 2026-10-27 başlangıç: R159 yayın makbuzu ve canlı main `6085341` doğrulandı;
  temiz tabandan izole R160 çalışma ağacı açıldı. Önceki son durum
  [r160a1-parent.md](docs/status-history/r160a1-parent.md) içinde korundu.
- 2026-10-27 ara kontrol: source kontrol bileşenleri ve yeni worker uygulandı;
  bağımsız inceleme düzeltmeleri tamamlandı. Son83 Linux testi geçti.
- 2026-10-27 aktarım: 11 source/test dosyası hash kontrollü biçimde primary
  çalışma ağacına aktarıldı. Windows36 PASS +47 platform SKIP, exit0.
  Commit, feature push ve exact-commit tam CI kapanışı sırada.
- R156 kabul edilmiş kuruluma, kişisel agent state'ine, native fork main'ine
  veya kökün eşzamanlı33 dosyasına bu paket kapsamında yazılmadı.

- 2026-10-27 reset sonrası devam: yeni yetkili Bridge oturumu açıldı;
  primary R160 HEAD ve canlı origin/main hâlâ `6085341`. Stage boş, yeni
  commit/push yok. İki odaklı koşunun 11 dosya hash'i ve ham logları yeniden
  doğrulandı; kaynaklar değişmemiş. Kökün korunacak33 dosyası birebir eşleşti;
  native `5e3635c` ve main çalışma ağaçları temiz. Yayın işi IN PROGRESS.

- 2026-10-27 yayın hazırlığı: yeni worker sonundaki tek fazla LF temizlendi;
  product davranışı değişmedi. Son hashlerle Linux83 PASS ve Windows36 PASS
  +47 platform SKIP yeniden gözlendi. Ham logların Git blob'larında aynı
  byte'larla korunması için yalnız R160 evidence kapsamına kural eklendi.

- 2026-10-27 yayın kontrolü: static gate PASS; 6.776 dosya denetlendi,
  4.167 test keşfedildi. Kaynak commit'i `420ec0e85c17e8dae72a859deec01f86de74a80b`
  oluşturuldu ve feature dalına normal push doğrulandı. Main hâlâ başlangıç
  `6085341` üzerindedir. Bu commit'in tam `alaz/local-ci` koşusu bekleniyor;
  statik keşif tam test çalıştırması sayılmadı.

- 2026-10-27 ilk tam CI: `420ec0e` için 4.167 test, 292.451s; 4.144 PASS,
  22 SKIP ve tek `test_eof_required` failure, exit1. 60ms içinde server'ın
  isteği görmesi varsayımı 1 CPU koşusunda sağlanmadı (calls0). Sonuç korunur;
  EOF kuralını zayıflatmadan gerçek veri/EOF handshake'i ile fixture düzeltilecek.
  Main ilerletilmedi. Kayıt: `evidence/p2-service-control-r160a1/initial-ci-failure.json`.

- 2026-10-27 EOF fixture düzeltmesi: tam client frame gözlendi; data handler
  ve promise reaksiyonlarından sonra sonuç hâlâ pending iken EOF açıkça
  bırakıldı. CLI24/24, tekCPU+iki test yükü altında EOF20/20 ve birleşik
  Linux83/83 PASS; aynı son kaynaklarla Windows36 PASS +47 SKIP, exit0.
  Ürün timeout veya EOF doğrulaması değişmedi. Kaynak onarım commit'i ve
  onun tam CI koşusu sırada. Ek kanıt: `eof-cli.json/log`, `eof-load.json/log`.
