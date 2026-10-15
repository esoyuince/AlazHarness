# REF-OC-001 — OpenCode izin ve olay bileşenleri

15 Ekim 2026. Kaynak: `anomalyco/opencode`, commit
`3943b84ef00e83dbc3c48e6a92b02f0d88fb35f9` (incelenen paketler 2.0.29).
Taban: `b461d4c805c7291f91899edd0d2028c7e00dbf4b`.

**Seçilmiş bileşen karakterizasyonu: PASS — 35 senaryo × 2 ayrı süreç = 70/70.**
**Tam OpenCode uygulaması, HTTP yetkilendirmesi veya ürün benimsemesi: NOT ACCEPTED.**

## Ne gerçekten çalıştırıldı?

- `core/src/permission.ts` içindeki evaluate/merge ve izin servisinin gerçek
  davranış gövdesi; ask/assert/reply, bekleyen işler, close ve hata yolları.
- Gerçek `Wildcard.match` ve gerçek OpenCode şemaları/olay manifesti.
- `server/src/event-feed.ts` içindeki gerçek make/frame, Effect Queue/Stream,
  abone kapsamı, taşma ve kodlama hatası davranışı.
- HTTP izin işleyicisinden değişmeden seçilen `requireOwnedRequest` işlevi ve
  ilişkili hata yapıları; gerçek Permission servisine karşı çağrıldı.
- OpenCode bun.lock dosyasındaki aynı Effect 4.0.1 sürümü. npm paket bütünlük
  değeri bun.lock ile eşleştirildi; kilit config/opencode-probe altında.

**Kontrollü fixture olanlar:** Bus, Location, Agent, SessionStore,
PermissionSaved ve PluginHooks dış servisleri. Oturumlar, kurallar ve kayıtlı
onaylar bu deneyin bellek içi verileridir. Gerçek OpenCode veritabanı, Plugin
çalıştırıcısı, ağ sunucusu ve HTTP middleware zinciri başlatılmadı. Effect'in
kuyruğu, Deferred/Fiber ve Schema uygulamaları taklit edilmedi. Sonucu üreten
izin veya olay algoritması testte yeniden yazılmadı.

Çalıştırma hazırlığı kaynakların importlarını kontrollü projeksiyona bağlar.
Permission dosyasının ilk import bölümü değiştirilir, kalan davranış gövdesi
korunur. MakeLocationNode yalnız asli Layer'ın alınması için test bağlayıcısıdır;
tam bağımlılık grafiğini başlatmaz. Şemalarda göreli .js importları .ts adreslerine
çevrilir. `requireOwnedRequest` ve iki hata sınıfı kaynak satırlarından aynen
seçilir. Projection.json 94 kaynak girdisini ve 96 üretilen dosyayı hash ile
kaydeder; buna lisans ve iki fixture dosyası dahildir. Bu sayılar test sayısı değildir.

## İzin bulguları

| Kontrol | Gözlenen davranış / Alaz için sonuç |
|---|---|
| Varsayılan ve sıra | Eşleşme yoksa ask; son eşleşen kural geçerli. Session kuralları agent kurallarının üzerine gelebiliyor. |
| Açık ret | Bir resource için etkin yapılandırılmış deny varsa saved allow ve plugin bunu aşamıyor. |
| Kaynak listesi | Bazı kaynaklara izin yetmez: diğerinde ask veya deny sonucu korunuyor. Boş resources listesi doğrudan servis çağrısında allow olabiliyor. |
| Eksik oturum/agent | Eksik oturum açık hata; çözümlenemeyen agent normal kaynak listesinde deny. |
| Once | Bekleyen iş çözülür ve kaldırılır; ikinci yanıt NotFound olur, kalıcı onay oluşmaz. |
| Reject | Aynı session'ın bekleyen izin grubu reddedilir; diğer session beklemeye devam eder. Feedback ayrı typed hata yolundadır. |
| Always | Aynı proje içindeki başka bir session'ın uygun bekleyen işini de çözebilir. Sonradan deny eklenen iş otomatik açılmaz. |
| Session sahipliği | İşleyicinin sahiplik işlevi yanlış session/request eşleşmesini reddeder; doğru eşleşme izin yanıtına geçebilir. |
| İptal/kapatma/hata | Bekleyicinin kesilmesi pending kaydını temizler; close sonrası deny; Asked yayın hatası pending kalıntısı bırakmaz. |
| Yinelenen pending ID | Başka session ile aynı pending kimliği sessizce devralınmaz; açık hata. |

Bu davranışlar bütün OpenCode'da bir güvenlik açığı bulunduğu iddiası değildir.
Örneğin tam araç yolu resources listesini zaten oluşturuyor olabilir; burada o
araç yolu çalıştırılmadı. **Alaz'ın kendi sınırında kaynak listesinin boş olmaması,
gerçek işlemi kapsaması ve güvenilir host tarafından hazırlanması ayrıca gerekir.**

Wildcard testi `src/../secret` metninin `src/*` ile eşleştiğini gösterdi. Bu yalnız
metinsel bir eşleşmedir; dosya açılmadı. Eşleştirici symlink/realpath veya çalışma
alanından çıkışı çözmez; sandbox diye kullanılamaz. Windows'ta case-insensitive,
diğer platformlarda case-sensitive davranış kaynak tarafından seçiliyor.

Permission.reply çekirdeği requestID ile çalışır; session bağını kontrol eden
parça HTTP işleyicisindeki ayrı işlevdir. Sadece çekirdeği kopyalayıp HTTP guard'ının
otomatik geldiğini varsayamayız. Bu deney guard'ı programatik sınar; gerçek
HTTP route, kullanıcı kimliği, middleware ve ağdan gelen payload doğrulaması açık.

## Olay akışı bulguları

Gerçek frame biçimi `data: <JSON>\n\n`; içinde ayrı SSE `id:` satırı yok.
Tek yayın bir defa kodlanır ve bütün uygun abonelere aynı çerçeve verilir. İç
olaylar kapasiteyi tüketmeden elenir; FIFO sırası korunur. Varsayılan kapasite
4096; deterministik testte kapasite 1 ve 3 kullanıldı.

Yavaş abone dolunca yalnız onun akışı SubscriberOverflow ile başarısız olur;
hızlı abone üç olayı eksiksiz alır. Kodlama hatası bütün mevcut aboneleri kapatır,
fakat yeni abone daha sonraki sağlam olayı alabilir. Son scope kapandığında
upstream observer aboneliği bırakılır. Abone yokken olay kodlanmadan düşer.

**Yeniden bağlanma kayıpsız replay değildir:** önceki abone kapatıldı, arada bir
olay yayımlandı, sonra yeni abone açıldı; yeni abone yalnız sonraki canlı olayı
aldı. Bu sonuç `protocol/groups/event.ts:44–52` açıklamasıyla uyumludur. Hata veya
kopmada yetkili oturum/görev durumunun tekrar sorgulanması gerekir. Yeniden
bağlanma testi gerçek Effect aboneliği seviyesindedir; gerçek TCP kopması,
EventSource istemcisi veya reverse-proxy dayanıklılığı deneyi değildir.

## Hazırlık, sınırlar ve ilk hata

Bun veya tam OpenCode kurulmadı. Yalnız Effect, proje runtime dizininde sabit
npm lock ile `npm ci --ignore-scripts --no-audit --no-fund` kullanılarak kuruldu.
Kişisel npm ayarları/API anahtarları/proxy değişkenleri çocuğa taşınmadı. Global
Node/npm ve mevcut agent profilleri değiştirilmedi. Üretilen kaynaklarla Effect
JS/JSON ağacının hash'leri koşu öncesi/sonrası eşleşti. Model/ücretli çağrı sıfır.

İlk deneme Node'un strip-only TypeScript kipinde kaynak namespace'ini açamadı;
hiçbir bileşen senaryosu çalışmadı. Mevcut Node'un `--experimental-transform-types`
seçeneğiyle kaynak değiştirilmeden düzeltildi. İlk hata kaydı korunur; 70 kabul
koşusuna eklenmedi. Bu çalışma statik TypeScript typecheck veya tam upstream
build kabulü değildir. Dosya/profil ayrımı OS sandbox güvencesi değildir.

35 senaryo, iki fresh child process altında tekrarlandı; Effect servis scope'ları
her senaryoda yenilendi. Pozitif sayaç beyanı tek başına kabul edilmez: runner
35 ayrı beklenen isim, sıralama, PID/nonce, gerçek exit, claim sınırları ve
kaynak hash'lerini doğrular. 21 yeni offline test bu kabul/kurulum yardımcılarını
sınar; OpenCode koşularının yerine geçmez.

## Yeniden üretim

```powershell
cd C:\Antigravity\AlazHarness\scratch\worktrees\ref-pi-001-ac97
python -B scripts/prepare_opencode_components.py --source-workspace C:\Antigravity\AlazHarness --output C:\Antigravity\AlazHarness\runtime\oc-new-prepared
# Yukarıdaki varsayılan plan yazmaz/kurmaz. Kurulum için açık --apply gerekir.
python -B scripts/run_opencode_components.py --source-workspace C:\Antigravity\AlazHarness --prepared C:\Antigravity\AlazHarness\runtime\ref-oc-001-8ea1\qualified --output C:\Antigravity\AlazHarness\runtime\oc-new-run --repeats 2
python -B -m unittest discover -s tests -v
```

Mevcut hazırlanmış ortam qualified klasöründedir; output yeni olmalıdır. Standart
CI Effect kurmaz veya bu 70 bileşen koşusunu çalıştırmaz. `evidence/ref-oc-001/`
altında component-suite, projection, preparation, local-validation ve ilk hata
kayıtları bulunur. Tam commit'in sunucu CI sonucu yayın sonrası ayrıca okunur.

## Karar ve sonraki iş

Seçilmiş izin/olay davranışı incelendi; bütün OpenCode servisinin ürüne alınması
onaylanmadı. Tek M1 yürütücüsünü koruyan bileşen kararı
`docs/adr/0003-mvp-single-runtime.md` içindedir. Sıradaki geliştirme kapısı
HYB-003-GATEWAY: mevcut HermesRunsClient ile gerçek Hermes Gateway/SessionAuthority
sınırını, kontrollü modelle tek iş üzerinden bağlamak. OpenCode kaynak erişimi,
project-wide onay ve volatile akış sınırları HYB-005 tasarım girdisidir; uygulanmış
Alaz izin motoru veya yeniden bağlanma garantisi diye raporlanmaz.

## Ek bağımsız sınır denetimi

Aynı kaynak dosyalarını Node resolver ile doğrudan yükleyen ikinci bir test düzeneği
12 izin ve8 olay gözlemiyle eklendi; uygulama kodunu yeniden yazmaz. Gerçek
Permission/EventFeed gövdeleri ve Effect çalışır, dış servis portları yine fixture.
Kaynak ve Effect byte hash'leri kaydedilir. Bağımsız rapor
`REF-OC-001-INDEPENDENT-QA.md` ve `evidence/ref-oc-001-qa/` altında korunur.
Bunlar35 ana senaryonun tekrarlarıyla tek yeni test sayısında birleştirilmez.

Özellikle üç ek sözleşme ihtiyacı bulundu:

1. Ask çağrısına verilen `save` dizisi veya get ile dönen pending nesnesi bellekte
   değiştirilirse sonraki always kapsamı değişebiliyor. HTTP JSON nesnesinin uzaktan
   aynı belleği paylaşması gösterilmedi; programatik gömme sınırı için immutable
   anlık kopya ve dışarıya detached çıktı gerekir.
2. Bekleyen seçilmiş once onayı, kural sonradan deny olsa bile işi çözebiliyor.
   Diğer bekleyenlerin always ile otomatik onayında deny yeniden kontrol ediliyor.
   İnsan onayının açık override mı yoksa güncel yasağa tabi mi olduğu belirlenmeli;
   Alaz değiştirilemez host yasağını gerçek araç yürütme sınırında korumalıdır.
3. Açıkça kullanıcı tarafından seçilmiş izin IDsi tamamlandıktan sonra aynı session
   içinde başka içerikle yeniden kullanılabiliyor. Gecikmiş yanıtın yeni işe
   uygulanmaması için host benzersiz request-generation kimliği tutmalı. Bu sonuç
   otomatik üretilen IDlerin çakıştığı veya tam HTTP'de saldırı gösterildiği iddiası değil.

Volatile EventFeed sonucu, OpenCode'da hiç kalıcı olay sistemi olmadığı anlamına
 gelmez. Ayrı durable session-log API'si bulunuyor; bu deneyde yürütülmedi. Bizim
harness için mevcut yetkili iş durumunu veya ayrıca kabul edilmiş kalıcı günlüğü
sorgulamak gerekir. Kaçırılmış bildirim dış işlemi yeniden başlatma yetkisi vermez.
