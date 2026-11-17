---
name: ap-calc-test
description: Create, revise, review, and grade original AP Calculus mock tests and progress checks with FRQ-dominant chapter practice, authentic exam-level reasoning, College Board-informed question layout, private rubrics, and verified interactive delivery. Use for AP Calc assessment generation, not ordinary single-question tutoring.
---

# AP Calc Test

Use this as the canonical Calculus assessment skill. The older `ap-calc-mock` and `ap-calc-progress-check` names route here. Follow the user's requested scope, difficulty, count, calculator rules, and delivery format. Existing Chapter 2 tests are workflow references, not difficulty ceilings.

Adapt the Business practice skill's source-grounded assessment, shared stimulus, clean navigation, revision-specific attempts, and private authoring workflow. Calculus needs mathematical notation, multipart reasoning and written grading; do not import Business's four-choice schema, business frameworks, embedded answer bank, or standing publication authorization.

## Learner defaults: assessment before coaching

- Make FRQs the main part of chapter mocks by **score and expected working time**, not merely by counting subparts. Aim for about **75% FRQ weighting** as a practical default; scale to scope and user constraints. For example, several substantial multipart FRQs and a small MCQ section may fit. This is a learner preference, not the official AP exam blueprint. For an explicitly requested full official-format simulation, verify and use that year's published blueprint instead.
- Match the complexity of the learner's actual teacher test: selecting the right quantity and method, combining representations, algebra, interpretation, and justification. Difficulty should come from those decisions, not gratuitous arithmetic or untaught content. Do not call a collection of routine rule drills exam-level practice.
- Keep method labels, formulas that reveal the solution path, worked examples, hint panels, difficulty tags and misconception labels out of the student assessment. A question explicitly assessing a required process (e.g., the limit definition) may name that process. Use neutral question numbers and authentic task verbs.
- Let the learner attempt the setup independently. In interactive review, respond to the specific error while preserving correct reasoning; distinguish independent answers from prompted answers. Release complete worked solutions after submission or when explicitly requested. An explanation request during a mock is permission to help; record that assistance rather than claiming an independent score.
- For retests, change context, wording, inputs, intervals, representations and part order where useful, not only coefficients. Include unprompted transfer checks. Do not infer unit mastery from scaffolded success.

Read [assessment-design.md](references/assessment-design.md) when constructing the blueprint. Read [college-board-layout.md](references/college-board-layout.md) before laying out questions or refreshing format research.

## Establish the assessment

1. Keep mocks under the subject folder's `practice/`; list each finished one in `practice/MOCKS.md` and read that list before creating, revising or grading.
2. Check the current AP Calc worksheets on disk (the subject folder's RESOURCES.md says where) and any relevant teacher directions. If a supplied Classroom or Drive link fails outside a signed-in session, inspect the already-open browser tabs before declaring it inaccessible.
   When the user asks for ideas from the worksheets' **Test Prep** sections, inspect those sections in the original PDFs, including any graph or equation that text extraction loses. Build a private mapping from each new question to the concept and likely misconception it tests. Write original numbers and contexts rather than copying worksheet items.
3. Check the current [AP Calculus AB course framework](https://apcentral.collegeboard.org/courses/ap-calculus-ab) and recent [released free-response questions and scoring information](https://apcentral.collegeboard.org/courses/ap-calculus-ab/exam/past-exam-questions) for skill expectations, directions, and part wording. Exam counts and timing can change; do not assume a chapter mock has official exam proportions. Label original questions as original practice.
4. Make a private coverage map: tested topics, representations, mathematical practices, calculator status, difficulty progression, and misconceptions. Distinguish the teacher's chapter numbering from College Board unit numbering. Ask only if the requested scope cannot be inferred from the user's materials.

## Write questions and key

- Prefer reasoning over repetitive computation. Mix formulas, tables, graphs, and contexts. Ask students to calculate, interpret, justify, and assess a flawed claim. Make every needed domain, unit, input, and graph point explicit.
- Match MCQ choice count to the verified target-year format or supplied teacher test; do not hard-code a historic count as universal. Each has one defensible answer and distractors traceable to real mistakes. Check each choice independently. Avoid cues in headings or later parts that reveal the answer.
- FRQs use clear labeled parts and award method, notation, units, and justification credit. Work every part independently before finalizing the private rubric; check alternate valid methods and edge cases.
- Keep the complete key, rubrics, skill tags, and author bank outside the published student page. If instant MCQ scoring is requested, the page may contain only the MCQ answers and explanations needed for that feature. Do not reveal them before submission.
- Do not copy unreleased or access-restricted AP Classroom questions into the student mock. Use teacher materials to understand scope and phrasing, then author original problems.

## Build the student interface

Use College Board-informed **question typography and structure** within the existing usable browser shell: a numbered shared stimulus, rendered math, legible figures/tables, and visibly separated parts. All needed data must remain accessible while answering; repeat it when necessary rather than forcing the learner to scroll back through chat. Use the public-source layout reference below, and distinguish it from an inspected live AP Classroom interface. Respect an explicit PDF or paper request rather than forcing an interactive page.


For a new interactive HTML mock, use the `ap-lit-practice` skill's `assets/practice-template.html` as the visual reference, adapted to math rather than poem-specific behavior.

- Use a restrained header, full-height split view, question or data on the left, response on the right, and a bottom bar with Back, progress, Review answers, and Next. On narrow screens use Question and Response tabs.
- Give one question at a time, accessible labeled choice selection, a clear-answer action, a review flag, a review grid before submission, and an explicit submission result. Keep explanations and MCQ scores hidden until submission. Keep the mock untimed unless the user asks otherwise.
- For FRQs allow typed work and multiple handwritten photos; save text locally and photos in IndexedDB. Let the student download an attempt containing their choices, written responses, flags, and images. State plainly that FRQs require written grading.
- When only the UI changes and question order remains identical, preserve or migrate saved attempts. When question content or order changes, use new storage version keys so old answers cannot attach to new questions. Never reset learner work as part of QA.

## Verify and deliver

1. Check question count, scope coverage, FRQ share of marks and expected time, answer indices, FRQ rubric totals, computations, units, graph/table consistency, and the absence of private FRQ solutions from the student file. Inspect the student version for inadvertent method hints and later-part answer leakage. Run `node --check` on authored JavaScript and extracted inline scripts.
2. Serve the page locally. In a separate QA origin or profile, test choice and flag persistence, clear answer, FRQ text after reload, photo attachment and removal, review and submission, scoring, export with image data, math rendering, and desktop and phone layouts. Check console errors and accessibility labels. A successful syntax check or HTTP response alone is insufficient.
3. Publish only when the learner asks, and only the student page; keep private keys and banks out of anything published.
4. Report the live or local link, exact question count, what was tested, and where the private guide lives. Do not expose answers during an unfinished attempt.

