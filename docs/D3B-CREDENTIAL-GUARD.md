# D3B — Dosya ve broker kimlik bilgisi koruması

İş: D3B-CREDENTIAL-6E42. Tarih: 18 Ekim 2026.
Dal: `alaz/d3b-credential-6e42`.
Başlangıç: `2bffac9aaf482363d335bdbd3c76cc687be83533`.

## Kabul sınırı

Bu dal, eşzamanlı `D3B-NETNS-4E62` ağ çalışmasının **tamamlayıcısıdır**.
Ağ dalının dosyaları veya kökteki durum aynası değiştirilmedi. Yeni bir ajan
motoru, veritabanı, zamanlayıcı, ayrı bütçe veya model çağırıcısı eklenmedi.

Linux x86_64 üzerinde Landlock ABI 3 ve `no_new_privs` kullanan, açıkça
başlatılan bir dosya erişim koruması eklendi. `credential_guard.py` yalnızca
izin verilen salt-okunur kaynaklar ve yazılabilir çalışma dizinleri için
kurallar oluşturur. Belirtilen korumalı dosyanın herhangi bir izinli ağacın
altında kalması reddedilir. Sistem geneline ayar kurulmaz. Modülü içe
aktarmak veya mevcut Gateway'i çalıştırmak korumayı kendiliğinden açmaz.

**Dar Linux dosya erişim kabulü geçti. Koruma altındaki gerçek Hermes
Gateway başlangıcı henüz geçmedi. Bu dal tam D3B veya üretime hazır
Gateway izolasyonu değildir.**

## Eklenen bileşenler

`packages/claw-hermes/credential_guard.py`: tip ve yol doğrulaması, Landlock
ABI denetimi, kurallar, tek iş parçacığı/açık dosya tanıtıcısı ön koşulları,
`no_new_privs`, kısıtlamanın uygulanması ve korumalı dosyanın açılamadığının
kontrolü. Desteklenmeyen kernel veya mimaride daha zayıf davranışa düşmez.

`scripts/run_credential_guard.py`: mevcut uygulamayı yeni ve kısıtlanmış
bir alt süreç olarak `exec` ile başlatan açık operatör komutu. Önce politika
uygulanır, ardından izinli çalışma dizinine durum makbuzu yazılır. Başarısızlık
halinde hedef uygulama korumasız çalıştırılmaz; çıkış kodu 2'dir.

`scripts/qa/native_credential_guard.py`: geçici ve yalnız teste ait Linux
verileri üzerinde olumlu/olumsuz denemeler. Üretim kimlik bilgisi kullanmaz.

`scripts/qa/native_credential_gateway.py`: AF21'in gerçek Gateway kabul
düzeneğini değiştirmeden çağıran ayrı test sarmalayıcısı. Yalnız bu koşunun
ürettiği broker başlangıç dosyasını Gateway'e izin verilen dizinin dışına
taşır ve Gateway alt sürecinin önüne dosya korumasını yerleştirir. Orijinal
broker, Gateway ve Dream ürün kodları değişmez. Sonuçları henüz FAIL'dir.

`tests/test_credential_guard.py`: 26 çevrimdışı politika/ABI sözleşme testi;
bu testler ana unittest sürecini Landlock ile kısıtlamaz.

## Gerçek Linux testinde ne doğrulandı?

Yeni bir özel dizinde rastgele oluşturulmuş broker dosyası ve salt-okunur
kaynak canary'si kullanıldı. Aynı kullanıcıya ait kısıtlanmamış test denetleyicisi
canary'leri oluşturdu; kısıtlanan çocuk bunların içeriğini yayımlamadı.

On üç çocuk süreç denetimi: izinli kaynak okunabiliyor; izinli çalışma dosyası
yazılabiliyor; SQLite yazma/okuma çalışıyor; gizli dosyanın okuma ve yazma
amaçlı açılması reddediliyor; salt-okunur dosya yazımı ve `O_RDONLY|O_TRUNC`
reddediliyor; sembolik bağlantıyla gizli dosyayı okuma ve ona sabit bağlantı
oluşturma reddediliyor; denetleyici sürecin `/proc/<pid>/mem` dosyasını açma
reddediliyor; yeni `exec` alt sürecinden gizli dosya okunamıyor;
`no_new_privs` etkin ve kapatılamıyor.

Üç ek başlangıç reddi: önceden açılmış gizli dosya tanıtıcısı, standart giriş
üzerinden soket ve gizli dosyanın önceden var olan ikinci sabit bağlantısı
hedef iş başlamadan reddediliyor. Gizli dosyanın ve kaynak canary'sinin özgün
baytları değişmeden kalıyor. Bu 16 kontrol tek Linux kabul çalışmasının
iddialarıdır; 16 benzersiz unittest veya 16 ayrı Gateway koşusu değildir.

Son kanıt: `evidence/d3b-credential-6e42/native-final.json`.
İlk dar kabul `native-initial.json` olarak korunur.

## Gateway denemelerinde açık kalan sorun

`gateway-initial.json` ve `gateway-diagnostic2.json`, hazırlanmış taşınabilir
Python yorumlayıcısının açık bıraktığı kendi çalıştırılabilir dosyasının
başlangıç denetiminde reddedildiği denemeleri korur. Yalnız `/proc/self/exe`
ile cihaz/inode kimliği aynı, salt-okunur ve açıkça izinli olan yorumlayıcı
tanıtıcısının kapatılması eklendi; diğer fazladan dosya tanıtıcıları hâlâ
reddedilir. Bu, açık kimlik bilgisi tanıtıcısına istisna vermek değildir.

`gateway-fdclosed3.json` kaydında koruma uygulanmış ve gizli dosya açılışı
reddedilmiş olmasına rağmen hedef Python başlangıcı tamamlanmamıştır.
İzin listesine yalnız salt-okunur `/dev/urandom` desteği eklenen
`gateway-entropy4.json` da Gateway başlangıcını tamamlamamıştır. Sonraki
teşhis kaydı bu turda okunamadı; son hatanın kök nedeni kesinleştirilmedi.

Bu denemelerde orijinal broker temiz kapandı, soket kaldırıldı ve hiçbir
sağlayıcı isteği yapılmadı. `guard.state=enforced`, Gateway'in çalıştığını
kanıtlamaz. Dört FAIL raporu korunur; yeni bir izin istisnası ekleyerek
korumayı sessizce kapatma veya sınırsız kök dosya erişimi verme yapılmadı.

## Landlock kapsamı ve güven varsayımları

Kernel arayüzü Linux 6.6 Landlock kullanıcı alanı dokümantasyonuna dayanır:
https://docs.kernel.org/6.6/userspace-api/landlock.html

ABI 3, açılacak dosyalar için kısıtları çocuk süreçlere ve `exec` sonrasına
aktarır. Daha sonra eklenen kurallar eski kısıtları kaldıramaz. Bu sürümde
**ağ trafiği ve Unix-socket bağlantıları** bu modül tarafından sınırlandırılmaz.
Metadata işlemlerinin tümü, bütün ioctl türleri, genel süreç sinyalleri,
önceden açık tanıtıcılar veya dışarıdaki yetkili bir yardımcı servisten alınan
veriler için eksiksiz koruma iddia edilmez. Ayrı host UID kullanılmadı.

Politikayı oluşturan operatör ve parent süreç güvenilir olmalıdır. Gizli
veriler çevre değişkenleri, stdin/stdout, izinli başka kopyalar veya yetkili
IPC servisleri üzerinden çocuğa verilmemelidir. Landlock izni bir ağaç için
olumludur; gizli dosyanın izinli üst dizini varsa ayrı bir negatif kural bunu
geri alamaz. Bu nedenle korumalı dosyanın izinli ağaçta olması reddedilir.
Kötücül yetkili host kullanıcısına veya kerneli ele geçiren saldırgana karşı
bağımsız kimlik bilgisi kasası değildir.

Gateway kendi çalışma veritabanına yazmaya devam edebilir. Bu nedenle
kötücül Gateway'in bütçe kayıtlarını değiştirmesine karşı bağımsız broker
otoritesi ayrıca tasarlanmalı/sınanmalıdır. Dosya erişimi kabulünü bu riskin
kapatılması gibi yorumlama.

## Açık operatör kullanımı

Örnek politika şekli; tüm yollar gerçek, canonical ve operatörün seçtiği
yollar olmalıdır. Salt-okunur ve yazılabilir ağaçlar örtüşemez. Uygulamanın
çalıştırılabilir dosyaları ve kitaplıkları salt-okunur izinlerde bulunmalıdır.

```json
{"version":1,"enabled":true,"readonly":["/usr","/owned/code"],"writable":["/owned/runtime","/dev/null"],"protected":["/private/broker.json"]}
```

```text
python3 -I -B scripts/run_credential_guard.py --policy <private-policy.json> --receipt <new-owned-runtime-receipt.json> -- <absolute-executable> <arguments>
```

Komut yeni bir çocuk/worker süreçte kullanılmalıdır; çalışan Gateway'in iş
parçacıklarına sonradan uygulanmamalıdır. Makbuz hedefi yeni ve izinli çalışma
alanı içinde olmalıdır. Varsayılan/prod profiller bu çalışmada değiştirilmedi.

## Kesin sonraki iş

Hazırlanmış Python ortamının kısıtlama sonrası başlamamasını, yeni ve özel
bir koşuda çözmek; gerekli en küçük izinleri açıkça gerekçelendirmek ve gerçek
Gateway + orijinal broker + dosya korumasını yeniden kabul etmek. Sonrasında
ayrı ağ dalıyla ortak kabul gerekir. Host dışı gerçek sağlayıcı veya öğrenme
ölçümü bu dar dosya pilotunda açılmadı. `main` birleştirmesi yapılmadı.

## Son test kaydı — 2026-10-18T11:58:34.760689+03:00

Tam çevrimdışı regresyon **1885/1885 PASS**, exit0, skip0. 26 yeni test
bu toplamın içinde; 266 ölçülen kaynak dosyası değişmedi. Ayrı Linux kernel
çalışması 13 erişim kontrolünü ve 3 başlangıç reddini geçti. Statik kapı
PASS. Bunlar koruma altındaki Gateway başlangıcındaki FAIL kayıtlarını
kapatmaz. Bu dal bileşen pilotudur; tam D3B kabulü açık kalır.
