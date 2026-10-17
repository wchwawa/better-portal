# Windows 10/11 - topluluk test ön sürümü

Yeni sürekli otomasyon için [AUTOMATION.tr.md](AUTOMATION.tr.md). Bu kılavuz yalnız süreli elle başlatılan oturumları anlatır.

Windows desteği fiziksel cihazlarla henüz doğrulanmadı. GitHub'da yalnız ön sürüm (prerelease) olarak sunulur; kararlı sürüm değildir. macOS'ta geçen çevrimdışı testler Windows sürücüsü veya gerçek bağlantı testi yerine geçmez.

## 1. Kurulum

- ZIP'i Windows'a aktar, tamamen bir klasöre çıkar. ZIP'in içinden çalıştırma. Klasör yalnız güvendiğin kullanıcılar tarafından değiştirilebilsin.
- [Python](https://www.python.org/downloads/windows/) 3.10 veya üstü kurulu olsun; Python launcher (`py`) dahil olmalı. Python 3.12/3.13/3.14 kullanılabilir.
- [Npcap](https://npcap.com/#download) resmî yükleyicisini kur. Eski WinPcap yerine Npcap kullan. Scapy rehberine göre WinPcap compatibility mode kapalı kalsın. Npcap erişimini yöneticilerle sınırlayabilirsin; deneme başlatıcıları zaten yönetici yetkisi ister. Wi-Fi monitor/raw 802.11 modu gerekmiyor; normal Ethernet görünümü kullanılacak. Sürücüyü bu pakete dahil etmiyoruz.
- `Setup-Windows.cmd` çift tıkla. Python ortamını kurar ve çevrimdışı testleri çalıştırır. Testler başarısızsa canlı denemeye geçme.
- Windows, Mac, PS5 ve Portal aynı yerel ağda olsun. PS5 Ethernet tercih edilir. Windows PC için de mümkünse Ethernet kullan; Wi-Fi sürücülerinde paket gönderme desteği değişebilir. USB gerekmez. Mac başlatıcısı aynı anda çalışmasın.

## 2. Adresleri ayarla ve kontrol et

- `Configure-Windows.cmd` üzerine sağ tık → **Yönetici olarak çalıştır**.
- İnternete/yerel ağa bağlı adaptör numarasını seç. VPN, loopback ve sanal adaptörü seçme.
- PS5 ve Portal'ın güncel IPv4 adreslerini gir. Adresleri cihazların ağ ekranından veya router uygulamasından öğren. Mac'in eski adreslerini varsayma.
- `Check-Windows.cmd` → **Yönetici olarak çalıştır**.
- `CHECK PASSED` bekle. Bu adım yalnız rota, IP forwarding, iki cihazın MAC adresleri ve Npcap erişimini kontrol eder; yönlendirme değiştirmez.
- Paylaşıma açık/hotspot/VPN veya IP yönlendirme etkin bir adaptörde program durabilir. Güvenlik duvarını kapatmanı istemiyoruz. Hata metnini paylaş.

## 3. Önce değişikliksiz bağlantı denemesi

- Portal'ın PS5 bağlantısını kes.
- `Baseline-Windows.cmd` → **Yönetici olarak çalıştır**.
- Enter, ardından **READY / HAZIR** mesajından sonra Portal'dan PS5'e bağlan.
- Aktarma 40 saniyeyle sınırlı. PS5 kabulü + STREAMINFO, iki yönde paket aktarımı ve hatasız geri yükleme görülürse `Baseline passed` yazılır.
- Görüntü ve kontrolün normal kaldığını gözünle doğrula. Sonuçta `restoration_errors` boş olmalı.
- Başarılı baseline kaydı yoksa bitrate denemesi açılmaz. Başarılı kayıt gerçek gecikme/akıcılık ölçümü değildir.

## 4. Bitrate denemesi

- Yeni bağlantı için tekrar Portal'ın PS5 bağlantısını kes.
- `Start-Windows.cmd` → **Yönetici olarak çalıştır**.
- İlk Windows denemesinde **65** seç. Başarılı ve akıcıysa ayrı yeni bağlantılarda 100, sonra 200 denenebilir.
- Enter → **READY / HAZIR** → Portal'dan bağlan.
- `Startup packet modified` mesajını, ardından sonucu bekle.
- Ayrı Npcap yakalama tutamacı değiştirilen paketin yerel çıkışını doğrular. Ham paketler diske yazılmaz.
- Başarı: yeni başlangıç, kabul ve akış bilgisi sonrası üç yüksek hedef; ayrıca bağımsız yerel çıkış doğrulaması. Bunun dışında kod 1 dönebilir. 200 profilinin hedefi 158 Mbps civarında kalırsa üç kez 160 Mbps koşulu sağlanmaz; bu bağlantı başarısız demek değildir.
- İşlemden sonra PC aradan çıkar. Hedef sayı gerçek video hızı değildir. Portal'da gördüğün hız, çözünürlük ve takılma durumunu bildir.

## Geri dönüş / kurtarma

- Normal ayara dönmek için Portal bağlantısını kes, başlatıcı olmadan yeniden bağlan.
- Ctrl+C temizliği tetikler. Terminali kapatma, PC'yi uyutma veya kapatma yerine Ctrl+C kullan.
- Bağımsız kurtarma süreci hazır olduktan 50 saniye sonra, ana işlem çökmüş olsa da özgün ARP eşlemelerini göndermeyi dener. Windows routing, kayıt defteri veya firewall ayarı değiştirilmez.
- `restoration_errors` varsa bilgisayarı en az 60 saniye açık tut. Deneme klasöründeki `recovery-state.recovery.json` ve `watchdog.log` dosyalarını incele. Bilgisayar kapanırsa kurtarma çalışamaz.
- Aktif işlem/watchdog kalmadığında yönetici Terminal'de `".venv\Scripts\python.exe" portal_windows.py --restore "experiments\ILGILI-KLASOR\recovery-state.json"` ile yalnız programın ürettiği ilgili kaydı tekrar uygula. Başkasından gelen kurtarma dosyasını çalıştırma.
- Bağlantı hâlâ bozuksa PS5 ve Portal ağ bağlantılarını yeniden kurarak komşu adres eşlemelerini yenile.

## Paylaşılacak sonuç

TUI, IP adreslerini girdikten hemen sonra **Setup check failed** veya **Could not finish** gösterirse başlığın altındaki hatayı oku. **D**, ardından **↑ / ↓** ile tam hata metnini görüntüle; Enter veya Esc ile geri dön. **Setup check failed**, ağ eşlemeleri değiştirilmeden önce bir kontrolün denemeyi durdurduğu anlamına gelir. Hata başka bir bağlantıyı gösteriyorsa tekrar dene ve **PC LAN adapter** altında onu seç. Yalnız başlık nedeni belirlemez; özel adresleri kaldırarak tam hata metnini paylaş.

TUI ilk kullanımda iki cihazın IP adreslerine doğrudan ulaşan bağlantıyı önerir. Öneriyi kontrol et veya **← / →** ile Wi-Fi/Ethernet bağlantını seç. Kaydedilmiş ve elle seçilmiş adaptörler korunur. Öneri yoksa adaptörü elle seç ve iki IP adresini kontrol et.

Önce Check ve Baseline terminal çıktılarını gönder. Sonra profil testi sonucu: `counts`, `ps5_messages`, `high_target_confirmed`, `egress_witness`, `restoration_errors` ve Portal gözlemin. `config.windows.json`, `windows-baseline.json`, `recovery-state.json` özel ağ bilgisi içerir; public issue'ya yükleme. Paket içindeki gerçek IP'ler yalnız sen Windows'ta girince oluşur.

Teknik kaynaklar: [Scapy Windows kurulumu](https://scapy.readthedocs.io/en/stable/installation.html), [Npcap rehberi](https://npcap.com/guide/npcap-users-guide.html). Adaptör/sürücü uyumluluğu canlı test gerektirir.

## İndirme ve ilk kez kullananlar için ek açıklamalar

1. GitHub **Releases** bölümünde **Windows Community Preview** ön sürümünü aç. **Assets** altındaki Windows ZIP paketini indir.
2. ZIP'e sağ tık → **Tümünü ayıkla**. Dosyaları birlikte tut. Mac'teki `.venv` klasörünü kopyalama.
3. Python kurulumu sonrası yeni Komut İstemi'nde `py -3 --version` yaz. 3.10 veya üstü görünmeli; `py` bulunamıyorsa Python launcher kurulumunu düzelt. WSL kullanma.
4. Npcap kurulunca açık terminalleri yeniden aç. Wireshark veya Git kurmak gerekmiyor. Python ve Npcap pakete dahil değil; resmî sitelerinden indir.
5. `Setup-Windows.cmd` testleri **OK** ile bitmeli. Kurulum bağımlılığı indirmek için internet ister.
6. Sonraki `.cmd` dosyalarında sağ tık → **Yönetici olarak çalıştır** seç ve Windows UAC istemini onayla. Windows parolanı kimseyle paylaşma.
7. **Configure → Check → Baseline → Start (65)** sırasını izle. Yukarıdaki adımlar başarılı olmadan sonraki aşamaya geçme. Başka bir Mac/PC başlatıcısı aynı anda çalışmasın.

## Test sonucunu gönderme

GitHub **Issues → New issue → Windows preview test result** şablonunu kullan. Başarılı sonuçlar da gerekli: Windows sürümü, Python/Npcap sürümü, adaptör modeli, Ethernet/Wi-Fi, Portal firmware'i, hangi aşamaya ulaştığın ve görüntü/akıcılık gözlemini yaz.

- Kod **0**: aşamanın yazılımsal koşulları sağlandı; görüntü ve kontrolü ayrıca dene.
- Kod **1**: aşama doğrulanmadı; özellikle 200 profilinde bu tek başına bağlantı başarısız demek değildir.
- Kod **2**: hata var; metni ve geri yükleme sonucunu incele.

Yerel sentetik testler macOS'ta çalıştırıldı. Windows sürücüsü, fiziksel adaptörden paket gönderimi ve Windows üzerinden gerçek PS5/Portal oturumu henüz doğrulanmadı. GitHub otomatik testlerinin durumunu ayrıca kontrol et; geçmişte hesap kaynaklı runner engeli vardı. Bu ön sürüm için kesin çalışma garantisi vermiyoruz.
