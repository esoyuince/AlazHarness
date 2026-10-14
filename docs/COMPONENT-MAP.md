# İlk bileşen haritası — sabit kaynaklar

Kapsam: başlangıç kaynak taraması. Tam bağımlılık çözümlemesi veya çalışan entegrasyon kabulü değildir. Kaynak kodu değiştirilmedi; listeleme ve belirtilen bölümler okundu.

| Kaynak | Sabit commit |
|---|---|
| OpenClaw | `2dcbb6138d57dccfcd54f2f908ef9f38268b1229` |
| Hermes Agent | `eb75627faf532fa6ffbdae59a0d14b0b385fc780` |

## Gözlenen giriş noktaları

| Parça | Yerel kaynak kanıtı | MVP kararı / henüz doğrulanmayan |
|---|---|---|
| Harness seçimi | OpenClaw `src/agents/harness-runtimes.ts:18-60`; plugin runtime seçimi ve `resolveConfiguredModelHarnessRuntime` | ADAPT adayı; Hermes adapter kaydının doğru sözleşmesi HYB-001'de çıkarılacak |
| Uyanma | OpenClaw `docs/gateway/heartbeat.md:15-25` | Belgeye göre heartbeat Automations zamanlayıcısına bağlı; ayrı fallback timer yok. Hermes'e bağlanan tetik hattı test edilmedi |
| Model/araç yürütme | Hermes `run_agent.py:1-24`; `agent/turn_*.py` dosyaları | TAKE adayı. `run_agent.py` import sırasında bootstrap ve kesilmiş update kurtarma yoluna giriyor; saf yan etkisiz kütüphane importu varsayma |
| Programatik giriş | Hermes `website/docs/developer-guide/programmatic-integration.md:9-17,37-60` | ACP, TUI JSON-RPC ve HTTP aynı AIAgent çekirdeğini farklı kapsamlarla dışa açıyor. Öncelikli deney TUI/ince adaptör; henüz seçim kesin değil |
| TUI uygulaması | Hermes `tui_gateway/server.py:24-52` | Profile/env/secret scope, state ID, subprocess ortamı ve transport bağımlılıkları gözlendi. Başlık dosyasını tek başına kopyalamak yeterli değil |
| Hedef komutu | Hermes `hermes_cli/goal_command.py:1-23`; `hermes_cli/goals.py` mevcut | Paylaşılan komut işleyicisi hedef state'ini değiştiriyor; yetkilendirme ve dönen prompt'u zamanlama adaptör sorumluluğunda |
| Hedef sürekliliği | Hermes `website/docs/user-guide/features/goals.md:9,24-39,60-79` | Belgeye göre /goal tek oturumlu; Kanban ile aynı şey değil. ACP /goal sunmuyor. Çok oturumlu uzun vadeli gündem ayrıca tasarlanacak |
| Hafıza ve state | Hermes `agent/memory_manager.py`, `agent/memory_provider.py`, `hermes_state.py` mevcut; AGENTS.md:20-26 | TAKE adayı; dosya varlığı uçtan uca doğru çalıştığını kanıtlamaz. Prompt cache korunarak oturum sınırı seçilmeli |
| Beceri üretimi | Hermes `tools/skill_manager_tool.py`, `tools/skill_provenance.py`, `tools/skill_usage.py` mevcut | TAKE adayı; beceri dosyası sayısı yerine bağımsız tekrar kullanım ölçülecek |

## Birleşimde öncelikli riskler

TUI belgesi (programmatic-integration.md:58-60) canlı oturuma bağlanma ile kaydedilmiş transcript'i yeniden açmayı ayırıyor; aynı session'a iki gateway sürecinin yazması veya süreç yeniden başlayınca prompt kabulünün kalıcı olması garantisini vermiyor. Bu yüzden kendi adaptörümüzde kabul/çalıştırma/sonuç kimlikleri ve kesinti uzlaştırması açık olmalı.

Aynı belgenin 88-101. satırları approval/clarify isteklerinin normal olay değil server-to-client JSON-RPC istekleri olduğunu açıklıyor. Sadece çıktı event'lerini geçirmek yeterli değildir; desteklenmeyen istekler açık hata vermeli.

OpenClaw paketinin prepare/postinstall betikleri var. Hermes import/bootstrap yolları mevcut profile dokunabilir. HYB-001'de izole state ve yan etki yüzeyi incelenmeden tüm kurulum veya agent entrypoint çalıştırılmayacak.

## HYB-001 çıktısı

Her TAKE/ADAPT/OMIT seçimi için dosya, sembol, doğrudan bağımlılıklar, lisans, mevcut ilgili test ve bizim entegrasyon testini listele. Tek küçük fake-model turu için gereken en dar gerçek kaynak bileşenlerini seç. Yeni sosyal ağ veya sıfırdan yeni model döngüsü yazma.

## HTTP contract candidate — isolated branch

This branch investigates Hermes native `/v1/runs` as an alternative to the initial
TUI candidate. See `docs/HYB-002-HTTP-CONTRACT.md` for exact wire symbols, source
reuse, negative tests and limitations. It does not supersede work concurrently
present on `alaz/hyb-001-component-slice` until the two candidates are reconciled.
