#!/usr/bin/env python3
"""Paid check (model calls for files not attributed yet): how often does the cutscene attribution agree with the team?

usage: check_attribution.py [--model MODEL] VoiceMan_03100 [VoiceMan_03300 ...]

Without --model it scores the attributions the pipeline uses (out/attribution/). With --model it attributes
the files again with that model into out/attribution/eval/<model>/, to compare models on the same files.

The team's per-quest files (th/<patch>/<quest-slug>.json at pipeline.TEAM_REV) say which quest a line was seen in. A cutscene row
counts as evidence when its key is 13 letters or longer and sits in the file of exactly one main-scenario
quest of the expansion. Agreement is the share of those rows the attribution gives to the same quest.
Shared files (cutscenes.json) carry no quest, so they are not evidence. Writes agreement.json next to the attributions.
"""
import json
import os
import sys
from collections import Counter

import attribution
import gamedata
import pipeline

MIN_KEY = 13


def team_owner(quest_table, expansion):
    """{key: stem} for keys found in exactly one main-scenario quest's team file."""
    owners = {}
    for quest in attribution.main_scenario(quest_table, expansion):
        for path in pipeline.quest_team_files(quest):
            for dialogue in pipeline.read_team(path):
                owners.setdefault(dialogue["key"], set()).add(quest["stem"])
    return {key: next(iter(stems)) for key, stems in owners.items() if len(stems) == 1 and len(key) >= MIN_KEY}


def main():
    call = pipeline.call_api if os.environ.get("ANTHROPIC_API_KEY") else pipeline.call_cli
    source, quest_table = pipeline.source_at("HEAD")
    names = {path.split("/")[-1]: path for path in source.files("cut_scene")}
    args = sys.argv[1:]
    model = args[1] if args[:1] == ["--model"] else None
    folder = f"{attribution.ATTRIBUTION_DIR}/eval/{model}" if model else attribution.ATTRIBUTION_DIR
    results = []
    for name in args[2:] if model else args:
        path = names[name]
        expansion = attribution.expansion_of(path)
        window = pipeline.windows_for(source, quest_table, expansion)[path]
        record = pipeline.attribute_file(call, source, quest_table, path, window, "lexical alignment of the expansion", model, folder)
        owner = team_owner(quest_table, expansion)
        rows = gamedata.read_rows(source, path)
        pairs = [(row, got, owner[row["key"]]) for row, got in zip(rows, attribution.by_row(record), strict=True) if row["key"] in owner]
        misses = [{"row": row["row"], "attributed": got, "team": want} for row, got, want in pairs if got != want]
        outside = sorted({want for _, _, want in pairs if want not in record["window"]})
        results.append({
            "file": path, "model": record["model"], "rows": len(rows), "window_quests": len(record["window"]), "window_method": record["window_method"],
            "votes": len(record["votes"]), "rows_votes_split_on": record["rows_votes_split_on"],
            "evidence_rows": len(pairs), "agree": len(pairs) - len(misses),
            "team_quests_outside_window": outside, "disagreements": misses,
        })
        single = [sum(got == want for (_, _, want), got in zip(pairs, [o for o, r in zip(attribution.expand(vote, len(rows)), rows) if r["key"] in owner])) for vote in record["votes"]]
        print(f"{name}: {len(pairs) - len(misses)}/{len(pairs)} evidence rows agree (single votes: {single}); window {len(record['window'])} quests; "
              f"misses by team quest {dict(Counter(m['team'] for m in misses))}")
    store = pipeline.OUT / folder / "agreement.json"
    stored = json.loads(store.read_text(encoding="utf-8")) if store.exists() else {}
    stored.update({result["file"]: result for result in results})
    agree, total = sum(r["agree"] for r in stored.values()), sum(r["evidence_rows"] for r in stored.values())
    pipeline.write_atomic(store, pipeline.dump(stored))
    print(f"all checked files: {agree}/{total} = {agree / total:.4f} over {len(stored)} files")


if __name__ == "__main__":
    main()
