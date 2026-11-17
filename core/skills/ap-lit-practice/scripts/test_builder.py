#!/usr/bin/env python3
"""Meaningful builder checks: validation, variable inputs, privacy and escaping."""
import copy
import json
import re
import subprocess
import tempfile
import unittest
from pathlib import Path
from build_practice import build, render

def fixture(count=3):
    # Synthetic content tests mechanics; it is not a student assessment.
    question = {
        "stem": "Which image appears in the passage?",
        "options": ["A lamp", "A boat", "A mountain", "A clock", "A road"],
        "answer": "A", "explanation": "The first line explicitly names a lamp.",
        "skill": "PRIVATE_SKILL_SENTINEL", "difficulty": 2, "evidence_lines": [1],
        "distractor_explanations": {k: "This image is not mentioned." for k in "BCDE"}
    }
    return {
        "id": "builder-qa", "title": "A Test Window", "author": "Synthetic fixture",
        "source_url": "", "rights": "permission", "minutes": 7,
        "stanzas": [["A lamp stood by the window.", "    Rain crossed the glass."],
                    ["A footstep paused outside."]],
        "questions": [copy.deepcopy(question) for _ in range(count)]
    }

def payload(document):
    return json.loads(re.search(r"const bank=(.*);\nconst questions=", document).group(1))

class BuilderTests(unittest.TestCase):
    def test_variable_counts_and_stanzas(self):
        for count in (1, 3, 13):
            output, private = render(fixture(count))
            data = payload(output)
            self.assertEqual(len(data["questions"]), count)
            self.assertEqual(data["minutes"], 7)
            self.assertEqual(data["lines"][1]["text"], "    Rain crossed the glass.")
            self.assertTrue(data["lines"][2]["stanzaStart"])
            self.assertFalse(data["lines"][1]["stanzaStart"])
            self.assertEqual(len(private["assessment"]["questions"]), count)
            self.assertNotIn("The Darkling Thrush", output)

    def test_tutor_metadata_is_not_student_payload(self):
        output, private = render(fixture())
        for field in ("difficulty", "evidence_lines", "distractor_explanations", "PRIVATE_SKILL_SENTINEL"):
            self.assertNotIn(field, output)
        self.assertEqual(private["assessment"]["questions"][0]["difficulty"], 2)

    def test_revision_isolation(self):
        a, _ = render(fixture())
        changed = fixture()
        changed["questions"][0]["options"][0] = "The window lamp"
        b, _ = render(changed)
        self.assertNotEqual(payload(a)["storage_id"], payload(b)["storage_id"])

    def test_markup_cannot_break_out(self):
        bank = fixture()
        malicious = '</script><script>alert("test")</script>'
        bank["title"] = malicious
        bank["questions"][0]["stem"] = malicious
        output, _ = render(bank)
        self.assertEqual(output.count("<script>"), 1)
        self.assertEqual(output.count("</script>"), 1)
        self.assertEqual(payload(output)["questions"][0]["stem"], malicious)

    def test_reject_invalid_key_evidence_and_duplicates(self):
        changes = [("answer", "F"), ("evidence_lines", [4]), ("difficulty", True),
                   ("options", ["same"] * 5), ("distractor_explanations", {})]
        for field, value in changes:
            bank = fixture()
            bank["questions"][0][field] = value
            with self.assertRaises(ValueError):
                render(bank)

    def test_reject_unsafe_link(self):
        bank = fixture()
        bank["source_url"] = "javascript:alert(1)"
        with self.assertRaises(ValueError):
            render(bank)

    def test_output_separation_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as temp:
            public, private = build(fixture(), temp)
            self.assertEqual(public.parent.name, "public")
            self.assertEqual(private.parent.name, "private")
            original = public.read_bytes()
            with self.assertRaises(ValueError):
                build(fixture(), temp)
            self.assertEqual(public.read_bytes(), original)

    def test_generated_script_syntax(self):
        output, _ = render(fixture())
        code = re.search(r"<script>([\s\S]*?)</script>", output).group(1)
        try:
            result = subprocess.run(["node", "--check"], input=code, text=True, capture_output=True)
        except FileNotFoundError:
            self.skipTest("Node is unavailable; check JavaScript in the browser.")
        self.assertEqual(result.returncode, 0, result.stderr)

if __name__ == "__main__":
    unittest.main(verbosity=2)

