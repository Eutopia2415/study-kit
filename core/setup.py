#!/usr/bin/env python3
"""Install or update the study kit.

    zsh setup.sh                       # asks which subjects, installs into ~/Study
    zsh setup.sh --subjects calc,lit   # no questions about subjects
    zsh setup.sh --study ~/School      # another folder (no spaces in the path)
    zsh setup.sh --agent codex         # run the tutor in Codex instead of Claude

Layout it makes:
    ~/Study/study-kit/        the kit itself; replaced on every update
    ~/Study/ME.md             your preferences (the tutor fills it in the first session)
    ~/Study/SCHEDULE.md       deadlines and the study log
    ~/Study/study-hall-data/  Study Hall's settings and history
    ~/Study/<Subject>/        one folder per subject: STATE.md, SKILLS.md, TEACHER.md, ... (yours)
Only study-kit/ and each subject's CLAUDE.md, AGENTS.md and .codex/config.toml are rewritten on update.
Every subject folder works in both apps; --agent only picks which one Study Hall opens a block in.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

SRC = Path(__file__).resolve().parents[1]          # the kit folder this script came from
SKILL_HOMES = {"claude": Path.home() / ".claude" / "skills", "codex": Path.home() / ".agents" / "skills"}
APPS = {"claude": "Claude", "codex": "Codex"}
MARKER = ".study-kit"                               # marks a skill folder this kit installed
TEXT = {".md", ".mjs", ".py", ".sh", ".command", ".json", ".html", ".js", ".plist", ".swift"}


def say(msg=""):
    print(msg, flush=True)


def ask_app():
    if not sys.stdin.isatty():
        return "claude"
    ans = input("Which app will run the tutor, Claude or Codex? [claude/codex] ").strip().lower()
    return "codex" if ans.startswith("co") else "claude"


def ask_yes(question, default=True):
    if not sys.stdin.isatty():
        return default
    hint = "Y/n" if default else "y/N"
    ans = input(f"{question} [{hint}] ").strip().lower()
    return default if not ans else ans.startswith("y")


def fill(text, values):
    for k, v in values.items():
        text = text.replace("{{" + k + "}}", v)
    return text


def write_if_missing(path, text):
    if path.exists():
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return True


def install_kit(kit):
    """Copy the kit to its home (unless we are already running from there), then fill in its paths."""
    if SRC != kit:
        if kit.exists():
            shutil.rmtree(kit)
        shutil.copytree(SRC, kit, ignore=shutil.ignore_patterns("__pycache__", ".DS_Store"))
    subprocess.run(["xattr", "-dr", "com.apple.quarantine", str(kit)], stderr=subprocess.DEVNULL)
    values = {"KIT": str(kit), "STUDY": str(kit.parent)}
    for p in kit.rglob("*"):
        if p.is_file() and p.suffix in TEXT and "templates" not in p.parts:
            try:
                t = p.read_text()
            except (UnicodeDecodeError, OSError):
                continue
            if "{{KIT}}" in t or "{{STUDY}}" in t:
                p.write_text(fill(t, values))
    for p in list(kit.rglob("*.sh")) + list(kit.rglob("*.command")):
        p.chmod(0o755)


def install_skills(kit, agent):
    """Into the chosen app's skill folder, and the other app's too when that app is on this Mac."""
    homes = [SKILL_HOMES[agent]] + [SKILL_HOMES[a] for a in SKILL_HOMES
                                    if a != agent and (Path.home() / (".claude" if a == "claude" else ".codex")).exists()]
    for home in homes:
        install_skills_into(kit, home)


def install_skills_into(kit, home):
    home.mkdir(parents=True, exist_ok=True)
    done, kept = [], []
    for src in sorted((kit / "core" / "skills").iterdir()):
        if not src.is_dir():
            continue
        dst = home / src.name
        if dst.exists() and not (dst / MARKER).exists():
            kept.append(src.name)          # the learner's own skill of that name; never overwrite it
            continue
        if dst.exists() or dst.is_symlink():
            shutil.rmtree(dst) if dst.is_dir() and not dst.is_symlink() else dst.unlink()
        shutil.copytree(src, dst)
        (dst / MARKER).write_text("Installed by study-kit; setup.sh replaces this folder on update.\n")
        done.append(src.name)
    say(f"Skills installed in {home}: {', '.join(done) or 'none'}")
    if kept:
        say(f"Skills left alone (you already have your own): {', '.join(kept)}")


def config_subject(s, state_path):
    keep = ("id", "name", "short", "tab", "color", "weekly", "meets", "psCourse", "classroomCourse",
            "classroomHomework", "apcCourse", "classworkDir", "style")
    out = {k: s[k] for k in keep if k in s}
    out["state"] = str(state_path)
    out["deadlines"] = []
    return out


def default_week(ids):
    blocks, start = [], 19 * 60
    for i, sid in enumerate(ids):
        a, b = start + i * 50, start + i * 50 + 45
        blocks.append({"id": f"b{i + 1}", "start": f"{a // 60:02d}:{a % 60:02d}",
                       "end": f"{b // 60:02d}:{b % 60:02d}", "kind": "fixed", "subject": sid})
    return {str(d): [dict(b) for b in blocks] for d in range(7)}


def write_config(data_dir, study, chosen, catalog, base):
    cfg_path = data_dir / "config.json"
    data_dir.mkdir(parents=True, exist_ok=True)
    cfg = json.loads(cfg_path.read_text()) if cfg_path.exists() else dict(base, schedule=str(study / "SCHEDULE.md"))
    have = {s["id"] for s in cfg.get("subjects", [])}
    cfg.setdefault("subjects", [])
    added = [sid for sid in chosen if sid not in have]
    for sid in added:
        s = catalog[sid]
        cfg["subjects"].append(config_subject(s, study / s["name"] / "STATE.md"))
    if "week" not in cfg:
        cfg["week"] = default_week([s["id"] for s in cfg["subjects"]])
    else:
        for sid in added:                  # only new subjects; a block the learner removed stays removed
            add_block(cfg, sid)
    cfg_path.write_text(json.dumps(cfg, indent=2, ensure_ascii=False) + "\n")


def make_subject(kit, study, s):
    """Create a subject folder, or refresh its CLAUDE.md, AGENTS.md and Codex settings. Never overwrites the learner's files."""
    folder = study / s["name"]
    tpl = kit / "templates"
    custom = bool(s.get("custom"))
    values = {"NAME": s["name"], "ID": s["id"], "SLUG": s["slug"], "NAMESPACE": s["namespace"],
              "KIT": str(kit), "STUDY": str(study), "TODAY": date.today().isoformat(),
              # a kit course's COURSE.md stays in the kit (updates improve it); an added course's is the learner's own
              "COURSE": "COURSE.md" if custom else str(kit / "subjects" / s["slug"] / "COURSE.md"),
              "COURSE_PATH": str(folder / "COURSE.md") if custom else str(kit / "subjects" / s["slug"] / "COURSE.md"),
              "FOLDER": str(folder),
              "SCOPE_TITLE": f": {s['name']}", "SCOPE": f" for {s['name']} only, and beat ../MY-RULES.md too"}
    new = not folder.exists()
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "CLAUDE.md").write_text(fill((tpl / "CLAUDE.md").read_text(), values))      # Claude
    (folder / "AGENTS.md").write_text(fill((tpl / "AGENTS.md").read_text(), values))      # Codex
    (folder / ".codex").mkdir(exist_ok=True)
    (folder / ".codex" / "config.toml").write_text(fill((tpl / "codex" / "config.toml").read_text(), values))
    for name in ("STATE.md", "records.md", "MY-RULES.md"):
        write_if_missing(folder / name, fill((tpl / name).read_text(), values))
    write_if_missing(folder / "RESOURCES.md", f"# {s['name']}: resources on disk\n\nOne line per useful file: path, what it is. The tutor keeps this current.\n")
    src = tpl / "custom" if custom else kit / "subjects" / s["slug"]
    for p in src.rglob("*"):
        rel = p.relative_to(src)
        if p.is_file() and (custom or rel.name != "COURSE.md"):
            dst = folder / rel
            if not dst.exists():
                dst.parent.mkdir(parents=True, exist_ok=True)
                dst.write_bytes(fill(p.read_text(), values).encode() if p.suffix == ".md" else p.read_bytes())
    if custom:
        write_if_missing(folder / "TEACHER.md", (kit / "core" / "teachers" / "calm-explainer.md").read_text()
                         + "\nThe question this subject turns on, asked when the reasoning needs it and never as a tic: \"Why is that true?\"\n")
    for d in ("practice/tests", "uploads"):
        (folder / d).mkdir(parents=True, exist_ok=True)
    return new


PALETTE = ["#30d158", "#ff9f0a", "#ff375f", "#64d2ff", "#ffd60a", "#ac8e68", "#5e5ce6"]


def custom_subject(name, sid, cfg):
    """A config entry for a course the kit doesn't ship (setup.sh --add-subject "AP Physics 1")."""
    taken = {s["id"] for s in cfg.get("subjects", [])}
    base = re.sub(r"^ap\s+", "", name.strip(), flags=re.I)
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    if not sid:
        sid = re.sub(r"[^a-z0-9]", "", base.lower())[:10] or "subj"
    while sid in taken:
        sid += "x"
    short = base if len(base) <= 10 else base.split()[0]
    used = {s.get("color") for s in cfg.get("subjects", [])}
    color = next((c for c in PALETTE if c not in used), PALETTE[0])
    return {"id": sid, "name": name.strip(), "short": short, "tab": short, "color": color, "weekly": 2,
            "meets": ["A", "B", "C", "D"], "style": "deep", "custom": True, "slug": slug,
            "namespace": slug.replace("-", "_")}


def add_block(cfg, sid):
    """Give a newly added subject a 45-minute block after the last one on each day."""
    for day, blocks in cfg.get("week", {}).items():
        if any(b.get("subject") == sid for b in blocks):
            continue
        ends = [int(b["end"][:2]) * 60 + int(b["end"][3:5]) for b in blocks if b.get("end")]
        a = (max(ends) + 5) if ends else 19 * 60
        b = a + 45
        if b >= 24 * 60:
            continue
        ids = {x.get("id") for x in blocks}
        n = len(blocks) + 1
        while f"b{n}" in ids:
            n += 1
        blocks.append({"id": f"b{n}", "start": f"{a // 60:02d}:{a % 60:02d}", "end": f"{b // 60:02d}:{b % 60:02d}",
                       "kind": "fixed", "subject": sid})


def launcher(kit, study):
    cmd = study / "Study Hall.command"
    cmd.write_text(f"""#!/bin/zsh
# Double-click to open Study Hall. Starts the local server if it isn't running.
cd "{kit}/core/study-hall"
PORT=4417
if ! curl -s -o /dev/null "http://127.0.0.1:$PORT/api/state"; then
  STUDY_HALL_DATA="{study}/study-hall-data" nohup python3 server.py $PORT > /tmp/study-hall.log 2>&1 &
  sleep 1
fi
open "http://127.0.0.1:$PORT"
""")
    cmd.chmod(0o755)
    return cmd


def main():
    ap = argparse.ArgumentParser(description="Install or update the study kit.")
    ap.add_argument("--study", default=str(Path.home() / "Study"), help="where your study folders go (default ~/Study)")
    ap.add_argument("--subjects", help="comma-separated subject ids, e.g. calc,lit,biz")
    ap.add_argument("--add-subject", metavar="NAME", help='add a course the kit doesn\'t ship, e.g. "AP Physics 1"')
    ap.add_argument("--id", help="short id for --add-subject (default: from the name)")
    ap.add_argument("--hud", action="store_true", help="also build the Study HUD menu-bar app")
    ap.add_argument("--agent", choices=list(APPS), help="which app runs the tutor: claude (default) or codex")
    ap.add_argument("--no-skills", action="store_true", help="don't touch ~/.claude/skills or ~/.agents/skills (for testing)")
    a = ap.parse_args()

    study = Path(os.path.expanduser(a.study)).resolve()
    if " " in str(study):
        sys.exit(f"Pick a folder without spaces in its path (got {study}). Example: --study ~/Study")
    kit = study / "study-kit"
    data = study / "study-hall-data"
    catalog_list = json.loads((SRC / "core" / "subjects.json").read_text())
    catalog = {s["id"]: s for s in catalog_list["subjects"]}

    say(f"Study kit → {study}\n")
    existing = [sid for sid, s in catalog.items() if (study / s["name"]).exists()]
    if a.subjects:
        chosen = [x.strip() for x in a.subjects.split(",") if x.strip()]
        bad = [x for x in chosen if x not in catalog]
        if bad:
            sys.exit(f"Unknown subject id(s): {', '.join(bad)}. Choose from: {', '.join(catalog)}")
        chosen = list(dict.fromkeys(existing + chosen))
    elif a.add_subject:
        chosen = existing                                # adding one course: don't ask about the others
    else:
        chosen = [sid for sid, s in catalog.items()
                  if sid in existing or ask_yes(f"Do you take {s['name']}?")]

    cfg_path = data / "config.json"
    agent = a.agent or (json.loads(cfg_path.read_text()).get("agent") if cfg_path.exists() else None)
    if not agent:
        agent = "codex" if ask_app() == "codex" else "claude"

    study.mkdir(parents=True, exist_ok=True)
    install_kit(kit)
    if not a.no_skills:
        install_skills(kit, agent)

    tpl = kit / "templates"
    write_if_missing(study / "ME.md", (tpl / "ME.md").read_text())
    write_if_missing(study / "SCHEDULE.md", (tpl / "SCHEDULE.md").read_text())
    write_if_missing(study / "MY-RULES.md", fill((tpl / "MY-RULES.md").read_text(), {"SCOPE_TITLE": "", "SCOPE": " in every subject"}))
    write_config(data, study, chosen, catalog, catalog_list["config"])

    cfg = json.loads((data / "config.json").read_text())
    if cfg.get("agent") != agent:
        cfg["agent"] = agent
        (data / "config.json").write_text(json.dumps(cfg, indent=2, ensure_ascii=False) + "\n")
    if a.add_subject:
        if any(s["name"].lower() == a.add_subject.strip().lower() for s in cfg["subjects"]):
            say(f"{a.add_subject} is already set up; refreshing it.")
        else:
            s = custom_subject(a.add_subject, a.id, cfg)
            s["state"] = str(study / s["name"] / "STATE.md")
            s["deadlines"] = []
            cfg["subjects"].append(s)
            add_block(cfg, s["id"])
            (data / "config.json").write_text(json.dumps(cfg, indent=2, ensure_ascii=False) + "\n")

    folders = []
    for sid in chosen:
        new = make_subject(kit, study, catalog[sid])
        folders.append(study / catalog[sid]["name"])
        say(f"{'Created' if new else 'Updated'} {folders[-1]}")
    for s in cfg["subjects"]:
        if s.get("custom"):
            new = make_subject(kit, study, s)
            folders.append(study / s["name"])
            say(f"{'Created' if new else 'Updated'} {folders[-1]} (your own course)")
    if not folders:
        sys.exit("No subjects set up. Run again and answer y for at least one, or use --add-subject.")
    cmd = launcher(kit, study)

    if a.hud or (not a.add_subject and ask_yes("Build the Study HUD menu-bar app too? (needs Xcode command line tools)", default=False)):
        if shutil.which("swiftc"):
            subprocess.run(["zsh", str(kit / "core" / "study-hall" / "hud" / "build.sh")])
        else:
            say("swiftc isn't installed, so the HUD was skipped. Run xcode-select --install, then setup again with --hud.")

    first = study / a.add_subject.strip() if a.add_subject else folders[0]
    open_how = ('In the Codex app, open the folder "{first}" as a project (say yes when it asks to trust it),'
                if agent == "codex" else 'In the Claude app, open the Code tab, choose the folder "{first}",')
    say(f"""
Done. Next:
  1. Double-click "{cmd}" to open Study Hall (your planner and the Study Room).
  2. {open_how.format(first=first)}
     and say hi. The first session asks you a few questions and sets the tutor up for you.
  3. To change anything later, just tell the tutor, or see study-kit/CUSTOMIZE.md.
""")


if __name__ == "__main__":
    main()
