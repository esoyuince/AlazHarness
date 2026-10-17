# R1B — Linux native evidence qualification (AF13)

17 Ekim 2026. Ayrı QA çalışması; yeni source-capture veya model request-view özelliği uygulanmadı.

## Kaynak ve sahiplik

Ürün tabanı `b96a83f545ae12885f025ee0085cb018dad14511` (R1A). Git archive ile packages/scripts/config/sources.lock.json dosyaları, Git LF baytlarıyla `/tmp/alaz-r1b-af13/code` altına taşındı. Transfer: `code-transfer.json`. Hermes kaynağı mevcut hazırlanmış `eb75627faf532fa6ffbdae59a0d14b0b385fc780` pininde kaldı. Paket, servis, imaj veya bağımlılık kurulmadı; kişisel profile/anahtar kullanılmadı.

Eşzamanlı R1B ürün/yayın sahibi `8cb8` görülünce ikinci ürün yazıcısı olunmadı. Bu dal `alaz/r1b-linux-qa-af13`, çalışma `scratch/worktrees/r1b-linux-qa-af13`; ana ürün adresi `scratch/worktrees/evidence-r1b-8cb8`. Ürün kodu/ana dal/kaynak pinleri ve önceki araştırmalar korunur. Bu QA belgesi 8cb8'in Windows sonuçlarını kendi koşusu saymaz.

## Gerçek Linux deneyleri

Normal, provider-limit ve upstream-disconnect senaryoları taze ayrı profillerde mevcut gerçek Gateway, SessionAuthority, AIAgent, SDK, Unix credential broker ve ağsız Docker read_file zinciriyle yürütüldü. Yalnız model sağlayıcısı kimlik doğrulamalı yerel programlanmış test sunucusuydu. Gerçek model çıkarımı ve ücretli çağrı sıfır.

| Senaryo | Sağlayıcı isteği | Gerçek izole okuma | İş sonucu |
|---|---:|---:|---|
| Normal | 2 | 1 | completed |
| Çağrı limiti | 1 | 1 | failed; ikinci sağlayıcı çağrısı engellendi |
| Sağlayıcı bağlantısı koptu | 1 | 0 | failed; rezervasyon ve bilinmeyen kullanım korundu |

Bu üçü `native/native-suite.json` ve her profilin `broker-native-result.json` kaydında PASS. Normalde aynı egress izninin tekrar kullanımı ek istek olmadan reddedildi. Gateway/broker süreçleri temiz kapandı. İki gerçek araç konteynerinin tam ID ile yokluğu ayrıca Docker inspect üzerinden doğrulandı. Bu sadece önceki kabul edilmiş dar Linux araç sınırı; bütün Gateway için kötü niyetli aynı kullanıcı/OS ağ izolasyonu iddiası değildir.

## R1 raporunun gerçek kayıtlarla karşılaştırılması

Yeni `scripts/qa/r1_linux_evidence_af13.py` bir inceleyicidir; Gateway/model/araç/konteyner BAŞLATMAZ. Hazır kanıtı mevcut ürünün gerçek okuyucusuyla ve JSON/metin CLI ile okur. Docker komutu yalnız kayıttaki tam kimlikle read-only inspect'tir.

Son okumada üç profil PASS. 16 yanlış bearer/epoch/istek/iş/hash/aralık ret kontrolü ve üç sahte gözlemci-metadata kontrolü beklenen sonucu verdi. Bunlar yeni 19 standart unit test değildir; üç gerçek profilin içindeki ilave kontrollerdir. İki tool içeren profilde 1 baytlık yerel görünüm partial, 171 baytlık tam saklanan görünüm complete; JSON/text CLI ile aynı sonuç.

Bağımsız QA, asıl dosyanın 51 baytını kapsüldeki kopya ve D2 binding inputDigest ile eşleştirdi. Saklanan tool çıktısı 171 UTF-8 bayttı. Dosya baytları ve araç çıktısı aynı nesne değil. R1 raporunda ikisi otomatik birleştirilmedi: originalSource sha/coverage, executionAttribution ve model request-view UNKNOWN/not_proven kaldı. Tam bir yerel görünüm, modelin gördüğünü veya anladığını kanıtlamadı. Kaynak içeriği, gerçek dosya yolu ve fixture kimlik bilgileri rapor metnine taşınmadı.

Son tekrar kaynaklar sabitken 66/67/58 mevcut profil dosyasında bayt değişimi göstermedi. Bu dar SON TEKRAR gözlemidir; ilk dosya sistemi açılışında hiç yan etki olmayacağını kanıtlamaz.

## G01 — ilk salt-okunur SQLite bağlantısı yardımcı dosya oluşturabiliyor

İlk üç inceleme, bütün profil dosyalarının aynı kalmasını bekleyen katı kontrolü geçemedi. İlk başarısız kayıtlarda fark listesi tutulmadığından nedeni o kayıt üzerinden kesinleştirilmedi; FAILler silinmedi. İnceleyiciye yalnız before/after manifest tanısı eklendi; mevcut assertion ve beklentiler gevşetilmedi. Aynı üç profilde ikinci okuma 3/3 PASS oldu.

Sonra iki ilave taze normal Gateway koşusuyla ilk-okuma denetimi yapıldı. Birinde doğrudan ürün inspectorünün ilk original SQLite erişimi olması sağlandı: istek anahtarı yalnız düzgün kapanmış, WAL dosyası olmayan replay veritabanının ayrı byte-identical QA kopyasından bulundu. Asıl profil bu hazırlıkta hiç SQLite ile açılmadı. Gerçek `EvidenceViewInspector.inspect` çağrısı, `runs_idempotency.db-wal` (boş) ve `runs_idempotency.db-shm` oluşturdu. Ana iki DB'nin ve diğer mevcut dosyaların hash'leri değişmedi. Rapor `verified_snapshot`, `writesPerformed=false` döndü.

**Karar:** Veri satırı/bütçe/görev değiştirmeme sözleşmesi ile diskte hiçbir dosya oluşturulmaması aynı sözleşme değildir. İlk-okuma filesystem-no-change kabulü FAIL olarak kalır; bir ürün mantığı onarımı yapılmış gibi raporlanmaz. Bu sonuç yetki aşımı veya veri kaybı kanıtı değildir. Sonradan üç profilin değişmeden okunması ilk FAILi kapatmaz.

SQLite'ın resmi WAL belgesi, read-only WAL veritabanında yardımcı WAL/SHM dosyalarının mevcut olması veya oluşturulabilmesi koşulunu açıklıyor: https://www.sqlite.org/wal.html#read_only_databases . Mode=ro ve query_only tek başına sıfır dosya sistemi yan etkisi garantisi değildir. Canlı veritabanına sırf bu testi geçirmek için immutable=1 eklenmedi; kilit/değişiklik/WAL davranışını atlayan bir kestirme benimsenmedi.

G01 sonraki sözleşmede açık olmalı: writesPerformed'in SQL/uygulama yazısı kapsamı belgelensin, filesystem-silent gerekiyorsa ayrı, tutarlı owner snapshot/okuma ortamı tasarlansın ve canlı WAL/eşzamanlı yazıcı durumlarıyla test edilsin. Bu değişiklik source-capture/model-inclusion kanıtı yaratmaz.

## Sayım ve kanıt ayrımı

Üç farklı Linux iş senaryosu + iki normal ilk-okuma tanılama tekrarı = beş GERÇEK yeni native çalışma. Beş farklı özellik senaryosu değildir. Bu çalışmalar sonrası salt-okunur karşılaştırmalar yeni ajan çalışması değildir. Normal/restart Windows çalışmaları başka kapsamdır ve buradaki sayılara eklenmez.

Aynı sabit kaynaklarla tam standart offline paket **1374/1374 PASS**, exit 0, atlanan test yok. Ölçülen 217 kod/test/konfigürasyon dosyasında değişim veya yeni dosya yok. Kesin makbuz `standard-suite.json`. Native ve yanlış-istek kontrol sayıları o toplamın üzerine eklenmez. Bu dalda yeni bir runtime özelliği, model sağlayıcısı veya native test motoru yazılmadı.

## Dosyalar

- `evidence/r1b-linux-qa-af13/native/review-v1/verification.json`: ilk üç FAIL.
- `.../native/review-v2/verification.json`: üç profil ve 16 negatif kontrolün son PASS.
- `.../native/first-read-control/`: daha ayrıntılı ilk-okuma tekrarı.
- `.../native/direct-first-read/direct-reader-result.json`: ürün inspectorü doğrudan ilk erişim; G01 kanıtı.
- `.../native/{normal,provider-limit,upstream-disconnect}/`: gerçek çalışma makbuzları.
- `.../transfer-receipts.json`: gelen 25 metadata/rapor dosyasının hash'leri.

Ham sır içeren config, özel CLI girişleri ve DB'ler yalnız proje runtime veya `/tmp/alaz-r1b-af13` deney ortamında; depoya kopyalanmadı. GitHub'a gidecek dosyalar açıkça seçilir. Ana dal birleştirilmez.

## Kesin sonraki uygulama

R1B1 trusted-source capture kaydını mevcut izole okuma/tek native owner altında üretmek; sonra R1B2 gerçek normalize provider isteğine eklenen veriyle bağlamak. Prepared/yanıt-gözlendi/kayıp yanıt ayrımı korunmalı. Dosyanın tam kapsüle alınması, tool çıktısının tam olması ve modele tam gönderilmesi ayrı kalır. Bu ikisi BU QA PAKETİNDE UYGULANMADI. D3B OS izolasyonu, gerçek model/token/tarife, HYB006 ve tam M1/M2 açık.
