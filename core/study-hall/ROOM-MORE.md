# Room: the rest

Sections of ROOM.md that only some blocks need. ROOM.md says when to read each one; read only that section.

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
