# Kaynak birleştirme incelemesi — M1 öncesi

Tarih: 2026-10-14. Durum: hazırlık kontrol listesi; uygulanmış mimari veya ürün kabulü değil.

Ana plan `MVP-v0.1.md` ve çalışma kuralları `WORKSPACE-RULES.md` değişmez. Bu belge o planın kaynak seviyesinde nasıl doğrulanacağını detaylandırır.

## Modül başına kanıt

Her TAKE / ADAPT / OMIT kararına kaynak adı, sources.lock.json SHA'sı, dosya/sembol, bağımlılıklar, lisans bildirimi, ilgili test ve neden eklenir. Sadece belge anlatımı veya eski sohbet yeterli değildir.

## Birleşim sınırında cevaplanacaklar

1. Olay nereden giriyor; hangi modül gerçek model/araç döngüsünü başlatıyor? İkinci gereksiz LLM çağrısı var mı?
2. Görev/deneme/oturum/ajan kimliğinin sahibi kim? Aynı olay tekrar geldiğinde ne olur?
3. İptal sadece arayüzü mü durduruyor, gerçek çalışan aracı da mı? Süreç kesintisinde unknown yan etki nasıl uzlaştırılıyor?
4. ACP, TUI JSON-RPC ve doğrudan Python arayüzünde hedef, izin, resume ve akış desteği hangilerinde gerçekten var?
5. Hafıza/skill dosyalarını kim yazıyor? Yeni oturumda ne zaman yükleniyor? Başka ajanın state'ine erişim engeli nerede?
6. Bütçe rezervasyonu nerede yapılıyor; fiyat bilinmezse unknown kaydı korunuyor mu? Zamanlayıcıların tek sahibi var mı?
7. Sandbox sınırı gerçek subprocess/filesystem/network noktasında mı? Sadece prompt veya örnek ayar güvenlik kanıtı değildir.
8. Hermes/OpenClaw kullanıcının mevcut profilini istemeden açıyor mu? Test ortamına özel state yolları kaynak kodunda doğrulanmalı.
9. Hangi kurulum/lifecycle scriptleri çalışacak; hangi sürümlere ihtiyaç var? Global ortam yerine projeye özel ortam kullanılmalı.
10. Becerinin yazılmış olmasıyla yeni görevde işe yaraması ayrı ölçülüyor mu?

## Bağımsız kaynak hazırlık kontrolü

`python scripts/verify-source-snapshot.py` iki vendor deposunda kök, remote, HEAD, temiz çalışma ağacı, lisans hash'i, izlenen dosyaların varlığı ve Git nesne bağlantısını kontrol eder. Ağ/model çağrısı yapmaz, rapor verilmezse dosya yazmaz. `--output evidence/<paket>/source-snapshot.json` yeni bir rapor oluşturabilir; mevcut raporu ezmez.

`python -m unittest discover -s tests -p test_source_snapshot_checks.py -v` yalnız bu kontrol aracının küçük birim testlerini çalıştırır. Bunların geçmesi hibrit MVP kabulü değildir.

GitHub fork-parent ilişkisi, kök alt modül/kilit uyumu, LFS yükleri, bağımlılık kurulumu ve ürün testleri ayrıca doğrulanır. Tüm tarihçe indirilmediyse HEAD kaynak kontrolünü tarihçe tamlığı olarak sunmayız.
