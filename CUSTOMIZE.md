# Making it yours

The easiest way: **tell the tutor.** "Shorter replies." "Stop the cold questions in Calc." "Make the teacher stricter." It writes the change into the right file and tells you which one. Everything below is what it does for you, if you'd rather do it yourself.

## Where each kind of change goes
| I want to change… | Edit this | Updates touch it? |
|---|---|---|
| How I like to learn, my language, examples from my world | `~/Study/ME.md` | never |
| A rule for every subject (switch one off, change a number) | `~/Study/MY-RULES.md` | never |
| A rule for one subject | `~/Study/<Subject>/MY-RULES.md` | never |
| The teacher's personality | `~/Study/<Subject>/TEACHER.md` | never |
| My goals, gaps, what's next | `~/Study/<Subject>/STATE.md` (the tutor keeps it) | never |
| Block times, colours, which nights | Study Hall's Schedule and Settings pages | never |
| Add a course the kit doesn't have | `zsh ~/Study/study-kit/setup.sh --add-subject "AP Physics 1"` | |
| Add a kit course I skipped | `zsh ~/Study/study-kit/setup.sh --subjects biz` | |
| Run the tutor in Codex instead of Claude, or back | `zsh ~/Study/study-kit/setup.sh --agent codex` (or `claude`) | |

Don't edit anything inside `~/Study/study-kit/`, or the CLAUDE.md, AGENTS.md or `.codex/` in a subject folder: updates replace them. You never need to, because a MY-RULES line beats the kit's rules. The order is kit rules, then the course, then ME.md, then `~/Study/MY-RULES.md`, then the subject's MY-RULES.md, and the later one wins.

## MY-RULES examples
Copy any of these into a MY-RULES.md, one per line, in your own words:
- Up to 150 words of explaining per reply, not 80.
- No cold questions at the start; go straight to new material.
- Two questions per card are fine when they're about the same graph.
- Run every block in chat, not the room.
- Always reply in Chinese, with the English exam terms in brackets.
- Give me the answer when I ask for it, no questions first.
- End every block with three exam-style multiple-choice questions.
- (in Calc's file) I use a calculator on Part B questions; don't make me do that arithmetic by hand.
- (in Lit's file) One timed essay every Sunday, Q3 only, until the in-class essay.

## Teachers
Ready-made voices are in `study-kit/core/teachers/`: calm explainer, strict coach, Socratic, funny older friend. Copy one over a subject's TEACHER.md (keep that subject's last line, "The question this subject turns on"), or ask the tutor: "switch Calc to the strict coach". Or describe your own ("like a football coach", "like my teacher Ms. Lee, she always asks 'so what?'") and the tutor writes it, keeping the same shape: a "Who" paragraph and three short exchanges in that voice.

## A course of your own
`--add-subject` makes the folder, a Study Hall colour and an evening block. The first block in that folder asks you for the syllabus or the Course and Exam Description (drop the PDF into the chat) and builds the skill map and exam format from it. Then it teaches like any other subject.
