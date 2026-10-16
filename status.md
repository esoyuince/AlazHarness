# AlazHarness — status

Son güncelleme: 16 Ekim 2026. Canlı Git/HEAD/CI her devamda doğrulanır.

## Güncel nokta

**HYB-005C yerel salt-okunur rapor/CLI yayımlandı; kodun aynı-commit CI sonucu başarılı.**
Görev sonucu, native usage ve scope-wide rezervasyon/kullanım ayrı tutulur. Tek uygulama/yayın sahibi247a.
Aktif dal: alaz/hyb-005c-report-247a.
Aktif çalışma ağacı: C:\Antigravity\AlazHarness\scratch\worktrees\main-6f88.
Başlangıç HEAD aaf29d46b6496942c01a38f7373a9d56931c7cd0; temiz ve CI success.
Varsayılan kök eski korunmuş dalda; yalnız status.md erişim kopyası eşitlenir.
Main değiştirilmedi. Önceki kayıt docs/history/2026-10-16-STATUS-BEFORE-HYB005C-247a.md.

## Kapsam ve kabul

Mevcut LocalRecoveryInspector ve ExecutionLedger kullanılır; ikinci DB/kuyruk,
ajan döngüsü, scheduler veya para iadesi oluşturulmaz. Fiziksel sağlayıcı usage
ve native görev özeti ayrı kaynak/kapsam taşır; v1 ledger çağrıları runId taşımadığı
için scope toplamını tek görevin kesin maliyeti gibi sunma. Bütçe rezervasyonu fatura değildir.
Eksik/kısmi kullanım sıfır sayılmaz. Özet metni görev başarısı değildir.
İlk hedef: kaynak/CLI sözleşmesi, ret testleri, eski native kayıtların salt-okuma
karşılaştırması tamamlandı. Bu tur yeni native Gateway çalıştırılmadı.
Tam standart964/964 PASS;7eski profilin okuyucu/CLI kontrolü7/7 PASS.
Model çıkarımı/ücretli çağrı/kurulum yok. Genel izolasyon ve M1/M2 AÇIK.

## Başlangıç

247a yeni kısa dalı aynı temiz worktree üzerinde açtı. Başlangıç custody
runtime/hyb005c-247a/start.json. Değişiklik öncesi status tam arşivlendi.

### 2026-10-16T20:17:37.832474+03:00 — HYB-005C QA9256

Canlı247a tek uygulama/yayın sahibi görüldü;9256 önceki hash/cleanliness koşulunda çakışmayı yazmadan yakaladı.9256 yalnız ayrı QA9256 test/rapor/kanıtlarına bakacak, ürün/branch/native batch/commit yapmayacak. İnceleme hedefi: v1 ledger kapsamını run maliyeti saymama; rezervasyonu fiziksel gönderim/fatura sanmama; eksik usage sıfır değil; task outcome mevcut inspector ile; salt-okuma/kimlik/epoch/malformed retleri. QA başlangıç NOT RUN; yeni model/ücretli çağrı yok.

### 2026-10-16T20:19:53.110104+03:00 — HYB005C QA9256 baseline

Yedi eski final native profilin claim toplamları doğrudan SQL ile okundu; native task sonuçları mevcut inspector ile doğrulandı, iki DB byte/hashleri aynı. Yeni Gateway/model yok. Evidence/hyb-005c-qa9256/baseline-oracle.json: summary240/40 vs native120/20; SDK retry1reservation/unknown usage. Önemli: tool-limit/denied-write native completed olsa da araç ret; bu bağımsız görev başarı kanıtı değil. V1 profile toplamını tek run maliyeti/teslim sayısı sayma. Rapor henüz sınanmadı, baseline ayrı kapsam.

### 2026-10-16T20:22:56.562818+03:00 — HYB005C QA9256 iki bulgu

Gerçek host_report+sentetik SQLite30test26PASS/4FAIL exit1/drift0. QA-R01: in_progress/unknown canonical identity true olsa da usage native RESULT ile doğrulanmıyor; dış observed usage999/888 raporda complete_fields oluyor. Terminal-verified dışını unavailable/unverified tut. QA-R02: orphan status ve active admission outcome serbest metinleri JSON/textte aynen sızıyor; known enum doğrula/withhold. Tests/test_host_report_qa9256.py değişmeden korunur; rapor docs/research/HYB-005C-QA9256.md, ilk makbuzlar evidence/hyb-005c-qa9256. Ürün247a düzeltmesi beklenir;9256 ürün değiştirmedi.

### 2026-10-16T20:25:34.171877+03:00 — HYB005C ilk rapor ve QA kapanışı

39 ilk test PASS. QA9256 iki bulgusu ürün kodunda düzeltildi: nonterminal usage
verileri doğrulanmış sayılmıyor; serbest status/outcome metni dışarı yansımıyor.
Aynı30 QA testiyle birleşik69/69 PASS, drift0. Native completion bağımsız
hedef başarısı diye sunulmuyor. SDK/yardımcı çağrılar için açık scope-only
salt-okuma modu eklendi; bu modu test etmeden kabul yazma. Rapor eski native
state/ledger okuyucularını yeniden kullanır; runtime writer kaynakları değişmedi.

### 2026-10-16T20:27:49.851545+03:00 — HYB005C QA9256 düzeltme/CLI teyidi

Aynı30QA testi30/30 PASS (test SHA değişmedi, drift0). İki bulgu ürün247a düzeltmesiyle kapandı; ilk26/30FAIL makbuzu korunur. Beş eski gerçek native görev profilinde yeni rapor direct-SQL oracle ile aynı; gerçek CLI JSON+text10/10 eşleşti. DB byte/hashleri aynı, yeni Gateway/model0. Ledger scope/usage/reservation ile native task/usage ayrı; summary failed, native120/20 vs scope240/40. Retained-report-qa.json ve sanitize summary örneği evidence/hyb-005c-qa9256 altında. Bu5eski profil/10CLI koşusu yeni native kabul değildir.

### 2026-10-16T20:28:19.158647+03:00 — HYB005C QA9256 tam standart tur

Aynı30ret testi ve5eski native profil/10CLI doğrulaması tamamlandı.9256 şimdi tüm standart discoveryyi bağımsız çalıştırıyor; başlangıç/sonda kod/test/config dosya seti ve hash kontrolü var. Henüz bu full tur PASS sayılmaz. Model/Gateway/kurulum yok;247a tek uygulama/yayın sahibi. Makbuz7f8ab426-370a-4217-baad-ab5d5b599be4 lane92566938-2fd3-42cf-814b-1807134eb066.

### 2026-10-16T20:28:37.101062+03:00 — HYB005C son-kod kabul turu

83 hedefli standart test PASS; eski7native profil üstünde yeni report/CLI
7/7 PASS (yeni Gateway çalışması DEĞİL). Scope-only SDK1reservation/usageUNKNOWN;
unknown-price CLI exit2/bilgi doğrulanmadı. Kaynak ve iki DB değişmedi. Son
ürün kodu artık sabit: full root unittest başlatılıyor. Bu aşamada ürün/test
dosyası eklenirse yeniden tam doğrulama gerekir. Makbuz a9a74ad6-b663-4f97-bdd0-f8a5947ca2b2, lane247a055b-2607-49e2-9b48-8658ebc54345.

### 2026-10-16T20:30:54.928467+03:00 — HYB005C QA9256 teslim

Bağımsız tam standart964/964 PASS exit0/skip0;177ölçülen code/config dosyası drift0/yeni0. Aynı30ret testi bu964içinde. Toplam7eski native profil readonly teyit:5taskreport/API/CLI +2scope-only;14CLI çağrısı, yeni Gateway/model0. SDK usageUNKNOWN/rezervasyon korunur; unknown-price doğru exit2. Tüm DB hashleri aynı. QA9256 rapor/test/kanıtları seçilerek stage edildi; ürün247a tek Git teslim sahibi. Önce26PASS/4FAIL ve başarısız iddialar silinmedi. Kök32dosya/dört upstream/mevcut ledger-inspector-pinler değişmedi. Exact-SHA CI yerel PASS sayısından çıkarılmaz.

### 2026-10-16T20:32:21.471967+03:00 — HYB005C yerel kapanış ve yayın hazırlığı

Son ürün/test koduyla964/964 standart test PASS, exit0/skip0;177 ölçülen
kod/config dosyasında değişiklik/yeni dosya0. Aynı83 hedefli test964 içindedir.
7eski native profil:5görev+scope,SDK scope-only,unknown-price ret; okuyucu ve
CLI7/7 beklenen sonuç, kaynakDB/config/makbuz hashleri aynı. Yeni native/inference0.
QA9256 aynı30 testin4ilkFAILini doğruladı; son30/30 ve bağımsız964/964 PASS.
QA test/rapor/kanıtları okunarak aynı teslimde birleştirilir; sayılar toplanmaz.

Rapor:docs/HYB-005C-HOST-REPORT.md. Uygulama:packages/claw-hermes/host_report.py;
komut:scripts/inspect_host_report.py (--request veya --scope-only, JSON/text).
Kanıt:evidence/hyb-005c/full-validation.json ve retained-verification.json;
örnekler retained-reports/. Eski yazıcı/dispatch/inspector kodu değiştirilmedi.
32kök dosya ve4upstream kaynak korundu. Yeni bağımlılık, model, sunucu ayarı yok.
Sonraki HYB-005D: credential/egress izolasyonu; ardından gerçek sağlayıcı
model/tarife/token sınırı ve HYB-006 hafıza/beceri. HTTP raporu/per-run bağlama
ayrı açık kapsam. Main ilerletilmedi, M1/M2 açık. Commit/push/CI henüz doğrulanmadı.

### 2026-10-16T20:33:04.502004+03:00 — HYB005C QA9256 belge kapsamı

Ek sentetik readonly gözlem: doğru scope/key rezervasyonu var ama admission yoksa task canonicalVerified=false, partial_snapshot; ayrı doğrulanan profile budget görünür. Bu beklenen kapsam, execution izni yok. Ana rapordaki “If canonical identity cannot be verified, no execution totals...” ifadesi scoped reservation identity olarak daraltılmalı; gerçek davranışla çelişmesin. orphan-scope-semantics.json ve QA raporu stage edildi. Ürün/test kodu değişmedi;964tam test makbuzu korunuyor.

### 2026-10-16T20:37:21.950002+03:00 — HYB005C yayın ve aynı-SHA CI

Kod commit: `a77b729f35a7bda794fe4af41f5fcdced1da7dbd`; feature dalına push edildi. GitHub
alaz/local-ci success ve alaz-server aynı sha==checkout_sha makbuzu964/964,
failed0/skipped0/suite_errors0/status_delivery posted doğrulandı. Kanıt
evidence/hyb-005c/code-ci.json. Bu sunucu koşusu standart suite; eski7native
profil yalnız yeni okuyucuyla yerelde sınandı, yeni Gateway/model yürütümü yok.

Bu son belge commit öncesi HEAD/remote eşit, çalışma ağacı temizdi.177 ölçülen
kod/config son964PASS ile aynı; bu kapanışta yalnız belge ve CI makbuzu değişir.
Yeni belge SHA kendi CI sonucuyla ayrıca kontrol edilir. Kök status.md eşitlenir.
Main birleştirilmedi; mevcut native yazıcı/izin/bütçe motoru değişmedi.
Kesin sonraki iş HYB-005D credential/egress izolasyonu; per-run usage binding,
gerçek tarife/tokenizer ve HYB-006 hafıza/beceri kabulü ayrı. M1/M2 AÇIK.
