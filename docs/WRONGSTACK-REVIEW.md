# WrongStack incelemesi — AlazHarness için seçici uyarlama

İş: WRONGSTACK-REVIEW-AAC6. Tarih: 18 Ekim 2026.
Kaynak: WrongStack/WrongStack, `ffbd572d593cf25e840299773455ee096ddaf237`.
Kök paket sürümü: **1.1.8**. Lisans: **MIT**.
Alaz araştırma dalı: `alaz/review-wrongstack-aac6`.
Alaz tabanı: `b3197e2f2266bfd998920f7b2c1400c39bbc6195`.

## Karar

**WrongStack değerli bir açık kaynak bileşen kaynağıdır; mevcut OpenClaw–Hermes temelini değiştirmek veya üçüncü ana yürütücüyü eklemek için henüz gerekçe değildir.** Sonuç-duyarlı döngü tespiti, mission/plan ayrımı, kesintide görev sahipliği, SAGE koşullu hafıza, tek kullanımlık doğrulama izni ve tek-sahipli mailbox seçilerek uyarlanabilir.

Bütün ürünün güvenli, öğrenebilen veya üretime hazır olduğu kabul edilmedi. Eternal modunun tamamlanma kısayolu, otomatik YOLO, varsayılan kapalı governance bağlantısı ve policy-only sandbox ayrı değerlendirilmelidir. Bu inceleme kullanıcı isteğiyle sıradaki ortak D3B işinden önce yapıldı; D3B kabulünü gereksiz hâle getirmiyor.

## Kanıt sınırı ve lisans

README, mimari belgeler, seçilmiş kaynaklar, çağrı yerleri, paket bağımlılıkları ve hedefli test kaynakları okundu. Bütün depo satır satır denetlenmedi. Yerel envanter 11.909 izlenen dosya, packages altında 36 dizin ve ad desenine uyan 4.503 test dosyası saydı. **Bunlar test vaka veya PASS sayısı değildir.** Upstream mimari raporu, farklı packages+apps kapsamıyla 38 workspace ve 4.470 test dosyası bildiriyor; kapsamları birleştirmiyoruz.

Upstream install/build/test/benchmark, CLI/TUI/WebUI, eternal/parallel veya gerçek model çalıştırılmadı. Alaz ürün kodu, testleri, runtime ayarları, ana dalı ve diğer çalışma ağaçları değiştirilmedi. Önceki Alaz 1.903 test sonucu WrongStack kabulü olarak sayılmadı.

LICENSE: Copyright (c) 2026 ECOSTACK TECHNOLOGY OÜ, MIT. Kaynak alınır veya uyarlanırsa telif/izin bildirimi korunmalı; köken commit ve değişiklikler kaydedilmelidir. MIT, harici bağımlılıkların tümünü aynı lisanslı yapmaz ve güvenlik garantisi değildir. Bu turda yalnız özgün analiz metni yazıldı; upstream uygulama dosyaları Alaz ürün ağacına alınmadı. [S01]

## Büyük bir ajan ürünü, küçük bir drop-in modül değil

Node >=22.19.0 ve Bun >=1.4.3 tanımlayan TypeScript monoreposu; ajan çekirdeği, sağlayıcılar, araçlar, terminal/web yüzeyleri, görev/evre düzeni, worktree, SAGE, mailbox, Kanban ve governance paketleri var. SAGE; core, persistence ve primitives paketlerine bağlı. Mailbox-MCP core ve MCP'ye; governance persistence'e bağlı. Domain tipleri küçük olabilir, tüm servis yaşam döngüsü ve veri sahipliği küçük değildir. [S02,S03]

Alaz'ın mevcut Gateway/broker/kimlik bilgisi/bütçe ve Dream kanıtlarını bu geniş platformda yeniden bağlamak ciddi entegrasyon işidir. Bu, kaynak bağımlılıklarına dayalı mühendislik değerlendirmesidir; canlı WrongStack performansının kötü olduğu iddiası değildir.

## 1. Otonomi: işe yarayan döngü, alınmayacak başarı kısayolu

`/autonomy` off/suggest/auto/eternal/parallel modları sunuyor. Önceden tanımlı hedef aktifken eternal döngü sıradaki todo, çalışma ağacı veya yeni görev önerisinden iş seçebilir. Ardışık arızalar ve tekrarlanan işler için bekleme/yeniden planlama yolları var. İlk hedef ve izinlerden sonra yeni insan mesajı beklemeyen **operasyonel devamlılık** tasarımıdır; bilinç, kendi isteği veya nedensiz amaç edinme kanıtı değildir. [S04,S05]

Eternal/parallel açılışında CLI `onYolo(true)` çağırır. Dokümandaki açık deny kuralları yine geçerlidir; buna rağmen otonomi modu ile onayların gevşetilmesi bağlıdır. Bizde otomatik devam etme yetkisi, yeni dosya/ağ/harcama yetkisi üretmemeli. [S04]

`eternal-autonomy.ts` içindeki `[GOAL_COMPLETE]` yolu, ek bağımsız doğrulama olmadan hedefi temizleyip döngüyü durdurur. Kaynak yorumu bunun maliyet tasarrufu için kasıtlı olduğunu açıklıyor. `clearGoalManually` kalıcı hedef durumunu değiştirme/silme yoludur; doğrulanmış başarı makbuzu değildir. Diğer teslimat/Brain yollarıyla bu kısayolu karıştırmıyoruz. [S05,S06]

Ayrı `/goal start` evre yürütücüsü daha güçlü: CLI/WebUI'da varsayılan doğrulama, bağımlılık sırası, worktree ve bütünleşmiş sonuç kontrolü bulunuyor. Dolayısıyla bütün WrongStack doğrulamasız çalışır sonucu da yanlış. Alaz uyarlamasında modelin başarı bildirimi yalnız **proposed_complete**, bağımsız kabul ise **verified_complete** olmalı. [S07,S08]

## 2. Hızlı kazanım: sonuç-duyarlı döngü tespiti

`agent-loop-detector.ts` tamamlanmış etkileşimi araç adı, normalize argümanlar, hata durumu ve sonuç içeriğiyle karşılaştırıyor. Büyük çıktı dosyaya aktarıldığında tam temizlenmiş çıktının host özeti kullanılıyor: farklı geçici dosya adı ilerleme sayılmıyor; aynı baş/son görünümün arasında değişen içerik kaybolmuyor. Batch ve periyodik tekrarlar da hesaba katılıyor. [S09,S10]

Bizde aynı status çağrısının sonucu değişiyorsa sırf komut aynı diye kesmemek; aynı hatayla biten pahalı denemeyi sonsuza kadar yinelememek önemli. Bu sınırlı algoritma için yeni model gerekmez. Yine de değişen zaman damgası gerçek ilerleme değildir; iş bütçesi ve kapsamı ayrı kalır.

Dedektör, eşik oluşturan çağrı yürütülüp kaydedildikten sonra devreye girer. Yan etkiyi veya harcamayı önceden durduran güvenlik kapısı değildir. Alaz izin/bütçe rezervasyonu önde kalmalı; küçük argüman fingerprint fonksiyonu güvenlik amaçlı kriptografik kanıt bağı gibi kullanılmamalı. [S09,S10]

Aynı feedback tasarımında başarılı dosya değişikliğinden sonra LSP tanıları sürüm, SHA-256 ve sunucu kimliğine bağlanır. Sessiz/geç/başarısız sunucu temiz dosya değil **unverified** sonucu verir; tam test/typecheck yerine geçmez. Daha sonraki kod üretim döngüsü için iyi bir kısa geri bildirimdir. [S09]

## 3. SAGE ve Memory Companion: Dream için güçlü eşleşme

SAGE salt konuşma arşivi değildir: kaynak anchor'ı, revizyon, kayıt türü, uygulanabilirlik, görünürlük ve yaşam döngüsü taşır. Ayrı vector-memory katmanı yapılandırılmış store ve vektör sonuçlarını birleştirebilir; her SAGE çağrısının otomatik vektör araması olduğu varsayılmaz. [S11,S12]

`appendModelFeedback` mevcut revizyona ait olmayan geri bildirimi reddeder, tekrarı tekilleştirir, geçmişi sekiz yorumla sınırlar. useful/outdated/incorrect/irrelevant/uncertain yorumu eklenince içerik, güven, tazelik veya yaşam döngüsü kendiliğinden değişmez. İşe yaramadı diye otomatik silme; işe yaradı diye olgusal itirazı otomatik kapatma yok. [S13]

Bu, bizim alıntının bulunması ile dersin doğru ve yeni görevde yararlı olması ayrımımıza uyar. Yetkili SAGE güncelleme araçları yazabilir; salt-okunur Companion'ın yazamaması bütün SAGE'nin yazılamaz olduğu anlamına gelmez.

### Koşullu hafıza

Bir kayıt hangi sürüm/bağlamda geçerli olduğunu taşır. Sınırlı literal `source_contains` kontrolleri komut veya regex çalıştırmadan kaynak gözlemi üretir: satisfied/not_satisfied/unknown. Dosya yoksa veya okunamıyorsa otomatik doğru ya da yanlış denmez. Literal eşleşme, yorumun ve tüm varsayımların doğruluğunu ispatlamaz. [S11]

Alaz'a öneri: Dream adayına kaynak sürümü, ortam/rol, geçerlilik şartı ve gözlem özeti bağlamak; önce göreve uygulanabilirliğini kontrol etmek, sonra D2 ölçümünü kullanmak. Aynı cümlenin farklı koşulları otomatik çelişki veya mükerrer sayılmamalı. Bunu yeni bir SAGE veritabanı sahibi açmadan mevcut sözleşmeye uyarlamak daha uygundur.

### Salt-okunur inceleme rolü

Host, proje role override'larından sonra Companion izinlerini tekrar daraltıyor: okuma araçları, 8 iterasyon, 12 araç çağrısı, 12.000 token, 0,15 dolar sınırı; otomatik session_note, yazma veya skill ekleme yok. Sonuçtaki alıntılar verilmiş kaynakla eşleşmeli; yayın öncesinde hafıza revizyonu ve kaynak hash tekrar kontrol edilmeli. Yorum yine danışma niteliğindedir. [S11,S14,S15]

Bu rolü hemen otomatik başlatmak zorunda değiliz. Yeni model maliyeti açmadan önce aynı tazelik/koşul kuralları deterministik kontrollerde kullanılabilir; gerçek sağlayıcı bütçesi hazır olduğunda dar Companion pilotu değerlendirilebilir.

## 4. Kesintilerde görev sahipliği ve hedef–plan ayrımı

Kalıcı mission ile evre/task yürütme grafiğinin ayrılması faydalı: uzun vadeli amaç, o amaca yönelik o anki denemeden farklı kayıttır. Goal'a özgü dal/checkout ve süreç tabanlı lease, aynı hedefin iki sahibini önlemek için tasarlanmış. Resume sırasında kaydedilmiş worktree kimliği bulunamıyorsa başka dizinde sessizce devam edilmez. [S07]

`GoalTaskExecutionOwnership` küçük ama kritik ilke taşır: **timeout isteği iptal eder; iş gerçekten sonlanmadan çalışma slotu bırakılmaz.** Aynı task önceki promise'in sonlanmasını bekler; phase drain açık işleri bekler. Bu sınıf kendi başına süreçler arası kalıcı sahiplik sağlamaz; lease/host katmanı ayrıca gerekir. [S16]

Evre görevleri tamamlanıp merge başarısız olduğunda kod ayrı failure/inceleme durumu tutuyor ve worktree'yi koruyor. Alaz'da da kod üretildi/test geçti/dala bütünleşti/yayımlandı ayrımlarını korumalıyız. [S17]

## 5. Governance: güçlü kontrat, henüz zorunlu uçtan uca kapı değil

TaskContract, AcceptanceCriteria, AutonomyEnvelope, verification run ve tek kullanımlık lease tasarımları alınmaya değer. Görev kapsamı, ölçüt, varsayım kaynağı, izinli işlem, bütçe ve geri alma sınıfı yapılandırılmış veridir; model önerisi tek başına yetki kaynağı değildir. [S18,S19,S20]

Enforced `VerificationToolGateway`, taze workspace kimliğini alıp verifier/run/task/plan fingerprint/workspace hash'e bağlı lease'i yürütmeden hemen önce tüketir. İstek rastgele shell komutu veya araç payload'ı taşımaz; kayıtlı kontrol çağrılır. Lease tüketildikten sonra runner hatası legacy fallback'e dönüşmez. Belirsiz yan etkiyi yok saymama ilkesine uygundur. [S21,S22]

Fakat sınıfın varsayılanı legacy'dir. Governance README ve CLI bağlantısı `WRONGSTACK_GOVERNANCE=1` ile deneysel, varsayılan-kapalı bir entegrasyon olduğunu; mevcut normal araç yürütmesini henüz zorunlu olarak değiştirmediğini belirtir. İncelenen runtime yollarında VerificationToolGateway'i tüm araçların zorunlu kapısı olarak doğrulamadık. Paketin ve testlerin varlığı bütün uygulamanın bu sınırdan geçtiği kanıtı değildir. [S18,S21]

Alaz'a ikinci bir governance DB sahibi açmak yerine, kontrat/kanıt/tek-kullanımlık verifier iznini mevcut güvenilir broker sınırına uyarlamak gerekir. Gateway'in yazabildiği bütçe veritabanını değiştirmesine karşı bağımsız otorite sorunu, tek başına yeni event journal eklemekle kapanmaz.

## 6. Mailbox: sohbetten çok kalıcı sonuç teslimi

Mesajı okuma ile görevi tamamlama ayrı. Proje başına tek SQLite sahibi, yerel IPC, istemci heartbeat/lease, hedef ajan ve saklanan sonuçlar var. `mailbox-project-server.ts` önce endpoint sahipliğini kazanır, sonra SqliteMailbox açar; yarışmayı kaybeden süreç DB sahibi olmaz. [S23,S24]

Alaz için alınacak sözleşme: taskId/attemptId/actorId/lease/resultRef/seen/settled ayrımı. Geç yanıt hâlâ gelebiliyorsa eski çağrıyı körlemesine tekrarlamak yerine kalıcı sonuca bakmak. Bu mimari bize çok-ajan gerçekten gerektiğinde fayda sağlar; yalnız mailbox eklemek işin doğruluğunu veya exactly-once fiziksel yürütmeyi garanti etmez.

Kimlik bilgisi varsayımları karıştırılmamalı: mailbox kaynak yorumunda metadata dosyasının token taşıdığı görülür; governance'ın secret taşımayan metadata tasarımını bütün mailbox'a genelleyemeyiz. OS düzeyinde okuma/IPC sınırı D3B ile ayrıca sınanmalıdır.

## 7. Alınmayacak güvenlik ve başarı kısayolları

Sandbox modu dokümanda varsayılan off. `policy-only` backend `enforceExec()` içinde daima allow döndürüyor; gerçek containment gelmeden merkezi çağrı yolunu kurmak için kullanılan bir iskelet. Container ve Windows-native yolları ayrı; bu incelemede çalıştırılmadılar. Sandbox seçeneği bulunmasını kernel izolasyonu kabulü saymayız. [S25,S26]

Bu, WrongStack'te izin mekanizması olmadığı demek değil. Permission kuralları, tool gate, bütçe, MCP engelleme/güven ayarları ve gerçek backend seçenekleri var; hangi modun ve backend'in kullanıldığı önemli. [S25,S27]

Subagent bütçeleri iterasyon, tool, token, maliyet, idle ve duvar saati gibi boyutları izliyor. Olumlu; fakat bunları Alaz fiziksel rezervasyon/sağlayıcı yanıtı/kayıp ACK ispatı yerine koymayız. İncelenen limit kodundan bütün sistem için bağımsız harcama garantisi çıkarılmadı. [S28]

## 8. Uyarlama matrisi — henüz uygulanmadı

| Parça | Alaz'a katkı | Göreli bağlama maliyeti | Karar |
|---|---|---|---|
| Sonuç-duyarlı anti-loop | Gereksiz tekrarı kesmek, değişen gözlemi korumak | Düşük/orta | İlk küçük işlevsel pilot |
| TaskContract + VerificationLease | Başarı önerisi, izin ve bağımsız kabulü ayırmak | Orta | Ortak D3B/broker sınırıyla tasarla |
| Mission/plan + settlement ownership | Yeni insan mesajı beklemeden devam; mükerrer işten kaçınma | Orta | Otonomi katmanının sözleşmesi |
| SAGE koşulları + danışma geri bildirimi | Eski/uygunsuz hafızanın yanlış derse dönüşmesini önleme | Orta | Mevcut Dream verisine dar uyarlama |
| Mailbox kalıcı teslim/lease | Çok ajanda görev ve sonuç sahipliği | Orta/yüksek | Çok-ajan ihtiyacında |
| Bütün CLI/core/SAGE/runtime ve UI | Yeni tam platform | Yüksek | Bu MVP için önerilmiyor |

Maliyetler mimari değerlendirmedir, ölçülmüş gün/saat veya benchmark değil. Bir TypeScript parçasını Python'a taşımak kaynak/lisans bildirimini gereksiz yapmaz. Her port için pin, değişiklik listesi ve korunan sınırlar kaydedilmelidir.

## 9. Önerilen Alaz otonomi sözleşmesi

Bu bölüm tasarım önerisidir, çalışan özellik değildir:

`Goal -> TaskProposal -> AcceptedContract -> Plan -> ExecutionLease -> Attempt -> Evidence -> Verification -> SettledOutcome`

Amaç kalıcıdır. Model aday işi önerir; contract kapsamı/ölçütü/harcama sınırını host politikasına bağlar. Lease aynı plan+workspace+attempt için tek kullanımlık izindir. Evidence kaynak veya sağlayıcı makbuzudur, başarının kendisi değildir. Verification bağımsız ölçer. Yalnız sonuçlanan iş sonraki görevi ve Dream değerlendirmesini etkiler. Timeout hedef dosyasını silmez veya yeni harcama hakkı yaratmaz.

Ajanın kendine faydalı olması şöyle somutlaşır: konu seçer, yöntem/araç üretir, onu görmediği yeni görevde sınar ve faydalı sürümü yeniden kullanılabilir eser olarak korur. Bunun için bilinç veya model ağırlığının değişmesi varsayımı gerekmez. Kabul, eternal açık olduğu için değil, yeni görevde ölçülen faydadan gelir.

İlk pilotun önerilen negatif testleri: değişen sonuç kesilmez; yalnız spool yolu değişen aynı sonuç ilerleme sayılmaz; eski kaynak/revizyonla olumlu hafıza yorumu yayınlanmaz; timeout sahipliği serbest bırakmaz; sahte GOAL_COMPLETE yalnız öneri sayılır; lease aynı iş için iki fiziksel çağrı açamaz; otonomi modu yetkiyi kendi başına artırmaz. **Bunlar bu turda çalıştırılmış testler değildir.**

Ortak ağ/dosya D3B kabulü ve bağımsız broker bütçe otoritesi önceliği korunur. İlk küçük ek davranış anti-loop; ardından hedef/plan devamlılığı ve koşullu Dream hafızası. Yeni bir tam platform kurmak yerine mevcut temelin eksik sözleşmelerini tamamlarız.

## Kaynak dizini

Bütün yollar aynı pin'e aittir:
https://github.com/WrongStack/WrongStack/tree/ffbd572d593cf25e840299773455ee096ddaf237

S01 LICENSE.
S02 package.json; packages/{governance,sage,mailbox-mcp,persistence,primitives}/package.json.
S03 docs/architecture.md (seçilmiş bölümler).
S04 docs/slash/autonomy.md; packages/cli/src/slash-commands/autonomy.ts (eternal/parallel çağrı yolu).
S05 packages/core/src/execution/eternal-autonomy.ts (özellikle 325–403; seçilmiş döngü/seçim bölümleri).
S06 packages/core/src/execution/eternal-completion.ts.
S07 docs/slash/goal.md.
S08 packages/core/src/goal/phase-orchestrator-gates.ts.
S09 docs/agent-feedback.md.
S10 packages/core/src/core/agent-loop-detector.ts; packages/core/src/utils/tool-result-fingerprint.ts.
S11 docs/sage-feedback-lifecycle.md.
S12 docs/sage/retrieval.md; packages/sage/src/memory-model.ts (model alanları).
S13 packages/sage/src/shared/model-feedback.ts; packages/sage/src/sqlite-store-update.ts (ilgili yollar).
S14 packages/cli/src/fleet/memory-companion-policy.ts.
S15 packages/cli/src/fleet/memory-companion-evidence.ts.
S16 packages/core/src/goal/task-execution-ownership.ts.
S17 packages/core/src/goal/phase-orchestrator-integration.ts (seçilmiş yollar).
S18 packages/governance/README.md; packages/runtime/src/governance-bootstrap.ts; packages/cli/src/cli-main-helpers.ts (ilgili çağrı/flag bölümleri).
S19 packages/governance/src/task-contract.ts (kontrat alanları).
S20 packages/governance/src/autonomy-envelope.ts.
S21 packages/governance/src/verification-tool-gateway.ts.
S22 packages/governance/src/verification-execution-lease.ts.
S23 docs/mailbox-architecture.md (ilgili sahiplik/teslim bölümleri).
S24 packages/core/src/coordination/mailbox-project-server.ts (özellikle 490–535 ve seçilmiş auth/lease alanları).
S25 docs/slash/sandbox.md.
S26 packages/core/src/sandbox/backends/policy-only.ts.
S27 packages/core/src/sandbox/wrap.ts (wrapper/MCP bölümleri).
S28 packages/core/src/coordination/subagent-budget-limits.ts.

Hedefli test kaynaklarının başlıkları da incelendi: goal lease admission, task ownership, loop detection/delegation, mailbox IPC, SAGE feedback/validity ve governance verification lease/gateway. Bunların adları geçtiklerini kanıtlamaz. Upstream architecture-health-current raporu çalıştırılmadan okundu; bildirilen döngü/istisna sayıları canlı kabul yerine konmadı.
