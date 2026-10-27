# AlazHarness — status

## R164A1 — özgün servis volume kapanışı — IN PROGRESS

P1 DONE; P2 IN PROGRESS. P3–P5, tam D3B, M1 ve production OPEN.

- Aktif dal: `alaz/p2-service-closure-r164a1`.
- Aktif çalışma ağacı: `C:\Antigravity\AlazHarness\scratch\worktrees\p2-service-closure-r164a1`.
- Başlangıç ve yayımlanmış main: `28a12e1b18a839a9489a0c463d904b8e9a46db03`.
- Önceki R163 final yayın günlüğü: R163 çalışma ağacındaki
  `scratch/r163a1-publication/final-publication.json`, SHA-256
  `63525a048232d70109aa0378bf967376a96ef2e5ef0510bd8e28dd604d5cf809`.
- Önceki izlenen durumun tam kaydı: [R163 parent](docs/status-history/r164a1-parent.md).
- Native seçim: `5e3635c2cdfc2161fd20c089618bd7f2a7c12f2d`, 760 dosya.

### Amaç ve kapsam

[Entegrasyon planının](docs/P2-SERVICE-INTEGRATION-R161A1-PLAN.md) dördüncü adımı:
özgün child final/exit0/stdout-stderr EOF kanıtını aynı ServiceVolumeSupervisor
üzerindeki mevcut normal stop/finish zincirine bağlamak. Worker-only cgroup,
özgün UNMOUNTED/worker exit0 sonucu, boş cgroup, global loop bağlantısının yokluğu,
fence temizliği ve imaj lease'inin en son bırakılması aynı sahipte doğrulanacak.
Dış CLOSED yalnız zincirin bütünü normal olarak tamamlanınca üretilecek.

Status ve aynı request ID'nin tekrarı yalnız özgün işlemin kanıtını gözler.
Child sonradan tamamlanırsa yeni açık close isteği ilk volume kapanış denemesini
başlatabilir. Başlamış fakat belirsiz kalan stop/finish körlemesine yinelenmez.
Özgün child slotu, Popen/channel, worker, pin, lease ve actor referansları korunur.

### Başlangıç doğrulaması

R163 final journal beklenen hash ile eşleşti; main ve R163 feature temiz ve
28a12e1 commit'inde. Sekiz korunan depo, kökün 33 değişmiş dosyası ve önceki
R162/R161/R160 çalışma ağaçlarının durumları eşleşti. Yeni izole çalışma ağacı ve
native 760 kaynak byte'ının son kontrolü `scratch/r164a1-publication/` makbuzlarıyla
izleniyor. Başlangıçta devam eden eski mutation veya CI işi yoktur.

### Test ve yayın

R164 kaynak uygulaması, bağımsız kaynak incelemesi ve iki platformdaki odaklı
doğrulama PASS. Ürün değişikliği yalnız `gateway_supervised_service.py`,
`service_volume_supervisor.py` ve `service_control_server.py` dosyalarındadır.
Özgün genel stop/finish, worker, channel, kernel yardımcıları ve ürün JS kodu
değişmedi. Yeni 85 test; önceki kaynak/test nesilleri için dokuz exact parent
arşivi ve ayrı tarihsel çözümleyici eklendi.

| Doğrulama | Seçilen | PASS | SKIP | FAIL / ERROR | Exit |
|---|---:|---:|---:|---:|---:|
| Linux odaklı | 806 | 806 | 0 | 0 / 0 | 0 |
| Primary Windows odaklı | 806 | 626 | 180 | 0 / 0 | 0 |
| Tarihsel kaynak bağlama, ayrı Linux koşusu | 14 | 14 | 0 | 0 / 0 | 0 |

Windows atlamaları POSIX pipe, Unix socket/peer credentials, dosya metadata ve
symlink gereksinimleriyle açıkça kayıtlıdır; Linux odaklı koşusunda atlama yoktur.
İki odaklı koşu aynı 25 kaynak, 50 test/destek dosyası, runner ve sıralı 806 test
kimliğine bağlıdır; koşu öncesi/sonrası byte hashleri değişmedi. Ayrı tarihsel
14 test, odaklı 806 içinde de bulunur; toplam test sayısına tekrar eklenmez.

Kanıtlar `evidence/p2-service-closure-r164a1/` altındaki `focused-linux.json`,
`focused-windows.json`, ham loglar, `history-focused-linux.json`,
`historical-source-bindings.json`, `review-provenance.json` ve `source-check.json`.
Yeni kaynak commit/push/tam CI, kapanış commit/tam CI, main yayını ve final
integrity henüz NOT RUN. Ayrıntılı rapor:
[özgün volume kapanışı](docs/P2-SERVICE-CLOSURE-R164A1.md).
Bu paket kaynak/fixture kapsamındadır; gerçek kernel/kurulu servis veya model
kabulü değildir. Host görev erişimi ve yeni tek P2 kurulumu sonraki adımlardır.

### Kesin sonraki adım

Yalnız seçilmiş R164 dosyalarını stage et; staged tree'ye bağlı statik kontrolü,
kaynak commit/push ve exact tam CI'yi tamamla. Ardından yalnız status/rapor/kaynak
CI makbuzuyla kapanış commit'i, ikinci tam CI, yayın öncesi integrity, normal
main fast-forward/push, ayrı main verified-success reuse ve final integrity
günlüğünü kapat. Yayından sonra planın beşinci adımı, host görevlerinin aynı
kimliği doğrulanmış native API'ye dar erişimidir. Yeni tek P2 kurulumu/kernel
kabulü ve seçilmiş gerçek model/provider/toolset/bütçe deneyi açık kalır.

### İş günlüğü

- 2026-10-27 başlangıç: R163 terminal yayın kaydı ve canlı repository durumları
  doğrulandı. R164 kapanış, Unix gözlem ve tarihsel kaynak korunması ayrı dosya
  sahiplikleriyle paralel yürütülüyor. Native/model/kurulum değişikliği yok.
- 2026-10-27 ara kontrol: Linux 806/806 PASS. Windows işlemi
  `c164a101-1027-4a01-8000-000000000028` yeniden çalıştırılmadan terminal
  makbuzundan okundu: completed, exit 0, 626 PASS + 180 SKIP. Exact JSON/loglar
  geri okundu ve kaynak/test/runner kimlikleri Linux ile eşleşti. Sekiz korunan
  depo, dört önceki feature, kökün 33 değişmiş dosyası ve aktif BASE/branch tekrar
  doğrulandı; index temiz. Yayın yardımcılarının son bağımsız incelemesi sürüyor.
