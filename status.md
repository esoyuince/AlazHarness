# AlazHarness — status

## R161A1 — dar CI düzeltmesi ve odaklı gate PASS; tam CI PENDING

P1 DONE; P2 IN PROGRESS. P3–P5, tam D3B, M1 ve production OPEN.

- Aktif dal: `alaz/p2-service-profile-r161a1`.
- Aktif çalışma ağacı: `C:\Antigravity\AlazHarness\scratch\worktrees\p2-service-profile-r161a1`.
- Başlangıç/main: `5b7eba4d97f63623c20b51f476f4bf36ba6e7d94`.
- Native seçim: değişmemiş `5e3635c2cdfc2161fd20c089618bd7f2a7c12f2d`, 760 dosya.
- İş makbuzları: aktif çalışma ağacında `scratch/r161a1-publication/`.
- Kaynak commit: `5f038cd5ea49177c10a4e42717b016eb86268e6f`; feature push terminal PASS.
- İlk tam CI `5f038cd` için FAIL: 4.302 test, 18 ERROR, 22 SKIP; main başlangıç commit'inde.
- 17 hata test HTTP import fixture'ı, 1 hata legacy partial consumer'ın bounded ret sırası içindir.

### Tamamlanan kaynak bağlantısı

Ayrı `hermes-service-profile-v1`, typed config beklentisi ve 64 KiB canonical
JSON okuması eklendi. Config ve dört yardımcı okuma bounded/no-follow/nonblocking
FD ile denetlenir. Hash/device/inode/size ve kaynak seçimi host/target projection,
ayrı servis handoff'u ve özgün NativeStoreStartup/PreparedRuntimeConsumer boyunca
korunur. ExecutionBoundary worker thread'de gerçek native config yolu ve worker
snapshot yolunu kontrol eder; gerçek loader çağrısının iki yanında config'i
yeniden denetler. Default finite/readiness/retained seçimleri değişmedi.

Config byte drift yeni admission'ı durdurur. Özgün receipt/lease korunuyorsa
bilinen detach ve üç store kapanışı mümkün kalır. Mevcut HERMES_HOME/lease
sahiplik retleri devam eder; snapshot'lar her eşzamanlı ABA yarışının kanıtı değildir.

### Test ve kaynak kanıtı

| Kanıt | Sonuç |
|---|---|
| Son odaklı Linux | 306/306 PASS, 0 SKIP, 7.155s, failure/error 0, exit 0 |
| Aynı seçim primary Windows | 306 test: 298 PASS, 8 platform SKIP, 10.358s, failure/error 0, exit 0 |
| Yeni beş test modülü | 133 test; birleşik seçime dahil |
| Tarihsel kaynak koruması | 6 arşiv gerçek Git 5b7eba4 ile byte-exact; güncel pinler ayrı |
| Korunan çalışma | 8 depo ve kökün 33 değişmiş dosyası eşleşti; native 760 kaynak eşleşti |
| Son exact-commit tam CI / yayın | İlk `5f038cd` FAIL korunuyor; düzeltme odaklı PASS, yeni tam CI PENDING |

Windows'taki POSIX FIFO/link/owner ve symlink fixture atlamaları Linux'ta geçti.
Native constructor/loader ve kernel portları ilgili testlerde doubles'tır;
gerçek dosya/FD, worker thread ve SQLite close gözlemleri kaynak fixture
kapsamındadır. Geniş scratch socket koşusunun EPERM başarısızlıkları ve kesilmiş
R159 route koşusu başarılı gate olarak sayılmadı; raporda ayrı korunur.

Kanıtlar: [Linux](evidence/p2-service-profile-r161a1/focused-linux-repaired.json),
[Windows](evidence/p2-service-profile-r161a1/focused-windows-repaired.json),
[Git/koruma kontrolü](evidence/p2-service-profile-r161a1/parent-source-check.json).
Rapor: [R161A1](docs/P2-SERVICE-PROFILE-R161A1.md).

### Açık kapsam ve kesin sonraki adım

Kaynak commit/push tamamlandı. Tam repository CI'nin exact SHA sonucunu
doğrula; kapanış kaydı commit'ini de aynı gate'ten geçirip normal fast-forward
ile main'e yayımla. Devamında sabit
projected service receiver/factory, canlı supervisor Unix sunucusu,
child final/exit/EOF ile volume stop/finish ve host görev erişimi tamamlanır.
Native effective-config, backup/restart/capture ve yeni P2 kurulum kabulü açıktır.

Yeni kurulum veya gerçek sağlayıcı/model çağrısı yapılmadı. R156 kurulumu
değiştirilmedi. Gerçek modelden önce model/sağlayıcı, araçlar ve bütçe seçilecek.
R161 entegrasyon planı ve P2 bu kaynak teslimatıyla kapanmaz.

Plan: [R161A1](docs/P2-SERVICE-INTEGRATION-R161A1-PLAN.md).
Önceki durum: [R160](docs/status-history/r161a1-parent.md).
Yol haritası: [PRODUCT-ROADMAP](docs/PRODUCT-ROADMAP.md).

### İş günlüğü

- 2026-10-27 başlangıç: R160 terminal yayın makbuzu ve canlı Git durumu
  doğrulandı; main `5b7eba4` tabanından izole R161 çalışma ağacı açıldı.
- 2026-10-27 kaynak incelemesi: profil iki kez denetleniyor; startup ve
  prepared consumer exact owner/receipt bağı istiyor. Servis seçiminin bu
  zincire açık taşınması ve eski kaynak kanıtlarının korunması kararlaştırıldı.

- 2026-10-27 ara kontrol: sürümlü servis profili, projection ve ayrı exec
  codec uygulandı. Config ve yardımcı profil okumalarında O_NONBLOCK ile FIFO
  değişimi reddedildi. Native get_hermes_home context override ve worker config
  snapshot yolunun servis loader guard'ına ayrıca bağlanması sürüyor. Windows
  kaynak aktarımı ve tam CI henüz NOT RUN; commit/push yapılmadı.

- 2026-10-27 odaklı gate: yedi ürün dosyası donduruldu; bağımsız kaynak
  incelemesi tamamlandı. 293 testlik Linux/Windows seçimleri ve Git kaynak
  arşiv kontrolü terminal PASS. Tam CI öncesi kendi dosyaları gözden geçiriliyor.

- 2026-10-27 yayın başlangıcı: ilk Windows statik taraması 50 saniye sınırında
  kesildi (test sonucu değildir); ikinci koşu 46.207s içinde 6.808 dosya,
  10 bileşen, 4.302 test keşfiyle PASS. Yalnız 36 sahipli dosya commit edildi.
  `5f038cd` feature dalına normal push ile gönderildi; CI status57363472085
  RUNNING. Main değişmedi. İşlem makbuzları `source-commit.json`,
  `source-push.json` ve `pre-publication-checks.json` içinde terminaldir.

- 2026-10-27 ilk tam CI: 4.302 test/308.090s, 18 ERROR ve 22 SKIP, exit 1.
  17 test minimal CI'de aiohttp import'u bulamadı; 1 mevcut c127 testi yeni
  consumer guard'ında `_owner` yokken bounded ret yerine AttributeError gördü.
  Ham log ve iki neden `evidence/p2-service-profile-r161a1/initial-ci-failure.json`
  ile korunur. Consumer ret sırası ve açık no-network test portları dar
  düzeltmedir; atlama veya CI bağımlılık yüklemesi yapılmayacak.

- 2026-10-27 dar düzeltme: consumer owner yokluğu bounded ret ile kapanır;
  aktif receipt kaldırılması guard'ı kapatamaz. HTTP import fixture portları
  gerçek bind'i korur ve HTTP çalıştırmayı reddeder. 49 ilgili test gerçek
  aiohttp importu engelliyken PASS. Mevcut 13 C127 work-guard testi eklenmiş
  son odaklı seçim Linux 306 PASS; Windows 298 PASS/8 SKIP. Yeni consumer
  SHA `a39245d9` için bağımsız inceleme ve sabit current-source pin güncellendi.
