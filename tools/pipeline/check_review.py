#!/usr/bin/env python3
"""Paid check (one Haiku call): does the review stage catch mistranslations seeded into a finished quest?"""
import json

import pipeline

QUEST = "KinGml101_05475"
SEEDED = {
    "ESTINIEN_000_107": "อิชการ์ดใช้เวลาแค่ปีเดียวก็หลุดพ้นจากมันได้",
    "ESTINIEN_000_114": "ยังไงข้าก็จะไม่ไปที่ไรซิ่งสโตนส์หรอก เจ้าไปเล่าเรื่องนั้นให้คนอื่นฟังเถอะ",
    "TATARU_000_206": "กรุณาออกไปจากดอว์นส์เรสไพต์เดี๋ยวนี้เลยค่ะ!",
}

record = pipeline.load_record(QUEST)
if not record:
    raise SystemExit(f"{QUEST} is not in out/review; translate it first")
source, quest_table = pipeline.source_at(record["selection"]["commit"])
unit = pipeline.build_unit(source, quest_table[QUEST], pipeline.stored_attributions(record["selection"]["cutscene_candidates"]))
work = pipeline.stored_work(record)
rows = [{**row, "text_haiku": work[row["key"]]["text_haiku"]} for row in unit["rows"] if not row["skip"] and row["file"].startswith("quest/")]
seeded = set()
for position, row in enumerate(rows):
    for suffix, wrong in SEEDED.items():
        if row["text_id"].endswith(suffix):
            row["text_haiku"] = wrong
            seeded.add(position)
assert len(seeded) == len(SEEDED), "seed ids not found"
reasons = pipeline.review(pipeline.call_cli, {"run_id": "seeded-review-check", "quest": QUEST}, rows)
for position, reason in sorted(reasons.items()):
    print(f"{'seeded' if position in seeded else 'UNSEEDED'} {rows[position]['text_id']}: {reason}")
print(f"caught {len(seeded & set(reasons))} of {len(seeded)} seeded lines; {len(set(reasons) - seeded)} unseeded lines flagged")
