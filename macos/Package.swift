// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "BetterPortal", platforms: [.macOS(.v13)],
    products: [
        .executable(name: "BetterPortal", targets: ["BetterPortal"]),
        .executable(name: "PortalHelper", targets: ["PortalHelper"]),
        .executable(name: "PortalBridge", targets: ["PortalBridge"]),
        .executable(name: "PortalLauncher", targets: ["PortalLauncher"]),
    ],
    targets: [
        .target(name: "PortalShared"),
        .executableTarget(name: "BetterPortal", dependencies: ["PortalShared"]),
        .executableTarget(name: "PortalHelper", dependencies: ["PortalShared"]),
        .executableTarget(name: "PortalBridge", dependencies: ["PortalShared"]),
        .executableTarget(name: "PortalLauncher"),
        .testTarget(name: "PortalSharedTests", dependencies: ["PortalShared"]),
    ])
