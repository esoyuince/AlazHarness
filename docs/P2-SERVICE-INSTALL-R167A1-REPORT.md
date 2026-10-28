# R167A1 — P2 servis kurulumu ve başlangıç doğrulaması

## Sonuç ve kapsam

**Yeni lab kurulumu, bağımsız kurulu-dosya doğrulaması, sabit Python importları ve Node CLI help PASS. Kaynak yayını IN PROGRESS.** P1 DONE; P2 IN PROGRESS; P3–P5, tam D3B, M1 ve production OPEN.

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

Canlı başlangıç envanteri 19 korunan depo/çalışma ağacını ve varsayılan kökteki 33 mevcut değişmiş dosyayı kaydetti. R166'nın yetkili terminal journal SHA-256 değeri `f130d8d02050a35c0a15bfce7244ff9c57c4c42cb85f22ead9904fe206e162e8`; başlangıç kaydı `scratch/r167-install/baseline.json` içindedir. Yayın akışı bu kayıtları yeniden doğrular.

## Uygulanan değişiklikler

Ayrı `scripts/install_service_candidate.py`, mevcut servis manifesti/arşivini ve dış kaynak pinlerini doğrular; root tarafından kontrol edilen dizin zinciri, no-follow/held-descriptor dosya kontrolleri, gerçek runtime binary hashleri ve sınırlı sürüm çıktılarıyla yeni hedefe kurulum yapar. Hedefin önceden bulunması reddedilir. Geçici stage tamamlandıktan sonra atomic no-replace geçişi uygulanır. Ayrı doğrulama modu kurulu dosya kümesini ve makbuzu yeniden okur.

29 yeni installer testi; runtime envanteri, resmi Node dosya kurulumu, servis kurulumu ve ordinary-user başlangıç kontrolleri için QA betikleri eklendi. Tarihsel finite builder/installer ve R166 servis builder/verifier değişmedi. Windows transportları, exclusive attempt/intent/execution-start kayıtlarıyla mutasyonu ve gözlemini ayırır; bilinmeyen sonuç otomatik yeniden yürütülmez.

## Test sonuçları

| Koşum | RUN | PASS | SKIP | FAIL / ERROR | Exit | Süre |
|---|---:|---:|---:|---:|---:|---:|
| Linux odaklı regresyon | 123 | 123 | 0 | 0 / 0 | 0 | 26.00735 s |
| Primary Windows windows-02 | 123 | 88 | 35 | 0 / 0 | 0 | 366.345013 s |

123 test = değişmeyen 94 ilgili test + 29 yeni installer testi. Seçilen ve çalıştırılan benzersiz test kimlikleri her iki platformda eşit; 81 girdi ve koşucu hashleri önce/sonra aynı. Windows skip'leri açıkça tanımlı Linux-only koşullarıdır. Bu odaklı testler sentetik fixture ve sınırlı yerel Python çocuklarını kapsar; gerçek kurulum ve tam CI kanıtı ayrıca tutulur.

Kanıtlar: [odaklı test özeti](../evidence/p2-service-install-r167a1/focused-checks.json), [Linux tam kayıt](../evidence/p2-service-install-r167a1/focused-linux.json), [Linux log](../evidence/p2-service-install-r167a1/focused-linux.log), [Windows tam kayıt](../evidence/p2-service-install-r167a1/focused-windows-02.json), [Windows log](../evidence/p2-service-install-r167a1/focused-windows-02.log).

R167 tam CI henüz kabul edilmedi. 4706 test, değişmeyen 4677 testlik tabana 29 yeni test eklenmesinden çıkan beklenen sayıdır; gerçek koşum yapılmadan PASS veya çalıştırılmış test sayısı değildir.

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

## Kaynak yayını

Dal `alaz/p2-service-install-r167a1`; primary `C:\Antigravity\AlazHarness\scratch\worktrees\p2-service-install-r167a1`. Bu raporun hazırlandığı anda R167 commit/push ve tam CI henüz NOT RUN. İncelenmiş özel yayın controller'ı; exact dosya manifesti, korunan repo/dosya hashleri, normal push ve ayrı remote readback, taze source/closure CI, main fast-forward ve aynı commit için doğrulanmış CI reuse ister. Güncel CI politika gözlemi digest'i `383891808b8fc874e0c6021f66e82801984f6a5ce43391fd36727f03a3e3642d`; CI ayarı değiştirilmedi.

Özel yayın makbuzları `scratch/r167-publication` altında tutulur. Bir komutun dönmesi, remote yayının veya CI'nın kabul edildiği anlamına gelmez. Source CI sonrası bu rapor ve status ile ayrı source-ci kanıtı, üç dosyalık closure commit'ine alınacak.

## Açık P2 ve production kapıları

Aynı kurulu aday için sıradaki iş gerçek servis profili, supervisor/child/volume, namespace/cgroup/mount/lease yaşam döngüsü ve sıralı kapanışın provider-free fixture ile doğrulanmasıdır. Ardından host CLI/API üzerinden start → submit → observe → result/usage → cancel → close, kayıp yanıt sonrası özgün kimlikle sorgu, restart ve effective-config gözlemleri gerekir. Belirsiz process/control/close sonuçları kaynakları erken bırakmadan uzlaştırılmalıdır.

Seçilmiş provider/model, gerekli bağımlılık kapanışı ve açık çağrı/token/maliyet sınırları sağlandığında küçük izinli araç göreviyle gerçek model kabulü yapılır. P3 kalıcılık/beceri kullanımı, P4 işletim ve P5 tek sürüm adayı/pilot açık kalır. **Bu çalışmada gerçek model çağrısı 0; service, kernel, gerçek model ve production kabulü false.**
