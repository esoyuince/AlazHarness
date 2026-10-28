# AlazHarness — R167A1 servis kurulumu ve başlangıç doğrulaması

**Kurulum ve sınırlı başlangıç kontrolleri PASS. R167 kaynak yayını IN PROGRESS.**

**P1 DONE; P2 IN PROGRESS. P3–P5, tam D3B, M1 ve production OPEN.**

- Aktif dal: `alaz/p2-service-install-r167a1`.
- Yetkili çalışma ağacı: `C:\Antigravity\AlazHarness\scratch\worktrees\p2-service-install-r167a1`.
- Başlangıç commit'i: `833a40aa99f5ca7e2b2562a19e8f0c286a0adea2` (tamamlanmış R166 yayını).
- Rapor: [R167 servis kurulumu ve doğrulaması](docs/P2-SERVICE-INSTALL-R167A1-REPORT.md).
- Önceki kayıtlar: [R166 kapanış durumu](docs/status-history/r167-parent.md), [R167 ara durumunun tam kopyası](docs/status-history/r167-pre-publication.md).

## Tamamlananlar

R166 servis adayı, özel P71C Linux laboratuvarındaki yeni `/opt/alaz-r167a1` hedefine kuruldu. Kurulum 878 kaynak ve 1162 bağımlılık dosyasını içeriyor. Python 3.12.3 ve resmi imzası doğrulanmış Node 24.22.1 için gerçek executable kimliği, SHA-256 ve sürüm geri okuması geçti. Ayrı ordinary-user doğrulaması kurulu dosyaları yeniden okuyarak makbuzla eşleştirdi.

| Kontrol | Gerçek sonuç | Kanıt |
|---|---|---|
| Linux odaklı regresyon | 123 RUN / 123 PASS / 0 SKIP, exit 0 | [Odaklı test özeti](evidence/p2-service-install-r167a1/focused-checks.json) |
| Primary Windows regresyonu | 123 RUN / 88 PASS / 35 tanımlı Linux-only SKIP, exit 0 | Aynı sabit test seçimi ve 81 girdi |
| Gerçek kaynak kurulumu | 878 kaynak + 1162 bağımlılık, exit 0 | [Kurulum ve bağımsız readback](evidence/p2-service-install-r167a1/installation.json) |
| Python başlangıcı | 15 sabit import PASS; `-I -S -B`, exit 0 | [Sınırlı başlangıç doğrulaması](evidence/p2-service-install-r167a1/qualification.json) |
| Node CLI help | Beklenen 2046 bayt çıktı, boş stderr, exit 0 | Aynı başlangıç kaydı |
| R167 tam CI ve kaynak yayını | IN PROGRESS; henüz kabul edilmiş R167 tam CI yok | `scratch/r167-publication` |

Python kontrolü 444 native, 50 harness ve 304 bağımlılık dosyasının import kökenini doğruladı. Tek `socket.bind` girişimi, sabit urllib3 IPv6 yetenek yoklamasına bağlandı ve engellendi; aynı socket'in kapandığı, `HAS_IPV6=False` olduğu ve başka engellenmiş etki bulunmadığı gözlendi. Kurulu kaynak/bağımlılık dosyaları ve runtime binary'leri işlem öncesinde ve sonrasında değişmedi. Geçici home içindeki `SOUL.md` ile birlikte denemeye ait home kaldırıldı.

İlk strict import kontrolü (native029) ve ortamdan gelen `sitecustomize` nedeniyle reddedilen ilk qualification (native037) başarısız olarak korunuyor. Ayrı native042 denemesi daha sıkı no-site başlangıcıyla geçti; eski retler PASS olarak yeniden sınıflandırılmadı. [Başarısız denemelerin kaydı](evidence/p2-service-install-r167a1/preserved-attempts.json).

## Kabul sınırı

Bu sonuç kurulu adayın dosya kimliği ve sınırlı başlangıç uyumluluğunu kabul eder. Servis nesneleri oluşturulmadı; gerçek servis/kernel yaşam döngüsü, provider bağımlılık tamlığı ve gerçek model kabulü açık. Audit guard, işletim sistemi sandbox kabulü değildir. **Gerçek model çağrısı: 0.**

Kurulan ürün kaynağı harness `1600eba430562795b9114209d1168bfa0d6ea5fd`, native `5e3635c2cdfc2161fd20c089618bd7f2a7c12f2d` olarak sabit. Araçların R167 yayın commit'i bu ürün kimliğini değiştirmez. Önceki R156 kurulumu ve tarihsel finite builder/installer korunuyor.

## Devam adresi ve kesin sonraki adım

Son tamamlanan işlem native042 ordinary-user qualification: PASS, exit 0; tam çıktı native043 ile geri okundu. Bekleyen veya sonucu belirsiz native işlem yok. Güncel özel devam kaydı: `scratch/r167-install/orchestration-checkpoint.json`.

Önce bu kaynak paketini commit/push, taze source ve closure tam CI, main fast-forward, aynı commit için doğrulanmış CI reuse ve final integrity/terminal seal ile kapat. Bu adımların gerçek sonuçları ayrı yayın makbuzlarında tutulur; beklenen test sayısı gerçekleşmiş CI sonucu sayılmaz.

Ardından aynı kurulu adayda açık servis profiliyle gerçek supervisor/child/volume ve namespace/cgroup/mount/lease yaşam döngüsünü, sıralı kapanışı ve belirsiz yanıt sonrası uzlaştırmayı doğrula. Host CLI/API kullanım zinciri ve restart gözlemi sonraki P2 kapılarıdır. Seçilmiş provider/model ve çağrı/token/maliyet sınırları tanımlandığında sınırlı gerçek model kabulüne geçilir.

## İş günlüğü

- 28 Ekim 2026: Kullanıcının devam talebiyle R167 başlatıldı. R166 nihai kapanışı korundu; yeni servis installer ve runtime/dependency doğrulaması için ayrı dal/çalışma ağacı açıldı. Kaynak uygulaması, testler ve gerçek kurulum sonuçları geldikçe bu kayıt güncellenecek.

- 28 Ekim 2026: Runtime envanteri ve imzalı Node dağıtımı doğrulandı. Node için yeni ayrı hedef hazırlanıyor; mevcut 1162 dosyalık bağımlılık kümesi sağlayıcı tamlığı iddiası taşımıyor. Kurulum ve gerçek servis/model kabulü ayrı kalır.
- 28 Ekim2026: Node ve kaynak/bağımlılık kurulumu tamamlandı; iki runtime sürümü gerçek executablelardan doğrulandı. Bağımsız readback ve başlangıç kontrolleri sürüyor.

- 28 Ekim 2026: Ayrı import qualification denemesi native037 exit 2 ile reddedildi. Engellenen bind, sabit urllib3 kaynağına ve tam çağrı zincirine bağlandı; sonraki origin kontrolü ortamdan gelen sitecustomize dosyasını kabul etmedi. Native039 salt okunur başlangıç tanısı bu dosyanın ürün importlarından önce yüklendiğini gösterdi. Yeni deneme için Python başlangıcında site yüklemesini kapatan daha sıkı -S koşulu hazırlanıyor. Önceki retler korunuyor; gerçek servis/model kabulü yok.

- 28 Ekim 2026: Ayrı native042 no-site qualification exit 0 ile PASS. Sabit 15 import, kaynak kökenleri, aynı engellenmiş IPv6 yoklamasının kapanışı ve önce/sonra dosya doğrulamaları tamamlandı. Node CLI help ve bağımsız kurulum readback sonuçlarıyla birlikte yayın paketi hazırlanıyor. P2 ve production kabulü açık.
