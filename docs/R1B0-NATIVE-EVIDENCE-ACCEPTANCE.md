# R1B0 — Gerçek kayıt üzerinde kanıt görünümü kabulü

17 Ekim 2026. Bu paket R1A'nın eksik pozitif native kayıt kabulünü tamamlar.
R1B'nin asıl kaynak yakalama ve sağlayıcıya gönderilen görünüm bağları henüz
uygulanmadı. Ürün tabanı b96a83f545ae12885f025ee0085cb018dad14511;
önceki R1A kodu d56aa994 ve son belge CI sonucu canlı sorguda başarılı bulundu.

## Bu tur değişenler

Mevcut `scripts/verify_evidence_view_retained.py` artık yalnız eski beş sabit
profili değil, operatörün açıkça seçtiği tek bir kayıtlı test profilini de
inceleyebilir. Yeni `--fixture`, `--scenario`, `--receipt-sha256` birlikte
zorunludur. SHA, verilen makbuzun bayt kimliğini sabitler; kriptografik üretici
imzası veya güvenilmeyen hosta karşı kanıt değildir.

Kayıtlı senaryo, sabit Hermes commit'i, başarıyla bitmiş test çalışması,
sıfır gerçek/ücretli model çağrısı, temiz süreç kapanışı ve normal senaryoda
bütçenin korunduğu yeniden açılış kontrol edilir. Eski profil modu korunur.
Yanlış makbuz, başka senaryo, eksik kapanış ve kaynak değişimi başarılı kabul
edilmez. Çıktı yolu normalize edilip runtime kapsamına bağlanır; mevcut çıktı
ve kaynak profilin üzerine yazılmaz. Linkli yollar reddedilir.

Asıl `EvidenceViewInspector`, `HostReportInspector`, Gateway, bütçe defteri,
araç izinleri, kaynak pinleri ve model taşımaları değiştirilmedi. İkinci bir
veritabanı, kuyruk, kanıt otoritesi veya otonomi döngüsü eklenmedi.

## Gerçek native deneyler

Mevcut, daha önce hazırlanmış Windows HTTP/Hermes ortamı kullanıldı. Yeni paket
kurulmadı. Her deney kendi yeni runtime profiline, sentetik anahtarlara ve
küçük test metnine sahipti. Eski profillerin tarihleri, saati ve retention
kuralları değiştirilmedi. Deneyler normal çalışma ve sağlayıcı çağrı limiti
olarak sırayla yürütüldü.

- Normal: bir görev, iki fiziksel kontrollü sağlayıcı isteği ve bir gerçek
  izinli dosya okuması. Aynı profil yeniden açıldığında ek istek veya bütçe
  iadesi oluşmadı. İlk açılış ve yeniden açılış temiz kapandı.
- Sağlayıcı limiti: bir görev, bir fiziksel kontrollü sağlayıcı isteği ve bir
  gerçek izinli dosya okuması. Sonraki sağlayıcı isteği engellendi; görev
  başarılı sayılmadı. Süreç temiz kapandı.

İki görev, üç Gateway süreç yaşamı vardır; yeniden açılış yeni görev değildir.
Gateway, SDK, ajan döngüsü, gerçek dosya aracı ve native durum kaydı kullanıldı.
Model yanıtlarını programlanmış loopback sunucusu verdi: gerçek çıkarım ve
ücretli çağrı sıfırdır. Bu Windows profilleri dar izinli LOCAL dosya yolunu
kullanır; Linux Docker/broker izolasyonu veya Windows OS izolasyonu kabulü
olarak sunulamaz. SSH denemesi exit255 ve boş çıktı verdiği için sunucuya
ulaşıldığı iddia edilmez; sistem servisleri veya ağ ayarları değiştirilmedi.

## Rapor kabulü

İki yeni profil, gerçek güncel saatle ve saklama süresi içindeyken okundu.
Son verifier ile mevcut rapor API'si, JSON CLI ve metin CLI eşleşti. Görevin
başarısız olması rapor doğrulamasının başarısızlığı değildir: limitli görev
`failed` olarak raporlandı ve doğrulanmış rapor CLI exit0 verdi.

Her iki kayıtta bir araç metni, saklandığı biçimde 187 UTF-8 bayttır. Bu boyut
orijinal dosyanın boyutu değildir. Gerçek terminal kaydının canonical JSON
özeti ve saklanan araç metni hash'leri doğrudan SQLite okumalarıyla eşleşti.
Bir baytlık seçim `partial` ve `computed_locally_not_dispatched` kaldı.

Kaynak dosyanın tamamının görülmesi, hangi sağlayıcı isteğine hangi aralığın
gönderildiği, modelin anlaması ve bağımsız hedef başarısı hâlâ doğrulanmış
sayılmaz. İlgili alanlar UNKNOWN/false kalır. Rapor başarıyla okununca yeni
çalıştırma, yeniden deneme, onarım veya bütçe iadesi izni verilmez.

Doğrulamalar sırasında `state.db`, `runs_idempotency.db`, `config.yaml` ve
native makbuz dosyasının önce/sonra hash'leri değişmedi. Özel CLI girişleri
anahtar taşır; yalnız Git dışı runtime dizinlerinde tutulur. Git'e sadece
seçilmiş, sentetik deneyin arındırılmış metadata sonuçları eklenir.

Eski beş HYB005B profili de son verifier ile yeniden kontrol edildi. Beşi de
`retention_expired` ile reddedildi, sıfır kanıt referansı ve CLI exit2 döndü.
Bunlar beş yeni Gateway yürütmesi veya beş pozitif envanter değildir.

## Korunan ilk başarısızlıklar

İlk launch daha eski, HTTP bağımlılığı olmayan hazırlanmış ortamı kullandı ve
`aiohttp` yüklenemediği için ready olmadan kapandı. Her iki süreç sonlandırılmış
olarak doğrulandı, sağlayıcı isteği oluşmadı. Başarısız makbuz korunur.
Doğru mevcut HTTP ortamı import kontrolünden geçirildikten sonra iki taze
kabul profili üretildi. Başarısız profilin içeriği yenilenmedi.

Yeni verifier için 29 offline test eklendi. İlk tur 28 geçti, bir test çıktı
path'indeki `..` normalizasyonunun containment kontrolünden önce yapılmadığını
buldu. Yalnız verifier düzeltildi; aynı test dosyası değiştirilmeden 29/29 geçti.
Bu bir operatör test yardımcı programı yolu hatasıydı; yeni bir dış dosya
oluşturulmadı ve harness'in araç sandbox'ı hakkında bir ihlal iddiası değildir.

Tam standart testin ve aynı commit CI'ın sonucu kendi makbuzunda kaydedilir;
29 test ana toplamın içindedir. Native çalıştırmalar standart CI kapsamına
otomatik eklenmez. Bu tur ayrı bir insan/ajan QA yazarı kullanılmadı.

## Tekrar üretme

Önce mevcut `run_native_execution_gate.py` ile açıkça seçilmiş hazırlanmış
interpreter kullanılarak yeni profil üretilebilir. Bu ayrı, opt-in bir
çalıştırmadır. Aşağıdaki okuyucu tek başına iş/model başlatmaz:

```text
python -B scripts/verify_evidence_view_retained.py --source-workspace C:\Antigravity\AlazHarness --fixture <runtime-altindaki-profil-dizini> --scenario normal --receipt-sha256 <execution-result.json-SHA256> --output <yeni-runtime-cikti-dizini>
python -B scripts/verify_evidence_view_retained.py --source-workspace C:\Antigravity\AlazHarness --expect-expired --output <yeni-runtime-cikti-dizini>
python -B -m unittest discover -s tests -p test_evidence_fixture_verifier.py -v
```

## Devam noktası

R1B0 burada yalnız gerçek kayıt kabulüdür. Sıradaki R1B1, gerçek araç sınırında
kaynak yakalama kimliğini ve kapsamını mevcut yetkili kayıt sahibine bağlamak;
R1B2, normalizasyon/redaksiyon sonrası sağlayıcı isteğinin görünüm kaydını
oluşturmak. Bir metin içindeki model üretimi `complete/seen/proof` alanları
bu kayıtların yerine geçemez. Geçmiş kayıtlar geriye dönük tam/iletilmiş sayılmaz.
D3B OS kimlik/egress, gerçek model-fiyat-token, HYB006 ve M1/M2 açık kalır.

Kanıt: `evidence/r1b-native-8cb8/`. Özel çalışma kayıtları:
`runtime/r1b-native-8cb8/`. Eski araştırma dosyaları diğer çalışma ağacında
korundu. Bu paket main birleşimi veya yeni ürün yetkisi içermez.

## Son kaynak standart kabulü

2026-10-17T10:26:35.129507+03:00: 1403/1403 standart test PASS, exit0, skip0. Ölçülen217kod/test/config
dosyasında değişim veya ekleme yok. Yeni29test bu toplamın içindedir.
Yayın ve CI sonucu bu yerel başarıdan çıkarılmaz; ayrıca kaydedilir.
