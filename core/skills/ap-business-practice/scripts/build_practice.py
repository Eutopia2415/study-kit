#!/usr/bin/env python3
"""Build a self-contained AP Business case practice from a validated bank."""
import argparse
import hashlib
import html
import json
import re
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
LETTERS = "ABCD"

def require(condition, message):
    if not condition:
        raise ValueError(message)

def nonempty(value):
    return isinstance(value, str) and bool(value.strip())

def validate(bank):
    require(isinstance(bank, dict), "Assessment must be a JSON object.")
    for field in ("id", "title", "rights"):
        require(nonempty(bank.get(field)), f"{field} must be a nonempty string.")
    require(re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", bank["id"]), "id must be a lowercase slug.")
    require(bank["rights"] in ("original", "user-provided", "permission"), "Unsupported rights value.")
    source = bank.get("source_url", "")
    require(isinstance(source, str), "source_url must be a string.")
    if source:
        parsed = urlparse(source)
        require(parsed.scheme in ("http", "https") and bool(parsed.netloc), "source_url must use HTTP(S).")
    # Accept older banks with a minutes field, but new pages are untimed.
    if "minutes" in bank:
        minutes = bank["minutes"]
        require(type(minutes) is int and 1 <= minutes <= 180, "Legacy minutes must be an integer from 1 to 180.")
    cases = bank.get("cases")
    require(isinstance(cases, list) and bool(cases), "cases must be a nonempty list.")
    for index, case in enumerate(cases, 1):
        require(isinstance(case, dict) and nonempty(case.get("title")), f"Case {index} needs a title.")
        paragraphs = case.get("paragraphs")
        require(isinstance(paragraphs, list) and bool(paragraphs) and all(nonempty(p) for p in paragraphs),
                f"Case {index} needs nonempty paragraphs.")
    questions = bank.get("questions")
    require(isinstance(questions, list) and 1 <= len(questions) <= 40, "Provide 1 to 40 questions.")
    for n, q in enumerate(questions, 1):
        prefix = f"Question {n}: "
        require(isinstance(q, dict), prefix + "must be an object.")
        for field in ("stem", "explanation", "skill"):
            require(nonempty(q.get(field)), prefix + field + " must be nonempty.")
        options = q.get("options")
        require(isinstance(options, list) and len(options) == 4 and all(nonempty(o) for o in options),
                prefix + "exactly four nonempty options are required.")
        require(len({o.strip().casefold() for o in options}) == 4, prefix + "options must be distinct.")
        require(q.get("answer") in list(LETTERS), prefix + "answer must be A–D.")
        case_index = q.get("case_index")
        require(type(case_index) is int and 0 <= case_index < len(cases), prefix + "case_index must identify a case.")
        difficulty = q.get("difficulty")
        require(type(difficulty) is int and 1 <= difficulty <= 5, prefix + "difficulty must be 1–5.")
        paragraphs = q.get("evidence_paragraphs")
        require(isinstance(paragraphs, list) and bool(paragraphs) and
                all(type(i) is int and 1 <= i <= len(cases[case_index]["paragraphs"]) for i in paragraphs),
                prefix + "evidence_paragraphs must reference paragraphs in its case.")
        distractors = q.get("distractor_explanations")
        expected = set(LETTERS) - {q["answer"]}
        require(isinstance(distractors, dict) and set(distractors) == expected and all(nonempty(v) for v in distractors.values()),
                prefix + "explain exactly the three incorrect choices.")
    return bank

def script_json(value):
    # Escape HTML parsing delimiters as well as Unicode JavaScript line separators.
    return (json.dumps(value, ensure_ascii=False, separators=(",", ":"))
            .replace("&", r"\u0026").replace("<", r"\u003c").replace(">", r"\u003e")
            .replace("\u2028", r"\u2028").replace("\u2029", r"\u2029"))

def render(bank):
    validate(bank)
    canonical = json.dumps(bank, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    revision = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    # Only the data needed by the browser enters the student payload.
    student = {
        "id": bank["id"], "title": bank["title"], "revision": revision,
        "storage_id": "ap-business-" + bank["id"] + "-" + revision[:16],
        "cases": bank["cases"],
        "questions": [{"n": n, "stem": q["stem"], "options": q["options"], "case_index": q["case_index"]}
                      for n, q in enumerate(bank["questions"], 1)],
        "key": [q["answer"] for q in bank["questions"]],
        "explanations": [q["explanation"] for q in bank["questions"]],
    }
    source_html = ""
    if bank.get("source_url"):
        source_html = '<p class="source"><a href="' + html.escape(bank["source_url"], quote=True) + '" target="_blank" rel="noopener">Source</a></p>'
    substitutions = {
        "PAGE_TITLE": html.escape("AP Business Practice · " + bank["title"]),
        "TITLE": html.escape(bank["title"]),
        "SOURCE_HTML": source_html,
        "BANK_JSON": script_json(student),
    }
    template = (ROOT / "assets" / "practice-template.html").read_text(encoding="utf-8")
    tokens = set(re.findall(r"@@([A-Z_]+)@@", template))
    require(tokens == set(substitutions), "Template placeholders do not match builder fields.")
    output = re.sub(r"@@([A-Z_]+)@@", lambda m: substitutions[m.group(1)], template)
    private = {"revision": revision, "difficulty_calibration": "author-estimated-not-official",
               "assessment": bank}
    return output, private

def build(bank, output_dir):
    document, private = render(bank)
    output_dir = Path(output_dir)
    public_path = output_dir / "public" / "index.html"
    private_path = output_dir / "private" / "assessment.json"
    require(not public_path.exists() and not private_path.exists(), "Output already exists; use a fresh directory.")
    public_path.parent.mkdir(parents=True, exist_ok=True)
    private_path.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation protects against accidentally replacing an existing set.
    with private_path.open("x", encoding="utf-8") as handle:
        json.dump(private, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    with public_path.open("x", encoding="utf-8") as handle:
        handle.write(document)
    return public_path, private_path

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("assessment", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    try:
        bank = json.loads(args.assessment.read_text(encoding="utf-8"))
        public, private = build(bank, args.out)
    except (ValueError, OSError) as exc:
        parser.exit(1, "Error: " + str(exc) + "\n")
    print("Student practice: " + str(public.resolve()))
    print("Tutor metadata: " + str(private.resolve()))
    print("Questions: " + str(len(bank["questions"])))
    print("Serve public/ only. Difficulty labels are omitted from the student page.")

if __name__ == "__main__":
    main()
