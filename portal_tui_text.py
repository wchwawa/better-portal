"""Wizard translations and terminal-cell layout, without runtime dependencies."""
import re
import textwrap
import unicodedata

LANGUAGES = ('en', 'zh-CN')

# English is the source language. Diagnostic text from the relay stays verbatim.
ZH_CN = {
    'Guided macOS launcher. Demo mode never changes configuration or networking.': 'macOS 设置向导。演示模式不会修改配置或网络。',
    'Preview the wizard with simulated events; no sudo or network changes': '以模拟事件预览界面，无需 sudo，不修改网络',
    'Keep state labels and highlights, without motion': '保留状态和高亮，关闭动效',
    'High Bitrate  /  Guided setup': '高码率 / 设置向导',
    '  /  DEMO: no network changes': ' / 演示：不修改网络',
    '1 Prepare': '1 准备',
    '2 Devices': '2 设备',
    '3 Connect': '3 连接',
    '4 Result': '4 结果',
    'Please enlarge this terminal to at least 72 x 24.': '请将终端放大至至少 72 列、24 行。',
    '{phase}: {seconds}s remaining': '{phase}：剩余 {seconds} 秒',
    'Q or Esc stops safely and restores the network.': '按 Q 或 Esc 安全停止并恢复网络。',
    'Esc exits. Setup resumes when the window is larger.': '按 Esc 退出，放大窗口后可继续。',
    'Enter: continue    L: language    Esc: quit': 'Enter 继续    L 语言 / Language    Esc 退出',
    'Before you begin': '开始之前',
    'SAME NETWORK': '同一局域网',
    '  /  Mac + PS5 + Portal': ' / Mac + PS5 + Portal',
    'Use the main LAN; avoid guest Wi-Fi and VPN routes.': '使用家庭主网络，避开访客 Wi-Fi 和 VPN。',
    'DISCONNECT PORTAL': '断开 Portal 连接',
    '  /  keep ': ' / 保持 ',
    'PS5 powered on': 'PS5 开机',
    'On Portal: ': '在 Portal 上：',
    'Quick Menu -> Disconnect': '快捷菜单 -> 断开连接',
    'Keep this ': '保持 ',
    'Mac awake': 'Mac 唤醒',
    ' until restoration finishes.': '，直到网络恢复完成。',
    'Wait for ': '看到 ',
    'CONNECT NOW': '现在连接',
    ' before connecting Portal.': ' 提示后，再连接 Portal。',
    'I have checked these steps  ->': '已确认，继续 ->',
    'Tab: next field    Enter: next / start    Esc: back': 'Tab 下一项    Enter 下一项 / 开始    Esc 返回',
    'Your devices': '你的设备',
    'Edit the fields below, then choose your bitrate.': '填写下方地址和网卡，再选择码率。',
    'PS5 IPv4 address': 'PS5 IPv4 地址',
    'Portal IPv4 address': 'Portal IPv4 地址',
    'Mac LAN interface': 'Mac 局域网网卡',
    'Enter interface': '输入网卡名称',
    'Enter IPv4 address': '输入 IPv4 地址',
    'type here': '在此填写',
    'Bitrate (Mbps)': '码率 (Mbps)',
    'recommended': '推荐',
    'use arrow to choose': '方向键选择',
    'Type to replace; arrows to edit. Find IPs in your router list.': '直接输入可替换，方向键可编辑。IP 可在路由器设备列表中查找。',
    'Use the adapter on the PS5 / Portal LAN. Wi-Fi is often en0.': '选择与 PS5 / Portal 同一网络的网卡，Wi-Fi 通常为 en0。',
    '65 Mbps is recommended for your first attempt.': '首次使用推荐选择 65 Mbps。',
    'Try 100 Mbps after a stable 65 Mbps session.': '65 Mbps 稳定后，可以尝试 100 Mbps。',
    '200 Mbps is experimental and may increase stutter.': '200 Mbps 为实验选项，可能增加卡顿。',
    'Save and prepare connection  ->': '保存并准备连接 ->',
    'Enter a valid PS5 IPv4 address, such as 192.168.1.20': '请输入有效的 PS5 IPv4 地址，例如 192.168.1.20。',
    'Enter a valid Portal IPv4 address, such as 192.168.1.20': '请输入有效的 Portal IPv4 地址，例如 192.168.1.20。',
    'Use the PS5 IPv4 address shown by your router': '请使用路由器设备列表中 PS5 的 IPv4 地址。',
    'Use the Portal IPv4 address shown by your router': '请使用路由器设备列表中 Portal 的 IPv4 地址。',
    'PS5 and Portal must have different IPv4 addresses': 'PS5 和 Portal 的 IPv4 地址不能相同。',
    'Select a Mac LAN interface such as en0 or en4': '请输入 Mac 局域网网卡名称，例如 en0 或 en4。',
    'Could not save settings: {error}': '无法保存设置：{error}',
    'CHECK': '检查',
    'WAIT': '请稍候',
    'CONNECT': '请连接',
    'LINKING': '连接中',
    'LINKED': '已连接',
    'VERIFY': '验证中',
    'OK': '完成',
    'RESTORE': '恢复中',
    'READY': '已就绪',
    'RECOVER': '待恢复',
    'STOPPED': '已停止',
    'CONFIRMED': '已确认',
    'RESTORING': '恢复中',
    'STOPPING': '停止中',
    '! RECOVERY': '! 待恢复',
    'Restoring the direct path; please keep this Mac awake.': '正在恢复直连，请保持 Mac 唤醒。',
    'Q / Esc / Ctrl+C: stop and restore the network': 'Q / Esc / Ctrl+C 停止并恢复网络',
    'Keep Portal disconnected': '请保持 Portal 断开连接',
    'Checking devices...': '正在检查设备...',
    'Preparing the connection path...': '正在准备连接路径...',
    'CONNECT NOW: Portal -> PS5': '现在连接：Portal -> PS5',
    'Waiting for Portal to connect...': '等待 Portal 连接...',
    'Connection request received': '已收到连接请求',
    'Waiting for PS5 to accept the connection...': '等待 PS5 接受连接...',
    'PS5 accepted the connection': 'PS5 已接受连接',
    'Waiting for stream information...': '等待串流信息...',
    'Checking the higher target': '正在确认高码率目标',
    'Verifying the higher bitrate...': '正在验证高码率...',
    'Higher target reported': '已收到高码率目标',
    'PS5 confirmed the higher target.': 'PS5 已确认更高的目标码率。',
    'Finishing this attempt': '正在完成本次设置',
    'Restoring the direct connection...': '正在恢复直接连接...',
    'Restoring your network': '正在恢复网络',
    '  /  {seconds}s left to connect': ' / 剩余 {seconds} 秒，请连接',
    'On Portal, select your PS5 to start Remote Play.': '在 Portal 上选择你的 PS5，开始远程游玩。',
    'No action needed yet.': '暂时无需操作。',
    'When READY appears, you get {seconds} seconds to connect.': '显示“已就绪”后，你有 {seconds} 秒进行连接。',
    'Finishing this attempt...': '正在完成设置...',
    'Up to {seconds}s left to confirm.': '确认剩余最多 {seconds} 秒。',
    'Keep Portal connected.  ': '保持 Portal 连接。 ',
    'Request': '请求',
    'PS5 accepted': 'PS5 接受',
    'Target {samples}/3': '目标 {samples}/3',
    'Keep this Mac awake until the result appears.': '请保持 Mac 唤醒，直到结果出现。',
    'PS5-reported target: {target:.3f} Mbps': 'PS5 报告的目标码率：{target:.3f} Mbps',
    'Existing stream detected. Disconnect Portal, then reconnect now.': '检测到已有串流。请先断开 Portal，再立即重新连接。',
    'Enter / Esc: back to result': 'Enter / Esc 返回结果',
    'Local session details': '本次运行详情',
    'Report: {path}': '报告：{path}',
    'Recovery errors: {errors}': '恢复错误（原始信息）：{errors}',
    'Automatic recovery deadline: {seconds}s after watchdog start.': '自动恢复期限：恢复进程启动后 {seconds} 秒。',
    'The independent recovery process has its own deadline.': '独立的恢复进程会按其超时期限执行恢复。',
    'Manual recovery from this project folder: {command}': '在本项目目录中手动恢复：{command}',
    'The report and captures stay local. Share only a redacted summary.': '报告和抓包保存在本机。分享前请移除地址等隐私信息。',
    'Demo sessions do not write reports or change networking.': '演示模式不会保存报告或修改网络。',
    'The attempt stopped before a report was created.': '本次运行在报告生成前已停止。',
    'Enter / R: try again    D: details    Q / Esc: quit': 'Enter / R 重试    D 详情    Q / Esc 退出',
    'D: recovery details    Q / Esc: quit (keep Mac awake)': 'D 恢复详情    Q / Esc 退出（保持 Mac 唤醒）',
    ' / PS5 target, not measured throughput.': ' / PS5 目标值，并非实测视频码率。',
    'Try another session  ->': '再次设置连接 ->',
    'Quit and allow recovery': '退出并等待恢复',
    'Network recovery needs attention': '网络恢复需要处理',
    'The direct path could not be fully restored.': '未能完全恢复直接连接。',
    'Keep this Mac awake for automatic recovery. Reconnect Portal if needed. Press D for recovery details. Start another attempt only after recovery.': '保持 Mac 唤醒，等待自动恢复，必要时重连 Portal。按 D 查看恢复详情，恢复完成后再重试。',
    'Attempt stopped': '本次运行已停止',
    'Could not finish': '未能完成设置',
    'The attempt was stopped.': '本次运行已停止。',
    'Cancelled by user': '你已取消本次运行。',
    'No network mappings were changed. Keep both devices awake on the same LAN. Check the addresses and LAN adapter, then try again.': '网络映射未修改。保持两台设备唤醒并位于同一局域网，检查 IP 地址和网卡后重试。',
    'Network restoration completed. You can try again or quit.': '网络已恢复，可以重试或退出。',
    'No compatible startup captured': '未捕获到兼容的连接请求',
    'No new connection detected': '未检测到新连接',
    'The connection request was not modified.': '本次未修改连接请求。',
    'Disconnect Portal from PS5. Try again, wait for CONNECT NOW, then start a fresh Portal connection before the countdown ends.': '先断开 Portal 与 PS5，再重试。等到“现在连接”出现后，在倒计时结束前重新连接。',
    'Ready to play': '可以开始游玩',
    'PS5 confirmed the higher target. Direct-path restoration completed.': 'PS5 已确认更高的目标码率，直接连接已恢复。',
    'Keep this Portal session connected. This Mac is no longer relaying. Run the wizard again for each new connection.': '保持当前 Portal 连接。Mac 已退出中转，可关闭向导。每次断开后重新连接，都需再次运行。',
    'Target reported; verification incomplete': '已报告高码率，但验证未完成',
    'PS5 reported the higher target, but local packet verification was incomplete.': 'PS5 已报告更高的目标码率，但本机数据包验证未完成。',
    'Direct-path restoration completed. Check the report before retrying.': '直接连接已恢复。重试前请查看报告。',
    'Higher target not confirmed': '未确认高码率目标',
    'A startup request was modified, but three high target reports were not observed.': '已修改连接请求，但未收到三次高码率目标报告。',
    'Direct-path restoration completed. Reconnect normally, or retry with 65 Mbps.': '直接连接已恢复。可以正常重连，或选择 65 Mbps 重试。',
    'Open this wizard in an interactive Terminal window.': '请在可交互的终端窗口中打开向导。',
    'This guided launcher currently supports macOS.': '此设置向导目前支持 macOS。',
    'Double-click Start.command, or run: sudo .venv/bin/python portal_tui.py': '请双击 Start.command，或运行：sudo .venv/bin/python portal_tui.py',
    'This Python installation needs the standard curses module.': '当前 Python 安装需要标准 curses 模块。',
    'Demo closed.': '演示已关闭。',
    'Wizard closed.': '向导已关闭。',
    'Terminal setup failed: {error}. Try the macOS Terminal app.': '终端初始化失败：{error}。请尝试 macOS 自带的终端。',
}


def translate(text, language, **values):
    translated = ZH_CN.get(text, text) if language == 'zh-CN' else text
    return translated.format(**values) if values else translated


def cell_width(text):
    """CJK characters occupy two cells; combining marks share the prior cell."""
    return sum(0 if unicodedata.combining(char) else
               2 if unicodedata.east_asian_width(char) in ('W', 'F') else 1
               for char in text)


def clip_cells(text, width):
    used = 0
    for index, char in enumerate(text):
        used += cell_width(char)
        if used > width:
            return text[:index]
    return text


def pad_cells(text, width, *, center=False):
    text = clip_cells(text, width)
    remaining = width - cell_width(text)
    left = remaining // 2 if center else 0
    return ' ' * left + text + ' ' * (remaining - left)


def wrap_cells(text, width):
    if width < 2:
        raise ValueError('Text width must be at least two terminal cells')
    if cell_width(text) == len(text):
        return textwrap.wrap(text, width=width)
    # Keep Latin words intact when possible, but allow breaks between CJK glyphs.
    tokens = re.findall(r'[\w./:=+-]+|\s+|.', text, flags=re.ASCII)
    lines, line = [], ''
    for token in tokens:
        if token.isspace():
            if line and not line.endswith(' '):
                line += ' '
            continue
        if line and cell_width(line + token) > width:
            lines.append(line.rstrip())
            line = ''
        while cell_width(token) > width:
            head = clip_cells(token, width)
            lines.append(head)
            token = token[len(head):]
        line += token
    if line:
        lines.append(line.rstrip())
    return lines
