# R167A1 — P2 servis kurulumu ve başlangıç doğrulaması

## Sonuç ve kapsam

**Yeni lab kurulumu, bağımsız kurulu-dosya doğrulaması, sabit Python importları, Node CLI help ve R167 kaynak commit'inin taze tam CI koşumu PASS. Bu kapanış kaydı hazırlanırken kapanış commit'i/CI ve main yayını bekliyor.** P1 DONE; P2 IN PROGRESS; P3–P5, tam D3B, M1 ve production OPEN.

Bu dilim, R166'da hazırlanmış servis adayını gerçek Python 3.12/Node 24 ortamına yerleştirir ve başlangıç için gereken sabit dosyaları doğrular. Gerçek servis nesnesi, kernel yaşam döngüsü veya model işi başlatmaz. 1162 bağımlılık dosyası yalnız hazırlanmış import önkoşullarıdır; tüm provider ve plugin'lerin tamam olduğu anlamına gelmez.

## Kaynak ve kurulum kimliği

| Alan | Sabit kimlik |
|---|---|
| R167 araç tabanı | `833a40aa99f5ca7e2b2562a19e8f0c286a0adea2` |
| Kurulan harness ürün kaynağı | `1600eba430562795b9114209d1168bfa0d6ea5fd` |
| Kurulan native ürün kaynağı | `5e3635c2cdfc2161fd20c089618bd7f2a7c12f2d` |
| Manifest SHA-256 | `a3fde8b0ac808c375c4ecd0eab9f26938828b0d01cd4632ffa4234e47de38af8` |
| Kaynak arşivi SHA-256 | `43fc186b8f21e4f39e34364ae100c82e520317d6b06c8a100b29f3b26adcd56a` |
| Bağımlılık envanteri SHA-256 | `1e1c4d0a5a9f0d4d25c66aaabe0765c75cdca0dd84121f79883b9e3bf2b4ee18` |
| Kurulum makbuzu SHA-256 | `0ba26bfbae1a216a595baf6fb935ed18f399bcfd0ecf29aa9c14bf61bd04232f` |
| Yeni hedef | `/opt/alaz-r167a1` |

878 kaynak dosyası, 760 native + 117 harness + 1 bağımlılık referans haritasından oluşur. R167 araçlarının yayın kimliği, bu adayın ürün kaynağıyla karıştırılmaz.

Canlı başlangıç envanteri 19 korunan depo/çalışma ağacını ve varsayılan kökteki 33 mevcut değişmiş dosyayı kaydetti. R166'nın yetkili terminal journal SHA-256 değeri `f130d8d02050a35c0a15bfce7244ff9c57c4c42cb85f22ead9904fe206e162e8`; başlangıç kaydı `scratch/r167-install/baseline.json` içindedir. Yayın akışı bu kayıtları, aşağıdaki tam commitlerle sınırlandırılmış dış depo geçişini ayrıca bağlayarak yeniden doğrular.

## Uygulanan değişiklikler

Ayrı `scripts/install_service_candidate.py`, mevcut servis manifesti/arşivini ve dış kaynak pinlerini doğrular; root tarafından kontrol edilen dizin zinciri, no-follow/held-descriptor dosya kontrolleri, gerçek runtime binary hashleri ve sınırlı sürüm çıktılarıyla yeni hedefe kurulum yapar. Hedefin önceden bulunması reddedilir. Geçici stage tamamlandıktan sonra atomic no-replace geçişi uygulanır. Ayrı doğrulama modu kurulu dosya kümesini ve makbuzu yeniden okur.

29 yeni installer testi; runtime envanteri, resmi Node dosya kurulumu, servis kurulumu ve ordinary-user başlangıç kontrolleri için QA betikleri eklendi. Tarihsel finite builder/installer ve R166 servis builder/verifier değişmedi. Windows transportları, exclusive attempt/intent/execution-start kayıtlarıyla mutasyonu ve gözlemini ayırır; bilinmeyen sonuç otomatik yeniden yürütülmez.

## Test sonuçları

| Koşum | RUN | PASS | SKIP | FAIL / ERROR | Exit | Süre |
|---|---:|---:|---:|---:|---:|---:|
| Linux odaklı regresyon | 123 | 123 | 0 | 0 / 0 | 0 | 26.00735 s |
| Primary Windows windows-02 | 123 | 88 | 35 | 0 / 0 | 0 | 366.345013 s |
| R167 source tam CI | 4706 | 4673 | 33 | 0 / 0 | 0 | 382.910 s |

Odaklı 123 test = değişmeyen 94 ilgili test + 29 yeni installer testi. Seçilen ve çalıştırılan benzersiz test kimlikleri her iki platformda eşit; 81 girdi ve koşucu hashleri önce/sonra aynı. Windows skip'leri açıkça tanımlı Linux-only koşullarıdır. Bu odaklı testler sentetik fixture ve sınırlı yerel Python çocuklarını kapsar; gerçek kurulum ve tam CI kanıtı ayrıca tutulur.

Kanıtlar: [odaklı test özeti](../evidence/p2-service-install-r167a1/focused-checks.json), [Linux tam kayıt](../evidence/p2-service-install-r167a1/focused-linux.json), [Linux log](../evidence/p2-service-install-r167a1/focused-linux.log), [Windows tam kayıt](../evidence/p2-service-install-r167a1/focused-windows-02.json), [Windows log](../evidence/p2-service-install-r167a1/focused-windows-02.log).

R167 kaynak commit'i `508182cf7f476fbf1273cc185b037e7b8d8e1c11` için taze tam CI, native078 ile PASS olarak kabul edildi. Gerçek koşum 4706 test çalıştırdı: 4673 PASS, 33 SKIP, 0 FAIL ve 0 ERROR; süre 382.910 saniye. Delivery `3e47eae8-d2c7-11f1-9af9-75a41e919812`, GitHub `alaz/local-ci` success status kimliği `57464692579`. Container exit 0; timeout ve OOM yok, container kaldırıldı. Statik kontrol PASS ve 4706 test keşfetti; bu statik kontrolün kapsamı `M0_and_HYB_mock_contracts_not_full_runtime` olarak kaldı.

[Kabul edilmiş kaynak CI kanıtı](../evidence/p2-service-install-r167a1/source-ci.json), tam 9733 bayt CI logunun SHA-256 değeri `6746582a1edbaf8fadecdfb232d42446a2ec607a64ad903fe2eabc23e7a3e99b` ile bağlanır. Log baytları yerelde yeniden hash'lendi; metadata ham baytlarının yerelde yeniden hash'lendiği iddia edilmez (`metadataRawBytesLocallyRehashed=false`). Bu kabul, ayrı kapanış commit'inin tam CI kapısını veya gerçek servis/kernel/model kabulünü tamamlamaz.

## Gerçek runtime ve kurulum

Python `/usr/bin/python3.12`, gerçek sürüm 3.12.3, SHA-256 `e50d468e8b0adfb05733f5b87b3cff34829c4a8c1aea50c865aa8bdfe4bb150f`.

Node 24.22.1 Linux x64, [resmi dağıtım arşivinden](https://nodejs.org/dist/v24.22.1/) alındı. İmzalı checksum resmi aktif anahtarlıkla doğrulandı; arşiv SHA-256 `6c172a9ab6718f7b801fb5a7bd486af2ee5e32758086a04b84fcce2aa77095e6`. Seçilen binary SHA-256 `e32e2d16081cf644f88392934288086e7662529d0d43277c34f7aad2207cfafb`; ayrı hedef `/opt/alaz-r167a1-node-24.22.1/bin/node`.

Native021 yalnız Node dosyalarını kurdu, Node çalıştırmadı. Native025 servis installer koşumu, iki gerçek executable'ın sürüm/hash kontrolleriyle 878 kaynak ve 1162 bağımlılığı yeni hedefe kurdu; exit 0. Native027, ordinary `alazgateway` kullanıcısıyla bağımsız readback yaptı; exit 0 ve exact dosya/makbuz eşleşmesi PASS.

Önceki R156 kurulum makbuzu `a4bcc0f27d29f27f08c55d3a65eaa102a503a7da12d4672253f0245fd5d4f845` olarak korundu. Kurulum kanıtı [installation.json](../evidence/p2-service-install-r167a1/installation.json) içinde; paylaşılan makbuz projeksiyonu device/inode alanlarını çıkarır ve özgün tam makbuz hash'ine bağlanır.

## Başlangıç kontrolleri

### Node CLI

Native030, ordinary kullanıcıyla kurulu Node üzerinden yalnız `--help` yolunu çalıştırdı. Exit 0; 2046 bayt çıktı SHA-256 `412d1ffc1eb96d93940ebe573307702922676bc96cd6cf94887abb538785c40f` ile eşleşti, stderr boş. Kaynak/bağımlılık ve runtime byte readback işlem öncesinde ve sonrasında PASS. Task veya lifecycle komutu seçilmedi.

### Python sabit importları

Native042, ayrı `import-qualification-02` denemesinde `/usr/bin/python3.12 -I -S -B` ve ordinary kullanıcıyla PASS, exit 0. Hash'i doğrulanmış kaynak bellekte çalıştırıldı; kurulu input dizini değişmedi. Yeni probe SHA-256 `6146fac931f73034a99f35f0eaf2ffc556a00316d31d85c21d21a1aabf947ed0`. Tam stdout 112200 bayt; SHA-256 `74e9db7b23e3e9af57ea54439ed0db8010eebeaff8efc832c5b5bb4723108b3b`; native043 tam geri okumasıyla doğrulandı.

15 sabit import tamamlandı. Import kökeni doğrulaması 444 native, 50 harness ve 304 bağımlılık dosyasını kapsadı; ayrıca 5 incelenmiş yardımcı ve 241 standart kütüphane dosyası kaydedildi. `isolated=1`, `noSite=1`; ortam paketleri için yeni istisna eklenmedi.

Tek engellenmiş etki, urllib3 2.8.0 içindeki `_has_ipv6` kontrolünün `socket.bind(('::1', 0))` girişimiydi. Tam kaynak hash'i, çağıran function/code/globals/locals, import çağrı noktası ve gerçek IPv6 stream socket kimliği eşleşti. Bind engellendi; aynı socket kapandı, `HAS_IPV6=False` oldu. Diğer engellenmiş olaylar boş. Sonuç adı `PASS_FIXED_IMPORTS_WITH_DENIED_IPV6_PROBE`; sıfır engellenmiş olay isteyen eski strict politika başarıya çevrilmedi.

878 kaynak, 1162 bağımlılık ve runtime binary baytları önce/sonra aynıydı. Denemeye ait geçici home'da oluşan `SOUL.md` dahil geçici alan kaldırıldı. Guard süreç sonuna kadar etkin tutuldu; bu Python audit gözlemi hostile-code veya kernel sandbox kabulü değildir. [Tam sınırlı başlangıç kanıtı](../evidence/p2-service-install-r167a1/qualification.json).

## Korunan başarısız denemeler

1. Native007: GPGV Windows sürücü yolunu anahtar URL'si olarak yorumladı; exit 2. İmza kabul edilmedi, arşiv indirilmedi, lab değişmedi. Native008 ayrı koşumunda doğru MSYS yol biçimiyle aynı imzalı metadata/anahtarlık doğrulandı.
2. Native012: Windows focus, testler başlamadan LICENSE checkout CRLF/LF uyuşmazlığında reddedildi. Yalnız R167 checkout'u mevcut HEAD blob'unun sabit LF baytlarına CAS ile eşitlendi; test pinleri değiştirilmedi. windows-02 ayrı koşumda geçti.
3. Native029: 15 import yüklendi, socket.bind engellendi; strict import politikası exit 2 ile reddetti. Bu kayıt hâlâ `NOT_ACCEPTED_IMPORT_PREFLIGHT`.
4. Native037: Ayrı qualification tam IPv6 çağrı kimliğini gözledi; sonraki origin kontrolü ortamdan gelen `sitecustomize` dosyasını reddetti. Socket kapanışı kabul aşamasına ulaşılmadı. Native039, bu dosyanın ürün importlarından önce Python başlangıcında yüklendiğini gösterdi. Yeni native042 koşumu site başlangıcını kapatan daha sıkı `-S` koşuluyla yapıldı.

Hiçbir tarihsel başarısızlık yeniden etiketlenmedi. [Deneme zinciri ve tanı hashleri](../evidence/p2-service-install-r167a1/preserved-attempts.json).

### Yayın önkontrolleri ve ayrı düzeltmeler

| Deneme | Korunan sonuç ve sonraki sınırlı düzeltme |
|---|---|
| Native046 / source-stage01 | `input_changed_during_read` ile reddedildi; reservation veya yayın Git mutasyonu oluşmadı. Windows path stat ve fd stat ctime alanları farklı anlam taşıyordu. Düzeltme, her arayüzün kendi önce/sonra kontrolünü ve POSIX ctime karşılaştırmasını korudu. |
| Native049 / source-stage02 | `baseline_inventory` ile reddedildi; reservation veya yayın Git mutasyonu oluşmadı. Özgün baseline sonucu `OBSERVED` idi; yalnız controller'ın beklediği literal düzeltildi. Baseline baytları değiştirilmedi. |
| Native051 / source-stage03 | `exact_unstaged_allowlist` ile, kaynak paketine ait olmayan LICENSE stat kaydı nedeniyle reddedildi. Native053; çalışma dosyası, index ve HEAD içeriğinin aynı 1081 LF baytı olduğunu, raw diff ve numstat'ın boş olduğunu doğruladı. |
| Native057 / source-stage04 | `protected_repository_changed` ile reddedildi. Dış `alaz-Server` deposunun eşzamanlı belge güncellemesi native058 ile salt okunur gözlendi; aşağıdaki ayrı sözleşme yalnız tam gözlenen HEAD'i kabul etti. |

Native054'ün `git add --refresh -- LICENSE` işlemi sonrası durum kontrolü başarısız kaldı; dış işlem exit 1 olarak korunuyor. Ayrı native055 `git add -- LICENSE` koşumu exit 0 ile tamamlandı: tüm `ls-files --stage` baytları, LICENSE içeriği, HEAD ve 21 kaynak dosyası aynı kaldı; staged path listesi boştu ve fazladan LICENSE durum kaydı temizlendi. LICENSE kaynak paketine eklenmedi.

Bu yayın retleri PASS olarak yeniden sınıflandırılmadı; yeni denemeler ayrı kimliklerle yürütüldü. Özgün reservation/failure/native kayıtları `scratch/r167-publication` altında korunur. Yukarıda bağlanan public `preserved-attempts.json` kurulum ve başlangıç denemelerini içerir; bu sonraki yayın kayıtlarıyla değiştirilmedi.

## Kaynak yayını

Dal `alaz/p2-service-install-r167a1`; primary `C:\Antigravity\AlazHarness\scratch\worktrees\p2-service-install-r167a1`. Kaynak commit'i `508182cf7f476fbf1273cc185b037e7b8d8e1c11` normal push sonrası ayrı remote readback ile doğrulandı; aynı commit'in taze tam CI koşumu kabul edildi. Source CI makbuzu `source-ci-01.result.json`, SHA-256 `086d06e88d9de2b1b8ce05a14c3fb8bce925dea377925744b5b25aae9c3a296a`. Public `source-ci.json`, controller'ın ürettiği 1750 baytlık kanıtın birebir kopyasıdır; SHA-256 `356324edbf3b8d4989a092d20773748a1995de08b7a682e70e74ddedc667bbeb`.

**Bu kapanış kaydı hazırlanırken yayın kapılarının durumu:**

| Kapı | Kabul durumu |
|---|---|
| Kaynak commit'i ve normal push / bağımsız remote readback | PASS; `508182cf7f476fbf1273cc185b037e7b8d8e1c11` |
| Kaynak commit'inde taze tam CI | PASS; native078, yukarıdaki gerçek koşum ve kanıt |
| Yalnız status, bu rapor ve source-ci kanıtından oluşan üç dosyalık kapanış commit'i / push | PENDING |
| Kapanış commit'inde ayrı taze tam CI | PENDING |
| Main fast-forward, normal push ve bağımsız remote readback | PENDING |
| Aynı final commit için doğrulanmış CI reuse, final integrity ve terminal seal | PENDING |

Bu tablo hazırlanma anını kaydeder. Sonraki kapılar için yetkili sonuç, `scratch/r167-publication` altındaki `R167_SOURCE_PUBLICATION_COMPLETE` final publication seal kaydı ve onun bağladığı makbuzlardır. Kaynak CI kabulü kapanış/main adımlarını peşinen PASS yapmaz.

### Sınırlandırılmış dış depo geçişi

`C:\Antigravity\alaz-Server`, özgün `69f2f7d686da4bf40698dda095b576012ef65912` HEAD'inden temiz `main` üzerindeki `2e859e64bf50642d81e7ea6e4798fcfe13e8e09b` HEAD'ine dışarıdan ilerledi. Native058; eski commit'in ata olduğunu ve farkın tam olarak `M CURRENT-STATE.md` ile `A docs/2026-10-28-tailscale-security-maintenance.md` olduğunu doğruladı. Bu yayın çalışması dış depoya yazmadı.

`external-repository-transition-01.json` sözleşmesi, SHA-256 `2461dcc2cab5b1382e7fabcb5feac2edd37c2b87672467f386ca90e18b929e1b`, özgün baseline'ı ve native057 ret kaydını koruyarak yalnız bu tam HEAD geçişini bağlar. Her koruma adımı tam HEAD'i, temiz branch/status durumunu, atalık ilişkisini ve iki belgelik farkı yeniden denetler; sonraki descendant commitler kabul edilmez. Diğer 18 depo için mevcut koşullar, kökteki 33 dosya pini, R165/R166 dosyaları ve 760 native kaynak kontrolü korunur. Sonuçlarda dış geçiş açıkça kaydedilir (`fullyUnchangedFromBaseline=false`).

Yeni salt okunur CI politika gözlemi, önceki gözlemle aynı config/code/image/limit değerlerini verdi. Politika digest'i `383891808b8fc874e0c6021f66e82801984f6a5ce43391fd36727f03a3e3642d` olarak kaldı; CI ayarı değiştirilmedi. Kaynak CI bu politika altında gerçekleşti; kapanış CI için aynı politikaya bağlı ayrı kabul gerekir.

Özel yayın controller'ı exact dosya manifestini, korunan repo/dosya hashlerini, normal push sonrası ayrı remote readback'i, taze source/closure CI'yı, main fast-forward'u ve aynı commit için doğrulanmış CI reuse'u denetler. Bir komutun dönmesi, remote yayının veya CI'nın kabul edildiği anlamına gelmez. Kapanışta ürün/test baytları değişmez; yalnız bu rapor, status ve source-ci kanıtı güncellenir.

## Açık P2 ve production kapıları

Aynı kurulu aday için sıradaki iş gerçek servis profili, supervisor/child/volume, namespace/cgroup/mount/lease yaşam döngüsü ve sıralı kapanışın provider-free fixture ile doğrulanmasıdır. Ardından host CLI/API üzerinden start → submit → observe → result/usage → cancel → close, kayıp yanıt sonrası özgün kimlikle sorgu, restart ve effective-config gözlemleri gerekir. Belirsiz process/control/close sonuçları kaynakları erken bırakmadan uzlaştırılmalıdır.

Seçilmiş provider/model, gerekli bağımlılık kapanışı ve açık çağrı/token/maliyet sınırları sağlandığında küçük izinli araç göreviyle gerçek model kabulü yapılır. P3 kalıcılık/beceri kullanımı, P4 işletim ve P5 tek sürüm adayı/pilot açık kalır. **Bu çalışmada gerçek model çağrısı 0; service, kernel, gerçek model ve production kabulü false.**
