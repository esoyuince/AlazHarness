# P2 / R163A1 — özgün supervisor ve Unix kontrol sunucusu

Tarih: 27 Ekim 2026. **Odaklı kaynak ve source CI PASS; yayın IN PROGRESS; P2 IN PROGRESS.**

Bu paket [entegrasyon planının](P2-SERVICE-INTEGRATION-R161A1-PLAN.md) üçüncü
adımını uygular: özgün ServiceVolumeSupervisor içinde tek sabit servis çocuğu,
aynı Popen'a bağlı ServiceChannel ve R160 CLI'nin özel Unix kontrol sunucusu.
Child final/exit/EOF ile volume stop/finish bağlantısı, host görev erişimi ve
yeni kurulum kabulü ayrı açık adımlardır.

Taban: `dc1ccb5ecf4e9741f6fd828a03e8ebed7f9497b7`. Önceki R162 final yayın
günlüğü SHA-256 `7522fe8ea5267866a1a5de82368148c9a1452f7b50bf406cc46b44dd3bf33314`
ve canlı main/feature durumları doğrulandı. Sekiz korunmuş depo, kökün 33 dosyası
ve R162/R161/R160 çalışma ağaçları korunuyor. Native seçim
`5e3635c2cdfc2161fd20c089618bd7f2a7c12f2d`, 760 dosya; değişmedi.

## Özgün volume sahibi ve sabit çocuk

[ServiceVolumeSupervisor](../packages/claw-hermes/service_volume_supervisor.py)
aynı begin/attach/start akışını kullanır. Begin tek `_service_child` alanını
oluşturur; child kontrolü yeni
[gateway_supervised_service.py](../packages/claw-hermes/gateway_supervised_service.py)
kardeşine yönlendirilir. İkinci imaj lease'i, mount worker, volume sahibi,
native runner, authority, epoch veya sonuç deposu eklenmez.

`freeze_launch` bounded canonical bir veri seçimi üretir; launch girdileri
sonradan değiştirilebilen caller dict'lerine bağlı kalmaz. Bu veri çalıştırılacak
komutu veya factory'yi seçemez. Servis handoff'u, yeni instance/service ID,
scratch export ve sabit readonly giriş yolları effect öncesinde denetlenir.
Bir sonraki epoch'un ServiceChannel sınırında kalması da Popen öncesinde gerekir.

Launch yalnız exact özgün owner, aynı main thread, RUNNING worker ve aynı
lease/fence bağında ilerler. Özgün worker'ın namespace descriptor'ı ve cgroup
üyeliği denetlenir. Child attempt, Popen çağrısından önce owner üzerinde tutulur.
Popen dönüp sonraki PID/startTicks/channel adımı başarısız olduğunda da aynı
nesne korunur; yeni süreç veya gizli cleanup başlatılmaz.

Sabit argv `/usr/bin/python3.12 -I -B .../scripts/run_supervised_service.py`'dır.
Yalnız bilinen namespace FD'si ve standart pipe'lar aktarılır. Yeni
[bootstrap girişi](../scripts/run_supervised_service.py) bounded tek satırı
newline ile tamamlar; EOF beklemez ve kontrol stdin'inden buffered read-ahead
yapmaz. Child özgün doğrudan parent'ı denetler, önce cgroup'a katılır, sonra
bilinen mount namespace'e geçer ve aynı R162 `gateway_service_launch.launch`
fonksiyonunu çağırır. Eski finite/readiness launcher'ları değişmez.

`observe_service(timeout=0)` yalnız aynı child pipe'larını okur. Kısmen yazılmış
bootstrap veya close frame'inin kalan byte'larını göndermez. `close_service`
yalnız mevcut kanalın izin verdiği bilinen READY/DRAINING durumunda tek close
komutu gönderir; pending veya tamamlanmış isteği gözlemlemek yeni bir close
değildir. Özgün owner, worker, child, channel veya process kimliği kaybolursa
UNKNOWN aynı referansları tutar. Yabancı actor, özgün attempt'i UNKNOWN yapmak
için bile değiştiremez.

## Özel Unix kontrol sunucusu

[service_control_server.py](../packages/claw-hermes/service_control_server.py)
hazır RUNNING exact supervisor ve değişmez launch seçimiyle kurulur. Dış istek
yalnız şu beş alanı taşır: `command`, `expectedOwner`, `protocol`, `requestId`,
`serviceId`. Command `start`, `close` veya `status` olabilir. Launch config,
executable, callback, görev HTTP payload'ı veya credential alanı kabul edilmez.

Sunucu R160 `alaz-supervisor-control-v1` protokolünü kullanır. İstek compact
ASCII JSON, tek newline ve tam write-EOF ile tamamlanır. En fazla 65.536 byte
kabul edilir; duplicate alan, ek frame, taşma, geçersiz tür/sayı ve deadline
sonucu mutation başlatmaz. Newline tek başına dispatch izni değildir.

Private parent dizini ve socket kimliği korunur. Socket sahibi aynı UID/GID,
izinleri 0600; parent yalnız sahibine açıktır. Var olan dosya veya stale socket
silinmez ya da benimsenmez. Bağlanan peer, gerçek SO_PEERCRED ile denetlenir.
Original PID/startTicks/token, actor ve filesystem kimlikleri her dispatch
öncesinde tekrar kontrol edilir. Token yalnız özel connection kaydındadır;
normal server/CLI teşhislerine owner token alanı eklenmez.

Her mutation request ID effect öncesinde sınırlı kayda alınır. En fazla 64
kayıt tutulur; eski kaydı silerek bir ID'yi yeniden çalıştırılabilir hale getiren
eviction yoktur. Aynı ID/action yalnız özgün sonucu gözler; aynı ID/farklı action
reddedilir. Farklı start ID ikinci child açamaz. Capacity dolması yeni mutation'ı
reddeder. Status bu kayıt bütçesini tüketmez ve child'a status komutu yazmaz.

Client bağlantısının kaybı devam eden bounded lifecycle çağrısını iptal etmez.
Reply yazımı veya son doğrulama bozulduğunda effect'in başlamış olabileceği
bilgisi korunur. Yabancı thread ve aynı thread'den yeniden giriş, başka isteğin
dispatch kaydını sıfırlayamaz. Listener kapatılması yalnız listener FD'sini
kapatır; socket path, özgün owner ve mutation geçmişi tutulur. Yeniden bind,
socket replacement, child termination veya volume cleanup tetiklenmez.

## Üçüncü ve dördüncü adım arasındaki sınır

ServiceChannel'ın gerçek final frame, original Popen exit0 ve stdout/stderr EOF
kontrolü child completion üretir. Bu paket onu dış `CLOSED` sonucuna dönüştürmez.
Native kapanış bilgileri ve üç fiziksel store/caller lease bilgileri doğrulanmış
child raporundan alınabilir; dış sonuç `DRAINING` kalır. `volumeUnmounted`,
`fenceRemovedAfterCleanup` ve `imageLeaseReleased` her zaman false'tur.

Child attempt oluştuğu andan itibaren `ServiceVolumeSupervisor.stop/finish`
bu pakette kapalıdır; temiz child completion da bu guard'ı kaldırmaz. Dördüncü
adım özgün worker-only cgroup kontrolünü, normal unmount/worker exit0 sonucunu,
boş cgroup ve global loop envanterini, fence'in temizlikten sonra kaldırılmasını
ve imaj lease'inin en son bırakılmasını aynı sahip üzerinde bağlayacaktır.

## Kaynak geçmişi

Parent `service_volume_supervisor.py` 3.281 byte ve SHA-256
`30fa40aa1ee1378f5136f27da04879677e457c9c56f983527833d2974bf4f8e8`
olarak ayrı arşivlendi. Yeni dar helper yalnız exact eski dosya/hash çiftini
seçer; current, unknown ve daha eski R160 nesli bu arşive yönlendirilmez.
İki son R160 JSON'u ile ilk R160 JSON'u ve bunlara ait üç ham log byte-exact
korunur. Eski PASS kayıtları yeni kaynakla yeniden etiketlenmez.

## Doğrulama durumu

Son birleşik Linux seçimi 721 testin tamamını geçirdi: 0 SKIP/failure/error,
exit 0 ve 34,652970 saniye. Seçim 47 selector, 25 ürün dosyası ve 42 test/destek
dosyasına bağlıdır; ürün, test ve runner hashleri koşu öncesi/sonrası aynı kaldı.
Ham log 119.698 byte, SHA-256
`c20794b8aedba050312000ceb9d9f795aa3a1809e43e1ca5f91e9d1df2f22e63`.
Primary Windows aynı 721 testte 608 PASS + 113 platform SKIP; failure/error 0,
exit 0 ve 30,781900 saniye. Linux'a özgü socket/SO_PEERCRED/pipe ve POSIX metadata
testleri açık nedenleriyle atlandı; Windows sonucu bu Linux davranışlarının
çalıştığı iddiası değildir. Windows ham log 126.792 byte, SHA-256
`3ff80841b609bceed571fd1e40f4453c53902ff601b8fc6bd2f4bb4e47bbab0b`.
İki platformun ordered 721 test ID digest'i
`641a97535e7eac8fe1b518848d7cae4874d01f7ec53b891ab25af87ca1354df1`.
Kaynak commit'i [`35f4fd6`](https://github.com/esoyuince/AlazHarness/commit/35f4fd6f4d6d42de9322dd55c636cbf25ef61137)
için tam `alaz/local-ci` PASS: **4.481 test, 4.459 PASS,
22 SKIP; failure/error 0**, 308.335 saniye. Tek container exit 0,
OOM/timeout false, cleanup removed. Bu gerçek tam source CI çalışmasıdır;
önceki teslimattan reuse değildir. GitHub status `57385451563` ve
delivery `64501c92-d222-11f1-944d-affa131d6a9f`, checkout/status/source SHA,
suite proof ve ham log aynı hedefe bağlandı.

[Public source CI makbuzu](../evidence/p2-service-supervisor-r163a1/source-ci.json)
özel kabul kaydının byte-exact kopyasıdır; SHA-256
`82a169dd23876ffdfe4160d841bbcecd6a7400805e897d908343ded2579e3078`. Remote metadata digest'i authenticated SSH
gözleminden gelir; raw metadata byte'ları yerelde tekrar hash'lendiği iddia edilmez.
CI ham log SHA-256 `c7d8855cc6e2cb6adf96de8a82ecb08719e3060a29ea5f1a71939fedb80a7cda`.

Bu raporun takip commit'i yalnız status, rapor ve source CI kanıtını değiştirir.
Onun exact-commit tam CI'si, main fast-forward/push, ayrı main verified-success
reuse ve son bütünlük gözlemi henüz bu snapshot'ta NOT RUN; kesin kapanış
`scratch/r163a1-publication/final-publication.json` içinde kaydedilir.
Source/final ürün ve test byte eşliği yayın gate'inde yeniden denetlenir.

Bağımsız kaynak incelemesi PASS; epoch üst sınırının effect öncesinde reddi,
yabancı actor'un özgün attempt'i değiştirmemesi ve sunucuda actor/reentrancy
kontrolünün dispatch kaydı sıfırlanmadan yapılması bulguları kapatıldı.
Reviewer ürün testlerini yürüttüğünü iddia etmez; kendi fresh history koşusu
10/10 PASS'tir. Önceki geliştirme başarısızlıkları özel kayıtlarda korunur;
sunucunun eski fixture ile 42-test koşusu son fixture kabulü sayılmaz.
Son birleşik koşu tüm güncel test ve fixture byte'larını bağlar. Kanıt dizini:
[evidence/p2-service-supervisor-r163a1](../evidence/p2-service-supervisor-r163a1/).

Test kapsamı kaynak/fixture'dır. Gerçek Unix soketleri, SO_PEERCRED, CLI süreçleri
ve child pipe'ları çalışır. Kernel/mount/cgroup/image lease, native runtime,
store sonuçları, source-trust ve /proc startTicks portları açık fixture'lardır.
Yeni kurulum, R156 kurulum değişikliği, native servis/model/sağlayıcı çağrısı yoktur.

## Sonraki somut iş

Bu kaynak paketinin tam CI ve yayın kapanışından sonra planın dördüncü adımı:
child final/exit/EOF'dan özgün volume stop/finish zincirine bağlantı.

Mevcut `ServiceChannel._accept/_reap`, final + özgün Popen exit0 + iki pipe EOF
kanıtını zaten üretir. Aynı child slotu korunarak bu completion, yalnız özgün
worker'ın cgroup'da kaldığı kontrolüne ve mevcut normal `VolumeSupervisor.stop`
sonucuna bağlanmalı. Slotu boşaltmak tek attempt sahipliğini kaybettirir. Generic
`finish()` tek başına STOPPED veya worker exit0 şartı koymadığından servis katmanı
başarılı özgün stop makbuzunu ayrıca istemelidir. Mevcut unmount, boş cgroup,
global loop envanteri, fence ve son image lease sırası yeniden yazılmamalı.

Stop sonrası mevcut `gateway_supervised_service._owner/_check` yoluna dönmek
RUNNING/canlı worker şartıyla çelişir. Kapanış kanıtı aynı özgün owner üzerinde
ayrı tutulmalı. Volume CLOSED olduktan sonra da mevcut Unix `_owned()` yolu
reddedeceğinden kayıp son yanıt ve duplicate-ID gözlemi, özgün actor/socket
kimliğine bağlı saklanan kapanış sonucuyla tasarlanmalıdır. Status veya replay
yeni STOP, cleanup ya da lease bırakma başlatmamalı.

Ardından
özel child loopback'e dar host görev erişimi, effective-config/backup/restart/
capture nitelendirmesi ve yeni tek P2 kurulumunun kabulü gelir. Gerçek model ve
harcama sınırı henüz seçilmedi. **P1 DONE; P2 IN PROGRESS; tam M1 ve production OPEN.**
