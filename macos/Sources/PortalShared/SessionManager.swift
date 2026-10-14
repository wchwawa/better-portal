import Foundation

public protocol SessionWorker: AnyObject {
    func start(_ request: SessionRequest, uid: uid_t,
               event: @escaping ([String: Any]) -> Void,
               finished: @escaping ([String: Any]) -> Void) throws
    func cancel()
    func kill()
}

/// All state transitions run on one queue, including process callbacks and IPC.
public final class SessionManager {
    private let queue = DispatchQueue(label: "portal.sessions")
    private let factory: () -> SessionWorker
    private let recoveryPending: () -> Bool
    private let clock: () -> TimeInterval
    private var worker: SessionWorker?
    private var owner: UUID?
    private var ownerUID: uid_t?
    private var removing: UUID?
    private var events: [[String: Any]] = []
    private var result: [String: Any]?
    private var heartbeat: TimeInterval = 0
    private var started: TimeInterval = 0
    private var cancelledAt: TimeInterval?

    public init(factory: @escaping () -> SessionWorker,
                recoveryPending: @escaping () -> Bool,
                clock: @escaping () -> TimeInterval = { ProcessInfo.processInfo.systemUptime }) {
        self.factory = factory; self.recoveryPending = recoveryPending; self.clock = clock
    }

    public func exchange(_ data: Data, caller: UUID, uid: uid_t) -> Data {
        queue.sync {
            do {
                guard uid >= 501 else { throw PortalError("Use Better Portal as your normal Mac user") }
                let message = try decode(data)
                guard let operation = message["op"] as? String else { throw PortalError("Missing operation") }
                if operation != "start", Set(message.keys) != ["op"] { throw PortalError("Unexpected request fields") }
                switch operation {
                case "status":
                    return encode(["busy": worker != nil, "recovery_pending": recoveryPending(),
                                   "removing": removing != nil])
                case "start":
                    let request = try SessionRequest(message)
                    guard removing == nil, worker == nil, !recoveryPending() else {
                        throw PortalError("Another attempt or recovery is active. Wait for it to finish.")
                    }
                    let next = factory()
                    owner = caller; ownerUID = uid; events = []; result = nil
                    heartbeat = clock(); started = heartbeat; cancelledAt = nil; worker = next
                    do {
                        try next.start(request, uid: uid, event: { [weak self] event in
                            self?.queue.async { [weak self] in
                                guard let self, self.owner == caller, self.worker != nil else { return }
                                // Never let an abandoned terminal create unbounded history.
                                if self.events.count >= 256 { self.events.removeFirst() }
                                self.events.append(event)
                            }
                        }, finished: { [weak self] report in
                            self?.queue.async { [weak self] in
                                guard let self, self.owner == caller else { return }
                                self.worker = nil; self.result = report
                            }
                        })
                    } catch { worker = nil; owner = nil; ownerUID = nil; throw error }
                    return encode(["started": true])
                case "poll", "cancel":
                    guard owner == caller, ownerUID == uid else { throw PortalError("This connection does not own the session") }
                    heartbeat = clock()
                    if operation == "cancel" { cancel() }
                    let pending = events; events = []
                    var response: [String: Any] = ["events": pending, "running": worker != nil]
                    if let result { response["report"] = result }
                    return encode(response)
                case "prepareRemoval":
                    guard removing == nil || removing == caller,
                          worker == nil || ownerUID == uid else {
                        throw PortalError("Another Mac user has an active session")
                    }
                    removing = caller; cancel()
                    return encode(["ready": worker == nil && !recoveryPending()])
                case "abortRemoval":
                    guard removing == caller else { throw PortalError("Removal belongs to another connection") }
                    removing = nil; return encode(["ok": true])
                default: throw PortalError("Operation is not allowed")
                }
            } catch { return encode(["error": error.localizedDescription]) }
        }
    }

    private func cancel() {
        if worker != nil && cancelledAt == nil { cancelledAt = clock(); worker?.cancel() }
    }

    public func disconnected(_ caller: UUID) {
        queue.async {
            if self.owner == caller { self.cancel() }
            if self.removing == caller { self.removing = nil }
        }
    }

    public func tick() {
        queue.sync {
            guard worker != nil else { return }
            if clock() - heartbeat > 10 || clock() - started > 200 { cancel() }
            if let cancelledAt, clock() - cancelledAt > 20 {
                // The detached watchdog remains alive; its lock still gates retry/removal.
                worker?.kill()
            }
        }
    }
}

public final class ServiceEndpoint: NSObject, PortalService {
    private let manager: SessionManager
    public let id = UUID()
    private let uid: uid_t
    public init(manager: SessionManager, uid: uid_t) { self.manager = manager; self.uid = uid }
    public func exchange(_ request: Data, withReply reply: @escaping (Data) -> Void) {
        reply(manager.exchange(request, caller: id, uid: uid))
    }
    public func disconnected() { manager.disconnected(id) }
}

public final class ServiceListener: NSObject, NSXPCListenerDelegate {
    private let manager: SessionManager
    public init(manager: SessionManager) { self.manager = manager }
    public func listener(_ listener: NSXPCListener, shouldAcceptNewConnection connection: NSXPCConnection) -> Bool {
        guard connection.effectiveUserIdentifier >= 501 else { return false }
        let endpoint = ServiceEndpoint(manager: manager, uid: connection.effectiveUserIdentifier)
        connection.exportedInterface = NSXPCInterface(with: PortalService.self)
        connection.exportedObject = endpoint
        connection.invalidationHandler = { endpoint.disconnected() }
        connection.interruptionHandler = { endpoint.disconnected() }
        connection.resume()
        return true
    }
}
