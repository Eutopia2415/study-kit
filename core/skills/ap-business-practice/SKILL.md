---
name: ap-business-practice
description: Create and grade interactive AP Business case-study practice from the learner's course materials, using original cases, four-choice questions, evidence-based explanations, and a compact browser exam. Use for AP Business practice creation, review, or diagnostic tutoring.
---

# AP Business Practice

Build questions from the learner's actual module, notes, textbook, and sample question style. Treat “AP Business” as the learner's course label; do not claim that a new set is an official exam or invent an official blueprint.

## Establish scope

- Save each set under the subject folder's `practice/` and add a line for it to `practice/MOCKS.md`. Keep the answer bank separate from the student page.
- Identify the unit, concepts, source pages, question count, choice format, and requested difficulty from supplied material. If a source is missing, author within the known scope and label uncertainty rather than fabricate its coverage.
- Prefer short original fictional cases with concrete customers, costs, constraints, choices, and outcomes. Reuse a case for related questions when that tests connected reasoning.
- Keep every question on the requested business scope and score it within the same set.

## Author questions

Use four A–D options for the existing course practice pattern unless the learner's supplied format calls for another. Ask for application and judgment, not just definitions. Mix identification, calculation, interpretation of evidence, and evaluation. For each calculation, state the relevant assumptions and verify units and arithmetic.

Each item needs one best answer, a case paragraph reference, a private skill and difficulty estimate, an explanation, and a specific reason each distractor fails. Check that plausible competitors fail on the facts of the case. Balance answer letters and avoid clues from answer length or wording.

For written responses or tutoring, use Point → Evidence → Explanation → Judgment when evaluation is called for. Tie the judgment to a condition, tradeoff, or limitation in the case. Do not treat a named framework such as PESTEL or competitive strategy as analysis until the relevant facts and business effects are explained.

Read [assessment-format.md](references/assessment-format.md) before building a bank.

## Build the browser practice

The bundled builder makes a self-contained HTML page and a separate private bank:

```sh
python3 "<skill-dir>/scripts/build_practice.py" assessment.json --out "<new-output-directory>"
```

The output is `public/index.html` and `private/assessment.json`. Use a fresh output directory for a revision. Serve or publish only `public/`. The browser page contains a left case pane, a right question pane, bottom Back/Review/Next controls, a mobile case/question switch, saved progress, review, and optional feedback after submission. AP Business worksheets are untimed: do not show a clock, timer control, countdown message, or elapsed-time result. Keep the visible title and controls concise. Avoid promotional subtitles and repeated instructions.

The local page includes its answer key for browser grading. UI concealment is not secure against source inspection; a proctored test would need server-side grading.

## Verify, publish, and hand off

When changing the builder or template, run:

```sh
python3 "<skill-dir>/scripts/test_builder.py"
```

For each set, verify question count, exact case references, calculations, generated JavaScript, and answer/explanation alignment. Inspect the page in a browser at desktop and iPad portrait widths. On iPad, case and question tabs must switch cleanly, and Back/Review/Next must remain usable at the bottom. Exercise a choice, navigation, review, and submission. Use a separate QA attempt so a learner's saved answers remain intact. Keep the handoff page fresh and unsubmitted.

Don't publish a set anywhere unless the learner asks; open the local page and hand it off.

Deliver the student link or file and keep the key in the private folder. If the learner sends results, grade against the matching bank revision, report the raw practice score, and diagnose errors from their actual answers. Ask for reasoning on representative misses before assigning a cause. Do not infer an official AP score from a short set.
