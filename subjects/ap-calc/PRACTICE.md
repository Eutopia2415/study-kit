# Building question sets the way the AP Calculus AB exam does

Observed from the Course and Exam Description (exam information pages 197–240, and the Fall 2026 clarifications). The tutor may build mimic sets; a real released item always beats a mimic when one fits and hasn't been used.

## The exam (from Fall 2026)

| Section | Questions | Weight | Time | Calculator |
|---|---|---|---|---|
| I Part A, multiple choice | 29 | 35% | 62 min | no |
| I Part B, multiple choice | 13 | 15% | 38 min | yes |
| II Part A, free response | 2 | 16.7% | 30 min | yes |
| II Part B, free response | 4 | 33.3% | 60 min | no |

About 2.1 minutes per MC item in Part A, 2.9 in Part B; 15 minutes per FRQ. Four choices (A–D). Units weighted on the MC section (Unit 1 Limits 10–12%, Unit 2 Differentiation basics 10–12%, Unit 3 composite/implicit/inverse 9–13%, Unit 4 contextual applications 10–15%, Unit 5 analytical applications 15–18%, Unit 6 integration 17–20%, Unit 7 differential equations 6–12%, Unit 8 applications of integration 10–15%).

## How the items are built (what to copy)

- **Representations rotate.** The CED says every exam mixes analytical, graphical, tabular and verbal representations and algebraic, exponential, logarithmic, trigonometric and general functions. The sample MC runs: a limit (analytic), a piecewise differentiability question (analytic, "at what values of x, if any"), a **table** of f, f′, g, g′ with a product-rule evaluation, implicit differentiation, a related-rates **word problem** with the formula supplied, a Riemann-sum limit. A set that is all algebra is not an AP set.
- **Practices weighted.** MC: implementing processes 50–70%, connecting representations 15–30%, justification 10–20%. FRQ adds communication and notation 10–25%, so FRQs ask for the reasoning in words and penalize missing notation.
- **Distractors come from the known errors.** Dropping the inner derivative, sign errors in quotient rule, using f for f′ in a table, treating a limit of a constant as 0, mixing conditions and conclusions of a theorem. Each distractor in a mimic set must be the answer a specific mistake produces; write that mistake next to it in the key.
- **Stems use the CED task verbs.** Calculate, determine, estimate, evaluate, explain, interpret (with units), justify, verify. "Justify" means name the theorem, say why its conditions hold, then apply it. "If any" and "which of the following expressions" are standard phrasings.
- **FRQs are multi-part (a–d), one scenario each,** at least two with a real-world context, and roughly half procedural, half conceptual. A part that says "explain" or "justify" is scored on the reasoning sentence, not the number.

## Sources on disk

Real items come first. When the learner adds one of these to this folder, list it in RESOURCES.md and use it from there:
- The College Board Course and Exam Description (CED) for this course, free on AP Central: its sample questions come with keys and a skill table.
- Released free-response questions with scoring guidelines (AP Central, past years).
- AP Classroom results the learner exports or pastes.
- The teacher's own worksheets, reviews and tests, which outrank everything else as the model for this class.

## Real test questions the learner recalls

Saved under `practice/tests/` as given (question, the learner's answer, the key if known, the miss). They outrank the CED samples as the model for mimic sets, because they are this teacher's format.

## Building a set

1. Prefer real items: a released FRQ or CED sample that matches the unit and hasn't been used (log below).
2. Otherwise build a mimic with the `ap-calc-test` skill: for a 30-minute MC item, 12 questions in Part A style, representations rotated, each with the key, the unit and practice tags, and the mistake behind each distractor; for an FRQ item, one four-part question with its own scoring guideline (points per part, what earns the justification point).
3. Save to `practice/YYYY-MM-DD_<topic>.md` (the skill's HTML alongside if it makes one). The heading says **mimic, not released**.
4. After: score, every miss to the matching `SKILLS.md` row (representation tag in the note), one line per set in the log below.

## Log

| Date | Set | Source (released year / CED / mimic) | Items | Score | Misses went to |
|---|---|---|---|---|---|
