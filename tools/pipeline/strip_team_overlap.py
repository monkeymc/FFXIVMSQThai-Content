"""Remove th/ rows whose plugin keys collide with haiku/ rows (--apply), or report collisions."""
import json, re, sys
from pathlib import Path

ROOT = Path(sys.argv[1])
SE = re.compile(r"[\x02][\s\S]{1,4}[\x03]|[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]")
SLASH = re.compile(r"\b(\w+)\s*/\s*(\w+)\b")
TAG = re.compile(r"^\(-.+?-\)")


def pure(s):
    k = "".join(c.lower() for c in SE.sub("", s) if c.isascii() and c.isalnum())
    for w in ("forenamesurname", "forename", "surname", "playerplayer", "player"):
        k = k.replace(w, "")
    return k


def variants(text):
    clean = SE.sub("", text).replace("*", "")
    results = [clean]
    if TAG.sub("", clean, count=1) != clean:
        results.append(TAG.sub("", clean, count=1))
    for m in SLASH.finditer(clean):
        results = [r.replace(m.group(0), g) for r in results for g in (m.group(1), m.group(2))]
    return {k for k in map(pure, results) if k}


def keys(d):
    return variants(d.get("text_en") or "") | ({d["key"]} if d.get("key") else set())


def loaded(d):
    return bool((d.get("text_en") or "").strip() and (d.get("text") or "").strip())


TEAM_FILES = ("7.56/a-winters-dream.json", "7.56/cutscenes.json", "3.x/as-goes-light-so-goes-darkness.json")
TARGETS = {f"{base}/{name}" for base in ("th", "editor/public/th") for name in TEAM_FILES}
haiku = set()
for f in sorted((ROOT / "haiku").glob("*.json")):
    for d in json.loads(f.read_text())["dialogues"]:
        haiku |= keys(d)

total = 0
for f in sorted([*(ROOT / "th").rglob("*.json"), *(ROOT / "editor/public/th").rglob("*.json")]):
    raw = f.read_text()
    data = json.loads(raw)
    if "dialogues" not in data:
        continue
    hit = [d for d in data["dialogues"] if loaded(d) and keys(d) & haiku]
    targeted = str(f.relative_to(ROOT)) in TARGETS
    if not hit:
        continue
    total += len(hit)
    print(f"{'REMOVE' if targeted else 'keep  '} {f.relative_to(ROOT)}: {len(hit)} of {len(data['dialogues'])} rows collide")
    if "--apply" in sys.argv and targeted:
        data["dialogues"] = [d for d in data["dialogues"] if d not in hit]
        f.write_text(json.dumps(data, ensure_ascii=False, indent=2) + ("\n" if raw.endswith("\n") else ""))
print(f"haiku keys: {len(haiku)}, colliding team rows: {total}")
