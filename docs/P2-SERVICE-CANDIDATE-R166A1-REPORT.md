# R166A1 — P2 servis kaynak paketi hazırlığı

## Sonuç ve kapsam

Servis nesli için ayrı kaynak paketi builder'ı ve salt okunur verifier hazırdır. Gerçek primary Git nesnelerinden üretilen 878 dosyalık paket doğrulandı. Son yeni test dosyası Linux yerel ve Windows primary koşumlarında 30/30 PASS verdi.

Bu, P2 adım 6'nın kaynak hazırlığı ve R166 kaynak yayın paketidir. Güncel Linux/Windows odaklı kontroller, source commit/normal push ve source tam CI PASS. Bu sabit checkpoint final CI, main ve terminal yayın kabulünden önce hazırlanmıştır; bu sonraki adımlar burada NOT RUN. P2 IN PROGRESS. Gerçek kurulum, runtime seçimi/readback, servis bağımlılık kabulü, service/kernel ve model kabulü OPEN. Paket veya fixture testi, bu kabul alanlarını tamamlanmış yapmaz.

Aktif dal `alaz/p2-service-candidate-r166a1`; primary çalışma ağacı `C:\Antigravity\AlazHarness\scratch\worktrees\p2-service-candidate-r166a1`. Başlangıç HEAD `1600eba430562795b9114209d1168bfa0d6ea5fd` ve ilk çalışma ağacı temizliği doğrulandı. R165 terminal yayın günlüğü SHA-256 `34bf70efdd2d642b671c648cf57a65bff0f4b35270f3838d4309d4e7984b7f60` ile kapanmıştır.

## Neden ayrı paketleme yolu gerekiyor?

Korunan finite builder/installer 756 native dosyalı önceki nesle bağlıdır. Servis yolu native `5e3635c2cdfc2161fd20c089618bd7f2a7c12f2d` commit'ini ve 760 dosyayı kullanır. Yeni builder bu nesli, üç servis girişini, seçim/config/host-lock dosyalarını, Node CLI importlarını ve gerekli execution/recovery destek dosyalarını açıkça seçer. Eski iki araç değişmeden kalır; hash ile sabitlenmiş saf yardımcı işlevleri kullanılır.

`scripts/build_service_candidate.py`, immutable Git nesnelerini okur ve yalnız yok olduğu doğrulanmış, ignore edilmiş `scratch/service-candidates` hedefinde çıktı üretir. `scripts/verify_service_candidate.py` içindeki `prepare_bytes`, manifest SHA-256, arşiv SHA-256, harness commit ve native commit olmak üzere dört zorunlu dış kimlik bağı ister. Kaynaklar çıkarılmaz veya yürütülmez.

## Doğrulanan paket

Paket `scratch/service-candidates/r166a1-primary-01` altındadır ve yayımlanmış R165 ürün kaynaklarından üretilmiştir. R166 değişiklikleri bu kaynakları paketleyen/doğrulayan yeni araçlar ve testlerdir; kabul edilen kaynak commit'i `6d65f66ba961f1390e3d44e34a0207f367a5de89`'dir. Doğrulanan 878 dosyalık paketin harness kimliği aşağıdaki R165 BASE commit olarak kalır; yeni araç commit’i bu artifact kimliğinin yerine geçirilmez.

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

Canlı yayın başlangıcında 18 korunan depo, kökteki 33 mevcut değişiklik, 760 native kaynak dosyası ve uzak referanslar doğrulandı. Source tam CI artık gerçek 4677 RUN /4644 PASS /33 SKIP /0 FAIL /0 ERROR sonucuyla kabul edilmiştir; statik keşif de 4677’dir. Mevcut 480 saniyelik tam CI politikası korunur.

## Source CI kabulü ve final yayın handoff'u

| Alan | Gerçek source CI değeri |
|---|---|
| Kaynak commit | `6d65f66ba961f1390e3d44e34a0207f367a5de89` |
| Ref | `refs/heads/alaz/p2-service-candidate-r166a1` |
| Kabul zamanı | `2026-10-28T04:02:12.999395+00:00` |
| Suite | 4677 RUN /4644 PASS /33 SKIP /0 FAIL /0 ERROR |
| Süre | 380.213 s |
| GitHub context/status | `alaz/local-ci` / `success` |
| GitHub status ID | `57436285811` |
| Delivery | `6de92cf4-d280-11f1-8f48-26660b4477f2` |
| Container | exit 0; timeout false; OOM false; cleanup removed |
| Tam suite yeniden kullanımı | Yok; bu delivery'de gerçek tam koşum |
| Statik keşif | 4677; PASS |
| CI politika SHA-256 | `39feb838fe28d4176b40dc99d8dcc824648c1b374a3d168ef0e4a23bdade4776` |
| Kabul kaydı SHA-256 | `c374d361d719bc59a20890b71ae797cb4a9498ff7ecf25f433ea231960d85f7a` |
| CI log SHA-256 | `023d5c6251b5620db845458eec12b3121957a8a7edada7eeeb9952128c630bc1` |

### Korunan stage başarısızlıkları ve dar recovery

İlk preflight `024`, `check-ignore -z` için gerekli stdin biçimi eksik olduğundan Git exit 128 / native exit 2 ile reddedildi; stage intent veya index değişikliği oluşmadı. Salt okunur reconciliation sonrası stdin düzeltmesi ayrı incelendi. İkinci stage `027`, iki exact add işleminden sonra `git diff --cached --check` exit 2 ile durdu. Bu iki başarısız native makbuz korunur; başarılı işlem olarak yeniden yazılmaz.

İkinci bulgu, [ilk Windows timeout logunun](../evidence/p2-service-candidate-r166a1/focused-windows.log) 83. satırında, test sürerken kalan son boşluktur. Log `14539` bayt ve SHA-256 `68f1a2bc6b97187199f16e384b52b83ee381f648e9403fd4292e794ef606fe96` olarak aynen saklandı. İncelenen recovery yalnız bu exact iki satırlık Git diagnostic'ini kabul eder: tam check **exit 2**, log dışındaki 18 yol **exit 0**. Tam check sonucu sıfırmış gibi kaydedilmez. Başka bir whitespace bulgusu veya değişmiş log baytı reddedilir.

Recovery mevcut index yol/blob/hash kümesini, 963 önceki girdi pinini ve saf hesaplanan tree kimliğini doğruladı; add işlemlerini tekrarlamadı, index baytlarını veya raw logu değiştirmedi. Statik kapı ayrıca PASS verdi. Source commit aynı dar whitespace bağını yeniden denetledi. Sonraki closure değişikliği normal sıfır-bulgulu kapıya tabidir. Eski helper/contract/intent/add dönüşleri ve gerçek `024`/`027` makbuzları, incelenen `publication-recovery-contract.json` girdileriyle private olarak bağlıdır. Tüm denenmiş işlemler PASS değildir. Terminal journal yalnız gerçekten tamamlanan recovery/yayın zincirini sayar; bu checkpoint sonraki final/main adımlarının tamamlandığını ileri sürmez.

[Source CI kaydı](../evidence/p2-service-candidate-r166a1/source-ci.json), gerçek private kabul dosyasının exact bayt kopyasıdır. Güncel GitHub success kimliği, aynı commit/ref'e ait sunucu delivery'si, tam log hash/boyutu, suite/static sayaçları ve container sonucu incelenen kabul kapısında eşleştirildi. Sunucu metadata hash'i authenticated SSH gözlemine dayanır; ham metadata baytları burada bağımsız yeniden hash'lenmiş sayılmaz.

Bu sürümlenen checkpoint source CI kabulünden sonra, closure/final CI ve main işlemlerinden önce hazırlandı. Final CI, main yayını/main CI ve terminal kayıt burada NOT RUN olarak sabittir. Sonraki gerçek sonuçların yetkili kaydı `scratch/r166-publication/final-publication.json` olacaktır; bu dosyanın varlığı veya PASS sonucu bu checkpoint tarafından varsayılmaz.

Final CI aynı source sonucunun yeniden adlandırılması olamaz: closure commit'i için yeni, tam ve reuse içermeyen koşum gerekir. Main kabulü ise ayrı main push status/delivery'sine ve kabul edilmiş aynı-commit final proof'un doğrulanmış yeniden kullanımına bağlanır; main için tam suite yeniden koşulmuş iddiası kurulmaz. Bu paragraf sonraki adımların gereksinimini kaydeder; başarılarını bildirmez.

P1 DONE; P2 IN PROGRESS. P3–P5, tam D3B, M1 ve production OPEN. R156 kurulumu, eski finite araçlar, kökteki 33 değişiklik ve 760 native kaynak korunur. Runtime seçimi/readback, gerçek bağımlılık kurulumu, native service/kernel ve model/provider kabulü bu source CI sonucuyla tamamlanmaz.

## Kaynak push sonrası tamamlamanın kanıt sınırı

Source commit `6d65f66ba961f1390e3d44e34a0207f367a5de89` ve normal source push için özgün alt komut dönüşleri exit 0'dır. Buna rağmen `036` üst işlemi, commit/push sonrasındaki salt okunur uzak-ref gözleminde native exit 2 ile bitmiştir. Korunan üst işlem bu kapanışta veya terminal zincirde başarılı işlem olarak sunulmaz.

Ayrı `033` önkoşul denemesi de native exit 2 olarak korunur; o denemede Git mutation girişimi yoktur. `035`, `038` ve `040` gözlemleri, özgün denemeler ve dönüşler, SHA-256 ile sabit supplemental contract'a bağlanır. Bu sözleşme özgün publication contract'ı ve helper'ı değiştirmez.

İlk tamamlayıcı `055`, reservation öncesindeki geçmiş ref kapsamı denetiminde native exit 2 ile reddedildi. `040` yalnız source/main için iki ref gözlemişti; bu geçmiş gözlemi dokuz ref'lik tam koruma kümesiyle eşitlemek doğru değildi. `056`, source push/recovery çıktılarının ve yeni remote-read kayıtlarının bulunmadığını, özgün kayıtlar ve 19 kaynak dosyasının değişmediğini doğruladı. Çalıştırılmış eski yardımcı/sözleşme ve gerçek `055`/`056` makbuzları aynen arşivlendi. Sonraki incelenen düzeltme source push makbuzunun iki ref'ini ayrı tutar; bütün dokuz korunmuş Harness ref'i ayrıca proof içinde doğrulanır. `055` başarıya çevrilmez.

Sonraki tamamlayıcı yalnız salt okunur gözlem ve doğrulama yaptı: commit/push yeniden çalıştırılmadı, Git configuration değiştirilmedi, Git index'e veya native servis runtime'ına müdahale edilmedi. Kaynak push'un tamamlanmış postcondition kaydı ve recovery proof, gerçekten exit 0 ile tamamlanan ayrı native makbuza bağlanır:

| Kanıt | SHA-256 / kimlik |
|---|---|
| Supplemental contract | `6bbedb4c9be4c9f534be9496af0a080a611cf1f219916741a181dde3e884b03e` |
| Source push postcondition kaydı | `dfe135bbecf42e00ddc7552ba16a068bcdc4820e258818a6d1053ebd3e9f41e9` |
| Salt okunur recovery proof | `b7f4ef1037c29990f055356752408c8da656a74bbf0a4cf967fa738755d25dbb` |
| Tamamlayıcı native işlem | `c166a101-1028-4a01-8000-000000000059` |
| Tamamlayıcı native makbuz | `8a2aa9e355cb697cbda319f50f05fa34fabdaf1c077f0366e8c26fa60f6c64ed` |
| Özgün başarısız `033` makbuzu | `007995a6736c506ea8891a1e2c48771fa1d658269fed8c56af1b36236493fd40` |
| Özgün başarısız `036` makbuzu | `7eeb7a87e2e4c8d4292b01dbcb7e21bfec4b2073618d8610df0e7e9897b431e5` |
| İlk tamamlayıcı `055` başarısızlık makbuzu | `cb5bccb595c5a6ae7b4fded8ded11b5a1604193cecf1c677789580639e6074a5` |
| `056` salt okunur no-effect gözlemi | `70e22f83b24a4487b53c5ea9ccd87742ec1c20054f4d5f4aa9f783a4333256e7` |

Bu ayrı tamamlamanın PASS olması, özgün başarısız işlemlerin sonucunu değiştirmez. Önceki `024`/`027` stage başarısızlıkları, ilk Windows timeout'u ve tarihsel test başarısızlıkları da kendi kayıtlarıyla korunur. Kapanış kapsamı yine yalnız status.md, bu rapor ve exact source-ci.json dosyalarıdır. Final CI, main yayını ve terminal journal bu checkpoint hazırlanırken NOT RUN kalır.

## Dosyalar ve devam adresi

Yayın paketinin sahiplenilmiş yolları iki yeni script, yeni test, bu rapor, `status.md`, önceki durumun exact arşivleri `r166-parent.md` ve `r166-pre-publication.md` ile `evidence/p2-service-candidate-r166a1` altındaki incelenmiş kanıtlardır. Tam yol/hash kümesi private `source-publication-manifest.json` dosyasında sabitlenir. Kaynak commit/normal push `6d65f66ba961f1390e3d44e34a0207f367a5de89` ile tamamlandı; source CI kabulü aşağıdaki exact kanıta bağlıdır. Bu kapanış yalnız rapor, status ve source-ci.json dosyalarını değiştirir.

Private kanıtlar `scratch/r166-source-preparation` altındadır: değişmeyen `PREPARATION.md` ve `local-preparation.json`, test taşınabilirlik ek kaydı, `primary-source-observation.json`, `primary-source-verified.json`, `focused-windows-01.json`, tam test logu ve gerçek Bridge makbuzları. `primary-checkpoint.json` son koruma/teslim sınırını ve dosya hashlerini bağlar.

Sonraki somut iş, bu üç dosyalık source-CI kapanışını normal commit/push ile kaydedip ayrı final tam CI kabulünü almaktır. Main fast-forward/normal push, ayrı main status/delivery ile doğrulanmış aynı-commit CI yeniden kullanımı ve terminal journal bundan sonra gelir. Ardından Python/Node binary seçimi ve readback, referans bağımlılıkların gerçek baytları ve servis için yeterliliği, R156'yı koruyan yeni kurulum hedefi ve ayrı installer uygulaması ele alınır. Service/kernel ve yapılandırılmış model/provider kabulü kendi gerçek koşum ve kanıtlarını gerektirir.
