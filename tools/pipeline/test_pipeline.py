#!/usr/bin/env python3
"""Offline checks: lints catch seeded defects, a line gets only the longest terms.json names it uses, every source row
and team key is accounted for (and a row that disappears stops the run), both selection modes pick the
right files, the strip tool removes only colliding target rows, and the API backend parses a Messages response from a local stub (run with .venv/bin/python)."""
import argparse
import contextlib
import copy
import io
import json
import os
import re
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import attribution
import gamedata
import pipeline
import strip_team_overlap
from key_ja import EDGE_CASES, key_ja


def checks(speaker, text, en="I will go to the ship with you at once.", ja="今すぐにでも、お前と一緒にあの船へ向かうとしよう。", terms=()):
    row = {"speaker": speaker, "text_en": en, "text_ja": ja}
    return {flag["check"] for flag in pipeline.lint(row, text, pipeline.Terms(dict(terms)))}


clean = "ข้าจะเข้าไปที่เรือกับเจ้าเดี๋ยวนี้ ข้างในมีข้าวอยู่"
assert checks("Estinien", clean) == set(), checks("Estinien", clean)
assert checks("Tataru", clean) == {"pronoun"}
assert checks("Tataru", "ฉันจะเข้าไปข้างในเรือกับคุณเดี๋ยวนี้เลยค่ะ") == set()
assert checks("Estinien", "ข้าจะไปที่เรือกับเจ้าเดี๋ยวนี้ครับ") == {"pronoun"}
assert checks("Alphinaud", "ผมจะให้คะแนนเรือลำนี้กับคุณเดี๋ยวนี้ครับ") == set()
assert checks("Alphinaud", "ผมจะไปที่เรือกับคุณเดี๋ยวนี้นะคะ") == {"pronoun"}
assert checks("Alphinaud", "ผมจะไปที่เรือกับเจ้าเดี๋ยวนี้ครับ") == {"pronoun"}
assert checks("Alphinaud", "ผมจะไปหาเจ้าของเรือกับคุณเดี๋ยวนี้ครับ") == set()
assert checks("Visna", clean, en="Forename, come to the ship with me at once.") == {"forename"}
assert checks("Visna", clean, ja="Forenameさん、今すぐ一緒にあの船へ向かおう。") == {"forename"}
assert checks("Visna", "ข้าจะไปที่เรือ Glaðr กับเจ้าเดี๋ยวนี้") == {"script"}
assert checks("Visna", "ข้าจะไปที่グラズ號กับเจ้าเดี๋ยวนี้") == {"script"}
assert checks("Visna", "Forename ไปที่เรือกับข้าเดี๋ยวนี้", en="Forename, come to the ship with me at once.") == set()
assert checks("Visna", "ไปเรือ") == {"length"}
assert checks("Visna", clean, en="Come with me, now.") == set(), "fits ja, so the terse en does not flag"
assert checks("Visna", "ข้าจะไปที่เรือกับเจ้าเดี๋ยวนี้เลย！？") == {"script"}
assert checks("Visna", "  ") == {"empty"}
naglfar = {"ナグルファル": "Naglfar"}
assert checks("Visna", "ข้าจะไปที่นากล์ฟาร์กับเจ้าเดี๋ยวนี้", ja="今すぐ一緒にナグルファルへ向かうとしよう。", terms=naglfar) == {"name"}
assert checks("Visna", "ข้าจะไปที่ Naglfar กับเจ้าเดี๋ยวนี้", ja="今すぐ一緒にナグルファルへ向かうとしよう。", terms=naglfar) == set()
assert checks("Visna", clean, terms=naglfar) == set()
assert checks("Visna", "ข้าจะไปที่ Naglfar กับเจ้าเดี๋ยวนี้", en="I will go to Naglfar with you at once.") == set(), "a name from en is not untranslated"
print("lints: ok")

KEY_JA_CASES = {
    "休息は取れまっしたか？\nみなさんも大分落ち着いたようなので、": "休息は取れまっしたかみなさんも大分落ち着いたようなので",
    "つまり、確保のチャンスでっす！\nPlayerさん、どうか": "つまり確保のチャンスでっすさんどうか",
    "つまり、確保のチャンスでっす！\nForenameさん、どうか": "つまり確保のチャンスでっすさんどうか",
    "トールダン7世や……あの氷女だって。": "トールダン7世やあの氷女だって",
    "浮島に生じた「」に設置してほしい。": "浮島に生じたに設置してほしい",
    **EDGE_CASES,
}
for text, expected in KEY_JA_CASES.items():
    assert key_ja(text) == expected, (text, key_ja(text), expected)
print("key_ja: ok")

terms = pipeline.Terms({"エーテル": "Aether", "エーテライト": "Aetheryte", "エーテライト・プラザ": "Aetheryte Plaza", "暁": "Scions"})
assert terms.used_by({"text_ja": "エーテライト・プラザで「暁」と会う。"}) == {"エーテライト・プラザ": "Aetheryte Plaza", "暁": "Scions"}
assert terms.used_by({"text_ja": "エーテルが満ちている。"}) == {"エーテル": "Aether"}
assert terms.used_by({"text_ja": "今すぐ一緒にあの船へ向かおう。"}) == {}
assert pipeline.Terms({}).used_by({"text_ja": "エーテル"}) == {}
block = pipeline.lines_block([{"speaker": "Aymeric", "shown_as": None, "file": "cut_scene/031/VoiceMan_03100", "text_ja": "「暁」の方々も", "text_en": "the Scions"},
                              {"speaker": "Aymeric", "shown_as": None, "file": "quest/021/x", "text_ja": "ありがとう", "text_en": "Thanks"}], terms=terms)
assert [json.loads(line).get("terms") for line in block.split(",\n")] == [{"暁": "Scions"}, None], block
print("terms: ok")

ROW_CASES = [
    ("quest/054/KinGml101_05475", "TEXT_KINGML101_05475_SEQ_00", "Tataru has a favor to ask of you.", "タタルは頼みがあるようだ。", "journal", None),
    ("quest/054/KinGml101_05475", "TEXT_KINGML101_05475_SEQ_06", "", "", "empty", None),
    ("quest/054/KinGml101_05475", "TEXT_KINGML101_05475_TODO_00", "Search for Estinien.", "エスティニアンを探す", "todo", None),
    ("quest/054/KinGml102_05476", "TEXT_KINGML102_05476_SYSTEM_000_072", "Somehow, you sense them.", "仲間の気配を感じる。", "system", None),
    ("quest/054/KinGml101_05475", "TEXT_KINGML101_05475_Q1_000_000", "What will you say?", "なんと言う？", "choice", None),
    ("quest/054/KinGml101_05475", "TEXT_KINGML101_05475_A1_000_002", "Where's your linkpearl?", "リンクパールは？", "choice", None),
    ("quest/021/HeaVnb108_02163", "TEXT_HEAVNB108_02163_QIB_TODO_001", "Defeat the heretics.", "異端者を倒せ", "duty_text", None),
    ("quest/021/HeaVnb108_02163", "TEXT_HEAVNB108_02163_TERRORIST_LEADER_BATTLETALK_000_010", "Kill them all!", "皆殺しだ！", None, "Terrorist_Leader"),
    ("quest/054/KinGml101_05475", "TEXT_KINGML101_05475_TATARU_000_005", "", "", "empty", "Tataru"),
    ("quest/054/KinGml101_05475", "TEXT_KINGML101_05475_ESTINIEN_000_100", "Player... If I didn't know better.", "Player……奇遇だな。", None, "Estinien"),
    ("quest/054/KinGml101_05475", "TEXT_KINGML101_05475_ESTINIEN_000_101", "...", "……", "no_key", "Estinien"),
    ("cut_scene/075/VoiceMan_07505", "TEXT_VOICEMAN_07505_000330_ESTINIEN", "No sooner did light encase you.", "お前が光に包まれた", None, "Estinien"),
    ("cut_scene/075/VoiceMan_07505", "TEXT_VOICEMAN_07505_Q1_000_001_NONE_VOICE", "What will you say?", "なんと言う？", "choice", None),
    ("cut_scene/075/VoiceMan_07505", "TEXT_VOICEMAN_07505_A7_000_001_NONE_VOICE", "Player Player, at your service!", "どうも、Player Playerです！", "choice", None),
    ("cut_scene/075/VoiceMan_07505", "TEXT_VOICEMAN_07505_001550_SYSTEM_NONE_VOICE", "Meanwhile...", "一方その頃……", "system", None),
    ("cut_scene/075/VoiceMan_07505", "TEXT_VOICEMAN_07505_001390_YSHTOLA", "", "（★未使用／削除予定★）", "unused", "Yshtola"),
    ("cut_scene/025/VoiceMan_02500", "TEXT_VOICEMAN_02500_700010_NABRIALES", "It appears I have underestimated you.", "（★未使用／削除予定★）", "unused", "Nabriales"),
    ("cut_scene/075/VoiceMan_07505", "TEXT_VOICEMAN_07505_010000_ALL", "（大勢の声出力用ラベル・翻訳不要）", "（大勢の声出力用ラベル・翻訳不要）", "not_for_translation", "All"),
    ("cut_scene/042/VoiceMan_04200", "TEXT_VOICEMAN_04200_000410_ALPHINAUD", "", "", "empty", "Alphinaud"),
    ("cut_scene/031/VoiceMan_03100", "TEXT_VOICEMAN_03100_000810_WARRIOROFDARKNESS", "(-???-)SHORT ATTACK GRUNT - SHOULD NOT DISPLAY", "(-？？？？-)ふんっ！", "not_displayed", "Warriorofdarkness"),
    ("cut_scene/075/VoiceMan_07505", "TEXT_VOICEMAN_07505_000290_ESTINIEN", "[LANDING EXERT]", "ふっ", None, "Estinien"),
    ("cut_scene/024/VoiceMan_02400", "TEXT_VOICEMAN_02400_K00010_NANAMOULNAMO", "I shall have no further need of you.", "そなたはもうよい", None, "Nanamoulnamo"),
]
for path, text_id, en, ja, skip, speaker in ROW_CASES:
    row = gamedata.make_row(path, 0, text_id, en, ja)
    assert (row["skip"], row["speaker"]) == (skip, speaker), (text_id, row["skip"], row["speaker"])
shown = gamedata.make_row("cut_scene/075/VoiceMan_07505", 25, "TEXT_VOICEMAN_07505_000162_CALYX", "(-Calyx-)Our destination is the Fourth.", "(-カリュクス-)行き先は「第四世界」……。")
assert (shown["shown_as"], shown["text_en"], shown["key"], shown["key_ja"]) == ("Calyx", "Our destination is the Fourth.", "ourdestinationisthefourth", "行き先は第四世界"), shown
full = gamedata.make_row("cut_scene/075/VoiceMan_07505", 138, "TEXT_VOICEMAN_07505_000999_VISNA", "Player Player, at your service!", "どうも、Player Playerです！")
assert (full["text_en"], full["key"]) == ("Forename Surname, at your service!", "forenamesurnameatyourservice"), full
print("row kinds: ok")

WINDOW = ["A", "B", "C"]
assert attribution.parse_starts({"starts": [{"quest": "A", "row": 0}, {"quest": "C", "row": 4}]}, WINDOW, 6) == [{"quest": "A", "row": 0}, {"quest": "C", "row": 4}]
record = {"rows": 6, "starts": [{"quest": None, "row": 0}, {"quest": "B", "row": 2}, {"quest": None, "row": 5}]}
assert attribution.parse_starts({"starts": record["starts"]}, WINDOW, 6) == record["starts"]
assert attribution.by_row(record) == [None, None, "B", "B", "B", None]
for bad in (
    [{"quest": "B", "row": 0}, {"quest": "A", "row": 3}],
    [{"quest": "A", "row": 1}],
    [{"quest": "A", "row": 0}, {"quest": "B", "row": 6}],
    [{"quest": "A", "row": 0}, {"quest": "B", "row": 0}],
    [{"quest": "A", "row": 0}, {"quest": "A", "row": 3}],
    [{"quest": "Z", "row": 0}],
    [],
):
    try:
        attribution.parse_starts({"starts": bad}, WINDOW, 6)
        raise AssertionError(f"accepted {bad}")
    except ValueError:
        pass
votes = [[{"quest": "A", "row": 0}, {"quest": "B", "row": 3}], [{"quest": "A", "row": 0}, {"quest": "B", "row": 2}], [{"quest": "A", "row": 0}, {"quest": "C", "row": 3}, {"quest": None, "row": 5}]]
assert attribution.majority(votes, 6) == ([{"quest": "A", "row": 0}, {"quest": "B", "row": 3}], 4), attribution.majority(votes, 6)
assert attribution.majority(votes[:1], 6) == (votes[0], 0)
assert attribution.monotone_segments([[5, 0, 0], [0, 1, 0], [9, 0, 2], [0, 0, 3]], 3) == [0, 0, 0, 2], "the best row-by-row pick 0,1,0,2 goes back; states never do"
print("attribution reply and segmentation: ok")

COMMIT_756 = "a67c23b"
VOICEMAN = "cut_scene/075/VoiceMan_07505"
STARTS = [("KinGml101_05475", 0), ("KinGml102_05476", 74), ("KinGml103_05477", 160), ("KinGml104_05478", 240), (None, 276)]
replies, attributed = [], []


def fake_backend(system, user, effort, model):
    ids = re.findall(r'\{"id": "(\d+)"', user)
    if system == attribution.BOUNDARY_SYSTEM:
        file = re.search(r"Rows of (\S+) ", user).group(1)
        attributed.append((file, effort, model))
        starts = STARTS if file == VOICEMAN else [(None, 0)]
        reply = json.dumps({"starts": [{"quest": quest, "row": row} for quest, row in starts]})
    elif system == pipeline.REVIEW_SYSTEM:
        reply = '{"2": "seeded reason"}'
    elif not replies:
        reply = "not json"
    elif len(replies) == 1:
        reply = json.dumps({"lines": {i: "ทดสอบ" for i in ids[1:]}})
    else:
        reply = "```json\n" + json.dumps({"lines": {i: "ข้าจะไปที่นากล์ฟาร์！" for i in ids}}) + "\n```"
    if system != attribution.BOUNDARY_SYSTEM:
        replies.append(reply)
    usage = dict.fromkeys(["input_tokens", "output_tokens", "cache_write_tokens", "cache_read_tokens", "thinking_tokens"], 1)
    return reply, {"backend": "fake", "model": "fake", **usage, "stop_reason": "end_turn", "cost_usd": 0.5}


def request(**given):
    return argparse.Namespace(**{"commit": None, "quest": [], "patch": None, "at": "HEAD", **given})


def stops(action, message):
    try:
        action()
    except SystemExit as stop:
        assert message in str(stop), stop
        return
    raise AssertionError(f"did not stop with {message!r}")


with tempfile.TemporaryDirectory() as tmp:
    pipeline.OUT = Path(tmp) / "out"
    pipeline.COST_LOG, pipeline.TERMS = pipeline.OUT / "cost_log.jsonl", Path(tmp) / "terms.json"
    pipeline.OUT.mkdir()
    pipeline.PLUGIN_OUT = Path(tmp) / "plugin"
    pipeline.CHUNK = 1000
    stem = "KinGml102_05476"

    selected = pipeline.select(request(commit=COMMIT_756), fake_backend)
    assert [s for s, _ in selected] == ["KinGml101_05475", "KinGml102_05476", "KinGml103_05477", "KinGml104_05478"], selected
    assert all(sel["mode"] == "commit" and sel["cutscene_candidates"] == [VOICEMAN] and len(sel["commit"]) == 40 for _, sel in selected)
    assert attributed == [(VOICEMAN, "high", attribution.ATTRIBUTION_MODEL)] * attribution.ATTRIBUTION_VOTES, attributed
    by_name = pipeline.select(request(commit=COMMIT_756, quest=["A Winter's Dream"]), fake_backend)
    assert [s for s, _ in by_name] == ["KinGml101_05475"] and len(attributed) == attribution.ATTRIBUTION_VOTES, "a stored attribution is not asked for again"
    stops(lambda: pipeline.select(request(commit=COMMIT_756, quest=["JobXbm001_05490"]), fake_backend), "not a main-scenario quest changed by")
    old = pipeline.select(request(quest=["As Goes Light, So Goes Darkness"]), fake_backend)
    assert [s for s, _ in old] == ["HeaVnb108_02163"] and old[0][1]["mode"] == "quest"
    assert "cut_scene/031/VoiceMan_03100" in old[0][1]["cutscene_candidates"], old
    assert all(path.startswith("cut_scene/03") for path in old[0][1]["cutscene_candidates"])
    print(f"selection: ok, commit mode picks 4 quests and {VOICEMAN}; quest mode examines {old[0][1]['cutscene_candidates']}")

    selection = dict(selected)[stem]
    stops(lambda: pipeline.run_quest(stem, fake_backend, False, selection), "invalid output twice")
    for folder in (pipeline.PLUGIN_OUT, pipeline.OUT / pipeline.REVIEW_DIR, pipeline.OUT / pipeline.COVERAGE_DIR):
        assert not list(folder.glob("KinGml*.json")), "a failed quest must not leave an output"
    pipeline.run_quest(stem, fake_backend, False, selection)
    plugin_path, review_path, coverage_path = (folder / f"{stem}.json" for folder in (pipeline.PLUGIN_OUT, pipeline.OUT / pipeline.REVIEW_DIR, pipeline.OUT / pipeline.COVERAGE_DIR))
    plugin, record, coverage = (json.loads(path.read_text(encoding="utf-8")) for path in (plugin_path, review_path, coverage_path))
    assert list(plugin) == ["quest_id", "source", "repo_file", "dialogues"], list(plugin)
    assert plugin["quest_id"] == stem and plugin["repo_file"] == "7.56/a-rush-of-cold-wind.json"
    assert plugin["source"] == {"quest": stem, "cutscene_files": [VOICEMAN], "datamining_commit": selection["commit"]}
    assert all(list(d) == ["key", "key_ja", "text_id", "speaker", "text_en", "text_ja", "text"] for d in plugin["dialogues"])
    assert all(d["text"] == "ข้าจะไปที่นากล์ฟาร์!" and d["key"] for d in plugin["dialogues"]), "full-width punctuation must be normalized"
    quest_lines = [d for d in plugin["dialogues"] if d["text_id"].startswith("TEXT_KINGML102_05476_")]
    cutscene_lines = [d for d in plugin["dialogues"] if d["text_id"].startswith("TEXT_VOICEMAN_07505_")]
    assert len(quest_lines) == 19 and len(quest_lines) + len(cutscene_lines) == len(plugin["dialogues"]) and cutscene_lines
    assert len({d["key"] for d in plugin["dialogues"]}) == len(plugin["dialogues"]), "keys must be unique in one file"
    repo = pipeline.read_team(plugin["repo_file"])
    assert {d["key"]: d["text_en"] for d in quest_lines} == {d["key"]: d["text_en"] for d in repo}, "key and text_en must equal the repo's"
    shared = {d["key"]: d["text_en"] for d in pipeline.read_team(f"7.56/{pipeline.SHARED_TEAM_FILE}")}
    assert all(shared.get(d["key"]) == d["text_en"] for d in cutscene_lines), "cutscene key and text_en must equal the team's cutscenes.json"
    assert [r["key"] for r in record["rows"]] == [d["key"] for d in plugin["dialogues"]]
    assert all(r["text_haiku"] == d["text"] and r["text_human"] for r, d in zip(record["rows"], plugin["dialogues"]))
    flags = [[f["check"] for f in r["flags"]] for r in record["rows"]]
    assert flags[1].count("review") == 1 and "review" not in flags[0]
    assert "pronoun" in flags[0], "Alphinaud saying ข้า must be linted"

    source, _ = pipeline.source_at(selection["commit"])
    detail = coverage["rows_detail"]
    for entry in coverage["sources"]:
        csv_rows = len(source.table(f"en/{entry['file']}"))
        assert sorted(r["row"] for r in detail if r["file"] == entry["file"]) == list(range(csv_rows)), entry["file"]
        assert entry["rows"] == csv_rows == entry["translated"] + sum(entry["skipped"].values())
    assert [entry["file"] for entry in coverage["sources"]] == ["quest/054/KinGml102_05476", VOICEMAN]
    assert all(r["reason"] for r in detail if r["disposition"] == "skipped") and all(r["reason"] is None for r in detail if r["disposition"] == "translated")
    assert coverage["totals"]["translated"] == len(plugin["dialogues"]) and coverage["totals"]["rows"] == len(detail)
    owners = {r["row"]: r for r in detail if r["file"] == VOICEMAN}
    assert owners[10]["reason"] == "other_quest" and owners[10]["detail"] == "KinGml101_05475"
    assert owners[80]["disposition"] == "translated" and owners[300]["reason"] == "unused"
    assert owners[48]["reason"] == "not_for_translation" and coverage["totals"]["skipped"]["other_quest"] > 100
    team = coverage["team"]
    assert team["files"] == ["7.56/a-rush-of-cold-wind.json", "7.56/cutscenes.json"]
    assert team["keys"] == team["in_output"] + len(team["not_in_output_keys"]) and team["in_output"] >= 19
    assert all(entry["reason"].startswith("source_row_skipped:") for entry in team["not_in_output_keys"]), team["not_in_output"]
    for path in Path(tmp).rglob("*.json"):
        assert ("dialogues" in json.loads(path.read_text(encoding="utf-8"))) == (path.parent == pipeline.PLUGIN_OUT and path.name.startswith("KinGml")), path
    print(f"coverage: ok, {coverage['totals']}, team keys {team['in_output']}/{team['keys']} in output, rest {team['not_in_output']}")

    dialogues = plugin["dialogues"]
    pipeline.check_coverage(source, coverage, dialogues)
    seeded = {}
    seeded["a source row is dropped"] = copy.deepcopy(coverage)
    del seeded["a source row is dropped"]["rows_detail"][3]
    seeded["a skipped row has no reason"] = copy.deepcopy(coverage)
    next(r for r in seeded["a skipped row has no reason"]["rows_detail"] if r["disposition"] == "skipped")["reason"] = None
    seeded["a team key is dropped"] = copy.deepcopy(coverage)
    seeded["a team key is dropped"]["team"]["keys"] += 1
    for name, broken in seeded.items():
        stops(lambda: pipeline.check_coverage(source, broken, dialogues), "coverage check failed")
    stops(lambda: pipeline.check_coverage(source, coverage, dialogues[:-1]), "coverage check failed")
    stops(lambda: pipeline.check_coverage(source, coverage, [{**dialogues[0], "text": " "}, *dialogues[1:]]), "coverage check failed")
    read_rows = gamedata.read_rows
    gamedata.read_rows = lambda src, path: read_rows(src, path)[:-1] if path == "quest/054/KinGml102_05476" else read_rows(src, path)
    stops(pipeline.refresh, "coverage check failed")
    gamedata.read_rows = read_rows
    print(f"coverage check: ok, stops on {len(seeded) + 3} seeded defects, including a row lost while reading the CSV")

    before = plugin_path.read_bytes(), review_path.read_bytes(), coverage_path.read_bytes()
    plugin_path.unlink()
    coverage_path.unlink()
    pipeline.refresh()
    assert (plugin_path.read_bytes(), review_path.read_bytes(), coverage_path.read_bytes()) == before, "refresh must rebuild the projections and be repeatable"
    log = [json.loads(line) for line in pipeline.COST_LOG.read_text(encoding="utf-8").splitlines()]
    assert [(e["stage"], e["attempt"], e["error"] is None, e["effort"]) for e in log] == [
        *[("attribute", 1, True, "high")] * len(attributed), ("translate", 1, False, "medium"), ("translate", 2, False, "medium"),
        ("translate", 1, True, "medium"), ("review", 1, True, "medium")], log
    calls = len(replies)
    pipeline.run_quest(stem, fake_backend, False, selection)
    assert len(replies) == calls, "existing output must be skipped without calling the model"
    stored = json.loads(review_path.read_text(encoding="utf-8"))
    stored["rows"] = stored["rows"][:-3]
    review_path.write_text(pipeline.dump(stored), encoding="utf-8")
    stops(pipeline.refresh, "has no stored translation")
    pipeline.run_quest(stem, fake_backend, False, selection)
    assert len(replies) == calls + 2 and (plugin_path.read_bytes(), coverage_path.read_bytes()) == before[::2], "only the 3 missing lines are translated again"
    pipeline.CHUNK = 40
    chunks = -(-len(dialogues) // 40)
    pipeline.run_quest(stem, fake_backend, True, selection)
    assert len(replies) == calls + 2 + 2 * chunks, "--force must redo translate and review, one pair of calls per chunk"
    quests = pipeline.refresh()
    pipeline.write_vectors(quests)
    pipeline.write_report(quests)
    report = (pipeline.OUT / "report.md").read_text(encoding="utf-8")
    quest_row = f"| fake | {2 * chunks} | {2 * chunks} | {2 * chunks} | {2 * chunks} | {2 * chunks} | {2 * chunks} | {chunks}.000000 | n/a |"
    total_calls = len(attributed) + 4 + 2 + 2 * chunks
    assert quest_row in report and f"{total_calls} calls, ${total_calls / 2:.6f}" in report, report[:2500]
    assert f"VoiceMan_07505 attribution (351 rows, 3 votes) | fake | {attribution.ATTRIBUTION_VOTES} |" in report and "| other_quest" not in report.split("## Coverage")[0]
    assert f"| {stem} | 7.56/a-rush-of-cold-wind.json, 7.56/cutscenes.json | {team['keys']} | {team['in_output']} |" in report, report
print("pipeline with fake backend: ok")

with tempfile.TemporaryDirectory() as tmp:
    pipeline.ROOT, pipeline.PLUGIN_OUT = Path(tmp), Path(tmp) / "haiku"
    line = lambda en, text="ข้อความ": {"key": gamedata.make_key(en), "text_en": en, "text": text}
    team = {
        "7.56/windborne.json": [line("Raise output to the wind engine!"), line("Only the team has this line.")],
        "7.56/cutscenes.json": [line("(-???-)Of course!"), line("Choose ship/isle."), line("Not in haiku.")],
        "7.56/other-quest.json": [line("Of course!")],
        "7.56/untranslated.json": [line("Raise output to the wind engine!", text="")],
    }
    for mirror in strip_team_overlap.MIRRORS:
        for name, dialogues in team.items():
            (Path(tmp) / mirror / name).parent.mkdir(parents=True, exist_ok=True)
            (Path(tmp) / mirror / name).write_text(json.dumps({"quest_id": None, "dialogues": dialogues}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    pipeline.PLUGIN_OUT.mkdir()
    plugin = {"quest_id": "KinGml104_05478", "repo_file": "7.56/windborne.json", "dialogues": [line(en, "ไทย") for en in ("Raise output to the wind engine!", "Of course!", "Choose isle.")]}
    (pipeline.PLUGIN_OUT / "KinGml104_05478.json").write_text(json.dumps(plugin), encoding="utf-8")
    sys.argv = ["strip_team_overlap.py"]
    with contextlib.redirect_stdout(io.StringIO()):
        strip_team_overlap.main()
    assert all(json.loads((Path(tmp) / "th" / name).read_text(encoding="utf-8"))["dialogues"] == rows for name, rows in team.items()), "without --apply nothing changes"
    sys.argv = ["strip_team_overlap.py", "--apply"]
    with contextlib.redirect_stdout(io.StringIO()):
        strip_team_overlap.main()
    after = {name: [d["text_en"] for d in json.loads((Path(tmp) / "th" / name).read_text(encoding="utf-8"))["dialogues"]] for name in team}
    assert after == {
        "7.56/windborne.json": ["Only the team has this line."], "7.56/cutscenes.json": ["Not in haiku."],
        "7.56/other-quest.json": ["Of course!"], "7.56/untranslated.json": ["Raise output to the wind engine!"],
    }, after
    snapshot = {f: f.read_bytes() for f in Path(tmp).rglob("*.json")}
    with contextlib.redirect_stdout(io.StringIO()) as printed:
        strip_team_overlap.main()
    assert {f: f.read_bytes() for f in Path(tmp).rglob("*.json")} == snapshot, "a second --apply must change nothing"
    assert "colliding rows in target files: 0 (removed)" in printed.getvalue(), printed.getvalue()
    assert all((Path(tmp) / "th" / name).read_bytes() == (Path(tmp) / "editor/public/th" / name).read_bytes() for name in team)
print("strip team overlap: ok")

try:
    import anthropic  # noqa: F401
except ImportError:
    raise SystemExit("api stub: skipped, anthropic SDK not installed in this interpreter")

seen = {}


class Stub(BaseHTTPRequestHandler):
    def do_POST(self):
        seen["path"] = self.path
        seen["body"] = json.loads(self.rfile.read(int(self.headers["content-length"])))
        reply = json.dumps({
            "id": "msg_stub", "type": "message", "role": "assistant", "model": "claude-haiku-5-5",
            "content": [{"type": "thinking", "thinking": "", "signature": "s"}, {"type": "text", "text": '{"lines": {"1": "ทดสอบ"}}'}],
            "stop_reason": "end_turn", "stop_sequence": None,
            "usage": {"input_tokens": 1000, "output_tokens": 2000, "cache_creation_input_tokens": 400, "cache_read_input_tokens": 300},
        }).encode()
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(reply)))
        self.end_headers()
        self.wfile.write(reply)

    def log_message(self, *args):
        pass


server = HTTPServer(("127.0.0.1", 0), Stub)
threading.Thread(target=server.serve_forever, daemon=True).start()
os.environ.update(ANTHROPIC_API_KEY="stub", ANTHROPIC_BASE_URL=f"http://127.0.0.1:{server.server_port}")
text, usage = pipeline.call_api("SYSTEM", "USER", "medium", pipeline.MODEL)
server.shutdown()
assert text == '{"lines": {"1": "ทดสอบ"}}', text
assert seen["path"] == "/v1/messages" and seen["body"]["model"] == "claude-haiku-5-5", seen
assert seen["body"]["output_config"] == {"effort": "medium"} and seen["body"]["system"][0]["cache_control"] == {"type": "ephemeral"}, seen["body"]
expected = (1000 * 0.10 + 2000 * 0.50 + 400 * 0.125 + 300 * 0.01) / 1e6
assert abs(usage["cost_usd"] - expected) < 1e-12, (usage, expected)
assert (usage["input_tokens"], usage["output_tokens"], usage["cache_write_tokens"], usage["cache_read_tokens"]) == (1000, 2000, 400, 300)
print(f"api stub: ok, request keys {sorted(seen['body'])}, cost ${usage['cost_usd']:.6f}")
