# AlazHarness — status

Son güncelleme: 16 Ekim 2026. Her devamda canlı dal/HEAD/CI kontrol edilir.

## Güncel nokta

**HYB-005D2 dar Linux .txt entegrasyonu yayımlandı; exact-code CI1163/1163 PASS.**
Gerçek Hermes dosya okuma yolu mevcut admission/izin/bütçe denetimlerinden sonra
Linux izole araç sürecine bağlandı. Son kodla8/8 native senaryo,4fiziksel araç
konteyneri ve yerel+sunucu1163/1163standart test doğrulandı. Kod e6cb7f1;
ana kodun CI sonucu success. Son belge HEAD/CI her devamda canlı sorgulanır.
Tek entegrasyon/yayın sahibi247a.
Aktif dal: alaz/hyb-005d2-native-tool-247a.
Aktif çalışma ağacı: C:\Antigravity\AlazHarness\scratch\worktrees\main-6f88.
Başlangıç HEAD fb3d7ca7fec3b5e0242a8e7c174b553dbfe366d8; temiz ve exact CI success.
Önceki tam durum docs/history/2026-10-16-STATUS-BEFORE-HYB005D2-247a.md.
Kök eski korunmuş dalda; yalnız status.md erişim kopyası eşitlenir. Main değişmez.

## Güncel kabul ve sınırlar

D2 kabulü yalnız açıkça yapılandırılmış Linux .txt okuma yolu içindir. Son
native8senaryo ve1163standart test ayrıdır;101yeni test1163içindedir. Başarı,
ret,iptal,zaman aşımı ve yalnız açıklama üreten completed görevler ayrılır.
İzolasyon eksik veya yanlışsa required-client görev göndermez;imaj yoksa host
fallback olmaz. Native durdurma/canlı izin iptali çalışan konteyneri kapatır;
rezervasyonlar otomatik iade edilmez. Mevcut ledger/oturum sahibi korunur.

Provider kimlik bilgisi/ağ sınırı,Windows ağ kabulü,parent-hard-crash takeover,
gerçek sağlayıcı token/fiyat doğrulaması,hafıza/beceri transferi ve tamM1/M2 açık.
Sistem paketleri/kişisel profil/firewall/daemon ayarı değiştirilmedi;özel Linux
test ortamında native PM frozen bağımlılık hazırlığı yapıldı. Ücretli/model0.

## Başlangıç günlüğü — aşağıdaki eski NOT RUN/FAIL kayıtları tarihsel kanıttır

İlk kaynak incelemesinde mevcut agent list kontrol edildi;bu projeye bağlı uygun
çalışır ajan yoktu. Başka proje ajanlarının iptal edilmiş izinleri canlandırılmadı.
İlk NOT RUN ve başarısız deneyler sonraki kabulün yerine geçmez;aynı şekilde
son başarı da eski başarısız makbuzları silmez. Güncel özet yukarıdadır.

### 2026-10-16T22:01:43.825241+03:00 — HYB005D2 QA d65f başlangıç

Canlı247a entegrasyon/yayın sahibi korunuyor;d65f yalnız ayrı QA test/rapor/kanıtı
üretecek, ürün dalı/native batch/commit açmayacak. Öncelik: gerçek native handler
paritesi; canonical admission+scope+generation; izin/bütçe reddinde hiçbir host
fallback olmaması; native tools/interrupt.py thread ve acting_for_tid iptalinin
doğru taşınması. İlk plan docs/research/HYB-005D2-QAD65F.md. Testler NOT RUN.
Kök32dosya başlangıç hashleri runtime/hyb005d2-qad65f/start.json; sır/model0.

### 2026-10-16T22:03:55.567750+03:00 — HYB005D2 QA d65f native iptal bulgusu

Gerçek pinned tools.interrupt modülü mevcut prepared Python ile8senaryoda
çalıştı;8beklenen gözlem eşleşti. is_interrupted acting_for_tid kontrol eder,
run_if_not_interrupted yalnız kendi threadini kontrol eder: aktarılan worker
iptali görse de callback çalışabilir. Bu D2 bug kanıtı değil, bağlamada dikkat
edilecek upstream davranışı; sole veto olarak kullanma. Kanıt
evidence/hyb-005d2-qad65f/native-interrupt-observation.json; yeni Gateway/tool/
container/model0, bütün QA threadleri kapandı. Ürün247a tek yazıcı korunuyor.

### 2026-10-16T22:09:08.457551+03:00 — HYB005D2 QA d65f gerçek dispatch imzası

Kaynak ön bulgusu: pinned model_tools._execute_tool satır827–839 read_file
için registry.dispatch kwargs yalnız task_id/session_id/user_task veriyor;
parent_agent göndermiyor. Yeni isolated_read.invoke parent_agent zorunlu
tuttuğundan gerçek yol native_cancellation_unavailable reddi üretebilir.
Test fixture parent_agent eklemiş; gerçek native çağrı imzasıyla doğrulama
gerekiyor. İptal thread-context kaynağı kullanılmalı; ürün247a düzeltir.
Ayrıca reserved ticket sonrası quarantine ve generation değişimi retleri
QA tarafından test ediliyor; henüz bu son ikisi doğrulanmış bulgu değil.

### 2026-10-16T22:09:50.794197+03:00 — D2 ilk bağlama

Native terminal-environment provider yolu seçildi; isolated_read.py ve optional
execution_boundary entegrasyonu yazıldı. Mevcut native file handler/canonical
ledger yeniden kullanılıyor.37 yeni synthetic-port sözleşme testi37/37 PASS,
kaynak drift0; gerçek Hermes/Docker aynı zincir henüz NOT RUN. Sonuçlar
evidence/hyb-005d2/read-initial*. Kişisel state/anahtar/host ayarı değiştirilmedi.

### 2026-10-16T22:10:55.406827+03:00 — HYB005D2 QA d65f 7 regresyon

Gerçek isolated_read/ledger + sentetik SQLite/native/Docker portları30test:
23PASS/7FAIL exit1/drift0. I01(2):reserved ticket sonrası quarantine kontrol
edilmiyor. I02(3):admission_id biçimi ve çağrı başı id/generation sabitleme yok;
entry sonrası id/generation değişse de execute oluyor. I03(2):completed+exit1
ve tool_failed+exit0 çelişkileri kabul ediliyor. Değişmeyen testler
tests/test_isolated_read_qad65f.py; kanıt evidence/hyb-005d2-qad65f/initial-*.
Ürün247a düzeltmesi bekleniyor; bu testler gerçek native/Docker kabulü değil.
Önceki parent_agent eksik gerçek dispatcher kwargs uyarısı da raporda.

### 2026-10-16T22:12:31.836620+03:00 — QA d65f native dispatcher gözlemi

Gerçek model_tools._execute_tool + native approval ContextVars + kayıtçı registry
portu:kwargs gerçekten task_id/session_id/user_task;parent_agent yok. ID/context
eşleşti,restore edildi. Fakat modül importu7subprocess denemesi yaptı ve guard
hepsini engelledi;genel deney FAIL olarak korunur. Bu sonuç imza gözlemini
destekler,temiz full native kabulü değildir. Çalışan tool/Gateway/network/model0.
Kanıt native-dispatch-observation.json; önceki8native interrupt gözlemi ayrıdır.

### 2026-10-16T22:14:24.294796+03:00 — QA d65f değişmeyen7regresyon kapandı

Ürün247a düzeltmesiyle aynı30QA testi30/30 PASS,exit0/drift0. Test/fixture SHA
722b7876... ilk7FAILle birebir aynı. Quarantine,admission id/generation
sabitlemesi ve exit/outcome çelişkileri ret. Kanıt recheck-run.json/.txt; ilk
FAIL korunur. parent_agent gerçek dispatch uyuşmazlığı ayrı açık başlıktır.
Bu recheck gerçek Gateway/Docker değil; ürün yazıcısı yine247a.

### 2026-10-16T22:16:35.845632+03:00 — QA d65f native-imzalı iptal köprüsü

Ürün _NativeInterruptSource eklendi;gerçek dispatcherda eksik parent_agent yerine
approval session/call context ve yakalanmış current/acting threadID kullanıyor.
14ek sentetik-port test14/14 PASS exit0/drift0:parent olmadan dispatch shape,
acting iptal,yabancı context,başka thread polling,sibling ayrımı,kalıcı iptal.
Önceki30test aynı hashle korunur. QA kaynakları sabitlendi;44offline QA testi,
8native interrupt gözlemi ve dispatch-import-guard FAILi ayrı kapsamlar.
Tam Gateway/container bağlaması henüz bu sonuçlarla kabul edilmez.

### 2026-10-16T22:17:40.936977+03:00 — QA d65f tam standart kontrol

44QA testi ve kaynak-iptal gözlemleri hazır;yalnız QA dosyaları stage edildi.
Bağımsız tam discovery şimdi başlıyor;code/config dosya seti+hashleri baş/son
karşılaştırılacak. Bu anda henüz PASS değil. Makbuz354bb8cc-f6d6-4386-a7a0-61b792ab56db
lane d65f180c-d7d6-4fc4-9533-5ecd8a943745. Yeni native script eklenirse final
snapshot sayılmaz; eski sayılar taşınmaz. Product/Git247a tek sahibi.

### 2026-10-16T22:19:18.566584+03:00 — QA d65f tam tur kaynak değişimi

1143/1143 unittest exit0/skip0; ancak koşuda host-gate-client.mjs ve
host_gate_plugin.py değiştiğinden full-standard.json NOT_ACCEPTED. Eski yeşil
son-kaynak kabulüne taşınmaz.44QA testi bu1143içinde. Gerçek native entegrasyon
ve yeni istemci şartları tamamlanınca sabit kaynakla tam tur gerekecek.

### 2026-10-16T22:19:29.484598+03:00 — D2 özel Linux ortamı

İlk geniş kaynak arşivi120s deadline doldu; etkiler okundu, remote klasör yoktu.
Daha dar3724 public Python/config dosyası v2 arşiviyle aktarıldı ve hashleri aynı.
Native PM frozen build yalnız /tmp/alaz-hyb005d2-247a/prepared altında özel
Python/bağımlılık ortamı kuruyor; sistem paketleri/kişisel HOME/daemon değişmez.
Hazırlık makbuzu edb9d5a5-2b9d-4efd-8821-9f309c01f0b8; model/ajan çalıştırmaz.

### 2026-10-16T22:21:12.928225+03:00 — QA d65f zorunlu izolasyon istemcisi

Gerçek HostGateClient+loopback fetch8/8 bağımsız kontrol PASS:eksik/yanlış/bool
izolasyon bildirimi ve dispatch öncesi downgrade reddediliyor;iki required header
gidiyor,tek dispatch,ham/v1/runs fallback0. Kanıt client-run.json/.txt; native
Gateway değil. QA artık52 benzersiz offline test;eski1143tura bu8eklenmez.
Yalnız yeni QA dosyaları stage edildi;nihai tam suite/code-commit247a sahibinde.

### 2026-10-16T22:21:55.858584+03:00 — QA d65f Linux hazırlık salt-okuma bulgusu

Server prepared/build-receipt.json exit1,parent_reaped=true. stderr gerçek
native pm/runtime.py _inputs içinde source/pm/uv.lock FileNotFoundError gösteriyor.
Dar source arşivinde nested lock dosyası eksik;native PM pinini değiştirmek veya
frozen kapatmak yerine orijinal pinned pm/uv.lock ve gereken kaynak veri
dosyalarını manifestli aktarmak gerekir. QA serverda yalnız makbuz okudu,
hazırlığı tekrar başlatmadı veya native kaynak değiştirmedi.

### 2026-10-16T22:25:30.244682+03:00 — QA d65f ikinci tam tur

1163test exit0/skip0;koşuda isolated_read.py ve execution_model_fixture.py
değişti,second-full-standard.json yine NOT_ACCEPTED. Final native/probe+ürün
kaynakları sabitlenince tam suite gerekecek;QA tekrar tekrar aktif kod üstünde
full tur başlatmayacak.52QA ret testi önceki hedefli makbuzları ayrı korunur.

### 2026-10-16T22:30:15.837426+03:00 — D2 Linux native başlangıç

Eksik orijinal pm/uv.lock eklendikten sonra frozen hazırlık exit0; Python ve
bağımlılıklar yalnız özel prepared-v2 altında. İlk gerçek Linux Gateway hazır
oldu ve temiz kapandı; test fixture plugin entries/settings yolunu yanlış
yazdığı için dedicated route404 verdi, iş kabulü yok. Fixture mevcut native
kontrata düzeltildi; ilk FAIL saklanır. Yeni native normal denemesi başlamış
durumda; ürün/test dosyaları hâlâ değişiyor, full-suite freeze ilan edilmedi.

### 2026-10-16T22:30:20.604016+03:00 — QA d65f ilk native deneme teşhisi

trial-normal-1 gerçek Gateway hazır,pid83504,çıktı0/reaped;client capabilities
host_http_404. Native stderr explicit_host_policy_required ve bilinmeyen
alaz_isolated_read backend. Kaynak hermes_cli.plugins.PluginContext.get_config
plugins.entries.<id>.settings.<key> okuyor. Yeni probe ise plugins.<id> altına
yazıyor. Mevcut run_native_execution_gate.py:40 doğru entries/allow_tool_override
True/settings(policy,execution) şekliyle yeniden kullanılmalı. Deneme sonucu
FAIL korunur;fallback yapılmamış. QA serverda yalnız hata makbuzu/kaynak okudu.

### 2026-10-16T22:44:19.712764+03:00 — D2 native son-aday matrisi

trial-normal-2 gerçek Gateway+native dosya aracı+Docker PASS;1iş/1read budget/
1konteyner/2kontrollü sağlayıcı isteği;native result+admission+ticket eşleşti.
Yeni v3 matrisi8senaryo sıralı:normal,tool-limit,missing-isolation,wrong-backend,
missing-image,cancel-native,timeout,live-revoke. Son üçü test için mevcut imajdan
ağsız üretilen8s gecikmeli Python imajıyla çalışır;ürün fallback değildir.
Makbuz f950fe59-711c-4473-b48a-616f4f1aa3d4; snapshot integration-v3.
Bu matriste ürün kodu sabit;tam suite henüz final kabul değil.

### 2026-10-16T22:48:48.633983+03:00 — D2 son-aday yerel/native kabul

Son sabit kod/config/test197dosya:1163/1163 PASS exit0/skip0/drift0.101yeni test
(37bridge+12client+52bağımsızQA)1163içinde. Native integration-v3 sekiz gerçek
Gateway koşusu8/8beklenen davranış:normal,tool-limit,eksik izolasyon,yanlış
backend,eksik imaj,native stop,deadline,canlı allowlist iptali.4fiziksel araç
konteyneri kapandı/kaldırıldı;diğer retler konteyner açmadı. Native stop interrupted,
canlı revocation failed;timeout/ret sonrası açıklama completed olabilir ama araç
başarısı DEĞİL. Bütçe iadeleri yok. Sekiz eski koşu ayrıca SQLite/transcript/
container exactID ile readonly8/8teyit;bu8yeni koşu değildir. Kanıt evidence/hyb-005d2.
Test türetilmiş slowimage exactID kaldırıldı,baseimaj korundu. Native PM ile
yeni bağımlılıklar yalnız özel Linux prepared-v2 alanına kuruldu;ücretli/model0.
32legacy kök dosya ve4pinli upstream temiz/korundu. Main değişmedi. Rapor
docs/HYB-005D2-NATIVE-TOOL.md. Git/CI için tek yayın sahibi247a; henüz exact
commit CI PASS iddiası yok. Sıradaki D3: provider credential/egress sınırı;
parent-hard-crash takeover,Windows native ağ,hafıza-transfer,M1/M2 açık.

### 2026-10-16T22:53:13.222236+03:00 — D2 yayın ve aynı-kod CI kapanışı

Kod commit: e6cb7f16016548c8bea7275f4ac3c987d6fad71b. Feature dalına push ve
yerel/remote eşitlik doğrulandı;GitHub alaz/local-ci success. Server makbuzu
sha==checkout_sha bu exactcommit:executed1163/passed1163/failed0/skipped0/
suite_errors0,status_delivery posted. Kanıt evidence/hyb-005d2/code-ci.json.
Sekiz Linux native Gateway koşusu ve4gerçek araç konteyneri ayrı opt-in
deneylerdir,standart CI içinde tekrar çalışmadı. Tam1163suite ile aynı197
kod/config/test dosyası korunuyor; bu kapanış belge/makbuz değiştirir.

Son belge commit kendi CI ile ayrıca doğrulanır. Ana dal değiştirilmedi;32kök
legacy dosya ve4upstream pin temiz/korundu. status.md kök erişim kopyası eşit.
Kesin sonraki iş HYB-005D3 provider kimlik bilgisi ve zorunlu dış ağ sınırı.
Parent hard-crash/container takeover,Windows ağ,gerçek sağlayıcı token/fiyat,
hafıza/beceri transferi,tamM1/M2 AÇIK. Gateway ana süreci henüz güvenilmeyen
koda karşı izole edilmiş sayılmaz;bu kabul yalnız bounded native read yoludur.

### 2026-10-16T22:54:31.408505+03:00 — Durum belgesi üst özeti

Başlangıçtaki NOT RUN koşulları tarihsel günlük başlığına ayrıldı;üst bölüm
güncelD2 kabulünü ve açıkD3/M1/M2 sınırlarını gösteriyor. Bu yalnız belge
düzeltmesidir;kod/config/test/kanıt sayıları değişmedi.
