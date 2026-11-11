#!/usr/bin/env python3
"""Remove the team rows that would hide a haiku/ translation in the plugin.

usage: strip_team_overlap.py [--apply]

The plugin keeps the first translation it loads for a key, so a team row whose key equals a key of a haiku/
file can show instead of the Haiku line. The targets are, for each file in haiku/, the team's file of that
quest (its repo_file) and the cutscenes.json next to it, in th/ and in the editor/public/th/ mirror. Without
--apply the tool lists the colliding rows of every team file and changes nothing; with --apply it removes the
ones in the targets. Collisions outside the targets are generic lines that many quests share ("Of course!")
and stay. A second --apply changes nothing.
"""
import argparse
import json
import re
from pathlib import Path

import pipeline

MIRRORS = ("th", "editor/public/th")
# The plugin's ToPureAlphanumericKey, and the variants it also registers: without a leading (-Name-) tag,
# and each side of an "a/b" choice.
SE = re.compile(r"[\x02][\s\S]{1,4}[\x03]|[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]")
SLASH = re.compile(r"\b(\w+)\s*/\s*(\w+)\b")
TAG = re.compile(r"^\(-.+?-\)")


def pure(s):
    k = "".join(c.lower() for c in SE.sub("", s) if c.isascii() and c.isalnum())
    for w in ("forenamesurname", "forename", "surname", "playerplayer", "player"):
        k = k.replace(w, "")
    return k


def variants(text):
    clean = SE.sub("", text).replace("*", "")
    results = [clean]
    if TAG.sub("", clean, count=1) != clean:
        results.append(TAG.sub("", clean, count=1))
    for m in SLASH.finditer(clean):
        results = [r.replace(m.group(0), g) for r in results for g in (m.group(1), m.group(2))]
    return {k for k in map(pure, results) if k}


def keys(d):
    return variants(d.get("text_en") or "") | ({d["key"]} if d.get("key") else set())


def loaded(d):
    return bool((d.get("text_en") or "").strip() and (d.get("text") or "").strip())


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--apply", action="store_true", help="remove the colliding rows from the target files")
    args = parser.parse_args()
    haiku, targets = set(), set()
    for f in sorted(pipeline.PLUGIN_OUT.glob("*.json")):
        plugin = json.loads(f.read_text(encoding="utf-8"))
        for d in plugin["dialogues"]:
            haiku |= keys(d)
        if plugin["repo_file"]:
            targets |= {plugin["repo_file"], f"{plugin['repo_file'].split('/')[0]}/{pipeline.SHARED_TEAM_FILE}"}
    targets = {name for name in targets if (pipeline.ROOT / MIRRORS[0] / name).exists()}

    counts = {"REMOVE": 0, "keep": 0}
    for mirror in MIRRORS:
        for f in sorted((pipeline.ROOT / mirror).rglob("*.json")):
            raw = f.read_text(encoding="utf-8")
            data = json.loads(raw)
            if "dialogues" not in data:
                continue
            hit = [d for d in data["dialogues"] if loaded(d) and keys(d) & haiku]
            if not hit:
                continue
            action = "REMOVE" if str(f.relative_to(pipeline.ROOT / mirror)) in targets else "keep"
            counts[action] += len(hit)
            print(f"{action:6} {f.relative_to(pipeline.ROOT)}: {len(hit)} of {len(data['dialogues'])} rows collide")
            if args.apply and action == "REMOVE":
                data["dialogues"] = [d for d in data["dialogues"] if d not in hit]
                f.write_text(json.dumps(data, ensure_ascii=False, indent=2) + ("\n" if raw.endswith("\n") else ""), encoding="utf-8")

    differ = [name for name in sorted(targets) if len({(pipeline.ROOT / m / name).read_bytes() for m in MIRRORS if (pipeline.ROOT / m / name).exists()}) > 1]
    print(f"haiku keys: {len(haiku)}; target files: {', '.join(sorted(targets))}")
    print(f"colliding rows in target files: {counts['REMOVE']} ({'removed' if args.apply else 'run with --apply to remove'}); elsewhere, kept: {counts['keep']}")
    if differ:
        raise SystemExit(f"th/ and its mirror differ: {differ}")


if __name__ == "__main__":
    main()
