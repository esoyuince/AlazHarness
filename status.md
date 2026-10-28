# AlazHarness — R166A1 P2 servis kaynak paketi hazırlığı

**IN PROGRESS — R166 kaynak yayın paketi ve tam CI aşaması. Servis kaynak paketi hazırlığı PASS; R166 yayın kabulü henüz NOT RUN.**

P1 DONE; P2 IN PROGRESS. P3–P5, tam D3B, M1 ve production OPEN.

- Amaç: P2 adım 6 için ayrı service candidate kaynak seçimi ve salt okunur doğrulama bağı.
- Kaynak tabanı: R165 final `1600eba430562795b9114209d1168bfa0d6ea5fd`; primary main aynı commit'tedir.
- Aktif primary: `C:\Antigravity\AlazHarness\scratch\worktrees\p2-service-candidate-r166a1`; dal `alaz/p2-service-candidate-r166a1`, başlangıç HEAD `1600eba430562795b9114209d1168bfa0d6ea5fd`. Yeni çalışma ağacı başlangıçta temiz doğrulandı.
- Geçici yerel hazırlık: `/workspace/scratch/ea99314b5e4a/AlazHarness-R166` (Git checkout değil; primary nesnelerinden gerçek paket üretimi ayrı kapıdır).
- R165 kapanışı PASS: final integrity ve terminal journal tamamlandı; main CI status `57429769016`, delivery `73f4c7de-d26c-11f1-984d-2e32e229aea0`, aynı commit için doğrulanmış final CI yeniden kullanımı. Terminal journal SHA-256 `34bf70efdd2d642b671c648cf57a65bff0f4b35270f3838d4309d4e7984b7f60`.
- Önceki durumun exact yerel arşivi: [r166-parent](docs/status-history/r166-parent.md).
- Aktif rapor: [R166 servis kaynak paketi](docs/P2-SERVICE-CANDIDATE-R166A1-REPORT.md).
- Yayın öncesi durumun exact arşivi: [r166-pre-publication](docs/status-history/r166-pre-publication.md).

## Kaynak yayını başlangıcı

- Canlı başlangıç kontrolü PASS: aynı base/branch, boş stage, altı beklenen dosya değişikliği; 18 korunan depo, kökteki 33 mevcut değişiklik, 760 native dosya ve uzak Git referansları doğrulandı.
- Yayın çalışma kayıtları `scratch/r166-publication` altındadır. `baseline.json` SHA-256 `e6d521ced6578b0b9206aaf2565041550ab76f5fca5092c714a9d7a8e59d0930`; gerçek tamamlanmış başlangıç komutu `c166a101-1028-4a01-8000-000000000005`, exit 0.
- Güncel 94-test yayın kontrolü PASS: Linux 94 RUN /94 PASS /0 SKIP, 24.51232 s; Windows 94 RUN /74 PASS /20 mevcut Linux-only SKIP, 307.510766 s. Her iki koşumda 0 FAIL /0 ERROR, exit 0; aynı 79 girdi ve koşucu değişmedi. Tam kayıt/loglar `evidence/p2-service-candidate-r166a1` altındadır. Önceki 30-test hazırlık kayıtları korunur.
- Source statik kapı/commit/push/tam CI, closure commit/final CI, main ve terminal yayın kaydı henüz NOT RUN. Gerçek kurulum veya model kabulü bu kaynak yayınının kapsamına eklenmedi.

## Sınırlar

Eski finite builder/installer, 756 native dosyalı seçim ve R156 kurulumu korunur. Yeni kaynak yolu service native `5e3635c2cdfc2161fd20c089618bd7f2a7c12f2d` ve 760 dosyaya bağlanır. Servis giriş/config, recovery destek dosyaları ve Node 24 CLI import kapanışı açık seçilir. Yeni araçlar builder ve verifier'dır; installer içermez. Model/provider çağrısı, gerçek kurulum, deploy veya çalışma zamanı ayar değişikliği bu hazırlıkta yoktur.

## Şimdiki kontrol sınırı

- Yeni kaynak/test dosyaları: `scripts/build_service_candidate.py`, `scripts/verify_service_candidate.py`, `tests/test_service_candidate.py`.
- Son test dosyası `01eecade206c607aae3aa2075b91872dfb708aeb1436f69ef7b8d35fb772e54b` ile yerel yeni odaklı koşum: 30 RUN /30 PASS /0 SKIP /0 FAIL /0 ERROR, exit 0, 7.890 saniye. Windows primary aynı test dosyası: 30 RUN /30 PASS /0 SKIP /0 FAIL /0 ERROR, exit 0, 46.297002 saniye; kaynak hashleri değişmedi.
- İlgili eski builder/installer ile birleşik yerel koşum: 94 RUN /94 PASS /0 SKIP /0 FAIL /0 ERROR, exit 0, 33.366 saniye. Bu tarihsel sonuç taşınabilirlik düzeltmesinden önceki `40c3c8f88476d73eb5024cd4bfbce4cc8317ea01da6630ebba33dab809173bc6` test dosyasına aittir; son dosyayla birleşik tekrar yapılmış sayılmaz.
- Önceki fazla geniş yerel regresyon: 120 RUN /114 PASS /6 ERROR, exit 1. Kısmi snapshot'ta bulunmayan tarihsel kanıt dosyaları nedeniyle başarısızdır; başarılı sayılmaz. Tam log alınmadığı sınırı hazırlık notunda korunur.
- Primary kaynak aktarımı, gerçek Git nesnelerinden paket üretimi ve bağımsız hashlerle `prepare_bytes` doğrulaması PASS. Paket: 760 native +117 harness +1 bağımlılık referans haritası, toplam 878 dosya. Kaynak commit'i `1600eba430562795b9114209d1168bfa0d6ea5fd`; native `5e3635c2cdfc2161fd20c089618bd7f2a7c12f2d`.
- Paket adresi: `scratch/service-candidates/r166a1-primary-01`. Manifest SHA-256 `a3fde8b0ac808c375c4ecd0eab9f26938828b0d01cd4632ffa4234e47de38af8`; arşiv SHA-256 `43fc186b8f21e4f39e34364ae100c82e520317d6b06c8a100b29f3b26adcd56a`.
- Kanıtlar: `scratch/r166-source-preparation/primary-source-observation.json`, `primary-source-verified.json`, `focused-windows-01.json` ve tam `.log`; gerçek Bridge makbuzları aynı klasördedir. İlk yerel hazırlık notları değiştirilmeden korunur; son test için `test-portability-addendum.json` kullanılır. Son koruma/teslim kaydı `primary-checkpoint.json` dosyasındadır.
- R166 commit/push/tam CI/yayın NOT RUN. Runtime seçimi/readback, bağımlılıkların gerçek kuruluma kabulü, service/kernel/model kabulü OPEN. Dosya-CLI doğrulaması POSIX yolunu kullanır; bellek içi `prepare_bytes` ayrı doğrulama girişidir.

## Kesin sonraki adım

Hashleri sabitlenen sahiplenilmiş kaynak/rapor/arşiv/kanıt dosyaları için statik/source kapısını, normal source commit/push ve mevcut tam CI politikasını uygula. Henüz commit edilmiş veya yayımlanmış R166 varmış gibi devam etme. Sonraki kurulum diliminde Python 3.12/Node 24 dosya kimliklerini ve readback'i, 1162 bağımlılık referansının gerçek baytlarını ve servis için yeterliliğini doğrula; R156'yı koruyan yeni hedef için installer tasarla. Ardından gerçek service/kernel ve yapılandırılmış model kabulü ayrı kanıtlarla ilerler.

## İş günlüğü

- 28 Ekim 2026: Bridge yeniden canlı doğrulandı. R165'in gerçek terminal sınırı canlı Git ve makbuzlardan geri alındı; tamamlanmış Git/CI işlemleri tekrarlanmadı. Main CI kuyruğu beklenirken bağımsız kaynak paketleme hazırlığı başlatıldı. Kaynak/test/kanıt aktarımı ve tam yayın ayrı kapılardır.
- 28 Ekim 2026: R165 terminal kapanışı tamamlandı. R166 yeni çalışma ağacı exact final commit'te oluşturuldu; başlangıç temizliği, eski araç hashleri ve parent status hash'i primary üzerinde doğrulandı. Bağımsız kaynak incelemesindeki üç eksik destek dosyası ve arşiv padding kontrolü düzeltildi. Primary aktarımı ve gerçek kaynak paketi kontrolüne geçildi.
- 28 Ekim 2026: Primary gerçek kaynak paketi 878 dosyayla üretildi ve dört dış kimlik/hash bağı üzerinden doğrulandı. Yeni testin case-collision fixture'ı immutable Git tree nesneleriyle taşınabilir yapıldı; son dosya Linux yerel ve Windows primary odaklı koşumlarında 30/30 PASS verdi. Kurulum/model çalıştırılmadı; R166 kaynak yayını sonraki ayrı kapıdır.
- 28 Ekim 2026: Kaynak yayını başlatıldı. Canlı Git/hash/uzak-ref başlangıç kontrolü PASS; önceki hazırlık durumu exact arşivlendi. LICENSE, SECURITY.md ve docs/THIRD-PARTY.md yerel kısmi snapshot'a exact base Git baytlarıyla tamamlandı; bunlar yeni ürün değişikliği değildir. Yayın yardımcıları bağımsız incelemede, aynı seçime bağlı odaklı yayın kanıtları hazırlanıyor.

- 28 Ekim 2026: Güncel kaynak yayın koşucusu bağımsız incelendi; aynı 94 test Linux'ta 94 PASS, Windows primary'deki ayrı windows-02 koşumunda 74 PASS /20 mevcut Linux-only SKIP verdi. İlk Windows denemesi dış 300 saniyelik sınırda kesildi; final sayacı bilinmeyen bu denemenin gerçek başarısız makbuzu ve eksik logu ayrıca korunur. Yeniden denemeden önce aynı koşucu sürecinin bulunmadığı doğrulandı; tam CI politikası değişmedi. 79 girdi/koşucu hashleri değişmedi; tamamlanan koşumların tam logları ve gerçek Windows makbuzu kaynak kontrolüne bağlandı. Statik kapı ve Git/CI yayını ayrı sonraki işlemlerdir.
