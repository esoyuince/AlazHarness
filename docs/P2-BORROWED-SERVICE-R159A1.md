# P2 / R159A1 — Native yerel transport ve servis sahibi

## Teslimatın sınırı

Bu paket, R159 planının **native transport, somut servis sahibi ve kuyrukta
iptal kanıtı** bölümünü tamamlar. P1 DONE; P2 IN PROGRESS; P3–P5, tam D3B,
M1 ve production OPEN kalır. Günlük kurulu ürünün `start/close` girişleri,
uzun ömürlü supervisor/control kanalı, yeni P2 kurulumu ve gerçek model görevi
bu kaynak kabulüne dahil değildir. [R159 planı](P2-BORROWED-SERVICE-R159A1-PLAN.md)
bu açık kapıları korur.

Harness başlangıcı `37620d5c14afee895b16e3441f7a7ed14b77e7d7`; native başlangıcı
`d1516731308de8e87130dc68124e69aad35d6911`, yeni native kaynak
`5e3635c2cdfc2161fd20c089618bd7f2a7c12f2d` olur. İki depo da ayrı
`alaz/p2-borrowed-service-r159a1` çalışma ağacında geliştirilir. Native değişiklik
yalnız feature dalında yayınlanır; fork main ve upstream main korunur. Harness
yayını, son commit için gerekli CI geçtikten sonra normal fast-forward yoludur.
Git yayını mevcut kuruluma dağıtım değildir.

## Çalışan kaynak davranışı

`BorrowedHTTPTransport`, hazırlanmış özgün runner, API adapter, authority,
epoch/instance, üç store ve aynı event loop üzerinde açıkça oluşturulur.
`127.0.0.1` dinleyicisi, açık kimlik doğrulama anahtarı ve tek açılış denemesi
kullanır. Native yüzey run sorgusu, events ve Stop ile sınırlıdır; Host Gate
kendi issue/dispatch/request yollarını ekler. Cron, ordinary reconnect,
sweeper veya heartbeat yaşam döngüsü başlatılmaz. Borrowed metrics varsayılan
profilin status dosyasına yazmaz; ordinary metrics davranışı korunur.

`BorrowedServiceOwner`, mevcut `NativeStoreStartup` ve consumer'ın özgün
sahipliğine bağlanır. Gerçek PluginContext, tek model politikası, execution
boundary ve broker zorunludur. Yeni iş, ancak **bütün servis READY** iken
Host Gate'in SQL yazma noktasındaki kimlik/evre kontrolünü geçer. Native portun
tek başına bağlanmış olması yeterli değildir. Başlangıç sonrası kaynak veya
hazırlık kontrolü başarısızsa servis UNKNOWN yapılarak dışarıdan yeni iş kabulü
kapatılır; özgün native admission mühürlenmeye çalışılır. Mühürleme de
doğrulanamazsa ayrı hata nedeni kaydedilir ve özgün sahip tutulur. Salt durum
sorgusu da kaybolmuş kimliği veya evreyi READY
göstermeyi sürdürmez.

Drain yeni işleri kapatır, mevcut işe ilişkin sorgu ve Stop erişimini korur.
İptal edilen HTTP gözlemcisi, içerideki shielded handler'ı veya onun beklediği
SQLite thread işini tamamlanmış saydırmaz. Dinleyici retirement'ından önce
HTTP handler'ları, native physical worker'lar, canonical ledger yükümlülükleri
ve gerçek native session gözlem abonelikleri boş olmalıdır. Ön etkisiz busy
reddi DRAINING durumunu korur; etkisi başlamış setup/cleanup belirsizliği
UNKNOWN olarak sahipliği tutar.

Somut servis sahibinin normal kapanış sırası: admission seal ve bütün idle
kapıları → listener retirement → runtime/API retirement → drain/detach →
özgün loop executor'ının tamamlanması → üç gerçek fiziksel store close →
özgün profile lease finish. **Image lease bu sınıfın yetkisinde değildir**;
gelecek supervisor bağlantısı kendi stop/finish sırasını ayrıca kanıtlamalıdır.

## Kuyrukta iptal düzeltmesi

Eski native Stop yolunda, `cancel_queued` producer bekleyicisini çözüp media
release beklerken producer retirement tamamlanabiliyordu. Stop daha sonra
`_stopping_run_ids` işaretini yeniden ekleyerek kapanışı gereksiz yere açık
bırakıyordu. Yeni queued dalı bu geç işareti eklemez.

Canonical SQL sorgusu, yalnız cancelled ve generation değeri null olan aynı
admission/run/session için güncel epoch/instance bağını ve aynı SQL snapshot'ında ilgili managed
worker kaydının bulunmadığını doğrular. Hiç başlatılmamış admission anlamı,
değişmeyen canonical null-generation sözleşmesiyle birlikte değerlendirilir. Yanıtın dokuz alanlı
`canonical_queued_cancellation` kanıtı istemcide tam şema ve kimlik eşleşmesiyle
denetlenir. Bozuk kanıt, çelişkili terminal bayrakları veya tek başına null
generation başarıya yükseltilmez.

İstemci bunu sunucunun admission'a özel raporu olarak gösterir:
`noWorkerStartedReported: true` mümkün olur, fakat `canonicalVerified` ve
`physicalWorkerTerminalVerified` false kalır. Stop ACK tek başına terminal
kanıt değildir; aynı run ayrıca gözlenir. Yeniden gönderme veya repair izni
üretilmez; eksik kullanım/maliyet sıfır gösterilmez.

## Kaynak seçimi ve tarihsel kabul

Yeni opt-in seçim, ayrı 760 dosyalık manifest ve aynı native commit'e bağlı
beş dosyalık Host Gate sınır kilidini kullanır. Retained manifest'in 756
dosyasına `agent/secret_sources/command.py`, authority-runs, borrowed transport
ve metrics modülleri eklenir. Değişmiş altı mevcut native dosyanın hash'i yeni
manifest'te güncellenir. Eski finite/retained manifest'ler, varsayılan Host Gate
kilidi ve execution kilidi değiştirilmez.

760 dosyanın hash kontrolü ve dört ek modülün doğrudan import incelemesi
**statik kaynak kapanışıdır**. Yeni ürün kurulumunun paketlenmesi, Node/runtime
bağımlılıkları ve gerçek seçilmiş modelin bütün lazy import yolları için
kurulum kabulü yapılmış sayılmaz.

Değişen dokuz ürün kaynak dosyasının tam parent Git blob'ları ayrı arşivlenir.
Tarihsel resolver yalnız sabit dosya adı ve beklenen eski hash eşleşince bu
arşive gider; yeni/yanlış hash'i kabul etmez. Önceki receipt sonuçları veya
beklenen eski digest'ler yeniden yazılmaz. Bu arşivler eski kabulün kimliğini
korur; yeni kaynağı kabul etmez.

## Doğrulama

| Kontrol | Sonuç | Kanıtın kapsamı |
|---|---|---|
| Yeni native lifecycle/queued testleri | 27 PASS; 22 transport + 5 queued | Gerçek native üç store, authority, loopback HTTP, worker/SQL/observer sınırları |
| Seçilmiş mevcut native testleri | 34 PASS; 8 bind + 23 drain + 3 metrics | Ayrı resmi runner çağrıları; bütün native test paketi değildir |
| Native Ruff | PASS, exit 0 | Resmi `scripts/check --only ruff` |
| Native source-health | 11 dosya; 0 blocking, 0 advisory | Tam parent/current blob'ları ve pinned araç sürümü |
| Host servis testleri | 31 PASS | Gerçek harness guard/SQLite/thread; native lifecycle arayüzleri double |
| İstemci ve recovery | 58 PASS; 31 CLI/HTTP + 18 recovery + 9 queued | HTTP fixture/protokol; eski logda launcher/interpreter/exit kaydı yok |
| Tarihsel kaynak/provenance | 12 PASS | Altı yeni ve altı R158 arşiv bütünlüğü/tamper testi |
| Eski queued hedefle regression | Beklenen 2 FAIL; 3 deselected | Yalnız d151 authority-runs geri kondu; güncel supporting source kullanıldı |

Native testler resmi `scripts/run_tests.sh`, tek worker ve sıfır retry ile
çalıştırıldı. Test-home izolasyonu runner'ın env temizlemesi sonrasında native
conftest ve test fixture'larından gelir. Eski hedefle iki kırmızı test,
yeni proof assertion'larına ulaşmadan stranded stopping-marker kusurunda
başarısız olur; aynı senaryolar güncel yeşil koşudadır.

İlk denemelerde eksik export helper'ları, iki özgün gate'in yanlış tek kimlik
sayılması, transaction içinde kilitleyen property erişimi, busy istisna türü
ve gözlem aboneliği sınırı bulundu ve düzeltildi. Başarısız çıktılar ile son
yeşil sonuçlar ayrı korunur. Eksik `tools.bot_failure_reasons` özgün Git
blob'undan tamamlandıktan sonra mevcut active-work dosyası 23/23 geçti.

Kısmi cloud export'taki geniş host regresyon koşusu 118 method çalıştırdı:
117 başarılı, bir method error ve sayıya dahil olmayan bir class-setup error.
İki hata eksik tarihsel evidence dosyalarındandır; bu koşu PASS diye kaydedilmez.
Tam primary çalışma ağacı ve son commit CI sonucu yayın kaydında ayrıca yer alır.

## İlk tam CI ve tarihsel test onarımı

İlk kaynak commit'i `a4d290441b88afc8eb9bd8193a03c72475bb051f` için tam CI,
4.084 testte 4.060 başarılı, 2 başarısız, 22 atlanan ve sıfır error ile bitti.
İki başarısızlık, R140 tarihsel receipt hash'lerinin değişmiş güncel dosya
byte'larıyla karşılaştırılmasından kaynaklandı. Ana dal R158 parent'ında kaldı.
Özgün başarısız CI logu ve metadata'sı `initial-ci-failure.json` ile işaretlenen
ham dosyalarda aynen saklanır; sonuç PASS olarak yeniden yazılmaz.

Onarım yalnız iki test yönteminin kaynak nesli seçimini değiştirir. Kayıtlı eski
hash, mevcut katı R159 resolver üzerinden tam Git arşiviyle doğrulanır. Güncel
canlı kaynak ayrıca hash'lenir ve eski baseline'dan farklı olduğu doğrulanır.
Arşiv seçilen değişmiş dosyalarda ayrıca canlı hash'in receipt neslinden farklı
olduğu ve güncel digest'in eski arşivi seçemediği denetlenir.
Eski receipt, beklenen digest, sonuç veya ürün/native/config kaynağı değişmez.
İki onarılmış yöntem ve altı provenance testi Linux'ta 8/8 geçti. Tam R140
modülü ile R158/R159 provenance modülleri primary Windows'ta 22/22 geçti;
ikisinde de failure/error/skip sıfır ve gerçek process exit 0 oldu.

Bu onarımın bağımsız incelemesi ve ham test kayıtları ayrıca saklanır. Son
onarım commit'inin tam CI kabulü, normal main yayını ve yayın sonrası doğrulama
sonuçları aşağıdaki final publication journal'dan okunmalıdır. Hedefli testler
kurulu günlük servis, yeni Linux restart, gerçek model veya production kabulü
anlamına gelmez.

## İkinci tam CI ve test dosyasının tarihsel nesli

İlk onarım commit'i `e25c2cc063d4c595ddbb5b7a62c069453d5971d9`, önceki iki
R140 hatasını giderdi. Tam CI bu kez 4.084 testte 4.061 başarılı, 1 başarısız,
22 atlanan ve sıfır error bildirdi. Değişmeyen L145 kabul testi, 625 eski kaynak
hash'i içinde onarılan R140 test dosyasının da eski neslini doğruluyordu.
Bu başarısız koşunun özgün metadata/logu `second-ci-failure.json` üzerinden
ayrıca korunur; ana dal bu aşamada da önceki kabul edilmiş sürümde kaldı.

Çözüm, R159'un katı tarihsel arşiv eşlemesine yalnız o testin tam parent Git
blob'unu eklemektir. 7.789 byte'lık eski test hem `37620d5` hem `a4d2904`
sürümünde aynı SHA-256 ile doğrulandı. Böylece arşiv kümesi dokuz ürün kaynağı
ve bir test nesli olarak ona çıktı. Eski dokuz kayıt aynı kaldı; resolver
fonksiyonunun gövdesi, güncel R140 testi ve L145 testi değiştirilmedi. Mevcut
altı provenance yöntemi, güncel/bilinmeyen hash'in arşivi seçememesini ve
arşiv kaybı/bozulmasının reddini artık bu onuncu kayıt için de doğrular.

Genişleyen arşivle hedefli Linux koşusu 8/8, primary Windows'ta R140, L145 ve
iki provenance modülünün ortak koşusu 28/28 geçti; failure/error/skip sıfır.
İlk 28-test kaydı bağlantı yenilenmesi sırasında terminal makbuzunu kaybettiği
için ayrıca korundu; önceki test sürecinin kapandığı doğrulandıktan sonra yapılan
bağımsız 28-test koşusunda gerçek process exit 0 kaydedildi. Bu kabul eski
kayıtların kaynak kimliğini korur; yeni runtime veya kurulu servis kabulü
üretmez. Son commit'in tam CI ve normal main yayın sonucu final publication
journal'da ayrıca doğrulanmalıdır.

## Kanıtlar ve yayın kaydı

Kanıt dizini: [evidence/p2-borrowed-service-r159a1](../evidence/p2-borrowed-service-r159a1).
Başlıca kayıtlar: `baseline.json`, `native-lifecycle-tests.json`,
`native-source-checks.json`, `native-code-health.json`, `host-service-tests.json`,
`client-control-tests.json`, `historical-source-review.json` ve
`source-selection-review.json`. Ham son koşular ve önceki hata kayıtları
aynı dizinde tutulur. Native commit/push kaydı `native-publication.json` içindedir.

Son harness commit, feature/main ref'leri, gerekli CI, sahip olunan dosya
hash'leri ve korunmuş çalışma ağaçları, primary R159 çalışma ağacındaki
`scratch/r159a1-publication/final-publication.json` ile doğrulanır. Bu ignored
journal, kendi commit'inin hash'ini aynı commit'e yazma döngüsünü önler.

## Kesin sonraki adım

Mevcut finite supervisor protokolü tek terminal stdout sonucunu child çıktıktan
sonra alır; çocuk süresi ve mount worker idle sınırı günlük servise yetmez.
Önce açıkça uzun ömürlü supervised child sahibi, ready/control/final-receipt
kanalı ve süre sınırları tasarlanıp uygulanmalıdır. CLI `start/close` bu gerçek
sahibe bağlanmalı; kapanan HTTP listener'dan gelen ACK, son child/store/image
kapanışı yerine kullanılmamalıdır.

Ardından ayrı P2 kaynak/bağımlılık adayı ve yeni kurulumda aynı native günlük
akış kabul edilir. Sonraki gerçek model denemesinden önce tek route/model,
izinli küçük `.txt` dosyası ve çağrı/token/mikro-USD tavanları somut seçilir.
Bu pakette provider/model çağrısı sıfırdır; mevcut R156 kurulumu değiştirilmez.
P2 ancak bütün günlük akış ve o sınırlı gerçek görev kabul edildiğinde kapanır.
