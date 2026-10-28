# AlazHarness — R166A1 P2 servis kaynak paketi hazırlığı

**IN PROGRESS — R166 kaynak commit/push ve source tam CI PASS. Bu checkpoint final CI, main ve terminal yayın kabulünden önceki sabit handoff kaydıdır.**

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
- Kaynak commit/normal push ve source tam CI PASS: `6d65f66ba961f1390e3d44e34a0207f367a5de89`, 4677 RUN /4644 PASS /33 SKIP /0 FAIL /0 ERROR, container exit 0. Closure/final CI, main ve terminal kayıt bu checkpoint hazırlanırken NOT RUN. Gerçek kurulum veya model kabulü bu kaynak yayınının kapsamına eklenmedi.

## Source CI kabulü ve sabit kapanış sınırı

- Kaynak commit: `6d65f66ba961f1390e3d44e34a0207f367a5de89`; source CI kabul zamanı: `2026-10-28T04:02:12.999395+00:00`.
- Gerçek tam suite: 4677 RUN /4644 PASS /33 SKIP /0 FAIL /0 ERROR; süre 380.213 s. Statik keşif 4677; timeout/OOM yok, container kaldırıldı. Sonuç önceki bir delivery'den yeniden kullanılmadı.
- GitHub `alaz/local-ci` success status ID `57436285811`; delivery `6de92cf4-d280-11f1-8f48-26660b4477f2`. [Exact source CI kaydı](evidence/p2-service-candidate-r166a1/source-ci.json), private kabul dosyasının aynı baytlarıdır; SHA-256 `c374d361d719bc59a20890b71ae797cb4a9498ff7ecf25f433ea231960d85f7a`.
- CI politika SHA-256 `39feb838fe28d4176b40dc99d8dcc824648c1b374a3d168ef0e4a23bdade4776`; mevcut tam CI politikası değişmedi. Bu source/fixture CI sonucu gerçek kurulum, native service, kernel veya model kabulü değildir.
- İlk stage preflight denemesi (`024`) Git `check-ignore` çağrı uyumsuzluğunda native exit 2 ile reddedildi; index değişmedi. İkinci stage denemesi (`027`), korunmuş eksik Windows logunun 83. satırındaki trailing whitespace nedeniyle iki exact add işleminden sonra native exit 2 ile durdu. Her iki başarısız makbuz ve eski helper/contract/intent değişmeden saklandı.
- Ayrı incelenen recovery, mevcut 19-file index'i yeniden add etmeden doğruladı. Tam whitespace kontrolü gerçek exit 2 olarak kalır; yalnız `evidence/p2-service-candidate-r166a1/focused-windows.log` dosyasının exact `68f1a2bc6b97187199f16e384b52b83ee381f648e9403fd4292e794ef606fe96` baytlarına bağlı tek bulgu kabul edilir, kalan 18 yolun kontrolü exit 0'dır. Ham log düzeltilmedi veya kırpılmadı. Bu nedenle tüm denenmiş işlemler PASS değildir; sonraki kabul edilmiş recovery/yayın zinciri ayrı tutulur.

Bu sürümlenen checkpoint source CI kabulünden sonra, closure/final CI ve main işlemlerinden önce hazırlandı. Final CI, main yayını/main CI ve terminal kayıt burada NOT RUN olarak sabittir. Sonraki gerçek sonuçların yetkili kaydı `scratch/r166-publication/final-publication.json` olacaktır; bu dosyanın varlığı veya PASS sonucu bu checkpoint tarafından varsayılmaz.

## Kaynak commit/push gözlemlerinin ayrı uzlaştırması

- İlk kaynak commit çağrısı (`033`) native exit 2 ve `gitMutationAttempted=false` olarak kaldı. `035` salt okunur gözlemi bu denemenin etkisini ayrıca uzlaştırdı.
- Daha sonraki `036` çağrısında gerçek source commit ve normal push alt komutlarının her biri exit 0 döndü. Üst işlem, sonraki salt okunur uzak-ref gözlemi tamamlanamadığı için native exit 2 ile kaldı; `036` başarılı native işlem olarak yeniden sınıflandırılmadı.
- `038` ve `040` salt okunur kayıtları ile özgün commit/push dönüşleri değişmeden korundu. Ayrı incelenen tamamlayıcı, commit veya push'u tekrarlamadan güncel uzak ref'leri ve korunması gereken çalışma alanlarını doğruladı.
- İlk tamamlayıcı `055`, geçmiş `040` gözleminin iki ref'ini dokuz ref'lik tam koruma kümesiyle karşılaştıran önkoşul denetiminde native exit 2 ile reddedildi; reservation veya yeni remote-read kaydı oluşmadı. `056` bunu salt okunur olarak doğruladı. Sonraki incelenmiş sürüm source push makbuzundaki iki ref'i, ayrıca korunan dokuz ref'in tamamından ayrı doğrular. `055` makbuzu SHA-256 `cb5bccb595c5a6ae7b4fded8ded11b5a1604193cecf1c677789580639e6074a5` ile saklanır.
- Gerçek tamamlayıcı işlem `c166a101-1028-4a01-8000-000000000059` native exit 0 ile tamamlandı. Bu tamamlamanın kayıt SHA-256 değeri `8a2aa9e355cb697cbda319f50f05fa34fabdaf1c077f0366e8c26fa60f6c64ed`; ayrı recovery proof SHA-256 değeri `b7f4ef1037c29990f055356752408c8da656a74bbf0a4cf967fa738755d25dbb` ve source-push.json SHA-256 değeri `dfe135bbecf42e00ddc7552ba16a068bcdc4820e258818a6d1053ebd3e9f41e9` olarak bağlıdır.
- Supplemental contract SHA-256 `6bbedb4c9be4c9f534be9496af0a080a611cf1f219916741a181dde3e884b03e`. Özgün `033` ve `036` makbuzları sırasıyla `007995a6736c506ea8891a1e2c48771fa1d658269fed8c56af1b36236493fd40` ve `7eeb7a87e2e4c8d4292b01dbcb7e21bfec4b2073618d8610df0e7e9897b431e5` hash'leriyle korunur. Tüm denenmiş işlemler PASS değildir; yeni tamamlayıcının başarı iddiası yalnız doğruladığı salt okunur uzlaştırmaya aittir.

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
- R166 kaynak commit/push ve source tam CI PASS; final CI/main/terminal yayın kabulü bu checkpoint içinde NOT RUN. Runtime seçimi/readback, bağımlılıkların gerçek kuruluma kabulü, service/kernel/model kabulü OPEN. Dosya-CLI doğrulaması POSIX yolunu kullanır; bellek içi `prepare_bytes` ayrı doğrulama girişidir.

## Kesin sonraki adım

Kabul edilen source CI kaydını içeren üç dosyalık closure commit/push adımını tamamla; ardından aynı final commit için ayrı ve yeniden kullanımsız tam CI kabulünü al. Sonra main fast-forward/normal push, ayrı main CI makbuzu ve final integrity/terminal journal sırasını uygula. Bu sonraki adımlar bu checkpoint içinde yapılmış sayılmaz. Sonraki kurulum diliminde Python 3.12/Node 24 dosya kimliklerini ve readback'i, 1162 bağımlılık referansının gerçek baytlarını ve servis için yeterliliğini doğrula; R156'yı koruyan yeni hedef için installer tasarla. Ardından gerçek service/kernel ve yapılandırılmış model kabulü ayrı kanıtlarla ilerler.

## İş günlüğü

- 28 Ekim 2026: Bridge yeniden canlı doğrulandı. R165'in gerçek terminal sınırı canlı Git ve makbuzlardan geri alındı; tamamlanmış Git/CI işlemleri tekrarlanmadı. Main CI kuyruğu beklenirken bağımsız kaynak paketleme hazırlığı başlatıldı. Kaynak/test/kanıt aktarımı ve tam yayın ayrı kapılardır.
- 28 Ekim 2026: R165 terminal kapanışı tamamlandı. R166 yeni çalışma ağacı exact final commit'te oluşturuldu; başlangıç temizliği, eski araç hashleri ve parent status hash'i primary üzerinde doğrulandı. Bağımsız kaynak incelemesindeki üç eksik destek dosyası ve arşiv padding kontrolü düzeltildi. Primary aktarımı ve gerçek kaynak paketi kontrolüne geçildi.
- 28 Ekim 2026: Primary gerçek kaynak paketi 878 dosyayla üretildi ve dört dış kimlik/hash bağı üzerinden doğrulandı. Yeni testin case-collision fixture'ı immutable Git tree nesneleriyle taşınabilir yapıldı; son dosya Linux yerel ve Windows primary odaklı koşumlarında 30/30 PASS verdi. Kurulum/model çalıştırılmadı; R166 kaynak yayını sonraki ayrı kapıdır.
- 28 Ekim 2026: Kaynak yayını başlatıldı. Canlı Git/hash/uzak-ref başlangıç kontrolü PASS; önceki hazırlık durumu exact arşivlendi. LICENSE, SECURITY.md ve docs/THIRD-PARTY.md yerel kısmi snapshot'a exact base Git baytlarıyla tamamlandı; bunlar yeni ürün değişikliği değildir. Yayın yardımcıları bağımsız incelemede, aynı seçime bağlı odaklı yayın kanıtları hazırlanıyor.

- 28 Ekim 2026: Güncel kaynak yayın koşucusu bağımsız incelendi; aynı 94 test Linux'ta 94 PASS, Windows primary'deki ayrı windows-02 koşumunda 74 PASS /20 mevcut Linux-only SKIP verdi. İlk Windows denemesi dış 300 saniyelik sınırda kesildi; final sayacı bilinmeyen bu denemenin gerçek başarısız makbuzu ve eksik logu ayrıca korunur. Yeniden denemeden önce aynı koşucu sürecinin bulunmadığı doğrulandı; tam CI politikası değişmedi. 79 girdi/koşucu hashleri değişmedi; tamamlanan koşumların tam logları ve gerçek Windows makbuzu kaynak kontrolüne bağlandı. Statik kapı ve Git/CI yayını ayrı sonraki işlemlerdir.

- 2026-10-28T04:02:12.999395+00:00: R166 kaynak commit `6d65f66ba961f1390e3d44e34a0207f367a5de89` için source tam CI kabul edildi: 4677 RUN /4644 PASS /33 SKIP /0 FAIL /0 ERROR; status `57436285811`, delivery `6de92cf4-d280-11f1-8f48-26660b4477f2`. Exact kabul baytları public source-ci.json'a alındı. İlk Windows 300 saniyelik timeout denemesi, bilinmeyen final sayaçları ve eksik loguyla ayrı tutuldu; tarihsel kayıtlar değiştirilmedi. Bu üç dosyalık kapanış final CI/main/terminal kabulünden önceki handoff sınırıdır.
