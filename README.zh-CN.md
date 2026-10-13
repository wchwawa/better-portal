# Better Portal

[English](README.md) · **简体中文**

在 Mac 上通过终端向导，为 PlayStation Portal 连接 PS5 时选择更高的目标码率。

> **基于 [atameric/ps5-portal-high-bitrate](https://github.com/atameric/ps5-portal-high-bitrate)。** 感谢 [@atameric](https://github.com/atameric) 提出原始思路并完成实现。Better Portal 在此基础上提供引导式终端界面，保留原始 MIT 许可证和贡献历史。

选好语言，填入设备地址和码率，等到**“现在连接”**出现后连接 Portal。向导会记住设置，并用两分钟倒计时、连接动画和结果提示带你完成每次操作。

## 开始前需要什么

- 一台 PS5 和一台 PlayStation Portal，已经能够正常连接和游玩。
- Mac、PS5、Portal 位于**同一家庭局域网**。PS5 可以接网线，Portal 使用 Wi-Fi；避开访客 Wi-Fi、VPN 和开启设备隔离的网络。
- Mac 上安装 **Python 3.10 或更新版本**。可以运行 `python3 --version` 检查，或从 [Python 官方 macOS 下载页](https://www.python.org/downloads/macos/)安装。
- Mac 登录密码。设置连接时需要管理员权限。

这是一个实验性社区工具，效果取决于设备、系统版本和网络。建议从 **65 Mbps** 开始；目标码率更高，并不保证画面更流畅或延迟更低。

## 安装与打开

1. [下载 Better Portal](https://github.com/wchwawa/better-portal/archive/refs/heads/main.zip)，解压到本地文件夹。
2. 双击文件夹中的 **Setup.command**，完成依赖安装后按 Enter。
3. 每次需要设置新的 Portal 连接时，双击 **Start.command**。

如果出现密码提示，输入 Mac 登录密码并按 Enter。输入密码时，终端不会显示字符。

也可以通过终端安装，首次运行：

```sh
git clone https://github.com/wchwawa/better-portal.git
cd better-portal
./Setup.command
```

之后在项目文件夹中运行：

```sh
./Start.command
```

终端窗口至少需要 **72 列、24 行**。如果出现窗口过小提示，放大窗口即可继续。

## 第一次使用

下方图片来自实际程序的演示模式，使用示例地址，等待过程经过缩短。

### 先选择语言

首次打开时，用方向键选择 **简体中文** 或 **English**，按 **Enter** 确认。选择会立即保存，下次直接使用上次的语言。

以后想切换语言，在**准备页按 L** 即可。按 Esc 放弃切换，设备地址和码率设置不受影响。演示模式中的语言选择不会保存。

![首次启动时选择 English 或简体中文](docs/images/language.png)

### 1. 准备设备

在 Portal 上打开**快捷菜单 → 断开连接**，先断开与 PS5 的连接。保持 PS5 开机，Portal 唤醒，Mac 在整个设置和网络恢复过程中保持唤醒。

黄色文字标出了需要确认的事项。确认后按 **Enter** 继续。

![准备页用黄色突出同一网络、断开 Portal 和保持 Mac 唤醒](docs/images/prepare-zh-CN.png)

### 2. 填写地址，选择码率

在路由器的已连接设备列表中找到 PS5 和 Portal 的 **IPv4 地址**，分别填入高亮输入框。**Mac 局域网网卡**会自动建议一个值；如果使用其他网卡连接家庭网络，请修改为对应名称。

用 **Tab** 或 **↑ / ↓** 切换输入项，直接输入可以替换已选内容。移动到码率选项后，用 **← / →** 或**空格**选择：

| 码率 | 适合什么时候使用 |
| --- | --- |
| **65 Mbps，推荐** | 首次使用从这里开始。流动的彩虹文字标记推荐选项。 |
| **100 Mbps** | 65 Mbps 稳定后再尝试，比较同一游戏场景的表现。 |
| **200 Mbps，实验选项** | 可能增加卡顿，也不一定能达到目标值。 |

方向键提示位于选项右侧。按 Enter 移动到**保存并准备连接**，再按 Enter 开始。地址和码率会保存，供下次使用。

![设备页的高亮输入框、65 Mbps 流动彩虹推荐文字和右侧方向键提示](docs/images/devices-zh-CN.gif)

### 3. 看到“现在连接”后再连接

显示**请稍候**时，让 Portal 保持断开。终端中的 Portal 与 PS5 图案会随设备检查、连接准备的实际阶段变化。

出现**已就绪 / 现在连接**后，在 Portal 上选择 PS5，开始远程游玩。你有 **120 秒**进行连接，界面从 **02:00** 开始倒计时。

收到连接请求、PS5 接受连接、确认目标码率时，图案之间的连线会依次变化。连上后保持 Portal 连接，等待向导完成设置并恢复直接连接。

![连接页从设备检查、两分钟倒计时，到 PS5 接受连接和码率验证的动画](docs/images/connect-zh-CN.gif)

需要中止时，按 **Q、Esc 或 Ctrl+C**，等待结果出现。网络恢复期间请保持 Mac 唤醒。

### 4. 查看结果，开始游玩

**可以开始游玩**表示高码率目标已确认、本机验证通过，直接连接已恢复。保持当前 Portal 连接，按 **Q** 或 **Esc** 退出向导即可。

![结果页分别显示成功、需要重试、主动取消和网络恢复警告](docs/images/result-zh-CN.gif)

| 结果 | 接下来怎么做 |
| --- | --- |
| **可以开始游玩**，绿色 `[OK]` | 继续游玩，Mac 已退出本次连接的中转。 |
| **未检测到新连接 / 未捕获到兼容的连接请求** | 先断开 Portal，再重试；等到“现在连接”出现后再连接。 |
| **未确认高码率目标 / 已报告高码率，但验证未完成**，黄色 `[?]` | 按 **D** 查看详情。可以正常重连，或用 65 Mbps 重试。 |
| **本次运行已停止**，`[X]` | 已取消本次运行，确认网络恢复状态后重试或退出。 |
| **网络恢复需要处理**，红色 `[!]` | 保持 Mac 唤醒，等待自动恢复。按 **D** 查看恢复详情，恢复完成后再重试。 |

界面中的 **63.106 Mbps** 等数值是 PS5 报告的目标码率，**并非实测视频码率**。结果图案描述本次运行的结果，不会在退出后持续监测连接。

## 常见问题

**关闭 Portal 或断开重连后，还需要重新运行吗？**

需要。每次新建远程游玩连接，都需要重新运行。打开 **Start.command**，确认已保存的设置，等到“现在连接”后再连接。

**玩游戏时，Mac 必须一直开着吗？**

显示“可以开始游玩”后，Mac 已退出中转，可以关闭向导。设置、取消和网络恢复期间，请保持 Mac 唤醒，直到恢复完成。

**会保存我的 Mac 密码吗？**

不会。是否需要再次授权由 macOS 控制。在同一个已打开的向导中重试，不会重复询问密码。

**怎样恢复默认连接？**

断开 Portal，直接正常重连，不运行 Better Portal 即可。工具不修改设备固件。

**提示设备没有响应，怎么办？**

唤醒 PS5 和 Portal，确认当前 IP 地址，以及三台设备是否处于同一家庭网络。如果提示 IP 冲突，先检查路由器设备列表，再重试。底层错误详情保留原文，便于排查。

**更高码率反而卡顿？**

先试 65 Mbps，或直接正常重连。更高码率不一定适合你的网络。

**提示找不到 `.venv/bin/python`，或启动文件无法打开？**

先在下载的项目文件夹中运行 **Setup.command**。也可以打开终端，输入 `cd `，把项目文件夹拖入终端，按 Enter，然后依次运行 `./Setup.command` 和 `./Start.command`。

**可以先看看界面，不连接设备吗？**

安装后，在项目文件夹中运行下面的命令。演示模式无需管理员权限，不修改网络，也不保存设置：

```sh
.venv/bin/python portal_tui.py --demo
```

如果想关闭动效，在启动命令后添加 `--no-animations`：

```sh
sudo .venv/bin/python portal_tui.py --no-animations
```

**支持 Windows 或 Linux 吗？**

此引导界面面向 **macOS**。原项目提供独立的 [Windows 指南](https://github.com/atameric/ps5-portal-high-bitrate/blob/main/WINDOWS.md)和 [Linux / 自动化指南](https://github.com/atameric/ps5-portal-high-bitrate/blob/main/AUTOMATION.md)。

**去哪里反馈问题？**

请[创建 Issue](https://github.com/wchwawa/better-portal/issues)，说明界面中的提示、macOS 和 Portal 系统版本，以及所选码率。分享截图前遮住设备地址，原始抓包请保留在本机。设置和运行报告均保存在你的 Mac 上。

## 致谢

原始码率调整思路来自 **[@atameric](https://github.com/atameric)** 和 [ps5-portal-high-bitrate](https://github.com/atameric/ps5-portal-high-bitrate)。感谢原项目的贡献者与测试者，也可以[支持原作者](https://buymeacoffee.com/atameric)。

Better Portal 的 Mac 引导体验由 [@wchwawa](https://github.com/wchwawa) 维护，使用 [MIT 许可证](LICENSE)。这是独立社区软件，与 Sony 或 PlayStation 无隶属关系。
