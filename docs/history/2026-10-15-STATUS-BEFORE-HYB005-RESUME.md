# AlazHarness — status

Son güncelleme: 15 Ekim 2026. Canlı Git durumunu bu kayıtla birlikte kontrol et.

## Güncel çalışma noktası

MAIN-INTEGRATION: PUBLISHED, CI DELIVERY RECHECK: kullanıcı HYB-004C dahil doğrulanmış dalın main'e
birleştirilmesini ve kalan işlerin sürdürülmesini onayladı. Yerel main,
58b210ac9d400b84b028a2b57dcf1a4a396f089e ->
2c79dce64bde02b45104d42d909784bea370dc1e fast-forward edildi; geçmiş korunuyor.
Temiz main çalışma ağacında604/604 standart test PASS; kod değişmedi. Remote
push eccf8fc olarak tamamlandı. İlk GitHub webhook teslimi500/timeout aldı;
aynı delivery kimliği kontrollü yeniden teslim edildi. Test FAIL değil; yeni
main exact-SHA CI henüz gözlenmedi. Aşağıdaki kayıt bu belirsizliği korur.

Varsayılan kök: C:\Antigravity\AlazHarness.
Aktif temiz entegrasyon çalışma ağacı: scratch/worktrees/main-6f88.
Aktif dal: alaz/hyb-005-host-gate-6f88. Bu tur tek yazıcı6f88. Eski ref-pi-001-ac97 ve diğer deneme
dalları korunur; hepsinin körlemesine merge edilmesi söz konusu değildir.
Kök, korunmuş eski kirli dalda kalır; orada reset/clean/stash/toplu stage yapılmaz.
Kök status.md yalnız hash kontrollü erişim kopyasıdır.

## Doğrulanmış kapsam

HYB-004C'ye kadarki paketler geçmişleriyle bu birleşimdedir. Gerçek Hermes
Agent/Gateway, read_file, kontrol, kesinti karakterizasyonu, readonly uzlaştırma
ve açık operatör kapanışı kendi raporlarında dar kapsamlarıyla kabul edilmiştir.
Önceki604 standart test ve3final native senaryo bu turda yeniden çalıştırılmış
sayılmaz; ana dalın yeni standart koşusu evidence/main-integration altında olacak.
Üretime hazır sürüm veya M1/M2 tamamlandı iddiası yoktur. Ücretli model0.

## Şimdi yürütülen iş

Main yayın/CI kapanışından sonra HYB-005-HOST-GATE için main'den yeni kısa dal:
kapalı/unknown veya gönderim sonucu belirsiz anahtar tekrar POST edilmemeli;
yalnız yetkili yeni istek tek gönderim sınırından geçmeli. Retention yokluğu
"hiç gönderilmedi" kanıtı değildir. İkinci scheduler/ajan/ayrı durum DB'si ekleme.
Gerçek araç izinleri ve tüm model çağrıları için bütçe ayrıca uygulanıp sınanmalı.

## Tarihçe

Önceki status'un tamamı: docs/history/2026-10-15-STATUS-BEFORE-MAIN-6f88.md.
Önceki tüm native/local/CI kapsamları ve eski history bağlantıları orada korunur.

### 15 Ekim 2026 — MAIN-INTEGRATION başlangıcı

Canlı origin/main58b210a, kaynak dal2c79dce; kaynak dal exact-CI success okundu.
Fast-forward yalnız temiz yeni main worktree'sinde;32 eski kök dosya hash'i
runtime/main-merge-6f88/custody-start.json içinde. Kaynak pinleri değişmedi.

### 15 Ekim 2026 — MAIN/HYB005 bağımsız QA72d4 başlangıcı

Mevcut main-6f88 tek uygulama/yayın sahibi korunur. İkinci merge girişimi canlı
ref önkoşulunda, herhangi bir yazı olmadan durdu. QA72d4 mevcut ff kodunda ayrı
604standart koşusunu inceliyor; HYB005 için kapanış/retention/kayıp ACK/aynı key
eşzamanlılık retleri hazırlanıyor. Ana kontrol koduna ikinci yazar yok.
Özel QA alanı runtime/main-host-qa-72d4; plan QA-PLAN.md. Henüz host kabulü yok.

### 15 Ekim 2026 — MAIN-INTEGRATION yerel doğrulama

604/604 standart test exit0/skip0. README ve status artık güncel kapsamı gösteriyor.
Kaynak dal24 commit ilerideydi; 343 dosyalık mevcut paket içerik birleştirmesi
yapılmadan fast-forward ile alındı. Bu ek belge commitinde runtime kodu değişmedi.

### 15 Ekim 2026 — Bağımsız main doğrulaması QA72d4

Birleşmiş2c79dce kodunda ayrı standart koşu604/604 PASS, exit0/skip0 ve kod
drift0. evidence/main-integration-qa/validation.json ve unittest.txt; yalnız bu
iki QA kanıt dosyası stage edildi. Native deneyler yeniden çalıştırılmadı.
HYB005 QA taslağı runtime/main-host-qa-72d4/QA-PLAN.md; kapalı/unknown/retention
ve kayıpACK için bağımsız ret senaryoları, tek ürün yazıcısı6f88 korunuyor.

### 15 Ekim 2026 — Main yayın ve CI bağlantı incelemesi

Main eccf8fc yayımlandı;604 yerel +604 bağımsız koşu ayrı PASS. İlk push
webhook cevabı alınamadı, sunucuda matching iş yoktu; gerçek GitHub delivery
aynı SHA/ref ile yeniden teslim istendi(202). Sunucu konfigürasyonu değiştirilmedi.
Kanıt evidence/main-integration/webhook-redelivery.json. HYB005 yeni dalda
ilerleyecek, CI belirsizliği yeşil sayılmayacak.

### 15 Ekim 2026 — HYB-005A başlangıç6f88

Yeni dal main b8ff44ff105965ba3f6f9fa9559ad96f2c084815 üzerinden açıldı. Tek uygulama yazıcısı6f88; QA72d4
sadece ayrı test/rapor sahibi. İlk dar kapsam: native Gateway plugin portunda
yeni istek belgesi + gönderimden önce aynı native state_meta transactionında
tek-kullanımlık tüketim; kayıpACK/retention sonrası tekrar gönderim yok. Native
SessionDB yazma sahibi kullanılır, ikinci store/scheduler yok. Sadece kayıtlı
host girişinden verilen yeni anahtarlar; legacy/kapalı/unknown key ret. Gerçek
model/araç izinleri ve token/para bütçesi bu ilk dilimde tamamlanmış sayılmayacak.
Ürün ve native testler IN PROGRESS/NOT RUN; ana dal artık birleşmiştir.

### 15 Ekim 2026 — HYB005A QA72d4 sınırları

Main eccf8fc exact GitHub alaz/local-ci success bağımsız yeniden okundu. Yeni
feature main b8ff44f tabanında. QA native plugin auth, immutable permit, önce
kalıcı tüketim sonra forwarding, closure/retention ve kayıpACK sonrası ret
sınırlarına bakacak. Rapor docs/research/HYB-005A-INDEPENDENT-QA.md PLANNED.
6f88 tek ürün yazıcısı; QA eski native profillere yazmayacak. Gerçek model0.

### HYB-005A — bağlantı sonrası devam9897

Yerel erişim geri geldi. Mevcut alaz/hyb-005-host-gate-6f88 dalında iki yarım
host_gate dosyası ve önceki QA planı bulundu, runtime/hyb005-resume-9897/before
altında aynen korundu. Yeni ikinci ürün dalı yok.9897 tek devam yazıcısı.
Hook inceleme9766d59 exact-CI success okundu; isteğe bağlı eklenti hatası
yürütmeyi durdurmayabilir. Zorunlu host rotası, kayıttan önce izin tüketimi,
eşzamanlılık ve kayıp ACK testleri IN PROGRESS. Main birleşimi tekrarlanmaz.
