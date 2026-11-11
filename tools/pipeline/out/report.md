# Haiku translation pipeline report

Model `claude-haiku-5-5`, effort `medium`. Every number below is computed from `out/cost_log.jsonl`, `out/review/<quest_id>.json`, `out/coverage/<quest_id>.json` and the sources. `out/<quest_id>.json` is the plugin-facing file.

## Cost

Per quest: the calls of the runs that produced the current output (translate + review, retries included). Attributing a cutscene file to quests takes one call per vote, listed under its file name.

| quest | backend | calls | input tok | cache-write tok | cache-read tok | output tok | of which thinking | cost USD | est. API-path USD |
|---|---|---|---|---|---|---|---|---|---|
| HeaVnb108_02163 (164 lines) | cli | 6 | 12 | 55227 | 3771 | 92143 | 77030 | 0.057156 | 0.051606 |
| KinGml101_05475 (96 lines) | cli | 4 | 8 | 30465 | 2514 | 46452 | 38968 | 0.029345 | 0.026281 |
| KinGml104_05478 (69 lines) | cli | 4 | 8 | 21572 | 2514 | 31623 | 26500 | 0.020152 | 0.017977 |
| VoiceMan_03008 attribution (33 rows, 3 votes) | cli | 3 | 6 | 26668 | 53336 | 29588 | 29464 | 0.020662 | 0.022612 |
| VoiceMan_03100 attribution (203 rows, 3 votes) | cli | 3 | 6 | 43833 | 89373 | 48487 | 48038 | 0.033904 | 0.037382 |
| VoiceMan_03300 attribution (202 rows, 3 votes) | cli | 3 | 6 | 42624 | 86955 | 33441 | 32954 | 0.026115 | 0.029496 |
| VoiceMan_07400 attribution (508 rows, 3 votes) | cli | 3 | 8 | 61228 | 185960 | 115310 | 114595 | 0.071761 | 0.082192 |
| VoiceMan_07505 attribution (351 rows, 3 votes) | cli | 3 | 6 | 31626 | 17164 | 25792 | 25473 | 0.019393 | 0.017593 |
| **total, current outputs** | cli | 29 | 60 | 313243 | 441587 | 422836 | 393022 | 0.278488 | 0.285138 |

All logged calls, including probes, rejected attempts and superseded runs: 77 calls, $1.245953.

### Every logged run

Same quest, same prompt: the spread between rows is run-to-run variance, mostly thinking tokens.

| quest | run | stages | effort | output tok | of which thinking | cost USD | current output |
|---|---|---|---|---|---|---|---|
| a-winters-dream | 20261110T191650 | translate+review | medium | 15891 | 12229 | 0.010262 |  |
| a-winters-dream | 20261110T191925 | translate+review | medium | 13733 | 10146 | 0.009180 |  |
| a-rush-of-cold-wind | 20261110T192023 | translate+review | medium | 9458 | 7388 | 0.006259 |  |
| the-world-locked-in-ice | 20261110T192106 | translate+review | medium | 23448 | 18902 | 0.014713 |  |
| a-rush-of-cold-wind | seeded-review-check | review+review | medium | 6059 | 5480 | 0.005319 |  |
| a-rush-of-cold-wind | 20261110T192549-d39180 | translate+review | medium | 6881 | 4754 | 0.004991 |  |
| a-rush-of-cold-wind | 20261110T192635-6da495 | translate+review | low | 9070 | 6981 | 0.006082 |  |
| VoiceMan_07505 | 20261111T020413-d43b08 | attribute | high | 7790 | 7679 | 0.007015 | yes |
| KinGml101_05475 | 20261111T020448-48626d | translate+review+translate+review | medium | 28257 | 21736 | 0.018712 |  |
| VoiceMan_03008 | 20261111T020703-7171b2 | attribute | high | 6603 | 6557 | 0.008347 |  |
| VoiceMan_03100 | 20261111T020734-357204 | attribute | high | 9979 | 9802 | 0.013709 |  |
| HeaVnb108_02163 | 20261111T020820-647317 | translate+review+translate+review+translate+review | medium | 95321 | 78915 | 0.058001 |  |
| VoiceMan_03008 | 20261111T021545-544bbd | attribute | high | 12025 | 11969 | 0.010377 |  |
| VoiceMan_03100 | 20261111T021637-c9caf9 | attribute | high | 14325 | 14196 | 0.014604 |  |
| HeaVnb108_02163 | 20261111T021742-5bc75b | translate+review | medium | 16824 | 14439 | 0.010365 |  |
| VoiceMan_03008 | 20261111T022022-472cf7 | attribute | high | 1742 | 1696 | 0.104620 |  |
| VoiceMan_03300 | 20261111T022022-f62299 | attribute | high | 7654 | 7487 | 0.011185 |  |
| VoiceMan_03100 | 20261111T022038-082c1c | attribute | high | 3778 | 3649 | 0.186520 |  |
| VoiceMan_03300 | 20261111T022110-0a8663 | attribute | high | 1614 | 1461 | 0.163220 |  |
| VoiceMan_07400 | 20261111T022125-a59a1d | attribute | high | 5986 | 5770 | 0.263340 |  |
| VoiceMan_07400 | 20261111T022058-a9a537 | attribute | high | 21652 | 21399 | 0.021004 |  |
| VoiceMan_03008 | 20261111T022837-a22330 | attribute | high | 7297 | 7265 | 0.008982 | yes |
| VoiceMan_03100 | 20261111T022912-0a1658 | attribute | high | 15088 | 14959 | 0.016316 | yes |
| VoiceMan_03300 | 20261111T023037-7538d9 | attribute | high | 9699 | 9546 | 0.013380 | yes |
| VoiceMan_07400 | 20261111T023127-89c219 | attribute | high | 51149 | 50919 | 0.037826 | yes |
| VoiceMan_03008 | 20261111T023700-49cfa4 | attribute+attribute | high | 22291 | 22199 | 0.011679 | yes |
| VoiceMan_03100 | 20261111T023842-0b373c | attribute+attribute | high | 33399 | 33079 | 0.017588 | yes |
| VoiceMan_03300 | 20261111T024109-4e08e7 | attribute+attribute | high | 23742 | 23408 | 0.012735 | yes |
| VoiceMan_07400 | 20261111T024250-516591 | attribute+attribute | high | 64161 | 63676 | 0.033935 | yes |
| VoiceMan_07505 | 20261111T024834-0904a5 | attribute+attribute | high | 18002 | 17794 | 0.012378 | yes |
| KinGml104_05478 | 20261111T123252-d0889d | translate+review+translate+review | medium | 35328 | 28528 | 0.022276 |  |
| probe-terms | 20261111T184453-0ea82f | translate | medium | 784 | 688 | 0.000763 |  |
| probe-terms | 20261111T184518-c60ef9 | translate | medium | 1132 | 1030 | 0.000948 |  |
| probe-terms | 20261111T184526-c48fa0 | translate | medium | 816 | 716 | 0.000427 |  |
| probe-terms | 20261111T184532-5692db | translate | medium | 1078 | 977 | 0.000558 |  |
| probe-terms | 20261111T184549-ac55a0 | translate | medium | 563 | 472 | 0.000668 |  |
| probe-terms | 20261111T184556-1f4fb3 | translate | medium | 824 | 723 | 0.000431 |  |
| probe-terms | 20261111T184601-23a8f0 | translate | medium | 880 | 776 | 0.000460 |  |
| HeaVnb108_02163 | 20261111T185104-153130 | translate+review+translate+review+translate+review | medium | 92143 | 77030 | 0.057156 | yes |
| KinGml101_05475 | 20261111T190826-e2cae7 | translate+review+translate+review | medium | 46452 | 38968 | 0.029345 | yes |
| KinGml104_05478 | 20261111T191136-c2a659 | translate+review+translate+review | medium | 31623 | 26500 | 0.020152 | yes |

CLI overhead: a probe with a 3-word prompt was billed 610 input tokens, so about that many tokens per call are the CLI harness, and the CLI writes the whole prompt to the 1-hour cache (2x the input price). The API-path estimate removes the harness tokens and prices all input at $0.10/MTok and the same output tokens at $0.50/MTok, without caching. It is an estimate; the API path was not run.

## Flags

Lines with at least one flag per check. `human` runs the same deterministic lints on the human reference as a noise baseline (the `name` lint is skipped there because the team writes names in Thai, not the English of terms.json).

| quest | lines | any flag | empty | forename | name | pronoun | script | length | review | human: any lint |
|---|---|---|---|---|---|---|---|---|---|---|
| HeaVnb108_02163 | 164 | 35 | 0 | 3 | 2 | 0 | 18 | 10 | 5 | 4 |
| KinGml101_05475 | 96 | 10 | 0 | 0 | 0 | 0 | 8 | 2 | 2 | 0 |
| KinGml104_05478 | 69 | 5 | 0 | 0 | 0 | 0 | 5 | 0 | 0 | 0 |

## Coverage

From `out/coverage/<quest_id>.json`. Every row of every source file is translated or skipped with a reason; every key of the team's files is in the output or listed with a reason.

| quest | commit | source file | rows | translated | skipped by reason |
|---|---|---|---|---|---|
| HeaVnb108_02163 | `52a72b38aa2f` | quest/021/HeaVnb108_02163 | 165 | 89 | empty 38, unused 20, journal 6, todo 4, choice 4, duty_text 4 |
| HeaVnb108_02163 | `52a72b38aa2f` | cut_scene/031/VoiceMan_03100 | 203 | 75 | other_quest 124, choice 3, not_displayed 1 |
| KinGml101_05475 | `a67c23b00fe8` | quest/054/KinGml101_05475 | 98 | 30 | empty 38, unused 17, journal 6, todo 4, choice 3 |
| KinGml101_05475 | `a67c23b00fe8` | cut_scene/075/VoiceMan_07505 | 351 | 66 | other_quest 203, unused 74, choice 7, not_for_translation 1 |
| KinGml104_05478 | `a67c23b00fe8` | quest/054/KinGml104_05478 | 83 | 28 | empty 42, unused 6, journal 4, todo 2, system 1 |
| KinGml104_05478 | `a67c23b00fe8` | cut_scene/075/VoiceMan_07505 | 351 | 41 | other_quest 232, unused 74, choice 3, not_for_translation 1 |

| quest | team files | team keys | in output | not in output by reason |
|---|---|---|---|---|
| HeaVnb108_02163 | 3.x/as-goes-light-so-goes-darkness.json | 157 | 141 | text_differs 10, not_in_searched_files 3, merged_rows 2, found_elsewhere 1 |
| KinGml101_05475 | 7.56/a-winters-dream.json, 7.56/cutscenes.json | 102 | 96 | source_row_skipped:choice 6 |
| KinGml104_05478 | 7.56/cutscenes.json, 7.56/windborne.json | 72 | 69 | source_row_skipped:choice 3 |

## Cutscene attribution

Which rows of a voiced-cutscene file belong to which quest, from `out/attribution/<file>.json`. Row ranges are inclusive.

- `cut_scene/030/VoiceMan_03008` (33 rows; window of 13 quests from lexical alignment of the expansion; votes split on 11 rows): HeaVna707_01669 0-21; unattributed 22-32.
- `cut_scene/031/VoiceMan_03100` (203 rows; window of 15 quests from lexical alignment of the expansion; votes split on 5 rows): HeaVnb101_02156 0-29; HeaVnb103_02158 30-49; HeaVnb104_02159 50-79; HeaVnb105_02160 80-119; HeaVnb106_02161 120-123; HeaVnb108_02163 124-202.
- `cut_scene/033/VoiceMan_03300` (202 rows; window of 15 quests from lexical alignment of the expansion; votes split on 2 rows): HeaVnd101_02242 0-30; HeaVnd102_02243 31-58; HeaVnd103_02244 59-109; HeaVnd104_02245 110-156; HeaVnd105_02246 157-167; HeaVnd106_02247 168-200; unattributed 201-201.
- `cut_scene/074/VoiceMan_07400` (508 rows; window of 24 quests from lexical alignment of the expansion; votes split on 173 rows): KinGmj101_05426 0-69; KinGmj102_05427 70-114; KinGmj103_05428 115-170; KinGmj104_05429 171-186; KinGmj103_05428 187-187; KinGmj105_05430 188-236; KinGmj106_05431 237-280; KinGmj107_05432 281-303; KinGmj108_05433 304-372; KinGmj109_05434 373-442; KinGmk101_05470 443-492; unattributed 493-507.
- `cut_scene/075/VoiceMan_07505` (351 rows; window of 4 quests from main-scenario quests changed in the same commit; votes split on 132 rows): KinGml101_05475 0-73; KinGml102_05476 74-175; KinGml103_05477 176-232; KinGml104_05478 233-276; unattributed 277-350.

## Names

`terms.json` holds 2318 Japanese names with their official English, which translations keep (`name` flags above).

## Japanese keys

329 rows, 329 distinct `key_ja`. Rows with an empty key: ['TEXT_HEAVNB108_02163_YSHTOLA_000_086']. Keys shared by more than one row: none. `key_ja_vectors.json` holds 29 vectors.

## Samples

Three lines per quest: most flags first, then longest.

### HeaVnb108_02163

**Alphinaud** (`TEXT_HEAVNB108_02163_ALPHINAUD_000_083`)

- JA: ドラゴン族に対する恐怖と憎悪が薄れることを祈ろう。 多くの犠牲の上に、この変革があるのだから……。
- EN: Let us pray that the Ishgardians who yet harbored doubts will take these events to heart and accept the truth of Ser Aymeric's words.
- Human: ขอให้ชาวอิชการ์ดที่ยังเคลือบแคลงสงสัยเก็บเหตุการณ์ในวันนี้ไปไตร่ตรอง และยอมรับความจริงในคำพูดของเซอร์เอเมอริกเสียที
- Haiku: ขอให้ความหวาดกลัวและความเกลียดชังที่ชาว Ishgardian ยังมีต่อมังกรจางลงเถอะครับ การเปลี่ยนแปลงครั้งนี้เกิดขึ้นได้ก็เพราะต้องแลกมากับการสูญเสียมากมาย ขอให้ชาว Ishgardian ที่ยังลังเลได้รับบทเรียนจากเหตุการณ์นี้ และยอมรับความจริงในคำพูดของท่าน Aymeric ด้วย...
- Flags: script: untranslated: Ishgardian Ishgardian; length: th/en 1.91, th/ja 5.18

**Narration** (`TEXT_VOICEMAN_03100_002000_NARRATION`)

- JA: フォルタン伯爵の回顧録『蒼天のイシュガルド』 第二章「光と闇の境界」より抜粋
- EN: From the memoirs of Count Edmont de Fortemps
*Heavensward: As Goes Light, So Goes Darkness*
- Human: (no team translation)
- Haiku: จากบันทึกความทรงจำของเคานต์ Edmont de Fortemps "Heavensward: As Goes Light, So Goes Darkness"
- Flags: name: イシュガルド is Ishgard in terms.json; review: Dropped the chapter marker 第二章 from 『蒼天のイシュガルド』第二章「光と闇の境界」; the Thai gives only a merged book/chapter title with no chapter number.

**Lucia** (`TEXT_HEAVNB108_02163_LUCIA_000_045`)

- JA: 教皇庁の封鎖は完了した。 奴らの注意を正面に惹き付けておくゆえ、頼むぞ！
- EN: We will hold here, Forename. The Fury guide and keep you!
- Human: (no team translation)
- Haiku: ปิดล้อม Vault เรียบร้อยแล้ว ข้าจะดึงความสนใจของพวกมันไว้ทางด้านหน้าเอง ฝากด้วยนะ!
- Flags: forename: source has Forename, translation does not; script: untranslated: Vault

### KinGml101_05475

**Alphinaud** (`TEXT_VOICEMAN_07505_000310_ALPHINAUD`)

- JA: もしや、君の…… エートスによる転移に、私たちも？
- EN: Were we...were we caught up in the incantation?
- Human: เรา...เราโดนคาถานั่นดูดมาด้วยหรือเปล่า
- Haiku: หรือว่า... การเคลื่อนย้ายด้วย Ethos ของคุณ ทำให้ผมกับ Estinien ถูกดึงไปด้วยหรือครับ?
- Flags: script: untranslated: Ethos Estinien; length: th/en 1.79, th/ja 3.36

**Alphinaud** (`TEXT_VOICEMAN_07505_000380_ALPHINAUD`)

- JA: 転移の最中に、イゼルと似た人物を……？
- EN: A woman who looked like Ysayle...
- Human: หญิงสาวที่หน้าตาเหมือนอีเซลรึ...
- Haiku: ระหว่างการเคลื่อนย้าย... ผมเห็นผู้หญิงที่หน้าตาคล้าย Ysayle หรือครับ?
- Flags: length: th/en 2.09, th/ja 3.63; review: Wrong agent: ja "転移の最中に、イゼルと似た人物を……？" asks whether the listener saw a lookalike, but th has Alphinaud say "ผมเห็น" (I saw).

**Alphinaud** (`TEXT_VOICEMAN_07505_000020_ALPHINAUD`)

- JA: アシエン・ハルマルトによれば、 それは星の理に則った、さながら自然治癒のような世界統合。
- EN: According to Halmarut, it is the fate that awaits should the reflections be allowed to merge of their own accord─an act of healing dictated by the laws of nature.
- Human: ตามที่ฮาลมารุตบอก มันคือชะตากรรมที่รออยู่หากปล่อยให้เหล่าโลกเงาสะท้อนหลอมรวมกันเองตามครรลอง—การเยียวยาที่กฎแห่งธรรมชาติกำหนดไว้
- Haiku: ตามคำของ Halmarut ผู้เป็น Ascian นั่นคือการรวมโลกเข้าด้วยกันตามกฎแห่งดาว คล้ายการรักษาตัวเองตามธรรมชาติครับ
- Flags: script: untranslated: Ascian

### KinGml104_05478

**Salvagecrewc** (`TEXT_KINGML104_05478_SALVAGECREWC_000_010`)

- JA: 見てのとおり、牽引している間は、 グラズ號とはそう簡単には行き来できないからね。 母船への到着まで、この浮島で過ごしてもらうことになるよ。
- EN: While the ship is towing the isle, we can't readily move between them. Which is to say, you'll have to remain here until we get to the mother ship.
- Human: ระหว่างที่เรือลากเกาะไปด้วย เราจะข้ามไปมาระหว่างสองที่ไม่ได้ง่ายๆ พูดง่ายๆ คือเธอต้องอยู่ตรงนี้จนกว่าจะถึงเรือแม่
- Haiku: อย่างที่เห็นนั่นแหละ ตอนที่กำลังลากเกาะอยู่ ฉันกับ Glaðr ก็ไปมาหาสู่กันไม่ได้ง่ายๆ หรอก เธอต้องอยู่บนเกาะนี้จนกว่าจะถึงเรือแม่นั่นแหละ
- Flags: script: untranslated: Glaðr

**Halmarut** (`TEXT_VOICEMAN_07505_001630_HALMARUT`)

- JA: ラハブレア様たちの思惑とは違っているでしょうが…… 世界統合を企む以上、私はアシエン・ハルマルトです。
- EN: Though my motives may differ from that of Lahabrea and the other unsundered, my objective remains the same─the Rejoining. Halmarut will suffice.
- Human: แม้แรงจูงใจของข้าจะต่างจากลาฮาเบรอาและเหล่าผู้มิได้ถูกแบ่งแยกคนอื่น แต่เป้าหมายของข้ายังคงเดิม—การหลอมรวมโลก เรียกฮาลมารุตก็พอแล้ว
- Haiku: แม้เจตนาของผมอาจต่างจากท่าน Lahabrea และพวกที่ไม่ถูกแยก แต่ตราบใดที่เป้าหมายของผมยังคงเป็นการรวมโลกกลับเป็นหนึ่งเดียว ผมก็คือ Ascian Halmarut ครับ Halmarut ก็พอครับ
- Flags: script: untranslated: Ascian

**Grahatia** (`TEXT_VOICEMAN_07505_001700_GRAHATIA`)

- JA: そんなことがあったのか……！ ヴォイドに行ったときと同じ消え方をしたから、 成功したんだろうとは思ってたが……。
- EN: That is quite a tale... As you disappeared in the same manner as before, we suspected the incantation was successful.
- Human: เรื่องราวชวนทึ่งจริงๆ... เพราะคุณหายตัวไปแบบเดียวกับคราวก่อน พวกเราเลยเดาว่าคาถานั้นคงสำเร็จ
- Haiku: อย่างนั้นเองหรือ...! เห็นว่าหายตัวไปด้วยวิธีเดียวกับตอนไปที่ Void ข้าก็เดาอยู่แล้วว่าคาถาคงสำเร็จ
- Flags: script: untranslated: Void
