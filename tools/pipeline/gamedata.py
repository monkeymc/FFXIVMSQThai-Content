"""Game data at one commit of xivapi/ffxiv-datamining: quests, text rows, and why a row is or is not translated.

A text row is one CSV row of a quest file (csv/<lang>/quest/NNN/<Stem>.csv) or of a voiced-cutscene file
(csv/<lang>/cut_scene/NNN/VoiceMan_NNNNN.csv). `skip` is None for a row that is translated, else the reason
it is not. Reasons that depend on which quest is being built (other_quest, unattributed, duplicate_key) are
added by the pipeline; the ones here depend on the row alone.
"""
import csv
import os
import io
import re
import subprocess
from pathlib import Path

from key_ja import key_ja

REPO = Path(os.environ.get("FFXIV_DATAMINING", Path(__file__).resolve().parent / "dl/ffxiv-datamining"))
# JournalGenre rows 1-15 are the main scenario, "Seventh Umbral Era" to "Winter's Prelude".
MSQ_GENRES = range(1, 16)

# First match on the label after TEXT_<STEM>_ wins; no match is spoken dialogue.
QUEST_KINDS = [
    (r"SEQ_\d+$", "journal"),
    (r"TODO_\d+$", "todo"),
    (r"SYSTEM_", "system"),
    (r"[QA]\d+_", "choice"),
    (r"QIB_", "duty_text"),
    (r"POP_?MESSAGE|ACCESS_MESSAGE|INSTANCE_BATTLE", "system"),
]
# The same for the label after TEXT_VOICEMAN_<NNNNN>_.
CUTSCENE_KINDS = [
    (r"[QA]\d+_", "choice"),
    (r".*_SYSTEM(_NONE_VOICE)?$", "system"),
]
SHOWN_AS = re.compile(r"\A\(-(.*?)-\)")


class Source:
    """Read-only view of the datamining repository at one commit."""

    def __init__(self, commit="HEAD", repo=REPO):
        self.repo = repo
        self.commit = self._git("rev-parse", f"{commit}^{{commit}}").strip()
        self._tables = {}

    def _git(self, *args):
        return subprocess.run(["git", "-C", str(self.repo), *args], capture_output=True, text=True, check=True).stdout

    def table(self, name):
        """Rows of csv/<name>.csv, or [] when the commit has no such file."""
        if name not in self._tables:
            try:
                text = self._git("show", f"{self.commit}:csv/{name}.csv")
            except subprocess.CalledProcessError:
                text = ""
            self._tables[name] = list(csv.reader(io.StringIO(text.removeprefix("﻿"), newline="")))
        return self._tables[name]

    def blob(self, name):
        return self._git("rev-parse", f"{self.commit}:csv/{name}.csv").strip()

    def files(self, folder):
        """Names (no csv/<lang>/ prefix, no .csv) of the English files under csv/en/<folder>/."""
        out = self._git("ls-tree", "-r", "--name-only", self.commit, f"csv/en/{folder}/")
        return sorted(line[len("csv/en/"):-len(".csv")] for line in out.splitlines() if line.endswith(".csv"))

    def changed(self):
        """Names changed against the first parent, in either language."""
        out = self._git("diff", "--name-only", f"{self.commit}^1", self.commit)
        names = (re.fullmatch(r"csv/(?:en|ja)/(.+)\.csv", line) for line in out.splitlines())
        return sorted({match.group(1) for match in names if match})


def quests(source):
    """{stem: quest} for every named quest. `cutscenes` is what Quest.csv links. The sheet holds 50 script
    parameters per quest, so a quest that fills all 50 can have cutscenes that are not listed;
    `may_have_cutscenes` is False only when the list is complete and empty."""
    paths = {row[0]: row[1] for row in source.table("en/Cutscene")[1:] if row[1]}
    table = source.table("en/Quest")
    column = {name: index for index, name in enumerate(table[0])}
    out = {}
    for row in table[1:]:
        if not row[column["Name"]]:
            continue
        instructions = [(row[2 + 2 * n].upper(), row[3 + 2 * n]) for n in range(50)]
        genre = int(row[column["JournalGenre"]])
        cutscenes = [
            {"id": int(arg), "path": paths[arg]} for name, arg in instructions
            if "CUT" in name and "LCUT" not in name and "LEVEL_CUT" not in name and arg in paths
        ]
        out[row[column["Id"]]] = {
            "stem": row[column["Id"]], "quest_row": int(row[0]), "name": row[column["Name"]].strip(),
            "expansion": int(row[column["Expansion"]]), "genre": genre, "msq": genre in MSQ_GENRES,
            "cutscenes": cutscenes, "may_have_cutscenes": bool(cutscenes) or all(name for name, _ in instructions),
        }
    return out


def quest_path(stem):
    return f"quest/{stem.split('_')[1][:3]}/{stem}"


def msq_paths(source):
    """The main-scenario corpus: the quest file of every MSQ quest, then every voiced-cutscene file."""
    return [quest_path(stem) for stem, quest in quests(source).items() if quest["msq"]] + source.files("cut_scene")


def play_order(quest):
    """HeaVna101 < HeaVna102 < HeaVnb101: the stem's letters are the patch group, its digits the order in it."""
    return quest["stem"][:6].lower(), quest["stem"][6:9]


def placeholders(text):
    return re.sub(r"Player(?![a-z])", "Forename", text.replace("Player Player", "Forename Surname"))


def make_key(text_en):
    return re.sub("[^a-z]", "", text_en.lower())


def label_kind(path, text_id):
    """(kind, speaker) from a row label. kind is 'dialogue' or a skip reason."""
    if path.startswith("quest/"):
        rest = re.sub(r"\ATEXT_[A-Z0-9]+_\d+_", "", text_id.upper())
        kinds = QUEST_KINDS
        speaker = re.sub(r"(_BATTLETALK.*|(_\d+)+)\Z", "", rest)
    else:
        rest = re.sub(r"\ATEXT_VOICEMAN_\d+_", "", text_id.upper())
        kinds = CUTSCENE_KINDS
        speaker = re.sub(r"\A[A-Z]?\d+_|_NONE_VOICE\Z", "", rest)
    for pattern, kind in kinds:
        if re.match(pattern, rest):
            return kind, None
    return "dialogue", speaker.title()


def make_row(path, index, text_id, raw_en, raw_ja):
    kind, speaker = label_kind(path, text_id)
    shown = SHOWN_AS.match(raw_en)
    text_en = placeholders(SHOWN_AS.sub("", raw_en))
    text_ja = placeholders(SHOWN_AS.sub("", raw_ja))
    key = make_key(text_en)
    if "未使用" in raw_ja:
        skip = "unused"
    elif "翻訳不要" in raw_ja:
        skip = "not_for_translation"
    elif not raw_en.strip():
        skip = "empty"
    elif kind != "dialogue":
        skip = kind
    elif "SHOULD NOT DISPLAY" in raw_en:
        skip = "not_displayed"
    elif not key:
        skip = "no_key"
    else:
        skip = None
    return {
        "file": path, "row": index, "text_id": text_id, "kind": kind, "speaker": speaker,
        "shown_as": shown.group(1) if shown else None,
        "text_en": text_en, "text_ja": text_ja, "key": key, "key_ja": key_ja(text_ja), "skip": skip,
    }


def read_rows(source, path):
    """Every row of one text file, English and Japanese paired by label."""
    en, ja = source.table(f"en/{path}"), source.table(f"ja/{path}")
    if not en:
        raise SystemExit(f"{path}: no English file at commit {source.commit[:12]}")
    if [row[1] for row in en] != [row[1] for row in ja]:
        raise SystemExit(f"{path}: en and ja row labels differ at commit {source.commit[:12]}")
    return [make_row(path, index, e[1], e[2], j[2]) for index, (e, j) in enumerate(zip(en, ja))]
