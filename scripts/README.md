# Hazırlık araçları

- verify_workspace.py: kaynak kilidi/gitlink/remotes/hash'ler, gerekli dosyalar ve Git dışı runtime kontrolü; --deep Git nesne bağlantısını da denetler.
- verify-source-snapshot.py: bağımsız kaynak ağacı ve dosya varlığı kontrolü; ürün testi değildir.
- restore_sources.py: varsayılan yalnız plan; --apply kaydedilmiş submodule kaynaklarını geri yükler, paket kurmaz.
- setup-openclaw-pnpm.ps1: kaynaktaki pnpm sürüm/bütünlük pinini projeye özel runtime alanında kurar veya doğrular; global ortamı değiştirmez.
- pnpm-openclaw.ps1: açıkça verilen argümanları projeye özel pnpm ile OpenClaw dizininde çalıştırır. install/build gibi argümanlar gerçekten yan etki yaratır; otomatik çağrılmaz.

Bütün yollar C:\Antigravity\AlazHarness altında çözülür. Yeni bir betik ağ/komut/ücretli model işlemi yapıyorsa bunu adında ve açıklamasında açıkça belirtmelidir.
