# D3B-IPC-A731 — açıkça seçilmiş yerel soket görünümü

Tarih: 19 Ekim 2026. Dal: `alaz/d3b-ipc-a731`.
Taban: `5e7a14ebfa2111e9301d3cd50ee62733810f5f99`.

## Bu dilimin üründeki karşılığı

Önceki aynı-süreç network namespace + Landlock katmanları host TCP ve özel
kimlik dosyasının açılmasını engelliyordu; fakat pathname Unix socket
bağlantısı dosya açma kontrolü değildir. Önceki yalnız bize ait test soketine
bağlantı başarılı kalmıştı. Yeni `ipc_view.py`, hedef uygulamanın dosya yolu
çözümlemesini ayrı bir mount namespace ve seçilmiş kök görünümü içine alır.

Bu yeni bir ajan motoru veya görev döngüsü değildir. Ortak başlatıcıda **isteğe
bağlı `ipc` sözleşmesi** kullanılınca, mevcut kaynaklar/çalışma dizinleri ve
**bir adet açıkça seçilmiş broker socket inode'u** görünür olur. Eski host kökü
hedef çalışmadan önce ayrılır. Kaynak, süreç, syscall veya test hatasında
başlatıcı korumasız devam etmez. `ipc` bulunmayan eski sözleşme eski davranışı
korur; eski modda pathname IPC izolasyonu olduğu iddia edilmez.

## Kurulum sırası ve kaynak sahipliği

1. Güvenilir başlatıcı sözleşme, komut özeti, boş/özel geçici kök ve broker
   socket kimliğini denetler. Kök `/tmp/alaz-ipc-*` altında yeni, uid sahibi
   aynı ve mode0700 olmalıdır. Broker ve üst dizini grup/diğer erişimine
   kapalı olmalıdır. Broker bir symlink veya geniş bir dizin grant'ı değildir.
2. Mevcut `linux_netns` tek iş parçacıklı çocukta kullanıcı/ağ namespace'i ve
   özel loopback kurar; açık dosya/soketleri taşımaz.
3. Yetkiler hâlâ varken yeni private mount namespace yaratılır. Sözleşmedeki
   dosya kökleri, tam broker soketi, yalnız başlatılan PID'nin proc alt ağacı
   ve `/proc/stat` bağlanır. Normal uygulama alias yolları gerektiği kadar
   yaratılır. Eski root `pivot_root` ile ayrılıp detach edilir.
4. Mevcut yetki düşürme ve seccomp kuralları yeni mount/namespace/chroot,
   başka süreç belleği, dosya tanıtıcısı alma gibi geri dönüşleri engeller.
   Mevcut Landlock politikası bundan sonra aynı süreçte uygulanır.
5. Komut yalnız her katman doğrulanınca `exec` edilir. Broker'ın upstream
   özel dosyası Landlock izinlerinin dışında kalır; denetim gerçek EACCES
   üzerinden yapılır, dosya yokluğu başarılı gizlilik testi sayılmaz.

Salt-okunur kökler readonly; çalışma kökleri noexec/nosuid ve izinli kapsamda
writable'dır. Mount kaynağındaki daha sıkı VFS bayrakları korunur. WSL'nin
`/usr` altındaki kilitli alt mount'ları içeren ağaç önce recursive clone
edilir, tespit edilen alt mount'lar daha sonra boş readonly/mode000 tmpfs ile
örtülür. Bu işlem host mount tablosunu değiştirmez; değişiklikler yalnız yeni
çocuğun private namespace'inde kalır.

## Kontrollü doğrulama kapsamı

`tests/ipc_view_linux.py` yalnız tarafımızdan yaratılan gerçek test uçlarını
kullanır; Docker daemon, kullanıcı D-Bus/SSH agent veya mevcut host servisine
bağlantı denenmez. Deneyden önce tüm kontrol uçları hosttan erişilebilir
oldukları doğrulanır. Çocukta broker iki defa (kendisi ve exec edilmiş alt
süreç), izin dışı pathname/abstract/TCP uçları sıfır defa erişim almalıdır.

24 kernel davranışı ve 5 başlangıç reddi ayrı deneydir. Doğrudan pathname,
symlink, parent `/proc/<pid>/root` yolu ve libc connect denemeleri; açık
secret/soket taşıma; alt sürecin broker ve engelli soket davranışı; özel
loopback/runtime socket kullanımı kontrol edilir. Başlangıçta fazladan
socket içeren runtime, symlink broker, geniş broker izinleri, dolu root ve
uyuşmayan komut hash'i reddedilir. Host servisleri taranmaz.

29 yeni çevrimdışı birim testi politika/alias/kapsam doğrulaması, eksik veya
sınırlanmış dizin taramasının ret olması, eski başlatma imzasının korunması,
IPC kurulum hatasında fallback olmaması ve doğru sözleşme aktarımını sınar.
Bunlar kernel/Gateway'i yeniden çalıştırmaz. Native Gateway normal,
budget-limit, candidate-disconnect ve review-revoked koşuları ayrıca,
yeni geçici Linux kaynak kopyalarından yürütülür.

## Korunan ilk başarısızlıklar

`kernel-initial.json`: WSL alt mount'ları yüzünden güvenli preflight reddi.
`kernel-submounts2.json`: kullanıcı namespace'inde host uid0 görünümü değişti;
nesne kimliği dev/inode/type sabitlenerek eşleştirme düzeltildi.
`kernel-idmap3.json`: locked mount grubunun non-recursive bind'i EINVAL;
recursive bind + alt mount maskelemesi kullanıldı.
`kernel-mount4.json`: proc mount'unun kilitli NOEXEC kısıtı temizlenemez;
kaynak VFS kısıtlarının korunması sağlandı.

Bu dört denemede hedef başlamadı, kontrol soketlerine bağlantı yapılmadı ve
geçici root'lar temizlendi. Kayıtlar başarısız olarak kalır. `kernel-flags5`
ilk olumlu deneydir; son sertleştirilmiş kaynak için `kernel-final.json` esastır.
İlk gerçek Gateway `a731-normal1`, son dört çalışmadan önceki ara kanıttır.

## Bilinçli sınırlar — tam D3B henüz değil

**Bu bir mount görünümü sınırıdır; tüm IPC/kimlik/bütçe otoritesi değil.**

Kaynak ve çalışma ağaçlarının host tarafındaki sahibi güvenilir kabul edilir.
Başlangıç taraması sonrasında ayrı bir host yazıcısının aynı export köküne
socket/dosya yerleştirmesine karşı ağaçlar immutable değildir. Dosya kökleri
paylaşılır; kötü niyetli ayrı host süreci veya kernel açığına karşı sertifika
verilmez. Aynı host UID kullanılmaya devam eder; diğer süreçlere sinyal,
kaynak tüketimi, PID yaşam döngüsü gibi konular tam süreç izolasyonu değildir.

`/proc/self` görünümü başlatılan PID'ye sabittir. Yeni alt süreç normal dosya,
network ve broker erişimini devralır; kendi psutil/proc metaveri görünümü veya
genel çocuk-process yöneticisinin bütün özellikleri bu dilimde kabul edilmedi.
Broker yeniden başlatılıp yeni socket inode'u oluşturursa eski bind otomatik
olarak yenisine bağlanmaz; yeni güvenilir başlatma ve uzlaştırma gerekir.

**Gateway'in yazabildiği state DB'den bağımsız broker bütçe/tek-kullanımlık izin
otoritesi hâlâ açık.** Önceki ledger eşleşmeleri düşman bir Gateway'in yazdığı
kayıtlara karşı bağımsız kanıt değildir. Bu dilim onu çözdü diye işaretlenmez.
Makbuzun bulunduğu runtime, modelin yazabildiği alan olabilir; dış kontrolcü
ve tam kaynak/proses eşleştirmesi olmadan sadece JSON yeterli kanıt değildir.

Native deneylerde gerçek Hermes Gateway, mevcut SessionAuthority ve orijinal
`aiohttp` broker çalışır; yanıtlar programlanmış localhost sağlayıcıdan gelir.
Gerçek/ücretli model çağrısı, Docker araç birleşimi, bağımsız öğrenme başarısı,
otomatik hedef seçimi ve aktif hafıza terfisi **NOT RUN / DISABLED** kalır.

## Açık test ve kullanım

Eski ortak sözleşmeye eklenecek parça (dosya oluşturma/izin ve komut hash'i
çağıran güvenilir başlatıcının sorumluluğunda):

```json
"ipc": {"version": 1, "mode": "projected_root",
        "root": "/tmp/alaz-ipc-unique-owned-empty",
        "brokerSocket": "/tmp/owned-private-broker/egress.sock"}
```

Bu parça tek başına bir Gateway konfigürasyonu değildir; mevcut kişisel veya
üretim profilleri değiştirilmedi. Native testte yalnız yeni run id kullanılır:

```text
wsl --exec python3 -B /mnt/c/Antigravity/AlazHarness/scratch/worktrees/d3b-ipc-a731/scripts/qa/native_combined_ext4.py --run-id new-unique-id --scenario normal --ipc
python -B -m unittest discover -s tests -v
python -B scripts/ci_check.py
```

## Birincil teknik başvurular

- Linux mount namespaces: https://man7.org/linux/man-pages/man7/mount_namespaces.7.html
- pivot_root: https://man7.org/linux/man-pages/man2/pivot_root.2.html
- Linux 6.6 Landlock: https://docs.kernel.org/6.6/userspace-api/landlock.html

Bu belgeler mekanizmayı açıklar; bu depodaki uygulamanın kabulü yalnız açık
kaynak ve deney makbuzlarına dayanır. Kesin test/CI/commit sonucu son kabul
bölümüne ve `status.md` dosyasına ancak gözlendikten sonra yazılır.

## Son yerel kabul — 2026-10-19T00:48:55.920603+03:00

Gerçek Gateway4/4 aynı185 kaynaklık snapshot ile PASS; aynı PID üzerinde
netns + IPC mount view + Landlock. Kernel24 erişim ve5 başlangıç reddi
PASS. Tam1967/1967 unittest PASS,exit0,skip0,283source hash aynı. Yeni29
test toplamda bir kez; Linux üzerinde aynı29 ayrıca PASS. Statik kontrol
PASS1967 keşif,1395root dosya,2gitlink; bu ek test yürütmesi değildir.
Kontrollü12 test kimlik bilgisi,21 kamu dosyasında bulunmadı; ilgili
Gateway/broker0 çalışıyor. Bu genel sır taraması değildir.
Kodun exact SHA yayın/CI bilgisi aşağıda veya status.md içinde ayrı tutulur.

## Git teslimi — 2026-10-19T00:53:51.782087+03:00

Kod `7a9623321cc5b3296f48f45b99312cf89424203d`, `alaz/d3b-ipc-a731` dalında yayımlandı.
283 kaynak Git blobu test edilen baytlarla eşleşir; uzak dal eşit ve
çalışma ağacı temiz doğrulandı. GitHub alaz/local-ci bu kayıt anında
PENDING (56646653273); yerel1967 PASS uzakCI başarı diye yazılmaz.
Son belge/status commitinin CI durumu ayrıdır. Geç gelen nihai CI sonucu
varsa runtime/d3b-ipc-a731/final-ci.json yerel makbuzunda ayrıca kaydedilir.
Main ve önceki çalışma ağaçları değiştirilmedi.

Sonraki dar kabul: broker yalnız kendisinin yazabildiği kalıcı bütçe ve
tek-kullanımlık istek kayıtlarıyla karar vermeli. Gateway DB üzerinde
ticket/limit/state değiştirme, broker restart ve kayıp yanıt deneyleri
ek provider izni veya bütçe sıfırlaması yaratmamalı. Bu belge tasarımdır,
uygulanmış yeni otorite değildir.
