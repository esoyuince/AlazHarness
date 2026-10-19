# AlazHarness

OpenClaw + Hermes bileşenlerinden hibrit ajan harness'i; ardından kendi gündemini seçen otonomi katmanı.

Varsayılan çalışma klasörü: `C:\Antigravity\AlazHarness`.

## Başlangıç

1. `status.md`: güncel dal, çalışma ağacı, doğrulanmış durum ve kesin sonraki iş. CURRENT-STATE.md tarihseldir.
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

Durum: deneysel geliştirme tabanı. Seçilmiş OpenClaw/Hermes bileşenleri, gerçek Hermes Agent/Gateway araç turu, kesinti incelemesi ve açık yerel operatör kapanışı dar kapsamlarıyla doğrulandı. Model yanıtları kontrollü test sağlayıcısıdır. Tam M1, üretim güvenliği, gerçek-model kabulü ve M2 otonomi henüz tamamlanmadı.

## Open source / local setup

Original AlazHarness code is [MIT licensed](LICENSE). See [upstream notices](docs/THIRD-PARTY.md).

```sh
git clone https://github.com/esoyuince/AlazHarness.git
cd AlazHarness
python -B scripts/restore_sources.py --apply
python -B -m unittest discover -s tests -v
python -B scripts/ci_check.py
```

Tests require Python 3.11+, Node 24+ and Git, but no model key.
Source restore does not install or start agents.
[CI scope](docs/CI.md) / [Contributing](CONTRIBUTING.md) / [Security](SECURITY.md).

## First component demo (not an autonomous agent)

```sh
python -B scripts/demo_hybrid.py
python -B scripts/verify_components.py
```

This runs copied OpenClaw lifecycle code and Hermes transport/budget code across
real Node/Python processes with an explicitly scripted test peer. No model or
agent tool is called. [Scope, API and next boundary](docs/HYB-001-COMPONENT-SLICE.md).

## Integrated transport candidates

The reviewed stdio component slice and HTTP candidate now share one source tree
and provenance manifest. `python -B scripts/demo_hybrid_mock.py` exercises the
HTTP contract; `python -B scripts/demo_hybrid.py` exercises stdio.
Ten upstream payloads (including two licenses) live under packages/upstream.
See [integration decisions](docs/HYB-003-INTEGRATION.md). A scripted transport
peer is not evidence of real AIAgent execution.

## Platform design: portable core, Linux-first sandbox (PLAT-001)

The hybrid control plane is intended to run on Windows, Linux and macOS,
with Linux-native isolated execution supplied by explicit platform
adapters. Node 24 is the portable integration layer; the selected
Hermes engine remains the first M1 runtime. Windows/WSL2 uses a
separately verified Linux guest rather than silently running tools on
Windows. On Apple Silicon, a trusted remote Linux x86_64 worker or a
separately ported Linux ARM64 guest is a future option, not current
support: the existing security guard requires Linux x86_64.

A side-effect-free route inspector is available today:

~~~sh
node scripts/inspect_platform.mjs --mode=guarded
node tests/node/platform-cases.mjs all
~~~

The inspector returns NOT_ACCEPTED and **does not start any agent,
VM, WSL bridge, real provider or sandbox**. Test scenarios for macOS
and ARM64 simulate host descriptions, not physical-device acceptance.
Architecture: [ADR-0004](docs/adr/0004-portable-core-linux-security.md);
[platform support matrix](docs/PLATFORM-COMPATIBILITY.md).
Full D3B and multi-OS deployment remain future acceptance gates.

## Development baseline

`main` is the reviewed integration baseline, not a production release. Keep new
work in short feature branches; record exact test/CI scope before merging.
See [integration workflow](docs/INTEGRATION-WORKFLOW.md) and [current status](status.md).
