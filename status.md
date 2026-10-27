# AlazHarness — status

## R162A1 — sabit projected servis receiver/factory — IN PROGRESS

P1 DONE; P2 IN PROGRESS. P3–P5, tam D3B, M1 ve production OPEN.

- Aktif dal: `alaz/p2-service-receiver-r162a1`.
- Aktif çalışma ağacı: `C:\Antigravity\AlazHarness\scratch\worktrees\p2-service-receiver-r162a1`.
- Başlangıç ve önceki yayımlanmış main: `b56b9b321002a5bb8696fcae27edcfc92c28df1c`.
- Önceki R161 kapanışı: 4.302 test, 4.280 PASS, 22 SKIP; exact-commit tam CI ve main verified reuse PASS.
- Native seçim: `5e3635c2cdfc2161fd20c089618bd7f2a7c12f2d`, 760 dosya; değişmedi.
- Başlangıç makbuzları: `scratch/r162a1-publication/baseline.json` ve `worktree-created.json`.
- Önceki durumun tam kaydı: [R161 parent](docs/status-history/r162a1-parent.md).

### Amaç ve mevcut sonuç

R161 ServiceStartup transferini sabit kardeş receiver ile doğrulayıp aynı
ProfileLease / NativeStoreStartup / BorrowedServiceOwner nesnelerini R160
control driver'a bağla. Aynı runner, authority, epoch ve üç fiziksel store
korunur. Tek startup denemesi, READY öncesi config/source kabulü ve UNKNOWN
sonucunda özgün owner/loop'un korunması yeni birleştirme sınırlarıdır.

Canlı başlangıç doğrulaması PASS: korunan sekiz depo, kökün 33 değişmiş
dosyası, önceki R161/R160 çalışma ağaçları ve 760 native kaynak eşleşti.
Yeni izole dal main'in yayımlanmış commit'inden açıldı. Değiştirilecek
kaynaklar bu çalışma ağacında; özgün kökteki kullanıcı değişiklikleri korunur.

### Test ve yayın

Receiver/entry: yerel 35 yeni test ve ilgili eski seçimle 102/102 PASS, exit 0.
READY/config düzeltmesi: parent üzerinde 7 testte 4 FAIL / 3 PASS; dar düzeltme
sonrasında 7/7 PASS. Yeni tarihsel koruma ve ilgili lifecycle seçimi 38/38 PASS,
exit 0. İki kaynak bölümü bağımsız salt-okunur incelemeden geçti. Bu sonuçlar
kaynak/fixture kapsamındadır; ham kayıtlar evidence/p2-service-receiver-r162a1 altındadır.

Receiver, READY guard ve factory kaynakları primary çalışma ağacına aktarıldı.
Factory'nin 39 yeni testi dahil son birleşik seçim: Linux 483/483 PASS, 0 SKIP,
exit 0 (10,854351 s); primary Windows 466 PASS + 17 platform SKIP = 483,
failure/error 0, exit 0 (38,271473 s). Aynı test kimlikleri, runner ve 14 ürün
kaynak hash'i iki koşuda eşleşti. Config/native ve lifecycle bağımsız incelemeleri
PASS. Son kanıtlar `focused-linux-r2.*`, `focused-windows.*` ve iki review JSON'udur.
İlk Linux kaydı son Windows CRLF test karşılaştırması düzeltmesinden önceki ayrı
483/483 sonucu olarak korundu; ürün değişmedi. Tam CI, commit/push ve main
aktarımı IN PROGRESS; henüz tamamlanmış yayın olarak sayılmaz.
Yeni kurulum, native servis çalıştırma veya gerçek model/sağlayıcı çağrısı yoktur.

### Kesin sonraki adım

Son kaynak, test ve rapor dosyalarını açık owned-path listesiyle stage/commit et.
Kaynak commit'inin tam CI kanıtını doğrula; bu ham kabul kaydını kaynak paketine
ekleyen belge kapanış commit'ini de exact-commit tam CI'dan geçir. Bütünlük
kontrolünden sonra main'i normal fast-forward/push ile ilerlet; main'in aynı
commit için ayrı verified-reuse makbuzunu ve final yayın günlüğünü doğrula.

Sonraki entegrasyonlar: supervisor Unix kontrol sunucusu, child final/exit/EOF
ile volume stop/finish, host görev erişimi ve yeni tek P2 kurulum kabulü.
[Entegrasyon planı](docs/P2-SERVICE-INTEGRATION-R161A1-PLAN.md) açık kalır.

### İş günlüğü

- 2026-10-27 başlangıç: R161 final yayın kaydı
  `e45e98eefc8ca24a569847097e10fb5cafeb30bdb4a9ce6cd050c20524df5165`
  ve canlı Git/dosya durumu doğrulandı. Base b56b9b3 üzerinden izole R162 dalı
  açıldı. Receiver, factory ve provenance için üç bağımsız çalışma ayrıldı.
- 2026-10-27 ön inceleme: eski finite/readiness launcher'ı değiştirmeden kardeş
  receiver/entry seçildi. Native plugin/config kaynakları seçilmiş manifest
  hash'leriyle okundu. Son async readiness aralığındaki config drift'i yeni
  assembly testine alındı; henüz uygulanmış/test edilmiş sonuç değildir.

- 2026-10-27 kaynak checkpoint: receiver/entry ve final READY config guard'ı
  tamamlandı; 102 ve 38 testlik ayrı yerel seçimler PASS. Son async aralıkta
  config/source/receipt değişiminin yanlış READY üretmesi dört negatif testle
  doğrulandı ve dar hook ile düzeltildi. Parent runtime ve eski dokuz R159
  kanıtı ayrı hash'lerle korundu. Factory kaynak taslağı bağımsız review'da;
  native config loader'ın backup yan etkisi owner.start sonrasına sıralandı.

- 2026-10-27 son kaynak seçimi: stderr/exception diagnostic hatası ve kapalı loop
  retention boşlukları düzeltildi; foreign exception metni diagnostic'e taşınmaz.
  Factory'nin 39 testiyle toplam 90 yeni test eklendi. Son Linux 483 ve Windows 466+17 koşuları
  PASS; bağımsız iki factory review PASS. İlk native ownership/store importları
  mevcut güvenilir kurulum önkoşulunu korur; 760 qualification sonraki native
  config/plugin importlarından öncedir. İlk import öncesi attestation veya
  kurulu servis kabulü iddiası yoktur. Yeniden bağlantı kontrolünde 20 checkpoint
  dosyası, sekiz korunmuş depo, kökün 33 dosyası ve eski çalışma ağaçları eşleşti.
