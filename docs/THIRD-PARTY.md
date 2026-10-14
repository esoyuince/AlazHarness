# Kaynak kökeni ve lisans kayıtları

Ana kaynaklar, orijinal Git geçmişleri ve lisans dosyaları korunarak vendor altında tutulur. Başlangıç commit ve dosya hash'leri sources.lock.json içindedir.

| Proje | Resmî kaynak | Kullanıcı fork'u | Korunan lisans |
|---|---|---|---|
| OpenClaw | openclaw/openclaw | esoyuince/openclaw | vendor/openclaw/LICENSE — MIT, Copyright 2026 OpenClaw Foundation |
| Hermes Agent | NousResearch/hermes-agent | esoyuince/hermes-agent | vendor/hermes-agent/LICENSE — MIT, Copyright 2025 Nous Research |

OpenClaw THIRD_PARTY_NOTICES.md kaynakta korunur. Diğer dosya/paket bildirimleri de kaynak ağacıyla birlikte korunur. Bu kayıt bütün geçişli bağımlılıkların veya modellerin lisans incelemesinin tamamlandığı anlamına gelmez.

AlazHarness original contributions are licensed under the root MIT LICENSE. Upstream licenses and copyright notices remain unchanged. When extracting a module, preserve its source commit, license, attribution and change history.

## Selected component copies

`packages/upstream/openclaw/` and `packages/upstream/hermes/` retain the respective
upstream LICENSE files. `components.lock.json` records every copied source path,
commit, original hash, target hash and the single import-path relocation.
`packages/upstream/README.md` documents the supported subset and unused optional
transport path. This is not a claim that full upstream applications or every
transitive dependency have been licensed/audited by the component tests.
