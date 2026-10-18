# D3B — Dosya koruması altında gerçek Gateway başlangıcı

İş: **D3B-CREDENTIAL-STARTUP-B71E**, 18 Ekim 2026.
Dal: `alaz/d3b-credential-startup-b71e`.
Baz: `7632784c1238fdb5ebd09ee1131cb6a52ba5a4a1`.
Bu çalışma, önceki dosya koruması pilotunun Gateway başlangıç sorununu çözer.
Ayrı ağ dalının kaynaklarını ve kökün durum aynasını değiştirmez.

## Saptanan başlangıç engelleri

Önceki, sonucu belirsiz kalan tanı kaydını yeniden okumak yerine yeni özel
koşular oluşturuldu. Sistem Python 3.12.3 ve hazırlanmış Python 3.14.3,
aynı koruma altında küçük bir programı ve rastgele sayı üretimini çalıştırdı.
Sorun Python'un her koşulda başlatılamaması değildi.

**Windows bağlı dosya sistemi:** Bu WSL/kernel ortamında, izinli bir dizindeki
Gateway işçi dosyasının `/mnt/c` üzerinden açılması errno 13 ile reddedildi.
Bayt bayt aynı dosya, Linux dosya sistemindeki izinli bir dizinden okunabildi.
`filesystem-differential.json` bu karşılaştırmayı saklar. Bunu bütün WSL,
9p veya ağ dosya sistemleri hakkında genel bir iddia olarak yorumlama.
Çözüm, yetkiyi genişletmek değil, seçilmiş kaynakların doğrulanmış Linux
çalışma kopyasını kullanmaktır. Son kopyadaki 176 kaynak/konfigürasyon dosyası
Windows çalışma ağacıyla SHA-256 ve bayt karşılaştırmasıyla eşleşir; kişisel
profil, gizli anahtar ve `.git` ağacı kopyalanmaz. Kopya dosyaları salt okunurdur.

**Süreç yaşam döngüsü:** Hermes, kendi PID kaydını doğrularken `status`, `stat`
ve `cmdline` dosyalarını okur. Eski politika bütün `/proc` okumalarını
reddediyordu. İsteğe bağlı `self_metadata` alanı eklendi. Liste yalnız
`status`, `stat`, `cmdline` adlarından oluşabilir; caller PID veya yol
seçemez. Başlatıcı, kendi gerçek PID'sini korumayı kurarken belirler; yalnız
bu üç dosyanın inode'una READ_FILE izni verilir. Dizin listeleme, bellek,
ortam değişkenleri, başka PID, yazma veya çalıştırma izni verilmez.

**Kontrol soketi:** Uzun çalışma yolunda Hermes kısa bir kontrol soketi yolu
kullanır. Tüm `/tmp` ağacına yazma izni yerine, yalnız bu koşunun denetleyicisinin
oluşturduğu özel, kısa ve 0700 izinli `XDG_RUNTIME_DIR` verildi. Broker'ın
gizli başlangıç dosyası bu izinli dizinin dışında kalır. Başarılı kapanışta
kontrol soketinin kaldırılması da kabul şartıdır.

**HTTP modülünün başlatılması:** `aiohttp.web`, Python `mimetypes` aracılığıyla
`/etc/mime.types` dosyasını okur. Yalnız bu mevcut dosyaya salt okunur erişim
eklendi; `/etc` ağacına genel erişim verilmedi.

## Ürün değişikliği ve varsayılanlar

Tek ürün değişikliği `packages/claw-hermes/credential_guard.py` içindeki
isteğe bağlı kendi-süreç metaverisi desteğidir. Alan kullanılmadığında eski
politika normalizasyonu ve hash değeri değişmez. Eski koruma, kalıtılan dosya
kontrolleri, gizli dosyanın bağlantı kontrolü ve `no_new_privs` davranışı korunur.
Yeni alan varsayılan olarak yoktur; mevcut profiller sessizce güncellenmez.

Örnek ilave politika alanı:

```json
"self_metadata": ["status", "stat", "cmdline"]
```

Bu liste bir `/proc` ağacı izni değildir. Yeni bir `exec` aynı PID üzerinde
çalıştığında gerekli metaveri okunur. Çocuk süreç, kendi farklı PID metaverisini
kendiliğinden okumaya yetkili olmaz; test bunu ayrıca doğrular. Eski Gateway
süreçlerini inceleyen yeniden başlatma veya çok-profilli devir senaryoları bu
çalışmayla kabul edilmiş sayılmaz.

`scripts/qa/native_credential_gateway.py`, mevcut AF21 gerçek Gateway
kabul düzeneğini kullanır. Gateway, Dream, broker, SDK ve kaynak kilitleri
bu iş için yeniden yazılmadı. Yeni değişiklikler yalnız başlatma politikası,
özel soket dizini, dört senaryo seçimi ve çıktı kontrolleridir.

## Kabul kapsamı

İlk başarılı korumalı koşuda gerçek Hermes Gateway, gerçek SessionAuthority,
üretimdeki değiştirilmemiş aiohttp broker ve D1 → D2A → D2B1 → D2B2 zinciri
birlikte çalıştı. Model sağlayıcısı yalnız programlanmış localhost yanıtları
üretir. 8/12 → 12/12 skoru bu programlanmış yanıtların sonucudur;
gerçek model öğrenmesi veya bağımsız genelleme kanıtı değildir.

Son kaynak sürümü için dört ayrı kabul senaryosu yürütülür:

| Senaryo | Beklenen sağlayıcı istek/yanıtı | Beklenen değerlendirme durumu |
|---|---|---|
| Normal | 4 / 4 | completed; iki deneme sonucu mevcut |
| Bütçe sınırı | 3 / 3 | unknown; ilave istek gönderilmez |
| Dersli yanıt bağlantı kesintisi | 4 / 3 | unknown; tamamlanmayan çift başarı sayılmaz |
| İnceleme kararı geri çekilmesi | 3 / 3 | unknown; dersli istek gönderilmez |

Her koşunun PASS sayılması için özgün test zincirine ek olarak dosya
koruması uygulanmış, broker başlangıç dosyasının okunması reddedilmiş,
dosyanın özgün baytları değişmemiş ve kontrol soketleri kaldırılmış olmalıdır.
Gerçek süreç kapanışları, broker soketi ve aktif istek sayısı AF21 makbuzunda
ayrıca doğrulanır. Canlı deneyler standart unittest toplamına eklenmez.

## Korumanın zayıflamadığını gösteren ayrı kontroller

`native_credential_self_metadata.py`, hazırlanmış yorumlayıcıyla yeni bir
kısıtlı süreç başlatır. Üç kendi-PID dosyası okunabilir; `/proc` dizini,
kendi ortamı/belleği, parent durumu/belleği ve gizli broker dosyası okunamaz.
İzinli kaynak, çalışma dosyası ve SQLite işlemleri çalışır. `no_new_privs`
açıktır ve kapatılamaz. Yeni exec alt süreci gizli dosyayı veya kendi
farklı PID'sinin metaverisini okuyamaz. On altı kontrol tek Linux deneyidir.

Özgün `native_credential_guard.py` de değişmeden yeniden çalıştırılır:
13 erişim kontrolü ve önceden açık gizli dosya, soket stdio, sabit bağlantı
ile gelen üç başlangıç reddi. Bunlar ayrı test kimlikleri gibi sayılmaz.

`tests/test_credential_startup.py` içindeki 12 yeni çevrimdışı test,
isteğe bağlı alanın tür/yol/kimlik sınırlarını ve geriye uyumluluğunu sınar.
26 eski testle dar seçim 38'dir; 12 yeni test tam toplamın içinde bir kez sayılır.

## Yeniden çalıştırma ve veri güvenliği

Bu WSL ortamında korumalı Gateway kodunu doğrudan `/mnt/c` üzerinden
çalıştırma. Önce `packages`, `scripts`, `config` ve `sources.lock.json`
altındaki gerekli kaynakları, yeni ve özel bir Linux dizinine baytları
koruyarak al; her dosyayı işin kaynak manifestiyle doğrula. Ham vendor
kaynağını veya kullanıcı profillerini bu kopyaya ekleme. Önceki hazırlanmış
Hermes/Python/Node ortamı kendi sabitlenmiş yolunda kullanılır.

Snapshot içinden, her defasında kullanılmamış bir koşu kimliğiyle:

```text
<prepared-python> -B scripts/qa/native_credential_gateway.py --run-id <new-id> --scenario normal
```

Diğer senaryolar: `budget-limit`, `candidate-disconnect`, `review-revoked`.
Makbuz dosyaları yeni olmalıdır. Eski başarısız kayıtları değiştirme veya
mevcut özel çalışma dizinini silerek aynı koşuyu tekrarlama.

Kaynak/kanıt rehberi: `evidence/d3b-startup-b71e/`.
`source-freeze-final.json` test edilen Windows kaynaklarını;
`linux-snapshot-final.json` gerçekten çalıştırılan Linux kopyasını;
`native-suite-final.json` dört canlı koşuyu;
`self-metadata-final.json` ve `primitive-final.json` kernel deneylerini;
`full-standard-final.json` tam unittest sonucunu ayrı saklar.
Tam test ve Git/CI sonuçları yalnız gerçek makbuzları görüldükten sonra kapatılır.

## Hâlâ açık olanlar

Bu kabul yalnız dosya erişimi koruması ve gerçek Gateway birlikteliğidir.
Ağ izolasyonu dalıyla ortak çalıştırma bu turda yapılmadı. Ayrı host UID,
her türlü Unix-socket veya metadata erişimine karşı tam engelleme,
Gateway'in kendi bütçe deposuna kötücül yazmasına karşı bağımsız otorite,
Docker araçlarıyla birleşik yol ve süreçler arası devir/yeniden başlatma ayrı işlerdir.
Kernel veya yetkili host ele geçirilmesine karşı bir anahtar kasası değildir.

Gerçek harici model, fiyat/token sözleşmesi, doğrulanmış öğrenme,
otomatik aktif hafıza/beceri terfisi ve `main` birleşimi bu çalışmanın dışında kalır.
Önce dosya ve ağ katmanlarını aynı gerçek Gateway koşusunda birlikte kabul et.

## Son kabul — 2026-10-18T15:57:54.402732+03:00

Dört korumalı gerçek Gateway senaryosu **4/4 PASS**: normal 4/4 HTTP,
bütçe sınırı 3/3, bağlantı kesintisi 4/3, inceleme iptali 3/3. Tümünde
korumalı broker dosyası değişmedi, kontrol/broker soketleri kaldırıldı,
Gateway ve broker temiz kapandı. 16 yeni kernel kontrolü ve eski 13+3
kontrol ayrı başarılı deneylerdir. 38 dar politika testi ve tam
**1897/1897 unittest PASS**, exit0/skip0; yeni12 tam toplamın içindedir.
268 ölçülen kaynak dosyası değişmedi; statik kapı PASS. Gerçek model
yoktur; ağ katmanıyla birleşik kabul ve tam D3B hâlâ açık.
