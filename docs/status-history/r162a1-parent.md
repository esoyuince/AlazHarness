# AlazHarness — status

## R161A1 — servis profil/config kaynak kapısı PASS

P1 DONE; P2 IN PROGRESS. P3–P5, tam D3B, M1 ve production OPEN.

- Aktif dal: `alaz/p2-service-profile-r161a1`.
- Aktif çalışma ağacı: `C:\Antigravity\AlazHarness\scratch\worktrees\p2-service-profile-r161a1`.
- Başlangıç: `5b7eba4d97f63623c20b51f476f4bf36ba6e7d94`.
- İlk kaynak commit'i: `5f038cd5ea49177c10a4e42717b016eb86268e6f`; ilk CI FAIL kaydı korunur.
- Kabul edilmiş kaynak/düzeltme commit'i: `92c53fc12844d312f93b289259775f463f2a0238`.
- Native seçim değişmedi: `5e3635c2cdfc2161fd20c089618bd7f2a7c12f2d`, 760 dosya.
- Kapanış commit'i, exact CI ve main aktarımının terminal makbuzu:
  aktif çalışma ağacında `scratch/r161a1-publication/final-publication.json`.
  Bu belgeyi taşıyan commit de kendi tam CI sonucu olmadan main'e aktarılmaz.

### Tamamlanan iş

Ayrı `hermes-service-profile-v1`, typed config beklentisi ve 64 KiB canonical
JSON kabulü eklendi. Config ve dört yardımcı dosya bounded/no-follow/nonblocking
FD okumalarıyla denetlenir. Kaynak seçimi ile home, üç DB, önceki epoch/instance
ve config hash/device/inode/size bağları host/target projection, ayrı 16 KiB
servis handoff'u ve özgün startup/consumer boyunca korunur.

Execution boundary gerçek native loader'ın önünde/arkasında config'i, gerçek
config yolunu, HERMES_HOME ve dosyayı atlayan worker snapshot durumunu denetler.
Worker thread ana thread'e bağlı lease/SQLite yöntemlerini çağırmaz. Eski
finite/readiness/retained seçimleri ve native source pin'leri değişmedi.

Config byte drift yeni işi durdurur; özgün receipt ve sahiplik korunuyorsa
bilinen detach/üç store kapanışı sürer. Mevcut HERMES_HOME/lease retleri korunur.
Eksik owner typed ret verir; receipt kaldırılması servis guard'ını kapatamaz.

### Test ve kanıt

| Kapsam | Doğrulanmış sonuç |
|---|---|
| Son odaklı Linux | 306/306 PASS, 0 SKIP, 7.155s, failure/error 0, exit 0 |
| Aynı seçim primary Windows | 306 test: 298 PASS, 8 platform SKIP, 10.358s, failure/error 0, exit 0 |
| Gerçek aiohttp importu engelli dar kontrol | 49/49 PASS; fixture kaldırıldı, fail/error/skip 0 |
| `92c53fc` tam kök/bileşen CI | 4.302 test: 4.280 PASS, 22 SKIP; 305.340s; failure/error 0, exit 0 |
| Aynı CI statik gate | 6.815 dosya, 10 bileşen, 2 Git linki, 4.302 test keşfi; PASS |
| Kaynak geçmişi | 6 parent arşivi Git 5b7eba4 ile byte-exact; güncel dört pin ayrı |
| Korunan çalışma | 8 depo, kökün 33 değişmiş dosyası ve 760 native kaynak eşleşti |

Windows'taki POSIX FIFO/link/owner ve symlink fixture atlamaları Linux'ta geçti.
Native constructor/loader ve kernel uçları ilgili testlerde explicit doubles;
gerçek dosya/FD, worker thread ve SQLite close gözlemleri kaynak fixture
kapsamındadır. Yeni kurulu servis, gerçek kernel veya model kabulü değildir.

İlk tam CI'deki 18 ERROR / 22 SKIP (4302 test, 308.090s, exit 1) silinmedi.
17 hata optional aiohttp import fixture'ı, 1 hata eksik owner için bounded ret
sırasıydı. Test atlamadan ve CI bağımlılığı yüklemeden dar düzeltme yapıldı.
Geniş scratch socket koşusunun EPERM ve kesilmiş route koşuları da başarılı
gate sayılmadı. İlk checkpoint kaynak hash'leri kendi sürümüne aittir.

Kaynak CI status `57365201257`, delivery
`1bd87354-d206-11f1-8ab8-707145c4fcfb`: authenticated GitHub durumu, aynı
checkout/source SHA, ham log, tam suite, statik gate ve container cleanup
birlikte doğrulandı. Son kapanış commit'inin CI kanıtı
`scratch/r161a1-publication/accepted-final-ci.json` içindedir. Main push aynı
commit'in doğrulanmış sonucunu kullanırsa bu ikinci tam koşu diye sayılmaz;
ayrı `accepted-main-ci.json` ve final yayın makbuzu ile bağlanır.

Kanıtlar: [son Linux](evidence/p2-service-profile-r161a1/focused-linux-repaired.json),
[son Windows](evidence/p2-service-profile-r161a1/focused-windows-repaired.json),
[ilk CI hatası](evidence/p2-service-profile-r161a1/initial-ci-failure.json),
[düzeltme](evidence/p2-service-profile-r161a1/repair-check.json),
[kabul edilmiş kaynak CI](evidence/p2-service-profile-r161a1/source-ci.json).
Rapor: [R161A1](docs/P2-SERVICE-PROFILE-R161A1.md).

### Kesin sonraki adım

Sabit projected service receiver/factory'yi özgün BorrowedServiceOwner ve
R160 lifecycle kontrolüne bağla. Ardından canlı supervisor Unix sunucusu,
child final/exit/EOF ile volume stop/finish ve host görev erişimi tamamlanır.
Native effective-config, backup/restart/capture ve yeni P2 kurulum kabulü açıktır.
Kaynak profil snapshot'ı her eşzamanlı aynı-UID ABA yarışını dışlama iddiası değildir.

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

- 2026-10-27 ikinci yayın: `92c53fc` normal push ile gönderildi. 16 dar
  düzeltme/kanıt dosyası değişti; toplam sahipli dosya 43. Statik gate 81.387s,
  6.815 dosya, 10 bileşen ve 4.302 test keşfiyle PASS. `repair-commit.json` ve
  `repair-push.json` terminal PASS; yeni tam CI RUNNING, main değişmedi.

- 2026-10-27 kaynak CI kabulü: `92c53fc` için 4.302 test / 4.280 PASS /
  22 SKIP ve statik gate PASS. Status, ham log ve server metadata eşleşmesiyle
  `accepted-source-ci.json` üretildi ve public source-ci.json ile birebir
  bağlandı. Kapanış paketi yalnız bu rapor/durum/CI kaydını ekler; ürün kodu
  değişmez. Kapanış ve main sonucu yukarıdaki terminal makbuzlara yazılır.
