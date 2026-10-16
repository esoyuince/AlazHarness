# AlazHarness — status

Son güncelleme: 16 Ekim 2026. Her devamda canlı dal/HEAD/CI doğrulanır.

## Güncel nokta

**HYB-005D3A dar Linux provider broker yerelde kabul edildi; Git/CI yayını sürüyor.**
D3B tüm Gateway için OS kimlik/ağ izolasyonu ve M1/M2 AÇIK.
Aktif dal: alaz/hyb-005d3-provider-247a.
Aktif çalışma ağacı: C:\Antigravity\AlazHarness\scratch\worktrees\main-6f88.
Başlangıç: 2ee705ec6427d9af9bd695e132d82e198dc20b0a; temiz, exact CI success.
D2 tamamlanmış bulundu; tekrarlanmayacak. Önceki tam durum
 docs/history/2026-10-16-STATUS-BEFORE-HYB005D3-247a.md altında korundu.
247a tek uygulama/yayın sahibi. Agent list kontrolünde bu projeye uygun ajan yok;
başka proje/revoked ajanlarına dokunulmadı. Sonradan gelen QA7e1b test/kanıtları
okunarak aynı teslimde korundu; kendi uygulama/native çalışması bağımsız QA sayılmaz.

## İlk başlangıç kapsamı — aşağıdaki günlükte sonuçlandırıldı

Mevcut canonical admission/ExecutionLedger tek yazar korunur; ikinci DB veya
scheduler yok. Önce mevcut provider/D2 kaynak sınırı ve özel Linux ortamı okunur.
Kişisel sır/model çağrısı, host firewall/daemon değişikliği yapılmaz. Testler yeni
proje alanı/sentetik credential ile. D3 için test/native/CI henüz NOT RUN.
Main ve kökteki32korunmuş dosya değişmez; yalnız status erişim kopyası eşitlenir.
Tam M1/M2, gerçek fiyat/tokenizer, Windows ağ ve crash-takeover AÇIK.

### 2026-10-16T23:07:39.807307+03:00 — D3 QA7e1b başlangıç

Eşzamanlı247a başlangıcı precondition ile görülüp hiçbir ürün/branch yazısı
yapılmadı. QA7e1b ayrı test/rapor/kanıt işi: credential ayrımı, hedef/header/
redirect/proxy retleri ve ön-rezervasyon/belirsiz yanıt. Ürün/Git247a tek
sahibi korunur. Yeni kodu hayal ederek test yazma; gerçek API okunacak.
Windows/root network/kişisel anahtar/model yok. Başlangıç NOT RUN.

### 2026-10-16T23:13:30.269786+03:00 — D3 QA7e1b kaynak incelemesi

Yeni broker kaynakları okundu. Ham response substring kontrolü JSON/akışın
çözümlenmiş metninde credential gizliliğini tek başına kanıtlamaz; semantik
yanıt incelemesi açık. check_authority transaction sonrası epoch/data_version
teyidi yok; snapshot/future-lease ayrımı açıkça tanımlanmalı. Bunlar henüz
çalıştırılmış negatif test değil; kaynak inceleme sorularıdır. Ek HTTP test
dosyası yazısı araçça engellendi ve dosya yok; tekrar gönderilmedi. QA şimdi
mevcut test_provider*.py dosyalarını kaynak hashleriyle bağımsız çalıştırır.

### 2026-10-16T23:14:19.909593+03:00 — D3 QA7e1b mevcut test turu

Mevcut72provider testi71PASS/1ERROR,exit1/source-drift0. Hata Windows üzerinde
asyncio.open_unix_connection var olmayan simgesini patch(create=False) ile
kurmaya çalışırken oluşuyor; ürün ağ çağrısı değil, test port kurulum hatası.
Testin not-called assertionını koruyarak explicit synthetic port kurulmalı.
Kanıt evidence/hyb-005d3-qa7e1b/existing-targeted-first.json/.txt. Bu72 yeni
QA testi değildir; gerçek Gateway/broker/model çağrısı yok.

### 2026-10-16T23:15:53.765353+03:00 — D3 QA7e1b beş regresyon

Yeni9synthetic SQLite/read testi4PASS/5FAIL exit1/drift0. G01(2): consume sonrası
queued check_authority grant expiry yeniden kontrol etmiyor; tamexpiry ve21s
sonrası kabul ediyor. G02(3):snapshot rollback sonrası epoch/instance/grant
değişse de check_authority dönüyor. Bunlar gerçek ağda istek gönderildi kanıtı
değil; okuma aşaması ret kontratları. Aynı testler tests/test_provider_snapshot_qa7e1b.py
SHAa704d597... değişmeden korunur; ilk sonuç evidence/hyb-005d3-qa7e1b/snapshot-initial.*.
Ürün247a düzeltecek; QA ürün dosyasına dokunmadı.

### 2026-10-16T23:18:14.102276+03:00 — D3 QA7e1b IPC kimliği

Gerçek _exchange/framing/signature kodu ve yalnız bellekteki sentetik IPC
portlarıyla11/11 PASS,drift0. Yanlışnonce/broker/domain/type,peer ret,socket
değişimi ve iptal/stream close retleri doğrulandı. Gerçek ağ/broker/OS testi
değil. QA toplam20yeni offline vaka:9snapshot+11identity. Beş snapshot FAIL
ürün düzeltmesi ve değişmeyen test rechecki olmadan kapanmış sayılmaz.

### 2026-10-16T23:20:21.377310+03:00 — D3 QA7e1b değişmeyen testlerle kapanış

G01/G02 ürün247a tarafından düzeltildi: expiry başta/sonda, snapshot sonrası
epoch+instance+data_version ve dosya kimliği yeniden denetleniyor. Aynı9snapshot
ve11IPC testi20/20 PASS; ilk5FAIL assertion/test hashleri değişmedi,source drift0.
unchanged-recheck.json/.txt kanıt. Hamyanıt/JSON semantic reflection kaynak
sorusu ayrı; bu testler onu veya gerçek ağ yarışı/OS izolasyonunu kapatmaz.

### 2026-10-16T23:21:01.863786+03:00 — D3 QA7e1b tam standart tur

Aynı20 bağımsız test PASS. Mevcutprovider+9snapshot seçimi81/81 PASS; Windows
port hazırlık hatası düzeldi. QA şimdi bütün standart discoveryyi kaynak seti
ve hashleri başta/sonda kontrol ederek çalıştırıyor. Sonuç henüz yok; yeni
broker/Gateway/native ağ deneyi başlatılmayacak. Makbuz539ca4eb-9bd1-4cd4-80a1-a38f75569c26.

### 2026-10-16T23:21:10.159529+03:00 — D3 düzeltmeler ve Linux deneyi

QA7e1b ek20test/raporu okunarak aynı çalışmaya dahil ediliyor; ürün yazıcısı
247a kalır. G01/G02 expiry/snapshot5FAIL kapandı; aynı9test yeşil. Ek15 yanıt
koruma testinin7ilkFAILi JSON/SSE decoded credential ve malformed yanıt kontrolü
ile düzeltildi.55broker/81provider seçimleri PASS; kesişimli altkümeler toplanmaz.
Yeni code-v2 hashli snapshot eski özel Linux prepared ortamına aktarılıp normal
Gateway+ayrı broker+gerçek read Docker senaryosu başlatılıyor. Makbuz bu yeni
komutun sonucu; henüz native PASS değil. Upstream sentetik credential yalnız
broker özel dosyasında; Gateway arbitrary same-UID koduna karşı OS izolasyonu
iddaa edilmiyor. Ağsız araç sınırı D2 korunur.

### 2026-10-16T23:24:20.134158+03:00 — D3 QA7e1b cevap koruma ve full tur

Primary decoded JSON/SSE response guardı ve testleri okundu; tekrar koşulan
seçimin makbuzu response-and-identity-recheck.json. Kaynak sorusu bu desteklenen
representasyon sınırında ele alındı; gerçek HTTP test iddiası yok. İlk full
1270test exit0/skip0 ama run_native_provider_broker.py koşu sırasında değişti:
full-standard-first snapshot NOT_ACCEPTED korundu. Son sabit kaynak full turu
beklenir; ilk başarı yeni sürüme taşınmaz.

### 2026-10-16T23:27:03.801812+03:00 — D3 son kaynak kabul başlangıcı

Normal v3 gerçek Gateway/broker/read zinciri PASS:2origin/2grant/1read,3yanlış
credential401. Sonrasında gerçek Unix idle-close testi gecikme gösterdi;
shutdown sırası düzeltildi,3aynı lifecycle testi PASS. Önceki1270tam suite
PASS aday sürümdür; son kaynak daha yenidir. Yeni code-v4 tüm code/config/test
hashleri runtime/hyb005d3-247a/transfer-v4.json ile sabitlenmiştir. Bundan
sonra ürün/test eklenirse final kabul yenilenecek. 5native senaryo seri ve
Unix close testi başlatılacak; diğer QA dosyaları yeni uygulama yazıcısı olmaz.
Gerçek model0/ücret0; tüm Gateway için OS firewall/aynıUID izolasyon iddiası yok.

### 2026-10-16T23:31:15.471301+03:00 — D3 QA7e1b seçilmiş teslim

20yeni QA testi sabit hashli;5ilk snapshot ret hatası üründe kapandı, aynı20/20
PASS. Seçilmiş QA rapor/test/kanıt dosyaları stage edildi; ürün/native/Git
yayın247a tek sahibi. İkinci full1273test exit0/skip0 ama native launcher
değişimi ve verify_broker_socket_shutdown.py eklemesi var: NOT_ACCEPTED
snapshot aynen korundu. Son sabitfull/native/CI sonucu bu iki koşudan çıkarılmaz.
Ek gerçek HTTP test dosyası yok; engellenen yazı başka yoldan tekrarlanmadı.

### 2026-10-16T23:33:49.375111+03:00 — D3A yerel kabul ve yayın hazırlığı

Final-v4 aynı source set:1273/1273 standart PASS exit0/skip0;210ölçülen dosya
aynı/yeni0. Beş gerçek Gateway+ayrı broker senaryosu PASS,10süreç exit0; normal
2origin/2grant/1read ve aynı-grant replay ret/ekorigin0. Missing/stale0job/0claim;
provider-limit1origin/1read failed; disconnect1origin/reservedunknown/no-tool.
İki gerçek Docker read konteyneri exactID yok;5profil SQLite/grant/claim ve
broker socket kapanışı ayrıca readonly teyit edildi. Aynı0.3s Unix idle-close
son sürümde PASS. Bu teyitler yeni5yürütme veya gerçek model sayılmaz.

QA7e1b20yeni test aynı iddia/hashlerle okundu,5ilk readerFAIL üründe kapandı.
Onların iki fulltur dosya değişimi nedeniyle NOT_ACCEPTED olarak korunur;
final1273 bizim sabit-v4 koşumuzdur.15responseguard ve3lifecycle kendi testlerimiz;
bütün110yeni vaka1273içindedir. İlk syntax/mock/reader/yanıt/close FAILler silinmedi.

Mevcut ledger, recovery, izole runner ve kaynak pinleri değişmedi;32eski kök dosya
ve4upstream temiz korundu. Yeni provider_egress.py/provider_broker.py + özel
launcher; execution_boundary ve required HostGateClient bağlandı. Ana rapor
 docs/HYB-005D3-PROVIDER-BROKER.md; kanıt evidence/hyb-005d3 ve QA7e1b dizini.
Bu yalnız trusted host üstünde yerel brokered route; sameUID kötü niyetli kod,
remote HTTPS/gerçektarife/tokenizer ve tümOSegress kabulü değil. Legacy direct
mod broker sayılmıyor. Sıradaki D3B OS boundary; M1/M2/hafıza AÇIK.
Commit/push/aynı-SHA CI henüz kapanmadı. Main değiştirilmez.

### 2026-10-16T23:37:18.068867+03:00 — D3 QA7e1b sabit full ve yayın farkı

Üçüncü bağımsız full1273/1273 PASS exit0/skip0,211code/config dosyası drift0.
full-standard-final.json/.txt;20QA testi bu1273içinde. Sonrasında publication
hygiene provider_egress.py EOF boş satırı kaldırıldı:0ef894c8..→fa1d568d... .
Tek fark son boş satır; AST eşitliği ayrıca okundu. Eski native/full makbuz
hashleri DEĞİŞTİRİLMEZ; yeni bytehashin test/CI durumu ayrı kayıt edilmeli
veya test edilen byte korunmalı. Bu bulgu ürün mantığı değişimi değil.

### 2026-10-16T23:38:01.815450+03:00 — D3 QA7e1b final teslim

Sabit-v4 bağımsız1273/1273 PASS exit0/skip0,211ölçülen dosya drift0.20yeni
QA testi bunun içinde; önceki iki NOT_ACCEPTED makbuz korunur. Beş gerçek
native-v4 koşu server source/SQLite/origin/lifecycle kayıtlarıyla readonly
5/5 CORROBORATED; yeni native0, kaynak kayıtları değişmedi. QA rapor/test/
kanıtlar seçilerek stage edildi. EOF tek boşsatır yayınnormalizasyonu ayrı
belgelendi, native/full eski SHA değiştirilmedi; exact-byte CI kapanışı
entegrasyon247a işi. QA ürün/kaynakpin/private-state dosyası değiştirmedi.

### 2026-10-16T23:41:58.821150+03:00 — D3A yayın baytları doğrulandı

Yayın hijyeninde provider_egress.py sonda1boş satır kaldırıldı; Python AST ve
kaynak konumları eşit olsa da tüm kabul son v5 baytlarıyla tekrarlandı.
Full-publication1273/1273 PASS exit0/skip0,210dosya drift0/yeni0. Native final-v5
5/5 PASS; Unix idle-close0.3s PASS. Final-native claim/grant/bütçe ve iki Docker
ID/soket yokluğu ayrıca readonly teyit; bu5ek çalışma sayılmaz. Önceki v4,
1270aday/QA değişmişset/JSimport/reader/response/close hataları korunur.
Finalkanıtlar evidence/hyb-005d3/full-publication.json, native-suite-final.json,
native-final-*.json, publication-native-corroboration.json. Ücretli/model0.
Kod feature commit/push için hazır; main değişmez, exact-SHA CI henüz beklenir.

### 2026-10-16T23:47:11.713639+03:00 — D3A son Git kimliği kontrolü

210test-edilen kaynak/index karşılaştırmasında209dosya birebir aynı. Yalnız
önceki D2config/isolated-read/source-lock.json çalışma kopyasıCRLF/indexLF;
78satırsonu dışında bytefark0, Gitblob base ile aynı, staged değişim değil.
Kaynak kilidi veya eski çalışma kopyası değiştirilmedi. Kanıt
index-byte-verification.json. Yeni/değişmiş bütün ürün/test kodları exactindex.

QA7e1b sonradan sabit-v4 üçüncü tam1273PASS ve5native kaydın readonly teyidini
getirdi; okunarak kaydedildi. İlk iki NOT_ACCEPTED tur aynen korunur. Bizim
sonv5 full-publication1273PASS ve5finalnative ayrı kapsam; sayılar toplanmaz.
Yalnız bu teslimin seçilmiş dosyaları commit/push ediliyor. CI eskiHEADden
aktarılmayacak. Main ve32kök eski dosya/upstreamler değişmiyor.
