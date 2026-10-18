# WrongStack incelemesi — AlazHarness için bileşen ve otonomi değerlendirmesi

**Karar: değerli bir bileşen/tasarım kaynağı; bütün üçüncü motor olarak ekleme önerisi yok.**

İş: WRONGSTACK-REVIEW-4F91. Tarih: 18 Ekim 2026.
Kaynak: `WrongStack/WrongStack`, sürüm **1.1.8**.
Sabit commit: `ffbd572d593cf25e840299773455ee096ddaf237`.
Alaz inceleme dalı: `alaz/research-wrongstack-4f91`.
Alaz başlangıcı: `b3197e2f2266bfd998920f7b2c1400c39bbc6195`.

## 1. Sonuç ve kapsam

WrongStack, yalnızca sohbet ekranı veya başka bir terminal ajanını saran ince bir
arayüz değildir. Kodda hedef döngüsü, faz/görev yürütücüsü, rol tabanlı alt ajanlar,
kalıcı hafıza, role özel talimat geliştirme, araç yönlendirme ve farklı güvenlik
katmanları vardır. Kullanıcının her adımda yeniden komut vermeden bir görevi
sürdürme hedefimize ciddi bir uygulama örneği sunar. Bununla birlikte kaynak
incelemesi, bağımsız irade veya yeni görevlerde doğrulanmış öğrenme sonucu değildir.
Bir hedefin ve çalıştırma modunun önceden seçilmesi hâlâ gerekir. [S03] [S26]

Bu turda kaynak kod indirildi ve sabit sürümde **58 dosya** incelendi:
32 dosya tam metin, 26 dosya seçilmiş aralık/sembol veya test başlığı düzeyinde.
Ayrıca 36 çalışma alanı paketinin metadata bağımlılıkları okundu. Tam liste,
inceleme derinliği ve Git blob/SHA-256 değerleri `coverage.json` içindedir.
11.909 izlenen dosyanın tümü için güvenlik denetimi yapılmış değildir.
4.503 test/spec dosya adı eşleşmesi bulundu; bu sayı çalıştırılmış test veya
başarılı kabul sayısı değildir. **WrongStack kurulmadı, testleri çalıştırılmadı,
ajan/model başlatılmadı; hiçbir ürün kodu Alaz'a aktarılmadı.**

Kök LICENSE MIT ve telif sahibi 2026 ECOSTACK TECHNOLOGY OÜ'dür. İncelenen 36
paket manifesti de MIT bildirir. MIT metni, kopyalarda veya önemli kod parçalarında
telif ve izin bildiriminin korunmasını ister. Üçüncü taraf paketlerin, gömülü
varlıkların ve ayrı dağıtımların tamamı için lisans taraması yapılmadı; kök
lisansından bütün bağımlılıklara otomatik sonuç çıkarılmamalı. [S01] [S02]

## 2. Otonominin iki farklı yürütme yolu

### Hedefe karşı sürekli çalışan döngü

`EternalAutonomyEngine`, bekleyen görevler, Git durumu ve modelin ürettiği sonraki
adım adaylarından iş seçer; ajanı çalıştırır, sonucu kaydeder ve döngüye devam
eder. Hedef yoksa durur. Yani burada gerçekten her iterasyon için ayrı insan
komutu gerekmeyen bir yürütme düzeni vardır. Ancak kullanıcı tarafından verilen
kalıcı amaç ile modelin kendi öznel isteği aynı kavram değildir. Bu inceleme
ikincisini göstermiyor.

Bu yolun tamamlanma kuralları Alaz'a aynen taşınmamalı. Başarılı sayılan bir
iterasyondaki `[GOAL_COMPLETE]` modeli durdurup hedef dosyasını temizleyebiliyor;
koordineli ilerleme yokken `[PROGRESS: 100%]` de hedefi tamamlatabiliyor. Kaynak
bunu maliyet azaltmak için ayrı doğrulayıcı çağırmamak olarak açıkça anlatıyor.
İlgili testler de bu davranışı bekliyor. Brain bağlanmamış bazı tamamlanma
heuristiklerinde olumlu karar verilebiliyor. Bu bütün WrongStack tamamlanma
yollarının aynı derecede zayıf olduğu anlamına gelmez; aşağıdaki faz yolu farklıdır.
[S17] [S18]

İncelenen eternal yürütücü kendi içinde genel yaşam süresi/toplam maliyet tavanı
koymama tercihini belgeliyor; iterasyon sınırları, yeniden deneme beklemeleri ve
ayrı alt ajan/fleet bütçe kodları ise mevcut. Dolayısıyla doğru sonuç, 'projede
bütçe yok' değil, **sınırsız tekrar seçeneğinin Alaz'ın dışarıdan uygulanan toplam
bütçesine bağlanmadan alınmaması gerektiği**. `/autonomy eternal` ve parallel
komutları da etkileşimli onayları azaltan YOLO modunu açtığını bildiriyor; açık
ret kuralları yine geçerli. Otonomi seçimi bizim ürünümüzde yeni yetki verilmesi
anlamına gelmemeli. [S26]

### Faz grafiği, çalışma kopyası ve kabul kapıları

Daha güçlü örnek; görev amacı ile yürütme kimliğinin ayrılması, faz bağımlılıkları,
her faza ait Git worktree, görevlerin bitmesinden sonra doğrulama ve birleştirilmiş
son ağacın tekrar kontrol edilmesi. Hedefe ait çalışma dalı ile ana depo ayrılıyor.
Kurtarma kodu, kaybolmuş/eski worktree kimliğini sessizce ana klasörle değiştirmiyor;
tamamlanmış işleri koruyor ve eski nihai doğrulama sonucunu yeniden değerlendirme
öncesinde temizliyor. [S03] [S04] [S20]

Özellikle `GoalTaskExecutionOwnership` yararlı: zaman aşımı isteği iptal etmekle
aynı görevin gerçekten kapanmasını ayırıyor. Eski çalışan hâlâ yazabiliyorken
aynı görev yeniden başlatılmıyor ve çalışma yeri serbest sayılmıyor. Ancak bu
küçük sınıfın kendisi süreç içi Promise/Map yönetimidir; tek başına disk üstünde
kalıcı epoch/lease veya sistemler arası tam-bir-kez garantisi değildir. [S05]

Faz doğrulama callback'i bağlanmadığında kapı başarılı no-op dönebiliyor;
nihai `verifyGoal` de çekirdekte opsiyonel. Kanban tarafında strict/soft/off
farkı var; soft hatada uyarıyla completed olabilen yollar mevcut. Bu yüzden
'her completed bağımsız doğrulandı' denemez. Bizde eksik doğrulayıcı
**NOT_RUN** olmalı, PASS değil. [S19] [S20] [S21]

## 3. En değerli hafıza örneği: SAGE ve Memory Companion

### Bilginin doğruluğu, güncelliği ve bu işe uygunluğu ayrılıyor

SAGE'in model geri bildirimi `observedRevision` ile belirli bir hafıza sürümüne
bağlanıyor. Eski revizyona yazma reddediliyor; yinelenen yorumlar ayrıştırılıyor;
yorum doğrudan güven puanı veya doğruluk terfisi almıyor. Hafızanın koşullu
geçerliliği için dosya/bağlantı kontrolleri yapılabiliyor; dosyada metin bulunması
bütün koşulların sağlandığına eşit değil ve `applicability` bilinmeyen kalabiliyor.
Kaynak kontrolü başarısız veya süreyi aşmışsa belirsizlik saklanıyor. [S10] [S11]

Bu ayrım Dream'e doğrudan uyuyor: 'geçmiş kayıtta bu cümle var', 'kaynak bugün
aynı', 'bu ders bugünkü görev için uygun' ve 'bu ders başarıyı artırdı' dört ayrı
iddia olmalı. Mevcut D1/D2A kayıtlarımızın yanına koşul ve kaynak revizyonu koymak,
her şeyi yeni bir SAGE veritabanına taşımaktan daha düşük riskli bir uyarlamadır.
Bu öneri henüz uygulanmadı.

### Yardımcı ajan sınırı çıktıdan sonra da denetleniyor

Memory Companion bayat, itiraz edilmiş veya kaynağı değişmiş bir notu dar bir
incelemeye alıyor. Başlangıçta ve sonuç döndükten sonra hafıza revizyonunu ve
kaynak içerik özetini yeniden okuyor. Kaynak, inceleme sürerken değişmişse sonuç
kullanılmıyor. Son asenkron dosya kontrolünden sonra revizyonu tekrar kontrol
etmesi özellikle iyi bir yarış durumu önlemidir. Oturum kapanması, farklı
izleyici/oturum kapsamı ve `contextPolicy=never` gibi durumlar da kontrol ediliyor.
Dönen sonuç tavsiye niteliğinde; yardımcı kendi başına hafızayı değiştirmiyor.
[S08]

İlgili araç sınırı proje/rol ayarları birleştirildikten **sonra** yeniden uygulanıyor:
yalnız okuma/arama araçları ve sonuç gönderimi, en fazla 8 iterasyon, 12 araç
çağrısı, 12.000 token, 0,15 USD yapılandırılmış maliyet tavanı ve 60 saniye.
Bu rakamlar ölçülmüş gerçek maliyet değil, kaynakta tanımlı sınırlardır.
Tek aktif inceleme, sınırlı kuyruk ve revizyon/kaynak bazlı bekleme süresi gereksiz
model çağrılarını azaltmayı amaçlıyor. Bu uygulama düzeyi sınırı tek başına
kernel sandbox anlamına gelmez. [S09] [S08]

**Uyarlama önerisi:** D3B birleşik kabulünden sonra aynı ExecutionLedger üzerinden
bütçelenen, yalnız aday değerlendirme raporu üreten bir `memory-review` görevi.
Ayrı sürekli çalışan sonsuz ajan veya ikinci yazıcı değil. Kesin kabul testleri:
eski revizyon reddi; kaynak yarışında sonuç iptali; oturum kapandıktan sonra
geç sonuç reddi; role yapılan genişletmenin sınırı aşamaması; yeni izin yok;
hafıza terfisi yok; gözlenen bilginin öğrenme başarısı gibi raporlanmaması.

## 4. Rol öğrenmesi ve skill geliştirme: gerçek uygulama, sınırlı ölçüm

Yanıtları sadece geçmişe kaydetmenin ötesinde `learned.md`, rolün
`consolidated.md` dosyası ve skill başına proje ekleri tutuluyor. Bu ekler sonraki
ajan başlangıcında talimata dönüyor. Dosya boyutları sınırlandırılmış; yönlendirme
ve skill kullanım/başarı sayaçları var. Konsolidasyon, modelin gördüğü kaynak
anahtarlarını saklayarak arada gelen yeni derslerin yanlışlıkla silinmesini
önlemeye çalışıyor. Bu, gerçek bir kalıcı prosedürel bağlam geliştirme örneği;
model ağırlıklarının güncellendiğine dair incelememizde bulgu yok. [S14] [S15] [S16]

Fakat **metrikteki kontrol grubu gerçek 'talimat yok' grubu değil**. Kod, talimat
promptta bulunduğu hâlde görev raporunda kullanımı görülmediyse bunu kontrol
koluna yazıyor. Kullanımı belirlemek için komut/yol kelimeleri veya ayırt edici
sözcük eşleşmeleri var. Talimat raporda anılmadan davranışı etkileyebilir; anılması
da başarıya onun neden olduğunu kanıtlamaz. Kaynak zaten bunu nedensel ispat
değil korelasyon olarak niteliyor. [S12]

`directiveLift`, uygulandı diye sınıflanan görevlerin düzeltilmiş başarı oranıyla
kontrol sayılan grubun oranını çıkarıyor. Bu gösterge sıralama, eskime ve
karantina için yararlı olabilir; yeni görevde neden-sonuç deneyinin yerine
geçmez. Bazı 'proven' işaretleri eski kayıtları korumak için yeterli kontrol
kolu olmadan da korunabiliyor. Alaz'ın gerçekten derssiz ve dersli iki koşulunu
ayıran D2B planını bu yaklaşım ile değiştirmemeliyiz. [S13]

Ayrıca rol öğrenmesi politikasında varsayılan enabled ve eksik/okunamayan politika
üzerinden varsayılana dönüş yolları var. Bu ürün tercihi, bizim açık opt-in ve
korumalı terfi sözleşmemizle aynı değil. **Talimat kaydetme, talimatın faydalı
olduğunu ispatlama ve aktif skill'e alma ayrı durumlar olarak kalmalı.** [S29]

## 5. Küçük, güçlü parça: sonuç farkına duyarlı döngü kesici

Aynı araç adı ve argümanların tekrar etmesi her zaman tıkanma değildir; dosyanın
veya iş durumunun değişmesini bekleyen bir okuma faydalı olabilir. WrongStack
bu yüzden iterasyon imzasına araç girdisi yanında sonucu da katıyor. Aynı
adımların periyodik olarak dönmesini ve aynı sonucun tekrarını ayrı yakalıyor.
Tam, temizlenmiş araç çıktısının SHA-256 bağı görünür özetin dışında saklanıyor;
rastgele çıktı dosyası yolu değişmesi yeni kanıt sayılmıyor. Blok içeriği sonradan
değiştirilirse eski özet bağı kullanılmıyor. [S06] [S07]

Bu, hem maliyet hem kullanıcının 'sanki ilerlemiyoruz' hissi için doğrudan değerli.
Alaz uyarlaması yeni bir model gerektirmeden `tool + canonicalArgs + resultDigest
+ effectState` imzasını mevcut işlem kaydından üretebilir. Eşdeğer tekrar önce
uyarı/bekleme, sonra bütçe sınırında duraklama üretmeli; modelin aynı şeyi daha
farklı kelimelerle anlatması ilerleme kabul edilmemeli. Sadece zaman damgası
farkı gibi durumları nasıl ele aldığımız ayrıca test edilmeli. SHA tek başına
semantik ilerleme kanıtı değildir.

## 6. İzolasyon ve yetki: aynı şeyleri ölçmüyoruz

Kaynakta varsayılan sandbox `off` ve `policy-only`; policy-only backend hiçbir
çağrıyı reddetmiyor. Dolayısıyla yalnız `enforced` etiketini görmek kernel
izolasyonu kanıtı değil, seçilen backend ve gerçek yönlendirme de önemli.
Bununla birlikte projede sadece göstermelik koruma yok: container backend'i
bash/exec için Docker komutu ve ağsız yönlendirme üretir; image veya runner yoksa
reddeder. Windows-native yolu da restricted-token helper kullanımı ve eksik
helper için reddetme içerir. Bu yollar bu incelemede çalıştırılmadı. [S22] [S23]
[S24] [S25]

Container katmanının kendi açıklamasında git/pwsh için kapsam farkı var;
MCP araçları da dış sunucuda çalıştığından yerel argv sandbox'ıyla eşdeğer değil.
İncelenen sarmalayıcı bunlara ayrı ret/güven/tek-çağrı onay kuralları uyguluyor.
Bütün Gateway'in dosya/ağ kimliğini, broker sırrını ve bütçe otoritesini aynı
anda sınayan D3B hedefimizin yerine bu araç katmanını geçirmemeliyiz.

Kanıt kabulünde de benzer ayrım var: `EvidenceValidator`, referans sayısı/türü
ve açıklamanın aşırı belirsiz olup olmadığını denetler. Bu sınıf tek başına
verilen dosya yolunun gerçek olduğunu, komutun çalıştığını veya test çıkışının
sahte olmadığını doğrulamaz. Başka doğrulayıcılar olabilir; bu gözlem bütün
sistemde sahte kanıt açığı ilanı değildir. Alaz'da dış deneme çıktısının gerçek
sağlayıcı/işlem kaydıyla bağını ayrıca korumamız gerekir. [S27]

## 7. Alaz'a aktarılabilecek ilk paket

Aşağıdakiler **uygulama önerisidir, bu turda yapılmadı**.

| Öncelik | Kaynak fikir | Alaz'a uyarlama | Korunacak sınır |
|---|---|---|---|
| P1 | Görev sahipliği ve settle bekleme | goal/run/attempt/workspace kimliğiyle mevcut state sahibine bağlama | Timeout sonucu UNKNOWN olabilir; eski yazıcı sürerken kör tekrar yok |
| P1 | Sonuç farkına duyarlı tekrar tespiti | Mevcut araç makbuzundan model kullanmadan ilerleme imzası | Farklı çıktı yolu veya model iddiası ilerleme değil |
| P1 | Koşullu hafıza ve revizyon kontrolü | D1/D2A adayına güncel kaynak/uygulanabilirlik bilgisi | Geçerlilik kontrolü öğrenme ispatı veya izin değil |
| P2 | Sınırlı Memory Companion | Olayla tetiklenen dar salt-okunur inceleme görevi | Aynı bütçe sahibi, tek sonuç kaydı, otomatik hafıza yazımı yok |
| P2 | Faz grafiği ve merged-tree doğrulaması | Küçük kalıcı görev yürütücüsü; zorunlu final doğrulama | Callback yoksa NOT_RUN; ana dal otomatik birleştirme yok |
| P3 | Role/skill'e özgü konsolidasyon | Deneyle kabul edilmiş derslerden sınırlı, geri alınabilir ek | Modelin kendi raporu bağımsız başarı puanı olmaz |

Bunların üstünde Brain benzeri ucuz karar seçimi kullanılabilir: tekrar limiti,
açık başarısızlık veya bekleme kararı için deterministik kurallar; belirsiz
strateji için model; yüksek etkili işlem için mevcut insan/host politikası.
Modelin önerdiği 'düşük risk' etiketi izin veya bütçe genişletmesin. [S28]

Bu tasarımda WrongStack'ten alınan katman yalnız **sonraki eylem önerisi** üretir.
Gerçek çağrı mevcut HostGate/ExecutionLedger ve izolasyon zincirinden geçer.
Tek state sahibi, tek bütçe defteri, tek yetki kapısı korunur. Yeni SAGE
veritabanı, ikinci sağlayıcı döngüsü, ikinci bağımsız otomatik scheduler ve
aynı notları farklı biçimde yazan iki hafıza otoritesi eklenmez.

## 8. Neden bütünüyle üçüncü motor değil?

Paket manifestlerinden hesaplanan iç bağımlılık kapanışı, core için kendisi dâhil
4, SAGE için 5, runtime için 10, CLI için 35 çalışma alanı paketine uzanıyor.
Bu sayılar gerçek derlenmiş boyut veya tüm transitif npm bağımlılıkları değil;
yalnız incelenen manifest grafiği. Yine de 'SAGE'i tek dosya takarız' varsayımının
neden güvenilir olmadığını gösteriyor. TypeScript paketleri arasında ortak event,
kimlik, depolama, sağlayıcı ve araç tipleri var.

Alaz altyapısını sırf daha önce emek verdik diye korumak doğru gerekçe olmaz.
Karşılaştırmalı sınırlı bir pilot, ileride WrongStack temelinin açıkça daha uygun
olduğunu gösterebilir. Fakat bu kaynak incelemesinden 'motoru değiştirince daha
ucuz ve güvenli olur' sonucu çıkmıyor. Şu an en ekonomik yaklaşım küçük modüller
ve sözleşmeler üzerinden seçim; temel değişikliği için aynı görevler, model,
bütçe ve kabul ölçütleriyle ayrı deney gerekir. Bu deney bu turda yapılmadı.

**Kesin sıralama önerim:** başlamış D3B birleşik kabulünü tamamla; sonra görev
sahipliği/tekrar kesici ve hedef önericisini küçük bir otonomi dilimi olarak ekle;
ardından koşullu Dream hafızası ve kısıtlı inceleme görevi. Skill'e kalıcı yazımı
ancak bağımsız dersli/derssiz başarı ve gerileme testi kabul ederse değerlendir.
Bu, kullanıcının daha hızlı ve maliyet etkin hibrit geliştirme amacını, kanıt
sözleşmesini atlamadan sürdürür.

## 9. Teslim, kapsam dışı işlemler ve devam

Harici kaynak detached commit olarak `scratch/research-sources/wrongstack-ffbd572`
altında saklandı. Kendi upstream fork'u oluşturulmadı. Rapor ve kaynak manifesti
Alaz'ın ayrı araştırma dalındadır. Kök `status.md`, D3B dosya/ağ çalışma ağaçları,
ürün paketleri, sağlayıcı ayarları, test kaynakları ve main değiştirilmedi.

WrongStack build/test/native acceptance **NOT_RUN**; bağımlılık kurulumu **YOK**;
gerçek/ücretli model çağrısı **YOK**; kod transplantasyonu **YOK**. Alaz'ın önceki
1903 test sonucu önceki ürüne aittir; bu inceleme adına yeniden PASS sayılmaz.
Raporun kaynak eşleşmesi ve Git teslimi, çalışma zamanı kabulünden ayrı kaydedilir.

## Kaynak referansları

Bütün bağlantılar yukarıdaki tek commit'e sabittir. Satır aralıkları iddianın
kaynağını gösterir; bütün paket veya dağıtım denetimi anlamına gelmez.

- [S01] [LICENSE](https://github.com/WrongStack/WrongStack/blob/ffbd572d593cf25e840299773455ee096ddaf237/LICENSE#L1-L21)

- [S02] [package.json](https://github.com/WrongStack/WrongStack/blob/ffbd572d593cf25e840299773455ee096ddaf237/package.json)

- [S03] [docs/architecture/project-goals.md](https://github.com/WrongStack/WrongStack/blob/ffbd572d593cf25e840299773455ee096ddaf237/docs/architecture/project-goals.md)

- [S04] [packages/core/src/goal/goal-run-lifecycle.ts](https://github.com/WrongStack/WrongStack/blob/ffbd572d593cf25e840299773455ee096ddaf237/packages/core/src/goal/goal-run-lifecycle.ts#L1-L89)

- [S05] [packages/core/src/goal/task-execution-ownership.ts](https://github.com/WrongStack/WrongStack/blob/ffbd572d593cf25e840299773455ee096ddaf237/packages/core/src/goal/task-execution-ownership.ts#L1-L71)

- [S06] [packages/core/src/utils/tool-result-fingerprint.ts](https://github.com/WrongStack/WrongStack/blob/ffbd572d593cf25e840299773455ee096ddaf237/packages/core/src/utils/tool-result-fingerprint.ts#L1-L29)

- [S07] [packages/core/src/core/agent-loop-detector.ts](https://github.com/WrongStack/WrongStack/blob/ffbd572d593cf25e840299773455ee096ddaf237/packages/core/src/core/agent-loop-detector.ts#L1-L170)

- [S08] [packages/cli/src/fleet/host-memory-companion.ts](https://github.com/WrongStack/WrongStack/blob/ffbd572d593cf25e840299773455ee096ddaf237/packages/cli/src/fleet/host-memory-companion.ts#L155-L345)

- [S09] [packages/cli/src/fleet/memory-companion-policy.ts](https://github.com/WrongStack/WrongStack/blob/ffbd572d593cf25e840299773455ee096ddaf237/packages/cli/src/fleet/memory-companion-policy.ts#L1-L53)

- [S10] [packages/sage/src/shared/model-feedback.ts](https://github.com/WrongStack/WrongStack/blob/ffbd572d593cf25e840299773455ee096ddaf237/packages/sage/src/shared/model-feedback.ts#L1-L60)

- [S11] [packages/sage/src/retrieval/validity-checks.ts](https://github.com/WrongStack/WrongStack/blob/ffbd572d593cf25e840299773455ee096ddaf237/packages/sage/src/retrieval/validity-checks.ts#L1-L60)

- [S12] [packages/core/src/coordination/agents/project-agent-directive-outcome.ts](https://github.com/WrongStack/WrongStack/blob/ffbd572d593cf25e840299773455ee096ddaf237/packages/core/src/coordination/agents/project-agent-directive-outcome.ts#L160-L245)

- [S13] [packages/core/src/coordination/agents/project-agent-learning-structured.ts](https://github.com/WrongStack/WrongStack/blob/ffbd572d593cf25e840299773455ee096ddaf237/packages/core/src/coordination/agents/project-agent-learning-structured.ts#L90-L165)

- [S14] [packages/core/src/coordination/agents/project-agent-capture.ts](https://github.com/WrongStack/WrongStack/blob/ffbd572d593cf25e840299773455ee096ddaf237/packages/core/src/coordination/agents/project-agent-capture.ts)

- [S15] [packages/core/src/coordination/agents/project-agent-skill-layer.ts](https://github.com/WrongStack/WrongStack/blob/ffbd572d593cf25e840299773455ee096ddaf237/packages/core/src/coordination/agents/project-agent-skill-layer.ts#L1-L43)

- [S16] [packages/core/src/coordination/agents/project-agent-consolidation.ts](https://github.com/WrongStack/WrongStack/blob/ffbd572d593cf25e840299773455ee096ddaf237/packages/core/src/coordination/agents/project-agent-consolidation.ts#L153-L245)

- [S17] [packages/core/src/execution/eternal-autonomy.ts](https://github.com/WrongStack/WrongStack/blob/ffbd572d593cf25e840299773455ee096ddaf237/packages/core/src/execution/eternal-autonomy.ts#L325-L395)

- [S18] [packages/core/src/execution/eternal-completion.ts](https://github.com/WrongStack/WrongStack/blob/ffbd572d593cf25e840299773455ee096ddaf237/packages/core/src/execution/eternal-completion.ts#L65-L149)

- [S19] [packages/core/src/goal/phase-orchestrator-gates.ts](https://github.com/WrongStack/WrongStack/blob/ffbd572d593cf25e840299773455ee096ddaf237/packages/core/src/goal/phase-orchestrator-gates.ts#L67-L115)

- [S20] [packages/core/src/goal/phase-orchestrator.ts](https://github.com/WrongStack/WrongStack/blob/ffbd572d593cf25e840299773455ee096ddaf237/packages/core/src/goal/phase-orchestrator.ts#L185-L270)

- [S21] [packages/kanban/src/verification/completion-gate.ts](https://github.com/WrongStack/WrongStack/blob/ffbd572d593cf25e840299773455ee096ddaf237/packages/kanban/src/verification/completion-gate.ts)

- [S22] [packages/core/src/sandbox/types.ts](https://github.com/WrongStack/WrongStack/blob/ffbd572d593cf25e840299773455ee096ddaf237/packages/core/src/sandbox/types.ts#L1-L46)

- [S23] [packages/core/src/sandbox/backends/policy-only.ts](https://github.com/WrongStack/WrongStack/blob/ffbd572d593cf25e840299773455ee096ddaf237/packages/core/src/sandbox/backends/policy-only.ts#L1-L13)

- [S24] [packages/core/src/sandbox/backends/container.ts](https://github.com/WrongStack/WrongStack/blob/ffbd572d593cf25e840299773455ee096ddaf237/packages/core/src/sandbox/backends/container.ts#L14-L143)

- [S25] [packages/core/src/sandbox/backends/windows-native.ts](https://github.com/WrongStack/WrongStack/blob/ffbd572d593cf25e840299773455ee096ddaf237/packages/core/src/sandbox/backends/windows-native.ts#L96-L136)

- [S26] [packages/cli/src/slash-commands/autonomy.ts](https://github.com/WrongStack/WrongStack/blob/ffbd572d593cf25e840299773455ee096ddaf237/packages/cli/src/slash-commands/autonomy.ts#L34-L59)

- [S27] [packages/kanban/src/verification/evidence-validator.ts](https://github.com/WrongStack/WrongStack/blob/ffbd572d593cf25e840299773455ee096ddaf237/packages/kanban/src/verification/evidence-validator.ts#L54-L98)

- [S28] [packages/core/src/coordination/brain-quick-decision.ts](https://github.com/WrongStack/WrongStack/blob/ffbd572d593cf25e840299773455ee096ddaf237/packages/core/src/coordination/brain-quick-decision.ts#L1-L63)

- [S29] [packages/core/src/coordination/agents/project-agent-learning-policy.ts](https://github.com/WrongStack/WrongStack/blob/ffbd572d593cf25e840299773455ee096ddaf237/packages/core/src/coordination/agents/project-agent-learning-policy.ts)

- [S30] [packages/core/src/goal/phase-orchestrator-runtime.ts](https://github.com/WrongStack/WrongStack/blob/ffbd572d593cf25e840299773455ee096ddaf237/packages/core/src/goal/phase-orchestrator-runtime.ts#L1-L17)
