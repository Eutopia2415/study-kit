---
name: ap-lit-practice
description: Create interactive AP Literature poetry multiple-choice practice with evidence-based questions, a concise exam page, optional randomized bonus wildcards, hidden difficulty ratings, and diagnostic grading. Also use to explain and adapt practice after a learner submits answers.
---

# AP Literature Practice

Build a source-grounded practice set and tutor from the learner's actual reasoning. Default to an interactive local exam; honor a request limited to grading, explanations, or a text worksheet.

## Select and author

- Model supplied AP questions' skills, reasoning demands, and plausible distractors. Label new items original AP-style practice, not official College Board questions.
- For an unseen poem, check course/conversation context and confirm the candidate title if novelty remains uncertain. Absence from memory does not prove unfamiliarity.
- Prefer a suitable public-domain poem; verify the text and line/stanza breaks against a reliable source. Respect supplied sources and reproduction permissions. Give only necessary literal background before the attempt, without preteaching tested meanings.
- Match the supplied set's size and A–E format where practical. Roughly 8–13 questions is a useful default, not a requirement. Challenge through interpretation, not rare vocabulary alone.
- For a wildcard mock, author exactly 15 poem questions, then use the wildcard builder below. It inserts 3–5 wildcards after poem question 2 or later, with at least one poem question between them. Each attempt samples from capital city, people faces, math (including calculus), iGEM, and flags. Three wildcards use three different randomly chosen categories; four or five use at least three categories. Include exactly one accessible easy question and make the others niche and demanding. Do not force a face or math question every time. Randomize questions, order, colors, and positions; exclude every question from the immediately previous attempt and prefer unseen questions. Reloading resumes the saved sequence. Provide a visible New action with confirmation. Make visuals legible on desktop and iPad with descriptive accessible text that does not reveal answers. Avoid topic captions and point badges. Keep the visible poem count at 15. A correct wildcard earns one bonus point. If two or more wildcards are wrong or unanswered, submission shows the original poem grade in blue crossed out and the final 0/15 in red; all points are eliminated. Preserve the previous grading rule for already saved attempts.
- Keep capital and flag recognition separate: a capital-city question can show the country's name or outline, but no flag; a flag question asks for the country and shows its flag. Sample them as distinct categories so either or both can appear in an attempt.
- Exam mode conceals hints, keys, explanations, skill tags, and difficulty during the attempt. Use coached mode if explicitly requested.

Read [assessment-format.md](references/assessment-format.md) before constructing the frozen bank. Each item needs one best answer, exact evidence lines, a skill, estimated difficulty, an explanation, and a reason each distractor fails.

Vary contextual vocabulary, figurative relationships, narrator tone versus character feeling, stanza/sentence function, purpose and consequence, qualified inference, overall attitude, and EXCEPT questions. Avoid asking the same broad interpretation repeatedly.

Privately estimate difficulty from 1–5:
1. Direct local retrieval.
2. Contextual paraphrase or a clear relationship.
3. Multi-line integration or a plausible distractor.
4. Subtle tone, qualification, metaphor, or structure.
5. Sustained inference among closely competing readings.

These are author estimates, not calibrated AP ratings. Omit difficulty and skill tags from student UI/results/exports by default; reveal them when the learner asks. Don't announce which questions are hardest.

Before delivery, try to defend the closest competing answer from the poem. Revise if two choices remain comparably supported. Check evidence, line references, vocabulary precision, answer-length clues, answer-position patterns, and cross-question spoilers. The builder validates structure, not literary quality.

For a new version of an existing poem mock, read the earlier assessment and its private question-history ledger before writing. Assign each new question a short `angle_id` for the exact claim or skill being tested. Exclude earlier stems **and** earlier interpretive angles; changing a few words, line numbers, or answer positions does not make a new question. Check wildcard countries, people pairings, math tasks, and iGEM mechanisms against prior versions too. Run the poem's history checker if present, then review semantic overlap by hand. Record the new bank in the private ledger only after the replacement is verified. Keep the ledger and answer keys out of GitHub Pages. When a finite wildcard pool is exhausted across repeated attempts, disclose that later attempts may reuse questions rather than promising unlimited unique draws.

## Build the interactive set

Reuse the bundled designed template. Ordinary new sets do not need a new design concept, image-generation pass, framework, or backend. Keep the page close to the learner-approved To Autumn layout: passage on the left, question and choices on the right, Back/Review/Next fixed at the bottom, and a compact mobile passage/question switch.

Use the poem title as the visible page heading. Keep functional labels such as question number, flag, confidence, progress, and score; remove promotional subtitles, repeated instructions, and decorative commentary. Do not add explanations before submission or display an unanswered-bonus count on the review screen.

```sh
python3 "<skill-dir>/scripts/build_practice.py" assessment.json --out "<new-output-directory>"
```

For a 15-question wildcard mock, use:

```sh
python3 "<skill-dir>/scripts/build_wildcard_practice.py" assessment.json --out "<new-output-directory>"
node "<skill-dir>/scripts/test_wildcards.cjs" "<new-output-directory>/public/index.html"
```

The wildcard builder uses the bundled five-category bank and the portrait assets referenced by its questions. It creates the same public/private split and refuses overwrite. If changing topics, check every answer, distractor, visual, and accessible description first. Keep enough easy and elite items across the five categories for consecutive attempts to be disjoint even when both draw five.

Outputs:
- `public/index.html`: self-contained practice.
- `private/assessment.json`: full frozen bank with grading/difficulty metadata.

Choose a stable task-output location. The builder refuses to overwrite an existing set. Serve only the public directory, for example:

```sh
python3 -m http.server 9317 --bind 127.0.0.1 --directory "<new-output-directory>/public"
```

Choose a free port if needed; don't stop unrelated processes. The HTML also opens standalone. Open the interactive page and preserve its browser tab when supported; provide the file as a durable fallback.

The template includes a numbered poem with stanza breaks; one question at a time; A–E choices; flags; optional confidence; Back/Next; review grid; optional timer; independent saved progress per revision; submission and opt-in explanations; unknown-word notes; copy/download summaries; responsive poem/question layers; and explicit inline reset confirmation.

Difficulty is omitted from the student payload. The offline answer key is concealed in the UI until submission, not secure against source inspection. If real test security is requested, explain that server-side grading would be needed.

## Verify and deliver

After changing the builder/template, run:
```sh
python3 "<skill-dir>/scripts/test_builder.py"
```

For each new set, verify poem text, all referenced lines, question count, and generated JavaScript syntax. Inspect the rendered page and exercise selection, navigation, flags, reload persistence, review, submission, and explicit feedback. Check desktop and iPad portrait widths. On iPad, passage or visual and questions must switch cleanly, and Back/Review/Next must remain usable at the bottom. Inspect an actual wildcard image or equation.

Use a separate QA attempt. Never reset or overwrite learner answers. Hand off a fresh set with no selections and the timer stopped. Keep native dialogs out of the reset flow; the template uses an inline confirmation.

Don't publish a set anywhere unless the learner asks. Save it under the subject folder's `practice/`, add a line to `practice/MOCKS.md`, and open the local page fresh and unsubmitted.

Deliver briefly: open/link the practice and ask for the answer summary after completion. Don't reveal the key or interpretation first.

## Grade and tutor

Read [diagnostic-tutoring.md](references/diagnostic-tutoring.md) for grading or follow-up.

- Use the frozen bank or a verified supplied key. Flag uncertain handwriting rather than automatically marking it wrong.
- Report raw set percentage separately from official AP scoring; don't predict an AP grade from a short set.
- Support strengths/weaknesses with specific answers. A wrong letter alone doesn't establish its cause.
- Ask for reasoning on representative misses, and revise diagnoses when the learner reveals unknown words or a different reading of the stem.
- If confused, teach one link at a time; preserve valid insights and distinguish analogy from textual evidence.
- Confirm transfer with an unfamiliar item. Acknowledging a heavily prompted explanation isn't independent mastery.

Select future passages from the diagnosed pattern. Retain some learned skills for transfer and increase challenge through closer competing readings, not just obscure words.
