// Classwork sync for Study Hall, run inside ego-browser (Ego Lite, already signed in to the school Google account):
//   ~/.local/bin/ego-browser nodejs < {{KIT}}/core/study-hall/classwork_sync.mjs
// The server starts it (POST /api/sync/classwork-run, the HUD's "Sync Classroom Now", and the 18:30 daily run).
//
// For each subject in config.json with a classroomCourseId it reads the course's Classwork tab and Stream, finds posts
// it hasn't seen before (the first run takes the last 14 days), and downloads their Drive attachments: Docs, Slides and
// Drawings as PDF, Sheets as .xlsx, Drive files as they are. Files go to a temp folder; the server skips any whose name
// and size already exist in the subject folder, moves the rest into the folder named by config "classworkDir", and
// rewrites each STATE.md Classroom block.
//
// Read-only on Classroom: it only clicks "View more" and each row's own expand toggle (the [role=button][aria-expanded]
// header), never a menu, Turn in, Mark as done or Add comment. A sign-in page or any challenge stops the run.
// The ego runtime doesn't inherit cwd or env, so every path is absolute.

const ROOT = "{{KIT}}/core/study-hall";
const SERVER = "http://127.0.0.1:4417";
const FIRST_RUN_DAYS = 14;   // the first sync of a course takes posts from the last 14 days as new
const MAX_AGE_DAYS = 30;     // later syncs never treat a post older than this as new (the Stream keeps loading old ones)

const fs = await import("node:fs");
const os = await import("node:os");
const path = await import("node:path");
const crypto = await import("node:crypto");

const readJSON = (file, fallback) => { try { return JSON.parse(fs.readFileSync(file, "utf8")); } catch { return fallback; } };
const cfg = readJSON(`${ROOT}/config.json`, {});
const known = readJSON(`${ROOT}/school.json`, {}).classwork || {};
// curl through child_process, not fetch or node:http: inside ego's node (24.22) both crash in undici's
// parser when the Python server closes its HTTP/1.0 socket. curl is immune and the browser is untouched.
const { execFileSync } = await import("node:child_process");
const send = (route, body) => {
  try {
    const code = execFileSync("/usr/bin/curl", ["-s", "-o", "/dev/null", "-w", "%{http_code}", "-X", "POST",
      "-H", "content-type: application/json", "--data-binary", JSON.stringify(body), SERVER + route], { timeout: 120000 }).toString();
    return Promise.resolve(code.startsWith("2"));
  } catch { return Promise.resolve(false); }
};
const log = (...a) => console.log("[classwork]", ...a);
const pad = (n) => String(n).padStart(2, "0");
const ymd = (d) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
const today = ymd(new Date());
const TMP = path.join(os.tmpdir(), "study-hud-downloads");

// Everything that runs inside the page. One function, so helpers travel with it into page.evaluate().
async function inPage({ op, args, id }) {
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const main = () => document.querySelector("main") || document.body;
  const today = new Date(args.today + "T12:00:00");
  const MON = { jan: 0, feb: 1, mar: 2, apr: 3, may: 4, jun: 5, jul: 6, aug: 7, sep: 8, oct: 9, nov: 10, dec: 11 };
  const pad = (n) => String(n).padStart(2, "0");
  const ymd = (d) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
  const shift = (n) => { const d = new Date(today); d.setDate(d.getDate() + n); return ymd(d); };
  // "9:50 AM", "Yesterday", "Oct 29", "Oct 29, 2025", "Friday"; future = a due date rather than a posted one
  const day = (s, future) => {
    s = (s || "").trim();
    if (/^\d{1,2}:\d{2}/.test(s) || /^Today/i.test(s)) return shift(0);
    if (/^Yesterday/i.test(s)) return shift(-1);
    if (/^Tomorrow/i.test(s)) return shift(1);
    const w = s.match(/^(Sun|Mon|Tue|Wed|Thu|Fri|Sat)[a-z]*\b/i);
    if (w) {
      const k = (["sun", "mon", "tue", "wed", "thu", "fri", "sat"].indexOf(w[1].toLowerCase()) - today.getDay() + 7) % 7;
      return shift(future ? k : (k ? k - 7 : 0));
    }
    const m = s.match(/^([A-Za-z]{3})[a-z]*\.?\s+(\d{1,2})(?:,\s*(\d{4}))?/);
    if (!m || !(m[1].toLowerCase() in MON)) return null;
    const d = new Date(m[3] ? +m[3] : today.getFullYear(), MON[m[1].toLowerCase()], +m[2], 12);
    if (!m[3] && !future && d - today > 2 * 864e5) d.setFullYear(d.getFullYear() - 1);
    if (!m[3] && future && today - d > 180 * 864e5) d.setFullYear(d.getFullYear() + 1);
    return ymd(d);
  };
  // What to download for an attachment. Classroom's own link says which signed-in account is the school one (authuser=N).
  const plan = (href) => {
    const who = (href.match(/[?&]authuser=(\d+)/) || [])[1] || "0";
    const fid = (href.match(/\/d\/([\w-]{20,})/) || href.match(/[?&]id=([\w-]{20,})/) || [])[1];
    const doc = (kind) => `https://docs.google.com/${kind}/d/${fid}/`;
    if (/docs\.google\.com\/document\//.test(href) && fid) return { get: doc("document") + `export?format=pdf&authuser=${who}`, ext: "pdf" };
    if (/docs\.google\.com\/presentation\//.test(href) && fid) return { get: doc("presentation") + `export/pdf?authuser=${who}`, ext: "pdf" };
    if (/docs\.google\.com\/spreadsheets\//.test(href) && fid) return { get: doc("spreadsheets") + `export?format=xlsx&authuser=${who}`, ext: "xlsx" };
    if (/docs\.google\.com\/drawings\//.test(href) && fid) return { get: doc("drawings") + `export/pdf?authuser=${who}`, ext: "pdf" };
    if (/docs\.google\.com\/forms\/|forms\.gle\//.test(href)) return { skip: "Google Form (link only)" };
    if (/drive\.google\.com\/drive\/(u\/\d+\/)?folders\//.test(href)) return { skip: "Drive folder (open it in Classroom)" };
    if (/drive\.google\.com\//.test(href) && fid) return { get: `https://drive.usercontent.google.com/download?id=${fid}&export=download&confirm=t&authuser=${who}`, ext: "" };
    return {};
  };
  const attachments = (el) => {
    const found = new Map();
    for (const a of el.querySelectorAll('a[aria-label^="Attachment"]')) {
      const href = a.href;
      if (found.has(href)) continue;
      const label = a.getAttribute("aria-label").replace(/^Attachment:\s*/, "");
      let type, name;
      const link = label.match(/^Link to (.*)$/);
      if (link) {
        type = "Link";
        name = (a.innerText.split("\n")[0] || "").trim();
        if (!name || /^Just a moment/i.test(name)) { try { name = new URL(href).hostname; } catch { name = link[1]; } }
      } else {
        const i = label.indexOf(": ");
        type = i > 0 ? label.slice(0, i) : "File";
        name = i > 0 ? label.slice(i + 2) : label;
        if (/^YouTube/i.test(type)) name = name.replace(/\s*\([^)]*\)$/, "");
      }
      found.set(href, { name: name.slice(0, 150), type, url: href.replace(/[?&]usp=classroom_web/, "").replace(/[?&]authuser=\d+$/, ""), ...plan(href) });
    }
    return [...found.values()];
  };
  const seen = new Set(args.seen || []);
  const isNew = (p) => !seen.has(p.id) && (!args.cutoff || (p.posted ? p.posted >= args.cutoff : (!p.due || p.due >= args.cutoff)));
  const unit = (p) => (((p.topic || "") + " " + p.title).match(/\bUnit\s*(\d+)/i) || [])[1] || null;
  const challenge = () => /accounts\.google\.com/.test(location.host) || /verify it.s you|confirm it.s you|unusual traffic|not a robot|captcha/i.test(document.body?.innerText || "");

  if (op === "challenge") return challenge() ? `${location.href} | ${document.title}` : null;

  if (op === "more") {   // each topic shows ten posts; "View more" only lists the rest
    const more = [...main().querySelectorAll('[role="button"],button')].filter((b) => /^View more$/i.test((b.innerText || "").trim()));
    for (const b of more) b.click();
    return more.length;
  }

  if (op === "list") {
    const topics = {};
    for (const t of main().querySelectorAll("[data-topic-id]")) {
      const h = t.querySelector('h2,h3,[role="heading"]');
      if (h && h.innerText.trim() && !topics[t.dataset.topicId]) topics[t.dataset.topicId] = h.innerText.trim();
    }
    const KIND = { 1: "assignment", 4: "question", 5: "material" };
    const posts = [];
    for (const r of main().querySelectorAll("li[data-stream-item-id]")) {
      const toggle = r.querySelector('[role="button"][aria-expanded]');
      const lines = r.innerText.split("\n").map((l) => l.trim()).filter(Boolean);
      const p = { id: r.dataset.streamItemId, kind: KIND[r.dataset.streamItemType] || (lines[0] || "").replace(/^Completed\s+/, "").toLowerCase(),
                  title: (toggle?.getAttribute("aria-label") || lines[2] || "").trim(),
                  topic: topics[r.closest("[data-topic-id]")?.dataset.topicId] || null, done: /^Completed\b/.test(lines[0] || "") };
      for (const l of lines) {
        const m = l.match(/^(Posted|Edited|Due)\s+(.+)$/);
        if (m && m[1] === "Due") p.due = day(m[2], true); else if (m && !p.posted) p.posted = day(m[2], false);
      }
      p.unit = unit(p);
      p.isNew = isNew(p);
      p.canExpand = !!toggle;
      posts.push(p);
    }
    const who = document.querySelector('a[aria-label*="Google Account"]')?.getAttribute("aria-label") || "";
    return { posts, account: (who.match(/\(([^)]+@[^)]+)\)/) || [])[1] || null, course: document.title.replace(/^Classwork\s+(for\s+)?/i, "").replace(/\s+-\s+Classroom$/i, "") };
  }

  if (op === "expand") {   // open one row (its header toggle only), read its attachments, close it again
    const r = main().querySelector(`li[data-stream-item-id="${id}"]`);
    const toggle = r?.querySelector('[role="button"][aria-expanded]');
    if (!toggle) return null;
    if (toggle.getAttribute("aria-expanded") !== "true") toggle.click();
    for (let i = 0; i < 25 && !r.querySelector('a[href*="/details"]'); i++) await sleep(200);
    // The attachment chips load after the row opens: wait until their count holds steady (about 3 s when there are none).
    let count = -1, steady = 0;
    for (let i = 0; i < 24 && steady < 3; i++) {
      await sleep(250);
      const n = r.querySelectorAll('a[aria-label^="Attachment"]').length;
      steady = n === count && (n > 0 || i >= 8) ? steady + 1 : 0;
      count = n;
    }
    let posted = null;
    for (const l of r.innerText.split("\n")) { const m = l.trim().match(/^(Posted|Edited)\s+(.+)$/); if (m) { posted = day(m[2], false); break; } }
    const out = { attachments: attachments(r), link: r.querySelector('a[href*="/details"]')?.href || null, posted };
    if (toggle.getAttribute("aria-expanded") === "true") toggle.click();
    return out;
  }

  if (op === "stream") {   // announcements; the "posted a new material" cards repeat Classwork and are skipped
    // Attachment chips load after the posts: wait until their count holds steady (at least 2 s).
    let count = -1, steady = 0;
    for (let i = 0; i < 32 && steady < 4; i++) {
      await sleep(250);
      const n = main().querySelectorAll('a[aria-label^="Attachment"]').length;
      steady = n === count && i >= 8 ? steady + 1 : 0;
      count = n;
    }
    const posts = [], done = new Set();
    for (const el of main().querySelectorAll("[data-stream-item-id]")) {
      const sid = el.dataset.streamItemId;
      if (done.has(sid)) continue;
      done.add(sid);   // the first (outermost) element of each post holds all of it
      const lines = el.innerText.split("\n").map((l) => l.trim()).filter(Boolean);
      if (!/^Post by\b/i.test(lines[0] || "")) continue;
      let posted = null;
      for (const l of lines.slice(0, 6)) {
        const m = l.match(/^(?:Created|Posted|Edited)?\s*([A-Z][a-z]{2}\s+\d{1,2}(?:,\s*\d{4})?|\d{1,2}:\d{2}\s*[AP]M|Yesterday)/);
        if (m) { posted = day(m[1], false); break; }
      }
      const at = lines.findIndex((l) => /^More options$/i.test(l));
      const body = lines.slice(at + 1).filter((l) => !/^(Add (class )?comment|\d+ class comments?|class comments?)$/i.test(l)).join(" ");
      const p = { id: sid, kind: "announcement", title: body.replace(/\s+/g, " ").slice(0, 160) || "(announcement)", topic: null, posted };
      p.unit = unit(p);
      p.isNew = isNew(p);
      if (p.isNew) p.attachments = attachments(el);
      posts.push(p);
    }
    return { posts };
  }
  return null;
}

const fileName = (title, suggested, ext) => {
  const clean = (s) => String(s || "").replace(/\//g, "-").replace(/:/g, " -").trim();
  const sug = clean(suggested);
  const base = sug.replace(/\.[^.]+$/, "");
  if (/\.[A-Za-z0-9]{1,6}$/.test(sug) && !["", "download", "export", "uc", "unknown"].includes(base.toLowerCase())) return sug;
  const t = clean(title) || "attachment";
  return !ext || t.toLowerCase().endsWith("." + ext) ? t : `${t}.${ext}`;
};

class Stop extends Error {}

const task = await taskSpace("study-hall classwork sync");
const page = task.page("p1");
log(`task space ${task.spaceId}`);
await send("/api/sync/classwork-status", { ok: true, running: true, message: "Syncing (ego-browser)…" });

const stopIfChallenged = async (where) => {
  const hit = await page.evaluate(inPage, { op: "challenge", args: { today } }).catch(() => null);
  if (hit) throw new Stop(`Google asked for sign-in or a check at ${where} (${hit}). Sign in in Ego Lite, then sync again.`);
};
const open = async (url) => {
  await page.goto(url);
  if (/accounts\.google\.com/.test(await page.url())) throw new Stop(`Google sent the browser to sign-in (${await page.url()}). Sign in in Ego Lite, then sync again.`);
};

let account = null;
const results = [];
try {
  for (const s of cfg.subjects || []) {
    const cid = s.classroomCourseId;
    const folder = s.folder || (s.state ? path.dirname(s.state) : null);
    if (!cid || !folder) continue;
    const prev = known[s.id];
    const first = !prev || !prev.seen;
    const args = { today, seen: (prev && prev.seen) || [], cutoff: ymd(new Date(Date.now() - (first ? FIRST_RUN_DAYS : MAX_AGE_DAYS) * 864e5)) };
    const r = { subject: s.id, courseId: cid, firstRun: first, ok: true, posts: [] };
    results.push(r);
    // Classwork tab
    try {
      await open(`https://classroom.google.com/w/${cid}/t/all`);
      await page.waitForFunction(() => document.querySelector("li[data-stream-item-id]") || /no (class)?work|nothing here/i.test(document.querySelector("main")?.innerText || ""),
        undefined, { timeout: 25_000 }).catch(() => {});
      await stopIfChallenged(`${s.short || s.id} Classwork`);
      for (let k = 0; k < 15 && (await page.evaluate(inPage, { op: "more", args })) > 0; k++) await page.waitForTimeout(1200);
      const listed = await page.evaluate(inPage, { op: "list", args });
      account = account || listed.account;
      r.course = listed.course;
      for (const p of listed.posts) {
        if (p.isNew && p.canExpand) {
          const x = await page.evaluate(inPage, { op: "expand", args, id: p.id });
          if (x) {
            p.attachments = x.attachments;
            p.link = x.link;
            p.posted = p.posted || x.posted;
          }
          if (p.posted && p.posted < args.cutoff) { p.isNew = false; delete p.attachments; }
        }
        delete p.canExpand;
        r.posts.push(p);
      }
    } catch (e) {
      if (e instanceof Stop) throw e;
      r.ok = false;
      r.error = `Classwork: ${String(e.message || e).slice(0, 160)}`;
    }
    // Stream (announcements)
    try {
      await open(`https://classroom.google.com/c/${cid}`);
      await page.waitForFunction(() => document.querySelector("[data-stream-item-id]"), undefined, { timeout: 20_000 }).catch(() => {});
      await stopIfChallenged(`${s.short || s.id} Stream`);
      r.posts.push(...(await page.evaluate(inPage, { op: "stream", args })).posts);
    } catch (e) {
      if (e instanceof Stop) throw e;
      r.streamError = String(e.message || e).slice(0, 160);
    }
    // Downloads: open each export/download URL with the download wait armed; the page load aborts and a download starts.
    for (const p of r.posts.filter((p) => p.isNew)) {
      for (const a of p.attachments || []) {
        if (!a.get) { a.status = a.skip ? "skipped" : "link"; continue; }
        const dl = page.waitForEvent("download", { timeout: 60_000 });
        dl.catch(() => {});
        await page.goto(a.get).catch(() => {});   // net::ERR_ABORTED is the normal result for a download
        try {
          const d = await dl;
          const dir = path.join(TMP, crypto.randomUUID());
          const temp = path.join(dir, fileName(a.name, d.suggestedFilename(), a.ext));
          await d.saveAs(temp);
          a.status = "downloaded";
          a.temp = temp;
          a.bytes = fs.statSync(temp).size;
        } catch (e) {
          await stopIfChallenged(`the download of "${a.name}"`);
          const where = await page.title().catch(() => "");
          a.status = "failed";
          a.reason = `no download started${where ? ` (the link opened "${where.slice(0, 60)}")` : ""}; no access to export it, or it took over a minute`;
        }
      }
    }
    const n = r.posts.filter((p) => p.isNew).length;
    log(`${s.id}: ${r.posts.length} posts read, ${n} new${r.error ? `, ${r.error}` : ""}${r.streamError ? `, stream: ${r.streamError}` : ""}`);
  }
} catch (e) {
  const why = String(e.message || e).slice(0, 300);
  log(`stopped: ${why}`);
  await send("/api/sync/classwork-status", { ok: false, signedOut: e instanceof Stop, message: why });
  process.exit(2);   // the task space stays as it is for the user to look at; no finish()
}

const ok = await send("/api/sync/classwork", { account, source: "ego-browser", subjects: results });
log(ok ? "posted to Study Hall" : "could not reach Study Hall's server");
await task.finish({ keep: [] });
if (!ok) process.exit(3);
