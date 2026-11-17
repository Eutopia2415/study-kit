#!/usr/bin/env python3
"""Build a poem practice with interleaved wildcard questions."""
import argparse
import html
import json
import re
import shutil
from pathlib import Path

from build_practice import render, script_json

ROOT = Path(__file__).resolve().parents[1]


def build(assessment_path, output_dir):
    bank = json.loads(Path(assessment_path).read_text(encoding="utf-8"))
    standard_html, private = render(bank)
    if len(bank["questions"]) != 15:
        raise ValueError("The current wildcard layout needs exactly 15 poem questions.")
    wildcard_bank = json.loads((ROOT / "assets/wildcards.json").read_text(encoding="utf-8"))
    count = len(wildcard_bank["questions"])
    if count < 23 or any(len(wildcard_bank[field]) != count for field in ("key", "explanations", "distractors")):
        raise ValueError("Wildcard bank needs at least twenty-three complete questions.")
    tiers = [question.get("tier") for question in wildcard_bank["questions"]]
    if any(tier not in ("easy", "elite") for tier in tiers) or tiers.count("easy") < 5 or tiers.count("elite") < 10:
        raise ValueError("Wildcard bank needs at least five easy and ten elite questions.")
    categories = {"capital city", "people faces", "math", "iGEM", "flags"}
    if {question.get("category") for question in wildcard_bank["questions"]} != categories:
        raise ValueError("Wildcard bank needs the five supported categories.")
    if sum(question["category"] == "people faces" for question in wildcard_bank["questions"]) < 3 or sum(
            question["category"] == "flags" for question in wildcard_bank["questions"]) < 5:
        raise ValueError("Wildcard bank needs three portraits and five flag questions.")
    if any(not any(question["category"] == category and question["tier"] == "elite"
                   for question in wildcard_bank["questions"]) for category in categories - {"people faces"}):
        raise ValueError("Every non-portrait category needs elite questions.")
    for question, answer, distractors in zip(wildcard_bank["questions"], wildcard_bank["key"], wildcard_bank["distractors"]):
        if question.get("kind") != "bonus" or len(question.get("options", [])) != 5 or answer not in "ABCDE" or set(distractors) != set("ABCDE") - {answer}:
            raise ValueError("Wildcard questions need five options, one answer, and four distractor explanations.")
    start = standard_html.index("const bank=") + len("const bank=")
    end = standard_html.index(";\nconst questions=", start)
    student = json.loads(standard_html[start:end])
    student["lines"] = [dict(text=line, stanzaStart=stanza_index > 0 and index == 0)
        for stanza_index, stanza in enumerate(bank["stanzas"]) for index, line in enumerate(stanza)]
    distractors = [question["distractor_explanations"] for question in bank["questions"]]
    glossary = bank.get("glossary", [])
    source = ('<p class="source"><a href="' + html.escape(bank["source_url"], quote=True) +
              '" target="_blank" rel="noopener">Poem source</a></p>') if bank.get("source_url") else ''
    glossary_html = ''
    if glossary:
        glossary_html = '<details class="gloss"><summary>Vocabulary notes</summary>' + ''.join(
            '<p><b>' + html.escape(item["term"]) + ':</b> ' + html.escape(item["definition"]) + '</p>'
            for item in glossary) + '</details>'
    template = (ROOT / "assets/wildcard-template.html").read_text(encoding="utf-8")
    slug = bank["id"] + '-' + private["revision"][:16]
    replacements = {
        "TITLE": html.escape(bank["title"]),
        "TITLE_JSON": script_json(bank["title"]),
        "AUTHOR": html.escape(bank["author"]),
        "GLOSS_AND_SOURCE": glossary_html + source,
        "BANK_JSON": script_json(student),
        "DISTRACTORS_JSON": script_json(distractors),
        "BONUS_JSON": script_json(wildcard_bank),
        "STORAGE_KEY": 'ap-lit-' + slug + '-wildcard',
        "COLOR_KEY": 'ap-lit-' + bank["id"] + '-colors',
        "PRACTICE_ID": slug,
        "DOWNLOAD_NAME": bank["id"] + '-answers.txt',
    }
    tokens = set(re.findall(r'@@([A-Z_]+)@@', template))
    if tokens != set(replacements):
        raise ValueError("Wildcard template placeholders are out of sync.")
    document = re.sub(r'@@([A-Z_]+)@@', lambda match: replacements[match.group(1)], template)
    output_dir = Path(output_dir)
    public = output_dir / 'public'
    private_dir = output_dir / 'private'
    if (public / 'index.html').exists() or (private_dir / 'assessment.json').exists():
        raise ValueError("Output exists; choose a new directory.")
    public.mkdir(parents=True, exist_ok=True)
    private_dir.mkdir(parents=True, exist_ok=True)
    (public / 'index.html').write_text(document, encoding='utf-8')
    (private_dir / 'assessment.json').write_text(json.dumps({**private, 'wildcards': wildcard_bank}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    assets = public / 'assets'
    assets.mkdir(exist_ok=True)
    portrait_names = set(re.findall(r'assets/(celebrity-blend[^"\s]+\.png)',
        ' '.join(question.get('visual', '') for question in wildcard_bank['questions'])))
    for name in portrait_names:
        portrait = ROOT / 'assets' / name
        if not portrait.is_file():
            raise ValueError(f"Missing portrait asset: {name}")
        shutil.copy2(portrait, assets / name)
    return public / 'index.html', private_dir / 'assessment.json'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('assessment', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    try:
        public, private = build(args.assessment, args.out)
    except (ValueError, OSError) as error:
        parser.exit(1, 'Error: ' + str(error) + '\n')
    print('Student practice:', public.resolve())
    print('Private bank:', private.resolve())


if __name__ == '__main__':
    main()
