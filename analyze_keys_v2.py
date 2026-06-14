#!/usr/bin/env python3
import os
import csv
import json
import re
import glob
from pathlib import Path
from collections import defaultdict

def to_pure_alphanumeric_key(text):
    if not text:
        return ""
    no_payload = re.sub(r'[\x02].{1,4}[\x03]|[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
    # Strip asterisks
    no_payload = no_payload.replace('*', '')
    
    chars = []
    for c in no_payload:
        if ('A' <= c <= 'Z') or ('a' <= c <= 'z') or ('0' <= c <= '9'):
            chars.append(c.lower())
    key = "".join(chars)
    
    # Strip player name placeholders to align translation files (Forename/Surname)
    # with raw datamining files (Player/Player Player/blanks)
    key = key.replace('forenamesurname', '')
    key = key.replace('forename', '')
    key = key.replace('surname', '')
    key = key.replace('playerplayer', '')
    key = key.replace('player', '')
    
    return key

def generate_key_variants(text_en):
    # Standard cleanup of FFXIV payload
    text = re.sub(r'[\x02].{1,4}[\x03]|[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text_en)
    text = text.replace('*', '') # Remove asterisks (e.g. *she* -> she)
    
    # Slash pronoun combinations
    pattern = re.compile(r'\b(\w+)\s*/\s*(\w+)\b')
    matches = list(pattern.finditer(text))
    if not matches:
        return [to_pure_alphanumeric_key(text)]
        
    variants = [text]
    for match in matches:
        full_match = match.group(0)
        left = match.group(1)
        right = match.group(2)
        
        new_variants = []
        for v in variants:
            new_variants.append(v.replace(full_match, left))
            new_variants.append(v.replace(full_match, right))
        variants = new_variants
        
    return list(set(to_pure_alphanumeric_key(v) for v in variants))

def extract_speaker(key):
    parts = key.split('_')
    if len(parts) > 1:
        last_part = parts[-1]
        if not last_part.isdigit() and last_part:
            return last_part
    return ""

def run_analysis_v2(workspace_dir):
    content_dir = Path(workspace_dir) / "th"
    datamining_dir = Path("/home/chatja/fun/FFXIVMSQThai/ffxiv-datamining")
    web_dir = Path(workspace_dir) / "web"
    web_dir.mkdir(exist_ok=True)

    if not content_dir.exists() or not datamining_dir.exists():
        print(f"Required directories not found! Content: {content_dir.exists()}, Datamining: {datamining_dir.exists()}")
        return

    # 1. Load translated dialogues
    print("Loading translated dialogues from content/...")
    json_files = glob.glob(os.path.join(content_dir, "**", "*.json"), recursive=True)
    translated_db = {} # pure_key -> {text_en, text_th, quests, files}
    total_json_dialogues = 0

    for file_path_str in json_files:
        file_path = Path(file_path_str)
        rel_file = file_path.relative_to(workspace_dir)
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                quest_id = data.get("quest_id", "unknown")
                for d in data.get("dialogues", []):
                    en = d.get("text_en", "").strip()
                    th = d.get("text", "").strip()
                    if not en or not th:
                        continue
                    total_json_dialogues += 1
                    
                    pure_key = d.get("key", "").strip()
                    if not pure_key:
                        pure_key = to_pure_alphanumeric_key(en)
                        
                    if pure_key not in translated_db:
                        translated_db[pure_key] = {
                            "text_en": en,
                            "text_th": th,
                            "quests": set(),
                            "files": set()
                        }
                    translated_db[pure_key]["quests"].add(quest_id)
                    translated_db[pure_key]["files"].add(str(rel_file))
        except Exception as e:
            print(f"Error reading {file_path}: {e}")

    # 2. Load game dialogues from CSVs
    print("Loading game dialogues from ffxiv-datamining/csv/en/cut_scene/ and quest/...")
    csv_pattern_cs = os.path.join(datamining_dir, "csv", "en", "cut_scene", "**", "*.csv")
    csv_pattern_q = os.path.join(datamining_dir, "csv", "en", "quest", "**", "*.csv")
    csv_files = glob.glob(csv_pattern_cs, recursive=True) + glob.glob(csv_pattern_q, recursive=True)
    
    game_db = {} # pure_key -> {voice_key, speaker, file, patch, raw_text}

    for file_path_str in csv_files:
        file_path = Path(file_path_str)
        patch_dir = file_path.parent.name
        file_name = file_path.name
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                for row in reader:
                    if len(row) >= 3:
                        voice_key = row[1]
                        dialogue_en = row[2]
                        if len(row) > 3:
                            dialogue_en = ", ".join(row[2:])
                            
                        pure_key = to_pure_alphanumeric_key(dialogue_en)
                        if not pure_key:
                            continue
                            
                        # If duplicate keys exist in game data, keep one (or aggregate)
                        if pure_key not in game_db:
                            game_db[pure_key] = []
                        game_db[pure_key].append({
                            "voice_key": voice_key,
                            "speaker": extract_speaker(voice_key),
                            "file": file_name,
                            "patch": patch_dir,
                            "raw_text": dialogue_en
                        })
        except Exception as e:
            print(f"Error reading {file_path}: {e}")

    # 3. Load alignment.json and Match using V1 (Exact), V2 (Pronoun Variants), and V3 (Fuzzy Alignment)
    alignment_path = content_dir / "alignment.json"
    alignment_map = {}
    if alignment_path.exists():
        try:
            with open(alignment_path, 'r', encoding='utf-8') as f:
                alignment_map = json.load(f)
            print(f"Loaded {len(alignment_map)} alignment pairs from alignment.json.")
        except Exception as e:
            print(f"Error loading alignment.json: {e}")
    else:
        print("alignment.json not found!")

    # Reverse alignment map (maps clean translation key -> game key)
    # alignment.json structure: game_key: trans_key
    reverse_alignment = {t_key: g_key for g_key, t_key in alignment_map.items()}

    print("Performing match analysis...")
    matched_v1 = [] # Standard exact matches
    matched_v2 = [] # Improved matches via slash/pronoun variants
    matched_v3 = [] # Mapped phrasing / fuzzy matches via alignment.json
    unmatched = []

    speaker_counts = defaultdict(int)
    patch_counts = defaultdict(int)

    for pure_key, trans in translated_db.items():
        quests = list(trans["quests"])
        files = list(trans["files"])
        
        # Scenario A: Direct standard exact match
        if pure_key in game_db:
            matches = game_db[pure_key]
            for m in matches:
                if m["speaker"]:
                    speaker_counts[m["speaker"]] += 1
                patch_counts[m["patch"]] += 1
            
            matched_v1.append({
                "pure_key": pure_key,
                "text_en": trans["text_en"],
                "text_th": trans["text_th"],
                "quests": quests,
                "files": files,
                "status": "matched_standard",
                "matches": matches
            })
        else:
            # Scenario B: Try slash variations (Improved matching)
            variants = generate_key_variants(trans["text_en"])
            found_match = False
            for var_key in variants:
                if var_key in game_db:
                    matches = game_db[var_key]
                    for m in matches:
                        if m["speaker"]:
                            speaker_counts[m["speaker"]] += 1
                        patch_counts[m["patch"]] += 1
                    
                    matched_v2.append({
                        "pure_key": pure_key,
                        "matched_var_key": var_key,
                        "text_en": trans["text_en"],
                        "text_th": trans["text_th"],
                        "quests": quests,
                        "files": files,
                        "status": "matched_improved",
                        "matches": matches
                    })
                    found_match = True
                    break
            
            # Scenario C: Try fuzzy alignment matching (V3)
            if not found_match:
                clean_trans_key = to_pure_alphanumeric_key(trans["text_en"])
                if clean_trans_key in reverse_alignment:
                    g_key = reverse_alignment[clean_trans_key]
                    if g_key in game_db:
                        matches = game_db[g_key]
                        for m in matches:
                            if m["speaker"]:
                                speaker_counts[m["speaker"]] += 1
                            patch_counts[m["patch"]] += 1
                        
                        matched_v3.append({
                            "pure_key": pure_key,
                            "matched_aligned_key": g_key,
                            "text_en": trans["text_en"],
                            "text_th": trans["text_th"],
                            "quests": quests,
                            "files": files,
                            "status": "matched_aligned",
                            "matches": matches
                        })
                        found_match = True

            # Scenario D: Truly unmatched
            if not found_match:
                unmatched.append({
                    "pure_key": pure_key,
                    "text_en": trans["text_en"],
                    "text_th": trans["text_th"],
                    "quests": quests,
                    "files": files,
                    "status": "unmatched"
                })

    # Stats
    total_keys = len(translated_db)
    count_v1 = len(matched_v1)
    count_v2 = len(matched_v2)
    count_v3 = len(matched_v3)
    count_unmatched = len(unmatched)
    
    rate_v1 = (count_v1 / total_keys) * 100 if total_keys else 0
    rate_v2 = (count_v2 / total_keys) * 100 if total_keys else 0
    rate_v3 = (count_v3 / total_keys) * 100 if total_keys else 0
    rate_total = ((count_v1 + count_v2 + count_v3) / total_keys) * 100 if total_keys else 0
    
    print(f"Stats:")
    print(f"  Standard Matches (V1): {count_v1} ({rate_v1:.2f}%)")
    print(f"  Improved Matches (V2): {count_v2} (Adds {rate_v2:.2f}%)")
    print(f"  Aligned Matches (V3): {count_v3} (Adds {rate_v3:.2f}%)")
    print(f"  Total Matched: {count_v1 + count_v2 + count_v3} ({rate_total:.2f}%)")
    print(f"  Unmatched: {count_unmatched} ({(count_unmatched/total_keys)*100:.2f}%)")

    # 4. Save CSV and JSON
    all_matched = matched_v1 + matched_v2 + matched_v3
    # Output v2 CSV
    out_csv = os.path.join(workspace_dir, "compiled_dialogues_v2.csv")
    with open(out_csv, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['language', 'patch', 'file', 'index', 'key', 'speaker', 'dialogue', 'status'])
        for item in all_matched:
            for m in item["matches"]:
                writer.writerow(['en', m['patch'], m['file'], '', m['voice_key'], m['speaker'], m['raw_text'], item['status']])
                
    # Detailed V2 report
    report_v2 = {
        "summary": {
            "total_dialogues": total_json_dialogues,
            "unique_keys": total_keys,
            "matched_standard": count_v1,
            "matched_improved": count_v2,
            "matched_aligned": count_v3,
            "total_matched": count_v1 + count_v2 + count_v3,
            "unmatched": count_unmatched,
            "match_rate_standard": rate_v1,
            "match_rate_improved": (count_v1 + count_v2) / total_keys * 100 if total_keys else 0,
            "match_rate_overall": rate_total
        },
        "matched_standard": matched_v1,
        "matched_improved": matched_v2,
        "matched_aligned": matched_v3,
        "unmatched": unmatched
    }
    with open(os.path.join(workspace_dir, "key_analysis_report_v2.json"), 'w', encoding='utf-8') as f:
        json.dump(report_v2, f, ensure_ascii=False, indent=2)

    # 5. Build Compact Web JSON Database (data.json)
    sample_dialogues = []
    
    # Flatten items for display
    def flatten_item(item):
        m_info = item.get("matches", [{}])[0] if "matches" in item else {}
        return {
            "text_en": item["text_en"],
            "text_th": item["text_th"],
            "quests": item["quests"],
            "files": item["files"],
            "status": item["status"],
            "game_en": m_info.get("raw_text", ""),
            "voice_key": m_info.get("voice_key", ""),
            "speaker": m_info.get("speaker", ""),
            "patch": m_info.get("patch", ""),
            "game_file": m_info.get("file", "")
        }

    # Add all improved matches (solution showcase)
    for item in matched_v2:
        sample_dialogues.append(flatten_item(item))

    # Add all aligned matches
    for item in matched_v3:
        sample_dialogues.append(flatten_item(item))
        
    # Sample 1000 standard matches
    for item in matched_v1[:1000]:
        sample_dialogues.append(flatten_item(item))
        
    # Sample 1000 unmatched
    for item in unmatched[:1000]:
        sample_dialogues.append(flatten_item(item))

    # Spotlight item
    spotlight_dialogue = None
    for item in matched_v2:
        if "lost without the familiar" in item["text_en"].lower():
            spotlight_dialogue = flatten_item(item)
            break
            
    web_db = {
        "summary": {
            "total_dialogues": total_json_dialogues,
            "unique_keys": total_keys,
            "matched_standard": count_v1,
            "matched_improved": count_v2,
            "matched_aligned": count_v3,
            "total_matched": count_v1 + count_v2 + count_v3,
            "unmatched": count_unmatched,
            "match_rate_standard": f"{rate_v1:.2f}%",
            "match_rate_improved": f"{(count_v1 + count_v2) / total_keys * 100:.2f}%" if total_keys else "0.00%",
            "match_rate_overall": f"{rate_total:.2f}%"
        },
        "top_speakers": sorted(speaker_counts.items(), key=lambda x: x[1], reverse=True)[:10],
        "top_patches": sorted(patch_counts.items(), key=lambda x: x[1], reverse=True)[:10],
        "spotlight": spotlight_dialogue,
        "dialogues": sample_dialogues
    }
    
    with open(os.path.join(web_dir, "data.json"), 'w', encoding='utf-8') as f:
        json.dump(web_db, f, ensure_ascii=False, indent=2)
    print(f"Optimized web database written to {os.path.join(web_dir, 'data.json')}")

if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    run_analysis_v2(current_dir)
