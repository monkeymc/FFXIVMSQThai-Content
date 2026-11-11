# Haiku translation pipeline

เครื่องมือแปลเควสต์ main scenario ของ FFXIV เป็นภาษาไทยด้วย Claude Haiku ทีละเควสต์ ผลลัพธ์คือไฟล์ `haiku/<quest_id>.json` ที่ plugin โหลดได้ และไฟล์ coverage ที่พิสูจน์ว่าไม่มีบรรทัดตกหล่น

ทุกคำสั่งในไฟล์นี้รันจาก root ของ repo

## ขั้นตอนโดยรวม

1. **เลือก** เควสต์และไฟล์ข้อความจาก [xivapi/ffxiv-datamining](https://github.com/xivapi/ffxiv-datamining) คือไฟล์เควสต์ (`quest/NNN/<Stem>.csv`) และไฟล์ cutscene ที่มีเสียง (`cut_scene/NNN/VoiceMan_NNNNN.csv`)
2. **ระบุเควสต์ของบรรทัด cutscene** ไฟล์ VoiceMan หนึ่งไฟล์มีบทพูดของหลายเควสต์ต่อกัน Haiku โหวต 3 รอบว่าแต่ละเควสต์เริ่มที่แถวไหน แล้วใช้เสียงข้างมาก ผลเก็บใน `out/attribution/` และจะไม่ถามซ้ำ
3. **แปล** แถวที่เป็นบทพูดของเควสต์ จากภาษาญี่ปุ่นเป็นหลัก โดยใช้ภาษาอังกฤษช่วยตีความ ชื่อเฉพาะใช้ภาษาอังกฤษทางการตาม `terms.json` ดู [TERMS.md](TERMS.md)
4. **ตรวจ** ด้วย lint (สรรพนามของตัวละคร ชื่อเฉพาะตาม `terms.json` ตัวอักษรที่ไม่ได้แปล ความยาว) และให้ Haiku อีกรอบหาจุดที่แปลผิดความหมาย
5. **พิสูจน์ความครบ** ทุกแถวของไฟล์ต้นทางต้องถูกแปลหรือถูกข้ามพร้อมเหตุผล และทุก key ในไฟล์ของทีมต้องอยู่ในผลลัพธ์หรือมีเหตุผลกำกับ ถ้าไม่ครบ pipeline จะหยุดและไม่เขียนไฟล์
6. **ลบบรรทัดของทีมที่ key ชนกัน** ด้วย `strip_team_overlap.py` เพราะ plugin ใช้คำแปลจากไฟล์แรกที่โหลดสำหรับแต่ละ key

## ตั้งค่าเครื่อง

```
python3 -m venv tools/pipeline/.venv
tools/pipeline/.venv/bin/pip install anthropic
git submodule update --init --filter=blob:none tools/pipeline/dl/ffxiv-datamining
tools/pipeline/.venv/bin/python tools/pipeline/test_pipeline.py
```

- datamining เป็น submodule ที่ pin ไว้ที่ commit หนึ่ง ถ้าจะอัปเดตเป็นเวอร์ชันล่าสุด ใช้ `git submodule update --remote tools/pipeline/dl/ffxiv-datamining` แล้ว commit ตัว submodule
- `anthropic` ใช้เฉพาะตอนเรียกผ่าน API และใน test ส่วน API stub ถ้าไม่ติดตั้ง test ส่วนนั้นจะถูกข้าม
- ค่าเริ่มต้นเรียก Haiku ผ่าน `claude -p` จึงต้อง login Claude Code ไว้ก่อน ถ้าตั้ง `ANTHROPIC_API_KEY` ไว้ จะเรียกผ่าน API แทน
- test ไม่เรียก model และไม่เสียเงิน ใช้เวลาราว 10 วินาที

## แปลเควสต์หนึ่งเควสต์

ตัวอย่างนี้แปลเควสต์ Windborne (`KinGml104_05478`) ของ patch 7.56

```
tools/pipeline/.venv/bin/python tools/pipeline/pipeline.py --commit a67c23b --quest Windborne
tools/pipeline/.venv/bin/python tools/pipeline/strip_team_overlap.py --apply
tools/pipeline/.venv/bin/python tools/pipeline/strip_team_overlap.py
```

- คำสั่งแรกเขียน `haiku/KinGml104_05478.json` และ `tools/pipeline/out/coverage/KinGml104_05478.json`
- คำสั่งที่สองลบบรรทัดของทีมที่ key ชนกับไฟล์ใน `haiku/` ทั้งใน `th/` และ `editor/public/th/`
- คำสั่งที่สามไม่แก้ไฟล์ใดๆ แค่แสดงว่ายังมีการชนเหลืออยู่หรือไม่ บรรทัดสุดท้ายต้องเป็น `colliding rows in target files: 0`
- เควสต์ที่แปลไว้แล้วจะไม่ถูกแปลซ้ำ ใส่ `--force` ถ้าต้องการแปลใหม่
- ใส่ `--list` เพื่อดูว่าจะเลือกเควสต์และไฟล์ cutscene อะไร โดยยังไม่แปล

## วิธีเลือกเควสต์

| คำสั่ง | ใช้เมื่อ | เลือกอะไร |
|---|---|---|
| `--commit REV` | เนื้อหาตั้งแต่ patch 7.41 | เควสต์ main scenario ที่ commit `REV` ของ datamining แก้ไข |
| `--commit REV --quest NAME` | เนื้อหาตั้งแต่ patch 7.41 | เฉพาะเควสต์ที่ระบุ จากกลุ่มข้างบน |
| `--quest NAME [--at REV]` | เนื้อหาเก่า | เควสต์ตามชื่อหรือ stem เช่น `"As Goes Light, So Goes Darkness"` หรือ `HeaVnb108_02163` |
| `--patch X.Y [--at REV]` | เนื้อหาเก่า | เควสต์ทั้งหมดที่มีบทพูดในโฟลเดอร์ `cut_scene/0XY` |
| ไม่ใส่อะไร | หลังแก้ lint หรือ `terms.json` | ไม่เรียก model สร้างไฟล์ของทุกเควสต์ที่เก็บไว้และรายงานใหม่ |

- ใส่ `--quest` ซ้ำได้หลายครั้ง
- `--commit` ใช้ได้ตั้งแต่ patch 7.41 เท่านั้น เพราะ repo datamining จัดโครงสร้างใหม่ใน commit `d3eb86d`
- `--at` คือ commit ของ datamining ที่จะอ่าน ค่าเริ่มต้นคือ `HEAD`

## ไฟล์ผลลัพธ์

| ไฟล์ | เนื้อหา |
|---|---|
| `haiku/<quest_id>.json` | ไฟล์ของ plugin มี `key`, `key_ja`, `text_en`, `text_ja` และคำแปล `text` |
| `tools/pipeline/out/coverage/<quest_id>.json` | ผลการพิสูจน์ความครบ ดูหัวข้อถัดไป |
| `tools/pipeline/out/review/<quest_id>.json` | บันทึกของ pipeline คำแปลของ Haiku เทียบกับของทีม และ flag จาก lint และ review |
| `tools/pipeline/out/attribution/VoiceMan_NNNNN.json` | ผลโหวตว่าแถวไหนของไฟล์ cutscene เป็นของเควสต์ไหน |
| `tools/pipeline/out/cost_log.jsonl` | ค่าใช้จ่ายของทุกครั้งที่เรียก model |
| `tools/pipeline/out/report.md` | สรุปค่าใช้จ่าย flag coverage และตัวอย่างคำแปล |
| `tools/pipeline/terms.json` | ชื่อเฉพาะภาษาญี่ปุ่นคู่กับชื่อภาษาอังกฤษทางการ สร้างด้วย `build_terms.py` ดู [TERMS.md](TERMS.md) |

ไฟล์ใน `out/review/` คือข้อมูลหลัก ไฟล์ใน `haiku/` และ `out/coverage/` สร้างใหม่จากไฟล์นี้และจากต้นทางทุกครั้งที่รัน

## อ่านไฟล์ coverage

- `totals` นับแถวทั้งหมด แถวที่แปล และแถวที่ข้ามแยกตามเหตุผล
- `sources` นับแบบเดียวกันแยกตามไฟล์ต้นทาง
- `team` เทียบกับไฟล์ของทีม `keys` คือจำนวน key ของทีม `in_output` คือจำนวนที่อยู่ในผลลัพธ์ ที่เหลืออยู่ใน `not_in_output_keys` พร้อมเหตุผล
- `rows_detail` ระบุทีละแถว

เหตุผลที่ข้ามแถว:

| เหตุผล | ความหมาย |
|---|---|
| `other_quest` | แถวของไฟล์ cutscene ที่เป็นของเควสต์อื่น |
| `unattributed` | แถวของไฟล์ cutscene ที่ไม่ได้เป็นของเควสต์ใดในรายการ |
| `duplicate_key` | key ซ้ำกับแถวก่อนหน้าในเควสต์เดียวกัน |
| `unused`, `not_for_translation`, `empty` | ข้อมูลเกมระบุว่าไม่ใช้ ไม่ต้องแปล หรือว่าง |
| `journal`, `todo`, `system`, `duty_text` | ไม่ใช่บทพูด |
| `choice` | ตัวเลือกของผู้เล่น ทีมแปลไว้ แต่ pipeline ยังข้าม |
| `not_displayed`, `no_key` | ไม่แสดงในเกม หรือไม่มีตัวอักษรภาษาอังกฤษให้สร้าง key |

เหตุผลที่ key ของทีมไม่อยู่ในผลลัพธ์:

| เหตุผล | ความหมาย |
|---|---|
| `source_row_skipped:<เหตุผล>` | มีแถวต้นทาง แต่ถูกข้ามด้วยเหตุผลนั้น |
| `text_differs` | ข้อความของทีมต่างจากต้นทางเล็กน้อย ระบุแถวที่ใกล้ที่สุด |
| `merged_rows` | ทีมรวมหลายแถวต่อกันเป็นบรรทัดเดียว |
| `found_elsewhere` | key อยู่ในไฟล์เควสต์หรือไฟล์ cutscene อื่น |
| `not_in_searched_files` | ไม่พบในไฟล์ที่ค้น อาจมาจาก sheet อื่น เช่นบทพูดของ NPC |

## ไฟล์ของทีมและการลบบรรทัดที่ชนกัน

- pipeline อ่านไฟล์ของทีมจาก `th/` ที่ branch `main` ไม่ใช่จาก working tree เพราะ branch นี้ลบบรรทัดของทีมออก ถ้าอ่านจาก working tree ไฟล์ coverage จะเสียไปหลังลบ เปลี่ยน branch ได้ด้วย `FFXIV_TEAM_REV`
- `strip_team_overlap.py` หาไฟล์เป้าหมายจากไฟล์ใน `haiku/` เอง คือไฟล์ของทีมของเควสต์นั้น (`repo_file`) และ `cutscenes.json` ในโฟลเดอร์เดียวกัน
- บรรทัดที่ชนกันนอกไฟล์เป้าหมายเป็นประโยคทั่วไปที่หลายเควสต์ใช้ เช่น "Of course!" เครื่องมือจะแสดงเป็น `keep` และไม่ลบ บรรทัดเหล่านี้ขึ้นคำแปลของใครขึ้นกับลำดับที่ plugin โหลดไฟล์
- รัน `--apply` ซ้ำได้ ครั้งที่สองจะไม่แก้อะไร
- ถ้าไฟล์เป้าหมายใน `th/` กับ `editor/public/th/` ไม่เหมือนกันทุก byte เครื่องมือจะหยุดพร้อมแจ้งชื่อไฟล์

## ตัวแปร environment

| ตัวแปร | ค่าเริ่มต้น | ใช้ทำอะไร |
|---|---|---|
| `FFXIV_DATAMINING` | `tools/pipeline/dl/ffxiv-datamining` | ที่อยู่ของ repo datamining |
| `FFXIV_TEAM_REV` | `main` | branch หรือ commit ที่ใช้อ่านไฟล์ของทีม |
| `FFXIV_PLUGIN_OUT` | `haiku` | โฟลเดอร์ที่เขียนไฟล์ของ plugin |
| `ANTHROPIC_API_KEY` | ไม่ตั้ง | ถ้าตั้ง จะเรียก Haiku ผ่าน API แทน `claude -p` |

## ค่าใช้จ่าย

- ค่าแปลราว $0.03–0.07 ต่อเควสต์
- ค่าโหวต attribution ราว $0.02–0.03 ต่อไฟล์ cutscene จ่ายครั้งเดียวต่อไฟล์
- `out/report.md` แสดงค่าใช้จ่ายจริงจาก `out/cost_log.jsonl`

## การตรวจที่ไม่เสียเงิน

- `check_msq_list.py` เทียบรายชื่อเควสต์ MSQ ในวิกิ (revision ที่ตรึงไว้) กับเควสต์ MSQ ใน `Quest.csv` และอ่านทุกไฟล์ที่ `gamedata.msq_paths` เลือก ออกด้วย exit code ไม่ใช่ 0 ถ้ามีเควสต์ที่ขาดหรือไฟล์ที่อ่านไม่ได้ ใส่ `--wikitext FILE` เพื่ออ่านสำเนาที่บันทึกไว้แทน

## การตรวจที่เสียเงิน

สองสคริปต์นี้เรียก Haiku จริง ใช้วัดคุณภาพ ไม่ต้องรันทุกครั้ง

- `check_attribution.py VoiceMan_NNNNN ...` วัดว่าการระบุเควสต์ของบรรทัด cutscene ตรงกับไฟล์ของทีมกี่เปอร์เซ็นต์ ใส่ `--model MODEL` เพื่อลองกับ model อื่น
- `check_review.py` ใส่คำแปลผิดลงในเควสต์ที่แปลแล้ว แล้วดูว่าขั้น review จับได้ไหม

## ข้อจำกัดที่รู้อยู่

- การระบุเควสต์ของบรรทัด cutscene ตรงกับไฟล์ของทีม 88.7% (วัดจาก 4 ไฟล์) ข้อผิดพลาดที่เจอคือยกบทพูดทั้งช่วงไปให้เควสต์ที่อยู่ติดกัน
- ตัวเลือกของผู้เล่นใน cutscene ยังไม่แปล
- ชื่อของผู้เล่นในเกมยังขึ้นเป็น "Forename" จนกว่าจะแก้ issue #3 ของ plugin
