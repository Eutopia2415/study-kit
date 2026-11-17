#!/usr/bin/env python3
"""Check wildcard output isolation, escaping, and script syntax."""
import json
import re
import subprocess
import tempfile
import unittest
from pathlib import Path

from build_wildcard_practice import build
from test_builder import fixture


class WildcardBuilderTests(unittest.TestCase):
    def test_build_and_escape(self):
        bank = fixture(15)
        bank['title'] = '</script><script>alert("x")</script>'
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'input.json'
            source.write_text(json.dumps(bank))
            public, private = build(source, root / 'set')
            page = public.read_text()
            self.assertEqual(page.count('<script>'), 1)
            self.assertEqual(page.count('</script>'), 1)
            self.assertNotIn('PRIVATE_SKILL_SENTINEL', page)
            self.assertEqual(
                sorted(path.name for path in (public.parent / 'assets').glob('*.png')),
                ['celebrity-blend-frida-keanu.png', 'celebrity-blend-rihanna-chaplin.png',
                 'celebrity-blend-serena-elvis.png'])
            self.assertEqual(len(json.loads(private.read_text())['assessment']['questions']), 15)
            bonus_questions = json.loads(private.read_text())['wildcards']['questions']
            capitals = [question for question in bonus_questions if question['category'] == 'capital city']
            flags = [question for question in bonus_questions if question['category'] == 'flags']
            self.assertGreaterEqual(len(capitals), 5)
            self.assertGreaterEqual(len(flags), 5)
            self.assertTrue(all('class="map-art"' in question['visual'] and 'flag-art' not in question['visual']
                                for question in capitals))
            self.assertTrue(all('class="flag-art"' in question['visual'] and 'map-art' not in question['visual']
                                for question in flags))
            code = re.search(r'<script>([\s\S]*?)</script>', page).group(1)
            result = subprocess.run(['node', '--check'], input=code, text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            with self.assertRaises(ValueError):
                build(source, root / 'set')

    def test_reject_wrong_core_count(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'input.json'
            source.write_text(json.dumps(fixture(14)))
            with self.assertRaises(ValueError):
                build(source, root / 'set')


if __name__ == '__main__':
    unittest.main(verbosity=2)
