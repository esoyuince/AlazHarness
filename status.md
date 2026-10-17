# AlazHarness — AF13 Linux native QA

Son güncelleme: 2026-10-17T10:34:07.418965+03:00

Tamamlanan kapsam: üç ayrı fresh Linux Gateway/broker senaryosu ve bunların
R1 evidence/JSON/textCLI doğrulaması. Üç son rapor PASS;16negatif veri/kimlik
kontrolü ve3observer metadata kontrolü geçer. İki ek fresh normal çalışma
ilk-read WAL/SHM yan etkisini tekrarladı. Toplam5native çalışma3ana senaryo;
ücretli/model çıkarımı0. Salt-okunur yeniden okuma yeni ajan işi değildir.

1374/1374 standart PASS,skip0,217ölçülen kaynak drift0. YeniR1B0 Windows
paketi1403test ayrı ürün dalının sonucudur; toplamlar birleştirilmez.
G01 filesystem-zero-write ilk-okuma FAIL korunur; SQLite mode=ro WAL/SHM
oluşturabiliyor. Ana DB/veri/izin/bütçe değişimi görülmedi. Ürünefixuygulanmadı.

Çalışma: C:\Antigravity\AlazHarness\scratch\worktrees\r1b-linux-qa-af13
Dal: alaz/r1b-linux-qa-af13
Taban: b96a83f545ae12885f025ee0085cb018dad14511
Rapor: docs/research/R1B-LINUX-EVIDENCE-QA-AF13.md
Kanıt: evidence/r1b-linux-qa-af13
Native private: /tmp/alaz-r1b-af13
Bu QA dalı ürün yazıcısı değildir;8cb8 ürün/yayın sahibi korunur.
Kaynak capture ve provider request-view UYGULANMADI; sıradaki R1B1/R1B2.
Ana ürün pointer: scratch/worktrees/evidence-r1b-8cb8/status.md.
Main ve upstreamler değişmez; seçilmiş QA dosyaları commit/push aşamasında.
