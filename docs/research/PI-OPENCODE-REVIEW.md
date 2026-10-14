# Pi ve OpenCode: ek harness kaynak incelemesi

**Tarih:** 15 Ekim 2026. **Durum:** Kaynak ve sözleşme incelemesi; çalışma zamanı kabulü değil.

## Kesintiden sonra hangi noktadayız?

OpenClaw/Hermes stdio ve HTTP adaylarının birleşimi `99d6fe16bea4a98ae72f0aff2ceb2ea235bf0851` commit'iyle `alaz/hyb-003-integration-46cc` dalında kaydedildi ve GitHub'a gönderildi. Kesintideki birleştirme dosyaları yerelde bulundu; 128 test ve kaynak kontrolleri yeniden çalıştırıldı. Aynı commit'in alaz-server makbuzunda 128/128 PASS ve GitHub `alaz/local-ci=success` doğrulandı. Bu, bağlantı hatasının sebebinin bulunduğu anlamına gelmez.

Önceki gerçek Hermes deneyinde genel AIAgent kurucusu, gerçek konuşma döngüsü ve gerçek `read_file` aracı çalışmıştı. Yalnız model HTTP cevapları betiklenmişti. Bu tur o deneyler körlemesine tekrarlanmadı; saklanan makbuzların çalıştırıcı hash'leri doğrulandı. Tam Hermes Gateway, tam OpenClaw olay girişi ve M1/M2 kabulü hâlâ açık.

## Kaynaklar ve edinim sınırı

| Proje | İncelenen resmî depo | Sabit commit | Bu turdaki durum |
|---|---|---|---|
| Pi | `earendil-works/pi`, `main` | `b06c1f2cf1dea6af8748ddeee18c23587d2cb7c6` | Sığ, seçili dizinli yerel referans klonu; MIT |
| OpenCode | `anomalyco/opencode`, `dev` | `3943b84ef00e83dbc3c48e6a92b02f0d88fb35f9` | Sığ, seçili dizinli yerel referans klonu; MIT |

Referanslar varsayılan çalışma alanındaki `scratch/research/20261015-pi-opencode-46cc/{pi,opencode}` altında. Git geçmişinin ve her dosyanın tamamı indirilmedi. Uzak depoya gönderim adresleri `DISABLED`; yeni fork oluşturulmadı. Paket kurulumu, kurulum betiği, uygulama çalıştırma veya model çağrısı yapılmadı.

`config/research-sources.lock.json` bu iki inceleme kaynağının kimliğini, dosya hash'lerini ve gerçekten okunan satır aralıklarını tutar. Bu dosya, kullanılan OpenClaw/Hermes sürümlerini sabitleyen `sources.lock.json` veya üretime alınmış kopyaları tutan `config/components.lock.json` ile aynı amaçta değildir. Bir referans kaydının bulunması kodunun alındığını göstermez.

## Dört projeyi hangi sorumluluklar için değerlendiriyoruz?

| Kaynak | İlgili parça | AlazHarness açısından karar |
|---|---|---|
| OpenClaw | Seçilmiş iptal, süre sınırı ve tamamlanma yardımcıları; daha sonra olay girişi | Mevcut test edilmiş kopyalar korunuyor. Tam Gateway henüz kabul edilmedi. |
| Hermes | Gerçek araç/model döngüsü; hafıza, beceri ve hedef yürütme adayları | Mevcut karşılaştırma temeli korunuyor. Yerel gerçek dosya okuma kanıtı var; diğer yetenekler bu kanıtla kapanmaz. |
| Pi Agent Core | Model sağlayıcısının değiştirilebildiği döngü, araç öncesi/sonrası kancalar, tur sonu kararı | Küçük karşılaştırmalı prototip adayı. Hermes'in yanına ikinci karar döngüsü olarak eklenmeyecek. |
| Pi Durable | Kalıcı görevler, yürütmeden önce niyet kaydı, tekrar politikası, kesintiden devam | Öncelikli deney adayı. Özellikle HYB-004 için değerli; deneysel API ve tek durum sahibi şartı var. |
| OpenCode | Gömülü SDK, oturum yaşam döngüsü, izin hizmeti, yeniden deneme ve bağlam yönetimi | SDK ve izin sözleşmesi için deney adayı. Kaynak ilişkileri netleşmeden tek dosya kopyalamak uygun değil. |

Bunlar ölçülmüş performans veya maliyet sıralaması değildir. Mevcut kodu çöpe atma ya da dört motoru aynı anda çalıştırma kararı alınmadı.

## Pi: bizim ihtiyacımıza yakın iki farklı katman

### Agent Core: küçük ve müdahale edilebilir yürütme sınırı

`packages/agent` paketinin kurucusu model akışını `streamFn` ile alıyor. `prepareRequest` sağlayıcı isteğinden önce; `finishTurn` araç sonuçları tamamlandıktan sonra çalışıyor. `end` ve `continue` kararları mevcut döngü içinde uygulanıyor. Bu, otonomi katmanının ileride nereye bağlanabileceğini incelemek için iyi bir sınırdır; kendi başına amaç üretimi değildir. Her turda koşulsuz `continue` döndürmek yalnızca sonsuz çalışmaya dönüşebilir. [P1]

Bir kancanın her mantıksal turda çağrılması, sağlayıcının kendi yeniden denemelerinin, bağlam özetlemelerinin ve yardımcı isteklerin de aynı bütçeden düşüldüğünü kanıtlamaz. Hermes'te gördüğümüz “bir iterasyon, bir HTTP isteği değildir” ayrımı Pi deneyi için de korunmalı.

### Pi Durable: görev ve kayıt sürekliliği

Pi Durable README'si paketi açıkça **deneysel** olarak tanımlıyor. Kaynakta araç çağrısının son argümanları ve tekrar politikası çalıştırmadan önce checkpoint'e yazılıyor. Kesintiden sonra yalnız hem saklanan hem güncel araç politikası `safe` olduğunda yeniden çalıştırılıyor; aksi durumda kısmen çalışmış olabilecek çağrı `interrupted` sonucuyla kapanıyor. İlgili test gövdelerinde tekrar sayısı ve korunmuş çıktı beklentileri mevcut; bu testler burada çalıştırılmadı. [P2][P3]

Bu yaklaşımın incelenmesi değerlidir: dış etki belirsizken işlemi tekrar yapmak yerine, tekrar edilebilirliği araç bazında ifade ediyor. Bununla birlikte `safe` etiketi kendiliğinden dış serviste tam-bir-kez çalışma garantisi vermez. Araç uygulaması veya karşı servis hâlâ bu iddiayı sağlamalıdır.

**Önemli sözleşme farkı:** Pi aynı konuşmadaki aynı `requestId` ve aynı giriş türü için önceki kaydı döndürüyor; içerik değişikliğini ayrıca karşılaştırmıyor. Testinde `hi` ve `different` aynı kimlikle aynı kayda bağlanıyor. AlazHarness HTTP adayımızın farklı içerik/aynı anahtar durumunda çakışma beklemesiyle eşdeğer değil. Bunu hata diye etiketlemiyoruz; farklı API sözleşmesi. Benimsemek için tek yetkili kayıt sahibinde tutarlı bir içerik parmak izi sözleşmesi gerekir. [P4]

Diğer sınırlar da önemli: README depolamayı aynı anda **tek sürecin** sahiplenmesi gerektiğini, süreçler arası kilit olmadığını belirtiyor. SQLite `synchronous=NORMAL` ayarı süreç çökmesi ile güç/host kaybını aynı garantiye koymuyor. Bellek deposu kalıcı değil; JSONL geçmişi bellekte de tuttuğundan uzun ömürlü ajan için SQLite öneriliyor. Kullanım/maliyet toplamları bulunması, harcamayı önceden durduran bir sınırın uygulandığı anlamına gelmez. [P2]

Gözlem beklemesini iptal etmek işi iptal etmekten ayrı. Arka plan alt görevlerinin ebeveyn iptalinden bağımsız kalabildiği sahiplik seçeneği de var. Bizde varsayılan davranışın ne olacağı açıkça seçilip test edilmeli; “parent bitti, her şey bitti” varsayımı yapılamaz. [P2][P4]

### OpenClaw ile ilişkisi

Pi'nin resmî sitesi OpenClaw'ı bir entegrasyon örneği olarak gösteriyor. Fakat bizim sabit OpenClaw commit'inde doğruladığımız doğrudan Pi paket bağımlılığı `@earendil-works/pi-tui:1.0.3`; eski isimlerde Agent Core/Coding Agent importları taranan alanlarda bulunmadı. Bu yüzden “zaten tam Pi motorunu kullanıyoruz” veya “hiç ilişki yok” sonucuna atlamıyoruz. Güncel Pi kaynağı ile sabit OpenClaw kaynağının bağımlılık ve kod kökeni ayrı değerlendirilmelidir. [P5]

## OpenCode: yalnız terminal arayüzü değil

### Gömülü çalışma seçeneği

İncelediğimiz `dev` commit'inde kök paket 2.0.29; kod `packages/core`, `packages/server`, `packages/protocol`, `packages/sdk` gibi parçalara ayrılmış. Eski `packages/opencode` yollarına göre entegrasyon yazmak doğru olmaz.

SDK README'si ve `EmbeddedHost.create` uygulaması, hazırlanmış sunucu yönlendiricisinin aynı süreçte çağrılmasını gösteriyor: ayrı bir ağ dinleyicisi veya HTTP ağ sıçraması zorunlu değil. Kaynakta varsayılan veritabanı `:memory:`; yeniden başlatmada kalıcılık için açık bir dosya yolu gerekir. Host açılışında askıdaki oturumların sürdürülmesi kendi yaşam döngüsüne bağlanıyor. SDK örneklerinin bulunması bizim ortamımızda kabul edilmiş olması değildir. [O1]

Paket, yalnız ince bir istemci değil: core/server/client/schema/plugin ve Effect bağımlılıklarını da getiriyor. Kaynakta Node/Bun/Workerd seçimleri var; kök geliştirme araç zinciri Bun 1.4.2. Dolayısıyla ne “kesinlikle yalnız Bun ile çalışır” ne de “tek dosyayı alıp Node'a koymak yeterli” diyeceğiz. Özellikle Workerd yolu ileride incelenebilir; bu tur Cloudflare dağıtımı yapılmadı. [O2]

### İzin ve tekrar davranışları

İzin hizmetinde `allow/ask/deny`, eylem-kaynak örüntüsü, ajan/oturum kuralları ve kaydedilmiş onaylar ayrı ele alınıyor. Seçili kaynak, tanımlı reddi kayıtlı izinden önce kontrol ediyor; kapanış bekleyen onayları reddederek sonlandırıyor. `always` seçiminde kaydedilen izinler proje kimliğiyle veritabanına yazılabiliyor. Bu kapsam, genel web kılavuzundaki oturumla sınırlı açıklamadan doğrudan varsayılmamalı; bağlanacağımız commit'in gerçek API'sini kullanmalıyız. [O3]

Bu bize izin kancası ve kapanış sözleşmesi açısından fikir/kod adayı sağlar. Ancak Effect, Bus, Location, Agent, SessionStore ve PermissionSaved bağımlılıkları nedeniyle yalnız `permission.ts` dosyasını kopyalamak tam denetim sistemi oluşturmaz. Araç çalıştırma yolunun gerçekten bu kapıdan geçtiği ayrıca kanıtlanmalı; izin kuralı bir işletim sistemi sandbox'ı değildir.

Oturum gelen kutusunda ilk kabulün kazanması ve aynı oturum/tür kimliğiyle uzlaştırma bulunuyor. Yeniden deneme bileşeni ayrıca sağlayıcı hatası, gecikme ve girişim sayısını değerlendiriyor. Bunları doğrudan bizim idempotency veya sert bütçe sözleşmemizle eş tutmayacağız. İncelenen `max-steps.ts` ise bir prompt metni; onu okumak tek başına araçların kesin engellendiği kanıtı olamaz. [O4]

## Sonraki teknik karar için eşit kabul matrisi

Önerim önce küçük, aynı koşullu Pi Durable deneyi; ardından aynı sınırların OpenCode SDK üzerinden karşılaştırılması. Mevcut Hermes prototipi karşılaştırma temeli kalır. En düşük bağımlılık/yama yüküyle kabulü geçen parça seçilir; yalnız geçmiş yatırım gerekçesiyle Hermes'e, yalnız yenilik gerekçesiyle Pi/OpenCode'a bağlı kalınmaz.

| Deney | Başarı için gerekli gözlem |
|---|---|
| Gerçek döngü, betiklenmiş sağlayıcı | Araç gerçekten çalışır; çıktı ikinci model isteğine girer; kurucu/araç işleyicisi taklit edilmez. |
| Aynı anahtar ve değişmiş içerik | Seçilen sözleşmeye göre açık çakışma; sessizce başka girdinin sonucunu sahiplenme yok. |
| Kabul cevabı kaybı | Aynı iş bulunur; dış eylem yeniden tetiklenmez. |
| Niyet/etki/sonuç arasındaki çökme | Güvensiz dış etki otomatik tekrarlanmaz; belirsizlik korunur. |
| Beklemeyi iptal ve işi iptal | Gözlemcinin ayrılması, işi durdurma ve alt görevlerin kapanışı ayrı doğrulanır. |
| Kalıcılık ve tek sahip | Yeni süreçte kayıt korunur; ikinci süreç aynı durumu kontrolsüz sahiplenemez. |
| İzin ve maliyet | Reddedilen araç çalışmaz; özet/yeniden deneme/yardımcı çağrılar bütçeye dahildir. |

`REF-PI-001` ve `REF-OC-001` bu matrisle iş listesine eklendi; henüz çalıştırılmadı. Mevcut HYB-003 gerçek Gateway testi, HYB-004/005 dayanıklılık ve bütçe işleri kapatılmadı. Otonomi katmanı yine kabul edilmiş M1'in üzerine gelecek.

## Sabit kaynak başvuruları

[P1] [Pi Agent Core README, L124–200](https://github.com/earendil-works/pi/blob/b06c1f2cf1dea6af8748ddeee18c23587d2cb7c6/packages/agent/README.md#L124-L200); [agent-loop.ts](https://github.com/earendil-works/pi/blob/b06c1f2cf1dea6af8748ddeee18c23587d2cb7c6/packages/agent/src/agent-loop.ts#L219-L305).

[P2] [Pi Durable README](https://github.com/earendil-works/pi/blob/b06c1f2cf1dea6af8748ddeee18c23587d2cb7c6/packages/durable/README.md): L1–7 deneysel kapsam; L103–126 devam; L534–580 sahiplik; L648–693 kullanım ve depolama.

[P3] [Pi ToolTask niyet ve tekrar, L107–200](https://github.com/earendil-works/pi/blob/b06c1f2cf1dea6af8748ddeee18c23587d2cb7c6/packages/durable/src/harness/tool.ts#L107-L200); [incelenen test gövdeleri, L109–163](https://github.com/earendil-works/pi/blob/b06c1f2cf1dea6af8748ddeee18c23587d2cb7c6/packages/durable/test/harness-tools-recovery.test.ts#L109-L163).

[P4] [Pi kabul uygulaması, L171–185](https://github.com/earendil-works/pi/blob/b06c1f2cf1dea6af8748ddeee18c23587d2cb7c6/packages/durable/src/harness/submissions.ts#L171-L185); [içerik değişimi ve bekleme testleri, L82–147](https://github.com/earendil-works/pi/blob/b06c1f2cf1dea6af8748ddeee18c23587d2cb7c6/packages/durable/test/harness-submissions.test.ts#L82-L147).

[P5] [Pi resmî sitesi](https://pi.dev/); [sabit OpenClaw package.json](https://github.com/openclaw/openclaw/blob/2dcbb6138d57dccfcd54f2f908ef9f38268b1229/package.json#L2289).

[O1] [OpenCode SDK README](https://github.com/anomalyco/opencode/blob/3943b84ef00e83dbc3c48e6a92b02f0d88fb35f9/packages/sdk/README.md); [EmbeddedHost, L30–70](https://github.com/anomalyco/opencode/blob/3943b84ef00e83dbc3c48e6a92b02f0d88fb35f9/packages/sdk/src/internal/host.ts#L30-L70).

[O2] [OpenCode SDK bağımlılıkları](https://github.com/anomalyco/opencode/blob/3943b84ef00e83dbc3c48e6a92b02f0d88fb35f9/packages/sdk/package.json); [Core runtime seçimleri](https://github.com/anomalyco/opencode/blob/3943b84ef00e83dbc3c48e6a92b02f0d88fb35f9/packages/core/package.json#L32-L75).

[O3] [Permission uygulaması](https://github.com/anomalyco/opencode/blob/3943b84ef00e83dbc3c48e6a92b02f0d88fb35f9/packages/core/src/permission.ts#L87-L347); [kaydedilen onaylar](https://github.com/anomalyco/opencode/blob/3943b84ef00e83dbc3c48e6a92b02f0d88fb35f9/packages/core/src/permission/saved.ts); [ilgili test gövdeleri](https://github.com/anomalyco/opencode/blob/3943b84ef00e83dbc3c48e6a92b02f0d88fb35f9/packages/core/test/permission.test.ts#L235-L335).

[O4] [Oturum gelen kutusu, L154–180](https://github.com/anomalyco/opencode/blob/3943b84ef00e83dbc3c48e6a92b02f0d88fb35f9/packages/core/src/session/inbox.ts#L154-L180); [yeniden deneme bileşeni](https://github.com/anomalyco/opencode/blob/3943b84ef00e83dbc3c48e6a92b02f0d88fb35f9/packages/core/src/session/runner/retry.ts).

Bu başvurular seçili statik incelemenin kapsamıdır; bütün depoların veya bütün testlerinin denetlendiği iddiası yoktur.
