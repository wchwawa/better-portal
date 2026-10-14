## Teşekkürler

Orijinal bit hızı ayarlama yöntemi **[@atameric](https://github.com/atameric)** ve [ps5-portal-high-bitrate](https://github.com/atameric/ps5-portal-high-bitrate) projesinden gelir. [Orijinal geliştiriciyi destekleyebilirsiniz](https://buymeacoffee.com/atameric).

[MIT](LICENSE) lisansı altında yayımlanır. Bağımsız bir topluluk yazılımıdır; Sony veya PlayStation ile bağlantılı değildir.

# Better Portal

[English](README.md) · [简体中文](README.zh-CN.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Español](README.es.md) · [Français](README.fr.md) · **Türkçe**

PlayStation Portal üzerinden kendi PS5’inizde oynarken daha yüksek bir görüntü kalitesi hedefi seçin. Better Portal, **macOS veya Windows** üzerinde kurulumu ekran ekran anlatır.

Bu kılavuz Türkçedir. Terminal arayüzü şu anda **English, 简体中文, 日本語, 한국어, Español ve Français** dillerini destekler. Aşağıdaki görseller İngilizce Mac arayüzünden alınmıştır.

[macOS hızlı başlangıç](#macos-quick-start) · [Windows hızlı başlangıç](#windows-quick-start) · [İlk oturum](#first-session) · [Cihaz adreslerini bulma](#find-device-addresses) · [Sorun giderme](#questions-and-fixes)

## Başlamadan önce

Şunları hazırlayın:

- Bir **Mac veya Windows 10/11 bilgisayar**, bir **PS5** ve bir **PlayStation Portal**. Portal, kendi PS5’inizde Uzaktan Oynama ile normal şekilde oyun oynatabiliyor olmalıdır.
- Üç cihaz da **evinizdeki aynı yönlendiriciye** bağlı olmalıdır. Bilgisayar ve Portal ev Wi-Fi ağını kullanabilir; PS5 aynı Wi-Fi ağına veya bu yönlendiriciye bir ağ kablosuyla bağlanabilir. Misafir ağını kullanmayın; bilgisayarda VPN kullanıyorsanız bağlantısını kesin.
- Kurulum için internet erişimi ve bilgisayarınızda Better Portal’a yönetici izni verebilme olanağı.

Bu, topluluk tarafından geliştirilen deneysel bir araçtır. **65 Mbps** ile başlayın. Bit hızı, her saniye gönderilebilen görüntü verisinin miktarıdır. Daha yüksek bir değer ayrıntıları iyileştirebilir, ancak bağlantı kararsızsa takılmalara da yol açabilir.

<a id="get-started"></a>

## Hızlı başlangıç

Kurulumu yalnızca bir kez yapmanız gerekir. İndirdiğiniz klasörü bütünüyle saklayın; her oyun oturumunda açacağınız dosya bu klasördedir.

**Kullandığınız bilgisayara** uygun adımları izleyin. Setup bağımlılıkları bir kez kurar; Start, her yeni Portal bağlantısı için sihirbazı açar.

| Bilgisayarınız | İlk kurulum | Oturum başlatma |
| --- | --- | --- |
| **macOS** | **Setup.command** dosyasına çift tıklayın | **Start.command** dosyasına çift tıklayın |
| **Windows 10 / 11** | **Setup-Windows.cmd** dosyasına çift tıklayın | **Start-Windows.cmd** dosyasına çift tıklayın |

<a id="macos-quick-start"></a>

### macOS hızlı başlangıç

<a id="install-python"></a>

1. **Python’u kurun:** [Python’un Mac indirme sayfasını](https://www.python.org/downloads/macos/) açın, **Python 3.14 macOS installer** seçeneğini seçin ve indirdiğiniz `.pkg` dosyasını açın. **Continue → Install** adımlarını izleyin. Python 3.10 veya daha yeni bir sürümü zaten kullanıyorsanız onu kullanmaya devam edebilirsiniz.
2. **Python kurulumunu tamamlayın:** Finder’da **Applications → Python 3.14** klasörünü açıp **Install Certificates.command** dosyasına çift tıklayın. `update complete` yazısını bekleyin, ardından pencereyi kapatın. Başka bir Python sürümü için onun Applications klasörünü kullanın. [Resmî kurulum adımlarına](https://docs.python.org/3.14/using/mac.html) bakabilirsiniz.
3. **Better Portal’ı indirin:** [ZIP dosyasını indirin](https://github.com/wchwawa/better-portal/archive/refs/heads/main.zip), **Finder → Downloads** klasörünü açın ve ZIP dosyasına çift tıklayarak çıkarın. **better-portal-main** klasörünü açın.
4. **İlk kurulumu yapın:** **Setup.command** dosyasına çift tıklayın. Bir Terminal penceresi açılır. **`Setup complete.`** yazısını bekleyin, **Return** tuşuna basın ve pencereyi kapatın.
5. **Oturum başlatın:** aynı klasördeki **Start.command** dosyasına çift tıklayın. **`Password:`** yazısı görünürse **Mac oturum açma parolanızı** yazıp **Return** tuşuna basın. **Yazarken harf veya nokta görünmemesi normaldir.** [İlk oturum](#first-session) bölümüne geçin.

macOS bir başlatıcıyı engellerse [“macOS dosyayı açmıyor”](#macos-blocked) bölümüne bakın. Kurulum başarısız olursa oturum başlatmadan önce [Sorular ve çözümler](#questions-and-fixes) bölümündeki adımları izleyin.

<a id="windows-quick-start"></a>

### Windows hızlı başlangıç

1. **Python’u kurun:** [Python’un Windows indirme sayfasını](https://www.python.org/downloads/windows/) açın ve **`py` başlatıcısıyla birlikte 64 bit Python 3.14 (x86-64)** kurun. Mevcut, uyumlu bir x86-64 Python 3.10–3.14 kurulumu da kullanılabilir.
2. **Npcap’i kurun:** [npcap.com](https://npcap.com/#download) adresinden indirin. **WinPcap uyumluluk modunu işaretlemeyin**; Wi-Fi izleme modu / raw 802.11 desteği gerekmez. Bu seçenekler [Scapy’nin Windows kurulum adımlarına](https://scapy.readthedocs.io/en/stable/installation.html#windows) uygundur.
3. **Better Portal’ı indirin:** [ZIP dosyasını indirin](https://github.com/wchwawa/better-portal/archive/refs/heads/main.zip). **Dosya Gezgini → İndirilenler** içinde ZIP dosyasına sağ tıklayın → **Tümünü Ayıkla** seçeneğini seçin. Çıkarılan **better-portal-main** klasörünü açın.
4. **İlk kurulumu yapın:** **Setup-Windows.cmd** dosyasına çift tıklayın. **`Setup complete`** yazısını bekleyin, ardından pencereyi kapatmak için bir tuşa basın. Çevrimdışı kontroller başarısız olursa oturum başlatmadan önce hatayı çözün.
5. **Oturum başlatın:** aynı klasördeki **Start-Windows.cmd** dosyasına çift tıklayın ve **Windows izin istemini** onaylayın. [İlk oturum](#first-session) bölümüne geçin.

Windows aynı sihirbazı, dilleri, ayarları ve 120 saniyelik bağlantı geri sayımını kullanır. Cihazlar ekranında **PC LAN adapter** seçimi bulunur. Windows’ta gerçek cihaz testleri devam etmektedir; ayrıntılı gereksinimler ve sorun giderme için [Windows kılavuzuna (İngilizce)](WINDOWS.md) bakın.

**Her iki platformda da:** çıkarılan klasörü bütünüyle saklayın ve her yeni oturum için ilgili Start dosyasını açın. Adresler, dil ve bit hızı kaydedilir. Bu dosyalara çift tıklayarak kurulum yapabilir ve uygulamayı açabilirsiniz; kod düzenlemeniz gerekmez.

<a id="first-session"></a>

## İlk oturumunuz

**Sihirbazı bilgisayarınızın klavyesiyle kullanın.** Klavye girişini alması için terminal penceresinin içine bir kez tıklayın. Renkli düğmeler fareyle değil, tuşlarla seçilir. Mac’teki **Return**, ekranda belirtilen **Enter** tuşudur.

| Tuş | İşlevi |
| --- | --- |
| **Return / Enter** | Seçimi onaylar, sonraki alana geçer veya seçili düğmeyi çalıştırır. |
| **Tab** veya **↑ / ↓** | Cihaz alanları arasında geçiş yapar. `>` işareti geçerli satırı gösterir. |
| **← / →** | Bit hızı satırı seçiliyken değeri değiştirir. `[x]` seçili seçeneği gösterir. |
| **S** | Dili değiştirmek için Ayarlar’ı açar. Tuşa bir kez basmanız yeterlidir; Return gerekmez. |

Aşağıdaki görseller **Mac’te demo modunda çalışan gerçek uygulamayı** gösterir. Windows’ta aynı adımlar izlenir; Mac ağ arayüzü alanının yerine PC ağ bağdaştırıcısı seçilir. `DEMO` yazısı ve adresler örnek içindir. **Kendi cihaz adreslerinizi kullanın ve uygulamanızdaki sayacı izleyin.** Bir görsele tıklayarak büyütebilirsiniz.

### Dil seçin

**↑ / ↓** ile **English**, **简体中文**, **日本語**, **한국어**, **Español** veya **Français** seçip **Return** tuşuna basın. Seçiminiz kaydedilir. Doğrudan Prepare ekranına geçiyorsanız önceden kaydedilmiş bir seçiminiz vardır; **S** ile değiştirebilirsiniz.

![İlk açılışta dil listesi; seçili satır Return ile onaylanır](docs/images/language.png)

### 1. Cihazları hazırlayın

**Portal’da**, hızlı menüyü açmak için sağ üst köşeden sola kaydırın, ardından **Disconnect** seçeneğini seçin. PS5’in açık kalması için **Put the Connected PS5 in Rest Mode** seçeneğini kapalı bırakın. Menüyü bulmakta zorlanırsanız [Sony’nin Uzaktan Oynama kılavuzuna (İngilizce)](https://www.playstation.com/en-nz/support/hardware/playstation-remote-play-on-psportal/) bakın.

**Portal açık ve Wi-Fi ağına bağlı kalsın.** Yalnızca mevcut oyun oturumunu bitiriyorsunuz. Bilgisayarı uyanık tutun; dizüstü bilgisayarın kapağını açık bırakın.

**Bilgisayarınızda**, sarı hatırlatmaları okuyun, ardından Devices ekranına geçmek için **Enter / Return** tuşuna basın.

![Prepare ekranı: aynı ev ağı, Portal’ın PS5 bağlantısı kesilmiş ve Mac uyanık](docs/images/prepare.png)

### 2. İki adresi girin ve 65 Mbps seçimini koruyun

<a id="find-device-addresses"></a>

**Önce PS5 ve Portal adreslerini bulun.** IPv4 adresi, cihazın ev ağındaki numarasıdır: noktalarla ayrılmış dört sayı grubundan oluşur. İki cihazın numarası farklıdır.

1. **Ev yönlendiricinizi veya Wi-Fi ağınızı** yönetmek için normalde kullandığınız uygulamayı ya da yönetim sayfasını açın. Adı, yönlendiricinize veya internet sağlayıcınıza göre değişir.
2. **Devices**, **Connected devices** veya **Clients** gibi bir bölüm arayın. **PS5** kaydını açıp **IP address / IPv4 address** bilgisini not edin. **PlayStation Portal** için de aynısını yapın.
3. İki adresi yanınızda bulundurun. Cihaz adreslerini kullanın; yönlendiricinin adresini, MAC adresini veya internet hız testi sonucunu kullanmayın. **Bu kılavuzdaki `192.168.1.20` ve `192.168.1.30` adreslerini kopyalamayın.**

Görselli bir örnek için [TP-Link Tether’da Local Device → Clients → cihaz yolunu](https://www.tp-link.com/us/support/faq/2611/) izleyebilirsiniz. [ASUS’un da cihaz listesi kılavuzu vardır](https://www.asus.com/us/support/faq/1005513/). Yönlendirici uygulamasını açmayı veya cihazları tanımayı bilmiyorsanız, devam etmeden önce Wi-Fi kurulumunu yapan kişiden ya da internet sağlayıcınızdan iki yerel adresi öğrenin.

**Şimdi Devices ekranını yukarıdan aşağıya doldurun:**

| Satır | İşlemi yapın, ardından Return tuşuna basın |
| --- | --- |
| **PS5 IPv4 address** | Bulduğunuz PS5 adresini yazın. |
| **Portal IPv4 address** | Bulduğunuz Portal adresini yazın. |
| **Mac LAN interface** — yalnızca macOS | Genellikle `en0` gibi önerilen değeri bırakın. Alan boşsa veya başka bir bağdaştırıcı kullanıyorsanız [buradan kontrol edin](#mac-adapter). |
| **PC LAN adapter** — yalnızca Windows | **← / →** ile ev yönlendiricinize bağlı Wi-Fi veya Ethernet bağdaştırıcısını seçin. |
| **Bitrate (Mbps)** | İlk denemede **65 recommended** seçili kalsın. |
| **Save and prepare connection** | Hazırlığı başlatmak için Return tuşuna basın. Portal şimdilik bağlı olmasın. |

Bir alana geçtiğinizde yazmaya başlamak önceki değeri değiştirir. Yanlış yazarsanız **↑** ile geri dönün. Adresler ve bit hızı sonraki kullanım için kaydedilir.

![İlk kullanımda Devices ekranı: PS5 giriş alanı vurgulanır ve yanında type here yazısı bulunur](docs/images/devices-input.png)

<details>
<summary>Klavye adımlarını ve hareketli 65 Mbps önerisini izleyin</summary>

Bu örnekte örnek adresler girilir, önerilen bağdaştırıcı bırakılır, 65 Mbps korunur ve başlatma düğmesine geçilir. Animasyon tekrar eder; gerçek kullanımda girdileriniz ekranda kalır.

![İki adres, Mac bağdaştırıcısı, hareketli 65 Mbps seçimi ve başlatma düğmesi arasında klavyeyle geçiş](docs/images/devices.gif)

</details>

<details>
<summary>100 veya 200 Mbps ne zaman denenebilir?</summary>

Bit hızı satırında **← / →** veya **Boşluk** ile seçim yapın. Kararlı bir 65 Mbps oturumundan sonra **100 Mbps** deneyebilirsiniz. **200 Mbps** deneyseldir ve takılmaları artırabilir. Aynı oyun sahnesini karşılaştırın; daha yüksek değer her zaman daha iyi değildir.

</details>

### 3. Bilgisayarda bekleyin, sonra Portal’dan bağlanın

**Önce: WAIT, beklemeniz gerektiği anlamına gelir.** Bilgisayar cihazları kontrol edip bağlantıyı hazırlarken Portal bağlı olmasın.

![WAIT ekranı: uygulama cihazları kontrol ederken Portal bağlı olmamalıdır](docs/images/connect-wait.png)

**Sonra: READY / CONNECT NOW, Portal’ı elinize almanız gerektiği anlamına gelir.** Portal’ın Uzaktan Oynama ana ekranında PS5’inizi seçip normal şekilde bağlanın. Sihirbazda **02:00** ile başlayan **120 saniyeniz** vardır. Uygulama **bağlantıyı Portal’dan sizin başlatmanızı** bekler.

![READY ekranı: iki dakikalık geri sayım sürerken Portal’ı PS5’e bağlayın](docs/images/connect-ready.png)

Portal bağlandığında bağlantıyı açık bırakın. Bir pencereyi kapatmadan önce bilgisayarda **Result** ekranının görünmesini bekleyin. Süre dolarsa sonuç ekranındaki yeniden deneme adımlarını izleyin.

Erken durdurmak için bilgisayarda **Q** tuşuna basıp sonucu bekleyin. Bağlantı geri yüklenirken bilgisayarı uyanık tutun.

<details>
<summary>Kısaltılmış bir bağlantı örneğini izleyin</summary>

Bu tekrarlanan demo, WAIT durumundan READY durumuna, bağlantı kontrollerine ve başarıya ilerler. Simüle edilmiş olaylar ve kısaltılmış bir bekleme kullanır. **Kendi uygulamanızdaki geri sayımı izleyin.**

![Cihaz kontrolünden READY durumuna ve sonuca ilerleyen tek bir simüle edilmiş başarılı deneme](docs/images/connect.gif)

</details>

### 4. Bit hızı hedefini, ardından Portal’ı kontrol edin

Yeşil **Bitrate target confirmed** yazısı ve **`[OK]`**, PS5’in daha yüksek bir hedef bildirdiğini gösterir. **Oynamadan önce Portal’daki görüntüyü, sesi ve kontrolleri kontrol edin.** Araç oynatmayı veya cihazların adres eşlemelerini doğrulayamaz. Ekran siyah kalırsa Better Portal kullanmadan normal şekilde bağlantıyı kesip yeniden bağlanın, ardından sorunu bildirin. Geri yükleme bitene kadar bilgisayarı uyanık tutun. Çıkmak için **Q** tuşuna basın; başlatıcı `Press Enter to close` dediğinde Enter / Return tuşuna basıp pencereyi kapatın.

Görseller ve animasyonlar, bu sonucu **Ready to play** olarak adlandıran önceki bir sürümü gösterir. O mesaj da yalnızca hedefi doğruluyordu.

![Başarılı sonuç: Ready to play yazısı ve Portal ile PS5 arasında yeşil OK bağlantısı](docs/images/result-success.png)

**63.106 Mbps** gibi bir değer, PS5’in bildirdiği hedeftir; **gerçek video aktarım hızının ölçümü değildir**. Bilgisayarın artık bu oturumun verilerini aktarması gerekmez.

**Portal bağlantısını bir sonraki kez kestiğinizde veya cihazı kapattığınızda:** Mac’te **Start.command**, Windows’ta **Start-Windows.cmd** dosyasını açıp dört adımı tekrarlayın. Kaydedilmiş adresler otomatik doldurulur; ağınız değiştiyse kontrol edin.

## Farklı bir sonuç görürseniz

Bunlar **farklı olası sonuçlardır**; başarılı bir oturumdan sonra sırayla beklemeniz gereken aşamalar değildir.

| Sihirbazdaki mesaj | Sonraki adımınız |
| --- | --- |
| **No new connection detected** / **No compatible startup captured** | Portal’ın PS5 bağlantısını kesin. Yeniden denemek için **Return** tuşuna basın. Portal’dan yalnızca bir sonraki READY isteminden sonra bağlanın. |
| **Higher target not confirmed** / **Target reported; verification incomplete** | Ayrıntılar için **D** tuşuna basın. Ağ geri yüklendikten sonra normal şekilde bağlanın veya 65 Mbps ile yeniden deneyin. |
| **Attempt stopped** | Geri yükleme durumunu okuyun. Tamamlandıysa Return ile yeniden deneyin veya Q ile çıkın. |
| **Network recovery needs attention** | Bilgisayarı uyanık tutun. Kurtarma ayrıntıları için **D** tuşuna basın ve yeni bir denemeden önce kurtarmanın bitmesini bekleyin. |

<details>
<summary>Yeniden deneme ve kurtarma örneklerini ayrı ayrı görün</summary>

**Yeni bağlantı yok:** yeni bir deneme başlatıp READY isteminden sonra Portal’dan yeni bir bağlantı kurun.

![Yeni bir Portal bağlantısının algılanmadığı tamamlanmış deneme örneği](docs/images/result-timeout.png)

**Kurtarma ilgi gerektiriyor:** bilgisayarı uyanık tutun ve D: ayrıntılar bölümündeki adımları izleyin.

![Kurtarma adımlarıyla birlikte tamamlanmamış ağ geri yükleme örneği](docs/images/result-recovery.png)

[Sonuç animasyonu](docs/images/result-terminal-art.gif), karşılaştırmak için farklı simüle edilmiş sonuçları gösterir; başarılı bir oturum bu sonuçların hepsinden geçmez.

</details>

## Dil ayarları

**S** tuşuna basın, **ok tuşlarıyla** bir dil seçin ve geri dönmek için **Enter**, **Esc** veya **S** tuşuna basın. Değişiklikler hemen uygulanır ve kaydedilir; Esc, değişikliği geri almadan paneli kapatır. Girdileriniz ve bulunduğunuz adım korunur.

Bağlantı sırasında Ayarlar açık olsa da geri sayım devam eder. **Q** denemeyi durdurmaya devam eder. Ağ geri yükleme başladığında panel kapanır.

<details>
<summary>Anlık dil değişimini ve diğer dört çeviriyi görün</summary>

![Ayarlar’da altı dil arasında anında geçiş yapıp aynı forma dönme](docs/images/settings.gif)

![Aynı cihaz ekranının Japonca, Korece, İspanyolca ve Fransızca sürümleri](docs/images/languages.gif)

</details>

<a id="troubleshooting-and-recovery"></a>

<a id="questions-and-fixes"></a>

## Sorular ve çözümler

**Windows kurulumu, izinler, Npcap veya bağdaştırıcı seçimiyle ilgili sorun mu var?**

[Windows sorun giderme kılavuzunu (İngilizce)](WINDOWS.md#questions-and-fixes) kullanın. Aşağıdaki `.command` dosyaları ve Mac arayüzü adımları macOS içindir.

<a id="macos-blocked"></a>

**macOS dosyayı açmıyor: geliştirici doğrulanamıyor veya Apple dosyayı kontrol edemiyor.**

Bu depodan indirdiğiniz dosyayı açmayı denedikten sonra **Apple menüsü → Sistem Ayarları → Gizlilik ve Güvenlik** yolunu izleyin. Engellenen dosya bildirimini bulun. İndirmeye güveniyorsanız **Yine de Aç** seçeneğini ve ardından **Aç** seçeneğini onaylayın. [Apple’ın görselli adımları](https://support.apple.com/en-us/102445) istemleri açıklar. “Bilgisayarınıza zarar verecek” uyarısı farklı bir durumdur; durun ve Apple’ın bu uyarıyla ilgili adımlarını izleyin.

**Setup, Setup complete yerine Python veya sertifika hatası gösteriyor.**

**Install Certificates.command** dâhil [macOS Python adımlarını](#macos-quick-start) tamamlayın. Başarısız kurulum penceresini kapatıp **Setup.command** dosyasını yeniden açın. Sorun devam ederse yardım isterken hata metnini paylaşın.

**Parola kabul edilmiyor veya hesabın sudo kullanamayacağı söyleniyor.**

Mac oturum açma parolanızı kullanın. Mac hesabınız yönetici değilse bilgisayarı yöneten kişiden başlatmaya izin vermek için yardım isteyin.

**Metin kesiliyor veya uygulama daha büyük bir pencere istiyor.**

Terminal penceresinin bir köşesini sürükleyerek büyütün. Uygulama en az 72 sütun ve 24 satırlık alan ister. Yeterli alan olduğunda devam eder.

**Bir cihaz yanıt vermedi veya görüntü takılıyor.**

PS5 ve Portal’ı uyanık tutun. Güncel adresleri ve ev Wi-Fi bağlantısını yeniden kontrol edin. Takılma için 65 Mbps deneyin veya Portal’ın bağlantısını kesip Better Portal olmadan normal şekilde yeniden bağlanın.

**Yönetici parolamı kaydeder mi?**

Hayır. İzni macOS veya Windows yönetir. Aynı açık sihirbazda yeniden denemek parolayı tekrar istemez.

**Nasıl yardım alabilirim?**

Görünen adım ve mesaj, bilgisayarınızın işletim sistemi ve Portal sürümleri, ayrıca seçtiğiniz bit hızıyla birlikte [bir Issue açın](https://github.com/wchwawa/better-portal/issues). Paylaşmadan önce ekran görüntülerindeki cihaz adreslerini gizleyin. Ham raporlar ve paket kayıtları özel ağ bilgileri içerebilir; bunları yerel olarak saklayın.

<a id="terminal-help"></a>

<details>
<summary>macOS Terminal yardımı: klasörü açma, önizleme ve bulunamayan Python dosyası</summary>

Terminal’i elle açmak için **Command (⌘) + Boşluk** tuşlarına basın, **Terminal** yazın ve Return tuşuna basın.

1. `cd` yazıp ardından **bir boşluk** bırakın.
2. Finder’daki **better-portal-main klasörünü** Terminal penceresine sürükleyip Return tuşuna basın. Böylece Terminal’e hangi klasörü kullanacağını söylersiniz.
3. Aşağıdan **bir seferde tek komut** kopyalayın, Terminal’e yapıştırın ve Return tuşuna basın. Yalnızca komut metnini kopyalayın.

Start, `.venv/bin/python` dosyasını bulamıyorsa önce bu klasörde kurulumu çalıştırın:

```sh
./Setup.command
```

Ardından gerçek bir oturum başlatın:

```sh
./Start.command
```

Kurulumdan sonra **yalnızca önizleme** için:

```sh
.venv/bin/python portal_tui.py --demo
```

**Animasyonsuz önizleme** için:

```sh
.venv/bin/python portal_tui.py --demo --no-animations
```

İki önizleme komutu da cihazlarınız olmadan bağlantıyı simüle eder. Yönetici parolası gerektirmez, ağı değiştirmez ve ayar kaydetmez. Gerçek bir oturum için Start.command dosyasını açmadan önce önizlemeyi kapatın.

</details>

<a id="mac-adapter"></a>

<details>
<summary>Mac LAN interface alanı boş veya USB / Ethernet bağdaştırıcısı kullanıyorum</summary>

Arayüz, Wi-Fi adınız veya IP adresiniz değil, `en0` gibi bir addır. Kontrol etmek için yukarıdaki adımlarla Terminal’i açıp şu komutu çalıştırın:

```sh
networksetup -listallhardwareports
```

Wi-Fi için **Hardware Port: Wi-Fi** bölümünü bulun ve **Device:** yanındaki adı kullanın. Kablolu bağlantı için bağlı Ethernet bağdaştırıcısının bölümünü kullanın. Bu Device adını Better Portal’a girin. Hangi bağdaştırıcının kullanıldığını belirleyemiyorsanız yardım isterken bu soruyu da ekleyin.

</details>

<details>
<summary>Mac’te Git ve Terminal kullanıyor musunuz?</summary>

```sh
git clone https://github.com/wchwawa/better-portal.git
cd better-portal
./Setup.command
./Start.command
```

</details>

**Linux kullanıyor musunuz?** Orijinal projenin [Linux / otomatik kurulum kılavuzuna](https://github.com/atameric/ps5-portal-high-bitrate/blob/main/AUTOMATION.md) bakın.
