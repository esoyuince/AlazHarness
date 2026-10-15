# AlazHarness — status

Son güncelleme: 15 Ekim 2026. Canlı Git durumunu bu kayıtla birlikte kontrol et.

## Güncel çalışma noktası

MAIN-INTEGRATION: PUBLISHED; HYB-005A RESUMED: kullanıcı HYB-004C dahil doğrulanmış dalın main'e
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

### 15 Ekim 2026 — HYB005A devam890e — IN PROGRESS

Yerel bağlantı döndü; main-6f88 mevcut dalı/dosya hashleri doğrulandı.
6f88 oturumundan kalan iki host dosyası runtime/hyb005-resume-890e/before altında
birebir korundu; yeni uygulama sahibi bu890e oturumudur. İkinci motor/store yok.
9766d59 kanca incelemesi exact-SHA CI success okundu. Zorunlu kapı gerçek HTTP
yürütme sınırında kurulup fail-open plugin kaydıyla karıştırılmadan sınanacak.
Native/standart testler bu tur için henüz NOT RUN. Eski sonuçlar taşınmaz.

### HYB005A — çalışma sahipliği uzlaştırması QA890e

Canlı dosyalarda aynı anda9897 devam yazıcısı bulundu.890e önceki uygulama
sahipliği notunu geçersiz kılar;9897 TEK ürün/dal/commit sahibi kalır.890e yalnız
 bağımsız tests/test_host_gate_qa.py, docs/research/HYB-005A-QA890e.md ve
 evidence/hyb-005a-qa890e altında çalışır. Ürün dosyaları değiştirilmez.
Eski middleware incelemesi9897 tarafından zaten içeri alınmış, ikinci kopya yok.
Kapsam: tek-kullanım, bozuk kayıt, eksik geçmiş, callback/ret ve cancellation
kontratları; native süreç deneyleri varsa ayrıca readonly teyit. IN PROGRESS.

### HYB005A QA890e — ilk36 test / iki gerçek aday hatası

36 bağımsız synthetic-owner SQLite testi34PASS/2FAIL(exit1), kod drift0.
QA-01 tüketilmiş intent satırı eksik ama sayaç kaldığında aynı requestId yeniden
issue ediliyor. QA-02 cfg.issued=0 iken var olan intent unutulup yeni izin veriliyor.
HostGateLedger retained-row/count tutarlılığını aynı native transaction içinde
kanıtlamadan yeni issue/consume yapmamalı. İki test değiştirilmeden korunur; ürün
sahibi9897 düzeltmesi beklenecek. Rapor docs/research/HYB-005A-QA890e.md, ilk
kanıt evidence/hyb-005a-qa890e. Bu native Gateway kabulü veya disk-arızası deneyi değil.

### HYB-005A9897 — ilk gerçek Gateway ve test durumu

HostGateLedger sayaç/saklanan intent tutarlılığı aynı transaction içinde eklendi;
QA36/36 yeniden PASS. HostGateClient dedicated /alaz/host/v1/dispatch kullanır,
raw /v1/runs fallback yok. İlk native normal turda gerçek plugin discovery +
Gateway + native SessionDB + read_file:10eşzamanlı dispatch1kabul/9ret. Aynı
profil epoch2 yeniden açılınca consumed ret ve aynı sonuç; toplammodelHTTP2,
araç1. İlk normal deneyi final client veri-descriptor kontrolünden ÖNCEDİR,
runtime/hyb005-resume-9897/normal-trial-01 içinde korunur. Final dört native
senaryo şimdi ayrı yeni profillerde yürütülüyor; henüz toplu PASS değil.

### HYB005A QA890e — kayıt hataları kapandı / istemci iki bulgu

Aynı36 ledger QA testi düzeltme sonrası36/36 PASS(exit0/drift0); iki eski FAIL
korundu.12 gerçek HostGateClient + fixture fetch testinde10PASS/2FAIL:202
completed=false/partial=true çelişkisi ve object output kabul ediliyor.
Beklenti invalid_host_admission + mayHaveBeenAccepted=true + retryAllowed=false;
izin iade edilmez. tests/node/host_gate_qa.mjs ve test_host_client_qa.py hazır.
Rapor HYB-005A-QA890e.md QA-03/04;9897 tek üretim yazıcısı.17loopbackHTTP bileşen
deneyi ayrıca geçti(synthetic adapter/native guard yalnız bind anında fixture);
bunlar gerçek Gateway koşusu değil. Güçlendirilmiş checker final yeniden koşacak.

### HYB005A QA890e — dört native kaydın bağımsız teyidi

QA-01/02 aynı36 ledger testiyle; QA-03/04 aynı12 client testiyle PASS, drift0.
17 gerçek loopbackHTTP bileşen kontrolü de final checker ile PASS; synthetic
adapter/native-owner olup native diye sayılmaz. Dört qualified primary native
koşu kendi state.db, process-exit/nonce ve product hashleriyle ayrıca doğrulandı:
normal/lostACK tek admission+tek read_file, modelHTTP2; missing-plugin/invalid-policy
admission/tool/model0. Clean reopen sırasında yeni model yok. Bu dört ek native
çalıştırma değil; existing4 kayıt teyidi. Kanıt evidence/hyb-005a-qa890e/native-retained-corroboration.json.
Tam bağımsız standart suite halen kendi çağrısında sürüyor; sonucu yeşil varsayılmaz.
32 eski kök dosya ve dört upstream temiz/pinli korunuyor;9897 tek commit sahibi.
