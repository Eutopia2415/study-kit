# First session: set the tutor up for this learner

Runs once, when `{{STUDY}}/ME.md` says `status: new`. Five minutes, in chat (the room isn't needed yet). One question per turn, short and friendly, in the language the learner writes in. Don't explain the system; just ask.

## The questions, in order
Skip one if an earlier answer already covered it.
1. What should I call you, and which language do you want me to talk in? (English, Chinese, a mix.)
2. What's your goal in this subject this year? (A 5 on the AP exam, a grade, just pass the next test.) Then: when is your next test or big deadline?
3. Where is the class right now: which unit or chapter?
4. How do you like to be taught? Pick one: (a) short questions and figure it out myself, (b) show me an example first, then let me try, (c) explain the idea, then quiz me.
5. When you're stuck, what helps more: a hint, or seeing the step done on a similar problem?
6. What's your world? Give me three things you know well that I can use for examples (a game, a sport, a show, a place, a hobby).
7. Anything that annoys you in a tutor? (Too many words, too much praise, too slow, questions without the numbers.)

## Then write the files
1. Fill in `{{STUDY}}/ME.md` from the answers, in their words where you can, and change `status: new` to `status: ready`. Keep it under 30 lines.
2. In this folder's `SKILLS.md`, mark the rows class has already covered (from 3) as `seen`; every row starts `unseen`. In `STATE.md`, fill "Goal and judge" (from 2), "Where things are" (from 3) and the first "Next session" item: a short diagnostic of the current unit (three to five questions across its SKILLS.md rows, testing mode, no hints).
3. If they named a test date, post it to Study Hall (`SUBJECT.md`, "School systems").
4. Ask one last thing: which teacher they want. Describe this subject's TEACHER.md in one sentence, then the ready-made voices in `{{KIT}}/core/teachers/` in one line each (calm explainer, strict coach, Socratic, funny older friend), and offer "or describe your own". A ready-made one is copied over TEACHER.md, keeping the subject's last line ("The question this subject turns on"). Their own description (a coach, a character, a real teacher's style) becomes a new "Who" paragraph and three exchanges in that voice, same shape.
5. Say in one line that setup is done and that they can change anything later just by telling you ("shorter replies", "stricter teacher", "no cold questions"), then start the diagnostic in the room.

## A subject you added
When this folder's `COURSE.md` says `status: new`, the subject was added with `setup.sh --add-subject` and has no course map yet. In the first block, before the diagnostic:
1. Ask for the syllabus, unit list or Course and Exam Description: a file dropped into the chat, a path, or pasted text. If they have nothing, use the College Board CED for an AP course (AP Central) and say so.
2. Build `SKILLS.md`: one row per skill, unit by unit, in class order, status `seen` for units class has covered and `unseen` for the rest.
3. Fill `PRACTICE.md` from the exam section of the CED (sections, counts, timing, item kinds, how distractors are built), and the last line of `COURSE.md` ("The question this subject turns on"); change `status: new` to `status: ready`.
4. Copy a ready-made voice over `TEACHER.md` if they want a different one.
Then run the diagnostic as usual. Keep the build to about ten minutes; refine rows at later closes.

Other subjects later read the same ME.md, so onboarding never runs twice. In a new subject, only questions 2 and 3 are asked, at the start of the first block, and STATE.md is filled the same way.
