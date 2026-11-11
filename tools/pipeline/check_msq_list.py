#!/usr/bin/env python3
"""Free check (one HTTP GET, no model calls): does gamedata.msq_paths cover every main-scenario quest?

usage: check_msq_list.py [--wikitext FILE] [--per-path]

Compares the quest list of the wiki page Main Scenario Quests at revision 1560298 with the quests whose
JournalGenre is main scenario, by name. A bare link title keeps its parentheses when the game's name does
(The Company You Keep (Maelstrom)), else they are a disambiguation (Solution Nine (Quest)). A name the wiki and
the game list a different number of times is reported, not failed: the wiki lists Close to Home once per city
where the game splits it into 8 quests. Then every msq_paths file is read with gamedata.read_rows.

Exits non-zero when a wiki quest has no main-scenario quest, a main-scenario quest is not on the wiki, or a
file cannot be read. The folders csv/*/opening (the 3 city openings), dungeon, custom and story are outside
the corpus because the pipeline does not translate them.
"""
import argparse
import json
import re
import sys
import urllib.request
from collections import Counter, defaultdict

import gamedata

REVISION = 1560298  # 2026-09-26
# index.php?action=raw sits behind a Cloudflare browser challenge; api.php returns the same wikitext.
WIKI = f"https://ffxiv.consolegameswiki.com/mediawiki/api.php?action=parse&oldid={REVISION}&prop=wikitext&format=json&formatversion=2"
# The table above this heading links to questline pages, not quests.
QUESTS_START = "==Seventh Umbral Era Quests=="
ROW = re.compile(r"\|\s*'*\[\[([^\]|]+)(?:\|([^\]]+))?\]\]'*\s*\|\|")
# The game writes Α Test of Wιll with Greek Alpha and iota.
GREEK = str.maketrans("ΑΒΕΖΗΙΚΜΝΟΡΤΥΧαιοε", "ABEZHIKMNOPTYXaioe")


def normalize(name):
    return re.sub(r"[^a-z0-9]", "", name.translate(GREEK).lower())


def wiki_titles(text):
    """One tuple per quest row: the names it may go by in the game, in the order to try them."""
    rows = []
    for line in text[text.index(QUESTS_START):].splitlines():
        if match := ROW.match(line):
            target, shown = match.groups()
            bare = re.sub(r"\s+\([^)]*\)$", "", target)
            rows.append((shown,) if shown else (target,) if bare == target else (target, bare))
    return rows


def compare(rows, quests):
    """Report of wiki rows against {stem: quest}. A row matches the main-scenario quests of its first name that has any."""
    msq = defaultdict(list)
    for quest in quests.values():
        if quest["msq"]:
            msq[normalize(quest["name"])].append(quest["stem"])
    wiki = Counter()
    missing, kept = [], 0
    for titles in rows:
        keys = [normalize(t) for t in titles if normalize(t) in msq]
        if not keys:
            missing.append(titles[0])
            continue
        wiki[keys[0]] += 1
        kept += len(titles) == 2 and keys[0] == normalize(titles[0])
    names = {normalize(quest["name"]): quest["name"] for quest in quests.values() if quest["msq"]}
    outside = Counter(normalize(quest["name"]) for quest in quests.values() if not quest["msq"])
    return {
        "wiki_rows": len(rows), "msq_stems": sum(map(len, msq.values())), "matched": sum(wiki.values()),
        "kept_parentheses": kept,
        "wiki_without_stem": missing,
        "stems_without_wiki": sorted(stem for key, stems in msq.items() if key not in wiki for stem in stems),
        "count_differences": [
            {"name": names[key], "wiki": wiki[key], "stems": stems, "outside_msq": outside[key]}
            for key, stems in sorted(msq.items()) if key in wiki and wiki[key] != len(stems)
        ],
    }


def read_corpus(source):
    """({path: translatable rows}, {path: error}) over gamedata.msq_paths."""
    counts, errors = {}, {}
    for path in gamedata.msq_paths(source):
        try:
            counts[path] = sum(row["skip"] is None for row in gamedata.read_rows(source, path))
        except SystemExit as stop:
            errors[path] = str(stop)
    return counts, errors


def fetch():
    request = urllib.request.Request(WIKI, headers={"User-Agent": "FFXIVMSQThai-Content check_msq_list.py"})
    with urllib.request.urlopen(request, timeout=60) as response:
        page = json.load(response)["parse"]
    if page["revid"] != REVISION:
        raise SystemExit(f"wiki returned revision {page['revid']}, not {REVISION}")
    return page["wikitext"]


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--wikitext", help="read a saved copy of the page instead of fetching it")
    parser.add_argument("--per-path", action="store_true", help="print the translatable-row count of every file")
    args = parser.parse_args()
    text = open(args.wikitext, encoding="utf-8").read() if args.wikitext else fetch()
    source = gamedata.Source()
    quests = gamedata.quests(source)
    report = compare(wiki_titles(text), quests)
    counts, errors = read_corpus(source)

    for name in report["wiki_without_stem"]:
        print(f"FAIL wiki quest with no main-scenario quest: {name}")
    for stem in report["stems_without_wiki"]:
        print(f"FAIL main-scenario quest not on the wiki: {stem} {quests[stem]['name']}")
    for path, error in errors.items():
        print(f"FAIL unreadable: {error}")
    for diff in report["count_differences"]:
        print(f"count differs: {diff['name']}: {diff['wiki']} wiki rows, {len(diff['stems'])} quests {diff['stems']}, "
              f"{diff['outside_msq']} of that name outside the main scenario")
    if args.per_path:
        for path, count in counts.items():
            print(f"{count:6d} {path}")
    empty = [path for path, count in counts.items() if path.startswith("quest/") and count == 0]
    cutscenes = sum(path.startswith("cut_scene/") for path in counts)
    print(f"wiki quest rows: {report['wiki_rows']}, main-scenario quests: {report['msq_stems']}, matched: {report['matched']} "
          f"({report['kept_parentheses']} by a title with its parentheses), count differences: {len(report['count_differences'])}")
    print(f"files read: {len(counts)} of {len(counts) + len(errors)} ({len(counts) - cutscenes} quest, {cutscenes} cut_scene), "
          f"translatable rows: {sum(counts.values())}, quests with none: {len(empty)} {[path.split('/')[-1] for path in empty]}")
    print(f"datamining {source.commit[:12]}, wiki {args.wikitext or f'revision {REVISION}'}")
    if report["wiki_without_stem"] or report["stems_without_wiki"] or errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
