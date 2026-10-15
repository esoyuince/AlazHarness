# AlazHarness — status

15 Ekim 2026. Her yeni işte bu dosya ile canlı Git durumunu birlikte doğrula.

## Kaldığımız yer

**HYB-004 seçilmiş Gateway kesinti davranışları: PASS.** Beş gerçek süreç
kill/reopen senaryosu iki tekrarda10/10 geçti; fakat **genel otomatik kurtarma ve
M1 kabulü NOT ACCEPTED**. İstek anahtarı rezervasyonu ile canonical iş kabulü
arasındaki kalıcı boşluk doğrulandı. Sıradaki iş HYB-004B.

| Alan | Güncel kayıt |
|---|---|
| Varsayılan kök | C:\Antigravity\AlazHarness |
| Aktif çalışma ağacı | C:\Antigravity\AlazHarness\scratch\worktrees\ref-pi-001-ac97 |
| Aktif dal | alaz/hyb-004-recovery-208f |
| Bu paketin tabanı | e6f596c2e73ba1db3b617b74f40423a531237cda |
| Yayın | Yerel tamamlandı; bu yeni paketin commit/push/exact-SHA CI kontrolü PENDING. Teslim eki ayrıca kaydedilir. |
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
