# AlazHarness — R168A1 gerçek servis yaşam döngüsü

**IN PROGRESS — QA04 nihai kaynak baytlarıyla normal-04 ve lostreply-02 gerçek servis yaşam döngüsü PASS; Linux05/Windows05 sabit136 test seçimi PASS. Kaynak yayın paketi02 hazırlanıyor; commit/push/full CI henüz yapılmadı. Önceki QA03 PASS kayıtları korunuyor; normal-02 UNKNOWN açık. P1 DONE; P2 IN PROGRESS; P3–P5/M1/production OPEN.**

## Çalışma bağlamı

- Asıl worktree: `C:\Antigravity\AlazHarness\scratch\worktrees\p2-service-lifecycle-r168a1`
- Branch: `alaz/p2-service-lifecycle-r168a1`
- Başlangıç/main: `9440a2251d26db88b5f08a0e0292e73f4fbb6e57`.
- R167 kaynak yayını tamamlandı. Önceki status metni değiştirilmeden `docs/status-history/r168-parent.md` dosyasında saklandı; önceki hazırlık anındaki PENDING satırlarının son otoritesi R167 terminal seal'idir.
- R167 terminal seal SHA-256: `65693d5e1453da650422d63b30b29e5b3ed291aad753b527ed24985e08456cd8`.
- Bu worktree baseline SHA-256: `1af1f7710647f06b25d7efd8b7bb26a18d2ad9ab12476391d16c97ad12cf368f`.
- 20 korunan repository/worktree ve kökteki mevcut 33 değişiklik çalışma başında aynı kaldı. Root convenience status güncellenmedi.

## Amaç ve kabul sınırı

Aynı `/opt/alaz-r167a1` kurulumunun gerçek profile/üç store hazırlığı, gerçek broker readiness ping'i, özgün ServiceVolumeSupervisor, CLI start → READY → status → sıralı close ve kapanış gözlemi. Normal akış ve ayrı image/profile üzerindeki kayıp lifecycle yanıtı özgün owner/request ile doğrulandı; model/görev yürütme kabulü bu işin kapsamı dışında kaldı. 878 kurulu kaynak ve 1162 bağımlılık dosyası değiştirilmeyecek. Provider/model/tool yürütme bütçeleri sıfır; görev/model çağrısı yapılmayacak.

## Güncel ilerleme

| Alan | Durum | Kanıt / kalan iş |
|---|---|---|
| R167 devam zemini | PASS | F9440, tam yayın seal'i, 22 sahipli dosya doğrulandı |
| İzole R168 worktree | PASS | Native002; temiz F9440 üzerinde yeni branch; 20/33 korunuyor |
| Gerçek OS Python başlangıcı | V2 SOURCE GATE PASS | Native021 beş bağlamın gerçek kaydı; tek fark HOME=/ altında pwd built-in yokluğu. Her bağlam exact observation ile sabitlendi; bağımsız review PASS |
| Service seed / ping broker | SOURCE GATE PASS | Seed 30/30, broker 25/25 PASS; bağımsız kaynak incelemesi PASS |
| Controller / Linux transport | SOURCE + NORMAL PASS | Dar exact diagnostic incelemesi PASS; Linux04:136 PASS0skip. Gerçek normal03 start/READY/status/close/final-status ve kaynak postconditions PASS |
| Kayıp yanıt kabulü | PASS | Native043 exit0: close bir kez gönderildi, gerçek REPLY_LOST; aynı owner/request ile salt okunur final status CLOSED/3store. Native044388669B/e4f8f161… asıl makbuz hashini doğruladı |
| Windows runner / primary test | FINAL QA04 SOURCE PASS | Linux05:136 PASS/0 skip; Windows05:93 PASS/43 declared skip/0 fail/error. Tam loglar ve465 input hash/136 seçili-yürütülmüş ID birebir doğrulandı; eski04 kayıtları korunuyor |
| Gerçek normal-01 | REFUSED — PREFLIGHT | Native019 terminal exit2: bootstrap single-context contract uyuşmazlığı; service/kernel effects başlamadı. Native020 dört deneme yolunun yokluğunu doğruladı |
| Gerçek normal-02 | UNKNOWN — RETAINED | Native028: seed exit0/PASS ve üç fiziksel DB close;1265B exact SQLite DELETE uyarısı eski stderr gate tarafından reddedildi. Controller7/broker14/worker15 ve loop0 korunuyor; service hiç başlamadı |
| Salt okunur custody / bağımsız hedef | OBSERVED | Native029 kurulu878+1162 dosyayı doğruladı; Native033 eski PID/start/namespace/cgroup/fence/image/loop/mount ve broker kayıtlarını iki kez bağladı. o gözlemde normal03/QA03 yolları yoktu ve yeterli alan vardı; eski UNKNOWN kapanmış sayılmıyor |
| Gerçek normal-03 | PASS | Native040 exit0; gerçek servis READY ve normal CLOSED. Üç fiziksel store kapanışı, özgün child/worker exit0,2EOF,volume/fence/imagelease,1brokerping/0provider ve değişmez2040 kurulu dosya. Native041392108B ham sonucu26608f17… hash ile doğruladı |
| Eski UNKNOWN son custody | OBSERVED | Native046 iki başarılı denemeden sonra aynı7/337,14/670,15/719 süreçleri ve kaynakları gözlemledi; normal02 UNKNOWN, normal close/cleanup/lab-clean iddiası yok |
| Güncel QA04 gerçek kabul | PASS | Native069 normal04, native072 lostreply02 exit0; native070/073 asıl ham sonuçlar byte-exact doğrulandı. Yeni6QA kaynakları final seed/controller pinlerine bağlı; kurulu878+1162 ve runtime aynı |
| Güncel eski UNKNOWN gözlemi | OBSERVED | Native074 iki QA04 kabulünden sonra eski7/337,14/670,15/719 süreçleri ve loop0/image/fence/scope/mount aynı; normal02 UNKNOWN ve close iddiası yok |
| Yayın hazırlığı | IN PROGRESS | Primary discovery4842 unique/0test yürütme. İlkstageUNKNOWN korunuyor; native064 owned25 index çıkışı PASS. Policy02 tam policy/code/config/image eşitliği PASS. Yeni8public kanıt eski9 dosyaya ekleniyor; kaynak commit/push/fullCI henüz yapılmadı |

## Yapılacaklar

1. Son QA04 public kanıt/rapor paketini dondur; eski9public dosya ve tüm deneme/yayın kayıtlarını değiştirmeden koru. Güncel giriş: `evidence/p2-service-lifecycle-r168a1/summary-qa04.json`.
2. Sabit4.842 test seçimi ve değişmez CI policy ile kaynak/closure tam CI, ardından main fast-forward ve normal push yayınını doğrula. Bu adıma kadar tam CI sonucu NOT RUN.
3. Eski normal02 UNKNOWN kaynaklarına replay/adoption/cleanup uygulanmaz; mevcut kodda özgün owner için resume/normal-close arayüzü yok. P4 işletim/recovery açığı kaydedildi.
4. P2 gerçek görev/günlük kullanım, P3 hafıza/beceri, P4 işletim/recovery, P5 aynı aday M1/pilot kapıları açık. Provider/model/tool/bütçe seçimi olmadan gerçek model/görev kabulü yapılmaz.

## Değişiklik günlüğü

- 2026-10-28 13:35 UTC: R168 yeni branch/worktree oluşturuldu; gerçek başlangıç baseline'ı ve önceki R167 kapanış pin'i kaydedildi. Model/iş/servis/kernel kabulü henüz çalıştırılmadı.
- 2026-10-28 13:37 UTC: Kaynak incelemesi controller-main-thread ve gerçek broker ping gerekliliğini doğruladı. `-I -B` alt süreçler için ortam başlangıcını ayrıca ölçme gereği kaydedildi.

- 2026-10-28 13:58 UTC: Dört sabit hedefli seçimde 90 test PASS, 0 skip. Kısıtlı yürütücüdeki AF_UNIX EPERM ayrı gözlem olarak saklandı; izinli yürütücüde gerçek socket/ping testleri geçti. Kurulu aday kabulü henüz çalıştırılmadı. Controller, seed, broker, bootstrap, boundary ve transport bağımsız kaynak incelemeleri tamamlandı.

- 2026-10-28 14:10 UTC: Host/source review PASS. Linux fixed focus02:121 PASS/0 skip, kaynaklar aynı. Windows01:70 PASS/43 declared skip/6 error/2 failure; tam log saklandı, dört dosyada POSIX lexical fixture düzeltildi, kapsam/skip sayısı korunuyor. Normal01 prepare tamamlandı; Linux service apply henüz yapılmadı.

- 2026-10-28 14:22 UTC: Normal01 kaynak/bootstrap aşamasında terminal reddedildi, yeniden oynatılmadı. Beş gerçek actor/context gözleminde yalnız pwd built-in farkı bulundu; v2 her bağlamı ayrı exact contract ile bağlar. Eski QA01/contract ve ret raw kaydı korundu. V2 source review PASS, Linux03 124PASS0skip; Windows03 ve ayrı QA02/normal02 kabulü sırada. Ürün kurulumunda değişiklik yok.

- 2026-10-28 14:45 UTC: Windows03 tam124 seçim81PASS43declaredskip doğrulandı. normal02 terminal controller sonucu UNKNOWN; seed exit0/PASS ayrı tutuldu, servis başlangıcı yok. Native029 ve033 read-only custody kanıtları eski kaynakları koruyup yeni03 yollarının ayrılığını doğruladı. Exact üç SQLite DELETE diagnostic sınıflandırıcısı kaynak pinleri/seed close/handoff kontrolleriyle hazırlanıyor; önceki UNKNOWN yeniden sınıflandırılmıyor, replay/cleanup yok.

- 2026-10-28 14:52 UTC: Exact diagnostic kaynak incelemesi PASS, sabit136 Linux/Windows seçimi geçti; aynı465 input hash/136 ID doğrulandı. Yeni QA03/normal03 native040 gerçek lifecycle PASS, native041 asıl ham result392108B/26608f17… eşleşti. Native043 ayrı lostreply01 çalışıyor; henüz terminal iddia yok. Eski normal02 UNKNOWN açık; yayın/CI henüz yapılmadı.

- 2026-10-28 14:59 UTC: Lostreply01 native043 terminal PASS; özgün close bir kez gönderildi, REPLY_LOST sonrasında aynı owner/request final status CLOSED. Native044 asıl388669B/e4f8f161… makbuzu ve4.842 unique discovery doğruladı. Native046 eski normal02 kaynaklarını salt okunur gözlemledi: UNKNOWN değişmedi. Native047 policy/code/image digest aynı; public kanıt ve yayın hazırlığı sürüyor.

- 2026-10-28 15:34 UTC: İlk yayın gözlemi inherited iki logun yeni worktree'deki CRLF farkında reddedildi; exact BASE LF baytları SHA-CAS ile geri kondu, eski CRLF preimage'ları saklandı. Native060 yalnız aynı iki blobun Git stat önbelleğini yeniledi; logical index aynı kaldı. Native062 kaynak stage Gitadd0, ardından rapor/seed EOF boş satırı kontrolü exit2: özgün stage UNKNOWN korunuyor. Native064 yalnız sahipli25 yolu BASE index'e çıkardı; çalışma baytları20repo/33root değişikliği aynı. Seed yalnız son ikiLF trim, controller yalnız seed SHA pini, rapor yalnız sonLF trim: bağımsız review PASS. Linux05 136PASS0skip,465input aynı; Windows05 ve QA04 üzerinde yeni gerçek kabul hazırlanıyor. Commit/push/tamCI henüz yapılmadı.

- 2026-10-28 15:41 UTC: QA04 exact source doğrulaması tamamlandı. Linux05 136PASS0skip; Windows05 93PASS43declaredskip; aynı465input/136ID. Native069 normal04 gerçek yaşam döngüsü PASS; native070392242B/4e55ddcb… asıl dosyayla eşleşti. Native072 lostreply02 birclose/REPLY_LOST/özgünstatusCLOSED PASS; native073388720B/bc6470e4… eşleşti. Her iki yeni deneme kendi3store/child/worker/volume/lease kaynaklarını kapattı; kurulu2040 dosya/runtime değişmedi,0model0task. Native074 eski normal02 UNKNOWN custody OBSERVED: yeniden oynatma/adoption/cleanup yok. Native075/076 freshpolicy02 tam eşitlik PASS. Yayınpaketi02, kaynak ve closure tamCI4842, main fast-forward/normalpush sırada; henüz commit/tamCI yok.
