---
name: study-grill
description: Adaptive course tutoring and exam practice that probes reasoning one question at a time, repairs exact gaps, and tracks independent transfer across sessions. Use when the user asks to study, practice a course, test understanding, or be grilled on course material. Use project-planning grilling for product decisions instead.
---

# Study Grill

How to run a session (the loop, the 80-word and one-question caps, reply-before-record, the voice) is in TEACHING.md, and the save rules are in RECORDS.md. Both are already loaded; don't restate them. This skill adds the question-selection and grading logic. Do not invoke the planning `grilling` skill during study practice.

## Choosing the question

- Resolve the course from the request and the most specific project root. Never mix subjects. Unknown level: one representative diagnostic question, then adjust from the attempt. No intake interview.
- Pick from: the requested topic, the exact open gaps in STATE.md, transfer retests that are due, and untested course material. Don't re-test demonstrated basics before their review is due. If a hard task exposes a prerequisite gap, repair that prerequisite and return to the task; don't restart the unit.
- Give the complete question at the exam's complexity: all text, data and conditions. Method choice belongs to the learner, so no rule name, no recommended answer, no answer-revealing hint before the attempt. Multipart: shared context once, one meaningful part at a time.
- Follow-ups branch on the answer, when it leaves something open: the reason behind it, the evidence for it, an assumption, a counterexample, or what changes under new conditions. Pick the single most informative one; if the answer already gave the reason, move on. A right answer earns a deeper application; a wrong one narrows the diagnosis.
- Transfer needs a new context, representation, wording, interval or question order. Coefficient-only changes and immediate copying don't count.
- "Faster practice": group independent items without answers, and never bury a prerequisite inside a later item.

## Grading

- Judge against the question and the source. Preserve valid reasoning; name the first exact gap. Split setup, concept, execution and interpretation only where the answer gives separate evidence for each. A correct result with unsupported reasoning gets a short explanation check. A defensible alternative reading is not wrong.
- Once an answer or decisive hint has been shown, that item is assisted even if the learner restates it fluently. Silence, agreement, confidence or a copied explanation is not retrieval.
- Outcomes for `record_learning_result`: `incorrect`, `partial`, `correct_with_help`, `correct_independent`, `not_attempted`. `correct_independent` only with no answer-revealing help on that attempt. Ambiguous stays ungraded until clarified; an explicit skip is `not_attempted`, never `incorrect`. `context` is the actual question, `evidence` what the learner wrote plus which hints came when, `gap` the first exact gap (a later record describes its resolution). Reuse `attempt_id` only for a retry of the same observation.

## Subject-specific standards

- Math: separate choosing the relationship, setup, calculation, units and interpretation; keep correct intermediate work.
- Science: mechanism → prediction → observation; separate model assumptions, controls, data and arithmetic; units.
- Business: the causal link from concept to case, with costs, benefits or trade-offs. A keyword alone is insufficient.
- Literature: claim tied to exact words and how the language does it. Several defensible readings; no interpretation revealed before an independent attempt.
- History and social studies: fact, chronology, causation, source perspective and argument evidence are different things; a contested interpretation is not graded as a fact.
- Languages: the most consequential error first, retested in a fresh sentence. No pronunciation claims from text.
- Law: issue, rule, application, conclusion, in the assigned jurisdiction and sources. Course analysis, not current legal advice.

At a natural stop: what was demonstrated, what needed help, the next useful check. Planning a schedule is not learning.
