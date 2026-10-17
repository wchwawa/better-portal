# Windows 设置向导

[English](WINDOWS.md) · [返回 Better Portal](README.zh-CN.md)

Windows 与 Mac 使用**同一个 TUI 向导**：选择语言、检查前提、填写地址、选择码率、等待“现在连接”、查看结果。Windows 的网络功能使用 Npcap，管理员权限由 Windows 系统弹窗授权。

当前是 **Windows 预览版**。自动测试验证原生 Windows 终端与连接逻辑；Windows 上的真实 PS5 / Portal 播放仍需实机测试。目标码率确认不等于已验证画面、声音、输入延迟或持续视频吞吐量。

## 首次安装

准备 x64 Windows 11 或 Windows 10 电脑、PS5 和 PlayStation Portal。普通 Remote Play 应已能正常使用。三台设备接入同一个家庭路由器，PS5 可以用网线。Portal 保持开机并连接 Wi-Fi，但断开当前 PS5 会话；电脑保持唤醒。此快速启动暂不支持原生 ARM64 电脑。

1. 下载 [Better Portal ZIP](https://github.com/wchwawa/better-portal/archive/refs/heads/main.zip)。在文件资源管理器右键 ZIP → **全部解压缩**，打开解压后的文件夹。保留完整目录，不要在 ZIP 内直接运行，也不要复制 Mac 的 `.venv` 文件夹。
2. 双击 **Start-Windows.cmd**。已有 x64 Python 3.10–3.14 时会直接使用，否则通过 Windows 包管理器安装 Python 3.14。如果包管理器不可用，会打开 [Python 官网](https://www.python.org/downloads/windows/)：选择 Python 3.14 的 **Windows installer (64-bit)** 完成安装，再回到启动窗口按 Enter。程序依赖会自动安装。
3. 如果尚未安装 Npcap，会打开 [Npcap 官网](https://npcap.com/#download)。下载并运行安装程序，允许 Windows 的权限请求。**不要勾选 WinPcap 兼容模式**，也不需要 Wi-Fi 监听模式或 raw 802.11 支持。“仅管理员访问”可以保留。安装结束后，回到启动窗口按 **Enter** 继续。如果安装程序要求重启，请重启电脑后重新打开 Start-Windows.cmd。
4. 依赖准备完成后，TUI 向导会自动打开。允许 Windows 的权限请求，再按下方步骤操作。无需单独运行 Setup。

不需要安装 Git 或 Wireshark。首次安装需要联网，已安装的依赖会复用。Npcap 从官方网站安装，不随本项目打包；其免费版需要[通过安装窗口操作](https://npcap.com/guide/npcap-users-guide.html)。**Setup-Windows.cmd** 仍可使用，用于只准备依赖、不打开向导。

## 以后每次使用

**双击 Start-Windows.cmd，然后允许 Windows 的用户账户控制（UAC）请求。**如果账户需要管理员凭据，由 Windows 提示输入。Better Portal 不收集或保存密码；在同一个向导窗口内重试，无需再次授权。

首次打开会让你选择英语、简体中文、日语、韩语、西班牙语或法语。选择会保存，以后按 **S** 可随时切换语言。

1. **准备：**Portal 断开与 PS5 的连接，确认三台设备在同一个家庭局域网内。
2. **设备：**输入路由器设备列表里的 PS5 和 Portal **IPv4 地址**。首次使用时，**PC 局域网网卡**会建议 Windows 用于直接访问这两个设备的连接。核对该选项，或用 **← / →** 选择连接家庭网络的 Wi-Fi 或以太网网卡；已保存或手动选择的网卡会保留。若无法建议网卡，请自行选择并核对两个地址。首次保留 **65 Mbps**，再选择“保存并准备连接”。Tab 或 ↑ / ↓ 切换行，Enter 继续。
3. **连接：**“等待 / WAIT”时保持 Portal 断开。看到 **现在连接 / CONNECT NOW** 后，再在 Portal 上正常连接 PS5。此时才开始 **120 秒倒计时**；临近结束才收到连接请求，也会留出独立的确认时间。终端图案会跟随请求、PS5 接受和目标码率报告变化。
4. **结果：**“目标码率已确认”表示程序观察到高目标、验证了本机发包，并完成恢复步骤。**仍需在 Portal 检查画面、声音和操作。**若黑屏，请断开后正常重连，不运行 Better Portal。**D** 查看报告或恢复详情，允许重试时按 **Enter**，按 **Q** 退出。

[图文 README](README.zh-CN.md)展示同一个向导；图片来自 Mac 的演示模式。Windows 使用上面说明的 PC 网卡选择和 Windows 启动器。

地址保存到 `config.windows.json`，语言和码率保存到 `tui-settings.json`，与 Mac 的 `config.json` 分开。Portal 断开或关机后，本次会话结束；下次重新打开 **Start-Windows.cmd**。

想放到桌面：右键 **Start-Windows.cmd** → **显示更多选项** → **发送到 → 桌面快捷方式**。保留原项目文件夹，不要只把启动文件移走。

## 常见问题

**需要我的 PlayStation 账号密码吗？**

不需要。Better Portal 不要求 PSN 用户名或密码，只需两个设备的局域网地址及电脑网卡。Windows 的管理员权限请求与 PSN 账号无关。

**Python 安装失败。**

查看启动窗口中的错误，检查网络，再次打开 **Start-Windows.cmd** 重试。也可以从上方官网手动安装 x64 Python 3.14。启动器会直接查找已安装的解释器，无需修改 PATH 或自行运行 `py`。

**提示缺少 curses，或启动时关闭了。**

重新打开 **Start-Windows.cmd**。它会检查依赖版本和模块能否加载，缺失或损坏时会重新安装。启动错误会保留在窗口中，直到你按 Enter。确保解压目录可写，并关闭其他安装窗口。实际连接不能通过 WSL 或 Notebook 运行。

**找不到网卡，或提示缺少 Npcap。**

安装 Npcap 后关闭向导，重新打开 **Start-Windows.cmd**。确保 Wi-Fi 或以太网网卡已连接，不要选 VPN 或回环网卡。若取消了权限弹窗，重新启动并允许授权。

**填写设备后直接显示“连接前检查失败 / Setup check failed”或“未能完成设置 / Could not finish”。**

先看标题下方的错误。按 **D**，再用 **↑ / ↓** 滚动查看完整错误；Enter 或 Esc 返回。“连接前检查失败”表示程序在修改网络映射前就被检查拦下。若错误指出另一张网卡，请重试并在 **PC 局域网网卡**中选择它。其他错误可按下面的说明排查，或提供隐去私人地址后的完整报错。仅凭标题无法判断原因。

**设备无法访问，或路由／转发检查失败。**

保持 Portal 唤醒，核对当前 IPv4 地址，选择同一家庭局域网的网卡。避免访客 Wi-Fi、设备隔离、VPN 路由或该网卡的 Internet 连接共享。程序只检查路由和转发状态，不修改防火墙、注册表或系统转发配置。无需通过关闭防火墙解决报错。

**没检测到新连接，或倒计时结束。**

断开 Portal 与 PS5 的连接，在向导里重试，等下一次“现在连接”后再连接。保存的设置会继续使用。连接阶段按 Q、Esc 或 Ctrl+C 会停止尝试，先恢复网络，再显示结果。

**“网络恢复需要处理”。**

保持电脑唤醒，按 **D** 查看报告位置和自动恢复期限。独立恢复进程运行期间会持有整台电脑共用的锁，阻止另一场尝试覆盖恢复；结果页也会禁用直接重试。

期限过后仍有问题时，确认尝试及恢复进程已经停止，再在**以管理员身份打开的 PowerShell** 中执行 D 页面给出的恢复命令。只使用本工具生成的状态文件，不要删锁强行重试。也可重新连接设备的网络以刷新映射。电脑关机后无法自动恢复。

## 可选的排错命令

普通用户直接使用向导，**无需分别运行 Configure、Check 或 Baseline 启动器**。旧的命令行探测仍保留，修改码率前要求同一配置已有成功的基线记录。

在项目文件夹中的管理员终端运行：

```bat
.venv\Scripts\python.exe portal_windows.py --check
.venv\Scripts\python.exe portal_windows.py --baseline
.venv\Scripts\python.exe portal_windows.py --profile 65
```

每次都需要 READY 后重新建立 Portal 连接。旧命令行保留 35 秒连接窗口，TUI 为 120 秒。

只预览界面，无需管理员权限、Npcap 或设备：

```bat
.venv\Scripts\python.exe portal_tui.py --demo
```

加 `--no-animations` 可关闭动画。演示模式不会保存设置或修改网络。常驻自动服务请看 [AUTOMATION.md](AUTOMATION.md)，不要与手动向导同时运行。

## 反馈 Windows 11 实测

通过 [Windows 测试反馈模板](https://github.com/wchwawa/better-portal/issues/new?template=windows-test.md)提供程序版本、Windows 版本、Python / Npcap 版本、网卡、Portal 固件、最后显示的阶段，以及恢复后画面、声音和操作是否正常。也请测试取消后再次尝试。

[验证说明](docs/windows-tui-validation.md)区分了自动测试与实机验收。不要上传完整配置、恢复文件或抓包；只分享隐去私人信息的报告字段。报告中的目标码率不是实测吞吐量。
