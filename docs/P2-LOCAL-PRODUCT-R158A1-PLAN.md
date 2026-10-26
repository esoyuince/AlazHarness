# P2 / R158A1 — Günlük yerel kullanım başlangıç paketi

## Amaç ve hazır temel

P1 R156 finite + R157 readiness kabulleriyle tamamlandı. Sıradaki ürün çıkışı:
tek profil için başlat → görev ver → izle → sonuç/kullanım gör → iptal et → kapat.
Hermes canonical admission/result ve mevcut HostGateClient/HermesRunsClient
korunur. İlk gerçek görev, açıkça seçilmiş model ve bütçeyle izinli küçük bir
metin dosyasını okuyup kullanılabilir yanıt üretir.

Bu belge bir kaynak/uygulama planıdır. R157'de listener, CLI veya gerçek model
kabulü yapılmadı; P2 OPEN. Plan, P1'in 35/60/15 saniyelik QA yaşam döngüsünü
günlük kullanım servisi olarak sunmaz.

## İlk okunacak mevcut dosyalar

Primary'de dosya/simge keşfi doğrulandı. Tam davranış incelemesi sonraki iştedir.

| Alan | Mevcut kaynaklar |
|---|---|
| İstemci bileşenleri | `packages/claw-hermes/host-gate-client.mjs`, `packages/claw-hermes/hermes-runs.mjs` |
| Mevcut operatör/QA istemcileri | `scripts/native_host_gate_client.mjs`, `scripts/native_gateway_client.mjs`, `scripts/native_execution_client.mjs`, `scripts/gateway_recovery_client.mjs` |
| Harness yaşam döngüsü | `gateway_prepared_consumer.py`, `gateway_consumer_api.py`, `host_gate_plugin.py` |
| Sağlayıcı/araç/bütçe | `execution_boundary.py`, `provider_broker.py`, `execution_budget.py`, `broker_budget.py`, `host_report.py` |
| Native API/listener | `gateway/session_api.py`, `gateway/platforms/api_server.py`, `api_server_prepared.py`, `api_server_borrowed.py`, `api_server_runs.py`, `api_server_run_observation.py` |
| Native stop ve fiziksel iş | `gateway/session_authority.py`, `session_runtime_workers.py`, `session_pending_controls.py`, `session_api_turn.py` |
| Yerel çalışma/model | `gateway/session_local.py`, `session_cli_turn.py`, `hermes_cli/local_runtime/endpoint.py`, `agent/secret_sources/command.py` |

Native kaynak kökü:
`C:\Antigravity\AlazHarness\scratch\worktrees\hermes-finite-close-f135c6`,
commit `d1516731308de8e87130dc68124e69aad35d6911`.
Harness kısaltılmış Python dosyaları `packages/claw-hermes/` altındadır.
Dosyanın repoda bulunması kurulu pakete dahil veya ürün akışına bağlı olduğu
anlamına gelmez; paket closure farkı ayrıca doğrulanır.

## Uygulama sırası

1. Mevcut istemciler ve handler'ları tam oku; komut → fonksiyon → endpoint/IPC
   → terminal durum eşlemesini çıkar. QA scriptlerini ürün CLI'si gibi varsayma.
2. Native listener sahibi, adres/kimlik doğrulama, admission açılışı, stop isteği
   ve fiziksel worker sonlanmasını aynı kaynakla bağla. Mevcut borrowed adapter
   publication listener başlatmaz; `observe_api_turn` gözlemcisi shield edilir.
3. Mevcut bileşenlerle ince yerel kontrol katmanını uygula. Yeni görev kuyruğu
   veya ikinci kalıcı sonuç otoritesi oluşturma. Aynı request ID aynı canonical
   işe bağlansın; bağlantı kaybı yeni hesaplama veya sahte iptal yaratmasın.
4. Orijinal üç store, epoch, profile/image lease ve kapanış sırasını koruyarak
   ürün yaşam döngüsünü bağla. Aktif veya belirsiz iş varken temiz kapanış gösterme.
5. Seçilen modelin kaynak/secret-source closure'ını ve gerçek broker rotasını
   doğrula. Çağrı, token ve mikro-USD tavanlarını başlamadan görünür yap.
6. Kaynak/birim kabulünden sonra P2'nin seçilmiş kaynaklarından üretilmiş tek
   güncel ürün kurulumunda gerçek kullanıcı akışını
   ve tek sınırlı model görevini kabul et; sonuç/kullanım ve iptal semantiğini kaydet.

## P2 kabul ölçütleri

- Tek start, tek native owner; task sonucu kalıcı admission/result ile aynı.
- Aynı request tekrarında yeniden hesaplama yok; farklı ID yeni iş oluşturur.
- İzleyici/CLI bağlantısı kesildiğinde işin durumu kaybolmaz; tekrar gözlem aynı işe bağlanır.
- Cancel gerçek native stop yolundan geçer; iptal istendi, terminal durdu ve
  durumu belirsiz sonuçları ayrıdır.
- Bütçe dolduğunda yeni fiziksel provider çağrısı açılmaz; kayıp yanıtın
  rezervasyonu kendiliğinden iade edilmez; bilinmeyen kullanım sıfır gösterilmez.
- Kapanış admission seal → işin terminal durumu → runtime/API retirement →
  detach → fiziksel store close → lease release sırasıyla doğrulanır.
- Gerçek model, izin verilen dosya/araçla kullanışlı çıktı üretir.
  Scripted fixture sonucu gerçek model kabulünün yerine geçmez.

P3–P5 ve tam M1/prod kabulü bu paketten ayrıca izlenir. Mevcut hafta tahminleri
ölçülmüş teslim tarihi değildir; P2 bağlantısı ve ilk gerçek görev süresi
görüldükten sonra yeniden değerlendirilir.

Dayanak: [R157 raporu](M1-INSTALLED-READINESS-R157A1.md),
[yol haritası](PRODUCT-ROADMAP.md),
[kaynak keşfi](../evidence/m1-installed-readiness-r157a1/p2-source-discovery.json).
