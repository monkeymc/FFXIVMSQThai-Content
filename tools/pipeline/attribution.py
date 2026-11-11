"""Which quest does each row of a voiced-cutscene file belong to?

No CSV column links a VoiceMan row to a cutscene or a quest. What the data does show (measured against the
team's per-quest files for patches 3.0-7.5, see check_attribution.py): one file holds the cutscene lines of
consecutive main-scenario quests, back to back, in quest order. So attribution is a segmentation problem,
solved in two steps:

1. window: which quests can the file hold? Either the main-scenario quests changed in the same commit, or the
   result of a deterministic lexical alignment of the whole expansion (every VoiceMan row against every
   main-scenario quest's own text, monotone in quest order), widened to whole stem groups. The alignment is
   right about the neighbourhood and wrong about the exact boundaries, so it only picks candidates. Either
   way the window keeps only quests that Quest.csv links to a cutscene, or whose 50 script parameters are
   all used so that the list may be cut short.
2. boundaries: a model call returns the first row of each quest's block. The pipeline asks ATTRIBUTION_VOTES
   times, validates each reply with parse_starts, gives each row to the quest most replies name, and stores
   the result, so a file is attributed once.

Rows the model gives to no quest stay unattributed and are recorded as such.
"""
import math
import re
from collections import Counter

import gamedata

ATTRIBUTION_DIR = "attribution"
ATTRIBUTION_MODEL = "claude-haiku-5-5"
ATTRIBUTION_EFFORT = "high"
# One reply misplaces whole blocks now and then, differently each time, so each row goes to the quest most replies give it.
ATTRIBUTION_VOTES = 3
WORD = re.compile(r"[a-z']{3,}")
SMOOTHING = 20.0
EVIDENCE_CAP = 5.0
CONTEXT_LINES = 20

BOUNDARY_SYSTEM = """You align voiced cutscene dialogue from Final Fantasy XIV to the quests it plays in.

You get (1) a list of consecutive main-scenario quests in play order, each with its journal entries (a summary of what happens in that quest, in order) and some of its own non-cutscene dialogue, and (2) the rows of one voiced-cutscene text file. The file holds the cutscene lines of these quests back to back, in the same order as the quests: all lines of one quest, then all lines of the next. Each quest is listed with the number of cutscenes it plays. A quest with cutscenes usually has rows in this file, even if only a few; it has none when its cutscenes are unvoiced or when its lines sit in the neighbouring file, which is common for the first and last quests of the list. Rows marked (unused) are leftovers; ignore them when deciding.

Find where each quest's block of rows begins. Use scene changes (a new place, a new cast, a new topic) and match each scene to the quest whose journal describes it. A quest's non-cutscene dialogue happens right before and after its cutscenes, so it shows who is present and what is being discussed.

Return only a JSON object, no code fence, no commentary:
{"starts": [{"quest": "<quest id>", "row": <first row number of that quest's block>}, ...]}
- List only quests that have at least one row, in the given quest order, with strictly increasing row numbers.
- The first entry must have the first row number of the file. Every row belongs to the block of the nearest entry at or before it.
- A block that belongs to none of the listed quests (a trailer, a run of unused leftovers) is listed with "quest": null."""


def expansion_of(path):
    """cut_scene/031/VoiceMan_03100 -> 1: folder 02x is A Realm Reborn (Quest.Expansion 0), 03x Heavensward, ..."""
    return int(path.split("/")[1][:2]) - 2


def main_scenario(quest_table, expansion):
    """Main-scenario quests of an expansion in play order."""
    return sorted((q for q in quest_table.values() if q["msq"] and q["expansion"] == expansion), key=gamedata.play_order)


def candidates(quest_table, stems):
    """The quests among `stems` that can own cutscene lines, in play order."""
    return [quest["stem"] for quest in sorted((quest_table[stem] for stem in stems), key=gamedata.play_order) if quest["may_have_cutscenes"]]


def tokens(text):
    return set(WORD.findall(text.lower()))


def monotone_segments(scores, count):
    """Best assignment of rows to `count` ordered states where the state never decreases. scores[row][state]."""
    best, backs = [0.0] * count, []
    for row in scores:
        choice, lead, new = [0] * count, 0, [0.0] * count
        for state in range(count):
            if best[state] > best[lead]:
                lead = state
            choice[state], new[state] = lead, best[lead] + row[state]
        best = new
        backs.append(choice)
    state = max(range(count), key=best.__getitem__)
    out = [0] * len(scores)
    for index in range(len(scores) - 1, -1, -1):
        out[index] = state
        state = backs[index][state]
    return out


def lexical_windows(source, quest_table, expansion):
    """{VoiceMan path: [quest stems]}: the quests of the stem groups a file's rows align to that can own
    cutscene lines. No model, same answer every run."""
    quests = main_scenario(quest_table, expansion)
    files = [path for path in source.files("cut_scene") if expansion_of(path) == expansion]
    if not quests or not files:
        return {path: [] for path in files}
    counts = []
    for quest in quests:
        count = Counter()
        for row in gamedata.read_rows(source, gamedata.quest_path(quest["stem"])):
            if row["text_en"].strip():
                count.update(tokens(row["text_en"]))
                if row["speaker"]:
                    count[f"speaker:{row['speaker']}"] += 1
        counts.append(count)
    background = sum(counts, Counter())
    total = sum(background.values())
    sizes = [sum(count.values()) for count in counts]

    def evidence(row):
        found = [token for token in tokens(row["text_en"]) if token in background]
        if row["speaker"] and f"speaker:{row['speaker']}" in background:
            found.append(f"speaker:{row['speaker']}")
        out = []
        for count, size in zip(counts, sizes):
            score = 0.0
            for token in found:
                prior = background[token] / total
                ratio = math.log((count.get(token, 0) + SMOOTHING * prior) / (size + SMOOTHING) / prior)
                score += max(-EVIDENCE_CAP, min(EVIDENCE_CAP, ratio))
            out.append(score)
        return out

    rows = [(path, row) for path in files for row in gamedata.read_rows(source, path)]
    states = monotone_segments([evidence(row) for _, row in rows], len(quests))
    group = lambda quest: quest["stem"][:7]
    windows = {}
    for path in files:
        used = [state for (row_path, row), state in zip(rows, states) if row_path == path and row["text_en"].strip()]
        groups = {group(quests[state]) for state in range(min(used), max(used) + 1)} if used else set()
        windows[path] = candidates(quest_table, [quest["stem"] for quest in quests if group(quest) in groups])
    return windows


def quest_context(source, quest):
    journal, talk = [], []
    for row in gamedata.read_rows(source, gamedata.quest_path(quest["stem"])):
        text = " ".join(row["text_en"].split())
        if not text:
            continue
        if row["kind"] == "journal":
            journal.append(f"- {text}")
        elif row["kind"] == "dialogue":
            talk.append(f"{row['speaker']}: {text[:140]}")
    if len(talk) > 2 * CONTEXT_LINES:
        talk = talk[:CONTEXT_LINES] + ["..."] + talk[-CONTEXT_LINES:]
    linked = f"{len(quest['cutscenes'])} cutscenes" if quest["cutscenes"] else "cutscene count unknown"
    return f"### {quest['stem']} \"{quest['name']}\" ({linked})\nJournal:\n" + "\n".join(journal) + "\nNon-cutscene dialogue:\n" + "\n".join(talk)


def boundary_prompt(source, quest_table, window, rows):
    lines = []
    for row in rows:
        text = " ".join(row["text_en"].split()) or "(unused)"
        lines.append(f"{row['row']}\t{row['shown_as'] or row['speaker'] or row['kind']}\t{text}")
    return (
        "Quests in play order:\n\n" + "\n\n".join(quest_context(source, quest_table[stem]) for stem in window)
        + f"\n\nRows of {rows[0]['file']} (row number, speaker, text):\n" + "\n".join(lines)
    )


def parse_starts(reply, window, row_count):
    starts = [(entry["quest"], int(entry["row"])) for entry in reply["starts"]]
    named = [quest for quest, _ in starts if quest is not None]
    unknown = [quest for quest in named if quest not in window]
    positions = [window.index(quest) for quest in named if quest in window]
    rows = [row for _, row in starts]
    if unknown:
        raise ValueError(f"quests not in the list: {unknown}")
    if positions != sorted(set(positions)):
        raise ValueError("quests must appear once each, in the given order")
    if not rows or rows[0] != 0 or rows != sorted(set(rows)) or rows[-1] >= row_count:
        raise ValueError(f"rows must start at 0, increase strictly and stay below {row_count}")
    return [{"quest": quest, "row": row} for quest, row in starts]


def expand(starts, row_count):
    """Quest stem (or None) of every row, from block starts."""
    out = []
    for index, start in enumerate(starts):
        end = starts[index + 1]["row"] if index + 1 < len(starts) else row_count
        out += [start["quest"]] * (end - start["row"])
    return out


def by_row(record):
    return expand(record["starts"], record["rows"])


def majority(votes, row_count):
    """(starts, rows the votes split on): each row goes to the quest most votes give it, the first vote on a tie."""
    owners, split = [], 0
    for row in zip(*(expand(vote, row_count) for vote in votes)):
        counts = Counter(row)
        owners.append(max(row, key=lambda quest: (counts[quest], -row.index(quest))))
        split += len(counts) > 1
    starts = [{"quest": quest, "row": index} for index, quest in enumerate(owners) if index == 0 or quest != owners[index - 1]]
    return starts, split
