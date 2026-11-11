# Haiku translation pipeline report

Model `claude-haiku-5-5`, effort `medium`. Every number below is computed from `out/cost_log.jsonl`, `out/review/<quest_id>.json`, `out/coverage/<quest_id>.json` and the sources. `out/<quest_id>.json` is the plugin-facing file.

## Cost

Per quest: the calls of the runs that produced the current output (translate + review, retries included). Attributing a cutscene file to quests takes one call per vote, listed under its file name.

| quest | backend | calls | input tok | cache-write tok | cache-read tok | output tok | of which thinking | cost USD | est. API-path USD |
|---|---|---|---|---|---|---|---|---|---|
| HeaVnb108_02163 (164 lines) | cli | 8 | 16 | 61205 | 5016 | 112145 | 93354 | 0.068365 | 0.062208 |
| KinGml101_05475 (96 lines) | cli | 6 | 12 | 34418 | 1254 | 41990 | 31882 | 0.027892 | 0.024197 |
| KinGml104_05478 (69 lines) | cli | 4 | 8 | 22994 | 1254 | 35328 | 28528 | 0.022276 | 0.019846 |
| VoiceMan_03008 attribution (33 rows, 3 votes) | cli | 3 | 6 | 26668 | 53336 | 29588 | 29464 | 0.020662 | 0.022612 |
| VoiceMan_03100 attribution (203 rows, 3 votes) | cli | 3 | 6 | 43833 | 89373 | 48487 | 48038 | 0.033904 | 0.037382 |
| VoiceMan_03300 attribution (202 rows, 3 votes) | cli | 3 | 6 | 42624 | 86955 | 33441 | 32954 | 0.026115 | 0.029496 |
| VoiceMan_07400 attribution (508 rows, 3 votes) | cli | 3 | 8 | 61228 | 185960 | 115310 | 114595 | 0.071761 | 0.082192 |
| VoiceMan_07505 attribution (351 rows, 3 votes) | cli | 3 | 6 | 31626 | 17164 | 25792 | 25473 | 0.019393 | 0.017593 |
| **total, current outputs** | cli | 33 | 68 | 324596 | 440312 | 442081 | 404288 | 0.290370 | 0.295525 |

All logged calls, including probes, rejected attempts and superseded runs: 56 calls, $1.135046.

### Every logged run

Same quest, same prompt: the spread between rows is run-to-run variance, mostly thinking tokens.

| quest | run | stages | effort | output tok | of which thinking | cost USD | current output |
|---|---|---|---|---|---|---|---|
| a-winters-dream | 20261110T191650 | translate+review | medium | 15891 | 12229 | 0.010262 |  |
| a-winters-dream | 20261110T191925 | translate+review | medium | 13733 | 10146 | 0.009180 | yes |
| a-rush-of-cold-wind | 20261110T192023 | translate+review | medium | 9458 | 7388 | 0.006259 |  |
| the-world-locked-in-ice | 20261110T192106 | translate+review | medium | 23448 | 18902 | 0.014713 |  |
| a-rush-of-cold-wind | seeded-review-check | review+review | medium | 6059 | 5480 | 0.005319 |  |
| a-rush-of-cold-wind | 20261110T192549-d39180 | translate+review | medium | 6881 | 4754 | 0.004991 |  |
| a-rush-of-cold-wind | 20261110T192635-6da495 | translate+review | low | 9070 | 6981 | 0.006082 |  |
| VoiceMan_07505 | 20261111T020413-d43b08 | attribute | high | 7790 | 7679 | 0.007015 | yes |
| KinGml101_05475 | 20261111T020448-48626d | translate+review+translate+review | medium | 28257 | 21736 | 0.018712 | yes |
| VoiceMan_03008 | 20261111T020703-7171b2 | attribute | high | 6603 | 6557 | 0.008347 |  |
| VoiceMan_03100 | 20261111T020734-357204 | attribute | high | 9979 | 9802 | 0.013709 |  |
| HeaVnb108_02163 | 20261111T020820-647317 | translate+review+translate+review+translate+review | medium | 95321 | 78915 | 0.058001 | yes |
| VoiceMan_03008 | 20261111T021545-544bbd | attribute | high | 12025 | 11969 | 0.010377 |  |
| VoiceMan_03100 | 20261111T021637-c9caf9 | attribute | high | 14325 | 14196 | 0.014604 |  |
| HeaVnb108_02163 | 20261111T021742-5bc75b | translate+review | medium | 16824 | 14439 | 0.010365 | yes |
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
| KinGml104_05478 | 20261111T123252-d0889d | translate+review+translate+review | medium | 35328 | 28528 | 0.022276 | yes |

CLI overhead: a probe with a 3-word prompt was billed 610 input tokens, so about that many tokens per call are the CLI harness, and the CLI writes the whole prompt to the 1-hour cache (2x the input price). The API-path estimate removes the harness tokens and prices all input at $0.10/MTok and the same output tokens at $0.50/MTok, without caching. It is an estimate; the API path was not run.

## Flags

Lines with at least one flag per check. `human` runs the same deterministic lints on the human reference as a noise baseline (the `name` lint is skipped there because terms.json holds Haiku's own spellings).

| quest | lines | any flag | empty | forename | name | pronoun | script | length | review | human: any lint |
|---|---|---|---|---|---|---|---|---|---|---|
| HeaVnb108_02163 | 164 | 30 | 0 | 4 | 20 | 0 | 0 | 6 | 2 | 4 |
| KinGml101_05475 | 96 | 15 | 0 | 0 | 4 | 0 | 10 | 1 | 1 | 0 |
| KinGml104_05478 | 69 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 |

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

`terms.json` holds 100 renderings.

- HeaVnb108_02163: received 23 known names; conflicts with terms.json (not overwritten): [{'en': 'Holy See', 'recorded': 'ศาลศักดิ์สิทธิ์', 'this_run': 'สำนักสันตะปาปา'}].
- KinGml101_05475: received 16 known names; conflicts with terms.json (not overwritten): [{'en': 'Estinien', 'recorded': 'เอสตินเนียน', 'this_run': 'อิสตินเนียน'}].
- KinGml104_05478: received 23 known names; conflicts with terms.json (not overwritten): none.

## Japanese keys

329 rows, 329 distinct `key_ja`. Rows with an empty key: ['TEXT_HEAVNB108_02163_YSHTOLA_000_086']. Keys shared by more than one row: none. `key_ja_vectors.json` holds 29 vectors.

## Samples

Three lines per quest: most flags first, then longest.

### HeaVnb108_02163

**Alphinaud** (`TEXT_HEAVNB108_02163_ALPHINAUD_000_005`)

- JA: オルシュファン卿……。
- EN: It was not so long ago, was it...
- Human: เพิ่งผ่านไปไม่นานนี้เองสินะ...
- Haiku: ท่านโอร์ชฟอง... เมื่อไม่นานมานี้เองนะครับ...
- Flags: name: Haurchefant is ออร์ชูฟัน in terms.json; name: Orshufan is ออร์ชูฟัน in terms.json; name: Ser is เซอร์ in terms.json

**Edmont** (`TEXT_VOICEMAN_03100_001740_EDMONT`)

- JA: アイメリク卿…… 水を差すような事を言うようで心苦しくはありますが、 今後は、より慎重になるよう進言させてもらいますぞ。
- EN: Yet how will they choose to remember it, Ser Aymeric? And will these events serve to bring man and dragon closer together, or drive a deeper wedge between brothers?
- Human: ทว่าผู้คนจะเลือกจดจำวันนี้อย่างไรเล่า ท่านเซอร์เอเมอริก และเหตุการณ์นี้จะช่วยดึงมนุษย์กับมังกรให้ใกล้ชิดกันยิ่งขึ้น หรือจะยิ่งตอกลิ่มความร้าวฉานระหว่างพี่น้องให้ลึกกว่าเดิมกันแน่
- Haiku: ข้าเสียใจที่ต้องพูดสิ่งที่ขัดหูท่าน แต่ต่อไปขอให้ท่านรอบคอบกว่านี้ ข้าจะขอเสนอแนะไว้
- Flags: name: Aymeric is เอเมอริก in terms.json; name: Ser is เซอร์ in terms.json

**Artoirel** (`TEXT_HEAVNB108_02163_ARTOIREL_BATTLETALK_006_005`)

- JA: どこまで卑劣な奴らなのだ……。 早く人質を解放し、アイメリク卿に加勢せねば！
- EN: Ser Aymeric is still wounded, Forename! If we do not move quickly, he will surely fall!
- Human: ท่านเอเมอริกยังบาดเจ็บ Forename! หากไม่รีบลงมือ ท่านไม่รอดแน่!
- Haiku: พวกนี้มันเลวทรามได้ถึงขนาดนี้เชียวหรือ... ต้องปลดปล่อยตัวประกันให้เร็วที่สุด แล้วไปช่วยท่านเอเมอริกให้ได้!
- Flags: forename: source has Forename, translation does not; name: Ser is เซอร์ in terms.json

### KinGml101_05475

**Thancred** (`TEXT_VOICEMAN_07505_000170_THANCRED`)

- JA: 罠という可能性もあるが…… ウィンタラーが現存する鏡像世界から選ばれているなら、 第四世界の様子も知るに越したことはないな。
- EN: While I wouldn't be surprised if it was a trap, if the Fourth was specifically chosen from among all worlds, it may nevertheless be worth paying it a visit.
- Human: ต่อให้เป็นกับดักผมก็ไม่แปลกใจหรอก แต่ถ้าเขาเจาะจงเลือกเดอะโฟร์ทขึ้นมาจากบรรดาโลกทั้งหมด มันก็อาจคุ้มค่าที่จะไปเยือนสักครั้ง
- Haiku: ก็อาจเป็นกับดักได้ แต่ถ้าโลกที่สี่ถูกเลือกมาจากบรรดาโลกเงาสะท้อนที่ยังมีอยู่ ก็คงไม่เสียหายที่จะไปดูสักหน่อย
- Flags: name: Winterer is วินเทอเรอร์ in terms.json; review: ja "ウィンタラーが現存する鏡像世界から選ばれているなら" has the Winterers as the one chosen, but th makes the Fourth World the chosen one ("ถ้าโลกที่สี่ถูกเลือก"), swapping the subject.

**Alphinaud** (`TEXT_VOICEMAN_07505_000020_ALPHINAUD`)

- JA: アシエン・ハルマルトによれば、 それは星の理に則った、さながら自然治癒のような世界統合。
- EN: According to Halmarut, it is the fate that awaits should the reflections be allowed to merge of their own accord─an act of healing dictated by the laws of nature.
- Human: ตามที่ฮาลมารุตบอก มันคือชะตากรรมที่รออยู่หากปล่อยให้เหล่าโลกเงาสะท้อนหลอมรวมกันเองตามครรลอง—การเยียวยาที่กฎแห่งธรรมชาติกำหนดไว้
- Haiku: ตามคำของอาเชียน ฮัลมารุต หากปล่อยให้เงาสะท้อนรวมตัวกันเองตามธรรมชาติ นั่นคือจุดจบที่รออยู่ เป็นการรักษาตัวเองตามกฎแห่งธรรมชาติ
- Flags: name: Rejoining is การรวมโลกเข้าด้วยกัน in terms.json

**Tataru** (`TEXT_KINGML101_05475_TATARU_000_204`)

- JA: もちろん無事だとは信じていましたが、 安否もわからないと不安だけは募るもの……。 今後は気をつけてほしいのでっす！
- EN: While we had faith that you were safe and well, without *any* response, we couldn't help but worry. In future, please make an effort to stay in contact!
- Human: ถึงพวกเราจะเชื่อมั่นว่าคุณปลอดภัยดี แต่การไม่มีคำตอบกลับมาสักนิดเดียว มันก็อดเป็นห่วงไม่ได้นี่นา! ต่อไปนี้ช่วยพยายามติดต่อกันบ้างนะคะ!
- Haiku: ฉันเชื่อมั่นว่าคุณต้องปลอดภัยค่ะ แต่พอไม่มีข่าวคราวเลย ก็อดกังวลไม่ได้เลยนะคะ ต่อจากนี้ช่วยพยายามติดต่อกลับมาด้วยนะคะ！
- Flags: script: untranslated: ！

### KinGml104_05478

**Salvagecrewc** (`TEXT_KINGML104_05478_SALVAGECREWC_000_050`)

- JA: まずは天幕を張りたいところだけど…… さすがにもうちょっと氷が溶けてくれないと、 ペグが刺さらないかなあ？
- EN: I'd like to pitch a tent, but the stakes won't pierce the ground until the ice has thawed some more...
- Human: อยากกางเต็นท์อยู่เหมือนกัน แต่ตอกหมุดไม่ลงเลยจนกว่าน้ำแข็งจะละลายมากกว่านี้...
- Haiku: อยากจะกางเต็นท์ก่อนอยู่หรอก แต่คงต้องรอให้น้ำแข็งละลายไปอีกหน่อย ไม่งั้นหมุดเต็นท์คงปักลงพื้นไม่ได้แน่ๆ
- Flags: review: The ja ends in a hedged question, 'ペグが刺さらないかなあ？' ('I wonder if the pegs won't go in?'), but the th states it as a certainty with 'แน่ๆ' ('surely can't'), changing the meaning.

**Krile** (`TEXT_VOICEMAN_07505_001810_KRILE`)

- JA: 第九世界側から今回の件を探ってみたいのだけれど…… トレノをはじめ、あっちにはまだ、 雷属性による麻痺症状で苦しんでいる人がいるの。
- EN: I intend to visit the Ninth to see if there have been any developments following recent events. While there, I also hope to treat those in Treno and elsewhere who suffer from levin sickness.
- Human: ฉันตั้งใจจะไปเยือนโลกเงาสะท้อนที่เก้า เพื่อดูว่ามีความคืบหน้าอะไรหลังเหตุการณ์ที่ผ่านมาบ้าง แล้วก็หวังจะได้รักษาผู้คนในเทรโนและที่อื่นๆ ที่ป่วยด้วยโรคไข้สายฟ้าไปด้วย
- Haiku: ฉันอยากลองสืบเรื่องครั้งนี้จากทางโลกที่เก้าดูน่ะ... ที่เทรโนและที่อื่นทางนั้น ยังมีคนที่ทรมานจากอาการเป็นอัมพาตจากธาตุสายฟ้าอยู่เลย
- Flags: none

**Halmarut** (`TEXT_VOICEMAN_07505_001614_HALMARUT`)

- JA: ですが、考えがあるなら事前に共有していただけた方が、 私もびっくりせずに済みますし、協力できて効率的かと……！
- EN: Nevertheless, had you shared your intentions beforehand, I might have offered my cooperation. It would have been more efficient─and spared me the shock.
- Human: กระนั้นก็เถอะ หากท่านบอกเจตนาไว้ล่วงหน้า ข้าคงยื่นมือให้ความร่วมมือได้ มันย่อมมีประสิทธิภาพกว่านี้—แล้วข้าก็คงไม่ต้องตกใจด้วย
- Haiku: แต่ถ้ามีแผนอยู่ละก็ ช่วยบอกกันล่วงหน้าไว้น่าจะดีกว่านะคะ ฉันจะได้ไม่ตกใจ แล้วร่วมมือกันก็มีประสิทธิภาพกว่าด้วยค่ะ...!
- Flags: none
