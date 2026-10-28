# P2 / R165A1 — host görev erişimi

**IN PROGRESS — Linux/Windows odaklı kabul, source/statik kapı ve source tam CI PASS;
closure/final CI ve main yayını sırada.** Kaynak CI kabul kaydı: 2026-10-28T00:14:26.232108+00:00.
Exact source commit `acb9aa2c5e903afe6fd919aedcc26a5acc959674`; parent `994751bed14046e3e0dd14be90912048b996a836`.
Yeni tam CI: **4647 RUN / 4614 PASS / 33 SKIP /
0 FAIL / 0 ERROR**, exit 0; gerçek sayılar ve kabul zinciri
[source CI makbuzuna](../evidence/p2-host-task-access-r165a1/source-ci.json) bağlıdır.

Odaklı Linux **459/459 PASS, 0 SKIP**; Windows **459 RUN / 241 PASS / 218 SKIP**.
İki odaklı kabulde FAIL/ERROR 0 ve exit 0; ilk Linux ve Windows FAIL kayıtları
ayrı, değişmeden korunur. Ürün/test/süreler dar tanı veya tekrar için değiştirilmedi.

Aktif dal, primary çalışma yolu ve iş günlüğü [status.md](../status.md) içindedir.
Bu paket [P2 entegrasyon planının](P2-SERVICE-INTEGRATION-R161A1-PLAN.md) beşinci
adımıdır. P1 DONE; P2 IN PROGRESS; P3–P5, tam D3B, M1 ve production OPEN.
Yeni kurulum, gerçek native/kernel servis ve model kabulü NOT RUN.

Aşağıdaki uygulama ve odaklı kabul bölümleri, source commit'teki anlık görüntünün
baytlarını korur. Bu tarihsel bölümlerdeki CI `NOT RUN` ifadeleri kaynak öncesi
aşamaya aittir; güncel source CI sonucu sondaki yayın bölümünde kayıtlıdır.
Final/main sonuçları henüz oluşmadığı için bu kapanış belgesine gelecekteki SHA
yazılmaz; sonraki kesin aşamalar `scratch/r165-publication/final-publication.json` ile izlenir.

## Amaç ve seçilen yol

Servis çocuğu kendi network namespace'inde `127.0.0.1` listener'ını açar.
Host CLI'nin loopback'i aynı endpoint değildir. Projection ayrıca standart
akışlar dışındaki ambient FD'leri kapatır. R165 bu sınırları koruyarak,
hosttaki özel Unix endpoint'inden aynı özgün çocuğun mevcut stdin/stdout
FIFO/pipe akışına sınırlı görev çerçeveleri taşır. Child, isteği
kendi sabit loopback endpoint'indeki gerçek HTTP API'ye iletir.

Taşıma yeni görev kuyruğu, sonuç deposu, native owner, süreç veya imaj sahibi
oluşturmaz. Mevcut runner/authority/epoch ve üç fiziksel store görevlerin
sahibidir. Kimlik doğrulaması, Host Gate admission ve yürütme/bütçe denetimleri
aynı native API üzerinde kalır. CLI taşıması aşağıdaki ortam değişkeniyle
seçilir; JavaScript API'sindeki `taskTransport` ayrı constructor seçeneğidir.

## CLI bağlantısı ve varsayılanlar

[CLI](../scripts/alaz_local.mjs), görev ve gözlem komutları için
`ALAZ_TASK_TRANSPORT=supervised-service` seçimini kabul eder. Değişken
verilmezse mevcut HTTP taşıması kullanılır. Supervisor taşıması Linux ve
Node 24 gerektirir; taşıma hatasında host TCP'ye otomatik geçiş yapılmaz.

| Alan | Geçerli bağlantı / varsayılan |
|---|---|
| `ALAZ_TASK_TRANSPORT` | Verilmezse HTTP; verilirse yalnız `supervised-service` |
| `ALAZ_BASE_URL` | Her iki taşımada zorunlu literal loopback URL; Unix modunda izinli yolların origin eşlemesidir, gerçek HTTP hedefini özgün child sahibi belirler |
| `ALAZ_API_TOKEN` | Her iki taşımada zorunlu; verilen token native HTTP'ye Bearer olarak iletilir |
| Supervisor bağlantısı | `ALAZ_SERVICE_SOCKET`, `ALAZ_SERVICE_ID`, `ALAZ_SERVICE_OWNER_PID`, `ALAZ_SERVICE_OWNER_START_TICKS`, `ALAZ_SERVICE_OWNER_TOKEN` birlikte, güvenilir özgün owner kaydından sağlanır |
| `--request-timeout-ms` | Varsayılan 5.000 ms; aralık 10–60.000 ms |
| İstemci response sınırı | Varsayılan 1.048.576 byte; JavaScript `maxResponseBytes` üst sınırı 4.194.304 byte, CLI'de ayrı response-limit seçeneği yok |
| Watch/cancel | `--wait-ms` varsayılanı 30.000 ms; `--poll-ms` varsayılanı 100 ms |
| CLI `--input` | UTF-8 dosya veya stdin; en fazla 65.536 byte, transport request-body üst sınırından ayrı |

`start`, `close` ve `service-status` aynı beş supervisor alanını kullanır.
Görev, request, status, watch, result, usage ve cancel için base URL/token
zorunluluğu supervisor taşıması seçildiğinde de sürer. Varsayılanlar
[task istemcisi](../packages/claw-hermes/service-task.mjs) ve
[yerel kontrol](../packages/claw-hermes/local-control.mjs) koduyla bağlıdır.

## Altı izinli HTTP yolu

| Yöntem | Yol | İşlev |
|---|---|---|
| GET | `/alaz/host/v1/capabilities` | Mevcut yetenek ve sınır sözleşmesi |
| POST | `/alaz/host/v1/intents` | Özgün request ID için Host Gate izni |
| POST | `/alaz/host/v1/dispatch` | Mevcut izinle tek görev aktarımı |
| GET | `/alaz/host/v1/requests/<32lowerhex>` | Kayıp yanıt sonrası özgün istek sorgusu |
| GET | `/v1/runs/run_<32lowerhex>` | Aynı run üzerinden durum, sonuç ve kullanım |
| POST | `/v1/runs/run_<32lowerhex>/stop` | Mevcut native iptal yolu |

Query, fragment, percent-encoded yol ve caller tarafından seçilen origin
kabul edilmez. Raw run yaratma veya provider endpoint'i bu taşıma sözleşmesine
girmez. Gelen Bearer credential native HTTP API'ye aynen iletilir; başka bir
credential üretilmez ve HTTP handler doğrudan çağrılmaz. HTTP hata durumu ve
gövdesi korunur; redirect izlenmez. İzinli header kümesi ve sürüm değerleri
ayrıca doğrulanır. HTTP oturumu her exchange'e aittir, `trust_env=False` olur
ve kalıcı background oturum oluşturmaz.

## Framing, kimlik ve sınırlar

Görev çerçevesi `ALAZTASK/1 ` öneki, compact ASCII JSON ve tek LF taşır.
Body canonical base64 olarak kodlanır; tekrarlı alanlar reddedilir. Hostun
tam çerçevesi ve write EOF'u alınmadan child'a yönlendirme yapılmaz.
Host protokolü `alaz-service-task-client-v1`, child protokolü
`alaz-service-task-v1` olarak ayrı seçilir. Özgün lifecycle şemaları ve
**65.536 byte** çerçeve sınırı korunur.

| Alan | Protokol sınırı |
|---|---:|
| Decode edilmiş request body | En fazla 1.048.576 byte |
| Decode edilmiş response body | En fazla 4.194.304 byte ve caller sınırı |
| Header toplamı | En fazla 8.192 byte |
| Tam task request çerçevesi | En fazla 1.500.000 byte |
| Tam task response çerçevesi | En fazla 5.700.000 byte |
| `timeoutMs` | Exact integer, 10–60.000 ms |
| `maxResponseBytes` | Exact integer, 128–4.194.304 byte |
| Parent gözlem beklemesi | En fazla 60 saniye |

Özel Unix bağlantısı aynı service ID ile supervisor PID/startTicks/token
kimliğine bağlıdır. Her dış exchange'in ayrı request ID'si vardır. Child
isteği lifecycle komutlarıyla aynı monoton sequence'i ve sequence'e bağlı
request ID'yi kullanır; aynı kanalda tek bekleyen exchange bulunur. Task
yanıtındaki özgün owner ve sequence doğrulanmadan HTTP sonucu kabul edilmez.
Standart service status çıktısı body, header veya credential taşımaz.

## Kayıp yanıt ve kapanış sözleşmesi

Bir dış request ID ikinci POST aktarımı başlatamaz. Görülmüş ID'lerin sınırlı
metadata kaydı dolduğunda eski mutasyonlar tekrar açılmaz. Otomatik POST retry
yoktur; istemci özgün native request locator'ını yeni bir salt okunur HTTP
exchange ile sorgular. Gecikmiş child yanıtı yeniden gönderim yapmadan
gözlenebilir kalır. İstemcinin ayrılması görev iptali veya kaynak bırakma
kanıtı sayılmaz.

Sunucunun POST kimliği kapasitesinin varsayılanı ve üst sınırı 4.096'dır;
salt okunur sorgular bu kapasiteyi tüketmez. Bu kayıt yalnız aktarım kimliği
ve fingerprint tutar; görev veya sonuç store'u değildir.

Geçerli HTTP hata yanıtı lifecycle'ı tek başına belirsiz yapmaz. Bozuk
kimlik/çerçeve veya etkisi belirsiz pipe işlemi özgün sahibi ve mevcut
belirsizlik kaydını tutar. READY/draining kabul sınırları native servis
sahibinden gelir. Task yanıtı, status veya bağlantının kaybolması child final,
exit0, iki EOF ve özgün volume stop/finish zincirinin yerini almaz.

## Kaynak ve tarihsel kanıt sınırı

R164A2 başlangıcındaki kaynakların gerçek parent Git baytları
[parent-source.json](../evidence/p2-host-task-access-r165a1/parent-source.json)
ile ayrı bağlandı. Önceki odaklı sonuçlar, CI kayıtları ve
tarihsel resolver'lar yeni koşu yapılmış gibi güncellenmez. R165'in güncel
kodu için ayrı kaynak/test seçimi, önce/sonra hashleri ve taze koşu gerekir.

Native servis seçimi R159'un
`5e3635c2cdfc2161fd20c089618bd7f2a7c12f2d` nesline bağlıdır. Mevcut
`gateway_service_sources.REQUIRED` ve servis manifest'i zaten
`agent/secret_sources/command.py`, `api_server_metrics.py` ve
`api_server_authority_runs.py` kaynaklarını içerir. Önceki R156 command-module
mesajı tarihsel bir kurulum bulgusudur; güncel servis kaynak seçiminin bu
dosyayı atladığı iddiası değildir. Seçilmiş sağlayıcının gerçek kurulumdaki
import, effective-config ve credential yolu ayrıca kabul edilecektir.

## Altıncı adımın açık işi: yeni candidate ve kurulum

Yerel `service_task_protocol.py`, `service_task_http.py` ve
`service_task_server.py`, mevcut builder'ın `packages/claw-hermes/*.py`
seçimine otomatik girer. Native Hermes manifest'ine veya upstream component
lock'una yeni yerel modül kaydı gerekmez. Bu kaynak seçimi kurulum kabulü değildir.

[Mevcut builder](../scripts/build_projected_candidate.py) hâlâ retained/finite
`d1516731308de8e87130dc68124e69aad35d6911` neslinin **756 native dosyasını**
paketler. P2 servis seçimi ise
`5e3635c2cdfc2161fd20c089618bd7f2a7c12f2d` neslinde **760 native dosya** içerir.
Builder'ın sabit giriş listesinde `run_supervised_service.py`,
`run_service_projected.py`, `run_service_volume_worker.py` ile servis
selection/manifest/host-lock config'leri yoktur. Host CLI ve `.mjs` modülleri
de projected candidate kapsamına girmez.

Planın altıncı adımı bu yüzden ayrı, güncel P2 candidate/install paketi gerektirir:
servis generation'ı ve kaynak/config kapanışı, sabit girişler, Node 24 host CLI
dağıtımı ve bağımlılıkları kesin envantere bağlanmalıdır. Host CLI dağıtımı,
child'ın readonly Python/native kaynak alanından ayrı tanımlanmalıdır.
[Installer](../scripts/install_projected_candidate.py) builder'ın kesin hashini,
manifest'i ve envanterini denetler; eski finite kurulumu yeniden adlandırmak
bu bağı kurmaz. Kabul edilmiş R156 kurulumu ve tarihsel kanıtlar korunur.

## Linux odaklı kabul ve korunan ilk başarısız koşu

Son [makbuz](../evidence/p2-host-task-access-r165a1/focused-linux-02.json) ve
[ham log](../evidence/p2-host-task-access-r165a1/focused-linux-02.log), Linux
Python 3.12.14 üzerinde **459 seçili ve çalıştırılmış tekil testin tamamının
PASS** olduğunu gösterir. FAIL, ERROR ve SKIP 0; exit 0; süre **102,228894
saniye**. Seçili ve çalıştırılmış sıralı test kimlikleri aynıdır. Makbuzdaki
82 ürün, 26 test ve 81 destek girdisi ile koşucunun önce/sonra hashleri sabittir.

| Kanıt | SHA-256 |
|---|---|
| Son Linux JSON makbuzu | `6bc116d89cb66cf84be466444d9200a6ddbd93695f443b77af7b1a510441b1bf` |
| Son Linux ham logu, 69.877 byte | `3527aafb9016b811d17ca3ce68c0c71496d74f622194cb9b1c7d44420ff6b263` |
| Odaklı koşucu | `4914833ef72c8dec2d81a1ebffc188dc312ba66a48f12765fabf8579b0f8b312` |
| Sıralı seçili/çalıştırılmış test kimlikleri | `c74abcc9063bbba53118ac32fbda68cffff828836a411c1e7482a9d95906449c` |

İlk [makbuz](../evidence/p2-host-task-access-r165a1/focused-linux.json) ve
[log](../evidence/p2-host-task-access-r165a1/focused-linux.log) **FAIL** olarak
korundu: 458 test, 451 PASS, 1 FAIL, 6 ERROR, 0 SKIP, exit 1. Altı ERROR,
kısmi cloud export'unda eksik olan R158 binding dosyası ve dört exact arşiv
yüzündendi. Bu beş dosya başlangıç commit'i
`994751bed14046e3e0dd14be90912048b996a836` üzerinden alınıp Git blob kimlikleri
ve [R158 resolver binding'i](../evidence/p2-local-control-r158a1/historical-source-bindings.json)
ile hash/boyut düzeyinde doğrulanarak tamamlandı. Tarihsel byte veya test
beklentisi yeniden üretilmedi. Koşucu bu girdileri artık açıkça hashler.

Tek FAIL, mevcut `test_local_control.LocalControlTests.test_watch_timeout`
vakasının başlangıç isteğindeydi. İlgili test baytları değişmeden yapılan
baseline/current karşılaştırmasının 16 normal denemesinde tekrar üretilemedi;
zorlanmış event-loop durması her iki nesilde de hata verdi. Bu araştırma ilk
FAIL'i PASS'e çevirmez. Son seçim, task yanıtından sonra tamamlanmamış byte
kalmasına ilişkin bir channel regresyonu ekler; ilk seçimin testleri kaldırılmadı.

Sabit CI image'ında `aiohttp` bulunmadığı salt okunur preflight ile görüldü.
Standart discovery, bu bağımlılık yokken gerçek HTTP fixture testlerini açık
gerekçeyle SKIP kaydeder. Hazırlanmış Linux odaklı koşucu ise `aiohttp`
bulunmasını zorunlu tutar; yukarıdaki 459 testin tamamı çalıştı. Standart
source/final CI henüz çalışmadığı için ona ait PASS veya SKIP sayısı yoktur.
CI bağımlılık kurulumu veya image/politika değişikliği yapılmadı.

Bu sonuç gerçek fixture socket/pipe/HTTP ve doğrudan lifecycle/client/history
kapsamındadır. Kurulu native servis, kernel confinement ve gerçek model/provider
kabulü değildir; makbuzda gerçek model/provider çağrıları 0'dır.

## İlk Windows odaklı koşusu ve sınırlı tanı

İlk [Windows makbuzu](../evidence/p2-host-task-access-r165a1/focused-windows.json)
ve [ham log](../evidence/p2-host-task-access-r165a1/focused-windows.log), aynı
459 seçili testte **240 PASS / 218 SKIP / 1 FAIL / 0 ERROR**, exit 1 ve
**107,029062 saniye** kaydetti. Başarısız test mevcut
`test_hybrid_wire.HybridWireTests.test_timeout` vakasıdır. Bu koşu kabul
kapısını geçmedi; ilk Linux FAIL kaydından ayrı, değişmeden korunur.
Kaynak/test/destek ve koşucu hashleri ile sıralı test kimlikleri Linux seçimiyle
eşleşir. Test süreleri, assertion'lar ve ürün/test kaynakları değiştirilmedi.

| Korunan Windows kanıtı | SHA-256 |
|---|---|
| İlk Windows JSON makbuzu | `5696d2ee9271ad78fe6e0ca19af5962c42e0e086303ef68658a08bb9e7881ff0` |
| İlk Windows ham logu, 93.016 byte | `f63130cffa1963f7eecbc0bc7d8451fb60ca25ba00ae3d3088cc533b42c0948e` |

Dar BASE/current incelemesi request 33 ile completed/exit 0 tamamlandı.
Aynı özgün testin BASE üzerinde altı, güncel kaynak üzerinde altı normal
tekrarının tümü geçti. Ayrı iki kontrollü 350 ms gecikme demosunda injection
her iki sürümde gözlendi; ikisi de `settlement_unconfirmed`, `state=unknown`
ve `backendConfirmed=false` üretti. Bu demolar ürün kabulü değildir ve ilk
Windows FAIL'inin kesin kök nedenini kanıtlamaz. Clone/source hashlerinin
inceleme boyunca değişmediği doğrulandı.

Özel tanı kaydı:
`scratch/r165-publication/wire-timeout-investigation/wire-timeout-diagnosis.json`,
SHA-256 `ef941c268d11d4a5a899c53449c92302d840c36bad792d8a35e5dcfece1005ad`.
İlk iki başarısız focused kaydı yeni koşuya aktarılmış başarı sayılmaz.

## Son Windows odaklı kabulü

Taze [Windows makbuzu](../evidence/p2-host-task-access-r165a1/focused-windows-02.json)
ve [ham log](../evidence/p2-host-task-access-r165a1/focused-windows-02.log), request
34 completed/exit 0 ile **459 RUN / 241 PASS / 218 SKIP / 0 FAIL / 0 ERROR**
kaydetti. Süre **87,580529 saniye**. Seçilen/yürütülen sıralı test ID hash'i
`c74abcc9063bbba53118ac32fbda68cffff828836a411c1e7482a9d95906449c`, Linux
koşusuyla aynıdır. 82 kaynak, 26 test ve 81 destek girdisi ile koşucu
hashleri koşu öncesi/sonrası değişmedi ve Linux seçimiyle eşleşti.

Windows JSON makbuzu **188.392 byte**, SHA-256
`467bb6dfe54af160c1bb0fe2c5e8925016c095ee249a9c5bc83639fe39b1d5c8`.
Windows logu **89.964 byte**; SHA-256
`8ae9e94300661d1ab206c95d470fe8d16ad7e77d18a7f0c1671357dbffb69669`.
Koşucu SHA-256
`4914833ef72c8dec2d81a1ebffc188dc312ba66a48f12765fabf8579b0f8b312`.
Windows'taki 218 SKIP, POSIX pipe/SIGINT ve Linux Unix socket/peer credential/process
identity koşulları için kaydedilmiş platform sınırlarıdır; başarı sayısına eklenmez.
Linux odaklı koşusunda aynı
459 testin tamamı çalışıp PASS oldu. Dar tanının normal tekrarları ve kontrollü
gecikme demoları bu birleşik seçimin test sayısına ayrıca eklenmez. Yeni PASS,
korunan ilk FAIL'in kesin nedenini kanıtlamaz. Bu kanıt kaynak/fixture kapsamındadır;
kurulu native servis, gerçek kernel confinement veya model kabulü değildir.

## Primary aktarımı ve kalan yayın kapıları

Önceki kesintide ilk paket üç dosyada uygulanmıştı; eski request 10 kesin
`failed/not_started` olarak kaldı. Yeni request 12'nin geçmiş yürütme sonucu
**UNKNOWN** kaydı korunuyor. Bağlantı dönüşünde request 14 canlı dosya
önkoşullarını okudu: ikinci paketin dört dosyası exact önceki baytlarıyla
bulundu. Runtime'ın yeniden başlamış olması ve kuyruğun boş gözlenmesiyle
birlikte mevcut dosya durumu uzlaştırıldı; eski işlem için başarılı veya
başlamamış makbuz üretilmedi.

Sonraki yeni request 15–18 aktarımı hash doğrulamasıyla tamamlandı. **24/24
ürün/test dosyası**, odaklı koşucu ve bütün dondurulmuş public Linux/parent
kanıtları primary'de doğrulandı. Bridge erişimi canlı; son Windows odaklı
kapısı da PASS.

## Source commit, statik kapı ve yeni tam CI

Kaynak commit'i `acb9aa2c5e903afe6fd919aedcc26a5acc959674`, parent `994751bed14046e3e0dd14be90912048b996a836` üzerinden normal feature
push ile yayımlandı. 52 kaynak/doc/evidence yolunu bağlayan source manifest SHA-256
`93db883d906d9a86dae7163811de4f238a1031812effe2a5b9384ce1d7588d9b`; source-check SHA-256 `37b90fa45e5a27e8915ca4d1357a5adeb96a19490a5d151d53368cd346352cbc`.
İlk Linux ve Windows FAIL raporları/logları bu kaynak paketinde değişmeden korundu.

Staging/statik kapısı **PASS**, exit 0: staged tree `1b554ddb277f0213c0e28a761e3d90d6669d8062`,
keşfedilen test sayısı **4647**. Aynı source commit için yeni tam CI
[public makbuzda](../evidence/p2-host-task-access-r165a1/source-ci.json) **4647 RUN / 4614 PASS /
33 SKIP / 0 FAIL / 0 ERROR**,
**356.659 saniye**, container exit **0** kaydetti. `alaz/local-ci` status
ID **57424993426**, durum `success`; `fullSuiteExecuted=true`, `reused=false`,
`timeout=false`, `oomKilled=false`, container cleanup `removed`.
Public makbuz, kabul edilmiş özel source CI kaydının birebir aynı baytlarıdır.

CI SKIP sayısı PASS sayısına eklenmez; Linux odaklı kabul aynı 459 seçili testin
tamamını çalıştırdı. Sabit CI image/command ve 480 saniyelik politika değiştirilmedi;
politika SHA-256 `39feb838fe28d4176b40dc99d8dcc824648c1b374a3d168ef0e4a23bdade4776`.
Statik/fixture ve tam CI kabulü, kurulu native servis veya gerçek model kabulü değildir.

## Kapanış anındaki kalan kapılar ve güncel yayın kaydı

| Kapı | Bu kapanış kaynak kaydı hazırlanırken durum |
|---|---|
| Linux odaklı kabul | PASS — 459 RUN / 459 PASS / 0 SKIP / 0 FAIL / 0 ERROR |
| Windows odaklı kabul | PASS — 459 RUN / 241 PASS / 218 SKIP / 0 FAIL / 0 ERROR; ilk FAIL ayrıca korunur |
| 52 yollu source paketi ve staging/statik kapı | PASS — source commit'in exact tree ve hashleriyle bağlı |
| Source commit, normal feature push ve yeni tam CI | PASS — yukarıdaki exact source commit ve public CI makbuzu |
| Üç dosyalı closure commit/push ve yeni final tam CI | NOT RUN — sıradaki kapı |
| Normal main FF/push, aynı commit CI reuse kabulü ve son bütünlük | NOT RUN — final kapılarından sonra |
| Yeni P2 candidate/install ve gerçek kernel/native servis kabulü | NOT RUN — planın altıncı adımı |
| Gerçek provider/model/araç/bütçe seçimi | OPEN; gerçek model/provider kabulü NOT RUN |

Bu belge closure commit'i oluşmadan hazırlanır; kendi gelecekteki commit SHA'sını
içermez. Exact closure/final SHA, final CI, main yayını ve son bütünlük sonuçları,
bu kapılar gerçekten tamamlandıktan sonra `scratch/r165-publication/final-publication.json` günlüğüne bağlanır.
Bu yolun belirtilmesi, günlüğün var olduğu veya sonraki kapıların geçtiği anlamına gelmez.

Plan/roadmap'in source commit'te kalan staging/CI/yayın `NOT RUN` satırları,
kaynak öncesi anlık görüntüdür. Bu belgedeki source CI kaydı daha yeni aşamayı
gösterir; daha sonraki yayın için terminal günlük esas alınır. Aşağıda veya önceki
bölümlerde korunan tarihsel `NOT RUN` ve FAIL ifadeleri kendi kayıt anlarına aittir.
P1 DONE; P2 IN PROGRESS; P3–P5, tam D3B, M1 ve production OPEN.
Sıradaki yayın işi yalnız status.md, R165 raporu ve public source-ci.json için
closure commit/push ve yeni final tam CI'dır. Sonraki ürün işi yeni P2
candidate/install paketidir; eski R156 kurulumu ve tarihsel kanıtlar korunur.
