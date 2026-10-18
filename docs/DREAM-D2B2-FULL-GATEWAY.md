# Dream D2B2 — Gerçek Hermes Gateway ve üretim broker kabulü

**İş:** DREAM-D2B2-GATEWAY-AF21 · **Tarih:** 18 Ekim 2026
**Dal:** `alaz/dream-d2b2-gateway-af21`
**Başlangıç:** `d7f97ffc45d2cbf9907590effec672154ad1518c`

## Sonuç ve kapsam

Dört ayrı Linux çalışmasında gerçek Hermes Gateway, yerel SessionAuthority,
Alaz HostGate eklentisi ve değiştirilmemiş `ProviderBrokerServer`/`aiohttp`
HTTP yolu birlikte sınandı. Normal iş, yetersiz toplam rezervasyon bütçesi,
dersli denemenin yanıtı gelmeden bağlantının kopması ve adayın inceleme
kararının geri çekilmesi beklenen davranışı gösterdi. Bu, önceki testte
kullanılan stdlib `_upstream` taklidi değildir.

**Gerçek olan altyapıdır; model yanıtları hâlâ programlanmış yerel test
sunucusundan gelir.** Bu kabul, gerçek model çıkarımını, öğrenmeyi,
Docker dosya-aracı izolasyonunu veya tüm işletim sistemi seviyesinde ağ
izolasyonunu kanıtlamaz. Ürün paketleri ve `main` bu işte değiştirilmedi.
Yeni dosyalar kabul düzeneği, çevrimdışı test, rapor ve kanıttır.

## Artık hangi zincir uçtan uca çalışıyor?

Gerçek bir Gateway görevinden yerel test yanıtıyla tamamlanmış oturum
oluşturulur. D1 bu oturumun gerçekten saklanmış son yanıtından kaynak
alıntılı aday ders çıkarır. D2A HTTP arayüzü üzerinden aday yalnızca
`accept_for_testing` olarak işaretlenir. D2B1, aday kimliğini, güncel inceleme
revizyonunu ve puanlayıcı kodunu cevap anahtarının özel HMAC taahhüdüne bağlar.
D2B2 aynı sorular için derssiz ve dersli istekleri mevcut ortak bütçe
kayıtlarından ve gerçek ayrı broker sürecinden geçirir.

Normal koşuda sırasıyla `native_agent`, `dream`, `baseline`, `candidate`
olmak üzere dört gerçek yerel HTTP isteği oluştu. Dört istek özeti, yerel
sunucunun gördüğü ham baytların SHA-256 değerleriyle eşleşti. Aynı dört
istek için mevcut veritabanında dört sağlayıcı rezervasyonu, dört egress
yetkilendirme kaydı ve dört doğrulanmış yanıt gözlemi bulundu. Tek native
görev kabulü, tek Dream aday kümesi, tek inceleme ve tek iki-denemeli kayıt
var. Dosya aracı çalıştırılmadı.

## Aynı son sürümle yapılan dört kabul denemesi

| Senaryo | Fiziksel HTTP / gözlenen yanıt | Saklanan deneme kolu | Deneme sonucu |
|---|---|---|---|
| Normal | 4 / 4 | Derssiz + dersli | `completed` |
| Toplam token rezervasyon sınırı | 3 / 3 | Yalnız derssiz | `unknown`, `token_exposure_limit` |
| Dersli yanıt gelmeden bağlantı kesintisi | 4 / 3 | Yalnız derssiz | `unknown` |
| İnceleme kararı geri çekildi | 3 / 3 | Hiçbiri | `unknown`; dersli istek gönderilmedi |

Son üç satırdaki `unknown`, testin başarısızlığı değildir: eksik veya yetkisi
geri çekilmiş bir işin başarılı ilan edilmemesi beklenir. Aynı plana yapılan
**açık test tekrarı** yeni sağlayıcı rezervasyonu oluşturmadı. Geri çekilmiş
adayda tekrar HTTP 409 ile reddedildi. Otomatik yeniden gönderim veya bütçe
iadesi açılmadı.

Her koşuda Gateway ve broker exit0 ile kapandı, broker soketi kaldırıldı ve
aktif broker isteği kalmadı. Özel test profilindeki operatör hafıza/beceri
sentinel dosyaları aynı kaldı. Gateway'in mevcut Python ağ gözlemcisi bu
koşularda dış bağlantı girişimi raporlamadı; bu gözlem OS seviyesinde eksiksiz
egress denetimi anlamına gelmez. Kaynak kodu çalışma öncesi/sonrası hash'leri
son makbuzlarda saklanır.

## Kesintiden önceki sorunlar ve korunan kanıt

`normal-initial.json` broker soketi için aşırı uzun çalışma yolu nedeniyle
başlangıç reddini korur. Çözüm, üretim broker kontrolünü gevşetmek değil,
test soketini kısa, özel ve yeni bir `/tmp` dizinine almaktı.
`normal-brokerpath-2.json` test sunucusunun boş HTTP 401 yanıtına JSON
bekleyen test yardımcısının hatasını korur.

`normal-auth-3.json` gerçek bütçe reddini içerir: test zinciri dört rezervasyon
gerektirirken toplam tavan üç rezervasyona göre belirlenmişti. Her rezervasyon
131.072 giriş + 32.768 çıkış = 163.840 token **risk tavanıdır**, ölçülmüş
model token kullanımı değildir. Normal test için 4 × 163.840 = 655.360 toplam
tavan ve en fazla dört çağrı açıkça tanımlandı. Ürün bütçe kontrolü ve
üretim ayarları değiştirilmedi. Aynı üç-rezervasyon sınırı ayrı olumsuz test
olarak tekrar sınandı ve dördüncü isteği doğru biçimde engelledi.

`normal-budget4-4.json` kesinti öncesinde zaten tamamlanmış ilk başarılı
koşuyu korur. Kesinti sonrasında bu sonuç yeniden çalıştırılmış gibi
sunulmadı; yeni dört senaryo yeni profillerde ve ayrı `*-final.json`
dosyalarında çalıştırıldı. Önceki hatalar silinmedi veya PASS'a çevrilmedi.

## Ortam ve kaynak sabitleme

Hermes kaynak revizyonu:
`eb75627faf532fa6ffbdae59a0d14b0b385fc780`.
Kaynak kilidindeki dosya hash'leri yeniden doğrulandı. Linux çalışma alanı
`/home/ender/alaz-harness-d2b2-gateway-af21` altında ayrıldı. Python 3.14.3,
Hermes'in `pm.build_environment(..., frozen=True)` çıktısı, `aiohttp` 3.14.3
ve Node v26.7.0 kullanıldı. Node arşivi Hermes PM kilidindeki SHA-256 ile
kontrol edildi; eksik `libatomic` paketi yalnız bu özel araç dizinine açıldı.
Sistem geneline paket kurulmadı ve kişisel Hermes profili kullanılmadı.

Python 3.14.3 test için seçilmiş sabit yorumlayıcıdır; Hermes PM kilidindeki
ayrı Python 3.14.7 paketinin çalıştırıldığı iddia edilmez. Bağımlılık hazırlığı,
çalışan sürümler ve arşiv hash'leri `environment-verified.json` içindedir.
Önceki temel HostGate yeniden başlatma smoke testi de aynı ortamda başarılıdır;
bu, Dream inceleme/deneme kayıtlarının epoch değişiminde yeniden açılmasının
ayrıca kabul edildiği anlamına gelmez.

## Yeniden üretim ve kanıt yolları

` scripts/qa/native_d2b2_full_gateway.py ` kabul çalıştırıcısıdır;
` scripts/qa/d2b2_gateway_task_client.mjs ` yalnız ilk gerçek native görevi
mevcut HostGate istemcisiyle başlatır. Betikler kişisel veya üretim profilini
kullanmaz; yeni çalışma yolu ve yeni kamuya açık makbuz adı ister.

```text
<prepared-python> -B scripts/qa/native_d2b2_full_gateway.py --scenario normal --source-workspace <pinned-source-workspace> --python <prepared-python> --node <private-node-wrapper> --output <new-private-runtime-directory> --public-receipt evidence/d2b2-gateway-af21/<new-report>.json
```

Diğer senaryolar: `budget-limit`, `candidate-disconnect`, `review-revoked`.
Çağrı ve kaynak hash'leri `*-launch.json` dosyalarında, gerçek çalışma
sonuçları `*-final.json` dosyalarındadır. Özel profil, ham yanıt metinleri,
API tokenları, broker imza anahtarı ve cevap anahtarı Git'e alınmaz. Test
profilleri teşhis için özel Linux çalışma alanında tutulur; silindikleri
iddia edilmez. Sonlanan süreçler yeniden kullanılmaz.

`tests/test_d2b2_gateway_acceptance.py` dört bütçe/senaryo sözleşmesi ve yedi
sonuç-kaynağı kontrolü içerir. Bunlar çevrimdışı testlerdir; yeni native
çalıştırma veya yeni model çağrısı sayılmaz. Tam regresyonun ve Git/CI'nın
kesin sonucu ayrı makbuzla kaydedilir; test keşfi test çalışması değildir.

## Açık kalanlar

Gerçek modelden yanıt alma ve Dream dersinin yararlılığını bağımsız yeni
görevlerde ölçme henüz yapılmadı. Test sunucusu başarıyı 8/12 ve 12/12
üretecek şekilde programlıdır; bu sayılar öğrenme kanıtı olarak kullanılamaz.
İnceleme kararı da test istemcisi tarafından verilmiştir; fiziksel insan
incelemesi doğrulanmış değildir.

D3B bütün Gateway için OS kimliği/ağ izolasyonu, gerçek sağlayıcı/model/
tarife ve token sözleşmesi, Dream kayıtlarının yeniden başlatma sonrası
epoch uzlaştırması ve Docker aracıyla aynı zincirin kabulü açık kalır.
Gerçek model deneyi bu kapsamlar ve açık bütçe içinde ayrı yürütülmelidir.
Otomatik aktif hafıza/beceri terfisi ve otonom amaç seçimi açılmadı.

## Son yerel kabul — 2026-10-18T10:50:35.433372+03:00

Dört son native senaryo aynı kaynak sürümüyle PASS. Çevrimdışı tam regresyon
**1.859/1.859 PASS**, exit0 ve atlanan test yok; 11 yeni test bu toplamın
içindedir. Ölçülen 261 kaynak/test/konfigürasyon dosyasının SHA-256 değeri
sabittir. Statik kapı PASS, 1.859 test keşfi, 1.222 kök dosya ve iki gitlink
kontrolü raporladı; bu ikinci bir tam test çalışması değildir.

Son süreç kontrolünde bu işe ait çalışan Gateway veya broker bulunmadı.
Dört Gateway kapanışı doğrulandı. Otuz oluşturulmuş test kimlik bilgisiyle
yapılan kontrol, taranan kamuya açık kanıt dosyalarında eşleşme bulmadı.
Bu dar kontrol genel sır taraması veya OS izolasyon sertifikası değildir.
Özel teşhis profilleri özel Linux runtime alanında tutulmaktadır.

Git/CI yayını bu yerel kanıttan ayrı doğrulanacaktır.

## Git yayını ve aynı-kaynak CI — 2026-10-18T10:58:05.757705+03:00

Kabul kodu ve kanıtlar `35099bda644ebe042a4fab40649604fb837bb367` commit’iyle
`alaz/dream-d2b2-gateway-af21` dalına gönderildi. GitHub `alaz/local-ci`
**SUCCESS** olarak doğrulandı; API uzak test sayısını raporlamaz. Yerel
1.859/1.859 test ve dört native koşu ayrı kanıtlardır. Aynı 11 yeni
çevrimdışı kontrol hazırlanmış Linux Python ortamında da geçti; bunlar
yeni benzersiz testler veya yeni Gateway koşuları değildir.

Yayımlanan commit içindeki 261 kaynak dosyası ve dört native JSON makbuzu
test edilen baytlarla eşleşir. Ürün paketleri, konfigürasyon kilitleri ve
`main` değişmedi. Bu bölümün eklendiği yalnız-belge commit’inin CI durumu
yayından sonra ayrı kontrol edilir; kod CI başarısı onun yerine sayılmaz.
