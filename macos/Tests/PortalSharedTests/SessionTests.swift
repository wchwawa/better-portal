import Testing
import Foundation
import Security
@testable import PortalShared

final class FakeWorker: SessionWorker {
    var starts = 0, cancels = 0, kills = 0
    var uid: uid_t?
    var event: (([String: Any]) -> Void)?
    var finish: (([String: Any]) -> Void)?
    var failure = false
    func start(_ request: SessionRequest, uid: uid_t, event: @escaping ([String: Any]) -> Void,
               finished: @escaping ([String: Any]) -> Void) throws {
        if failure { throw PortalError("Synthetic launch failure") }
        starts += 1; self.uid = uid; self.event = event; finish = finished
    }
    func cancel() { cancels += 1 }
    func kill() { kills += 1 }
}

@Suite(.serialized)
final class SessionTests {
    let start: [String: Any] = ["op": "start", "profile": "65", "config": [
        "interface": "en0", "ps5_ip": "192.168.1.20", "portal_ip": "192.168.1.30"]]
    let caller = UUID()
    func send(_ manager: SessionManager, _ value: [String: Any], caller: UUID? = nil, uid: uid_t = 501) -> [String: Any] {
        try! decode(manager.exchange(encode(value), caller: caller ?? self.caller, uid: uid), limit: Portal.maxReply)
    }
    @Test func testValidationRejectsExtraFieldsCommandsPathsAndInvalidProfiles() {
        var attacks: [[String: Any]] = [
            ["op": "exec", "command": "id"], ["op": "poll", "uid": 0],
            ["op": "cancel", "state": "/etc/passwd"], ["op": "start"],
        ]
        for profile: Any in ["300", 65, true] {
            var value = start; value["profile"] = profile; attacks.append(value)
        }
        for extra in ["uid", "executable", "output", "SUDO_UID", "import_path"] {
            var value = start; value[extra] = "/tmp/payload"; attacks.append(value)
        }
        for interface in ["en0\n", "en0;id", "utun0", "../../en0", "en"] {
            var value = start; var config = value["config"] as! [String: String]
            config["interface"] = interface; value["config"] = config; attacks.append(value)
        }
        for address in ["127.0.0.1", "0.0.0.0", "224.0.0.1", "255.255.255.255", "1;id", "::1", "192.168.1.20"] {
            var value = start; var config = value["config"] as! [String: String]
            config["portal_ip"] = address; value["config"] = config; attacks.append(value)
        }
        let worker = FakeWorker()
        let manager = SessionManager(factory: { worker }, recoveryPending: { false })
        for value in attacks { XCTAssertNotNil(send(manager, value)["error"], "\(value)") }
        XCTAssertEqual(worker.starts, 0)
        XCTAssertThrowsError(try decode(Data(repeating: 0, count: 4097)))
        XCTAssertThrowsError(try decode(Data("[]".utf8)))
    }
    @Test func testAuthenticatedCallerCannotBeOverriddenAndResultsBelongToConnection() {
        let worker = FakeWorker()
        let manager = SessionManager(factory: { worker }, recoveryPending: { false })
        XCTAssertNotNil(send(manager, start, uid: 0)["error"])
        XCTAssertEqual(send(manager, start, uid: 502)["started"] as? Bool, true)
        XCTAssertEqual(worker.uid, 502)
        XCTAssertNotNil(send(manager, ["op": "poll"], uid: 501)["error"])
        XCTAssertNotNil(send(manager, ["op": "cancel"], caller: UUID(), uid: 502)["error"])
        XCTAssertNotNil(send(manager, ["op": "prepareRemoval"], caller: UUID(), uid: 501)["error"])
        XCTAssertEqual(worker.cancels, 0)
    }
    @Test func testConcurrentStartCancelAndRetryHaveNoStaleEvents() {
        let worker = FakeWorker()
        let manager = SessionManager(factory: { worker }, recoveryPending: { false })
        XCTAssertNotNil(send(manager, start)["started"])
        XCTAssertNotNil(send(manager, start, caller: UUID())["error"])
        worker.event?(["type": "ready", "seconds": 120])
        XCTAssertEqual((send(manager, ["op": "poll"])["events"] as? [[String: Any]])?.count, 1)
        _ = send(manager, ["op": "cancel"]); _ = send(manager, ["op": "cancel"])
        XCTAssertEqual(worker.cancels, 1)
        worker.finish?(["completed": false, "run_error": "Cancelled by user", "restoration_errors": []])
        XCTAssertNotNil(send(manager, ["op": "poll"])["report"])
        XCTAssertNotNil(send(manager, start)["started"])
        let fresh = send(manager, ["op": "poll"])
        XCTAssertNil(fresh["report"])
        XCTAssertEqual((fresh["events"] as? [Any])?.count, 0)
    }
    @Test func testDisconnectAndMissingHeartbeatsCancelThenBoundWorkerLifetime() {
        let worker = FakeWorker(); var now: Double = 0
        let manager = SessionManager(factory: { worker }, recoveryPending: { false }, clock: { now })
        _ = send(manager, start)
        now = 11; manager.tick()
        XCTAssertEqual(worker.cancels, 1)
        now = 32; manager.tick()
        XCTAssertEqual(worker.kills, 1)
        worker.finish?([:]); _ = send(manager, start)
        manager.disconnected(caller)
        _ = send(manager, ["op": "status"])
        XCTAssertEqual(worker.cancels, 2)
    }
    @Test func testRemovalDrainsRecoveryAndBlocksNewStartsUntilDisconnect() {
        let worker = FakeWorker(); var recovery = false
        let manager = SessionManager(factory: { worker }, recoveryPending: { recovery })
        _ = send(manager, start)
        let remover = UUID()
        XCTAssertEqual(send(manager, ["op": "prepareRemoval"], caller: remover)["ready"] as? Bool, false)
        XCTAssertEqual(worker.cancels, 1)
        recovery = true; worker.finish?(["restoration_errors": ["synthetic"]])
        XCTAssertEqual(send(manager, ["op": "prepareRemoval"], caller: remover)["ready"] as? Bool, false)
        XCTAssertNotNil(send(manager, start)["error"])
        recovery = false
        XCTAssertEqual(send(manager, ["op": "prepareRemoval"], caller: remover)["ready"] as? Bool, true)
        XCTAssertNotNil(send(manager, start)["error"])
        manager.disconnected(remover)
        XCTAssertNotNil(send(manager, start)["started"])
    }
    @Test func testLaunchFailureReleasesSlotAndRecoveryOnDaemonRestartBlocksStart() {
        let worker = FakeWorker(); worker.failure = true
        let manager = SessionManager(factory: { worker }, recoveryPending: { false })
        XCTAssertNotNil(send(manager, start)["error"])
        worker.failure = false; XCTAssertNotNil(send(manager, start)["started"])
        let restarted = SessionManager(factory: { worker }, recoveryPending: { true })
        XCTAssertNotNil(send(restarted, start)["error"])
        XCTAssertEqual(send(restarted, ["op": "prepareRemoval"])["ready"] as? Bool, false)
    }
    @Test func testProgressAndPipeBuffersAreBounded() throws {
        let worker = FakeWorker()
        let manager = SessionManager(factory: { worker }, recoveryPending: { false })
        _ = send(manager, start)
        for index in 0..<1000 { worker.event?(["type": "tick", "seconds": index]) }
        XCTAssertEqual((send(manager, ["op": "poll"])["events"] as? [Any])?.count, 256)
        let buffer = LineBuffer(limit: 4)
        XCTAssertTrue(try buffer.append(Data("ab".utf8)).isEmpty)
        XCTAssertEqual(try buffer.append(Data("c\nxy\n".utf8)), [Data("abc".utf8), Data("xy".utf8)])
        XCTAssertThrowsError(try buffer.append(Data("12345".utf8)))
    }
    @Test func testProtectedPayloadRejectsWritableFilesAndEscapingLinks() throws {
        let root = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: false,
                                               attributes: [.posixPermissions: 0o755])
        defer { try? FileManager.default.removeItem(at: root) }
        let file = root.appendingPathComponent("payload")
        try Data("data".utf8).write(to: file)
        try FileManager.default.setAttributes([.posixPermissions: 0o644], ofItemAtPath: file.path)
        XCTAssertNoThrow(try CodeIdentity.protectedTree(root, owner: getuid()))
        try FileManager.default.setAttributes([.posixPermissions: 0o666], ofItemAtPath: file.path)
        XCTAssertThrowsError(try CodeIdentity.protectedTree(root, owner: getuid()))
        try FileManager.default.removeItem(at: file)
        try FileManager.default.createSymbolicLink(at: file, withDestinationURL: URL(fileURLWithPath: "/etc/passwd"))
        XCTAssertThrowsError(try CodeIdentity.protectedTree(root, owner: getuid()))
    }
}

@Suite(.serialized)
final class XPCTests {
    @Test func testNativeXPCMessagesAndCodeIdentityRejection() throws {
        guard getuid() >= 501 else { throw PortalError("Needs an unprivileged Mac user") }
        // Only this test listener trusts the runner's exact designated identity.
        // Production always requires an Apple signature, Team ID and app IDs.
        var code: SecCode?, staticCode: SecStaticCode?, requirement: SecRequirement?, text: CFString?
        XCTAssertEqual(SecCodeCopySelf([], &code), errSecSuccess)
        XCTAssertEqual(SecCodeCopyStaticCode(code!, [], &staticCode), errSecSuccess)
        XCTAssertEqual(SecCodeCopyDesignatedRequirement(staticCode!, [], &requirement), errSecSuccess)
        XCTAssertEqual(SecRequirementCopyString(requirement!, [], &text), errSecSuccess)
        for allowed in [true, false] {
            let worker = FakeWorker()
            let manager = SessionManager(factory: { worker }, recoveryPending: { false })
            let delegate = ServiceListener(manager: manager)
            let listener = NSXPCListener.anonymous()
            listener.delegate = delegate
            listener.setConnectionCodeSigningRequirement(allowed ? text! as String : "identifier \"untrusted-client-must-fail\"")
            listener.resume()
            let connection = NSXPCConnection(listenerEndpoint: listener.endpoint)
            connection.remoteObjectInterface = NSXPCInterface(with: PortalService.self)
            connection.resume()
            let finished = DispatchSemaphore(value: 0)
            let proxy = connection.remoteObjectProxyWithErrorHandler { _ in
                XCTAssertFalse(allowed); finished.signal()
            } as! PortalService
            proxy.exchange(encode(["op": "status"])) { data in
                XCTAssertTrue(allowed)
                XCTAssertEqual((try? decode(data))?["busy"] as? Bool, false)
                finished.signal()
            }
            #expect(finished.wait(timeout: .now() + 5) == .success)
            connection.invalidate(); listener.invalidate()
            withExtendedLifetime(delegate) {}
            XCTAssertEqual(worker.starts, 0)
        }
    }
}

// Small assertion adapters keep the state-machine cases readable on both Xcode
// and Command Line Tools installations using Swift Testing.
private func XCTAssertTrue(_ value: Bool) { #expect(value) }
private func XCTAssertFalse(_ value: Bool) { #expect(!value) }
private func XCTAssertEqual<T: Equatable>(_ a: T, _ b: T) { #expect(a == b) }
private func XCTAssertNil<T>(_ value: T?) { #expect(value == nil) }
private func XCTAssertNotNil<T>(_ value: T?, _ message: String = "") { #expect(value != nil, "\(message)") }
private func XCTAssertThrowsError<T>(_ value: @autoclosure () throws -> T) {
    do { _ = try value(); Issue.record("Expected rejection") } catch {}
}
private func XCTAssertNoThrow<T>(_ value: @autoclosure () throws -> T) {
    do { _ = try value() } catch { Issue.record("Unexpected rejection: \(error)") }
}
