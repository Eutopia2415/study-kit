# Running a block in the room

Every subject has its own room: `http://127.0.0.1:4417/room/lit`, `/room/calc`, `/room/biz`, `/room/law`, `/room/phil`. room.py sends everything you post to your subject's room, which it knows from the folder you are working in (`begin lit` names it outright; `--room lit` on any command if you are somewhere else). Another tutor open at the same time has its own room and cannot touch yours, so never post "again" because a card seems to have been replaced: check `room.py state` first.

The learner sits in your room's page, which Study Hall opened beside this chat. They never type in the chat; they answer cards. You put one card in front of them at a time and wait for the answer. The page has two sides. The reference side (left) holds everything to look at: at the top the two pins of the task (`task`, the question they are answering, and `work`, what they have written for it so far), which stay put; under them your card's `context` and its text or picture. Nothing else from earlier in the block is kept there. The work side shows your latest `say` and one panel with the question and the answer box; the panel's header shows the card's `item` and `n`, so name the item plainly ("Thesis rewrite", "Cold retrieval") and count it ("2/4"). Put `"mode": "teach"` or `"mode": "test"` on every question, passage, choice and canvas card (TEACHING.md, "Two modes"); the header shows it as a Teaching or Testing chip. A `lesson` shows Teaching and a `close` or `mcq` shows Testing without it. Earlier turns are folded behind History, so a `say` has to stand on its own: the learner sees your latest words and their last answer, not the whole conversation. Everything in TEACHING.md, TEACHER.md and the subject's rules still decides *what* you ask and *how*; this file is only the plumbing.

## Starting

`room.py begin lit` (the subject id from config.json; `--who "Ms. Lee"` overrides the name on the page) sets the colour and name, clears the card area, keeps the day's history and prints the room's link. If no room page is open when you begin or post a card, room.py brings the open room tab forward (Dia or Chrome), or opens one only when there is none; put the link in your first chat line anyway, so the learner can find it from another screen. The HUD does this itself when it opens the room; do it by hand when you start a block another way.

## The one command

```bash
python3 {{KIT}}/core/study-hall/room.py ask <<'EOF'
{"type": "question", "mode": "test", "say": "Okay, one cold one first.", "item": "Cold retrieval", "n": "1/3",
 "prompt": "For $g(x)=x^2-4x+1$, the average rate of change on $[0,4]$ is $0$. Is the tangent at $x=0$ horizontal? Justify with a number."}
EOF
```

It posts the card, waits up to 9 minutes for the answer and prints it. Read the first line, not the exit code (0 for all three, 1 only for a real error): "No answer yet" means run `room.py wait` again (or `room.py say` something if the silence is the point, Calc watching). "They ask, before answering: …" means the learner pressed ? on your last reply and asked for more: answer that with `room.py say`, the usual 80 words, no new card, then `wait` again; the card is still up. Anything else is their answer. Your words to the learner go in `say`, at most 80 words of explaining, same as chat. The next card's `say` is your reply to the last answer. `room.py say "yeah, keep going"` replies without a new card.

The chat is the log, not the conversation: write nothing there between cards. Each exchange is one `ask` call. The turn ends in words only when you start a background wait (one line: "Essay running; back at the bell") and at the close.

## Cards

Every card takes `say`, `item` (top-bar label), `n` ("2/4") and `must` (true on the must-finish item). Text fields take `**bold**`, `*italic*` and `$math$`.

Every card can also carry the text: `lines` (one string per line), `cite`, `marks` (line numbers to highlight) and `from` (the number of the first line, default 1, so an excerpt of lines 12–14 is `"from": 12, "marks": [13]`). The text is the page on the left, beside whatever the card asks. Instead of the text, a card can carry a `figure`, `image` or `video` there (below, "Figures, images and video"), and any card with text can carry `notes` (below, "Their work on screen"). `say` goes above the card, so a long reply pushes the card down rather than covering it; 40 words reads as a line, 80 as a paragraph.

**The text stays up.** Send the poem, the prompt, the picture or their essay once. Every card after it that brings no text or picture of its own keeps it on screen, with its notes, so they can still see what the next question is about. Don't send the lines again; send only what changes: `marks` to move the highlight to the lines this question is about (the old marks drop), `notes` to replace the notes. room.py tells you on stderr what stayed ("Still on screen from the last card: cite, lines"); if a follow-up card prints no such line, the text did not stay, so send the lines with that card. Take it all down when you change the subject, with `"keep": false` on the first card that isn't about it. A card with its own `lines` or picture, a `lesson` and a `review` replace the text that was there; only the two pins (`task`, `work`, below) stay through it, so the essay question is still at the top left over a lesson's diagram or over their essay. A `close` starts clean, because it is the retry with no cues: send its prompt text with it, or `"keep": true` if the text itself isn't a cue. The learner can also put the page away and bring it back with the book button, top right.

**What the question points at is on the card.** Context is what the learner needs to do the question in front of them, and nothing else (11-14: "context should be like the question, what i wrote and stuff… what i actually need to complete the question at hand"). It is three things, top left, in this order:

1. **The question they are answering**: `"task"`. The essay question, the problem, the hypo. Send it once, as a string, a list of lines, or `{"text": "…", "cite": "AP 2023 Q3"}`: the task sentence, not the whole handout. The server carries it onto every card until you send another; `"task": false` takes it down.
2. **What they have written for it so far**: `"work"`. Their thesis and sentences as they stand now, whole and in order: `{"lines": ["<thesis>", "<sentence one>", "<sentence two>"], "cite": "Your paragraph so far"}`. The server carries it too. Send it again every time a sentence changes, so it is always the current version; never a list of drafts. `"work": false` when the card's own text already is all of it. A new `task` drops the old `work`.
3. **The exact thing this card points at**, only when it points at something: the card's own `lines` with `marks` and `notes` (the sentence under discussion), or `"context"` for a few words the prompt literally refers to: `{"from": "answer"}` when the question is about the answer they just gave ("why that word?"), `"context": "…"` (or `{"text": "…", "cite": "…"}`) for one line of the poem or the rule you are applying. Most cards need no `context` at all. Never attach their last answer out of habit: on 11-14 a closing card asking for a whole thesis carried "Your answer: oh because that is where she broke their kissy moment", which had nothing to do with it ("what is your logic for context?"). The test for anything on the reference side: would they use it to answer this card? If not, leave it off.

- Not context: earlier drafts, texts from earlier cards, anything they do not need for this question. Nothing from earlier in the block is kept on screen except the two pins and the last card's own text; the old pile of earlier sheets is gone. If a question needs something from before, it goes in `work` or `context`.
- The server sends a card back when it works on their writing ("rewrite sentence two", "your thesis", a text whose `cite` starts "Your") and `task` or `work` has not been decided, and when its prompt says "line 9" or "the graph" with nothing on the card to match. It tells you what to add. It no longer asks for a quote of their words: their writing is the `work` pin.
- A text, numbered lines or a picture ("line 9", "the graph", "the passage"): it is open on the page, sent with this card or still up from the last one.
- A lesson's closing `check` counts. The pins stay above the lesson's picture; anything else the check asks them to change or reuse goes in `context` on the lesson card.
- A set and `"keep": false` start clean: the pins come down with the text. A `close` keeps the `task` (the question is not a cue) and drops the `work` (their earlier writing is), so don't send the question again as `lines` and don't add `context`; `"keep": true` keeps both.

Their answer doesn't disappear either: when your next card arrives, the question they just answered, their answer in full and your reply sit right above it. So a reply can point at their words ("your line is all subject, no action") without quoting them back.

| type | fields | answer you get back |
|---|---|---|
| `question` | `prompt`; `photo: false` hides the photo button | their text, and photo paths (open them with Read) |
| `passage` | `prompt`, `lines`, `marks`, `cite` (a question with the text beside it) | same as question |
| `canvas` | `prompt`, `minutes` (default 40), `claim` (their checked argument, prefilled) | claim, full essay, words, time left or "auto-handed in" |
| `mcq` | `items: [{"q", "o": [4 choices], "k": 0-based integer index of the key, 0 = A}]`, `minutes`, `source` ("Released 2023 set 1" or "Written in the AP style") | score, and per item: right with the pick, or wrong with the pick and the key, both as letter and text. Keys never reach the page before submission. |
| `choice` | `prompt`, `options` (strings), optional `readings: [{"label","text"}]` (when the labels are the options, the readings themselves are the buttons), `why: true` for a sentence after the pick | the option and the why |
| `close` | `prompt` (the night's hardest move again, no cues), `question: false` to drop the write-a-question box | the retry, their question, photos |
| `lesson` | `steps` (below), optional `title`, optional `check: {"prompt", "options"?, "why"?}` | how long they spent, then their answer to the check (or "Got it." with no check) |
| `review` | `text`, or `file` (an absolute .md/.txt path), or `"from": "answer"` (their last written answer today, word for word); `notes`; optional `title`, `cite`, `prompt` (adds an answer box), `prefill` | their answer, or "Got it." with no prompt |

## Lessons: teaching with a picture

A `lesson` card is for the new-idea step of the loop, or any time a picture beats a paragraph: a graph, a motion on a line, a table, a chain of steps, a passage with the marks moving. The learner presses space (or Next) to reveal one step at a time; the picture for each step sits beside its words and stays up until a later step brings a new one. They can go back to any step they've seen. A ? question arrives prefixed "Step 3 of 6:", so you know where they got lost. Send it with `room.py ask` like any card.

How to write one, because a lesson that only restates the rule is worse than none:
- Concrete first: their world (something from ME.md's world: a game, a place, a sport), then the general rule.
- The *why* gets its own step before the rule. Distance vs displacement needs "rate × time is a rectangle" before "area is distance", or the area step is magic.
- One change per step: one new curve, one shaded region, one marked line. 25–50 words a step, 4–7 steps.
- State the numbers. "Distance is 12 m, displacement 4 m" lands; "they differ" doesn't.
- Words match what is on screen at that step: don't say "drag" on a step with no slider, or "arcs" when the picture shows arrows.
- Labels are names, never explanations: `Displacement`, not `Displacement (left cancels right)`; `4 m`, not `4 m (0 to 1 s)`. The step text explains, the picture shows.
- End with a `check` that needs the idea, not a recall of the last step (a different interval, a new function).

Each step is `{"text": "...", <one visual>}`; a step without a visual keeps the last picture. Visuals:

- `graph`: `x: [lo, hi]` (set it), `y` (optional; read off the curves otherwise), `xlabel`, `ylabel`, `fns: ["x^2-3x", {"fn", "label", "color", "dash", "domain": [a, b]}, {"points": [[x, y], ...], "label"}]`. Overlays: `shade: {"fn": 0, "from", "to"}` (area to the axis; above in the curve's colour, below in amber), `points: [{"on": 0, "x": 1, "label"} | {"at": [x, y]}]`, `vlines: [{"x", "label"}]`, `hlines`, `tangent: {"fn": 0, "at"}`, `secant: {"fn": 0, "from", "to"}`. Live: `slider: {"name": "a", "min", "max", "value", "step", "label": "t"}` (they drag on the graph or the slider; use `a` anywhere a number goes, as `"to": "a"` or `"at": "a"`), `readout: [{"label", "area": {"fn", "from", "to", "abs": true}} | {"label", "slope": {"fn", "at"}} | {"label", "value": "a^2-3a"}]`.
  Expressions: `+ - * / ^`, `3x`, `2(x+1)`, `sin(x) cos tan sqrt abs ln log exp min max`, `pi`, `e`; the variable is `x` or `t`. Write `x/2`, not `1/2x` (that reads as `(1/2)·x`). `fn` refers to `fns` by 0-based index. Colours: `subject` (default), `amber`, `good`, `red`, `ink`, `muted`.
- `numberline`: `range: [lo, hi]`, `points: [{"at", "label", "open": true}]`, `intervals: [{"from", "to", "label": "+", "color": "good"}]` (sign charts), `moves: [{"from", "to", "label"}]` (stacked arrows in time order), `net: true` or a label (the arrow from the first start to the last end).
- `table`: `head: [...]`, `rows: [[...], ...]`, `mark: [row numbers from 1]`.
- `flow`: `["Offer", "Acceptance", "Consideration"]`, or `{"items": [...], "at": 2}` to light one up. `at` counts from 1 (2 lights "Acceptance"), or is the item's own text (`"at": "Acceptance"`); 0 is refused. Light the item the step is about, so the picture and the step agree.
- `lines`, `marks`, `cite`, `from`: the text, with this step's marks.
- `figure`, `image`, `video`: a file you made (next section).

The server checks every expression and reference before the card goes up and says what is wrong ("step 3 graph: fn \"y+1\": unknown name y"), so a broken graph never reaches the learner. A worked example, the distance vs displacement lesson: `tests/fable-block/lesson-example.json`.

## Figures, images and video

Make the picture with a skill from TEACHING.md's menu, then name the file on a lesson step or beside any card. The server copies it into the room, so the page never reads your folders.

- `"figure": {"src": "/abs/fig.html", "light": "/abs/fig-light.html", "alt": "Dial indicator"}`: one self-contained HTML page, shown live and interactive. An anatomy build writes exactly that: `node build.mjs`, and `node build.mjs --light` for the light theme, which the room swaps in with its own theme. The room hides anatomy's caption paragraph, because your step text does that job; keep its legend keys to bare part names.
- `"image": "/abs/frame.png"` (or `{src, light, alt, title}`): png, jpg, gif, webp, svg. `"pdf": "/abs/handout.pdf"` (or `{src, page, title}`): a PDF, opened at `page`. Several at once: `"resources": [{"pdf": "/abs/case.pdf", "page": 2, "title": "Case study"}, {"image": "/abs/chart.png", "title": "Figure 1"}]`, one tab each (up to 8).
- **Whenever you show a picture, a scan, a photo, a book page or a document, show it this way**. It opens in the viewer on the reference side: a title, a tab per file, Full screen, page and zoom controls; they pinch or ctrl-scroll to zoom where the pointer is, double-click to zoom in and back, drag to pan. So: send the file itself, never a description of a picture or a path in `say`; give it a `title` that says what it is ("Atonement, London 1999, last page"); send a PDF as a PDF with `page` set to the page your question is about, not screenshots of its pages; put several sources on one card as `resources`, not one card each. The question about it is the card's `prompt`, and the pins (`task`, `work`) stay above it.
- `"video": {"src": "/abs/clip.mp4", "loop": true}`: mp4 or webm. It starts muted and plays; add `"sound": true` when it has narration, so it waits for them to press play. Manim: `manim -qm scene.py Name` writes `media/videos/scene/720p30/Name.mp4`.

A path is absolute. A missing file, a wrong type or an HTML page that loads files from beside it is refused with the reason. Timing: a manim clip renders in about ten seconds at `-ql`, but an anatomy figure can take most of an hour, so build it before the block or in the background while they answer a card (a background Bash command, or a subagent). Never leave them waiting on an empty room.

## Their work on screen: review cards and notes

A `review` card puts their own words on screen, with your highlights and margin notes, like marking a paper together: an essay after the bell (`"from": "answer"` right after a canvas), the explanation they just sent, a paragraph to rewrite (`prompt` and `prefill`).

`notes` is a list of `{"quote": "words copied from the text", "note": "the comment", "tone": "good"}`. Tones: `good` keep this, `amber` fix this, `red` wrong, `subject` (default) look here. A note with no `note` is a plain highlight; `"n": 2` picks the second time the words appear. The quote has to match the text (any spacing, straight or curly quotes); a misquote is refused, saying which note.

Notes also work live, on the card that's up, without replacing it or touching what they've typed: on a review card, on any card with `lines`, such as the poem beside a question, and on a text that stayed up from an earlier card.

```bash
python3 {{KIT}}/core/study-hall/room.py note "be not proud" "An order. Who gives orders to Death?" --tone amber
python3 {{KIT}}/core/study-hall/room.py notes <<< '[]'      # clear them; a list replaces them all
```

The new note pulses and scrolls into view. Numbers follow reading order. Your `say` still carries the talk; a note is a comment on a phrase, the same 80-word habit, a sentence or two.

## Shared docs: writing that keeps growing

A review card is one look at one text. Writing that gets revised over a block or across nights goes in a Claude Doc you both see live, such as a timed essay's rewrite, a Business case write-up or a Law outline. Load the `anthropic-skills:docs` skill first, then:

1. Make the doc with their text exactly as they wrote it (from the canvas answer, or pasted). Title it `<Subject> · <task> · <date>`. Open it with the Artifact tool's `open`.
2. After that, their text is theirs. Never edit it. You only comment, anchored on their exact words, a sentence or two each, saying keep, fix, wrong or look here the way the note tones do.
3. While you work in the doc, the doc is the whole lesson. Take the card down with `room.py end "In your doc."`. Then ask your questions as comments on their words, still one at a time, and wait for their reply in the thread. Go back to the room when the doc work is done.
4. They can comment to you in the doc with @Claude. It reaches the session that made the doc as a turn headed `[Artifact comment sent to Claude]`. Answer it in that thread, not in chat.
5. Put the doc link in STATE.md, so the next session reopens the same doc (read only what changed since your last `rev`) instead of starting a new one.
6. Homework hand-in. When you're satisfied and they say it's done, copy their final text, exactly as they wrote it, into the assignment's Google Doc on Classroom with the learner's school account (ME.md, "Accounts"), in Ego Lite (`ego-browser` skill, task space created with the profile ME.md names). Find the assignment in Drive yourself the same way. If ME.md names no account or Ego Lite isn't installed, skip this step and tell them the doc is ready to paste. Paste it in one go. Then ask "Turn it in?" and press Turn in only on their yes, every time.

## Things that bite

Posting a new card replaces the one up: whatever the learner was typing on it never reaches you, so wait for the answer first. A text left up after the questions have moved on to something else is the other way to lose them: `"keep": false`. An `mcq` clock starts when the page opens the set; if the page isn't open, `wait` just times out.

## When they leave the plan

If the learner says in chat or a `?` that they want their own homework instead ("help me finish my questions"), take the card down with `room.py end "Okay, your questions."` and work it in chat. Homework has its own pages and numbering, so it doesn't fit cards, and a card left up only waits. Go back to the room only if they ask.

## Timed cards

`canvas` and `mcq` keep their own clock on the server: it starts when the learner presses Start (canvas) or opens the set (mcq), locks at 0:00 and hands in the last autosaved draft even if the page is closed. For a 40-minute canvas, post it with `room.py card` (prints the id), then run `room.py wait --card ID --timeout 3000` **in the background** and end the turn with one line; you are woken when it is handed in. Never speak during a timed attempt.

## Ending

The last card is a `close`. A close answer that stops mid-sentence, or one that comes after a `?` saying they're stuck, isn't the end: reply with `say`, put up a teaching card to finish it, then a fresh `close` (TEACHING.md, loop step 6). A `?` arrives with what they have written so far, so they never have to hand in to show you. After a whole close answer: grade it in the final `say` via `room.py end "…"` (this clears the card area), then do the close bookkeeping your rules ask for (STATE.md, SKILLS.md, Graphiti, the SCHEDULE.md row) and end the turn with a short line in chat.
