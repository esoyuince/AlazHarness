# AlazHarness — status

Son güncelleme: **15 Ekim 2026**. Ana devam kaydı; yeni işte canlı Git durumunu doğrula.

## Kaldığımız yer

**HYB-003-GATEWAY IN PROGRESS:** taban45f7d0e; tek uygulama sahibi5a5c; mevcut aktif worktree. Gerçek gateway sınırı ve kayıt kanıtı hazırlanıyor.

**REF-OC-001 seçilmiş kaynak bileşeni karakterizasyonu PASS.** Gerçek OpenCode
Permission/EventFeed davranış gövdeleri ve Effect/şemalar çalıştı; dış servisler
kontrollü fixture. Tam OpenCode HTTP/DB/uygulama veya ürün benimsemesi kabul edilmedi.
İlk M1 yolu tek Hermes yürütücüsü olarak korundu; Pi ikinci oturum yazarı değil.
Karar: `docs/adr/0003-mvp-single-runtime.md`. Tam M1 ve M2 otonomi açık.

| Alan | Güncel kayıt |
|---|---|
| Varsayılan çalışma alanı | `C:\Antigravity\AlazHarness` |
| Aktif çalışma ağacı | `C:\Antigravity\AlazHarness\scratch\worktrees\ref-pi-001-ac97` |
| Aktif dal | `alaz/hyb-003-gateway-5a5c` |
| Başlangıç commit'i | `b461d4c805c7291f91899edd0d2028c7e00dbf4b` |
| Bu paketin yayını | Kod8117b0a push edildi; exact-SHA alaz/local-ci success,280/280 PASS. Belge HEAD CI ayrı doğrulanır. |
| Repo | `esoyuince/AlazHarness`, public / MIT |
| main | Geliştirme paketleri henüz main ile birleştirilmedi. |

Kökteki `alaz/hyb-001-component-slice` kirli tarihsel ağacını güncel sanma.
Reset/clean/stash veya toplu commit yapma. İzlenen status aktif worktree'dedir;
kök kopyasını yalnız dış değişikliği ezmediğini doğrulayarak eşitle.
CURRENT-STATE.md önceki ayrıntıları korur; ikinci güncel kayıt sahibi değildir.

## Son doğrulama

- **280/280 standart test PASS**, exit0; fail/error/skip0. Son tam tur29.137s.
  `python -B -m unittest discover -s tests -v`.
- **35 ana bileşen senaryosu ×2 süreç =70/70 PASS.** Kaynak gövdeleri gerçek;
  oturum/agent/saved/bus/plugin servislerinin verileri açıkça fixture.
- **20 ek bağımsız bileşen gözlemi PASS** (izin12, olay8). Kaynak doğrudan
  resolver ile yüklendi; aynı uygulama gövdesini testte yeniden yazmadı.
  Paketleme sırasında bu20 kontrol ayrıca tekrar çalıştırılıp doğrulandı.
- Üç sayı ayrı kapsamlardır. Standart alaz-server CI Effect kurmaz veya bu
  yerel OpenCode bileşen senaryolarını çalıştırmaz. Eski native sayılar eklenmez.
- Kanıt: `evidence/ref-oc-001/component-suite.json`, `final-validation.json`,
  `final-root-unittest.txt`, `independent-recheck.json`, `projection.json`.
  Bağımsız rapor/kanıt: `docs/research/REF-OC-001-INDEPENDENT-QA.md` ve
  `evidence/ref-oc-001-qa/`. Önceki269 testi ilk ara turdur; final280 ayrıdır.
- Gerçek model çıkarımı, ücretli çağrı, tam OpenCode servis/HTTP/DB veya
  işletim sistemi sandbox kabulü yok. Gerçek TCP kopması sınanmadı.
- Source/projection/Effect hashleri koşular boyunca değişmedi. Root'ta önceden
  bulunan32 ilgisiz dosyanın hashleri korundu; vendor/research/runtime pinleri aynı.

## REF-OC-001'in kararları

İzin sırası son eşleşmeye dayanır; yapılandırılmış etkin deny, saved allow/plugin
öncesinde uygulanır. Always onayı aynı projedeki diğer session'a da yayılabilir.
Boş kaynak listesi doğrudan servis çağrısında allow olabilir; wildcard gerçek
filesystem/symlink sınırını çözmez. Bekleyen request/save nesnesi mutable;
seçilmiş once onayı sonradan değişen deny'ı yeniden değerlendirmez. Explicit
izin IDsi tamamlandıktan sonra aynı session'da başka isteğe tekrar verilebilir.
Bunlar tam üründe uzaktan açığın kanıtı değildir; Alaz host sınırının şartlarıdır.

Alaz için immutable approval snapshot, benzersiz onay nesli, doğru session/iş
bağı, gerçek araç noktasında güncel değiştirilemez politika ve nonempty trusted
resources gerekir. Bu tur üretim izin servisi yazılmadı.

EventFeed volatile: yavaş abone açık hata alır; kodlama hatası mevcut aboneleri
kapatır; yeni abone sonraki olayı alabilir. Kopuklukta yayımlanan olaylar otomatik
geri gelmez. Bu OpenCode'un ayrı durable session-log API'si olmadığı anlamına
gelmez; o API bu pakette test edilmedi. Yetkili durum yeniden sorgulanmadan
kayıp bildirim üzerinden araç etkisi tekrar edilmez.

## Kullanılan ortam ve kaynaklar

OpenCode pin `3943b84ef00e83dbc3c48e6a92b02f0d88fb35f9`.
Effect4.0.1, kaynak bun.lock ile aynı archive integrity; tek bağımlılık olarak
`runtime/ref-oc-001-8ea1/qualified` içine sabit npm lock ve ignore-scripts ile
kuruldu. Global Node/npm, Bun, kişisel profil/anahtar veya servis değiştirilmedi.
Kaynak projeksiyonu94 source /96 output hash içerir; bu test sayısı değildir.
Import yönlendirmesi ve küçük işlev seçimi dışında hedef davranış gövdeleri
korunur. Ayrıntı `docs/research/REF-OC-001-COMPONENTS.md`.

Hazırlık `scripts/prepare_opencode_components.py` plan kipinde yazmaz; --apply
kurar. Çalıştırma `scripts/run_opencode_components.py`, ek QA
`scripts/run_independent_opencode_qa.py`; her output yeni olmalı.
Node runtime namespace için mevcut --experimental-transform-types kullanıldı.
İlk strip-only yükleme hatası kabul sayısına katılmadan kaydedildi.

## Önceki tamamlanan işler

M0: kaynak/fork/pin/MIT/CI. HYB-001/002: seçilmiş OpenClaw/Hermes ve taşıma
sözleşmesi. Hermes gerçek AIAgent/read_file yerel taklit modelle çalıştı.
REF-PI-001 Agent/read, REF-PI-002 Durable kesinti ve REF-PI-002B atomik içerik
kabulü ayrı kanıtlarıyla korundu. 002B iki Durable geçmişini birleştirdi;
strict-admission sahibi binding/transaction sorunları düzeltildi. Motorların
bütün çalışma özellikleri veya M1/M2 tamamlandı denmedi.
Paralel eski Pi Agent c31cf19 paketi otomatik birleştirilmedi/silinmedi.

## Sıradaki kesin iş

**HYB-003-GATEWAY — NOT RUN.** Mevcut HermesRunsClient'ı sabit kaynakta gerçek
Hermes Gateway / SessionAuthority / APIServerAdapter zincirine, tek kontrollü
model ve gerçek araç ile bağla. Duplicate/conflict/lost-ack/cancel/resume
sınırlarını native kayıtla ölç. Yeni mock HTTP sunucusu gerçek Gateway kabulü
sayılmaz. Hermes tek yürütücü/oturum sahibi kalsın; Pi Durable yan veritabanı
olarak eklenmez. Dört aday kaynak dört çalışan ajan döngüsü değildir.

Sonraki açık kapılar: gerçek OpenClaw girişi, çok süreçli store sahipliği,
kalıcı kesinti entegrasyonu, araç izinleri, tüm provider/yardımcı çağrılarda
istek-token-para bütçesi, OS izolasyonu, hafıza/beceri transferi ve sınırlı gerçek
model M1 kabulü. Otonom gündem M2 bunlardan sonra.

## Kayıt ve geçmiş

Her iş başı/ara sonuç/sonu status güncellenir. Komut, test kapsamı, gerçek exit,
kanıt, commit/push ve exact-SHA CI ayrıdır; eski yeşil yeni commit'e taşınmaz.
Kör etkili retry yok. Başlangıç/QA günlüklerinin tam eski kopyası
`docs/history/2026-10-15-STATUS-BEFORE-OC001-DELIVERY.md` içindedir. Önceki
002B history dosyaları da oradaki bağlantılarıyla korunur. Eski komutlar yeni
çalıştırma yetkisi değildir.

### 2026-10-15 — REF-OC-001 — Yerel kapanış

İzin/olay araştırma sınırı tamamlandı; bütün280 standart test ve ayrı70 ana
bileşen /20 ek bağımsız gözlem PASS. Kaynak/app graph'ı değiştirilmedi;
fixture ve tekrar üretim helperları ile kanıt/ADR/status eklendi. Tam ürün
benimsemesi açık. Sonraki kayıt commit/push/CI'ı kanıtla güncelleyecek.

### 2026-10-15 — REF-OC-001 — Yayın kapanışı

Kod8117b0a611dab5d96acdd658a78365ebbbae2920 uzak dalda; alaz-server aynı SHA280/280, fail/skip/suite_error0 ve GitHub alaz/local-ci success doğrulandı. Kanıt evidence/ref-oc-001/code-ci.json. Önceki PENDING kayıt tarihsel; native70 ve bağımsız20 bu CI toplamına eklenmez. Sonraki iş HYB-003-GATEWAY; main birleşmedi.

### 2026-10-15 — HYB-003-GATEWAY — Başlangıç

Taban45f7d0e9f1ebb7bd15dc846c0d0b7cf9276d758a, aynı ref-pi-001-ac97 worktree;5a5c tek yazıcı. Önceki REF-OC-001 kod8117b0a exact-SHA280/280 server PASS; son belge CI ayrı. Yerel kontrollü model, yeni izole profil, gerçek GatewayRunner/SessionAuthority/APIServerAdapter ve HermesRunsClient hedefleniyor. Mevcut vendor/kişisel profil/sunucu değiştirilmez; ücretli model veya otonomi yok.

### 2026-10-15 — HYB-003-GATEWAY-QA208f — Başlangıç

Bağımsız QA IN PROGRESS.5a5c tek uygulama yazıcısı korunuyor;208f aynı
çekirdeğe ikinci uygulama/runner yazmıyor. Yetkisiz çağrı, idempotency kimliği,
native admission/status tutarlılığı ve iptal/yeniden bağlanma kanıtları
runtime/hyb-gateway-qa-208f altında inceleniyor. Kişisel profil/model anahtarı
yok, ücretli çağrı yok. Sonuç henüz NOT RUN; uygulama makbuzu kendiliğinden kabul değil.

### 2026-10-15 — HYB-003-GATEWAY — Bağımlılık/başlatma ara kaydı

İlk trial-01 gerçek Gateway başladı fakat aiohttp olmadığı için API adapter kurulamadı; model çağrısı0, kabul FAIL, süreç exit1 ve toplandı. Başarısız kanıt runtime/hyb-gateway-5a5c/trial-01 içinde korunuyor. Eski native env değiştirilmedi; PM frozen minimal sms extra yalnız aiohttp3.14.3 için ayrı prepared/env oluşturdu (SMS platformu etkin değil). Doğru Gateway tur sınırı agent.max_turns olarak düzeltildi. trial-02 gerçek başlatma/kabul deneyi çalışıyor; native request c9207a74-f8bb-4c2e-a4d4-e85e5350b3b6 sonucu henüz bilinmiyor.

### 2026-10-15 — HYB-003-GATEWAY-QA208f — Yerel bağımsız kabul

9/9 gerçek HTTP ret sınırı PASS, model0: native GatewayRunner/Authority/API,
canonical store aynı, yanlış auth/key/native-session/unknown-run hiçbir iş
oluşturmadı. Parent ve gerçek Windows alt süreç OS handle ile doğrulandı;
kapanış sonrası bağımsız readonly DB0 admission/0tool, integrity ok.
16 offline kanıt/reader testi ayrı PASS. Primary trial-03 kaydı bağımsız
readonly incelendi:1 terminal admission/1gerçek read_file/two mock HTTP,
nonce/PID shutdown tutarlı. Bu tekrar lifecycle koşusu veya crash kabulü değil.
Kod scripts/run_gateway_refusal_qa.py ve scripts/qa/hermes_gateway_refusals.py;
rapor HYB-003-GATEWAY-INDEPENDENT-QA.md; evidence/hyb-gateway-qa.
Global/native kaynak değiştirilmedi; yalnız izole frozen aiohttp ortamı hazırlandı.
Primary5a5c tek uygulama yazıcısı; tüm paket CI/commit henüz bu kayıtta PENDING.

### 2026-10-15 — HYB-003-GATEWAY-QA208f — Tam standart ve kalıcı kayıt kapanışı

Bağımsız tam standart koşu321/321 PASS, exit0/skip0, ölçülen kod drift yok.
6 ana native koşunun sonuç/kimlik/store kayıtları readonly ikinci kez
incelendi: normal/lost-ack tek canonical+idempotency kayıt,1 read_file/2 modelHTTP;
stop native interrupted,0 tool/1 modelHTTP. Bu6 yeni yürütme değil, önceki
koşuların bağımsız teyididir. QA9 gerçek HTTP ret testi ayrı; model çıkarımı0.
11 yalnız QA dosyası stage edildi; yeni branch veya ikinci uygulama commit'i
açılmadı.4 upstream temiz ve pinler aynı. Rapor/kanıt primary teslimine hazır.
Paket commit/push/CI için canlı HEAD ayrıca okunmalı; önceki CI taşınmaz.
