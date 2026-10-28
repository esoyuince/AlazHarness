# AlazHarness — R167A1 P2 servis kurulumu ve runtime doğrulaması

**IN PROGRESS — Python 3.12/Node 24 ve gerçek bağımlılık doğrulaması; ayrı servis installer ve yeni kurulum hedefi.**

P1 DONE; P2 IN PROGRESS. P3–P5, tam D3B, M1 ve production OPEN.

- Başlangıç commit: `833a40aa99f5ca7e2b2562a19e8f0c286a0adea2`.
- Aktif primary: `C:\Antigravity\AlazHarness\scratch\worktrees\p2-service-install-r167a1`.
- Dal: `alaz/p2-service-install-r167a1`.
- R166 yayını tamamlandı: source/final tam CI, main aynı-commit doğrulanmış reuse, final integrity ve terminal seal PASS. Yetkili terminal journal SHA-256 `f130d8d02050a35c0a15bfce7244ff9c57c4c42cb85f22ead9904fe206e162e8`.
- Önceki izlenen durumun exact arşivi: [r167-parent](docs/status-history/r167-parent.md).
- Aktif rapor: [R167 servis kurulumu](docs/P2-SERVICE-INSTALL-R167A1-REPORT.md).

## Amaç ve kabul sınırı

R166'nın doğrulanmış servis adayı için somut Python/Node executable kimliği, sürüm geri okuması ve 1162 gerçek bağımlılık dosyasını doğrula. Ayrı servis installer ile yeni, önceden bulunmayan bir hedef oluştur; kurulu kaynak/bağımlılık baytlarını ve kurulum kaydını bağımsız yeniden oku.

878 dosyalık mevcut adayın ürün kaynağı R165 `1600eba430562795b9114209d1168bfa0d6ea5fd`, native kaynağı `5e3635c2cdfc2161fd20c089618bd7f2a7c12f2d` olarak kalır. R166 araç yayını `833a40a` bu ürün kimliğinin yerine geçmez. Eski finite builder/installer ve kabul edilmiş R156 kurulumu korunur.

Bu dilim kaynak ve runtime kimliği/kurulum kabulüdür. Gerçek servis başlatma, kernel yaşam döngüsü, seçilmiş sağlayıcı/model ve production kabulü ayrı kapılardır. Model/provider seçimi ve harcama sınırı henüz bu çalışmaya eklenmedi.

## Son tamamlanan adım ve devam

- Başlangıç: main/R166 temiz833a40a, native temiz5e3635c2; 19 korunan depo ve kökteki33 mevcut dosya kaydedildi.
- Yeni servis installer ve kurulum/import/CLI betikleri bağımsız incelemede PASS; tarihsel yardımcılar değişmedi.
- Linux odaklı regresyon:123 RUN/123 PASS/0 SKIP. Windows windows-02:123 RUN/88 PASS/35 tanımlı Linux-only SKIP. İki koşum exit0; seçilen/çalışan kimlikler ve81 girdi sabit.
- Windows ilk koşumu LICENSE checkout CRLF/LF farkında test öncesi reddedildi. Yalnız R167 checkout'u exactGitblob LF baytlarına eşitlendi; pinler değişmedi ve ilk kayıt korundu.
- Resmi Node24.22.1 imzası/arşivi doğrulandı ve yeni ayrı lab hedefine kuruldu; Node provisioning sırasında eskiR156 makbuzu/mount durumu korundu. İlk GPG Windows/MSYS yol hatası ayrı FAIL olarak saklandı.
- Gerçek servis kurulumu native025 exit0: yeni /opt/alaz-r167a1 hedefine878 kaynak+1162 bağımlılık dosyası kuruldu. Executable hash/sürüm kontrolleri Python3.12.3 ve Node24.22.1 için PASS. Makbuz SHA256: `0ba26bfbae1a216a595baf6fb935ed18f399bcfd0ecf29aa9c14bf61bd04232f`.
- Ayrı ordinary-user readback native027 PASS, exit 0. Node CLI help native030 PASS, exit 0; 2046 bayt exact çıktı, stderr boş. Python import native029 exit 2: 15 modül yüklendi, fakat socket.bind girişimi guard tarafından reddedildi; import kabulü false. Nedeni araştırılıyor. Servis/kernel/model kabulü false. R167 source publication hazırlanıyor.
- Özel makbuz/başlangıç kayıtları: `scratch/r167-install`; kurulum girdileri ve özgün operation kayıtları: `scratch/install-candidates/service-install-01`.

## İş günlüğü

- 28 Ekim 2026: Kullanıcının devam talebiyle R167 başlatıldı. R166 nihai kapanışı korundu; yeni servis installer ve runtime/dependency doğrulaması için ayrı dal/çalışma ağacı açıldı. Kaynak uygulaması, testler ve gerçek kurulum sonuçları geldikçe bu kayıt güncellenecek.

- 28 Ekim 2026: Runtime envanteri ve imzalı Node dağıtımı doğrulandı. Node için yeni ayrı hedef hazırlanıyor; mevcut 1162 dosyalık bağımlılık kümesi sağlayıcı tamlığı iddiası taşımıyor. Kurulum ve gerçek servis/model kabulü ayrı kalır.
- 28 Ekim2026: Node ve kaynak/bağımlılık kurulumu tamamlandı; iki runtime sürümü gerçek executablelardan doğrulandı. Bağımsız readback ve başlangıç kontrolleri sürüyor.

- 28 Ekim 2026: Ayrı import qualification denemesi native037 exit 2 ile reddedildi. Engellenen bind, sabit urllib3 kaynağına ve tam çağrı zincirine bağlandı; sonraki origin kontrolü ortamdan gelen sitecustomize dosyasını kabul etmedi. Native039 salt okunur başlangıç tanısı bu dosyanın ürün importlarından önce yüklendiğini gösterdi. Yeni deneme için Python başlangıcında site yüklemesini kapatan daha sıkı -S koşulu hazırlanıyor. Önceki retler korunuyor; gerçek servis/model kabulü yok.
