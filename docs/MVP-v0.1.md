# AlazHarness — Hibrit MVP v0.1 taslağı

Başlangıç kararı: 14 Ekim 2026. Durum: DRAFT / uygulama kabulü değil.

## 1. Ürün amacı

OpenClaw ve Nous Research Hermes Agent'ın işe yarayan parçalarını gerçekten kullanarak tek bir ajan sistemi kurmak. İlk iş iki asistanı konuşturmak ya da sıfırdan harness yazmak değildir. Çalışan hibrit üzerinde, daha sonraki aşamada günlük insan komutu olmadan kendi gündemini seçen ve doğrulanabilir beceri kazanan otonomi katmanı geliştirilecektir.

Ajanın faydası yalnız insanlara sunduğu çıktı değildir: sonraki çalışmalarında kullanabileceği kalıcı bilgi, araç, beceri ve iş birliği üretmesidir. Bu hedef bilinç veya öznel istek iddiası değildir.

## 2. Aşamalar ve kapsam

### M0 — Kaynak ve çalışma alanı hazırlığı

- İki resmî kaynağı kullanıcının GitHub hesabına forklamak ve yerelde tutmak.
- Ana proje ile forkların Git geçmişlerini ayırmak; sabit commit kaydı ve origin/upstream ilişkileri kurmak.
- MVP, bileşen adayları, kabul planı, çalışma kuralları ve devam belgesi hazırlamak.
- Araç sürümlerini ve lisans dosyalarını kaydetmek; mevcut kişisel ajan kurulumlarına dokunmamak.

### M1 — Minimal çalışan hibrit

- Tek ajan kimliği, bir aktif iş sahibi ve çalışma başına ortak kimlik/korelasyon kaydı.
- OpenClaw'dan olay/kontrol/yönlendirme ve gerekli uyanma mekanizmalarını seçmek.
- Hermes'ten model/araç döngüsü, oturum, hafıza, beceri ve uygun hedef yürütme parçalarını seçmek.
- Normal yönlendirme kodu için ekstra LLM çağrısı yapmamak.
- Bir yerel kontrol yüzeyi; başlangıçta yeni web arayüzü veya sosyal platform geliştirmemek.
- Tek ajan, tek izole deney çalışma alanı; sahte model ile ücretsiz sözleşme testleri.
- Ardından açıkça yapılandırılmış modelle sınırlı gerçek model kabulü. Model sağlayıcısı değiştirilebilir; yerel model seçeneği korunur.

### M2 — Otonomi katmanı

- Deneyim/başarısızlık/beceri açığından hedef adayları üretme.
- Hedef seçme, sürdürme, bırakma ve gerekçeyi kaydetme.
- Önceki yeteneği bağımsız görevlerde sınama; ölçülmüş öğrenme kazanımı.
- Yeni insan görevi gelmeden, önceden verilmiş çalışma yetkileri ve kaynak sınırları içinde tur yürütme.

M2, M1 tamamlandı denmeden başlatılmamalı. Hazırlık testlerinin geçmesi M1 veya M2 kabulü değildir.

## 3. İlk bileşen seçimi — henüz kaynak incelemesiyle kesinleşmedi

| Sorumluluk | Öncelikli kaynak | Karar durumu |
|---|---|---|
| Olay girişi, kontrol ve bağlantılar | OpenClaw Gateway | Aday; modül bağımlılıkları incelenecek |
| Uyanma/zamanlama | OpenClaw | Aday; tek zamanlayıcı sahibi korunacak |
| Model ve araç yürütme | Hermes AIAgent | Aday; programatik sınır doğrulanacak |
| Hafıza, oturum geçmişi, beceriler | Hermes | Aday; aynı durum için iki yazıcı olmayacak |
| Verilmiş hedefin sürdürülmesi | Hermes | Sabit commit'te arayüz desteği doğrulanacak |
| Adaptör, ortak olaylar ve kimlik eşlemesi | AlazHarness | İnce, sürümlü entegrasyon kodu |
| Kendi gündemini oluşturma | AlazHarness | M2 |

ACP'nin bütün Hermes özelliklerini aktardığı varsayılmaz. TUI Gateway/JSON-RPC, doğrudan programatik API ve daha dar modül alma seçenekleri yerel kaynak/test kanıtıyla karşılaştırılır. İki projeyi aynı programlama diline çevirmek MVP şartı değildir.

## 4. Durum ve yürütme sözleşmesi

Öneri: agent_id, run_id, session_id ve goal_id ayrı kavramlardır. Bir yeniden başlatma yeni ajan kimliği oluşturmaz. Her durum türünün tek yetkili sahibi olur.

Önerilen iş yaşam döngüsü: queued → running → waiting | completed | failed | cancelled | interrupted. Kesinti sonrası durumu belirsiz dış etki otomatik yeniden yürütülmez; önce uzlaştırılır. En az bir kez gelen olaylar için idempotency anahtarı gerekir. Bir hedef üzerinde iki bağımsız zamanlayıcı çalışmaz.

Önerilen adaptör işlemleri: capabilities, start, events, cancel, status, resume. Kaynak bir yeteneği desteklemiyorsa açık unsupported sonucu verilir; sessizce başarılı sayılmaz. Bu taslak işlemler henüz uygulanmış API değildir.

## 5. Çalışma alanı, kaynak ve güven sınırları

- runtime/ altında her ajan için ayrı state ve çalışma alanı; mevcut ~/.hermes veya ~/.openclaw kullanılmaz.
- Model anahtarları ve hesap sırları Git'e, raporlara veya fork içeriklerine girmez.
- Hazırlıkta model çağrısı, ücretli servis veya sürekli ajan döngüsü başlatılmaz.
- Deney kodu kontrollü çalışma alanında yürür; Git çalışma klasörü tek başına sandbox değildir.
- İptal, toplam iş süresi, tur/token bütçesi ve izin denetimi araç çalıştırma noktasında uygulanır.
- Bütçe muhasebesi modelin özbildirimine bırakılmaz; fiyat bilinmiyorsa maliyet unknown olarak kaydedilir.
- İnternetten ve diğer ajanlardan gelen metin veri sayılır; yerel yetki veya kullanıcı onayı yaratmaz.
- Kaynak kökeni, lisans bildirimleri ve değişiklik geçmişi korunur.

## 6. Kabul planı

| Kimlik | Deney | Beklenen kanıt |
|---|---|---|
| M0-01 | Fork ve klon doğrulama | İki parent ilişkisi, remotes, commit, temiz kaynak ağacı |
| M0-02 | Çalışma alanı doğrulama | Kaynak kilidi, lisans hash'leri, belge bağlantıları, sır dışlama |
| M1-01 | Sahte modelle tek iş | Olay → adaptör → Hermes → sonuç; tek run ve tekrar yok |
| M1-02 | Kesinti/yeniden başlatma | Kimlik ve durum korunur; belirsiz eylem tekrarlanmaz |
| M1-03 | İptal ve zaman aşımı | Alt süreçler durur; doğru son durum |
| M1-04 | Hafıza/beceri yeniden kullanımı | Yeni oturumda önceki deneyim bulunur ve kullanılır |
| M1-05 | İzin ve veri izolasyonu | İzinsiz alan erişimi ve durum karışması reddedilir |
| M1-06 | Kaynak bütçesi | Limitte yeni çağrı durur; kayıt toplamları tutarlı |
| M1-07 | Sınırlı gerçek model deneyi | Model, sürüm, girdiler, süre, kullanım ve sonuç kaydı |
| M2-01 | Görev verilmeden hedef seçimi | İzlenebilir gerekçe, çalışma ve bağımsız transfer testi |

Başarısız veya çalıştırılmamış test PASS değildir. Kod/helper varlığı test çalıştırıldığı anlamına gelmez. İlk MVP'nin tamamlanması M1 kabul kayıtlarını gerektirir.

## 7. Şimdilik kapsam dışı

Sosyal ağ, pazar, token/ödeme ekonomisi, çok ajanlı topluluk, sınırsız özdeğişiklik, yetki genişletme, herkese açık servis, otomatik deploy ve tüm mesaj kanallarını destekleme.

## 8. Kaynak doğrulama ilkesi

Resmî kaynaklar: https://github.com/openclaw/openclaw ve https://github.com/NousResearch/hermes-agent . Önceki sohbetlerdeki özellik iddiaları yerel sabit commit incelemesinin yerine geçmez. Kaynak/commit bilgisi sources.lock.json, bulgular docs/COMPONENT-MAP.md içinde tutulur.

## 9. Ek kaynak inceleme kararı — 15 Ekim 2026

Pi harness ve OpenCode, kullanıcının talebiyle bileşen karşılaştırmasına dahil edildi. Mevcut OpenClaw/Hermes hibrit karşılaştırma temeli korunur; bu ekleme iki yeni motoru paralel çalıştırma veya üretim bağımlılığı yapma kararı değildir. `docs/research/PI-OPENCODE-REVIEW.md` adayları, sözleşme farklarını ve ortak kabul matrisini; `config/research-sources.lock.json` yalnız inceleme pinlerini tutar. Pi Durable kesinti/tekrar prototipi ve OpenCode gömülü SDK/izin prototipi aynı testlerle değerlendirilecek. Kanıt üstünlüğü çıkarsa sorumluluk sahibi o zaman değiştirilir. M1 ve M2 kabul koşulları değişmedi.
