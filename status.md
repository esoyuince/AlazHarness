# AlazHarness — status

## R163A1 — özgün supervisor ve Unix kontrol sunucusu — IN PROGRESS

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
Exact-commit tam CI henüz NOT RUN. Önceki R162 kapanışı yeni kaynak başarısı sayılmaz.
Yeni kurulum, native servis çalıştırma veya model/sağlayıcı çağrısı yoktur.

### Kesin sonraki adım

Son kaynak seçiminde statik gate, normal feature push, exact-commit tam CI ve
main yayın kapanışı. Sonucu belirsiz mutation yoktur. Kaynak yayınından sonra
planın dördüncü adımı olan özgün volume stop/finish bağlantısına geç.

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
