# REF-PI-002 — Pi Durable kabul, süreç kesintisi ve yeniden yürütme

Tarih: 15 Ekim 2026. Kaynak: `earendil-works/pi`,
`b06c1f2cf1dea6af8748ddeee18c23587d2cb7c6` (Durable 1.2.0).
Temel AlazHarness commit: `a39a1ea08e108246463c983cc210975c9012364b`.
Dal: `alaz/ref-pi-002-durable-4c9f`.

**Davranış ölçümü: 9 senaryo × 2 tekrar = 18/18 PASS.**
**Bizim aynı anahtar/değişmiş içerik şartımız: FAIL. Ürüne benimseme: NOT ACCEPTED.**
Bu iki sonuç birbiriyle çelişmez: deney kaynak sistemin davranışını doğru ölçtü,
ama ölçülen davranışın bir bölümü bizim kabul şartımıza uymuyor.

## Gerçekten çalıştırılan sınır

Değişmemiş upstream `Harness.open`, gerçek görev zamanlayıcısı, submission/entry
kayıtları ve Node SQLite depolaması kullanıldı. Modelin yanıtlarını Pi'nin kendi
`fauxProvider` mekanizması üretti; sağlayıcı ağı, model çıkarımı ve ücretli çağrı yok.
Bu deney modelin kalitesini değil, Durable'ın kayıt ve yeniden yürütme davranışını
sınıyor. Önceki Pi HTTP/SSE sağlayıcı deneyi ayrı kanıttır.

Yan etki aracı bu deney için yazılmış küçük bir yerel test aracıdır; yerleşik read
aracı veya gerçek ticari servis değildir. Gerçek dosya etkisi yaratır. Araç her
girişini `attempts.jsonl`, gerçekleşen etkileri `effects.jsonl` içine fsync ile
yazar. Üst süreç bu kayıtları kendi okur; ajanın son metnine dayanmaz.

Dört crash senaryosunda ilk Node süreci, gözlenen kesin bir kayıt sınırında üst
süreç tarafından zorla kapatıldı. `Harness.close()` ile nazik kapanış taklit
edilmedi. Üst süreç çocuğu bekleyip topladı, SQLite'ı salt okunur açarak integrity,
entries/submissions ve görev checkpoint'lerini doğruladı, bağlantısını kapattı;
ancak sonra yeni Node sürecini aynı depoyla başlattı. İki Harness sahibi aynı
veritabanını eşzamanlı açmadı. PID, gerçek çıkış kodu, kill bariyeri ve zaman
sırası makbuzlarda ayrı tutuluyor. Windows'ta öldürülen çocuklar exit 1, yeniden
açılan çocuklar exit 0 verdi; bu planlı ilk exit bir test hatası değildir.

## Sonuç tablosu

| Senaryo | Gözlenen davranış | Sınır / karar |
|---|---|---|
| admission | Aynı anahtar aynı işi buluyor; farklı tür reddediliyor; başka conversation ayrılıyor; yeniden açmada kimlik korunuyor. Farklı write ve input içerikleri de eski işi döndürüyor. | Davranış ölçüldü; strict payload conflict şartı FAIL. |
| cancel-wait | Yalnız bekleyicinin context'i iptal edildi; iş placed kaldı ve daha sonra tamamlandı. | Beklemeyi bırakmak işi durdurmak değildir. |
| abort-work | Çalışan submission'ın withdraw sonucu already_placed; gerçek root.abort işi durdurdu, unanswered/aborted ve idle görüldü. | Conversation abort ile submission withdrawal ayrı. |
| storage-before | Gerçek SQLite commit'inden hemen önce kontrollü hata; ilk hata korundu, sonraki çağrı SessionFailed; yeniden açmada eski kayıt yok, retry sonrası bir kayıt var. | Fault injection; fiziksel disk arızası testi değil. |
| storage-after | Gerçek commit tamamlandıktan sonra onay yolu hata verdi; yeniden açmada kabul kaydı bulundu, aynı anahtarla retry ikinci kayıt yaratmadı. | Kaybolan onayın “iş hiç olmadı” sayılmaması doğrulandı. |
| crash-pending | Kabul ve provider kimliği kaydedilmişken, yanıt öncesi süreç öldürüldü; yeniden açmada aynı iş/kimlik tamamlandı. | Yeniden model isteği var; çıkarım ve para bütçesi testi değil. |
| crash-unsafe | Araç intent'i ve dosya etkisi var, tool result yokken öldürüldü; yeni süreç aracı tekrar çağırmadı, interrupted error üretti. | 1 execute/1 etki. Submission done olsa da kullanıcı işinin sonucu belirsiz; taskCompleted=false. |
| crash-safe | Aynı kesitte safe iş yeniden çalıştı; örnek araç kendi anahtarlı, exclusive-create idempotency işlemini kullandı. | 2 execute/1 etki. safe etiketi tek başına exactly-once sağlamaz. |
| crash-committed | Sonuç ve son durum yazıldıktan sonra ama kapanıştan önce süreç öldürüldü; yeni süreç hazır sonucu aldı. | Yeniden araç veya model isteği yok; 1 etki. |

İki tekrarda sekiz kontrollü process-kill/reopen çifti var; dokuz farklı senaryodur,
18 farklı senaryo değildir. İlk geliştirme denemeleri `runtime/` altında korunur;
final test sayısına eklenmez. Nihai makbuz `evidence/ref-pi-002/native-suite.json`.
Worker/runner/validator SHA256 değerleri aynı dosyada kayıtlıdır.

## Ana uyumsuzluk: aynı requestId, farklı içerik

Pi'nin testinde de bu davranış amaçlanıyor:
`packages/durable/test/harness-submissions.test.ts:82–107`. Uygulama
`packages/durable/src/harness/submissions.ts:179–185` üzerinde mevcut kimliği
buluyor, yalnız submission türü ayrımını yapıp eski kimliği döndürüyor.

Bu deneyde sadece “write” değil, gerçek model işi başlatan “input” da sınandı:
`input-first` ve `input-changed` aynı requestId ile aynı submission'a bağlandı;
kayıtlı ilk içerik korundu. Yeniden açmadan sonraki farklı içerik de yeni iş
oluşturmadı ve açık bir conflict cevabı vermedi. **Bu upstream tasarım tercihi,
AlazHarness'in daha katı sözleşmesiyle uyumsuz; otomatik olarak güvenlik açığı
veya upstream hatası diye adlandırılmıyor.**

Sonraki iş REF-PI-002B: aynı conversation/requestId için kalıcı içerik parmak izi
ve atomic admission sınırını seçmek. Aynı içerik eski sonucu vermeli; farklı içerik
uygulanmadan conflict dönmeli. Kontrol ve iş kabulü arasında crash/race boşluğu
bırakılamaz. Payload hash'ini requestId'ye ekleyip farklı içerikleri sessizce yeni
işe dönüştürmek çözüm sayılmaz. Yeni bir paralel transcript deposu veya Hermes'in
oturumuna ikinci yazar eklenmemeli. Mevcut public API yeterli değilse dar bir
uyarlama seçenekleri kaynak/test düzeyinde değerlendirilecek.

## Henüz kanıtlanmayanlar

SQLite WAL ve synchronous=NORMAL ile process crash sınandı; elektrik kesilmesi,
çekirdek/host çökmesi veya fiziksel disk kaybı değil. Kaynak README bir depoyu tek
sürecin sahiplenmesini istiyor; cross-process sahiplik kilidi bu deneyde eklenmedi.
İdempotent örnek aracın seçilmiş kesit dışındaki bütün arıza noktaları veya
haricî servislerin exactly-once davranışı kanıtlanmadı. Genel OS sandbox, tam
OpenClaw/Hermes Gateway, ağ kopması, kullanıcı verisi kurtarma, token/para bütçesi,
bellek transferi, gerçek model zekâsı ve M2 otonomi bu kabulün dışında.

## Tekrar üretim

Kaynak değiştirilmez ve dependency kurulmaz. Önceki hazır Pi ortamı kullanılır:

```powershell
cd C:\Antigravity\AlazHarness\scratch\worktrees\ref-pi-002-4c9f
python -B scripts/run_native_pi_durable.py --source-workspace C:\Antigravity\AlazHarness --prepared C:\Antigravity\AlazHarness\runtime\pi-ref001-ac97 --output C:\Antigravity\AlazHarness\runtime\pi-durable-yeni --repeats 2
```

Çıktı klasörü yeni olmalıdır. `--scenario` tek senaryo seçer; rapor kapsamı onu
belirtir. Her aşama süreyle sınırlı; crash'te yalnız oluşturulan çocuk öldürülür.
İstisnada da çocuk toplanır. Kişisel profile/anahtarlara, proxy ayarlarına ve Node
injection değişkenlerine başvurulmaz. Bu kontrollü ortam, hostile kod sandbox'ı değildir.

Standart CI yalnız bağımlılıksız kanıt/launcher kontrollerini çalıştırır:

```powershell
python -B -m unittest discover -s tests -v
python -B scripts/ci_check.py
```

Yeni negatif kontroller: sahte PASS, normal exit'in crash diye sunulması, eksik
process/toplama, eşzamanlı depo sahibi, bellekteki checkpoint ile disk kaydının
farkı, yinelenmiş etki, belirsiz sonucun başarıya çevrilmesi ve gizlenen payload
çakışması. Native 18 çalışma bu standart test sayısına dahil edilmez.

## Kaynak / delil

Kaynak yolları ve tam dosya hash'leri `evidence/ref-pi-002/source-custody.json`.
Hash, tam kod denetimi iddiası değil sürüm kimliğidir. Başlıca kaynaklar:
Durable README; `harness/{submissions,tool,provider}.ts`; `storage/sqlite/{node,storage}.ts`;
`test/{harness-submissions,harness-tools-recovery,harness-generation-recovery,harness-storage-failure}.test.ts`.
Upstream test dosyaları okunup tasarımla karşılaştırıldı; upstream Vitest paketi
bu turda çalıştırılmadı. Bizim gerçek native giriş deneyi ayrı çalıştırıldı.
