# R157A1 — Güncel kurulumda readiness ve P1 kapanışı

## Sonuç

**R157 native readiness PASS; birleşik P1 kabulü DONE.** R156'nın kabul edilmiş
kurulumunda, ayrı yeni bir ext4 imajı ve özgün supervisor yaşam döngüsüyle seed
epoch 1 → readiness epoch 2 → normal stop/finish tamamlandı. R156'nın finite
normal/replay/yeni/hata kanıtı aynı kurulum için korunur. Yeni runtime kurulmadı,
runtime kodu değiştirilmedi, finite deneme tekrarlanmadı.

P1, kurulum/supervisor/native iş bağlantısının kabulüdür. P2–P5, gerçek model,
servis/genel admission, restart replay, tam D3B, M1 ve production kabulü açıktır.
[R157 ham sonucu](../evidence/m1-installed-readiness-r157a1/image001/result.json)
ve [birleşik P1 kaydı](../evidence/m1-installed-readiness-r157a1/p1-acceptance.json)
bu ayrımı açık alanlarla taşır.

## Kaynak ve kurulum bağı

| Kimlik | Değer |
|---|---|
| QA başlangıç commit'i | `cdc974728e69f590838b82421cd244e36554a74f` |
| Kurulu harness kaynağı | `e641a5000810efb2a453ae847f689b422f7d41a7` |
| Native kaynak | `d1516731308de8e87130dc68124e69aad35d6911` |
| Mevcut kurulum | `/opt/alaz-r156a1`, özel `AlazHarness-D3B-P71C` laboratuvarı |
| Dosyalar | 838 kaynak = 81 harness + 756 native + 1 bağımlılık envanteri; 1.162 bağımlılık |
| Kurulum kökü | device/inode `2096/29702` |
| Receipt SHA-256 | `a4bcc0f27d29f27f08c55d3a65eaa102a503a7da12d4672253f0245fd5d4f845` |
| R157 execution binding | `11fa244a48ff250115264428bb39d0f5dd5364c0fa5ca05e2ca8d05baf76e577` |
| R157 intent | `995225a4262b807450226ed252ed4bdc5a9e9cb8f40313ef6acd37aa26bbd72a` |
| R157 result | `5bd9879c71d3c2ee2e45762899892f51195068937cf1d30108d5c32127f33426` |
| Birleşik P1 kaydı | `3a62514022e0b21f94d0ee6cf07ed74d89e470bb1f73d96965611aabc35bf6aa` |

R156 ve R157 sonuçlarının installation nesneleri bütün alanlarıyla eşittir.
R157 caller, imaj oluşturmadan önce mevcut kurulu kaynak ve bağımlılıkları
özgün verifier ile tekrar okudu. Sonradan çalışan ortak kanıt doğrulayıcısı bu
kayıtları ve Git kaynaklarını inceler; yeni bir canlı kurulum kontrolü çalıştırmaz.

Özgün source-only installation binding/receipt baytları ve eski kapsam alanları
değişmedi. Yeni kabul ayrı R157/P1 kayıtlarına yazıldı. Eski R155 readiness
sonucunun yeni kuruluma devralındığı iddia edilmez.

## Yapılan değişiklikler

- `scripts/qa/r157a1_prepare.py`: sabit R155 şablonlarını ve R156 kurulum/proof
  girdilerini doğrulayıp dört açık QA kaynağı üretir.
- `r157a1_accept.py`, `r157a1_linux_accept.py`, `r157a1_linux_transport.py`
  ve `r157a1_seed_child.py`: ayrı taze R157 alanlarına bağlı tek readiness denemesi.
  Özgün readiness, ownership, stop/finish ve unknown-custody algoritmaları korunur.
- `tests/test_r157_preparation.py`: değişmiş kaynak/proof/receipt, yanlış kapsam,
  yeniden bağlanmış proof, frozen girdi değişimi, tekrar yürütme ve yanlış
  başarı/epoch/kapanış kayıtlarının reddi.
- `evidence/m1-installed-readiness-r157a1/verify_p1.py`: iki gerçek kabulün
  bağlarını ve paketlenmiş 81 harness dosyasının kesin Git blob baytlarını okur.
  Runtime, WSL, kurulum veya model çağrısı yapmaz.

Özgün R156 producer ve ordinary driver değişmedi. Altı accepted ordinary001
dosyası ayrı okuma kapsamında, boyut ve SHA-256 ile sabittir. Yeni girdi yalnız
producer, seed boundary ve readiness caller içerir; finite helper içermez.

## Gerçek native deneme

Tek Bridge request:
`53c00157-2ce9-4eea-9b9f-61beef0377f2`.
26 Ekim 2026 09:03:47 UTC'de başladı; 09:04:52 UTC'de terminal exit 0/PASS gözlendi.
Aynı request takip edildi; ikinci deneme veya otomatik cleanup yapılmadı.

Yeni alanlar `/opt/alaz-r157a1-accept-input`, `/srv/alaz-r157a1`,
`/sys/fs/cgroup/alaz-r157a1` ve `/tmp/alaz-ipc-r157a1`.
64 MiB imaj inode'u 31972; R156 finite imajı inode 31956 ve ayrı yoldadır.
Her deneme kendi içinde tek özgün supervisor ve aynı imajı kullanır.

| Aşama | Kanıtlanan sonuç |
|---|---|
| Seed | PID 11/start ticks 2300, parent PID 7; epoch 1; altı kontrol; 29.658 ms |
| Readiness | PID 16/start ticks 5542; epoch 2; altı kontrol; özgün owner CLOSED |
| Kaynak kimliği | Aynı profile `1792:12`, DB kimlikleri `1792:26/30/31`; mount namespace `4026532224` |
| Normal kapanış | Worker 10 UNMOUNTED; volume CLOSED; owned users ve loop bağlantısı yok; fence kaldırıldı; lease en son bırakıldı |
| Host etkisi | Mount namespace ve mount tablosu değişmedi |
| İş kapsamı | Görev/model/listener sıfır; servis, admission ve finite work açılmadı |

17 frozen dosya ve dört yürütme dosyası olmak üzere 21 dosyalık kanıt kümesi
korunur. Ham stdout → transport → caller → seed/readiness sonuçları, 10 gömülü
stream'in boyut/hashleri ve PID/start bağları bağımsız olarak doğrulandı.
`observedAfterUnknown=false`, `originalRetainedVolumes=[]`; çözülmemiş bir
R157 etkisi yoktur. Host kaydındaki `partialStatePreserved=true` saklanan
dosyalara ilişkindir; burada belirsiz terminal sonuç anlamına gelmez.

Outer stderr boş. Seed ve readiness iç stderr'i ayrı ayrı 1.265 bayttır:
üç veritabanı için SQLite DELETE-mode seçimi uyarıları. Handoff'taki
`journal_mode=delete` aynı modu kaydeder. Uyarılar ham kanıtta korunur;
SQLite yükseltmesi veya tamamen boş child stderr iddia edilmez.

## P1 neden tamamlandı?

| P1 kapısı | Özgün kanıt |
|---|---|
| Güncel kurulum ve kaynak kimlikleri | R156 kurulum + R157'nin aynı kurulu baytları yeniden doğrulaması |
| Task-free readiness ve kapanış | R157 ayrı taze lifecycle, seed 1 → readiness 2 → normal close |
| Normal / aynı isteğin tekrarı / yeni iş / kontrollü hata | R156 finite; hesaplama sayıları 1/1/2/3 |
| Aynı isteğin tekrarında yeniden hesaplama olmaması | R156 normal/replay aynı admission, request ID ve sonuç hashleri |
| Özgün native owner/consumer/store/lease kapanışı | İki native sonuç ve özgün close sözleşmeleri |
| Kaynak değişmeden ortak kabul | Paketlenmiş 81 harness Git blob'u kaynak e641, QA HEAD ve manifest ile aynı |

Finite model factory/hesaplama/close scripted fixture'dır. Gerçek native
API/authority/worker/persistence çalışmıştır; bu sonuç gerçek sağlayıcı veya
genel servis kabulüne dönüştürülmez.

## Doğrulamalar ve yayın

- Kaynak ve yaşam döngüsü incelemesi: PASS.
- Linux hazırlık birim testleri: 22/22 PASS, 5,217 saniye; gerçek native kapsamı yok.
- Windows hazırlık testleri: 22 çalıştı, 21 PASS, 1 platform skip, 0 hata; 35,689 saniye.
- Gerçek candidate manifest/archive doğrulaması ve kaynak üretimi: PASS.
- Frozen intent/bundle/proof incelemesi: PASS; özgün host tam envanteri apply öncesinde yeniden doğruladı.
- Tek native deneme: exit 0/PASS.
- Birleşik P1 ve 81 paketlenmiş Git blob karşılaştırması: PASS.
- Yerel staged static gate: PASS — 6.641 dosya, 3.976 test keşfi, exit 0; bu tarama testleri çalıştırmaz.
- Exact-commit `alaz/local-ci` ve normal main fast-forward yayını:
  son commit oluşturulduktan sonra yayın günlüğünde doğrulanır.

İlk ortak kaynak kontrolü, Windows checkout'taki LICENSE CRLF baytlarını paket
LF baytlarıyla doğrudan karşılaştırdığı için reddedildi. Git blob ve manifest
hashleri baştan aynıydı. Düzeltilen kontrol kesin blob baytlarını karşılaştırır,
checkout'ta yalnız bu LF/CRLF farkını kabul eder ve paket yollarında temiz Git
diff ister. Yalnız LICENSE etkilendi. İlk doğrulayıcı ve başarısız source-only
çıktı saklandı; bu olay yeni native deneme yaratmadı.

Yayının son terminal makbuzu aktif R157 worktree'deki
`scratch/r157a1-publication/final-publication.json` dosyasıdır. Bu belgenin
içinde bulunduğu commit'in canlı CI durumu, Git referansları ve makbuz birlikte
kontrol edilir. Git yayını kurulu servise dağıtım değildir.

## Sonraki kesin iş

[P2 / R158 başlangıç paketi](P2-LOCAL-PRODUCT-R158A1-PLAN.md): mevcut istemci ve
native listener/stop sahipliğini doğrulayıp günlük yerel akışı bağlamak.
R156'daki `agent.secret_sources.command` paketleme kaydı, gerçek model için
gerekli closure ile ele alınır. Ücretli gerçek model denemesinden önce seçilmiş
model ve açık çağrı/token/maliyet bütçesi gerekir. P3 kalıcılık/hafıza, P4 arıza
ve işletim, P5 aynı kaynakta M1/pilot açık kalır.

## Kanıt dizini

- [Başlangıç ve korunan dosyalar](../evidence/m1-installed-readiness-r157a1/baseline.json)
- [Kaynak hazırlığı](../evidence/m1-installed-readiness-r157a1/preparation001/preparation.json)
- [Yürütme bağı](../evidence/m1-installed-readiness-r157a1/preparation001/execution-binding.json)
- [Windows testleri](../evidence/m1-installed-readiness-r157a1/checks/preparation-tests.json)
- [Kaynak incelemesi](../evidence/m1-installed-readiness-r157a1/source-review.json)
- [Frozen girdi incelemesi](../evidence/m1-installed-readiness-r157a1/frozen-input-review.json)
- [Native kanıt incelemesi](../evidence/m1-installed-readiness-r157a1/native-review.json)
- [R157 sonucu](../evidence/m1-installed-readiness-r157a1/image001/result.json)
- [R156 finite sonucu](../evidence/m1-native-finite-r156a1/image001/result.json)
- [Birleşik P1 kabulü](../evidence/m1-installed-readiness-r157a1/p1-acceptance.json)
- [Güncel devam kaydı](../status.md)
