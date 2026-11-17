#!/usr/bin/env python3
"""Smoke test for the study kit. Run it with:  zsh test.sh

It installs the kit into a throwaway folder (your real ~/Study, ~/.claude and ~/.codex are never touched),
starts Study Hall on a spare port, sends a question card through the Study Room, answers it the way
the browser page does, and checks that re-running setup keeps your own files. Nothing opens on screen.
Pass --keep to leave the throwaway folder behind for a look.
"""
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.parse
import urllib.request
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
FAILS = []


def check(ok, what, detail=""):
    print(("  ok    " if ok else "  FAIL  ") + what + (f"  ({detail})" if detail and not ok else ""))
    if not ok:
        FAILS.append(what)
    return ok


def run(args, **kw):
    return subprocess.run(args, capture_output=True, text=True, timeout=120, **kw)


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def http(url, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"} if data else {})
    with urllib.request.urlopen(req, timeout=10) as r:
        return r.status, r.read().decode("utf-8", "replace")


def main():
    keep = "--keep" in sys.argv
    tmp = Path(tempfile.mkdtemp(prefix="studykit-test-")).resolve()
    study = tmp / "Study"
    stubs = tmp / "bin"            # stand-ins for `open` and `osascript`, so no browser window pops up
    stubs.mkdir()
    for name in ("open", "osascript"):
        (stubs / name).write_text("#!/bin/sh\nexit 0\n")
        (stubs / name).chmod(0o755)
    env = dict(os.environ, PATH=f"{stubs}:{os.environ['PATH']}")
    server = None
    print(f"Study kit smoke test, in {tmp}\n")
    try:
        print("Install")
        r = run([sys.executable, str(KIT / "core" / "setup.py"), "--study", str(study), "--subjects", "calc,lit,biz",
                 "--agent", "claude", "--no-skills"], input="n\n", env=env)
        check(r.returncode == 0, "setup.py finishes", (r.stderr or r.stdout)[-400:])
        for f in ("ME.md", "MY-RULES.md", "SCHEDULE.md", "Study Hall.command", "study-hall-data/config.json"):
            check((study / f).exists(), f"~/Study/{f} exists")
        for name in ("AP Calc", "AP Lit", "AP Business"):
            folder = study / name
            for f in ("CLAUDE.md", "STATE.md", "SKILLS.md", "TEACHER.md", "MY-RULES.md"):
                check((folder / f).exists(), f"{name}/{f} exists")
            text = (folder / "CLAUDE.md").read_text() if (folder / "CLAUDE.md").exists() else ""
            check("{{" not in text, f"{name}/CLAUDE.md has no unfilled placeholders")
            imports = re.findall(r"^@(\S+)", text, re.M)
            missing = [i for i in imports if not (Path(i) if i.startswith("/") else folder / i).exists()]
            check(imports and not missing, f"{name}/CLAUDE.md imports all point at real files", f"missing: {missing}")
            agents = (folder / "AGENTS.md").read_text() if (folder / "AGENTS.md").exists() else ""
            reads = re.findall(r"^\d+\. `([^`]+)`", agents, re.M)
            check(len(reads) == 7 and all(Path(r).exists() for r in reads) and "{{" not in agents,
                  f"{name}/AGENTS.md (Codex) lists 7 real files to read", f"{[r for r in reads if not Path(r).exists()]}")
            toml = (folder / ".codex" / "config.toml").read_text() if (folder / ".codex" / "config.toml").exists() else ""
            check("network_access = true" in toml and f'writable_roots = ["{study}"]' in toml,
                  f"{name}/.codex/config.toml allows localhost and ~/Study writes")
        leftovers = [str(p.relative_to(study)) for p in study.rglob("*")
                     if p.is_file() and "templates" not in p.parts and p.suffix in (".md", ".py", ".command", ".json", ".mjs")
                     and re.search(r"\{\{(KIT|STUDY)\}\}", p.read_text(errors="ignore"))]
        check(not leftovers, "no {{KIT}} or {{STUDY}} left in installed files", ", ".join(leftovers[:5]))

        print("\nStudy Hall")
        port = free_port()
        origin = f"http://127.0.0.1:{port}"
        server = subprocess.Popen([sys.executable, "server.py", str(port)], cwd=study / "study-kit" / "core" / "study-hall",
                                  env=dict(env, STUDY_HALL_DATA=str(study / "study-hall-data")),
                                  stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
        for _ in range(50):
            try:
                http(origin + "/api/state")
                break
            except OSError:
                time.sleep(0.2)
        for path in ("/", "/room/calc", "/api/state", "/api/block", "/settings"):
            try:
                code = http(origin + path)[0]
            except Exception as e:
                code = e
            check(code == 200, f"GET {path} returns 200", str(code))

        def calc_link():
            st = json.loads(http(origin + "/api/state")[1])
            return next((x.get("chat") or {}).get("link", "") for x in st["subjects"] if x["id"] == "calc")
        check(calc_link().startswith("claude://code/new?folder="), "the Calc chat link opens Claude")

        print("\nStudy Room: tutor sends a card, learner answers, tutor reads it")
        renv = dict(env, STUDY_HALL_ROOM=origin)
        room = [sys.executable, str(study / "study-kit" / "core" / "study-hall" / "room.py")]
        r = run(room + ["begin", "calc"], env=renv)
        check(r.returncode == 0 and "/room/calc" in r.stdout, "room.py begin calc prints the room link", r.stderr[-300:])
        card = {"type": "question", "mode": "test", "prompt": "Smoke test: what is the derivative of sin x?"}
        r = run(room + ["card", "--room", "calc"], input=json.dumps(card), env=renv)
        card_id = r.stdout.strip()
        check(r.returncode == 0 and card_id, "room.py card posts a question", r.stderr[-300:])
        try:
            http(origin + "/api/room/submit", {"room": "calc", "card": card_id, "data": {"answer": "cos x"}})
        except Exception as e:
            check(False, "the room page can hand in an answer", str(e))
        r = run(room + ["wait", "--room", "calc", "--card", card_id, "--timeout", "5"], env=renv)
        check(r.stdout.strip() == "cos x", "room.py wait returns the answer", (r.stdout + r.stderr)[-300:])

        print("\nUpdates keep your own files")
        me = study / "ME.md"
        me.write_text(me.read_text() + "\nsmoke-test marker\n")
        r = run([sys.executable, str(KIT / "core" / "setup.py"), "--study", str(study), "--no-skills"], input="n\n", env=env)
        check(r.returncode == 0, "setup.py runs again", (r.stderr or r.stdout)[-400:])
        check("smoke-test marker" in me.read_text(), "ME.md edits survive a re-run")

        print("\nSwitching to Codex")
        r = run([sys.executable, str(KIT / "core" / "setup.py"), "--study", str(study), "--agent", "codex", "--no-skills"],
                input="n\n", env=env)
        check(r.returncode == 0, "setup.py --agent codex finishes", (r.stderr or r.stdout)[-400:])
        want = "codex://threads/new?path=" + urllib.parse.quote(str(study / "AP Calc"))
        check(calc_link() == want, "the Calc chat link now opens Codex in the AP Calc folder", calc_link())
        try:
            code, out = http(origin + "/api/start", {"subject": "calc", "minutes": 45, "start": "19:00", "end": "19:45"})
            link = json.loads(out).get("link", "")
        except Exception as e:
            link = str(e)
        check(link.startswith(want + "&prompt=") and "Tonight" in urllib.parse.unquote(link),
              "starting a block opens Codex with the block as the first message", link[:120])

        print("\nAdding a course of your own")
        r = run([sys.executable, str(KIT / "core" / "setup.py"), "--study", str(study), "--add-subject", "AP Physics 1",
                 "--no-skills"], env=env)
        check(r.returncode == 0, "setup.py --add-subject finishes", (r.stderr or r.stdout)[-400:])
        check((study / "AP Physics 1" / "CLAUDE.md").exists(), "AP Physics 1 folder is created")
        cfg = json.loads((study / "study-hall-data" / "config.json").read_text())
        check(any(s["name"] == "AP Physics 1" for s in cfg["subjects"]), "config.json lists AP Physics 1")
        try:
            state = http(origin + "/api/state")[1]
        except Exception as e:
            state = str(e)
        check("AP Physics 1" in state, "the running Study Hall sees it without a restart")
    finally:
        if server:
            server.terminate()
            try:
                server.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server.kill()
        if keep or FAILS:
            print(f"\nThrowaway install left at {tmp}")
        else:
            shutil.rmtree(tmp, ignore_errors=True)

    print()
    if FAILS:
        print(f"{len(FAILS)} check(s) failed: " + "; ".join(FAILS))
        return 1
    print("All checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
