# ADR-0003 — MVP'de tek yürütücü ve seçilmiş kaynaklar

15 Ekim 2026. Durum: **MVP uygulama yönü; ürün kabulü değil**.
Bu karar ilk OpenClaw–Hermes hibrit hedefini sürdürür. Pi/OpenCode incelemesinin
kapsama alınması dört motoru birden çalıştırma veya sessizce motor değiştirme
kararı değildi. Yeni kaynağın kapsamı sınırlıdır; bu belgede performans üstünlüğü
veya öğrenme kabiliyeti karşılaştırması iddia edilmez.

## Seçim

| Sorumluluk | İlk M1 yolu | Sınır |
|---|---|---|
| Olay girişi, iptal/deadline kontrolü | OpenClaw'dan doğrulanmış küçük bileşenler + mevcut adaptör | Tam OpenClaw Gateway henüz kabul edilmedi. |
| Model/araç yürütme ve oturumun gerçek sahibi | Hermes | Gerçek AIAgent/read_file kanıtı var; gerçek HTTP Gateway zinciri sırada. |
| Kesinti ve atomik kabul karşılaştırması | Pi Durable + Alaz strict-admission ayrı aday | Hermes'e ikinci store/scheduler olarak eklenmez. Pi içinde çalışan katman Hermes atomikliği diye sunulmaz. |
| İzin ve olay sınırları | OpenCode incelemesindeki davranışlar HYB-005 şartlarına aktarılır | Bütün Effect/SessionStore/Plugin grafiğini sadece eşleştirici için taşımıyoruz. |
| Otonom gündem | Alaz M2 | M1 kabulünden önce başlatılmayacak. |

Hermes'i ilk M1 yolu olarak korumak onun daha ucuz veya daha hızlı olduğunu
kanıtladığımız anlamına gelmez. Aynı ürün katmanında eşit koşullu benchmark
henüz yok. Gerekçe, kullanıcının mevcut hibrit kararı ve kurulan entegrasyon
üzerinden tek uçtan uca işi bitirerek kapsamı daraltmaktır. Pi bulguları ve kodu
silinmez; başka bir yürütücüye geçiş ayrıca somut entegrasyon/maliyet kararı olur.

## Neden dört motor değil?

Her kaynağın kendi oturum, görev ve izin grafiğini birleştirmek aynı durumun
birden çok yazarı ve görünmeyen model çağrıları riski doğurur. Normal yönlendirme
LLM gerektirmez. Bir iş, tek yürütücü tarafından sahiplenilir. RequestId, runId,
sessionId ve agentId ayrıdır. Alt süreç veya ikinci bir kontrol bağlantısı,
ikinci bir kalıcı oturum sahibi demek değildir.

Pi strict-admission, Pi'nin tek native transaction'ında fingerprint ve admission
bağlar. Bunu Hermes'e yan kayıt olarak eklemek aynı atomikliği sağlamaz. Hermes'in
kendi kabul/anahtar/kayıt sözleşmesi gerçek Gateway üzerinden ayrıca ölçülür;
uyuşmazlık varsa ince bir uyarlama ve kabul deneyiyle çözülür.

## OpenCode'dan çıkardığımız uygulanacak şartlar

- Araç kaynakları güvenilir yürütme katmanında oluşturulur; boş liste, metinsel
  wildcard veya modelin verdiği kapsam doğrudan dosya izni sayılmaz.
- Agent/session tercihi ile değiştirilemez host yasağı ayrı tutulur. Son eşleşen
  kuralın bütün üst düzey güven sınırlarını koruduğu varsayılmaz.
- MVP'de projedeki tüm oturumlara yayılan otomatik kalıcı onay varsayılan olmaz.
  İzin kimliği, ilgili session ve işlemin kapsamıyla eşleştirilir.
- Onay girdileri beklemeye alınmadan önce immutable snapshot'a çevrilir; dışarıya
  verilen pending görüntüsü asıl nesneye referans taşımamalıdır. ID aynı session'da
  bile başka bir onay nesline tekrar verilmemelidir.
- Bekleme sırasında kural değişirse, gerçek araç yürütme anındaki değiştirilemez
  host yasağı tekrar kontrol edilir. Kullanıcı once onayı genel bypass olmaz.
- Canlı olay akışı bilgi bildirir, tek gerçek durum kaynağı değildir. Taşma veya
  kopmada görünümü güncel yetkili durumdan uzlaştırmadan tamamlandı denmez.
- Yeniden bağlanınca kayıp işler otomatik yeniden başlatılmaz. Mevcut işin
  kimliğiyle sorgulama yapılır; belirsiz dış etki aynen belirsiz kalır.

Bu şartlar bu turda üretim izin servisine uygulanmadı; REF-OC-001 karakterizasyonu
bize neyi ayrıca tasarlayıp test etmemiz gerektiğini gösteriyor.

## Kesin sonraki kabul: HYB-003-GATEWAY

Gerçek Hermes Gateway / SessionAuthority / APIServerAdapter kaynağını mevcut
pin üzerinde oku. Aynı kontrollü modelle HermesRunsClient -> native kabul ->
gerçek araç -> durum/sonuç zincirini tek işte sınayacağız. Aynı requestId tekrarını,
değişmiş içeriği, kayıp kabul yanıtını, iptali ve yeniden bağlanmayı ekleyeceğiz.
İşin tamamlanma kanıtı yalnız transport çıktısı değil native kaydı/araç sonucu
olmalı. Yeni HTTP taklidi yazarak gerçek Gateway kabulü kapatılmayacak.

Mevcut deneysel dallar main'e otomatik taşınmaz. Kaynak pinleri, katkı lisansları,
kanıt kapsamları ve status.md devam zinciri korunur. Gerçek model bütçesi, OS
izolasyonu, hafıza/beceri transferi ve M1 kabulü ayrı kapılardır.

## Kanıtlar

Hermes: evidence/hyb-003/native-file-read.json ve native-budget-summary.json.
Pi: evidence/ref-pi-001, ref-pi-002, ref-pi-002-sqlite, ref-pi-002b.
OpenCode: evidence/ref-oc-001/component-suite.json ve
 docs/research/REF-OC-001-COMPONENTS.md. Native deney sayıları ve offline test
sayıları topluca “ürün testleri” diye birleştirilmez.
