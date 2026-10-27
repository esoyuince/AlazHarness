# P2 / R161A1 — servis profil ve supervisor entegrasyonu

Durum: IN PROGRESS. Birinci adımın servis profil/config kaynak denetimleri
R161A1 ile PASS; ikinci adımın sabit receiver/factory odaklı kaynak testleri
R162A1 ile PASS. Üçüncü adımın supervisor/Unix/CLI kaynak bağlantısı R163A1 ile,
dördüncü adımın özgün volume stop/finish bağlantısı R164A1 ile PASS.
Exact-commit CI/yayın status.md'de izlenir. Beşinci adımın host görev erişimi
R165A1 ile IN PROGRESS; ürün kaynağı uygulandı, Linux odaklı kapısı 459/459 PASS.
24/24 ürün/test, koşucu ve dondurulmuş Linux/parent kanıtları primary'ye hash
kontrolüyle aktarıldı; Bridge erişimi canlı. Taze `windows-02` aynı 459 seçimde
241 PASS ve 218 SKIP, FAIL/ERROR 0, exit 0 verdi. İlk Linux ve ilk Windows
FAIL kayıtları ayrı korunur. Exact kaynak/closure commit'leri, staging/statik,
source/final CI ve main yayınının güncel durumu [status.md](../status.md) ve
[R165 kaynak raporunda](P2-HOST-TASK-ACCESS-R165A1.md) izlenir.
Kurulu servis veya gerçek model kabulü değildir.
Kaynak raporu: [R161A1 profil ve config](P2-SERVICE-PROFILE-R161A1.md).
İkinci kaynak paketi: [R162A1 receiver/factory](P2-SERVICE-RECEIVER-R162A1.md).
Üçüncü kaynak paketi: [R163A1 supervisor/Unix](P2-SERVICE-SUPERVISOR-R163A1.md).
Dördüncü kaynak paketi: [R164A1 özgün volume kapanışı](P2-SERVICE-CLOSURE-R164A1.md).
Beşinci kaynak çalışması: [R165A1 host görev erişimi](P2-HOST-TASK-ACCESS-R165A1.md).
Önceki paket: [R160A1](P2-SERVICE-CONTROL-R160A1.md).
Güncel durum ve yayın kaydı: [status.md](../status.md).

## Hedef

R159 native servis sahibi ve R160 kontrol bileşenlerini aynı özgün
VolumeSupervisor içinde tek sabit ürün çocuğuna bağlamak. Kullanıcının
başlat/durum/kapat komutlarının gerçekten o çocuğu yönettiğini, kapanışın
özgün native kaynaklardan imaj lease'ine kadar tamamlandığını kanıtlamak.
Bu aşamadan sonra yeni P2 kurulumu ve sınırlı gerçek model görevi gelir.

## Kaynakta doğrulanan iki ön koşul

1. `gateway_native_layout.py` cold/prepared profilde yalnız açık dosya ve
   dizin kümesini kabul eder; `gateway_retained_profile.py` buna runtime,
   cache, auth lock ve active sessions girdilerini ekler. `config.yaml`
   bu kümelerde yoktur. Sabitlenmiş native `hermes_cli/config.py` içindeki
   `get_config_path` ve `load_config_readonly` ise model/plugin ayarlarını
   HERMES_HOME/config.yaml üzerinden okur. Servis için açık, hash'e ve
   dosya kimliğine bağlı ayrı bir profil kabul sözleşmesi gerekir.
2. Projected child kendi network namespace'ine girer ve yalnız kendi
   loopback listener'ını açar. Host CLI'nin aynı 127.0.0.1 adresine istek
   göndermesi bu listener'a erişmez. Projection ayrıca standart akışlar
   dışındaki ambient FD'leri kapatır. Host erişimi, gözlenmiş bir taşıma
   yoluyla ve mevcut HTTP kimlik doğrulama/route sınırları korunarak
   ayrıca tasarlanmalı ve doğrulanmalıdır.

Bu engeller için mevcut finite/readiness profil guard'ları gevşetilmez;
guard sonrasında dosya ekleme veya native config loader'ını değiştiren
gizli fallback kabul edilmez. R160 lifecycle kanalı HTTP görev proxy'si
değildir ve böyle kullanıldığı varsayılmaz.

## Uygulama sırası

### 1. Açık servis profili — kaynak sözleşmesi PASS

27 Ekim 2026: ayrı service layout/expectation, bounded config okuması,
projection ve ayrı handoff, özgün startup/consumer/worker-thread loader
bağları tamamlandı. Son seçimde 306 odaklı test Linux'ta PASS; Windows'ta 298 PASS ve
8 platform SKIP, failure/error 0. Tam CI ve yayın sonucu kaynak raporu ve
status.md üzerinden ayrıca izlenir. Bu sonuç restart/capture, native effective
config veya kurulu supervisor kabulüne genişletilmez.


Mevcut profil seçimine servis için ayrı sürümlü sözleşme ekle. Native
model/plugin yapılandırmasının hangi dosyadan ve hangi hash/device/inode
kimliğiyle okunduğunu admission öncesinde sabitle. Secret dosyalarını veya
değerlerini public manifest'e taşıma. Başlangıç ile ikinci snapshot
arasındaki değişim, symlink, beklenmeyen dosya, yabancı sahiplik ve receipt
uyuşmazlığını reddet. Eski P1 finite/readiness girişleri ve kanıtları kendi
değişmemiş kaynak seçimleriyle çalışmaya devam etsin.

### 2. Sabit projected servis çocuğu — odaklı kaynak testleri PASS

27 Ekim 2026: ayrı receiver/entry ve sabit factory özgün lease/startup/consumer/
service/control zincirine bağlandı. Son async readiness aralığından sonra config
ve kaynak kabulü tekrar denetleniyor. Tek attempt, aynı store/epoch/runner ve
UNKNOWN'da aynı process/loop sahipliği korundu. Son kaynak seçiminde Linux
483 PASS; primary Windows 466 PASS + 17 platform SKIP, failure/error 0 ve exit 0.
Bağımsız config/native ve lifecycle review PASS. Bu kaynak testleri gerçek
kurulum, kernel confinement, native listener, backup/restart veya model kabulü değildir.

Yeni kardeş receiver/factory yalnız doğrulanmış servis profili ve mevcut
native kaynak seçimiyle BorrowedServiceOwner oluştursun. Aynı runner,
authority, epoch ve üç fiziksel store kullanılsın. R160 control driver
yalnız bu somut sahibin lifecycle'ını yönetsin. Tek startup denemesi ve
ownership kaydı korunsun; kaynak kabulü bitmeden READY yayımlanmasın.

### 3. Özgün supervisor ve kontrol sunucusu — odaklı kaynak testleri PASS

27 Ekim 2026: exact özgün ServiceVolumeSupervisor, tek sabit child, original
Popen/ServiceChannel ve private Unix server bağlandı. Gerçek fixture socket,
SO_PEERCRED, Node CLI ve child pipe entegrasyonu dahil Linux 721/721 PASS;
Windows aynı seçimde 608 PASS + 113 platform SKIP, failure/error 0 ve exit 0.
25 ürün ve 42 test/destek dosyası koşu öncesi/sonrası aynı hashlerle bağlandı.
Bağımsız kaynak review PASS. Kaybolan start/close yanıtında status aynı attempt'i
gözler; ikinci child/close veya cleanup oluşmaz. Child completion dışarıda
DRAINING kalır; volume, fence ve image lease kapanışı aşağıdaki dördüncü adımdır.
Bu sonuç gerçek kernel, kurulu supervisor, native servis veya model kabulü değildir.

ServiceVolumeSupervisor'ın özgün begin/attach/start akışı içinde çocuğu
sahiplen; ServiceChannel'ı yalnız bu Popen nesnesine bağla. Supervisor
PID/startTicks/token kimliğine sabitlenmiş özel Unix socket sunucusunu
uygula. R160 CLI protokolünün exact schema, bounded frame, tek mutation,
request ID ve read-only status kurallarını sunucu tarafında da uygula.
Kaybolan start/close yanıtı yeniden child veya cleanup başlatmasın.

### 4. Final makbuzundan volume kapanışına bağlantı — odaklı kaynak testleri PASS

27 Ekim 2026: aynı özgün child/Popen/ServiceChannel'ın final/exit0/iki EOF kanıtı,
worker-only ve alt cgroup içermeyen scope üzerinden mevcut normal stop/finish'e
bağlandı. Exact UNMOUNTED/worker exit0 makbuzu finish'in ayrıca ön koşuludur.
Özgün boş cgroup, loop, fence ve image lease sırası tamamlanınca Unix sunucusu
CLOSED kanıtını yanıt yazmadan önce saklar; mevcut CLI tam kapanışı bildirir.
Status ve aynı request ID cleanup başlatmaz. Child gecikmeli tamamlanırsa yeni
açık close yalnız henüz denenmemiş volume kapanışını başlatabilir; başlamış
veya UNKNOWN/BUSY kalmış stop/finish yeniden denenmez. Tail stream close hatası
dahil belirsizlikte özgün sahip ve kanıt tutulur; sahte CLOSED üretilmez.

Son birleşik seçim Linux'ta 806/806 PASS; primary Windows'ta 626 PASS ve
180 platform SKIP, failure/error 0, exit 0. Aynı 25 ürün, 50 test/destek dosyası,
runner ve sıralı test kimlikleri korunur. Bağımsız kaynak review ile taze
tarihsel 14 test PASS; bu 14 test birleşik seçimin de içindedir. Exact source/final
tam CI ve main yayını ayrıca izlenir. Bu kaynak/fixture sonucu yeni kurulum,
gerçek kernel/native servis veya model kabulü değildir.

Native transport/runtime/consumer, üç fiziksel store ve caller/profile lease
sıralı kapanışından sonra final çerçevesi alınır; aynı child'ın gerçek exit0
sonucu ve stdout/stderr EOF kanıtları doğrulanır. Cgroup'da yalnız özgün mount
worker kalmalı ve alt cgroup bulunmamalıdır. Özgün volume stop akışı,
worker'ın bu üyelik kontrolünü yapmasını, normal unmount sonucunu ve worker'ın
exit0 ile sonlanmasını doğrular. Ardından finish, tamamen boş cgroup'u ve
global loop bağlantısının kaldırıldığını doğrular; fence'i temizlikten sonra
kaldırır ve imaj lease'ini en son bırakır. UNKNOWN/BUSY durumları özgün sahibi
ve kanıtı korur.

### 5. Host görev erişimi — R165A1 odaklı kaynak kabulü PASS

28 Ekim 2026: `994751bed14046e3e0dd14be90912048b996a836` tabanında
dar görev taşıması uygulandı. Seçilen yol, aynı özel Unix endpoint'inden
özgün çocuğun mevcut stdin/stdout FIFO/pipe akışına ayrı `ALAZTASK/1`
çerçeveleri taşımak; HTTP isteğini child'ın kendi sabit loopback API'sinde,
gelen credential ve mevcut admission sınırlarıyla yürütmektir. Standart
akışlar dışındaki FD kapatma ve izolasyon guard'ları korunur. Özgün lifecycle
şeması ve 65.536 byte sınırı ayrı kalır; task gövdeleri, çerçeveleri ve süreleri
kendi bounded sözleşmesine bağlıdır.

Altı izinli yol; capabilities, intent, dispatch, özgün request sorgusu, run
durum/sonuç/kullanımı ve stop'tur. Aynı sequence üzerinde tek bekleyen child
exchange ve dış request ID tekrarında yeni POST üretmeme koşulu uygulanır.
Kayıp dispatch yanıtı mevcut native locator üzerinden yeni salt okunur
exchange ile sorgulanır. Detaylı yol/sınır ve belirsizlik sözleşmesi
[R165A1 tasarım kaydındadır](P2-HOST-TASK-ACCESS-R165A1.md).

CLI'de `ALAZ_TASK_TRANSPORT=supervised-service` açık seçilir; verilmezse
HTTP taşıması kullanılır. `ALAZ_BASE_URL` ve `ALAZ_API_TOKEN`, supervisor
taşımasında da zorunludur; base URL yalnız route origin eşlemesidir. Beş
`ALAZ_SERVICE_*` socket/owner alanı ayrıca sağlanır. Request timeout varsayılanı
5.000 ms, istemci response sınırı 1.048.576 byte; watch/cancel beklemesi
30.000 ms ve polling 100 ms'dir. Kesin alanlar ve aralıklar R165 raporundadır.

Son [Linux makbuzu](../evidence/p2-host-task-access-r165a1/focused-linux-02.json)
ve [log](../evidence/p2-host-task-access-r165a1/focused-linux-02.log): **459/459
PASS**, 0 FAIL/ERROR/SKIP, exit 0, 102,228894 saniye; kaynak/test/destek/koşucu
hashleri sabit. İlk [458 testlik koşu](../evidence/p2-host-task-access-r165a1/focused-linux.json)
451 PASS, 1 FAIL ve 6 ERROR ile FAIL olarak korunur. Eksik beş tarihsel dosya
exact base'ten tamamlandı; eski watch-timeout başlangıç hatası ilgili testler
değişmeden tekrar üretilemedi ve geriye dönük PASS sayılmadı.

Sabit CI image'ında `aiohttp` yoktur. Standart discovery bağımlılığa bağlı
HTTP fixture testlerini açık SKIP olarak kaydeder; hazırlanmış Linux odaklı
koşucu bağımlılığı zorunlu tutar ve 459 testin tamamını çalıştırdı. Source/final
CI sonuçları R165 raporunda izlenir; CI image/kurulum/politika değişikliği yapılmadı.

Primary aktarımı tamamlandı: 24/24 ürün/test dosyası, koşucu ve dondurulmuş
Linux/parent kanıtları hashleriyle doğrulandı. Request 12'nin geçmiş yürütme
sonucu UNKNOWN olarak kaldı; request 14'te dört hedef dosyanın exact önceki
baytları, runtime restart ve boş kuyruk gözlemiyle mevcut durum uzlaştırıldı.
Yeni request 15–18 aktarımı tamamlandı; Bridge erişimi canlı.

İlk [Windows makbuzu](../evidence/p2-host-task-access-r165a1/focused-windows.json)
ve [log](../evidence/p2-host-task-access-r165a1/focused-windows.log) **459 RUN /
240 PASS / 218 SKIP / 1 FAIL / 0 ERROR**, exit 1 ile FAIL olarak korunur.
Başarısız mevcut vaka `test_hybrid_wire.HybridWireTests.test_timeout` oldu.
Dar incelemede aynı özgün testin BASE ve güncel kaynakta altışar normal tekrarı
PASS; iki kontrollü 350 ms gecikme demosunda her iki sürüm aynı
`settlement_unconfirmed`/`state=unknown`/`backendConfirmed=false` sonucunu verdi.
Bu inceleme ilk FAIL'in kesin kök nedenini veya ürün kabulünü kanıtlamaz.
Ürün/test kaynakları, süreler ve assertion'lar değiştirilmedi.

Taze [Windows makbuzu](../evidence/p2-host-task-access-r165a1/focused-windows-02.json)
ve [log](../evidence/p2-host-task-access-r165a1/focused-windows-02.log), request 34
completed/exit 0 ile **459 RUN / 241 PASS / 218 SKIP / 0 FAIL / 0 ERROR** ve
87,580529 saniye kaydetti. Seçilen/yürütülen test kimlikleri, kaynak/test/destek
ve koşucu hashleri son Linux koşusuyla aynı ve değişmedi. Linux'ta 459/459 PASS,
Windows'ta 241 PASS + 218 SKIP ayrımı korunur; tanının tekrarları veya demoları
bu test sayısına eklenmez. İlk iki FAIL geriye dönük başarı sayılmaz.

Source-check/exact manifest, staging/statik kontrol ve source/final CI/yayın
kapılarının güncel sonuçları status.md ve R165 raporunda ayrı izlenir.
Aşağıdaki ilk kabul hedefi korunur; kaynak/fixture başarısı kurulu native servis,
gerçek kernel veya model kabulü değildir.

Özel child loopback'e host üzerinden erişecek dar transport yolunu seç
ve aynı authenticated native API'ye bağla. Yeni queue veya sonuç store'u
oluşturma. Aynı kurulumda görev, özgün request sorgusu, durum, sonuç,
kullanım ve cancel işlemlerini başlat/kapat akışıyla birlikte doğrula.
`endpointScope: private-service-loopback` tek başına host erişim kanıtı
sayılmasın.

### 6. Yeni kurulum ve gerçek kabul

Paketleme açığı: mevcut projected builder retained/finite `d1516731...`
neslinin 756 native dosyasına bağlıdır; P2 servis seçimi `5e3635c2...`
neslinde 760 native dosyadır. Yerel `packages/claw-hermes/*.py` otomatik
seçilse de servis girişleri (`run_supervised_service.py`,
`run_service_projected.py`, `run_service_volume_worker.py`), servis
selection/manifest/host-lock config'leri ve Node 24 host CLI dağıtımı mevcut
candidate'ın sabit listesinde yoktur. Ayrı P2 candidate/install paketinde
bu kaynaklar ve bağımlılıklar kesin envantere bağlanmalı; installer'ın
builder/manifest hash bağı yeni paket için doğrulanmalıdır. Eski finite
paketin tarihsel pin ve kabul kayıtları yeni servis kabulüne çevrilmez.

Güncel kaynak/bağımlılık manifest'iyle yeni tek P2 kurulumu oluştur;
kabul edilmiş R156 kurulumunu değiştirme. Gerçek kernel namespace,
cgroup, mount ve lease yaşam döngüsünü aynı kurulumda doğrula. Başlat,
görev ver, izle, sonucu/kullanımı gör, iptal et ve kapat için ayrı
gözlenebilir sonuçları sakla. Process/control-response kaybı ve kapanış
belirsizliği vakalarında kaynakların erken bırakılmadığını denetle.

Gerçek sağlayıcı kabulünden önce tek model/sağlayıcı, araç kümesi ve
harcama sınırı açıkça seçilmiş olmalı. Henüz böyle bir seçim veya bütçe
yoktur. Scripted model sonucu gerçek model başarısı olarak sunulmaz.

## Kapanış ölçütü

Kaynak ve istemci fixture testlerine ek olarak aynı güncel kuruluma
bağlanan gerçek supervisor/child/volume kanıtı gerekir. Son kaynak
commit'inin tam CI sonucu, kurulum makbuzu ve gerçek çalışma sonuçları
ayrı kaydedilir. Yalnız kaynak yayını P2'yi, tam M1'i veya production
kabulünü kapatmaz.
