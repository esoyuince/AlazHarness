# R158A1 — Yerel görev kontrolü ve kayıp yanıt sorgusu

## Teslimatın kapsamı

P2'nin komut satırı kontrol katmanı ve istek kimliğinden çalışma kimliğine salt
okunur sorgu eklendi. Mevcut `HostGateClient`, `HermesRunsClient`, native
admission/result ve tek kullanımlık host intent korunur. Yeni kuyruk, model
döngüsü veya ikinci kalıcı sonuç deposu yoktur.

**Bu teslimat kaynak ve HTTP sözleşmesi kabulüdür. P2'nin tamamı, çalışan günlük
servis ve gerçek model kabulü açık kalır.** P1'in R156/R157 kurulumu değiştirilmedi;
R158 kodu o kurulumun kabulünü otomatik devralmaz. Başlangıç harness commit'i
`aba1e6af9242e7b4006bbd9f6244022549a52c61`; incelenen native kaynak
`d1516731308de8e87130dc68124e69aad35d6911`.

## Kullanıcıya açılan komutlar

Giriş: `node scripts/alaz_local.mjs`. Node 24, açık loopback `ALAZ_BASE_URL`
ve ortamdan verilen `ALAZ_API_TOKEN` gerekir. Aşağıdaki bağlı komutlar, bu
protokolü sunan ve ayrıca kabul edilmiş bir servis gerektirir; R158 böyle bir
servisi kurmaz veya başlatmaz.

| Komut | Davranış |
|---|---|
| `task --request-id <32hex> --model <model> --input <dosya veya ->` | Açık model/girdiyle mevcut intent ve dispatch yolunu bir kez kullanır. Execution boundary ve provider broker zorunludur. |
| `request --request-id <32hex>` | Yeni GET üzerinden özgün isteğin hangi retained native çalışmaya bağlandığını sorgular. Görev göndermez. |
| `status --run-id <run_32hex>` | Mevcut native çalışma durumunu ve kimlik alanlarını gösterir. |
| `watch --run-id <run_32hex>` | Mevcut çalışmayı HTTP GET ile izler. Süre aşımı veya Ctrl+C yalnız izlemeyi bırakır. |
| `result --run-id <run_32hex>` | Terminal yanıt ve admission kimlik üçlüsü varsa çıktıyı gösterir; başarısız veya yarım sonuç tamamlanmış yanıt sayılmaz. |
| `usage --run-id <run_32hex>` | Native çalışmanın bildirdiği token sayaçlarını kapsamıyla gösterir. Eksik/bozuk değer ve maliyet `null` kalır. |
| `cancel --run-id <run_32hex>` | Bir native stop isteğinden sonra aynı çalışmayı ayrıca izler; ACK terminal kanıt değildir. |
| `start`, `close` | `service_lifecycle_not_implemented`, exit 64. Servis etkisi yaratmaz. |

`watch` ve `cancel` için `--wait-ms` ve `--poll-ms`; bağlı komutlarda
`--request-timeout-ms` bulunur. Yardım çıktısı aralıkları listeler. Girdi UTF-8
ve en çok 65.536 bayttır; dosya veya stdin kullanılır. Kimlik bilgisi komut
argümanından alınmaz. CLI istek/sonuç dosyası yazmaz; özgün request ID kullanıcıda
kalmalıdır. Anahtar, ham hata/stack veya keyfi sunucu alanları tanılara eklenmez.

Çıkış kodları: 0 kabul/gözlem, 2 başarısız veya tamamlanmamış iş sonucu,
3 belirsiz/eksik gözlem, 64 geçersiz girdi veya desteklenmeyen işlem.
`status` için 0, işin başarıyla tamamlandığı anlamına gelmez.

## Yanıt kaybolduğunda

Host intent tüketimi native admission'dan önce kalıcılaştırılır. Yanıtın
kaybolması hem native kabulden önce hem sonra olabilir. Aynı isteği yeniden
göndermek bu iki durumu ayırt etmez; mevcut consumed intent tekrar kullanılamaz.

Yeni `GET /alaz/host/v1/requests/{request_id}` bunun için dar bir sorgudur:

| Sınıflandırma | Gözlenen durum | Sonraki işlem |
|---|---|---|
| `not_found` | Bu kimlik doğrulama kapsamında retained intent yok | Özgün kimliği koru; yokluk yeniden gönderme yetkisi değildir. |
| `issued_not_dispatched` | Intent issued; native reservation yok | Salt durum bilgisi; otomatik dispatch yapılmaz. |
| `handoff_unresolved` | Intent consumed; native reservation yok veya önceden kaldırılmış | Durum belirsiz; yeniden gönderme yok. |
| `native_run_located` | Scope, özgün key, fingerprint ve retained run ID eşleşiyor | Dönen gerçek run ID ile ayrı native gözlem yapılabilir. |

Host request ID ile native run ID ayrı kimliklerdir; `run_<requestId>`
türetilmez. Sorgu `state.db` ve `runs_idempotency.db` dosyalarını `mode=ro`,
`query_only` ve kapalı trusted-schema ile okur. Mevcut namespace/envanter,
intent digest/scope/profile, epoch/instance, iki dosyanın kimliği ve okuma
öncesi/sonrası veri sürümleri doğrulanır. Çakışan veya eksik kanıt açık hata verir.

Sorgu native `lookup()` veya GET run handler'ını çağırmaz: bu yollar retention
budama veya eski owner projection'ını onarma gibi yazılar yapabilir. Yeni
sorguda intent issue/consume, bütçe başlatma, broker ping veya provider çağrısı
yoktur. Dönen kayıt yalnız locator'dır; `canonicalVerified=false`,
`snapshotOnly=true`, `retryAllowed=false`, `repairAllowed=false` kalır.
Retained ama süresi dolmuş bir locator daha sonraki native GET'in başarılı
olacağını garanti etmez. Mevcut `status/watch` GET'leri ayrı native gözlemdir;
onlar için tüm sunucu davranışının veritabanına yazmadığı iddia edilmez.

## İptal ve kullanım bilgisi

İptal kaydı `requestAttempted`, `requestAcknowledged`,
`requestMayHaveBeenAccepted` ve terminal gözlemi ayrı taşır.
`physicalWorkerTerminalVerified=false` kalır. İş iptal isteğiyle yarışırken
tamamlanırsa sonuç `completed` olarak korunur. Kayıp veya bozuk stop ACK'i,
istenen durdurmanın etkisiz kaldığı şeklinde yorumlanmaz; base istemcinin
başarılı HTTP yanıtından sonraki schema hatası da artık olası kabulü korur.

Mevcut katı recovery classifier, başlamadan iptal edilmiş ve
`execution_generation=null` dönen bir native işi `terminal_unverified`
olarak sınıflandırır. CLI `cancelled` durumunu gösterir ancak unresolved/exit 3
verir. Bu gözlenebilir sınır testlidir; tam native iptal kabulü R159'da ele alınır.

Token alanları native çalışma yanıtından gelir; fiziksel çağrı kapsamının
bağımsız doğrulaması değildir. Profil/principal rezervasyonları bir çalışmaya
mal edilmez. Bilinmeyen maliyet sıfır değildir ve rezervasyon fatura değildir.

## Günlük servis için bulunan somut sınır

P1'deki borrowed API adapter, `connect()` çağrısını
`borrowed_listener_not_qualified` ile reddediyor. Prepared kontrolleri her
aşamada listener/app/site alanlarının boş olmasını; descriptor'ın
`caller_prepared/active/draining/drained` ailesinde kalmasını istiyor.
Ordinary runner start/stop ve local runtime API start da caller-owned modunu
reddediyor. Mevcut host/execution boundary ise `ready` descriptor'ı bekliyor.

Ayrıca host-gate kaynak kilidi eski `eb75627` sınırına bağlı. Primary'deki
doğrudan bayt karşılaştırması `api_server.py` ve `api_server_runs.py` için iki
uyuşmazlık buldu. Execution kilidinin beş dosyası, retained manifest'in 756 ve
finite manifest'in 755 dosyası mevcut native baytlarla eşleşti. Bu kilitler
R158'de gevşetilmedi veya yalnız hash değiştirilerek uyumlu ilan edilmedi.

`agent/secret_sources/command.py` native repoda var, fakat iki ürün kaynak
manifest'inde yok. Gerçek provider upstream'i şu anda loopback `/v1` adresi
bekliyor; dış sağlayıcıya hazır doğrudan rota varsayılamaz.

[R159 servis planı](P2-BORROWED-SERVICE-R159A1-PLAN.md), yeni kuyruğa ihtiyaç
duymadan mevcut owner'a açık listener sahipliği ekleyecek bir sonraki pakettir.

## Doğrulama ve kanıt

- Yeni Linux kontrolleri: 25 SQLite/HTTP handler + 31 CLI/HTTP fixture testi,
  **56/56 PASS**. Mevcut ledger 36 ve host-client 17 regresyon kontrolü de geçti.
- HTTP/CLI sunucuları test fixture'ıdır; gerçek native servis veya model kabulü değildir.
- İlk Windows kontrolünde dokuz kaynak/test dosyası birlikte doğrulandı: **109 test,
  104 PASS, 5 skip, 0 hata**, 27,248 saniye, exit 0. Dört aiohttp handler testi
  bu Python ortamında bağımlılık olmadığı için, bir CLI sinyal testi POSIX
  gerektirdiği için atlandı; bu beş test Linux'ta geçti. Kesin sayım ve ham
  çıktılar `checks/windows-focused.json` ve `checks/windows-focused.txt` içindedir.
- Yerel static/discovery kapısı testleri çalıştırmaz; tam suite sonucu exact
  commit'in `alaz/local-ci` kaydıyla ayrıca doğrulanır.
- İlk kısıtlı Linux ortamında socket/thread uyanışı engellendi; izinli yerel
  test çalışmasında aynı kod geçti. Mevcut aiohttp string-AppKey uyarısı korunur.
- R158'de native runtime/kurulum, gerçek provider/model çağrısı ve prod dağıtımı yoktur.

### İlk tam CI bulguları ve düzeltme

İlk feature commit'i `cd596387f9f4fc03f02eeaf540e24a921792820e` üzerinde
tam suite gerçekten çalıştı: **4.032 test, 17 failure kaydı, 10 skip**, 263,358
saniye. `alaz/local-ci` sonucu FAILED idi ve main bu sonuçla ilerletilmedi.
Ham log, metadata ve özet `checks/ci-first-attempt*` dosyalarında korunur.

On altı failure kaydı, eski deneylerin kaynak kimliklerini değişmiş güncel
dosyalarla karşılaştırmasından geldi. Dört değişen mevcut ürün dosyasının
`aba1e6af9242e7b4006bbd9f6244022549a52c61` parent commit'indeki birebir
baytları arşivlendi. Yeni çözümleyici yalnız tam eski dosya adı/hash çifti için
sabit commit, yol, kapsam, boyut ve arşiv hash'ini doğrular. Güncel veya bilinmeyen
hash'ler canlı kaynak kontrolünde kalır; eksik/bozuk arşiv hata verir. Eski 11
receipt test modülü, beklenen hash'ler ve deney sonuçları değiştirilmedi.
Bu bağlantı geçmiş kanıtı korur; güncel native kabulü veya yeni bir deney değildir.

Diğer failure, 40 ms'lik izleme süresinde ilk GET'in mutlaka sunucuya ulaşacağını
varsayan testti. Ürün doğru biçimde tüm gözlem için süre sınırı uygular; işlemci
yükü altında istek ulaşmadan süre dolabilir. Fixture artık önce gerçek,
kimliği doğrulanmış bir durum sorgusunu tamamlar; aynı 40 ms sürede izleme
kesilmesini, `execution_timeout`, exit 3 ve hiç stop/dispatch olmamasını denetler.
Ürün zaman aşımı değiştirilmedi. Tamamlanmaya kadar gerçek çoklu GET izleme
senaryosu da korunur.

İlk arşiv düzeltmesiyle Windows'ta 118 testin 114'ü geçti, biri atlandı;
üç assertion daha ilerleyerek dördüncü dosyanın (`host-gate-client.mjs`) eski
kimliğini ortaya çıkardı. Bu ham sonuç `checks/windows-ci-repair-001.*` altında
korunur. Dört dosyanın tamamını kapsayan son Windows kontrolü **118 test,
117 PASS, 1 POSIX skip, 0 failure/error**, 22,299 saniye ve exit 0 ile geçti.
Ham sonuç `checks/windows-ci-repair-002.*`, bağımsız kaynak incelemesi
`ci-repair-review.json` içindedir. Altı yeni arşiv doğrulama testi eksik/bozuk
kayıt, yönlendirilmiş yol, değiştirilmiş baytlar ve güncel/bilinmeyen sürüm
durumlarını kapsar. Düzeltme ürün kodunu, native kilitleri veya kurulumu değiştirmez.

Kaynak incelemeleri ve başlangıç kaydı
[`evidence/p2-local-control-r158a1`](../evidence/p2-local-control-r158a1/) altındadır.
Son commit/push/CI/main ve korunan çalışma ağaçlarının doğrulaması, aktif R158
worktree'deki `scratch/r158a1-publication/final-publication.json` ile kaydedilir.
Git yayını servis dağıtımı değildir. P1 DONE; P2 IN PROGRESS; P3–P5/M1/prod OPEN.
