# AlazHarness — T143 / R144 yayın devam kaydı

## IN PROGRESS — Tam regresyon doğrulandı; tek yayın sahibi bu T143 dalıdır

Çalışma: `alaz/d3b-retained-exec-t143a7`.
Yol: `C:\Antigravity\AlazHarness\scratch\worktrees\d3b-retained-exec-t143a7`.
Başlangıç/main: `802910552bc4c804348d4c604fbae8130a45f5ed`.
H143 bağımsız QA dalına dokunulmaz; alternatif codec tekrar eklenmez.

### Kesinti sonrası doğrulanan durum

Tam test 3566: 3543 PASS, 23 SKIP, 0 hata/başarısızlık, çıkış 0.
`full001/result.json` ile ham test günlüğü ve 625 kaynak + 11 yama özeti eşleşiyor.
Önceki 620 kaynağın tamamı değişmeden kaldı. 23 atlamanın kimliği/gerekçesi aynı.
Bu tur tam test ve gerçek Linux deneyleri yeniden başlatılmadı.

Ürün yalnız yeni `gateway_retained_handoff.py`: mevcut üç typed expectation için
sınırlı kanonik JSON, zorunlu ayrı trusted expected_home; projected wrapper fixedTARGET.
JSON kimlik doğrulama veya kernel/çalıştırma yetkisi değildir. Asıl owner tüm canlı
lease/mount/schema/epoch kontrollerini sürdürür. Yeni signer/manager/scheduler yok.

Normal ve kontrollü hata: gerçek ordinary-user Linux os.execve, aynı PID/startticks,
yeni yorumlayıcı ve boş registry. Eski sonuç/usage replay hesaplanmaz; yeni iş bir kez
çalışır. Native sonuçlandırma, iki normal owner kapanışı/3 fiziksel bağlantı ve
caller lease release doğrulandı. Model factory/compute/close test dublörü.
Kernel izolasyonu, fixedTARGET exec entegrasyonu, HTTP, çökme/güç kaybı ve gerçek
model/araç/hafıza/bütçe kabulü hâlâ açık. Önceki reddedilen root işlemleri denenmez.

### Yayın sırası ve koruma

Önce statik kontrol ve yalnız seçili dosyalarla commit; sonra outgoing tarama ve
exact-SHA branch push; aynı SHA CI başarı + canlı main/ancestry kontrolü olmadan
main ilerletilmez. Force-push/squash/install/service/provider işlemi yok.
Root 33 kullanıcı dosyası, kurulu native eb75627 ve optional d151 korunuyor.
Bu devam turu R144 yalnız T143 yayınını tamamlar; H143 tekrar ürün sahibi olmaz.

### Kanıt ve devam

`docs/D3B-RETAINED-EXEC-T143A7.md`;
`evidence/d3b-retained-exec-t143a7/full001/` ve `resume-r144c7/`.
Önceki status: `docs/status-history/t143a7-prepublication-r144c7.md`.
İşlemlerin makbuzu/kimliği sonuç belirsizliğinde okunur, körlemesine tekrar yok.


### Live final writer resolution: R144C7 publishes, R144C8 read-only

Stable peer single-writer-review.json explicitly names original T143/R144C7 sole
publisher and forbids future handoff. Original provisional reciprocal yields are
superseded. R144C7 acquired exclusive scratch/task-claims/t143-publication-r144.json
before index mutation; R144C8 tree remains untouched. Exact frozen T143 package
only; no source edits, full/native replay, root/service/provider changes.
