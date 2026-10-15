# AlazHarness — status

Son güncelleme: **15 Ekim 2026**. Bu dosya iş başlangıcı, ara kontrol ve iş sonu için ana devam kaydıdır.

## Kaldığımız yer

**REF-PI-001 dar kapsamlı gerçek Pi çalıştırma deneyi tamamlandı. Sıradaki iş REF-PI-002: Pi Durable kabul / kesinti / yeniden oynatma deneyi.**

M0 hazırlık tamam; **tam M1 hibrit kabulü ve M2 otonomi hâlâ açık**. OpenClaw–Hermes yerine başka motor seçilmedi. Pi ve OpenCode, yararlı parçaları değerlendirmek için kapsama alındı. Dört ayrı ajan döngüsü kurmuyoruz; tek harness ve tek yetkili oturum sahibi hedefleniyor.

## Doğru çalışma klasörü ve dal

| Alan | Kayıt |
|---|---|
| Varsayılan çalışma alanı | `C:\Antigravity\AlazHarness` |
| Bu devam zincirinin aktif çalışma ağacı | `C:\Antigravity\AlazHarness\scratch\worktrees\ref-pi-001-ac97` |
| Aktif dal | `alaz/ref-pi-001-native-ac97` |
| Son doğrulanmış geliştirme commit'i | `99e2a4f210ea713e2d121505f52272a40c6641e3` |
| Repo | `esoyuince/AlazHarness` — public, MIT |
| Son geliştirme commit'inin CI durumu | `alaz/local-ci: success`; bu kayıt yazılırken GitHub API'den yeniden okundu |
| `main` durumu | Geliştirme paketleri henüz `main` ile birleştirilmedi |

Kökteki eski `alaz/hyb-001-component-slice` çalışma ağacı, kullanıcıya/eşzamanlı çalışmalara ait commit edilmemiş dosyalar içeriyor. **Sırf eski CURRENT-STATE.md öyle diyor diye HYB-001'i yeniden başlatma; kökte reset/clean/stash veya toplu commit yapma.** Önce yukarıdaki aktif çalışma ağacının canlı durumunu doğrula.

Bu dosyanın Git'te izlenen sürümü aktif dalın kökündedir. Varsayılan kökteki `status.md`, aynı devam kaydının kolay erişim kopyasıdır. İş sonunda kendi güncellemeni doğrula ve iki kopyayı, dış değişiklik yoksa eşitle; sessizce başka bir işin kaydının üzerine yazma. Yeni bir aktif dal seçilirse bu tabloyu ve kökteki kopyayı birlikte güncelle.

## Yapılan işler

| İş / kilometre taşı | Sonuç ve kapsam | Git / kanıt |
|---|---|---|
| M0 başlangıç | Çalışma alanı, ilk MVP taslağı, OpenClaw/Hermes forkları ve sabit kaynaklar hazır. | `bb86dc9`; `docs/MVP-v0.1.md`, `sources.lock.json` |
| Açık kaynak ve sunucu CI | MIT yayın, GitHub remote ve alaz-server Local CI kuruldu. | `dcd809d`, `58b210a`; `evidence/publication/2026-10-15.json` |
| HYB-001/002 bileşenleri | OpenClaw/Hermes kaynak dilimleri ve stdio/HTTP sözleşme testleri birleştirildi; tek kaynak ağacı ve kilit. | `99d6fe1`; `config/components.lock.json`, `evidence/hyb-003/` |
| Gerçek Hermes araç turu | Gerçek AIAgent ve read_file çalıştı; model yanıtları kontrollü yerel HTTP taklidi. | `evidence/hyb-003/native-file-read.json`, `native-budget-summary.json` |
| Pi/OpenCode incelemesi | Resmî kaynaklar indirildi, commit ve dosya hash'leri sabitlendi; ilk bileşen değerlendirmesi yazıldı. | `3bf5305`; `docs/research/PI-OPENCODE-REVIEW.md`, `config/research-sources.lock.json` |
| REF-PI-001 | Gerçek Pi Agent + sağlayıcı ayrıştırması + yerleşik read; 6 senaryo × 2 tekrar = 12/12 yerel PASS. | `99e2a4f`; `docs/research/REF-PI-001-NATIVE.md`, `evidence/ref-pi-001/` |

Kanıt yolları aktif çalışma ağacına göredir. Başka bir daldaki aynı dosya adı aynı içeriği/sonucu garanti etmez. Eski başarı sayıları yeni deneye eklenmez.

## Son doğrulama ve sınırları

- **Standart testler:** son geliştirme paketinde yerel 146/146; aynı commit için sunucuda 146/146, başarısız ve atlanan test yok. Yerel kayıt `evidence/ref-pi-001/local-validation.json`; son sunucu/Git teslim özeti varsayılan kökün `runtime/pi-ref001-ac97/FINAL-STATE.json` dosyasında.
- **Gerçek Pi deneyi:** 6 farklı senaryo, iki tekrar, 12 başarılı çalışma. Normal okuma, olmayan dosya, model beklerken iptal, tek tur, istek sınırı, kesilmiş araç çıktısı. `evidence/ref-pi-001/native-suite.json`.
- **Ayrım:** 12 yerel Pi çalışması, 146 standart testin içinde değildir. Sunucu standart CI'sı gerçek Pi motorunu kurup çalıştırmadı.
- Model yanıtları yerel taklit; gerçek model çıkarımı, ücretli model çağrısı veya otonom gündem döngüsü çalıştırılmadı. Test kontrolü üretim güvenlik/para garantisi değildir.
- Hermes `max_iterations=1` sonrası özet/yeniden deneme çağrıları olabilir. Pi deneyindeki ekstra istek engellemesi genel bağlantı hatasına dönüşebiliyor; test kontrolünde `request_budget_exhausted` nedeni ayrıca korunuyor. Tur sayısı tek başına maliyet sınırı değildir.

## Açık işler ve sıradaki kesin adım

**Öncelik REF-PI-002 — NOT RUN.** Sabitlenmiş Pi Durable API'sini ve ilgili upstream testleri oku; ayrı profil/depolama ile şu durumları test et: aynı requestId + değişmiş içerik, iş kabulü ile dış etki/sonuç kaydı arasındaki kesinti, güvenli olmayan tekrar, bekleyiciyi iptal ile işi iptal ayrımı, depolama hatası ve yeniden açma. Dış etki sayacını ajanın kendi beyanından bağımsız tut. Hermes'in oturumuna ikinci bir yazıcı ekleme.

**Diğer açık kapılar:** OpenCode REF-OC-001 izin/olay testleri; gerçek Hermes Gateway / SessionAuthority / APIServerAdapter zinciri; tam OpenClaw girişi; bütün sağlayıcı/yardımcı çağrıları kapsayan istek-token-para bütçesi; işletim sistemi izolasyonu; hafıza/beceri transferi; sınırlı gerçek model kabulü. M2 bunların yerine geçen bir gösteriyle kapatılmaz.

**Bekleyen uzlaştırma:** Paralel bir Pi paketi `alaz/ref-pi-001` dalında, `c31cf19260675cc991f9caf07af45442611085e6` commit'inde görüldü; çalışma ağacı `scratch/worktrees/review-pi-opencode-46cc`. O dalın CURRENT-STATE.md kaydı 154 standart test ve 11 farklı yerel senaryo bildiriyor. Bunlar bu daldaki 146 / 12 sonuçlarıyla birleştirilmedi ve bu belge işi sırasında yeniden çalıştırılmadı. İlgili kod/kanıt farkını incelemeden merge, üzerine yazma veya toplama yapma. `alaz/hyb-003-integration-46cc` üzerindeki `26b1b90` da ayrı araştırma kaydıdır.

## Kaynaklar ve yerel ortam

| Kaynak | Sabit commit | Varsayılan kökten konum |
|---|---|---|
| OpenClaw | `2dcbb6138d57dccfcd54f2f908ef9f38268b1229` | `vendor/openclaw` |
| Hermes | `eb75627faf532fa6ffbdae59a0d14b0b385fc780` | `vendor/hermes-agent` |
| Pi | `b06c1f2cf1dea6af8748ddeee18c23587d2cb7c6` | `scratch/research-sources/20261015-pi-opencode-46cc/pi` |
| OpenCode | `3943b84ef00e83dbc3c48e6a92b02f0d88fb35f9` | `scratch/research-sources/20261015-pi-opencode-46cc/opencode` |

Pi'nin hazırlanmış ayrı ortamı `runtime/pi-ref001-ac97`; Hermes'in ortamı `runtime/hermes-hyb003-46cc`. Bağımlılık kurmak/ajan çalıştırmak bu durum belgesi işinin parçası değil. Kişisel profiller, API anahtarları ve özel sunucu ayarları bu dosyada tutulmaz.

## Yeni sohbet veya bağlantı kesintisinden devam

Önce `status.md` ve `AGENTS.md`, sonra aktif işin raporu ve `docs/MVP-v0.1.md` okunur. Canlı Git durumunu doğrulamak için:

```powershell
cd C:\Antigravity\AlazHarness\scratch\worktrees\ref-pi-001-ac97
git status --short --branch
git log -3 --oneline
git worktree list
```

Gerekli olduğunda standart test komutları:

```powershell
python -B -m unittest discover -s tests -v
python -B scripts/ci_check.py
python -B scripts/verify_components.py --with-vendor --source-workspace C:\Antigravity\AlazHarness
```

Bunlar komut kaydıdır, otomatik çalışma talimatı değildir. Kesintide yarım kalan işlem için önce makbuz, process/run kimliği ve dosya/Git etkisini incele; bilinmeyen sonucu otomatik yeniden çalıştırma. Eski araç sessionId'si yeni yetki değildir.

## Her işte kayıt düzeni

İşe başlarken iş kimliği, amaç, aktif dal/çalışma ağacı, başlangıç commit'i ve durum yazılır. Önemli ara sonuç veya kesintide gerçekten tamamlanan en son adım ve belirsizlik kaydedilir. İş sonunda yapılan/değişen dosyalar, test komutu-kapsamı-sayıları-exit kodu, kanıt yolu, commit/push/CI durumu, engeller ve kesin sonraki adım güncellenir.

`PASS`, `FAIL`, `NOT RUN`, `BLOCKED`, `IN PROGRESS`, `UNKNOWN` birbirinden ayrılır. Özellikle mock/native, yerel/CI ve kod/test/makbuz ayrımı korunur. Başlık özeti güncellenir; aşağıdaki iş günlüğü eski sonuçları silmeden yeni kayıtla büyütülür. Uzarsa eski bölüm `docs/history/` altında tarihli belgeye taşınır ve buradan bağlanır. `CURRENT-STATE.md` eski ayrıntılara erişim içindir; bu dosyayla yarışan ikinci güncel durum kaydı yapılmaz.

## İş günlüğü

### 2026-10-15 — STATUS-001 — Kalıcı devam kaydı

**Durum: DONE — dokümantasyon ve yerel doğrulama.** Kullanıcının istediği kalıcı devam kaydı oluşturuldu. `status.md`, `AGENTS.md`, `CURRENT-STATE.md`, `docs/WORKSPACE-RULES.md` güncellendi; eski durum metinleri silinmedi. Aktif çalışma ağacı, ana devam zinciri, paralel paket uyarısı, kanıtlar ve REF-PI-002 sonraki adımı kaydedildi.

Belge bağlantıları, temel commit referansları, iki status kopyasının eşitliği, eski metnin korunması, depo yayın kontrolü ve `git diff --check` PASS / exit 0. Bu belgelerin güncellenmesi için 146 ürün/yardımcı testi veya 12 native deney tekrar çalıştırılmadı; yukarıdaki sayılar son geliştirme paketinin kanıtlarıdır. Belge commit'inin push/CI sonucu gerektiğinde `git log -1 -- status.md` ile bulunan tam commit üzerinden sorgulanır; önceki yeşil sonuç yeni commit'e taşınmaz.

Bu iş yalnız dört belgeyi kapsar. Yeni ürün kodu, model çağrısı, bağımlılık kurulumu, upstream güncellemesi veya main merge yok. Kökteki önceden mevcut 29 dosyanın içerik hash'leri korunmuştur. Sıradaki geliştirme işi REF-PI-002; paralel Pi paketi uyumluluğu okunmadan üzerine yazılmaz.
