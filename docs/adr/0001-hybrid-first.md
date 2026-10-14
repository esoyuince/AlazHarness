# ADR-0001 — Önce OpenClaw–Hermes hibriti

Tarih: 2026-10-14. Hibrit-önce yönü: kullanıcı tarafından seçildi. Teknik bileşen sınırları: kaynak incelemesi bekleyen öneri.

## Karar

Çalışan mevcut parçaları birleştir; harness'i baştan yeniden üretme. OpenClaw kontrol/olay katmanı ve Hermes yürütme/hafıza katmanı öncelikli adaydır. İki projede aynı sorumluluğu yapan parçaların ikisini birden çalıştırma. AlazHarness otonomi katmanı çalışan hibritten sonra gelir.

## Depo düzeni

Ana depo C:\Antigravity\AlazHarness içinde proje belgeleri, adaptörler ve sözleşme testlerini tutar. vendor/openclaw ile vendor/hermes-agent, kullanıcı forklarına bağlı Git submodule olarak commit'e sabitlenir. Böylece lisanslar, özgün geçmiş ve güncelleme izlenebilirliği korunur. Gerekli kaynak değişiklikleri ilgili forkta alaz/mvp-0.1 dalında yapılır; ana depoda gitlink ve kaynak kilidi birlikte ilerletilir.

Bu, yalnız referans depo okuma yaklaşımı değildir: MVP'de seçilen gerçek kaynak bileşenleri çalışacaktır. Kaynakların şu anda ayrı klasörlerde olması, iki bağımsız ajan döngüsü çalıştıracağımız anlamına gelmez.

## Seçilmeyen alternatifler

- Her şeyi sıfırdan yazmak: kullanıcı hedefi ve MVP maliyetiyle uyumsuz.
- İki tam asistanı her mesajda birbirine danıştırmak: mükerrer model maliyeti ve belirsiz state sahipliği.
- İki ağacı tek Git geçmişine izsiz kopyalamak: köken, lisans ve upstream güncelleme zorluğu.
- ACP'yi incelemeden tek entegrasyon çözümü kabul etmek: tüm gerekli özellikleri aktardığı doğrulanmadı.

## Sınır

Henüz bağımlılık kurulumu, uygulama build'i veya çalışan hibrit yok. Bu ADR entegrasyon testlerinin yerine geçmez.
