# REF-PI-001 — gerçek Pi döngüsü, araç ve HTTP sınırı

Tarih: 15 Ekim 2026. Durum: **DIRECT-CORE PROBE PASS / MOTOR DEĞİŞİMİ ONAYI DEĞİL**.
Dal: `alaz/ref-pi-001`. Başlangıç commit'i `3bf5305f9cadab584429ca4d97a941f394c0522f`.
Pi kaynak commit'i: `b06c1f2cf1dea6af8748ddeee18c23587d2cb7c6`.

## Çalıştırılan gerçek zincir

Pi'nin `Agent` kurucusu → kendi konuşma/araç döngüsü → kendi `read` aracı →
`pi-ai` OpenAI-compatible HTTP sağlayıcısı → yalnız 127.0.0.1 üzerinde çalışan
betiklenmiş model yanıtı. Ajan, araç, şema doğrulama ve HTTP/SSE ayrıştırma
kodları taklit edilmedi. Sadece modelin yanıtları kontrollü test verisi.

Kaynakta bulunan `source-resolver.ts` ön yüklenerek tam sabit kaynak ağacındaki
TypeScript dosyaları çalıştırıldı. Pi'nin Agent döngüsü yeniden yazılmadı veya
patch edilmedi. Tam Coding-agent SDK, TUI ve Durable başlatılmadı.

Her senaryo yeni bir çalışma dizini, profil ve tahmin edilemez dosya işareti
kullanır. Dosya içeriği modelin ikinci HTTP isteğindeki GERÇEK araç sonucunda
görülmeden başarı kabul edilmez. API anahtarı, proxy, NODE_OPTIONS ve kişisel
Pi/Hermes/OpenClaw profilleri süreç ortamına aktarılmaz. Kontrol edilen dosya
uygulama projesine veya kullanıcı verilerine ait değildir.

## On bir bağımsız senaryo

| Senaryo | Sunucuya ulaşan HTTP isteği | Beklenen ve gözlenen sonuç |
|---|---:|---|
| file-read | 2 | Yerleşik read bir kez çalışır; dosya işareti araç sonucu üzerinden döner; stop. |
| missing-file | 2 | Dosya okuma hata sonucu; READ_FAILED. Turun stop ile bitmesi araç başarısı sayılmaz. |
| cancelled-model | 1 | Yanıt beklerken gerçek Agent.abort; aborted, araç çalışmaz. |
| timeout-model | 1 | Test denetleyicisinin süresi dolunca Agent.abort; aborted. Bu, tüm araçlar için yerleşik zaman bütçesi iddiası değildir. |
| budget-stop | 1 | Bir okumadan sonraki ikinci model isteği gönderilmeden engellenir; error, başarılı tamamlanma değil. |
| retry-cap | 1 | 503 sonrası sağlayıcının yeniden denemesi gönderim sayacını aşamaz; ikinci HTTP isteği sunucuya ulaşmaz. |
| truncated-stream | 1 | finish_reason olmadan kapanan SSE başarılı sayılmaz; error. |
| model-switch | 3 | Aynı süreçte ikinci model kimliğine geçilir; mevcut araç sonucu tekrar kullanılır, ikinci dosya okuması yok. |
| event-barrier | 2 | agent_end dinleyicisi bitmeden prompt/waitForIdle bitmez; sonra durum temizlenir. |
| permission-denied | 2 | Testin beforeToolCall politikası okumayı reddeder; hata sonucu, başarılı okuma yok. |
| concurrent-prompt | 2 | Aynı Agent üzerindeki ikinci eşzamanlı prompt reddedilir; fazladan iş yok. |

Bütün senaryolarda sunucu ve bağlantıların kapanması ayrıca doğrulanır. Bekleyen
araç kümesi boş ve Agent idle olmalıdır. PASS sayısı farklı senaryoların sayısıdır;
aynı deneyin yeniden çalıştırılması yeni özellik/test sayısı diye toplanmaz.

## Eklediğimiz küçük parça: HTTP gönderim sayacı

`packages/hybrid-runtime/provider-request-gate.mjs`, Pi'nin desteklediği `fetch`
seçeneğine verilen AlazHarness bileşenidir. Sabit loopback hedef ve POST dışında
istek göndermez; yönlendirme takip etmez. Kontenjanı await öncesinde ayırır;
böylece eşzamanlı çağrılar limiti aşamaz. Belirsiz ağ hatası, abort sonrası
belirsiz etki veya 503 cevabı kontenjanı geri vermez. close yeni çağrıları kapatır;
zaten gönderilmiş isteği geri almış sayılmaz.

Bu **Pi'nin yerleşik para limiti değildir**. Yalnız bu fetch kapısından geçen
HTTP istekleri için bir üst sınırdır. Token/para muhasebesi, diğer sağlayıcılar,
WebSocket, başka süreçler, yardımcı çağrılar ve kalıcı bütçe kaydı ayrıca
uygulanmalı ve test edilmeli. Şimdilik üretim Hermes/OpenClaw akışına eklenmedi.
İzin hook'u ve loopback hedef listesi işletim sistemi sandbox'ı değildir.

## Hermes ile karşılaştırmanın sınırı

Önceki `evidence/hyb-003/native-file-read.json` kaydındaki Hermes turu da gerçek
motor + gerçek dosya aracı + iki yerel model isteğiydi. Bu aynı temel davranışın
iki kaynakta da kurulabildiğini gösteriyor. Pi burada yalnız bir read aracıyla,
Hermes ise farklı yapılandırılmış dosya araç setiyle çalıştı. Protokol ayrıntıları,
başlangıç işleri ve dil/runtime farklıdır; sürelerden performans üstünlüğü çıkarmıyoruz.

Hermes max_iterations=1 testi ek özet isteğine izin verdi. Pi deneyindeki sert
HTTP sınırını ise BİZİM fetch kapımız sağladı. Bunu Pi'nin doğal olarak daha ucuz
veya Hermes'in başarısız olduğu şeklinde sunmuyoruz. Her iki motorda aynı gönderim
ve maliyet muhasebesi sözleşmesinin uygulanması sonraki karşılaştırmadır.
Model-switch yalnız aynı betiklenmiş HTTP sağlayıcısındaki iki model kimliğidir;
gerçek model aileleri arası taşınabilirlik, ağırlık öğrenmesi veya yeni oturumda
kalıcı hafıza kullanımı kanıtlanmadı.

## Tekrarlanabilir hazırlık

Referans klon: varsayılan çalışma alanı altındaki
`scratch/research-sources/20261015-pi-opencode-46cc/pi`.
`prepare_native_pi.py` varsayılan olarak yalnız plan gösterir. `--apply` ile temiz
referansın sabit commit'ini yeni bir dizine git archive üzerinden açar ve
`npm ci --ignore-scripts --omit=dev` çalıştırır. Model veya ajan başlatmaz.
Ayrı npm user/global config, cache ve home kullanır; mevcut klasörün üstüne yazmaz.
Yaşam döngüsü kurulum betikleri çalıştırılmaz. İlk hazırlıkta 120 bağımlılık
paketi kuruldu; referans kaynak ve ürünün iki submodule pini değişmedi.

Örnek, bu Git çalışma ağacından:

```powershell
python -B scripts/prepare_native_pi.py --reference-source C:\Antigravity\AlazHarness\scratch\research-sources\20261015-pi-opencode-46cc\pi --output C:\Antigravity\AlazHarness\runtime\pi-new
# Gerçek bağımlılık kurulumu için aynı komuta --apply eklenir.
python -B scripts/run_native_pi_probe.py --prepared-root C:\Antigravity\AlazHarness\runtime\ref-pi-001-4eb7 --output C:\Antigravity\AlazHarness\runtime\pi-native-new
```

Node24+ ve npm gerekir. Her çıktı dizini yeni olmalıdır. Hazırlanan 1922 Pi dosyası
tek tek hash ile doğrulanır; manifestin de repo içindeki sabitlenmiş özeti kontrol
edilir. Bu, kurulmuş bütün transitif bağımlılıkların ayrı bir güvenlik denetimi
anlamına gelmez; npm lock bütünlüğüyle kaynak doğrulama farklı kapsamdır.

## Test katmanları ve düzeltmeler

Standart test paketi: 128 mevcut + 26 yeni = **154**. Yeni 16 Node senaryosu HTTP
kapısını, 10 Python testi başlatıcı/manifest/rapor sınırlarını sınar. Bu paket
Pi bağımlılıklarını indirmez ve native senaryoları çalıştırmaz; mevcut alaz-server
CI bu katmanı aynı kaynak sınırlarıyla çalıştırır. Native senaryoların kanıtı
ayrı rapordur, Windows üzerinde elde edildi.

İlk hazırlık betiği, aynı kaynak dosyalarını farklı JSON satır sonuyla kaydedince
fail-closed durdu; 1922 dosyanın tamamı eşit bulundu. Manifest hash'i sıralanmış
kanonik JSON içeriğine bağlandı; hiçbir dosya hash kontrolü kaldırılmadı ve bunun
regresyon testi eklendi. İlk kök test denemesinde eski on dosyalık sözdizimi listesi
yeni dosyayı reddetti; tüm eski kontroller korunarak üç yeni modülle on üçe genişletildi.
İlk başarısız test günlüğü de saklandı. Keşif amaçlı ilk native çalıştırmanın
socket kapanışını henüz beklemeyen raporu nihai kabul kaydı olarak kullanılmadı;
kabul sürümü bütün socket close olaylarını bekler.

## Karar ve sıradaki sınır

Pi doğrudan çekirdek adayı artık sadece belge üzerinden değil, bu sınırlı gerçek
çalıştırmayla değerlendirilmiş durumda. Tam motor değişimi veya M1 kapanışı yok.
REF-PI-002: Pi Durable kabul/kayıt/yeniden başlatma, aynı anahtarla farklı içerik,
belirsiz yan etki ve iptal edilmiş bekleyici durumları. REF-OC-001: OpenCode izin ve
olay akışı. Bu turda OpenCode kodu çalıştırılmadı. Tam OpenClaw/Hermes Gateway
zinciri, parasal bütçe, işletim sistemi izolasyonu ve M2 otonomi hâlâ açık.

Kaynak girişleri (aynı Pi commit'i): `packages/agent/src/agent.ts`,
`packages/agent/src/agent-loop.ts`, `packages/coding-agent/src/core/tools/read.ts`,
`packages/ai/src/api/openai-completions.ts`,
`packages/coding-agent/src/experimental/source-resolver.ts`.
Kanıtlar: `evidence/ref-pi-001/`; çalıştırma pini: `config/pi-native-probe.lock.json`.

## Temiz ortamda tekrar sonucu

Paketlenen prepare_native_pi.py --apply yeni bir dizinde başarıyla çalıştı.
Bu ikinci bağımsız kurulumda on bir native senaryonun tamamı yeniden geçti;
bütün soketler kapandı ve 1922 kaynak dosyası tekrar doğrulandı.
`native-reproduced.json` ve `preparation-reproduced.json` nihai tekrar kanıtıdır.
Bu tekrar ayrı özellik/test sayısı olarak toplamı artırmaz.
