# AlazHarness — status

Son güncelleme: 2026-10-17T13:08:14.323885+03:00

## Güncel nokta

R1B2-REQUEST-AF13 yerel/gerçek Linux dar kabul PASS; commit/push tamam.
Kod commit: d8628aa614236b80022780ea1d79c05cf9fb72cb
Kod alaz/local-ci SUCCESS (GitHub status56589060219,10:06:44Z).
Bu son belge/durum commitinin kendi CI kontrolü yayından sonra ayrıca yapılır.
Aktif dal: alaz/r1b2-request-view-af13
Aktif çalışma ağacı: C:\Antigravity\AlazHarness\scratch\worktrees\request-r1b2-af13
Başlangıç commit: e2a5b300568425358e181954cffb697ace2d032b.
1595/1595standart PASS exit0/skip0;235ölçülen kaynak aynı/yeni0.
84yeni standart=68primary+16independent;35optinQA ayrı PASS/toplama eklenmez.
6finalnative PASS:5Dockerread,10scriptedprovider,12process clean;5container/6socketyok.
8manifest/3kaynak-inclusion;250satır4166raw→20satır594tool→11679byte gerçekrequest.
prepared→handoff_armed→broker_response_observed; handoff niyet fiziksel-send kanıtıdeğil.
After-tool bağlantıkopunca kaynak-inclusionkalır ama response/validatedfalse.
InitiatingRunIdNULL/modelProcessingfalse; profile request taskcost değildir.
Aynı DBowner/claim/egress,record_request_view:true optin; yeniDB/kuyruk/izinyok.
G01filesystemsilence,D3BOSsınırı,realmodel/fiyat/token,R2,HYB006,M1/M2 AÇIK.
Rapor docs/R1B2-REQUEST-VIEW.md; evidence/r1b2-request-af13 ve r1b2-qa-9b08.
Ana dal/pinler/önceki araştırmalar ve çalışma ağaçları değiştirilmedi.

## İş günlüğü

### 2026-10-17T12:20:57.284640+03:00 — başlangıç

Canlı status/Git kontrolüyle temiz e2a5b30 bazından ayrı worktree açıldı.
Agent listte uygun Alaz ajanı yok; diğer projelerin/revoked ajanları kullanılmaz.
Önce provider boundary/egress/source-capture gerçek APIleri incelenecek.
Ürün yazıcısı AF13; test sırasında kaynaklar sabitlenir, doc/evidence ayrı kalır.
Main ve önceki çalışma ağaçları değiştirilmez.

### 2026-10-17T12:22:11.426733+03:00 — R1B2 bağımsız QA 9B08

AF13 ürün alanı eşzamanlı açılırken 9B08 başlangıç preconditionı ret verdi;
hiçbir eski durum üzerine yazılmadı. 9B08 ayrı alaz/r1b2-qa-9b08 dalı
ve scratch/worktrees/request-r1b2-qa-9b08 alanında yalnız test/kanıt/rapor
hazırlayacak; ürün APIyi okur, ürün kaynakları ve mevcut63QA testler değişmez.
Ürün/yayın sahibi AF13 kalır; 9B08 root devam adresini değiştirmez.

### 2026-10-17T12:23:52.431541+03:00 — 9B08 R1B2 sözleşme incelemesi

Mevcut provider HTTP sınırı profil-scoped; body.user/modelmessage kendi
başına request-run authority değildir. QA, source→payload inclusion ile
provider-request job ownership ayrımını özellikle denetleyecek. Send/commitACK/
unknown/refund ve duplicate sameID+content ambiguity negatifleri bekler.
Ayrı rapor request-r1b2-qa-9b08/docs/research/R1B2-REQUEST-QA-9B08.md.
Yeni API henüz yok; test uydurulmadı. Product AF13 tek sahibi kalır.

### 2026-10-17T12:26:16.168174+03:00 — 9B08 baseline transport10/10 PASS

Ayrı QA dalında test_request_transport_qa_9b08.py hazır: nested caller mutasyonu,
Unicode/CRLF exact digest, sahte proof opaque, commitfail/lostACK/cancel/IPC
kaybı ve aynı ticket replay kontrolleri10/10PASS. Bu R1B1 tabanı gerçek
ledger/client +sentetikIPC kapsamı; henüz R1B2 kabulü değil. Ürün API hazır
olunca onun üstüne ayrı testler yazılacak. Test dosyası QA ağacında, primary
tests veya ürün dosyalarına müdahale edilmedi.

### 2026-10-17T12:31:02.555362+03:00 — R1B2 ilk ürün API hazır, NOT TESTED

request_view.py prepare_in_transaction(conn,ledger,grant,payload), arm_handoff(ledger,ticket),
observe_response(ledger,armed,raw,status,content_type), enrich_request_views(conn,section,context,policy).
Execution setting record_request_view:true strict bool, broker şart; default false.
BrokerClient.send(...,record_view=True); egress authorize aynıtxde prepare kaydı.
prepared→handoff_armed→broker_response_observed. Handoff write-ahead NIYET, fiziksel
send kanıtı DEĞİL. Başarılı signed broker reply sonrası rawresponse hash kaydı;
provider body-validation/settlement ayrıca. Commit/lostACK rezervasyonu geri vermez.
Profile-scoped request; initiatingRunId=None. Kaynak exact toolID/hash/bytes ancak
prepare sırasında tek trusted returned+settled capture ile bağlanır. Report:
providerRequestViews ve refs.providerRequestInclusions; modelVisibility UNKNOWN.
9B08 ayrı QA APIyi artık okuyabilir; eski63test değişmez, ürün tek yazıcısı AF13.
Bu aday henüz syntax compile dışında NOT TESTED; native/CI/PASS iddiası yok.

### 2026-10-17T12:39:56.137550+03:00 — R1B2 birim/native hazırlığı

İlk46yeni request/capture/broker test PASS; eski81provider regression PASS.
Bunlar sentetikowner/IPC, native değildir. Gerçek origin rawrequest hash/byte
ölçümü eklendi; after-tool-disconnect senaryosu ikinci ağyanıtını koparıyor.
Linux candidate-v1 kaynakları hashli transfer edildi. İki native koşu başlıyor:
normal ve after-tool-disconnect; makbuz d25a3b75-2b21-4148-924e-7c840476a318.
Yol /tmp/alaz-r1b2-af13/v1-*. Bu adayın native sonucu henüz NOT RUN;
tekrar başlatmadan makbuz/sonuçlar okunmalı. 9B08 ayrı QA yeniAPIyi okuyabilir.

### 2026-10-17T12:40:51.076000+03:00 — 9B08 request-view29/29 bağımsız QA PASS

Candidate-v1 exact ürünkopyası üstünde gerçek API29test PASS. Test scripti
scratch/worktrees/request-r1b2-qa-9b08/scripts/qa/test_request_view_9b08.py;
ALAZ_R1B2_QA_SOURCE ile hedef seçilir. İlk27PASS/2FAIL test injection COMMITten
önce kapanıyordu; yalnızhelperdüzeltildi,29testAST/assertionaynı. İlkFAILkaydı
ve eskihelperkorundu; ürün kusuru diye sunulmaz. Baseline16+API29 ayrıdır.
Primary bu testleri final frozen source üstünde aynıscriptle tekrar edebilir;
9B08 ürün/pin/source değişikliği yapmadı. Final native/CI henüz bizim QA kabulü değil.

### 2026-10-17T12:42:47.189008+03:00 — ilk native iki durum PASS

Candidate-v1 normal ve after-tool-disconnect PASS; iki rapor JSON/textCLI
PASS. Her ikisi2provider/1izoleread, toplam4realprocess cleanexit. İlk normal
174bayttoolçıktısı ikinci gerçek wire isteğinin metadatahashine bağlandı;
aynıikinciistek bağlantıkoptuğunda handoff_armed ve responsefalse/usageunknown.
Origin-side rawrequesthash kayıtları ürün requestDigest/byteCount ile eşit.
Yeni68ownoffline test PASS (46+22); eski81providerregression ayrı.
9B08 gerçekAPI29PASS notu okundu; dosyası ayrıQAağacında, final kaynakta ayrıca
çalıştırılacak. Şimdi final6native kapsamı/tamstandart ve yayın sabitlemesi.
Bu iki koşu sonraki finaltekrarın toplamına eklenmez; modelçıkarımı/ücret0.

### 2026-10-17T12:46:17.819306+03:00 — 9B08 35API/HTTP QA ve2native bağımsız teyit

AyrıQAda29API+6actualHTTP-handler opt-in test35/35PASS, frozen-v1kaynak.
16baselineQA1527full içinde;35opt-inhenüzprimarytoplamınaparçadeğil.
İki v1Linux profili ürünproofhelperkullanmadan nativeDB/sourcecapsule/actual
originbytehash/174bayttoolID eşleşmesiyle CORROBORATED;144sourcepin ve
2DockerexactID/2socketkapanışteyidi. Normalresponseobs,aftertooldisconnect
handoff_armed/responsefalse. YeniNative/model0. QAkarşılaştırıcı
request-r1b2-qa-9b08/scripts/qa/corroborate_request_native_9b08.py.
Testler final-test-custody.json ile51toplam(16baseline+35opt-in)sabit.
İlk2injectionfixtureFAILkorundu, ürünkusuru değil. Finalprimarykaynağı/native
profillerhazıroluncasamescriptlerle9B08ayrıteyit; ürüntekAF13yazıcısı.

### 2026-10-17T12:46:53.269327+03:00 — R1B2 final kaynak sabitlemesi

68primary yeni test ve16bağımsızbaseline standart keşfinde;9B08 opt-in29API+6HTTP
ayrı çalıştırıldı35/35PASS, assertion kaynağı değiştirilmedi. Opt-in35ana
standart sayısına dahil değildir. Yeni ürün/kaynak testleri artık sabitlenecek.
publication-source-freeze.json kapsamıyla full standart ve6nativefinal sırada.
Ürünsha request_view29cc8a80, providerprobe5b8bffd7. 9B08 son nativeyi kendi
read-only scriptiyle kontrol edebilir; ekstra koşu modeli başlatmak yok.
Sonraki geçici Linuxcode /tmp/alaz-r1b2-af13/publication-v2 ve pub-* olacaktır.
Önceki2nativePASS ayrı adaykanıtı olarak korunur, final6ile8senaryo denmez.

### 2026-10-17T12:48:44.261319+03:00 — final kabul işlemleri

235source freeze ile fullstandard39c7d7e9-23e8-4212-a0b8-a5894a1c1a67 çalışıyor.
Native6case fe2edca5-aa49-4d48-bc1d-4987cf70ade3; code publication-v2,outputs pub-*.
Yeni native tekrar göndermeden makbuz okunmalı. Yalnız docs/evidence/status değişir;
ürün/test/script/config sabit. 9B08finalcorroboration bu6son profile yapılabilir.

### 2026-10-17T12:54:30.382861+03:00 — 9B08 final35QA ve6native bağımsız kabul tamamlandı

Son request_view29cc8a80 üstünde değişmeyen35QA PASS/234source drift0.
Readonlyscript publication-v2 pub-normal/partial/limit/disconnect/after-tool/
optout6profile CORROBORATED;146programhashsame. originbytehash/claim/egress/
sourcecapsule/terminaltext eşleşmesi,5DockerIDyok/6socketyok. Partial4166→594
→11679requestbytes. Yanıtkayıpları handoff_armed kalır. YeniQA native/model0.
Primaryfull1595makbuzuokundu;QAroot1527ve35optinsayısıyla toplanmaz.
QA alanında native-publication-remote-verbatim.json gerçekremote baytları;
öncekiJSONkopyasındakiLF/CRLFfarkı açık tutuldu. Wrapper sonsysNameError
remotePASSsavedsonrasıydı; hiçbirnative tekrarçalıştırılmadı. Ürünkodudeğişmedi.

### 2026-10-17T12:57:19.038201+03:00 — son kabul ve yayın hazırlığı

Tamstandart39c7d7e9-23e8-4212-a0b8-a5894a1c1a67 1595PASS; native6final
fe2edca5-aa49-4d48-bc1d-4987cf70ade3 PASS,source değişmedi. 29safe dosya
SSHüzerinden bytehashle geldi; actual request/bodytoolmetadata eşleşmesi ve
DockerexactID/socketyokluğu read-only teyit edildi. Önceki2candidate korunur.
9B08 report/51testkökeni korunur;16standart+35optin ayrı. Son9B08native6teyidi
ayrıca okunacak, önceki2teyit altısonprofili kapatmış sayılmıyor.
Şimdi yalnız buişin seçilmiş dosyaları exactindexkontrol+rootgate ardından
commit/push; localPASS CIbaşarısı değildir. Mainmerge yok.

### 2026-10-17T13:03:14.811539+03:00 — bağımsız son kabul ve exact-index yayın kontrolü

9B08 altı finalprofilCORROBORATED raporu doğrudan okundu; remoteverbatim hash
ve6native makbuz hashleri primarykopyaylaeşit.16baseline+35optin ayrımı korunur.
235source değişmedi. Seçili106dosya stage edildi; whitespacecheck0. Rootgate ve
exact-index bayt karşılaştırması şimdi çalışır; ardından yalnız seçilmişpaket
commit/push. Çalışma tekrar/nativesayısı artmadı, main/önceki ağaçlar korunur.

### 2026-10-17T13:06:59.779972+03:00 — kod yayımlandı, exact CI sürüyor

Kod d8628aa614236b80022780ea1d79c05cf9fb72cb origin/alaz/r1b2-request-view-af13
üzerinde;235acceptedkaynakGitcommitobjeleriylebyteeşit. Commit108seçilmişdosya.
Rootgate1033text/2gitlink/10component ve1595discovery PASS. Gerçek remoteCI
56588998282 statusu pending; öncekiCI bucommite aktarılmaz. Finaldoc/status
kaydı codeCI sonucu alındıktan sonra yayımlanacak. Main/sourcepins değişmedi.

### 2026-10-17T13:08:14.323885+03:00 — exact-code CI başarılı ve son durum kaydı

Kod d8628aa614236b80022780ea1d79c05cf9fb72cb alaz/local-ci SUCCESS;
GitHub56589060219,2026-10-17T10:06:44Z; ikiAPIyle doğrulandı. APIde sunucu
sayısı yok, yerel1595 sonucu server1595 diye yazılmadı.235sourcecommitblobları
frozenkaynaklaeşit.35optinQA/6native ve bağımsız6corroboration ayrı kalır.
R1B2 kaynak→araçdönüşü→normalizeistekteiçerik bağı bu dar kapsamda kapanmıştır.
Handoffwriteahead fiziksel-send garantisi değildir; originatingrun ve model
understanding/processing UNKNOWN/false. G01/D3B/realmodel/R2/HYB006/M1/M2 açık.
Sonraki uygulama D3B OSkimlik/egress sınırı, ardından kontrollü gerçeksağlayıcı
kabulü. YeniDB/kuyruk/izinsizaraç/model/ücret/servisinstall/mainmerge yapılmadı.
Bu finaldocs/summary/status/CIreceipt dışında hiçbirürün/test değişmez.
