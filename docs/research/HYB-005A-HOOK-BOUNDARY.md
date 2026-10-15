# HYB-005A — zorunlu kapı ile eklenti bildiriminin ayrılması

15 Ekim 2026. Durum: **bileşen davranışı doğrulandı; host kapısı uygulanmadı**.
Dal: `alaz/hyb-005a-hook-boundary-890e`. Taban:
`b8ff44ff105965ba3f6f9fa9559ad96f2c084815`.

## Neden ayrı bir inceleme dalı?

Yerel köprünün envanter çağrısı bir kez oturum döndürdü; dosya, komut ve sonuç
çağrıları ise tekrar 502 verdi. Alternatif masaüstü bağlantısında çevrimiçi
bilgisayar bulunamadı. Bu yüzden Windows'taki HYB-005 dalının değişikliklerini
okuyamadık, test edemedik veya güvenle birleştiremedik. O dalı ve main'i değiştirmeden
bu dar, tekrar üretilebilir kontrol yayımlanıyor. GitHub'daki main b8ff44f ve onun
alaz/local-ci success sonucu yeniden okundu. Yereldeki durum bununla eşit varsayılmaz.

Bu bir ikinci ürün uygulaması, scheduler veya oturum deposu değildir. İzin/bütçe
kapısını yanlış bir eklenti davranışına dayandırmamak için yapılmış kaynak testidir.

## Doğrulanan kaynak

Hermes commit: `eb75627faf532fa6ffbdae59a0d14b0b385fc780`.
Kaynak dosya: `hermes_cli/middleware.py`, 8459 bayt.
Git blob: `753b6643ab2c6b2d7cfc38d1e65043286ceb0080`.
SHA256: `3745ad211f365554a3c070083dc39d3ff9b6cdc93965f13d8796918433ec2328`.

[Kaynak kod](https://github.com/esoyuince/hermes-agent/blob/eb75627faf532fa6ffbdae59a0d14b0b385fc780/hermes_cli/middleware.py)
GitHub bağlantısından okundu. Deney ortamındaki kopya bu metinden oluşturuldu;
Git blob kimliği ve SHA256 denetlendi. Kontrol bu denetlenmiş baytları derleyip
çalıştırır, sonra dosyanın değişmediğini tekrar doğrular. Uyumsuz kaynak yürütülmez.
Depoya upstream kaynak kopyası eklenmedi; script zaten mevcut vendor dosyasını ister.

## Kritik sonuç

Gerçek `_run_execution_chain`, eklentinin kendi callback'inin `next_call` öncesinde
attığı Exception'ı kaydeder ve sonraki callback'e/terminal işleme devam eder.
Bu nedenle **bir execution middleware içinde PermissionError yükseltmek tek başına
izin veya bütçe vetosu değildir**. Yanlış callback imzasında oluşan TypeError için
de terminal işlem devam etti. Bu, eklenti hatasına dayanıklı tasarım davranışıdır;
herhangi bir upstream güvenlik açığının uzaktan istismar edildiği iddia edilmiyor.

`next_call` çağrılmadan normal bir ret nesnesi döndürmek bu dar deneyde terminal
çağrısını durdurdu. Fakat bu nesne yalnız fixture değeridir. Gerçek SDK response,
araç sonuç şeması, retry sınıflandırması ve bütün çağıranların bu reddi doğru
işlemesi **test edilmedi**; bunu hazır bir üretim çözümü diye kullanmayın.

## Çalıştırılan yedi durum, iki middleware türü

Aynı tablo hem gerçek `run_llm_execution_middleware` hem
`run_tool_execution_middleware` üzerinden sınandı: toplam **14/14 gözlem**.

| Durum | Terminal callback sayısı | Sonuç |
|---|---:|---|
| Middleware kaydı yok | 1 | Normal devam; zorunlu koruma varsayılamaz. |
| `next_call` öncesi PermissionError | 1 | Hata kaydedildi; çağrı engellenmedi. |
| `next_call` olmadan normal ret değeri | 0 | Yalnız fixture düzeyinde durdu. |
| Başarılı `next_call` sonrası hata | 1 | İlk sonuç korundu; ikinci işlem yok. |
| İkinci kez `next_call` | 1 | Sözleşme hatası kaydedildi; ikinci terminal çağrı yok. |
| Terminal callback OSError verdi | 1 | Hata çağırana taşındı; burada retry olmadı. |
| Yanlış callback imzası | 1 | TypeError kaydedildi; işlem devam etti. |

Gerçek upstream fonksiyon gövdesi değiştirilmedi. Plugin registry ve terminal
provider/araç callback'i ise kontrollü test bileşenleridir; terminal yalnız sayaç
artırır. Tam PluginManager yüklemesi, Gateway, gerçek AIAgent, provider, dosya aracı,
HTTP/SSE veya native veritabanı çalıştırılmadı. Çalışma ortamı Linux/Python3.13.5
sandbox'tır; kullanıcının Windows bilgisayarı veya alaz-server değildir.

`CHARACTERIZATION_CONFIRMED`, gözlenen davranış beklentisiyle eşleşti demektir;
**izin kapısının güvenli olduğu veya bu eksikliğin giderildiği anlamına gelmez**.
14 gözlem önceki 604 standart teste eklenmez. Üç ek launcher kontrolü de ayrı:
yanlış kaynak, bulunamayan kaynak ve var olan çıktının üzerine yazma reddedildi.
Gerçek model/araç/ağ çağrısı ve bağımlılık kurulumu sıfır.

## Diğer kaynak sınırları — bu deneyde yürütülmedi

[auxiliary_hooks.py](https://github.com/esoyuince/hermes-agent/blob/eb75627faf532fa6ffbdae59a0d14b0b385fc780/agent/auxiliary_hooks.py)
pre/post yardımcı model kancalarını observer-only/fail-open olarak tanımlar ve
`_fire` hatalarını yakalar. Gözlem bildirimi üzerinden exception atarak bütün
fiziksel provider çağrılarını sınırladığımız varsayılmamalı.

[plugins.py](https://github.com/esoyuince/hermes-agent/blob/eb75627faf532fa6ffbdae59a0d14b0b385fc780/hermes_cli/plugins.py)
`register_platform_handler` sözleşmesi de factory hatasında platformun bağlanmaya
devam edebildiğini söyler. Bu generic metodun varlığı, API-server için gereken
zorunlu kapının gerçekten bağlandığını kanıtlamaz. Gerçek başlatma yolu ayrıca
incelenecek; kaynak yorumları test makbuzu değildir.

## HYB-005A için uygulama/kabul kararı

1. Tek-kullanımlık gönderim izni, opsiyonel bildirim callback'i veya yokluğu normal
   karşılanan middleware kaydı olamaz. Zorunlu kapının yokluğu, kurulum hatası,
   policy okuma hatası ve eksik kimlik yeni gönderimi durdurmalıdır.
2. Gerçek yürütme sınırında açık ret sonucu, alt katmanın yeniden deneme mantığıyla
   birlikte sınanmalı. Sadece exception sınıfı veya plugin listesi yeterli değildir.
3. Gönderimden önce native sahibin transaction'ında tüketilen izin, yalnız
   **en fazla bir gönderim girişimi** sağlar. COMMIT ile ağ gönderimi arasındaki
   kesinti işi hiç iletmemiş olabilir; otomatik retry ile gizlenemez. Belirsiz
   durum, tekrar çalıştırma izni değil uzlaştırma gerektirir.
4. Kayıtlı kapalı/unknown istek, scope ve fingerprint kontrolü olmadan tekrar
   gönderilmemeli. Anahtarın süresinin dolması veya yeni rastgele anahtar üretmek
   aynı kullanıcı niyetinin yeni bir iş olduğunun kanıtı değildir.
5. Ana tur, özet, fallback, SDK retry ve yardımcı çağrılar için gerçek provider
   çıkışında kapsama testi gerekir. Araç izinleri de gerçek araç çalıştırma
   sınırına bağlanmalı; bu rapor bunları uygulamıyor.

Yerel bağlantı geri geldiğinde önce main-6f88 içindeki aktif dal/diff/status ve
henüz yayımlanmamış HYB-005 dosyaları okunmalı. Bu inceleme paketi uzlaştırılmadan
aynı hedefin ikinci uygulamasını yazmayın. Main birleşimi zaten yapılmıştır;
tekrarlanmayacak. Bu dal main'e otomatik birleştirilmez.

## Tekrar üretim

Repo içinden, mevcut sabitlenmiş Hermes kaynak ağacıyla:

```powershell
python -B scripts/research/probe_hyb005_hook_boundary.py --source-file C:\Antigravity\AlazHarness\vendor\hermes-agent\hermes_cli\middleware.py --output C:\Antigravity\AlazHarness\runtime\fresh-hook-boundary.json
```

Çıktı dosyası yeni ve üst klasör mevcut olmalı. Script paket kurmaz; farklı
commit veya satır-sonu baytlarında kaynak uyuşmazlığıyla durur, kaynağı değiştirmez.
Normal CI yalnız kendi standart paketini çalıştırır; bu opsiyonel upstream-bileşen
kontrolünü çalıştırdığı varsayılmaz. Kanıtlar `evidence/hyb-005a-boundary/` altındadır.
