# P2 / R168A1 — kurulu servisin görev açmadan yaşam döngüsü

**Kaynak yayını öncesi durum: 28 Ekim 2026, 15:45 UTC. R168A1 IN PROGRESS;
son QA04 baytlarıyla görev açmadan normal servis yaşam döngüsü ve ayrı
kayıp close yanıtı kabulü PASS.** Aynı R167 kurulumunda `normal-04` ile
gerçek CLI start/status READY ve close/son status CLOSED görüldü.
Ayrı `lostreply-02`, tek gönderilen close
yanıtı düşürüldükten sonra aynı özgün isteğin salt okunur status ile CLOSED
olarak uzlaştırılmasını kabul etti. İkisinde de özgün child ve volume
kapanış sırası tamamlandı. İlk gerçek deneme
bootstrap ön kontrolünde reddedilmişti; ikinci denemenin controller/broker/
worker sahipliği UNKNOWN olarak korunuyor. Yeni normal kabul bu eski
kaydı kapatmıyor. Önceki QA03 kabulleri tarihsel olarak korunuyor. İlk
source stage, Git add sonrası EOF kontrolünde UNKNOWN kaldı; commit
oluşmadı. R168 kaynak yayını **PENDING**, exact-commit tam CI **NOT RUN**.

P1'in önceki kabulü DONE olarak korunur. P2 IN PROGRESS; P3–P5, tam M1 ve
production kabulü OPEN. Güncel çalışma kaydı [status.md](../status.md), ürün
kabul koşulları [MVP-v0.1](MVP-v0.1.md), paket sırası
[ürün yol haritasıdır](PRODUCT-ROADMAP.md). Bu rapor sonraki bir denemenin
başarısını veya eski UNKNOWN sahibin kapanışını peşinen kaydetmez.

## 1. Sabit kapsam ve başlangıç

R168, R167'nin yayımlanmış
`9440a2251d26db88b5f08a0e0292e73f4fbb6e57` tabanından
`alaz/p2-service-lifecycle-r168a1` dalında ilerliyor. R167 kaynak yayını,
exact-commit CI ve main kapanışı terminal seal ile tamamlandı; bu önceki
kapanış gerçek servis kabulü değildi. Önceki durum
[parent arşivinde](status-history/r168-parent.md), kurulum kapsamı
[R167 raporunda](P2-SERVICE-INSTALL-R167A1-REPORT.md) korunur.

Hedef aynı `/opt/alaz-r167a1` kurulumudur: **878 kaynak dosyası ve 1.162
bağımlılık dosyası**, sabit Python 3.12.3 ve Node 24.22.1. Bu çalışma için
kurulu ürün baytları veya R167 kurulum makbuzu değiştirilmedi. Başlangıçta
20 repository, 33 korunan kök dosyası ve R167'nin 22 yayımlanmış dosyası
bağlandı. Bu sayımlar ortam korumasıdır; ürün veya servis kabulü sayısı
değildir.

Amaç aynı özgün `ServiceVolumeSupervisor`, sabit ürün çocuğu, gerçek Unix
kontrol sunucusu ve Node CLI üzerinden **start → READY → status → close →
CLOSED** akışını kabul etmektir. Gerçek native seed, yeni supervised ext4
profili içinde hazırlanır; başka profilden veritabanı veya kimlik taşınmaz.
Görev yürütme ve model çağrısı bu kapsamda **0** olarak tutulur. Sağlayıcı,
araç görevi, restart ve günlük kullanım kabulü ayrı kapılardır.

## 2. Kaynak ve fixture sonuçları

Bootstrap gözlemi, görev açmayan ping broker, host koşucusu, lifecycle
controller ve servis seed'i için ayrı QA kodu ve odaklı testler hazırlandı.
Bu testlerin PASS sonucu gerçek kurulu servisin READY veya CLOSED durumuna
ulaştığını göstermez.

| Kayıt | RUN | PASS | SKIP | FAIL / ERROR | Sonuç ve kapsam |
|---|---:|---:|---:|---:|---|
| Linux `focus-linux-03` | 124 | 124 | 0 | 0 / 0 | PASS; tam log ve sabit girdi hashleri yerel olarak doğrulandı. |
| Windows `focus-windows-01` | 121 | 70 | 43 | 2 / 6 | FAIL olarak korunuyor. |
| Windows `focus-windows-02` | 121 | 78 | 43 | 0 / 0 | Test fixture'larının platform uyarlaması sonrası yeni koşu PASS. |
| Windows `focus-windows-03`, actual native026 | 124 | 81 | 43 | 0 / 0 | PASS; 93.636 baytlık sonuç makbuzu ve 22.716 baytlık tam log yerel olarak hashleriyle doğrulandı. |
| Linux `focus-linux-04` | 136 | 136 | 0 | 0 / 0 | PASS; önceki QA03 baytlarına ait tarihsel seçim. |
| Windows `focus-windows-04` | 136 | 93 | 43 | 0 / 0 | PASS; önceki QA03 baytlarına ait tarihsel seçim. |
| Linux `focus-linux-05` | 136 | 136 | 0 | 0 / 0 | PASS; son QA04 baytları, tam log/makbuz eşleşiyor. |
| Windows `focus-windows-05` | 136 | 93 | 43 | 0 / 0 | PASS; son QA04 baytları, tam log/makbuz eşleşiyor. |

Windows SKIP kayıtları açık platform koşullarına bağlıdır; çalışmış test
olarak sayılmaz. İlk FAIL geriye dönük PASS yapılmadı. Son Linux05 ve
Windows05 koşularının **465 girdi hash'i, 136 seçilen test kimliği ve 136
yürütülen test kimliği birebir aynı**. Önceki Linux03/Windows03'ün 124
testlik ve Linux04/Windows04'ün 136 testlik kayıtları ayrı korunur;
eski kaynak baytlarının sonucu QA04 sonucu olarak yeniden etiketlenmez.
136 odaklı testin PASS olması tam source
CI'nin çalıştığı anlamına gelmez. Native044'ün ayrı güncel kaynak keşfi
**4.842 test** kaydetti; bu discovery işleminde test çalıştırılmadı.

## 3. Gerçek denemeler ve korunmuş sonuçlar

| Deneme / gözlem | Gerçek sonuç | Kabul edilen sınır |
|---|---|---|
| `normal-01`, native019 | REFUSED / NOT_ACCEPTED | OS bootstrap ön kontrolü, kernel ve servis etkilerinden önce reddetti. |
| Beş başlangıç bağlamı, native021 | Salt okunur tanı | Gözlenen fark yalnız `pwd` builtin modülünün bağlama göre yüklenmesiydi; v2 sözleşmesi gerçek bağlamları ayrı bağladı. |
| `normal-02`, native028 | UNKNOWN / `ROOT_OUTCOME_UNKNOWN` | Gerçek volume/worker ve native seed aşamasına ulaşıldı; servis yaşam döngüsü kabul edilmedi. |
| `normal-02` seed alt süreci | PASS / `SERVICE_SEED_CREATED`, exit 0 | Üç fiziksel veritabanı bağlantısı kapandı; consumer ayrıldı, seed'in profile lease'i normal bırakıldı. |
| `custody-readonly-01` | OBSERVED | Özgün üç süreç kimliği ve kısmi kaynaklar korundu; kurulu 878 kaynak ve 1.162 bağımlılık yeniden doğrulandı. |
| `custody-and-separation-02` | OBSERVED | Aynı üç süreç ve tutulan kaynaklar gözlem aralığında değişmedi; yeni denemeye ayrılan beş kök gözlem öncesinde ve sonrasında yoktu. |
| QA03 / `normal-03`, native040 | PASS / `REAL_SERVICE_LIFECYCLE_CLOSED` | Ayrı yeni owner ve imajda gerçek start/READY/status/close/CLOSED, broker ping ve normal kapanış kabul edildi. |
| `normal-03` primary makbuz geri okuması, native041 | MATCH | 392.108 baytlık gerçek sonuç dosyası, native çıktısından alınan yerel kopyayla aynı hashte. |
| `lostreply-01`, native043 | PASS / `REAL_SERVICE_LIFECYCLE_CLOSED` | Gerçek kanalda tek close yanıtı kontrollü düşürüldü; aynı özgün istek status ile CLOSED gözlendi, close tekrarlanmadı. |
| `lostreply-01` primary makbuz geri okuması, native044 | MATCH | 388.669 baytlık gerçek sonuç dosyası, native çıktısından alınan kopyayla aynı hashte. |
| İki kabul sonrası `custody-after-acceptances-03`, native046 | OBSERVED | Eski `normal-02` controller/broker/worker kimlikleri ve tutulan kaynaklar aynı; özgün sonuç hâlâ UNKNOWN. |
| QA04 / `normal-04`, native069; primary geri okuma native070 | PASS / MATCH | Son QA04 baytlarıyla ayrı yeni owner ve imajda normal lifecycle kapandı; 392.242 baytlık gerçek makbuz doğrulandı. |
| QA04 / `lostreply-02`, native072; primary geri okuma native073 | PASS / MATCH | Son QA04 baytlarıyla ayrı tek close yanıtı düşürüldü; aynı request/owner CLOSED, close tekrarı yok; 388.720 baytlık makbuz doğrulandı. |
| QA04 kabulleri sonrası `custody-after-qa04-04`, native074 | OBSERVED | Eski üç süreç kimliği ve tutulan kaynaklar gözlem aralığında aynı; `normal-02` UNKNOWN olarak kaldı. |

### `normal-01`: başlangıç bağlamı uyuşmazlığı

Controller `QUALIFY_ACTUAL_OS_BOOTSTRAP` aşamasında
`qa_bootstrap_refused` nedeniyle terminal REFUSED verdi. Broker, seed veya
ürün servisi başlatılmadı; bu denemenin kernel yaşam döngüsü etkileri
başlamadı. Sonraki salt okunur tanı bu sınırı doğruladı.

Ürünün gerçek `-I -B` OS başlangıcı, R167'nin `-I -S -B` import kabulünden
ayrı incelendi. Beş gerçek actor/environment/cwd bağlamının gözlemi,
`HOME=/` içeren bağlamlarda `pwd` builtin modülünün yüklenmediğini gösterdi.
V2 düzeltmesi her bağlamın exact başlangıç kümesini bağlar; genel bir modül
istisnası eklemez. Kaynak incelemesi ve odaklı testleri PASS oldu; eski
sözleşme ve reddedilen deneme korundu.

Bu bootstrap kontrolü başlangıçtan sonra gözlenen modül kökenlerini,
kaynak/cache baytlarını ve güvenilir dosya kimliklerini nitelendirir.
Python açılırken daha önce gerçekleşmiş tüm etkileri gözlediği veya
yüklenmiş bütün code object'lerini kanıtladığı iddia edilmez.

### `normal-02`: seed başarılı, özgün lifecycle UNKNOWN

Gerçek seed, özgün worker'ın supervised ext4 profili içinde sıradan gateway
kullanıcısıyla tamamlandı. Typed servis başlangıç kaydı profile lease hâlâ
tutulurken üretildi. Seed makbuzu `ownerState=CLOSED`,
`consumerState=DETACHED`, üç fiziksel bağlantı için kapalı durum, sıfır
bekleyen async iş/thread ve normal loop kapanışı kaydediyor. Görev, listener
ve gerçek model çağrısı açılmadı.

Seed stderr'inde üç native SQLite uyarısı bulundu. Kurulu native guard,
`state.db`, `runs_idempotency.db` ve `response_store.db` için WAL yerine
**DELETE** journal mode seçti; handoff bu gerçek modu taşıdı. Seed exit 0
ve PASS olmasına rağmen o denemenin QA controller'ı boş stderr şartını
sağlayamadı ve `qa_seed_exit_or_output` gerekçesiyle
`REAL_NATIVE_SERVICE_SEED` aşamasında UNKNOWN'a geçti. Uyarılar ham
çıktıda korunuyor; stderr temizmiş gibi raporlanmıyor.

Bu noktada servis çocuğu yoktu ve salt okunur gözlemde servis kontrol
socket'i bulunmuyordu. Dolayısıyla gerçek servis start/READY/status/CLOSED
kabulü yapılmadı. Seed'in kendi kaynaklarını normal kapatması, supervisor'ın
volume veya imaj lease'ini kapattığı anlamına gelmez.

Sonraki salt okunur custody gözleminde controller **PID 7 / startTicks 337**,
broker **PID 14 / 670** ve mount worker **PID 15 / 719** aynı kimliklerle
yaşıyordu; cgroup'da worker bulunuyordu. İmaj, fence ve özgün sahiplik
korundu. Bu gözlemde sinyal, adoption, replay veya cleanup yapılmadı ve
878/1.162 dosyanın tamamı tekrar hash düzeyinde doğrulandı.

Broker daha sonra kendi yaşam süresi sınırında
`ping_broker_lifetime_expired` ile UNKNOWN kaydetti;
`shutdownCommandAccepted=false`. Bu kayıt normal shutdown değildir.
Özgün controller'ın o aşama için resume/close API'si bulunmadığından
`normal-02` **UNKNOWN olarak kalır**. Laboratuvar temiz, eski owner kapalı
veya kaynaklar serbest bırakılmış sayılmaz. Yeni ayrı denemenin olası
başarısı da bu eski custody kaydını kapatmaz.

İkinci salt okunur kayıt `custody-and-separation-02`, aynı PID/startTicks
kimliklerini, worker'ın özel ext4 mount'unu, loop bağlantısını ve tutulan
kaynakları yeniden gözledi. Host mount tablosu yalnız bu gözlem aralığında
değişmedi; ilk denemeden beri değişmezlik veya gözlem sonrasına taşan canlı
custody iddia edilmedi. `normal-03` için ayrılan beş kök iki okumada da yoktu.
Bu gözlem yeni süreç, mount, SQLite bağlantısı, ping, sinyal veya cleanup
üretmedi; yeni denemeyi başlatmadı veya yetkilendirmedi. Kurulu bütün
baytları yeniden taramadığı da açıkça kayıtlıdır; 878/1.162 byte doğrulaması
önceki `custody-readonly-01` kaydına aittir.

İki yeni gerçek kabul tamamlandıktan sonra native046, yalnız eski
`normal-02` custody'sini tekrar salt okunur gözledi. Controller
7 / 337, broker 14 / 670 ve worker 15 / 719 kimlikleri gözlem öncesi ve
sonrasında aynıydı; tutulan kaynaklar değişmedi ve özgün sonuç UNKNOWN
olarak kaldı. Bu son kayıt yeni kapasite/deneme değerlendirmesi, kurulumun
yeniden tam byte taraması, kapanış veya tüm laboratuvarın temiz olduğu
iddiasını taşımaz. Sinyal, mount, SQLite bağlantısı, ping, adoption, replay
ve cleanup işlemi yapılmadı. Gözlemin sonrasına canlı custody garantisi
verilmez.

Son QA04 kabullerinden sonra native074 aynı dar retained-only gözlemi
yeniden tamamladı. Controller 7 / 337, broker 14 / 670 ve worker 15 / 719
kimlikleri ile tutulan kaynaklar gözlem öncesinde ve sonrasında aynıydı.
Özgün sonuç yine UNKNOWN; normal close, tüm laboratuvarın temizliği veya
gözlem sonrası canlılık garantisi çıkarılmadı. Bu kayıt da kurulum
baytlarını yeniden taramadı ve yeni bir lifecycle başlatmadı.

## 4. Son QA04 baytlarının gerçek kabulü — PASS

EOF düzeltmesinden sonra yeni QA04 paketiyle iki ayrı taze lifecycle
çalıştırıldı. QA manifesti
`2ddb7cafc1eb422e313f48517b7352b0f18470b8d400fb4d991c3d50ac8393f7`;
son seed kaynağı
`129afb6e52e8034ba25a583868699f774592efe09296651a2b90145393ed272f`,
controller kaynağı
`844b73ddf0e2829faaf33b0ab880e7d871a4110c03c270b204834a8d80086ff0`
hash'leriyle bağlıdır. Değişmeyen ürün kurulumu yine aynı 878 kaynak,
1.162 bağımlılık ve R167 kurulum makbuzudur.

| Güncel gerçek kabul | Özgün sahiplik | Sonuç |
|---|---|---|
| `normal-04`, native069 | Controller PID 157 / startTicks 427339; worker 165; servis çocuğu 182 / 430833 | Start READY, status READY, close CLOSED ve son status CLOSED; host/caller exit 0. |
| `lostreply-02`, native072 | Controller PID 224 / startTicks 445264; worker 232; servis çocuğu 249 / 447281 | Tek close gönderimi ardından REPLY_LOST; aynı request/owner için salt okunur status CLOSED; host/caller exit 0. |

İki deneme farklı imaj/profil ve özgün sahiplerle yürütüldü; eski QA03
denemesi veya `normal-02` custody'si devralınmadı. Her ikisinde gerçek seed
epoch 1 ardından sabit servis çocuğu epoch 2 çalıştı. Aynı owner/serviceId
bağı, child final çerçevesi, exit 0 ve stdout/stderr EOF doğrulandı.
Kapanışta üç fiziksel store, profile lease, API/transport/runtime ve
default executor tamamlandı; ardından özgün worker/volume, loop, fence
ve en son imaj lease'i sırası kapandı. Her broker bir ping kabul etti,
yetkili shutdown sonrası exit 0 verdi; physical provider attempts,
responses, görev ve model çağrısı 0 kaldı.

`lostreply-02` gerçek kontrol kanalında kontrollü yanıt kaybıdır:
`sentOnce=true`, `responseRead=false`, `requestDispatched=true`,
`state=REPLY_LOST`, `closeRepeated=false`. Kapanış proof'u son gözlemden
önce saklandı; sender'ın request ID'si ile final status request ID'si
aynıdır. Alınmış close cevabı olmadığı için `close=null` korunur.
Bu sonuç yalnız aynı özgün close isteğinin salt okunur uzlaştırmasını
kapsar; start/dispatch yanıt kaybı, process crash veya restart kabulü
değildir.

Native070 ve native073, primary sonuç dosyalarını geri okuyarak sırasıyla
392.242 ve 388.720 baytlık makbuzları exact hashleriyle doğruladı. Her iki
sonuçta kurulu kaynak/runtime baytları ve denemeye ait host mount
namespace/tablosu değişmedi; bütün sahip olunan çocuklar terminaldir.
Task-free lifecycle kabulü true, görev yürütme/restart/tam D3B/M1/production
alanları false kalır. Önceki UNKNOWN sahibi için kapanış iddiası yoktur.

### Tarihsel QA03: `normal-03` — PASS

Native040, ayrı QA03 ve yeni owner/imaj üzerinde exit 0 ile tamamlandı.
Host sonucu `REAL_SERVICE_LIFECYCLE_ACCEPTED`, özgün caller sonucu
`REAL_SERVICE_LIFECYCLE_CLOSED`. Caller'ın ham stdout boyutu/hash'i ve
çözümlenmiş sonucu birbirine bağlı; transport terminal exit 0 ve tam
akış kaydı mevcut. Native041, primary'deki 392.108 baytlık sonuç dosyasını
salt okunur geri okuyarak aynı SHA-256 değerini doğruladı.

| Gerçek adım | Sonuç |
|---|---|
| Yeni native seed | PASS; epoch 1, üç fiziksel bağlantı CLOSED, consumer DETACHED, seed profile lease'i normal bırakıldı. |
| Node CLI `start` | `READY`; tek özgün servis çocuğu başladı. |
| Node CLI `service-status` | Aynı servis için `READY`; yeni child veya mutation üretmedi. |
| Gerçek ping broker | Bir ping kabul edildi; physical provider attempts, responses ve gerçek model çağrısı 0. |
| Node CLI `close` | `CLOSED`; özgün child/native kaynaklar ve volume kapanışı tamamlandı. |
| Son `service-status` | Aynı kapanış için `CLOSED`; retry kapalı. |
| Broker ve controller | Yetkili broker shutdown kabul edildi, broker exit 0; controller terminal exit 0. |

QA03 classifier, seed stderr'indeki üç uyarıyı dört exact kurulu native
kaynak, sabit seed kaynağı, SQLite sürüm gözlemi ve DELETE handoff ile
`EXACT_PINNED_NATIVE_DELETE_WARNINGS` olarak bağladı. Classifier native kod
çalıştırmadı veya DB açmadı; önceki UNKNOWN kaydını yeniden sınıflandırmadı.
Üç uyarının 1.265 baytlık stderr'i korundu. Ürün çocuğunun kapanış kanalında
da aynı stderr hash'i bulunuyor; boş stderr veya warningsiz çalışma
iddiası yok.

Yeni controller PID 30 / startTicks 145519, mount worker PID 38 ve servis
çocuğu **PID 55 / startTicks 148688 / epoch 2** ile aynı özgün sahiplik
zinciri doğrulandı. Çocuğun final çerçevesi, exit 0, stdout EOF ve stderr
EOF kanıtları alındı. API session/transport/runtime retirement, default
executor join, consumer detach, **üç fiziksel store** ve profile lease
kapanışı tamamlandı. Ardından özgün worker normal unmount/exit 0 yaptı;
boş cgroup, kaldırılmış loop bağlantısı, temizlikten sonra kaldırılan fence
ve **en son bırakılmış imaj lease'i** doğrulandı. Bu sıra
[servis entegrasyon sözleşmesindeki](P2-SERVICE-INTEGRATION-R161A1-PLAN.md)
normal kapanışı bu denemede kabul eder. İmajın ve bütün çalışma dosyalarının
silindiği iddia edilmez.

Canlı kernel gözleminde ürün çocuğu UID 23001 / GID 23003,
`CapEff=0`, `CapBnd=0`, `NoNewPrivs=1` ile çalışıyordu; ilgili cgroup'da
yalnız özgün worker ve servis çocuğu vardı. Projected çocuğun dosya
görünümünde `/etc/python3.12/sitecustomize.py`, iki ambient dist-packages
kökü ve `/mnt/c/Windows` yoktu. Bu dar canlı gözlem tam import trace veya
tam shared-library closure kabulü değildir. CLI cevapları
`kernelVerified=false` ve `hostHttpReachabilityVerified=false` alanlarını
korur; ayrı controller kernel gözlemi CLI'nin kendi iddiasına dönüştürülmez.

Denemenin host mount namespace'i ve mount tablosu değişmedi. Kurulu
878 kaynak, 1.162 bağımlılık ve runtime baytları kapanışta yeniden aynı
bulundu. Görev/model çağrısı, provider/tool bütçesi ve upstream provider
başlangıcı **0**. Kabul **yalnız görev açmadan gerçek normal servis yaşam
döngüsüdür**; görev yürütme, restart, tam D3B, M1 ve production alanları
false kalır. Bu yeni owner'ın normal kapanışı eski `normal-02` custody
kaydına uygulanmaz; laboratuvarın bütünü temiz sayılmaz.

### Tarihsel QA03: `lostreply-01` — PASS

Native043, ayrı `lostreply-01` yaşam döngüsünde host/caller PASS ve exit 0
ile tamamlandı. QA03 araçları yeniden kullanıldı; imaj yolu ve fiziksel
kimliği, supervisor sahibi ve profil denemesi `normal-03`'ten ayrıdır.
Önceki owner veya UNKNOWN kaynaklar devralınmadı.

Gerçek kontrol kanalına **bir close çerçevesi gönderildi**, istemci yanıtı
okumadan bağlantısını bıraktı. Bu kontrollü hata enjeksiyonudur; rastlantısal
bir ağ kesintisi gözlenmiş gibi sunulmaz. Sender kaydında
`sentOnce=true`, `responseRead=false`; sunucuda
`requestDispatched=true`, `state=REPLY_LOST` ve özgün owner'ın tutulduğu
görülüyor. `closeRepeated=false`; alınmış normal bir close cevabı olmadığı
için sonuçtaki `close` alanı null olarak korunuyor.

Terminal kapanış kanıtı sonraki gözlemden önce saklandı. Ardından gerçek
Node CLI `service-status`, sender'ın **aynı özgün request ID'si**, aynı
serviceId ve **owner PID 97 / startTicks 172948** ile CLOSED döndürdü.
Bu gözlem close isteğini yeniden göndermedi. Ayrı servis çocuğu
PID 122 / startTicks 176623 için exit 0 ve iki EOF; üç fiziksel store,
profile lease, transport/runtime/API/executor ve özgün volume/fence/image
lease kapanışları doğrulandı. Broker yine bir ping kabul edip normal
shutdown/exit 0 ile kapandı; provider attempt, görev ve model çağrısı 0.

Bu kabul aynı istek için kayıp **close yanıtının** salt okunur
uzlaştırmasını kapsar. Kayıp start/dispatch yanıtı, process crash, restart
veya eski `normal-02` sahibinin kurtarılması bu sonuçtan çıkarılmaz.
388.669 baytlık sonuç native043'ün tam çıktısından yerel olarak doğrulandı;
native044 primary dosyayı salt okunur geri okuyarak aynı hash'i doğruladı.

## 5. İlk stage UNKNOWN; kaynak yayını PENDING, tam CI NOT RUN

Native062'de özgün `stage-source-01`, izinli 25 dosyaya yönelik Git add
işlemini exit 0 ile tamamladı. Sonraki `git diff --cached --check`, raporun
332. ve QA seed'in 972. satırındaki **fazla boş EOF satırları** nedeniyle
exit 2 verdi. İşlem bütünü post-check UNKNOWN olarak kaydedildi; Git add
sonucu geriye dönük başarısız yapılmadı ve stage bütünü PASS sayılmadı.
Bu noktada source commit oluşmadı.

Native064, aynı 25 sahip olunan yolu açıkça seçen ayrı ve kayıtlı unstage
işlemiyle index'i exact BASE girdilerine döndürdü. Çalışma dosyalarının
baytları, HEAD/branch, 20 korunan repository ve 33 kök dosyası değişmedi.
Özgün config/manifest, rezervasyon, command return ve UNKNOWN kaydı
korundu; eski stage otomatik tekrarlanmadı.

Git whitespace kontrolü gevşetilmedi. Rapordan bir fazla LF, seed'den iki
fazla LF kaldırıldı; controller'da yalnız sabit seed hash'i güncellendi.
Son dosyalar tek LF ile biter. Seed iş mantığı ve kurulu ürün değişmedi;
QA kaynak baytları değiştiği için önceki QA03 kabulü yeni baytlara
devralınmadı. Focus05 ve ayrı `normal-04`/`lostreply-02` kabulleri son
QA04 baytlarını yeniden bağladı. QA03'ün dokuz public dosyası aynen
korundu; sekiz yeni QA04 kanıt dosyası ayrı adlarla eklendi.

Özel yayın yardımcıları ve bir defalık işlem günlüğü hazırlandı; hazırlık
kaynak yayını sonucu değildir. R168 source commit, source exact-commit tam
CI, closure commit/tam CI, main fast-forward, bağımsız remote uzlaştırması
ve final seal bu anlık görüntüde **PENDING**; tam CI **NOT RUN**.
Native044'ün kaynak
keşfi 4.842 benzersiz test ve sıfır import hatası verdi; bu adım **0 test
yürüttü**. Son kaynak manifesti dondurulduğunda staging/statik çıktı aynı
discovery sayısını yeniden bağlamalıdır. R167'nin CI sonucu R168'e
devralınmayacaktır. Normal Git yayını kurulu servise dağıtım veya production
kabulü sayılmaz.

## 6. Ürünün hazır olması için açık kapılar

| Sıra | Gerekli sonuç | Bu rapordaki durum |
|---|---|---|
| R168 normal lifecycle | Aynı kurulumda gerçek CLI start/READY/status ve özgün sıralı CLOSED | Son QA04 ile `normal-04` PASS; QA03 `normal-03` tarihsel PASS. Eski `normal-02` UNKNOWN ayrı. |
| Kayıp close yanıtı | Tek mutation sonrası aynı owner/request'in salt okunur uzlaştırması | Son QA04 ile `lostreply-02` PASS; QA03 `lostreply-01` tarihsel PASS. Close veya cleanup replay yok. |
| Eski UNKNOWN custody | Korunan kısmi kaynakların açık ve yetkili işletim yolu | OPEN; `normal-02` için normal kapanış veya kurtarma kanıtı yok. |
| R168 kaynak/CI/yayın | Son kaynak hashleri ve exact-commit CI ile ayrı source/closure/main zinciri | PENDING; discovery 4.842, tam source/closure CI henüz çalışmadı. |
| P2 günlük yerel kullanım | Başlat, görev ver, izle, sonuç/kullanımı gör, iptal et, kapat | OPEN; bu çalışmada görev yürütme yok. |
| P2 seçilmiş gerçek sağlayıcı | Gerekli modüller/secret-source bağlantısı, seçilmiş model ve açık maliyet/araç/token bütçesiyle sınırlı gerçek görev | OPEN; gerçek model çağrısı 0. |
| P3 kalıcılık ve yeniden kullanım | Yeni oturumda kimlik/geçmiş; hafıza veya becerinin gerçekten bulunup kullanılması | OPEN. |
| P4 arıza ve işletim | Süreç/broker/yanıt kaybı, timeout, operatör uzlaştırması, yedek/geri yükleme ve yükseltme/geri dönüş | OPEN; R168'in korunmuş UNKNOWN kaydı bu ihtiyacı somutlaştırıyor. |
| P5 tek sürüm ve pilot | Aynı kaynak/kurulumda M1-01..M1-07, temiz kurulum ve sınırlı gerçek görev pilotu | OPEN; production kabulü yok. |

Bu sıra [MVP-v0.1](MVP-v0.1.md) ve
[ürün yol haritasındaki](PRODUCT-ROADMAP.md) gözlenebilir kabul koşullarına
bağlıdır. Test veya commit sayısından tamamlanma yüzdesi ya da teslim tarihi
çıkarılmıyor.

## 7. Public kanıt paketi ve ham kayıt kimlikleri

**Son QA04 kabulünün indeksi `summary-qa04.json` dosyasıdır.** Sekiz yeni
dosya, son kaynak baytlarını ve yeni gerçek makbuzları bağlar. Önceki
`summary.json` ve onun sekiz bağlı dosyası QA03'ün değişmemiş tarihsel
kanıtlarıdır; güncel QA04 sonucu olarak kullanılmaz. İndeksler bağlı
dosyaların byte/hash bağlarını taşır. Kimlik ilişkileri public kayıtlarda
digest ile korunur; ham authority
değerleri ve özel ortam dökümleri yayımlanmaz. Public test logları test
sonuç satırları ve yapılandırılmış özetten üretilmiş gösterimlerdir; özgün
tam logların boyut/hash bağları ilgili JSON makbuzlarında ayrıca bulunur.

### Güncel QA04 — sekiz yeni dosya

| Kanıt | Dosya ve kapsam |
|---|---|
| Son paket indeksi | [summary-qa04.json](../evidence/p2-service-lifecycle-r168a1/summary-qa04.json): son QA04 source/manifest, iki yeni gerçek kabul, EOF düzeltmesi ve eski kayıtların korunması. |
| Normal yaşam döngüsü | [normal-04.json](../evidence/p2-service-lifecycle-r168a1/normal-04.json): son QA04 ile özgün READY/CLOSED ve normal kapanış. |
| Kontrollü kayıp close yanıtı | [lostreply-02.json](../evidence/p2-service-lifecycle-r168a1/lostreply-02.json): son QA04 ile tek close ve aynı request/owner için terminal gözlem. |
| Son retained-only gözlem | [retained-normal-02-after-qa04.json](../evidence/p2-service-lifecycle-r168a1/retained-normal-02-after-qa04.json): native074, eski `normal-02` UNKNOWN. |
| Linux odaklı kapı | [focused-linux-05.json](../evidence/p2-service-lifecycle-r168a1/focused-linux-05.json) ve [focused-linux-05.log](../evidence/p2-service-lifecycle-r168a1/focused-linux-05.log): 136 PASS, 0 SKIP. |
| Windows odaklı kapı | [focused-windows-05.json](../evidence/p2-service-lifecycle-r168a1/focused-windows-05.json) ve [focused-windows-05.log](../evidence/p2-service-lifecycle-r168a1/focused-windows-05.log): 93 PASS, 43 SKIP. |

### Tarihsel QA03 — dokuz dosya değişmeden korunuyor

| Kanıt | Dosya ve kapsam |
|---|---|
| Paket indeksi | [summary.json](../evidence/p2-service-lifecycle-r168a1/summary.json): iki gerçek kabul, önceki sonuçlar ve kabul sınırları. |
| Normal yaşam döngüsü | [normal-03.json](../evidence/p2-service-lifecycle-r168a1/normal-03.json): aynı owner/child, READY/CLOSED ve normal kapanış. |
| Kontrollü kayıp close yanıtı | [lostreply-01.json](../evidence/p2-service-lifecycle-r168a1/lostreply-01.json): tek close ve aynı özgün isteğin salt okunur terminal gözlemi. |
| Korunan eski custody | [retained-normal-02.json](../evidence/p2-service-lifecycle-r168a1/retained-normal-02.json): iki kabul sonrası eski UNKNOWN'un salt okunur gözlemi. |
| Deneme geçmişi | [preserved-attempts.json](../evidence/p2-service-lifecycle-r168a1/preserved-attempts.json): önceki FAIL/REFUSED/UNKNOWN ve sonraki ayrı sonuçlar. |
| Linux odaklı kaynak kapısı | [focused-linux.json](../evidence/p2-service-lifecycle-r168a1/focused-linux.json) ve [focused-linux.log](../evidence/p2-service-lifecycle-r168a1/focused-linux.log): 136 PASS, 0 SKIP. |
| Windows odaklı kaynak kapısı | [focused-windows.json](../evidence/p2-service-lifecycle-r168a1/focused-windows.json) ve [focused-windows.log](../evidence/p2-service-lifecycle-r168a1/focused-windows.log): 93 PASS, 43 SKIP. |

### Özgün operatör kayıtlarının pin'leri

Aşağıdaki yollar repository içindeki özel operatör kayıtlarını tanımlar;
ham ortam dökümleri, authority değerleri ve özel baseline bu public rapora
eklenmemiştir. Listelenen baytlar bu çalışma kopyasında okunup hashleri
doğrulandı. Windows03 tam logunun boyutu ve hash'i de gerçek sonuç
makbuzuna bağlandı.

| Kayıt | SHA-256 |
|---|---|
| `scratch/r168-service/parent-r167-seal.json` | `65693d5e1453da650422d63b30b29e5b3ed291aad753b527ed24985e08456cd8` |
| `scratch/r168-service/focus-linux-03/result.json` | `9b6854bdc93b8bfa45d3297a4e6ee8c3a9985bf4b036aa6121d3e37d822949a0` |
| `scratch/r168-service/focus-windows-01/result.json` | `70baeb932bcab0913a756a92925c5d2b562fd2b2d93946c2b758389fbc79bff6` |
| `scratch/r168-service/focus-windows-02/result.json` | `6c079c148864789d89e191bbdee5ab29d64b7278467e4fe2a892da67f45a56fd` |
| `scratch/r168-service/focus-windows-03/result.json` | `3996440fed7af36cb7559a4a63b98722504c07ce3aa68109231772b73a05da26` |
| `scratch/r168-service/focus-windows-03/full.log` | `4fb30b0018bdb533ef3bda68f5fd5e09df95bd05afa1e23b9661338a2b1299c5` |
| `scratch/r168-service/focus-linux-04/result.json` | `cbe09118507cf481a313b113fc96f73a178447e30ba90064e9158fcafe75c129` |
| `scratch/r168-service/focus-linux-04/full.log` | `aef6ef93159ed3350ba9fde90eaf694f7b2393894c3e736084c9a8d8bd0108b2` |
| `scratch/r168-service/focus-windows-04/result.json` | `1e6398825a8b9c8343cc1b2072dba9018c3f6fd8cfb383c83b01bf65bf3d4f20` |
| `scratch/r168-service/focus-windows-04/full.log` | `3690dd96ea9c35a39f71fddfdca6f0287dbc80542fd3e68625e64914716ff0c6` |
| `scratch/r168-service/normal-01/result.json` | `3f60875da0e5ebb178812599724f43312fa49b4d664854f94c4584c89725069c` |
| `scratch/r168-service/bootstrap-context-observations-01.json` | `d270433b5649e4cfbc41482db2c215986cdd10b47a3d6c8731d49c5e29eee797` |
| `scratch/r168-service/normal-02/result-from-native.json` | `5aac3b693d44c27749ab187768231937d020d208465a9875b65869f47faad1ce` |
| `scratch/r168-service/normal-02/seed-stdout.txt` | `a704da053c72605bab29debe08757c77c0b28f84752c3e1cfe33ff4db5225bd8` |
| `scratch/r168-service/normal-02/seed-stderr.txt` | `6835531560cfb3b3e7d8ebd1bad0e8cfd3e1710408cac85f9a1814b00133916c` |
| `scratch/r168-service/normal-02/custody-readonly-01.json` | `bccd7b7e006261aade9578682c0ef3dafedd09f802778ed64ee918699ba676b4` |
| `scratch/r168-service/normal-02/custody-and-separation-02.json` | `fe3f153f6afac813a8277f8d6642d41fbfbc8ec28ff33d232e88f18ee3d0f53a` |
| `scratch/r168-service/normal-02/custody-after-acceptances-03.json` | `6de63b79b7357a6bae95881640202bae4d198cfde053b6e71f912d3015e012ac` |
| `scratch/r168-service/normal-02/broker-stdout.log` | `046bc4f55e4d4ea244027273464d448d5507a561670291d6ce72fe3f7b4a8c3d` |
| `scratch/r168-service/normal-03/result.json` | `26608f17f965f6db616e41d48963af7daccb9dd352c3a6e0fcece311a40d596e` |
| `scratch/r168-service/normal-03/primary-readback.json` | `bf8f0f68c85e7471fdfb8db89df619d988d6ba82426c7a0378e255bdcea572ed` |
| `scratch/r168-service/lostreply-01/result.json` | `e4f8f16133f2b7436df4d48e518947a1377e98fddc07b06edb05316487a31ba0` |
| `scratch/r168-service/lostreply-01/primary-readback.json` | `b135ace18afaabcb5f231536528fe5907cc4482c0d569de7ba75c5a1c0b5c6ef` |
| `scratch/r168-service/focus-linux-05/result.json` | `3f4a4de342a305c9ffb02b1dd0adccc9c673cbcdc30b7c8fb41455630f8d12b7` |
| `scratch/r168-service/focus-linux-05/full.log` | `a8e0307f370a8594b39189a73eb2bc8ad52c01f4ec6b05c847d34dabe85498c1` |
| `scratch/r168-service/focus-windows-05/result.json` | `7857f53eacc8810f834891af7c657c676a260cd4ee00e7bd22db19e4587f83de` |
| `scratch/r168-service/focus-windows-05/full.log` | `690be53fc2f9276da3804586ff4c5919585b99d1cf23a23867013e950f5cc2af` |
| `scratch/r168-service/normal-04/result.json` | `4e55ddcb37e079ebedc576c515555c6298bcd38c248bb0205a515e918001dcd4` |
| `scratch/r168-service/normal-04/primary-readback.json` | `f7f6ef0311c5134b4b7be947a07fc3c94d3e5469efd208cc36a0714f1137dd6f` |
| `scratch/r168-service/lostreply-02/result.json` | `bc6470e456efaa47c9600d82c5bc201bba42d03a21dac6bbb6bbbff42c476039` |
| `scratch/r168-service/lostreply-02/primary-readback.json` | `0c5a0d96a7adae52ed3ad6b0639b85d502fa501d41f5b3425cbf51b370004e07` |
| `scratch/r168-service/normal-02/custody-after-qa04-04.json` | `209d279d633b647cf5ecea1cd6b951aafa87093bc2c522a0daee615bf00d77f3` |
| `scratch/r168-publication/stage-source01-readonly-diagnostic.json` | `4839009cba819a5af43bc26bf6abf135a4c1fec8536a707bb25ce6efeae2d8b8` |
| `scratch/r168-publication/unstage-source-packet01-01.result.json` | `bdafbf0db2e569952f7528d5670ccdf83c441323eaa2c4019f046ac53e7be458` |

Yeni gerçek sonuçlar geldiğinde bu rapor yeni zaman damgasıyla güncellenecek;
önceki FAIL, REFUSED ve UNKNOWN kayıtları kendi sonuçlarıyla korunacaktır.
