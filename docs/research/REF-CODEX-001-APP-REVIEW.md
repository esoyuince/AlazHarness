# REF-CODEX-001 — Codex uygulaması ve açık kaynak ajan motoru incelemesi

**Tarih:** 17 Ekim 2026 · **Sonuç:** STATİK İNCELEME TAMAMLANDI; AlazHarness ürün benimsemesi YAPILMADI.
**Araştırma dalı:** `alaz/ref-codex-001-c7a1`; başlangıç: `5b1f2dd12820434a257bb9709293195a36b6f18f` (Dream D1).
**Açık kaynak referans:** [`openai/codex`](https://github.com/openai/codex), sabit revizyon [`ce0323f2f2d3b25e82806cd555237da3db4e1897`](https://github.com/openai/codex/commit/ce0323f2f2d3b25e82806cd555237da3db4e1897); Apache-2.0.

## Kısa karar

Codex, OpenClaw/Hermes/Pi/OpenCode/Claude Code'dan sonraki **altıncı harici referans**.
AlazHarness ayrı yedinci projedir. Mevcut Hermes AIAgent'ı Codex ile değiştirmeyi
önermiyorum. Codex'ten ürünümüze en çok değer katacak fikir **iki aşamalı hafıza
uzlaştırma**, sonra **kabul edildi / tüketildi / çalıştırıldı ayrımı olan ajan
mesajlaşması**, ardından **sürümlü iş bildirimleri ve çalışma alanı sahipliği**.
İlk iki fikir için bile yeni bir çekirdek, ikinci scheduler ya da ürün GUI'si şart değil.
Bunların hiçbiri bu inceleme sonucunda uygulanmış sayılmaz.

## 1. Gerçekten ne incelendi?

Windows'taki kurulu resmî Codex sürümleri:

- Kararlı MSIX `OpenAI.Codex 26.1013.3656.0`, çalıştırılmadan statik incelendi.
- Ayrı ve daha eski `OpenAI.CodexBeta 26.727.4816.0` yalnız sürüm/kurulum karşılaştırması için listelendi.
- Bağımsız kurulu npm CLI paketi `@openai/codex 0.159.2` ve ayrı çalışır Codex yürütücüsü görüldü; yürütülmedi.

Özgün inceleme alanı (Git dışı):
`C:\Antigravity\AlazHarness\scratch\research-sources\20261017-codex-app-c7a1`.
Kararlı MSIX içinden **7 açıkça seçilmiş paket dosyası**, toplam
**1.062.328.381 bayt**, kaynak/kopya SHA-256 karşılaştırmasıyla ayrıldı.
Bunlar ASAR, Codex CLI/core yürütücüsü, code-mode host, Windows sandbox servisi,
command runner ve iki küçük kurulum/config metaverisidir. Beta tam kopyalanmadı.

ASAR **582.042.823 bayt / 21.070 girdi / 15.107 `.js` girdisi** içeriyor;
**0 kaynak haritası** gözlendi. Seçilmiş **40 JS/JSON** dosyası özel çalışma
alanında statik çıkarıldı ve hash'leri teyit edildi. Buradaki işlem
**paketlenmiş JavaScript'i okumadır**; özgün TypeScript, Rust/C++ veya bütün
native ikiliyi geri derlemek değildir. Uygulamanın kendisi, hesap/oturum,
kişisel konuşma, `.codex` profili veya açık işler okunup çalıştırılmadı.

Sadece dosya varlığı, statik kod, test şeması veya UI protokol dizesi; bir
özelliğin kullanıcının hesabında **etkin** olduğunu veya uçtan uca sağlandığını
kanıtlamaz. Dahası, sabitlediğimiz **public repo commit'i ile kurulu MSIX/CLI
binary'sinin bire bir kaynak revizyon eşleşmesi kanıtlanmadı**. Sonraki bulgular
bu iki kanıt türünü birbirine karıştırmaz.

Git'e özel paket, çıkarılan minify/proprietary kod, oturum, kimlik bilgisi,
yürütücü veya profil verisi girmez. Yayımlanan `evidence/ref-codex-001-c7a1/`
yalnız hash, sayım, kaynak yolu ve bizim gözlem/önerilerimizi içerir.

## 2. Mimari bulgular — kod kaynağı ve kapsam

### CX01 — App yüzeyi ayrı, model/araç yürütücüsü ayrı

Paketin `.vite/build/main`, `worker`, `webview/assets/app-initial` JS dosyalarında
`thread/start`, `thread/resume`, `thread/fork`, `turn/start`, `turn/steer`,
`thread/metadata/update` ve kuyruk işlemlerine ait protokol dizeleri görüldü.
Resmî [App Server belgeleri](https://learn.chatgpt.com/docs/app-server)
`initialize`/`initialized`, thread/turn, event stream ve interrupt ayrımını
açıklıyor. Uygulama UI'sı bu sözleşmelerin istemcisi olabilir; **ASAR içindeki
dize görülmesini gerçek ağ çağrısı veya aktif iş yeteneği sanmıyoruz**.

**Alaz karşılığı:** Var olan Gateway/HostGate/Hermes tek yürütücüsünü koru. İleride
herhangi bir UI'dan gelen komut için tek kimlikli turn event ve tamamlanma
makbuzu kullanan ince bir facade tasarlanabilir. Şimdi ikinci app-server/runtime
kurmak faydasız ve riskli.

### CX02 — Geçmişi saklamak, metaveri yazmak ve okumak ayrı

[`codex-rs/thread-store/README.md`](https://github.com/openai/codex/blob/ce0323f2f2d3b25e82806cd555237da3db4e1897/codex-rs/thread-store/README.md)
raw canonical history append ile metadata patch güncellemelerini ayırıyor.
`LiveThread` aynı canlı oturumun kalıcı sahibi; local store JSONL + SQLite
ve uyumluluk katmanları kullanıyor. [`live_writer.rs`](https://github.com/openai/codex/blob/ce0323f2f2d3b25e82806cd555237da3db4e1897/codex-rs/thread-store/src/local/live_writer.rs)
thread başına writer lock, archive/resume ve history-revision yeniden okumasını
yönetiyor. İki yazıcının aynı thread'i otomatik paylaşacağı iddia edilmiyor.

**Alaz karşılığı:** Bizde tek native state sahibi, admission/epoch/recovery ve
request-evidence DB var. Yeni thread-store eklemek yerine olay–metadata ayrımını
koruyup gelecekte `ownerRevision` eşitlik kontrolü ile kullanıcı yüzeyleri için
kayıp güncelleme senaryolarını sınamak gerekir. İçerik hash'i kullanım yetkisi değildir.

### CX03 — Okundu bilgisi sürümlü; gözlenme işi tamamlamak değil

[`codex-rs/app-server/README.md`](https://github.com/openai/codex/blob/ce0323f2f2d3b25e82806cd555237da3db4e1897/codex-rs/app-server/README.md)
`readState={firstUnread,revision}` ve `expectedRevision` ile çatışma
sözleşmesi açıklıyor. Okunmadı göstergesi yalnız uygun kalıcı terminal
çıktılarla ilerliyor; ekranın görüntülenmesi işi tamamlamıyor. Aynı revision
farklı thread/host arasında saat gibi karşılaştırılamıyor. Eksik DB sorgusu,
boş geçmiş (`nextCursor:null`) kabul edilmiyor.

**Alaz karşılığı:** Operatör inbox/uyarı UI'sı geliştirildiğinde ayrı
`needsAttention` + `revision` tutulabilir. Bu işin D1 öğrenme kalitesi veya
bugünkü M1 yürütmesi için ön şart değildir. Özel revizyonu görünür doğruluk
kanıtı olarak kullanmayacağız.

### CX04 — En önemli bulgu: Codex iki aşamalı hafıza

[`codex-rs/memories/README.md`](https://github.com/openai/codex/blob/ce0323f2f2d3b25e82806cd555237da3db4e1897/codex-rs/memories/README.md)
ve [`phase1.rs`](https://github.com/openai/codex/blob/ce0323f2f2d3b25e82806cd555237da3db4e1897/codex-rs/memories/write/src/phase1.rs)
uygun geçmiş rollout'lardan **Phase 1: tek oturum başına çıkarım** tanımlıyor.
Koşulları: memory özelliği açık, root session, ephemeral/subagent değil, DB
mevcut; yaş/boşta kalma penceresi, sınırlı startup claim, lease, eşzamanlılık
üst sınırı, `succeeded` / `succeeded_no_output` / backoff'lu failure ayrımı.
Çıktı `raw_memory`, kısa özet ve opsiyonel slug; kısmi kayıtları ve sırları
ayrıca ele alıyor. Bu, otomatik ağırlık eğitimi veya gerçek ders doğruluğu değildir.

[`phase2.rs`](https://github.com/openai/codex/blob/ce0323f2f2d3b25e82806cd555237da3db4e1897/codex-rs/memories/write/src/phase2.rs)
ve [`state/src/runtime/memories.rs`](https://github.com/openai/codex/blob/ce0323f2f2d3b25e82806cd555237da3db4e1897/codex-rs/state/src/runtime/memories.rs)
**Phase 2: global uzlaştırma** için tek lock alıyor. Önce uygun Phase1 notlarını
seçip ortak bellek workspace'ine yazıyor; eski başarılı Git baseline ile diff
hesaplıyor. **Anlamlı değişiklik yoksa ilave konsolidasyon ajanını çalıştırmadan
başarılı çıkabiliyor.** Değişiklik varsa sınırlandırılmış, network kapalı ayrı
consolidation agent yürütüyor; global lease heartbeat ve başarılı sonucun
ardından baseline reset/watermark güncelleniyor. Önceki aşamanın kullanım sıklığı
ve son kullanım zamanı seçimde etkili; eski/stale girdiler elenebiliyor.

**Alaz karşılığı:** Dream D1 zaten yalnız seçilmiş terminal kayıttan kanıtlı
**aday** üretiyor. Codex'in Phase2 otomatik `MEMORY.md`/skills güncelleme yolunu
şu anda açmamalıyız. Özgün çözümümüz: `CandidateReview → EvidenceDiff →
IndependentVerifier → PromotableMemoryProposal`. Diff, review edilmiş çalışma
alanında üretilebilir; fakat **modelin yazdığı not + kaynak alıntısı** beceri
sertifikası olamaz. Tutulmuş yeni görevde faydası ölçülmeden aktif hafızaya veya
beceriye otomatik alınmamalı. Kaynak silme de otomatik geçmiş silmek değildir.

### CX05 — Ajan iletişimi kabul/okuma/uyanma ayrımı

[`codex-rs/core/src/agent/api.rs`](https://github.com/openai/codex/blob/ce0323f2f2d3b25e82806cd555237da3db4e1897/codex-rs/core/src/agent/api.rs)
`AgentControl` sözleşmesinde child açma, bilinen child'ı geri yükleme, mail
kuyruğu ve `watch_mailbox` yollarını ayırıyor. Kaydedilen ifade:
**başarılı teslim, modelin mesajı okuduğu anlamına gelmez**. `queue-only`
mesaj bir turn başlatmaz; follow-up/wake ayrı. Toplam kullanım kaydı ve
ajan slot/guard'ları ayrı sorumluluk.
[`multi_agents_spec.rs`](https://github.com/openai/codex/blob/ce0323f2f2d3b25e82806cd555237da3db4e1897/codex-rs/core/src/tools/handlers/multi_agents_spec.rs)
spawn, send ve wait parametrelerini açık tanımlıyor. Statik kaynak bir uçtan
uca çok ajanlı kabul testi yerine geçmez.

**Alaz karşılığı:** Önce tek ajan+tek kanıtlı deney. M2'de yan ajan gerekli
olursa `MessageAccepted`, `MessageConsumed`, `TurnStarted`, `ResultVerified`
alanlarını ayıralım. Gelen başka ajan mesajı **yetki devri değil kaynaklı
iddia** olarak saklansın. Yeni ajan çağrısı mevcut bütçeyi sıfırlamasın.

### CX06 — İzin kararı ile sandbox tekrar denemesi aynı değil

[`tools/orchestrator.rs`](https://github.com/openai/codex/blob/ce0323f2f2d3b25e82806cd555237da3db4e1897/codex-rs/core/src/tools/orchestrator.rs)
onay→sandbox seçim→araç→denial/retry akışını koordine ediyor; yeni, genişletilmiş
yetki isteyen retry için yeniden onay kuralı var.
[`tools/sandboxing.rs`](https://github.com/openai/codex/blob/ce0323f2f2d3b25e82806cd555237da3db4e1897/codex-rs/core/src/tools/sandboxing.rs)
profillere göre sınırları ayrı denetliyor. Uygulama paketinde Windows sandbox
servisi ayrı ikili olarak bulunuyor; dosya varlığı tüm Gateway'nin OS izolasyonu
kanıtı değil.

**Alaz karşılığı:** Mevcut tek kullanımlık tool izinleri ve Docker no-network
sınırı korunmalı. D3B OS kimliği/egress ayrımını gerçek Linux/Windows koşularla
kapatmadan genel shell/network yetkisi vermemeliyiz. Araç ret sonrası
`unsandboxed` sessiz fallback ve bilinmeyen istek tekrar gönderimi YOK.

### CX07 — Paralel iş için worktree ve zamanlanmış iş izolasyonu

Resmî [Git worktrees](https://learn.chatgpt.com/docs/environments/git-worktrees)
ve [Scheduled tasks](https://learn.chatgpt.com/docs/automations?surface=app)
belgeleri paralel thread'leri ayrılmış checkout'larda ve planlı işleri proje
worktree'lerinde çalıştırmayı açıklıyor. Kurulu UI paketinde `worktree`,
`automation` ve `thread/queue/*` dizeleri bulunuyor. Bunlar otomatik hedef
seçimi veya mevcut kullanıcı sürümünde etkinlik kanıtı değildir.

**Alaz karşılığı:** Zaten feature worktree, tek writer, exact-source CI ve
bağımsız QA yapıyoruz. Bu fikirlerin işe yarar kısmı alındı; ilk MVP için
Codex'in bütün desktop UX'ini kopyalamak gereksiz. Handoff/merge yalnız kaynak
SHA/diff/testler uzlaştırıldıktan sonra açıkça yapılmalı.

### CX08 — App-server transport kesinliği sınırlıdır

Yayınlanan app-server belgeleri `thread/start`, `turn/start`, `turn/steer`,
`turn/completed` olaylarını ayrı tutuyor. Statik masaüstü JS'de
`AppServerRequestDeliveryError` türü ve bazı turn/metadata yolları var.
**Bu, kaybolmuş ACK durumunda fiziksel eylemin tamamlanmadığını kanıtlamaz**.
Bizdeki R1B2 `prepared → handoff_armed → broker_response_observed` ayrımı aynı
soruna temkinli yaklaşır. Hata sonrası kör tekrar veya bütçe iadesi yapılmamalı.

## 3. AlazHarness mevcut durumuyla karşılaştırma

| Alan | Mevcut Alaz | Codex'ten alacağımız özgün yaklaşım | Öncelik |
|---|---|---|---|
| Tek çalışma sahibi, event/ledger | HYB004/HYB005 çalışıyor | Thread revision ve notification ayrımını ileride UI için kullan | P2 |
| Gerçek native izole okuma | HYB005D2 + kaynak yakalama | Genel araç yüzeyini hemen açma; D3B kanıtından sonra değerlendirme | P0 izolasyon |
| Kaynak → istekte kullanılan içerik | R1B1/R1B2 var | Aynı provenance'ı Dream review'a taşı | P0 |
| Dream D1 aday üretimi | Manuel, candidate-only; scriptli modelle kabul | İki aşamalı uzlaştırma + no-change fast path + usage/conflict sinyali | P1 |
| Becerinin gerçekten işe yaraması | HYB006/M1 transfer AÇIK | Held-out ikinci görevde başarımı ölç, sonra terfi | P0 ürün değeri |
| Çok ajanlı mesajlaşma | MVP hedefi tek ajan | Kabul/okuma/uyanma durumlarını ayır; mevcut ortak bütçeden paylaştır | P2 |
| Scheduled/worktree çalışma | Git worktree/CI kanıt süreci var | Ayrı cron/UI yerine mevcut tek sahiplik kuralını koru | P3 |

**En büyük fark:** Codex'in bellek üretimi ile Alaz'ın hayal edilen *öğrenme*
ölçümü birbirinden farklı. Bizim özgün katmanımız, yalnız hafıza notu sayısını
değil, yeni görevdeki doğrulanmış faydayı ölçmek olmalı.

## 4. Özgün entegrasyon teklifi: DREAM-D2-MIN, sonra HYB006

1. **D2-01 Baseline:** Sabit, küçük görev ailesi ve 12-20 saklı olumlu/olumsuz
   örnek üzerinde Dream D1 aday üretimi. Önce model/sağlayıcı/tarife/token
   gerçek kabul sınırı oluştur; model kalitesi testi sonuçlarını ayrı kaydet.
2. **D2-02 CandidateReview:** Aday kimliği, kaynak/quote ve çelişkili örnekleri
   birlikte sunan yalnız inceleme arayüzü. Operatör `accept/reject/defer` seçer;
   *kabul = gerçek dünya doğruluğu* olmaz, otomatik active-memory write yok.
3. **D2-03 Diff workspace:** Önceki review edilmiş aday seti ile yeni aday setinin
   eklenen/değişen/geri çekilen parçalarını Git diff benzeri deterministik
   mekanizmayla hesapla. **Diff boşsa model çağrısını atla** ve kullanım
   rezervasyonu yaratma. Tek review writer; kilit kaybında publish ret.
4. **D2-04 VerificationContract:** Ayrılmış yeni görev/örneklerde önceden
   kilitlenmiş test, kaynak+model sürümü ve bütçe kimliğiyle iyileşmeyi doğrula.
   Sadece bu kapıdan geçen yöntem `promotable`, bir sonraki aşamada kontrollü
   hafıza/beceri transferine aday olabilir. Yanlış aday korunur ama çekilmesi
   aktif geçmişi silmez.
5. **D2-05 Bounded wake (sonra):** Phase1 tetiklemeyi yalnız manuel başladıktan
   sonra, bir sonraki aşamada yetkili iş tamamlama event'ine bağla. Bir batch
   belirsizse kör yeniden başlatma yok. Otomatik hedef seçimi ancak M1/M2
   yetki, maliyet ve transfer kapıları kapandıktan sonra.

### Önerilen kabul testleri — **HEPSİ NOT RUN**

| Kimlik | Test | Beklenen |
|---|---|---|
| COD-01 | Aynı thread'e iki metadata yazıcısı | Eski revision reddi, içerik kaybı yok |
| COD-02 | İki Dream çıkarımı aynı işi talep ediyor | Tek claim, çift model çağrısı yok |
| COD-03 | Hiç yeni aday veya workspace değişikliği yok | Faz 2 için sıfır ek model çağrısı |
| COD-04 | Konsolidasyon lock/epoch kayboluyor | Başarı/aktif hafıza yazısı yok |
| COD-05 | Sahte kaynak alıntısı ve gerçek ama yanlış ders | İlkinde ret, ikincisinde yalnız unverified candidate |
| COD-06 | Aynı örnek birden fazla notta | Çoklu bağımsız kanıt sayılmıyor |
| COD-07 | Yeni görevde tutarlı başarısızlık | Beceri terfisi yok, sonuç geri çekilebilir |
| COD-08 | Yan ajan mesajı bekleme kuyruğunda | Accepted ≠ consumed ≠ started |
| COD-09 | Sandbox ret sonrası geniş yetkiyle retry | Yeni onay ve yeni bütçe, sessiz fallback yok |
| COD-10 | Eski UI readState revision | Ret/refresh, başka thread revision'ı karşılaştırılmaz |
| COD-11 | Provider kopması ve belirsiz iş etkisi | No auto replay/refund/goal-success |
| COD-12 | Eski hafıza dosyaları, sır ve kişisel kaynak | Koruma; aktivasyon/terfi yok; veri sızıntısı yok |

Bunlar *test planıdır*; statik araştırma PASS'ı, çalıştırılmamış davranış
senaryolarının kabulü değildir.

## 5. Lisans ve kanıt sınırları

`openai/codex` açık repo Apache-2.0. Herhangi bir dosyasını doğrudan alırsak
uygun lisans/NOTICE ve kaynak değişiklik bildirimi şartlarını ayrıca
incelemeliyiz. **MSIX içindeki paketlenmiş UI kodunun açık repo ile aynı lisansa
sahip olduğunu varsaymıyoruz**. MIT Alaz'a kapalı desktop blob/string/prompt
veya native executable aktarılmadı. Sadece mimari sorun/çözüm karşılaştırıldı;
özgün kod sözleşmeleri önerildi. Resmî belgeler ve pinned açık kod referansları
`evidence/ref-codex-001-c7a1/source-map.json` içindedir.

Bu tur Codex uygulamasını/CLI'yi çalıştırmadık, kullanıcının özel `.codex`
veya oturum verilerini incelemedik, Alaz ürün kodunu değiştirmedik, model/ücretli
çağrı yapmadık. Tam kaynak Rust build'i, binary/source kesin eşlemesi, cihaz
sandbox penetrasyon testi ve gerçek Codex oturum lifecycle deneyi **NOT RUN**.
Son commit/CI bilgisi çalışma `status.md` dosyasına ayrıca kaydedilir.
