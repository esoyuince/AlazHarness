# AlazHarness — status

## R164A2 — aynı kaynakların yeni CI politikasıyla yayını — kaynak CI PASS; yayın IN PROGRESS

P1 DONE; P2 IN PROGRESS. P3–P5, tam D3B, M1 ve production OPEN.

- Yayın dalı: `alaz/p2-service-closure-r164a2`.
- Primary çalışma ağacı: `C:\Antigravity\AlazHarness\scratch\worktrees\p2-service-closure-r164a2`.
- Başlangıç ve yayın öncesi main: `28a12e1b18a839a9489a0c463d904b8e9a46db03`.
- A2 kaynak commit'i: `5467f599f36a0b88de699c7d6628a52235719e38`; normal feature push ve exact tam CI PASS.
- Korunan R164A1 dalı: `alaz/p2-service-closure-r164a1`; son commit
  `82cab2562007dff124326cff83022f0370f31ccb`.
- R164A1 kaynak commit'i: `090754b6caf20bbda7f643dae1eddb31ada69a3b`.
- Önceki izlenen durumun tam bayt arşivi: [R164A1 parent](docs/status-history/r164a2-parent.md).
- Son kabul edilmiş R163 yayın günlüğü SHA-256:
  `63525a048232d70109aa0378bf967376a96ef2e5ef0510bd8e28dd604d5cf809`.
- Native seçim: `5e3635c2cdfc2161fd20c089618bd7f2a7c12f2d`, 760 dosya.

### Amaç ve kapsam

R164A1, [entegrasyon planının](docs/P2-SERVICE-INTEGRATION-R161A1-PLAN.md)
dördüncü adımındaki özgün servis volume kapanışını kaynak/fixture düzeyinde
uyguladı. Child final/exit0/EOF kanıtı aynı ServiceVolumeSupervisor üzerindeki
normal stop/finish zincirine bağlıdır; tam zincir bitmeden dış CLOSED üretilmez.
Ürün davranışı ve önceki odaklı doğrulama ayrıntıları
[uygulama raporunda](docs/P2-SERVICE-CLOSURE-R164A1.md) korunur.

R164A2 yeni yayın neslidir. Ürün, test, runner ve tarihsel kaynak bağları R164A1
ile aynı baytlarda tutulur. Kullanıcı, yalnız AlazHarness'in CI süre bütçesinin
360 saniyeden 480 saniyeye çıkarılmasını ve yayının tamamlanmasını açıkça
onayladı. Ayrı altyapı değişikliği 27 Ekim 2026 saat 23:26 TRT'de uygulandı:
yalnız AlazHarness için `timeout_sec` 360 → 480 oldu. Özel yedek, mevcut worker
kilidi, boş kuyruk/processing, tek alan farkı, owner/mode korunması, fsync ve
exact geri okuma doğrulandı. İmaj, tam test/statik komutu, kaynak sınırları,
güven kuralları ve concurrency aynı kaldı; servis yeniden başlatılmadı.

Uygulama makbuzu `scratch/r164a2-publication/ci-policy-change.json`, SHA-256
`87b368acf04df8cf1f5ef11eca761a12ed76e8e63d983296b7dd34d971200f10`.
Yeni politika digest'i
`39feb838fe28d4176b40dc99d8dcc824648c1b374a3d168ef0e4a23bdade4776`.
Altyapı ayarı APPLIED/PASS. Yeni A2 kaynak commit'inin aynı politika altında tam
CI kabulü PASS; kapanış commit'inin tam CI'sı ve main yayını bu checkpoint'te
henüz NOT RUN.

### Korunan doğrulamalar ve yayın engelinin nedeni

Aşağıdaki odaklı sonuçlar R164A1'in gerçek koşularıdır; A2'de yeniden çalışmış
gibi sayılmaz. Aynı 25 ürün dosyası, 50 test/destek dosyası, runner ve sıralı
806 test kimliği yeni nesilde de bayt eşitliğiyle korunmalıdır.

| Korunan koşu | Seçilen/koşulan | PASS | SKIP | Test failure / error | Genel sonuç |
|---|---:|---:|---:|---:|---|
| R164A1 Linux odaklı | 806 | 806 | 0 | 0 / 0 | PASS, exit 0 |
| R164A1 primary Windows odaklı | 806 | 626 | 180 | 0 / 0 | PASS, exit 0 |
| R164A1 ayrı tarihsel bağ | 14 | 14 | 0 | 0 / 0 | PASS, exit 0 |
| `090754b` tam CI, 360 sn politika | 4.566 | 4.544 | 22 | 0 / 0 | PASS, 347,819 sn |
| `82cab256` ilk tam CI | 4.566 | 4.544 | 22 | 0 / 0 | FAIL, rc124 / timeout; test bölümü 348,954 sn |
| `82cab256` tek operatör tekrarı | 4.566 | 4.544 | 22 | 0 / 0 | FAIL, rc124 / timeout; test bölümü 349,703 sn |

Tarihsel 14 test, 806 seçimin içinde de bulunur; toplam test sayısına tekrar
eklenmez. Windows SKIP kayıtları POSIX pipe, Unix socket/peer credentials,
directory fsync ve ilgili platform koşullarını açıkça belirtir. Linux odaklı
koşusunda atlama yoktur.

İki başarısız final koşusunun test ve statik PASS metni, genel timeout sonucunu
PASS'e çevirmez. 360 saniyelik sınır bütün Docker komutuna uygulanır; yalnız
test bölümünün süresi değildir. Ayrı aşama zamanları olmadığından aşım tek bir
alt işleme bağlanamaz. Son final status ID `57399491641`; ilk başarısız status
ID `57397447692`. Eski kaynak CI kabulü 360 saniyelik politikaya bağlıdır ve
480 saniyelik yeni yayın neslinin source/final kabulü olarak kullanılamaz.

R164A1 uygulama kanıtları `evidence/p2-service-closure-r164a1/` altında özgün
kimlikleriyle korunur. Eski CI sonuçları ve yeni altyapı değişikliği
[A2 recovery kaydına](evidence/p2-service-closure-r164a2/recovery.json) bağlanır.
A1 son engel kontrolü 43 paket dosyası, sekiz korunan çalışma ağacı, kökün
33 değişmiş dosyası, dört önceki feature ve 760 native kaynağın korunmasını
PASS olarak kaydetti. A2 kendi başlangıç ve yayın kontrollerini ayrıca yapar.

### A2 kaynak CI kabulü

Exact `5467f599f36a0b88de699c7d6628a52235719e38` commit'i için required
`alaz/local-ci` yeni tam koşusu PASS: 4.566 test, 4.544 PASS, 22 SKIP,
failure/error 0; test süresi 350,015 saniye. Container exit 0, OOM/timeout false
ve cleanup `removed`. Statik kapı 6.906 dosya denetledi, 4.566 test keşfetti ve
PASS verdi. Bu sonuç gerçek tam koşudur; önceki başarı yeniden kullanılmadı.

GitHub status ID `57410520459`, zaman 27 Ekim 2026 23:43:59 TRT;
delivery `46974e68-d246-11f1-9f75-c42a6ebc041e`. Authenticated GitHub gözlemi,
sunucu artifact'ı, ham log, suite sayıları ve yeni politika digest'i aynı exact
commit'e bağlandı. [Public source CI makbuzu](evidence/p2-service-closure-r164a1/source-ci.json),
kapanış commit'inde `accepted-source-ci.json` kabul makbuzunun exact baytlarını
taşır; SHA-256
`5bb8ac9ce765973eeb42908b212ac730959f37ec4054ca3fb18bab4831ccf703`.

### Yeni yayın neslinin kabul durumu

| Adım | Bu checkpoint'teki durum |
|---|---|
| 360 → 480 saniye değişikliği için kullanıcı yetkisi | ONAYLI |
| Altyapı yedeği, atomik değişiklik ve exact geri okuma | PASS; 480 saniye APPLIED |
| A2 kaynak commit/push ve exact tam CI | PASS; `5467f599` |
| A2 kapanış commit/push ve aynı politika altında exact tam CI | NOT RUN |
| Yayın öncesi integrity ve normal main fast-forward/push | NOT RUN |
| Ayrı main status kabulü ve final integrity | NOT RUN |

Kaynak ve kapanış CI makbuzlarının politika digest'i aynı olmalıdır; mevcut
kabul kontrolü gevşetilmez. Kabul edilmiş A2 kaynak CI makbuzu, kapanış commit'inde public
`evidence/p2-service-closure-r164a1/source-ci.json` dosyasına exact baytlarıyla
bağlanır. Bu dosya adı uygulama neslini korur; içindeki target ve politika
alanları yeni yayın neslinin gerçek koşusunu gösterir.

Kesin terminal yayın sonucu primary çalışma ağacındaki
`scratch/r164a2-publication/final-publication.json` ile tamamlanır. Bu izlenen
kapanış checkpoint'i A2 kaynak CI kabulünden sonra hazırlanmıştır; kendi final
commit CI'sı, main ve final integrity sonucu burada NOT RUN'dır. Kaynak başarısı
terminal yayın makbuzunun yerine geçmez. Gerçek kernel, kurulu servis ve model
kabulü bu paketin kapsamı değildir.

### Kesin sonraki adım

Yalnız status, rapor ve kabul edilmiş public kaynak CI makbuzuyla kapanış
commit'ini oluştur. Bu exact final commit'in tam CI'sını aynı 480 saniyelik
politika altında doğrula. Ardından yayın öncesi integrity, normal main
fast-forward/push, ayrı main verified-success reuse ve final integrity
günlüğünü tamamla.

Yayından sonra planın beşinci adımı host görevlerinin aynı kimliği doğrulanmış
native API'ye dar erişimidir. Yeni tek P2 kurulumu/kernel kabulü ve seçilmiş
gerçek model/provider/toolset/bütçe deneyi açık kalır.

### İş günlüğü

- 2026-10-27 R164A2 başlangıç: kullanıcı CI sınırının 360 → 480 saniyeye
  çıkarılmasını ve yayının tamamlanmasını onayladı. Eski R164A1 status dosyası
  baytları değiştirilmeden arşivlendi. İki timeout FAIL kaydı ve eski kaynak
  PASS makbuzu korunarak yeni yayın nesli hazırlanıyor. Bu kayıt yeni bir
  ürün/test yürütmesi veya uygulanan altyapı ayarı iddiası taşımaz.
- 2026-10-27 23:26 TRT altyapı checkpoint'i: yalnız AlazHarness CI timeout
  alanı 360 → 480 olarak uygulandı. Makbuz `87b368ac…200f10`, config/politika
  geri okuması ve korunan diğer alanlar PASS. Native işlem
  `c164a201-1027-4a01-8000-000000000116` completed, exit 0. Bu uygulama sonucu
  source veya final CI kabulü değildir; yeni tam CI nesli sıradadır.
- 2026-10-27 A2 kaynak CI checkpoint'i: `5467f599` normal feature push
  sonrasında exact tam CI ile kabul edildi: 4.566 toplam, 4.544 PASS, 22 SKIP,
  failure/error 0, 350,015 saniye; container exit 0, OOM/timeout false, cleanup
  removed. Status `57410520459`; kabul makbuzu SHA-256
  `5bb8ac9ce765973eeb42908b212ac730959f37ec4054ca3fb18bab4831ccf703`.
  Kapanış commit'i yalnız takip belgeleri ve bu public makbuzu taşır; ürün/test
  baytları final commit'in yeni tam CI'sında yeniden doğrulanacaktır.
