"""The room: one card at a time between the tutor (room.py) and the learner (room.html).

State lives in room.json next to config.json, so a server restart or a page reload loses nothing.
The tutor posts a card and blocks in wait() until the learner submits; a timed card whose clock ran
out is handed in from its last autosaved draft, so a closed laptop still produces an attempt.
"""
import base64
import hashlib
import json
import os
import re
import shutil
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path

TYPES = ("question", "passage", "canvas", "mcq", "choice", "close", "lesson", "review")
GRACE = 8          # seconds after a deadline before the server hands in the draft itself
MAX_UPLOAD = 12 * 1024 * 1024
PAGE_ALIVE = 75    # a background tab's 1 s poll is throttled to about once a minute, so 4 s read an open room as closed

# Bring an open room tab forward instead of opening another one. Only asks browsers that are already running.
FOCUS_TAB = '''on matches(u, targets)
  repeat with x in targets
    if u is (x as text) or u starts with (x & "?") or u starts with (x & "#") then return true
  end repeat
  return false
end matches

on run targets
  if application "Dia" is running then
    tell application "Dia"
      repeat with w in windows
        repeat with t in tabs of w
          if my matches(URL of t, targets) then
            focus t
            activate
            return "Dia"
          end if
        end repeat
      end repeat
    end tell
  end if
  if application "Google Chrome" is running then
    tell application "Google Chrome"
      repeat with w in windows
        set i to 0
        repeat with t in tabs of w
          set i to i + 1
          if my matches(URL of t, targets) then
            set active tab index of w to i
            set index of w to 1
            activate
            return "Google Chrome"
          end if
        end repeat
      end repeat
    end tell
  end if
  return ""
end run'''


def show_room(url):
    """Focus the room's tab if one is open anywhere, otherwise open one. Returns "focused" or "opened"."""
    import subprocess
    from urllib.parse import urlsplit
    u = urlsplit(url)
    targets = [f"{u.scheme}://{h}:{u.port}{u.path}" for h in ("127.0.0.1", "localhost")]
    try:
        r = subprocess.run(["osascript", "-e", FOCUS_TAB, *targets], capture_output=True, text=True, timeout=8)
        if r.stdout.strip():
            return "focused"
    except (OSError, subprocess.SubprocessError):
        pass
    try:
        subprocess.run(["open", url], check=False, timeout=5)
    except (OSError, subprocess.SubprocessError):
        pass
    return "opened"


class Room:
    def __init__(self, data_dir, subjects_fn, folder_fn, rid=None):
        self.rid = rid                       # the subject this room belongs to (None: the one shared room of old, and tests)
        self.path = Path(data_dir) / (f"room-{rid}.json" if rid else "room.json")
        self.subjects = subjects_fn          # () -> {id: subject config}
        self.folder = folder_fn              # (subject config) -> folder path or None
        self.cond = threading.Condition()
        try:
            self.s = json.loads(self.path.read_text())
        except (OSError, ValueError):
            self.s = {}
        self.seen = 0            # when the page last polled; a post with no page open gets the room shown
        self.s.setdefault("v", 0)
        self.s.setdefault("history", [])
        for k in ("subject", "who", "card", "say", "sub", "draft", "note"):
            self.s.setdefault(k, None)

    # ---------- helpers ----------
    def page_open(self):
        return time.time() - self.seen < PAGE_ALIVE

    def gone(self):
        """The page said goodbye (tab closed or navigated away); the next poll from another tab brings it back."""
        with self.cond:
            self.seen = 0
        return {"ok": True}

    def _save(self):
        self.s["v"] += 1
        self.s["touched"] = time.time()
        self.s["history"] = self.s["history"][-160:]
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.s, ensure_ascii=False))
        tmp.replace(self.path)
        self.cond.notify_all()

    def _log(self, who, text, **more):
        if text or more.get("kind") == "begin":
            self.s["history"].append({"t": datetime.now().strftime("%H:%M"), "who": who, "text": str(text or "")[:2000], **more})

    def _who(self):
        if self.s.get("who"):
            return self.s["who"]
        subj = self.subjects().get(self.s.get("subject") or "", {})
        return subj.get("teacher") or subj.get("short") or "Tutor"

    def _auto_submit(self):
        """Hand in a timed card from its draft once its clock is past the grace period."""
        c, now = self.s.get("card"), time.time()
        if not c or self.s.get("sub") or not c.get("deadline") or now < c["deadline"] + GRACE:
            return False
        d = self.s.get("draft") or {}
        data = {"claim": d.get("claim", ""), "text": d.get("text", ""), "answers": d.get("answers")}
        self._submit(c, data, auto=True)
        return True

    def _submit(self, c, data, auto=False):
        result = None
        if c["type"] == "mcq":
            keys = c.get("_keys") or []
            ans = list((data or {}).get("answers") or [])
            ans += [None] * (len(keys) - len(ans))
            right = [a is not None and k is not None and int(a) == int(k) for a, k in zip(ans, keys)]
            result = {"score": sum(right), "total": len(keys), "right": right, "keys": keys, "answers": ans[:len(keys)]}
            c["result"] = result
        self.s["sub"] = {"card": c["id"], "data": data or {}, "at": time.time(), "auto": auto}
        if any(str((data or {}).get(k) or "").strip() for k in ("text", "answer", "retry", "why")):
            self.s["last"] = {"card": c["id"], "data": data, "at": self.s["sub"]["at"]}   # for a review card's from: "answer", after newer cards
        self._log("You", summarize(c, data or {}, result, auto))
        self._save()
        return result

    # ---------- learner side ----------
    def view(self, block):
        with self.cond:
            self.seen = time.time()
            if self._auto_submit():
                pass
            subj_id = self.s.get("subject")
            subj = self.subjects().get(subj_id or self.rid or "", {})   # an idle room still wears its subject's name and colour
            c = self.s.get("card")
            pub = {k: v for k, v in c.items() if not k.startswith("_")} if c else None
            sub = self.s.get("sub")
            submitted = bool(c and sub and sub["card"] == c["id"])
            say = self.s.get("say")
            pending = bool(submitted and (not say or say["at"] < sub["at"]))
            draft = self.s.get("draft") if c and (self.s.get("draft") or {}).get("card") == c["id"] else None
            note = self.s.get("note")
            asked = bool(c and note and note.get("card") == c["id"] and (not say or say["at"] < note["at"]))   # asked, no reply yet
            who = self._who()
            return {"v": self.s["v"], "room": self.rid, "now": time.time(), "subject": subj_id, "name": subj.get("name"), "color": subj.get("color"),
                    "who": who, "av": initials(who), "block": block, "card": pub, "say": say, "pending": pending or asked, "asked": asked,
                    "submitted": submitted, "draft": draft, "history": self.s["history"][-120:], "ended": self.s.get("ended")}

    def start_timer(self, card_id):
        with self.cond:
            c = self.s.get("card")
            if not c or c["id"] != card_id:
                return None
            if c["type"] in ("canvas", "mcq") and not c.get("deadline") and not self.s.get("sub"):
                c["startedAt"] = time.time()
                c["deadline"] = c["startedAt"] + 60 * float(c.get("minutes") or 40)
                self._save()
            return c.get("deadline")

    def draft(self, card_id, body):
        with self.cond:
            c, sub = self.s.get("card"), self.s.get("sub")
            if not c or c["id"] != card_id or (sub and sub["card"] == card_id):
                return False
            old = self.s.get("draft") or {}
            if old.get("card") == card_id and float(body.get("t") or 0) < float(old.get("t") or 0):
                return True
            self.s["draft"] = {"t": float(body.get("t") or 0), "card": card_id, "claim": str(body.get("claim") or "")[:2000],
                               "text": str(body.get("text") or "")[:60000], "answers": body.get("answers"), "at": time.time()}
            self.s["v"] += 1                      # no notify needed; nothing waits on drafts
            tmp = self.path.with_suffix(".tmp")
            tmp.write_text(json.dumps(self.s, ensure_ascii=False))
            tmp.replace(self.path)
            return True

    def note(self, card_id, text):
        """The learner asks for more without answering the card: the tutor's wait wakes with it, the card stays up."""
        text = str(text or "").strip()[:600]
        if not text:
            return {"error": "Empty."}
        with self.cond:
            c = self.s.get("card")
            if not c or c["id"] != card_id:
                return {"error": "That card has been replaced."}
            self.s["note"] = {"card": card_id, "text": text, "at": time.time()}
            self._log("You", "? " + text)
            self._save()
            return {"ok": True}

    def submit(self, card_id, data):
        with self.cond:
            c, sub = self.s.get("card"), self.s.get("sub")
            if not c or c["id"] != card_id:
                return {"error": "That card has been replaced."}
            if sub and sub["card"] == card_id:
                return {"error": "Already handed in.", "result": c.get("result")}
            return {"ok": True, "result": self._submit(c, data, auto=bool((data or {}).pop("auto", False)))}

    def upload(self, card_id, name, data_url):
        m = re.match(r"^data:(image/(png|jpe?g|heic|webp|gif));base64,(.+)$", data_url or "", re.S)
        if not m:
            return {"error": "Images only."}
        raw = base64.b64decode(m.group(3))
        if len(raw) > MAX_UPLOAD:
            return {"error": "That image is over 12 MB."}
        ext = {"jpeg": "jpg", "jpg": "jpg"}.get(m.group(2), m.group(2))
        subj = self.subjects().get(self.s.get("subject") or "")
        base = Path(self.folder(subj)) if subj and self.folder(subj) else self.path.parent
        out = base / "uploads" / datetime.now().strftime("%Y-%m-%d")
        out.mkdir(parents=True, exist_ok=True)
        stem = re.sub(r"[^\w-]+", "-", Path(name or "photo").stem)[:40] or "photo"
        f = out / f"{datetime.now():%H%M%S}-{stem}.{ext}"
        f.write_bytes(raw)
        return {"ok": True, "path": str(f)}

    # ---------- tutor side ----------
    def begin(self, subject, who=None):
        """A block starts: new subject, clean card area, history kept for the day only."""
        with self.cond:
            today = datetime.now().strftime("%Y-%m-%d")
            if self.s.get("day") != today:
                self.s["history"] = []
                self.s["last"] = None
            self.s.update(day=today, subject=subject, who=who, card=None, say=None, sub=None, draft=None, ended=None)
            if self.s["history"] and self.s["history"][-1].get("kind") != "begin":
                self._log(self._who(), "", kind="begin", subject=subject)
            self._save()
            return {"ok": True, "page": self.page_open()}

    def post(self, card):
        t = card.get("type")
        if t not in TYPES:
            return {"error": f"type must be one of {', '.join(TYPES)}"}
        need = {"question": ["prompt"], "passage": ["prompt", "lines"], "canvas": ["prompt"], "mcq": ["items"],
                "choice": ["prompt", "options"], "close": ["prompt"], "lesson": ["steps"], "review": []}[t]
        missing = [k for k in need if not card.get(k)]
        if missing:
            return {"error": f"{t} card needs: {', '.join(missing)}"}
        if t == "lesson":
            err = check_lesson(card)
            if err:
                return {"error": err}
        kept = keep_source(card, self.s.get("card"))   # the text on screen stays under a follow-up card
        err = keep_pins(card, self.s.get("card"), kept)   # the question they are answering and what they have written for it
        if err:
            return {"error": err}
        err = give_context(card, self.s.get("last") or self.s.get("sub"), kept)   # what the question points at is on the card
        if err:
            return {"error": err}
        if t == "review":
            err = prep_review(card, self.s.get("last") or self.s.get("sub"))
            if err:
                return {"error": err}
        elif card.get("notes") is not None:
            err = check_notes(card["notes"], note_text({**kept, **card}))
            if err:
                return {"error": err}
        err = take_card_media(card, self.path.parent / "media")
        if err:
            return {"error": err}
        with self.cond:
            card = {**kept, **{k: v for k, v in card.items() if k not in ("keep", "shelf", "room")}}
            c = {k: v for k, v in card.items() if k not in ("say", "subject", "who")}
            c["id"] = uuid.uuid4().hex[:8]
            c["posted"] = time.time()
            if t == "mcq":
                for n, it in enumerate(c["items"], 1):
                    k, o = it.get("k"), it.get("o") or []
                    if not it.get("q") or len(o) < 2:
                        return {"error": f"mcq item {n} needs q and at least two choices in o"}
                    if not isinstance(k, int) or isinstance(k, bool) or not 0 <= k < len(o):
                        return {"error": f"mcq item {n}: k must be the 0-based index of the key (0 to {len(o) - 1}), not {k!r}"}
                c["_keys"] = [it.get("k") for it in c["items"]]
                c["items"] = [{k: v for k, v in it.items() if k != "k"} for it in c["items"]]
                c.setdefault("minutes", round(len(c["items"]) * 1.1, 1))
            if t == "canvas":
                c.setdefault("minutes", 40)
            if card.get("subject"):
                self.s["subject"] = card["subject"]
            if card.get("who"):
                self.s["who"] = card["who"]
            self.s.update(card=c, sub=None, draft=None, ended=None)
            if card.get("say"):
                self.s["say"] = {"text": str(card["say"])[:1500], "at": time.time()}
                self._log(self._who(), card["say"])
            self._log(self._who(), asked(c), kind="card", card=c["id"], type=t)
            self._save()
            return {"ok": True, "id": c["id"], "page": self.page_open(), "kept": sorted(kept),
                    "pins": [k for k in ("task", "work") if isinstance(c.get(k), dict)]}

    def notes(self, notes, add=False):
        """Highlights and margin notes on the card that's up, without replacing it (room.py note / notes)."""
        with self.cond:
            c = self.s.get("card")
            if not c:
                return {"error": "No card is up."}
            text = note_text(c)
            if text is None:
                return {"error": "This card has no text to mark: post a review card, or a card with lines."}
            new = (list(c.get("notes") or []) if add else []) + list(notes or [])
            err = check_notes(new, text)
            if err:
                return {"error": err}
            c["notes"] = new
            self._save()
            return {"ok": True, "count": len(new)}

    def say(self, text, end=False):
        with self.cond:
            self.s["say"] = {"text": str(text)[:1500], "at": time.time()}
            self._log(self._who(), text)
            if end:
                self.s.update(card=None, ended=time.time())
            self._save()
            return {"ok": True}

    def wait(self, card_id=None, timeout=540):
        """Block until the learner submits the current card (or card_id), it is replaced, or timeout."""
        stop = time.time() + max(1, min(float(timeout), 3600))
        with self.cond:
            card_id = card_id or (self.s.get("card") or {}).get("id")
            while True:
                self._auto_submit()
                c, sub = self.s.get("card"), self.s.get("sub")
                if not card_id or not c:
                    return {"status": "none"}
                if not c or c["id"] != card_id:
                    return {"status": "replaced"}
                note, say = self.s.get("note"), self.s.get("say")
                if note and note.get("card") == card_id and (not say or say["at"] < note["at"]) and not (sub and sub["card"] == card_id):
                    return {"status": "note", "text": note["text"]}
                if sub and sub["card"] == card_id:
                    return {"status": "submitted", "card": {k: v for k, v in c.items() if k != "_keys"} | {"keys": c.get("_keys")},
                            "submission": sub, "text": summarize(c, sub["data"], c.get("result"), sub.get("auto"), full=True, sub_at=sub["at"])}
                left = stop - time.time()
                if left <= 0:
                    return {"status": "timeout", "draft": (self.s.get("draft") or {}) if (self.s.get("draft") or {}).get("card") == card_id else None}
                self.cond.wait(min(left, 2.0))


def initials(name):
    parts = [p for p in re.split(r"\s+", re.sub(r"^(Mr|Ms|Mrs|Dr)\.?\s+", "", str(name or ""))) if p]
    if not parts:
        return "·"
    return (parts[0][0] + (parts[-1][0] if len(parts) > 1 else "")).upper()


def summarize(card, data, result=None, auto=False, full=False, sub_at=None):
    """One readable account of a submission: short for the page's history, full for the tutor."""
    t, lim = card["type"], (None if full else 1200)
    cut = (lambda s: s) if full else (lambda s: s if len(s) <= lim else s[:lim].rsplit(" ", 1)[0] + "…")
    photos = data.get("photos") or []
    tail = ("\n" if full else " ") + "Photos: " + ", ".join(photos) if photos else ""
    if t in ("question", "passage"):
        return cut(str(data.get("answer") or "").strip() or "(no text)") + tail
    if t == "canvas":
        text = str(data.get("text") or "").strip()
        words = len(text.split())
        how = "auto-handed in at 0:00" if auto else "handed in"
        if not full:
            return f"Essay, {words} words, {how}."
        left = ""
        if card.get("deadline") and not auto:
            secs = max(0, int(card["deadline"] - (sub_at or time.time())))
            left = f", {secs // 60}:{secs % 60:02d} left on the clock"
        return f"Claim: {str(data.get('claim') or '').strip()}\nEssay ({words} words, {how}{left}):\n{text}"
    if t == "mcq":
        if not result:
            return "MCQ set handed in."
        line = f"MCQ {result['score']} of {result['total']}" + (" (auto-handed in at 0:00)" if auto else "")
        if not full:
            return line
        L = "ABCDE"
        rows = []
        items = card.get("items") or []
        for i, (a, k, ok) in enumerate(zip(result["answers"], result["keys"], result["right"])):
            o = (items[i].get("o") if i < len(items) else None) or []
            text = lambda j: (" " + str(o[int(j)])[:90]) if j is not None and int(j) < len(o) else ""
            if ok:
                rows.append(f"{i + 1}. right, {L[int(a)]}{text(a)}")
            else:
                pick = (L[int(a)] + text(a)) if a is not None else "blank"
                rows.append(f"{i + 1}. wrong: picked {pick}; key {L[int(k)] if k is not None else '?'}{text(k)}")
        return line + "\n" + "\n".join(rows)
    if t == "choice":
        return f"Chose: {data.get('choice')}" + (f"\n{data.get('why')}" if data.get("why") else "")
    if t == "review":
        head = f"Read your notes ({len(card.get('notes') or [])})."
        ans = str(data.get("answer") or "").strip()
        if not card.get("prompt"):
            return head if full else "Got it."
        return f"{head}\nQuestion: {card.get('prompt')}\n{ans or '(no text)'}" if full else cut(ans or "(no text)")
    if t == "lesson":
        n = len(card.get("steps") or [])
        took = ""
        if full and sub_at and card.get("posted"):
            secs = max(0, int(sub_at - card["posted"]))
            took = f", {secs // 60}:{secs % 60:02d} on it"
        head = f"Went through the lesson ({n} steps{took})."
        k = card.get("check") or {}
        if not k:
            return head if full else "Got it."
        if k.get("options"):
            body = f"Chose: {data.get('choice')}" + (f"\n{data.get('why')}" if data.get("why") else "")
        else:
            body = str(data.get("answer") or "").strip() or "(no text)"
        return f"{head}\nQuestion: {k.get('prompt')}\n{body}" if full else cut(body)
    if t == "close":
        out = cut(str(data.get("retry") or "").strip() or "(no text)")
        if data.get("question"):
            out += ("\nQuestion they wrote: " if full else " · Q: ") + cut(str(data["question"]).strip())
        return out + tail
    return json.dumps(data)[:400]


# ---------- lesson cards: steps beside a graph, number line, table, flow or text ----------
# Graph expressions use a small language that room.html also parses (keep the two in step):
# + - * / ^, implicit products (3x, 2(x+1)), the functions below, pi and e, x or t as the variable.
NAMES = ("asin", "acos", "atan", "sqrt", "floor", "ceil", "sign", "sin", "cos", "tan", "abs", "exp", "log", "min", "max", "ln", "pi")
VISUALS = ("graph", "numberline", "table", "flow", "figure", "image", "video", "pdf", "lines")


def _arr(v):
    return [] if v is None else v if isinstance(v, list) else [v]


def _tokens(src):
    s = str(src).replace("\u2212", "-").replace("\u03c0", "pi").replace("\u00b7", "*").replace("\u00d7", "*")
    out, i = [], 0
    while i < len(s):
        ch = s[i]
        if ch in " \t\n\r\f\v":
            i += 1
            continue
        m = re.match(r"[0-9]+\.?[0-9]*|\.[0-9]+", s[i:])
        if m:
            out.append(("n", m.group()))
            i += len(m.group())
            continue
        if ch in "+-*/^(),":
            out.append((ch, ch))
            i += 1
            continue
        if ch.isascii() and ch.isalpha():
            w = next((f for f in NAMES if s.startswith(f, i)), ch)
            out.append(("id", w))
            i += len(w)
            continue
        raise ValueError(f'unexpected "{ch}"')
    return out


def check_expr(src, names):
    """None when src is a number or parses using only `names` (plus pi, e and the functions); else what's wrong."""
    if isinstance(src, (int, float)) and not isinstance(src, bool):
        return None
    if not isinstance(src, str) or not src.strip():
        return "empty"
    try:
        t = _tokens(src)
    except ValueError as e:
        return str(e)
    p = [0]
    peek = lambda: t[p[0]][0] if p[0] < len(t) else None

    def eat(k):
        if peek() != k:
            raise ValueError(f"expected {k}" + (f" before {t[p[0]][1]}" if p[0] < len(t) else " at the end"))
        p[0] += 1

    def expr():
        term()
        while peek() in ("+", "-"):
            p[0] += 1
            term()

    def term():
        unary()
        while True:
            if peek() in ("*", "/"):
                p[0] += 1
                unary()
            elif peek() in ("n", "id", "("):
                power()
            else:
                return

    def unary():
        if peek() in ("+", "-"):
            p[0] += 1
            unary()
        else:
            power()

    def power():
        atom()
        if peek() == "^":
            p[0] += 1
            unary()

    def atom():
        if p[0] >= len(t):
            raise ValueError("ends too soon")
        k, v = t[p[0]]
        p[0] += 1
        if k == "n":
            return
        if k == "(":
            expr()
            eat(")")
            return
        if k == "id":
            if v in NAMES and v != "pi":
                if peek() == "(":
                    p[0] += 1
                    expr()
                    while peek() == ",":
                        p[0] += 1
                        expr()
                    eat(")")
                else:
                    power()
                return
            if v in ("pi", "e") or v in names:
                return
            raise ValueError(f"unknown name {v}" + (" (the slider is " + ", ".join(sorted(n for n in names if n not in "xt")) + ")" if set(names) - {"x", "t"} else ""))
        raise ValueError(f"unexpected {v}")

    try:
        expr()
        if p[0] < len(t):
            raise ValueError(f"unexpected {t[p[0]][1]}")
    except ValueError as e:
        return str(e)
    except RecursionError:
        return "too deeply nested"
    return None


def _num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def check_graph(g):
    if not isinstance(g, dict):
        return "must be an object"
    for key in ("x", "y"):
        r = g.get(key)
        if r is not None and not (isinstance(r, list) and len(r) == 2 and all(_num(v) for v in r) and r[0] < r[1]):
            return f"{key} must be [low, high] with low < high"
    names = set()
    sl = g.get("slider")
    if sl is not None:
        if not isinstance(sl, dict) or not re.fullmatch(r"[a-df-wyzA-Z]", str(sl.get("name") or "")):
            return "slider needs a one-letter name (not x or e)"
        if not (_num(sl.get("min")) and _num(sl.get("max")) and sl["min"] < sl["max"]):
            return "slider needs numbers min < max"
        if "step" in sl and not (_num(sl["step"]) and sl["step"] > 0 and (sl["max"] - sl["min"]) / sl["step"] <= 100000):
            return "slider step must be a positive number"
        if "value" in sl and not (_num(sl["value"]) and sl["min"] <= sl["value"] <= sl["max"]):
            return "slider value must be a number between min and max"
        names.add(sl["name"])
    plot = names | {"x", "t"}
    fns = _arr(g.get("fn")) + _arr(g.get("fns"))
    if not fns and not g.get("points"):
        return "needs fn, fns or points"

    def ref(r, what):
        if isinstance(r, int) and not isinstance(r, bool):
            return None if 0 <= r < len(fns) else f"{what}: fn {r} but there are {len(fns)} functions (0-based)"
        err = check_expr(r, plot)
        return f'{what} "{r}": {err}' if err else None

    def val(v, what):
        err = check_expr(v, names)
        return f'{what} "{v}": {err}' if err else None

    errs = []
    for key in ("shade", "tangent", "secant", "points", "vlines", "hlines", "readout"):
        bad = [e for e in _arr(g.get(key)) if not isinstance(e, dict)]
        if bad:
            return f"{key} entries must be objects, not {json.dumps(bad[0])[:40]}"
    for r in _arr(g.get("readout")):
        for k in ("area", "slope"):
            if k in r and not isinstance(r[k], dict):
                return f"readout {k} must be an object like {{\"fn\": 0, ...}}"
    for f in fns:
        if isinstance(f, dict) and f.get("points") is not None and not f.get("fn"):
            pts = f["points"]
            if not (isinstance(pts, list) and pts and all(isinstance(q, list) and len(q) == 2 and all(_num(v) for v in q) for q in pts)):
                errs.append("points must be [[x, y], ...] numbers")
            continue
        src = f if isinstance(f, str) else f.get("fn") if isinstance(f, dict) else None
        if isinstance(f, dict) and f.get("color") is not None and not isinstance(f["color"], str):
            errs.append("color must be a word or #hex")
        err = check_expr(src, plot)
        if err:
            errs.append(f'fn "{src}": {err}')
        if isinstance(f, dict) and f.get("domain") is not None:
            d = f["domain"]
            if not (isinstance(d, list) and len(d) == 2):
                errs.append("domain must be [from, to]")
            else:
                errs += [e for e in (val(d[0], "domain"), val(d[1], "domain")) if e]
    for s in _arr(g.get("shade")):
        errs += [ref(s.get("fn", 0), "shade")] + [val(s[k], "shade " + k) for k in ("from", "to") if k in s]
    for tn in _arr(g.get("tangent")):
        errs += [ref(tn.get("fn", 0), "tangent"), val(tn.get("at"), "tangent at")]
    for sc in _arr(g.get("secant")):
        errs += [ref(sc.get("fn", 0), "secant"), val(sc.get("from"), "secant from"), val(sc.get("to"), "secant to")]
    for pt in _arr(g.get("points")):
        if "on" in pt:
            errs += [ref(pt["on"], "point on"), val(pt.get("x"), "point x")]
        elif isinstance(pt.get("at"), list) and len(pt["at"]) == 2:
            errs += [val(pt["at"][0], "point"), val(pt["at"][1], "point")]
        else:
            errs.append('a point needs "at": [x, y], or "on": fn and "x"')
    errs += [val(l.get("x"), "vline") for l in _arr(g.get("vlines"))] + [val(l.get("y"), "hline") for l in _arr(g.get("hlines"))]
    for r in _arr(g.get("readout")):
        if r.get("area"):
            a = r["area"]
            errs += [ref(a.get("fn", 0), "readout area")] + [val(a[k], "readout " + k) for k in ("from", "to") if k in a]
        elif r.get("slope"):
            errs += [ref(r["slope"].get("fn", 0), "readout slope"), val(r["slope"].get("at"), "readout slope at")]
        elif "value" in r:
            errs.append(val(r["value"], "readout value"))
        else:
            errs.append("a readout needs area, slope or value")
    errs = [e for e in errs if e]
    return errs[0] if errs else None


def check_lesson(card):
    steps = card.get("steps")
    if card.get("lines") is not None and not (isinstance(card["lines"], list) and all(isinstance(l, str) for l in card["lines"])):
        return "lines must be a list of strings, one per line"
    if not isinstance(steps, list) or not steps:
        return "lesson card needs steps: a list of {text, and optionally graph | numberline | table | flow | figure | image | video | lines}"
    for n, st in enumerate(steps, 1):
        if isinstance(st, str):
            continue
        if not isinstance(st, dict):
            return f"step {n} must be text or an object"
        if not (st.get("text") or any(st.get(k) for k in VISUALS)):
            return f"step {n} needs text or a visual"
        if st.get("lines") is not None and not (isinstance(st["lines"], list) and all(isinstance(l, str) for l in st["lines"])):
            return f"step {n} lines must be a list of strings, one per line"
        if st.get("graph"):
            err = check_graph(st["graph"])
            if err:
                return f"step {n} graph: {err}"
        nl = st.get("numberline")
        if nl:
            r = nl.get("range") if isinstance(nl, dict) else None
            if not (isinstance(r, list) and len(r) == 2 and all(_num(v) for v in r) and r[0] < r[1]):
                return f"step {n} numberline needs range: [low, high]"
            if "step" in nl and not (_num(nl["step"]) and nl["step"] > 0 and (r[1] - r[0]) / nl["step"] <= 200):
                return f"step {n} numberline step must be a positive number giving at most 200 ticks"
            for key, fields in (("points", ("at",)), ("intervals", ("from", "to")), ("moves", ("from", "to"))):
                for item in _arr(nl.get(key)):
                    if not isinstance(item, dict):
                        return f"step {n} numberline {key} entries must be objects"
                    for f in fields:
                        err = check_expr(item.get(f) if isinstance(item, dict) else None, set())
                        if err:
                            return f"step {n} numberline {key} {f}: {err}"
        tb = st.get("table")
        if tb and not (isinstance(tb, dict) and isinstance(tb.get("rows"), list) and all(isinstance(r, list) for r in tb["rows"])
                       and (tb.get("head") is None or isinstance(tb["head"], list))):
            return f"step {n} table needs rows: [[...], ...] and optionally head: [...]"
        fl = st.get("flow")
        if fl and not (isinstance(fl, list) or (isinstance(fl, dict) and isinstance(fl.get("items"), list))):
            return f"step {n} flow is a list of strings, or {{items, at}}"
        if isinstance(fl, dict) and fl.get("at") is not None:
            items, at = [str(x) for x in fl["items"]], fl["at"]
            ok = at in items if isinstance(at, str) else (isinstance(at, int) and not isinstance(at, bool) and 1 <= at <= len(items))
            if not ok and items:
                return (f'step {n} flow: "at" counts from 1 (1 lights "{items[0][:30]}", {len(items)} lights "{items[-1][:30]}"), '
                        f'or is the item\'s own text; got {at!r}')
    k = card.get("check")
    if k is not None:
        if not isinstance(k, dict) or not k.get("prompt"):
            return "check needs a prompt"
        if k.get("options") is not None and not (isinstance(k["options"], list) and len(k["options"]) >= 2
                                                 and all(isinstance(o, str) and o.strip() for o in k["options"])):
            return "check options needs at least two strings"
    return None


# ---------- figures, images and videos the tutor made
# A card names a file on disk; it is copied into <data>/media under its content hash, and the page only
# ever loads /media/<hash>.<ext>. So the room serves nothing but files a tutor put on a card.

MEDIA = {"figure": (".html", ".htm"), "image": (".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".avif"),
         "video": (".mp4", ".webm", ".mov", ".m4v"), "pdf": (".pdf",)}
MEDIA_MAX = {"figure": 25 << 20, "image": 25 << 20, "video": 400 << 20, "pdf": 80 << 20}
# Added to a figure: no page margins (anatomy's .iso-page centres itself with big ones) and no caption paragraph
# (the card's own text explains), and the figure's height reported so the frame fits it without a scrollbar.
EMBED = ('<style>html,body{margin:0!important}body{display:flow-root!important}.iso-page{margin:0 auto!important;width:100%!important}'
         '.iso-figure{margin:0!important}.iso-legend{padding:0 14px 14px!important}.iso-caption{display:none!important}</style>'
         '<script>(()=>{const b=document.body,s=()=>parent.postMessage({roomFigure:1,'
         'h:Math.ceil(Math.max(b.scrollHeight,b.getBoundingClientRect().height))},"*");'
         'addEventListener("load",s);new ResizeObserver(s).observe(b);s()})()</script>')


def _store(path, kind, media_dir):
    p = str(path).strip()
    if re.fullmatch(r"/media/[0-9a-f]{16}\.[a-z0-9]{2,5}", p) and (media_dir / p[7:]).is_file():
        return p                                    # already in the store (a card sent again)
    f = Path(os.path.expanduser(p))
    if not f.is_absolute():
        return (f"{p} isn't an absolute path",)
    if not f.is_file():
        return (f"no file at {p}",)
    ext = f.suffix.lower()
    if ext not in MEDIA[kind]:
        return (f"{f.name}: a {kind} is {' '.join(MEDIA[kind])}",)
    size = f.stat().st_size
    if size > MEDIA_MAX[kind]:
        return (f"{f.name} is {size >> 20} MB; a {kind} can be {MEDIA_MAX[kind] >> 20} MB",)
    media_dir.mkdir(parents=True, exist_ok=True)
    if kind == "figure":
        text = f.read_text(errors="replace")
        tags = re.sub(r"(?is)(<script\b[^>]*>).*?(</script>)", r"\1\2", text)
        local = [m for m in re.findall(r"""(?is)<(?:img|script|link|source|video|audio|iframe)\b[^>]*?\b(?:src|href)\s*=\s*["']([^"']+)["']""", tags)
                 if not re.match(r"(?i)(https?:|data:|blob:|#|//)", m)]
        if local:
            return (f"{f.name} loads {local[0]} from beside it; a figure has to be one self-contained HTML file (anatomy's build output is)",)
        i = text.lower().rfind("</body>")
        raw = (text[:i] + EMBED + text[i:] if i >= 0 else text + EMBED).encode()
        out = media_dir / (hashlib.sha1(raw).hexdigest()[:16] + ".html")
        if not out.exists():
            out.with_suffix(".part").write_bytes(raw)
            out.with_suffix(".part").replace(out)
        return "/media/" + out.name
    h = hashlib.sha1()
    with open(f, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    out = media_dir / (h.hexdigest()[:16] + (".mp4" if ext == ".m4v" else ".jpg" if ext == ".jpeg" else ext))
    if not out.exists():
        tmp = media_dir / (out.name + ".part")
        shutil.copyfile(f, tmp)
        tmp.replace(out)
    return "/media/" + out.name


def take_media(obj, where, media_dir):
    """Each figure / image / video in obj becomes {src, light?, poster?, ...} pointing into the store."""
    for kind in MEDIA:
        v = obj.get(kind)
        if v is None:
            continue
        if isinstance(v, str):
            v = {"src": v}
        if not isinstance(v, dict) or not isinstance(v.get("src"), str):
            return f"{where}{kind} is a file path, or {{\"src\": path, \"light\": path for the light theme, \"alt\", \"title\"}}"
        out = dict(v)
        for key in ("src", "light", "poster"):
            if v.get(key) is None:
                continue
            r = _store(v[key], "image" if key == "poster" else kind, media_dir)
            if isinstance(r, tuple):
                return f"{where}{kind} {key}: {r[0]}"
            out[key] = r
        obj[kind] = out
    return None


def take_card_media(card, media_dir):
    err = take_media(card, "", media_dir)
    if err:
        return err
    res = card.get("resources")          # several pictures or PDFs on one card, shown as tabs of one viewer
    if res is not None:
        if not isinstance(res, list) or not res or len(res) > 8 or not all(isinstance(x, dict) and (x.get("image") or x.get("pdf")) for x in res):
            return 'resources is a list of up to 8 items, each {"image": path} or {"pdf": path}, with an optional "title" (and "page" for a pdf)'
        for n, item in enumerate(res, 1):
            err = take_media(item, f"resource {n} ", media_dir)
            if err:
                return err
    if card.get("type") != "lesson":
        return None
    for n, st in enumerate(card.get("steps") or [], 1):
        if isinstance(st, dict):
            err = take_media(st, f"step {n} ", media_dir)
            if err:
                return err
    return None


# ---------- review cards and notes: the learner's own text on screen, with the tutor's highlights
TONES = ("subject", "amber", "good", "red")
QUOTE_CHARS = {"'": "['’‘]", "’": "['’‘]", "‘": "['’‘]",
               '"': '["“”]', "“": '["“”]', "”": '["“”]'}


def quote_re(q):
    """The same match the page makes: any run of whitespace matches any other, straight and curly quotes match."""
    return r"\s+".join("".join(QUOTE_CHARS.get(ch, re.escape(ch)) for ch in tok) for tok in str(q).split())


def note_text(card):
    if card.get("type") == "review":
        return str(card.get("text") or "")
    lines = card.get("lines")
    if isinstance(lines, list) and lines:
        return "\n".join(str(l) for l in lines)
    return card["text"] if isinstance(card.get("text"), str) and card["text"].strip() else None   # a review's text kept under a follow-up


# ---------- the text stays up
# A follow-up card that brings no text or picture of its own keeps the one on screen: the poem, the prompt, the graph,
# the learner's own essay with its notes. So the learner can still see what a question is about after answering the
# one before it. A card drops it with "keep": false (or an empty "lines"); a lesson or a review brings its own, and
# a close keeps it only with "keep": true.
SOURCE_KEYS = ("lines", "text", "figure", "image", "video", "pdf", "resources")


def keep_source(card, prev):
    if not prev or card.get("type") in ("lesson", "review") or card.get("keep") is False:
        return {}
    if card.get("type") == "close" and card.get("keep") is not True:
        return {}                                   # the close is the unaided retry: no text or notes unless the tutor asks
    if any(k in card for k in SOURCE_KEYS) or card.get("file") or card.get("from") == "answer":
        if "lines" in card and not card["lines"]:
            card.pop("lines")                       # "lines": [] means: take the text down
        return {}
    kept = {}
    if isinstance(prev.get("lines"), list) and prev["lines"]:
        kept = {k: prev[k] for k in ("lines", "cite", "from", "notes") if prev.get(k) is not None}
    elif isinstance(prev.get("text"), str) and prev["text"].strip():
        kept = {k: prev[k] for k in ("text", "cite", "title", "notes") if prev.get(k) is not None}
    else:
        kept = {k: prev[k] for k in ("figure", "image", "video", "pdf", "resources") if prev.get(k)}
    if "notes" in card:
        kept.pop("notes", None)
    if "cite" in card:
        kept.pop("cite", None)
    return kept


# ---------- what the question points at is on the card
# The learner never scrolls up to find what a question is about. A card can carry "context": words shown right above the
# prompt ({"from": "answer"} for their last written answer, or a string, or {"text", "cite"}). A prompt that points at
# their own words, at numbered lines or at a picture, with nothing on the card to match, is sent back to the tutor with
# what to add; "context": false says the question has nothing to look back at.
LINE_REF = re.compile(r"\blines?\s+\d+", re.I)
PICTURE_REF = re.compile(r"\b(?:the|this|that)\s+(passage|poem|stanza|excerpt|graph|table|figure|diagram|prompt|picture|image|photo|pdf|page|slide|handout|case study|chart|map)\b", re.I)


# A card that works on the learner's own writing: "rewrite sentence two", "your thesis", "fix the claim".
WRITING = re.compile(r"\b(?:your\s+(?:own\s+|first\s+|second\s+|third\s+|last\s+|new\s+|whole\s+)?|(?:rewrite|revise|redraft|reword|fix|tighten)\s+(?:the\s+|that\s+|this\s+|your\s+)?)"
                     r"(?:thesis|claim|sentences?|paragraph|essay|draft|intro|introduction|topic sentence|clause|meaning clause|body paragraph|conclusion)\b"
                     r"|\bsentence\s+(?:one|two|three|four|five|\d)\b", re.I)
YOURS = re.compile(r"^\s*(?:your|you)\b", re.I)
PIN_SHAPE = 'a string, a list of lines, {"text" or "lines": …, "cite": "…"}, or false'


def _pin(v):
    """"task" or "work" as the tutor sends it -> {"text" | "lines", "cite"}; None when the shape is wrong."""
    if isinstance(v, str) and v.strip():
        return {"text": v.strip()[:6000]}
    if isinstance(v, list) and v and all(isinstance(x, str) for x in v):
        return {"lines": [x[:1200] for x in v][:60]}
    if isinstance(v, dict):
        out = {}
        if isinstance(v.get("lines"), list) and v["lines"] and all(isinstance(x, str) for x in v["lines"]):
            out["lines"] = [x[:1200] for x in v["lines"]][:60]
        elif isinstance(v.get("text"), str) and v["text"].strip():
            out["text"] = v["text"].strip()[:6000]
        else:
            return None
        if v.get("cite"):
            out["cite"] = str(v["cite"]).strip()[:200]
        return out
    return None


def keep_pins(card, prev, kept):
    """The two things that stay at the top left for as long as a task lasts: the question the learner is answering
    ("task") and what they have written for it so far ("work"). The tutor sends each once and the server carries it
    onto every later card; sending one again replaces it, false takes it down. A new task drops the old work.
    A set and "keep": false start clean; a close keeps the task and drops the work. Earlier drafts are not carried anywhere.
    Returns an error for the tutor when a card works on the learner's writing and either one has not been decided."""
    t, prev = card.get("type"), prev or {}
    clean = card.get("keep") is False or t in ("mcq", "canvas")
    for k in ("task", "work"):
        if k in card and card[k] is not False:
            pin = _pin(card[k])
            if pin is None:
                return f'"{k}" is {PIN_SHAPE}'
            card[k] = pin
    if clean:
        for k in ("task", "work"):
            if card.get(k) is False:
                card.pop(k)
        return None
    if t == "close" and card.get("keep") is not True:
        # The close is the retry with no cues. The question they are answering is not a cue, so it stays; what they wrote before is, so it goes.
        if "task" not in card and isinstance(prev.get("task"), dict):
            card["task"] = prev["task"]
        for k in ("task", "work"):
            if card.get(k) is False:
                card.pop(k)
        return None
    mine = _sheet({**kept, **card}) if t != "lesson" else None
    old = _sheet(prev)
    if "task" not in card:
        if "task" in prev:
            card["task"] = prev["task"]
        elif prev.get("type") == "canvas" and prev.get("prompt"):
            card["task"] = {"text": str(prev["prompt"]), "cite": "Prompt"}      # the essay's prompt stays through the feedback on it
        elif old and mine and (old.get("lines") or old.get("text")) and old.get("cite") and _sheet_key(old) != _sheet_key(mine) \
                and not YOURS.match(str(old["cite"])) and (t == "review" or YOURS.match(str(mine.get("cite") or ""))):
            card["task"] = {k: old[k] for k in ("lines", "text", "cite") if old.get(k)}   # a prompt, then their writing about it
    if "work" not in card and "work" in prev and card.get("task") == prev.get("task"):
        card["work"] = prev["work"]
    prompt = str((card.get("check") or {}).get("prompt") or "") if t == "lesson" else str(card.get("prompt") or "")
    writing = t == "review" or bool(WRITING.search(prompt)) or bool(mine and YOURS.match(str(mine.get("cite") or "")))
    if not writing:
        return None
    need = []
    if "task" not in card:
        need.append('the question they are writing for is not on screen. Pin it once: "task": {"text": "<the essay question, or just its task sentence>", '
                    '"cite": "AP 2023 Q3"}. It stays at the top left on every card until you send another; "task": false if no question stands behind this writing')
    if "work" not in card and t != "review":          # a review card's own text is their writing, whole
        need.append('what they have written for it so far is not on screen. Pin it: "work": {"lines": ["<thesis>", "<sentence one>", "<sentence two>"], '
                    '"cite": "Your paragraph so far"}: the current version only, whole, in order, never a list of drafts. Send "work" again whenever a sentence changes; '
                    '"work": false if this card\'s own text already is everything they have written')
    if need:
        return "This card works on their own writing, and " + "; and ".join(need) + ". Context is what they need to do this question: the question, what they wrote, the line you are pointing at. Nothing else."
    return None


def _last_words(sub):
    d = (sub or {}).get("data") or {}
    return next((str(d[k]).strip() for k in ("text", "answer", "retry", "why") if str(d.get(k) or "").strip()), "")


def give_context(card, last, kept):
    """Normalise card["context"]; return an error for the tutor when the prompt points at a line or a picture that isn't on the card.
    Their own writing is not checked here: it is the pinned "work" (keep_pins). Until 11-14 a prompt saying "your thesis" was sent
    back unless some words of theirs were on the card, and the tutor answered by pasting their last answer onto every card."""
    t = card.get("type")
    ctx = card.get("context")
    if isinstance(ctx, str) and ctx.strip():
        card["context"] = {"text": ctx.strip()[:6000]}
    elif isinstance(ctx, dict):
        if ctx.get("from") == "answer":
            words = _last_words(last)
            if not words:
                return 'context from: "answer", but there is no written answer yet today; quote the words yourself with "context": "…"'
            card["context"] = {"text": words[:6000], "who": "You"}
        elif isinstance(ctx.get("text"), str) and ctx["text"].strip():
            card["context"] = {k: str(ctx[k]).strip()[:6000 if k == "text" else 200] for k in ("text", "cite", "who") if ctx.get(k)}
        else:
            return 'context is {"from": "answer"}, a string, or {"text": "…", "cite": "…"}'
    elif ctx is not None and ctx is not False:
        return 'context is {"from": "answer"}, a string, {"text": "…", "cite": "…"}, or false'
    explicit = "context" in card
    if ctx is False:
        card.pop("context")
    if explicit or t in ("mcq", "close", "canvas"):
        return None                      # the tutor has decided; a set carries its own stems, a close and a timed essay start clean
    prompt = str((card.get("check") or {}).get("prompt") or "") if t == "lesson" else str(card.get("prompt") or "")
    own_text = t == "review" or any(isinstance(x.get("text"), str) and x["text"].strip() for x in (card, kept)) or card.get("file") or card.get("from") == "answer"
    lines = any(isinstance(x.get("lines"), list) and x["lines"] for x in (card, kept))
    step_pics = t == "lesson" and any(isinstance(s, dict) and any(s.get(k) for k in VISUALS) for s in card.get("steps") or [])
    picture = lines or step_pics or any(x.get(k) for x in (card, kept) for k in ("figure", "image", "video", "pdf", "resources", "text"))
    m = LINE_REF.search(prompt)
    if m and not lines:
        return (f'The prompt points at "{m.group(0)}" but no text is on screen. Send the lines with this card (or quote the line in "context"); '
                '"context": false only if they do not need to see it.')
    m = PICTURE_REF.search(prompt)
    if m and not picture and not own_text:
        return (f'The prompt points at "{m.group(0)}" but nothing is on screen beside the card. Send it with this card (lines, figure, image) or quote it in "context"; '
                '"context": false only if they do not need to see it.')
    return None


def _sheet(c):
    """A card's own text or picture on its own, without the marks and notes: what keep_pins compares and pins."""
    if isinstance(c.get("lines"), list) and c["lines"]:
        return {k: c[k] for k in ("lines", "cite", "from") if c.get(k) is not None}
    if isinstance(c.get("text"), str) and c["text"].strip():
        return {k: c[k] for k in ("text", "title", "cite") if c.get(k)}
    if c.get("image"):
        return {"image": c["image"]}
    if c.get("type") == "canvas" and c.get("prompt"):
        return {"text": str(c["prompt"]), "cite": "Prompt"}       # the essay's prompt stays through the feedback on it
    return None


def _sheet_key(x):
    return json.dumps([x.get("lines"), x.get("text"), (x.get("image") or {}).get("src") if isinstance(x.get("image"), dict) else x.get("image")], sort_keys=True)


def asked(c):
    """What a card asked, in a line or two, for the transcript once it has been answered."""
    t = c.get("type")
    if t == "mcq":
        n = len(c.get("items") or [])
        return f"{n} question{'s' if n != 1 else ''}" + (f" · {c['source']}" if c.get("source") else "")
    if t == "lesson":
        return str(c.get("title") or (c.get("check") or {}).get("prompt") or "Lesson")
    if t == "review":
        return str(c.get("prompt") or c.get("title") or "Your writing, with notes")
    return str(c.get("prompt") or "")


def check_notes(notes, text):
    if text is None:
        return "notes need text to mark: a review card, or a card with lines"
    if not isinstance(notes, list):
        return "notes is a list of {quote, note, tone}"
    for n, x in enumerate(notes, 1):
        if not isinstance(x, dict) or not isinstance(x.get("quote"), str) or not x["quote"].strip():
            return f"note {n} needs quote: words copied from the text"
        if x.get("note") is not None and not isinstance(x["note"], str):
            return f"note {n}: note is the comment, a string"
        if x.get("tone") is not None and x["tone"] not in TONES:
            return f"note {n}: tone is one of {', '.join(TONES)}"
        hits = len(re.findall(quote_re(x["quote"]), text))
        q = x["quote"].strip()
        if not hits:
            return f'note {n}: "{q[:60]}" isn\'t in the text; copy the words exactly'
        k = x.get("n", 1)
        if not (isinstance(k, int) and not isinstance(k, bool) and 1 <= k <= hits):
            return f'note {n}: "{q[:40]}" appears {hits} time{"s" if hits > 1 else ""}; n picks which, 1 to {hits}'
    return None


def prep_review(card, sub):
    """text, or file (an essay on disk), or from: "answer" (the learner's last submission, word for word)."""
    if card.get("file"):
        f = Path(os.path.expanduser(str(card["file"])))
        if not f.is_absolute() or not f.is_file():
            return f"no file at {card['file']} (an absolute path)"
        if f.suffix.lower() not in (".md", ".txt", ".markdown"):
            return f"{f.name}: file is a .md or .txt"
        if f.stat().st_size > 400_000:
            return f"{f.name} is too long for one card"
        card["text"] = f.read_text(errors="replace")
        card.pop("file")
    elif card.get("from") == "answer":
        d = (sub or {}).get("data") or {}
        text = next((str(d[k]).strip() for k in ("text", "answer", "retry", "why") if str(d.get(k) or "").strip()), "")
        if not text:
            return "from: answer, but there's no written answer yet today"
        card["text"] = text
        card.pop("from")
    if not isinstance(card.get("text"), str) or not card["text"].strip():
        return "review card needs text, file (an absolute path) or from: \"answer\""
    return check_notes(card.get("notes") or [], card["text"])
