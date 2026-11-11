# HANDOFF: branch `haiku`

เขียนเมื่อ 2026-11-11 สำหรับทำต่อจากเครื่องอื่น ไฟล์นี้อยู่เฉพาะใน branch `haiku` ห้าม merge เข้า main

## สถานะตอนนี้

- branch `haiku` แยกจาก main ที่ `a6d9887` commit `0e25b72` push แล้ว และผ่านการทดสอบในเกมแล้ว (A Winter's Dream และ As Goes Light, So Goes Darkness ผู้ใช้ยืนยันว่าแปลถูกต้องครบ)
- commit ถัดจากนั้นเพิ่มไฟล์นี้กับ `tools/pipeline/strip_team_overlap.py`
- งาน "clean up + README + Windborne" เสร็จแล้ว (commit ถัดมา) ยังไม่ push และยังไม่ได้ทดสอบ Windborne ในเกม วิธีใช้ tool ดูที่ `tools/pipeline/README.md`

## ใน branch มีอะไร

- **`tools/pipeline/`** เป็น pipeline แปลด้วย Haiku
  - `pipeline.py` เป็นจุดเริ่ม ดูวิธีใช้ด้วย `--help`
  - `gamedata.py` อ่าน CSV จาก datamining และจัดประเภทแถว
  - `attribution.py` ระบุว่าบรรทัด cutscene เป็นของเควสต์ไหน โดยให้ Haiku โหวต 3 รอบ
  - `key_ja.py` สร้าง key ภาษาญี่ปุ่น
  - `terms.json` เก็บชื่อเฉพาะ
  - `test_pipeline.py` เป็น test
  - `check_attribution.py` และ `check_review.py` เป็นการตรวจที่ต้องเสียเงินเรียก Haiku
- **`tools/pipeline/out/`** เก็บผลที่ไม่ใช่ไฟล์ของ plugin
  - `coverage/` พิสูจน์ความครบ
  - `review/` เทียบคำแปลของทีมกับของ Haiku
  - `attribution/` ผลการระบุเควสต์ของบรรทัด cutscene จะไม่ถาม Haiku ซ้ำ
  - `cost_log.jsonl` บันทึกค่าใช้จ่าย
  - `report.md` สรุปผล
- **`tools/pipeline/strip_team_overlap.py`** ลบบรรทัดของทีมที่ key ชนกับไฟล์ใน `haiku/` ต้องลบเพราะ plugin ใช้คำแปลจากไฟล์ที่โหลดก่อน หาไฟล์เป้าหมายจาก `repo_file` ของไฟล์ใน `haiku/` เอง
- **`haiku/`** มีไฟล์ของ plugin 3 ไฟล์ คือ `KinGml101_05475.json`, `HeaVnb108_02163.json` และ `KinGml104_05478.json` (Windborne)
- **บรรทัดของทีมที่ลบออกใน branch นี้** มีดังนี้ ลบทั้งใน `th/` และ `editor/public/th/`
  - `7.56/a-winters-dream.json` 30 บรรทัด
  - `7.56/cutscenes.json` 66 บรรทัด
  - `3.x/as-goes-light-so-goes-darkness.json` 144 บรรทัด
  - `7.56/windborne.json` 28 บรรทัด (ทั้งไฟล์) และ `7.56/cutscenes.json` อีก 41 บรรทัด
- **ไฟล์ของทีม** pipeline อ่านจาก `th/` ที่ branch `main` (`FFXIV_TEAM_REV`) เพราะ branch นี้ลบบรรทัดออก ถ้าอ่านจาก working tree ไฟล์ coverage จะเสีย

## ตั้งค่าเครื่องใหม่

```
git fetch origin && git switch haiku
python3 -m venv tools/pipeline/.venv
tools/pipeline/.venv/bin/pip install anthropic   # ใช้เฉพาะตอนเรียกผ่าน API และใน test ของ API stub
git clone --filter=blob:none https://github.com/xivapi/ffxiv-datamining tools/pipeline/dl/ffxiv-datamining
cd tools/pipeline && .venv/bin/python test_pipeline.py
```

- **datamining** ค่าเริ่มต้นอ่านจาก `tools/pipeline/dl/ffxiv-datamining` (อยู่ใน .gitignore) ถ้าวางไว้ที่อื่น ตั้ง `FFXIV_DATAMINING` ให้ชี้ไปที่นั่น
- **ตัวแปลภาษา** ค่าเริ่มต้นเรียก `claude -p` ด้วย Haiku จึงต้อง login Claude Code ไว้ก่อน ถ้าตั้ง `ANTHROPIC_API_KEY` ไว้ จะเรียกผ่าน API แทน ทางนี้ยังไม่เคยลองกับ API จริง
- **push** จากเครื่องเดิมผ่าน shell ของ Claude Code ไม่ได้ (Keychain error -25308) ต้อง push จาก Terminal ปกติ

## งานถัดไป: clean up + README + Windborne

prompt ที่ผู้ใช้อนุมัติแล้ว:

```
Goal
On branch `haiku`: clean up tools/pipeline/ (restructuring allowed: split/rename files, change the CLI,
if it makes the tool easier to use), write tools/pipeline/README.md in Thai, and prove the tool on quest
Windborne (KinGml104_05478) by producing haiku/KinGml104_05478.json.

Done when
- Following the README commands verbatim produces haiku/KinGml104_05478.json.
- Its coverage file shows every source row translated or skipped with a reason, and every team key
  (th/7.56/windborne.json + Windborne lines of th/7.56/cutscenes.json) in the output or listed with a reason.
- Tests pass. The two existing plugin files in haiku/ are byte-identical.
- Team rows colliding with Windborne keys are removed from th/ and editor/public/th/ (as done for the
  previous two quests), by a tool in tools/pipeline/ documented in the README; no collision remains.

Evidence to show
Commands run with real output, coverage totals, cost, test output, diff --stat of the commit.

What we know
Windborne cutscene lines are in VoiceMan_07505; earlier Haiku votes disagreed on the 103/104 boundary.

Constraints
Commit on `haiku`, then stop. No push, no change to main. Report back to the user in Thai.
```

- **คำสั่งแปลที่น่าจะใช้** คือ `pipeline.py --commit a67c23b --quest Windborne` ไฟล์ attribution ของ VoiceMan_07505 มีอยู่แล้ว จะไม่เสียค่าโหวตซ้ำ
- **`strip_team_overlap.py`** ต้องเพิ่ม `7.56/windborne.json` ใน `TEAM_FILES` หรือเปลี่ยนให้รับรายชื่อไฟล์จาก argument แล้วรันด้วย `--apply` ไฟล์ใน `th/` กับ `editor/public/th/` ที่ถูกแก้ต้องยังเหมือนกันทุก byte

## สิ่งที่ต้องรู้

- **plugin** ใช้คำแปลจากไฟล์แรกที่โหลดสำหรับแต่ละ key (TryAdd) และสร้าง key จาก `text_en` ด้วย
- **ประโยคทั่วไปที่ซ้ำข้ามเควสต์** มี 68 บรรทัดที่ไม่ได้ลบ เช่น "I...see?" และ "Of course!" บรรทัดเหล่านี้ขึ้นคำแปลของใครขึ้นกับลำดับที่ plugin โหลดไฟล์
- **การเลือกไฟล์ด้วย commit** ใช้ได้ตั้งแต่ patch 7.41 เท่านั้น เพราะ repo datamining จัดโครงสร้างใหม่ใน `d3eb86d` เนื้อหาเก่ากว่านั้นให้ใช้ `--quest` หรือ `--patch`
- **การระบุว่าบรรทัด cutscene เป็นของเควสต์ไหน** ตรงกับไฟล์ของทีม 88.7% (วัดจาก 4 ไฟล์) ข้อผิดพลาดที่เจอคือยกบทพูดทั้งช่วงไปให้เควสต์ที่อยู่ติดกัน
- **ตัวเลือกของผู้เล่นใน cutscene** pipeline ข้าม แต่ทีมแปลไว้ ยังรอผู้ใช้ตัดสินใจ
- **ชื่อของผู้เล่น** ในเกมยังขึ้นเป็น "Forename" จนกว่าจะแก้ issue #3 ของ plugin
- **ค่าใช้จ่าย** ค่าแปลราว $0.03–0.07 ต่อเควสต์ บวกค่าโหวต attribution ราว $0.02–0.03 ต่อไฟล์ cutscene ซึ่งจ่ายครั้งเดียว
