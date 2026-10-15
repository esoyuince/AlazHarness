# AlazHarness — status

Son güncelleme:15 Ekim2026. Canlı Git HEAD/status/remote/CI her devamda kontrol edilir.

## Güncel nokta

HYB-005A HOST DISPATCH: LOCAL/NATIVE NARROW ACCEPTANCE PASS; CODE PUBLISHED, EXACT-COMMIT CI PASS.
Mevcut b8ff44f main tabanında kesintiden kalan iki ürün taslağı sürdürüldü.
HostGateLedger, native state_meta yazma sahibi üzerinden izin üretir/tüketir;
HostGateClient yalnız /alaz/host/v1/dispatch kullanır, ham native başlangıca
fallback YOK. Bunlar yeni task queue, agent loop veya ikinci DB değildir.

Aktif dal: alaz/hyb-005-host-gate-6f88.
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
