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
| P2 | Günlük yerel kullanım ve tek gerçek model | Başlat, görev ver, izle, sonuç/kullanımı gör, iptal et, kapat; seçilmiş araçla gerçek görev ve sınırlandırılmış model bütçesi | IN PROGRESS; R158 yerel CLI ve kayıp yanıt locator kaynak/HTTP sözleşmesi tamamlandı. Native günlük listener/start/close ve gerçek model kabulü açık; R159 sıradaki paket. |
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
kararı üstteki tabloda ve en son R158 teslimatında yer alır.

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
