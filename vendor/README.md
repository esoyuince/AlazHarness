# Sabitlenen kaynaklar

- openclaw/: esoyuince/openclaw fork'u; upstream openclaw/openclaw.
- hermes-agent/: esoyuince/hermes-agent fork'u; upstream NousResearch/hermes-agent.

Her alt depo ana projede bir Git submodule olarak tutulur. sources.lock.json kayıtları ve gitlink commit'leri aynı olmalıdır. origin kullanıcının fork'u, upstream resmî kaynaktır. Geliştirme dalı alaz/mvp-0.1; main kaynak tabanıdır.

İlk klonlar depth=1 ve yalnız main kaynak ağacını içerir; eski Git geçmişinin tamamı indirilmez. Bu, çalışma ağacının sparse olduğu anlamına gelmez. Gereken eski geçmiş daha sonra hedefli fetch ile alınabilir. İç içe submodule varsa URL/commit kontrolüyle ayrıca kaydedilir.

Lisans metinlerini veya atıfları kaldırmayın. Kaynaklardaki .env örneklerini gerçek sırlarla doldurmayın. Otomatik install/postinstall/setup/onboarding çalıştırmayın; önce paket ve lifecycle gereksinimlerini inceleyin.
