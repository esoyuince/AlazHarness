# D3B-JOINT-18D3 — Aynı Gateway sürecinde ağ ve dosya koruması

İş başlangıcı: 18 Ekim 2026. Dal: `alaz/d3b-joint-18d3`.
Çalışma ağacı: `scratch/worktrees/d3b-joint-18d3`.
Araştırma/credential tabanı: `ab68dac5d9b9803719255810ef73f20ef6dd9e3d`.
Ağ kaynağı: `7915c77c6cf0f48fcae6a13e08cd7fd997cda4f2`.
Birleştirme: `6c679bd3da66ad407f342259a5fdd140062c6853` (ana dala değil).

## Amaç ve kapsam

Ayrı ayrı kabul edilmiş ağ namespace/seccomp ve Landlock dosya korumasını
aynı gerçek Hermes Gateway sürecinde kullanmak; bir katmanı açınca diğerini
gevşetmeden mevcut Dream zincirini ve olumsuz durumları yeniden sınamak.
Bu belge birleştirme tasarımını ve ölçülebilen kabul sınırını anlatır.
Nihai test/CI sonuçları aşağıdaki tarihli kabul bölümünde ayrıca kaydedilir.

WrongStack incelemesi bu dalda korunur. Bağımsız yetki sahibi, sonuç sahipliği
ve doğrulama ayrımına uyulur; WrongStack kodu ürün içine kopyalanmamıştır.
Üçüncü ajan motoru, yeni hafıza deposu veya otomatik zamanlayıcı eklenmez.
Sonuç-duyarlı tekrar dedektörü ayrı sonraki davranış adayıdır.

## Değişmeyen güvenlik bileşenleri

`linux_netns.py` ve `run_in_network_namespace.py` ağ dalının kabul edilmiş
baytlarıdır. `credential_guard.py` ile `run_credential_guard.py` credential
fix dalındaki baytları korur. Üretim broker, bütçe, Dream ve yerel kaynaklı
Hermes modülleri değiştirilmez. Belge çatışmalarında iki dalın ek kayıtları
korunmuştur; eski ağ durumu tarihsel olarak etiketlenmiştir.

Yeni `scripts/run_joint_boundary.py` yalnız açık başlatma komutunu birleştirir:

```text
network namespace / zero capabilities / seccomp
    -> Landlock dosya koruması
    -> açıkça verilen program
```

Ağ kurulumu taze, henüz no_new_privs uygulanmamış bir süreç ister; bu yüzden
sıra sabittir. Her katman `exec` ile aynı PID üzerinde devam eder. Bir katman
başarısızsa hedefe doğrudan geçiş veya korumasız tekrar yoktur. Hedef program
salt-okunur kökten, makbuzlar yeni ve izinli yazma alanından gelmelidir.

## Gerçek kabul düzeneği

`verify_joint_gateway.py`, mevcut `native_d2b2_full_gateway.py` kabul akışını
kullanır. Kaynak/test simülasyonu ile gerçek sistem sınırı birbirine karıştırılmaz:

- Hermes kaynağı sabit `eb75627faf532fa6ffbdae59a0d14b0b385fc780` commit'idir.
- Gateway gerçek ayrı süreçte, orijinal aiohttp broker başka host sürecindedir.
- HTTP sağlayıcısı yalnız test kontrolcüsünün programlanmış localhost sunucusudur.
- Gateway'in yerel API'si için güvenilir test kontrolcüsü `nsenter` ile içeri
  girer. Gateway'in kendisi bu namespace değiştirme işlemini yapamaz.
- İşletim sistemi ve kullanıcı profili değiştirilmez. Var olan özel hazırlanmış
  Python/Node ortamı kullanılır; global paket kurulumu yoktur.

WSL'nin Windows kaynak mount'u yerine yalnız kodun SHA-256 ile doğrulanmış
geçici Linux kopyası çalıştırılır. Kaynak kopyalama, iki mevcut snapshot
fonksiyonunu tekrar kullanır. API anahtarları, runtime ve kişisel profiller
kopyanın içinde değildir. Kod kopyası ölçümden sonra kaldırılır.

Testin kendi broker bootstrap dosyası Gateway'in yazma/okuma alanının dışına
taşınır. Dar self-process metadata seçeneği ve kısa özel XDG socket dizini,
önceki credential kabulündeki aynı sınırlarla korunur. `/proc`, `/tmp`, `/etc`
ağaçları topluca açılmaz. `/usr` ve hazırlanmış çalışma kitaplıkları mevcut
salt-okunur kapsamlarıyla kullanılır; bunun tüm dosya metadata'sını gizlediği
veya kötü niyetli tüm host servislerine erişimi kestiği iddia edilmez.

### Aynı süreçte 15 başlangıç kontrolü

Her Gateway koşusundan önce `joint_boundary_probe.py` iki koruma etkin durumdayken
ayrı network namespace, no_new_privs, seccomp, sıfır capability, korunan dosya
ve sembolik bağlantı reddi, kendi environ dosyasının reddi, Python ve ham libc
ile host TCP reddi, namespace yeniden-giriş reddi, özel loopback çalışması
ve yeni exec alt sürecindeki ağ/dosya mirasını kontrol eder.

Bunlar 15 kontrol türüdür; dört koşuda tekrarlanmaları 60 benzersiz test veya
60 model deneyi değildir. Çevrimdışı unittest toplamına eklenmezler.
Korunan dosya içeriği okunmaz; yalnız açma girişiminin reddi gözlenir.

### Dört mevcut Dream senaryosu

| Senaryo | Beklenen fiziksel istek/yanıt | Beklenen deneme sonucu |
|---|---:|---|
| normal | 4 / 4 | completed; baseline ve candidate |
| budget-limit | 3 / 3 | unknown; yalnız baseline |
| candidate-disconnect | 4 / 3 | unknown; yalnız baseline |
| review-revoked | 3 / 3 | unknown; candidate gönderilmez |

Her satır ayrıca sıfır yeni tekrar rezervasyonu, kaynak baytlarının değişmemesi,
DB bütünlüğü, istek digest/egress/rezervasyon eşleşmesi ve temiz Gateway/broker
kapanışını gerektirir. Belirsiz olumsuz sonuç, başarısız kabul testi demek değildir:
başarılı çift uydurmadan unknown bırakmak beklenen davranıştır.

## Korunan ilk başarısız kayıt

`18d3-normal-pilot` test adaptöründe var olmayan `base_url` alanını okuduğu için
Gateway başlamadan başarısız oldu. Gerçek `BrokerConfig` alanı
`upstream_base_url`; gizli test değerini denetleyen alan da `upstream_bearer`dır.
Yalnız adaptör eşlemesi düzeltildi. Başarısız makbuz ve ilk kaynak manifesti
korundu; ürün koruması gevşetilmedi, eski deneme geriye dönük PASS sayılmadı.

## Hâlâ açık: tam D3B ve gerçek öğrenme

Bu birleşim doğrudan ağ ve korunan dosya açma sınırını birlikte gösterir.
**Tam D3B kabulü değildir.** Ayrı host UID, bütün pathname Unix hizmetlerinin
allowlist'i, kapsamlı PID/mount/metadata sınırı henüz sağlanmış sayılmaz.
Seccomp mevcut kısıtlı syscall listesi, tam sistem çağrısı allowlist'i değildir.

Broker hâlâ Gateway'in erişebildiği mevcut oturum/rezervasyon verilerine ve
D3A güven modeline dayanır. Bu otoritenin kötü niyetli Gateway yazımlarından
bağımsız korunması, ayrı güvenilir bütçe/izin sahibi ve tek tüketim sözleşmesi
sonraki kritik iştir. Başlangıç makbuzları tek başına kötü niyetli süreçten
bağımsız kriptografik attestation değildir.

Gerçek ücretli model, uzaktan HTTPS/tarife kabulü, Docker araç çalışması,
bağımsız beceri transferi ve otomatik hafıza güncellemesi çalıştırılmadı.
Programlanmış 8/12 -> 12/12 skorları gerçek öğrenme kanıtı değildir.

## Yeniden üretim

Önceki görevde hazırlanmış Linux ortamı ve aynı kaynak pini gerekir:

```text
python3 -B scripts/qa/verify_joint_gateway.py --run-id <yeni-kimlik> --scenario normal
python3 -B scripts/qa/verify_joint_gateway.py --run-id <yeni-kimlik> --scenario budget-limit
python3 -B scripts/qa/verify_joint_gateway.py --run-id <yeni-kimlik> --scenario candidate-disconnect
python3 -B scripts/qa/verify_joint_gateway.py --run-id <yeni-kimlik> --scenario review-revoked
python -B -m unittest discover -s tests -v
python -B scripts/ci_check.py
```

Özel profiller hazırlanmış Linux `source-workspace/runtime/joint-18d3-*` altında,
sır içermeyen makbuzlar `evidence/d3b-joint-18d3/` altında tutulur. Mevcut kimlik
üzerine yazma veya etkisi bilinmeyen işi otomatik tekrarlama yoktur.

## Teknik kaynaklar

Linux 6.6 Landlock: https://docs.kernel.org/6.6/userspace-api/landlock.html
Seccomp filtre sözleşmesi: https://docs.kernel.org/userspace-api/seccomp_filter.html
Yerel kaynak/önceki kabul: `docs/D3B1-NETWORK-NAMESPACE.md`,
`docs/D3B-CREDENTIAL-STARTUP.md`, `docs/WRONGSTACK-REVIEW.md`.

## Ölçülen yerel kabul — 2026-10-18T21:53:55.224973+03:00

**Ortak Gateway4/4 PASS.** Normal4/4, bütçe3/3, kopma4/3, inceleme
geri çekme3/3 fiziksel istek/yanıt kaydedildi. Normal iki kol tamamlandı;
bütçe/kopma bir kolu korudu. Geri çekmede sonuç API’si hiçbir kolu güncel
kabul olarak yayımlamadı ve tekrar409 döndü; candidate isteği gönderilmedi.
Her koşuda aynı PID üzerinde15 kontrol PASS, broker/Gateway exit0,
soket kaldırılmış ve aktif istek0. Dört koşunun183-kaynak manifesti aynı.

**Tam1940/1940 PASS,1940 benzersiz kimlik, atlanan0;278 kaynak hash eşit.**
Önceki credential1903 + ağ17 + yeni20; ayrı native kontroller toplamda değil.
Aynı20 yeni test Linux’ta ayrıca PASS. Root static PASS:1940 keşif,
1394 izlenen metin,2 gitlink; keşif ikinci runtime testi değildir.

Beş özel profil ve15 bilinen test kimlik bilgisi için19 yayımlanabilir dosya
taramasında eşleşme yok. Bu profillere ait canlı Gateway görülmedi;
özel teşhis profilleri saklandı. Genel sır veya tam host güvenlik denetimi değil.
Kod yayını ve exact-SHA CI bundan sonraki ayrı teslim kaydıdır.

## Exact kod yayını ve CI — 2026-10-18T21:58:04.701480+03:00

Kod `94ad295ec6bf34c18e00c167b31e39f3be612335` commit’iyle
`alaz/d3b-joint-18d3` dalına gönderildi. GitHub `alaz/local-ci`
**SUCCESS**: status56641282756, güncelleme2026-10-18T18:56:44Z.
GitHub durum API’si uzak test adedini vermiyor; yerel1940 benzersiz test
ve dört ortak Gateway ölçümü kendi makbuzlarıyla ayrıca doğrulandı.

Yayımlanan278 kaynak/test/konfigürasyon Git blobu test edilen baytlarla aynı.
Diğer araştırma/ağ/credential dallarının HEAD’leri ve main b8ff44f korundu.
Kök status başka çalışma tarafından eşzamanlı güncellendi; bu görev oraya
yazmadı. Aktif devam adresi bu ortak dalın izlenen status.md dosyasıdır.
Bu son takip yalnız belge/status/CI/byte-proof kaydı; kod ve test değişmez.
Belge commit’inin kendi CI’si yayın sonrasında ayrıca kontrol edilir.
