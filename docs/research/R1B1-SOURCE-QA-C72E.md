# R1B1 source capture — independent QA C72E

17 Ekim 2026. Durum QA_COMPLETE; AF13 ürün yazıcısı, C72E yalnız test/kanıt.

## Nihai QA sonucu

C72E bağımsız standart1511/1511PASS, exit0/skip0,226kod/test/config dosyasında
kaynak değişimi veya ekleme yok. 63C72E vaka bu1511içindedir; alt kümeler veya
eski sürüm tekrarları toplama eklenmez. Son tam koşu G03 düzeltmesi sonrası
kaynaklara aittir: full-standard-publication.json. İlk1421/1501source-drift
NOT_ACCEPTED; sabit1504PASS ise G03 öncesi ayrı tarihsel kaynak olarak korunur.

Beş primary publication-v4 native kayıt bağımsız salt-okunur doğrulandı:
full/partial/limit/disconnect/optout. C72E yeni native/model çalıştırmadı.
Kaynak hashleri hem canlı Windows ürünüyle hem Linux yürütülen kaynakla aynı;
source input/kapsül/DBcapture hashleri ve native toolID/terminaloutput hashleri
ayrıca eşleşti. Dört konteynerin exact-ID yokluğu ve beş broker socket yokluğu
kontrol edildi. Ana DB/source/native makbuz byte değişimi yok; G01 filesystem
sessizliği iddiası yok. Kanıt native-publication-corroboration.json.

G03 yeni writerda kapandı: omitted requested alanları NULL, açık limit20
gerçek250satır kaynağın ilk20satırını döndürdü. 21. ve250.satır araç içeriğinde
yok; total_lines250/truncatedtrue. Source4166bayt ile formattedreturn594bayt
ayrı; modelVisibility/understanding UNKNOWN/false kaldı. Eski v3yanlış200kayıtları
onarılmadı veya yeni kabul gibi etiketlenmedi. finding-g03-closure.json.

Ürün/pin/main/Git yazımı QA tarafından yapılmadı. Ürün/yayın sahibi AF13.
R1B2 request-view, D3B OS, gerçek model/token/tarife, beceri transferi ve M1/M2
açık. Bu sonuç yalnız dar R1B1 kaydına aittir.

## Baseline exact-byte capture

Gerçek `isolated_read._snapshot_input` fonksiyonu 18 ayrı unittest ile sınandı.
Geçici dosyalar ve açıkça belirtilen stat/fd portları kullanıldı. UTF-8, CRLF,
BOM ve decode edilemeyen baytlar aynen alınır. Boş ve tam 65536-byte girdi
başarılı; 65537-byte, bağlı dosya, başka uzantı, inode veya metadata değişimi
reddedilir. Ret sonrası descriptor kapanışı da doğrulandı. 18/18 PASS, exit0,
source drift0. Bu native Gateway/Docker/model kanıtı değildir.

Kanıt `evidence/r1b1-qa-c72e/snapshot-first.json` ve `.txt`.
Test kaynağı `tests/test_source_snapshot_qa_c72e.py`, SHA256
85e0b62ab6b0cfd7f16fd522499459bfc6b745f1c8227c13f66e8bad52eedb2e.

## İncelenen gerçek upstream sınırı

Hermes pin eb75627faf532fa6ffbdae59a0d14b0b385fc780. `tools/approval_context.py`
26-31,94-106 satırlarındaki task-local session/tool-call kimlikleri; kaynak
SHA256 9ffa125caadc2253165b069375bcae0065949131baa92a7f2b13fea4c2827ae4.
`tools/file_tools.py` 606-756 gerçek read handler, 1309-1311 registry wrapper;
SHA256 1a23773abe410feb5dd99276d08b6c0837624309ea489c508d683c6965408f94.
Bunlar okunmuştur, test/modül olarak import edilmemiştir.

Tam staging snapshotı ile offset/limit sonucu ayrıdır. Native file reader
line number, truncation/char budget, redaction, binary/error ve dedup yolları
uygular. Dolayısıyla source hash ile returned-content hash eşit olmayabilir;
normalizasyon ardından uyuşmayan terminal sonuç yalnız hash benzerliğiyle
bağlanamaz. Approval context native kapsam dışındaysa yeni kaynak kanıtı
üretilemez; bir kullanıcı metni veya dönmüş JSON yetkili metadata değildir.

## Yeni ürün API için bekleyen inceleme

Gerçek API mevcut olduğunda: owner-transaction kaybı/lost ACK, yabancı session,
generation, ticket, politika ve eski epoch; hata/iptal sonrası sahte tamamlama;
boş/eksik kaynak ayrımı; aynı callback retry; terminal sonucu değiştirme;
reader'ın SQL yazmaması, model görünümü UNKNOWN, rapora kişisel path/content
sızmaması. Bu maddeler henüz çalıştırılmış test değildir.

G01 açık: read-only SQL bağlantısı WAL/SHM yardımcı dosya oluşturabilir.
`writesPerformed=false` no application mutation anlamına gelir; byte-silent
filesystem kabulü olarak raporlanmaz. Canlı veritabanına immutable eklenmez.

Ürün kodu, pinler, main, başka işler veya ücretli servisler C72E tarafından
çalıştırılmadı/değiştirilmedi. Yeni testler ana suite'e alınırsa alt gruplar
tekrar toplanmaz; bağımsız full/native kabul ayrı kaydedilir.

## R1B1 gerçek API üstünde bağımsız 40 test

Ürün `source_capture.py` API ve `isolated_read`/`evidence_view` bağlantısı
okunduktan sonra 40 yeni test yazıldı. İlk koşu 40/40 PASS, exit0, source drift0.
Sentetik SQLite owner ve Docker/native identity portları kullanılır; gerçek
capture/ledger/invoke/report kodları çalışır. Bu bağımsız yazarlı test setidir;
yeni bir native Gateway/model kabulü değildir.

Begin kaydı araç işlevinden önce kalıcıdır. Begin precommit/lostACK ve finish
precommit/lostACK ayrı sınandı: onay kaybı yeni çalıştırma hakkı veya otomatik
bütçe iadesi vermez. Timeout, outputlimit, yanlış container ID, epoch revokasyonu
ve arada silinen/değiştirilen capture kaydı başarısız kalır. Finish ACK kaybında
returned satırı diskte bulunabilir; claim hâlâ reserved olduğu için terminal
mesajıyla doğrulanmış eşleşme ilan edilmez.

Başarılı bağlama scope/admission/generation/ticket/native tool id hash ve
saklanan çıktı boyutu/hash'i ister. Aynı çıktının farklı tool ID'siyle gelmesi,
aynı terminal metnine iki capture talibi, yinelenen sonuçIDleri, yabancı scope,
yanlış epoch/generation, bozulmuş hash/schema/type ve eksik claim ayrı sınandı.
Yeni runtime epoch ve archived admission doğru kayda erişebilir, yeni iş yok.
Silinen kaynak dosya rapor tarafından yeniden açılmaz. Kısmi offset/limit
isteği tam host snapshotını modelin tam gördüğü iddiasına dönüştürmez.

Toplam C72E 58 yeni test: 18 ham snapshot + 40 capture/invoke/report. Testler
ana standarda dahil edilirse altkümeler tekrar toplanmaz. İki test kaynağı
snapshot-test-custody.json ve capture-test-custody.json ile sabitlendi; yeni
test eklenmeyecek. Ürün düzeltmesi gerekirse aynı assertionlarla tekrar edilecek.

İlk baseline full1421 test exit0 olsa da iki ürün dosyası ve source_capture
modülü koşu sırasında değişti/eklendi: baseline-standard.json NOT_ACCEPTED.
Bu kayıt silinmez ve son source sürümünün full kabulü olarak kullanılamaz.
Native ve son sabit full/CI kabulü henüz bu QA tarafından doğrulanmadı.

## G02: registration arama yolu kapanınca lazy import kayboluyor

İlk gerçek Linux v1 normal koşunun başarısız makbuzu bağımsız salt-okunur
kontrol edildi: araç tool_guard_unavailable, capture0, konteyner0. İş ve
sağlayıcı süreçleri temiz kapandı; ham kullanıcı/fixture içeriği okunmadı.
Makbuz SHA256 c402f7b2e4ea63a75ae92ca81121afbfbc1d9ad7575b04dc31c6c86d646f95c6.
`scripts/run_native_host_gate.py:41-56` shim register(ctx) tamamlanınca PRODUCT
arama yolunu kaldırır. İlk aday source_capture importunu invoke içine ertelediği
için gerçek tool çağrısı sırasında ModuleNotFoundError oluşur. Primary AF13
source_capture modülünü plugin kaydı sırasında yükleyerek düzeltmiştir.

Bu native kusur için sabit58QA test değiştirilmeden ayrı2fresh-subprocess
loader testi eklendi. Böylece C72E toplam60 =18snapshot+40capture+2loader.
Bu iki yeni testin İLK çalıştırılması düzeltme SONRASI gerçekleşti:2/2PASS.
Ardından aynı değişmeyen iki test, özel ignored QA kopyasındaki gerçek retained
pre-fix isolated_read.py ile çalıştırıldı:optinFAIL(ModuleNotFoundError),
legacyoptoutPASS. Bu sonradan yapılan eski-sürüm karakterizasyonudur; geçmişte
çalışmış ilk red-test gibi tarih atılmaz. Canlı ürün kaynağı eskiye alınmadı.

Test SHA256 0ef64ca5c25f7378af574f48a3a1ad7c521ab40dfd8758276a0413565239bd28.
Eski isolated_read SHA dcc0f8518a22bae7e6f6deade7ac6a3178712f9c44a970274a4f9e46060ae1b5.
Kanıt loader-first.* ve loader-retained-prefixed.*. İkincisindeki dosya adı
prefixed olsa da içerik ve scope alanı retained pre-fix davranışı açıklar.

İkinci full1501test exit0 ama import düzeltmesi ve primarybootstrap test eklemesi
koşu içinde:full-standard-candidate.json NOT_ACCEPTED. Final freeze sonrası
aynı60QA ve bütün standard tekrar ölçülmeden nihai kabul değildir.

## C72E-G03 — açık varsayılan sayfalama / capture metadata uyumsuzluğu

Son native250satır case bağımsız ilk kapsam kontrolünü geçmedi. Model aracı
yalnız path ile çağırıyor (offset/limit yok). Guard/capture args.get(limit,200)
kullanırken original handlera args limit eklenmeden iletiliyor. Gerçek terminal
sonucunda total_lines250,truncatedfalse; line201 ve line250 içerikte var.
Capture requestedLimit200 yazıyor. Source snapshot4166 bayt, tool dönüş5426.
Bu native veri kapsamının, kayıttaki defaultla farklı olduğunu kanıtlar.

Bu bir model-view kanıtı veya kaynak izin kapsamı aşımı iddiası değil; fakat
partial-case adı, requestedLimit200 ve250satırın gerçekte200e kesildiği kabulü
kapanamaz. Dosya zaten açıkça izinli; R1B1 kendi actualOutputCoverage UNKNOWN
alanı doğru korunuyor. Çağırılan native normalizer/defaultla effective limit
aynı kayda ve gerçek argümana bağlanmalı. Ham omitted/explicit istek ayrımı
korunmalı; salt makbuzu tam/kısmi diye yeniden etiketleyerek düzeltilmez.

Kanıt: native-pagination-observation.txt ve finding-g03.json. İlk C72E
corroboration attempt Docker absence mesajı lower-case olduğu için tanıparserı
başarısızdı; ikinci denemedeki gerçek partial assertionFAIL ayrıca korundu.
Primary final5koşu/probe PASS bu ilave G03 kabulünü kapatmaz.

## G03 çözüm sözleşmesi ve QA taslağının düzeltilmesi

Primary, davranışı değiştirmeden ham istek alanlarını kaydetmeyi seçti:
args içinde bulunmayan offset/limit NULL; açık null veya sınır dışı değer ret.
Bu mevcut requested alanlarının doğru anlamıdır; bu dilim effective output
coverage ölçmez. C72E üç yeni testin ilk taslağında requested=effective ve
omitted native default<=1000 varsaydı; testler çalıştığında primary ham-istek
sözleşmesini çoktan düzeltmişti. Bu nedenle o ikiFAIL ürün kusurunun kapanış
kanıtı değildir; taslak/test kaynağı ve contract-alignment gerekçesi korundu.

Doğru ham-istek sözleşmesine göre aynı üç vaka yeniden yazıldı: omitted alan
NULL kalır; açık offset/limit değişmez; orijinal fingerprint ve çağrı inputu
mutasyona uğramaz. Bu testler yeni üründe3/3PASS; aynı test kaynağı gerçek
retained-v3 source_capture.py ile ayrı ignored QA kopyasında2FAIL/1PASS.
Eski200/1 tahminleri açıkça başarısızdır. Canlı ürün geri alınmadı ve eski
makbuza yeni tarih/sonuç yazılmadı. İlk60QA test kaynakları değişmedi; C72E
63vaka bu turdaki tam sayıdır. Alanların requested/effective ayrımı bir test
beklentisini başarı uğruna gevşetmek değil; kaydın gerçek kapsamını daraltır.

Kanıt pagination-draft-before-contract-alignment.txt, pagination-first.*,
pagination-contract-alignment.*, pagination-current.* ve pagination-retained-v3.*.
Native G03 semantik kapanışı için yeni250satır fixture açık read-limit20 ile
çalışmalı, dönen içerikte line21 bulunmamalı; önceki v3full-output PASSi bu
kabulün yerine geçemez. İlk C72E native helper hata kayıtları da korunur.

Yeni full standard request6d811202-83cd-4f9a-9537-a6433105ed21 G03-sonrası kaynakla
başlatıldı. Önceki1504PASS sabit AMA önceki ürün sürümüdür, bu yeni sürüme
aktarılmaz. Publication full sonucu henüz bu paragraf yazılırken yok.
