# Windows / Linux otomasyon önizlemesi

Mac mini'deki ilk sürekli çalışan sürüm gerçek PS5/Portal ile kullanıcı tarafından doğrulandı. Bu pakette aynı tek yönlü yaklaşım ortak bir motora taşındı. **Windows otomasyonu fiziksel doğrulama bekliyor. Linux/Pi için kullanıcıdan kurulum, yeniden başlatma ve yeni bağlantı başarı bildirimi geldi; çökme sonrası kurtarma ve geniş uyumluluk henüz doğrulanmadı.** Deneysel test sürümüdür. Ortak motorun macOS servis kurucusu bu pakette yok; mevcut macOS elle başlatıcı kullanılabilir.

Bilgisayar açık, uyanık ve PS5/Portal ile aynı doğrudan yerel ağda kalmalı. Bilgisayarı mümkünse Ethernet ile bağla. Router'da cihazların IP adreslerini sabitle. USB gerekmiyor. Yalnız Portal'dan PS5'e giden kontrol trafiği bilgisayardan geçer; görüntü PS5'ten Portal'a doğrudan gider. Kontrol yoluna ek bir adım eklenir; gecikme ölçülmedi. 4K, upscale veya sürekli 200 Mbps garantisi yok.

## Windows

1. Yeni sürüm ZIP'ini indir, ayrı ve güvendiğin bir klasöre çıkar.
2. [python.org](https://www.python.org/downloads/windows/) üzerinden 64-bit Python 3.10+ kur. Otomatik servis için tam kurucuda **tüm kullanıcılar için**, `C:\Program Files` altına kurulum seç; Python launcher da kurulsun. Store veya kullanıcı klasörüne kurulmuş Python, SYSTEM görevi için uygun değil.
3. [Npcap](https://npcap.com/#download) kur; WinPcap API uyumluluğunu seç. Wi-Fi monitor mode kullanma. Kurucu isterse yeniden başlat.
4. `Setup-Windows.cmd` çalıştır. Bağımlılıkları kurar ve çevrimdışı testleri çalıştırır. `py -3` yanlış Python'u seçiyorsa `.venv` klasörünü tüm kullanıcılara kurulu Python'un tam yoluyla yeniden oluştur.
5. Portal açık ve Wi-Fi'ye bağlı olsun. `Auto-Windows.cmd` dosyasına sağ tıkla, **Yönetici olarak çalıştır**. `Configure`, ilk deneme için `65`, yerel ağ adaptörünün **listedeki numarasını** seç, sonra cihazların IPv4 adreslerini gir. Adaptörün yanında gösterilen PC IP'si sadece bilgi içindir. Eski preview.1 sürümündeki interface name/GUID alanı adaptör adı veya tam Npcap cihaz kimliğini ister; PC IP'sini yazma. MAC adresleri yerel olarak kaydedilir.
6. Portal oyun bağlantısını kes. Aynı yönetici menüsünden `Baseline` seç. **BASELINE READY** görünce Portal'dan bağlan, 60 saniye görüntü ve kontrolü dene. Bu tur bitrate değiştirmez. Trafik aktarılıp geri yükleme tamamlanınca yerel test kaydı yazılır; görüntüyü otomatik doğrulamaz.
7. Sorunsuzsa `Run` seç. **AUTO READY** sonrasında yeni Portal bağlantısı kur. Göstergeyi ve hareketli oyunu kontrol et. Ctrl+C ile durdur, geri yüklemenin bitmesini bekle. Bu deneme çalışmıyorsa servis kurma.
8. Çalışıyorsa `Install` seç ve baseline gözlemini onayla. Kod/ayarlar `C:\ProgramData\PortalBitrateAuto` altına kopyalanır; sadece Administrators/SYSTEM yazabilir. `PortalBitrateAutoPreview` görevi Windows açılışında SYSTEM olarak çalışır. Kullanıcı parolası/token saklanmaz.
9. `Status` ile görevi ve zaman damgalı raporu kontrol et. Portal'ı yeniden bağlayarak, sonra PC'yi yeniden başlatarak otomatik açılışı ayrıca test et.

Menüde `Start`, `Stop`, `Status`, `Uninstall` bulunur. Stop kalıcı durdurma işareti yazar; PC yeniden açılınca da Start diyene kadar çalışmaz. Uninstall görevi kaldırır, yerel özel dosyaları saklar. Kurtarma sürecini zorla kapatma. Görevin kaydedilmiş olması çalıştığını kanıtlamaz. SYSTEM/Npcap veya bağımsız kurtarıcı başlatma hatasını kontrolleri silerek aşmaya çalışma; hata metnini kişisel bilgileri temizleyerek bildir.

## Linux

İlk hedef: fiziksel Debian/Ubuntu benzeri sistem, Ethernet, Python 3.10+, iproute2, libpcap, systemd. Raspberry Pi OS kullanan Pi 3B için aşağıdaki kullanıcı başarı bildirimi var; işletim sistemi mimarisi/sürümü belirtilmediği için ARM64 uyumluluğu kanıtlanmış değil. WSL, NAT kullanan Docker/VM ağı veya modem firmware'i desteklenen kurulum hedefi değil. Ayrı deneysel Proxmox LXC / Linux Docker macvlan seçeneği aşağıda anlatılıyor.

```sh
sudo apt update
sudo apt install python3 python3-venv python3-pip iproute2 libpcap0.8
# İndirdiğin klasörde:
sh Auto-Linux.sh setup
sh Auto-Linux.sh configure 65
```

Adaptörü `ip -br link` / `ip -br addr` ile bul. Örneğin `eth0` veya `enp3s0`; kendi adaptörünü kullan. Kayıt sırasında her iki cihaza da yerel ağdan erişilebilmeli.

1. Portal oyun bağlantısını kes. `sh Auto-Linux.sh baseline` çalıştır. **BASELINE READY** sonrasında bağlanıp 60 saniye görüntü/kontrol testi yap.
2. Çalışıyorsa `sh Auto-Linux.sh run` ile aktif dene. **AUTO READY** sonrası yeni bağlantı kur, göstergeyi kontrol et. Ctrl+C ile durdur.
3. İki deneme de başarılıysa `sh Auto-Linux.sh install` çalıştır ve gözlemini onayla. Kod `/opt/portal-bitrate-auto`, özel kayıtlar `/var/lib/portal-bitrate-auto` altına root yetkili olarak kurulur. systemd servis adı `portal-bitrate-auto`.
4. `sh Auto-Linux.sh status` ile kontrol et. Yeni Portal bağlantısı ve Linux yeniden başlatma testlerini yap.

```sh
sh Auto-Linux.sh stop
sh Auto-Linux.sh start
sh Auto-Linux.sh status
sh Auto-Linux.sh uninstall
```

Stop yeniden başlatmadan sonra da geçerli. Uninstall servisi kaldırır, özel dosyaları bırakır. Güncelleme/profil değişikliği için önce stop/uninstall, özel dosyaları yedekleyip eski kurulum klasörlerini kaldırma, yeni configure/baseline/install gerekir. Kurucu mevcut kurulumu bilerek ezmez.

## Linux kullanıcı test raporu (30 Eylül 2026)

[Tissee'nin raporu](https://www.reddit.com/r/PlaystationPortal/comments/1wtyglf/comment/pd2k5ls/): EndeavourOS dizüstü bilgisayar ve Ethernet bağlantılı Raspberry Pi OS / Pi 3B üzerinde başarı. Pi yeniden başlatılınca systemd servisi açılıyor, Portal yeni bağlantı kurabiliyor ve PS5 dinlenme modundan açıldığında da 100 Mbps profili çalışıyor. Tam dağıtım sürümü, mimari, sürekli gerçek video hızı ve giriş gecikmesi verilmedi. Bu kullanıcı bildirimi; bakımcı tarafından yapılmış benchmark veya genel uyumluluk garantisi değil. Çökme kurtarması ve uzun süreli kullanım hâlâ test bekliyor.

Kullanıcı, Docker'ın açtığı/yeniden uyguladığı IPv4 forwarding ayarını çözmek zorunda kaldı. Röle forwarding açıkken başlamayı reddeder ve bu ayarı değiştirmez. [Docker belgelerine](https://docs.docker.com/engine/network/packet-filtering-firewalls/#docker-on-a-router) göre olağan iptables arka ucunda açılışta forwarding etkinleştirilebilir; bridge ağı forwarding gerektirir. Ortak Docker makinesinde bunu kapatmak container ağını bozabilir. Gereksinimler çakışıyorsa ayrı bir röle makinesi kullan; ayarı körlemesine kapatma veya kontrolü kaldırma. Bu rapor fiziksel Linux kurulumu içindir, Docker içinde röle çalıştırma doğrulaması değildir.

## Proxmox LXC / Docker deneysel kurulum

[SDNick484'in PR #1 katkısı](https://github.com/atameric/ps5-portal-high-bitrate/pull/1), mevcut röleyi Proxmox üzerinde küçük bir Alpine LXC container'ına veya Linux Docker üzerinde macvlan ağına kurar. Container, PS5/Portal ile aynı yerel ağda kendi MAC adresini kullanır. Kablolu host gerekir; Docker Desktop, WSL ve Wi-Fi macvlan kurulumu desteklenmez. Bitrate motoru değişmez.

[İngilizce adım adım kurulum](deploy/README.md): Proxmox'ta kurucudan sonra container içinde `portal configure 65`, `portal baseline`, `portal try`, başarılıysa `portal enable` sırası izlenir. OpenRC servisi yeniden başlatmada açılabilir. Profil değiştirmek için servisi durdur, yeniden configure ve baseline yap, sonra başlat. Docker'da aynı adımlar Compose üzerinden uygulanır. Kurucuyu veya `portal` yardımcısını ortak fiziksel host üzerinde çalıştırma.

**Firewall kapsamı:** Proxmox kurucusu yeni röle container'ının `net0` kartında `firewall=0` kullanır. Bu, o karttaki Proxmox filtrelemesini kapatır; host'un genel firewall'unu, router'ı veya diğer container'ları kapatmaz. Container bağlı olduğu LAN'a bu filtre olmadan açılır. Güvenilir LAN ve yalnız röleye ayrılmış container kullan; başka servis kurma veya Internet'e açma. Mevcut container'ın firewall ayarı otomatik değiştirilmez. Container içindeki IPv4 forwarding kapatılır; host'un ayarı korunur.

Proxmox için katkı sahibinin gerçek PS5/Portal başarı bildirimi var. Docker için kendi fork'unda sahte ağ uçlarıyla başarılı testler var; gerçek cihaz doğrulaması yok. Biz yeni Linux/Proxmox/Docker donanım testi yapmadık. Tam dağıtım sürümleri, gerçek cihazda yeniden başlatma/çökme kurtarması, uzun süreli kararlılık ve Alpine dışındaki Gentoo/OpenRC kullanımı hâlâ test bekliyor. Deneysel destek olarak değerlendir.

## Arıza ve gizlilik

Bağımsız kurtarıcı, program kapanınca veya takılınca Portal'ın ARP kaydını geri yüklemeye çalışır. Elektrik kesilmesi, ağ kablosunun çıkması, bilgisayarın uyuması veya iki sürecin birden öldürülmesi bunu engelleyebilir. Böyle bir durumda Portal bağlantısını yeniden kur. Başarısız kurtarma sonraki açılışı bloke eder. Kurtarma ve kilit kaldırma adımları [İngilizce kılavuzda](AUTOMATION.md); çalışan sürecin kilidini silme.

`unique_modified_startups` sadece yerelde değiştirilip gönderilen başlangıç paketini sayar; PS5'in kabulünü veya gerçek bitrate'i kanıtlamaz. Portal göstergesi ve oynanabilir oturumla doğrula.

Fiziksel Windows/systemd servisi IP forwarding açmaz, firewall veya firmware değiştirmez; mevcut forwarding açıkken işlem reddedilir. Ayrı container kurulumunun forwarding ve kart filtreleme davranışı yukarıda anlatılmıştır. Router IP rezervasyonları önemli.

Test raporuna işletim sistemi, adaptör, Windows'ta Npcap sürümü, profil, baseline/aktif/yeniden bağlanma/yeniden başlatma sonucu, gösterge aralığı ve takılma bilgisini yaz. **Gerçek IP/MAC içeren ayarları, runtime klasörlerini, pcap dosyalarını, `.env`, API anahtarı veya token paylaşma.** Ayrıntılar: [TESTING.md](TESTING.md).
