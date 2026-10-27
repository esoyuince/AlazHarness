# P2 / R164A1 — özgün servis volume kapanışı

Tarih: 27 Ekim 2026. **Kaynak/fixture entegrasyonu ve odaklı testler PASS;
exact-commit tam CI ve yayın NOT RUN. P2 IN PROGRESS.**

R164, [entegrasyon planının](P2-SERVICE-INTEGRATION-R161A1-PLAN.md) dördüncü
adımını kaynak düzeyinde tamamlar. Özgün servis çocuğunun final/exit0/EOF kanıtı,
aynı ServiceVolumeSupervisor'ın normal stop/finish zincirine bağlandı. Unix
kontrol sunucusu, bütün zincir tamamlandığında mevcut CLI'ye CLOSED bildirir.
Linux'ta aynı kaynak seçimiyle 806/806 test geçti; primary Windows'ta 626 PASS,
180 platform SKIP, failure/error 0 ve exit 0 kaydedildi. Bu sonuç yeni kurulum,
gerçek kernel/servis veya model kabulü değildir.

## Kaynak ve çalışma kimliği

- Base: `28a12e1b18a839a9489a0c463d904b8e9a46db03`.
- Dal: `alaz/p2-service-closure-r164a1`.
- Primary çalışma ağacı:
  `C:\Antigravity\AlazHarness\scratch\worktrees\p2-service-closure-r164a1`.
- Önceki R163 final yayın günlüğü SHA-256:
  `63525a048232d70109aa0378bf967376a96ef2e5ef0510bd8e28dd604d5cf809`.
- Önceki izlenen durum: [R163 parent kaydı](status-history/r164a1-parent.md).
- Native seçim: `5e3635c2cdfc2161fd20c089618bd7f2a7c12f2d`, 760 dosya.

[Başlangıç kanıtı](../evidence/p2-service-closure-r164a1/baseline.json), sekiz
korunan deponun, kökün 33 değişmiş dosyasının ve dört önceki feature çalışma
ağacının durumlarını bağlar. İlk yerel seçimin 899 dosyası exact base Git
baytlarıyla karşılaştırıldı; native seçimin 760 dosyası da doğrulandı. Kökün
eşzamanlı değişiklikleri ve kabul edilmiş R156 kurulumu korunur.

## Tamamlanan davranış

### Özgün child ve volume sahibinin korunması

Servis aynı begin/attach/start akışından açılır. Child slotu ve ayrı özgün child
referansı, Popen, ServiceChannel, worker, pin, image lease, actor, scope, hedef,
fence, loop FD ve süreç kimlikleri saklanır. Yerine konan bir nesne, yalnız
CLOSED etiketi veya çağıranın verdiği boolean/dict bu sahipliği devralamaz.
`check_service_owner` yalnız doğrulama yapar; child'a veri göndermez ve cleanup
başlatmaz.

Kapanış öncesi read-only status, özgün actor/nesne/fence/lease bağını denetler;
canlı child başlangıç kimliği veya worker kaybı, özgün gözlemci tarafından
UNKNOWN olarak bildirilebilir. Böylece belirsizlik, kaydı gözlemlemeyi veya
aynı sahibi tutmayı engellemez. Yabancı actor veya değiştirilmiş sahiplik bu
gözlem yolunu kullanamaz.

### Final kanıtından normal cleanup'a geçiş

Bir açık close işlemi şu sırayla ilerler:

1. Özgün ServiceChannel'ın doğru kimlik, sequence ve request ID'ye bağlı final
   çerçevesi doğrulanır. Native transport/runtime/consumer, üç fiziksel store ve
   caller/profile lease kapanış kanıtı gerekir. Bekleyen veya kısmi input,
   trailing output, açık stdin, eksik stdout/stderr EOF ya da gerçek Popen exit0
   eksikliği kapanışa izin vermez.
2. Aynı cgroup'da yalnız özgün mount worker bulunmalı; alt cgroup olmamalıdır.
   STOPPING ve deneme kaydı, stop herhangi bir byte yazmadan önce tutulur.
   Mevcut `VolumeSupervisor.stop` çağrılır. Özgün PID/token'lı exact UNMOUNTED
   makbuzu ile worker exit0 doğrulanıp saklanır.
3. Finish için ayrıca bu başarılı stop makbuzu gerekir. Tamamen boş ve alt
   cgroup içermeyen özgün scope doğrulanır; FINISHING kaydı effect öncesinde
   tutulur. Mevcut `VolumeSupervisor.finish` çağrılır.
4. Generic finish'in normal sırası korunur: boş cgroup ve host mountpoint
   kontrolü, tutulan loop FD'nin bir kez kapanması, global device/inode loop
   bağlantısının yokluğu, tekrar kontrol, scope temizliği, özgün fence'in
   kaldırılması ve parent fsync, ardından image lease'in bırakılması. Normal
   akışın akış kapatma işlemleri de başarıyla dönmüş olmalıdır. Yalnız dönen
   exact finish makbuzu, özgün CLOSED stage ve boş loop FD birlikte CLOSED
   sonucunu oluşturur.

Generic volume, worker, channel ve kernel algoritmaları değiştirilmedi.
Doğrudan ServiceVolumeSupervisor.stop/finish çağrıları da aynı kanıt kapılarından
geçer; child final kanıtı başarılı stop makbuzunun yerini alamaz.

### Gecikmiş sonuç, kaybolan yanıt ve belirsizlik

| Gözlenen durum | Dış sonuç ve izin verilen devam |
|---|---|
| Child tamamlandı; volume kapanışı henüz başlamadı | DRAINING. Status ve aynı request ID'nin gelişi yalnız gözlemdir. |
| Bounded close süresi doldu; child daha sonra tamamlandı | Status ve eski ID cleanup başlatmaz. Yeni açık close ID'si, henüz denenmemiş ilk volume kapanışını başlatabilir. |
| Stop/finish başladı veya üyelik ön kontrolü UNKNOWN/BUSY ile sonuçlandı | Özgün deneme ve referansları korunur. Aynı veya yeni ID stop/finish'i yeniden çalıştırmaz; R164 otomatik uzlaştırma sağlamaz. |
| Tam cleanup bitti; son yanıt gönderilemedi | Önceden saklanmış terminal CLOSED kanıtı status, aynı ID veya sonraki close ile gözlenir; ikinci cleanup yapılmaz. |
| Child tamamlandı; volume kapanışı belirsiz kaldı | Child completion korunur, dış durum UNKNOWN kalır. Kısmi cleanup bütün kaynaklar bırakıldı diye sunulmaz. |

Özellikle loop AUTOCLEAR beklemesi, global attachment, eksik stop yanıtı, BUSY,
fence/fsync veya lease kapanış belirsizliği yeni bir stop/finish çağrısıyla
örtülmez. Generic finish, kendi güçlü referansını kaldırdıktan sonra bir
stream.close hatası verebilir. Bu durumda servis katmanı özgün sahibi yeniden
güçlü referansla tutar; dönen finish makbuzu olmadığından CLOSED üretmez. Böyle
bir kuyruk hatasında bazı kaynaklar zaten bırakılmış olabilir; bütün kaynaklar
hâlâ açıkmış veya bütün kapanış kesinleşmiş gibi bir iddia yoktur.

### Unix kontrol sunucusu ve mevcut CLI

Her snapshot, exact volumeClosure şemasıyla ve özgün typed kapanış kanıtıyla
yeniden eşleştirilir. Dış CLOSED için child completion, üç store, tüm native
kapanış bayrakları, volume unmount, fence temizliği ve image lease bırakılması
birlikte gerekir. Terminal görünüm canonical byte'ları ve özgün child referansı,
yanıt yazılmadan önce saklanır.

Kapanış sonrası gözlem, kaldırılmış fence/cgroup veya bırakılmış lease üzerinde
RUNNING şartı aramaz; saklanan özgün kimlik ve makbuzları denetler. Controller
PID/startTicks/token, actor, socket ve parent kimliği kontrolleri sürer. Eski
owner/service veya değiştirilmiş socket kabul edilmez. Geçici yanıt hatası,
saklanan terminal sonucu silemez.

Ürün JavaScript'i ve R160 wire protokolü değişmedi. Mevcut Node istemci/CLI,
başarılı tam kapanışta `closed_reported`, `serviceClosed: true`,
`closureReported: true` ve exit 0 döndürür. `retryAllowed`, `volumeMayClose` ve
`fullD3BAccepted` üzerinden yeni bir cleanup veya kabul yetkisi verilmez.

## Değişen dosyalar ve tarihsel bağ

Ürün değişikliği üç dosyayla sınırlıdır:

| Ürün dosyası | Son SHA-256 |
|---|---|
| `packages/claw-hermes/gateway_supervised_service.py` | `2369f36805ffc4a708c2578d9877cd2497c2afe76da279208990f2faa1ca45b1` |
| `packages/claw-hermes/service_volume_supervisor.py` | `a82e969db632e792cca3f5fdbf73fb98583fb92fb55d2efe1de48299b1af076d` |
| `packages/claw-hermes/service_control_server.py` | `3265d9048ee602e2e3456a9b37e7ca6a89fbc0b5c8b09e345450a10775748195` |

Yeni R164 kapsamı 42 lifecycle, 22 server, 7 Node CLI entegrasyon ve 14 tarihsel
bağ testiyle 85 test ekler. Sekiz yeni test/destek dosyası ve beş mevcut R163
test/destek dosyasındaki uyarlama bu sözleşmeyi taşır. R163 Python CLI wrapper'ı
değişmedi. Önceki CLI fixture'ı, volume kapanış ön koşulunun sağlanmadığı durumda
generic stop/finish çağrılmadığını sınayacak şekilde güncellendi.

[Tarihsel kaynak bağları](../evidence/p2-service-closure-r164a1/historical-source-bindings.json),
exact base'deki üç ürün ve altı test/destek dosyasının dokuz arşivini içerir.
Değişmeyen eski Python CLI wrapper'ının arşivi de bu altı kayda dahildir.
R163'ün 13 kanıt dosyası, yedi eski resolver/test dosyası ve altı R160 JSON/log
kaydı kendi baytlarıyla korunur. Yeni history resolver yalnız exact parent
dosya/hash eşleşmesini kabul eder; güncel, bilinmeyen veya başka nesil isteği
eski başarıya dönüştürmez. Eski resolver'lar ve makbuzlar yeniden etiketlenmedi.

Parent ServiceVolumeSupervisor hash'i
`82d2439a3f22873267ae9f7606eef2b032f6203f2dab240c41c1c5bbd5b132df`;
R160'ın final `30fa40aa1ee1378f5136f27da04879677e457c9c56f983527833d2974bf4f8e8`
ve initial `eb28de8c043aaf8105cfc54261ccd481424cf973de756ae4aea73753142f9d29`
nesilleri ayrı kalır. Güncel R164 kabulü aşağıdaki taze koşulardan gelir.

## Doğrulama sonuçları

| Doğrulama | Seçilen/koşulan | PASS | SKIP | Failure / error | Exit | Süre |
|---|---:|---:|---:|---|---:|---:|
| Son birleşik Linux odaklı seçim | 806 | 806 | 0 | 0 / 0 | 0 | 96.378312 s |
| Aynı seçimin primary Windows koşusu | 806 | 626 | 180 | 0 / 0 | 0 | 62.8848 s |
| Bağımsız taze tarihsel bağ koşusu | 14 | 14 | 0 | 0 / 0 | 0 | 0.198434 s |
| Exact source commit tam CI | NOT RUN | — | — | — | — | — |
| Exact final commit tam CI | NOT RUN | — | — | — | — | — |
| Main yayını ve ayrı status kabulü | NOT RUN | — | — | — | — | — |

Tarihsel 14 test, birleşik 806 seçimin de içindedir; toplam ilerlemeye ayrıca
eklenmez. Windows SKIP kayıtları POSIX child pipe, Unix socket/SO_PEERCRED,
directory fsync ve diğer ilgili platform koşullarını açık gerekçeleriyle taşır.
Bu platform davranışları Linux'ta çalıştırıldı. Her iki odaklı koşu, 51 selector,
25 ürün dosyası, 50 test/destek dosyası ve aynı runner üzerinden yapılmıştır;
kaynak/test hashleri koşu öncesinde ve sonrasında aynıdır.

Linux lifecycle fixture'ı gerçek child Popen ve pipe'larını; server/CLI zinciri
gerçek Unix socket, SO_PEERCRED ve Node istemcisini kullanır. Özgün generic
stop/finish ve üyelik denetim kodları, açık worker/kernel/loop/lease fixture
portları ve geçici dosyalarla çalışır. Bu ayrım gerçek mount/kernel veya kurulu
native servis kabulü iddiasını sınırlar. Yedi yeni CLI senaryosu tam kapanış,
kayıp son yanıt, gecikmiş child kapanışı, kayıp stop yanıtı, AUTOCLEAR beklemesi,
stream close hatası ve CLOSED sonrasında eski owner isteğini kapsar.

[Bağımsız kaynak incelemesi](../evidence/p2-service-closure-r164a1/review-provenance.json)
PASS; son kaynakta açık blocker yoktur. İncelemeci ürün testlerini çalıştırmadı;
ürün/test sözleşmelerini ve exact hashlerini inceledi, tarihsel 14 testi ayrıca
çalıştırdı. İncelemede bulunan read-only UNKNOWN kapısı, son kaynakta düzeltilip
iki lifecycle ve bir server regresyonuyla son birleşik koşuya dahil edildi.
Geliştirme koşuları kendi kaynak nesilleriyle saklanır; final 806 kanıtının
yerine geçirilmez.

### Kanıt dosyaları

- [Linux JSON](../evidence/p2-service-closure-r164a1/focused-linux.json) ve
  [ham log](../evidence/p2-service-closure-r164a1/focused-linux.log).
- [Windows JSON](../evidence/p2-service-closure-r164a1/focused-windows.json) ve
  [ham log](../evidence/p2-service-closure-r164a1/focused-windows.log).
- [Tarihsel test JSON](../evidence/p2-service-closure-r164a1/history-focused-linux.json)
  ve [ham log](../evidence/p2-service-closure-r164a1/history-focused-linux.log).
- [Odaklı runner](../evidence/p2-service-closure-r164a1/focused-runner.py),
  [tarihsel bağ](../evidence/p2-service-closure-r164a1/historical-source-bindings.json)
  ve [bağımsız review](../evidence/p2-service-closure-r164a1/review-provenance.json).

| Kanıt kimliği | SHA-256 |
|---|---|
| Linux JSON | `e445597df74f78a499a6c73e50b67e78937672d5c275d0d7b8fd981d92a29d46` |
| Linux ham log | `ad59c5dac7496b59f5de16933b73451200c04eddd5059d04d15d9be103d6c5d3` |
| Windows JSON | `bea40dc964113eb406bfc437311f77e23c02c268525764d7d41ce60178682b19` |
| Windows ham log | `f10ac8c57aecff463a55b4a03bab3f4f6843d90fa5dc1724b8a1cb50c97b0fba` |
| Sıralı 806 test kimliği | `e620cc0d833024134a5d41766d7c8f52c8d9102a6de8895d2cf54f81419d6805` |
| Runner | `bdbcca1355dab5b902ed4c6a84061baf9cce0aa7ab78678b11b8e9abf2ecc429` |
| Tarihsel kaynak bağları | `80e2b9a532eeceb1b94281667f4bde4e7de1461012f8a9e7f6fac922771c46e8` |
| Bağımsız kaynak review | `e26366bde84b24f9b9b70633ee1102634225062f19081a534f18415a7c0933f4` |

## Yayın checkpoint'i ve kabul sınırı

Bu raporun kaynak checkpoint'inde yeni R164 commit/push, exact source/final tam
CI, normal main fast-forward/push ve final integrity henüz çalıştırılmadı.
Bu aşamalar [status.md](../status.md) ve primary çalışma ağacındaki
`scratch/r164a1-publication/` makbuzlarıyla devam eder. Yalnız test başarısı,
commit veya main yayını sonucu olarak sunulmaz. Son yayın hükmü, iki exact
commit'in tam CI kanıtı, ayrı main status kabulü ve final integrity birlikte
doğrulandıktan sonra `final-publication.json` içinde kaydedilir.

Native 760 kaynak ve R156 kurulumu değişmedi. Yeni P2 kurulumu, gerçek kernel
namespace/cgroup/mount/lease yaşam döngüsü, host HTTP görev erişimi, native
backup/restart/effective-config ve gerçek model/sağlayıcı kabulü bu pakette
NOT RUN; gerçek model/sağlayıcı çağrısı sıfırdır. Belirsiz cleanup için otomatik
retry veya operatör uzlaştırma akışı eklenmedi.

## Kesin sonraki adım

R164'ün yayın kapıları tamamlandıktan sonra entegrasyon planının beşinci adımı:
host görev erişimini aynı authenticated native API'ye bağlayan dar transport
yolu. Yeni queue veya sonuç store'u oluşturmadan görev, özgün request sorgusu,
durum, sonuç, kullanım ve cancel akışı doğrulanacak. Ardından altıncı adımda
yeni tek P2 kurulumu ve gerçek kernel/native kabulü gelir. Gerçek sağlayıcı
deneyi için tek model/sağlayıcı, araç kümesi ve harcama sınırı henüz seçilmedi.

**P1 DONE; P2 IN PROGRESS; P3–P5, tam D3B, M1 ve production OPEN.**
