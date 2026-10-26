# R156A1 — Sabit girişten sonlu native görev akışı

## Durum

**Yeni kurulum ve aynı imajda sınırlı native finite kabul: PASS.** R155'teki
özgün supervisor, retained projection ve native sahiplik yoluna ayrı bir sabit
görev girişi eklendi. Yeni kurulumda seed epoch 1, tek finite child epoch 2,
normal görev, birebir tekrar, yeni görev, kontrollü hata ve özgün normal kapanış
birlikte doğrulandı. Son kaynak/kanıt commit'inin CI ve main yayını bu raporun
native kabul checkpoint'inde bekliyor; nihai durum `status.md` ve exact-SHA
publication kaydından okunur.

**Model factory, hesaplama ve model close açık scripted fixture'dır.** Gerçek
sağlayıcı çağrısı sıfırdır. Bu başarı genel kullanıcı görevini, gerçek modeli,
broker alışverişini, restart replay'i, tam P1/D3B/M1 veya production'ı kabul etmez.

Başlangıç commit'i: `4823ebbca5f039aee1e9a4a209e40a48c015044a`.
Kurulan runtime kaynak commit'i: `e641a5000810efb2a453ae847f689b422f7d41a7`.
Native kaynak: `d1516731308de8e87130dc68124e69aad35d6911`.
Çalışma dalı: `alaz/m1-finite-product-r156a1`.
Önceki kabul: [R155A1](M1-SEED-READINESS-R155A1.md).
Güncel devam kaydı: [status.md](../status.md).

## Bağlanan akış

Yeni giriş, özgün `RetainedVolumeSupervisor` üzerindeki `run_finite` işlemidir.
Readiness ve finite işlemleri aynı tek çocuk deneme kaydını paylaşır. Tamamlanan
veya sonucu belirsiz bir denemeden sonra ikinci çocuk başlatılmaz.
`observe_finite` yalnız ilk çocuğu gözler; girdi yeniden gönderilmez.

Sabit supervised giriş `run_supervised_finite.py`, özgün cgroup katılımı ve
mount namespace denetimlerinden sonra sabit `run_finite_projected.py` hedefine
geçer. Çalıştırılacak dosya, komut, model veya serbest prompt istekten alınmaz.
Projected transfer, ayrı protokol ve ortam alanlarıyla work hash'ini, önceki
retained kaydı, PID'yi ve mount beklentisini bağlar. Mevcut readiness transferi
ve readiness-only sonuç alanları korunur.

Son hedef şu özgün yaşam döngüsünü kullanır:

1. Caller-held `ProfileLease` ve `NativeStoreStartup`; altı startup kontrolü.
2. Aynı üç store ve bağlantıyla `PreparedRuntimeConsumer`.
3. Canonical API adapter publication ve yerel admission aktivasyonu.
4. Native `run_api_turn`, authority scheduling, physical worker ve sonuç settlement.
5. Özgün drain, runtime/session retirement, detach, fiziksel store close ve caller lease finish.
6. Üst süreçte aynı çocuğun terminal durumu, cgroup ve worker kontrolü; ardından özgün volume stop/finish.

Event loop üzerindeki ek görevler ve idle executor, store ve caller lease
bırakılmadan önce denetlenir. Süre aşımı native görevi iptal etmez; aynı task,
loop, consumer, owner ve lease referansları saklanır. Belirsizlikte otomatik
retry, forced close, registry temizliği veya lease bırakma yoktur.

## İlk kabulün dört vakası

| Vaka | Native istek kimliği | Beklenen davranış |
|---|---|---|
| Normal A | Yeni request ID | Worker içinde sınırlı hesaplama; sonuç `50`; native terminal `completed`. |
| Birebir tekrar A | Aynı session, request ID ve içerik | Aynı admission ve kayıtlı sonuç; hesaplama sayısı artmaz. |
| Yeni B | Yeni request ID | İkinci bağımsız admission ve hesaplama; sonuç `7`. |
| Kontrollü hata C | Üçüncü request ID | Model fixture'ındaki hata özgün native `failed` sonucu olarak kaydedilir; normal drain/close tamamlanır. |

Dört API gözlemi için üç model-fixture çalışması beklenir. Her vaka doğrudan
özgün admission ledger ve `admission_result` üzerinden okunur; elle SQL
settlement yapılmaz. Supervisor yalnız bütün vakaları ve özgün kapanışı içeren
tam, bağlı receipt'i kabul eder. Uygulama hatası vakasının tamamlanması,
çöken veya eksik çıktı veren çocuk sürecin başarılı sayılması değildir.

## Model ve kabul sınırları

Bu P1 diliminde **yalnız model factory, hesaplama ve model close açıkça
belirtilen scripted fixture'dır**. API, runner, authority, worker ve store
yaşam döngüsü özgün native uygulamadır. Gerçek sağlayıcı/model çağrısı sıfırdır;
HTTP servisi, gerçek broker alışverişi veya genel runtime admission yetkisi
açılmaz.

Native `execute_finite_admission` çağrısının izlenmesi, CLI/unattended policy
bayraklarının kabulü anlamına gelmez: kullanılan API yolu bu payload bayrağını
eklemez. Buradaki kapsam sonlu ve sınırlı API qualification akışıdır.
Aynı owner içindeki replay, restart sonrası replay kabulü de değildir.

## Kurulum ve kanıt sırası

Değişmiş runtime, eski R154 kurulum kaydına eklenmez. Yeni kaynak adayı immutable
Git commit'inden üretilir; değişmemiş 756 native kaynak ve 1.162 bağımlılık
kimliğiyle doğrulanır. İki yeni modül ve iki sabit script ile gerçek aday
838 kaynak dosyası içerir; sayı ve her dosyanın hash'i sealed manifestten doğrulandı.

Yeni sabit yollar `/opt/alaz-r156a1`, `/opt/alaz-r156a1-install-input` ve
`/opt/alaz-r156a1-accept-input` olarak ayrıdır. Kurulum kaydındaki gerçek
device/inode ve receipt hash'i ancak kurulum sonrasında elde edilir. Görev
başlatmayan producer, ordinary proof ve acceptance bundle bu gerçek kimliğe
bağlanır; eski proof yeniden adlandırılmaz.

Olumlu kabul yeni aynı ext4 imajında **seed epoch 1 → tek finite child
epoch 2 → özgün normal close** sırasını doğruladı. Readiness'ten sonra aynı supervisora
ikinci çocuk eklenmez. Seed 35 saniye, finite child 60 saniye ve kapanış payı
15 saniye olarak kalır; toplam 110 saniye, worker'ın 120 saniyelik ömrüne
sığmalı ve kalan süre özgün sahip üzerinden tekrar denetlenmelidir.

## Gerçek kurulum ve native kabul

Kaynak adayı `e641a50` commit'inden üretildi. Archive SHA-256
`3c829db65670756abd531d146aa72c0dc5b3773cd750fc87d26567763f3caef8`,
manifest SHA-256 `7a886c32fd81d046d44715921bdaae5765a6f4e481d33182258cc7aa2bac465a`.
`r156a1-install001`, ayrılmış `AlazHarness-D3B-P71C` ortamındaki
`/opt/alaz-r156a1` dizinine yalnız kaynak kurulumu yaptı. 838 kaynak ve 1.162
bağımlılık dosyası geri okundu; installer terminali exit 0 ile gözlendi.
Önceki `/opt/alaz-r154a1` ağacı değiştirilmedi.

Gerçek kurulum kaydı SHA-256
`a4bcc0f27d29f27f08c55d3a65eaa102a503a7da12d4672253f0245fd5d4f845`;
root device/inode `2096/29702`. Kayıt, installer'ın CLI çıktısından yeniden
üretilmedi: kurulu özgün dosya ordinary UID 23001 ile okunup hash'i doğrulandı.
Yedi sabit QA kaynağı bu gerçek kimliğe bağlandı.

`ordinary001` görev başlatmadan özgün native lifecycle'ı çalıştırdı: altı
başlangıç kontrolü, consumer `DETACHED`, owner `CLOSED`, üç fiziksel bağlantı
kapalı, profil lease'i normal bırakılmış, bekleyen task/thread sıfır. Dış süreçte
13.124 saniye, producer içinde 12.704 saniye ölçüldü. Görev, model ve listener
sayısı sıfırdı. Host hazırlığı sonraki adım öncesinde yalnız PASS etiketini değil,
bu ordinary proof'un altı dosyasını, kaynağını ve native kimliklerini doğruladı.

`image001`, yeni 64 MiB ext4 imajında aynı özgün supervisor ile çalıştı. Seed
10.069 saniyede tamamlandı; ardından tek finite çocuk PID 16, epoch 2 ile
kabul edildi. Bütün host işlemi bridge tarafından 43.597 saniyede gözlendi;
bu sayı yalnız finite hesaplama süresi değildir.

| Vaka | Gözlenen sonuç | Birikimli fixture hesaplaması |
|---|---|---:|
| Normal A | Native terminal `completed`; kaynakta beklenen cevap `50` ile doğrulandı. | 1 |
| Birebir tekrar A | Aynı admission ID, aynı API ve kayıtlı-sonuç hash'leri. | 1 |
| Yeni B | Farklı admission ID; terminal `completed`, beklenen cevap `7`. | 2 |
| Kontrollü hata C | Üçüncü admission; özgün native terminal `failed`. | 3 |

Her API dönüşü özgün `admission_result` içindeki `result` ve `usage` alanlarıyla
karşılaştırıldı. API tuple'ı ve saklanan dict farklı zarflar olduğundan bu iki
zarfın hash'lerinin birbirine eşit olduğu iddia edilmez; replay'de her zarfın
kendi hash'i ve admission kimliği aynı kaldı. Üç yeni admission için gerçek
native worker/settlement kullanıldı. Profil sayacı coroutine resume olaylarını
da içerir; `execute_finite_admission=56` gibi değerler 56 ayrı görev değildir.

Kapanışta aynı üç bağlantı doğrulandı; registry refcount sıfır, model fixture
örnekleri kapalı ve retirement kaynaklı değişen satır sayısı sıfırdı. Native
consumer/owner/lease kapanışından sonra özgün volume `stop` ve `finish`
çalıştı. Aynı worker PID 10 ve token ile `MOUNTED → UNMOUNTED → CLOSED`
gözlendi; sahip olunan çocuklar, loop bağlantısı ve fence kapandı, image lease'i
en son bırakıldı. Host mount namespace'i ve mount tablosu değişmedi.
`observedAfterUnknown=false`; retry veya forced cleanup uygulanmadı. Oluşturulan
imaj ve kanıt dosyaları saklandı; bütün çalışma dosyalarının silindiği iddia edilmez.

## Tanı çıktıları ve kalan sınırlar

Finite çocuğun stderr'i boş değildir: **4.513 byte** korunmuştur. Kontrollü
model hatasının beklenen traceback'i, native SQLite `DELETE` journal-mode
uyarıları ve `agent.secret_sources.command` modülünün bulunamadığını bildiren
bundled command secret-source kaydı vardır. Son kayıt, bu scripted akışın
terminal sonucunu ve kapanışını engellemedi; desteklenen gerçek sağlayıcı/secret
kaynaklarının eksiksiz paketlendiği sonucunu da vermez. Gerçek model geçişinden
önce bu paketleme kapsamı açıkça incelenip gerekli modüller yeni manifest ve
kurulumla doğrulanmalıdır. Ortam sessizce güncellenmedi veya fallback ile
başarılı gösterilmedi.

R155'in readiness-only kabulü eski kurulumuna aittir. R156'da özgün projected
startup altı kontrolle finite yol içinde geçti; yeni kurulumda ayrı
readiness-only operation yeniden çalıştırılmadı. **P1 bütünü bu nedenle açık
kalır.** Sonraki dar kabul, aynı güncel runtime için ayrı taze seed/readiness/
kapanış ve finite kanıtını birlikte bağlamalı; tamamlanmış aynı supervisor'a
ikinci çocuk eklememelidir.

## Doğrulama kayıtları

- [Başlangıç karşılaştırması](../evidence/m1-finite-product-r156a1/baseline.json)
- [İlk kaynak checkpoint'i](../evidence/m1-finite-product-r156a1/source-checkpoint.json)
- [Native sözleşme incelemesi](../evidence/m1-finite-product-r156a1/native-source-review.md)
- [Kurulum kaynak incelemesi](../evidence/m1-finite-product-r156a1/installation-source-review.md)
- [Acceptance kaynak incelemesi](../evidence/m1-finite-product-r156a1/acceptance-source-review.md)
- [Windows odaklı testler](../evidence/m1-finite-product-r156a1/windows-focused-tests.json):
  351 çalıştırıldı, 319 geçti, 32 platform nedeniyle atlandı; failure/error yok.
  Bunlar kernel veya installed native kabulü değildir.
- [İlk hazırlık testleri](../evidence/m1-finite-product-r156a1/windows-preparation-tests.json):
  Linux yolu Windows'ta temsil eden fixture'da bir error bulundu. Ürün
  validator'ı değiştirilmeden fixture'ın POSIX yol temsili düzeltildi;
  [düzeltme sonrası 23 testin tamamı geçti](../evidence/m1-finite-product-r156a1/windows-preparation-tests-corrected.json), exit 0.

- [Tam statik/discovery kapısı](../evidence/m1-finite-product-r156a1/pre-candidate-static.json):
  PASS; 6.498 root dosyası, iki kaynak gitlink ve 3.952 keşfedilen test.
  Bu kapı testleri keşfeder; keşfedilen testlerin tamamını çalıştırmaz.

- [Gerçek kurulum kaydı](../evidence/m1-finite-product-r156a1/installation/installation-receipt.json)
- [Yeni ordinary proof](../evidence/m1-native-finite-r156a1/ordinary001/result.json)
- [Aynı imajda native finite kabul](../evidence/m1-native-finite-r156a1/image001/result.json)
- [Bağlı kabul özeti](../evidence/m1-finite-product-r156a1/acceptance-summary.json)
- [Ham caller/transport çıktısı](../evidence/m1-native-finite-r156a1/image001/stdout.txt)

- [Bağımsız gerçek kabul incelemesi](../evidence/m1-finite-product-r156a1/actual-acceptance-review.md)
- [Özgün supervisor/kapanış incelemesi](../evidence/m1-finite-product-r156a1/actual-supervisor-review.md)
- [Son tam statik/discovery kapısı](../evidence/m1-finite-product-r156a1/final-static.json):
  PASS, 6.564 dosya / iki gitlink / 3.952 keşfedilen test; exit 0, 65.479 saniye.
  Tüm keşfedilen testlerin çalıştırıldığı iddiası bu kapıdan çıkarılmaz.

## Açık işler

Bu dilimde kaynak, yeni kurulum, ordinary proof ve aynı imajda finite/normal
kapanış kabulü tamamlandı. Final metadata ve exact-SHA CI/yayın kontrolü ayrıca
kaydedilir. P1'in güncel kurulumda ayrı readiness-only kanıtı, P2'nin günlük
yerel kontrol akışı ve seçilmiş bütçeli gerçek modeli, P3'ün oturumlar arası
hafıza/beceri kullanımı, P4'ün arıza/işletim akışları ve P5'in aynı sürümde
M1-01..M1-07/pilot kabulü açık kalır. Paid provider çalışması için model ve bütçe
seçimi gerekir; bu teslimatta maliyetli çağrı yapılmadı.
