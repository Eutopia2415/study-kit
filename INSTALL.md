# Installing the study kit (for Claude Code or Codex)

You are an AI coding agent and the user asked you to install this kit. It is a tutor for their classes that runs in Claude Code or Codex. Follow these steps in order. Keep your messages to the user short and friendly; they may not be technical.

## 1. Ask two things, one at a time
1. Which classes they take. The kit ships three ready-made courses: `calc` (AP Calc), `lit` (AP Lit), `biz` (AP Business). Any other course (AP Physics 1, AP Chemistry, a school subject) can be added by name.
2. Only if you can't tell which app you are running in: Claude or Codex. Otherwise use your own app without asking.

## 2. Run the installer
It downloads the kit from GitHub and writes to `~/Study` (outside this folder), so it needs network access and permission to write there. In Codex, ask for approval to run it outside the sandbox. In Claude Code, it is a normal permission prompt.

With at least one ready-made course (`--subjects` takes their ids, comma-separated). Use the command for the app you are running in.

In Claude Code:

```bash
zsh -c "$(curl -fsSL https://raw.githubusercontent.com/Eutopia2415/study-kit/main/install.sh)" _ --agent claude --subjects calc,lit
```

In Codex:

```bash
zsh -c "$(curl -fsSL https://raw.githubusercontent.com/Eutopia2415/study-kit/main/install.sh)" _ --agent codex --subjects calc,lit
```

If they take none of the ready-made courses, replace `--subjects ...` with `--add-subject "AP Physics 1"` (their course name).

Each other course is one more command, after the first finishes:

```bash
zsh ~/Study/study-kit/setup.sh --add-subject "AP Physics 1"
```

Pass every option on the command line: the installer can't answer questions when you run it. If any command fails, show the user the last lines of its output and stop.

## 3. Start Study Hall and hand over
1. Open the `Study Hall.command` that the installer's last message names (normally `open ~/Study/"Study Hall.command"`). It starts the planner and opens it in the browser.
2. Tell the user, in three short lines:
   - Setup is done, and Study Hall is open in the browser.
   - Next, open one class folder (the installer's last message names it, normally `~/Study/AP Calc`) in a new chat. In Claude Code, that's the folder picker in the Code tab. In Codex, open it as a project and say yes when Codex asks whether to trust it. Then say hi. The first session asks a few questions and sets the tutor up for them.
   - To update the kit later, ask you to run the install command again. Their own files are kept.

Don't start tutoring in this chat, and don't edit files under `~/Study/study-kit/`. The tutor runs in each class folder, and updates replace the kit folder.
