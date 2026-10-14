# Hazırlık ve yeniden açma

Varsayılan kök: `C:\Antigravity\AlazHarness`.

## Her oturum başında

`CURRENT-STATE.md` ve `docs/MVP-v0.1.md` oku. Ana depo ve iki kaynakta `git status` kontrol et. Kullanıcı değişikliklerini ezme.

## Yerel doğrulama

Kök dizinde, Python standart kütüphanesiyle:

```powershell
python -m unittest discover -s tests -p 'test_*.py' -v
python scripts/verify_workspace.py --deep
python scripts/verify-source-snapshot.py
python scripts/restore_sources.py
```

Son komut yalnız plan gösterir. `--apply` açıkça verildiğinde kayıttaki submodule commit'lerini indirir/açar; paket kurulumu yapmaz. Kaynak veya parent Git kaydı kirliyse önce değişiklikleri incele. Mevcut doğrulama raporları evidence/bootstrap altındadır.

## Kaynak stratejisi

İki resmî repo esoyuince hesabında public fork olarak oluşturuldu. Yerel kaynaklar vendor altında commit'e sabitlenen Git submodule'dür. origin fork'a, upstream resmî kaynağa bakar. upstream push adresi devre dışıdır; bu bir Git yanlış hedef korumasıdır, güvenlik sandbox'ı değildir.

Klonlar depth=1 ve main kaynak ağacını içerir: tüm güncel izlenen dosyalar yereldedir; geçmiş commit ve bütün branch/tag arşivi indirilmiş değildir. Geliştirme dalı `alaz/mvp-0.1` yerelde hazırdır; mevcut main tabanı değiştirilmeden korunur. İlk kaynak değişikliğinden önce bu dala geçilir.

Ana AlazHarness deposu şimdilik yereldir. Yeni bir GitHub ana proje deposu oluşturulup yayımlanmadı. İki fork GitHub'dadır. Ana depo için uzak yedek henüz yoktur.

## Araç sürümleri

- Node 24.19.0; OpenClaw kaynak koşulu `>=24.16.0 <25 || >=26.1.0`.
- OpenClaw packageManager pini pnpm 12.9.0 ve SHA512 bütünlük değeri. Global pnpm 11.6.0 değiştirilmedi.
- Projeye özel pnpm yolu: runtime/toolchains/pnpm-12.9.0. Betikler `scripts/setup-openclaw-pnpm.ps1` ve `scripts/pnpm-openclaw.ps1`.
- `setup-openclaw-pnpm.ps1` sadece paket yöneticisini yerel alana kurar/doğrular. Mevcut kaynak packageManager bütünlük pinini kontrol eder. Agent bağımlılıklarını kurmaz.
- Python 3.14.3 ve uv mevcut. Hermes pyproject alt sınırı legacy updater için 3.11 görünse de kaynaktaki yorumlar gerçek desteklenen runtime'ı 3.14 olarak belirtiyor.
- Windows PATH'inde Docker bulunmadı. WSL Ubuntu listelendi; WSL içi geliştirme ortamı/izolasyon henüz test edilmedi.

Kaynak paket kurulumları, build ve gerçek model deneyi HYB-001 sonrası, gerekli en küçük bileşenler ve izole state belirlendiğinde yapılacak. Global araç sürümü yükseltme veya kullanıcının mevcut ~/.hermes / ~/.openclaw state'ini kullanma.

## Durum ayrımı

M0 hazırlık denetimi kaynak/Git/dizin/belge tutarlılığını ölçer. M1 çalışan hibrit ve M2 otonomi henüz kabul edilmiş değildir. Örnek konfigürasyon dosyası çalışan bir izin/bütçe mekanizması değildir.
