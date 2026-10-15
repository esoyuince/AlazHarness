# AlazHarness — status

Son güncelleme: 15 Ekim 2026. Yeni iş başında bu kayıt ve canlı Git doğrulanır.

## Kaldığımız yer

**HYB-004B dar salt-okuma uzlaştırma kabulü PASS.** Sunucunun terminal etiketi,
native iş kabulü ve bağımsız kayıt doğrulaması ayrıldı. Eksik kayıtla interrupted
artık operator gerektiren terminal_unverified; tamamlanmış kanıtlı sonuç korunur,
belirsiz iş otomatik tekrarlanmaz. Orphan REPAIR uygulanmadı; M1/M2 açık.

| Alan | Güncel değer |
|---|---|
| Varsayılan kök | C:\Antigravity\AlazHarness |
| Aktif çalışma ağacı | C:\Antigravity\AlazHarness\scratch\worktrees\ref-pi-001-ac97 |
| Aktif dal | alaz/hyb-004b-reconciliation-7c8b |
| Bu paketin tabanı | ebc81a50350c2fdc3d32dc88d3e834adfaffedba |
| Yerel sonuç | 506/506 standart, son kod4/4native, bağımsız55targeted dahil PASS |
| Git/CI | Bu kaydın yazımında yeni commit/push/exact-SHA CI PENDING; teslim eki aşağıya eklenecek. |
| Remote | esoyuince/AlazHarness, public MIT |
| main | Geliştirme paketleri henüz main ile birleştirilmedi. |

Kökteki eski alaz/hyb-001-component-slice kirli tarihsel worktree güncel ürün
kodu değildir. Reset/clean/stash veya toplu stage yok. status burada izlenen esas
kayıt; kökteki kolay erişim kopyası hash kontrolüyle eşitlenir. Başka oturumun
değişikliğini okumadan ezme. CURRENT-STATE.md tarihseldir.

## Bu turda uygulananlar

- Mevcut HermesRunsClient.reconcile tek authenticated GET yapar. start/stop/POST,
  yazma ve otomatik retry içermez. Ham run sonucu korunur.
- Version1 HTTP sınıflandırması: transportConfirmed, admissionReported ve
  canonicalVerified ayrı. Native tuple yoksa backendConfirmed=false ve
  requiresOperator=true. Tuple varsa yalnız canonical_terminal_reported;
  independently canonicalVerified hâlâ false. Retry/repair her durumda false.
- resume readonly hale getirildi: observer timeout/abort yalnız gözlemi sonlandırır,
  native stop göndermez. Bilinçli kontrol işlemi observe/stop ayrı kalır.
- LocalRecoveryInspector iki native SQLite store'u mode=ro/query_only ile okur;
  scope/key/body hash/run/session/admission/generation ve epoch/instance eşleşir.
  Doğrudan model seçimi de karşılaştırılır; desteklenmeyen alias/provider reddedilir.
- Native tombstone/terminal identity/result da okunur. Canlı admission yokluğu
  tek başına orphan sayılmaz. Retention/missing key yokluğu yeni iş izni değildir.
- Sonucun output ve usage değeri kayıtla aynı değilse başarı doğrulanmaz. Eşzamanlı
  DB değişimi/epoch değişimi ve bozuk JSON/türler unverified döndürür. Veri silme,
  lookup pruning, repair veya ikinci store yoktur. Bağlantılar açık bırakılmaz.

Yerel context(profile/token/epoch) güvenilir host ayarıdır, ağ kullanıcısının
seçebileceği yol veya yetki değildir. Destek default-profile bearer/input ve
opsiyonel doğrudan model/session_id sınırıdır. Bu sürüm ağ auth endpoint'i,
aktif süreç lease'i, iki-store atomik admission veya sonradan etki izni değildir.
Her sonuç snapshotOnly ve retryAllowed=false/repairAllowed=false kalır.

## Kanıt ve ayrı sayılar

**506/506 tam standart test PASS**, exit0, skip0, ölçülen kaynak drift0.
Ana local-validation.json ve bağımsız root-final-validation.json birbirinden
ayrı gerçek koşulardır; sayıları toplanmaz.55 bağımsız QA testi506 içinde.

**Final native4/4 PASS**, her senaryo son kodda bir kez: completed, before-model,
after-tool ve after-reserve. Gerçek public Hermes Gateway, iki native store,
mevcut adapter ve gerçek read_file çalışır.4owned hard kill,8native süreç nesli.
Yalnız model cevapları localhost fixture. Yeniden açmada yeni model/araç yok;
belirsiz işi çalıştırma yok. Dört ek negative kapsamda wrong token/stale epoch/
changed body ve readonly DB byte eşitliği kontrol edilir.

İlk aynı4 senaryo ikişer kez8/8 geçti; QA düzeltmesinden önceki hashleriyle
native-suite.json içinde korunur, final4 kabulüne eklenmez. İlk test paketleme
syntax hatası ve dört parent grup hatası initial-failures.json içinde;
QA ilk bozuk payload/model/identity bulguları ayrıca eski FAIL olarak saklandı.

Bağımsız55targeted =22loopback/classifier +33sentetik SQLite test. Hepsi post-fix
PASS.10 eski HYB-004 profilinin final inspector ile recheck'i4terminal/4unknown/
2reserve-only ve DB baytları değişmeden PASS; bu10 yeni Gateway koşusu değildir.
Yerel inspection CLI4 gerçek çağrıda beklenen exit/classification verdi; bunlar
da yeni Gateway/model çalışması değildir.

Ana kanıt: evidence/hyb-004b/final-native-suite.json, final-*.json,
local-validation.json, root-unittest.txt, cli-validation.json, qa-transition.json.
Ek QA: evidence/hyb-004b-qa, docs/research/HYB-004B-INDEPENDENT-QA.md.
Uygulama raporu: docs/HYB-004B-RECONCILIATION.md.

## Bağımsız QA'da düzeltilenler

Export classifier çelişkili completed/failed işaretlerini ve string olmayan
run_id'yi reddeder; whitespace session geçerli tuple değildir. Bozuk payload
array ve api_turn_v1 list/null exception kaçırmaz. Doğru replay fingerprint'in
yanında self-consistent fakat farklı requested_model bulunan canonical kayıt
artık yanlış doğrulanmaz. Bunlar sentetik ret kayıtlarının bulguları;
normal upstream HTTP'de uzaktan exploit iddiası yapılmaz. İlk iki overstrict
QA GET hata alanı beklentisi ayrı gerekçeyle düzeltildi; gerçek regresyonlar silinmedi.

## Korunan ortam

Hermes pin eb75627faf532fa6ffbdae59a0d14b0b385fc780. Dört upstream kaynak temiz
ve pinler aynı; sources.lock/gitlinks/components lock değişmedi. Yeni inspector
şema kaynakları config/recovery-inspector/source-lock.json içinde8dosya hash'iyle.
32eski kök dosya korundu. Kişisel profil/gerçek API key kullanılmadı; yeni
bağımlılık kurulmadı, sunucu ayarı değiştirilmedi, gerçek çıkarım/ücretli çağrı0.
Hazır Python: runtime/hyb-gateway-5a5c/prepared/env/Scripts/python.exe.
Özel test config/anahtarları yalnız runtime/hyb004b-7c8b altında, Git dışında.
Native deney Windows/Node24/Python3.14; standart CI bunu kurup çalıştırmaz.

## Sıradaki kesin iş

**HYB-004C — NOT RUN:** açık operatör uzlaştırma işleminde yetkili owner/epoch,
scoped request/key/run fingerprint ve native transaction sınırını bağla. Readonly
JSON'u tek başına gelecekteki mutation izni sayma. Eksik rezervasyonla genuinely
unknown execution ve retained completion aynı onarım yolu olmayacak. Yetkisiz,
farklı payload, eski nesil, retention ve storage failure retleri gereken kapılar.
Otomatik key silme/yeniden POST yok; irreversible dış etki belirsizliği ayrıca açık.

Diğer açıklar: gerçek OpenClaw girişinin tamamı, OS araç izinleri/izolasyonu,
çok-yazıcılı fencing, bütün model/yardımcı çağrılarda para/token/request bütçesi,
kalıcı hafıza/beceri transferi, sınırlı gerçek model M1 ve ardından otonom gündem M2.

## Devam komutları

```powershell
cd C:\Antigravity\AlazHarness\scratch\worktrees\ref-pi-001-ac97
git status --short --branch
git log -3 --oneline
python -B -m unittest discover -s tests -v
python -B scripts/ci_check.py
```

Yerel context/query ve native komutları HYB-004B raporunda; output yeni olmalı.
Etkisi bilinmeyen çağrı körlemesine tekrarlanmaz. Commit/push/exact-CI ayrı okunur.

## Korunan geçmiş

Bu tur başlamadan ve çalışırken oluşan status'un TAM kopyası:
docs/history/2026-10-15-STATUS-BEFORE-HYB004B-DELIVERY.md.
Bu dosya eski bütün HYB004/QA5016 ve bu tur7c8b/QA4cff ara notlarını korur.
Daha eski history bağlantıları da aynı içerikte kalır. Geçmiş komutlar yeni yetki değildir.

### 2026-10-15 — HYB-004B — Yerel kapanış

506standart ve final4native/55targeted ayrı kapsamlarla doğrulandı. Readonly host
sözleşmesi uygulandı; orphan veritabanı onarımı uygulanmadı. M1/M2 NOT ACCEPTED.
Yeni kod commit/push/exact-SHA CI sonucu ayrıca eklenecek. main birleşmedi.
