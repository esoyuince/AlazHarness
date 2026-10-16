# AlazHarness — status

Son güncelleme:16 Ekim2026. Canlı Git HEAD/status/remote/CI her devamda kontrol edilir.

## Güncel nokta

HYB-005B IN PROGRESS:0d37 tek uygulama/commit yazıcısı. Mevcut kaynak ve
bütçe/araç yürütme sınırları okunuyor. Yeni testler NOT RUN; eski PASS taşınmaz.

HYB-005A HOST DISPATCH: LOCAL/NATIVE NARROW ACCEPTANCE PASS; CODE PUBLISHED, EXACT-COMMIT CI PASS.
Mevcut b8ff44f main tabanında kesintiden kalan iki ürün taslağı sürdürüldü.
HostGateLedger, native state_meta yazma sahibi üzerinden izin üretir/tüketir;
HostGateClient yalnız /alaz/host/v1/dispatch kullanır, ham native başlangıca
fallback YOK. Bunlar yeni task queue, agent loop veya ikinci DB değildir.

Aktif dal: alaz/hyb-005b-execution-0d37.
Aktif çalışma ağacı: C:\Antigravity\AlazHarness\scratch\worktrees\main-6f88.
Varsayılan kök C:\Antigravity\AlazHarness hâlâ eski korunmuş kirli daldadır;
üretim geliştirmesi kökte yapılmaz. Kök status.md hash kontrollü erişim kopyası.
Bu tur tek ürün/yayın yazıcısı9897; QA890e yalnız ayrı test/rapor/kanıt sahibidir.
Main birleşimi yeniden yapılmadı. Kaynak pinleri ve özel sunucu ayarları değişmedi.

## Tamamlanan işler ve kanıt

- Kesintiden kalan host_gate.py/host_gate_plugin.py aynı runtime altında yedeklendi,
  mevcut dal sürdürüldü. Eski hook sınır araştırması9766d59 exact Git bloblarıyla
  alındı; önceki kapsamı değiştirilmedi. Hook/eklenti istisnası tek veto sayılmaz.
- İstek belgesi body/model/profile/principal/epoch/expiry/namespace ile bağlanır.
  İzin tüketimi native SessionDB transactionında kalıcı olmadan handler çağrılmaz.
  Kayıp yanıt/istisna/yeniden açma sonrası tüketim geri verilmez.
- Aynı transactionda bounded intent/counter tutarlılığı: silinmiş satır veya
  gerilemiş sayaç otomatik yeni izin oluşturamaz. Geçmişin yokluğu replay izni değil.
- Sunucu ve istemci scope/body/auth/generation/bozuk cevap kontrolleri var.
  İstemci özel permit kimliğini ve immutable body snapshotını tutar; kopya ve
  başka istemcinin permit'i ağ isteği üretmez. Resume/inspect readonly kalır.
- QA bulguları: iki ledger tutarsızlığı ve iki client terminal/output çelişkisi
  düzeltilip aynı testlerle tekrar doğrulandı; ilk red kanıtlar silinmedi.

## Doğrulamalar — kapsamlar ayrı

Yerel TAM standart suite669/669 PASS, exit0/skip0/code-drift0:
evidence/hyb-005a/local-validation.json ve unittest.txt.
65yeni standart test669 içindedir:36ledger +17loopback-client +12client QA.
Bunlar native Gateway çalışmaları değildir. Kod2263c79 aynı-SHA server suite669/669 PASS.

Son ürün koduyla4/4 gerçek Gateway senaryosu PASS:
1) missing-plugin:0admission/0tool/0providerHTTP.
2) invalid-policy:0admission/0tool/0providerHTTP.
3) normal:10ayrı client dispatch1kabul/9ret;1admission/1read_file/2providerHTTP.
4) lost-ack:gerçek202drop, retry ret;1admission/1read_file/2providerHTTP.
Pozitif iki senaryo aynı profilde yeni native epoch ile tekrar açıldı; kayıtlar
ve sonuçlar aynı, ek model/araç çağrısı yok. Hepsi normal native kapanış;
bu pakette yeni hard-kill/power-loss deneyi yapıldı denmez.
Kanıt evidence/hyb-005a/native-suite.json ve native-store-check.json.
İlk normal ön-sürüm deneyi ve ilk non-JSON404 etiketleme hatası ayrı korunur;
son4koşuya eklenmez. Gerçek model çıkarımı/ücretli çağrı0.

Ayrı QA17/17 gerçek HTTP bileşen testi: gerçek plugin/aiohttp + sentetik
adapter/owner; bind-time provenance substitution açık belirtilmiştir. Native
Gateway veya standart669sayısının parçası değildir. Rapor/kanıt:
docs/research/HYB-005A-QA890e.md, evidence/hyb-005a-qa890e/.
32eski kök dosya ve4upstream kaynağı değişmeden korundu; yeni bağımlılık kurulmadı.

## Ürün sınırı ve açık işler

Bu paket tek-kullanımlık HOST HANDOFF sağlar, token/para bütçesi veya exactly-once
external effect sağlamaz. Native handler reddetse dahi tüketim geri verilmez;
committen sonra hiç kabul edilmemiş iş olabilir. Operatör incelemesi gerekir.
API bearer güvenilen yerel operatör yetkisidir; ayrı ajan credential'ı yoktur.
Eksik pluginde Alaz client yolu kapalıdır; unextended Hermes'in raw endpointlerinin
ve bütün GET/WS yollarının global sandbox ile kapandığı iddiası yoktur.
Farklı requestId ile eski işi yeniden adlandırmak otomatik kurtarma değildir.
Silinen/tam rollback olmuş bütün state veya yetkili kişinin sahte digest yazması
bu katmanın tespit garantisi değildir. Kaynak sürümü ve tek native owner şartı var.

## Kesin sonraki adım

Kod2263c793419cf004ce73147529cb382a9f1c3895 yayımlandı ve exact-SHA CI success.
Yeni oturumda son belge HEAD/CI ve temizliği kontrol et; sıradaki iş HYB-005B:
gerçek model/araç yürütme sınırında zorunlu izin + tüm sağlayıcı istek/token/para
bütçesi; özet/retry/auxiliary çağrı dahil. Optional hook exception fail-open
olduğu için tek başına güvenlik mekanizması yapılmaz. Ana hedef tek runtime,
sonrasında hafıza/beceri transferi ve sınırlı gerçek model kabulüdür. M1/M2 AÇIK.

## Belgeler ve tarihçe

Ana rapor docs/HYB-005A-HOST-GATE.md. CI kapsamı docs/CI.md.
Önceki bütün durum günlüğü docs/history/2026-10-15-STATUS-BEFORE-HYB005A-DELIVERY-9897.md.
Önceki main/004C ve bağımsız890e çalışma notları bu arşivde aynen korunur.

### HYB-005A9897 — yerel/native kapanış

Son4native koşu ve669standart test doğrulandı; kaynak hashleri değişmedi. İki
ledger ve iki client negatif bulgu testi zayıflatılmadan kapandı. Yayın aşaması
henüz tamamlanmış veya CI yeşil sayılmıyor. Bilinmeyen yazı körlemesine tekrarlanmaz.

### HYB005A QA890e — final bağımsız teslim

Tam standard suite669/669 PASS, exit0/skip0,131 ölçülen dosyada drift0/yeni
kod dosyası0. Dört hata eski FAIL makbuzlarıyla korundu ve aynı ret testleriyle
kapandı.36ledger+12client test bu669un içindedir;17componentHTTP ve4native
kayıt teyidi ayrıca scope taşır. docs/research/HYB-005A-QA890e.md ve kendi
seçilmiş QA dosyaları stage edildi. 9897 tek commit/push sahibi kalır;bu kayıt
exact-SHA CI kabulü değildir. Geri kalan: tüm model çıkışlarında bütçe, gerçek
araç izinleri ve host operatör yetki politikası; tamM1/M2 açık.

### HYB-005A9897 — yayın ve aynı-commit CI kapanışı

Kod2263c793419cf004ce73147529cb382a9f1c3895 origin dalına gönderildi. GitHub
alaz/local-ci success ve alaz-server tam aynı checkout SHA makbuzu669/669,
failed0/skipped0/suite_errors0/status_delivery=posted bağımsız okundu.
Sanitize makbuz evidence/hyb-005a/code-ci.json. Bu ek commit yalnız durum ve
kanıt belgesidir; ürün/test kodları yeniden değiştirilmedi. Bu belge commit'inin
son CI durumu yayın sonrası ayrıca sorgulanır, kod SHA yeşili ona taşınmaz.
Son kontrol öncesi aktif worktree temiz ve yerel/remote kod SHA eşitti.
Main bu feature paketine ilerletilmedi; önceki b8ff44f ortak tabanı korunuyor.
Sıradaki HYB-005B henüz başlamadı. Model/araç izinleri, bütün provider çağrılarının
bütçesi, izolasyon ve M1/M2 kabulü bu tek-kullanım kapısından ayrı açık işlerdir.

### 16 Ekim 2026 — HYB-005B başlangıç0d37

Taban30b205f temiz/origin eşit ve exact CI success. Mevcut main-6f88 worktree
üzerinde yeni kısa dal. Runtime/hyb005b-0d37 yalnız bu turun geçici kanıt alanı.
İlk iş native fiziksel model çağrısı ve gerçek araç ret sınırını saptamak;
opsiyonel fail-open kanca tek veto yapılmayacak. Tek native state sahibi
korunacak; provider cevapları local taklit, gerçek/ücretli model0.

### 16 Ekim2026 — HYB005B QA3193 başlangıcı

Canlı0d37 ürün yazıcısı görüldü;3193 ikinci ürün/dal oluşturmadı.3193 yalnız
bağımsız tests/test_execution_gate_qa.py ve tests/node/execution_gate_qa.mjs
(gerekirse seçilmiş scripts/qa/execution_*) ile docs/research/HYB-005B-QA3193.md,
evidence/hyb-005b-qa3193 altında inceleme yapar. Native provider SDK retry,
auxiliary/summary ve gerçek araç ret sınırları özellikle sorgulanacak. İsimler
çakışırsa önce kontrol. Testler NOT RUN, gerçek inference/ücretli çağrı yok.

### HYB005B QA3193 — SDK fiziksel istek kontrolü

Gerçek native auxiliary client factory + gerçek SDK + localhost503/200 fixture:
varsayılan max_retries0 bir SDK invoke→1HTTP/hata; explicit max_retries1 aynı
invoke→2HTTP/başarı.2/2 kontrol PASS; modeller taklit/inference0. Bu tam Gateway
veya yeni bütçe kapısı kabulü değil. Primary/aux her ikisi setdefault0 kullanıyor;
eski yorumda aux retry var demesi güncel davranış kanıtı değil. Kaynak ve raw
makbuzlar evidence/hyb-005b-qa3193 altında. Bütçe gerçek egress noktası gerektirir.

### HYB005B QA3193 — ilk45 ledger kontrolü43PASS/2FAIL

Gerçek ExecutionLedger/Policy + synthetic SQLite owner45case exit1/code-drift0.
QA-B01 provider ticket tool_return; QA-B02 read_file ticket response ile settle
edilebiliyor. Bütçe iadesi yok ama kind/outcome kaydı çelişkili. Settle ve retained
row validation tür/sonuç ilişkisini yazmadan doğrulamalı. İki test zayıflatılmaz:
tests/test_execution_gate_qa.py; ilk çıktı/sha evidence/hyb-005b-qa3193.
Ürün0d37 sahibi düzeltir;3193 yalnız test/rapor. Native kabul henüz değil.

### HYB005B QA3193 — ledger45PASS; iki HTTP bütçe kanıt sorunu

Aynı45ledger testi düzeltme sonrası45/45 exit0/drift0. Bağımsız gerçek aiohttp
route + synthetic owner/config/registry26case24PASS/2FAIL (stable2nd run).
QA-B03 allowed model isteğine wrong-model yanıt200 geçiyor; fiyat/model
bağı doğrulanmıyor. QA-B04 SSE usage101>cap100 ardından2 gelince ilk aşım
silinip200 çıkıyor. Her usage frame/model kimliği sınanmalı; rezervasyon iadesi
yok, gerçek sağlayıcı/faturalama hatası iddiası değil. Rapor ve tekrarlama
scripts/qa/execution_http_matrix.py; evidence/.../http-stable-initial.json.
İlk HTTP trial ürün driftliydi, ayrı başarısız kayıt olarak korundu.

### HYB005B0d37 — ilk uygulama ve native tanı

ExecutionLedger native state_meta ile fiziksel çağrı başına değişmez tam token/
microUSD risk rezervasyonu tutuyor; gerçek fatura/tokenizer iddiası yok.32 temel
standart test PASS. QA45 ilk43PASS/2FAIL kind/outcome çelişkisi düzeltildi.
İlk native açılış ready deadline aldı; ikinci public Gateway açıldı fakat custom
model anahtarı OPENAI_API_KEY’den seçilmediği için gerçek401 ret verdi, modelwire0.
Şimdi native model.api_key alanına ayrı sağlayıcı kimliği açıkça bağlandı. İlk
FAIL kanıtları korunur; native kabul henüz YOK. Kişisel profil/gerçek model0.

### HYB005B QA3193 — yanıt düzeltmeleri doğrulandı

Ledger45/45 aynı test; HTTP27/27 son sabit kod exit0/drift0. Wrong model ve SSE
önce yüksek sonra düşük usage artık ret; compact data:JSON da sınandı. Ek36
parser/path testi PASS. QA toplam93offline (45+36+12makbuz) tam standardın
parçasıdır;27HTTP ve2SDK fiziksel gözlem ayrı. Yeni36 native Gateway deneyi değil.
Eski43/45,24/26,drift ve fixture-setup hataları kanıtları korunur. Bütçe
gerçek tarife/tokenizer/OS izolasyonu kabulü sayılmaz. Full suite başlatılıyor.
