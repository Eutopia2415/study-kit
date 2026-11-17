---
name: guided-ap-calculus-tutoring
description: Tutor AP Calculus algebra, differentiation, or related-rates work when the learner wants to try each step first or asks for an easier step-by-step explanation.
argument-hint: "[problem or image description]"
allowed-tools:
  - Read
  - Grep
  - Bash
---

# Guided AP Calculus tutoring

## When to use

Use for AP Calculus help with algebraic simplification, exponents, differentiability, derivative rules, tables, related rates, or contextual motion/kinematics practice when the user asks for a guided explanation rather than an answer dump. Default to complete exam-style prompts matching the learner's real assessment complexity; explicit requests for hints, explanations, or a full solution override that default.

Do not use it to claim an image-derived expression is certain when its transcription is ambiguous, or to mark an exercise complete without the learner’s response.

## Inputs / context to gather

1. Restate the exact function, table values, diagram quantities, and requested output with parentheses and exponents made explicit.
2. Identify whether the user wants a hint, a setup check, a full derivation, or a recalculation.
3. Inspect the learner’s existing work first; retain every already-correct step.
4. For an ongoing tutoring thread, identify demonstrated knowledge and the one current uncertainty; if the user asks for the “big picture,” give that map before selecting a workbook/application question.

## Procedure

1. Start from the learner’s demonstrated level. Do not reteach basic differentiation or tangent-line setup unless the current work shows a gap; answer the specific question directly, then ask for one application-level next step.
2. Ask for one next step when the user signals they can try it, e.g. “i can do it” or “dont tell me the answer.” Do not front-load a full solution.
3. Check the governing structure before arithmetic.
   - Piecewise differentiability: continuity (matching values) first, then matching one-sided derivatives.
   - Composition/table: evaluate the inner function first, then use that output as the outer derivative input: `h'(g(x))g'(x)`.
   - Product/quotient: label `u`, `v`, and preserve the subtraction in `u'v - uv'`.
   - Nested power/trig/root: write the inside derivative explicitly before multiplying.
4. Correct only the first invalid factor, sign, table row, or arithmetic operation. Explain it with the exact current expression, then ask for a short confirmation or substitution.
5. For post-test or retest design, match the demonstrated assessment complexity, not merely its topic label. Start with a complete question that requires method choice, wording interpretation, connections among graphs/tables/formulas, and necessary algebra. For a contextual multi-part motion problem, make the learner choose among displacement, average velocity over an interval, instantaneous velocity, instantaneous acceleration, and average acceleration. Retest with a changed context, wording, representation, interval (including a nonzero start when useful), and question order; do not only swap coefficients.
6. Ask one question or meaningful part at a time for an independent attempt. Do not name the rule, give a premature hint, or pre-explain the solution. Give targeted feedback from the learner's setup, distinguish independent success from success after hints, and do not restart basics the learner has demonstrated.
7. For an ELI5 proof/explanation, begin with a tiny numerical case and a learner checkpoint before formal notation. For the finite halves sum, use `1/2 + 1/4 + 1/8 = 7/8` and ask what remains; introduce induction or the multiply-and-subtract proof only after the “missing piece is halved” pattern lands.
8. Preserve mathematically correct unsimplified forms unless the prompt explicitly requires simplification.
9. For an image/recalculation request, state the interpreted source expression before deriving. Keep conclusions conditional if the transcription or user confirmation is missing.
10. End with the next smallest unsolved step or a one-item practice check. Record an unanswered new problem as open rather than mastered.

## Efficiency plan

- Parse and restate notation once; avoid re-deriving from ambiguous shorthand.
- If the learner has already demonstrated the prerequisite, skip the recap and use the workbook/current prompt as the shortest route to the remaining gap.
- For a retest, reuse the concept map but generate one coherent fresh scenario instead of many isolated derivative drills; retain the learner's correct responses and only pursue the next unresolved concept. Do not infer full readiness from scaffolded routine exercises.
- Use the learner’s own work as the shortest path to the single error.
- Stop after a correct check when the user asked for guidance, not a complete lecture.
- Cache the parsed function/table inputs through the session; only re-check them if the user corrects the statement.

## Pitfalls and fixes

- Symptom: a correct rule gives a wrong number from a table -> likely wrong outer input. Fix: read `g(x)` first and look up `h'(g(x))`, not a nearby table row.
- Symptom: a nested derivative is missing a sign/factor -> likely omitted inner derivative. Fix: write the inside and its derivative on a separate line before simplifying.
- Symptom: quotient-rule coefficients were added -> likely loss of `u'v - uv'`. Fix: visually preserve the minus and substitute before combining like terms.
- Symptom: a learner is stuck on `x^(-1/2)` or division -> begin with concrete fractions/cancellation, then introduce reciprocal-exponent notation.
- Symptom: an ELI5 proof gets “i dont understand” -> likely abstraction arrived before a checkable case. Fix: restart at `n=3`, use common denominators and the leftover, then generalize.
- Symptom: image-based verification feels uncertain -> declare the transcription, derive independently, and keep the result conditional until confirmed.
- Symptom: a post-test retest is too easy although it includes the right derivatives -> likely routine, coefficient-swapped questions or a method already selected for the learner. Fix: use a context-rich multi-part prompt with varied intervals/order and ask one decision at a time.
- Symptom: the learner can finish after prompts but struggles independently -> likely hints named the rule or selected the method too early. Fix: track independent versus hinted success and revisit the concept later in a changed context/representation without announcing a transfer check.

## Verification checklist

- [ ] The function, grouping, and requested quantity were stated explicitly.
- [ ] The learner had an opportunity to attempt the next step when appropriate.
- [ ] Continuity/rule structure was checked before arithmetic.
- [ ] Every nested inside derivative, quotient subtraction, and table lookup is visible.
- [ ] A correct unsimplified expression was accepted when allowed.
- [ ] Any image-derived or unanswered result is labeled conditional/open.
- [ ] A retest, if requested, matches the assessment's contextual and method-selection complexity rather than only its derivative topic.
- [ ] No rule, method, or solution was revealed before the learner had a fair independent attempt, unless they explicitly requested it.
- [ ] Independent success and success after hints are not conflated.
