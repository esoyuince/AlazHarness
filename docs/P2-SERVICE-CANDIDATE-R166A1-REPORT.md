# R166A1 — P2 servis kaynak paketi hazırlığı

## Sonuç ve kapsam

Servis nesli için ayrı kaynak paketi builder'ı ve salt okunur verifier hazırdır. Gerçek primary Git nesnelerinden üretilen 878 dosyalık paket doğrulandı. Son yeni test dosyası Linux yerel ve Windows primary koşumlarında 30/30 PASS verdi.

Bu, P2 adım 6'nın kaynak hazırlığı ve R166 kaynak yayın paketidir. Güncel dosyalarla Linux/Windows odaklı yayın kontrolleri PASS; source statik kapı, commit/push, tam CI ve ana dal yayını henüz NOT RUN. P2 IN PROGRESS. Gerçek kurulum, runtime seçimi/readback, servis bağımlılık kabulü, service/kernel ve model kabulü OPEN. Paket veya fixture testi, bu kabul alanlarını tamamlanmış yapmaz.

Aktif dal `alaz/p2-service-candidate-r166a1`; primary çalışma ağacı `C:\Antigravity\AlazHarness\scratch\worktrees\p2-service-candidate-r166a1`. Başlangıç HEAD `1600eba430562795b9114209d1168bfa0d6ea5fd` ve ilk çalışma ağacı temizliği doğrulandı. R165 terminal yayın günlüğü SHA-256 `34bf70efdd2d642b671c648cf57a65bff0f4b35270f3838d4309d4e7984b7f60` ile kapanmıştır.

## Neden ayrı paketleme yolu gerekiyor?

Korunan finite builder/installer 756 native dosyalı önceki nesle bağlıdır. Servis yolu native `5e3635c2cdfc2161fd20c089618bd7f2a7c12f2d` commit'ini ve 760 dosyayı kullanır. Yeni builder bu nesli, üç servis girişini, seçim/config/host-lock dosyalarını, Node CLI importlarını ve gerekli execution/recovery destek dosyalarını açıkça seçer. Eski iki araç değişmeden kalır; hash ile sabitlenmiş saf yardımcı işlevleri kullanılır.

`scripts/build_service_candidate.py`, immutable Git nesnelerini okur ve yalnız yok olduğu doğrulanmış, ignore edilmiş `scratch/service-candidates` hedefinde çıktı üretir. `scripts/verify_service_candidate.py` içindeki `prepare_bytes`, manifest SHA-256, arşiv SHA-256, harness commit ve native commit olmak üzere dört zorunlu dış kimlik bağı ister. Kaynaklar çıkarılmaz veya yürütülmez.

## Doğrulanan paket

Paket `scratch/service-candidates/r166a1-primary-01` altındadır ve yayımlanmış R165 ürün kaynaklarından üretilmiştir. R166 değişiklikleri bu kaynakları paketleyen/doğrulayan yeni araçlar ve testlerdir; yeni bir R166 kaynak commit'i henüz yoktur.

| Alan | Gerçek değer |
|---|---|
| Harness commit | `1600eba430562795b9114209d1168bfa0d6ea5fd` |
| Native commit | `5e3635c2cdfc2161fd20c089618bd7f2a7c12f2d` |
| Native kaynak | 760 dosya |
| Harness kaynak | 117 dosya |
| Üretilen bağımlılık referans haritası | 1 dosya, 1162 girdi |
| Toplam | 878 dosya |
| Arşiv boyutu | 20.254.720 bayt |
| Manifest SHA-256 | `a3fde8b0ac808c375c4ecd0eab9f26938828b0d01cd4632ffa4234e47de38af8` |
| Arşiv SHA-256 | `43fc186b8f21e4f39e34364ae100c82e520317d6b06c8a100b29f3b26adcd56a` |
| Plan SHA-256 | `b4bf41dd7005244043ed8c6689219768fae87a4b743f6023b35f52b1241180cc` |

Bağımlılık dosyalarının gerçek baytları, Python ve Node bu arşive eklenmez. Manifest Python 3.12 ve Node >=24 <25 gereksinimini belirtir; seçilmiş binary path/hash ve gözlenen sürümler null, selection/readback NOT_RUN'dır. `install-plan.json`, yürütülebilir kurulum planı değildir; eksik kabul adımlarını kaydeder.

## İnceleme ve düzeltmeler

Node/TypeScript CLI kapanışındaki 12 dosya sabit hashlerle bağlanır; dolaylı `string-coerce.ts` importu da dahildir. Bağımsız inceleme üç ek zorunlu kaynağı belirledi: `packages/upstream/hermes/hermes_state_keys.py`, `terminal_status.py` ve `config/execution-gate/source-lock.json`. Bu kaynaklar eklendi ve execution lock içindeki beş native yol/hash bağı native manifest ile çapraz kontrol edildi.

Arşiv kontrolü dosya kümesini, adları, Git blob kimliklerini, SHA-256, mod ve boyutları doğrular. Fazla/eksik veya yinelenmiş üye, link, sparse içerik, bozuk metadata ve sonda veri reddedilir. İncelemede semantik tar okuyucusunun görmezden geldiği padding baytları bulundu; tam deterministik arşiv yeniden üretimi artık bu gizli farklılığı da reddeder. Mevcut sınırlı private-path/credential taramaları korunur; kapsam tam güvenlik denetimi değildir.

Yeni case-collision testi, iki dosya adını gerçek dosya sisteminde oluşturmaya bağımlıydı. Fixture immutable Git tree nesneleriyle değiştirildi. Hem `Fixture.py` hem `fixture.py` varlığı doğrulanır ve aynı reddetme koşulu sınanır; platform skip'i eklenmedi, fixture HEAD/index/ref'i değiştirilmez.

## Test kanıtları

| Koşum | RUN | PASS | SKIP | FAIL | ERROR | Exit | Süre |
|---|---:|---:|---:|---:|---:|---:|---:|
| Son yeni test dosyası, Linux yerel | 30 | 30 | 0 | 0 | 0 | 0 | 7.890 s |
| Son yeni test dosyası, Windows primary | 30 | 30 | 0 | 0 | 0 | 0 | 46.297002 s |
| Önceki test dosyasıyla ilgili eski/yeni birleşik regresyon | 94 | 94 | 0 | 0 | 0 | 0 | 33.366 s |
| Önceki fazla geniş yerel regresyon | 120 | 114 | 0 | 0 | 6 | 1 | 26.505 s |

Son test SHA-256 `01eecade206c607aae3aa2075b91872dfb708aeb1436f69ef7b8d35fb772e54b`'dir. 94 testlik sonuç, önceki `40c3c8f88476d73eb5024cd4bfbce4cc8317ea01da6630ebba33dab809173bc6` dosyasına aittir; yeni dosyayla yeniden koşulmuş sayılmaz. Builder ve verifier bu test taşınabilirlik düzeltmesinde değişmedi.

120 testlik başarısız denemenin altı hatası, kısmi yerel snapshot'ta eksik tarihsel `evidence/d3b-projected-launch-l145a8` JSON kayıtlarıdır. Sonuç FAIL olarak korunur. O denemenin çıktısı kısmen kırpılmış ve tam log dosyası alınmamıştır; bu sınır hazırlık kaydında açıktır. Yeni Windows koşumunun tam logu saklanmıştır.

Yerel testler sahiplenilmiş sentetik Git/byte fixture'larıdır. Ayrıca primary üzerindeki gerçek 760 native dosya ve R165 Git kaynaklarından paket üretimi yapıldı; bağımsız gözlenen manifest/arşiv hashleriyle ayrı `prepare_bytes` doğrulaması PASS verdi. Windows dosya-CLI kabulü yoktur; dosya okuma CLI'sı POSIX descriptor yolunu kullanır.

## Güncel kaynak yayını odaklı kontrolü

İncelenip sabitlenen aynı koşucu ve aynı 94 test kimliği iki platformda çalıştırıldı. İki yeni script, üç test dosyası ve 74 destek dosyası olmak üzere 79 girdi dosyasının hashleri koşumdan önce ve sonra eşittir. Önceki test tablosu tarihsel kayıt olarak korunur; aşağıdaki sonuçlar güncel `01eecade206c607aae3aa2075b91872dfb708aeb1436f69ef7b8d35fb772e54b` test dosyasına aittir.

| Güncel koşum | RUN | PASS | SKIP | FAIL | ERROR | Exit | Süre |
|---|---:|---:|---:|---:|---:|---:|---:|
| Linux | 94 | 94 | 0 | 0 | 0 | 0 | 24.51232 s |
| Windows primary | 94 | 74 | 20 | 0 | 0 | 0 | 307.510766 s |

Windows'taki 20 skip, değişmeyen `test_projected_install.OwnedFilesystemTests` sınıfının Linux descriptor/atomik yayın fixture'larıdır. Yeni 30 servis testi Windows'ta da PASS'tir. Bu sonuçlar Windows dosya-CLI kabulü veya gerçek kurulum kabulü oluşturmaz.

Tam seçili/çalıştırılmış test kimlikleri, platform/sürüm, girdi hashleri, skip nedenleri ve tam log hashleri [Linux kanıtı](../evidence/p2-service-candidate-r166a1/focused-linux.json) ile [Windows kanıtı](../evidence/p2-service-candidate-r166a1/focused-windows-02.json) dosyalarındadır. Loglar aynı klasördedir. [Kaynak kontrol kaydı](../evidence/p2-service-candidate-r166a1/source-check.json), bu sonuçları incelenen koşucuya ve gerçek Windows native işlem makbuzuna bağlar. Koşucu SHA-256 `95a91bf23787021abe47d7064dda84360cc2633547456d847d2989e311430cc3`; test seçimi SHA-256 `e55bf10e420caaa39e532ecbaaec1db21873df4a112caa9822ba30e1b0728dd3`.

İlk Windows yayın denemesi 300 saniyelik dış native komut sınırında `DEADLINE_EXCEEDED`, exit 124 ile kesildi. Final unittest özeti ve sonuç JSON'u oluşmadığından tam koşum sayıları bilinmiyor; başarılı sayılmadı. [Zaman aşımı kaydı](../evidence/p2-service-candidate-r166a1/preserved-windows-timeout.json), gerçek başarısız makbuz hashini ve exact eksik logu korur. Devam etmeden önce Python süreçleri salt okunur kontrol edildi ve çalışan aynı koşucu bulunmadı. Yukarıdaki Windows sonucu ayrı `windows-02` adıyla, 1200 saniyelik dış native sınırı altında tamamlanan koşumdur. Tam CI'nin 480 saniyelik politikası değişmedi.

[Korunan hazırlık geçmişi](../evidence/p2-service-candidate-r166a1/preserved-preparation-history.json), önceki farklı test hashine ait sonuçları ve 120-test/6-error denemesinin eksik tam log sınırını açık tutar. [Hazırlanmış gerçek paket](../evidence/p2-service-candidate-r166a1/prepared-candidate.json), [kaynak gözlemi](../evidence/p2-service-candidate-r166a1/prepared-source-observation.json) ve [önceki Windows 30-test kaydı](../evidence/p2-service-candidate-r166a1/preserved-primary-windows30.json) değişmeyen private asıllara hash ile bağlı, yerel mutlak yolları çıkarılmış yayın kopyalarıdır.

Canlı yayın başlangıcında 18 korunan depo, kökteki 33 mevcut değişiklik, 760 native kaynak dosyası ve uzak referanslar doğrulandı. Tam CI için beklenen keşif/koşum sayısı 4677'dir; bu sayı henüz tam CI PASS iddiası değildir. Mevcut 480 saniyelik tam CI politikası korunur.

## Dosyalar ve devam adresi

Yayın paketinin sahiplenilmiş yolları iki yeni script, yeni test, bu rapor, `status.md`, önceki durumun exact arşivleri `r166-parent.md` ve `r166-pre-publication.md` ile `evidence/p2-service-candidate-r166a1` altındaki incelenmiş kanıtlardır. Tam yol/hash kümesi private `source-publication-manifest.json` dosyasında sabitlenir. R166 kaynak commit/push işlemi henüz yapılmadı.

Private kanıtlar `scratch/r166-source-preparation` altındadır: değişmeyen `PREPARATION.md` ve `local-preparation.json`, test taşınabilirlik ek kaydı, `primary-source-observation.json`, `primary-source-verified.json`, `focused-windows-01.json`, tam test logu ve gerçek Bridge makbuzları. `primary-checkpoint.json` son koruma/teslim sınırını ve dosya hashlerini bağlar.

Sonraki somut iş, bu kaynak hazırlığını normal statik/source kapısı ve R166 yayın sürecine taşımaktır. Ardından Python/Node binary seçimi ve readback, referans bağımlılıkların gerçek baytları ve servis için yeterliliği, R156'yı koruyan yeni kurulum hedefi ve ayrı installer uygulaması ele alınır. Service/kernel ve yapılandırılmış model/provider kabulü kendi gerçek koşum ve kanıtlarını gerektirir.
