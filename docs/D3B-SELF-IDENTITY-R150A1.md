# R150A1 — R147 kimlik haritası düzeltmesinin Git entegrasyonu

## Gerçekleşen ilerleme

Adlandırılmış Cloudflare Bridge oturumu yeniden kullanılabildi. Dosya okumaları ve
Git durum sorgusu bu tur başarıyla tamamlandı. Yayınlanmış main çalışma ağacı
31e0c54 üzerinde temizdi. Kullanıcının kökteki33 dosya değişikliği ve eski dalı
korundu. Bridge yapılandırması veya erişim yetkileri değiştirilmedi.

Yama yalnız yeni alaz/d3b-self-identity-r150a1 dalına uygulandı. İş yolu:
C:\Antigravity\AlazHarness\scratch\worktrees\d3b-self-identity-r150a1.
Önce git apply --check, sonra apply çıkış0. Üç ürün dosyası ve iki test dosyası,
R147'nin seçili210testte sınanmış aday kopyasıyla bayt bayt aynı. Orijinal R147
çalışma kopyası, main, kurulu Hermes ve kaynak kilitleri değiştirilmedi.

## Değişikliğin sınırı

Yalnız açık seçenekle gerçek çalışan sürecin uid_map ve gid_map dosyalarına
READ_FILE izni eklenir. Yollar/PID politika JSON'undan alınmaz. VarsayılanFalse,
eski dosya listelerini ve politika özetlerini korur. Projection seçeneği yalnız
retained düzen ve mount gözlemi birlikte seçildiğinde geçerlidir. Sabit başlatıcı
seçeneği açıkça ister. Kimlik gözlemcisi, capability ve kullanıcı kontrolleri aynıdır.
Proc dizinine genel erişim veya yazma/çalıştırma izni verilmez.

R147 deneyindeki dosya ve syscall sınırları test dublörleridir. Bu entegrasyon
Landlock kurmaz; kernel/WSL/izole başlatma veya gerçek model deneyi içermez.
Daha önce reddedilmiş root/bootstrap/mount/temizlik işlemleri tekrarlanmadı.

## Tam regresyon ve eski kanıtların korunması

İlk tam koşu3630test:3587PASS,23SKIP,20FAIL,0ERROR, çıkış1. Yeni19R147 kontrolü
tam depo içinde de geçti.20başarısızlığın tamamı eski kaynak dosyası özetleriyle
ilgiliydi: yeni kodun eski deney kaynağıyla aynı olması bekleniyordu. Bu ilk ham
log, sonuç ve kaynak envanteri silinmedi veya başarı olarak yeniden etiketlenmedi.

Eski deneylere ait değişecek dosyalar immutable31e0c54 Git nesnelerinden arşivlendi.
Yeni yardımcı yalnız dokuz açık dosya adı VE tam eski beklenen SHA eşleştiğinde
bu arşivleri kullanır. Arşiv içeriği de tekrar hash edilir. Bilinmeyen dosya/özet
veya güncel aday özeti için otomatik muafiyet yoktur. Eski kanıtların beklenen
özetleri, sonuçları ve native/kernel kaynakları değiştirilmedi. Yeni testler bozuk
arşivi, farklı dosyaya yönlendirmeyi ve güncel kaynakla eski kanıtın karışmasını
reddeder. Bu test bakımı eski kernel kabulünü yeni ürüne taşımaz.

Düzeltme sonrası ilgili126kontrol PASS: eski başarısız modüller, yeni19R147 ve
sekiz yeni kaynak-kökeni negatif testi. Bunlar yeni tam regresyonun alt kümesidir;
126, eski210 ve tam test sayıları birbiriyle toplanmaz. Gerçek ürün dosyaları ve
orijinal19test bütün bu bakım boyunca R147 ile aynı kaldı.

Son tam koşu full002/ altında ayrı kaydedilir; tamamlanmadan PASS varsayılmaz.
Kaynak/config/test dosyaları634, native yama sayısı11. Önce/sonra özetleri ve
önceki23skip kimliği/gerekçesi karşılaştırılır. Eski full001FAIL korunur.

## Sıradaki kabul

Başarılı son tam regresyon ve statik kontrol ardından seçili dosyalar commit edilir.
Yayın yapılırsa yalnız aynı SHA CI başarısıyla main ilerletilir; force/squash yok.
Gerçek Landlock sonrası değişmemiş gözlemci, exec ve normal açılış/kapanış zinciri
ayrı bir testtir ve bu kayıttan kabul sonucu çıkarılamaz. Servis veya kurulu native
ortama otomatik dağıtım yapılmaz. Kesinti sonrası status.md ve terminal iş kaydı
okunur; sonucu belirsiz etkili komutlar tekrar edilmez.

## Son tam regresyon

Full002 tamamlandı:3638toplam,3615PASS,23SKIP,0ERROR/FAIL, runnerexit0.
634kaynak/config/test dosyası ve11yama önce/sonra/güncel aynı;23skip kimliği/gerekçesi
korundu. R14719kontrol ve yeni8arşivnegatif testi bu toplamın alt kümesidir.
Üç ürün dosyası dâhil R147beşdosya aynıdır. Ek bakım yalnız eski kaynak kanıtı
kontrollerindedir; eski sonuç veya beklenen SHA değiştirilmedi.622/631eski kaynak
dosyası değişmeden kaldı. Gerçek Landlock/WSL kabulü yapılmadı.
