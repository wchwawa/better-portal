import Foundation
import Darwin
import PortalShared

// The bridge is signed native code. Python never connects directly to the daemon.
// Closing stdin (including a crashed TUI) invalidates the XPC connection.
signal(SIGPIPE, SIG_IGN)
do {
    guard getuid() == geteuid(), geteuid() >= 501, CommandLine.arguments.count == 1 else {
        throw PortalError("Launch the wizard as your normal Mac user")
    }
    let client = try ServiceClient()
    defer { client.connection.invalidate() }
    let buffer = LineBuffer(limit: Portal.maxRequest)
    while true {
        let chunk = FileHandle.standardInput.availableData
        if chunk.isEmpty { break }
        for request in try buffer.append(chunk) {
            _ = try decode(request)
            let completed = DispatchSemaphore(value: 0)
            let lock = NSLock()
            var response: Data?
            client.send(request) { data in
                lock.lock(); if response == nil { response = data; completed.signal() }; lock.unlock()
            }
            guard completed.wait(timeout: .now() + 30) == .success else { throw PortalError("Helper did not respond") }
            lock.lock(); let data = response!; lock.unlock()
            guard data.count <= Portal.maxReply else { throw PortalError("Helper response too large") }
            try FileHandle.standardOutput.write(contentsOf: data + Data([10]))
        }
    }
} catch {
    try? FileHandle.standardOutput.write(contentsOf: encode(["error": error.localizedDescription]) + Data([10]))
    exit(1)
}
