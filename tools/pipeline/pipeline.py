#!/usr/bin/env python3
"""Select -> attribute cutscene lines -> translate (Haiku) -> check -> cover -> report, one quest at a time.

usage:
  pipeline.py --commit REV [--quest NAME_OR_STEM ...]   live content: main-scenario quests whose files REV changed
  pipeline.py --quest NAME_OR_STEM ... [--at REV]       old content: by quest name or stem, from game data
  pipeline.py --patch X.Y [--at REV]                    old content: the quests of the cut_scene/0XY files
  pipeline.py                                           no model calls: rebuild every stored quest and the report
options: --force (translate again), --list (print the selection and stop), --probe (measure CLI overhead)
Run strip_team_overlap.py --apply afterwards so the team's rows do not hide the new lines in the plugin.

A quest's sources are its quest file and the voiced-cutscene (VoiceMan) files that hold its lines. Every row
of those files ends up translated or skipped with a reason; out/coverage/<quest_id>.json records which, and
the run stops if a row is unaccounted for. Model calls happen only for rows without a stored translation
(or with --force) and for cutscene files without a stored attribution. Every run then rewrites
haiku/<quest_id>.json (plugin-facing), out/review/<quest_id>.json (pipeline record) and the coverage file from
the stored translations and the sources, lints and terms.json, then the report. The team's translations are
read from th/ at TEAM_REV, not from the working tree, because this branch removes team rows that collide.
"""
import argparse
import difflib
import json
import os
import re
import subprocess
import time
import uuid
from collections import Counter
from functools import cache
from pathlib import Path

import attribution
import gamedata
from key_ja import EDGE_CASES, key_ja

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
TEAM_REV = os.environ.get("FFXIV_TEAM_REV", "main")
SHARED_TEAM_FILE = "cutscenes.json"
OUT = HERE / "out"
PLUGIN_OUT = Path(os.environ.get("FFXIV_PLUGIN_OUT", ROOT / "haiku"))
COST_LOG = OUT / "cost_log.jsonl"
REVIEW_DIR = "review"
COVERAGE_DIR = "coverage"
TERMS = HERE / "terms.json"
VECTORS_NAME = "key_ja_vectors.json"
# Most lines sent in one translate call; a quest with more is split into equal chunks.
CHUNK = 60
# A row with nothing to translate keeps that reason whichever quest it sits in.
NO_CONTENT = ("unused", "not_for_translation", "empty")
# A team key that matches no row is explained by the closest row when their keys are at least this similar,
# and by a run of up to this many consecutive rows when it equals their keys joined.
NEAR_MATCH = 0.8
MERGED_ROWS = 4
# Japanese punctuation the model copies into Thai, and what the team writes instead.
PUNCTUATION = str.maketrans({**dict(zip("！？，．：；（）　", "!?,.:;() ")), "…": "..."})

MODEL = "claude-haiku-5-5"
EFFORT = "medium"
USD_PER_MTOK = {"input": 0.10, "output": 0.50, "cache_write": 0.125, "cache_read": 0.01}

# ข้า the pronoun, not เข้า / ข้าง / ข้าม / ข้าว / ข้าศึก. Misses ข้ามี, ข้ามา.
KHA = r"(?<!เ)ข้า(?![งมวศ])"
KA = r"คะ(?!แนน|เน)"
JAO = r"เจ้า(?!ของ|หน้าที่|นาย|หญิง|ชาย|เมือง|ค่ะ|คะ)"
VOICES = {
    "Alphinaud": ("polite, educated young man. ผม / คุณ, ends with ครับ where natural.", [KHA, JAO, "ฉัน", "ค่ะ", KA]),
    "Estinien": ("curt, blunt dragoon. ข้า / เจ้า, no polite particles.", ["ผม", "ฉัน", "ครับ", "ค่ะ", KA]),
    "Tataru": (
        "cheerful, friendly, receptionist-polite. ฉัน / คุณ, ค่ะ / คะ. Her Japanese tic is the stretched "
        "でっす / まっした; where ja has it, stretch the particle lightly (ค่า, นะคะะ), not on every line.",
        [KHA, JAO, "ผม", "ครับ"],
    ),
}

# Each band covers 120 of the 121 human-translated lines of patch 7.56. en and ja often differ in
# length, so a line is suspicious only when it fits neither.
LEN_BAND_EN = (0.5, 1.6)
LEN_BAND_JA = (0.8, 3.0)

TRANSLATE_SYSTEM = (
    """You translate Final Fantasy XIV main-scenario dialogue into Thai for a free fan translation. Each line gives the speaker, the Japanese original (ja) and the official English localization (en). Lines are in script order within one quest, so read them as one conversation. Lines with "part": "cutscene" are the quest's voiced cutscenes, in script order among themselves.

Source priority
- Translate from the Japanese. The English is a looser localization; use it to resolve who is speaking to whom and what is being referred to.
- When ja and en disagree in meaning, ja wins. A name that only en has, such as the person addressed, stays in the Thai line: players read names in English in the game, so it tells them who is meant. Titles around it are translated (en "Master Alphinaud, ..." -> ท่าน Alphinaud). Other content that only en adds (a flourish) may stay if it fits naturally.
- Japanese traps to check on every line: omitted subjects and objects (decide who does what to whom before writing; くれる, もらう, あげる give the direction), が and けど joining clauses as "but" rather than marking a subject, and sentence-final softeners that are not questions.
- Newlines inside ja are display wraps, not sentence breaks. Write each Thai line as a single line.
- When en is a voice direction in [square brackets], the line is a short vocal sound. Translate the ja sound as a Thai interjection, not the direction.
- "shown_as" is the name the game displays while the speaker's identity is not revealed. It is context only; never put it in the Thai line.

Thai style
- Natural spoken Thai as in a well-localized game script, not word-for-word translationese. Keep the weight of words (hope, at once, in earnest). Do not add or drop content.
- Keep ? ! ... to match the emotion of the original. Write ๆ attached to its word and followed by a space (จริงๆ แล้ว, never จริง ๆ แล้ว).
- `Forename` and `Surname` are the player's name placeholders. Copy them exactly, in Latin letters, wherever ja or en has them. Never translate, transliterate, or drop them.
- Proper nouns (people, places, ships, organizations, named concepts) stay in their official English form, in Latin letters, exactly as en spells them. Never transliterate them into Thai script and never romanize a Japanese reading (「暁」 is Scions, not Akatsuki or อรุโณทัย). A line's "terms" maps each Japanese name in it to that English form; write those exactly.
- Everything else is in Thai script. No Japanese characters may remain, and no Latin text other than proper nouns and the placeholders. English marks emphasis and ship names with *asterisks*; drop the asterisks.

Voices (pronouns and particles stay consistent per speaker)
"""
    + "".join(f"- {name}: {voice}\n" for name, (voice, _) in VOICES.items())
    + """- Any other speaker: plain everyday Thai matching the register of their Japanese (rough stays rough, casual stays casual). Pick one first-person pronoun per speaker and keep it.

Output
Return only a JSON object, no code fence, no commentary:
{"lines": {"<id>": "<Thai>", ...}}
- "lines" has exactly one non-empty entry per input id."""
)

REVIEW_SYSTEM = """You review a Thai fan translation of Final Fantasy XIV dialogue against its Japanese original (ja). The English localization (en) is a looser reference. Lines are in script order within one quest.

Flag a line only when the Thai (th) mistranslates the Japanese: wrong agent or recipient of an action, reversed or changed meaning, が/けど "but" read as a subject or the reverse, a statement turned into a question, meaning-bearing content dropped, or content invented that neither ja nor en has. When ja and en disagree, ja is right. Content that only en adds is allowed. Do not flag style, word choice, pronouns, or name spellings.

Return only a JSON object, no code fence: {"<id>": "<one-line reason in English, quoting the ja fragment>"} for flagged lines only. Return {} if none."""


def write_atomic(path, text):
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def dump(obj):
    return json.dumps(obj, ensure_ascii=False, indent=1) + "\n"


def new_run_id():
    return f"{time.strftime('%Y%m%dT%H%M%S')}-{uuid.uuid4().hex[:6]}"


def slug(name):
    return re.sub("[^a-z0-9]+", "-", name.lower().replace("'", "").replace("’", "")).strip("-")


def team_git(*args):
    return subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True, encoding="utf-8", check=True).stdout


@cache
def team_files():
    """Paths of the team's files at TEAM_REV, relative to th/."""
    return tuple(line[len("th/"):] for line in team_git("ls-tree", "-r", "--name-only", TEAM_REV, "th/").splitlines() if line.endswith(".json"))


@cache
def read_team(path):
    """The dialogues of th/<path> at TEAM_REV."""
    return json.loads(team_git("show", f"{TEAM_REV}:th/{path}"))["dialogues"]


def quest_team_files(quest):
    return sorted(path for path in team_files() if path.count("/") == 1 and path.endswith(f"/{slug(quest['name'])}.json"))


def load_team(quest):
    """The team's translations for one quest: its own file(s), and the shared cutscene file(s) next to them.
    {"quest": {path: {key: text}}, "shared": {path: {key: text}}}, paths relative to th/."""
    out = {"quest": {}, "shared": {}}
    for path in quest_team_files(quest):
        for kind, file in (("quest", path), ("shared", f"{path.split('/')[0]}/{SHARED_TEAM_FILE}")):
            if file in team_files():
                out[kind][file] = {d["key"]: d["text"] for d in read_team(file)}
    return out


def build_unit(source, quest, records):
    """Every row of the quest's sources with what happens to it.

    `records` are the stored attributions of the cutscene files that may hold the quest's lines. A file
    becomes a source when at least one of its rows is attributed to the quest. Each row gets `skip`: None
    (translated) or the reason, and `detail` for the reasons that point somewhere.
    """
    rows = gamedata.read_rows(source, gamedata.quest_path(quest["stem"]))
    for row in rows:
        row["owner"] = quest["stem"]
    cutscene_files = []
    for record in records:
        owners = attribution.by_row(record)
        if quest["stem"] not in owners:
            continue
        cutscene_files.append(record["file"])
        for row, owner in zip(gamedata.read_rows(source, record["file"]), owners, strict=True):
            row["owner"] = owner
            rows.append(row)
    first = {}
    for row in rows:
        row["detail"] = None
        if row["skip"] in NO_CONTENT:
            continue
        if row["owner"] != quest["stem"]:
            row["skip"], row["detail"] = ("other_quest", row["owner"]) if row["owner"] else ("unattributed", None)
        elif row["skip"] is None and row["key"] in first:
            row["skip"], row["detail"] = "duplicate_key", first[row["key"]]
        elif row["skip"] is None:
            first[row["key"]] = row["text_id"]
    return {"quest": quest, "rows": rows, "cutscene_files": cutscene_files, "examined": [record["file"] for record in records]}


def find_elsewhere(source, quest_table, quest, keys):
    """{key: 'file text_id'} for keys that sit in another main-scenario quest file or cutscene file of the expansion."""
    found, wanted = {}, set(keys)
    paths = [gamedata.quest_path(q["stem"]) for q in quest_table.values() if q["msq"] and q["expansion"] == quest["expansion"]]
    paths += [path for path in source.files("cut_scene") if attribution.expansion_of(path) == quest["expansion"]]
    for path in paths:
        if not wanted - set(found):
            break
        for row in gamedata.read_rows(source, path):
            if row["key"] in wanted and row["key"] not in found:
                found[row["key"]] = f"{path} {row['text_id']}"
    return found


def explain_absent(rows, key):
    """Why a team key equals no source key: (reason, detail), or None when no row comes close."""
    state = lambda row: f"{row['file']} {row['text_id']} ({'skipped:' + row['skip'] if row['skip'] else 'translated'})"
    keyed = [row for row in rows if row["key"]]
    for start, row in enumerate(keyed):
        for count in range(2, MERGED_ROWS + 1):
            run = keyed[start:start + count]
            if len({r["file"] for r in run}) == 1 and "".join(r["key"] for r in run) == key:
                return "merged_rows", "the team joined consecutive rows: " + "; ".join(state(r) for r in run)
    if not key or not keyed:
        return None
    ratio, row = max(((difflib.SequenceMatcher(None, key, row["key"], autojunk=False).ratio(), row) for row in keyed), key=lambda pair: pair[0])
    if ratio >= NEAR_MATCH:
        return "text_differs", f"closest row, key similarity {ratio:.2f}: {state(row)}; source text: {row['text_en']}"
    return None


def build_coverage(source, quest_table, unit, team, dialogues):
    """The proof that no row and no team key went missing. `dialogues` is the plugin-facing list."""
    quest, rows = unit["quest"], unit["rows"]
    output = {d["key"] for d in dialogues}
    sources = {}
    for row in rows:
        entry = sources.setdefault(row["file"], {"file": row["file"], "rows": 0, "translated": 0, "skipped": Counter()})
        entry["rows"] += 1
        if row["skip"]:
            entry["skipped"][row["skip"]] += 1
        else:
            entry["translated"] += 1
    by_key = {}
    for row in rows:
        by_key.setdefault(row["key"], []).append(row)

    def why_missing(key, row):
        detail = f" ({row['detail']})" if row["detail"] else ""
        return {"key": key, "reason": f"source_row_skipped:{row['skip']}", "detail": f"{row['file']} {row['text_id']}{detail}"}

    team_keys, missing, unmatched_shared = [], [], []
    for path, lines in team["quest"].items():
        for key in lines:
            found = by_key.get(key, [])
            team_keys.append((path, key, next((row for row in found if row["owner"] == quest["stem"]), found[0] if found else None)))
    for path, lines in team["shared"].items():
        for key in lines:
            mine = [row for row in by_key.get(key, []) if row["owner"] == quest["stem"] and row["file"] in unit["cutscene_files"]]
            if mine:
                team_keys.append((path, key, mine[0]))
            elif key not in by_key:
                unmatched_shared.append(key)
    absent = [key for _, key, row in team_keys if key not in output and not row]
    elsewhere = find_elsewhere(source, quest_table, quest, absent) if absent else {}
    for path, key, row in team_keys:
        if key in output:
            continue
        explained = None if row else explain_absent(rows, key)
        if row:
            missing.append({"team_file": path, **why_missing(key, row)})
        elif explained:
            missing.append({"team_file": path, "key": key, "reason": explained[0], "detail": explained[1]})
        elif key in elsewhere:
            missing.append({"team_file": path, "key": key, "reason": "found_elsewhere", "detail": elsewhere[key]})
        else:
            missing.append({"team_file": path, "key": key, "reason": "not_in_searched_files", "detail": "no row of this expansion's main-scenario quest files or cutscene files has this key or a similar one at this commit; the line may come from another sheet (NPC idle talk, duty yells)"})
    return {
        "quest_id": quest["stem"], "name": quest["name"], "datamining_commit": source.commit,
        "cutscenes_linked_in_quest_csv": quest["cutscenes"],
        "cutscene_files_examined": unit["examined"],
        "totals": {
            "rows": len(rows), "translated": sum(not row["skip"] for row in rows),
            "skipped": dict(Counter(row["skip"] for row in rows if row["skip"]).most_common()),
        },
        "sources": [{**entry, "skipped": dict(entry["skipped"].most_common())} for entry in sources.values()],
        "team": {
            "files": sorted({path for path, _, _ in team_keys} | set(team["quest"])),
            "keys": len(team_keys), "in_output": sum(key in output for _, key, _ in team_keys),
            "not_in_output": dict(Counter(entry["reason"] for entry in missing).most_common()),
            "not_in_output_keys": missing,
            "shared_file_keys_matching_no_selected_row": unmatched_shared,
        },
        "rows_detail": [
            {"file": row["file"], "row": row["row"], "text_id": row["text_id"], "key": row["key"],
             "disposition": "skipped" if row["skip"] else "translated", "reason": row["skip"], "detail": row["detail"]}
            for row in rows
        ],
    }


def check_coverage(source, coverage, dialogues):
    """Stop when a source row or a team key is unaccounted for. Counts the source files again, independently."""
    problems = []
    detail = coverage["rows_detail"]
    for entry in coverage["sources"]:
        expected = len(source.table(f"en/{entry['file']}"))
        seen = sorted(row["row"] for row in detail if row["file"] == entry["file"])
        if seen != list(range(expected)):
            lost = sorted(set(range(expected)) - set(seen))
            problems.append(f"{entry['file']}: {expected} rows in the CSV, {len(seen)} accounted for; missing rows {lost[:10]}")
        if entry["translated"] + sum(entry["skipped"].values()) != expected:
            problems.append(f"{entry['file']}: translated + skipped does not add up to {expected}")
    skipped_without_reason = [row["text_id"] for row in detail if row["disposition"] == "skipped" and not row["reason"]]
    if skipped_without_reason:
        problems.append(f"skipped without a reason: {skipped_without_reason[:5]}")
    translated = [row["key"] for row in detail if row["disposition"] == "translated"]
    texts = {d["key"]: d["text"] for d in dialogues}
    untranslated = [key for key in translated if not texts.get(key, "").strip()]
    if untranslated or len(translated) != len(dialogues) or len(set(translated)) != len(translated):
        problems.append(f"{len(translated)} rows marked translated, {len(dialogues)} dialogues written, {len(untranslated)} without text")
    totals, team = coverage["totals"], coverage["team"]
    if totals["translated"] + sum(totals["skipped"].values()) != totals["rows"] or totals["rows"] != len(detail):
        problems.append("totals do not add up")
    if team["in_output"] + len(team["not_in_output_keys"]) != team["keys"] or any(not entry["reason"] for entry in team["not_in_output_keys"]):
        problems.append("a team key is neither in the output nor listed with a reason")
    if problems:
        raise SystemExit(f"{coverage['quest_id']}: coverage check failed: " + "; ".join(problems))


def call_cli(system, user, effort, model):
    cmd = [
        "claude", "-p", "--model", model, "--effort", effort, "--output-format", "json",
        "--tools", "", "--system-prompt", system,
        "--safe-mode", "--strict-mcp-config", "--disable-slash-commands", "--no-session-persistence",
    ]
    proc = subprocess.run(cmd, input=user, capture_output=True, text=True, cwd=HERE, timeout=900)
    try:
        result = json.loads(proc.stdout)
    except ValueError:
        raise SystemExit(f"claude CLI failed (exit {proc.returncode}): {proc.stderr[:500] or proc.stdout[:500]}")
    if result.get("is_error"):
        raise SystemExit(f"claude CLI error: {str(result.get('result'))[:500]}")
    usage = result["usage"]
    return result["result"], {
        "backend": "cli", "model": ",".join(result["modelUsage"]),
        "input_tokens": usage["input_tokens"], "output_tokens": usage["output_tokens"],
        "cache_write_tokens": usage["cache_creation_input_tokens"],
        "cache_read_tokens": usage["cache_read_input_tokens"],
        "thinking_tokens": usage.get("output_tokens_details", {}).get("thinking_tokens"),
        "stop_reason": result.get("stop_reason"), "cost_usd": result["total_cost_usd"],
    }


def call_api(system, user, effort, model):
    import anthropic

    message = anthropic.Anthropic().messages.create(
        model=model, max_tokens=16000,
        system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
        output_config={"effort": effort},
        messages=[{"role": "user", "content": user}],
    )
    usage = message.usage
    tokens = {
        "input": usage.input_tokens, "output": usage.output_tokens,
        "cache_write": usage.cache_creation_input_tokens or 0,
        "cache_read": usage.cache_read_input_tokens or 0,
    }
    return "".join(block.text for block in message.content if block.type == "text"), {
        "backend": "api", "model": message.model,
        "input_tokens": tokens["input"], "output_tokens": tokens["output"],
        "cache_write_tokens": tokens["cache_write"], "cache_read_tokens": tokens["cache_read"],
        "thinking_tokens": None, "stop_reason": message.stop_reason,
        "cost_usd": sum(tokens[kind] * USD_PER_MTOK[kind] for kind in tokens) / 1e6,
    }


def log_call(entry):
    OUT.mkdir(exist_ok=True)
    with open(COST_LOG, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")


def ask(call, run, stage, system, user, parse, effort=None, model=None):
    """One request, validated by `parse`; one retry that tells the model what was wrong."""
    prompt, effort, model = user, effort or EFFORT, model or MODEL
    for attempt in (1, 2):
        text, usage = call(system, prompt, effort, model)
        try:
            body = text[text.index("{"): text.rindex("}") + 1]
            parsed, error = parse(json.loads(body)), None
        except (ValueError, KeyError, TypeError, AttributeError) as exc:
            parsed, error = None, f"{type(exc).__name__}: {exc}"
        log_call({"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), **run, "stage": stage, "attempt": attempt, "effort": effort, **usage, "error": error})
        if error is None:
            return parsed
        prompt = f"{user}\n\nYour previous reply was rejected ({error}). Return the complete JSON object again."
    raise SystemExit(f"{run['quest']}/{stage}: invalid output twice: {error}")


class Terms:
    """terms.json (built by build_terms.py): the official English of each Japanese proper noun. A line uses
    the longest names in its Japanese, without overlap: エーテライト・プラザ, not エーテライト inside it."""

    def __init__(self, english):
        self.english = english
        self.pattern = re.compile("|".join(map(re.escape, sorted(english, key=len, reverse=True))) or "(?!)")

    def __len__(self):
        return len(self.english)

    def used_by(self, row):
        return {match.group(): self.english[match.group()] for match in self.pattern.finditer(row["text_ja"])}


def load_terms():
    return Terms(json.loads(TERMS.read_text(encoding="utf-8")) if TERMS.exists() else {})


def lint(row, text, terms):
    flags = []
    if not text.strip():
        return [{"check": "empty", "detail": ""}]
    for placeholder in ("Forename", "Surname"):
        if placeholder in row["text_en"] + row["text_ja"] and placeholder not in text:
            flags.append({"check": "forename", "detail": f"source has {placeholder}, translation does not"})
    names = terms.used_by(row)
    for ja, en in names.items():
        if en not in text:
            flags.append({"check": "name", "detail": f"{ja} is {en} in terms.json"})
    used = [p for p in VOICES.get(row["speaker"], ("", []))[1] if re.search(p, text)]
    if used:
        flags.append({"check": "pronoun", "detail": f"{row['speaker']} uses " + " ".join(re.search(p, text).group() for p in used)})
    # Latin is a proper noun when en or terms.json has the word; anything else was left untranslated.
    english = set(re.findall(r"\w+", " ".join([row["text_en"], *names.values()])))
    leftover = [
        word for word in re.findall(r"[A-Za-z\u00C0-\u024F\u3000-\u30FF\u3400-\u9FFF\uFF00-\uFFEF]+", text.replace("Forename", "").replace("Surname", ""))
        if word not in english
    ]
    if leftover:
        flags.append({"check": "script", "detail": "untranslated: " + " ".join(leftover)})
    en_ratio, ja_ratio = len(text) / len(row["text_en"]), len(text) / len(row["text_ja"])
    fits_en = LEN_BAND_EN[0] <= en_ratio <= LEN_BAND_EN[1]
    fits_ja = LEN_BAND_JA[0] <= ja_ratio <= LEN_BAND_JA[1]
    if len(row["text_en"]) >= 15 and not (fits_en or fits_ja):
        flags.append({"check": "length", "detail": f"th/en {en_ratio:.2f}, th/ja {ja_ratio:.2f}"})
    return flags


def lines_block(rows, with_thai=False, terms=None):
    def line(n, row):
        out = {"id": str(n), "speaker": row["speaker"]}
        if row["shown_as"]:
            out["shown_as"] = row["shown_as"]
        if row["file"].startswith("cut_scene/"):
            out["part"] = "cutscene"
        out.update(ja=row["text_ja"], en=row["text_en"])
        if terms and (names := terms.used_by(row)):
            out["terms"] = names
        if with_thai:
            out["th"] = row["text_haiku"]
        return json.dumps(out, ensure_ascii=False)

    return ",\n".join(line(n, row) for n, row in enumerate(rows, 1))


def translate(call, run, rows, terms):
    """Sets text_haiku on every row."""
    ids = [str(n) for n in range(1, len(rows) + 1)]

    def parse(reply):
        lines = reply["lines"]
        bad = [i for i in ids if not (isinstance(lines.get(i), str) and lines[i].strip())]
        if bad or len(lines) != len(ids):
            raise ValueError(f"ids missing or empty: {bad}; unexpected: {sorted(set(lines) - set(ids))}")
        return lines

    lines = ask(call, run, "translate", TRANSLATE_SYSTEM, f"Lines:\n[{lines_block(rows, terms=terms)}]", parse)
    for i, row in zip(ids, rows):
        row["text_haiku"] = " ".join(lines[i].translate(PUNCTUATION).split())


def review(call, run, rows):
    """Returns {row position: reason} for lines the reviewer thinks mistranslate the Japanese."""

    def parse(reply):
        if not all(isinstance(v, str) and v.strip() and 1 <= int(i) <= len(rows) for i, v in reply.items()):
            raise ValueError("review must map known ids to non-empty reasons")
        return {int(i) - 1: v for i, v in reply.items()}

    return ask(call, run, "review", REVIEW_SYSTEM, f"Lines:\n[{lines_block(rows, with_thai=True)}]", parse)


SOURCES = {}


def source_at(commit):
    """(Source, quest table) of a commit, read once per run."""
    if commit not in SOURCES:
        source = gamedata.Source(commit)
        SOURCES[commit] = SOURCES[source.commit] = (source, gamedata.quests(source))
    return SOURCES[commit]


def stored_attributions(files):
    return [json.loads((OUT / attribution.ATTRIBUTION_DIR / f"{path.split('/')[-1]}.json").read_text(encoding="utf-8")) for path in files]


def load_record(stem):
    path = OUT / REVIEW_DIR / f"{stem}.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def stored_work(record):
    return {
        row["key"]: {"text_haiku": row["text_haiku"], "review": next((f["detail"] for f in row["flags"] if f["check"] == "review"), None)}
        for row in record["rows"]
    }


def run_quest(stem, call, force, selection):
    """Translate and review the rows of one quest that have no stored translation, then store the quest."""
    source, quest_table = source_at(selection["commit"])
    unit = build_unit(source, quest_table[stem], stored_attributions(selection["cutscene_candidates"]))
    record = None if force else load_record(stem)
    work = stored_work(record) if record else {}
    meta = {"selection": selection, "run_ids": record["run_ids"] if record else []}
    todo = [row for row in unit["rows"] if not row["skip"] and row["key"] not in work]
    if todo:
        run = {"run_id": new_run_id(), "quest": stem}
        meta["run_ids"] = meta["run_ids"] + [run["run_id"]]
        size = -(-len(todo) // -(-len(todo) // CHUNK))
        terms = load_terms()
        for start in range(0, len(todo), size):
            rows = todo[start:start + size]
            translate(call, run, rows, terms)
            reasons = review(call, run, rows)
            for position, row in enumerate(rows):
                work[row["key"]] = {"text_haiku": row["text_haiku"], "review": reasons.get(position)}
    store(stem, meta, work)
    print(f"{stem}: {len(todo)} lines translated and reviewed, {sum(not row['skip'] for row in unit['rows']) - len(todo)} already stored")


def store(stem, meta, model_work):
    """The only writer of a quest's files. Everything but model_work and meta is derived again from the sources.

    out/review/<quest_id>.json is the pipeline's record and is written first; the plugin-facing
    out/<quest_id>.json and out/coverage/<quest_id>.json are projections of it, so a crash between the
    writes is repaired by the next run. Nothing is written when the coverage check fails.
    """
    source, quest_table = source_at(meta["selection"]["commit"])
    quest = quest_table[stem]
    unit = build_unit(source, quest, stored_attributions(meta["selection"]["cutscene_candidates"]))
    team = load_team(quest)
    human = {key: text for lines in [*team["shared"].values(), *team["quest"].values()] for key, text in lines.items()}
    terms = load_terms()
    rows = [row for row in unit["rows"] if not row["skip"]]
    for row in rows:
        work = model_work[row["key"]]
        row["text_haiku"], row["text_human"] = work["text_haiku"], human.get(row["key"])
        row["flags"] = lint(row, row["text_haiku"], terms) + ([{"check": "review", "detail": work["review"]}] if work["review"] else [])
    dialogues = [
        {"key": row["key"], "key_ja": row["key_ja"], "text_id": row["text_id"], "speaker": row["speaker"],
         "text_en": row["text_en"], "text_ja": row["text_ja"], "text": row["text_haiku"]}
        for row in rows
    ]
    coverage = build_coverage(source, quest_table, unit, team, dialogues)
    check_coverage(source, coverage, dialogues)
    record = {"quest_id": stem, "name": quest["name"], **meta, "cutscene_files": unit["cutscene_files"]}
    for folder in (REVIEW_DIR, COVERAGE_DIR):
        (OUT / folder).mkdir(parents=True, exist_ok=True)
    PLUGIN_OUT.mkdir(parents=True, exist_ok=True)
    write_atomic(OUT / REVIEW_DIR / f"{stem}.json", dump({
        **record, "rows": [{field: row[field] for field in ("text_id", "key", "text_human", "text_haiku", "flags")} for row in rows],
    }))
    write_atomic(PLUGIN_OUT / f"{stem}.json", dump({
        "quest_id": stem,
        "source": {"quest": stem, "cutscene_files": unit["cutscene_files"], "datamining_commit": source.commit},
        "repo_file": next(iter(team["quest"]), None),
        "dialogues": dialogues,
    }))
    write_atomic(OUT / COVERAGE_DIR / f"{stem}.json", dump(coverage))
    return {**record, "datamining_commit": source.commit, "rows": rows, "coverage": coverage}


def refresh():
    """Rewrite every stored quest from its review record and the sources, lints and terms.json. No model calls."""
    quests = []
    for path in sorted((OUT / REVIEW_DIR).glob("*.json")):
        old = json.loads(path.read_text(encoding="utf-8"))
        meta = {field: old[field] for field in ("selection", "run_ids")}
        try:
            quests.append(store(old["quest_id"], meta, stored_work(old)))
        except KeyError as missing:
            raise SystemExit(f"{old['quest_id']}: source line {missing} has no stored translation; select the quest again to translate it")
    return quests


VECTOR_FEATURES = {
    "player name": "Forename", "multi-line": "\n", "ellipsis": "…", "quotes": "[「『]",
    "full-width punctuation": "[！？]", "symbols and digits": "[～─0-9０-９]", "single line": r"\A[^\n]*\Z",
}


def write_vectors(quests):
    """Test vectors for the C# port of key_ja: per feature, the first line of each quest that has it."""
    picked = {}
    for pattern in VECTOR_FEATURES.values():
        for quest in quests:
            row = next((r for r in quest["rows"] if re.search(pattern, r["text_ja"]) and r["text_id"] not in picked), None)
            if row:
                picked[row["text_id"]] = row
    vectors = []
    for row in picked.values():
        covers = [name for name, pattern in VECTOR_FEATURES.items() if re.search(pattern, row["text_ja"])]
        vectors.append({"text_id": row["text_id"], "covers": covers, "text_ja": row["text_ja"], "key_ja": row["key_ja"]})
        if "Forename" in row["text_ja"]:
            vectors.append({"text_id": row["text_id"], "covers": ["datamining Player form"], "text_ja": row["text_ja"].replace("Forename", "Player"), "key_ja": row["key_ja"]})
    vectors += [{"text_id": None, "covers": ["synthetic edge case"], "text_ja": text, "key_ja": key_ja(text)} for text in EDGE_CASES]
    write_atomic(OUT / VECTORS_NAME, dump({"rules": "see key_ja.py", "vectors": vectors}))


def probe_overhead(call):
    _, usage = call("Reply OK.", "OK", EFFORT, MODEL)
    log_call({"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "run_id": None, "quest": None, "stage": "overhead_probe", "attempt": 1, "effort": EFFORT, **usage, "error": None})


def total_input(entry):
    return entry["input_tokens"] + entry["cache_write_tokens"] + entry["cache_read_tokens"]


def write_report(quests):
    log = [json.loads(line) for line in COST_LOG.read_text(encoding="utf-8").splitlines()] if COST_LOG.exists() else []
    probes = [e for e in log if e["stage"] == "overhead_probe" and e["backend"] == "cli"]
    overhead = total_input(probes[-1]) if probes else None

    def api_estimate(entries):
        if overhead is None or any(e["backend"] != "cli" for e in entries):
            return None
        return sum((total_input(e) - overhead) * USD_PER_MTOK["input"] + e["output_tokens"] * USD_PER_MTOK["output"] for e in entries) / 1e6

    def cost_row(label, entries):
        est = api_estimate(entries)
        return (
            f"| {label} | {'+'.join(sorted({e['backend'] for e in entries}))} | {len(entries)} | {sum(e['input_tokens'] for e in entries)} "
            f"| {sum(e['cache_write_tokens'] for e in entries)} | {sum(e['cache_read_tokens'] for e in entries)} "
            f"| {sum(e['output_tokens'] for e in entries)} | {sum(e['thinking_tokens'] or 0 for e in entries)} "
            f"| {sum(e['cost_usd'] for e in entries):.6f} | {'n/a' if est is None else f'{est:.6f}'} |\n"
        )

    attributions = [json.loads(path.read_text(encoding="utf-8")) for path in sorted((OUT / attribution.ATTRIBUTION_DIR).glob("VoiceMan_*.json"))]
    md = ["# Haiku translation pipeline report\n\n", f"Model `{MODEL}`, effort `{EFFORT}`. Every number below is computed from `out/cost_log.jsonl`, `out/review/<quest_id>.json`, `out/coverage/<quest_id>.json` and the sources. `out/<quest_id>.json` is the plugin-facing file.\n\n"]
    md.append("## Cost\n\nPer quest: the calls of the runs that produced the current output (translate + review, retries included). Attributing a cutscene file to quests takes one call per vote, listed under its file name.\n\n")
    md.append("| quest | backend | calls | input tok | cache-write tok | cache-read tok | output tok | of which thinking | cost USD | est. API-path USD |\n|---|---|---|---|---|---|---|---|---|---|\n")
    current = []
    for q in quests:
        entries = [e for e in log if e["run_id"] in q["run_ids"]]
        current += entries
        md.append(cost_row(f"{q['quest_id']} ({len(q['rows'])} lines)", entries))
    for record in attributions:
        entries = [e for e in log if e["run_id"] in record["run_ids"]]
        current += entries
        md.append(cost_row(f"{record['file'].split('/')[-1]} attribution ({record['rows']} rows, {len(record['votes'])} votes)", entries))
    md.append(cost_row("**total, current outputs**", current))
    md.append(f"\nAll logged calls, including probes, rejected attempts and superseded runs: {len(log)} calls, ${sum(e['cost_usd'] for e in log):.6f}.\n")
    md.append("\n### Every logged run\n\nSame quest, same prompt: the spread between rows is run-to-run variance, mostly thinking tokens.\n\n")
    md.append("| quest | run | stages | effort | output tok | of which thinking | cost USD | current output |\n|---|---|---|---|---|---|---|---|\n")
    for run_id in dict.fromkeys(e["run_id"] for e in log if e["run_id"]):
        entries = [e for e in log if e["run_id"] == run_id]
        md.append(
            f"| {entries[0]['quest']} | {run_id} | {'+'.join(e['stage'] for e in entries)} | {entries[0]['effort']} "
            f"| {sum(e['output_tokens'] for e in entries)} | {sum(e['thinking_tokens'] or 0 for e in entries)} "
            f"| {sum(e['cost_usd'] for e in entries):.6f} | {'yes' if any(run_id in q['run_ids'] for q in quests) or any(run_id in a['run_ids'] for a in attributions) else ''} |\n"
        )
    if overhead is not None:
        md.append(
            f"\nCLI overhead: a probe with a 3-word prompt was billed {overhead} input tokens, so about that many tokens per call are the CLI harness, "
            "and the CLI writes the whole prompt to the 1-hour cache (2x the input price). "
            "The API-path estimate removes the harness tokens and prices all input at $0.10/MTok and the same output tokens at $0.50/MTok, without caching. It is an estimate; the API path was not run.\n"
        )

    md.append("\n## Flags\n\nLines with at least one flag per check. `human` runs the same deterministic lints on the human reference as a noise baseline (the `name` lint is skipped there because the team writes names in Thai, not the English of terms.json).\n\n")
    checks = ["empty", "forename", "name", "pronoun", "script", "length", "review"]
    md.append("| quest | lines | any flag | " + " | ".join(checks) + " | human: any lint |\n|---|---|---|" + "---|" * (len(checks) + 1) + "\n")
    for q in quests:
        per_check = [sum(any(f["check"] == c for f in r["flags"]) for r in q["rows"]) for c in checks]
        baseline = sum(bool(lint(r, r["text_human"], Terms({}))) for r in q["rows"] if r["text_human"])
        md.append(f"| {q['quest_id']} | {len(q['rows'])} | {sum(bool(r['flags']) for r in q['rows'])} | " + " | ".join(map(str, per_check)) + f" | {baseline} |\n")

    md.append("\n## Coverage\n\nFrom `out/coverage/<quest_id>.json`. Every row of every source file is translated or skipped with a reason; every key of the team's files is in the output or listed with a reason.\n\n")
    md.append("| quest | commit | source file | rows | translated | skipped by reason |\n|---|---|---|---|---|---|\n")
    for q in quests:
        for entry in q["coverage"]["sources"]:
            reasons = ", ".join(f"{reason} {count}" for reason, count in entry["skipped"].items()) or "none"
            md.append(f"| {q['quest_id']} | `{q['datamining_commit'][:12]}` | {entry['file']} | {entry['rows']} | {entry['translated']} | {reasons} |\n")
    md.append("\n| quest | team files | team keys | in output | not in output by reason |\n|---|---|---|---|---|\n")
    for q in quests:
        team = q["coverage"]["team"]
        reasons = ", ".join(f"{reason} {count}" for reason, count in team["not_in_output"].items()) or "none"
        md.append(f"| {q['quest_id']} | {', '.join(team['files']) or 'none'} | {team['keys']} | {team['in_output']} | {reasons} |\n")
    md.append("\n## Cutscene attribution\n\nWhich rows of a voiced-cutscene file belong to which quest, from `out/attribution/<file>.json`. Row ranges are inclusive.\n\n")
    for record in attributions:
        starts = record["starts"]
        blocks = [
            f"{start['quest'] or 'unattributed'} {start['row']}-{(starts[n + 1]['row'] if n + 1 < len(starts) else record['rows']) - 1}"
            for n, start in enumerate(starts)
        ]
        md.append(f"- `{record['file']}` ({record['rows']} rows; window of {len(record['window'])} quests from {record['window_method']}; votes split on {record['rows_votes_split_on']} rows): " + "; ".join(blocks) + ".\n")
    md.append(f"\n## Names\n\n`terms.json` holds {len(load_terms())} Japanese names with their official English, which translations keep (`name` flags above).\n")

    by_key = {}
    for q in quests:
        for row in q["rows"]:
            by_key.setdefault(row["key_ja"], []).append(row)
    shared = {k: rows for k, rows in by_key.items() if k and len(rows) > 1}
    vector_count = len(json.loads((OUT / VECTORS_NAME).read_text(encoding="utf-8"))["vectors"])
    md.append(
        f"\n## Japanese keys\n\n{sum(map(len, by_key.values()))} rows, {len(by_key)} distinct `key_ja`. "
        f"Rows with an empty key: {[r['text_id'] for r in by_key.get('', [])] or 'none'}. "
        f"Keys shared by more than one row: {len(shared) or 'none'}. `{VECTORS_NAME}` holds {vector_count} vectors.\n"
    )
    for rows in shared.values():
        same_ja = len({r["text_ja"] for r in rows}) == 1
        same_en = len({r["key"] for r in rows}) == 1
        md.append(
            f"\n- `{rows[0]['key_ja']}`: {', '.join(r['text_id'] for r in rows)}. Japanese text {'identical' if same_ja else 'differs'}; "
            f"English key {'identical' if same_en else 'differs'}; human Thai {'identical' if len({r['text_human'] for r in rows}) == 1 else 'differs'}; "
            f"Haiku Thai {'identical' if len({r['text_haiku'] for r in rows}) == 1 else 'differs'}.\n"
        )

    md.append("\n## Samples\n\nThree lines per quest: most flags first, then longest.\n")
    for q in quests:
        md.append(f"\n### {q['quest_id']}\n")
        for row in sorted(q["rows"], key=lambda r: (-len(r["flags"]), -len(r["text_en"])))[:3]:
            flags = "; ".join(f"{f['check']}: {f['detail']}" for f in row["flags"]) or "none"
            md.append(
                f"\n**{row['speaker']}** (`{row['text_id']}`)\n\n- JA: {' '.join(row['text_ja'].split())}\n- EN: {row['text_en']}\n"
                f"- Human: {row['text_human'] or '(no team translation)'}\n- Haiku: {row['text_haiku']}\n- Flags: {flags}\n"
            )
    write_atomic(OUT / "report.md", "".join(md))


def attribute_file(call, source, quest_table, path, window, method, model=None, folder=attribution.ATTRIBUTION_DIR):
    """The stored attribution of one cutscene file, made with model calls when the file has too few votes.
    Keyed by the file's git blob, so every commit and every selection mode share one attribution."""
    store = OUT / folder / f"{path.split('/')[-1]}.json"
    blob = source.blob(f"en/{path}")
    rows = gamedata.read_rows(source, path)
    record = json.loads(store.read_text(encoding="utf-8")) if store.exists() else {}
    if record.get("blob") != blob:
        record = {
            "file": path, "blob": blob, "datamining_commit": source.commit, "rows": len(rows), "window_method": method,
            "window": window, "model": (model or attribution.ATTRIBUTION_MODEL) if window else None, "run_ids": [], "votes": [],
        }
    missing = attribution.ATTRIBUTION_VOTES - len(record["votes"]) if record["window"] else 0
    if not record["window"]:
        record["votes"] = [[{"quest": None, "row": 0}]]
    elif missing > 0:
        run = {"run_id": new_run_id(), "quest": path.split("/")[-1]}
        prompt = attribution.boundary_prompt(source, quest_table, record["window"], rows)
        for _ in range(missing):
            record["votes"].append(ask(
                call, run, "attribute", attribution.BOUNDARY_SYSTEM, prompt,
                lambda reply: attribution.parse_starts(reply, record["window"], len(rows)),
                effort=attribution.ATTRIBUTION_EFFORT, model=record["model"],
            ))
        record["run_ids"].append(run["run_id"])
    elif "starts" in record:
        return record
    record["starts"], record["rows_votes_split_on"] = attribution.majority(record["votes"], len(rows))
    store.parent.mkdir(parents=True, exist_ok=True)
    write_atomic(store, dump(record))
    return record


def resolve_quest(quest_table, wanted):
    if wanted in quest_table:
        return wanted
    named = [q for q in quest_table.values() if q["name"].lower() == wanted.lower() or slug(q["name"]) == slug(wanted)]
    named = [q for q in named if q["msq"]] or named
    if len(named) != 1:
        raise SystemExit(f"quest {wanted!r}: {len(named)} matches {[q['stem'] for q in named]}; give the stem")
    return named[0]["stem"]


def windows_for(source, quest_table, expansion):
    """Lexical windows of one expansion at one commit, computed once and kept in out/attribution/windows.json."""
    path = OUT / attribution.ATTRIBUTION_DIR / "windows.json"
    stored = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    name = f"{source.commit}:{expansion}"
    if name not in stored:
        stored[name] = attribution.lexical_windows(source, quest_table, expansion)
        path.parent.mkdir(parents=True, exist_ok=True)
        write_atomic(path, dump(stored))
    return stored[name]


def select(args, call):
    """[(stem, selection)] for the request. Attributes the cutscene files it needs, which may call the model."""
    source, quest_table = source_at(args.commit or args.at)
    wanted = [resolve_quest(quest_table, name) for name in args.quest]

    def attribute(path, window, method):
        return attribute_file(call, source, quest_table, path, window, method)

    if args.commit:
        changed = source.changed()
        stems = [name.split("/")[-1] for name in changed if name.startswith("quest/")]
        other = sorted(stem for stem in stems if stem in quest_table and not quest_table[stem]["msq"])
        msq = sorted((stem for stem in stems if stem in quest_table and quest_table[stem]["msq"]), key=lambda stem: gamedata.play_order(quest_table[stem]))
        files = [name for name in changed if name.startswith("cut_scene/")]
        print(f"commit {source.commit[:12]} changed {len(stems)} quest files and {len(files)} cutscene files; main scenario: {msq}; not selected (not main scenario): {other}")
        outside = [stem for stem in wanted if stem not in msq]
        if outside:
            raise SystemExit(f"not a main-scenario quest changed by {source.commit[:12]}: {outside}")
        window = attribution.candidates(quest_table, msq)
        for path in files:
            attribute(path, window, "main-scenario quests changed in the same commit")
        return [(stem, {"mode": "commit", "commit": source.commit, "cutscene_candidates": files}) for stem in wanted or msq]

    if args.patch:
        major, minor = args.patch.split(".")
        folder = f"cut_scene/{int(major):02d}{minor[:1]}"
        expansion = int(major) - 2
        windows = windows_for(source, quest_table, expansion)
        groups = set()
        for path in source.files(folder):
            owners = attribution.by_row(attribute(path, windows[path], "lexical alignment of the expansion"))
            groups |= {owner[:6] for owner in owners if owner}
        patch_quests = sorted((q for q in quest_table.values() if q["msq"] and q["stem"][:6] in groups), key=gamedata.play_order)
        wanted += [q["stem"] for q in patch_quests if q["stem"] not in wanted]
        print(f"patch {args.patch}: {folder} holds lines of stem groups {sorted(groups)}; {len(wanted)} quests")

    selected = []
    for stem in wanted:
        windows = windows_for(source, quest_table, quest_table[stem]["expansion"])
        files = [path for path, window in windows.items() if stem in window]
        for path in files:
            attribute(path, windows[path], "lexical alignment of the expansion")
        selected.append((stem, {"mode": "patch" if args.patch else "quest", "commit": source.commit, "cutscene_candidates": files}))
    return selected


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--commit", help="datamining commit of a patch: select the main-scenario quests it changed")
    parser.add_argument("--quest", action="append", default=[], help="quest name or stem (repeatable)")
    parser.add_argument("--patch", help="patch number X.Y: select the quests of the cut_scene/0XY files")
    parser.add_argument("--at", default="HEAD", help="datamining commit to read for --quest and --patch (default HEAD)")
    parser.add_argument("--force", action="store_true", help="translate the selected quests again")
    parser.add_argument("--list", action="store_true", help="print the selection and stop")
    parser.add_argument("--probe", action="store_true", help="log one tiny call to measure per-call overhead")
    args = parser.parse_args()
    call = call_api if os.environ.get("ANTHROPIC_API_KEY") else call_cli
    OUT.mkdir(exist_ok=True)
    if args.probe:
        probe_overhead(call)
    selected = select(args, call) if args.commit or args.quest or args.patch else []
    for stem, selection in selected:
        print(f"selected {stem} ({selection['mode']}), cutscene files examined: {selection['cutscene_candidates']}")
    if args.list:
        return
    for stem, selection in selected:
        run_quest(stem, call, args.force, selection)
    quests = refresh()
    write_vectors(quests)
    write_report(quests)
    print(f"report: {OUT / 'report.md'}")


if __name__ == "__main__":
    main()
