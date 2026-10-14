import AppKit
import ServiceManagement
import PortalShared

final class Application: NSObject, NSApplicationDelegate {
    private let service = SMAppService.daemon(plistName: Portal.plist)
    private var window: NSWindow!
    private let status = NSTextField(wrappingLabelWithString: "")
    private let detail = NSTextField(wrappingLabelWithString: "")
    private var enable: NSButton!
    private var open: NSButton!
    private var remove: NSButton!
    private var removalClient: ServiceClient?
    private var removing = false
    private var removalRequestPending = false
    private var timer: Timer?

    private func text(_ source: String) -> String {
        let settings = FileManager.default.homeDirectoryForCurrentUser
            .appendingPathComponent("Library/Application Support/Better Portal/tui-settings.json")
        let saved = (try? Data(contentsOf: settings)).flatMap { try? JSONSerialization.jsonObject(with: $0) as? [String: Any] }
        let preferred = Locale.preferredLanguages.first ?? "en"
        let language = saved?["language"] as? String ?? (preferred.hasPrefix("zh") ? "zh-CN" : String(preferred.prefix(2)))
        guard let url = Bundle.main.url(forResource: language, withExtension: "json", subdirectory: "locales"),
              let data = try? Data(contentsOf: url),
              let catalog = try? JSONSerialization.jsonObject(with: data) as? [String: String] else { return source }
        return catalog[source] ?? source
    }

    func applicationDidFinishLaunching(_ notification: Notification) {
        window = NSWindow(contentRect: NSRect(x: 0, y: 0, width: 510, height: 290),
                          styleMask: [.titled, .closable, .miniaturizable], backing: .buffered, defer: false)
        window.title = "Better Portal"
        let title = NSTextField(labelWithString: "Better Portal")
        title.font = .boldSystemFont(ofSize: 25)
        status.font = .boldSystemFont(ofSize: 15)
        detail.textColor = .secondaryLabelColor
        enable = NSButton(title: text("Enable connection helper"), target: self, action: #selector(enableHelper))
        open = NSButton(title: text("Open wizard"), target: self, action: #selector(openWizard))
        let permissions = NSButton(title: text("System Settings"), target: self, action: #selector(settings))
        remove = NSButton(title: text("Remove connection helper"), target: self, action: #selector(removeHelper))
        let actions = NSStackView(views: [enable, open])
        actions.orientation = .horizontal
        let secondary = NSStackView(views: [permissions, remove])
        secondary.orientation = .horizontal
        let stack = NSStackView(views: [title, status, detail, actions, secondary])
        stack.orientation = .vertical; stack.alignment = .leading; stack.spacing = 17
        stack.translatesAutoresizingMaskIntoConstraints = false
        window.contentView!.addSubview(stack)
        NSLayoutConstraint.activate([
            stack.leadingAnchor.constraint(equalTo: window.contentView!.leadingAnchor, constant: 26),
            stack.trailingAnchor.constraint(equalTo: window.contentView!.trailingAnchor, constant: -26),
            stack.topAnchor.constraint(equalTo: window.contentView!.topAnchor, constant: 24)])
        refresh()
        timer = Timer.scheduledTimer(withTimeInterval: 1, repeats: true) { [weak self] _ in self?.refresh() }
        window.center(); window.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)
    }

    private func refresh() {
        if removing { pollRemoval(); return }
        let enabled = service.status == .enabled
        status.stringValue = text(enabled ? "Connection helper enabled" : "Helper disabled")
        detail.stringValue = text(enabled
            ? "Open the wizard normally. macOS manages authorization; Better Portal never stores your password."
            : service.status == .requiresApproval
                ? "Approve Better Portal in System Settings, then return here."
                : "Enable the helper once through macOS to use the wizard without sudo.")
        enable.isEnabled = !enabled
        open.isEnabled = enabled
        remove.isEnabled = service.status != .notRegistered && service.status != .notFound
        enable.title = text("Enable connection helper"); open.title = text("Open wizard")
        remove.title = text("Remove connection helper")
    }

    private func show(_ error: Error) {
        let alert = NSAlert(); alert.messageText = "Better Portal"
        alert.informativeText = error.localizedDescription
        alert.runModal()
    }

    @objc private func enableHelper() {
        do {
            guard Bundle.main.bundleURL.standardizedFileURL == Portal.app else {
                throw PortalError(text("Install Better Portal in Applications using its installer first."))
            }
            let team = try CodeIdentity.team()
            try CodeIdentity.protectedTree(Portal.app)
            try CodeIdentity.validate(Portal.app, team: team, identifier: Portal.appID)
            try service.register()
        } catch {
            if service.status != .requiresApproval { show(error) }
        }
        if service.status == .requiresApproval { SMAppService.openSystemSettingsLoginItems() }
        refresh()
    }

    @objc private func settings() { SMAppService.openSystemSettingsLoginItems() }

    @objc private func openWizard() {
        guard service.status == .enabled else { refresh(); return }
        guard let script = Bundle.main.url(forResource: "Start", withExtension: "command") else { return }
        NSWorkspace.shared.open(script)
    }

    @objc private func removeHelper() {
        // A disabled helper cannot be running new requests. Enable approval is
        // never requested just to remove a registration that was denied.
        if service.status != .enabled {
            if FileManager.default.fileExists(atPath: Portal.lock) {
                show(PortalError(text("Recovery is still pending. Keep this Mac awake and try again after it finishes.")))
                return
            }
            unregister(); return
        }
        do { removalClient = try ServiceClient(); removing = true; pollRemoval() }
        catch { show(error) }
    }

    private func pollRemoval() {
        status.stringValue = text("Finishing recovery before removal…")
        detail.stringValue = text("Keep this Mac awake. The helper will be removed when the network is restored.")
        enable.isEnabled = false; open.isEnabled = false; remove.isEnabled = false
        guard !removalRequestPending else { return }
        removalRequestPending = true
        removalClient?.send(encode(["op": "prepareRemoval"])) { data in
            DispatchQueue.main.async {
                self.removalRequestPending = false
                do {
                    let value = try decode(data, limit: Portal.maxReply)
                    if let error = value["error"] as? String { throw PortalError(error) }
                    if value["ready"] as? Bool == true { self.unregister() }
                } catch {
                    self.removing = false; self.removalClient = nil; self.show(error)
                }
            }
        }
    }

    private func unregister() {
        // Keep the drain connection alive until unregistration completes, so a
        // competing bridge cannot start between the idle check and unload.
        Task { @MainActor in
            do { try await service.unregister() }
            catch { show(error) }
            removing = false; removalClient = nil; refresh()
        }
    }

    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool { true }
}

let app = NSApplication.shared
let delegate = Application()
app.setActivationPolicy(.regular)
app.delegate = delegate
app.run()
