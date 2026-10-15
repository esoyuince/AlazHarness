# HYB-004 — Gerçek Gateway kesinti ve yeniden açılış

15 Ekim 2026. Dal: `alaz/hyb-004-recovery-208f`; taban
`e6f596c2e73ba1db3b617b74f40423a531237cda`.
Durum: ölçülen kesinti davranışının karakterizasyonu; genel kurtarma/ürün kabulü değil.
Kesin koşu sayıları `evidence/hyb-004/native-suite.json` içinde tutulur.

## Gerçek ve kontrollü parçalar

Mevcut HermesRunsClient, değiştirilmemiş native Gateway başlangıcı ve kapanışı,
SessionAuthority, APIServerAdapter, AIAgent ve yerleşik read_file kullanılır.
Model cevapları yalnız yerel betiklenmiş HTTP sağlayıcısından gelir. Rastgele
işaret ilk kullanıcı girdisinde bulunmaz; yalnız yeni deney dosyasında vardır.
Gerçek model çıkarımı ve ücretli sağlayıcı çağrısı yoktur. Ürün adaptörü ve vendor
kaynakları değiştirilmez; ikinci oturum deposu ya da alternatif yürütücü eklenmez.

Her deney bir profili iki ayrı native süreçte açar. İlk sürece OS ancestry ve
elde tutulan handle ile erişilir; başarılı düzgün kapanış yerine gerçekten
TerminateProcess uygulanır. Hem native sürecin hem venv başlatıcısının bittiği
kanıtlanır. İkinci açılış aynı config/API anahtarı/profile/port ile yapılır, yeni
nonce, native instance_id ve artan runtime epoch doğrulanır. İkinci süreç native
stop üzerinden temiz kapatılır. Bu bir elektrik kesintisi veya WAL testi değildir.

## Beş ayrı kayıt sınırı

| Deney adı | Kesinti noktası | Beklenen ve ölçülen ayrım |
|---|---|---|
| completed | Native sonuç tamamlanmış ve istemci tarafından okunmuş | Aynı run/admission/sonuç/usage korunur; yeni model veya read_file çağrısı yok. |
| before-model | İLK MODEL YANITI bekleniyor; model HTTP isteği zaten gelmiş | started işi unknown olur;0 araç sonucu; kör yeniden yürütme yok. Adı, sıfır HTTP çağrısı anlamına gelmez. |
| after-tool | Gerçek read_file sonucu ikinci model isteğine taşınmış, son model yanıtı verilmemiş | Kayıtlı tek araç sonucu korunur; native iş unknown kalır; operatör gereksinimi vardır. |
| before-reserve | Idempotency reserve çağrısından hemen önce | İki depoda da iş yok; eski geçici run_id404. Deneyin açık aynı-key gönderimi yeni bir işi tek kez yürütür. |
| after-reserve | Reserve commit'i bitmiş, canonical admission yapılmamış |1reservation/0admission/0araç. Yeniden açılışta aynı-key replay interrupted döner, asıl iş oluşmaz. Bu açık ürün engelidir. |

Bütün yeniden gönderimler deneyin açık işlemleridir. HermesRunsClient'a otomatik
POST retry eklenmez. Son iki deneyde ilk kabul yanıtının202 olarak alındığı iddia
edilmez: TCP kapanınca istemci write_outcome_unknown durumunu korur. Değişmiş
payload ile aynı anahtar her durumda409 verir.

## Tam kesinti noktasının elde edilmesi

İlk üç deney native kodun davranışına dokunmaz; provider cevabı kontrollü bekler
veya tamamlanmış native sonuç gözlenir. Son iki deneyde sadece test çocuğunda
Python settrace kullanılır. Sabit kaynak dosyasının AST'sinde reserve çağrısı ve
hemen sonraki branch bulunur (bu pinde795 ve799). Trace ilgili tek istek anahtarı
ve source hash ile sınırlıdır; native method, return değeri veya SQLite verisi
değiştirilmez. Checkpoint dosyası yazıldıktan sonra native iş parçacığı bekler,
üst süreç yalnız sahip olduğu native süreci keser. Bu zamanlama enjeksiyonudur,
kaynak yaması veya normal üretim yürütme yolu değildir.

Ek QA5016 aynı iki-store boşluğunu tamamen ayrı yöntemle inceler: dış SQLite
bağlantısı canonical depoda BEGIN IMMEDIATE ile yazıyı bekletir; veri yazmadan
rollback eder. Native source/trace değiştirmeden reservation gözlenir ve süreç
kesilir. Ana line-checkpoint sonucu ile bu kanıt aynı testmiş gibi toplanmaz.
Ayrıntı `docs/research/HYB-004-INDEPENDENT-QA.md`.

## Kanıtın otoritesi

Her iki süreç çıkışından sonra iki SQLite dosyası mode=ro ve query_only ile
okunur. Integrity, tek request/admission kimliği, payload digest, epoch/generation,
tek user girdisi, native read_file kaydı ve son çıktı hash'i doğrulanır. Sonuç
makbuzu veya HTTP terminal etiketi tek başına kabul sayılmaz. Model sayacı ilk
süreç dışındadır ve ikinci açılışta gereksiz yeni model denemelerini ayrıca reddeder.

`gateway_recovery_contract.py` bu kapsamı fail-closed denetler. Standart testler
makbuz tahrifi, kimlik/epoch/tekrar/bağlantı kapanışı ve AST sınırları içindir;
CI native Gateway başlatmaz. İlk beş gözlem ayrı validator fixture'ı olarak korunur;
son kabul koşularının sayısına otomatik eklenmez.

## Bulgu: orphan reservation

Hermes'in runs_idempotency.db ile state.db/session_admissions kayıtları ayrı
commit'lerde oluşur. Seçilen native kaynakta after-reserve kesintisi, kalıcı
reservation bulunurken hiç canonical iş olmadığını gösterdi. Yeni Gateway bu
kaydı interrupted olarak sunar, aynı anahtar yeni iş başlatmaz.

Bu güvenlik açısından kör tekrar yaratmıyor; fakat otomatik işi kurtarmıyor da.
Mevcut istemcinin backendConfirmed=true ifadesi bu durumda yalnız terminal HTTP
etiketini doğrular; canonical execution kanıtı değildir. requiresOperator=false
olması da bunun kendiliğinden çözüldüğünü göstermez. Genel HYB-004 otomatik kurtarma
ve M1 kabulü bu nedenle açık kalır. Eski anahtarı silerek yeniden başlatmak bu
pakette uygulanmaz. Sonuç, upstream'e tüm koşullarda veri kaybı açığı atfetmez.

## Sonraki iş — HYB-004B

Canonical admission kanıtı bulunmayan terminal rezervasyonu ayrı ve açık bir
orphan/uzlaştırma durumu olarak sınıflandır. Mevcut kayıtların sahipliği, request
parmak izi, epoch ve native durable kaynaklar birlikte doğrulanmadan yeniden
çalıştırma veya anahtar silme yapma. Belirsiz gerçek araç etkisinin uzlaştırılması,
rezervasyon saklama süresi dolması ve çok süreçli sahiplik ayrıca sınanmalı.

Gerçek write/harici yan etki ile tool-result commit'i ARASINDA kesinti henüz bu
beş read_file senaryosunda sınanmadı. after-tool, araç sonucu model isteğinde ve
kalıcı transcript'te görüldükten sonraki sınırdır. Pi'nin önceki harici SQLite
tekilleştirme kanıtı Hermes'e taşınmaz. Disk/güç arızası, çok-yazıcılı fencing,
OS sandbox, gerçek OpenClaw girişi, para bütçesi, hafıza/beceri transferi ve M2 açık.

## Yeniden üretim

```powershell
cd C:\Antigravity\AlazHarness\scratch\worktrees\ref-pi-001-ac97
python -B scripts/run_gateway_recovery.py --source-workspace C:\Antigravity\AlazHarness --python C:\Antigravity\AlazHarness\runtime\hyb-gateway-5a5c\prepared\env\Scripts\python.exe --output C:\Antigravity\AlazHarness\runtime\new-recovery-run --scenario completed
python -B -m unittest discover -s tests -v
python -B scripts/ci_check.py
```

Her output yeni olmalı. Hazır ortam tekrar kurulmaz. Diğer açık senaryolar üstteki
beş isimdir. Native deneme yerel Windows/Python3.14/Node24 kanıtıdır; Linux/native
CI çalışmış sayılmaz. API anahtarları ve tam profiller yalnız ignored runtime
altında tutulur; paylaşılan makbuzlarda token/config yer almaz.
