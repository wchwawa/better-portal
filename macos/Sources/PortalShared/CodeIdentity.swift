import Foundation
import Security

public enum CodeIdentity {
    public static func team() throws -> String {
        var code: SecCode?
        var staticCode: SecStaticCode?
        var info: CFDictionary?
        guard SecCodeCopySelf([], &code) == errSecSuccess, let code,
              SecCodeCopyStaticCode(code, [], &staticCode) == errSecSuccess, let staticCode,
              SecCodeCopySigningInformation(staticCode, SecCSFlags(rawValue: kSecCSSigningInformation), &info) == errSecSuccess,
              let team = (info as? [String: Any])?[kSecCodeInfoTeamIdentifier as String] as? String,
              team.range(of: "\\A[A-Z0-9]{10}\\z", options: .regularExpression) != nil else {
            throw PortalError("Install a build signed with an Apple Developer ID before enabling the helper")
        }
        return team
    }

    public static func requirement(team: String, identifiers: [String]) -> String {
        let identities = identifiers.map { "identifier \"\($0)\"" }.joined(separator: " or ")
        return "anchor apple generic and certificate leaf[subject.OU] = \"\(team)\" and (\(identities))"
    }

    public static func validate(_ url: URL, team: String, identifier: String) throws {
        var code: SecStaticCode?
        var requirement: SecRequirement?
        let text = self.requirement(team: team, identifiers: [identifier])
        guard SecStaticCodeCreateWithPath(url as CFURL, [], &code) == errSecSuccess, let code,
              SecRequirementCreateWithString(text as CFString, [], &requirement) == errSecSuccess,
              SecStaticCodeCheckValidity(code,
                  SecCSFlags(rawValue: kSecCSCheckAllArchitectures | kSecCSCheckNestedCode | kSecCSStrictValidate),
                  requirement) == errSecSuccess else {
            throw PortalError("Installed code failed signature verification. Reinstall Better Portal.")
        }
    }

    /// The installer owns the entire sealed payload. Internal framework symlinks
    /// are permitted; links out of the app and writable payloads are rejected.
    public static func protectedTree(_ root: URL, owner: uid_t = 0) throws {
        let base = root.standardizedFileURL.path
        guard root.resolvingSymlinksInPath().path == base else { throw PortalError("Unexpected installation path") }
        let fm = FileManager.default
        var enumerationError: Error?
        guard let entries = fm.enumerator(at: root, includingPropertiesForKeys: nil,
                                         errorHandler: { _, error in enumerationError = error; return false }) else {
            throw PortalError("Cannot inspect installed payload")
        }
        for url in [root] + entries.compactMap({ $0 as? URL }) {
            let attrs = try fm.attributesOfItem(atPath: url.path)
            guard (attrs[.ownerAccountID] as? NSNumber)?.uint32Value == owner else {
                throw PortalError("Install Better Portal with its installer before enabling the helper")
            }
            let resolved = url.resolvingSymlinksInPath().path
            guard resolved == base || resolved.hasPrefix(base + "/") else { throw PortalError("Payload link escapes app") }
            if attrs[.type] as? FileAttributeType != .typeSymbolicLink {
                guard let permissions = attrs[.posixPermissions] as? NSNumber,
                      permissions.intValue & 0o022 == 0 else { throw PortalError("Installed payload is writable") }
            }
        }
        if let enumerationError { throw enumerationError }
    }
}

public final class ServiceClient {
    public let connection: NSXPCConnection
    public init() throws {
        connection = NSXPCConnection(machServiceName: Portal.helperID, options: .privileged)
        connection.remoteObjectInterface = NSXPCInterface(with: PortalService.self)
        connection.setCodeSigningRequirement(CodeIdentity.requirement(
            team: try CodeIdentity.team(), identifiers: [Portal.helperID]))
        connection.resume()
    }
    public func send(_ request: Data, reply: @escaping (Data) -> Void) {
        guard request.count <= Portal.maxRequest else {
            reply(encode(["error": "Message too large"])); return
        }
        guard let proxy = connection.remoteObjectProxyWithErrorHandler({ error in
            reply(encode(["error": "Helper unavailable. Open Better Portal to enable it.",
                          "detail": error.localizedDescription]))
        }) as? PortalService else { reply(encode(["error": "Helper unavailable"])); return }
        proxy.exchange(request, withReply: reply)
    }
    deinit { connection.invalidate() }
}
