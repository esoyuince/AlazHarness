# R1B2 request view — independent QA 9B08

17 Ekim 2026. Sonuç: dar R1B2 bağımsız QA COMPLETE; Git/CI yayını aşağıda ayrıca kaydedilir. Ürün yazıcısı AF13; QA ayrı çalışma ağacında.
Kaynak baz e2a5b300568425358e181954cffb697ace2d032b. İlk okunan gerçek
execution_boundary/provider_broker/provider_egress/source_capture modülleri.
Henüz yeni R1B2 API yok; varsayımsal API için test yazılmadı.

## Sözleşme açısından denetlenecek kritik bağlantılar

1. HTTP provider sınırı bugün profil kapsamında; doğrulanmış bir request-run
kimliği taşımıyor. Serbest body.user, model mesajı, tool id veya çağıranın eklediği
manifest kendi başına admission yetkisi/iş sahipliği olamaz. Yalnız mevcut kaynağa
eşlenmiş tool içeriğinin belirli provider payloadında bulunması ile provider
isteğinin o göreve ait olması ayrı iddialar olmalı.
2. Manifest normalization sonrasındaki gerçek payloadı ölçmeli. max_tokens ekleme,
Unicode/CRLF, JSON escape biçimi, tool result kapsülü ve redaction scope ayrı.
3. PREPARED kayıt send olduğuna kanıt değildir. Commit failure/lost ACK -> no send;
transport cancellation/unknown -> no delivery promotion, no refund, no replay.
4. Aynı tool-call ID/aynı metin iki ayrı kaynaktan gelirse belirsiz eşleme ret;
güncel source receipt, settled read ticket ve payload digest birlikte denetlensin.
Değişen içerik, asistanın sahte proof JSONu, eski epoch ve foreign scope ret.
5. Bounded rapor yalnız metadata. Malformed/digest uyuşmazlığı alanı doğrulanmış
saydırmamalı. Eski kayıtlar UNKNOWN, model understanding/goal success false.

Bunlar mevcut sürüm için yeni güvenlik açığı iddiaları değil, uygulanacak R1B2
kabul ölçütleridir. Entegrasyon API okunduktan sonra bağımsız testler yazılacak.
Standart/native/CI kanıtları ve toplamlar ayrı tutulur; yeni servis/model çağrısı yok.

## Baseline transport doğrulaması

10 yeni bağımsız test10/10 PASS. Gerçek authorize_egress/ProviderBrokerClient ve
ExecutionLedger; SQLite owner/IPC sentetik. Native/model0. Kanıt
evidence/r1b2-qa-9b08/transport-baseline.json. Bu sonuç R1B2 değildir.

## Gerçek provider handler normalizasyonu

6 yeni bağımsız kontrol6/6 PASS. Gerçek ExecutionBoundary.bind içindeki POST
handler çağrılır; web.Response ve IPC yalnız test portlarıdır. İstek için
max_tokens belirtilmeyince policy ceiling gerçek egress payloadına eklenir;
explicit ceiling değişmez. Duplicate JSON/multimodal/yanlış bearer claimden
önce ret. Tool content UTF-8/CRLF/escape baytları korunur. Böylece manifestin
normalizasyon ÖNCESİ değil SONRASI fingerprinti kullanması gerektiği ölçüldü.
Bu ağ veya gerçek model deneyi değildir. boundary-baseline.json kaydı.

## R1B2 için planlanan bağımsız ters örnekler — NOT RUN

| Alan | Beklenen ayrım |
|---|---|
| Yabancı body.user veya model proof | İstek sahipliği yaratamaz |
| Aynı kaynak çıktısı iki farklı tool ID | Yanlış kaynakla bağlanamaz |
| Aynı ID ve çıktı, iki kaynak kaydı | Belirsizlik gizlenemez |
| Satırsonu/Unicode değişmiş sonuç | Eski ham hash ile eşlenemez |
| Hazırlama COMMIT ACK kayıp | Sonraki IPC başlamaz; aynı izin tekrar verilmez |
| Yanıt yok/iptal/bozuk yanıt | Başarılı teslim veya anlama ilan edilmez |
| Sonuç gözlem kaydı ACK kayıp | Eylem tekrarı ve bütçe iadesi doğmaz |
| Boş tool metni | Eksik metin sayılmaz; sıfır baytın kendi hash'i vardır |
| Eski epoch/scope/route/claim | Yeni request proof olarak kullanılamaz |
| Eksik veya bozulmuş manifest | Provider görünümü UNKNOWN/ret kalır |
| Eski kayıt | Geriye dönük kaynak veya request görünümü icat edilmez |
| Raporlama | Metadata-only; uygulama yazısı/çalıştırma/onarım yetkisi yok |

Bu tabloda öneri testler vardır; başarı sayısına dahil değildir. Yeni modül
API'si okunmadan isim veya davranış varsayarak ürün tamamlandı denmez.

## R1B2 ilk gerçek API üzerinde29 bağımsız kontrol

Exact candidate-v1 kopyasında29/29 PASS. Source değişmedi. Gerçek request_view,
egress, source_capture, ExecutionLedger ve EvidenceViewInspector kullanıldı;
SQLite owner, native/Docker ve IPC portları sentetik. Hiç native/model başlatılmadı.
Hazırlama/handoff/response/validated ayrımı; önceki kaynak eşlemesi, sonradan
oluşmuş kaynağın eski isteğe bağlanmaması, belirsiz iki source, yanlış toolID
ve metin, boolean/hash/schema/epoch/grant bozulması, optout ve read-only
raporlama ayrı kontrol edildi. InitiatingRunIdNone ve modelProcessingfalse kalır.

İlk29 koşu27PASS/2FAIL: QA helper prepare callbackinden dönüşte failure flagini
COMMITten önce sıfırlamıştı. İlk kaynak/FAIL saklandı. Yalnız enjeksiyonun
kapsayıcı authorize transaction boyunca sürmesi düzeltildi;29test fonksiyonu
AST/assertion değişmeden29PASS. Bu ikiFAIL ürün kusuru diye raporlanmaz.
Test scripts/qa/test_request_view_9b08.py; hedef ALAZ_R1B2_QA_SOURCE ile
açık seçilir. Otomatik baseline CIye dahil değildir. Kaynak receipt
candidate-v1-source.json; sonuç request-view-v1-fixture-fixed.json.

Baseline full1527/1527 PASS,228source sabit,skip0. Bu e2a5b30+16baselineQA
sonucudur; R1B2 son ürün/full/native/CI kabulü olarak kullanılamaz.

## R1B2 HTTP entegrasyonu ve Linux çapraz kontrol

Ayrı6actual HTTP-handler testi6/6PASS: manifest normalize edilen max_tokens
içerir; yanlış model response observed olabilir ama validated olamaz; prepare
hatasında IPCyok; lost transport handoffta kalır; strictbool ve broker şartı.
Aynı frozen source üzerinde29API+6HTTP=35opt-in kontrol başarılıdır.

İki primary gerçek Linux koşusu bağımsız standart kütüphane okuyucusuyla
incelendi; product proof helper import edilmedi ve yeni native iş yapılmadı.
144program/config hash'i, actual-origin raw wire fingerprint ve message
metadata, mevcut claim/egress/source ve terminaltooltext doğrudan eşleşti.
Normal:54baytsource→174bayttool→11220bayt ikinci request. İkinci yanıtkopması:
54→174→11250bayt ikinci request; gerçek originisteğigörmüşolsa bile ürün
yanıtalamadığı için handoff_armed/responsefalse/usageunknown kaldı.
İkiDockerIDyok ve ikibrokerSocketyok. Ana DB/source/capsule/receipt baytları
değişmedi. Bu genel filesystem-silence veya modelanlama kanıtı değildir.

Kanıt native-v1-corroboration.json. Aynı yeni final native koşular ayrıca
mevcut scriptle denetlenecek; ilkikikoşu final6kabulü olarak devralınmaz.
Test kaynakları final-test-custody.json ile sabit; artık yeni test eklenmez.

## Son ürün kaynağı üstünde yeniden doğrulama — 2026-10-17T12:49:01.701504+03:00

Primary request_view güncellemesinin diffi incelendi: bozuk false/0/tool_calls
boşlisteye dönüştürülmez; raporda sourceadayları tek bounded scanle doğrulanır.
Önceki adayda PASS olan35QA yeni kaynakta tekrar çalıştı:35/35PASS;234kod/test/
config/script dosyasında değişim/ekleme yok. Aynı script/assertion hashleri
korundu. Kanıt request-view-final.json. Bu native/model/CI yerine geçmez.

Mevcut tasarımda initiation/user/run maliyet atfı bilerek UNKNOWN kalır.
Kaynak provenance doğru olması provider isteğinin hangi iş tarafından
başlatıldığını doğrulamaz; modelProcessing/understanding false kalır.
Hazırlanan izin ve handoff intent, fiziksel gönderim makbuzu değildir.
Native originin bytes eşleşmesi bu kontrollü deney için ek operatör kanıtıdır;
ürün bilinmeyen yanıtı buna dayanarak geriye dönük başarılıya çevirmez.

## Nihai native teyit — 2026-10-17T12:54:30.382861+03:00

Aynı bağımsız script son6primary Linux profilde değişmeden çalıştı:6/6
CORROBORATED. Her profilde146program/config hash'i eşleşti. Toplam10gerçek
scriptedprovider isteği,5izoleread,6Gateway+6broker kapanışı; bunlar primary
koşularıdır, QA yeni iş çalıştırmadı.5exactDockerIDyok,6socketyok.

Normal ve kısmi okumada source→toolreturn→gerçek originpayload bağlantısı
doğrulandı. Partial4166bayt/250satır source→20satır/594bayttool→11679bayt
ikinci canonical request. İlk20satır içerikte,21/250yok. Provider-limit
dosyaokumasını korur ama ikinci payload/inclusion icat etmez. İlkistek ve
araçsonrasıyanıtkopmalarında handoff_armed/responsefalse/usageunknown; optout
manifestyok, eskiUNKNOWN korunur. InitiatingRun/modelProcessing/understanding
hiçbir durumda true yapılmadı.

Remote script exit0 ve PASS kaydı kaydedildikten sonra local üst taşıyıcının
son sys.exit satırı eksik sys importu nedeniyle exit1 verdi. İş yeniden
çalıştırılmadı. İlk ham-hash karşılaştırması ayrıca Windows LF→CRLF yazımı
yüzünden reddedildi; JSON değerleri aynı, satırsonu farkı tek fark olarak
doğrulandı. Remote orijinal baytlar ayrı native-publication-remote-verbatim.json
ile kayıpsız korundu; önceki yeniden biçimlenmiş kopya değiştirilmedi.
Makbuz native-publication-receipt-verification.json farkı açıkça kaydeder.

Primary full1595/1595PASS/skip0/235source değişmez makbuzu doğrudan okundu;
bu QA tarafından ikinci kez koşulan1595test değildir. QA dalı final1527
PASS/231source ayrı (R1B1baz+16baseline). Opt-in35QA yeniR1B2kaynağına
karşı ayrı çalıştı; primary1595sayısına dahil değil. G01FS-silence veD3B
OSizolasyonu, gerçekmodel/fiyat/token veM1/M2 açık.

## QA yayın paketi — 2026-10-17T12:55:38.065147+03:00

Dal alaz/r1b2-qa-9b08; sadece bağımsız test/script/rapor/kanıt. Core ürün
e2a5b30 tabanındadır. 16baseline test standart1527sayısına dahil;35R1B2
opt-in test explicit hedef kaynakla çalışır, bu dalın default CI sayısında yok.
Primary aynı16testi kendi1595standardına ve35scripti ayrı kabule dahil etmiştir.
Toplamlar birbirine eklenmez. Native6sonkoşu sadece readonly incelendi.

Yerel ilk yeniden biçimlendirilmiş JSONun CRLF baytları da
local-receipt-verbatim.json içindeki UTF8string/SHA256 ile kayıpsız taşınır.
Orijinal remoteJSON native-publication-remote-verbatim.json olarak korunur.
Bu bir biçim saklama ayrımıdır; native makbuz veya test beklentisi değişikliği değil.
Git commit/CI state ayrıca canlı doğrulanacaktır. Main ve ürün kaynakları
değiştirilmedi; gerçek model veya ücretli çağrı yapılmadı.
