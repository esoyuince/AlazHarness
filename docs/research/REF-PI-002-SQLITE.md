# REF-PI-002 — Gerçek Durable / SQLite kesinti deneyleri

15 Ekim 2026. Dal: `alaz/ref-pi-002-durable-ac97`.
Başlangıç: `a39a1ea08e108246463c983cc210975c9012364b`.

**Dar deney paketi tamam: 9 senaryo × 2 tekrar = 18/18 PASS.**
**Değiştirilmeden ürün içine benimseme: NOT ACCEPTED.** İçerik çakışması ve
bağımsız dış işlem tekilleştirmesi için Alaz tarafında ayrı sözleşme gerekiyor.
Bu sonuç, bütün M1'i veya otonom öğrenmeyi tamamlamaz.

## Gerçek olan ve taklit edilen

Pi `b06c1f2cf1dea6af8748ddeee18c23587d2cb7c6` kaynağındaki gerçek `Harness.open`,
Conversation/Submission, görev zamanlayıcısı, kayıt işlemleri ve Node SQLite
adaptörü kullanıldı. Kaynak dosyaları değiştirilmedi; önceki kilitli hazırlanmış
ortam yeniden kullanıldı. Yeni kurulum veya kişisel ajan profili erişimi yok.

Model tarafında Pi'nin kendi `fauxProvider` modeli açıkça programlandı. Genel
web/shell/hesap aracı verilmedi. Tek araç, bu deneye özel `ledger_effect`: ayrı
bir SQLite veritabanına sınırlı bir satır yazıyor. Bu sentetik bir iş ama **gerçek
kalıcı dış etki**; harness veritabanıyla aynı transaction içinde değil. Model
çıkarımı ve ücretli servis çağrısı sıfır. Gerçek HTTP sağlayıcı testinin yerine
geçmez; o sınır önceki REF-PI-001'de farklı kapsamda ölçülmüştü.

Python üst süreç yalnız başlattığı Node çocuğunu tanır. Hazırlık bildiriminin
scenario/nonce/PID/root/submission kimliğini doğrular, ilgili noktada çocuğu
zorla kapatır, çıkışını bekler, dış sayaçları salt okunur sorgular ve ancak sonra
**yeni Node sürecinde** aynı harness veritabanını açar. Beş kesinti senaryosu iki
tekrarda toplam **10 gerçek process kill** içerir. Bunlar graceful close/reopen
ile aynı şey değildir; fakat bilgisayarın elektriğinin kesilmesi de değildir.

Hazırlık bildirimi geçici dosyaya yazılıp fsync sonrası atomik yeniden adlandırma
ile görünür olur. İlgisiz PID öldürülmez. Her testin ayrı SQLite/veri dizini,
nonce'u, süreç çıkış kodları ve sonunda bağımsız sayaç doğrulaması vardır. Aynı
veritabanına iki canlı harness yazarı açılmaz. Timeout başarı sayılamaz.

## Sonuçlar — aşağıdaki sayılar tek tekrar içindir

| Senaryo | Araç giriş / dış etki | Ölçülen sonuç |
|---|---|---|
| duplicate-reopen | 0 / 0 | Aynı write ve gerçek input kimliği yeni süreçte korunur. Değişmiş payload eski işi döndürür; tür değişimi reddedilir. |
| before-effect | 1 / 1 | Kabul kaydından sonra model yanıtı verilmeden süreç kesilir. Yeniden açılınca tek araç etkisiyle tamamlanır. |
| unsafe-effect | 1 / 1 | Etki commit edilmiş, native araç sonucu dönmemişken kill. Unsafe araç yeniden yürütülmez; interrupted araç sonucu kaydedilir. |
| safe-effect | 2 / 2 | Aynı kesitte safe etiketli fakat tekilleştirmesiz fixture yeniden çalışır ve ikinci etkiyi üretir. Beklenen olumsuz kontrol. |
| idempotent-effect | 2 / 1 | Safe tekrar gerçekleşir; dış SQLite UNIQUE görev anahtarı aynı etkiyi ikinci kez yazdırmaz. |
| after-result | 1 / 1 | Native araç sonucu kaydedildikten sonra final model yanıtı öncesinde kill. Kaydedilmiş araç sonucu yeniden kullanılır. |
| wait-cancel | 1 / 1 | Bekleyicinin iptali çalışmayı durdurmaz; araç bırakılınca iş tamamlanır. |
| task-cancel | 1 / 0 | Yerleşmiş submission'ın abort'u already_placed; conversation abort gerçek aracı iptal eder, dış etki oluşmaz. |
| storage-failure | 1 / 0 | Commit sınırına enjekte edilen hata oturumu failed kapatır, bekleyiciyi/sonraki işi reddeder. Yeni açılışta hayalet yazı yoktur. |

`unsafe-effect` ve storage-failure sonrası programlanmış model son mesaj üretebilir;
submission'ın done olması kayıp/belirsiz araç etkisinin kullanıcı işi açısından
başarılı olduğu anlamına gelmez. Hata/interrupted araç kaydı ayrıca denetlenir.

## İki belirleyici ürün farkı

### 1. RequestId eşitliği, içerik eşitliği değil

Hem `write` hem gerçek `input` için aynı kimlik farklı içerikle tekrar gönderildi.
Pi eski submission kimliğini döndürdü, eski içeriği korudu ve yeni model çağrısı
yapmadı. Aynı anahtarla farklı submission türü gönderilmesi reddedildi.

Bu, kaynakta `submissions.ts:161–185` ile tarif edilen davranış; rastgele bir
upstream bug olarak raporlanmıyor. **Bizim şartımız ise aynı kimlik + farklı
istek içeriği için açık conflict.** Bu şart mevcut native davranışla sağlanmıyor.
Körce yeniden iş başlatmak çözüm değildir. Girdi, araç kapsamı ve ilgili seçenekler
kanonik biçimde parmak izine dönüştürülüp kabul ile tutarlı kalıcı tek yerde
karşılaştırılmalı. Bu paket henüz bu üretim katmanını uygulamıyor.

### 2. Safe işareti, dış etkide exactly-once garantisi değil

Safe yalnız tekrarın denenebileceğini bildiriyor. İki giriş/iki etki üreten
olumsuz kontrol bunu gerçekten gösterdi. Dış sistemde UNIQUE anahtarı kullanan
örnekte iki giriş/tek etki elde edildi. Bu koruma **bizim fixture'ın dış veritabanına
aittir**, Pi'nin bütün dış servisler için verdiği garanti değildir.

Gerçek adaptörler için anahtar agent/run/tool/işlem kapsamıyla çakışmasız olmalı;
dış işlem yeniden sorgulanamıyorsa durum unknown tutulmalı. Güvenli olmayan etki
bilinmeden yeniden yürütülmemeli. Aynı oturum için ikinci bir kayıt yazarı eklenmez.

## Hata ve güven sınırları

Storage failure, gerçek SQLite Storage.commit çağrısından önce test sarmalayıcısının
bir kez hata atmasıdır. Disk dolması, WAL bozulması veya fiziksel disk arızası
simüle edilmedi. Başarısız kabulden sonra uncommitted-note yokluğu, pending wait'in
reddi, failed kapanma ve yeni süreçte yeniden yazabilme ayrı denetlendi.

Pi SQLite adaptörü WAL ile synchronous=NORMAL kullanıyor. Bu çalışma süreç
kesilmesini sınar; güç kaybı dayanıklılığı veya çok yazarlı dağıtık kilit kanıtı
değildir. İzole HOME/veri dizini işletim sistemi sandbox'ı değildir. Dış ağ
engellemesine veya gerçek model güvenliğine dair kapsam dışı garanti verilmez.

## Test düzeneği düzeltmeleri

İlk denemede Windows --import için C: yolu yerine file URI gerektiği görüldü.
İkinci denemede kendi fixture'ımız TaskId'yi string sandı; kaynak `types.ts:19–24`
kaydın sayısal kimlik olduğunu gösteriyor. Number.isSafeInteger doğrulaması ve
fixture dış anahtarı için açık string serileştirme kullanıldı. Upstream kodu veya
istenen başarı ölçütü bu hataları gizlemek için değiştirilmedi. Başarısız ilk
kayıtlar runtime içinde tutuluyor; kabul toplamına eklenmediler.

## Yeniden çalıştırma ve kanıt

Aktif çalışma ağacı: varsayılan kökte `scratch/worktrees/ref-pi-001-ac97`.
Dizin adı önceki paketinden korunmuştur; güncel dal farklıdır.

```powershell
python -B scripts/run_durable_sqlite_probe.py --source-workspace C:\Antigravity\AlazHarness --prepared C:\Antigravity\AlazHarness\runtime\pi-ref001-ac97 --output C:\Antigravity\AlazHarness\runtime\durable-new-run --repeats 2
```

Output yeni olmalı. Komut otomatik kurulum yapmaz, kişisel key/proxy/Node değişkenlerini
çocuğa taşımaz. Her seed/resume ayrı süreç makbuzuyla raporlanır. Ham SQLite dosyaları
ve loglar Git dışı `runtime/pi-durable-ref002-ac97/acceptance-01` altında kaldı.
Paylaşılabilir kayıtlar `evidence/ref-pi-002-sqlite/` içinde:

- native-suite.json: 18 koşunun süreç kimliği, sınır, dış sayaç ve native sonucu.
- source-custody.json: kaynak pinleri ve worker/runner hashleri.
- initial-fixture-failures.json: önceki başarısız düzeneğin kapsamı ve düzeltmesi.
- local-validation.json / root-unittest.txt: 171/171 standart test PASS.

25 yeni standart test yalnız kanıt/kimlik/sayaç ve salt-okunur sorgu korumalarıdır.
171 standart teste 18 native deneyi ekleyerek yeni bir toplam üretmiyoruz. Mevcut
Linux CI bu native SQLite/Pi senaryolarını kurup çalıştırmaz; yerel Windows native
kanıtı ayrıdır. Son commit'in CI sonucu push sonrası ayrıca okunur.

## Sıradaki adım

REF-PI-002B: native kabulün üzerine küçük, kalıcı içerik-çakışma denetimi
ve dış etki sözleşmesi; aynı testler bu kez Alaz şartına göre çalışmalı. Benimseme
ancak doğru conflict, belirsiz etki koruması, kaynak sınırı ve tek-yazar sahipliğiyle
kararlaştırılır. OpenCode REF-OC-001 ve gerçek hibrit Gateway kapıları açık kalır.
Paralel 4c9f dalı bu paketle otomatik birleştirilmedi; kayıtlar/test sayıları ayrı
kalıyor. Tam M1/M2 veya motor değişimi onayı verilmedi.
