# Pi harness ve OpenCode — ilk bileşen incelemesi

Tarih: 15 Ekim 2026. Durum: **STATIC REVIEW / ADOPTION NOT ACCEPTED**.
Bu çalışma kaynak kimliği, seçilmiş kod sınırları, bağımlılıklar ve kabul deneyi
taslağıdır. Tam güvenlik denetimi, performans karşılaştırması veya çalışan
Pi/OpenCode entegrasyonu değildir. Çalışan ana plan hâlâ OpenClaw–Hermes hibritidir;
ayrı bir karar ve deney olmadan motor değiştirilmez.

## Kesintiden geri dönülen nokta

Birleştirilmiş stdio/HTTP paketi `99d6fe16bea4a98ae72f0aff2ceb2ea235bf0851`
commit'inde kayıtlıdır; GitHub `alaz/local-ci` success durumu bağlayıcıyla okundu.
Yerel kök testleri yeniden çalıştırıldı: 128/128 PASS. Önceki gerçek Hermes
AIAgent kurucusu → konuşma döngüsü → read_file → araç sonucunun modele dönmesi
kanıtı korunuyor. Model cevapları yerel betiklenmiş HTTP sağlayıcısından geldi;
gerçek model çıkarımı veya ücretli çağrı yapılmadı. Gerçek Gateway/SessionAuthority,
OpenClaw giriş zinciri, çökmeden devam, parasal bütçe ve M1/M2 hâlâ açık.

İnceleme dalı `alaz/review-pi-opencode-46cc`, temel commit'in devamıdır. Ortak
kirli kök ve başka dalların dosyaları bu incelemeye dahil edilmez. Aynı isimli
kurtarma kaydına bu oturumda yazılan ikinci kontrol, `recovery-recheck.json`
olarak ayrı korundu; birleştirme commit'indeki asıl kayıt değiştirilmedi.

## Kaynak kimliği ve çalışma alanı

| Kaynak | Resmî depo | Sabit commit | İncelenen paket sürümü |
|---|---|---|---|
| Pi | earendil-works/pi | b06c1f2cf1dea6af8748ddeee18c23587d2cb7c6 | agent/ai/durable: 1.2.0 |
| OpenCode | anomalyco/opencode | 3943b84ef00e83dbc3c48e6a92b02f0d88fb35f9 | core/server/client/sdk: 2.0.29 |

İki kaynağın kök lisansı MIT. Referans klonlar `scratch/research-sources/20261015-pi-opencode-46cc/`
altında `pi/` ve `opencode/` olarak bulunuyor. Depth=1, tam kaynak ağacı mevcut;
tam tarihçe yok. Commit'e detached ve push kapalı. Kullanıcı hesabında yeni fork
oluşturulmadı, bağımlılık kurulmadı, uygulama/test kodları çalıştırılmadı.

`config/research-sources.lock.json` yalnız inceleme kaynaklarını ve dosya hash'lerini
tutar. Ürün kaynak kilidi `sources.lock.json`, iki gitlink ve çalışma motorunun
konfigürasyonu değiştirilmedi. Bir referans klasörünün varlığı, uygulanmış özellik
değildir. OpenCode için eski Go deposu değil, yukarıdaki güncel resmî depo esas alındı.

## Pi: üç farklı düzeyi birbirine karıştırmayalım

**Agent core / pi-ai — öncelikli karşılaştırma adayı.**
`packages/agent/src/agent-loop.ts:38–60,207–300` üzerinde açık model çağrısı sınırı,
araç sonucu toplama, `prepareRequest`, `finishTurn` ve iptal/error bitişi görülüyor.
`finishTurn` sonraki turu sürdürme veya bitirme kararı verebiliyor. Bu noktalar
bizim gündem katmanımız için kullanılabilir bağlantı adaylarıdır; hedefleri kendi
kendine seçtiği veya maliyetin otomatik sınırlandığı anlamına gelmez. Agent core
pi-ai ve kendi tip/stream bileşenlerine bağlıdır; tek bir dosya olarak alınması
henüz onaylanmış değildir. Model sağlayıcı katmanının yeniden denemeleri ayrıca
hesaba katılmalıdır.

**Coding-agent SDK — hazır oturum ve araçlar adayı.**
`createAgentSession` (`packages/coding-agent/src/core/sdk.ts:191` giriş simgesi)
çalışma dizini, model/auth runtime, kaynak yükleyici ve oturum yöneticisiyle
birleşiyor. SDK belgesi, SessionManager kaydını bağlamın otoritesi olarak ayırıyor;
`agent_end` ile bütün devam işlerinin bitmesini ifade eden `agent_settled` aynı
şey değil. Varsayılan kullanıcı ayarları/anahtarları/uzantıları yerine testte
ayrı dizin ve açık araç listesi gerekir. Bu seçenek, çıplak Agent core'dan daha
fazla hazır davranış getirir; daha küçük olduğu varsayılmamalıdır.

**Pi Durable — HYB-004 için kuvvetli ama deneysel aday.**
README açıkça experimental diyor. `Harness.open`, `Submissions`, checkpoint
veren görevler ve SQLite/JSONL saklama yapıları tarif ediliyor. Kaynaktaki
`Submissions.submit` kabulü tek commit üzerinden yapıyor; beklemeyi iptal etmek
ile yürütülen işi iptal etmek ayrı işlemler. Araç yeniden oynatma politikası,
körlemesine tekrar çalıştırmak yerine güvenli tekrar işaretini/yarım kalmış
sonucu ayırıyor. Bunlar bizim connection-loss/crash/replay sorunumuza uygundur.
Ancak Chord, pi-ai, görev zamanlayıcısı ve depolama sözleşmesi birlikte incelenmeli;
Hermes'in kalıcı oturumuna ikinci bir yazar olarak eklenmemelidir.

**Somut doğrulanacak boşluk:** `submissions.ts:179–185` görünen tekrar yolunda
aynı conversation/requestId bulunduğunda türü kontrol edip eski kimliği döndürüyor.
Bu kesitte içerik parmak izi eşitliği kontrolü görünmüyor. Bu nedenle mevcut
AlazHarness “aynı anahtar + farklı içerik = conflict” koşulunun sağlandığını
varsayamayız. Bütün sistemi hatalı ilan etmek yerine özel uyumluluk testi gerekir.

Pi ile OpenClaw ilişkisini de sürüm bazında tutuyoruz: elimizde sabitlenen
OpenClaw `package.json` dosyasındaki doğrudan Pi bağımlılığı
`@earendil-works/pi-tui: 1.0.3`. Bu, Pi Agent core/Durable kodunun bu commit'teki
çalışma motorunda zaten bulunduğunu kanıtlamaz. Güncel web örneklerini tarihli
kaynak ağacının yerine koymuyoruz.

## OpenCode: izin ve oturum sınırları

| Alan | Görülen kaynak | Değerlendirme |
|---|---|---|
| İzin değerlendirmesi | core/src/permission.ts:87–100 | Eşleşen son action/resource kuralı; eşleşme yoksa ask. Saf değerlendirme mantığı ile Effect tabanlı servis ayrılabilir adaylar. |
| Onay ve oturum ilişkisi | core/src/permission.ts:1–125 | Bus, Location, Agent, SessionStore, kayıtlı kurallar ve eklenti bağımlılıkları var. Dosyayı kopyalamak bütün yetki sınırını taşımaz. |
| Olay akışı | server/src/event-feed.ts:1–89 | Sınırlı abone kuyruğu; taşma ve kodlama hataları açık hata olarak dönüyor. Sessiz olay kaybı yerine yeniden sorgulama tasarımına yararlı aday. |
| Oturum HTTP sözleşmesi | server/src/handlers/session.ts:1–90; protocol paketi | Tipli hata ve oturum/konum sahipliği önemli. Tam endpoint davranışı henüz test edilmedi. |
| Uygulamaya gömme / istemci | sdk ve client package.json; sdk/src/index.ts | @opencode/sdk yalnız ince HTTP istemcisi değil; core/server/plugin/Effect zinciri içeriyor. @opencode/client ayrı değerlendirilmeli. |

Kaynak `dev` dalının 2.0.29 ağacıdır. `V2_HTTP_API_AUDIT.md` eski uçların
kaldırılması/adlarının değiştirilmesi kararlarını içerir; örneğin `/api/info`
sağlık/sunucu bilgisini birleştiriyor. Eski v1 SDK örnekleri uyumluluk kanıtı
sayılmaz. Audit tablosundaki tikler bizim testlerimiz değildir.

İzin kuralları işletim sistemi sandbox'ı değildir. Benzer şekilde kullanım
kayıtları veya token sayaçları tek başına sert istek/para limiti değildir.
OpenCode'un bütün Effect, veritabanı ve araç bağımlılıklarını sırf izin motoru
almak için taşımak, MVP hızını azaltabilir; maliyet karşılaştırması henüz yapılmadı.

## İlk benimseme kararı

Henüz bu iki kaynaktan ürün kodu alınmadı. Öncelik önerisi: Pi Agent/SDK ile aynı
küçük gerçek araç turunu karşılaştır; Pi Durable'ı ayrı bir restart/replay deneyi
olarak incele; OpenCode'dan izin değerlendirmesi ve olay kaybı/yeniden bağlanma
sözleşmesini seçerek değerlendir. Dört ürünü zincirleyen ikinci/üçüncü model
çağrısı veya bağımsız oturum yazarı ekleme. Ortak model adaptörü ve mevcut
Hermes yerel sonucu karşılaştırma tabanı olsun.

## Sonraki kabul kapıları — henüz çalıştırılmadı

1. **REF-PI-001:** Aynı rastgele dosya işareti, aynı kısıtlı araç, aynı model
   taklidi; gerçek Pi kurucusu/döngüsü üzerinden sonucun yeniden okunması.
   İptal, araç hatası, eksik son olay ve model değişimi senaryolarını ekle.
2. **REF-PI-002:** Pi Durable kabul/yan etki/sonuç kaydı arasındaki kesintiler,
   aynı anahtar + farklı içerik, güvenli olmayan tekrar, iptal edilmiş bekleyici,
   depolama hatası ve yeniden açma. Tek durum sahibi ve bağımsız yan etki sayacı.
3. **REF-OC-001:** İzin önceliği, ask/deny, başka oturumun cevabı, abone taşması ve
   yeniden bağlanma testleri. Endpoint'leri sabit V2 protokolünden çıkar.

Adı bulunan upstream testler manifestte `located_not_run` olarak kayıtlıdır.
Başlangıç adayları: Pi agent-loop, harness-generation-recovery,
harness-cancellation-barrier, harness-nested-tools-restart, harness-storage-failure;
OpenCode permission, event-feed ve session-compaction testleri. Bunların varlığı
ve dosya hash'leri, geçtiğini kanıtlamaz. Benimseme ancak bu deneylerle birlikte
bakım yüzeyi ve bütün model çağrılarının maliyet hesabı görüldüğünde kararlaştırılır.

## Kaynakların yeniden bulunması

Manifestteki `source_url` alanları tam commit'e bağlıdır; satır kapsamları seçilmiş
okumayı gösterir, hash bütün dosyanın sürüm kimliğidir. Herhangi bir değişiklik
öncesi bu pinler ve lisanslar yeniden doğrulanmalıdır. Kapsamın sürüm notları ve
belge referansları: Pi agent README, coding-agent SDK belgesi, Durable README;
OpenCode package manifestleri ve V2_HTTP_API_AUDIT.md. Bunlar yerel test kanıtının
veya uygulanan çalışma ayarının yerine geçmez.
