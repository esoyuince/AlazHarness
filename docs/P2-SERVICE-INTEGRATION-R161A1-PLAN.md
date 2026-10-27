# P2 / R161A1 — servis profil ve supervisor entegrasyonu

Durum: IN PROGRESS. Birinci adımın servis profil/config kaynak denetimleri
R161A1 ile PASS; ikinci adımın sabit receiver/factory odaklı kaynak testleri
R162A1 ile PASS. Üçüncü adımın supervisor/Unix/CLI kaynak bağlantısı R163A1 ile
PASS; exact-commit CI/yayın status.md'de izlenir. Sıradaki bağlantı volume kapanışıdır.
Kurulu servis veya gerçek model kabulü değildir.
Kaynak raporu: [R161A1 profil ve config](P2-SERVICE-PROFILE-R161A1.md).
İkinci kaynak paketi: [R162A1 receiver/factory](P2-SERVICE-RECEIVER-R162A1.md).
Üçüncü kaynak paketi: [R163A1 supervisor/Unix](P2-SERVICE-SUPERVISOR-R163A1.md).
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

### 4. Final makbuzundan volume kapanışına bağlantı

Native transport/runtime/consumer, üç fiziksel store ve caller/profile lease
sıralı kapanışından sonra final çerçevesi alınır; aynı child'ın gerçek exit0
sonucu ve stdout/stderr EOF kanıtları doğrulanır. Cgroup'da yalnız özgün mount
worker kalmalı ve alt cgroup bulunmamalıdır. Özgün volume stop akışı,
worker'ın bu üyelik kontrolünü yapmasını, normal unmount sonucunu ve worker'ın
exit0 ile sonlanmasını doğrular. Ardından finish, tamamen boş cgroup'u ve
global loop bağlantısının kaldırıldığını doğrular; fence'i temizlikten sonra
kaldırır ve imaj lease'ini en son bırakır. UNKNOWN/BUSY durumları özgün sahibi
ve kanıtı korur.

### 5. Host görev erişimi

Özel child loopback'e host üzerinden erişecek dar transport yolunu seç
ve aynı authenticated native API'ye bağla. Yeni queue veya sonuç store'u
oluşturma. Aynı kurulumda görev, özgün request sorgusu, durum, sonuç,
kullanım ve cancel işlemlerini başlat/kapat akışıyla birlikte doğrula.
`endpointScope: private-service-loopback` tek başına host erişim kanıtı
sayılmasın.

### 6. Yeni kurulum ve gerçek kabul

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
