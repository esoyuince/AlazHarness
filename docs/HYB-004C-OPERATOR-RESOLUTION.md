# HYB-004C — Açık operatör kararıyla kabul edilmemiş isteği kapatma

15 Ekim 2026. Dal `alaz/hyb-004c-resolution-4cff`; taban
`21321cf2df520b7dca2d976dfd089a8322ff56b5`. Bu paket yeni ajan, kuyruk,
oturum veritabanı veya genel otomatik kurtarma sistemi eklemez. M1/M2 kabulü değildir.

## Uygulanan tek işlem: abandon_unadmitted

Operatör, rezervasyonu kalmış fakat asıl işi hiç kayda alınmamış isteği yeniden
çalıştırmak yerine açıkça kapatır. `requestClosed=true`, görevin başarısı değildir:
`taskSucceeded=false`, `retryAllowed=false`, `admissionCreated=false` ve
`reservationDeleted=false` korunur. Unknown/canonical/completed/retired iş bu
operatör işlemiyle değiştirilmez. Gerçek unknown execution için native resolver
ayrı bir davranıştır; burada çağrılmaz ve arkasındaki işler otomatik başlatılmaz.

`OperatorResolution.prepare` yalnız önizleme verir. Plan; işlem türü, komut
kimliği, profil ve principal kapsamı, run kimliği, anahtar/içerik parmak izleri,
epoch/instance ve iki kaydın snapshot parmak izine bağlıdır. Varsayılan onay
penceresi beş dakikadır. Çıktıda istek metni, bearer veya açık anahtar bulunmaz.
`apply` ayrı, açık bir işlem ve planın tam confirmationDigest değeri ister.
Bu hash bir login/onay servisi değildir: güvenilir yerel operatörün inceleyip
onayladığı baytları bağlar. Uzak istemciden alınmış profile_home/token/epoch
konfigürasyonu kabul eden ağ uç noktası eklenmedi.

## Sahiplik ve tek veritabanında kayıt

Apply, sabitlenmiş Hermes'in gerçek `exclusive_maintenance` mekanizmasını
kullanır. Gateway veya başka bakım sahibi varsa işlem reddedilir. Yalnız PID
metni veya caller'ın 'durduruldu' beyanı yeterli değildir; aynı native kilit
işlem boyunca tutulur. Eski rezervasyon PID'si hâlâ canlı görünüyorsa ayrıca
muhafazakâr ret vardır; PID başka sürece tekrar verilmiş olsa bile zorla devam yok.
Kilit inode'u silinmez veya değiştirilmez; native mekanizma içeriğini damgalayabilir.

SQL işlemi iki mevcut veritabanını açar, kaynak şemasını ve dosya kimliğini
kontrol eder. BEGIN IMMEDIATE altında güncel epoch/instance, anahtar/body/run,
retention ve canonical kayıtlar tekrar okunur. Değişen snapshot/plan reddedilir.
İki veritabanı üzerinde okuma/yazıcı rezervasyonları tutulsa da yazılan TEK
veritabanı `state.db`dir. Sadece mevcut `state_meta` içine aynı transaction'da
iki namespaced satır eklenir: komut makbuzu ve run→komut indeksi. İkinci bir
DB'ye ayrı commit yapılıp atomikmiş gibi sunulmaz. Replay anahtarı, transcript,
sessions, admissions, terminal sonuç ve kullanım değerleri değiştirilmez.

Yeni şema migration'ı, DELETE, eski işin status UPDATE'i veya modele POST yoktur.
`state_meta` üzerinde tetikleyici varsa yazma reddedilir. Kayıt/indeks bir arada
yazılır; aynı onaylı komutun cevabı kaybolursa tekrarında aynı makbuz döner.
Başarılı eski makbuz yeni epoch altında yeniden okunabilir, fakat yeni işlem
eski epoch veya süresi dolmuş planla uygulanamaz. Hata anında commit bilinmiyorsa
CLI `effect=unknown` der; yanlış bir kesin rollback iddiası yapılmaz.

## İndeks kaybı ve çelişkili sonradan gelen kayıt

Arşiv indeksi yoksa iş hiç var olmamış sayılmaz. Native terminal admission
kayıtları da sınırlı taranır: en çok10000 kayıt/8MiB; bozuk veya tamamlanamayan
arşiv taraması işlem izni vermez. Başka principal'a ait aynı run/target, ilgili
session, message veya worker de yokluk iddiasını engeller. Tamamlanmış/unknown
işin arşive taşınması onu terk edilebilir hâle getirmez.

Aynı komut tekrarında salt eski makbuz okunup güncel requestClosed varsayılmaz:
ilgili canonical işin hâlâ bulunmadığı yeniden kontrol edilir. Kapanıştan sonra
çelişkili kayıt oluşmuşsa replay ve readonly inspector reddeder. Bu kontroller
bağımsız QA'nın iki tutarsız sentetik kayıt senaryosundan geldi; ilk başarısız
çıktılar korunur. Normal native sistemin böyle kayıtlar ürettiği veya uzaktan
bir açık bulunduğu iddiası değildir.

## Okuyucuyla bütünleşme

`LocalRecoveryInspector` artık doğrulanmış operatör kaydı varsa
`reservation_abandoned_verified` döndürür. `resolutionVerified=true` ile
`canonicalVerified=false` aynı anda mümkündür: doğrulanan şey işin çalışması
değil, bu isteği çalıştırmadan kapatma kararıdır. Sonuç `taskSucceeded=false`
kalır. Yanlış/eksik indeks, bozuk digest, başka profil/anahtar, sonradan canonical
çelişki veya güncel epoch uyuşmazlığı sonucu doğrulatamaz.

Makbuz yetki nesnesi değildir. Dönen JSON'da retryAllowed'u değiştirmek bir
işlem yetkisi kazandırmaz. Dosyaları yazabilen kötü niyetli yöneticiye karşı
kriptografik attestation iddiası yoktur; bu yerel host güven sınırıdır.

## Saklama süresi ve açık sınırlar

Bu işlem native replay retention politikasını değiştirmez. Yerel audit kaydı
kalabilir fakat native anahtarın süresini sonsuza uzatmaz. Ham upstream POST
uç noktası Alaz audit kaydını bilmiyor. Süre dolduktan sonra dışarıdan ham API'ye
aynı anahtarla POST yapılmasını küresel olarak engellediğimiz iddia edilmez.
Alaz istemcisi hiçbir sonucu otomatik yeniden göndermiyor; gelecekteki tek
başlatma sınırı, kapalı istek ve retention geçmişini ayrıca bağlamak zorunda.

Default-profile bearer ve yeni run başlatan input/opsiyonel doğrudan model
kapsamı desteklenir; explicit session_id bu yazma işleminde reddedilir.
Güvenilen yerel context gerekir. Kaynak kilidi kod kökeni kontrolüdür, tüm
çalışan Python bağımlılıklarının imzalı doğrulaması değildir. Managed native
kilide uymayan kötü niyetli DB yazıcısı, makine güç kaybı, NFS/disk arızası,
WAL donanım dayanıklılığı ve genel çok-yazıcılı fencing kabul edilmedi.

## Kullanım

Hazır proje ortamı kullanılmalı; bu araç bağımlılık kurmaz. Context JSON:
profile_home, api_token, epoch, instance_id. Request JSON: body, idempotency_key,
observed. Bu dosyalar host-owned private runtime altında tutulur, Git'e girmez.

```powershell
$py = 'C:\Antigravity\AlazHarness\runtime\hyb-gateway-5a5c\prepared\env\Scripts\python.exe'
& $py -I -B scripts/resolve_gateway_reservation.py --source-workspace C:\Antigravity\AlazHarness --context <private-context.json> --request <private-request.json> --command-id <32hex>
# Önizlemedeki plan nesnesi ayrı plan.json'a kaydedilir ve operatör tarafından incelenir.
& $py -I -B scripts/resolve_gateway_reservation.py --source-workspace C:\Antigravity\AlazHarness --context <private-context.json> --request <private-request.json> --apply --plan <plan.json> --confirm <confirmationDigest>
```

Varsayılan dry-run'dır. Otomatik onay/force seçeneği yoktur. Exit0 kapanış veya
önizlemenin çıktısıdır, kullanıcı görevinin başarıyla çalıştığı anlamına gelmez.
Reddedilen istek exit2; storage_or_commit_unconfirmed sonucu tekrar yazmak için
izin değildir, önce aynı komutun makbuzu güncel sahiplik altında sorgulanır.

## Test kapsamları

- `tests/test_operator_resolution.py`: sentetik SQLite ve açık test-only lock
  yerine geçeni. SQL/closure/receipt kodu gerçek; native ownership kanıtı değil.
- `scripts/run_operator_resolution_probe.py`: yeni gerçek Gateway profili,
  owned crash/reopen, gerçek operatör CLI ve native maintenance ile kapanış;
  tamamlanmış ve unknown işler için ret. Orphan senaryosu üçüncü Gateway neslinde
  eski anahtarın replay'ini ve kapanışın korunmasını sınar. Tek model cevapları
  scripted localhost'tur. Mevcut eski native profiller değişmez.
- QA native lock ve transaction crash deneyleri ayrı kapsamdır; SQL fixture
  kullanılarak yapılmış süreç kesintisi, gerçek Gateway admission üretimi sayılmaz.
- Tam standart test paketi CI'da native ortam kurmaz veya model çalıştırmaz.

Son gerçek koşu sayısı ve dosya hash'leri `evidence/hyb-004c` içinde; ön-düzeltme
orphan-initial sonucu final koda taşınmaz. Bağımsız rapor ve kanıtlar
`docs/research/HYB-004C-INDEPENDENT-QA.md`, `evidence/hyb-004c-qa` altındadır.
Final kabul/commit/aynı-SHA CI status.md'de ayrı kaydedilir.

## Sonraki geliştirme

Kurtarmanın bu dar kapatma işlemiyle bitmesi, bütün retry sorunlarının çözülmesi
değildir. Yeni çağrıların tek host girişinde izin, kapalı istek/retention ve
bütçe kontrolünü bağlamak M1 için gerekli. Gerçek unknown dış etki yeniden
çalıştırılmaz. Bir sonraki paket, tek host yürütme sınırının bu kararları atlamadan
uygulandığını ve model/araç izinlerini test etmeye odaklanmalı; yeni otonomi
zamanlayıcısı veya başka model motoru eklenmemeli.

## Son yerel kabul

Son kodla standart604/604, Gateway-created profile3/3, bağımsız sentetik SQLite
üstünde gerçek transaction process-kill2/2 ve native lock13koşul PASS. Bunlar
farklı kanıt türleridir; toplanmaz. İlk orphan deneyi ön-fix olduğu için ayrı.
Ana Gateway koşularında model çıkarımı/ücretli çağrı0; operator aşamasında model
HTTP0. Native kaynaklar ve32eski kök dosya korunur. Git/CI kaydı status.mdye
yeni commit ile eklenecek. Kapanan şey explicit local audit işlemidir.
