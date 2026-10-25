# R149 — Öz süreç kimlik haritaları: ayrı Git kopyasında entegrasyon

## Çalışma alanı ve kapsam

Bu çalışma, yayımlanmış `31e0c54c530151bd25ebc43f617a853bb1736412`
sürümünün yeni ve bağımsız bir public Git klonunda yürütülüyor:
`C:\Antigravity\AlazHarness\scratch\r149-integration-a9\repo`.
Dal: `alaz/self-identity-r149a9`.

Asıl yerel deponun Git metadatasına veya çalışma ağaçlarına yazılmadı. Önceden
engellenen asıl Git durum komutu tekrar edilmedi. Yeni klondaki Git işlemleri
ayrı bir çalışma alanına ait; kurulu Hermes, servisler ve işletim sistemi izinleri
değiştirilmedi. Native submodule içerikleri kurulmadı; kaynak kilitleri ve 11 yama
aynen korundu. Asıl deponun güncel temizliği bu çalışmada yeniden doğrulanmış değil.

## R147 ürün yaması

R147 yamasının SHA-256 değeri:
`d78eb8c6b71d5d5d01ec4f29767285283fcd9d0bff8867f372c5e47e46ef7536`.

Yama önce `git apply --check` ile kontrol edildi, sonra yalnız bu yeni kopyaya
uygulandı. Üç ürün dosyası, bir mevcut test değişikliği ve bir yeni test dosyasının
son içerikleri, önceki R147 adayının beş SHA-256 değeriyle birebir aynı.

Genel izin mekanizmasındaki yeni seçenek varsayılan olarak kapalı. Açıldığında
yalnız `os.getpid()` ile belirlenen sürecin `uid_map` ve `gid_map` dosyalarına
READ_FILE izni ekliyor. Dizin, yazma veya çalıştırma izni yok; yol/PID politika
JSON'undan alınmıyor. Sabit retained başlatıcı bunu açıkça seçiyor. Eski düzenler,
varsayılan özetler ve gerçek kimlik gözlemcisi değişmiyor.

Bu kodun gerçek Landlock altında çalıştırıldığı iddia edilmiyor. Bu aşamada test
sınırları dosya/syscall modelleri içeriyor; namespace, mount, kernel, servis veya
sağlayıcı aktivasyonu yapılmadı.

## Tam regresyonda bulunan tarihsel kaynak uyuşmazlıkları

İlk tam koşu 3.630 testte tamamlandı: 20 başarısızlık, sıfır hata ve öncekiyle aynı
23 atlama. Tüm başarısızlıklar eski kanıtların yürütüldüğü kaynak özetlerini yeni
kaynak dosyalarıyla karşılaştıran kontrollerdi. Bu ilk sonuç başarısız olarak ve
ham günlüğüyle korunuyor; başarılı diye yeniden etiketlenmedi.

Dokuz adlandırılmış eski dosya için yalnız sabit `31e0c54` Git nesnelerinden alınan
kaynak arşivi eklendi. Beklenen eski özet, sabit kaynak nesli, baseline manifesti
ve arşiv içeriği birlikte eşleşmek zorunda. Bilinmeyen yol, bilinmeyen özet veya
yeni ürünün özeti eski arşive yönlendirilmiyor. Yeni kod eski kernel kanıtından
kabul devralmıyor. Eski sonuç/manifest/ham kanıt dosyaları değiştirilmedi.

Beş tarihsel test/yardımcı dosyasında yalnız kanıtın doğru kaynak nesline erişimi
uyarlandı. R147 ürün/test adayının beş dosyası bu düzeltme boyunca değişmedi.
Sorunlu modüllerin 99 testi tekrar geçti. R147'nin 19 testi ile 12 yeni arşiv
bağı kontrolü birlikte 31/31 geçti. Bunlar tam test paketinin alt kümeleridir;
ayrı kernel deneyleri veya toplam test sayısına ek kabul sayılmaz.

## Son doğrulama

İkinci tam koşu, 634 kaynak/config/test dosyası ve 11 yamanın değişmeden kaldığını
doğrulayacak şekilde çalıştırılıyor. Kesin terminal sonuç `full002/result.json`
içindedir; bu rapor tamamlanmadan PASS sonucu varsayılmaz. İlk başarısız koşu
`full001/` altında kalır. Yeni davranış ve tarihsel kanıt doğrulaması ayrıdır.

622 eski kaynak dosyası aynı, dokuz mevcut dosya değiştirilmiş ve üç yeni test/
yardımcı dosyası eklenmiştir. Ürün değişikliği hâlâ R147'nin üç dosyasıyla sınırlıdır.

## Sonraki kabul sınırı

Tam regresyon ve statik denetim sonrasında bu bağımsız dalda yerel commit yapılır.
Commit/push/uzak CI/main durumu ayrıca ve canlı kanıtla kaydedilir. Gerçek kernel
altındaki olumlu başlatma/exec/kapanış, HTTP, model, çökme ve güç kesintisi sonrası
kurtarma henüz bu çalışmanın kabulü değildir. Önceden engellenen root/WSL/mount
veya bootstrap işlemleri bu kaynak raporuyla yetkilendirilmiş sayılmaz.

## Kesin son tam test sonucu

İkinci tam koşu: **3.642 toplam, 3.619 başarılı, 23 atlanan, sıfır hata ve
sıfır başarısızlık; çıkış kodu 0**. Önceki 23 atlamanın kimlikleri ve gerekçeleri
aynı. 634 kaynak/config/test dosyası ile 11 yama koşu öncesi/sonrası/güncel olarak
eşleşiyor. İlk başarısız koşu aynen korunuyor. R147 beş aday dosyası değişmedi.
Bu sonuç gerçek Landlock/kernel kabulü değildir. Yerel commit ile yayın/CI/main
aşamaları ayrı tutulur; bu aşamada uzak depoya yazılmadı.
