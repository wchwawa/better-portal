import Foundation
import Darwin
import PortalShared

final class Worker: SessionWorker {
    private let process = Process()
    private var input: Pipe?
    func start(_ request: SessionRequest, uid: uid_t, event: @escaping ([String: Any]) -> Void,
               finished: @escaping ([String: Any]) -> Void) throws {
        let team = try CodeIdentity.team()
        try CodeIdentity.trustedDirectoryChain(Portal.runtimeDirectory)
        try CodeIdentity.protectedTree(Portal.runtimeDirectory)
        try CodeIdentity.validate(Portal.runtime, team: team, identifier: Portal.runtimeID)
        let input = Pipe(), output = Pipe()
        self.input = input
        process.executableURL = Portal.runtime
        process.arguments = ["worker", "--caller-uid", String(uid)]
        // Never inherit Python, loader, sudo, HOME or search-path overrides.
        process.environment = ["PATH": "/usr/bin:/bin:/usr/sbin:/sbin", "HOME": "/var/root",
                               "LANG": "en_US.UTF-8", "PYTHONNOUSERSITE": "1"]
        process.currentDirectoryURL = URL(fileURLWithPath: "/")
        process.standardInput = input; process.standardOutput = output
        process.standardError = FileHandle.nullDevice
        try process.run()
        output.fileHandleForWriting.closeFile()
        input.fileHandleForReading.closeFile()
        do {
            try input.fileHandleForWriting.write(contentsOf: encode(["config": request.config, "profile": request.profile]) + Data([10]))
        } catch {
            // Enrollment has not completed, so the child cannot alter mappings.
            input.fileHandleForWriting.closeFile()
            cancel(); process.waitUntilExit()
            throw error
        }
        DispatchQueue.global().async {
            var report: [String: Any]?
            let buffer = LineBuffer()
            do {
                while true {
                    let chunk = try output.fileHandleForReading.read(upToCount: 65536) ?? Data()
                    if chunk.isEmpty { break }
                    for line in try buffer.append(chunk) {
                        let message = try decode(line, limit: Portal.maxReply)
                        if let value = message["event"] as? [String: Any] { event(value) }
                        if let value = message["report"] as? [String: Any] { report = value }
                    }
                }
            } catch { self.cancel() }
            self.process.waitUntilExit()
            self.input?.fileHandleForWriting.closeFile()
            output.fileHandleForReading.closeFile()
            finished(report ?? ["completed": false, "run_error": "Connection worker stopped unexpectedly",
                                "restoration_errors": ["Independent recovery may still be running. Keep this Mac awake."],
                                "watchdog_seconds": 155])
        }
    }
    func cancel() { if process.isRunning { process.terminate() } }
    func kill() { if process.isRunning { Darwin.kill(process.processIdentifier, SIGKILL) } }
}

do {
    guard geteuid() == 0 else { throw PortalError("The connection helper must be started by macOS") }
    let team = try CodeIdentity.team()
    try CodeIdentity.trustedDirectoryChain(Portal.base)
    try CodeIdentity.protectedTree(Portal.app)
    try CodeIdentity.validate(Portal.app, team: team, identifier: Portal.appID)
    let manager = SessionManager(factory: { Worker() }, recoveryPending: {
        FileManager.default.fileExists(atPath: Portal.lock)
    })
    let delegate = ServiceListener(manager: manager)
    let listener = NSXPCListener(machServiceName: Portal.helperID)
    listener.setConnectionCodeSigningRequirement(CodeIdentity.requirement(
        team: team, identifiers: [Portal.appID, Portal.bridgeID]))
    listener.delegate = delegate
    let timer = DispatchSource.makeTimerSource()
    timer.schedule(deadline: .now() + 1, repeating: 1)
    timer.setEventHandler { manager.tick() }
    timer.resume()
    listener.resume()
    withExtendedLifetime((delegate, timer, listener)) { RunLoop.current.run() }
} catch {
    fputs("Better Portal helper: \(error.localizedDescription)\n", stderr)
    exit(1)
}
