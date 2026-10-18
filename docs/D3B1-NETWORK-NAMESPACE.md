# D3B1 — Gateway için çekirdek düzeyinde ağ sınırı

İş: D3B-NETNS-4E62. Tarih: 18 Ekim 2026.
Dal: `alaz/d3b-netns-4e62`; başlangıç `2bffac9aaf482363d335bdbd3c76cc687be83533`.

## Uygulanan parça

`packages/claw-hermes/linux_netns.py`, taze ve tek iş parçacıklı Linux x86_64
sürecini yeni kullanıcı/ağ namespace'ine alır. Yalnız kendi loopback arayüzünü
açar; sonra etkin, izin verilen, miras alınan, bounding ve ambient Linux
capability kümelerini sıfırlar. `no_new_privs` ve seccomp filtresi kurar.
Kurulumun herhangi bir adımı başarısızsa başlatıcı hedef programı çalıştırmaz;
sınırsız moda sessiz geçiş yoktur.

`run_in_network_namespace.py` açık operatör komutudur. Var olan mutlak
executable yolu ve yeni makbuz dosyası ister. Varsayılan çalışan kişisel veya
üretim Gateway ayarını değiştirmez. Sistem hesabı, global firewall, paket,
servis veya kalıcı ağ namespace'i oluşturmaz. Testte yalnız önceden hazırlanmış
özel WSL ortamı kullanıldı.

Host ağında önceden açılmış soketlerin taşınmaması için 0–2 dışındaki dosya
tanıtıcıları kapatılır; soket tipindeki standart giriş/çıkış reddedilir.
Normal AF_UNIX/IPv4/IPv6 soketleri dışında AF_VSOCK, AF_NETLINK, AF_PACKET ve
diğer aileler reddedilir. Namespace'e tekrar girme/değiştirme, yeni namespace
bayraklarıyla clone, ptrace/process_vm, pidfd_getfd, io_uring ve mount işlemleri
kısıtlanır. recvmsg/recvmmsg ile başka süreçten soket tanıtıcısı alma engellenir.
clone3 için ENOSYS dönüşü normal iş parçacığı oluşturmanın clone geri dönüşünü
korur. Bu kara liste tam syscall sandbox politikası değildir.

## Gerçek native ölçüm

`verify_network_namespace.py`, yalnız testin sahip olduğu host loopback
sunucularına karşı pozitif ve negatif kontroller kurar. Yönetimsiz host
bağlantısı başarılıyken sınır içindeki doğrudan Python ve ham libc bağlantıları
host IPv4/IPv6 sunucularına ulaşamaz. Harici bir sunucuya paket gönderilmez:
UDP kontrolü dokümantasyon adresine yerel yönlendirme yokluğu üzerinden yapılır.
Yeni exec alt süreci de aynı kısıtlamaları taşır. Önceden bağlı host soketi
aktarılmaya çalışıldığında kapanmıştır. Özel namespace loopback ve açıkça
kullanılan yol tabanlı Unix IPC çalışır.

Son native rapor 21 kontrol içerir. Bunlar 21 ayrı model deneyi değildir.
Ayrıca gerçek, sabit kaynaklı Hermes Gateway yeni ağ namespace'i içinde;
üretim broker'ı ve programlanmış HTTP sağlayıcısı host namespace'inde çalışır.
Mevcut D1 → D2A → D2B1 → D2B2 zinciri değiştirilmez. Güvenilir test kontrolcüsü,
Gateway'in yerel API'sine ulaşmak için host tarafından nsenter ile içeri girer;
kısıtlanmış Gateway aynı setns işlemini yapamaz. Kontrolcünün ayrı güvenilen
yetkisi bütün sandbox içeriğinin güvenli olduğu iddiasına dönüştürülmez.

Normal koşuda dört broker isteği tamamlanır. Yetersiz toplam bütçe, dersli
yanıtın kaybı ve inceleme kararının geri alınması ayrı profillerde sınanır.
Bu olumsuz koşullarda kayıt unknown kalmalı, tekrar yeni rezervasyon yapmamalı,
Gateway/broker temiz kapanmalıdır. Testlerin nihai sonucu JSON makbuzlarından
okunur; yalnız başarılı başlatma kabul sayılmaz.

## İlk hata ve düzeltme

İlk Gateway koşusunda seccomp'un sendmsg yasağı Python 3.14 asyncio'nun
birden fazla tamponla HTTP yanıtı yazmasını engelledi. D1 veritabanında
completed iken operatör yanıtı alamadı. Başarısız makbuz korunur; aynı iş
körlemesine yeniden gönderilmedi. Yeni özel profilde normal sendmsg/sendmmsg
iletime izin verildi. recvmsg/recvmmsg ve pidfd_getfd yasağı, açık FD kapatma,
ağ namespace'i ve capability sıfırlama korundu. Böylece çalışan bağlantı
tanıtıcılarına normal veri gönderimi korunurken descriptor alma açılmadı.
Bu testte Unix IPC için tam alıcı/sunucu allowlist'i bulunduğu iddia edilmez.

## D3B'nin tamamı değildir — önemli açık sınırlar

**Host UID ve dosya sistemi hâlâ paylaşılır.** Yeni user namespace, ayrı bir
host servis hesabının yerine geçmez. Yol tabanlı Unix soketleri erişilebilir;
yetkili yerel servisler veya Windows/WSL entegrasyon uçları tam olarak
sınırlandırılmış değildir. Host dosyaları ve başka süreçlerin erişilebilir
bilgileri için deny-by-default mount/PID/credential sınırı henüz yoktur.
Bu nedenle kötü niyetli tüm Gateway kodunun kimlik bilgisi okuyamayacağı,
başka host hizmetini aracı yapamayacağı veya host durumunu değiştiremeyeceği
iddia edilmez. Paylaşılan veritabanı ve broker kullanıcı kimliği mevcut
D3A güven modeli içinde kalır.

**D3B1 kabulü yalnız doğrudan ağ namespace'i/çekirdek filtre dilimidir.**
Tam D3B, uzaktan HTTPS sağlayıcı kabulü, gerçek tarife/token sözleşmesi,
Docker araç birleşimi ve gerçek modelle bağımsız öğrenme hâlâ AÇIKTIR.
Kullanıcının sağlayıcı anahtarları okunmadı, gerçek model çağrılmadı ve
aktif hafıza/beceri terfisi açılmadı. 8/12 → 12/12 yerel test yanıtları
programlanmıştır; öğrenme kanıtı değildir.

## Kaynaklar ve yeniden üretim

Linux çekirdeğinin no_new_privs ve seccomp davranışları:
https://cdn.kernel.org/doc/html/latest/userspace-api/no_new_privs.html
https://www.kernel.org/doc/html/v6.10/userspace-api/seccomp_filter.html
Kullanıcı namespace'i ve capability modeli:
https://man7.org/linux/man-pages/man7/user_namespaces.7.html

Testler, mevcut ortamın Linux 6.6 WSL çekirdeği ve libseccomp kütüphanesi
üzerinde sınandı. Başka mimari/işletim sisteminde açılmayı reddeder.

```text
python3 -B scripts/qa/verify_network_namespace.py --output <new-evidence.json>
<prepared-python> -B scripts/qa/verify_gateway_network_namespace.py --scenario normal --source-workspace <pinned-source> --python <prepared-python> --node <private-node> --output <new-private-runtime> --public-receipt evidence/d3b-netns-4e62/<new-receipt>.json
```

Ayrı Gateway senaryoları: normal, budget-limit, candidate-disconnect,
review-revoked. Test profilleri özel runtime içinde teşhis için tutulur.
Oluşturulmuş program ve sırlar kullanıcıya ait diğer projelerden bağımsızdır.
`tests/test_linux_netns.py` çevrimdışı sözleşme ve makbuz kontrolleridir;
standart testlerde yeni namespace veya Gateway çalışması başlatmaz.

## Kesin sonraki adım

Gateway için yalnız gereken kaynak/runtime ve broker soketinin görünür olduğu
salt okunur mount düzeni, ayrı PID görünümü ve host servis kimliği tasarlayıp
broker peer-credential sözleşmesiyle birlikte test et. Özellikle broker anahtar
dosyasını, diğer host Unix hizmetlerini ve host süreçlerine erişimi canary
kanıtıyla reddet. Bu gerçekleşmeden network-only sonucu tam güvenli otonomi
veya gerçek sağlayıcıya sınırsız yetki olarak kullanma.

## Son kabul — 2026-10-18T11:51:45.714629+03:00

Çekirdek düzeyinde 21/21 kontrol ve aynı ürün sürümüyle dört gerçek Gateway
senaryosu PASS. Çevrimdışı tam regresyon **1.876/1.876 PASS**, exit0, atlanan
test yok. Yeni 17 test bu toplamın içindedir; dört native koşu ayrıca
çalıştırılmıştır. Ölçülen 266 kaynak/test/konfigürasyon dosyası değişmedi.
Statik kapı PASS; test keşfi ikinci bir tam test çalışması değildir.

Bu işe ait beş deneme profilinde Gateway kapanışı doğrulandı; çalışan
Gateway/broker bulunmadı. 25 oluşturulmuş test kimlik bilgisiyle yapılan
kontrolde 27 taranmış kamuya açık dosyada eşleşme yoktu. Özel teşhis
profilleri tutulmaktadır. Bu kontrol genel sır veya tam OS izolasyon
sertifikası değildir. Kod yayını ve CI ayrı takip edilir.

## Git teslimi — 2026-10-18T11:54:39.352557+03:00

Ürün kodu, testler ve kanıtlar `1b8beb5fabfa973d9bef999a466021e8bf9bb355` commit’iyle
`alaz/d3b-netns-4e62` dalına gönderildi. Yayımlanan 266 kaynak dosyası
test edilen sürümle aynı. Son GitHub sorgusunda `alaz/local-ci` PENDING
idi; bu durum PASS sayılmıyor. Tam 1.876 yerel test, 21 native kontrol ve
dört Gateway koşusu bağımsız yerel kabul kanıtlarıdır.

Bu teslim kaydını içeren yalnız-belge commit’inin CI’si de ayrıca
doğrulanmalıdır. `main` ve korunmuş kök değişiklikleri aynı kaldı.
