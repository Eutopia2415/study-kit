#!/usr/bin/env python3
"""The tutor's side of the room. See ROOM.md.

    room.py ask [--timeout S] < card.json   post a card, wait for the answer, print it
    room.py card < card.json                post a card only, print its id
    room.py wait [--card ID] [--timeout S]  wait for the answer to the current card
    room.py begin SUBJECT [--who NAME]      start a block: subject colour and name, clean card area
    room.py say "text"                      a reply with no new card ("yeah, keep going")
    room.py note "quote" ["comment"] [--tone amber] [--n 2]
                                            highlight words on the card that's up, with a margin note
    room.py notes < notes.json              replace all of them ([] clears)
    room.py end "text"                      last words; clears the card area
    room.py state                           what the room shows right now

Every subject has its own room. room.py picks yours from the folder you are working in (the subject's folder), so two
tutors open at once never post over each other; `begin SUBJECT` names it outright, and --room ID overrides both.

Exit code 0 unless something broke (1). Read the first line: "No answer yet" (call wait again),
"They ask, before answering: …" (reply with `say`, then wait again), or anything else, their answer.
A timeout is not an error, so a background wait that times out doesn't show up as a failed command.
"""
import json
import sys
import urllib.request

import os
ORIGIN = os.environ.get("STUDY_HALL_ROOM", "http://127.0.0.1:4417").rstrip("/")   # tests point this at a separate copy
BASE = ORIGIN + "/api/room/"
PAGE = ORIGIN + "/room"


def ensure_page(r):
    """The learner has to see the card: if no page is polling, bring the open room tab forward (or open one)."""
    if r.get("page") is False:
        how = call("show", {}).get("how", "opened")
        print(f"Room {how}: {PAGE}", file=sys.stderr)



ROOM = None   # this tutor's room: a subject id, or None for whichever room was used last


def call(path, body=None, timeout=30):
    if ROOM and body is not None:
        body = {**body, "room": ROOM} if isinstance(body, dict) else body
    elif ROOM:
        path += ("&" if "?" in path else "?") + "room=" + ROOM
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        try:
            return json.load(e)
        except ValueError:
            return {"error": f"HTTP {e.code}"}
    except (ConnectionRefusedError, urllib.error.URLError) as e:
        if isinstance(e, ConnectionRefusedError) or isinstance(getattr(e, "reason", None), ConnectionRefusedError):
            sys.exit(f"The Study Hall server isn't running at {ORIGIN}. Start it with Study Hall.command.")
        sys.exit(f"Lost the connection to the room ({e}). Run wait again; the card and any answer are kept.")
    except OSError as e:
        sys.exit(f"Lost the connection to the room ({e}). Run wait again; the card and any answer are kept.")


def arg(name, default=None):
    a = sys.argv
    return a[a.index(name) + 1] if name in a and a.index(name) + 1 < len(a) else default


def read_card():
    raw = sys.stdin.read()
    try:
        return json.loads(raw)
    except ValueError as e:
        sys.exit(f"The card isn't valid JSON: {e}")


def wait(card_id=None, timeout=540):
    q = f"wait?timeout={int(timeout)}" + (f"&card={card_id}" if card_id else "")
    r = call(q, timeout=timeout + 30)
    if r.get("status") == "submitted":
        print(r["text"])
        return 0
    if r.get("status") == "note":
        print("They ask, before answering: " + r["text"])
        st = call("state") or {}
        d = st.get("draft") or {}
        if d.get("text") and (st.get("card") or {}).get("id") == d.get("card"):
            print("What they have written so far:\n" + str(d["text"])[:4000])
        print("Reply with room.py say (the card stays up), then run wait again.")
        return 0
    if r.get("status") == "timeout":
        d = r.get("draft") or {}
        words = len(str(d.get("text") or "").split())
        print("No answer yet." + (f" Draft so far: {words} words." if words else "") + " Run wait again.")
        return 0
    if r.get("status") == "replaced":
        print("That card was replaced by a newer one.")
        return 1
    if r.get("status") == "none":
        print("No card is up.")
        return 1
    print(json.dumps(r))
    return 1


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    cmd = sys.argv[1]
    timeout = float(arg("--timeout", 540))
    global ROOM, PAGE
    ROOM = arg("--room") or os.environ.get("STUDY_HALL_ROOM_ID") or (sys.argv[2] if cmd == "begin" and len(sys.argv) > 2 and not sys.argv[2].startswith("--") else None)
    if not ROOM:   # the room of the subject whose folder this tutor is working in
        from urllib.parse import quote
        ROOM = (call("whoami?cwd=" + quote(os.getcwd())) or {}).get("room")
    if ROOM:
        PAGE = ORIGIN + "/room/" + ROOM
    if cmd in ("ask", "card"):
        card = read_card()
        if isinstance(card, dict) and card.get("type") in ("question", "passage", "choice", "canvas") and not card.get("mode"):
            print('No "mode" on this card. Add "mode": "teach" or "test" (TEACHING.md, "Two modes"); the room shows it as a chip.', file=sys.stderr)
        r = call("card", card)
        if r.get("error"):
            sys.exit(r["error"])
        ensure_page(r)
        if r.get("kept"):   # the last card's text or picture is still beside this one
            print(f"Still on screen from the last card: {', '.join(r['kept'])}. Add \"keep\": false to a card to take it down.", file=sys.stderr)
        if r.get("pins"):   # the question and their writing so far, pinned at the top left for the whole task
            print(f"Pinned top left: {', '.join(r['pins'])}. Send \"work\" again when their writing changes; a new \"task\" replaces the old one.", file=sys.stderr)
        if cmd == "card":
            print(r["id"])
            return 0
        return wait(r["id"], timeout)
    if cmd == "wait":
        return wait(arg("--card"), timeout)
    if cmd == "begin":
        if len(sys.argv) < 3 or sys.argv[2].startswith("--"):
            sys.exit("room.py begin SUBJECT [--who NAME]   (the subject id from config.json: calc, lit, law, …)")
        r = call("begin", {"subject": sys.argv[2], "who": arg("--who")})
        ensure_page(r)
        print(PAGE)
        return 0
    if cmd == "note":
        pos = [a for i, a in enumerate(sys.argv[2:], 2) if not a.startswith("--") and not sys.argv[i - 1].startswith("--")]
        if not pos:
            sys.exit('room.py note "words from the text" ["your note"] [--tone subject|amber|good|red] [--n 2]')
        n = {"quote": pos[0]}
        if len(pos) > 1:
            n["note"] = pos[1]
        if arg("--tone"):
            n["tone"] = arg("--tone")
        if arg("--n"):
            n["n"] = int(arg("--n"))
        r = call("notes", {"notes": [n], "add": True})
        if r.get("error"):
            sys.exit(r["error"])
        return 0
    if cmd == "notes":
        raw = read_card()
        r = call("notes", {"notes": raw if isinstance(raw, list) else raw.get("notes", []), "add": False})
        if r.get("error"):
            sys.exit(r["error"])
        return 0
    if cmd in ("say", "end"):
        text = " ".join(a for a in sys.argv[2:])
        r = call("say", {"text": text, "end": cmd == "end"})
        if r.get("error"):
            sys.exit(r["error"])
        return 0
    if cmd == "state":
        print(json.dumps(call("state"), ensure_ascii=False, indent=1)[:4000])
        return 0
    sys.exit(__doc__)


if __name__ == "__main__":
    sys.exit(main())
