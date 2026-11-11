#!/usr/bin/env python3
"""Rebuild terms.json from the datamining name sheets and terms_manual.json. No model calls.

usage: build_terms.py [--at REV]

terms.json maps each Japanese proper noun that main-scenario text uses to its official English name, which
the translation keeps as is (TERMS.md). A sheet name becomes a term when its English starts with a capital
letter, since the sheets write common nouns (vulture, delivery moogle) in lower case; when its spellings
agree (spelling()); and when the Japanese appears in a main-scenario quest file or any cut_scene file.
terms_manual.json adds names that no sheet holds, such as 暁 for the Scions; a name a sheet already gives is an
error, so the two never disagree.
"""
import argparse
import json
import re
from pathlib import Path

import gamedata
from pipeline import TERMS, dump, write_atomic

MANUAL = Path(__file__).resolve().parent / "terms_manual.json"
# Sheet and name column, highest priority first: a Japanese name two sheets spell differently in English
# keeps the first sheet's spelling.
SHEETS = [
    ("ENpcResident", "Singular"), ("BNpcName", "Singular"), ("PlaceName", "Name"),
    ("ContentFinderCondition", "Name"), ("Race", "Masculine"), ("Tribe", "Masculine"), ("Town", "Name"),
]


def sheet_name(ja, en):
    """(ja, en) as a term, or None. A duty's Japanese name carries a category before a space (外郭攻略 カストルム・メリディアヌム)."""
    ja, en = (ja.split() or [""])[-1], re.sub(r"\A[Tt]he ", "", en.strip())
    if len(ja) < 2 or any(c.isascii() for c in ja) or "<" in en or "\n" in en or not en[:1].isupper():
        return None
    return ja, en


def spelling(english):
    """The one English name of several spellings: the shortest, when every other contains it (Gaius in Gaius
    van Baelsar, Aetheryte Plaza in Ul'dah Aetheryte Plaza). None when they disagree (Ifrit-Egi, Ifrit Egi)."""
    short = min(english, key=len)
    return short if all(short.lower() in en.lower() for en in english) else None


def sheet_names(source, sheet, column):
    """{ja: en} of one sheet, without the names whose spellings disagree."""
    ja, en = source.table(f"ja/{sheet}"), source.table(f"en/{sheet}")
    i, k = ja[0].index(column), en[0].index(column)
    english = {}
    for a, b in zip(ja[1:], en[1:]):
        if name := sheet_name(a[i], b[k]):
            english.setdefault(name[0], set()).add(name[1])
    return {name: spelt for name, spellings in english.items() if (spelt := spelling(spellings))}


def msq_text(source):
    return "\n".join(row[2] for path in gamedata.msq_paths(source) for row in source.table(f"ja/{path}")[1:] if len(row) > 2)


def merge(sheets, manual):
    """(terms, counts) from [(sheet, {ja: en})] in SHEETS order and terms_manual.json's {ja: en}. Stops on a manual
    name that a sheet already gives, whether or not the English agrees."""
    terms, origin, counts = {}, {}, []
    for sheet, names in sheets:
        found = {ja: en for ja, en in names.items() if ja not in terms}
        terms.update(found)
        origin.update(dict.fromkeys(found, sheet))
        counts.append((sheet, len(found)))
    for ja in manual:
        if ja in terms:
            raise SystemExit(f'{MANUAL.name}: {ja} is already in {origin[ja]} as "{terms[ja]}"; remove it from {MANUAL.name}')
    return dict(sorted({**terms, **manual}.items())), counts + [(MANUAL.name, len(manual))]


def build(source):
    text = msq_text(source)
    sheets = [
        (sheet, {ja: en for ja, en in sheet_names(source, sheet, column).items() if ja in text})
        for sheet, column in SHEETS
    ]
    return merge(sheets, json.loads(MANUAL.read_text(encoding="utf-8")))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--at", default="HEAD", help="datamining commit to read")
    args = parser.parse_args()
    source = gamedata.Source(args.at)
    terms, counts = build(source)
    write_atomic(TERMS, dump(terms))
    for name, count in counts:
        print(f"{name}: {count}")
    print(f"{TERMS.name}: {len(terms)} terms from datamining {source.commit[:12]}")


if __name__ == "__main__":
    main()
