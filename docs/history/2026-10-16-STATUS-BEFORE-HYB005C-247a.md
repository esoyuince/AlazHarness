# AlazHarness — status

Son güncelleme: 16 Ekim 2026. Devam etmeden önce canlı Git dalı, HEAD, çalışma
ağacı ve aynı commit'in CI sonucunu yeniden doğrula. Ana kayıt bu dosyadır.

## Güncel nokta

**HYB-005B dar yerel yürütme/bütçe paketi yayımlandı; kodun aynı-SHA CI sonucu başarılı.** Genel HYB-005, tam M1 ve otonomi M2 açık.

Aktif dal: `alaz/hyb-005b-execution-0d37`.
Aktif çalışma ağacı: `C:\Antigravity\AlazHarness\scratch\worktrees\main-6f88`.
Başlangıç commit'i: `30b205fa271d40956f02090896afdd1878377f57`.
Bu teslimin uygulama ve yayın sahibi: 3156. Önceki bağımsız QA3193/3156 ile
uygulama0d37/3723 kayıtları tarihsel kapsamlarını korur. Bu turdaki uygulama
ve kontroller aynı yazarın çalışmasıdır; ayrı bağımsız inceleme diye sunulmaz.

Varsayılan kök `C:\Antigravity\AlazHarness` eski korunmuş kirli daldadır;
geliştirme orada yapılmaz. Kökteki status.md yalnız kontrollü erişim kopyasıdır.
Main bu feature paketine ilerletilmedi; son ortak taban b8ff44f olarak korunuyor.

## Yapılanlar

ExecutionLedger, Hermes'in mevcut state_meta yazma sahibiyle sağlayıcı isteğinden
ÖNCE çağrı/token/microUSD risk rezervasyonu tutar. Hata, kayıp yanıt, bilinmeyen
usage veya yeniden açılış otomatik iade oluşturmaz. İkinci DB/kuyruk/motor yok.
ExecutionBoundary aynı native HTTP uygulamasında tek literal-loopback sağlayıcı
ve tek açık model için çalışır; dosya araçları native registry üzerinden korunur.
Yalnız açık allowlistteki düz .txt dosyaları gerçek Hermes read_file ile okunur.
Write/patch/search dar kapsamda reddedilir. requireExecution istemci modu yoksa
veya kapı hazır değilse host-only moda otomatik dönüş yapmaz.

QA-C01 ürüne uygulandı: başlangıç execution ayarlarının değişmez özeti güncel
native PluginContext ayarıyla eşleşmeden readiness/ledger erişimi yok. Bütçe
azaltılması, allowlistin kaldırılması, provider/key değişimi veya eksik ayarlar
reddedilir. Gerçek araç ledger yolu da yeniden kontrol eder. Önce4PASS/4FAIL olan
aynı8 test artık8PASS; ek6 final-boundary testi PASS. İlk FAIL kayıtları korundu.

Önceki kind/outcome, yanlış model ve çelişkili SSE kullanım bulguları da korunmuş
negatif testlerle kapanmıştır. Tüm değişiklikler mevcut kaynak pinlerini korur.

## Doğrulamalar — sayılar ayrı kapsamlar

- Tam yerel standart discovery: **881/881 PASS**, exit0, skip0;169 ölçülen
  script/test/paket/konfigürasyon dosyasında drift0. full-validation.json ve
  full-unittest.txt; bu sayı native Gateway koşularını içermez.
- Son ürün koduyla **7 native bütçe/araç senaryosu** kendi dar beklentilerini
  sağladı.6 senaryo ayrıca strict outcome/ret teyidinden geçti. Iteration-limit
  summary bir başarılı görev değildir; aşağıdaki ayrı bulgu geçerlidir.
- Normal iş:2provider/1read; aynı profilde yeni epoch ile clean reopen, değişmeyen
  sonuç ve bütçe. İzin geri çekme: gerçek capabilities503/provider metadata403,
  yeni rezervasyon/model0; yalnız TEST profili restore edilip tekrar açıldı.
- Provider-limit:1upstream istek/1read; ikinci istek provider_attempt_limit.
  Tool-limit:read0 ve gerçek ret. Denied-write:hedef dosya oluşmadı.
  SDK-retry-limit:gerçek native auxiliary factory+SDK tek invoke; ikinci fiziksel
  deneme bütçe kapısında durdu,1upstream/0admission. Unknown-price:0iş/0rezervasyon/0model.
- Toplam8 final Gateway süreç yaşamı normal kapandı; finalde zorla sonlandırma,
  kod değişimi, fixture hatası veya engellenmiş dış ağ girişimi yok.
- Ayrı opt-in gerçek aiohttp bileşen matrisi: **27/27 PASS**, sentetik owner/config/
  registry portları; tam Gateway ve881 standart testin parçası değildir.

Kanıt kökü: `evidence/hyb-005b-close-3156/`. Kaynak+process+SQLite teyitleri
final-native-suite.json, native-<senaryo>.json, normal-store-corroboration.json;
HTTP matrisi http-final-matrix.json; custody-final.json. Read-only teyitler yeni
native koşu sayılmaz. Gerçek model çıkarımı, ücretli çağrı ve yeni kurulum yok.

## Özet görevi ve kullanım görünümü — açık kalan ayrım

Tur sınırı nedeniyle özet dönen native iş API'de failed, admission kaydında
terminal/completed. Metin gerçekten saklı, fakat strict başarılı görev kontrolü
FAIL verdi; assertion veya ham kayıt değiştirilmedi. Native API kaynak kodu
incomplete/iteration-limit işlerini özellikle failed olarak sınıflandırıyor.

Aynı özetin iki fiziksel çağrısı execution ledger'da240girdi/40çıktı token,
Gateway aggregate'inde120/20 olarak göründü. Her iki tam risk rezervasyonu korunur;
bütçe denetimi küçük aggregate'e dayanmaz. final-native-suite.json bu sonucu
ITERATION_LIMIT_SUMMARY_BUDGET_CORROBORATED_NOT_TASK_SUCCESS olarak ayırır;
summary-strict-outcome.json başarısız strict beklentiyi aynen korur.

## Sınırlar ve kesin sonraki iş

**HYB-005C:** host görünümünde fiziksel usage, ayrılmış risk bütçesi, native rapor
ve görevin tamamlanma durumunu ayrı göstermek; özet/partial/limit senaryolarını
aynı kanıta bağlamak. Ardından credential/egress izolasyonu ve gerçek sağlayıcı
model/tarife/token sınırı kabulü. Mevcut operatör-bearer güven modelini ajanın
kendi izinleriyle karıştırma. HYB-006 hafıza/beceri transferi ve gerçek model M1
kabulü henüz yapılmadı; otonom scheduler açılmayacak.

Fixture fiyatı gerçek fatura veya kesin tokenizer kanıtı değildir. Tek yerel
chat-completions/read-only alt küme; global OS sandbox, bütün auxiliary yollar,
remote HTTPS, low-latency stream/cancel, TOCTOU ve irreversible write kabulü yok.
Yeni deneyler explicit180s ready sınırı/SDK-class preload ile koştu; legacy70s
cold-start performansı geçti denmez. Eski70s timeout/crash/drift/blocked-network
kayıtları evidence/hyb-005b ve eski QA dizinlerinde korunur.

## Belgeler ve tarihçe

Ana rapor: docs/HYB-005B-EXECUTION-GATE.md. Önceki incelemeler:
docs/research/HYB-005B-QA3193.md, HYB-005B-QA3156.md,
HYB-005B-CONTINUATION-3723.md. CI kapsamı docs/CI.md.
Önceki tam durum günlüğü:
`docs/history/2026-10-16-STATUS-BEFORE-HYB005B-DELIVERY-3156.md`.
69 başlangıç dosyası runtime/hyb005b-close-3156/before altında hashli korundu;
32 eski kök dosya ve4upstream kaynak ağacında değişiklik yok.

### 16 Ekim 2026 — yerel teslim kapanışı

C01 gerçek üründe kapandı.881standart/27HTTP PASS;7native dar beklenti,6strict
outcome teyidi ve1eksik özet işi ayrımı yukarıda. Aynı kaynak seti Git/CI için
hazırlanıyor. Commit/push/aynı-SHA CI tamamlanmadan yayın başarılı sayılmaz.

### Bağımsız QA545b bütünleşmesi ve özet anlamı

Ayrı QA545b dosyaları stage edilmiş bulundu; üzerine yazılmadan okundu.12 yeni
checkpoint testi zaten881 standart testin içindeydi, hash eşitliği doğrulandı.
Bağımsız881/881 koşu da PASS; sonuç toplamları iki katına çıkarılmaz. Rapor
HYB-005B-QA545b.md ve evidence/hyb-005b-qa545b aynı teslimde korunur.

Özetin canonical terminal RESULT kaydı completed=false ve max_iterations_reached(1/1)
diyor. Mevcut LocalRecoveryInspector sonucu doğrulayıp outcome=failed,
taskSucceeded=false, retryAllowed=false döndürüyor. Dolayısıyla admission
completed alanını görev başarısı sayan strict beklenti yanlıştı; mevcut recovery
inspector hatası veya native bozulma kanıtlanmadı. Eski strict FAIL gizlenmedi.
Kalan gerçek ayrım physical usage240/40 ile native aggregate120/20: HYB-005C
bunu görünür kılıp mevcut doğru inspector semantiğini kullanacak.

### 2026-10-16T03:28:27.009640+03:00 — kod yayımlandı, CI sonucu bekleniyor

Kod commit: `ca121ce036855b83f3e39735cc9d78aae96f70b6`. Mevcut feature dalına
push başarılı; yerel/remote eşit, o kontrol anında çalışma ağacı temiz.
GitHub alaz/local-ci şu an pending; eski commit yeşili aktarılmıyor.
169 ölçülen kod/config dosyası881 PASS koşusuyla aynı. Tarihsel unified-diff
evidence dosyasının zorunlu tek-space context satırı için yalnız o dosyaya
blank-at-eol niteliği verildi; eski patch byte/hashleri korundu, ürün koduna
whitespace muafiyeti yok. Commit110 dosyayı (kod, önceki/final kanıtlar, tarihçe)
içeriyor; vendorlar ve main değişmedi. Bu günlük CI bitince sonuçla tamamlanır.

### 2026-10-16T03:29:46.683288+03:00 — yayın ve aynı-commit CI kapanışı

Kod `ca121ce036855b83f3e39735cc9d78aae96f70b6` GitHub feature dalında.
GitHub alaz/local-ci success bağımsız sorgulandı. Alaz-server artifactinde
sha==checkout_sha==aynı kod SHA,881/881 PASS,failed0/skipped0/suite_errors0,
status_delivery=posted doğrulandı. Kanıt evidence/hyb-005b-close-3156/code-ci.json.
Bu testler standart pakettir;7native Gateway/SDK senaryosu serverda tekrar
çalıştırılmadı.881 bağımsız local QA ve881server sayıları ayrı koşular, toplanmaz.

Kod yayını sonrası kontrol:yerel/remote eşit, yalnız bu durum kaydı değişiyordu;
canlı AlazHarness native/test süreci görülmedi. Bu son commit yalnız belge/CI
kanıtlarını günceller. Onun CI sonucu push sonrası ayrıca sorgulanır; kod SHA
yeşili yeni belge SHA için varsayılmaz. Main birleşimi yapılmadı. Kesin sonraki
iş HYB-005C usage/outcome görünümü; genel izolasyon, gerçek tarife ve M1/M2 açık.
