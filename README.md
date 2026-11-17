# Study kit

An AI tutor for your AP classes. It runs in Claude (the desktop app's Code tab) or in Codex, and teaches you one question at a time in a study room in your browser. It remembers what you got wrong and brings it back before you forget it.

You start from a working setup and the tutor adjusts it to you. In the first session it asks you a few questions (language, how you like to learn, what you're into) and writes them down, and every subject uses them after that.

## What you need
- A Mac with either the Claude desktop app (signed in, with the Code tab) or the Codex app.
- Python 3. If Terminal says it's missing, run `xcode-select --install`.

## Install

**Easiest: ask your AI.** Open a new chat in Claude Code or Codex, in any folder, and paste:

```
Install the study kit from https://github.com/Eutopia2415/study-kit. Follow its INSTALL.md.
```

It asks which classes you take, installs everything into `~/Study`, and opens Study Hall. Say yes when it asks for permission to download and write to `~/Study`.

**Or one command in Terminal:**

```bash
zsh -c "$(curl -fsSL https://raw.githubusercontent.com/Eutopia2415/study-kit/main/install.sh)"
```

It asks Claude or Codex, then y or n for each class. When it's done, double-click `~/Study/Study Hall.command` to open your planner.

**Then start studying:** open a class folder, such as `~/Study/AP Calc`, and say hi.
- **Claude:** in the Code tab, choose the folder.
- **Codex:** open the folder as a project and say yes when it asks whether to trust it. Trusting it lets the tutor reach Study Hall on your Mac.

The first session asks a few questions (language, how you like to learn, what you're into) and sets the tutor up for you.

## What goes where
```
~/Study/
  study-kit/          the kit itself; replaced when you update, so don't edit it
  ME.md               you: name, language, how you like to learn (yours, edit anytime)
  MY-RULES.md         your rules for every subject; they beat the kit's rules
  SCHEDULE.md         deadlines and the study log
  Study Hall.command  double-click to open the planner and the study room
  AP Calc/            one folder per subject, all yours:
    STATE.md            what you're working on and your open gaps (the tutor keeps it current)
    SKILLS.md           every skill in the course and where you stand on it
    TEACHER.md          who the tutor is for this subject; rewrite it if you want someone else
    MY-RULES.md         your rules for this subject only
    records.md          every graded answer
```

## Making it yours
Just tell the tutor what to change: "shorter replies", "more Chinese", "no cold questions in Calc", "switch to the strict coach". It writes the change into one of your own files, and updates never undo it. [CUSTOMIZE.md](CUSTOMIZE.md) has the full map, ready-made teachers, rule examples, and how to add a course the kit doesn't have:

```
zsh ~/Study/study-kit/setup.sh --add-subject "AP Physics 1"
```

Your school's own systems are optional, and nothing in the kit is tied to one school:
- **PowerSchool grades:** build Study HUD (`--hud`, below), open Settings in it, press Sign in… under PowerSchool, and type your school's PowerSchool address with your login. The password stays in your Mac's Keychain.
- **A/B/C/D day rotation**, if your school has one: Set one, on Study Hall's planner page.
- **Google Classroom homework:** link each class on Study Hall's Settings page. The sync needs the Ego Lite browser signed in to your school Google account.

## Claude or Codex
Every subject folder works in both: Claude reads its CLAUDE.md, Codex reads its AGENTS.md, and both load the same kit files and your own. The only difference is which app Study Hall opens a block in. To switch, run setup again with `--agent codex` or `--agent claude`. A few Claude extras (shared Claude Docs for essay rewrites, renaming the chat) don't exist in Codex, so the tutor uses a Markdown file in the subject folder instead.

## Updating
Run the install command again, or ask your AI to. It replaces `study-kit/` and the CLAUDE.md, AGENTS.md and `.codex/config.toml` in each subject folder, and leaves everything else alone.

## Testing
`zsh test.sh` installs the kit into a throwaway folder, starts Study Hall on a spare port, sends one question through the Study Room and answers it, then checks that re-running setup keeps your files and that `--add-subject` works. It never touches your real `~/Study` or `~/.claude`, and nothing opens on screen. `zsh test.sh --keep` leaves the throwaway install behind so you can look at it.

## Optional
- `zsh setup.sh --hud` also builds Study HUD, a menu-bar app that opens each block at its time. It needs the Xcode command line tools.
- Class recordings: `pip3 install mlx-whisper`, then drop an audio file of class into the chat. The tutor transcribes it on your Mac and updates your notes.
