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
Before your first `lesson` card in a block, read this section in `ROOM-MORE.md` (same folder). The short rule: a new idea or a fix after a miss goes on a lesson card, picture beside the steps, and the question checks the step on screen.

## Figures, images and video
Before your first picture, PDF, figure or video in a block, read this section in `ROOM-MORE.md` (same folder). The short rule: send the file itself (`image`, `pdf` with `page`, or `resources`), never a description of it.

## Their work on screen: review cards and notes
Before your first review card or notes on their writing in a block, read this section in `ROOM-MORE.md` (same folder). The short rule: their own words go on a `review` card with your highlights and margin `notes`, and each note's quote must match their text.

## Shared docs: writing that keeps growing
Before you start or work in a shared doc, read this section in `ROOM-MORE.md` (same folder). The short rule: writing they keep revising goes in a Claude Doc; you comment, never edit their words.

## Things that bite

Posting a new card replaces the one up: whatever the learner was typing on it never reaches you, so wait for the answer first. A text left up after the questions have moved on to something else is the other way to lose them: `"keep": false`. An `mcq` clock starts when the page opens the set; if the page isn't open, `wait` just times out.

## When they leave the plan

If the learner says in chat or a `?` that they want their own homework instead ("help me finish my questions"), take the card down with `room.py end "Okay, your questions."` and work it in chat. Homework has its own pages and numbering, so it doesn't fit cards, and a card left up only waits. Go back to the room only if they ask.

## Timed cards

`canvas` and `mcq` keep their own clock on the server: it starts when the learner presses Start (canvas) or opens the set (mcq), locks at 0:00 and hands in the last autosaved draft even if the page is closed. For a 40-minute canvas, post it with `room.py card` (prints the id), then run `room.py wait --card ID --timeout 3000` **in the background** and end the turn with one line; you are woken when it is handed in. Never speak during a timed attempt.

## Ending

The last card is a `close`. A close answer that stops mid-sentence, or one that comes after a `?` saying they're stuck, isn't the end: reply with `say`, put up a teaching card to finish it, then a fresh `close` (TEACHING.md, loop step 6). A `?` arrives with what they have written so far, so they never have to hand in to show you. After a whole close answer: grade it in the final `say` via `room.py end "…"` (this clears the card area), then do the close bookkeeping your rules ask for (STATE.md, SKILLS.md, Graphiti, the SCHEDULE.md row) and end the turn with a short line in chat.
