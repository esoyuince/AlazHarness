# Dream D2B2 - Gercek Gateway sonucunun bagimsiz kayit kontrolu

Is: **DREAM-D2B2-GATEWAY-CUSTODY-73C9**. Tarih: **18 Ekim 2026**.
Dal: `alaz/dream-d2b2-gateway-custody-73c9`.
Taban: `d7f97ffc45d2cbf9907590effec672154ad1518c`.

## Sonuc

Kesilen AF21 calismasinda basarili sonuc diske zaten kaydedilmisti.
`normal-budget4-4.json` kaydini yeniden calistirmadan, durdurulmus gercek
Hermes Gateway profilinin SQLite veritabani, gorev sonucu ve kapanis
kayitlariyla karsilastirdik. Basarili dort-cagri zinciri **tutarli**.
Daha once uc cagri sonrasinda durdurulan denemenin `unknown` sonucu da
korunuyor; basarili sonuca donusturulmemis.

Bu tur yeni Gateway, ajan, model veya saglayici denemesi baslatmadi.
Test saglayicisinin onceki yanitlari programlanmisti. Gercek Gateway ve
uretim `aiohttp` broker entegrasyonu ile **gercek model ogrenmesi farkli
kabullerdir**. Modelin bir beceri ogrendigi bu kayitlarla kanitlanmaz.

## Neden ayri calisma agaci?

Devam ederken AF21 test betiginin ve status kaydinin baska bir islem
tarafindan guncellendigini gozledik. Kaynak betigin SHA-256 degeri
`50f16bff...` iken `f40d41fe...` oldu. Dolayisiyla devam eden kodu degistirmedik,
stage/commit etmedik ve ortak kok `status.md` dosyasini bu ayri kabul isinin
sonuclariyla ezmedik. Bu dal yalniz dogrulayici, testleri, iki degistirilmemis
orijinal sonuc kaydi ve kabul raporunu tasir.

Ana gelistirme: `scratch/worktrees/dream-d2b2-gateway-af21`.
Bu bagimsiz kontrol: `scratch/worktrees/dream-d2b2-gateway-custody-73c9`.
AF21'in yeni olumsuz senaryolari ve yayin durumu bu rapordan cikarilamaz;
bunlar kendi kesin kaynak surumunde ayrica kabul edilmelidir.

## Gercek kayitlardan dogrulananlar

| Kontrol | Tamamlanan profil | Butcede duran onceki profil |
|---|---:|---:|
| Yerel saglayici rezervasyonu | 4 | 3 |
| Egress izni ve request-view kaydi | 4 + 4 | 3 + 3 |
| Kalici degerlendirme sonucu | 2 kol | Yalniz baseline |
| Trial durumu | completed | unknown |
| Trial nedeni | Yok | token_exposure_limit |
| Ayrilan token ust siniri | 655.360 | 491.520 |
| Native veritabani butunlugu | ok | ok |

Basarili zincir: bir gercek native gorev -> D1 aday not -> D2A test icin
kabul -> baseline/candidate denemeleri. Native admission status'u
`terminal`, outcome'u `completed`; bunlar tek bir alan degildir.
D1 alintisi gercek native gorevin saklanan son ciktisinda bulunur.
D2A batch digest'i ve trial review revision'i ayni adaya baglidir.

Her claim, egress izni ve request-view kaydi icin SHA-256, scope, binding,
policy, epoch, instance ve ticket baglantilari ayri Python koduyla yeniden
kontrol edildi. Trial yanitlarinin yerel kayit hash'leri, case kapsamasi ve
broker response metaverisi de uyustu. Basarili senaryonun saglayici tarafinda
kaydedilmis dort istek hash'i veritabanindaki dort request digest'le ayni.

Test butcesi her deneme icin 131.072 + 32.768 = 163.840 token ust siniri
ayirir. Tam zincir dort cagri gerektirdiginden 655.360 token rezervasyon
butcesi gerekir. Eski 491.520 butce dorduncu cagrida dogru bicimde durdu.
Yeni deneme ayri profilde, en fazla dort saglayici cagrisi ile yapilmis;
eski profil butcesi sifirlanmamis. Bu sayilar tokenizer olcumu veya fatura
degil, bildirilmis ust sinirlara gore ayrilan risk butcesidir.

Kapanis nonce/PID baglantisi, native_result, lifecycle_completed ve sifir
engellenmis dis-ag girisimi kayitlari eslesiyor. Eski broker kaydi exit0,
soket kaldirildi ve activeRequests=0 diyor. Bagimsiz incelemede native DB,
ready/shutdown/task dosyalarinin baytlari once ve sonra ayni kaldi.
SQLite mode=ro + query_only kullanilir; bu, hic WAL/SHM yan dosyasi
olusamayacagi seklinde genis bir isletim sistemi iddiasi degildir.

## Sinirlar

- Kayitlar birbiriyle tutarli; bunlar guvenilir ucuncu taraf imzali bir
  fiziksel calistirma kaniti degildir. Yerel yonetici butun kayitlari
  degistirebilir. SHA-256 tutarlilik kontroludur, yetki degildir.
- Orijinal HTTP yanitinin ham baytlari tutulmadigi icin bu inceleme onlarin
  hash'ini yeniden hesaplamaz; saklanan broker metaverisini baglar.
- 8/12 -> 12/12 sentetik sonuc mevcut raporda vardir. Gizli cevap anahtari
  bu kontrol icin alinmadi; sayisal fayda yeniden puanlanmadi ve gercek
  model ogrenmesi kabul edilmedi.
- Calisma anindaki tum AF21 test kodunu geriye donuk olarak onaylamiyoruz.
  Betik inceleme sirasinda degisiyordu. Bu dalin kendi kaynaklari ve testleri
  ayri hash sabitlemesiyle test edilir.
- Hermes baslangicinda hazir beceri dosyalari ozel test profiline
  yerlestirilebilir. Bu inceleme tum profilin beceri dosyalarinin her an
  degismedigini iddia etmez. D1/D2 kayitlarinda aktif hafiza/beceri terfisi
  FALSE kalmistir; kullanicinin kisisel profili incelenmemistir.
- Docker/izole dosya okuma, tum Gateway OS kimligi/egress ayrimi D3B,
  dis saglayici tarifesi ve gercek gorulmemis-gorevde ogrenme halen aciktir.

## Yeniden uretim

`scripts/qa/gateway_checkpoint_audit.py` yalniz var olan iki AF21 profilini
salt-okunur acar. Urun modullerini import etmez; yeni model, Gateway,
network deneyi veya review karari baslatmaz. Ozel runtime dizini ve yeni
bir sonuc dosyasi acikca verilmelidir. Ortak/kisisel profiller hedeflenmez.

18 yeni unittest, sentetik kayit baglantilarini ve red davranisini sinar:
bozuk hash, yanlis budget, yanlis epoch, alinti uyuşmazligi, eksik claim,
sonuc degistirme, eski review ve sahte beceri terfisi. Bunlar 18 yeni native
Gateway denemesi degildir. Tam test sayisi ve CI kendi makbuzlarinda yer alir.

Kayitlar: `evidence/d2b2-gateway-custody-73c9/`.
`recovered-native-audit.json` iki native DB okumasinin sonucunu ve kaynak
hash'lerini; `source-references.json` orijinal rapor hash'lerini saklar.
`auditor-initial-correction.json`, ilk dogrulayicinin admission status/outcome
ayrimini yanlis beklemesini ve duzeltmeyi korur. Orijinal native kayitlar
bu duzeltme icin degistirilmedi.

## Kesin sonraki adim

AF21 sahibinin uzerinde calistigi yeni Gateway olumsuz senaryo sonucunu
kaynak commit'i ile karsilastirip iki dalin yalniz kabul edilmis dosyalarini
uzlastir. Ortak kaynak duzenleme veya `main` birlestirmesi bu tur yapilmadi.
Sonra D3B ve sinirlandirilmis gercek model/ogrenme kabulune gecilebilir.

## Yerel kabul - 2026-10-18T10:53:46.154147+03:00

Bu QA dalinda tam 1.866/1.866 unittest PASS;18 yeni test bu sayinin
icinde bir kez yer alir. Atlanan test yok,260 kaynak/test/konfigurasyon
dosyasi once-sonra SHA-256 esit. Statik kontrol PASS, test kesfi ayri.
Iki mevcut native profil salt-okunur dogrulandi; yeni native/model
calismasi yapilmadi. Kaynak/CI yayini bu dal icin ayrica kontrol edilir.

## Git yayini - 2026-10-18T10:57:32.221713+03:00

QA kod commit: `e564b606e605cfa66dab7fe9d7eba0f0746012a4`; dal
`alaz/dream-d2b2-gateway-custody-73c9`; origin push tamamlandi.
GitHub API son kontrolde bos statuses dondurdu: CI NOT_REPORTED;
CI basarisi iddia edilmez. Bu son belge guncellemesi urun/test kodunu
degistirmez. Ortak AF21 dalina veya main dalina merge yapilmadi.
