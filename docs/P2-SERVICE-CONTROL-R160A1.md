# P2 / R160A1 — Servis kontrolü ve uzun ömürlü sahiplik bileşenleri

Tarih: 27 Ekim 2026. **P2: IN PROGRESS.** Bu kayıt, günlük servis akışını
tamamlamak için eklenen kaynak bileşenlerini, sınanan davranışlarını ve açık
entegrasyon kapılarını kapsar. Bağımsız incelemede bulunan iki sorun düzeltildi; son kaynaklarla
83 odaklı Linux testi geçti. Tam proje CI ve yayın ayrıca doğrulanır.

## Başlangıç ve korunan kabul

Harness tabanı `60853416eed945fcbecb3c1be9da162020da8014` ve çalışma dalı
`alaz/p2-supervised-service-r160a1`'dir. R159'un seçilmiş native kaynağı
`5e3635c2cdfc2161fd20c089618bd7f2a7c12f2d` ve ona bağlı **760 dosyalık servis
seçimi** değişmemiştir. Bu paket yeni bir upstream sürümü seçmez.

**P1 DONE** kararı, R156 finite ve R157 readiness kayıtlarının aynı değişmemiş
R156 kurulumuna bağlanmasına dayanır. R160 kaynak testleri bu tarihsel kabulü
yeniden üretmez veya yeni kuruluma taşımaz. P3–P5, tam D3B, M1 ve production
kabulü açıktır. R160'ta yeni P2 kurulumu kabul edilmemiş, gerçek sağlayıcı veya
model çağrısı yapılmamıştır.

Önceki kapsam ve devam adresleri:
[R159 planı](P2-BORROWED-SERVICE-R159A1-PLAN.md),
[ürün yol haritası](PRODUCT-ROADMAP.md) ve [güncel durum](../status.md).

## Bu kaynak paketinde eklenenler

| Bileşen | Sorumluluğu | Kabul sınırı |
|---|---|---|
| Çocuk süreç kontrolü | Özgün `BorrowedServiceOwner` üzerinde ready, status, drain ve close çerçeveleri | Native yaşam döngüsü arayüzleri fixture ile sınanır; kurulu servis başlangıcı yoktur. |
| Ebeveyn pipe gözlemcisi | Özgün süreç nesnesinden sınırlı giriş/çıktı, yanıt ve final takibi | Süreci başlatma, volume kapatma veya image lease bırakma yetkisi sağlamaz. |
| Yerel CLI ve servis istemcisi | Açıkça seçilmiş özel Unix kontrol kanalına start, close ve service-status | Uyumlu gerçek supervisor sunucusu henüz bağlanmamıştır. |
| Uzun ömürlü volume worker | Özgün image lease/fence sahibinin servis için seçilen ayrı mount worker'ı | Gateway, profil, native servis veya model başlatmaz. |

### Çocuk süreç: tek özgün sahip ve sıralı kontrol

[gateway_service_control.py](../packages/claw-hermes/gateway_service_control.py),
R159'daki özgün `BorrowedServiceOwner` nesnesini aynı süreç, thread ve event
loop üzerinde tutar. Yeni veritabanı, görev kuyruğu veya sonuç deposu oluşturmaz.
İç protokol `alaz-service-control-v1`'dir; hazır olma kaydı ve sonraki yanıtlar
aynı servis kimliğine ve native `pid/epoch/instanceId` üçlüsüne bağlanır.

Başlatma tek denemedir. Kontrol komutları servis kimliğine bağlı sıra numarası
ve bundan türetilen istek kimliği taşır. Aynı son komutun yeniden gözlenmesi,
saklanan görev/yanıtı kullanır. Değiştirilmiş eski komut, atlanmış sıra veya
başka servis kimliği yeni işlem açmaz. Bilinen, etki başlamadan verilmiş bir
busy sonucu sonrasında yeni bir close komutu açıkça gönderilebilir; belirsiz
etki kendiliğinden tekrar denenmez.

Gözlemcinin iptali, sahibi hâlâ tutulan native işlemi iptal etmez. Kontrol
kanalı kaybında admission kapatılmaya çalışılır ve özgün sahip, event loop ile
devam eden görevler tutulur. Kanal kaybı normal kapanış olarak işaretlenmez.

`final` çerçevesi için transport, runtime, API oturumları, consumer, executor,
üç fiziksel store ve profil lease kapanışının tamamlanmış olması gerekir.
Çocuk süreç kaydı image lease'i bırakmaz; `imageLeaseReleasedHere` açıkça
`false` kalır. Çerçeve ayrıca özgün ebeveynin süreç çıkışı ve volume kontrollerine
bağlanmalıdır.

### Ebeveyn: giriş, yanıt, EOF ve süreç çıkışı ayrı kanıtlar

[supervised_service_channel.py](../packages/claw-hermes/supervised_service_channel.py)
ebeveynin zaten sahip olduğu süreç nesnesini kullanır. Tek seferlik bootstrap
ve aynı anda en fazla bir kontrol komutu tutar. İstek kaydı ilk byte
gönderilmeden önce saklanır. Süre aşımından sonraki gözlem, kalan giriş
byte'larını tamamlamaz ve komutu yeniden göndermez.

Bootstrap 128 KiB, tek protokol çerçevesi 64 KiB ve bir bekleme çağrısı en fazla
60 saniye ile sınırlıdır. Parçalı çerçeve korunur; stderr'in tamamı sayılır ve
hash'lenir, bellekte yalnız sınırlı son bölümü tutulur. Başka süreç/generation,
beklenmeyen sıra, tamamlanmamış girişe erken yanıt, final sonrası ek veri veya
çıkışla uyuşmayan final başarılı kapanış üretmez.

Çocuğun CLOSED kaydı, pipe EOF ve özgün sürecin terminal çıkışı ayrı gözlenir.
Bu bileşenin çıktısında `volumeMayClose` her durumda `false` kalır. Gerçek
supervisor ayrıca mount worker'ı ve cgroup kullanıcılarını doğrulayıp özgün
stop/finish sırasını yürütmelidir.

Bağımsız incelemede, süreç çıkışı bilindiği halde pipe EOF henüz tamamlanmadığında
eski READY görünümünün korunabildiği bir pencere bulundu. İlk birleşik test koşusu
bu durumu kapsamıyordu. Düzeltme, exit gözlendiğinde henüz doğrulanmış final yoksa
veya exit sıfırdan farklıysa durumu hemen UNKNOWN yapar; yeni komut
kabulünü durdururken çıktıların boşalmasına izin verir. Üç yeni deterministik
regresyon testi eski kodda başarısız, son kodda başarılıdır. Exit0 sonrasında
gecikmiş geçerli final ve iki EOF tamamlanırsa COMPLETED hâlâ mümkündür.

### CLI: açık bağlantı ve özgün supervisor kimliği

[service-control.mjs](../packages/claw-hermes/service-control.mjs) ve
[alaz_local.mjs](../scripts/alaz_local.mjs), `alaz-supervisor-control-v1`
sözleşmesini kullanan ayrı bir istemci yolu ekler. Görev/sonuç/iptal için mevcut
HTTP istemcisi korunur. Yeni lifecycle komutları native görev HTTP adresini
supervisor kontrol adresi olarak kullanmaz.

Servis bağlantısı Unix socket yolu, servis kimliği ve özgün supervisor'ın
`pid/startTicks/token` üçlüsüyle açıkça seçilir. Her start, close ve status
isteği bu üçlüyü `expectedOwner` önkoşulu olarak taşır. Uyumlu sunucu bütün
alanları kendi özgün sahibiyle **işlemi yürütmeden önce** karşılaştırmalı;
uyuşmazlıkta hiçbir lifecycle etkisi veya status dispatch başlatmamalıdır.
Yanıtta kimlik doğrulaması tek başına bu önkoşulun yerine geçmez. Token yalnız
özel kontrol isteğinde taşınır ve CLI tanı çıktısına yazılmaz.

`start` ve `close`, bu bağlantı
yapılandırıldığında açık bir istek kimliği gerektirir. `service-status` salt
okunur gözlem içindir. Servis bağlantısı verilmediyse önceki `start/close`
unsupported davranışı korunur; süreç taraması veya mevcut kişisel servisi
devralma yapılmaz.

İstemci tek istek gönderir. Süre aşımı, kesinti ve kayıp yanıt sonrasında yeni
başlatma/kapatma göndermez. Kullanıcı özgün kimlikle `service-status` çağırabilir.
Yanıt, özel socket denetimleriyle birlikte bütün şema/kimlik alanlarından,
tek satır ve EOF koşulundan geçer. Tekrarlı JSON alanları, başka sahip,
fazladan çerçeve veya eksik cevap reddedilir.

Sahiplik önkoşulu fixture testinde PID, başlangıç sayacı ve token ayrı ayrı
eskimiş start/close/status istekleriyle sınanır: sunucu fixture'ında lifecycle
etkisi sıfır kalır. Başka sahibin yanıtı istemcide özgün sahip için kabul
makbuzu sayılmaz; otomatik tekrar yetkisi doğmaz. Bu test, henüz bulunmayan
canlı supervisor sunucusunun uygulama kabulü değildir.

`start` için READY, `close` için CLOSED gerekir. Başka bir geçerli durumun
gözlenmesi istenen işlemi tamamlamış sayılmaz ve unresolved sonucu üretir.
CLOSED raporu için child, store, profil, mount, fence ve image kapanış
alanlarının tamamı doğrulanır. İstemci bunları özgün sahibin raporu olarak
sunar; `kernelVerified:false` ve `hostHttpReachabilityVerified:false` açıkça
korunur. Supervisor token'ı tanı çıktısına yazılmaz.

### Volume worker: uzun idle, aynı kapanış sırası

[service_volume_supervisor.py](../packages/claw-hermes/service_volume_supervisor.py)
ve [run_service_volume_worker.py](../scripts/run_service_volume_worker.py),
özgün volume sahibine açıkça seçilen version 2 worker ekler. Mevcut
finite/readiness worker'ı ve onun 120 saniyelik idle sınırı değişmez.

Yeni worker'ın bootstrap girişi 15 saniye ile sınırlıdır. Servis idle durumunda
ilk byte beklemesine süre sınırı koyulmaz; ilk byte geldiğinde 15 saniyelik
çerçeve süresi başlar. Byte sınırı korunur. Özgün parent-death sinyali ve
ebeveyn kimliği kontrolü uzun idle başlamadan kurulur.

STOP yalnız özgün token ile kabul edilir. Başka cgroup kullanıcısı veya alt
grup varsa worker BUSY döner; normal unmount reddedilirse yine BUSY kalır.
Zorla unmount veya otomatik lease bırakma eklenmemiştir. Miras alınan
stop/finish yolu süreç, cgroup, global loop bağlantısı, fence ve lease
sırasını korur. Bu worker için yapılan bağımsız kaynak incelemesinde somut yeni
güvensiz cleanup veya idle yarışı bulunmamıştır; bu inceleme gerçek kernel
kurulum kabulü değildir.

## Doğrulama ve kanıt sınırı

Nihai odaklı koşunun komutu, test sayısı, exit kodu, kaynak SHA-256'ları ve
kapsamı [focused-linux.json](../evidence/p2-service-control-r160a1/focused-linux.json)
içindedir. Ham çıktı:
[focused-linux.log](../evidence/p2-service-control-r160a1/focused-linux.log).

**Nihai odaklı kaynak kabulü: PASS — 83/83 test, exit 0; 8.668 saniye.**
26 child, 21 parent, 24 CLI ve 12 volume testi aynı koşuda geçti. İlk 79 testlik
koşu `initial-focused-linux.json/log` olarak korunur. Son inceleme iki sorunu
kapattı: gözlenmiş child exit sonrasında eski READY durumu ve mutation
öncesinde sunucuya expected-owner koşulu taşınmaması. Son makbuz 11 kaynak/test
dosyasının SHA-256 değerlerini içerir; kurulu runtime kabulü iddiası yoktur.

| Doğrulama | Kapsam |
|---|---|
| Çocuk kontrol sözleşmeleri | Gerçek event loop ve pipe davranışları; native yaşam döngüsü fixture sınırında |
| Ebeveyn kanal testleri | Gerçek sahip olunan alt süreçler, parçalı çıktı, timeout, EOF ve terminal çıkış |
| CLI testleri | Geçici gerçek Unix socket ve CLI süreçleri; supervisor sunucusu fixture |
| Volume worker testleri | Idle/çerçeve için gerçek pipe; root, mount ve cgroup sınırları fixture |
| Windows odaklı koşu | 83 test keşfedildi; 36 PASS, 47 POSIX/Unix koşulu nedeniyle SKIP, exit0; aynı 11 dosyanın hashleri doğrulandı. |
| Yeni kurulu native servis | NOT RUN |
| Gerçek model/sağlayıcı | NOT RUN; çağrı sayısı sıfır |
| R160 tam proje CI ve yayın | Bu raporda kabul/yayın iddiası yok; durum ayrıca `status.md` ile izlenir. |

[Windows makbuzu](../evidence/p2-service-control-r160a1/focused-windows.json) ve
[ham log](../evidence/p2-service-control-r160a1/focused-windows.log) platform
atlamalarını ayrı tutar.

İlk kısıtlı çalışma ortamında socket fixture'ları `listen EPERM` ile
başlatılamamıştır. Sonraki izinli yerel test koşuları bu ortam engelinden ayrı
kaydedilir. Fixture başarısı, yeni native kurulumun veya modelin çalıştığı
anlamına gelmez. Değişmemiş R159 host suite'i bu scratch ortamında ayrıca
denendi; ilk koşu durduruldu (exit130), sınırlı tanı koşusu ilk dört testten
sonra event-loop teardown sırasında süre aşımına uğradı (exit124). Bu denemeler
PASS sayılmaz veya R160 regresyonu olduğu ileri sürülmez. Tam kaynak için
asıl proje CI sonucu ayrıca gözlenir.

## Açık entegrasyon kapıları

1. **Sabit projected service factory yok.** Özgün launch/confinement zincirinden
   servis sahibi, seçilmiş config ve kontrol sürücüsünü kuran sabit ürün hedefi
   henüz bağlanmamıştır.
2. **Canlı supervisor Unix sunucusu yok.** CLI'nin bağlanacağı, özgün sahibi
   tutan ve gerçek start/status/close işlemlerini yürüten sunucu açık iştir.
3. **Özgün volume-supervisor final bağlantısı yok.** Native final, terminal
   child çıkışı ve volume stop/finish sonucunu tek özgün sahipte birleştiren
   ürün bağlantısı tamamlanmamıştır. Pipe gözlemcisi volume kapatma izni vermez.
4. **Özel loopback için HTTP erişim bağlantısı yok.** Child'ın network namespace'i
   içindeki `127.0.0.1` adresi host'tan erişilebilir sayılmaz. Bu adresin READY
   kaydında bulunması günlük görev HTTP akışını kabul ettirmez.
5. **Açık servis profil kabul sözleşmesi gerekiyor.** Mevcut retained/finite
   profil düzeni `config.yaml` dosyasını kabul etmez. Servis yapılandırmasını
   bu profile eklemek mevcut denetimleri geçirmez; ayrı ve sınırlı bir servis
   profil sözleşmesi, kaynak/config kimliği ve başlangıç denetimleri gerekir.

Bu kapılar kapanmadan günlük kurulu `start → task → watch → result/usage →
cancel → close` akışı ve P2 bütünü tamamlandı olarak işaretlenemez.

## Kesin sonraki sıra

1. Ayrı servis profil ve config kabul sözleşmesini belirle. İzinli dosyaları,
   kaynak/config hash'lerini ve gerekli secret-source bağımlılıklarını açıkça
   bağla; mevcut finite/retained kabulünü koru.
2. Bu sözleşmeyle sabit projected service hedefini kur. Özgün namespace,
   cgroup, kimlik düşürme ve dosya erişim denetimlerinden sonra aynı native
   sahibi ve kontrol sürücüsünü başlat.
3. Özgün supervisor'ı çocuk kanalına bağla. Native final, child terminali,
   mount worker/cgroup/loop kontrolleri ve son image lease bırakmasını tek
   kapanış kaydında birleştir; belirsiz etkide özgün sahibi tut.
4. Özel Unix kontrol sunucusunu ve açık host görev erişimi yolunu tamamla.
   Kaybolan yanıtın özgün kimlikle gözlemini, idle sürekliliğini ve close
   sırasında mevcut işin gözlenebilmesini kabul et.
5. Son harness, seçilmiş native kaynak, Node ve gerekli Python bağımlılıklarıyla
   ayrı P2 adayı paketle. Taze tek kurulumda günlük akışı ve özgün kapanış
   sırasını fixture ile kabul et; kaynak testlerini kurulum kanıtıyla karıştırma.
6. Tek route/model, izinli küçük dosya görevi ve çağrı/token/mikro-USD tavanları
   açıkça seçildikten sonra bir sınırlı gerçek model görevi yap. P2'nin kapanışı
   için bu kayıt ile aynı kurulumdaki günlük akış kabulünü birlikte değerlendir.

Bu belge R160 kaynak bileşenlerinin kapsamını kaydeder. Kesin commit, push,
CI ve fast-forward sonucu aktif çalışma ağacındaki
`scratch/r160a1-publication/final-publication.json` kaydından doğrulanır.
Git yayını kurulu ürüne dağıtım veya P2 kapanışı değildir.
Sonraki uygulama planı: [R161A1](P2-SERVICE-INTEGRATION-R161A1-PLAN.md).
