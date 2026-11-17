# Business case assessment data

Supply UTF-8 JSON to `scripts/build_practice.py`:

```json
{
  "id": "business-unit1-02",
  "title": "Business Unit 1",
  "source_url": "",
  "rights": "original",
  "cases": [
    {
      "title": "Case 1 · LunchLink",
      "paragraphs": [
        "Parents order lunches for children at an after-school program.",
        "The lunches cost $7 to make and deliver; parents pay $10."
      ]
    }
  ],
  "questions": [
    {
      "case_index": 0,
      "stem": "Who is the customer in the case?",
      "options": ["The parents", "The children", "The delivery company", "The program staff"],
      "answer": "A",
      "explanation": "The parents purchase the lunches; the children consume them.",
      "skill": "customer versus consumer",
      "difficulty": 2,
      "evidence_paragraphs": [1],
      "distractor_explanations": {
        "B": "The children eat the lunches but do not buy them.",
        "C": "The delivery company is not the buyer.",
        "D": "The staff do not purchase the lunches."
      },
      "source_module": "1.1"
    }
  ]
}
```

This is a schema example, not a finished assessment. `case_index` starts at 0. `evidence_paragraphs` starts at 1 within that case. `rights` is `original`, `user-provided`, or `permission`; establish it from the actual material. `source_url` may be empty, or an HTTP(S) link. Use 1–40 questions. New AP Business sets are untimed; the builder accepts a legacy `minutes` field in older banks but does not show or use it.

Use exactly four distinct options and answer A–D. Estimate private difficulty from 1–5. Explain exactly the three incorrect letters in `distractor_explanations`. `source_module` and source page metadata may be kept in the private bank for traceability; they do not enter the student page. The builder freezes the input with a revision hash, which separates saved browser attempts across revisions.
