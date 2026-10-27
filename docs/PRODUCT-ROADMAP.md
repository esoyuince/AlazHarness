# AlazHarness ürün yol haritası

Karar: 25 Ekim 2026. Kullanıcı, mevcut durum değerlendirmesinden sonra bu yolu
benimsedi. Güncel iş ve kanıtların sahibi `../status.md`; temel ürün kabul
koşulları `MVP-v0.1.md`. Bu belge önceki deneyleri veya sonuçlarını değiştirmez.

## İlk sürümün kapsamı

Tek ajan, tek desteklenen Linux ortamı, bir yerel kontrol yüzeyi, tek seçilmiş
model/sağlayıcı ve açıkça sınırlı araç kümesi. Hermes tek yürütücü ve kalıcı iş
sahibi; OpenClaw'dan doğrulanmış kontrol bileşenleri kullanılır. İlk M1 sürümü için
yeni web arayüzü, çok kullanıcılı servis veya M2 otonom gündem gerekli değildir.

Kodun varlığı, ayrı bileşen kabulü ve tek kurulu ürünün kabulü ayrı kaydedilir.
Eski kaynakla alınan başarı son kaynak için devralınmaz. Test/commit sayısı ürün
ilerlemesinin ölçüsü değildir; her paket aşağıdaki gözlenebilir çıkışı kapatır.

## Beş teslimat paketi

| Paket | Teslimat | Tamamlanma ölçütü | Güncel durum |
|---|---|---|---|
| P1 | Güncel kurulum, sabit supervisor/launcher ve gerçek native iş bağlantısı | Aynı kurulumun sabit readiness ve finite girişlerinden normal/hata, replay/yeni iş ve sıralı kapanış; gerekli kimlik, namespace, mount, FD ve kaynak kontrolleri | DONE; R156 finite + R157 readiness-only aynı değişmemiş kurulumda, ayrı taze imaj/supervisor yaşam döngülerinde PASS. Gerçek model/servis kabulü P2 kapsamındadır. |
| P2 | Günlük yerel kullanım ve tek gerçek model | Başlat, görev ver, izle, sonuç/kullanımı gör, iptal et, kapat; seçilmiş araçla gerçek görev ve sınırlandırılmış model bütçesi | IN PROGRESS; R164A2 yayını kapandı. R165A1 kaynağı ve 24/24 ürün/test aktarımı hazır; Linux 459/459 PASS, Windows 459 seçimde 241 PASS + 218 SKIP, FAIL/ERROR 0. İlk iki FAIL korunuyor. Staging/statik, source/final CI ve yayın NOT RUN. P2 candidate/install, kurulu profil/restart ve gerçek model kabulü açık. |
| P3 | Kalıcılık ve M1 hafıza/beceri yeniden kullanımı | Yeni oturumda geçmiş/kimlik korunur; önceki bilgi veya beceri gerçekten bulunup kullanılır | OPEN; retained ve Dream alt bileşen kanıtları mevcut. |
| P4 | Arıza ve işletim | Süreç/broker/yanıt kaybı ve süre aşımında açık durum; güvenli operatör uzlaştırması; kurulum, yedek/geri yükleme, yükseltme/geri dönüş | OPEN; bazı davranışlar ayrı deneylerde karakterize edildi. |
| P5 | Tek v0.1 sürüm adayı ve küçük pilot | M1-01..M1-07 aynı kaynak/kurulumda kapanır; temiz ortam kurulumu ve gerçek görev pilotu | OPEN; tam M1 ve prod kabulü yok. |

P1 olumlu kernel kabulünden önce P2 gerçek model deneyi ürün kabulü sayılmaz.
Kaynak/entegrasyon hazırlığı paralel yapılabilir; yetki veya kurulum yokluğu gizli
fallback, zayıflatılmış guard ya da önceki reddedilmiş işlemi tekrarlama gerekçesi
değildir. Gerçek sağlayıcı/maliyet deneyi seçilmiş model ve açık bütçe gerektirir.

## P1'in somut bağlantıları

1. Son harness ve native d1516731308de8e87130dc68124e69aad35d6911 kaynakları,
   mevcut sabit bağımlılıklar ve hash manifestleriyle kurulum adayı.
2. Var olan VolumeSupervisor içinde sabit ürün çocuğunun sahipliğini ve doğru
   cgroup/mount namespace katılımını sağlayan dar bağlantı.
3. Değişmemiş canlı guard'lar sonrası sabit retained receiver ve orijinal
   NativeStoreStartup; aynı sahibin API/authority/finite worker/kalıcılık akışı.
4. Gerçek retained profil beklentisi aynı supervised ext4 dosya sisteminde,
   orijinal normal close sonrasında ve lease hâlâ tutulurken üretilir. Eski QA
   profili/JSON'u taşınarak device/inode bilgisi yeniden yazılmaz.
5. Aynı kurulu runtime'ın readiness ve finite kardeş girişleri, ayrı taze yaşam
   döngülerinde kabul edilir; mevcut geçerli finite kanıtı korunur. Hata veya
   belirsizlikte zorla close, lease bırakma, mount kaldırma, reset ya da otomatik
   retry yok.

R152 yalnız sıradan kullanıcı altında gerçek Landlock + retained yaşam döngüsünü
kabul etti; bu eski sonuç tek başına ürün supervisor kabulü değildi. R155'te aynı
özgün supervisor ve ext4 imajında gerçek seed, sabit ürün çocuğu üzerinden
projected readiness ve normal kapanış ayrıca kabul edildi. L145 hedefi hâlâ
yalnız readiness yapar. R156 ayrı sabit finite kardeş giriş üzerinden gerçek
native API/authority/worker/persistence/kapanışını yeni kurulumda kabul etti;
R157 aynı güncel kurulumu değiştirmeden ayrı readiness-only kabulünü tamamladı.
İki gerçek native kabulün ortak kaynak bağı P1'i kapatır; P2–P5 açık kalır.

## M2 sonraki aşama

Kendi hedefini seçme/sürdürme/bırakma ve bağımsız görevlerde ölçülen öğrenme
kazanımı M1 sonrasıdır. Dream aday çıkarma, inceleme ve eşleştirilmiş değerlendirme
altyapısı vardır; programlı test yanıtları öğrenme kanıtı sayılmaz. M1-04 için
hafıza/beceri yeniden kullanımı gerekir; otomatik otonomiye geçiş zorunlu değildir.

## Planlama ve raporlama

Sohbetteki 3-5 hafta gözetimli alfa ve 6-10 hafta kontrollü prod aralıkları,
bir ana geliştiricinin odaklanması, tek platform/model/dar araç kapsamı, hazır
yetkili test ortamı ve büyük yeni mimari engel çıkmaması varsayımlı tahminlerdir.
Teslim tarihi veya ölçülmüş velocity değildir. P1 sonucu sonrası yeniden ölçülür.

Her paket raporu kullanıcıya açılan gerçek akışı, son kaynak/kurulum kimliğini,
çalışan kabulü ve açık kalanları bildirir. Mock/native/gerçek-model ve
PASS/FAIL/NOT RUN/BLOCKED durumları ayrı kalır. Exact-commit CI sonrasında normal
fast-forward yayın yapılabilir; Git yayını kurulu servise dağıtım değildir.

Aşağıdaki teslimat bölümleri kendi tarihlerindeki kapsamı korur. Güncel paket
kararı üstteki tabloda ve son R165 çalışma kaydında yer alır.

## P1 / R153A1 teslimatı

Sabit supervisor çocuğu, sınırlı pipe aktarımı ve güncel kaynak paketi tamamlandı.
Paket, `e03f7fd4e47fea6a58b749564ab350aeb4237a26` kaynak commit'inden 834 dosya ile üretildi;
756 native dosya d151 kaynağıyla hash düzeyinde eşleşir. 1.162 bağımlılık hash'i
referanstır; kurulum yapılmadı. Bu alt teslimat P1'i tamamlamaz: aynı kurulumda
olumlu projected readiness, gerçek retained seed ve ardından finite iş kabulü
sıradaki adımdır. Ayrıntı ve kanıtlar: [R153A1](M1-PRODUCT-PATH-R153A1.md).

## P1 / R154A1 teslimatı

Güncel R153 kaynak adayı, mevcut özel Linux laboratuvarında `/opt/alaz-r154a1`
altına kuruldu. 834 paket dosyası ve 1.162 bağımlılık dosyası, sabit Python
kimliği ve güvenilir dizin izinleriyle doğrulandı. Kurulumdan sonra ayrı bir
sıradan kullanıcı süreci bütün kurulu dosyaları ve kurulum kaydını yeniden
doğruladı; iki işlem de exit 0 ile tamamlandı.

P1'in güncel kaynak/bağımlılık kurulumu alt adımı tamamlandı. Aynı supervised
ext4 imajında orijinal native yaşam döngüsüyle gerçek başlangıç kaydı üretmek,
supervisor üzerinden olumlu projected readiness ve sıralı kapanışı kabul etmek,
ardından normal/hata, replay/yeni iş ve finite görev akışını bağlamak hâlâ açık.
Bu teslimatta native uygulama veya model çalıştırılmadı; P1, M1 ve prod kabulü
henüz tamamlanmadı. Ayrıntı ve kanıtlar: [R154A1](M1-INSTALL-READINESS-R154A1.md).

## P1 / R155A1 teslimatı

Aynı kurulumdaki özgün native yaşam döngüsü, ordinary007 ile sıradan kullanıcı
altında doğrulandı. Ardından yeni 64 MiB ext4 imajında, özgün VolumeSupervisor
içinde gerçek başlangıç profili üretildi (epoch 1). Sabit ürün çocuğu aynı profil
ve veritabanı kimlikleriyle projected readiness'i tamamladı (epoch 2); her iki
aşamada altı özgün başlangıç kontrolü geçti. Başka profilden state kopyalanmadı.

Özgün stop/finish sırası başarıyla kapandı: bütün sahip olunan çocuk süreçler
sonlandı, loop bağlantısı kaldırıldı, volume fence temizlikten sonra silindi ve
imaj lease'i en son bırakıldı. Host mount namespace'i ve mount tablosu değişmedi.
Saklanan imajın ve çalışma dosyalarının tümünün silindiği iddia edilmez.

Windows'taki seçilmiş 120 testin 113'ü geçti, yedisi platform gereği atlandı;
bu sayım gerçek native kabul ve son commit CI sonucundan ayrıdır. Bu teslimatta
gerçek görev/model çağrısı sıfırdır; metadata socket fixture gerçek broker
alışverişi, servis başlangıcı veya API admission kabulü değildir.

P1'in aynı imajda seed/readiness/sıralı kapanış alt adımı tamamlandı. Sıradaki
iş, aynı kabul edilmiş girişten finite native görevi bağlamak; normal/hata,
replay/yeni iş ve sıralı kapanışı tek kurulumda kabul etmek. P1 bütünü, P2-P5,
M1 ve prod açık. Rapor ve kanıtlar: [R155A1](M1-SEED-READINESS-R155A1.md).

## P1 / R156A1 kaynak hazırlığı

Sabit finite kardeş giriş ve ayrı sonuç sözleşmesi eklendi. Mevcut readiness ile
aynı supervisor'ın tek çocuk deneme kaydı kullanılır. İlk kabul, yeni aynı imajda
seed epoch 1 ardından tek finite child epoch 2 üzerinden normal görev, birebir
tekrar, yeni görev ve kontrollü uygulama hatası ile özgün drain/detach/close
sırasını hedefler. Model factory/hesaplama/close açık scripted fixture'dır;
gerçek sağlayıcı çağrısı, servis veya restart replay kabulü değildir.

Windows'ta 351 odaklı testin 319'u geçti, 32'si platform gereği atlandı. Bu sonuç
tek başına yeni kurulum/kernel kabulü sayılmaz. Daha sonra gerçekleşen yeni
kurulum ve native finite kabulü aşağıdaki R156 teslimatında ve
[R156A1 raporunda](M1-FINITE-PRODUCT-R156A1.md) kayıtlıdır; P1 bütünü ve ürün
kabulü açıktır.

## P1 / R156A1 native finite teslimatı

Yeni runtime `e641a5000810efb2a453ae847f689b422f7d41a7` kaynağından
`/opt/alaz-r156a1` altına kuruldu. 838 kaynak ve 1.162 bağımlılık dosyası
geri okundu; gerçek kurulum kaydına bağlı ordinary001 native açılış/kapanış
proof'u geçti. image001, yeni ext4 imajında özgün supervisor ile seed epoch 1
ve tek finite child epoch 2 üzerinden normal görev, birebir tekrar, yeni görev
ve kontrollü native terminal hata vakalarını kabul etti. Hesaplama sayıları
1/1/2/3: tekrar ikinci hesaplama üretmedi. Özgün consumer/owner/üç fiziksel
bağlantı/profile lease ve volume stop/finish sırası tamamlandı.

Model factory/hesaplama/close scripted fixture'dır; gerçek provider/model çağrısı
sıfır. Gerçek broker alışverişi, servis/genel runtime admission, restart replay
ve CLI/unattended policy kabul edilmedi. Child stderr'deki
`agent.secret_sources.command` kayıt hatası bu koşuda terminal başarıyı
engellemedi; gerçek model/secret-source paketlemesi için açık bir P2 takip
maddesidir. SQLite DELETE-mode uyarıları ve beklenen kontrollü hata traceback'i
ham çıktıda korunur; stderr'in temiz olduğu iddia edilmez.

**P1'in güncel kurulumda finite native alt kapısı tamamlandı. P1 bütünü hâlâ
IN PROGRESS.** En küçük kalan kapı, aynı 838 dosyalık kurulumun ayrı taze
imaj/lifecycle üzerinde sabit readiness-only girişinden görev başlatmadan
açılış ve normal kapanışını kabul etmektir. R155'in önceki kurulum başarısı
buraya taşınmaz; tamamlanan R156 supervisor'a ikinci çocuk eklenmez. Bu kapı
için runtime kodunu değiştirmek veya geçen finite işi tekrarlamak gerekmez.

Sonrasında P2 için günlük yerel başlat/görev/izle/sonuç/iptal/kapat akışı,
seçilmiş sağlayıcının gerekli modülleri ve açık model bütçesi gelir. P2 kaynak
hazırlığı paralel yapılabilir; ücretli model kabulü P1 ve model/bütçe seçiminden
sonradır. Rapor/kanıt: [R156A1](M1-FINITE-PRODUCT-R156A1.md). P2–P5, tam D3B,
M1 ve prod kabulü açık kalır.

## P1 / R157A1 güncel kurulumda readiness ve P1 kapanışı

26 Ekim 2026'da aynı `/opt/alaz-r156a1` kurulumu, kaynak veya kurulum kaydı
değiştirilmeden yeni 64 MiB ext4 imajında kabul edildi. Özgün task-free seed
epoch 1, tek readiness çocuğu epoch 2 ve altı başlangıç kontrolü geçti.
Özgün stop/finish sırası tamamlandı; sahip olunan çocuklar terminal, volume
CLOSED, loop bağlantısı kaldırılmış, fence temizlikten sonra kaldırılmış ve
imaj lease'i en son bırakılmıştır. Host mount namespace/tablosu değişmedi.

R156 finite ve R157 readiness kayıtlarının kurulum nesneleri alan alan eşittir:
harness `e641a5000810efb2a453ae847f689b422f7d41a7`, native `d1516731…`,
838 kaynak / 1.162 bağımlılık, aynı receipt ve kök device/inode. Paketlenmiş 81
harness Git blob'u da mevcut kaynakla birebir eşleşir. Ayrı imajlar, farklı
supervisor tokenları ve özgün kapanış kayıtlarıyla bağlanır; R156 işi tekrarlanmadı.

**P1 — DONE.** Normal/replay/yeni/hata native akışı ve görev açmadan readiness,
aynı kurulumun sabit kardeş girişlerinde kabul edildi. Model factory/hesaplama/
close R156'da scripted fixture'dır; iki kabulde gerçek sağlayıcı çağrısı sıfırdır.
Bu karar tam D3B, M1 veya production kabulü değildir.

Sonraki paket P2: mevcut HostGateClient/HermesRunsClient, native API ve bütçe
bileşenleri üzerinden günlük yerel kullanım. Önce gerçek CLI/listener/stop
bağlantıları ve seçilen modelin paketleme ihtiyacı doğrulanır; sonra
başlat/görev/izle/sonuç/kullanım/iptal/kapat akışı uygulanır. Gerçek sağlayıcı
kabulünden önce model ve harcama sınırı açık olmalıdır. P3 kalıcılık/hafıza,
P4 arıza/işletim ve P5 tek sürüm adayı/pilot açık kalır.

Rapor: [R157A1](M1-INSTALLED-READINESS-R157A1.md).
Ortak kabul: [P1 kaydı](../evidence/m1-installed-readiness-r157a1/p1-acceptance.json).
Sonraki iş: [P2 / R158 başlangıç paketi](P2-LOCAL-PRODUCT-R158A1-PLAN.md).

## P2 / R158A1 yerel kontrol ve kayıp yanıt sorgusu

Mevcut HostGateClient/HermesRunsClient üstünde görev, özgün istek sorgusu,
durum, izleme, sonuç, kullanım ve tek stop ardından gözlem komutları eklendi.
Kayıp dispatch yanıtı, aynı request ID'nin salt okunur native run locator'ıyla
sorgulanır; consumed istek tekrar açılmaz. Yeni kuyruk veya sonuç deposu yoktur.

Kaynak/HTTP fixture kabulü tamamlanır; günlük servis ve gerçek model kabulü
bundan ayrıdır. P1 borrowed adapter'ın listener'ı açıkça reddettiği, host-gate
kaynağının iki native dosyada eski sürüme bağlı kaldığı ve command secret-source
dosyasının ürün manifest'inde bulunmadığı doğrulandı. Kilitler gevşetilmedi.

Sıradaki somut iş [R159 borrowed servis bağlantısı](P2-BORROWED-SERVICE-R159A1-PLAN.md):
aynı native owner'a açık transport sahipliği, draining sırasında kontrol ve
sıralı close, ardından yeni tek P2 kurulumu ve sınırlı gerçek model görevi.
Rapor: [R158](P2-LOCAL-CONTROL-R158A1.md). P1 DONE; P2 IN PROGRESS; P3–P5/M1/prod OPEN.

## P2 / R159A1 native transport ve servis sahibi kaynak teslimatı

Özgün native runner/adapter/authority/üç store ve epoch üzerinde açık tek
loopback transport, dar authenticated sorgu/Stop yolları ve somut harness
servis sahibi eklendi. Bütün servis READY olmadan Host Gate üzerinden yeni iş kabul edilmez; drain
mevcut kontrolü korur. Listener retirement öncesinde HTTP handler, fiziksel
worker, SQL ve native gözlem aboneliği yükümlülükleri denetlenir. Belirsiz
etkiler özgün sahibi tutar; kapanış kanıtı yapay olarak tamamlanmaz.

Kuyrukta iptalin producer retirement sonrasında stopping işaretini yeniden
ekleme yarışı düzeltildi. Aynı canonical admission'ın hiç worker başlatmadığı
raporu, istemcide sıkı kimlik/şema kontrolüyle gösterilir; global fiziksel iş
kapanışı veya yeniden gönderme izni anlamına gelmez.

Yeni native kaynak `5e3635c2cdfc2161fd20c089618bd7f2a7c12f2d`, ayrı 760 dosyalık
servis manifest'i ve seçilmiş Host Gate kilidiyle sabitlenir. Eski P1 seçimleri
ve kurulum korunur. 27 yeni native + 34 seçilmiş mevcut native test, 31 host
servis testi, 58 istemci/recovery testi ve 12 provenance testi geçti; kapsamları
ve başarısız ilk denemeler ayrı kanıtlardadır. Kaynak kapanışı, kurulum kabulü
olarak devralınmaz.

**R159 planı ve P2 IN PROGRESS.** Sonraki somut iş, günlük uzun ömürlü supervisor
çocuğu ve ayrı control/final-receipt kanalı üzerinden CLI start/close bağlantısı;
sonra yeni tek P2 kurulumu ve seçilmiş sınırlı gerçek model görevidir. Gerçek
provider/model çağrısı sıfır; yeni kurulum, tam M1 ve prod kabulü yoktur.
Rapor: [R159](P2-BORROWED-SERVICE-R159A1.md).


## P2 / R160A1 servis kontrol bileşenleri

Özgün native servis sahibine bağlı ready/reply/final protokolü, zaten sahip
olunan çocuğun pipe kanalı, CLI start/close/service-status istemcisi ve sonlu
worker'dan ayrı uzun ömürlü volume worker eklendi. İstek ve yanıt aynı servis,
PID, epoch, instance ve sıra kimliğine bağlanır. Kayıp yanıt otomatik tekrar
üretmez; salt okunur gözlem özgün işlemin sonucunu bekler. Native CLOSED
makbuzu tek başına volume kapama yetkisi değildir: süreç exit0 ve iki pipe EOF
kanıtı da yalnız child completion sonucudur; özgün volume stop/finish ayrıca
bağlanmalıdır.

Bu teslimat kaynak bileşenlerinin kabulüdür. Çalışan supervisor Unix-socket
sunucusu ve projected service factory henüz yoktur. Mevcut retained/finite
profil allowlist'i native model yükleyicisinin beklediği config.yaml dosyasını
kabul etmez. Özel network namespace içindeki loopback listener host CLI için
doğrudan erişilebilir değildir. Guard sonrasında config eklemek veya host
loopback erişimini varsaymak çözüm olarak kullanılmadı.

Yeni testler gerçek geçici socket/pipe'larla framing, sahiplik ve yanıt kaybını;
native lifecycle ve kernel işlemleri için açık test doubles ile kapanış
sözleşmelerini sınar. Kesin son sayı ve kaynak hashleri raporun odaklı test
makbuzundadır; bu sayı gerçek kurulum/kernel/model kabulü değildir.
P1 DONE; P2 IN PROGRESS; P3–P5, tam D3B, M1 ve prod OPEN.

Rapor: [R160A1](P2-SERVICE-CONTROL-R160A1.md).
Sonraki iş: [servis profil ve supervisor entegrasyonu](P2-SERVICE-INTEGRATION-R161A1-PLAN.md).


## P2 / R161A1 servis profil ve config kaynak sözleşmesi

Ayrı sürümlü servis profili; seçilmiş native kaynak, canonical home, üç DB,
önceki epoch/instance ve config device/inode/size/SHA-256 değerlerini bağlar.
En fazla 64 KiB canonical JSON kabul edilir; yardımcı dosyalar bounded,
no-follow ve nonblocking FD okumalarından geçer. Eski profil seçimleri korunur.
Host/target projection yalnız home'u değiştirir; ayrı servis handoff'u genel
başlatma yetkisi vermez. Özgün startup/consumer/worker-thread execution zinciri
config'i ve native loader'ın gerçek home yolunu yeniden denetler. Config drift
admission'ı durdurur; özgün sahiplik korunuyorsa bilinen cleanup yolu çalışır.

Son seçimde 306 odaklı test Linux'ta PASS; Windows'ta 298 PASS, 8 platform SKIP ve hata0.
Altı parent arşivi Git 5b7eba4 byte'larıyla eşleşti; güncel kaynak pinleri ayrı
sınandı. Native 760 kaynak, eski finite/retained layout'lar ve R156 kurulumu
korundu. Tam CI/yayın ayrıca status.md ile izlenir. Bu kaynak teslimatı gerçek
supervisor/kernel/kurulum/model kabulü değildir; P2 IN PROGRESS.

Rapor: [R161A1](P2-SERVICE-PROFILE-R161A1.md). Sıradaki somut iş,
[entegrasyon planının](P2-SERVICE-INTEGRATION-R161A1-PLAN.md) sabit projected
service receiver/factory adımıdır; ardından canlı supervisor kontrol sunucusu,
final/exit/EOF ile volume stop/finish ve host görev erişimi gelir.

## P2 / R162A1 sabit projected receiver ve factory kaynak bağlantısı

Ayrı sabit receiver/entry, R161 servis transferini ve gerçek profil/config
baytlarını doğrulayıp özgün lease/startup/consumer/service sahibiyle R160 control
driver'a bağlar. Tek startup denemesi, aynı runner/authority/epoch ve üç store
korunur. Son async readiness aralığındaki config/source değişimi READY öncesinde
yeniden denetlenir; dört eski negatif sonuç parent üzerinde gösterilip düzeltildi.
Belirsiz hata ve diagnostic kaybı özgün process/loop sahipliğini korur.

Son odaklı seçimde Linux 483/483 PASS; primary Windows 466 PASS + 17 platform
SKIP, failure/error 0 ve exit 0. Bağımsız config/native ve lifecycle incelemeleri
PASS. Exact-commit tam CI/yayın [status.md](../status.md) ve
[R162A1 raporunda](P2-SERVICE-RECEIVER-R162A1.md) ayrıca izlenir. Native 760 dosya,
eski profil seçimleri ve R156 kurulumu değişmedi. Native backup/restart,
effective-config, gerçek supervisor/kernel/kurulum/model kabulü açık kalır.

Sıradaki iş [entegrasyon planının](P2-SERVICE-INTEGRATION-R161A1-PLAN.md) üçüncü
adımı: özgün ServiceVolumeSupervisor ve Popen'a bağlı Unix kontrol sunucusu;
ardından final/exit/EOF ile volume stop/finish ve host görev erişimi.
**P1 DONE; P2 IN PROGRESS; P3–P5, tam D3B, M1 ve production OPEN.**

## P2 / R163A1 özgün supervisor ve Unix kontrol sunucusu kaynak bağlantısı

Özgün ServiceVolumeSupervisor aynı lease/fence/worker içinde tek sabit servis
çocuğunu ve ona bağlı Popen/ServiceChannel'ı tutar. Private Unix server mevcut
R160 CLI'ye start/status/close sunar; tam canonical frame ve write-EOF,
PID/startTicks/token ve gerçek SO_PEERCRED doğrulaması effect öncesinde gerekir.
Request ID yeniden gelişi yalnız aynı attempt'i gözler. Kaybolan start/close
yanıtı ikinci child, tekrar close veya cleanup başlatmaz.

Son kaynak seçimi Linux'ta 721/721 PASS; primary Windows'ta 608 PASS + 113 platform
SKIP, failure/error 0 ve exit 0. Aynı 25 ürün ve 42 test/destek dosyası ile
runner hashleri korunur; bağımsız kaynak incelemesi PASS. Ham test kayıtları,
tarihsel parent/receipt koruması ve yayın durumu
[R163A1 raporunda](P2-SERVICE-SUPERVISOR-R163A1.md) ve [status.md](../status.md).

Child final/exit/EOF tek başına volume kapanışı sayılmaz: dış durum DRAINING,
volume/fence/image release bayrakları false kalır. Sonraki somut iş
[entegrasyon planının](P2-SERVICE-INTEGRATION-R161A1-PLAN.md) dördüncü adımı olan
özgün volume stop/finish bağlantısıdır. Native 760 dosya ve R156 kurulumu
değişmedi; bu kaynak/fixture kabulü gerçek kernel/kurulum/model kabulü değildir.
**P1 DONE; P2 IN PROGRESS; P3–P5, tam D3B, M1 ve production OPEN.**

## P2 / R164A1 özgün servis volume kapanışı kaynak bağlantısı

Özgün ServiceVolumeSupervisor'ın aynı child/Popen/ServiceChannel final, exit0 ve
stdout/stderr EOF kanıtı, mevcut normal stop/finish zincirine bağlandı. Önce
cgroup'da yalnız özgün mount worker bulunması ve alt cgroup olmaması, ardından
exact UNMOUNTED/worker exit0 makbuzu ve tamamen boş scope gerekir. Generic
cleanup, loop bağlantısının yokluğu, fence temizliği ve image lease'in en son
bırakılması sırasını korur. Unix sunucusu tam CLOSED kanıtını yanıt yazmadan
önce saklar; mevcut Node istemci/CLI başarılı tam kapanışı bildirir.

Status ve aynı request ID'nin tekrarı yalnız özgün sonucu gözler. Child geç
kapanmışsa yeni açık close, henüz denenmemiş ilk volume kapanışını başlatabilir.
Başlamış veya UNKNOWN/BUSY kalmış stop/finish, yeni ID ile de tekrarlanmaz.
Kayıp son yanıt ikinci cleanup'a yol açmaz. Tail stream close hatasında dahi
özgün sahip ve kanıt saklanır; eksik finish makbuzundan CLOSED çıkarılmaz.

Son birleşik odaklı seçim Linux'ta 806/806 PASS; primary Windows'ta 626 PASS ve
180 platform SKIP, failure/error 0 ve exit 0. Aynı 25 ürün, 50 test/destek dosyası,
runner ve sıralı test kimlikleriyle koşuldu; kaynak/test hashleri değişmedi.
Bağımsız kaynak review PASS, taze tarihsel 14 test PASS; bu tarihsel testler
birleşik 806 seçimin de içindedir. Dokuz exact parent arşivi ve önceki kaynak
nesillerine bağlı kanıtlar korundu. Exact source/final tam CI ve main yayını
[R164A1 raporu](P2-SERVICE-CLOSURE-R164A1.md) ile [status.md](../status.md)
üzerinden ayrıca izlenir.

Native 760 kaynak ve kabul edilmiş R156 kurulumu değişmedi. Bu kaynak/fixture
sonucu gerçek kernel, kurulu native servis, restart veya model kabulü değildir.
Sıradaki somut iş [entegrasyon planının](P2-SERVICE-INTEGRATION-R161A1-PLAN.md)
beşinci adımı olan host görev erişimi: aynı authenticated native API'ye dar
transport bağlantısı; yeni queue veya sonuç store'u olmadan görev, sorgu,
sonuç/kullanım ve cancel. Ardından yeni tek P2 kurulumu ve gerçek kernel/native
kabulü gelir. Gerçek sağlayıcı deneyi için model, araç kümesi ve bütçe seçimi açık.
**P1 DONE; P2 IN PROGRESS; P3–P5, tam D3B, M1 ve production OPEN.**

## P2 / R165A1 host görev erişimi — odaklı kaynak kabulü PASS

28 Ekim 2026: R164A2'nin yayımlanmış
`994751bed14046e3e0dd14be90912048b996a836` commit'i üzerinde P2 entegrasyon
planının beşinci adımı başladı. Aynı özel Unix endpoint'i ve özgün child'ın
mevcut stdin/stdout FIFO/pipe akışı üzerinden bounded görev çerçeveleri;
child'ın sabit loopback'inde aynı kimliği doğrulanmış native HTTP API'ye
bağlantı uygulandı. Yeni queue, sonuç store'u veya ikinci owner oluşturulmaz.

Capabilities, intent, dispatch, özgün request sorgusu, durum/sonuç/kullanım
ve stop için altı dar HTTP yolu seçildi. Lifecycle şeması ve 65.536 byte sınırı
korunur; task aktarımının ayrı byte/süre sınırları, özgün sequence ve tek
bekleyen exchange sözleşmesi vardır. Kayıp yanıt yeni POST ile tekrarlanmaz;
özgün native request locator'ı kullanılır.

CLI seçimi `ALAZ_TASK_TRANSPORT=supervised-service` ile yapılır; değişken
yoksa mevcut HTTP yolu kullanılır. `ALAZ_BASE_URL`, `ALAZ_API_TOKEN` ve beş
`ALAZ_SERVICE_*` bağlantı alanı açık sağlanır. Unix modunda URL yalnız route
origin eşlemesidir. Request timeout varsayılanı 5.000 ms, response sınırı
1.048.576 byte; watch/cancel bekleme/poll varsayılanları 30.000/100 ms'dir.

Son [Linux makbuzu](../evidence/p2-host-task-access-r165a1/focused-linux-02.json)
ve [log](../evidence/p2-host-task-access-r165a1/focused-linux-02.log) **459/459
PASS**, 0 FAIL/ERROR/SKIP, exit 0 ve 102,228894 saniye kaydetti; kaynak, test,
destek ve koşucu hashleri sabit kaldı. İlk [458 testlik koşu](../evidence/p2-host-task-access-r165a1/focused-linux.json)
451 PASS, 1 FAIL, 6 ERROR ile FAIL olarak korundu. Eksik beş R158 tarihsel
dosyası exact base'ten tamamlandı. Eski watch-timeout başlangıç hatası ilgili
test baytları değişmeden tekrar üretilemedi; ilk sonuç PASS'e çevrilmedi.

Sabit CI image'ında `aiohttp` yoktur; standart discovery gerçek HTTP fixture
testlerini bağımlılık yokluğunda açık gerekçeyle SKIP kaydeder. Hazırlanmış
Linux odaklı kapısı bu bağımlılığı zorunlu tutar ve bütün seçimi çalıştırdı.
Source/final CI sonuçları R165 raporunda izlenir; image, bağımlılık kurulumu veya
CI politikası değişikliği yapılmadı.

Primary aktarımı tamamlandı: 24/24 ürün/test dosyası, koşucu ve dondurulmuş
Linux/parent kanıtları hash kontrolüyle doğrulandı; Bridge erişimi canlı.
Request 12'nin geçmiş yürütme sonucu UNKNOWN olarak korunur. Request 14'te
canlı dosya önkoşulları, runtime restart ve boş kuyruk gözlemiyle mevcut durum
uzlaştırıldı; yeni request 15–18 aktarımı tamamlandı.

İlk [Windows makbuzu](../evidence/p2-host-task-access-r165a1/focused-windows.json)
ve [log](../evidence/p2-host-task-access-r165a1/focused-windows.log) **459 RUN /
240 PASS / 218 SKIP / 1 FAIL / 0 ERROR**, exit 1 olarak korundu. Mevcut
`test_hybrid_wire.HybridWireTests.test_timeout` vakası başarısız oldu.
Aynı özgün testin dar incelemesinde BASE ve güncel kaynakta altışar normal
tekrar PASS; iki kontrollü 350 ms gecikme demosunda her iki sürüm aynı
`settlement_unconfirmed`/`state=unknown`/`backendConfirmed=false` sonucunu verdi.
Bu bulgular ilk FAIL'in kesin kök nedeni veya ürün kabulü sayılmaz; kaynak,
test süreleri ve assertion'lar değiştirilmedi.

Taze [Windows makbuzu](../evidence/p2-host-task-access-r165a1/focused-windows-02.json)
ve [log](../evidence/p2-host-task-access-r165a1/focused-windows-02.log) **459 RUN /
241 PASS / 218 SKIP / 0 FAIL / 0 ERROR**, exit 0 ve 87,580529 saniye kaydetti;
request 34 tamamlandı. Kaynak/test/destek/koşucu hashleri ve seçilen/yürütülen
sıralı ID'ler Linux ile aynı kaldı. Linux 459/459 PASS ile Windows 241 PASS +
218 SKIP ayrı kaydedilir; tanı tekrarları ve demoları test sayısına eklenmez.
İlk Linux ve ilk Windows FAIL kayıtları değişmeden korunur; yeni PASS ilk
Windows başarısızlığının kesin nedenini kanıtlamaz.

Staging/statik kontrol, exact source/closure commit'leri, source/final CI ve
main yayınının güncel sonuçları [status.md](../status.md) ve R165 raporunda izlenir.
Odaklı kapıların geçmesi tek başına kaynak yayını değildir. R159 servis kaynak
seçimi command secret-source modülünü
zaten içerir; gerçek kurulumdaki provider/config/credential kabulü sonraki kapıdır.

Altıncı adımın paketleme açığı sürer: mevcut builder finite neslin 756 native
dosyasına, P2 servis seçimi 760 dosyalık ayrı nesle bağlıdır. Servis sabit
girişleri, selection/manifest/host-lock config'leri ve Node 24 host CLI
dağıtımı yeni P2 candidate/install paketinde açıkça envanterlenmelidir.
Yerel Python modüllerinin otomatik seçilmesi bu kurulum işini tamamlamaz.

Rapor: [R165A1 host görev erişimi](P2-HOST-TASK-ACCESS-R165A1.md).
Sonraki sıra: source-check ve exact manifest'i oluşturmak, staging/statik
ve source/final CI/yayın kapılarını tamamlamak; sonra yeni tek P2 kurulumu ve
gerçek kernel/native servis kabulü.
Sınırlı gerçek görev için model/sağlayıcı, araç kümesi ve bütçe seçimi ayrıca
açıktır. **P1 DONE; P2 IN PROGRESS; P3–P5, M1 ve prod OPEN.**
