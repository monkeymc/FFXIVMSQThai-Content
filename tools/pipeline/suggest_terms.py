#!/usr/bin/env python3
"""Free (no model calls): Japanese names the main scenario uses that terms.json lacks, each with the English that
the aligned English lines use for it, for the user to pick into terms_manual.json.

usage: suggest_terms.py

Reads the translatable rows of gamedata.msq_paths and writes out/terms_suggestions.json, most-used name first.
A name comes from SOURCES: a katakana word, the first part of a full name in ENpcResident (ナナモ of ナナモ・ウル・ナモ),
or LISTED, kanji names that no regex finds. A row has a name when pipeline.Terms, built from terms.json and every
candidate, would give the row that name: ナナモ is not counted inside ナナモ・ウル・ナモ.

The English is the capitalized phrase whose share of the rows with the name most exceeds its share of the other
rows, widened to a longer phrase that keeps most of those rows (Crystal Braves, not Braves) but not to a title
before it (Fortemps, not House Fortemps), and made singular when the singular also scores well (Ascian, not
Ascians). `share` is the part of the rows with the name whose
English contains it; the localization often rewords, so 0.4 is normal. A name whose English is in more than 1%
of the other rows is dropped, since that English is a pronoun or a common word (アタシ is "I").
"""
import json
import re
from collections import Counter

import gamedata
import pipeline

OUT = pipeline.OUT / "terms_suggestions.json"
MIN_KATAKANA_ROWS = 10
MIN_KATAKANA_LENGTH = 3
MAX_OUTSIDE = 0.01
# A longer phrase replaces the pick when it is in more than this share of the pick's rows: 45 of the 57 rows
# with Braves have Crystal Braves (0.79), 76 of 133 with Light have Warrior of Light (0.57), 8 of 16 with
# Alzadaal have Alzadaal III (0.5).
WIDEN_KEEP = 0.5
# The singular replaces a plural pick when its score is this share of the plural's.
SINGULAR_KEEP = 0.5
MAX_WORDS = 4
EXAMPLES = 3
FILTERS = ("in_terms", "no_rows", "no_phrase", "outside")
# A title before a name is not part of it: House Fortemps is in 23 of the 39 rows with Fortemps, Lord Kaien in
# 12 of 13 with Kaien, so no share tells them from Crystal Braves.
TITLES = {
    "House", "Lord", "Lady", "Ser", "Sir", "Master", "Mistress", "King", "Queen", "Emperor", "Empress",
    "Prince", "Princess", "Elder", "General", "Archbishop", "His", "Her", "Your",
}
# Names with kanji, which the katakana source cannot find. Most come from the script flags (English left in
# the Thai) in out/review: 教皇庁 is Vault there, 豪胆将の精兵 True Brothers of the Faith, 武王 Vow.
LISTED = [
    "蛮神", "ガレマール帝国", "光の戦士", "神殿騎士", "教皇庁", "竜詩戦争",
    "豪胆将の精兵", "トールダン7世", "皇都", "帝国", "武王", "理王", "第四世界", "グラズ號",
]

KATAKANA_RUN = re.compile(f"[{pipeline.KATAKANA}][{pipeline.KATAKANA}・]*")
WORD = r"[A-Z][\w'’-]*"
CAPITALIZED_RUN = re.compile(rf"{WORD}(?:\s+(?:of\s+(?:the\s+)?|the\s+)?{WORD})*")


def katakana_names(source, rows):
    runs = Counter(run for row in rows for run in set(KATAKANA_RUN.findall(row["text_ja"])))
    return {ja: None for ja, n in runs.items() if n >= MIN_KATAKANA_ROWS and len(ja) >= MIN_KATAKANA_LENGTH}


def npc_short_names(source, rows):
    """{first part: English first part} of ENpcResident full names whose Japanese and English have as many
    parts, when that first part is always spelt the same: エドモン・ド・フォルタン is Count Edmont de Fortemps, so
    エドモン is not Count."""
    ja, en = source.table("ja/ENpcResident"), source.table("en/ENpcResident")
    i, k = ja[0].index("Singular"), en[0].index("Singular")
    spellings = {}
    for a, b in zip(ja[1:], en[1:]):
        ja_parts, en_parts = a[i].split("・"), b[k].split()
        if len(ja_parts) == len(en_parts) > 1 and len(ja_parts[0]) >= 2 and en_parts[0][:1].isupper():
            spellings.setdefault(ja_parts[0], set()).add(en_parts[0])
    text = "\n".join(row["text_ja"] for row in rows)
    return {name: next(iter(english)) for name, english in spellings.items() if len(english) == 1 and name in text}


def listed_names(source, rows):
    return dict.fromkeys(LISTED)


SOURCES = {"katakana": katakana_names, "npc_short": npc_short_names, "listed": listed_names}


def find(source, rows):
    """({ja: {"source", "npc_short"}}, {source: names found}). A name two sources find keeps the first source."""
    found, counts = {}, {}
    for name, finder in SOURCES.items():
        names = finder(source, rows)
        counts[name] = len(names)
        for ja, english in names.items():
            entry = found.setdefault(ja, {"source": name, "npc_short": None})
            entry["npc_short"] = entry["npc_short"] or english
    return found, counts


def phrases(text):
    """Every run of 1 to MAX_WORDS capitalized words in text that starts and ends on one, joined by of / of the /
    the as the text joins them. A leading The is not part of a name, as in build_terms.sheet_name, nor is a title
    right before a name."""
    out = set()
    for run in CAPITALIZED_RUN.finditer(text):
        words = [re.sub(r"['’]s$|(?<=s)['’]$", "", word) for word in run.group().split()]
        capitals = [n for n, word in enumerate(words) if word[0].isupper()]
        for a, start in enumerate(capitals):
            titled = words[start] in TITLES and start + 1 in capitals
            if words[start] != "The" and not titled:
                out.update(" ".join(words[start:stop + 1]) for stop in capitals[a:a + MAX_WORDS])
    return out


def pick_english(inside, phrase_sets, background, total):
    """(English, runner-up or None) for the rows numbered `inside`, or None when they have no phrase. The
    runner-up is the best phrase that neither contains the pick nor is in it, and is not a common word."""
    count = Counter(phrase for n in inside for phrase in phrase_sets[n])
    if not count:
        return None

    def outside(phrase):
        return (background[phrase] - count[phrase]) / max(total - len(inside), 1)

    def score(phrase):
        return count[phrase] / len(inside) - outside(phrase)

    pick = max(count, key=lambda phrase: (score(phrase), phrase))
    wider = [phrase for phrase in count if f" {pick} " in f" {phrase} " and count[phrase] > WIDEN_KEEP * count[pick]]
    forms = [max(wider + [pick], key=lambda phrase: (len(phrase.split()), count[phrase], phrase))]
    singular = re.sub("ies$", "y", forms[0]) if forms[0].endswith("ies") else forms[0].removesuffix("s")
    if singular != forms[0] and count[singular] and score(singular) >= SINGULAR_KEEP * score(forms[0]):
        forms.insert(0, singular)
    others = [
        phrase for phrase in count
        if outside(phrase) <= MAX_OUTSIDE and not any(phrase in form or form in phrase for form in forms)
    ]
    return forms[0], max(others, key=lambda phrase: (score(phrase), phrase), default=None)


def occurrences(rows, names):
    """{name: [row number]}: the rows pipeline.Terms would give each name to."""
    terms = pipeline.Terms(dict.fromkeys(names, ""))
    rows_of = {}
    for n, row in enumerate(rows):
        for name in terms.used_by(row):
            rows_of.setdefault(name, []).append(n)
    return rows_of


def suggest(rows, found, terms):
    """(candidates by rows, {filter: names dropped}) for the names `found`, over the corpus rows."""
    filtered = dict.fromkeys(FILTERS, 0)
    rows_of = occurrences(rows, {*found, *terms})
    phrase_sets = [phrases(row["text_en"]) for row in rows]
    background = Counter(phrase for phrase_set in phrase_sets for phrase in phrase_set)
    candidates = []
    for ja, origin in found.items():
        inside = rows_of.get(ja, [])
        picked = ja not in terms and inside and pick_english(inside, phrase_sets, background, len(rows))
        built = picked and candidate(ja, origin, rows, inside, *picked)
        reason = (
            "in_terms" if ja in terms else "no_rows" if not inside else "no_phrase" if not picked
            else "outside" if built["outside"] > MAX_OUTSIDE else None
        )
        if reason:
            filtered[reason] += 1
        else:
            candidates.append(built)
    return sorted(candidates, key=lambda c: (-c["rows"], c["ja"])), filtered


def candidate(ja, origin, rows, inside, english, runner_up):
    """The record terms_suggestions.json lists for one name: ja, source, rows, en, share, outside, runner_up
    {en, share} or None, npc_short (ENpcResident's English or None), and examples [{file, ja, en}]."""
    def share(phrase):
        return sum(phrase in rows[n]["text_en"] for n in inside) / len(inside)

    with_english = [n for n in inside if english in rows[n]["text_en"]]
    elsewhere = sum(english in row["text_en"] for row in rows) - len(with_english)
    return {
        "ja": ja, "source": origin["source"], "rows": len(inside), "en": english,
        "share": round(len(with_english) / len(inside), 3),
        "outside": round(elsewhere / max(len(rows) - len(inside), 1), 4),
        "runner_up": runner_up and {"en": runner_up, "share": round(share(runner_up), 3)},
        "npc_short": origin["npc_short"],
        "examples": [{"file": rows[n]["file"], "ja": rows[n]["text_ja"], "en": rows[n]["text_en"]} for n in with_english[:EXAMPLES]],
    }


def main():
    source = gamedata.Source()
    paths = gamedata.msq_paths(source)
    rows = [row for path in paths for row in gamedata.read_rows(source, path) if row["skip"] is None]
    terms = json.loads(pipeline.TERMS.read_text(encoding="utf-8"))
    found, counts = find(source, rows)
    candidates, filtered = suggest(rows, found, terms)
    pipeline.write_atomic(OUT, pipeline.dump({
        "datamining": source.commit, "corpus": {"files": len(paths), "rows": len(rows)},
        "counts": {"found": counts, "filtered": filtered, "kept": len(candidates)}, "candidates": candidates,
    }))
    print(f"corpus: {len(paths)} files, {len(rows)} rows; found {counts}; filtered {filtered}; kept {len(candidates)}")
    print(f"{OUT.relative_to(pipeline.HERE)} from datamining {source.commit[:12]}")


if __name__ == "__main__":
    main()
