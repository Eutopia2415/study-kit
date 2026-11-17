# Running a subject block

Every subject folder's CLAUDE.md (Claude) or AGENTS.md (Codex) loads this file. TEACHING.md says how to teach, `{{STUDY}}/ME.md` says who the learner is, the course's COURSE.md says what is special about the subject, and this file is the shared plumbing.

## First session ever
If `{{STUDY}}/ME.md` still says `status: new`, run `{{KIT}}/core/ONBOARDING.md` before anything else in this session. It takes about five minutes and writes ME.md. Don't teach until it's done. If this folder's `COURSE.md` says `status: new` (a subject the learner added), run that file's section "A subject you added" first.

## Changing how the tutor works
When the learner asks to change something ("shorter replies", "no cold questions in Calc", "talk more Chinese", "make the teacher stricter"), make the change at once in the right file, keep the block going, and say in one line which file changed:
- How they like to be taught, their language, their world for examples: `{{STUDY}}/ME.md`.
- A rule for every subject that changes or switches off a kit rule (the word cap, cold questions, the room, the close): `{{STUDY}}/MY-RULES.md`.
- A rule for this subject only: `MY-RULES.md` in this folder.
- The teacher's personality and voice: `TEACHER.md` in this folder. Ready-made voices are in `{{KIT}}/core/teachers/`; to switch, copy one over TEACHER.md and keep the subject's last line ("The question this subject turns on").
- Block times and the evening plan: Study Hall's Schedule page (tell them where it is; don't edit config.json by hand).
- Never edit anything under `{{KIT}}`: updates replace it. A MY-RULES line wins over the kit, so a kit rule is changed by writing the new rule there, in plain words, one line each.
Read MY-RULES files as the learner's own decisions: follow them even where TEACHING.md says otherwise.

## Startup reads (silent, in the same turn as the first question)
- `STATE.md` (the plan: goal, open gaps in priority order, what's next), `TEACHER.md` (who you are for this block), `SKILLS.md` (the course map). Be the TEACHER.md person for the whole block.
- Learning records as `{{KIT}}/core/RECORDS.md` describes.
- A chat that Study Hall opened starts with a message headed "Tonight's block". That message is the block: subject, minutes, the items in order and a "Chat title" line. Don't read TONIGHT.md as well. In Claude, after the first exchange, rename this session to the "Chat title" line (`mcp__ccd_session_mgmt__set_session_title` with session_id "self"; load it with ToolSearch if it is deferred) and say nothing about it. At close, rename it to what actually got done, in 2 to 5 plain words.
- A chat opened without that message: read `{{STUDY}}/TONIGHT.md`. If its Date is today and its Subject is this one, it is the block; otherwise ignore it and work from STATE.md "Next session".

## Block clock
`curl -s localhost:4417/api/block` gives the running block (subject, end, minutes left, next block). Check it silently after the first question and at each item boundary. If the remaining items need more than 5 minutes beyond the time left, extend by the shortfall rounded up to 5: `curl -s -X POST localhost:4417/api/pause -d '{"action":"extend","min":N}'` (30 extra minutes per block at most, 60 when this subject has a test within 3 days). Ahead by more than 5: `{"action":"shorten","min":N}`. All done with time left: `{"action":"end"}`. Tell the learner in one line with the reason. If they say stop or keep going, do that instead. If the reply has no subject (Study Hall not running) or names another subject, leave the clock alone.

## Continuity
- Each block is a fresh chat in this folder. Continuity lives in STATE.md, SKILLS.md and the learning records, never in earlier chats.
- Hold the plan. If the learner wants to detour, say what STATE.md has as next and why in one line, then follow their decision.

## Closing a block
1. Update STATE.md: move gaps on graded evidence, rewrite "Next session", update the date. Only an unaided correct answer in a new context moves a gap to "Shown independently". Keep it under about 60 lines, not counting "What works for me", which is edited, never dropped.
2. Every open gap ends with its next retest date as `Retest MM-DD.`: 1 to 2 days after a miss or a helped answer, 3 to 4 days after the first unaided correct answer, 10 to 14 days after the second. One date per gap; replace the old one. Study Hall drills gaps in order of this date.
3. SKILLS.md: update the rows you touched (Status, Last, Next, Note). unseen or seen → tested the first time it's asked. Shown only after unaided correct answers on 3 separate days in changed contexts, never by hand. Next = the retest date while tested; once shown, 14 days later, then 30, then the month before the exam. Never delete a row; add one if class reaches a skill that isn't listed.
4. Append one row to the Log table in `{{STUDY}}/SCHEDULE.md`: date, subject, slot, minutes actually studied, what moved. Skip it if a row for today and this subject is already there (Study Hall's Done button may have written one).

## The room (every block)
Tutoring happens in the Study Room at http://127.0.0.1:4417/room, not in chat text; the chat is the log. The full rules are in `{{KIT}}/core/study-hall/ROOM.md`; read it in the startup turn.
- First thing in any session that teaches: `python3 {{KIT}}/core/study-hall/room.py begin <subject id>` (the id is at the top of this folder's CLAUDE.md or AGENTS.md). Your first chat line is the link it prints and nothing else. If the server isn't running, say so in one line and start it with `open "{{STUDY}}/Study Hall.command"`.
- Every question, passage, timed essay, MCQ set, choice and the close goes to the learner as a card through `room.py ask` (or `card` + `wait`). Your words go in the card's `say`, under the same 80-word cap. Nothing in chat between cards except the one line that starts a background wait, and the close.
- Send a text once: it stays on screen under every follow-up card. After that send only what changes (`marks`). Put `"keep": false` on the first card that has moved on.
- Context on every card: what the learner needs to answer the question in front of them and nothing else. `"task"` (the question they're answering) and `"work"` (what they've written for it so far) are pinned top left; `"context"` for a few words the prompt refers to. Never their last answer out of habit, never old drafts.
- Pictures and documents go as the file itself (`"image"`, `"pdf"` with `"page"`, or `"resources"`), never described in words.
- Teaching a new idea, or explaining after a miss where a picture beats a paragraph: a `lesson` card (ROOM.md, "Lessons").
- If the learner types in chat instead of answering the card, answer in the next card's `say`. Only "no room" or "in chat" from them moves the block to text.

## Question sets
`PRACTICE.md` in this folder says how this course's assessments are built (format, item kinds, how distractors are made) and where real items live. Real items (released questions, CED samples, the teacher's own worksheets and tests) always come first and are never rewritten as if they were yours. When none fits, build a mimic by PRACTICE.md: same shape, every item with its key, the SKILLS.md row it tests, and the mistake behind each wrong choice; save it under `practice/`, headed as a mimic.
- Guided notes and worksheets the learner has already filled in are a map of what a section covers, never a question source.
- When the learner tells you questions from a real test or quiz, save them as given to `practice/tests/YYYY-MM-DD_<test>.md` with their answer and what went wrong. Those are the teacher's real format and the model for new sets.
- Keep `RESOURCES.md` in this folder current: one line per useful file on disk (path, what it is). Use what's on disk before fetching.

## School systems
- Never open Google Classroom or AP Classroom during a session. Deadlines and homework come from Study Hall's sync (the Deadlines table in `{{STUDY}}/SCHEDULE.md` and the Study Hall page). The Classroom block in STATE.md is informational; if it's stale, ignore it.
- A test or in-class essay the learner mentions goes to Study Hall: `curl -s -X POST localhost:4417/api/deadline -H 'Content-Type: application/json' -d '{"subject":"<id>","date":"YYYY-MM-DD","label":"..."}'`.

## Class recordings (optional)
If the learner drops an audio recording of class and `{{KIT}}/tools/transcribe_recording.py` runs on this Mac (it needs `pip install mlx-whisper`; transcription is local, nothing is uploaded), run `python3 {{KIT}}/tools/transcribe_recording.py "<audio>" <slug> --out "<this folder>/recordings" --date <class date>` in the background and keep tutoring. Then write `NOTES.md` in that folder (what class covered in order, the teacher's explanations worth keeping, anything due), mark the SKILLS.md rows class covered as seen, and reply in three lines or fewer. If the script can't run, say so in one line and carry on.

## Running in Codex
This folder's AGENTS.md means you are in Codex. TEACHING.md, ROOM.md and the course files were written with Claude's tools in mind; where they name one, do this instead:
- **Shell access to Study Hall.** `room.py` and `curl localhost:4417` need the network. This folder's `.codex/config.toml` turns it on, and makes `{{STUDY}}` writable, once the learner trusts the folder. If a call is blocked by the sandbox anyway, ask for approval to run it, and tell the learner in one line to trust this folder in Codex so it stops asking.
- **Waiting for an answer.** `room.py ask` and `room.py wait` block until the learner hands the card in. Run them with `--timeout 300` and a shell timeout above that (330000 ms); on "No answer yet", run `room.py wait` again. Stay in the same turn while a card is up, so the learner never waits on you.
- **Skills.** The kit's skills are in `~/.agents/skills/<name>/SKILL.md`. "Load a skill" means read that file and follow it.
- **Session titles, Claude Docs, Artifacts, ArtifactComments, ToolSearch, task lists** don't exist here. Skip renaming the chat. Writing the learner keeps revising (ROOM.md, "Shared docs") goes in `drafts/<task>.md` in this folder: they write it, you never edit their words, and your comments go in room cards that quote the line they are about.
- **Learning records.** Use the Graphiti tools if this Codex has the `graphiti` MCP server; otherwise `records.md`, exactly as RECORDS.md says.
