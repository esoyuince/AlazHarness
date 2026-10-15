# REF-PI-002B — Atomik, içerik-duyarlı iş kabulü

15 Ekim 2026. Dal: `alaz/ref-pi-002b-admission-1720`.
İş: aynı anahtarın farklı içerikle sessizce eski işe bağlanmasını önlemek.
Bu belge dar native deney ve Alaz uyarlamasıdır; motor değiştirme veya tam M1/M2 kabulü değildir.

## Önceki paralel çalışmaların uzlaştırılması

İki ebeveyn: `9b801bd93d116223d57320bee379321ab383a6fd` (ac97) ve
`32654e4fbb403847ceec3cfbc94d3d046b84ec86` (4c9f). İkinci dalın bağımsız
kaynak/kanıt dosyaları bu geliştirme dalına alındı. Çakışan üç belge incelenerek
uzlaştırıldı; önceki durum geçmişi `docs/history/` içinde korunur. Yeni worktree
oluşturulmadı; mevcut temiz ac97 çalışma ağacında yeni dal kullanıldı.

ac97, tekilleştirilmemiş safe araç için 2 execute/2 etki olumsuz kontrolü ve
bağımsız SQLite etki sayacı içerir. 4c9f ek olarak commit-sonrası kayıp onay,
provider kimliği ve tamamlanmış sonucun hiç yeni çağrı olmadan geri alınmasını
sınar. Önceki 169/171 standart veya 18/18 native sayıları toplanarak yeni bir
kabul sayısı üretilmez. Eski iki native paket bu işte yeniden yürütülmedi;
birleştirilmiş standart testlerin tamamı ve yeni admission deneyleri ayrı çalıştırılır.

## Uygulanan küçük katman

Kod: `packages/admission/strict-admission.mjs`.

- Girdi ilk await'ten önce pasif, sınırlı, strict JSON anlık kopyasına çevrilir.
- Nesne anahtarları sıralanır; dizi sırası, metin boşlukları ve Unicode kod
  noktaları korunur. Bu proje içi v1 biçimidir; RFC8785 uyumluluğu iddia edilmez.
- Eksik whenBusy, followUp olur; açık null veya bilinmeyen alan reddedilir.
- NaN/Infinity, undefined, bigint/function/symbol, getter, çevrim, seyrek dizi,
  gizli alan, aşırı boyut/derinlik ve bozuk Unicode kabul edilmez.
- SHA256 yalnız kimlik karşılaştırmasıdır. ExecutionScope da parmak izine girer;
  bu alanı güvenilir host tutarlı biçimde sağlamalıdır. Alan kendi başına yetki vermez.
- Conversation kimliği yalnız bağlanılan Harness üzerinden çözülür. Dışarıdan
  verilen yabancı commit callback'i çalıştırılmaz.
- Parmak izi, requestId, submission türü ve native submissionId,
  `alaz.admission.v1` adlı conversation-scoped native document family'de tutulur.
- Parmak izi ve asıl admission tek `Conversation.commit` / `Storage.commit`
  içinde yazılır; ayrı veritabanı, önce-yaz-sonra-gönder kaydı veya ikinci kuyruk yoktur.
- Aynı anahtar ve aynı içerik eski native Submission'ı döndürür. Değişmiş içerik,
  tür veya executionScope `request_payload_conflict` ile reddedilir.
- Parmak izi olmayan eski/raw-native işin içeriği tahmin edilerek kaydı
  doldurulmaz: `unmanaged_or_inconsistent_admission` döner. Göç işlemi ayrıdır.
- Yerel doğrulama veya native kabul hatası callback'i geri alır; boş parmak izi
  kaydı yüzünden sonraki doğru isteğin takılması engellenir.

### Açık bağımlılık sınırı

Pi kök public API'sinde transaction içinde submission kabulünü dışarı veren uygun
bir işlem yok. Bu nedenle upstream değiştirilmeden, sabitlenmiş
`harness/submissions.ts` içindeki `admitSubmission` fonksiyonu enjekte edilir.
Bu **internal, sürüme bağlı bir bağlantı noktasıdır**; kararlı public SDK diye sunulmaz.
`config/admission-compatibility.lock.json` tam commit ve dosya hash'ini sabitler;
launcher ve worker çalışmadan önce doğrular. Sürüm değişiminde yeniden kabul gerekir.
Kuyruk ilerletme için bu dar uyarlama one/one davranışını seçer; genel Pi ayarlarının
birebir aktarıldığı varsayılmaz. Tek model/oturum sahibi hedefi değişmedi.

## Native kabul senaryoları

Runner: `scripts/run_native_admission.py`; worker: `scripts/native_admission_worker.mjs`.
Pi gerçek Harness, transaction, submission ve SQLite motorudur. Model cevapları
Pi fauxProvider; etkili tek araç ayrı yerel SQLite'a sınırlı satır yazar. İnternet
modeli, ücretli çağrı, kişisel profil veya genel shell/web aracı kullanılmaz.

| Senaryo | Zorunlu sonuç |
|---|---|
| canonical-write | Anahtar sırası değişse de aynı iş; içerik/tür/scope değişince conflict; başka conversation ayrı. |
| canonical-input | Gerçek input yinelenmez; çatışma yeni model çağrısı üretmez. Busy reject rollback sonrası anahtar yeniden kullanılabilir. |
| concurrent-same | İki guard nesnesinden aynı Harness'e 20 eşzamanlı çağrı: tek yeni admission, aynı native kimlik. |
| concurrent-conflict | İki farklı içerik, 20 çağrı: kazanan içeriğin 10 çağrısı aynı işi bulur, diğer 10 conflict alır. |
| snapshot-mutation | Çağrı başladıktan sonra değiştirilen JS nesnesi kabul edilen içeriği değiştiremez. |
| legacy-rejected | Parmak izi olmayan eski kabul sessizce eşleştirilmez/güncellenmez. |
| validation-rollback | Native input doğrulaması başarısız olduğunda binding kalmaz; aynı anahtarla doğru iş alınır. |
| fault-before | Gerçek commit öncesi enjekte hata: failed session, yeni süreçte 0 kabul/0 binding; retry sonrası bir çift. |
| fault-after | Gerçek commit sonrası onay hatası: yeni süreçte 1 kabul/1 binding; retry aynı kimliği bulur. |
| kill-before | Native commit sınırından önce zorla süreç sonlandırma: iki kayıt da yok; güvenli yeniden kabul. |
| kill-after | Commit tamamlandı, onay verilmedi: zorla sonlandırma sonrası iki kayıt da var; yeni iş yok. |
| kill-unsafe-effect | Kabul ve dış etki var, araç sonucu yokken kill: aynı işi bul, unsafe aracı tekrar yürütme, interrupted kaydını koru. |

Her koşu yeni SQLite dizini ve nonce kullanır. Üst Python süreç yalnız oluşturduğu
Node çocuğunu kapatır; kesin PID/nonce/senaryo/bariyer doğrulanır. Çıkış beklenmeden
yeni depo sahibi başlatılmaz. Ara ve son veritabanları üst süreçte salt okunur
incelenir: integrity=ok, submission/binding çiftinin birlikte varlığı/yokluğu ve
bağımsız dış etki sayısı. Başlangıç/bitiriş zamanları, gerçek exit kodu, kasıtlı
kill ve temiz son kapanış ayrı makbuzlanır. Modelin söylediği başarıya dayanılmaz.

## Sınırlar

Bu katman tek canlı Harness sahibinin mutation sırası altında atomiktir.
Eşzamanlı 20 çağrı, 20 ayrı yazıcı süreç anlamına gelmez. Pi store üzerinde
çok süreçli kilit/fencing eklenmedi. Raw native submit yolu yakalanmaz; ürün
entegrasyonunda dış girdiler mutlaka bu host sınırından geçmelidir.

ExecutionScope'un gerçek izin/model ayarıyla tutarlı olması host sorumluluğudur.
Bu kimlik kontrolü sandbox, yetki motoru, bütçe rezervasyonu veya session auth
mekanizması değildir. Parmak izi kayıtlarının silinmesi/retention'ı ve eski işler
üzerinde göç politikası henüz uygulanmadı. Bir requestId'nin fingerprint'ini
requestId'ye ekleyip farklı içerikle otomatik yeni iş yaratılmıyor.

Dış etkide exactly-once garantisi verilmez. Unsafe kesitte testin tek dış etkisi
korunur ve belirsizlik açık kalır; başka bir modelin hata sonrası yeni tool çağrısı
istemesini engelleyen genel üretim politikası bu pakette kurulmadı. SQLite
WAL/NORMAL ortamında süreç kill sınandı; elektrik, kernel veya fiziksel disk
arızası kabulü değil. Host izolasyonu yalnız deney dosya/profil düzenidir.

## Tekrar üretim

```powershell
cd C:\Antigravity\AlazHarness\scratch\worktrees\ref-pi-001-ac97
python -B scripts/run_native_admission.py --source-workspace C:\Antigravity\AlazHarness --prepared C:\Antigravity\AlazHarness\runtime\pi-ref001-ac97 --output C:\Antigravity\AlazHarness\runtime\admission-new --repeats 2
python -B -m unittest discover -s tests -v
python -B scripts/ci_check.py
```

Output yeni olmalıdır. Native komut yeni dependency kurmaz. Hazır ortamın kaynak
commit'i, package-lock'u ve iç API dosyası doğrulanır. Deney boyunca program
hash'leri değişirse kabul reddedilir. CI sadece standart host/kanıt testlerini
çalıştırır; Pi motorunu indirmez veya native deneyleri çalıştırmaz.

## Kanıt ve kabul durumu

Kesin sayılar `evidence/ref-pi-002b/local-validation.json` ve
`evidence/ref-pi-002b/native-suite.json` içinde; test dosyaları kendi makbuzlarının
hash'leriyle eşleşir. `initial-failures.json` geliştirme sırasındaki hataları korur.
İlk bağımsız sorgu, Pi'nin kind sütununu JSON kodlaması nedeniyle yanlış saydı;
record JSON çözülerek düzeltildi. Host testleri açık null seçeneği ve kaçış sonrası
byte sınırındaki iki hatayı yakaladı; ölçütler gevşetilmeden kod düzeltildi.

Dar kapsamlı atomik admission kabulü ile genel Pi benimsemesi ayrı kararlardır.
Tam M1/M2 açık; Hermes/OpenClaw motoru değiştirilmedi. Sonraki iş REF-OC-001:
OpenCode izin/olay sınırını ölçmek, sonra mevcut dört kaynaktan tek çalışma
çekirdeği/tek oturum sahibi için kısa ve kanıta dayalı bileşen kararını vermek.
Ayrı eski Pi Agent dalı c31cf19 bu Durable uzlaştırmasının parçası değildir.

## Final yerel sonuç ve bağımsız kapanış

Son dosya hash'leri üzerinde standart248/248 PASS (32.709s, exit0); gerçek admission
12 senaryo×2=24/24 PASS ve6 owned process kill. Bağımsız QA kaynakları okunup yeniden
çalıştırıldı: owner6 + atomic6 =12/12 PASS, exit0. Bu üç ayrı kapsam bir toplamda
birleştirilmez. İlk adayda yabancı Harness handle P1'i, bağlı Harness üzerinden
sayısal kimlik çözümüyle kapandı. SQLite reader ömür hatası explicit closing ile
kapatıldı; tam248 test yeniden geçti. Eski bağımsız rapor ve FAIL makbuzları
aynen korunur; bunlar final adayın açık hata listesi değildir.

Final native kanıt: evidence/ref-pi-002b/native-suite.json. Bağımsız yeniden
çalıştırma: independent-qa-recheck.json. Eski eleştiri/öneri: ref-pi-002b-qa.
Yerel kabulün sunucu CI'sı commit/push sonrası ayrıca doğrulanır.
