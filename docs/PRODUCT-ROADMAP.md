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
| P1 | Güncel kurulum, sabit supervisor/launcher ve gerçek native iş bağlantısı | Aynı ürün girişinden readiness, normal/hata, replay/yeni iş ve sıralı kapanış; gerekli kimlik, namespace, mount, FD ve kaynak kontrolleri | IN PROGRESS; R155. Güncel kurulum, aynı supervised imajda gerçek seed, projected readiness ve sıralı kapanış PASS; normal/hata, replay/yeni iş ve finite görev kabulü açık. |
| P2 | Günlük yerel kullanım ve tek gerçek model | Başlat, görev ver, izle, sonuç/kullanımı gör, iptal et, kapat; seçilmiş araçla gerçek görev ve sınırlandırılmış model bütçesi | OPEN; kontrollü model/broker altyapısı mevcut. |
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
5. Önce readiness, sonra finite iş kabulü; hata/belirsizlikte zorla close, lease
   bırakma, mount kaldırma, reset veya otomatik retry yok.

R152 yalnız sıradan kullanıcı altında gerçek Landlock + retained yaşam döngüsünü
kabul etti; bu eski sonuç tek başına ürün supervisor kabulü değildi. R155'te aynı
özgün supervisor ve ext4 imajında gerçek seed, sabit ürün çocuğu üzerinden
projected readiness ve normal kapanış ayrıca kabul edildi. L145 hedefi hâlâ
yalnız readiness yapar; gerçek finite görev bağlantısı ve kabulü açık.

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
