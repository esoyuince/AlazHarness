# D3B — Ağ ve dosya korumasının aynı Gateway üzerinde kabulü

İş: **D3B-COMBINED-DC64**, 18 Ekim 2026.
Dal: `alaz/d3b-combined-dc64`.
Çalışma ağacı: `C:\Antigravity\AlazHarness\scratch\worktrees\d3b-combined-dc64`.

## Karar ve kanıt kapsamı

**Aynı süreçte iki koruma ile native Gateway kabulü 4/4 PASS. Tam D3B değildir.**
Ağ ve dosya koruması için ayrı testlerden sonuç devralınmadı; aynı PID üzerindeki
uygulama, gerçek sabit Hermes Gateway, asıl aiohttp broker, kaynak baytları,
kanonik bütçe/istek kayıtları ve temiz kapanış birlikte ölçüldü.

Tam çevrimdışı regresyon ve son statik kontrolün durumu aşağıdaki teslim
bölümünde ayrıca kaydedilir. Native senaryoların PASS olması, bütün ürünün
veya sonraki gerçek model denemesinin kabulü değildir.

Kullanıcının WrongStack incelemesi sonrası verdiği devam kararıyla mevcut iki
Alaz koruması birleştirildi. WrongStack kaynak kodu veya üçüncü ajan motoru
bu teslimde eklenmedi; sözleşme/kimlik ve doğrulanmış sonuç ayrımı mevcut
uygulama üzerinde korundu. Sonuç-duyarlı tekrar tespiti, koşullu hafıza ve
bağımsız doğrulama izni uyarlamaları backlog olarak kalır.

## Birleştirilen geçmiş

- Araştırma + dosya koruması tarafı: `ab68dac5d9b9803719255810ef73f20ef6dd9e3d`.
- Ağ koruması tarafı: `7915c77c6cf0f48fcae6a13e08cd7fd997cda4f2`.
- Ortak ata: `2bffac9aaf482363d335bdbd3c76cc687be83533`.
- İki giriş commit'inin `alaz/local-ci` sonucu bu çalışmada **SUCCESS** gözlendi.

Ürün kaynakları arasında merge çatışması çıkmadı. Yalnız `docs/CI.md`,
`docs/BACKLOG.md` ve `status.md` kayıtları iki tarafın geçmişi korunarak
uzlaştırıldı. Kök `status.md` başlangıçta eski ağ dalıyla birebir aynıydı;
yeni güncel özet ve her iki günlük birleştirilerek kök ayna yenilendi.
Önceki çalışma ağaçları ve `main` değiştirilmedi.

## Uygulama

`combined_guard.py`, açık güvenilir operatör sözleşmesini doğrular. Sözleşme
sürüm, launchId, zorunlu iki katman, dosya politikası ve argv SHA-256 içerir.
Bilinmeyen alan, kapalı ağ, geniş dosya izni veya farklı komut reddedilir.

`run_combined_guard.py` kurulumu yeni tek iş parçacıklı çocuk süreçte yapar:

```text
güvenilir başlatıcı
  -> sözleşme ve komut eşleşmesi
  -> yeni user + network namespace
  -> yalnız özel loopback; capability kümelerini sıfırla; seccomp
  -> Landlock dosya politikası
  -> korunan dosyada açma reddini gözle
  -> yeni makbuzu yaz ve flush/fsync
  -> aynı PID ile hedefe exec
```

Sıra zorunludur: namespace kurulumu kendi `/proc` haritalarına geçici erişime
ihtiyaç duyar; Landlock bundan önce uygulanmaz. Bir katman kurulamazsa hedef
çalıştırılmaz. Tek katmana veya sınırsız çalışmaya geri dönüş yoktur.

**Komut özeti imzalı izin veya tek kullanımlık harcama yetkisi değildir.**
Sözleşme hâlâ güvenilir operatörün girdisidir; bir modelin aynı JSON'u üretmesi
ona yetki vermez. `launchId` kalıcı tekrar engelleme veya broker rezervasyonu
değildir. Üretim entegrasyonu ayrıca güvenilir sahip/kapalı izin yaşam döngüsü
ve yürütme noktası bağlantısını gerektirir. Başlatıcı makbuzu da tek başına
hedefin başarılı çalıştığını kanıtlamaz (`targetExecutionVerified:false`).

Mevcut `linux_netns.py` ve `credential_guard.py` kaynak baytları değiştirilmedi.
Aynı ortak launcher, daha önce ayrı kabul edilmiş iki bileşeni kullanır.

## Gerçek Gateway deneyi

`native_combined_gateway.py`, eski AF21 kabul işini kullanır. Yalnız testin
oluşturduğu broker bootstrap dosyası Gateway yazma alanından çıkarılır.
Gerçek broker ve programlanmış yerel HTTP sağlayıcı host ağında kalır.
Gateway aynı anda netns + Landlock altında çalışır. Güvenilir QA kontrolcüsü,
Gateway'in özel API'sine erişmek için host tarafından namespace'e girer;
bu kontrolcünün yetkisi sınırlanmış Gateway'in yetkisi olarak gösterilmez.

Dosya kuralları, önceki kabuldeki salt-okunur kaynak/yorumlayıcı köklerini,
seçilmiş sistem dosyalarını, yalnız kendi PID metadata kayıtlarını ve kendi
özel çalışma/soket dizinlerini kullanır. Tüm `/tmp`, `/etc` veya `/proc`
ağaçları açılmaz. Broker bootstrap dosyası grant'ların dışında kalır.

WSL v9fs kaynağını Landlock altında genişletmek yerine önceki
`source_files`/`copy_verified` yardımcılarıyla geçici native Linux kod kopyası
kullanılır. Her koşu öncesi/sonrası aynı **184** kaynak dosyası doğrulandı;
kopyalar deney sonunda kaldırıldı. Hazırlanmış Python/Node/Hermes ortamı
aynı kaldı; sistem paketleri veya kullanıcının kişisel profili değiştirilmedi.

| Senaryo | Fiziksel istek / gözlenen yanıt | Son durum | Tekrar davranışı |
|---|---:|---|---|
| Normal | 4 / 4 | completed; baseline ve candidate | Yeni rezervasyon yok; 200 |
| Toplam kaynak bütçesi sınırı | 3 / 3 | unknown; baseline korunur | Yeni rezervasyon yok; 202 |
| Candidate bağlantısı kesilir | 4 / 3 | unknown; baseline korunur | Yeni rezervasyon yok; 202 |
| İnceleme kararı geri çekilir | 3 / 3 | unknown; deneme sonucu yayımlanmaz | Candidate gönderilmez; tekrar 409 |

Her koşuda Gateway PID'si, iki-katman makbuzu ve canlı netns/capability
örnekleri eşleşti. Broker dosyası açma reddi gözlendi. Kanonik SQLite
bütünlüğü `ok`, istek özeti eşleşmeleri eksiksiz; Gateway/broker exit0,
Unix broker soketi kaldırılmış ve aktif istek0.

## Çekirdek ve başlangıç testleri

`tests/combined_guard_linux.py`, yalnız kendisine ait geçici dosyalar ve
host loopback dinleyicileri ile **24 kontrol + 5 başlangıç reddi** çalıştırdı.
Pozitif kontroller izinli dosya/SQLite yazımını, host sunucularının sınır dışında
çalışmasını ve özel namespace loopback'ini doğrular. Negatif kontroller gizli
dosya okuma/yazma, symlink/hardlink, önceden açık dosya/soket taşınması,
host IPv4/IPv6/ham libc bağlantısı, namespace'e geri giriş, descriptor alma ve
alt sürece miras alınan dosya/ağ reddini kapsar.

Yanlış argv özeti, kapalı ağ, ek yetki alanı, korunan dosyanın yazılabilir
alanda bulunması ve önceden sabit bağlantısı olan korunan dosya için hedef
hiç çalışmaz; başarı makbuzu oluşmaz. Son kernel kanıtı:
`evidence/d3b-combined-dc64/native-dual-initial.json`.

Bu kontroller standart unittest sayısına eklenmez. Yeni 18 çevrimdışı test
sözleşme doğrulaması, kurulum sırası, aynı PID, katman hatası ve geniş izin
reddini kontrol eder; kernel veya Gateway çalıştırmaz.

## Ölçülen açık: pathname Unix IPC

Test için dosya grant'larının dışında özel bir Unix soketi kuruldu. Sınırlanmış
çocuk, doğrudan host TCP'ye ulaşamadığı ve gizli dosyayı okuyamadığı hâlde bu
**yalnız bize ait test Unix soketine bağlanabildi**. Bu beklenen kapsam açığı
`ownedPathUnixSocketOutsideFileGrantsReachable:true` olarak açıkça kaydedildi.
Gerçek host servislerine deneme yapılmadı.

Landlock ABI3 dosya-açma sınırı, namespace dışındaki yol tabanlı IPC için
izinli uç listesi değildir. Broker gibi açıkça gerekli uçları koruyarak diğer
Unix/Windows-interop otoritelerinin görünürlüğünü ve erişimini sınırlamak
ayrı kabul işidir. Native deney PASS'i bu açığı kapatmaz.

## Tam D3B için kalanlar

1. Broker uç noktası dışında IPC erişimi; uygun mount/PID/host kimliği sınırı.
2. Gateway'in yazabildiği kanonik DB'den bağımsız, broker sahipliğinde bütçe ve
   tek-kullanımlık yürütme otoritesi. Mevcut ledger eşleşmesi düşman Gateway'e
   karşı kanıt değildir.
3. Başlatma sözleşmesinin üretim Gateway yolu ve güvenilir yetki verenle
   entegrasyonu; makbuzların modelin yazabildiği alandan bağımsız doğrulanması.
4. Gerçek sağlayıcı, fiyat/token sözleşmesi, Docker araç birleşimi ve ayrı
   görevlerde gerçek öğrenme ölçümü. Bu turda **gerçek model çağrısı0**.

Salt-okunur test sınırlarından tam kaynak/CPU/disk/IPC sandbox'ı veya ayrı host
kullanıcısı elde edildiği söylenmez. Model yanıtları programlanmıştır;
8/12 -> 12/12 puanı öğrenme veya maliyet kazancı değildir.

## Yeniden üretim

Aşağıdaki açık test komutları, hazır özel Linux ortamı ve sabit kaynaklar ister;
kişisel/üretim Gateway'i otomatik değiştirmez. Run id ve çıktı dosyası yeni
olmalıdır; kesintide aynı mutasyonu tekrar göndermeden önce makbuz okunur.

```text
wsl --exec python3 -B /mnt/c/Antigravity/AlazHarness/scratch/worktrees/d3b-combined-dc64/scripts/qa/native_combined_ext4.py --run-id new-unique-run-id --scenario normal
python -B -m unittest discover -s tests -v
python -B scripts/ci_check.py
```

Native kernel komutu Linux üzerinde `tests/combined_guard_linux.py --output`
ile yeni `evidence/d3b-combined-dc64/*.json` dosyasına yazar. Diğer Gateway
senaryoları: `budget-limit`, `candidate-disconnect`, `review-revoked`.

## Kernel başvuru kaynakları

- Linux 6.6 Landlock: https://docs.kernel.org/6.6/userspace-api/landlock.html
- Linux 6.6 seccomp: https://www.kernel.org/doc/html/v6.6/userspace-api/seccomp_filter.html

Bu kaynaklar genel API davranışını açıklar; yerel kabul sonuçları yukarıdaki
kaynak ve senaryo makbuzlarından gelir. Ana iki bileşenin önceki belgeleri:
[D3B1 ağ](D3B1-NETWORK-NAMESPACE.md), [dosya](D3B-CREDENTIAL-STARTUP.md).

## Teslim durumu

Native Gateway **4/4 PASS**, kernel **24 kontrol + 5 başlangıç reddi PASS**.
Tam çevrimdışı regresyon **1.938/1.938 PASS**, exit0, atlanan test yok.
**280** kaynak/test/konfigürasyon dosyası test boyunca aynı kaldı.
Yeni18 ve ağ dalından birleştirilen17 test toplamın içinde bir kez sayıldı.
Statik kontrol **PASS**,1938 keşif; 1366 kök dosya ve 2 kaynak gitlink.
Native testler standart sayıya eklenmedi. Dört deneyden sonra çalışan
Gateway/broker0; 12 üretilmiş test kimlik bilgisi için 23 kamuya açık dosyada
eşleşme bulunmadı. Bu genel sır taraması veya tam sandbox sertifikası değildir.
Kaynak, günlük ve senaryo özetleri `evidence/d3b-combined-dc64/` altında.
Git commit/push/CI ayrıca doğrulanır. `main`e birleştirme yapılmadı.

### Exact kod yayını ve CI — 2026-10-18T22:01:41.616485+03:00

Kod merge commit: `9a87838ebf382fe8b71c299a5867c479383fc5b6`, origin dalı `alaz/d3b-combined-dc64`.
GitHub `alaz/local-ci` **SUCCESS**, durum kimliği56641376354,
2026-10-18T18:59:43Z. API uzak test sayısı bildirmez; yerel1938/1938 ve
native4/4 bağımsız makbuzlardır. 280 kaynak Git blobu test edilen baytlarla
eşleşti; GitHub rapor/full-standard blobları da doğrulandı.
Bu takip yalnız rapor/status/yayın kanıtıdır; kod ve testler değişmedi.
Son belge commitinin CI durumu ayrı kontrol edilir. Ana dal değişmedi.
