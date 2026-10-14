import AppKit

// This unprivileged Applications entry only opens the protected app. It has no
// helper entitlement, XPC endpoint or user-controlled executable path.
let app = URL(fileURLWithPath: "/Library/Application Support/Better Portal/Better Portal.app")
guard FileManager.default.fileExists(atPath: app.path) else {
    fputs("Install Better Portal with its signed package first.\n", stderr)
    exit(1)
}
NSWorkspace.shared.open(app)
