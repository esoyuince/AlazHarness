# P2 / R159A1 — Mevcut native owner üzerinde yerel servis

## Başlangıç noktası

R158, görev/istek sorgusu/izleme/sonuç/kullanım/iptal CLI'sini ve kayıp yanıt
locator'ını kaynak/HTTP sözleşmesi düzeyinde ekledi. Günlük `start/close` ve gerçek
model kabulü açık. Önce `status.md`, R158 final publication kaydı ve canlı Git/CI
doğrulanır. Native taban d1516731308de8e87130dc68124e69aad35d6911'dir; R158'in
[raporu](P2-LOCAL-CONTROL-R158A1.md) ve lifecycle-review kanıtı somut kaynak eşlemesini taşır.

P1'in değişmemiş R156 kurulumu tarihsel kabul olarak korunur. Yeni servis
kaynağı için ayrı native feature çalışma ağacı ve yeni P2 kurulum adayı gerekir.
Ordinary runner startup'ı zorlamak veya mevcut no-listener kontrollerini atlamak
bu planın bir parçası değildir.

## Uygulanacak en küçük bağlantı

1. **Açık borrowed transport nesnesi.** Aynı event loop, runner, adapter,
   authority, üç store ve epoch çiftine bağlı native sahiplik kaydı ekle.
   P1'in varsayılan listener-free yolu değişmeden kalsın. App/runner/site,
   tek loopback adresi ve aktif handler kimlikleri sözleşmede yer alsın.
2. **Dar handler kümesi.** Mevcut native run/status/stop handler'ları, Host Gate
   ve seçilmiş execution/provider sınırı kullanılsın. Cron, tarayıcı kontrolü,
   bütün profil rotaları, ordinary reconnect/sweeper/heartbeat açılmasın.
   API metrics'in base adapter üzerinden default status dosyası yazması açıkça
   sahiplenilsin veya borrowed modda desteklenmeyen persistence olarak bastırılsın.
3. **Servis durumu.** Prepared kontrolleri yalnız doğrulanmış opt-in transport
   dalını kabul etsin. Host/execution boundary, aynı yeni ready kaydına ve
   kimliklere bağlansın. Descriptor alanını elle `ready` yapmak yeterli değildir.
4. **Kapanış ve kontrol.** Admission seal önce yapılsın. Draining sırasında
   mevcut işi gözlemleme ve exact-generation stop yolu açık kalsın. Native
   handler/worker/SQL yükümlülükleri terminal olmadan listener retirement,
   detach veya store/lease release tamamlandı gösterilmesin.
5. **CLI bağlama.** R158 `start/close` komutlarını gerçek sahiplik/terminal
   makbuzlarına bağla. Aynı request ID'nin locator ve native sonucu, kopup
   yeniden bağlanınca değişmesin. Null-generation queued cancellation'ın
   doğru ve kapsamı açık terminal raporunu native kanıtla tamamla.

## Durum ve kapanış ölçütleri

| Durum | Yeni görev | Mevcut gözlem | Mevcut işe stop | Store/lease bırakma |
|---|---|---|---|---|
| Ready | Policy/bütçe içinde | Açık | Açık | Hayır |
| Draining | Kapalı | Açık | Sınanmış native kontrol açık | Bütün kapanış kapılarından sonra |
| Unknown | Kapalı | Sınırlı tanı | Yalnız açıkça kabul edilmiş kontrol | Hayır |
| Closed | Kapalı | Canlı listener yok | Canlı kontrol yok | Özgün sıra tamamlanmış |

Sıra: admission seal → native iş/physical worker/handler terminal → transport
retirement → runtime/API retirement → drain/detach → üç fiziksel store close
→ profile/image lease release. Kuyruktaki iş için close politikası açık olsun:
bekleyen işi kullanıcı/native cancel ile kapatmadan clean-close yok; sessiz
silme, yeni request ID ile tekrar veya sahte idle yok.

Bind/setup/cleanup etkisi belirsizse nesne ve ownership retained kalır. İkinci
listener denemesi, zorla owner close veya lease bırakma yapılmaz.

## Kaynak, paket ve model bağlantısı

Native değişikliğin kaynak manifest'i ve host-gate uyum kilidi, gerçek yeni
dosyalar incelendikten sonra birlikte güncellenir. Aynı kuruluma R158'in Node
CLI/runtime bağımlılıkları ve `agent.secret_sources.command` dahil seçilmiş
modelin Python closure'ı alınır; yalnız repoda bulunması yeterli sayılmaz.

Provider broker'ın mevcut upstream sözleşmesi literal loopback `/v1` adresidir.
Gerçek model için seçilmiş yerel uyumlu sunucu/proxy veya açık route değişikliği
gereklidir. Kullanıcının kişisel anahtarları/servisleri keşfedilip devralınmaz.
Tek model, izinli küçük `.txt` dosyası ve çağrı/token/mikro-USD tavanları gerçek
denemeden önce görünür hale getirilir. Kaynak, fixture ve kurulum hazırlığı bu
seçim beklenmeden ilerletilir; fixture gerçek model kabulü sayılmaz.

## Kabul paketi

Önce anlamlı kaynak testleri: bind başarısızlığı, çift start, başka loop/owner,
kopan observer, kayıp ACK locator, queued/running stop, active/unknown close ve
draining sırasında stop erişimi. Ardından tek yeni kurulumda native localhost
akışı ve özgün sıralı kapanış; son olarak seçilen modelle tek sınırlı dosya görevi.

Mevcut ledger/broker rezervasyonları response-loss durumunda korunur; unknown
kullanım sıfır gösterilmez. Run usage ile profil/principal toplamı ayrı kalır.
Exact source/kurulum kimliği, native ve model çağrı sayısı, kullanım/bütçe ve
normal/başarısız/belirsiz kapanış kayıtları ayrı raporlanır.

R159'ın bitişinde gerçekten çalışan kapsam belirtilir. P2 yalnız bütün günlük
akış ve tek gerçek model görevi kabul edildiğinde kapanır; P3–P5 ve M1 ayrıca
izlenir. Yeni hafta tahmini için henüz ölçülmüş tam ürün akışı yoktur.
