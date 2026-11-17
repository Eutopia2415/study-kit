# Assessment data

The builder uses only Python's standard library. Supply UTF-8 JSON:
```json
{
  "id": "poetry-set-02",
  "title": "Poem title",
  "author": "Poet name",
  "source_url": "https://example.org/poem",
  "rights": "public-domain",
  "minutes": 15,
  "stanzas": [["First line", "    Indented line"], ["Next stanza"]],
  "glossary": [{"term": "literal term", "definition": "Neutral definition."}],
  "questions": [{
    "stem": "In line 2, the image primarily serves to",
    "options": ["Option A", "Option B", "Option C", "Option D", "Option E"],
    "answer": "B",
    "explanation": "Explain the answer using evidence and address the closest distractor.",
    "skill": "imagery and function",
    "difficulty": 3,
    "evidence_lines": [1, 2],
    "distractor_explanations": {
      "A": "Unsupported inference.",
      "C": "Confused relationship.",
      "D": "Overlooked qualification.",
      "E": "Imported detail."
    }
  }]
}
```
This illustrates the schema, not valid literary content for delivery.

Rules:
- Required strings are nonempty; id is a lowercase alphanumeric/hyphen slug.
- rights is public-domain, user-provided, or permission. The author must establish it; the builder cannot verify rights.
- source_url can be empty for a directly supplied source; otherwise HTTP(S). Don't invent sources.
- minutes is an integer 1–180, a suggested benchmark rather than official exam time.
- stanzas contains nonempty arrays of nonempty strings. One verse line per string, with leading spaces preserved. Don't include line-number labels; numbering continues across stanzas.
- glossary is optional. Don't define terms directly tested by questions.
- questions contains 1–40 items; ordinary passage sets should be shorter.
- Five distinct options, answer A–E, integer difficulty 1–5, and valid evidence_lines are required.
- distractor_explanations has exactly the four incorrect letters.
- Text is plain text, not markup. The builder escapes markup and script terminators.

The output freezes the complete input with a content hash. The assessment ID and revision identify browser storage and exported answers. A changed bank doesn't silently inherit old answers.

Student exports include set ID/revision, score, timed minutes, chosen letters, confidence, flags, and unknown words. Skill/difficulty/evidence metadata is private. The offline HTML contains the answer key and explanations for local scoring; UI hiding is not secure proctoring.

Serve only public/, never input JSON, private/, or the skill directory. Use a new output directory for a revision.

When grading later, retrieve the exact private bank matching the exported ID/revision. If unavailable, recover the real questions; don't invent a key from answer patterns.

