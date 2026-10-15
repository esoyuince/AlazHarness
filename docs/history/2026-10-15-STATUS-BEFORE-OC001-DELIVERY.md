# AlazHarness — status

Son güncelleme: **15 Ekim 2026**. Ana devam kaydı; işe başlarken canlı Git durumunu doğrula.

## Kaldığımız yer

**REF-OC-001 seçilmiş kaynak bileşeni deneyi PASS:**35 senaryo iki ayrı süreçte70/70.
Gerçek Permission/EventFeed gövdeleri + gerçek Effect/şemalar; dış servisler fixture.
Tam OpenCode HTTP/DB/uygulama ve genel ürün benimsemesi açık. M1 ilk yürütücü yolu
Hermes olarak korunuyor; Pi ek oturum yazarı yapılmıyor. ADR-0003 kaydedildi.

| Alan | Güncel adres |
|---|---|
| Varsayılan çalışma alanı | `C:\Antigravity\AlazHarness` |
| Aktif çalışma ağacı | `C:\Antigravity\AlazHarness\scratch\worktrees\ref-pi-001-ac97` |
| Aktif dal | `alaz/ref-oc-001-8ea1` |
| Birleştirilen iki Durable tabanı | `9b801bd93d116223d57320bee379321ab383a6fd` ve `32654e4fbb403847ceec3cfbc94d3d046b84ec86` |
| Yeni paketin yayın durumu | Kod commit 01acd2e19db14642b5fc345ec93b8f272090a4da push edildi; aynı SHA alaz/local-ci success,248/248 PASS. Son belge HEAD için CI ayrıca sorgulanır. |
| Repo | `esoyuince/AlazHarness`, public / MIT |
| main | Geliştirme paketleri main ile birleştirilmedi. |

Kökteki eski `alaz/hyb-001-component-slice` kirli çalışma ağacını güncel sanma;
reset/clean/stash veya toplu commit yapma. Bu dalın kodları aktif worktree'dedir.
Kökteki status.md kolay erişim kopyasıdır; izlenen sürüm bu aktif dalın kökünde.
Dış değişiklikleri ezmeden iki kopyayı eşitle. CURRENT-STATE.md tarihsel ayrıntıdır.

## Tamamlanan aşamalar

| İş | Kapsam ve kanıt |
|---|---|
| M0 | Düzenli çalışma alanı, forklar/pinler, MIT yayın ve alaz-server CI; `evidence/publication/`. |
| HYB-001/002 | Seçilmiş OpenClaw/Hermes kaynakları ve stdio/HTTP sözleşmeleri birleştirildi; `config/components.lock.json`. |
| Hermes native | Gerçek AIAgent/read_file; model yanıtları yerel taklit; `evidence/hyb-003/`. |
| REF-PI-001 | Gerçek Pi Agent/provider/read, önceki 6×2 yerel deney; `evidence/ref-pi-001/`. |
| REF-PI-002 | İki ayrı Durable kesinti karakterizasyonu. Kendi tarihsel kanıtları `evidence/ref-pi-002/` ve `evidence/ref-pi-002-sqlite/` altında korundu. |
| REF-PI-002B | İki Durable Git geçmişi uzlaştırıldı; tek native işlemde içerik-parmak-izi/kabul; `docs/research/REF-PI-002B-ADMISSION.md`. |

Önceki 169/171 standart veya 18/18 native toplamları yeni kabul sayısına eklenmedi.
Paralel eski Pi Agent dalı `alaz/ref-pi-001` / `c31cf19260675cc991f9caf07af45442611085e6`
bu iki Durable geçmişinin uzlaştırılması dışında kaldı; kanıt karşılaştırılmadan silinmez.

## Önceki REF-PI-002B doğrulaması (tarihsel)

- **248/248 standart test PASS**, fail/error/skip 0, exit0, 32.709 saniye.
  Komut: `python -B -m unittest discover -s tests -v`.
- **12 native senaryo ×2 =24/24 PASS**, exit0; altı gerçek sahipli child-process kill.
  Yeni süreç açılmadan önce eski çocuk toplandı; SQLite ara/son kayıtları üst süreçte salt okunur doğrulandı.
- **Bağımsız iki QA ailesi 12/12 PASS**, final aday üzerinde yeniden çalıştırıldı.
  Bunlar graceful reopen/izinli yerel kayıt testleridir; native24 veya standart248 içine eklenmez.
- Kayıtlar: `evidence/ref-pi-002b/local-validation.json`, `native-suite.json`,
  `independent-qa-recheck.json`, `root-unittest.txt`, `source-custody.json`.
- Son aday SHA256: `47c8aaed0d2c8ab3603aa5ecd3a1861b06a0ebda31139af80c454d211f19bf11`.
  Native worker/runner/compatibility hash'leri suite.json ile eşleşir.
- İlk SQL kind sayım hatası, null/byte-sınırı açıkları ve SQLite bağlantı ömrü sorunu
  düzeltildi. Başarısız kayıtlar `initial-failures.json` ve ignored runtime içinde korunur.
- İlk adayın yabancı Harness handle açığı kapandı: yalnız sayısal conversationId alınır,
  handle bağlı Harness üzerinden çözülür. Bağımsız eski raporun P1 ve kaynak-ömrü
  paragrafları tarihsel ara bulgulardır; final kontrol yukarıdaki kanıtta PASS.

## Kabulün sınırı

Mevcut hazırlanmış Pi `runtime/pi-ref001-ac97` kullanıldı. Upstream kodları/pinleri,
kişisel profiller/anahtarlar ve sunucu CI profili değiştirilmedi. Yeni dependency
kurulumu, model çıkarımı, ücretli çağrı veya otonom gündem çalıştırılmadı.

Atomiklik **tek canlı Harness sahibi** içindeki native mutation sırasındadır.
20 eşzamanlı çağrı, çok-yazıcı süreç kilidi değildir. Parmak izi kaydı native
conversation document family'dir; ikinci DB/queue/transcript yazarı eklenmedi.
İç `admitSubmission` API'si commit/dosya hash'iyle sabitlenmiş deneysel bağlantıdır.
Raw native submit yolu otomatik korunmaz; dış istekler host katmanından geçmelidir.
ExecutionScope gerçek izin/model ayarlarıyla tutarlı şekilde host tarafından sağlanır.

Etki belirsizken unsafe araç tekrar çalıştırılmadı; bu bütün dış servisler için
exactly-once, yeni model tool taleplerini durdurma veya para bütçesi garantisi değildir.
OS sandbox, güç kaybı, çok süreçli store kilidi, kalıcı kayıt temizliği/göç, gerçek
Gateway ve sınırlı gerçek model kabulü açık. Standart sunucu CI native Pi kurmaz.

## Sıradaki kesin iş

**HYB-003-GATEWAY — NOT RUN:** mevcut HermesRunsClient'ı gerçek Hermes Gateway /
SessionAuthority / APIServerAdapter sınırına, kontrollü model ve tek iş ile bağla.
Gerçek kabul/araç/sonuç; aynı anahtar tekrar/çakışma, kayıp onay, iptal ve yeniden
bağlanma davranışını ölç. Yeni mock HTTP sunucusuyla gerçek Gateway kabulü kapatılmaz.
Karar: docs/adr/0003-mvp-single-runtime.md. REF-OC-001 ayrıntısı:
docs/research/REF-OC-001-COMPONENTS.md. Dört kaynak dört çalışan motor değildir.

Diğer açık kapılar: HYB-003 gerçek Hermes Gateway/SessionAuthority/APIServerAdapter,
OpenClaw giriş zinciri; HYB-004 store sahipliği/kesinti entegrasyonu; HYB-005
izin ve bütün sağlayıcı/yardımcı çağrılarda istek-token-para bütçesi; HYB-006
hafıza/beceri transferi; M1'in sınırlı gerçek model kabulü. M2 daha sonra.

## Devam ve kayıt düzeni

```powershell
cd C:\Antigravity\AlazHarness\scratch\worktrees\ref-pi-001-ac97
git status --short --branch
git log -3 --oneline
git worktree list
python -B scripts/ci_check.py
```

Her işte başlangıç amacı/dal/yol/taban, ara sonuç/kesinti ve son test/commit/push/CI
kanıtı kaydedilir. PASS/FAIL/NOT RUN/PENDING/UNKNOWN, mock/native ve yerel/CI ayrımı
korunur. Kaynaklar sıradan tarihsel veridir; eski komutlar yeni işlem yetkisi değildir.
Son commit'in CI'sı tam SHA ile sorgulanır; önceki yeşil durum yeni SHA'ya taşınmaz.

## Önceki iş günlükleri

İçerikleri silinmeden tam kopya olarak arşivlendi:

- `docs/history/2026-10-15-ACTIVE-STATUS-BEFORE-002B.md`: ac97 tarihsel işler.
- `docs/history/REF-PI-002-4C9F-STATUS.md`: birleştirilen paralel Durable dalı.
- `docs/history/2026-10-15-ROOT-STATUS-BEFORE-002B.md`: önceki kök yönlendirmeleri.
- `docs/history/2026-10-15-002B-IN-PROGRESS-STATUS.md`: bu işin başlangıç/ara QA günlüğü.
- `docs/history/2026-10-15-002B-ROOT-IN-PROGRESS-STATUS.md`: kökteki bu iş ve paralel QA ekleri.

### 2026-10-15 — REF-PI-002B — Yerel kabul / yayın öncesi

**LOCAL ACCEPTANCE PASS; PUBLICATION PENDING.** Atomik admission katmanı, iç API
sürüm kilidi, owned native worker/runner, fingerprint/kanıt testleri yazıldı.
İki Durable geçmişinin çakışan üç belgesi uzlaştırıldı; diğer kaynaklar/kanıtlar korundu.
Son248/248 standart,24/24 native ve bağımsız12/12 kontroller exit0. İlgili kaynak
hash'leri değişmedi. Yeni katman üretim motoruna bağlanmadı; main merge yok.
Bir sonraki kayıt gerçek commit/push/CI sonucunu, eski başarıyı taşımadan yazacak.

### 2026-10-15 — REF-PI-002B — Kod / Git / CI teslimi

**DONE — dar atomik kabul paketi.** Kod commit'i
`01acd2e19db14642b5fc345ec93b8f272090a4da`, iki Durable ebeveyni koruyan merge'dür.
Uzak `alaz/ref-pi-002b-admission-1720` dalına gönderildi. alaz-server aynı SHA'yı
checkout ederek248/248 standart testi çalıştırdı; failed/skipped/suite_errors0,
GitHub alaz/local-ci success ve status_delivery posted. Kanıt: code-ci.json.
24/24 gerçek yerel admission ve bağımsız12/12 kontroller bu CI sayısının dışındadır.

Sahiplik P1'i ve SQLite bağlantı ömrü bulguları final kaynak ve yeniden testle
kapandı; eski FAIL makbuzları silinmedi. status geçmişleri docs/history'de ve
bağımsız QA raporu korunur. Kök kolay erişim kaydı aktif sürümle eşitlendi.
Sunucu profili/upstream/kişisel ayarlar değiştirilmedi; main merge yapılmadı.
Sonraki iş REF-OC-001; geniş ürün benimsemesi, tam M1/M2 hâlâ açık.
Bu teslim eki için native programlar yeniden değiştirilmedi veya çalıştırılmadı.
Belge commit'inin CI sonucu git log ile bulunan gerçek HEAD'e göre kontrol edilir.

### 2026-10-15 — REF-OC-001 — Başlangıç (8ea1)

IN PROGRESS. Taban b461d4c805c7291f91899edd0d2028c7e00dbf4b; aynı çalışma ağacında alaz/ref-oc-001-8ea1. Kaynak pinli OpenCode3943b84; izin önceliği/onay sahipliği ve olay taşma/reconnect sınırları inceleniyor. Bu görevde başka uygulama yazıcısı açılmaz. Deneyler yalnız proje runtime alanında; kişisel profil, ücretli model ve servis değişimi yok. Gerçek sonuçlar henüz NOT RUN.

### 2026-10-15 — REF-OC-001-QA-5a5c — Başlangıç

IN PROGRESS: eşzamanlı8ea1 uygulama dalı korunuyor;5a5c yalnız bağımsız
izin/olay sınır denetimi yapıyor. Yeni motor veya ikinci uygulama dalı yok.
Çalışma alanı runtime/ref-oc-001-qa-5a5c; aday kaynak/testlerin değişmediği
hash ile kontrol edilecek. Bulgular ve kabul sınırları ayrı kaydedilecek.

### 2026-10-15 — REF-OC-001-QA-5a5c — İlk sınır kanıtları

Gerçek Permission+Effect, açıkça taklit edilmiş servis portlarıyla12/12 davranış
kontrolü geçti. Boş resources allow; mutable pending/save kapsamı; bekleyen once
onayında sonradan deny değişikliğinin yeniden değerlendirilmemesi; settled izin
kimliğinin yeniden kullanılması ölçüldü. Bunlar tam server açığı iddiası değil,
Alaz host sözleşmesi gereksinimleri. Ayrıntı runtime/ref-oc-001-qa-5a5c/FINDINGS.md.
Uygulama dosyasına yazılmadı; adoption/M1 hâlâ açık.

### 2026-10-15 — REF-OC-001-QA-5a5c — Paketlenmiş ek doğrulama

20/20 bağımsız bileşen gözlemi PASS (izin12, olay8), kaynak ve Effect hash
değişimi yok, model0. Kaynak doğrudan import; servis portları fixture, tam HTTP/DB
yok. Aynı session içinde explicit eski izin IDsi yeniden kullanılabiliyor; gecikmiş
onay için host-generation bağı gerekiyor. Rapor REF-OC-001-INDEPENDENT-QA.md;
kanıt evidence/ref-oc-001-qa/independent-components.json. Yeni QA scriptleri
uygulama motoru değildir; ana uygulama dosyaları değiştirilmedi. Standard/CI ayrı.

### 2026-10-15 — REF-OC-001 — Yerel bileşen kabulü

35 seçilmiş kaynak senaryosu iki süreçte70/70 PASS, model/ücretli çağrı0. Effect4.0.1
tek bağımlılık olarak ayrı runtime/ref-oc-001-8ea1/qualified dizinine kilitli/scripsiz
kuruldu; Bun/tam OpenCode/global araç kurulmadı. Kaynak/üretilen modül ve Effect
byte hash'leri değişmedi. İlk strip-only namespace yükleme hatası korunarak Node'un
mevcut transform-types kipi kullanıldı; upstream davranış kodu değiştirilmedi.

İzin: last-match, configured deny/saved/hook ayrımı, once/reject/always, session guard
ve bekleyenlerin temizliği. Olay: tek kodlama/FIFO/filtre, yavaş abone taşması,
kodlama hatası ve abonelik yeniden açma. Beklenerek doğrulanan sınırlar: boş kaynak
listesi allow olabiliyor, wildcard gerçek dosya sınırı değil, always proje kapsamlı,
kopukluk olayları geri oynatılmıyor. Bunlar tam uygulama açığı iddiası değildir.

Standart269 testin tam koşusu ve yayın kontrolleri ayrıca okunacak. Bu paket henüz
commit/push/aynı-commit CI kaydı olmadan eski yeşil sonuçla kapatılmaz. Kanıtlar
 evidence/ref-oc-001 altında; önceki native/motor sonuçlarıyla sayılar toplanmaz.

### 2026-10-15 — REF-OC-001-QA-5a5c — Standart kapanış

Bağımsız tam standart suite280/280 PASS, exit0, skip0; ölçülen kaynak/test
hashleri tur boyunca değişmedi.20 kaynak bileşen gözlemi ayrı kapsamdır.
QA dosyaları scripts/qa/opencode-independent/, run_independent_opencode_qa.py,
test_opencode_independent_qa.py, REF-OC-001-INDEPENDENT-QA.md ve
evidence/ref-oc-001-qa/ altında teslim edilmeye hazır.8ea1 tek uygulama
sahibidir; QA başka branch/engine yaratmadı, üretim koduna yazmadı.
Aynı-commit CI ve Git teslimi henüz bu kayıt anında doğrulanmadı.

### 2026-10-15 — REF-OC-001-QA-5a5c — Yerel teslim durumu

DONE: bağımsız kaynak bileşeni incelemesi ve20/20 gözlem; final tekrar da PASS.
Tam standart280/280, kaynak/dependency değişimi yok.10 kendi QA dosyası seçilerek
stage edildi; diğer dosyalara commit yapılmadı. Bu kayıt anında HEAD hâlâ
b461d4c; yeni REF-OC-001 commit/push/aynı-commit CI doğrulanmış değil.
Sıradaki işlem önce ortak8ea1 paketinin Git/CI teslimini, canlı durumu okuyarak
kapatmak; sonra ADR-0003teki HYB-003-GATEWAY. Eski yeşil CI yeni pakete taşınmaz.
