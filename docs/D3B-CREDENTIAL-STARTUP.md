# D3B — Korumalı Gateway başlangıcı: A613 kabulü

Tarih: 18 Ekim 2026. Dal: `alaz/d3b-credential-fix-a613`.
Başlangıç commit'i: `7632784c1238fdb5ebd09ee1131cb6a52ba5a4a1`.

## Güncel karar

**Dosya koruması açıkken gerçek Hermes Gateway ve orijinal aiohttp broker
birlikte çalıştı: dört senaryo PASS. Tam D3B güvenlik kabulü hâlâ AÇIK.**
Bu sonuç, önceki `D3B-CREDENTIAL-6E42` raporunda açık kalan korumalı Gateway
başlangıcını bu dalın yeni kaynak sürümünde kapatır. Önceki FAIL kayıtları
silinmedi ve geriye dönük PASS olarak değiştirilmedi.

18 yeni benzersiz çevrimdışı test, toplam **1903/1903 PASS** içindedir.
Atlanan test yok. Tam günlükte 1903 farklı test kimliği bulundu; 269 ölçülen
kaynak/test/konfigürasyon dosyası son kaynak dondurmasıyla aynı. Statik
kontrol PASS; 1903 test keşfi ikinci bir test yürütmesi değildir.
Kanıtlar `evidence/d3b-credential-fix-a613/` altındadır.

## Başlangıcı engelleyen nedenler ve yapılan düzeltmeler

### 1. Windows üzerinden bağlanan kaynak dosyası

Yeni kontrol koşusunda koruma uygulanmış ve gizli broker dosyasını açma
reddedilmişti; fakat `/mnt/c/.../scripts/native_gateway_worker.py` açılamadı.
Aynı 36 baytlık dosya ve aynı Landlock izinleriyle yapılan karşılaştırmada
WSL `v9fs` üstündeki dizin okuması EACCES verdi; Linux'un yerel dosya
sistemindeki kopya açıldı. Bu, gözlenen ortamın davranışıdır; tüm WSL veya
9p sürümleri için evrensel sonuç değildir.

`scripts/qa/native_credential_ext4.py` yalnız `packages/`, `scripts/`,
`config/` ve `sources.lock.json` kaynaklarını yeni bir Linux geçici dizinine
kopyalar. Her dosya önce ve sonra SHA-256 ile doğrulanır; çalışma verileri,
üretim profilleri ve gizli dosyalar kopyalanmaz. Dört kabul koşusunda 176
kaynak dosyası birebir eşleşti ve geçici kod kopyaları kaldırıldı. Asıl
Windows çalışma ağacı geliştirme adresi olarak kalır; koruma kapatılmaz.
Dosya sistemi deneyi: `filesystem-comparison.json`.

### 2. Gateway'in kendi süreç kimliğini okuması

Kaynak kopyasıyla başlangıç ilerleyince Hermes/psutil kendi süreç kimliğini
okuyamadığı için durdu. `credential_guard.py` içine isteğe bağlı ve varsayılan
kapalı **`self_process_metadata`** alanı eklendi. Açıldığında yalnız koruma
kurulan mevcut PID'nin `stat`, `status`, `statm`, `cmdline` dosyalarına ve
sistem başlangıç zamanı için `/proc/stat` dosyasına READ_FILE verilir.

Bu, `/proc` ağacına genel izin değildir. `/proc` listelemesi, başka PID'nin
status/mem dosyası, kendi environ/mem dosyası ve yeni çocuğun kendi süreç
metadata dosyası testte açılamadı. Mevcut PID için gerekli psutil işlemleri
çalıştı. Aynı PID exec sırasında korunur; yeni PID için kendiliğinden yeni
izin üretilmez. `/proc/stat` sistem istatistiğidir, yalnız-kendi-süreci bilgisi
değildir. Bu küçük ek görünürlük raporda açıkça kabul edilir.

Ayrı iki gerçek Linux çocuk deneyi: metadata kapalıyken 13, açıkken 17
kontrol PASS (`metadata-accepted.json`). Bunlar 30 ek unittest değildir.
Eski politika şekli desteklenir ve metadata alanı yokken eski davranış sürer.

### 3. Kısa ve özel kontrol soketi dizini

Uzun hazırlık yolu Unix soketine sığmadığından Hermes `/tmp` altına dönüyordu.
Test başlatıcısı bunun yerine yalnız bu koşuya ait, kısa, 0700 özel dizini
`XDG_RUNTIME_DIR` olarak verir; yalnız bu dizin yazılabilir. Broker'ın gizli
başlangıç dosyası bu izin ağacının dışında kalır. Bütün `/tmp` açılmadı.

### 4. HTTP kitaplığının MIME tablosu

Aiohttp web başlangıcının gerektirdiği `/etc/mime.types` dosyasına salt-okunur
izin eklendi. `/etc` ağacı genel olarak açılmadı ve sistem dosyaları yazılabilir
hâle getirilmedi. Gateway/broker/Dream koduna farklı bir motor veya taklit
başlatıcı yerleştirilmedi; mevcut kabul düzeneği koruma altında çalıştırıldı.

## Gerçek korumalı Gateway senaryoları

| Senaryo | Fiziksel sağlayıcı isteği | Broker yanıtı | Deneme durumu | Kabul |
|---|---:|---:|---|---|
| normal | 4 | 4 | completed, iki kol | PASS |
| budget-limit | 3 | 3 | unknown, yalnız baseline | PASS |
| candidate-disconnect | 4 | 3 | unknown, yalnız baseline | PASS |
| review-revoked | 3 | 3 | unknown, kabul edilmiş kol yok | PASS |

Her senaryoda koruma `enforced`, gizli broker dosyası açılışı reddedilmiş,
Gateway temiz kapanmış, broker exit0 ve aktif istek sayısı sıfırdır; soket
kaldırılmıştır. Ortak bütçe rezervasyonları, istek görünümü ve yerel test
sağlayıcısının aldığı bayt özetleri 4/3/4/3 eşleşir. Tekrar gönderimleri
fazladan rezervasyon oluşturmadı; geri çekilmiş inceleme tekrarı reddedildi.

Bu sağlayıcı **programlanmış yerel test sunucusudur**. Normal koşudaki
8/12 → 12/12 puan farkı öğrenme kanıtı değildir. Ücretli veya gerçek model
çağrısı, Docker dosya aracı, otomatik hafıza/skill terfisi çalıştırılmadı.

Başarılı raporlar:
`gateway-a613-native-mime4.json`, `gateway-a613-final-budget.json`,
`gateway-a613-final-disconnect.json`, `gateway-a613-final-revoke.json`.
Her raporun `source-<runId>.json` kaynak manifesti korunur.

## Koruma regresyonu ve korunan başarısızlıklar

Önceki kernel deneyi yeni kaynakla tekrar geçti: 13 erişim kontrolü ve üç
başlangıç reddi (`../d3b-credential-6e42/native-a613-recheck.json`). Açık gizli
dosya tanıtıcısı, soket stdin ve gizli dosya sabit bağlantısı hâlâ reddedilir.

Metadata testinin ilk sürümleri `tempfile` importunun bu taşınabilir Python
ortamında önceden açık `/dev/urandom` tanıtıcısı bırakması yüzünden doğru
biçimde reddedildi. Import, yalnız kısıtlanmamış test denetleyicisine taşındı;
ürün koduna genel açık-tanıtıcı istisnası eklenmedi. Bu test FAIL'leri ve
kaynak/dizin/proc/MIME başlangıç FAIL'leri kanıt dizininde tutulur.

## Kesinti sonrası doğrulama

Yanıt kesildikten sonra tam regresyon günlüğü, statik kontrol makbuzu,
269 kaynak özeti ve dört native kaynak manifesti yeniden okundu. Sonuçları
bilinmeyen test/model işlemi tekrar başlatılmadı. `resume-verification.json`
1903 benzersiz test kimliğini ve kaynak eşitliğini kaydeder.

## Açık sınırlar ve kesin sonraki iş

Bu dal dosya-açılışı korumasını gerçek Gateway ile kabul eder; ağ dalını
birleştirmez. Ayrı host UID, PID/mount/Unix-soket görünürlüğü, yetkili hosta
karşı koruma ve Gateway'in yazabildiği bütçe kayıtlarına karşı bağımsız broker
otoritesi tamamlanmış değildir. Kernel dosya koruması bu riskleri tek başına
kapatmaz. Koruma davranışı kişisel/üretim profillerinde otomatik açılmadı.

Sıradaki iş: `alaz/d3b-netns-4e62` ile bu dalı ayrı bir entegrasyon çalışma
ağacında birleştirip iki korumayı AYNI Gateway sürecinde birlikte sınamak;
IPC/kimlik bilgisi erişimini ve broker-bütçe otoritesini ayrıca denetlemek.
Bu yapılmadan tam D3B veya gerçek model öğrenme kabulü ilan edilmemeli.
`main`, önceki çalışma ağaçları ve ağ dalına ait kök durum aynası korunur.

## Yeniden üretim

Hazırlanmış AF21 Linux/Python/Hermes ortamı mevcutken, yeni ve benzersiz bir
`run-id` ile çalıştırılır; var olan kanıt dosyaları üzerine yazılmaz:

```text
wsl.exe --exec python3 -B /mnt/c/Antigravity/AlazHarness/scratch/worktrees/d3b-credential-fix-a613/scripts/qa/native_credential_ext4.py --run-id a613-new-unique --scenario normal
```

Diğer seçenekler `budget-limit`, `candidate-disconnect`, `review-revoked`.
Çevrimdışı kontrol: `python -B -m unittest discover -s tests -v`.
Git/CI sonuçları yalnız yayımlanan kesin commit gözlendikten sonra kaydedilir.

## Yayın ve CI kapanışı — 2026-10-18T19:53:04.229087+03:00

Kod ve kabul kanıtları `ebfb3a20f472bdd6be6e5b86ed9d102ebab126d8` commit kimliğiyle
`alaz/d3b-credential-fix-a613` dalına gönderildi. 269 kaynak Git blobu test
edilen baytlarla eşit. Aynı commit için GitHub `alaz/local-ci` **SUCCESS**
(status 56637349043, 2026-10-18T16:51:27Z) gözlendi. API uzak test sayısı
vermez; yerel 1903/1903 ve dört korumalı Gateway kabulü ayrı kanıtlardır.

Bu rapor/durum/makbuz takibi yalnız belgedir; onun CI sonucu kendi commit
kimliğiyle ayrıca incelenir. Ürün ve test kaynakları değişmemiştir. Kök
durum aynası, ağ dalı ve main korunur. Ortak D3B ve gerçek model NOT RUN.
