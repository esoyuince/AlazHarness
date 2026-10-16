# AlazHarness — status

Son güncelleme: 16 Ekim 2026. Canlı dal/HEAD/CI doğrulanmadan eski sonuç aktarılmaz.

## Güncel nokta

HYB-005D1 Linux araç-süreci prototipi yerelde doğrulandı; Git/CI yayını IN PROGRESS.
Tam HYB-005D, gerçek Hermes bağlama ve Windows ağ kabulü AÇIK.
Aktif dal: alaz/hyb-005d-isolation-247a.
Aktif çalışma ağacı: C:\Antigravity\AlazHarness\scratch\worktrees\main-6f88.
Başlangıç HEAD fadb48acf6ada154497ec7f88b612b0e0fbb54e0; temiz, exact CI success.
247a bu turun entegrasyon/yayın sahibidir. Önceki HYB005C tam kaydı
 docs/history/2026-10-16-STATUS-BEFORE-HYB005D-247a.md altında korunur.
Kök eski korunmuş dalda; yalnız status.md erişim kopyası kontrollü eşitlenir.

## İlk adım ve sınırlar

Mevcut OS/çalıştırma araçları ve upstream sandbox parçaları salt okunur inceleniyor.
Uygulanmamış ağ ayarına veya Python audit hookuna sandbox kabulü yazılmaz.
Kişisel profil/sırlar, host firewall, servis veya kurulum değişikliği yok.
Test için yalnız yeni proje alanı ve sentetik sırlar; ücretli/model çağrısı yok.
Tek canonical ledger/runtime korundu. Linux araç süreci6son-kod Docker
senaryosunda doğrulandı; bütün harness izolasyonu veya M1/M2 kabulü değildir.

## Başlangıç kaydı

HYB005C964 PASS eski kapsamdır; bu turun sonucu değil. Başlangıç custody
runtime/hyb005d-247a/start.json. Main ve upstream pinler değiştirilmedi.

### 2026-10-16T21:17:35.547457+03:00 — HYB005D QA4023 Windows seçeneği

Canlı247a entegrasyon işi başladı; QA4023 ikinci ürün yazıcısı/branch olmayacak.
Yalnız yeni scripts/qa/*appcontainer* dosyaları ve QA4023 kanıtları: mevcut
Windows/.NET compiler ile sıfır network capability AppContainer fizibilitesi.
Sentetik sır/loopback sentinel, parent token/exit teyidi, yalnız yeni test alanı
ACL ve geçici adı eşsiz AppContainer profili; var olan profile/firewall/exemption
dokunulmaz. Hermes/Gateway, gerçek anahtar/model, otomatik scheduler yok.
Bu test gelecekteki zorunlu sınır için aday kanıtıdır, ürün izolasyonu kabulü değil.
Başlangıç NOT RUN. Ürün/CI yayın sahibi247a kalır.

### 2026-10-16T21:26:37.995646+03:00 — HYB005D QA4023 ilk native sınır

Gerçek Windows AppContainer token pre-resume doğrulandı:capabilities0/LowIL;
sentetik secret env yok, private read/write ve parent VM_READ ERROR_ACCESS_DENIED5;
izinli read başarılı/write ret.192.0.2.1 TCP WSAEACCES10013. Ancak IPv4/IPv6
loopback1500ms timeout10060, sentinel yalnız baseline1paket: explicit denial
şartı PASS değil. Bütün paket bu yüzden FAIL kalır; gözlemi başarıya çevirmeyiz.
SetLowLabel5/eksik LOCALAPPDATA203 önceki hazırlık hataları ayrı korundu;
geçici test profilleri silindi. Sıradaki QA yalnız lifecycle timeout testini
network assertinden önce ölçmek; ürün/Gateway/para/ağ ayarı değişmeyecek.

### 2026-10-16T21:29:41.767967+03:00 — HYB005D QA4023 son-kaynak gözlemleri

Aynı son C# ve launcher hashleriyle2native tekrar:private read/write/parent
VM_READ ret5, sentetik secret env yok, allowed read0/write5, TESTNET10013.
Her tekrarda ayrı timeout child job ile exit91, üç süreç reaped. Loopback
v4/v6 timeout10060 kaldı; sentinel ek mesaj0. İki strict native makbuz FAIL,
kanıtları değiştirilmedi. Beş denemede oluşan5benzersiz profil S_OK silindi,
folder kalmadığı ayrıca görüldü.33offline validator/env testi PASS; bunlar
Windows çalışması veya ürün kabulü değil. Rapor docs/research/HYB-005D-QA4023-WINDOWS.md;
evidence/hyb-005d-qa4023. Ürün/Gateway entegrasyonu ve tam izolasyon AÇIK.

### 2026-10-16T21:31:40.393850+03:00 — HYB005D QA4023 seçilmiş teslim

Windows QA kaynak/runner/33offline test/rapor/kanıtları ayrı adlarla stage edildi;
ürün isolated_tool.py ve diğer yazar dosyaları değişmedi/stage edilmedi. Hijyen
kontrolü geçti; full suite sonucu bundan çıkarılmaz. Native2final koşu v4/v6
explicit denial eksikliğiyle FAIL kalır; dosya/process/deadline bulguları ayrı.
Yeni5test profilinin klasörlerinin de silindiği doğrulandı,32kök dosya korundu.
Ürün247a Linux izolasyon uygulaması ve Git/CI teslimi sürüyor; QA ikinci
container/native batch başlatmaz. Ayrı Windows bulgusu tüm platform kabulü değildir.

### 2026-10-16T21:34:33.146739+03:00 — HYB005D Linux araç sınırı adayı

Tek kullanımlık Docker adapteri isolated_tool.py ve53offline ret testi eklendi;53/53 PASS.
Mevcut Docker29.8.1 ve önceden kurulu sha256:64af3819... imajıyla alaz-server
üstünde6 gerçek konteyner senaryosu başlatılıyor. Kaynaklar ayrı /tmp/alaz-hyb005d-247a-code-v1
altında hashle aynı; probe output /tmp/alaz-hyb005d-247a-probe-v1. Makbuz
ef49d31b-81dd-482f-b61e-80c315a28a24 lane247a. Kurulum/pull/firewall/daemon değişimi yok.
Bu yalnız araç alt süreç prototipidir; gerçek Hermes dispatch izolasyonu veya tüm
provider credential/egress kabulü DEĞİL. Sonuç alınmadan native PASS yazılmaz.

### 2026-10-16T21:35:49.248933+03:00 — HYB005D QA4023 standart tur kapsamı

1050/1050 unittest exit0/skip0. Fakat koşu sırasında scripts/run_isolated_tool_probe.py
eklendi; hiçbir eski source değişmese de ölçülen set farklı olduğundan snapshot
kabulü NOT_ACCEPTED kaydedildi. evidence/hyb-005d-qa4023/full-standard.json/.txt.
Native Windows strict FAIL ayrı. Final birleşik kaynakla tam suite yeniden
koşulmadan bu1050 eski koşusu exact final CI yerine kullanılamaz. QA ürün
yaması yapmadı; yeni probe primary247a çalışmasıdır.

### 2026-10-16T21:37:36.970030+03:00 — ilk Docker deneyi ve lifecycle düzeltmesi

6gerçek Docker araç senaryosu PASS; ancak iki ek sentetik start/attach-failure
regresyonu10PASS/2FAIL buldu. İlk çıktı/evidence korundu. Ürün: hiç başlamayan
konteyner0exit varsayımı başarı sayılmaz; attach/engine çelişkisi UNKNOWN. Aynı
testler dahil65/65 hedefli PASS. Final ürünle Docker6senaryo tekrar koşulacak;
ilk6başarı son sürüme aktarılmaz. Tam Hermes entegrasyonu hâlâ NOT RUN.

### 2026-10-16T21:43:25.277381+03:00 — HYB005D1 yerel teslim ve QA bütünleşmesi

Son Linux ürün88fd6d1... ile6/6 gerçek Docker kontrolü PASS; dört terminal durum
ve iki dosya/ağ/sır alt-süreç kontrolü. Engine inspect prestart koşulları ve
bitişte exactID stop/remove makbuzları eşleşti, altı konteyner kalmadı. Ağ
none; UID65534/caps0/NoNewPrivs/seccomp2; canary/proxy/Docker socket erişimi yok.
Read-only capsule/root, scratch çalışır; cgroup128MiB/pids32/CPU0.5 gözlendi.
İki simulated-start false-success hatası değişmeyen testlerle düzeltildi.
Final65 hedefli ve tam1062/1062 PASS exit0/skip0/drift0. 65+33 yeni test1062içinde.

Bağımsız QA4023 Windows kaynak/kanıt/testleri okundu; aynı dalda korunarak
bütünleştiriliyor. İki native AppContainer sonucu strict loopback10060 nedeniyle
FAIL kalır; sır/file/parent-memory/timeout olumlu alt kapsam ayrı.33offline
kontrat testini Windows kabulü sayma. QA1062 ikinci tam tur PASS; eski1050set-
değişimi makbuzu kabul dışı. Linux'u QA4023 bağımsız incelemiş diye sunma.

Dosyalar:packages/claw-hermes/isolated_tool.py, scripts/run_isolated_tool_probe.py;
rapor docs/HYB-005D-TOOL-ISOLATION.md; kanıt evidence/hyb-005d ve QA4023 dizini.
Mevcut Gateway, ledger, native read_file ve kaynak pinleri değişmedi. Linux
prototip henüz gerçek Hermes dispatch'e bağlı değil. Next HYB-005D2: bütçe/izin
kontrolünden sonra gerçek tool bağlama, iptal aktarımı ve host-fallback yokluğu;
ardından model-provider credential/egress sınırı. Parent hard-crash cleanup,
Windows native ağ, gerçek tarife/model ve M1/M2 AÇIK. Kurulum/ücretli çağrı0.
Main değiştirilmedi. Commit/push/aynı-SHA CI henüz başarılı sayılmaz.

### 2026-10-16T21:44:58.071556+03:00 — HYB005D QA4023 final teyit

Sabit son kaynakla1062/1062standart PASS,exit0/skip0;184code/config dosyası
değişmedi/yeni0. Önceki1050tur source-set eklemesi nedeniyle NOT_ACCEPTED
korundu.33Windows offline test bu1062içinde. Linux final6native araç koşusu
serverdaki gerçek kaynak/prestart/exit/capsule kayıtlarıyla readonly6/6
CORROBORATED; yeni container0. Modül88fd6d1a/probe7bd87920, kanıt
evidence/hyb-005d-qa4023/linux-final-corroboration.json. Bu Windows2strict
FAILini veya tam Hermes/provider izolasyonunu kapatmaz. QA dosyaları seçilerek
stage edildi, ürün/runtime/main değişmedi; tek Git yayın sahibi247a kalır.
