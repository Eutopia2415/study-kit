// Study HUD: a floating, always-on-top HUD that shows widget.html from the local Study Plan
// server. Modelled on Agent HUD (read out of its binary): the HUD lives on a screen edge
// (top/right/bottom/left) at an offset along it; dragging is handled natively with the
// closed-hand cursor and keeps the grab point under the pointer; on drop it snaps to the
// nearest edge. The page keeps screen-sized layout coordinates, but the actual native window
// is clipped to the visible HUD content. Transparent screen-sized windows block secure payment UI.
import Cocoa
import WebKit

// --port N points the app at another server (used for testing against a scratch copy).
let port = CommandLine.arguments.firstIndex(of: "--port").flatMap { i in
    CommandLine.arguments.dropFirst(i + 1).first.flatMap { Int($0) } } ?? 4417
let base = URL(string: "http://127.0.0.1:\(port)")!
// build.sh installs the app in ~/Applications (outside iCloud) and records study-hall/ in Info.plist.
let studyDir = (Bundle.main.object(forInfoDictionaryKey: "StudyHallDir") as? String).map { URL(fileURLWithPath: $0) }
    ?? Bundle.main.bundleURL.deletingLastPathComponent()

func dbg(_ s: String) { if let h = FileHandle(forWritingAtPath: "/tmp/study-hud-drag.log") { h.seekToEndOfFile(); h.write((String(format: "%.3f ", Date().timeIntervalSince1970.truncatingRemainder(dividingBy: 1000)) + s + "\n").data(using: .utf8)!); h.closeFile() } }

final class HUDWebView: WKWebView {
    override func acceptsFirstMouse(for event: NSEvent?) -> Bool { true }
}

// Every mouse event reaches the window before any view, so the drag lives here, the way
// Agent HUD's HUDDragView owns it: a press on the pill passes through to the page (so a
// click still works); once the pointer travels 3pt it becomes a drag, the page stops
// seeing the gesture, and the pill follows the pointer until release.
final class Panel: NSPanel {
    override var canBecomeKey: Bool { true }   // lets Escape and scrolling reach the page
    var isOnPill: (NSPoint) -> Bool = { _ in false }   // window coordinates
    var onDragStart: ((NSPoint) -> Void)?   // the press point, screen coordinates
    var onDragMove: ((CGFloat, CGFloat) -> Void)?    // screen-space offset from the press
    var onDragEnd: (() -> Void)?
    private var press: NSPoint?
    private(set) var dragging = false

    override func sendEvent(_ e: NSEvent) {
        switch e.type {
        case .leftMouseDown where isOnPill(e.locationInWindow):
            press = convertPoint(toScreen: e.locationInWindow)
            dragging = false
        case .leftMouseDragged:
            if let start = press {
                let p = convertPoint(toScreen: e.locationInWindow)
                if !dragging && hypot(p.x - start.x, p.y - start.y) >= 3 {
                    dragging = true
                    NSCursor.closedHand.push()
                    onDragStart?(start)
                }
                if dragging { onDragMove?(p.x - start.x, p.y - start.y); return }
            }
        case .leftMouseUp:
            let wasDragging = dragging
            press = nil
            if wasDragging {
                dragging = false
                NSCursor.pop()
                onDragEnd?()
                return
            }
        default: break
        }
        super.sendEvent(e)
    }
}

extension NSColor {
    convenience init(hex: String) {
        var v: UInt64 = 0
        Scanner(string: hex.trimmingCharacters(in: CharacterSet(charactersIn: "#"))).scanHexInt64(&v)
        self.init(srgbRed: CGFloat((v >> 16) & 0xff) / 255, green: CGFloat((v >> 8) & 0xff) / 255, blue: CGFloat(v & 0xff) / 255, alpha: 1)
    }
}

// An SF Symbol drawn in one colour at 2x, as a data URL the page can use in an <img>.
func symbolDataURL(_ name: String, hex: String, size: CGFloat) -> String? {
    guard let symbol = NSImage(systemSymbolName: name, accessibilityDescription: nil) else { return nil }
    let config = NSImage.SymbolConfiguration(pointSize: size, weight: .semibold)
        .applying(NSImage.SymbolConfiguration(paletteColors: [NSColor(hex: hex)]))
    let img = symbol.withSymbolConfiguration(config) ?? symbol
    let s = img.size
    guard let rep = NSBitmapImageRep(bitmapDataPlanes: nil, pixelsWide: Int(s.width * 2), pixelsHigh: Int(s.height * 2),
                                     bitsPerSample: 8, samplesPerPixel: 4, hasAlpha: true, isPlanar: false,
                                     colorSpaceName: .deviceRGB, bytesPerRow: 0, bitsPerPixel: 0) else { return nil }
    rep.size = s
    NSGraphicsContext.saveGraphicsState()
    NSGraphicsContext.current = NSGraphicsContext(bitmapImageRep: rep)
    img.draw(in: NSRect(origin: .zero, size: s))
    NSGraphicsContext.restoreGraphicsState()
    return rep.representation(using: .png, properties: [:]).map { "data:image/png;base64," + $0.base64EncodedString() }
}

// MARK: - PowerSchool sync
// The PowerSchool login lives in the macOS Keychain (typed into a native sign-in box, never written to a
// file). A hidden browser signs in with it, reads grades, summative scores and the A-D class matrix,
// and posts them to the local server, which maps courses onto subjects.

enum Keychain {
    static var server: String { UserDefaults.standard.string(forKey: "powerschoolHost") ?? "" }   // defaults write local.studykit.studyhud powerschoolHost <your school's PowerSchool address>
    static func save(user: String, pass: String) -> Bool {
        delete()
        let q: [String: Any] = [kSecClass as String: kSecClassInternetPassword, kSecAttrServer as String: server,
                                kSecAttrProtocol as String: kSecAttrProtocolHTTPS, kSecAttrAccount as String: user,
                                kSecValueData as String: Data(pass.utf8), kSecAttrLabel as String: "Study HUD: PowerSchool"]
        return SecItemAdd(q as CFDictionary, nil) == errSecSuccess
    }
    static func load() -> (user: String, pass: String)? {
        let q: [String: Any] = [kSecClass as String: kSecClassInternetPassword, kSecAttrServer as String: server,
                                kSecReturnAttributes as String: true, kSecReturnData as String: true, kSecMatchLimit as String: kSecMatchLimitOne]
        var out: CFTypeRef?
        guard SecItemCopyMatching(q as CFDictionary, &out) == errSecSuccess, let d = out as? [String: Any],
              let user = d[kSecAttrAccount as String] as? String, let data = d[kSecValueData as String] as? Data,
              let pass = String(data: data, encoding: .utf8) else { return nil }
        return (user, pass)
    }
    static var user: String? {
        let q: [String: Any] = [kSecClass as String: kSecClassInternetPassword, kSecAttrServer as String: server,
                                kSecReturnAttributes as String: true, kSecMatchLimit as String: kSecMatchLimitOne]
        var out: CFTypeRef?
        guard SecItemCopyMatching(q as CFDictionary, &out) == errSecSuccess, let d = out as? [String: Any] else { return nil }
        return d[kSecAttrAccount as String] as? String
    }
    static func delete() {
        SecItemDelete([kSecClass as String: kSecClassInternetPassword, kSecAttrServer as String: server] as CFDictionary)
    }
}

struct SyncError: LocalizedError {
    let message: String
    var errorDescription: String? { message }
}

@MainActor
final class PowerSchoolSync: NSObject, WKNavigationDelegate {
    var site: URL { URL(string: "https://\(Keychain.server.isEmpty ? "powerschool.invalid" : Keychain.server)/guardian/")! }
    private let web: WKWebView
    private var waiting: CheckedContinuation<Void, Error>?
    private var loads = 0   // counts page loads, so a timeout only ends the load it was set for
    private(set) var running = false

    override init() {
        let config = WKWebViewConfiguration()   // the default, persistent data store keeps the session between syncs
        config.preferences.inactiveSchedulingPolicy = .none   // full speed even though it is never on screen
        web = WKWebView(frame: NSRect(x: 0, y: 0, width: 1280, height: 900), configuration: config)
        super.init()
        web.navigationDelegate = self
    }

    // MARK: page loading
    func webView(_ w: WKWebView, didFinish n: WKNavigation!) { finish(nil) }
    // A redirect (Google sends you on to /u/0/...) cancels the first load with -999; wait for the next page instead.
    func webView(_ w: WKWebView, didFail n: WKNavigation!, withError e: Error) { if !redirected(e) { finish(e) } }
    func webView(_ w: WKWebView, didFailProvisionalNavigation n: WKNavigation!, withError e: Error) { if !redirected(e) { finish(e) } }
    private func redirected(_ e: Error) -> Bool {
        let e = e as NSError
        return (e.domain == NSURLErrorDomain && e.code == NSURLErrorCancelled) || (e.domain == "WebKitErrorDomain" && e.code == 102)
    }
    private func finish(_ e: Error?) {
        guard let c = waiting else { return }
        waiting = nil
        if let e { c.resume(throwing: e) } else { c.resume() }
    }

    // Runs `start` (which begins a navigation) and waits for the page to finish, up to 40 seconds.
    private func navigate(_ start: @escaping () -> Void) async throws {
        try await withCheckedThrowingContinuation { (c: CheckedContinuation<Void, Error>) in
            waiting = c
            loads += 1
            let load = loads
            start()
            DispatchQueue.main.asyncAfter(deadline: .now() + 40) { [weak self] in
                guard let self, self.loads == load else { return }   // that page loaded; a later one is waiting
                self.finish(SyncError(message: "PowerSchool took too long to answer."))
            }
        }
    }
    private func open(_ path: String) async throws {
        let url = URL(string: path, relativeTo: site)!
        try await navigate { self.web.load(URLRequest(url: url)) }
    }
    private func js(_ code: String, _ args: [String: Any] = [:]) async throws -> Any? {
        try await web.callAsyncJavaScript(code, arguments: args, in: nil, contentWorld: .defaultClient)
    }
    private func onLoginPage() async throws -> Bool {
        (try await js("return !!document.querySelector('#fieldAccount, input[name=account]')") as? Bool) ?? false
    }

    // MARK: the sync
    func run() async throws -> [String: Any] {
        guard !running else { throw SyncError(message: "A sync is already running.") }
        running = true
        defer { running = false }
        guard let login = Keychain.load() else { throw SyncError(message: "Not signed in. Use Sign in… first.") }

        try await open("home.html")
        if try await onLoginPage() {
            try await navigate {
                Task { _ = try? await self.js("""
                    const a = document.querySelector('#fieldAccount, input[name=account]');
                    const p = document.querySelector('#fieldPassword, input[name=pw], input[type=password]');
                    a.value = u; a.dispatchEvent(new Event('input', { bubbles: true }));
                    p.value = pw; p.dispatchEvent(new Event('input', { bubbles: true }));
                    const b = document.querySelector('#btn-enter-sign-in, #btn-enter, button[type=submit], input[type=submit]');
                    b ? b.click() : a.form.submit();
                    """, ["u": login.user, "pw": login.pass]) }
            }
            if try await onLoginPage() { throw SyncError(message: "PowerSchool didn't accept the username or password.") }
            if web.url?.path.contains("home.html") != true { try await open("home.html") }
        }

        // Current classes and their letter grades.
        let rows = (try await js("""
            const out = [], seen = new Set();
            for (const a of document.querySelectorAll('a[href*="scores.html"]')) {
              const tr = a.closest('tr'); if (!tr) continue;
              const cell = [...tr.cells].find(td => /Email/.test(td.innerText));
              const course = cell ? cell.innerText.split('\\n')[0].replace(/\\s+/g, ' ').trim() : '';
              const letter = a.innerText.trim();
              if (!course || seen.has(course)) continue;
              seen.add(course);
              out.push({ course, letter: /^[A-F][+-]?$/.test(letter) ? letter : null, href: a.getAttribute('href') });
            }
            return out;
            """) as? [[String: Any]]) ?? []
        if rows.isEmpty { throw SyncError(message: "Signed in, but found no classes on the Grades page.") }

        // Summative scores for each graded class.
        var courses: [[String: Any]] = []
        for row in rows {
            var c = row
            if row["letter"] is String, let href = row["href"] as? String {
                try await open(href)
                c["summatives"] = (try await js("""
                    for (let i = 0; i < 60; i++) {
                      const rows = [...document.querySelectorAll('table tr')].filter(tr => /^\\d{2}\\/\\d{2}\\/\\d{4}$/.test((tr.cells[0]?.innerText || '').trim()));
                      if (rows.length || i > 24) return rows.map(tr => {
                        const c = [...tr.cells].map(td => td.innerText.replace(/\\s+/g, ' ').trim());
                        const [m, d, y] = c[0].split('/'); const sc = (c[c.length - 3] || '').match(/^([\\d.]+)\\/([\\d.]+)$/);
                        return { date: `${y}-${m}-${d}`, category: c[1], name: c[2], pct: sc ? Math.round(sc[1] / sc[2] * 1000) / 10 : null };
                      }).filter(r => /summative/i.test(r.category) && r.pct != null).map(({ category, ...r }) => r);
                      await new Promise(r => setTimeout(r, 250));
                    }
                    return [];
                    """) as? [[String: Any]]) ?? []
            }
            c.removeValue(forKey: "href")
            courses.append(c)
        }

        // The A-D rotation matrix: which days each class meets.
        try await open("myschedulematrix.html")
        let matrix = (try await js("""
            const out = {};
            const expand = s => s.split(',').flatMap(p => { const [a, b] = p.split('-'); if (!b) return [a];
              const L = 'ABCDEFGH'; return L.slice(L.indexOf(a), L.indexOf(b) + 1).split(''); });
            for (const td of document.querySelectorAll('table td')) {
              const t = td.innerText; const m = t.match(/\\b[\\w]+\\(([A-H](?:[-,][A-H])*)\\)/);
              if (!m) continue;
              const course = t.split('\\n')[0].replace(/\\s+/g, ' ').trim();
              if (course) out[course] = [...new Set([...(out[course] || []), ...expand(m[1])])].sort();
            }
            return out;
            """) as? [String: Any]) ?? [:]

        return ["account": login.user, "courses": courses, "matrix": matrix]
    }
}

// MARK: - Google Classroom sync
// Google blocks apps that type passwords into its sign-in page, so you sign in once in a Study HUD
// window and the app keeps that session (like a browser). A hidden browser then reads the Classroom
// To-do list. If the session has ended, the sync reports it and asks you to sign in again.

let safariUA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Safari/605.1.15"

// A browser that never shows: it loads a signed-in page and reads it with JavaScript.
@MainActor
class HiddenBrowser: NSObject, WKNavigationDelegate {
    let web: WKWebView
    let name: String
    private var waiting: CheckedContinuation<Void, Error>?
    private var loads = 0   // counts page loads, so a timeout only ends the load it was set for
    var running = false

    struct SignedOut: Error {}

    init(name: String) {
        self.name = name
        let config = WKWebViewConfiguration()
        config.preferences.inactiveSchedulingPolicy = .none
        web = WKWebView(frame: NSRect(x: 0, y: 0, width: 1280, height: 1000), configuration: config)
        web.customUserAgent = safariUA
        super.init()
        web.navigationDelegate = self
    }

    // Classroom only draws its list when the page thinks it is on screen. So the browser sits inside the
    // HUD's own always-on-screen window: fully transparent, underneath the pill, never taking clicks.
    func attach(to container: NSView) {
        guard web.superview == nil else { return }
        web.alphaValue = 0
        web.frame = NSRect(x: 0, y: 0, width: 1280, height: 1000)
        container.addSubview(web, positioned: .below, relativeTo: nil)
    }
    func webView(_ w: WKWebView, didFinish n: WKNavigation!) { finish(nil) }
    // A redirect (Google sends you on to /u/0/...) cancels the first load with -999; wait for the next page instead.
    func webView(_ w: WKWebView, didFail n: WKNavigation!, withError e: Error) { if !redirected(e) { finish(e) } }
    func webView(_ w: WKWebView, didFailProvisionalNavigation n: WKNavigation!, withError e: Error) { if !redirected(e) { finish(e) } }
    private func redirected(_ e: Error) -> Bool {
        let e = e as NSError
        return (e.domain == NSURLErrorDomain && e.code == NSURLErrorCancelled) || (e.domain == "WebKitErrorDomain" && e.code == 102)
    }
    private func finish(_ e: Error?) {
        guard let c = waiting else { return }
        waiting = nil
        if let e { c.resume(throwing: e) } else { c.resume() }
    }
    func open(_ url: String) async throws {
        try await withCheckedThrowingContinuation { (c: CheckedContinuation<Void, Error>) in
            waiting = c
            loads += 1
            let load = loads
            web.load(URLRequest(url: URL(string: url)!))
            DispatchQueue.main.asyncAfter(deadline: .now() + 40) { [weak self] in
                guard let self, self.loads == load else { return }
                self.finish(SyncError(message: "\(self.name) took too long to answer."))
            }
        }
    }
    // A page that navigates away mid-script never answers, so give up after a while.
    func js(_ code: String, timeout: Double = 60) async throws -> Any? {
        try await withThrowingTaskGroup(of: Any?.self) { g in
            g.addTask { @MainActor in try await self.web.callAsyncJavaScript(code, arguments: [:], in: nil, contentWorld: .defaultClient) }
            g.addTask {
                try await Task.sleep(nanoseconds: UInt64(timeout * 1e9))
                throw SyncError(message: "\(self.name) stopped answering (the page moved on).")
            }
            defer { g.cancelAll() }
            return try await g.next() ?? nil
        }
    }
}

final class ClassroomSync: HiddenBrowser {
    init() { super.init(name: "Classroom") }

    func run() async throws -> [String: Any] {
        guard !running else { throw SyncError(message: "A sync is already running.") }
        running = true
        defer { running = false }
        try await open("https://classroom.google.com/a/not-turned-in/all")
        if web.url?.host?.contains("accounts.google.com") == true { throw SignedOut() }
        let items = (try await js("""
            const sleep = ms => new Promise(r => setTimeout(r, ms));
            for (let i = 0; i < 60 && !document.querySelector('a[href*="/details"]') && !/No work|Woohoo|nothing/i.test(document.body.innerText); i++) await sleep(250);
            const skip = /^(assignment|quiz_assignment|question|book|material|more_vert|More options|Learn with Gemini|Missing|Turned in|Assigned)$/i;
            const items = new Map();
            const read = () => { for (const a of document.querySelectorAll('a[href*="/details"]')) {
              const href = a.getAttribute('href'); if (items.has(href)) continue;
              const lines = (a.closest('li') || a.parentElement).innerText.split('\\n').map(l => l.trim()).filter(l => l && !skip.test(l));
              if (lines.length >= 2) items.set(href, { title: lines[0], course: lines[1], due: lines[2] && !/^Posted\\b/i.test(lines[2]) ? lines[2] : null });
            } };
            // The To-do sections (No due date, This week, Next week, Later) open one at a time: open each, read it.
            // Only those toggles; Google's own menus also carry aria-expanded.
            const toggles = () => [...document.querySelectorAll('[aria-expanded]')].filter(e => /keyboard_arrow_(down|up)/.test(e.innerText || ''));
            read();
            for (let k = 0; k < toggles().length; k++) { const t = toggles()[k]; if (t.getAttribute('aria-expanded') === 'false') { t.click(); await sleep(900); } read(); }
            const who = document.querySelector('a[aria-label*="Google Account"]')?.getAttribute('aria-label') || '';
            return { items: [...items.values()], account: (who.match(/\\(([^)]+@[^)]+)\\)/) || [])[1] || null,
                     page: location.href + ' | ' + document.visibilityState + ' | ' + document.body.innerText.replace(/\\s+/g, ' ').slice(0, 300) };
            """) as? [String: Any]) ?? [:]
        return items
    }
}

// AP Classroom keeps its College Board sign-in in the page's own storage. The hidden browser opens AP
// Classroom and asks its API (the one the page itself uses) for each course's assignments and due dates.
final class APClassroomSync: HiddenBrowser {
    init() { super.init(name: "AP Classroom") }

    func run(_ script: String = apcScript) async throws -> [String: Any] {
        guard !running else { throw SyncError(message: "A sync is already running.") }
        running = true
        defer { running = false }
        // The app itself bounces through College Board's sign-on, so open a plain file on the same site
        // instead: it shares the page's storage (where the sign-in lives) and never redirects.
        try await open("https://apclassroom.collegeboard.org/robots.txt")
        if CommandLine.arguments.contains("--apcprobe") { FileHandle.standardError.write("apc: at \(web.url?.absoluteString ?? "-")\n".data(using: .utf8)!) }
        let r = (try await js(script) as? [String: Any]) ?? [:]
        if r["signedOut"] as? Bool == true { throw SignedOut() }
        return r
    }
}
let apcScript = #"""
    const GQL = 'https://apc-api-production.collegeboard.org/fym/graphql';
    const REFRESH = 'https://am-accounts-production.collegeboard.org/token/refresh/';
    // 25 has no name in the API; its only item is "Review Ch 1 Limits", so it's the Calc course.
    const APC_NAMES = { 8: 'AP Computer Science A', 12: 'AP English Language', 13: 'AP English Literature', 25: 'AP Calculus', 30: 'AP Psychology' };
    // The sign-in tokens live in the page's storage under College Board's account_* keys.
    const token = name => { for (const st of [localStorage, sessionStorage]) for (const k of Object.keys(st))
      if (k.includes(name)) { const m = String(st.getItem(k)).match(/eyJ[\w.-]+/); if (m) return m[0]; } return null; };
    const exp = t => { try { return JSON.parse(atob(t.split('.')[1].replace(/-/g, '+').replace(/_/g, '/'))).exp * 1000; } catch { return 0; } };
    let access = token('account_access_token');
    const refresh = token('account_refresh_token');
    const page = location.href;
    if (!access || exp(access) < Date.now() + 60e3) {
      if (!refresh) return { signedOut: true, page };
      const j = await fetch(REFRESH, { method: 'POST', headers: { Authorization: 'Bearer ' + refresh } }).then(r => r.json()).catch(() => ({}));
      if (!j.access_token) return { signedOut: true, page };
      access = j.access_token;
    }
    const gql = (query, variables = {}) => fetch(GQL, { method: 'POST', headers: { Authorization: 'Bearer ' + access, 'Content-Type': 'application/json' },
      body: JSON.stringify({ query, variables }) }).then(r => r.json()).catch(e => ({ errors: [String(e)] }));
    const me = String(JSON.parse(atob(access.split('.')[1].replace(/-/g, '+').replace(/_/g, '/'))).identity?.am_user_id || '');
    // Course ids are small numbers (13 is AP Lit); ask for each and keep the ones this account is in.
    const Q = `query($id: String!) { studentSubject(id: $id) { id assignments { title initId status dueAt startsAt } } }`;
    const ids = Array.from({ length: 60 }, (_, i) => String(i + 1));
    const got = await Promise.all(ids.map(id => gql(Q, { id }).then(r => ({ id, r }))));
    const courses = [], items = [];
    const local = iso => { const d = new Date(iso), p = n => String(n).padStart(2, '0');
      return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}T${p(d.getHours())}:${p(d.getMinutes())}`; };
    for (const { id, r } of got) {
      const subj = r?.data?.studentSubject;
      if (!subj || !(subj.assignments || []).length) continue;
      const course = APC_NAMES[id] || `AP course ${id}`;
      courses.push(course);
      for (const a of subj.assignments) {
        if (a.status === 'locked') continue;   // closed by the teacher
        if (a.dueAt && new Date(a.dueAt) < Date.now() - 2 * 864e5) continue;   // long past due
        // The list doesn't say what you've done; an assignment you haven't started has no answers saved.
        const r = await gql(`query($a: String!, $s: String!) { assignment(assignmentId: $a) { studentResponses(studentId: $s) } }`, { a: a.initId, s: me });
        const saved = r?.data?.assignment?.studentResponses;
        if (saved == null || Object.keys(typeof saved === 'string' ? JSON.parse(saved || '{}') : saved).length) continue;
        items.push({ title: a.title, course, due: a.dueAt ? local(a.dueAt) : null, status: a.status });
      }
    }
    return { items, courses, page };
    """#

// Sign-in as a sheet on the Settings window: it can't get lost behind other windows or on another
// Space. It closes itself once the signed-in page loads (done(url) says when), or with Cancel.
@MainActor
final class SignInSheet: NSObject, WKNavigationDelegate {
    let window: NSWindow
    private let web: WKWebView
    private let done: (URL) -> Bool
    private let ready: String?
    private var sawLogin = false   // went through a sign-in form; landing back on the site means done   // optional page check, for sites that look the same signed in and out
    private var poll: Timer?

    init(url: String, note text: String, ready: String? = nil, done: @escaping (URL) -> Bool) {
        self.done = done
        self.ready = ready
        let size = NSSize(width: 520, height: 720)
        web = WKWebView(frame: NSRect(x: 0, y: 48, width: size.width, height: size.height - 48), configuration: WKWebViewConfiguration())
        web.customUserAgent = safariUA
        web.autoresizingMask = []  // resizing the cropped window must not reflow the page
        let cancel = NSButton(title: "Cancel", target: nil, action: nil)
        cancel.bezelStyle = .rounded
        cancel.keyEquivalent = "\u{1b}"   // Escape
        cancel.frame = NSRect(x: size.width - 100, y: 10, width: 88, height: 30)
        cancel.autoresizingMask = [.minXMargin, .maxYMargin]
        let note = NSTextField(labelWithString: text)
        note.frame = NSRect(x: 14, y: 16, width: 380, height: 18)
        note.textColor = .secondaryLabelColor
        let box = NSView(frame: NSRect(origin: .zero, size: size))
        box.addSubview(web); box.addSubview(cancel); box.addSubview(note)
        window = NSWindow(contentRect: box.frame, styleMask: [.titled], backing: .buffered, defer: false)
        super.init()
        window.contentView = box
        window.isReleasedWhenClosed = false
        cancel.target = self
        cancel.action = #selector(close)
        web.navigationDelegate = self
        web.load(URLRequest(url: URL(string: url)!))
        if ready != nil {
            poll = Timer.scheduledTimer(withTimeInterval: 1.5, repeats: true) { [weak self] _ in
                MainActor.assumeIsolated { self?.check() }
            }
        }
    }
    func webView(_ w: WKWebView, didFinish n: WKNavigation!) { check() }
    private func check() {
        guard let u = web.url else { return }
        if u.path.contains("login") || u.host?.contains("idp.") == true { sawLogin = true }
        guard done(u) else { return }
        guard let ready, !sawLogin else { close(); return }
        web.evaluateJavaScript(ready) { [weak self] r, _ in if r as? Bool == true { self?.close() } }
    }
    @objc func close() {
        poll?.invalidate(); poll = nil
        if let parent = window.sheetParent { parent.endSheet(window) } else { window.close() }
    }
}

final class AppDelegate: NSObject, NSApplicationDelegate, WKScriptMessageHandler, WKNavigationDelegate, NSWindowDelegate {
    var panel: Panel!
    var web: HUDWebView!
    var status: NSStatusItem!
    // Virtual page viewport, independent of the tightly fitted native window.
    var layoutFrame = NSRect.zero
    var hudVisible = true
    var card = NSRect.zero        // the pill, page coordinates as sent by the page
    var popovers: [NSRect] = []   // open popovers, page coordinates
    var inside = false
    var lastPointer = NSPoint(x: -1, y: -1)
    // Live pill dragging; the native window stays tightly fitted to page geometry.
    var dragPress = NSPoint.zero         // where the drag began, screen coordinates
    var dragFrac: CGFloat = 0.5          // where along its length the pill was grabbed (Agent HUD's dragGrabFraction)
    var dragGeneration = 0
    var dragEdge = "right"
    var dragDelta = NSPoint.zero         // screen-space offset from the press

    func applicationDidFinishLaunching(_ note: Notification) {
        let config = WKWebViewConfiguration()
        if CommandLine.arguments.contains("--geometrytest") { config.websiteDataStore = .nonPersistent() }
        config.userContentController.add(self, name: "hud")
        let frame = (NSScreen.main ?? NSScreen.screens[0]).visibleFrame
        layoutFrame = frame
        web = HUDWebView(frame: NSRect(origin: .zero, size: frame.size), configuration: config)
        web.setValue(false, forKey: "drawsBackground")
        web.underPageBackgroundColor = .clear
        web.navigationDelegate = self
        web.autoresizingMask = []  // resizing the cropped window must not reflow the page

        panel = Panel(contentRect: NSRect(origin: frame.origin, size: NSSize(width: 1, height: 1)), styleMask: [.borderless, .nonactivatingPanel], backing: .buffered, defer: false)
        let container = NSView(frame: NSRect(x: 0, y: 0, width: 1, height: 1))
        container.wantsLayer = true
        container.layer?.masksToBounds = true
        container.autoresizingMask = [.width, .height]
        web.frame = NSRect(origin: .zero, size: frame.size)
        container.addSubview(web)
        panel.contentView = container
        panel.isOnPill = { [weak self] p in self.map { $0.toView($0.card).contains(p) } ?? false }
        panel.onDragStart = { [weak self] p in self?.beginDrag(at: p) }
        panel.onDragMove = { [weak self] dx, dy in self?.moveDrag(dx, dy) }
        panel.onDragEnd = { [weak self] in self?.endDrag() }
        panel.isFloatingPanel = true
        panel.level = .floating
        panel.collectionBehavior = [.canJoinAllSpaces, .fullScreenAuxiliary, .stationary]
        panel.backgroundColor = .clear
        panel.isOpaque = false
        panel.hasShadow = false          // the page draws its own shadows
        panel.hidesOnDeactivate = false
        panel.animationBehavior = .none  // like Agent HUD: the window never animates, only its contents
        panel.ignoresMouseEvents = true
        // Remain ordered out until the page reports its first real content bounds.

        // Relayout the virtual viewport when the Dock, menu bar or displays change.
        NotificationCenter.default.addObserver(forName: NSApplication.didChangeScreenParametersNotification, object: nil, queue: .main) { [weak self] _ in
            guard let self else { return }
            self.layoutFrame = (self.panel.screen ?? NSScreen.main ?? NSScreen.screens[0]).visibleFrame
            self.web.setFrameSize(self.layoutFrame.size)
            self.fitPanelToContent()
        }
        Timer.scheduledTimer(withTimeInterval: 1.0 / 60, repeats: true) { [weak self] _ in
            guard let self, self.fakePointer == nil else { return }
            self.trackMouse(NSEvent.mouseLocation)
        }
        // A click anywhere outside the HUD (another app, or the settings window) closes a pinned popover.
        NSEvent.addGlobalMonitorForEvents(matching: [.leftMouseDown, .rightMouseDown]) { [weak self] _ in
            self?.web.evaluateJavaScript("window.hudOutside && hudOutside()")
        }
        NSEvent.addLocalMonitorForEvents(matching: [.leftMouseDown, .rightMouseDown]) { [weak self] e in
            if let self, e.window !== self.panel { self.web.evaluateJavaScript("window.hudOutside && hudOutside()") }
            return e
        }
        if CommandLine.arguments.contains("--selftest") { DispatchQueue.main.asyncAfter(deadline: .now() + 4) { self.selfTest() } }
        if CommandLine.arguments.contains("--settings") || CommandLine.arguments.contains("--sync") { DispatchQueue.main.asyncAfter(deadline: .now() + 1.5) { self.openSettings() } }
        if let i = CommandLine.arguments.firstIndex(of: "--apcprobe"), i + 1 < CommandLine.arguments.count {
            // run a script file on AP Classroom's page, log what it returns
            let script = (try? String(contentsOfFile: CommandLine.arguments[i + 1], encoding: .utf8)) ?? "return 'no script'"
            DispatchQueue.main.asyncAfter(deadline: .now() + 2) {
                if let container = self.panel.contentView { self.apClassroom.attach(to: container) }
                Task { @MainActor in
                    var out: String
                    do {
                        let r = try await self.apClassroom.run(script)
                        out = String(data: (try? JSONSerialization.data(withJSONObject: r, options: [.prettyPrinted, .sortedKeys])) ?? Data(), encoding: .utf8) ?? "?"
                    } catch { out = "error: \(error)" }
                    try? (out + "\nurl=\(self.apClassroom.web.url?.absoluteString ?? "-")\n").write(toFile: "/tmp/study-hud-apcprobe.log", atomically: true, encoding: .utf8)
                    NSApp.terminate(nil)
                }
            }
        }
        if CommandLine.arguments.contains("--googletest") {   // open the Google sign-in window, report what it shows
            DispatchQueue.main.asyncAfter(deadline: .now() + 2) {
                self.openSettings(); self.googleSignIn()
                DispatchQueue.main.asyncAfter(deadline: .now() + 6) {
                    let w = self.googleSheet?.window
                    let line = "googleWin=\(w != nil) visible=\(w?.isVisible ?? false) key=\(w?.isKeyWindow ?? false) frame=\(w.map { NSStringFromRect($0.frame) } ?? "-") url=\((w?.contentView as? WKWebView)?.url?.absoluteString ?? "-")\n"
                    try? line.write(toFile: "/tmp/study-hud-googletest.log", atomically: true, encoding: .utf8)
                }
            }
        }
        if CommandLine.arguments.contains("--minitest") {   // minimise the settings window, then reopen it both ways
            DispatchQueue.main.asyncAfter(deadline: .now() + 2) {
                self.openSettings()
                DispatchQueue.main.asyncAfter(deadline: .now() + 1.5) {
                    self.settingsWin?.miniaturize(nil)
                    DispatchQueue.main.asyncAfter(deadline: .now() + 1.5) {
                        let mini = self.settingsWin?.isMiniaturized == true
                        self.openSettings()   // Settings… / ⌘,
                        DispatchQueue.main.asyncAfter(deadline: .now() + 1.5) {
                            let back1 = self.settingsWin?.isVisible == true && self.settingsWin?.isMiniaturized == false
                            self.settingsWin?.miniaturize(nil)
                            DispatchQueue.main.asyncAfter(deadline: .now() + 1.5) {
                                _ = self.applicationShouldHandleReopen(NSApp, hasVisibleWindows: true)   // Dock icon click
                                DispatchQueue.main.asyncAfter(deadline: .now() + 1.5) {
                                    let back2 = self.settingsWin?.isVisible == true && self.settingsWin?.isMiniaturized == false
                                    try? "minimised=\(mini) reopenedFromMenu=\(back1) reopenedFromDock=\(back2)\n"
                                        .write(toFile: "/tmp/study-hud-minitest.log", atomically: true, encoding: .utf8)
                                    NSApp.terminate(nil)
                                }
                            }
                        }
                    }
                }
            }
        }
        if CommandLine.arguments.contains("--dragtest") { DispatchQueue.main.asyncAfter(deadline: .now() + 4) { self.dragTest() } }
        if let i = CommandLine.arguments.firstIndex(of: "--ticktest"), let secs = CommandLine.arguments.dropFirst(i + 1).first.flatMap(Int.init) {
            tickTest(seconds: secs)
        }

        buildStatusItem()
        ensureServer { [weak self] in
            self?.web.load(URLRequest(url: base.appendingPathComponent("widget")))
            if CommandLine.arguments.contains("--geometrytest") {
                DispatchQueue.main.asyncAfter(deadline: .now() + 4) { self?.geometryTest() }
            } else {
                DispatchQueue.main.asyncAfter(deadline: .now() + 8) { self?.scheduleSync() }
            }
        }
    }

    func beginDrag(at press: NSPoint) {
        dragGeneration += 1
        panel.level = NSWindow.Level(rawValue: NSWindow.Level.popUpMenu.rawValue + 1)
        dragDelta = .zero
        dragPress = press
        let f = layoutFrame, pressPage = NSPoint(x: press.x - f.minX, y: f.maxY - press.y)
        let vertical = card.height >= card.width
        dragFrac = vertical ? (pressPage.y - card.minY) / card.height : (pressPage.x - card.minX) / card.width
        dragEdge = vertical ? (card.midX < f.width / 2 ? "left" : "right") : (card.midY < f.height / 2 ? "top" : "bottom")
        // Keep the live WebKit pill visible throughout the gesture. Snapshot swaps can
        // capture clipped/transparent content and leave nothing visible during reorientation.
        web.evaluateJavaScript("hudDragStart()")
    }

    // Which edge the pointer asks for. Joining a perpendicular edge needs the pointer within 60pt of it;
    // leaving the top or bottom for a side also needs it out of a 120pt band, so a pointer sitting in a
    // corner (near both edges) can't flip the pill back and forth.
    func wantedEdge() -> String {
        let vis = (panel.screen ?? NSScreen.main!).visibleFrame
        let p = NSPoint(x: dragPress.x + dragDelta.x, y: dragPress.y + dragDelta.y)
        let near: CGFloat = 60, band: CGFloat = 120
        if dragEdge == "left" || dragEdge == "right" {
            if p.y > vis.maxY - near { return "top" }
            if p.y < vis.minY + near { return "bottom" }
            return p.x < vis.midX ? "left" : "right"
        }
        let inBand = dragEdge == "top" ? p.y > vis.maxY - band : p.y < vis.minY + band
        if !inBand && p.x < vis.minX + near { return "left" }
        if !inBand && p.x > vis.maxX - near { return "right" }
        return p.y > vis.midY ? "top" : "bottom"
    }

    func moveDrag(_ dx: CGFloat, _ dy: CGFloat) {
        dragDelta = NSPoint(x: dx, y: dy)
        let edge = wantedEdge()
        dragEdge = edge
        let p = NSPoint(x: dragPress.x + dx - layoutFrame.minX,
                        y: layoutFrame.maxY - (dragPress.y + dy))
        // Commands execute in order in WebKit. Geometry is reported in the same turn,
        // including on release, with no delayed callback that can hide the next drag.
        web.evaluateJavaScript("hudDragOrient('\(edge)', \(p.x), \(p.y), \(dragFrac))")
    }

    // Other apps' small windows floating above the HUD (another HUD on the same edge), screen coordinates.
    func obstacles() -> [NSRect] {
        let vis = (panel.screen ?? NSScreen.main!).visibleFrame, top = NSScreen.screens[0].frame.maxY
        let me = Int(ProcessInfo.processInfo.processIdentifier)
        let list = CGWindowListCopyWindowInfo([.optionOnScreenOnly, .excludeDesktopElements], kCGNullWindowID) as? [[String: Any]] ?? []
        return list.compactMap { w in
            guard (w[kCGWindowOwnerPID as String] as? Int) != me, (w[kCGWindowLayer as String] as? Int ?? 0) > panel.level.rawValue,
                  (w[kCGWindowAlpha as String] as? Double ?? 1) > 0.1,
                  let d = w[kCGWindowBounds as String] as? NSDictionary, let b = CGRect(dictionaryRepresentation: d) else { return nil }
            let r = NSRect(x: b.minX, y: top - b.maxY, width: b.width, height: b.height)
            return r.intersects(vis) && r.width < vis.width / 2 && r.height < vis.height / 2 ? r : nil
        }
    }

    // Slide a docked rectangle along its edge, the shorter way, until it clears every obstacle.
    func clearOfObstacles(_ r: NSRect, edge: String) -> NSRect {
        let vis = (panel.screen ?? NSScreen.main!).visibleFrame, gap: CGFloat = 8, blocks = obstacles()
        var r = r
        for _ in 0..<6 {
            guard let o = blocks.first(where: { $0.intersects(r.insetBy(dx: 1, dy: 1)) }) else { break }
            if edge == "left" || edge == "right" {
                let down = o.minY - gap - r.height, up = o.maxY + gap
                let ok = [down, up].filter { $0 >= vis.minY && $0 + r.height <= vis.maxY }
                guard let y = ok.min(by: { abs($0 - r.minY) < abs($1 - r.minY) }) else { break }
                r.origin.y = y
            } else {
                let left = o.minX - gap - r.width, right = o.maxX + gap
                let ok = [left, right].filter { $0 >= vis.minX && $0 + r.width <= vis.maxX }
                guard let x = ok.min(by: { abs($0 - r.minX) < abs($1 - r.minX) }) else { break }
                r.origin.x = x
            }
        }
        return r
    }

    func endDrag() {
        panel.level = .floating
        // Read the current page geometry after all queued moves, rather than using
        // stale native dimensions when the mouse is released during an edge change.
        let generation = dragGeneration
        web.evaluateJavaScript("hudDrop(); emitGeometry(); (() => { const r = $('pill').getBoundingClientRect(); return [r.x, r.y, r.width, r.height]; })()") { [weak self] value, _ in
            guard let self, !self.panel.dragging, self.dragGeneration == generation,
                  let a = value as? [Double], a.count == 4 else { return }
            let rect = self.screenRect(NSRect(x: a[0], y: a[1], width: a[2], height: a[3]))
            let clear = self.clearOfObstacles(rect, edge: self.dragEdge)
            if clear != rect {
                self.web.evaluateJavaScript("hudDropAt(\(clear.minX - self.layoutFrame.minX), \(self.layoutFrame.maxY - clear.maxY))")
            }
        }
    }

    /// Convert virtual top-left page coordinates to AppKit screen coordinates.
    func screenRect(_ r: NSRect) -> NSRect {
        NSRect(x: layoutFrame.minX + r.minX, y: layoutFrame.maxY - r.maxY,
               width: r.width, height: r.height)
    }

    func toView(_ r: NSRect) -> NSRect {
        screenRect(r).offsetBy(dx: -panel.frame.minX, dy: -panel.frame.minY)
    }

    func fitPanelToContent() {
        // Geometry arrives as one snapshot, so a relocated pill is never unioned with
        // a stale popover on the opposite side of the screen.
        let rects = ([card] + popovers).filter {
            $0.minX.isFinite && $0.minY.isFinite && $0.width.isFinite && $0.height.isFinite && !$0.isEmpty
        }
        guard hudVisible, !rects.isEmpty else { panel.orderOut(nil); return }
        let bounds = rects.dropFirst().reduce(rects[0]) { $0.union($1) }
        let frame = screenRect(bounds).insetBy(dx: -32, dy: -32).intersection(layoutFrame).integral
        guard !frame.isNull, !frame.isEmpty else { panel.orderOut(nil); return }
        // Keep the page's viewport and CSS coordinates unchanged inside a clipping view.
        // Only the native window changes size; it no longer covers unrelated apps.
        NSAnimationContext.runAnimationGroup { context in
            context.duration = 0
            panel.setFrame(frame, display: false)
            web.frame = NSRect(x: layoutFrame.minX - frame.minX, y: layoutFrame.minY - frame.minY,
                               width: layoutFrame.width, height: layoutFrame.height)
        }
        if !panel.isVisible { panel.orderFrontRegardless() }
    }

    // Only the pill and open popovers take the mouse; everywhere else, clicks reach the app underneath.
    var fakePointer: NSPoint?   // set by the self-test

    func trackMouse(_ p: NSPoint) {
        let f = panel.frame
        let local = NSPoint(x: p.x - f.minX, y: p.y - f.minY)
        let hit = panel.dragging || toView(card).contains(local) || popovers.contains { toView($0).contains(local) }
        if panel.ignoresMouseEvents == hit { panel.ignoresMouseEvents = !hit }
        if hit != inside {
            inside = hit
            web.evaluateJavaScript("window.hudHover && hudHover(\(hit))")
        }
        if hit && !panel.dragging && (abs(local.x - lastPointer.x) >= 1 || abs(local.y - lastPointer.y) >= 1) {
            lastPointer = local
            web.evaluateJavaScript("window.hudPointer && hudPointer(\(Int(p.x - layoutFrame.minX)), \(Int(layoutFrame.maxY - p.y)))")
        }
    }

    // MARK: messages from widget.html
    func userContentController(_ c: WKUserContentController, didReceive message: WKScriptMessage) {
        guard let body = message.body as? [String: Any], let type = body["type"] as? String else { return }
        if message.name == "app" {
            switch type {
            case "hud-size":
                if let value = body["value"] as? Double, value.isFinite {
                    web.evaluateJavaScript("hudSetSize(\(min(150, max(75, value))))")
                }
            case "ps-signin": promptLogin()
            case "ps-sync": syncPowerSchool()
            case "ps-signout": Keychain.delete(); report(ok: true, message: "Signed out. The saved login was removed from the Keychain.", account: nil)
            case "gc-signin": googleSignIn()
            case "gc-sync": syncClassroom()
            case "apc-signin": apcSignIn()
            case "apc-sync": syncAPClassroom()
            default: break
            }
            return
        }
        let rect = { (a: [Double]) in NSRect(x: a[0], y: a[1], width: a[2], height: a[3]) }
        switch type {
        case "geometry":
            guard let a = body["card"] as? [Double], a.count == 4 else { return }
            card = rect(a)
            popovers = (body["popovers"] as? [[Double]] ?? []).filter { $0.count == 4 }.map(rect)
            fitPanelToContent()
        case "card":
            if let x = body["x"] as? Double, let y = body["y"] as? Double, let w = body["w"] as? Double, let h = body["h"] as? Double {
                card = NSRect(x: x, y: y, width: w, height: h)
                fitPanelToContent()
            }
        case "popovers":
            popovers = (body["rects"] as? [[Double]] ?? []).filter { $0.count == 4 }.map(rect)
            fitPanelToContent()
        case "icons":   // {key: [symbol, hex, size]} -> hudIcons({key: dataURL})
            var out: [String: String] = [:]
            for (key, spec) in body["want"] as? [String: [Any]] ?? [:] {
                if let name = spec.first as? String, let hex = spec.dropFirst().first as? String,
                   let url = symbolDataURL(name, hex: hex, size: CGFloat(spec.dropFirst(2).first as? Double ?? 32)) { out[key] = url }
            }
            if let json = try? JSONSerialization.data(withJSONObject: out), let s = String(data: json, encoding: .utf8) {
                web.evaluateJavaScript("window.hudIcons && hudIcons(\(s))")
            }
        case "open":
            guard let s = body["url"] as? String, let url = URL(string: s) else { break }
            if url.host == base.host && url.port == port { openSettings() } else { NSWorkspace.shared.open(url) }
        default: break
        }
    }

    // A geometry regression test with an ephemeral WebKit store and no account sync.
    // Launch the test bundle against an isolated server with --geometrytest --port N.
    func geometryTest() {
        fakePointer = NSPoint(x: -10000, y: -10000)
        var failures: [String] = []
        var observations: [String] = []
        func check(_ value: Bool, _ message: String) { if !value { failures.append(message) } }
        func inspect(_ label: String) {
            let frame = self.panel.frame
            observations.append("\(label): window=\(NSStringFromRect(frame)) viewport=\(NSStringFromRect(self.layoutFrame))")
            check(self.card.width > 0 && self.card.height > 0, "\(label): missing pill")
            check(self.panel.isVisible, "\(label): window not visible")
            check(frame.width * frame.height < self.layoutFrame.width * self.layoutFrame.height * 0.8,
                  "\(label): window still covers most of screen")
            let visibleCard = self.screenRect(self.card).intersection(self.layoutFrame)
            check(frame.insetBy(dx: -1, dy: -1).contains(visibleCard), "\(label): pill clipped")
            for pop in self.popovers {
                check(frame.insetBy(dx: -1, dy: -1).contains(self.screenRect(pop).intersection(self.layoutFrame)),
                      "\(label): popover clipped")
            }
            check(self.web.frame.size == self.layoutFrame.size, "\(label): web viewport changed")
            let local = self.toView(self.card)
            let converted = self.panel.convertPoint(toScreen: NSPoint(x: local.midX, y: local.midY))
            let screen = self.screenRect(self.card)
            check(abs(converted.x - screen.midX) < 0.1 && abs(converted.y - screen.midY) < 0.1,
                  "\(label): pointer coordinates shifted")
        }
        let steps: [(String, String)] = [
            ("small right", "hudSetSize(75); hudPlace('right', 0.2)"),
            ("large left", "hudSetSize(150); hudPlace('left', 0.4)"),
            ("large top", "hudPlace('top', 0.5)"),
            ("large popover", "show('panel', null)"),
            ("right", "hudSetSize(100); hudPlace('right', 0.2)"),
            ("left", "hudPlace('left', 0.4)"),
            ("top", "hudPlace('top', 0.5)"),
            ("bottom", "hudPlace('bottom', 0.3)"),
            ("right before expand", "hudPlace('right', 0.2)"),
            ("expanded", "show('panel', null)"),
            ("collapsed", "show(null)"),
            ("drag layout", "hudDragStart(); hudDragTo(600, 250)"),
            ("drop", "hudDropAt(600, 250)")
        ]
        func run(_ index: Int) {
            guard index < steps.count else {
                self.hudVisible = false
                self.fitPanelToContent()
                check(!self.panel.isVisible, "hide left a transparent window visible")
                self.fitPanelToContent()
                check(!self.panel.isVisible, "geometry update overrode user hide")
                self.hudVisible = true
                self.fitPanelToContent()
                inspect("shown again")
                let result = (failures.isEmpty ? "PASS" : "FAIL") + "\n" +
                    observations.joined(separator: "\n") + "\n" + failures.joined(separator: "\n") + "\n"
                if let path = ProcessInfo.processInfo.environment["STUDY_HUD_TEST_RESULT"] {
                    try? result.write(toFile: path, atomically: true, encoding: .utf8)
                }
                NSApp.terminate(nil)
                return
            }
            let (label, script) = steps[index]
            self.web.evaluateJavaScript(script) { _, error in
                check(error == nil, "\(label): JavaScript failed")
                DispatchQueue.main.asyncAfter(deadline: .now() + 0.75) {
                    inspect(label)
                    self.web.evaluateJavaScript("[innerWidth, innerHeight]") { value, _ in
                        let size = value as? [Double] ?? []
                        check(size == [self.layoutFrame.width, self.layoutFrame.height], "\(label): CSS viewport changed")
                        run(index + 1)
                    }
                }
            }
        }
        run(0)
    }

    // MARK: self-test (launch with --selftest): drives hover, click and drag through the same
    // code paths a real mouse uses, and writes what the page did to /tmp/study-hud-selftest.log.
    func selfTest() {
        let logURL = URL(fileURLWithPath: "/tmp/study-hud-selftest.log")
        try? "".write(to: logURL, atomically: true, encoding: .utf8)
        func log(_ s: String) {
            if let h = try? FileHandle(forWritingTo: logURL) { h.seekToEndOfFile(); h.write((s + "\n").data(using: .utf8)!); h.closeFile() }
        }
        func probe(_ label: String, then: @escaping () -> Void) {
            web.evaluateJavaScript("JSON.stringify({open, peekKey, panelKey, hovered, body: document.body.className, title: open === 'panel' ? $('panel').querySelector('b')?.textContent : null, pos})") { r, e in
                log("\(label): \(r ?? "nil") \(e.map { "\($0)" } ?? "")"); then()
            }
        }
        let f = layoutFrame
        let pill = screenRect(card).offsetBy(dx: -f.minX, dy: -f.minY)
        log("frame \(f)  pill(view) \(pill)")
        var saved = "null"   // put the user's own placement back afterwards
        web.evaluateJavaScript("JSON.stringify(place)") { r, _ in saved = (r as? String) ?? "null" }
        let center = NSPoint(x: pill.midX, y: pill.maxY - 22 - 28)   // first row under the date, window coordinates
        let screenCenter = NSPoint(x: f.minX + center.x, y: f.minY + center.y)
        func mouse(_ type: NSEvent.EventType, _ p: NSPoint) {
            if let e = NSEvent.mouseEvent(with: type, location: panel.convertPoint(fromScreen: NSPoint(x: layoutFrame.minX + p.x, y: layoutFrame.minY + p.y)), modifierFlags: [], timestamp: ProcessInfo.processInfo.systemUptime,
                                          windowNumber: panel.windowNumber, context: nil, eventNumber: 0, clickCount: 1, pressure: 1) {
                panel.sendEvent(e)
            }
        }
        // 1. hover: pointer rests on the first block
        fakePointer = screenCenter
        trackMouse(screenCenter)
        log("hit test over pill -> ignoresMouseEvents=\(panel.ignoresMouseEvents) inside=\(inside) pointer page=\(Int(center.x)),\(Int(f.height - center.y))")
        web.evaluateJavaScript("(() => { const e = document.elementFromPoint(\(Int(center.x)), \(Int(f.height - center.y))); return (e?.closest('.item')?.dataset.k || 'none') + ' / ' + (e?.className || e?.tagName) })()") { r, _ in log("element under pointer: \(r ?? "nil")") }
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.6) {
            probe("after hover") {
                // 2. click the first block
                mouse(.leftMouseDown, center); mouse(.leftMouseUp, center)
                DispatchQueue.main.asyncAfter(deadline: .now() + 0.6) {
                    probe("after click on block 1") {
                        self.web.evaluateJavaScript("show(null)")
                        let second = NSPoint(x: center.x, y: center.y - 57)
                        mouse(.leftMouseDown, second); mouse(.leftMouseUp, second)
                        DispatchQueue.main.asyncAfter(deadline: .now() + 0.6) {
                        probe("after click on block 2") {
                        // 2b. press ▤ in that panel, then move the pointer away: the whole plan should stay open
                        self.web.evaluateJavaScript("(r => [r.left + r.width / 2, r.top + r.height / 2])($('panel').querySelector('[data-open]').getBoundingClientRect())") { r, _ in
                        let xy = (r as? [Double]) ?? [0, 0], btn = NSPoint(x: xy[0], y: f.height - xy[1])
                        self.fakePointer = NSPoint(x: f.minX + btn.x, y: f.minY + btn.y); self.trackMouse(self.fakePointer!)
                        mouse(.leftMouseDown, btn); mouse(.leftMouseUp, btn)
                        DispatchQueue.main.asyncAfter(deadline: .now() + 0.3) {
                        let away = NSPoint(x: f.minX + 5, y: f.minY + 5)
                        self.fakePointer = away; self.trackMouse(away)
                        DispatchQueue.main.asyncAfter(deadline: .now() + 1.2) {
                        probe("whole plan, 1.2s after the pointer left") {
                        self.web.evaluateJavaScript("hudOutside()")
                        DispatchQueue.main.asyncAfter(deadline: .now() + 0.3) {
                        probe("after a click outside") {
                        self.fakePointer = screenCenter; self.trackMouse(screenCenter)
                        // 3. drag the pill 500pt left and 200pt down, then release
                        mouse(.leftMouseDown, center)
                        for i in 1...20 { mouse(.leftMouseDragged, NSPoint(x: center.x - CGFloat(i) * 25, y: center.y - CGFloat(i) * 10)) }
                        DispatchQueue.main.asyncAfter(deadline: .now() + 0.3) {
                            probe("mid drag") {
                                mouse(.leftMouseUp, NSPoint(x: center.x - 500, y: center.y - 200))
                                DispatchQueue.main.asyncAfter(deadline: .now() + 0.8) {
                                    probe("after drop") {
                                        self.web.evaluateJavaScript("(p => p ? hudPlace(p.edge, p.at) : hudPlace('right', 0.12))(\(saved))")
                                        self.fakePointer = nil
                                        log("done")
                                        DispatchQueue.main.asyncAfter(deadline: .now() + 0.5) { NSApp.terminate(nil) }
                                    }
                                }
                            }
                        }
                        }
                        }
                        }
                        }
                        }
                        }
                        }
                        }
                    }
                }
            }
        }
    }

    // --ticktest N: every 20s for N seconds, log what each pill row shows to /tmp/study-hud-ticktest.log.
    func tickTest(seconds: Int) {
        let logURL = URL(fileURLWithPath: "/tmp/study-hud-ticktest.log")
        try? "".write(to: logURL, atomically: true, encoding: .utf8)
        let started = Date()
        let js = """
          JSON.stringify([{ popup: document.querySelector('#nudge.on')?.innerText.replace(/\\s+/g, ' ').slice(0, 90) || 'none' },
            ...[...document.querySelectorAll('#pill .item')].map(r => ({
            block: r.dataset.k, state: r.className.replace('item', '').trim(),
            shows: r.querySelector('.val span:not(.out)')?.textContent,
            ring: Math.round((1 - parseFloat(r.querySelector('.arc').style.strokeDashoffset) / \(2 * Double.pi * 18.5)) * 100) + '%' }))])
          """
        Timer.scheduledTimer(withTimeInterval: 5, repeats: true) { [weak self] timer in
            guard let self else { return }
            let t = Int(Date().timeIntervalSince(started))
            self.web.evaluateJavaScript(js) { r, _ in
                let clock = DateFormatter.localizedString(from: Date(), dateStyle: .none, timeStyle: .medium)
                if let h = try? FileHandle(forWritingTo: logURL) {
                    h.seekToEndOfFile(); h.write("\(clock) +\(t)s \(r ?? "nil")\n".data(using: .utf8)!); h.closeFile()
                }
            }
            if t >= seconds { timer.invalidate(); DispatchQueue.main.asyncAfter(deadline: .now() + 1) { NSApp.terminate(nil) } }
        }
    }

    // --dragtest: top bar -> into the top-right corner -> down the right side; then back up to the top.
    // Synthetic mouse events through the same window path; results in /tmp/study-hud-dragtest.log.
    func dragTest() {
        let logURL = URL(fileURLWithPath: "/tmp/study-hud-dragtest.log")
        try? "".write(to: logURL, atomically: true, encoding: .utf8)
        func log(_ s: String) {
            if let h = try? FileHandle(forWritingTo: logURL) { h.seekToEndOfFile(); h.write((s + "\n").data(using: .utf8)!); h.closeFile() }
        }
        func mouse(_ type: NSEvent.EventType, _ p: NSPoint) {   // p in window coordinates
            if let e = NSEvent.mouseEvent(with: type, location: panel.convertPoint(fromScreen: NSPoint(x: layoutFrame.minX + p.x, y: layoutFrame.minY + p.y)), modifierFlags: [], timestamp: ProcessInfo.processInfo.systemUptime,
                                          windowNumber: panel.windowNumber, context: nil, eventNumber: 0, clickCount: 1, pressure: 1) { panel.sendEvent(e) }
        }
        let f = layoutFrame
        var saved = "null"
        // Drag along a path of window points, one step every 30ms, then release and report.
        func drag(_ label: String, _ path: [NSPoint], then: @escaping () -> Void) {
            mouse(.leftMouseDown, path[0])
            var i = 1
            Timer.scheduledTimer(withTimeInterval: 0.03, repeats: true) { t in
                if i < path.count {
                    mouse(.leftMouseDragged, path[i]); i += 1
                    self.web.evaluateJavaScript("getComputedStyle($('pill')).opacity") { value, error in
                        if error != nil || (value as? String) != "1" || !self.panel.isVisible {
                            log("FAIL: live pill disappeared during drag")
                        }
                    }
                    return
                }
                t.invalidate()
                let mid = "livePanelVisible=\(self.panel.isVisible) edge=\(self.dragEdge)"
                mouse(.leftMouseUp, path[path.count - 1])
                DispatchQueue.main.asyncAfter(deadline: .now() + 0.8) {
                    self.web.evaluateJavaScript("JSON.stringify({place, pos, size: [$('pill').offsetWidth, $('pill').offsetHeight]})") { r, _ in
                        log("\(label): during drag \(mid) | after drop \(r ?? "nil")"); then()
                    }
                }
            }
        }
        func line(_ a: NSPoint, _ b: NSPoint, _ n: Int) -> [NSPoint] { (0...n).map { k in NSPoint(x: a.x + (b.x - a.x) * CGFloat(k) / CGFloat(n), y: a.y + (b.y - a.y) * CGFloat(k) / CGFloat(n)) } }
        web.evaluateJavaScript("JSON.stringify(place)") { r, _ in
            saved = (r as? String) ?? "null"
            self.web.evaluateJavaScript("hudPlace('top', 0.5)")
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.8) {
                let c = self.screenRect(self.card).offsetBy(dx: -f.minX, dy: -f.minY), start = NSPoint(x: c.midX, y: c.midY)
                log("start: top bar \(Int(c.width))x\(Int(c.height))")
                let corner = NSPoint(x: f.width - 20, y: f.height - 20), down = NSPoint(x: f.width - 20, y: f.height / 2)
                drag("top -> top-right corner -> down the right side", line(start, corner, 15) + line(corner, down, 15)) {
                    DispatchQueue.main.asyncAfter(deadline: .now() + 0.4) {
                        let c2 = self.screenRect(self.card).offsetBy(dx: -f.minX, dy: -f.minY), s2 = NSPoint(x: c2.midX, y: c2.midY)
                        drag("right side -> up into the top zone -> along the top to the left", line(s2, NSPoint(x: s2.x, y: f.height - 20), 15) + line(NSPoint(x: s2.x, y: f.height - 20), NSPoint(x: f.width * 0.3, y: f.height - 20), 15)) {
                            self.web.evaluateJavaScript("(p => p ? hudPlace(p.edge, p.at) : hudPlace('right', 0.12))(\(saved))")
                            log("done")
                            DispatchQueue.main.asyncAfter(deadline: .now() + 0.6) { NSApp.terminate(nil) }
                        }
                    }
                }
            }
        }
    }

    // MARK: server
    func ensureServer(then: @escaping () -> Void) {
        URLSession.shared.dataTask(with: base.appendingPathComponent("api/state")) { _, resp, _ in
            let up = (resp as? HTTPURLResponse)?.statusCode == 200
            DispatchQueue.main.async {
                if up { return then() }
                self.launchServer()
                DispatchQueue.main.asyncAfter(deadline: .now() + 1.2, execute: then)
            }
        }.resume()
    }

    var serverProcess: Process?   // only set when this app started the server; it stops it on Quit

    func launchServer() {
        let p = Process()
        p.executableURL = URL(fileURLWithPath: "/usr/bin/python3")
        p.arguments = [studyDir.appendingPathComponent("server.py").path, String(port)]
        p.currentDirectoryURL = studyDir
        let logPath = "/tmp/study-hall.log"
        if !FileManager.default.fileExists(atPath: logPath) { FileManager.default.createFile(atPath: logPath, contents: nil) }
        let log = FileHandle(forWritingAtPath: logPath)
        p.standardOutput = log; p.standardError = log
        try? p.run()
        serverProcess = p
    }

    func applicationWillTerminate(_ note: Notification) {
        serverProcess?.terminate()
    }

    func webView(_ w: WKWebView, didStartProvisionalNavigation n: WKNavigation!) {
        card = .zero
        popovers = []
        panel.orderOut(nil)
    }
    func webView(_ w: WKWebView, didFailProvisionalNavigation n: WKNavigation!, withError e: Error) { retry() }
    func webView(_ w: WKWebView, didFail n: WKNavigation!, withError e: Error) { retry() }
    func retry() {
        DispatchQueue.main.asyncAfter(deadline: .now() + 2) { [weak self] in
            self?.ensureServer { self?.web.load(URLRequest(url: base.appendingPathComponent("widget"))) }
        }
    }

    // MARK: menu bar
    func buildStatusItem() {
        status = NSStatusBar.system.statusItem(withLength: NSStatusItem.variableLength)
        status.button?.image = NSImage(systemSymbolName: "graduationcap", accessibilityDescription: "Study HUD")
        let menu = NSMenu()
        menu.addItem(withTitle: "Show / Hide HUD", action: #selector(toggle), keyEquivalent: "")
        menu.addItem(withTitle: "Settings…", action: #selector(openSettings), keyEquivalent: ",")
        menu.addItem(withTitle: "Sync PowerSchool Now", action: #selector(syncPowerSchool), keyEquivalent: "")
        menu.addItem(withTitle: "Sync Classroom Now", action: #selector(syncClassroom), keyEquivalent: "")
        menu.addItem(withTitle: "Sign in to Google…", action: #selector(googleSignIn), keyEquivalent: "")
        menu.addItem(withTitle: "Sync AP Classroom Now", action: #selector(syncAPClassroom), keyEquivalent: "")
        menu.addItem(withTitle: "Sign in to AP Classroom…", action: #selector(apcSignIn), keyEquivalent: "")
        menu.addItem(withTitle: "Reload", action: #selector(reload), keyEquivalent: "")
        menu.addItem(withTitle: "Move to Right Edge", action: #selector(resetPosition), keyEquivalent: "")
        menu.addItem(.separator())
        menu.addItem(withTitle: "Quit Study HUD", action: #selector(quit), keyEquivalent: "q")
        menu.items.forEach { $0.target = self }
        status.menu = menu
    }
    @objc func toggle() {
        hudVisible.toggle()
        fitPanelToContent()
    }
    @objc func openInBrowser() { NSWorkspace.shared.open(base) }

    // MARK: settings window
    // The settings page in a window of its own. While it is open the app shows in the Dock and gets a
    // normal menu bar (so ⌘C/⌘V work in its fields); closing it goes back to menu-bar-only.
    var settingsWin: NSWindow?

    @objc func openSettings() {
        if settingsWin == nil {
            let config = WKWebViewConfiguration()
            config.userContentController.add(self, name: "app")   // Sign in / Sync now / Sign out buttons
            let view = WKWebView(frame: NSRect(x: 0, y: 0, width: 920, height: 680), configuration: config)
            view.setValue(false, forKey: "drawsBackground")
            let tab = CommandLine.arguments.contains("--sync") ? "&tab=powerschool" : ""
            view.load(URLRequest(url: URL(string: "?app=1" + tab, relativeTo: base)!))
            let win = NSWindow(contentRect: view.frame, styleMask: [.titled, .closable, .miniaturizable, .resizable],
                               backing: .buffered, defer: false)
            win.title = "Study Plan"
            win.titlebarAppearsTransparent = true
            win.appearance = NSAppearance(named: .darkAqua)
            win.backgroundColor = NSColor(srgbRed: 0x16 / 255, green: 0x16 / 255, blue: 0x18 / 255, alpha: 1)
            win.contentView = view
            win.minSize = NSSize(width: 640, height: 480)
            win.isReleasedWhenClosed = false
            win.delegate = self
            win.center()
            win.setFrameAutosaveName("StudyPlanSettings")
            settingsWin = win
        }
        if NSApp.activationPolicy() != .regular {
            NSApp.setActivationPolicy(.regular)
            buildMainMenu()
        }
        NSApp.activate(ignoringOtherApps: true)
        if settingsWin?.isMiniaturized == true { settingsWin?.deminiaturize(nil) }   // bring it back out of the Dock
        settingsWin?.makeKeyAndOrderFront(nil)
    }

    // Clicking the Dock icon brings the settings window back (also after it was minimised).
    func applicationShouldHandleReopen(_ sender: NSApplication, hasVisibleWindows flag: Bool) -> Bool {
        if settingsWin != nil { openSettings() }
        return true
    }

    func windowWillClose(_ note: Notification) {
        if (note.object as? NSWindow) === settingsWin { NSApp.setActivationPolicy(.accessory) }
    }

    func buildMainMenu() {
        let main = NSMenu()
        func sub(_ title: String, _ items: [NSMenuItem]) {
            let item = NSMenuItem(title: title, action: nil, keyEquivalent: "")
            let m = NSMenu(title: title); items.forEach(m.addItem); item.submenu = m; main.addItem(item)
        }
        func item(_ t: String, _ a: Selector?, _ k: String, _ target: AnyObject? = nil) -> NSMenuItem {
            let i = NSMenuItem(title: t, action: a, keyEquivalent: k); i.target = target; return i
        }
        sub("Study HUD", [item("About Study HUD", #selector(NSApplication.orderFrontStandardAboutPanel(_:)), ""), .separator(),
                          item("Settings…", #selector(openSettings), ",", self), item("Open in Browser", #selector(openInBrowser), "", self), .separator(),
                          item("Hide Study HUD", #selector(NSApplication.hide(_:)), "h"), .separator(),
                          item("Quit Study HUD", #selector(quit), "q", self)])
        sub("Edit", [item("Undo", Selector(("undo:")), "z"), item("Redo", Selector(("redo:")), "Z"), .separator(),
                     item("Cut", #selector(NSText.cut(_:)), "x"), item("Copy", #selector(NSText.copy(_:)), "c"),
                     item("Paste", #selector(NSText.paste(_:)), "v"), item("Select All", #selector(NSText.selectAll(_:)), "a")])
        sub("View", [item("Reload", #selector(reloadSettings), "r", self)])
        sub("Window", [item("Close", #selector(NSWindow.performClose(_:)), "w"), item("Minimize", #selector(NSWindow.performMiniaturize(_:)), "m")])
        NSApp.mainMenu = main
    }

    @objc func reloadSettings() { (settingsWin?.contentView as? WKWebView)?.reload() }

    // MARK: PowerSchool
    lazy var powerSchool = PowerSchoolSync()

    // A native sign-in box; the password goes straight into the Keychain.
    @objc func promptLogin() {
        let alert = NSAlert()
        alert.messageText = "Sign in to PowerSchool"
        alert.informativeText = "Saved in your Mac's Keychain. Study HUD uses it only to read your grades and class schedule from your school's PowerSchool. The address is the site you sign in to, such as yourschool.powerschool.com."
        let host = NSTextField(frame: NSRect(x: 0, y: 64, width: 280, height: 24))
        host.placeholderString = "PowerSchool address"
        host.stringValue = Keychain.server
        let user = NSTextField(frame: NSRect(x: 0, y: 32, width: 280, height: 24))
        user.placeholderString = "Username"
        user.stringValue = Keychain.user ?? ""
        let pass = NSSecureTextField(frame: NSRect(x: 0, y: 0, width: 280, height: 24))
        pass.placeholderString = "Password"
        let box = NSView(frame: NSRect(x: 0, y: 0, width: 280, height: 90))
        box.addSubview(host); box.addSubview(user); box.addSubview(pass)
        alert.accessoryView = box
        alert.addButton(withTitle: "Save and Sync")
        alert.addButton(withTitle: "Cancel")
        alert.window.initialFirstResponder = host.stringValue.isEmpty ? host : (user.stringValue.isEmpty ? user : pass)
        let done: (NSApplication.ModalResponse) -> Void = { [weak self] r in
            guard r == .alertFirstButtonReturn else { return }
            let u = user.stringValue.trimmingCharacters(in: .whitespaces), p = pass.stringValue
            let h = host.stringValue.trimmingCharacters(in: .whitespaces)
                .replacingOccurrences(of: "https://", with: "").components(separatedBy: "/")[0]
            guard !h.isEmpty, !u.isEmpty, !p.isEmpty else { return }
            UserDefaults.standard.set(h, forKey: "powerschoolHost")
            if Keychain.save(user: u, pass: p) { self?.syncPowerSchool() }
            else { self?.report(ok: false, message: "Couldn't save to the Keychain.", account: u) }
        }
        if let win = settingsWin, win.isVisible { alert.beginSheetModal(for: win, completionHandler: done) }
        else { NSApp.activate(ignoringOtherApps: true); done(alert.runModal()) }
    }

    @objc func syncPowerSchool() {
        guard !powerSchool.running else { return }
        guard !Keychain.server.isEmpty else { promptLogin(); return }   // no school address yet
        report(ok: true, message: "Syncing…", account: Keychain.user, running: true)
        Task { @MainActor in
            do {
                let data = try await powerSchool.run()
                post("api/sync/powerschool", data)
            } catch {
                report(ok: false, message: error.localizedDescription, account: Keychain.user)
            }
        }
    }

    func report(ok: Bool, message: String, account: String?, running: Bool = false) {
        var body: [String: Any] = ["ok": ok, "message": message, "running": running]
        if let account { body["account"] = account }
        post("api/sync/status", body)
    }

    func post(_ path: String, _ body: [String: Any]) {
        var req = URLRequest(url: base.appendingPathComponent(path))
        req.httpMethod = "POST"
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        req.httpBody = try? JSONSerialization.data(withJSONObject: body)
        URLSession.shared.dataTask(with: req).resume()
    }

    // MARK: Google Classroom
    lazy var classroom = ClassroomSync()
    var googleSheet: SignInSheet?

    @objc func googleSignIn() {
        openSettings()
        guard let win = settingsWin, googleSheet == nil else { return }
        let sheet = SignInSheet(url: "https://accounts.google.com/ServiceLogin?continue=https://classroom.google.com/",
                                note: "Sign in with your school Google account.") { $0.host == "classroom.google.com" }
        googleSheet = sheet
        win.beginSheet(sheet.window) { [weak self] _ in
            self?.googleSheet = nil
            self?.syncClassroom()   // reports "signed out" again if you cancelled
        }
    }

    // Menu: the To-do sync, then the Classwork sync (new posts and their files), which the server runs in ego-browser.
    // The launch check and the 6-hour timer run the To-do sync only; the server runs Classwork daily at 18:30.
    @objc func syncClassroom() { syncClassroomTodo(thenClasswork: true) }

    func syncClassroomTodo(thenClasswork: Bool = false) {
        guard !classroom.running else { return }
        post("api/sync/classroom-status", ["ok": true, "running": true, "message": "Syncing…"])
        if let container = panel.contentView { classroom.attach(to: container) }
        Task { @MainActor in
            do {
                post("api/sync/classroom", try await classroom.run())
            } catch is ClassroomSync.SignedOut {
                post("api/sync/classroom-status", ["ok": false, "signedOut": true,
                     "message": "Signed out of Google. Use Sign in to Google… to reconnect."])
            } catch {
                post("api/sync/classroom-status", ["ok": false, "message": error.localizedDescription])
            }
            if thenClasswork { post("api/sync/classwork-run", ["reason": "Sync Classroom Now"]) }   // ego-browser has its own sign-in
        }
    }

    // MARK: AP Classroom
    lazy var apClassroom = APClassroomSync()
    var apcSheet: SignInSheet?

    @objc func apcSignIn() {
        openSettings()
        guard let win = settingsWin, apcSheet == nil else { return }
        let sheet = SignInSheet(url: "https://apclassroom.collegeboard.org/",
                                note: "Sign in with your College Board account.",
                                ready: "Object.keys(localStorage).some(k => /token/i.test(k) && /eyJ/.test(localStorage.getItem(k)))") { $0.host == "apclassroom.collegeboard.org" }
        apcSheet = sheet
        win.beginSheet(sheet.window) { [weak self] _ in
            self?.apcSheet = nil
            self?.syncAPClassroom()
        }
    }

    @objc func syncAPClassroom() {
        guard !apClassroom.running else { return }
        post("api/sync/apclassroom-status", ["ok": true, "running": true, "message": "Syncing…"])
        if let container = panel.contentView { apClassroom.attach(to: container) }
        Task { @MainActor in
            do {
                post("api/sync/apclassroom", try await apClassroom.run())
            } catch is HiddenBrowser.SignedOut {
                post("api/sync/apclassroom-status", ["ok": false, "signedOut": true,
                     "message": "Signed out of College Board. Use Sign in to AP Classroom… to reconnect."])
            } catch {
                post("api/sync/apclassroom-status", ["ok": false, "message": error.localizedDescription])
            }
        }
    }

    // Sync at launch when the last one is over 6 hours old, then every 6 hours.
    func scheduleSync(tries: Int = 0) {
        URLSession.shared.dataTask(with: base.appendingPathComponent("api/state")) { [weak self] data, _, _ in
            guard let s = data.flatMap({ try? JSONSerialization.jsonObject(with: $0) as? [String: Any] }) else {
                // The server isn't answering yet (it may be starting): ask again rather than sync everything.
                if tries < 5 { DispatchQueue.main.asyncAfter(deadline: .now() + 10) { self?.scheduleSync(tries: tries + 1) } }
                return
            }
            func stale(_ at: String?) -> Bool {
                Date().timeIntervalSince(at.flatMap { ISO8601DateFormatter().date(from: $0) } ?? .distantPast) > 6 * 3600
            }
            let ps = ((s["grades"] as? [String: Any])?["sync"] as? [String: Any])?["at"] as? String
            let gc = ((s["school"] as? [String: Any])?["sync"] as? [String: Any])?["at"] as? String
            let apc = ((s["school"] as? [String: Any])?["apSync"] as? [String: Any])?["at"] as? String
            DispatchQueue.main.async {
                if Keychain.user != nil && stale(ps) { self?.syncPowerSchool() }
                if stale(gc) { self?.syncClassroomTodo() }
                if stale(apc) { self?.syncAPClassroom() }
            }
        }.resume()
        guard tries == 0 else { return }   // the 6-hour timer is set once
        Timer.scheduledTimer(withTimeInterval: 6 * 3600, repeats: true) { [weak self] _ in
            if Keychain.user != nil { self?.syncPowerSchool() }
            self?.syncClassroomTodo()
            self?.syncAPClassroom()
        }
    }
    @objc func reload() { ensureServer { [weak self] in self?.web.reload() } }
    @objc func resetPosition() { web.evaluateJavaScript("window.hudPlace && hudPlace('right', 0.1)") }
    @objc func quit() { NSApp.terminate(nil) }
}

let app = NSApplication.shared
let delegate = AppDelegate()
app.delegate = delegate
app.setActivationPolicy(.accessory)
app.run()
