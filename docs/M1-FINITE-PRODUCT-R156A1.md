# R156A1 — Sabit girişten sonlu native görev akışı

## Durum

**IN PROGRESS.** R155'te kabul edilen supervisor, retained projection ve native
sahiplik yoluna ayrı bir sabit görev girişi eklendi. Bu raporun kaynak hazırlığı
aşamasında yeni kurulum ve projected finite kabulü henüz çalıştırılmadı.
Kod, fixture testleri, gerçek kurulum, native kabul ve exact-commit CI ayrı
sonuçlardır.

Başlangıç commit'i: `4823ebbca5f039aee1e9a4a209e40a48c015044a`.
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
kimliğiyle doğrulanır. İki yeni modül ve iki sabit script için beklenen toplam
838 kaynak dosyasıdır; gerçek sayı sealed manifestten alınır.

Yeni sabit yollar `/opt/alaz-r156a1`, `/opt/alaz-r156a1-install-input` ve
`/opt/alaz-r156a1-accept-input` olarak ayrıdır. Kurulum kaydındaki gerçek
device/inode ve receipt hash'i ancak kurulum sonrasında elde edilir. Görev
başlatmayan producer, ordinary proof ve acceptance bundle bu gerçek kimliğe
bağlanır; eski proof yeniden adlandırılmaz.

Olumlu kabul hedefi yeni aynı ext4 imajında **seed epoch 1 → tek finite child
epoch 2 → özgün normal close** sırasıdır. Readiness'ten sonra aynı supervisora
ikinci çocuk eklenmez. Seed 35 saniye, finite child 60 saniye ve kapanış payı
15 saniye olarak kalır; toplam 110 saniye, worker'ın 120 saniyelik ömrüne
sığmalı ve kalan süre özgün sahip üzerinden tekrar denetlenmelidir.

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

## Açık işler

Kaynak/fixture doğrulamasından sonra yeni kurulumun tam readback'i, yeni ordinary
proof, same-image projected finite kabulü ve normal kapanış gözlenmelidir.
Bunların ardından final kaynak ve evidence için exact-SHA CI ve normal main
yayını yapılır. P1 bütünü, P2–P5, tam D3B, M1 ve production kabulü bu kaynak
checkpoint'inde açık kalır.
