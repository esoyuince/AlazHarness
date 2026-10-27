# P2 / R162A1 — Sabit servis receiver ve özgün factory bağlantısı

Tarih: 27 Ekim 2026. **Odaklı kaynak testleri PASS; exact-commit CI ve yayın IN PROGRESS.**

Bu paket R161 servis profil/config kabulünü sabit projected receiver ve factory
üzerinden özgün üç-store startup, R159 BorrowedServiceOwner ve R160 control
driver'a bağlar. Supervisor Unix sunucusu, child final/exit/EOF ile volume
kapanışı, host görev erişimi, yeni P2 kurulum ve gerçek model kabulü açıktır.

Taban: `b56b9b321002a5bb8696fcae27edcfc92c28df1c`.
Native seçim: `5e3635c2cdfc2161fd20c089618bd7f2a7c12f2d`; 760 dosya
değişmedi. Başlangıçta sekiz korunmuş depo, kökün 33 değişmiş dosyası ve önceki
R161/R160 çalışma ağaçları doğrulandı. R156 kurulumu değiştirilmedi.

## Sabit receiver ve giriş

Yeni [gateway_service_launch.py](../packages/claw-hermes/gateway_service_launch.py)
ve [run_service_projected.py](../scripts/run_service_projected.py), eski
finite/readiness girişlerinden ayrı kardeş dosyalardır. Payload içinde executable,
komut, factory/callback, credential veya ham config yoktur.

`launch(..., scratch, instance_id, service_id)`, exact `ServiceStartup` ile
aynı volume/principal/profile bağını doğrular. R161 service projection kullanılır;
sonra ayrı service handoff, canlı identity/namespace ve mount gözlemi yapılır.
Sabit interpreter `/usr/bin/python3.12`, sabit `-I -B` argv ve sabit entry
kullanılır; host ortamı taşınmaz. Projection başladıktan sonraki hata,
projection'ı tekrar deneme veya host işine geri dönme yetkisi vermez.

Receiver'ın ayrı ortam alanları `ALAZ_SERVICE_WIRE` ve
`ALAZ_SERVICE_CONTEXT`; context protokolü
`alaz-projected-service-exec-context-v1`'dir. Wire ve context ayrı ayrı
16 KiB ile sınırlıdır. Exact alanlar, canonical JSON, PID, wire hash, yeni
instance, service ID ve home/mount kimliği doğrulanır.

Kontrol sırası:

1. Sabit Linux interpreter/flags ve exact environment/transfer.
2. Özgün live UID/GID/groups, capabilities, thread, no-new-privileges,
   namespace eşliği ve seccomp kontrolleri.
3. Gerçek mount'ın beklenen target/root/ext4/device ile eşliği.
4. Salt okunur gerçek service-profile inspection; selected source ve config
   kimliği/içeriği bu noktada yeniden kontrol edilir.
5. Ancak bu kontrollerden sonra sabit factory importu ve
   `execute(record, expected_mount, instance_id, service_id)`.

Bu aşamada receiver lease almaz, SQL açmaz veya native runtime başlatmaz.
Handoff verisi kendi başına kernel confinement veya başlatma yetkisi değildir.

## Factory ve aynı özgün sahip

[gateway_service_factory.py](../packages/claw-hermes/gateway_service_factory.py)
tek process attempt'i tutar. Ham config kabulünden sonra tek ProfileLease,
aynı `NativeStoreStartup`, aynı `BorrowedServiceOwner` ve mevcut R160
`drive_service` bağlanır. Ayrı runner, authority, epoch, queue veya sonuç
store'u oluşturulmaz.

`NativeStoreStartup` exact service receipt, prepared layout ve response
expectation ile kurulur. `owner.start()` yalnız bir kez çağrılır; native config
nesneleri bundan sonra hazırlanır. BorrowedServiceOwner, zaten VERIFIED olan
aynı owner'ın store ve epoch'unu kullanır; ikinci startup yapmaz.

Native loader'ın `readonly` adı yan etkisiz okuma anlamına gelmez: ilk parse
sonrasında native backup yazısı oluşabilir. Loader'ı strict profil/startup
kontrolünün önünde çağırmak bu kontrolün beklediği dosya kümesini değiştirirdi.
Factory gerçek loader'ı değiştirmeden startup sonrasına sıralar. Backup sonrası
yeniden başlatma/capture kabulü bu kaynak paketinin kapsamı değildir.

### Açık config sözleşmesi

Dosya R161'in en fazla 64 KiB canonical JSON sözleşmesiyle okunur. Okuma
bounded/no-follow/nonblocking FD yolundan geçer; inode, boyut, SHA ve kaynak
seçimi önce/sonra kontrol edilir. İkinci kontrolsüz dosya okuma yolu yoktur.

| Bölüm | Factory'nin kabul ettiği açık seçim |
|---|---|
| `model` | Tek model; `custom` provider; aynı API portundaki sabit `/alaz/provider/v1` route'u ve execution bearer eşliği |
| `gateway` | Multiplex ve session JSON yazımı kapalı; loop/systemd watchdog kapalı |
| `platform_toolsets` | Yalnız API için `file` |
| `platforms` | Tek etkin `api_server`; açık loopback host, port, API key ve model adı |
| `plugins` | Otomatik discovery listesi boş; yalnız `alaz-host-gate` entry, açık tool override izni ve policy/execution settings |
| Host policy | Aynı tek model ve açık issued/dispatch/validity sınırları |
| Execution | Mevcut ExecutionPolicy; broker zorunlu, ayrı bearer, açık kontrollü okuma dosyaları ve broker principal contract |

API key, provider bearer ve broker signing key birbirinden farklıdır.
Değerleri public makbuza veya control frame'ine taşınmaz.

Gerçek native `GatewayConfig`, `PlatformConfig`, `PluginManager`,
`PluginManifest` ve `PluginContext` doğrudan oluşturulur. Genel
`load_gateway_config`, plugin discovery veya caller-selected constructor yoktur.
Manifest'in source alanı `project`'tir; bundled etiketiyle override guard'ı
atlanmaz. Context'in manager/manifest nesne kimliği, plugin ID ve profile scope'u
kontrol edilir.

Gerçek `load_config_readonly()` sonucu ve gerçek `context.get_config()`
üzerinden alınan tüketilen alanlar, seçilmiş raw config ile türleri de korunarak
karşılaştırılır. Gerçek config yolu ve `HERMES_HOME` eşleşmelidir; dosyayı
atlayan worker snapshot kabul edilmez. Native hata/fallback wrapper'ı normal
dict gibi kabul edilmez. Native cache değiştirilmez.

Bu kontroller bütün native DEFAULT_CONFIG veya managed overlay yüzeyini
nitelendirmez. Kaynak okuma pinleri
[native-constructor-sources.json](../evidence/p2-service-receiver-r162a1/native-constructor-sources.json)
içindedir; sekiz dosya aynı 760 dosyalık native manifest'e bağlıdır.

İlk `runtime_ownership` ve özgün store importları, mevcut lease/startup yolunun
güvenilir kurulum ve import yolu önkoşulunu kullanır. Factory'nin 760 dosyalık
qualification kontrolü sonraki config/plugin importlarından önce çalışır;
ilk native import öncesinde ayrı bir byte attestation sağladığı iddia edilmez.
Gerçek kurulum manifest'inin kabulü yeni P2 kurulum adımında ayrıca gerekir.

## Son READY kontrolü ve doğrulanan eski boşluk

Mevcut BorrowedServiceOwner, son execution readiness await'inden sonra config'i
yeniden okumadan READY'ye geçebiliyordu. Yeni yedi test parent kaynakta
**3 PASS, 4 FAIL, 0 ERROR, exit 1** verdi. Dört negatif durum: son beklemede
config değişimi, receipt kaldırılması, kaynak seçimi değişimi ve son import
doğrulaması sırasında config değişimi.

Dar ürün değişikliği, son native source verification ardından özgün actor/loop
ve owner-held bağını, sonra startup'ın mevcut `_check_service_config()`
guard'ını yeniden çağırır. READY bundan sonra yayımlanır. Aynı yedi test
**7/7 PASS** oldu. Hata, mevcut UNKNOWN ve native admission seal yoluna gider;
ikinci start veya yeni owner oluşturulmaz.

Service profile bulunmayan eski seçimde yeni config I/O'su yapılmaz. Cleanup
koduna config okuması eklenmedi: byte drift sonrasında özgün sahiplik korunuyorsa
bilinen transport/runtime/API/consumer/executor/store/lease sırası çalışabilir.
[Başlangıç red kanıtı](../evidence/p2-service-receiver-r162a1/ready-config-baseline.json)
ve [son odaklı kayıt](../evidence/p2-service-receiver-r162a1/ready-config-focused.json)
ayrı korunur.

## UNKNOWN, loop ve final sınırı

Factory `asyncio.run()` kullanmaz. İlk profile reservation denemesinden itibaren
belirsiz hata aynı attempt ve event loop üzerinde tutulur. Otomatik close,
detach, task cancellation, lease finish veya yeni owner/loop ile tekrar yoktur.

Diagnostic yazımının kendisi retention'ı bozamaz: exception metnine dönüştürme
ve stderr write/flush hataları bounded, best-effort yoldadır. Mevcut loop
beklenmedik biçimde kapanmışsa aynı process/thread, orijinal nesne referanslarını
tutar; yeni loop/thread/service oluşturularak belirsizlik gizlenmez.
Diagnostic yalnız exact `ServiceFactoryRejected` kodlarını kullanır; diğer
exception türlerinin metni okunmadan genel hata kodu üretilir. Böylece native
exception metnindeki credential biçimli bir token stderr'e taşınmaz.

R160 driver aynı somut servisi yönetir; READY, command/reply ve final frame'leri
onun kontrolündedir. Başarılı factory dönüşü service ID, aynı PID, yeni
epoch/instance, özgün driver/service/startup/held nesneleri ve CLOSED receipt
ile bağlıdır. Üç store'un kapanışı ve caller/profile lease release mevcut owner
kapanış zincirinden gelir. Loop ancak temiz final ve boş pending-task kümesi
doğrulandıktan sonra kapanır.

Native Python stdout'u stderr'e yönlendirilir; control kanalı FD 1'e doğrudan
canonical frame yazar. Sabit giriş finali ikinci kez yazmaz; yalnız doğrulanmış
current-PID final sonrasında exit 0 verir. Parent, final frame'i tek başına
volume/image lease bırakma izni sayamaz: gerçek exit, stdout/stderr EOF,
cgroup, worker stop/finish ve loop/unmount kanıtı sonraki supervisor bağlantısında
birlikte doğrulanacaktır.

## Kaynak geçmişi ve test durumu

Parent runtime, b56b9b3 neslinden **17.305 byte / SHA-256
7936c0d964fcefcdb6d92c6c5c38ed4abcbbef421dcf731a47e8b80c69359a92**
olarak ayrı arşivlendi. R162 tarihsel çözümleyici yalnız exact eski path/hash
çiftini bu arşive yönlendirir. Güncel ve bilinmeyen hash'ler eski arşivle
kabul edilmez; güncel runtime pin'i ayrıdır. Dokuz eski R159 receipt ve eski
R161 core/history dosyaları yeniden yazılmadı.

| Yerel kaynak kontrolü | Doğrulanmış sonuç |
|---|---|
| Receiver/entry yeni suite | 35/35 PASS |
| Receiver + ilgili eski launcher/finite/handoff seçimi | 102/102 PASS, failure/error/skip 0, exit 0 |
| Yeni READY guard + history + ilgili lifecycle/history seçimi | 38/38 PASS, failure/error/skip 0, exit 0 |
| Factory yeni suite | 39 test; son birleşik Linux ve Windows seçimlerinde PASS |
| Son birleşik Linux seçimi | 483/483 PASS, failure/error/skip 0, exit 0; 10,854351 s |
| Aynı seçim, primary Windows | 466 PASS + 17 platform SKIP = 483; failure/error 0, exit 0; 38,271473 s |
| Bağımsız factory config/native ve lifecycle incelemeleri | PASS; test çalıştırma iddiası taşımayan iki ayrı review kaydı |
| Exact-commit tam CI ve yayın | IN PROGRESS |

Yeni test sayısı 90'dır: receiver 35, factory 39, son READY guard 7 ve kaynak
geçmişi 9. İlk birleşik Linux koşusu da 483/483 geçti. Ardından yalnız factory
testindeki subprocess satır sonu karşılaştırması Windows CRLF ile uyumlu hale
getirildi; ürün kodu değişmedi. İlk kayıt `focused-linux.*` olarak korundu;
son test snapshot'ının kabulü `focused-linux-r2.*` ve `focused-windows.*`
üzerindedir. İki son koşu aynı 483 test kimliğini, runner hash'ini ve 14 ürün
kaynak hash'ini taşır. Windows'taki 17 atlama kayıtta ayrı gerekçeleriyle listelenir.

Receiver'daki dört Linux testi gerçek geçici profile/config dosyalarını kullanır;
kernel/namespace/mount/exec portları fixture'dır. READY testleri gerçek service
start/failure/closure kodunu, gerçek config byte'larını ve SQLite kapanış
gözlemlerini kullanır; native preparation, HTTP ve execution readiness portları
doubles olarak açıklanır. Kaynak testinden gerçek native servis/model kabulü
çıkarılmaz.

Factory testleri gerçek harness factory → NativeStoreStartup →
PreparedRuntimeConsumer → BorrowedServiceOwner → R160 control zincirini ve üç
gerçek SQLite kapanış gözlemini çalıştırır. Native constructor/config loader,
kernel/lease preflight, native preparation/publication/HTTP/retirement, broker
readiness, executor join ve POSIX allowlisted-path portları açık fixture'lardır.
Tek start ve epoch ilerlemesi, özgün store/authority/runner kimlikleri, known-busy
close, pre-driver hata, ikinci deneme reddi, diagnostic kaybı ve finalin tek
yazılması sınanır. Kapalı loop testi fresh subprocess içinde aynı referans ve
tek thread'in korunduğunu gözler; test timeout'u yalnız test çocuğunu sonlandırır.

Kanıtlar [R162 dizininde](../evidence/p2-service-receiver-r162a1/).
Odaklı koşular ve bağımsız incelemeler tamamlandı. Yayın kabulü için exact
commit'in tam root/component CI sonucu ayrıca doğrulanacaktır.
Yeni kurulum veya gerçek model/sağlayıcı çağrısı yapılmadı.

## Sonraki somut iş

Factory birleşik kaynak testleri ve exact-commit yayını tamamlandıktan sonra,
[entegrasyon planının](P2-SERVICE-INTEGRATION-R161A1-PLAN.md) üçüncü adımı:
özgün ServiceVolumeSupervisor ve Popen'a bağlı supervisor Unix kontrol sunucusu.
Ardından child final/exit/EOF ile volume stop/finish ve host görev erişimi gelir.
Native backup/restart/capture/effective-config ve yeni tek P2 kurulum kabulü
açıktır. Model/sağlayıcı, araçlar ve harcama sınırı seçilmeden gerçek model
deneyi başlatılmaz. **P1 DONE; P2 IN PROGRESS; tam M1 ve production OPEN.**
