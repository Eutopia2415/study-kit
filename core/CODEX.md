# Running in Codex

You are in Codex (this folder's AGENTS.md loaded you). TEACHING.md, ROOM.md and the course files were written with Claude's tools in mind; where they name one, do this instead:
- **Shell access to Study Hall.** `room.py` and `curl localhost:4417` need the network. This folder's `.codex/config.toml` turns it on, and makes `{{STUDY}}` writable, once the learner trusts the folder. If a call is blocked by the sandbox anyway, ask for approval to run it, and tell the learner in one line to trust this folder in Codex so it stops asking.
- **Waiting for an answer.** `room.py ask` and `room.py wait` block until the learner hands the card in. Run them with `--timeout 300` and a shell timeout above that (330000 ms); on "No answer yet", run `room.py wait` again. Stay in the same turn while a card is up, so the learner never waits on you.
- **Skills.** The kit's skills are in `~/.agents/skills/<name>/SKILL.md`. "Load a skill" means read that file and follow it.
- **Session titles, Claude Docs, Artifacts, ArtifactComments, ToolSearch, task lists** don't exist here. Skip renaming the chat. Writing the learner keeps revising (ROOM.md, "Shared docs") goes in `drafts/<task>.md` in this folder: they write it, you never edit their words, and your comments go in room cards that quote the line they are about.
- **Learning records.** Use the Graphiti tools if this Codex has the `graphiti` MCP server; otherwise `records.md`, exactly as RECORDS.md says.
