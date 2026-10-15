# AlazHarness — status

Son güncelleme: 15 Ekim 2026. Her yeni işten önce bu kaydı ve canlı Git'i oku.

## Kaldığımız yer

**HYB-003-GATEWAY dar native kabul PASS.** Mevcut HermesRunsClient, gerçek public
Gateway başlangıcı, SessionAuthority/FIFO ve APIServerAdapter üzerinden yerleşik
read_file aracını çalıştırdı. Normal/kayıp kabul yanıtı/model beklerken stop:
3 senaryo ×2 ayrı profil ve süreç =6/6. Gerçek model çıkarımı ve ücretli çağrı0.
Tam OpenClaw giriş zinciri, M1 ve otonomi M2 henüz kabul edilmedi.

| Alan | Güncel kayıt |
|---|---|
| Varsayılan kök | C:\Antigravity\AlazHarness |
| Aktif çalışma ağacı | C:\Antigravity\AlazHarness\scratch\worktrees\ref-pi-001-ac97 |
| Aktif dal | alaz/hyb-003-gateway-5a5c |
| Bu paketin tabanı | 45f7d0e9f1ebb7bd15dc846c0d0b7cf9276d758a |
| Yayın | Kod c4a3f500eddc75d91c507ecb346af999237b32aa push edildi; aynı SHA alaz/local-ci success ve321/321 PASS. Son belge HEAD CI ayrıca sorgulanır. |
| Remote | esoyuince/AlazHarness public MIT |
| main | Bu geliştirme paketleri henüz main ile birleştirilmedi. |

Kökteki eski kirli alaz/hyb-001-component-slice dalı güncel ürün kodu değildir.
Reset/clean/stash veya toplu commit yapma. Aktif status.md esas, kökteki dosya
kolay erişim kopyasıdır. Eşzamanlı değişiklikleri okumadan üzerine yazma.

## Bu turda tamamlananlar

Önce REF-OC-001 kod8117b0a için alaz-server/GitHub280/280 success doğrulandı;
status teslim kaydı45f7d0e ile kapatıldı ve onun CI'sı da success okundu.
Yeni Gateway deneyinin raporu docs/HYB-003-GATEWAY.md içindedir.

- Normal:1 native admission,1 user,1 gerçek read_file sonucu,2 scripted model HTTP.
- Lost-ack: röle gerçek Gateway202'sini aldıktan sonra TCP yanıtını düşürür;
  adapter sonucu unknown olarak bildirir. Deneyin AÇIK aynı-key tekrarı aynı
  run_id'yi bulur;1 admission/1 tool/2 model HTTP. Otomatik POST retry eklenmedi.
- Stop: gerçek provider isteği gözlendikten sonra native stop; ayrı terminal
  sorgusu HTTPcancelled ve DBinterrupted gösterdi;1 admission/1 user/0 tool.
- Üç senaryoda aynı-key tekrar, farklı payload409, yanlış auth401 ve salt-okuma
  resume kontrolü var. Kapanış sonrası SQLite iki-store/kimlik/epoch ve transcript
  bağımsız okunur; gerçek source dosyaları testte değiştirilmez.
- Windows venv redirector+interpreter OS ancestry/held handle ile sahiplenilir.
  İki süreç de exit0 ve native shutdown makbuzuyla kapandı. Bu bir OS sandbox değil.
- Başarısız trial-01(aiohttp yok) ve trial-02(yanlış PID varsayımı) saklandı;
  bu iki koşu6 kabul toplamına dahil edilmez.

## Doğrulama ve ayrı kapsamlar

**321/321 offline kök testi PASS**, exit0, skip0.25 yeni Gateway kanıt/parent
kontrolü ve16 bağımsız ret kanıt testi dahil. Bu sayı native6 veya ek9 ile toplanmaz.
Ana native6 koşu yerel Windows/Python3.14/Node24 üzerinde geçti; CI bunları kurmaz.
Ek bağımsız9 gerçek HTTP ret kontrolü ayrıca incelenip bu ana entegrasyon tarafından
yeniden çalıştırıldı:0 admission/0tool, paylaşılan canonical store ve kapanış PASS.
Ek QA programatik Gateway/authority kurar, public tam start_gateway yaşam döngüsünü
sınamaz; ana6 koşu o yaşam döngüsünü gerçekten sınar.

Ana kanıt: evidence/hyb-003-gateway/native-suite.json, normal/lost-ack/stop-*.json,
local-validation.json, initial-failures.json, independent-refusal-recheck.json.
Ek bağımsız çalışma: evidence/hyb-gateway-qa ve
 docs/research/HYB-003-GATEWAY-INDEPENDENT-QA.md. Önceki280/70/20 sayıları tarihseldir.

## Kaynak/ortam

Hermes pin eb75627faf532fa6ffbdae59a0d14b0b385fc780; source-lock manifesti
config/gateway-probe/source-lock.json. OpenClaw/Pi/OpenCode pinleri temiz ve aynı.
HermesRunsClient ve10 seçilmiş upstream bileşeni değiştirilmedi. Kök32 eski
ilgisiz dosya korundu; sunucu ayarı veya kişisel ajan profili değiştirilmedi.

Mevcut minimal Hermes env API için aiohttp içermiyordu. Ayrı proje ortamı
runtime/hyb-gateway-5a5c/prepared/env/Scripts/python.exe altında, Hermes'in kendi
pm.build_environment frozen/sms extra ile hazırlandı. Bu pinli extra yalnız
aiohttp3.14.3 içerir; SMS açılmadı. Eski environment/global araçlar korunur.
Model yanıtları localhost scripted HTTP; API anahtarları yalnız bu yeni testlerin
rastgele local değerleri. Runtime config/profil/log/sırlar Git'e eklenmez.
Native SQLite koruması journal_mode=DELETE seçti; WAL/güç kaybı kabulü yok.

## Sıradaki kesin iş

**HYB-004-GATEWAY-RECOVERY — NOT RUN.** Aynı native profil, API kimliği ve request
anahtarını koruyarak farklı kalıcı kayıt sınırlarında owned process kill/reopen
sına. Kabulden önce/sonra, gerçek araç sonucu ile terminal kayıt arasındaki boşluk,
tamamlanmış cevabın yeni model çağrısız geri alınması ve yeni runtime epoch.
Kayıtları her süreç exit'ten sonra readonly ölç; sonuç belirsizse tool'u otomatik
tekrar başlatma. Hermes'in run_idempotency ve authority store'ları arasında crash
atomikliği henüz kanıtlanmadı; Pi strict-admission sonucu Hermes'e taşınmaz.

Diğer açıklar: tam OpenClaw girişi; gerçek araç yetkileri ve tüm model/yardımcı
çağrılarda istek/token/para bütçesi; OS izolasyonu; çok süreçli fencing; kalıcı
hafıza/beceri transferi; sınırlı gerçek model M1 kabulü. M2 daha sonra.

## Devam komutları

```powershell
cd C:\Antigravity\AlazHarness\scratch\worktrees\ref-pi-001-ac97
git status --short --branch
git log -3 --oneline
python -B scripts/ci_check.py
python -B -m unittest discover -s tests -v
```

Native komutlar ve açık sınırlar docs/HYB-003-GATEWAY.md içinde; her output yeni
olmalı. Önceki hazırlığı körlemesine tekrar kurma. Etkisi bilinmeyen çağrıyı yeniden
göndermeden makbuzunu oku. Kod/push/aynı SHA CI ayrı doğrulanır.

## Korunan geçmiş ve bu işin günlüğü

Önceki status'un TAM kopyası:
`docs/history/2026-10-15-STATUS-BEFORE-GATEWAY-DELIVERY.md`.
O dosya REF-OC-001, bu Gateway işinin başlangıç/ara durumlarını ve QA208f kayıtlarını
korur; daha eski iş günlüğü bağlantıları da kaybolmaz. CURRENT-STATE.md tarihseldir.

### 2026-10-15 — HYB-003-GATEWAY — Yerel kapanış

Gerçek public Gateway/Authority/API yolu kuruldu ve6/6 native,321/321 standart,
ek9/9 gerçek HTTP ret kontrolü ayrı kapsamlarda PASS. Kaynak gövdeleri veya
prod adaptör değiştirilmedi; test model/röle/parent/kanıt scriptleri ve rapor yazıldı.
Ücretli model ve otonom gündem yok. Yeni kodun Git/CI teslimi ayrıca eklenecek.

### 2026-10-15 — HYB-003-GATEWAY — Git / CI teslimi

**DONE — dar native Gateway kabul paketi.** Kod commit'i
`c4a3f500eddc75d91c507ecb346af999237b32aa` uzak alaz/hyb-003-gateway-5a5c dalında.
Gerçek alaz-server aynı commit'i checkout ederek321/321 standart testi çalıştırdı;
failed/skipped/suite_errors0, status_delivery posted. GitHub alaz/local-ci success
ayrıca okundu. Makbuz: evidence/hyb-003-gateway/code-ci.json.

Yerel6/6 public Gateway yaşam döngüsü ve ayrı9/9 programatik native HTTP ret
kontrolü CI321'e eklenmez. Ücretli model veya otonomi yok; vendor, asıl adaptör,
sunucu profili ve kişisel ayarlar korunur. Aktif iş günlüğü ve kök kolay erişim
kopyası eşitlendi. Main merge yapılmadı. Bu son ek yalnız teslim kaydıdır;
native deneyler bu belge güncellemesinde yeniden çalıştırılmadı.
Sonraki kesin iş HYB-004-GATEWAY-RECOVERY; M1/M2 henüz kabul edilmedi.
Belge commit'inin exact-CI durumu yeni HEAD üzerinden ayrıca kontrol edilmelidir.
