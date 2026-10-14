# AlazHarness

OpenClaw + Hermes bileşenlerinden hibrit ajan harness'i; ardından kendi gündemini seçen otonomi katmanı.

Varsayılan çalışma klasörü: `C:\Antigravity\AlazHarness`.

## Başlangıç

1. `CURRENT-STATE.md`: doğrulanmış durum, engeller ve sıradaki iş.
2. `docs/MVP-v0.1.md`: ilk MVP kapsamı ve kabul koşulları.
3. `docs/WORKSPACE-RULES.md`: dosya düzeni ve Git çalışma kuralları.
4. `sources.lock.json`: kaynak commit'leri ve fork ilişkileri (hazırlık sırasında oluşturulur).

## Dizinler

- `vendor/`: özgün geçmişleri korunan, commit'e sabitlenen OpenClaw ve Hermes forkları.
- `packages/`: AlazHarness'e ait adaptörler ve daha sonra otonomi katmanı.
- `docs/`: tasarım, kararlar, bileşen haritası ve çalıştırma notları.
- `scripts/`, `tests/`, `config/`: tekrar üretilebilir hazırlık, doğrulama ve sır içermeyen örnek ayarlar.
- `evidence/`: küçük, sır içermeyen doğrulama kayıtları.
- `runtime/`, `artifacts/`, `scratch/`: Git dışı çalışma durumu, çıktılar ve geçici dosyalar.

Durum: hazırlık aşaması. Henüz çalışan hibrit veya otonom ajan teslim edilmedi.

## Open source / local setup

Original AlazHarness code is [MIT licensed](LICENSE). See [upstream notices](docs/THIRD-PARTY.md).

```sh
git clone https://github.com/esoyuince/AlazHarness.git
cd AlazHarness
python -B scripts/restore_sources.py --apply
python -B -m unittest discover -s tests -v
python -B scripts/ci_check.py
```

Preparation checks require Python 3.11+ and Git, but no model key.
Source restore does not install or start agents.
[CI scope](docs/CI.md) / [Contributing](CONTRIBUTING.md) / [Security](SECURITY.md).
