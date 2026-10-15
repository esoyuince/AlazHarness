# AlazHarness — status

15 Ekim 2026. Her yeni işte bu dosya ile canlı Git durumunu birlikte doğrula.

## Kaldığımız yer

**HYB-004B IN PROGRESS:** salt-okuma uzlaştırma ve muhafazakâr terminal sınıflandırması; otomatik key silme/POST/onarım yok.

**HYB-004 seçilmiş Gateway kesinti davranışları: PASS.** Beş gerçek süreç
kill/reopen senaryosu iki tekrarda10/10 geçti; fakat **genel otomatik kurtarma ve
M1 kabulü NOT ACCEPTED**. İstek anahtarı rezervasyonu ile canonical iş kabulü
arasındaki kalıcı boşluk doğrulandı. Sıradaki iş HYB-004B.

| Alan | Güncel kayıt |
|---|---|
| Varsayılan kök | C:\Antigravity\AlazHarness |
| Aktif çalışma ağacı | C:\Antigravity\AlazHarness\scratch\worktrees\ref-pi-001-ac97 |
| Aktif dal | alaz/hyb-004b-reconciliation-7c8b |
| Bu paketin tabanı | e6f596c2e73ba1db3b617b74f40423a531237cda |
| Yayın | Kod869626e54e9d73149176463ec21fbe6e562218da push edildi; aynı SHA alaz-server386/386 ve GitHub alaz/local-ci success. Son belge HEAD CI ayrı sorgulanır. |
| Remote | esoyuince/AlazHarness public MIT |
| main | Geliştirme paketleri henüz main ile birleştirilmedi. |

Kök, eski kirli alaz/hyb-001-component-slice dalındadır; güncel ürün sanma.
Aktif izlenen status.md esas; kök kopyası kolay erişim içindir. Reset/clean/stash,
toplu commit veya eşzamanlı değişikliğin üzerine yazma yok. CURRENT-STATE.md
önceki ayrıntıları korur, ikinci bağımsız güncel durum kaydı değildir.

## Bu turdaki somut sonuç

- completed: tamamlanmış native sonuçtan sonra gerçek process kill; aynı profil
  yeni epoch ile açılınca aynı run/admission/sonuç/usage. Yeni model/read çağrısı0.
- before-model: bu isim ilk provider YANITI beklenirken kesintiyi ifade eder;
  bir HTTP isteği vardır. started->unknown,0tool, aynı iş yeniden çalıştırılmadı.
- after-tool: gerçek read_file sonucu kalıcı transcript ve ikinci model isteğinde;
  kill sonrası1tool korunur, unknown kalır, ek model/araç yok, operatör gerekir.
- before-reserve: iki kalıcı kayıt da yok. Eski geçici run_id404; deneyin açık
  aynı-key yeniden gönderimi yeni bir işi1kez yürütür. Otomatik retry değildir.
- after-reserve:1reservation/0canonical admission/0mesaj/0model/0tool. Reopen'da
  aynı-key202 replay interrupted döner ama iş hiç kabul edilmemiştir.

Son iki senaryoda test-only AST/line checkpoint795/799 ile zamanlama tutuldu;
yerel değişkenler, native method/return veya veri değiştirilmedi. Diğer üçü
trace kullanmadan public Gateway ve kontrollü model yanıtıyla yürür. Model0
ifadesi gerçek inference içindir; bazı senaryolarda scripted HTTP çağrıları vardır.

## Sayılar ve kanıt kapsamı

**386/386 standart offline test PASS**, exit0, skip0, ölçülen kod drift yok.
Önceki321 +38 yeni primary kanıt/checkpoint testi +27 QA validator/reader testi.
Bu standart sayı gerçek native koşu sayısı değildir ve aşağıdakilerle toplanmaz.

**10/10 primary native koşu:** beş senaryo×2,10owned hard kill ve20native
incarnation. Her kill'de hem tutulan OS native handle hem venv launcher çıkışı
beklendi; aynı profil/config/API key/port ile epoch1->2, ayrı instance/nonce.
Replacement native kapanışları exit0; ilk kasıtlı kill nonzero. Her profile ait
SQLite iki-store snapshot'ı süreçler kapandıktan sonra readonly doğrulandı.
On koşunun final store'u paketleme aşamasında tekrar readonly okundu.

**2 ayrı bağımsız QA kill/reopen:** external SQLite BEGIN IMMEDIATE rollback-only
kilidi, trace veya native method değişimi OLMADAN aynı orphan boşluğunu gösterdi.
İki profile de0model/0admission/0mesaj. QA'nın geçmişte sekiz primary store'a
bakmış olması8 yeni yürütme değildir. Üç kanıt kapsamını ayrı tut.

Ana kanıt: evidence/hyb-004/native-suite.json ve beş isim×iki JSON,
local-validation.json, root-unittest.txt, source-custody.json,
independent-qa-receipt-recheck.json. Ek QA: evidence/hyb-004-qa ve
 docs/research/HYB-004-INDEPENDENT-QA.md. Ana rapor docs/HYB-004-GATEWAY-RECOVERY.md.
İlk5 deneme gözlemleri tests/fixtures/gateway_recovery_receipts.json içinde
offline fixture olarak korunur; final10 koşuya eklenmez veya tekrar sayılmaz.

## Açık ürün engeli — orphan reservation

runs_idempotency.db ve state.db/session_admissions ayrı commit sınırlarıdır.
Reservation varken hiç canonical iş yoksa restart fallback interrupted sunuyor.
HermesRunsClient.backendConfirmed=true burada yalnız terminal HTTP etiketi;
canonical execution kanıtı değil. requiresOperator=false sonucu da otomatik
çözülmüş iş anlamına gelmez. Bu davranış karakterizasyon PASS'ini tam recovery
başarısı diye sunma. Otomatik key silme/yeni POST veya operatör uzlaştırması
bu pakette yazılmadı; kaynak motor/üretim adaptörü değişmedi.

## Sıradaki kesin iş — HYB-004B

Canonical admission kanıtı olmayan terminal reservation için açık orphan/unknown
sınıflandırma ve uzlaştırma sözleşmesi ekle. Sahiplik, aynı body fingerprint,
run/session/admission/epoch ve authoritative store doğrulanmadan etkili retry yok.
Missing HTTP cevabı veya yalnız terminal etiketiyle işi tamamlandı sayma.
Kalıcı onarım/retention expiry ve gerçek dış etki sınırları ayrıca test edilmeli.

Gerçek write veya dış etki gerçekleşip tool sonucu henüz commit olmadan kesinti
bu read_file paketinde SINANMADI. after-tool, kaydı ve ikinci model isteği görülmüş
araç sonucundan SONRADIR. Pi dış etki/atomik kabul sonuçları Hermes'e taşınmaz.
Çok süreçli fencing, disk/güç kaybı, WAL, OS sandbox, tam OpenClaw girişi,
para/token bütçesi, hafıza/beceri transferi ve sınırlı gerçek model M1 açık.
Otonom gündem M2 bunlar kapanmadan başlamaz.

## Kaynak/ortam ve dosya koruması

Hermes eb75627faf532fa6ffbdae59a0d14b0b385fc780, OpenClaw/Pi/OpenCode pinleri
aynı ve temiz.32 eski kök dosya hash'i korundu. Asıl HermesRunsClient ve ürün
kaynak kilitleri değişmedi. Yeni bağımlılık kurulmadı; mevcut
runtime/hyb-gateway-5a5c/prepared/env/Scripts/python.exe kullanıldı.
API key/config/private çıktılar ignored runtime/hyb004-208f altındadır;
QA alanı runtime/hyb004-qa-5016. Gerçek model/ücretli çağrı0, üretim/sunucu
ayar değişikliği0. Native journal_mode=DELETE; WAL/güç kaybı kanıtı yok.

```powershell
cd C:\Antigravity\AlazHarness\scratch\worktrees\ref-pi-001-ac97
git status --short --branch
git log -3 --oneline
python -B -m unittest discover -s tests -v
python -B scripts/ci_check.py
```

Native tekrar komutu ana rapordadır; her output yeni olmalı. Mevcut model
ortamını veya sonucu belirsiz işi körlemesine tekrar çalıştırma. Native10+QA2
Windows kanıtıdır; standart sunucu CI'sı bu native deneyleri kurup çalıştırmaz.

## Önceki işler ve korunan günlük

M0 ve kaynak/CI hazırlığı; OpenClaw/Hermes bileşenleri; gerçek Hermes Agent/read;
Pi Agent ve Durable/crash/strict admission; OpenCode permission/event araştırması;
HYB-003 gerçek Gateway normal/lost-ack/stop önceki kapsamlarında korundu.
Tek yürütücü karar ADR-0003: Hermes; Pi ikinci store/scheduler olarak eklenmez.

Önceki status'un TAM kopyası, bu işin başlangıç/ara ve QA günlükleriyle:
`docs/history/2026-10-15-STATUS-BEFORE-HYB004-DELIVERY.md`.
Önceki Gateway ve daha eski tarihsel günlük bağlantıları o dosyada korunur.

### 2026-10-15 — HYB-004 — Yerel kapanış

On gerçek process crash/reopen davranışı ve386 standart test doğrulandı.
İki bağımsız rollback-only lock deneyi aynı orphan penceresini teyit etti.
Bu paket source-characterization/test/kanıt teslimidir; orphan onarımı,
genel otomatik recovery, M1/M2 kabulü değildir. Git/CI teslimi ayrı yazılır.

### 2026-10-15 — HYB-004 — Git ve CI teslimi

Kod commit: `869626e54e9d73149176463ec21fbe6e562218da`, uzak
`alaz/hyb-004-recovery-208f`. Gerçek alaz-server aynı SHA'yı checkout edip
386/386 standart testi çalıştırdı; failed/skipped/suite_errors0, status_delivery
posted. GitHub alaz/local-ci success ayrıca doğrulandı. Kanıt:
`evidence/hyb-004/code-ci.json`.

Ana10 native kill/reopen ve ayrı2 bağımsız lock/kill/reopen bu386 sayısına
eklenmez. QA5016 son olarak on ana koşunun tamamını readonly teyit etti;
`evidence/hyb-004-qa/primary-store-final-corroboration.json` eski8 kapsamını
10a tamamlar, yeni10 yürütme değildir. Eski8 kayıt korunur.

Bu teslim orphan onarımını uygulamadı; test karakterizasyonu tamamlandı,
genel otomatik kurtarma/M1/M2 NOT ACCEPTED. Sıradaki iş HYB-004B. Native
kaynaklar, ürün adaptörü,32 eski kök dosya ve mevcut sunucu ayarları korunur.
Aktif çalışma ağacı ile kök status kopyası eşitlendi; main birleşmedi.
Bu belge güncellemesi native deneyleri tekrar çalıştırmadı; belge commit'inin
CI'sı son HEAD üzerinden ayrıca kontrol edilir.

### 2026-10-15 — HYB-004B — Başlangıç7c8b

Taban ebc81a5; ref-pi-001-ac97 aktif worktree temiz doğrulandı. Bu tur7c8b tek
yazıcı; mevcut HermesRunsClient terminal/kanıt ayrımı ve scoped readonly native
store incelemesi. Tamamlanan kayıt, bilinmeyen execution, orphan adayı, yanlış
kapsam/parmak izi/epoch ve eksik store ayrı sınanacak. Ücretli model/kurulum yok.
Durum IN PROGRESS; eski386 PASS yeni pakete aktarılmaz.

### 2026-10-15 — HYB-004B-QA4cff — Başlangıç

7c8b tek uygulama yazıcısı korunur.4cff bağımsız negatif test/kanıt incelemesi:
HTTP terminal etiketi, native admission/tombstone, scope/fingerprint/epoch,
retention ve iki-store tutarlılığı. Üretim çekirdeğine ikinci yazar/branch yok.
QA çalışma alanı runtime/hyb004b-qa-4cff; bu anda IN PROGRESS/NOT RUN.

### 2026-10-15 — HYB-004B-QA4cff — İlk regresyonlar

Bağımsız22 adapter/classifier kontrolünde3 kaynak hata tekrarı: export classifier
completed+failed=true, boşluk session ve toString run nesnesini native tuple saydı.
HTTP katmanı çelişkiyi zaten reddediyor; uzak exploit iddiası değil. Testler
scripts/qa/reconciliation_transport.mjs ve tests/test_reconciliation_transport_qa.py.
İlk5 FAIL kaydının2si QA GET hata alanı beklentisiydi, bunlar gerekçesiyle düzeltildi;
3 ürün düzeltmesi7c8b sahibi tarafından yapılmalı. Python inspector bozuk payload
tipleri ve arşivlenmiş admission için ayrıca sınanıyor; henüz kabul değil.

### 2026-10-15 — HYB-004B-QA4cff — Inspector ret sınırı

33 bağımsız sentetik SQLite testinde bozuk payload/list/null3 AttributeError ve
özgün body.model ile farklı native requested_model1 yanlış doğrulama üretildi.
Kalıcı native profiller değişmedi; sadece geçici SQLite fixture. Rapor ve
regresyonlar docs/research/HYB-004B-INDEPENDENT-QA.md,
tests/test_reconciliation_inspector_qa.py içinde.7c8b düzeltmeleri bekleniyor;
mevcut kanıtlar FAILED olarak saklandı, kabul sayılarına katılmadı.

### 2026-10-15 — HYB-004B — Ara sonuç ve QA düzeltme planı

Readonly inspector retained10 store üzerinde doğru üç sınıfı ayırdı; bu10 yeni
yürütme değildir. Yeni8 native koşu kendi hashleriyle sürüyor, bitmeden ilgili
çekirdek dosyaları değiştirilmez. QA4cff bozuk list/null payload ve seçilmiş model
uyuşmazlığı ile exported classifier tip/çelişki açıklarını yeniden üretti. Bunlar
düzeltilecek ve final native/standart doğrulama ayrı kaydedilecek. resume artık
zaman aşımında native stop göndermiyor;30 wire ve40 ilk inspector testi geçti.

### 2026-10-15 — HYB-004B-QA4cff — Regresyon kapanışı

Düzeltilmiş classifier48f2a374 ve inspector8695b480 üzerinde55/55 bağımsız
kontrol PASS, exit0, drift yok.22 gerçek loopback HTTP/saf sınıflandırma ve33
sentetik SQLite ret/kimlik/okuyucu kontrolü; bunlar native55 Gateway koşusu değil.
İlk hatalar saklandı. İlk503 tam tur hata ve eşzamanlı kod drift içerdi, final
kabul değildir. Şimdi sabit kodda tam suite ve retained10 native kayıt yeniden
inceleniyor; native geçmiş profiller değiştirilmeyecek.

### 2026-10-15 — HYB-004B-QA4cff — Bağımsız yerel kapanış

Tam506/506 offline test PASS, exit0/skip0/koddrift0;55 yeni QA kontrolü bu506ya
dahil. Final inspector ile önceki10 native profil yeniden readonly incelendi:
4 canonical terminal,4 execution unknown,2 reserve-only; DB dosyaları değişmedi.
Bunlar yeni native10 koşu değildir. Önceki503 FAIL+drift ve ilk hatalar korundu.
Rapor docs/research/HYB-004B-INDEPENDENT-QA.md; evidence/hyb-004b-qa içinde final
makbuzlar. Yalnız QA sahipli 20 dosya stage edildi;7c8b final tek commit
sahibi. Orphan onarımı/otomatik retry yok; M1/M2 açık.32 kök dosya/4 vendor korundu.
