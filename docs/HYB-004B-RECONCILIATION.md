# HYB-004B — Salt-okuma kurtarma ve kanıt ayrımı

15 Ekim 2026. Dal `alaz/hyb-004b-reconciliation-7c8b`; taban
`ebc81a50350c2fdc3d32dc88d3e834adfaffedba`. Bu paket mevcut istemci davranışını
ve yerel denetleyiciyi değiştirir. İkinci ajan döngüsü, scheduler, oturum deposu,
anahtar silme veya otomatik onarım eklemez. Tam M1/M2 değildir.

## Üründe değişen sınır

`HermesRunsClient.reconcile(runId)` tek kimliği doğrulanmış GET yapar; iş
başlatmaz, kontrol/stop yollamaz, retry yapmaz. `resume` artık salt okumadır:
zaman aşımı veya izleme iptali yalnız `observation_interrupted` döndürür.
Önceki `resume -> observe` bağlantısı timeout'ta native stop gönderebiliyordu;
bu yan etki ayrıldı. Bilinçli kontrol amaçlı `observe` ve `stop` ayrı kalır.

HTTP sınıflandırıcısı `run-recovery.mjs` native admission_id/session_id/positive
generation üçlüsü olmayan terminal sonucu `terminal_unverified` yapar.
`transportConfirmed=true` terminal HTTP etiketi anlamına gelir. Bu durumda
`backendConfirmed=false`, `requiresOperator=true`; otomatik retry/repair her
zaman false. Tam native tuple varsa `canonical_terminal_reported` gelir ama
`canonicalVerified` yine false; bu bağımsız veritabanı kanıtı değildir. Hiçbir
terminal etiket tek başına görevin başarılı olduğuna karar vermez. Ham native
status ve output korunur. ContractVersion1 bu daha sıkı anlamı görünür kılar.

## Gerçek kayıt denetleyicisi

`packages/claw-hermes/recovery_inspector.py`, source-key ve terminal mapper
bileşenlerini mevcut lisanslı seçilmiş Hermes kodundan kullanır. Yeni
`LocalRecoveryInspector` aynı makinedeki native `state.db` ile
`runs_idempotency.db` kayıtlarını SADECE salt okunur açar. Yerel çağıran tarafından
sağlanan `LocalRecoveryContext` güvenilir HOST konfigürasyonudur; bu bir ağ
isteğinden alınacak profil yolu/anahtar/epoch değildir. Bir API key sahibi olmak
rastgele bir dosya yolunu sunucuya okutma yetkisi vermez; bu sürüm internete açık
inspection endpoint'i sağlamaz.

İki dosya mode=ro ve query_only ile tek bağlantıda okunur. Sabit tablo adları,
özgün scoped idempotency key, tam body fingerprint, run kimliği, canonical payload
digest, içerik, doğrudan model seçimi, scope, session/admission/generation ve
beklenen runtime epoch/instance denetlenir. `data_version` ve epoch tekrar
okunarak gözlenen eşzamanlı değişiklikte karar reddedilir; dosya kimliği değişimi
de reddedilir. Bağlantı başarıda da hatada da kapatılır. SELECT/PRAGMA/ATTACH ve
okuma transaction'ı dışında SQL yazısı yoktur; native lookup() kullanılmaz,
çünkü o yöntem retention temizliği yapabilmektedir.

Sonuç bir SNAPSHOT'tır; atomik iki-store commit, canlı süreç lease'i veya sonradan
etki yapma izni değildir. `sourceCommit`, desteklenen şema kaynak sürümünü belirtir;
bağımsız çalışan bilinmeyen bir binary'nin uzaktan attestation'ı değildir. Native
kabul scripti gerçek vendor commit/temizliğini ayrıca doğrular.

| Kanıt | Sınıflandırma | Davranış |
|---|---|---|
| Tam native terminal kimliği + kayıtlı output/usage birebir | canonical_terminal_verified | Gerçek outcome korunur; yalnız completed ise taskSucceeded. Retry/repair yok. |
| Canonical kayıt unknown | execution_unknown | Operatör gerekir; yeniden çalıştırma yok. |
| Scoped rezervasyon var, o snapshot'ta canonical kayıt yok | reservation_without_admission_observed | Operatör gerekir; tamamlandı veya hiç çalışmadı garantisi verilmez. |
| Aktif canonical kayıt | in_progress | Mevcut işi gözle; yeni iş açma. |
| Yanlış key/scope/body/epoch, eksik/bozuk store veya uyuşmazlık | unverified | Güvenilir karar yok; işlem izni yok. |

Kaybolan canlı admission tek başına orphan sayılmaz. Native terminal identity,
tombstone ve final result kayıtları da kontrol edilir. Eski sonuç arşive taşındıysa
birebir korunabilir; arşiv eksik/çelişkiliyse karar verilmez. Anahtar yokluğu veya
retention dolması `lookup_unavailable`/`retention_expired` olur; bu durumlar
“hiç gönderilmedi, tekrar çalıştır” anlamına gelmez. Inspector expiry temizliği
yapmaz. Dönen JSON değiştirilebilir olsa bile hiçbir mutation API'si bu JSON'u
bir izin belgesi olarak tüketmez.

Destek default-profile bearer ve mevcut adapter'ın input/model/session_id body
şeklidir. Room grant, multiplex profile, model alias/explicit-provider/options
ve compression target remapping bu sürümde tahmin edilmez; güvenli ret verir.
Bu dar kapsam gizlenmemelidir. Üretimdeki tam auth/lease/route bağının eklenmesi
ayrı kabul işi olarak kalır.

## Gerçek deneyler ve regresyon kapsamı

İlk kod üzerinde dört senaryo ikişer kez yeni native süreçlerle geçti: orphan
reserve, completed, ilk model yanıtını bekleme, gerçek read_file sonucundan sonra
bekleme. Bunların sekiz native makbuzu korunur. Daha sonra bağımsız QA bozuk
payload tipleri, model-route kayıt uyuşmazlığı ve public classifier tip/çelişki
kontrollerini buldu; kod düzeltildi. İlk sekiz yeşil son kodun native kabulü diye
sunulmaz. Son kod için dört senaryo yeniden çalıştırılır ve sonuçlar
`final-native-suite.json` içinde ayrı tutulur; dosyanın varlığı ve gerçek PASS
alanları kontrol edilmeden kapanış iddiası yapılmaz.

Dört final koşu aynı gerçek public Gateway, model/araç döngüsü, native iki store
ve owned kill/reopen mekanizmasını kullanır. Her native koşuda iki süreç nesli,
bir zorunlu kill vardır. Yalnız model yanıtları controlled localhost fixture'dır.
Completed iki eski model HTTP isteği, before-model bir, after-tool iki, rezervasyon
boşluğu sıfır üretir; yeniden açıldıktan sonra ek model/araç yok. Inspector ayrıca
wrong-token/stale-epoch/changed-body retlerini o gerçek kayıtta dener ve native
DB baytlarının değişmediğini doğrular. Gerçek inference/ücretli çağrı yok.

Standart unit/loopback testleri bunlardan AYRIDIR. Kayıtlı on eski HYB-004 profilinin
final inspector ile yeniden okunması da yeni on süreç deneyi değildir. Sentetik
SQL arşiv/bozuk kayıt testleri gerçek native retirement/race kabulü yerine geçmez.
Eski gap validator önceki flagsiz sözleşmeyi tarihsel veride korur; yeni v1
projection'da muhafazakâr flagleri zorunlu kılar. Önceki makbuzlar değiştirilmez.

## Bağımsız QA kapanan bulguları

Public classifier artık tamamlandı+başarısız/partial gibi çelişkileri ve string
olmayan run_id'yi reddeder; boşluk session native kimlik sayılmaz. HTTP snapshot'ın
zaten reddettiği çelişki public yardımcıda da reddedilir. Bozuk payload/list/null
artık exception kaçırmadan unverified olur. Replay body.model ile native seçilmiş
model farklıysa kayıt doğrulanmaz; desteklenmeyen alias/provider rotası reddedilir.
Bunlar geçici fixture ile gösterilen ret/bozuk-record sorunlarıdır, normal upstream
trafikte gösterilmiş uzaktan açık iddiası değildir. İlk başarısız çıktılar korunur;
regresyonların düzeltme sonrası sonuçları bağımsız raporda ayrıca yazılır.

## Kullanım ve tekrar üretim

```javascript
const observation = await client.reconcile(runId); // exactly one GET
// observation.canonicalVerified is false: no database audit was performed here.
```

Yerel host private context dosyası alanları: profile_home, api_token, epoch,
instance_id. Request dosyası alanları: body, idempotency_key, observed. Bunlar
runtime altında tutulur, Git'e eklenmez. Güvenilen context, dış istemcinin
bildirdiği dosya yoluyla veya onun seçtiği epoch ile oluşturulmaz.

```powershell
python -B scripts/inspect_gateway_recovery.py --context <host-private-context.json> --request <original-request-and-observed.json>
python -B scripts/run_gateway_reconciliation.py --source-workspace C:\Antigravity\AlazHarness --python C:\Antigravity\AlazHarness\runtime\hyb-gateway-5a5c\prepared\env\Scripts\python.exe --output C:\Antigravity\AlazHarness\runtime\fresh-hyb004b --scenario after-reserve
python -B -m unittest discover -s tests -v
python -B scripts/ci_check.py
```

Inspection CLI'de exit0 yalnız tanı üretilebildiği anlamındadır, iş onarıldı demek
değildir; unverified exit2 döndürür. Native komut her defasında yeni output ister.
Mevcut hazırlanmış interpreter kullanılır, otomatik kurulum yapılmaz. Normal CI
native Gateway'i veya model sağlayıcısını başlatmaz.

## Sıradaki sınır — HYB-004C

Eksik rezervasyonu güvenilir owner/epoch bağı altında operatöre gösteren açık
uzlaştırma işlemi. Değişmez body fingerprint, scoped key/run/session ilişkisi ve
native transaction sınırları doğrulanmadan key silme veya yeniden gönderme yok.
Bilinmeyen gerçek dış etkiyi otomatik tekrar yürütmek hâlâ yasaktır. Bu paketin
readonly sonucu tek başına gelecekteki mutation işleminin yetkisi olmayacak.
Güç kaybı/WAL, çok-yazıcılı fencing, dosya dışında gerçek yan etkiler, OS sandbox,
tüm model çağrılarının para/token bütçesi, hafıza aktarımı, tam M1/M2 açık.

## Son yerel kabul

Son kod hashleriyle dört native senaryo yeniden çalıştırıldı: **4/4 PASS**;
her biri yeni owned kill/reopen, toplam4kill/8native nesil. Önceki sekiz native
koşu kendi eski hashleriyle korunur, bu son4 sayısına eklenmez. Tam standart
paket **506/506 PASS**, exit0/skip0/drift0. Bunun55i bağımsız targeted QA'dır;
55 ayrıca toplamın üzerine eklenmez.10 retained eski native kaydın son inspector
ile okunması ve4CLI çağrısı ayrı kapsamlardır, yeni Gateway çalışmaları değildir.
Sonuçlar: local-validation.json, final-native-suite.json ve cli-validation.json;
bağımsız kapsam evidence/hyb-004b-qa altında. Git/CI teslimi status.md'ye ayrıca
aynı commit ile kaydedilir. Bu dar readonly sözleşme kabulü orphan onarımı değildir.
