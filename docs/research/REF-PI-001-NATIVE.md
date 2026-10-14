# REF-PI-001 — Gerçek Pi araç turu ve sınırlı kontrol deneyleri

Tarih: 15 Ekim 2026. Durum: **DAR YEREL DENEY PASS; MOTOR DEĞİŞİMİ KARARI YOK.**
Dal: `alaz/ref-pi-001-native-ac97`; temel: `3bf5305f9cadab584429ca4d97a941f394c0522f`.

## Ne çalıştırıldı?

Pi `earendil-works/pi` kaynağı `b06c1f2cf1dea6af8748ddeee18c23587d2cb7c6`
commit'inden ayrı, kaynak dosyaları değişmemiş bir çalışma kopyasına alındı.
Kendi `source-resolver.ts` yükleyicisi üzerinden gerçek `Agent`, gerçek
`openai-completions.stream` sağlayıcı ayrıştırıcısı ve yerleşik `createReadTool`
çalıştırıldı. Pi'nin model döngüsü veya dosya okuma işlemi taklit edilmedi.
Yalnız model servisinin cevapları yerel HTTP/SSE sunucusunda betiklendi.

Her denemede yeni bir dosyaya tahmin edilemez işaret ve Türkçe metin yazılıyor.
Normal sonuç ancak yerleşik read aracının gerçek çıktısı ikinci model isteğinde
görülürse üretilebiliyor. Pi'ye verilen ilk kullanıcı mesajında dosyanın rastgele
işareti yok. Genel shell, yazma, tarayıcı veya başka bir ajan aracı açılmıyor.
Dosya araçlarının çalışma dizini seçimi işletim sistemi sandbox'ı değildir.

## Sonuçlar — iki tekrar, 12/12 başarılı

| Senaryo | Gerçek gözlem | Kabulün sınırı |
|---|---|---|
| file-read | Bir native read sonucu; iki model HTTP isteği; işaret araçta ve finalde; stop | Gerçek model zekâsı değil, döngü/araç/transport işleyişi |
| missing-file | Native dosya bulunamadı hatası modele ulaştı; bir hata sonucu, iki istek | Test PASS, kullanıcı işi tamamlanmış değil |
| cancel-model | İstek başladıktan sonra Agent.abort; aborted; model bağlantısı kapandı; araç yok | Sadece model beklerken iptal; uzun shell/OS süreç iptali denenmedi |
| one-round | finishTurn ile araçtan sonra bitiş; bir istek/bir read; final yok | Bizim açık host hook'umuz; Pi'nin varsayılan bütçe politikası değil |
| request-cap | Gerçek sağlayıcı fetch sınırında ikinci istek reddedildi; sunucu bir istek aldı | Bu testteki tek sağlayıcı için istek adedi; token/para/genel sistem bütçesi değil |
| truncated-tool | length ile kesilen araç cevabı yürütülmeden hata sonucuna dönüştü; beforeToolCall sıfır | Belirli kesik-çıktı senaryosu; bütün bozuk yanıt türleri değil |

Her turdan sonra agent_end ve idle durumu ayrı gözlemlendi; bekleyen araç kalmadı.
Test sunucusu kapatıldı, başlatılan Node çocuğu sonlandı. Native makbuzlar
`evidence/ref-pi-001/native-suite.json` içinde, 12 turun tamamını içeriyor.
Model çıkarımı ve ücretli sağlayıcı çağrısı sıfır. Kaynak/helper varlığını PASS
saymıyoruz; burada bu entrypoint'ler gerçekten çalıştırıldı.

## Önemli bulgu: bütçe nedeni taşınmalı

Fetch sınırı ikinci isteği durdurduğu hâlde Pi'nin native sonuç metni genel
`Connection error.` oldu. Host sayacı nedenin bütçe olduğunu bildiği için ayrıca
`request_budget_exhausted` sonucu üretiyoruz; özgün `errorMessage` saklanıyor.
Bunu ağ arızası sanıp otomatik yeniden iş başlatmak bütçe mantığını bozar.
Bu eşleme ve eşzamanlı istek rezervasyonu model cevabına değil normal koda bağlı.
`requestGate` yönlendirmeleri izlemez; yalnız seçilmiş loopback POST uç noktasına
izin verir. Diğer çalışma yollarının veya bütün Node ağ erişiminin sandbox'ı değildir.

## Hermes ile dürüst karşılaştırma

| Özellik | Önceden doğrulanan Hermes | Bu turdaki Pi |
|---|---|---|
| Native kurucu/döngü | AIAgent | Düşük seviyeli Agent |
| Yerleşik dosya aracı | read_file | read / createReadTool |
| Pozitif tur | Bir araç sonucu, iki yerel model isteği | Aynı sayılar ve rastgele dosya işareti doğrulaması |
| Model transport'u | Betiklenmiş JSON tamamlanma cevabı | Betiklenmiş SSE, gerçek Pi sağlayıcı ayrıştırıcısı |
| Bir turda duruş | max_iterations=1 ayrıca özet çağrısı yapabiliyor | Host finishTurn=end ikinci isteği önleyebiliyor |
| Maliyet sınırı | Tur sınırı tek başına yeterli değil | Test-host fetch sayacı kanıtı var; genel para limiti hâlâ yok |

Bu iki farklı katmanın ve farklı kontrol ayarlarının karşılaştırmasıdır.
Hermes'i yavaş, Pi'yi daha akıllı veya daha ucuz ilan etmek için benchmark değil.
Pi coding-agent'in `createAgentSession`/SessionManager katmanı, kaynak keşfi,
kalıcı hafıza, otomatik sıkıştırma ve Durable bu deneyde çalıştırılmadı.
Hermes kıyasının kaynağı mevcut `evidence/hyb-003/native-file-read.json` ve
`native-budget-summary.json`; bunlar bu turda yeniden çalıştırılmış sayılmaz.

## Tekrar üretim

Varsayılan kaynak referansı `config/research-sources.lock.json` içinde kalıyor.
Hazırlık yalnız yeni `runtime` dizinine klonlar ve kilitli `npm ci --ignore-scripts`
çalıştırır. Global npm/Pi kurulumu veya kullanıcı profili değiştirilmez. İlk
hazırlık makbuzu: preparation.json. Pi kaynak deposundaki lifecycle scriptleri
çalıştırılmadı; paket arşivleri kilit dosyasından kuruldu. Bu güvenlik denetimi değildir.

```powershell
cd C:\Antigravity\AlazHarness\scratch\worktrees\ref-pi-001-ac97
# Önce plan; var olan çıktıya yazılmaz.
python -B scripts/prepare_native_pi.py --source-workspace C:\Antigravity\AlazHarness --output C:\Antigravity\AlazHarness\runtime\pi-new
# Kurulum için aynı komuta --apply eklenir.
# Bu çalışma sırasında hazırlanmış kaynakla yeni test çıktısı:
python -B scripts/run_native_pi_suite.py --source-workspace C:\Antigravity\AlazHarness --prepared C:\Antigravity\AlazHarness\runtime\pi-ref001-ac97 --output C:\Antigravity\AlazHarness\runtime\pi-new-test --repeats 2
```

Tek senaryo için `run_native_pi_probe.py` aynı argümanları ve `--scenario` alır.
Her çıktı dizini yeni olmalı. Plan modu dosya oluşturmamalı; kaynak pin/dirty kontrolü
ve çıktı yolu kontrolleri unit testlerde var. API anahtarları, proxy, NODE_OPTIONS
ve kullanıcı npm kimlik bilgileri çocuğa geçirilmez. Testte yeni HOME kullanılır.

## CI kapsamı ve sonraki karar

Mevcut standart CI'ye yalnız hazırlık/izolasyon/host-kontrat unit testleri eklenir.
Pi native testi yerel Windows + Node24.19 kanıtıdır; alaz-server CI'nin Pi'yi de
kurup çalıştırdığı söylenmez. CI yeni bağımlılık indirmez ve model servisi kullanmaz.

Bu sonuç Pi Agent core'u **uygulanabilir aday** yapıyor; otomatik olarak Hermes'in
yerine geçirmiyor. İki motoru aynı konuşmanın çift yazarı yapmıyoruz. Sıradaki
REF-PI-002: Pi Durable'da kabul/yan etki/kayıt arasındaki kesintiler ve requestId
çakışmasını ölçmek. OpenCode REF-OC-001 izin/olay incelemesi hâlâ bekliyor.
Tam OpenClaw girişi, Hermes Gateway, kalıcılık, kapsamlı araç izolasyonu, para
bütçesi, beceri transferi, gerçek model ve M1/M2 kabul kapıları açık kalıyor.
