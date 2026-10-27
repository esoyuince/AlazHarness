# P2 / R161A1 — Açık servis profili ve yapılandırma kabulü

Tarih: 27 Ekim 2026. **Kaynak uygulaması ve odaklı testler PASS; P2 IN PROGRESS.**
Bu paket servis profilinin açık seçimini, projection ve ayrı handoff verisini,
özgün startup/consumer/execution bağlarını kapsar. Tam supervisor entegrasyonu,
yeni kurulum ve gerçek model kabulü açık kalır. Linux ve primary Windows
kaynak testleri tamamlandı; exact-commit tam CI ve yayın PENDING.

## Başlangıç ve korunan kapsam

Harness tabanı `5b7eba4d97f63623c20b51f476f4bf36ba6e7d94`'dir.
Native seçim `5e3635c2cdfc2161fd20c089618bd7f2a7c12f2d` ve R159'un
760 dosyalık servis manifest'i değişmedi. Yeni upstream/native sürümü seçilmedi.
Seçim kaydı [hermes-borrowed-service-r159a1.json](../config/hermes-borrowed-service-r159a1.json)
üzerinden okunur; feature, manifest ve seçim özetleri receipt'e bağlanır.

Eski minimal, cold, prepared, retained, finite ve readiness seçimleri korunur.
Bu yolların `config.yaml` reddi genel allowlist genişletmesiyle kaldırılmadı.
P1 DONE kararı tarihsel R156/R157 kabulüne bağlı kalır; bu kaynak paketi o
kabulü yeni bir kurulum için yeniden üretmez. P3–P5, tam D3B, M1 ve production açıktır.

## Teslim edilen kaynak sınırları

| Bileşen | Bu paketteki sorumluluk | Yetki sınırı |
|---|---|---|
| [Servis profili](../packages/claw-hermes/gateway_service_profile.py) | Ayrı layout, typed expectation, dosya kimliği ve içerik kontrolü | Lease, DB açılışı veya runtime admission sağlamaz. |
| [Servis projection](../packages/claw-hermes/gateway_service_projection.py) ve [state projection](../packages/claw-hermes/gateway_state_projection.py) | Aynı volume/profile kimliğini host ve target görünümüne bağlar | Özgün volume, namespace, mount ve confinement guard'ları korunur. |
| [Servis handoff](../packages/claw-hermes/gateway_service_handoff.py) | Ayrı sürümlü, sınırlı veri kodlama ve çözme | Payload tek başına süreç, mount veya servis başlatma yetkisi değildir. |
| [Özgün startup](../packages/claw-hermes/gateway_store_startup.py) | Açık servis profilini aynı üç store ve önceki epoch'a bağlar | Mevcut preopen/live/epoch ve belirsiz etki kuralları korunur. |
| [Özgün consumer](../packages/claw-hermes/gateway_prepared_consumer.py) | Receipt kimliğini hazırlama ve admission kontrollerinde tutar | İkinci store/runner sahibi oluşturmaz; bilinen cleanup yolu korunur. |
| [Execution boundary](../packages/claw-hermes/execution_boundary.py) | Seçilmiş dosyayı gerçek native loader çağrısının iki yanında kontrol eder | Mevcut model, route, credential, araç ve bütçe denetimlerinin yerine geçmez. |

### Profil: açık sözleşme ve sınırlı okuma

Yeni seçim `hermes-service-profile-v1` ve expectation şeması `1`'dir.
Expectation; kaynak seçimi, canonical home, home device/inode, üç DB kimliği,
önceki epoch/instance, discovery özeti ve config device/inode/size/SHA-256 taşır.
Yapısal doğrulama I/O yapmaz; gerçek inspection seçilmiş kaynak neslini de doğrular.

`config.yaml` en fazla **65.536 byte** olabilir. Kabul edilen içerik UTF-8,
anahtarları sıralı, gereksiz boşluksuz, son satır sonu olmayan canonical JSON
nesnesidir. Genel YAML kabulü yoktur. Tekrarlı alanlar, `${...}` başvuruları,
sonlu olmayan veya sınırı aşan sayılar ve aşırı derin/geniş yapı reddedilir.
Secret değerleri config içinden public makbuza veya handoff'a kopyalanmaz.

Tam inspection gerekli girdileri, private sahiplik/mod/device/link koşullarını,
SOUL/cache/discovery içeriklerini ve boş active-session durumunu kontrol eder.
İki snapshot arasında gözlenen değişiklik kabulü durdurur. Beklenmeyen dosya,
symlink, hardlink, özel dosya ve DB/lock ile yardımcı dosya alias'ı kabul edilmez.

Yardımcı dosyalar bounded `read` ile, `O_RDONLY|O_CLOEXEC|O_NOFOLLOW` ve mevcut
platformda `O_NONBLOCK` kullanılarak açılır; FD metadata'sı okumadan önce ve
sonra snapshot ile eşleşmelidir. `O_NONBLOCK`, regular file'ın arada FIFO'ya
dönüşmesi halinde kabul kontrolünün açılışta asılı kalmasını önler. DB, sidecar
ve sahiplik lock'ları yardımcı içerik okumasına açılmaz.

### Projection ve ayrı handoff

`ServiceProjection` özgün `VolumeBinding` nesnesini, principal değerlerini ve
receipt'in canonical alanlarını sabitler. Host/target dönüşümünde yalnız home
yolu değişir; config, kaynak ve store kimlikleri aynı kalır. Nesne referansı
korunsa bile bağlı principal/volume/receipt değerlerinin değişmesi reddedilir.

Servis layout'u ayrıca seçilmeden servis receipt'i kullanılamaz. Host, bind ve
target kontrolleri mevcut projection sırasına eklenir. Target receipt, kimlik
düşürme, network filter ve Landlock aşamalarından sonra yeniden doğrulanır.
Bu kaynak yolu yeni kernel çalıştırma veya kurulu confinement kabulü değildir.

`alaz-service-startup-v1` handoff'u en fazla **16.384 byte**'tır. Exact alanlar,
canonical JSON ve caller'ın beklediği home zorunludur. State/response/profile
kimlikleri ve önceki epoch/instance eşleşir. Eski retained protokolü aynı kalır;
iki protokol birbirinin payload'ını örtük biçimde kabul etmez. Handoff yalnız
config kimliği, boyutu ve özetini taşır; ham config veya credential içermez.

### Aynı sahip üzerinde startup, consumer ve execution

`NativeStoreStartup(..., service_profile=...)`, prepared layout ve response
expectation gerektirir; retained seçimiyle birlikte kullanılamaz. Aynı özgün
owner tipi, üç store ve cold preflight korunur. Config, native import ve
constructor sınırlarında, epoch ilerlemesi çevresinde yeniden kontrol edilir.
Constructor etkisi bilinmiyorsa otomatik tekrar veya lease bırakma yapılmaz.

Consumer özgün receipt nesnesini ve servis kaynak seçimini tutar. Servis profili
`borrowed_service`/finite/canonical/local seçeneklerini gerektirir. Receipt'in
değiştirilmesi veya kaldırılması, yanlış kaynak ve config drift yeni hazırlama,
readiness, publication veya activation kontrolünü durdurur.

Execution boundary bind sırasında özgün servis/native owner, lease, actor ve
receipt bağını saklar. Native `load_config_readonly()` değiştirilmeden çağrılır;
hemen öncesinde ve sonrasında dosya kimliği/özeti yeniden kontrol edilir.
`HERMES_HOME` ve native `get_config_path()` aynı seçilmiş dosyayı göstermelidir.
Context-local başka home seçimi ve dosyayı atlayan non-None worker config
snapshot'ı reddedilir. Worker thread bu kontrol için ana thread'e bağlı lease
ve SQLite kontrollerini çağırmaz. Eski varsayılan yol aynı kalır.

## Cleanup, snapshot ve effective-config sınırı

Config byte'larının değişmesi yeni işi durdurur; özgün receipt ve kaynak
sahipliği korunuyorsa bilinen detach/store close yoluna yeni config okuması
eklenmez. Cleanup kimlik, transaction, storage, quiescence ve native detachment
kontrollerinden geçmeye devam eder. Receipt/owner kaybı temiz kapanış sayılmaz.

`HERMES_HOME` değişikliği ayrı bir durumdur: mevcut `ProfileLease.check()` zaten
ortam/home sahipliğini yeniden doğrular. Bu eski ret davranışı gevşetilmedi.
Dosya drift'i sonrası başarılı fixture kapanışı ortam drift'ine genellenmez.

Receipt caller'ın beklentisidir; imza veya bağımsız yetki belgesi değildir.
Snapshot'lar gözlenen değişimi yakalar; aynı UID ile eşzamanlı yabancı yazarı
ve her ABA yarışını dışlamaz. Özgün lease ve writer dışlama önkoşulları sürer.

Native loader'ın “readonly” adı yalnız dönen config'in kullanım sözleşmesidir;
home/default/env/managed işlemleri ve config backup yazıları olabilir. Bu
paket ham seçilmiş byte'ları bağlar; bütün effective-config, plugin, secret
ve managed-overlay davranışlarını kabul etmiş sayılmaz. Mevcut model policy
denetimleri korunur. Loader'ın oluşturabileceği yeni girdiler allowlist'e
otomatik eklenmez; service restart/capture ve backup yaşam döngüsü hâlâ açıktır.

## Tarihsel kaynak ve güncel nesil

Değişen parent dosyaları exact byte/hash arşiviyle ayrı korunur. Tarihsel seçici
yalnız bilinen parent hash'ini bu arşive çözer; bilinmeyen veya güncel nesli eski
makbuza yönlendirmez. Güncel dört ürün dosyasının ayrı sabit SHA kontrolleri
vardır. Arşiv doğrulaması eski runtime sonucunu R161 kabulüne dönüştürmez.
Kayıt: [historical-source-bindings.json](../evidence/p2-service-profile-r161a1/historical-source-bindings.json).

## Test kapsamı ve yayın durumu

Aşağıdaki beş yeni modülde toplam 133 test vardır. İlgili eski startup, consumer,
execution, projection, handoff ve tarihsel kaynak denetimleriyle birleşik seçim
293 testtir. Donmuş yedi ürün dosyasının test öncesi/sonrası hashleri eşleşti.
Linux koşusu 293 PASS, 0 SKIP; Windows koşusu 285 PASS, 8 SKIP verdi. İkisinde
failure/error 0 ve exit 0. Windows atlamaları POSIX FIFO/link/owner denetimleri
ve symlink fixture erişimiyle sınırlıdır; aynı denetimler Linux'ta geçti.

| Yeni suite | Test | Sınanan kapsam |
|---|---:|---|
| `test_service_profile_r161a1.py` | 40 | Gerçek geçici dosya/FD, canonical config, snapshot, metadata ve yardımcı okuma yarışları |
| `test_service_profile_binding_r161a1.py` | 36 | Özgün owner/receipt, constructor/epoch/config drift, loader path/snapshot, worker thread ve cleanup |
| `test_service_projection_r161a1.py` | 27 | Host/target mapping, volume/principal/receipt değişimi ve projection aşama sırası; kernel portları fixture |
| `test_service_handoff_r161a1.py` | 18 | Ayrı protokol, bounded canonical codec, home/store/generation bağları ve payload reddi |
| `test_service_profile_history_r161a1.py` | 12 | Exact parent arşivi, ayrı güncel source pin'leri ve iki yönlü bozulma reddi |

Binding'in ayrı yerel koşusunda **36/36 PASS, exit0**; ilgili deterministik eski
startup/three-store/consumer/execution/R159 sınıflarında **72/72 PASS, exit0**
gözlendi. Bu sonuçlar native portları açık doubles ile sınar. SQLite kapanış
probları ve geçici dosyalar gerçektir; root fixture'ında yalnız owner ID'leri
normalize edilir. Native runtime, provider, model veya kernel kabulü çıkarılmaz.

Bağımsız donmuş kaynak incelemesinde yeni somut fail-open veya cleanup blocker
bulunmadı. Bu kaynak incelemesi kurulu servis çalışmasının yerine geçmez.
Geniş scratch koşusunda 144 testin 23'ü Node Unix socket `listen EPERM` nedeniyle
başarısız oldu; 121 test geçti. Tam R159 route grubunu içeren önceki koşu exit130
ile kesildi. Bu iki koşu tamamlanmış başarılı gate olarak kullanılmaz.

| Son makbuz | Doğrulanmış durum |
|---|---|
| [focused-linux.json](../evidence/p2-service-profile-r161a1/focused-linux.json) | 293/293 PASS, 0 SKIP, 4.503s, exit 0; Linux, Python 3.12. |
| [focused-windows.json](../evidence/p2-service-profile-r161a1/focused-windows.json) | 293 test: 285 PASS, 8 SKIP, 10.914s, exit 0; Windows, Python 3.14. |
| [parent-source-check.json](../evidence/p2-service-profile-r161a1/parent-source-check.json) | 6 arşiv Git 5b7eba4 ile byte-exact; 24 aktarılan dosya, 8 korunmuş depo, 33 kök dosyası ve 760 native kaynak eşleşti. |
| `evidence/p2-service-profile-r161a1/source-ci.json` | PENDING; son exact commit'in tam CI ve yayın zinciri kaydedilecek. |
| Yeni kurulu servis ve gerçek model | NOT RUN; bu teslimat bu kabulü içermiyor. |

Tekrarlanabilir odaklı komut:
`python evidence/p2-service-profile-r161a1/focused-runner.py --label <yeni-etiket>`.
Runner mevcut kanıtı üzerine yazmaz. Makbuzlar unittest runner ham logunu
dosya boyutu ve SHA-256 ile bağlar. Tam CI bütün kök ve bileşen testlerini
ayrıca çalıştırır; bu odaklı seçimin sayısı tam CI sayısı değildir.

## Kesin sonraki iş

Son test ve source/CI makbuzlarını tamamla. Ardından sabit projected service
receiver/factory, özgün supervisor Unix sunucusu, child final/exit/EOF ile
volume stop/finish bağlantısı ve özel loopback'e host görev erişimini bağla.
Yeni tek P2 kurulumunda başlat/görev/izle/sonuç/kullanım/iptal/kapat akışını
doğrula. Gerçek sağlayıcı için model, araçlar ve harcama sınırı ayrıca seçilmeli.
Tam sıra [R161 entegrasyon planında](P2-SERVICE-INTEGRATION-R161A1-PLAN.md),
güncel yayın kararı [status.md](../status.md) içinde izlenir. **P2 açık kalır.**
