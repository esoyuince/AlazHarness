# AlazHarness — status

## R163A1 — özgün supervisor ve Unix kontrol sunucusu — kaynak/ilk CI PASS; yayın IN PROGRESS

P1 DONE; P2 IN PROGRESS. P3–P5, tam D3B, M1 ve production OPEN.

- Aktif dal: `alaz/p2-service-supervisor-r163a1`.
- Aktif çalışma ağacı: `C:\Antigravity\AlazHarness\scratch\worktrees\p2-service-supervisor-r163a1`.
- Başlangıç ve yayımlanmış main: `dc1ccb5ecf4e9741f6fd828a03e8ebed7f9497b7`.
- Önceki R162 final günlüğü: `scratch/r162a1-publication/final-publication.json`
  (R162 çalışma ağacı), SHA-256 `7522fe8ea5267866a1a5de82368148c9a1452f7b50bf406cc46b44dd3bf33314`.
- Native seçim: `5e3635c2cdfc2161fd20c089618bd7f2a7c12f2d`, 760 dosya; değişmedi.
- Önceki durumun tam kaydı: [R162 parent](docs/status-history/r163a1-parent.md).

### Amaç ve kapsam

[Entegrasyon planının](docs/P2-SERVICE-INTEGRATION-R161A1-PLAN.md) üçüncü adımı:
özgün ServiceVolumeSupervisor begin/attach/start akışı içinde tek sabit servis
çocuğunu sahiplenmek ve R160 CLI için özel Unix kontrol sunucusunu bağlamak.
Aynı Popen ve ServiceChannel korunur; PID/startTicks/token eşliği mutation
öncesinde doğrulanır. Kaybolan start/close yanıtı ikinci child veya cleanup
başlatmaz; status yalnız özgün işlemin mevcut kanıtını okur.

Child final/exit/EOF ile volume stop/finish bağlantısı dördüncü adımdır ve bu
pakette açık kalır. Child kapanışı tek başına dış CLOSED veya imaj lease release
kanıtı değildir. Host görev erişimi, yeni P2 kurulumu ve gerçek model kabulü açıktır.

### Başlangıç doğrulaması

R162 final günlüğü beklenen hash ile eşleşti. Main ve R162 HEAD dc1ccb5, çalışma
ağaçları temiz. Korunan sekiz depo, kökün 33 değişmiş dosyası ve önceki R161/R160
çalışma ağaçları eşleşti. Native 760 kaynak byte'ı ve remote ref'ler değişmedi.
Yerel kaynak seçiminin 873 dosyası aynı base Git blob'larıyla birebir doğrulandı.
Yeni izole dalın oluşturulması ve başlangıç kayıtları
`scratch/r163a1-publication/` altında izlenir.

### Test ve yayın

R163 ürün kaynakları ve bağımsız inceleme PASS. Son birleşik Linux seçimi
721/721 PASS; 0 SKIP/failure/error, exit 0, 34,652970 saniye. 25 ürün dosyası,
42 test/destek dosyası ve runner hashleri koşu öncesi/sonrası aynı. Gerçek Unix
socket, SO_PEERCRED, Node CLI ve scripted child pipe entegrasyonu bu kapsamdadır;
kernel/native kurulum kabulü değildir. Primary Windows aynı 721 testte 608 PASS
ve 113 platform SKIP; failure/error 0, exit 0, 30,781900 saniye. JSON ve ham log
byte'ları geri okunup aynı kaynak/test/runner ve ordered test ID seçimine bağlandı.
Kaynak commit'i `35f4fd6f4d6d42de9322dd55c636cbf25ef61137` normal feature push ile
doğrulandı. Statik gate PASS; 4.481 test keşfedildi. Aynı commit'in
`alaz/local-ci` tam çalışması PASS: 4.481 test, 4.459 PASS,
22 SKIP, failure/error 0; 308.335 saniye, container exit 0,
OOM/timeout false ve cleanup removed. Status `57385451563`, delivery
`64501c92-d222-11f1-944d-affa131d6a9f`. Authenticated GitHub gözlemi, remote artifact,
ham log ve suite sayıları aynı exact commit'e bağlandı. Public kayıt
`evidence/p2-service-supervisor-r163a1/source-ci.json` kabul makbuzuyla byte-exact.

Bu takip kaydı source CI kabulünden sonra hazırlanmıştır. Kapanış commit'inin
kendi tam CI'si, main fast-forward/push, ayrı main verified-success reuse ve final
integrity sonucu henüz bu snapshot'ta NOT RUN. Kesin yayın sonucu
`scratch/r163a1-publication/final-publication.json` ile tamamlanır.
Yeni kurulum, native servis çalıştırma veya model/sağlayıcı çağrısı yoktur.

### Kesin sonraki adım

Yalnız status, R163 raporu ve public source-ci için kapanış commit'i/push;
aynı ürün/test byte'larında exact-commit tam CI; pre-main integrity; normal
main fast-forward/push; ayrı main CI verified-success reuse; final integrity
ve terminal işlem günlüğü. Kaynak yayınından sonra planın dördüncü adımı olan
özgün volume stop/finish bağlantısına geç. Native/model kabulü halen açık.

### İş günlüğü

- 2026-10-27 başlangıç: R162 final journal ve canlı repository/file durumu
  doğrulandı. Base dc1ccb5 üzerinden R163 izole çalışma açıldı. Supervisor,
  Unix protokolü ve tarihsel kaynak koruması ayrı çalışma kapsamlarına ayrıldı.
  Sonucu belirsiz eski mutation veya devam eden R162 CI işi bulunmuyor.
- 2026-10-27 Linux checkpoint: özgün child sahipliği, sabit bootstrap, Unix
  server ve CLI entegrasyonu tamamlandı. Epoch preflight, yabancı actor ve
  reentrant dispatch kaydı bulguları giderildi. Bağımsız kaynak review PASS;
  birleşik son kaynak seçimi 721/721 PASS. Final/exit/EOF sonrası dış durum
  DRAINING kalır; volume stop/finish bağlantısı dördüncü adımdır.
- 2026-10-27 Windows checkpoint: primary çalışma ağacındaki aynı ürün/test/runner
  byte'larında 608 PASS + 113 platform SKIP. 721 ordered test ID seçimi Linux ile
  aynı; iki ham log hash ve uzunlukları doğrulandı. Kaynak/test byte'ları sabit.
  Public source-check kaydı hazırlanıyor; commit/push/tam CI henüz NOT RUN.
- 2026-10-27 kaynak yayın checkpoint: 30 açık dosya stage edildi; diff ve byte
  eşliği PASS. Statik gate 4.481 test keşfetti, exit 0. Kaynak commit 35f4fd6
  normal push sonrası remote feature ref ile eşleşti; main dc1ccb5 olarak kaldı.
  Required `alaz/local-ci` çalışıyor. Native işlem makbuzu
  `c163a101-1027-4a01-8000-000000000026` terminal completed/exit0; tekrar edilmez.
- 2026-10-27 source CI checkpoint: 35f4fd6 exact-commit tam CI
  4481/4459/22 total/PASS/SKIP, failure/error 0,
  exit 0 kabul edildi. Kabul makbuzu SHA-256
  `82a169dd23876ffdfe4160d841bbcecd6a7400805e897d908343ded2579e3078`. Source CI kabul işlemi
  `c163a101-1027-4a01-8000-000000000039` terminal completed/exit0.
  Sonraki closure yalnız durum/rapor/CI kanıtı değiştirir; ürün/test byte'ları aynı.
