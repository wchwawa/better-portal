import Foundation
import Darwin

public enum Portal {
    public static let appID = "com.wchwawa.betterportal"
    public static let helperID = appID + ".helper"
    public static let bridgeID = appID + ".bridge"
    public static let runtimeID = appID + ".runtime"
    public static let plist = helperID + ".plist"
    public static let app = URL(fileURLWithPath: "/Applications/Better Portal.app")
    public static let storage = URL(fileURLWithPath: "/Library/Application Support/Better Portal")
    public static let lock = "/var/run/portal-lab-capture.lock"
    public static let maxRequest = 4096
    public static let maxReply = 1_048_576
}

@objc public protocol PortalService {
    func exchange(_ request: Data, withReply reply: @escaping (Data) -> Void)
}

public struct PortalError: Error, LocalizedError {
    public let message: String
    public init(_ message: String) { self.message = message }
    public var errorDescription: String? { message }
}

public func encode(_ value: [String: Any]) -> Data {
    (try? JSONSerialization.data(withJSONObject: value, options: [.sortedKeys])) ?? Data("{}".utf8)
}

public func decode(_ data: Data, limit: Int = Portal.maxRequest) throws -> [String: Any] {
    guard data.count <= limit,
          let object = try JSONSerialization.jsonObject(with: data) as? [String: Any] else {
        throw PortalError("Invalid or oversized request")
    }
    return object
}

public struct SessionRequest {
    public let config: [String: String]
    public let profile: String

    public init(_ value: [String: Any]) throws {
        guard Set(value.keys) == ["op", "config", "profile"], value["op"] as? String == "start",
              let profile = value["profile"] as? String, ["65", "100", "200"].contains(profile),
              let config = value["config"] as? [String: String],
              Set(config.keys) == ["interface", "ps5_ip", "portal_ip"],
              let interface = config["interface"],
              interface.range(of: "\\Aen[0-9]{1,4}\\z", options: .regularExpression) != nil,
              let ps5 = config["ps5_ip"], let portal = config["portal_ip"], ps5 != portal,
              Self.validAddress(ps5), Self.validAddress(portal) else {
            throw PortalError("Choose a Mac LAN interface, distinct local IPv4 addresses and a 65/100/200 profile")
        }
        self.config = config
        self.profile = profile
    }

    private static func validAddress(_ value: String) -> Bool {
        var address = in_addr()
        guard value.utf8.count <= 15, inet_pton(AF_INET, value, &address) == 1 else { return false }
        let parts = value.split(separator: ".").compactMap { Int($0) }
        return parts.count == 4 && parts[0] > 0 && parts[0] != 127 && parts[0] < 224
            && value != "169.254.0.0"
    }
}

/// A framed JSON stream is used only over anonymous pipes, never a network port.
public final class LineBuffer {
    private var pending = Data()
    private let limit: Int
    public init(limit: Int = Portal.maxReply) { self.limit = limit }
    public func append(_ bytes: Data) throws -> [Data] {
        pending.append(bytes)
        var lines: [Data] = []
        while let newline = pending.firstIndex(of: 10) {
            guard newline <= limit else { throw PortalError("Message too large") }
            lines.append(pending.prefix(upTo: newline))
            pending.removeSubrange(...newline)
        }
        guard pending.count <= limit else { throw PortalError("Message too large") }
        return lines
    }
}
