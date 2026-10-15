# HYB-003-GATEWAY — Gerçek Gateway üzerinden tek iş

15 Ekim 2026. Uygulama dalı `alaz/hyb-003-gateway-5a5c`; taban
`45f7d0e9f1ebb7bd15dc846c0d0b7cf9276d758a`. Son kabul sayıları
`evidence/hyb-003-gateway/native-suite.json` ve `local-validation.json` içindedir.
Bu paket dar native Gateway kabulüdür; tam M1/M2 veya üretim güvenliği değildir.

## Çalışan gerçek zincir

Mevcut `HermesRunsClient` → gerçek HTTP `/v1/runs` → `APIServerAdapter` →
`SessionAuthority` admission/FIFO → gerçek `AIAgent` → yerleşik `read_file` →
kalıcı transcript ve native terminal kayıt → HTTP durum/sonuç.

Hermes public `gateway.run.start_gateway(idle_exit=True)` girişinden başlatılır.
Sahiplik rezervasyonu, runtime epoch, SessionAuthority, kontrol/API listener'ları,
API key doğrulaması ve native kapanış asıl kaynak tarafından yürütülür. Deney
ikinci bir Agent/otorite oluşturmaz. `_gateway_runner_ref` yalnız gözlem ve
aynı gerçek runner'ın public `stop()` çağrısı için okunur; çalışma döngüsü,
agent sınıfı, admission, store ve tool handler monkeypatch edilmez.

Yalnız model sağlayıcısının cevapları yerel deterministik HTTP sunucusundan gelir.
Model tool-call ister; tool sonucundaki rastgele işaret gelmeden son cevap vermez.
İşaret ilk kullanıcı mesajında yoktur. Türkçe metin içeren test dosyası yeni
runtime altındadır. Model çıkarımı ve ücretli sağlayıcı çağrısı sıfırdır.

## Üç senaryo, aynı temel sözleşme

**Normal:** gerçek dosya okunur. Aynı anahtar/içerik aynı run_id döndürür; farklı
içerik409, yanlış API key401. İki GET gözlemiyle yeniden bağlanmak yeni iş başlatmaz.
İşin kullanıcı mesajı ve araç sonucu native veritabanında birer tanedir.

**Kayıp kabul yanıtı:** sınırlı loopback rölesi gerçek isteği Gateway'e iletir,
Gateway'in202 cevabını tamamen aldıktan sonra cevabı istemciye vermeden TCP
bağlantısını kapatır. Röle run/admission oluşturamaz, sahte başarılı yanıt yazmaz.
İstemci `write_outcome_unknown` ve `mayHaveBeenAccepted` üretir. Deney daha sonra
aynı anahtarla AÇIKÇA tekrar gönderir; bu mevcut run_id'yi bulur. Adaptöre otomatik
POST retry eklenmez. Rölenin gördüğü run_id, HTTP sonucu ve native admission eşleşir.

**Model beklerken stop:** model isteğinin gerçekten geldiği nonce ile doğrulanır;
HTTP stop gönderilir, sonra kontrollü geç model cevabı serbest bırakılır. İstemci
stop-ack'i son durum saymaz, ayrıca terminal durumu sorgular. HTTP `cancelled`,
native admission `interrupted`; bir kullanıcı girdisi ve sıfır araç sonucu beklenir.
Bu test her tür araç veya sınırsız asılı provider için genel iptal garantisi değildir.

Her native koşu yeni profil, API anahtarı, portlar, nonce ve çalışma süreci kullanır.
Beklenen aktif araç seti `file` grubudur: schema'da write_file/patch/search_files da
vardır; kontrollü model yalnız read_file ister. Bu deney bir read-only OS sandbox
veya gerçek modelle güvenli dosya yetkilendirmesi iddiası değildir.

## Bağımsız kayıt ve kaynak doğrulaması

Gerçek Gateway kapanıp hem Windows başlatıcı hem asıl Python süreci bittikten
sonra üst süreç iki SQLite dosyasını salt okunur açar. session_admissions'daki
admission_id/run_id/session_id/epoch/generation ve terminal outcome, HTTP sonucu
ile eşleştirilir. runs_idempotency'de tek kayıt, transcript'te tek user girdisi ve
beklenen tool sayısı gerekir. Dosya işareti hem tool kaydında hem final yanıtta
aranır. Sadece HTTP200 veya modelin başarı ifadesiyle PASS verilmez.

Windows venv python.exe bir başlatıcı ve ayrı interpreter süreci oluşturur.
Sahiplik denetimi nonce'a ek olarak OS process-parent zincirini doğrular ve
interpreter için açık process handle tutar. Timeout'ta yalnız bu handle ve
çağrının kendi Popen çocuğu hedeflenir. PID'yi dosyadan okuyup rastgele süreç
sonlandırma yoktur. Bu bir genel supervisor ya da çok-yazıcılı fencing çözümü değildir.

Kaynak commit'i `eb75627faf532fa6ffbdae59a0d14b0b385fc780`; pinli dosyalar
`config/gateway-probe/source-lock.json` içinde. Fixture/runner/client hash'leri
her koşudan önce/sonra eşit olmalıdır. Native probe günlükleri, config ve
rastgele API anahtarları yalnız ignored runtime içinde tutulur. Paylaşılan
suite kayıtları anahtar veya kişisel profil içermez.

## Hazırlık ve korunan ilk başarısızlıklar

Önceki minimal Hermes ortamında aiohttp yoktu; trial-01 API adapter olmadan
başlatma sınırında FAIL oldu, model isteği yoktu. Eski ortam değiştirilmeden
Hermes'in kendi `pm.build_environment` yöntemi, frozen kaynak kilidiyle yeni
ortam kurdu. Pinli `sms` extra yalnız `aiohttp==3.14.3` içerdiği için seçildi;
SMS platformu/servisi açılmadı. Bu ilişki hazırlık helper'ında doğrulanır.

Trial-02 Windows venv başlatıcısının PID'sini interpreter PID'si sanan deney
kontrolünde durdu. Kaynak Gateway hazırdı fakat koşu kabul edilmedi. OS ancestry
ve tutulan handle ile test düzeneği düzeltildi. Bu iki FAIL sonucu final kabul
sayısına dahil edilmez; silinmeden initial-failures.json içinde özetlenir.
Gateway tur ayarı `agent.max_turns`tur; ilk yanlış max_iterations ayarı düzeltildi.

Hermes mevcut SQLite bağlantısında kendi uyumluluk korumasıyla journal_mode=DELETE
seçti; bağımsız okuma bunu doğruladı. Bu testler WAL veya elektrik kesintisi kabulü
değildir. Kişisel/global runtime ve kaynak kodu güncellenmedi.

## Tekrar üretim

```powershell
cd C:\Antigravity\AlazHarness\scratch\worktrees\ref-pi-001-ac97
python -B scripts/prepare_native_hermes.py --source-workspace C:\Antigravity\AlazHarness --output C:\Antigravity\AlazHarness\runtime\gateway-new-env --gateway-http
# Plan varsayılan olarak yazmaz/kurmaz; kurulum için --apply eklenir.
python -B scripts/run_native_gateway.py --source-workspace C:\Antigravity\AlazHarness --python C:\Antigravity\AlazHarness\runtime\hyb-gateway-5a5c\prepared\env\Scripts\python.exe --output C:\Antigravity\AlazHarness\runtime\gateway-new-run --scenario normal
# Diğer açık senaryolar: lost-ack, stop. Her output yeni olmalıdır.
python -B -m unittest discover -s tests -v
python -B scripts/ci_check.py
```

Standart CI yalnız offline kontrolleri çalıştırır. Native Gateway kanıtı yerel
Windows/Python3.14/Node24 ortamınındır; Linux Gateway kabulü diye aktarılmaz.

## Açık kalan kapılar ve sıradaki iş

**HYB-004-GATEWAY-RECOVERY:** aynı profil ve kimliği koruyarak native Gateway'i
kabulden önce/sonra, araç etkisi ve sonuç kaydı arasında, tamamlanmış sonuçtan sonra
kes. Gerçek süreç çıkışı ve yeni epoch ile tekrar aç; mevcut run_id'yi sorgula.
Belirsiz yan etkiyi otomatik yeniden başlatma. HTTP replay tablosu ve authority
admission farklı native kayıtlar olduğu için Pi'nin atomiklik sonucu buraya
aktarılmaz; aradaki crash pencereleri ayrıca ölçülür.

Bu paket tam OpenClaw Gateway girişini, SSE olay replay'ini, ağ segmenti değişimini,
servis yöneticisi kurulumunu, makine güç kaybını, çok-yazıcılı fencing'i, gerçek
modeli, para/token bütçesini, güvenli OS araç izolasyonunu, hafıza/beceri transferini
ve otonom gündem oluşturmayı kabul etmez. Kaynaklar ve HermesRunsClient uygulaması
bu deney için değiştirilmedi. Main merge veya dağıtım yapılmaz.
