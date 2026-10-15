# AlazHarness — status

Son güncelleme: **15 Ekim 2026**. Ana devam kaydı; işe başlarken canlı Git durumunu doğrula.

## Kaldığımız yer

**REF-PI-002B dar atomik kabul deneyi PASS.** Aynı anahtar/aynı içerik tek native işi
buluyor; farklı içerik/tür/çalışma kapsamı açık `request_payload_conflict` alıyor.
Parmak izi ve native kabul aynı kayıt işleminde tutuluyor. Genel ürün benimsemesi,
tam M1 hibrit ve M2 otonomi **hâlâ açık**; motor değiştirilmedi.

| Alan | Güncel adres |
|---|---|
| Varsayılan çalışma alanı | `C:\Antigravity\AlazHarness` |
| Aktif çalışma ağacı | `C:\Antigravity\AlazHarness\scratch\worktrees\ref-pi-001-ac97` |
| Aktif dal | `alaz/ref-pi-002b-admission-1720` |
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

## Son yerel doğrulama

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

**REF-OC-001 — NOT RUN:** sabit OpenCode kaynağının izin değerlendirmesi ve olay
akışı/yeniden bağlanma sınırlarını, aynı şekilde kontrollü ve bağımsız gözlenen testlerle
ölç. Ardından mevcut dört kaynaktan tek çekirdek/tek oturum sahibi için kanıta dayalı
bileşen kararını yaz; sırf kapsama alındı diye dört motor birden ekleme.

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
