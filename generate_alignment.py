#!/usr/bin/env python3
import os
import json
import csv
import re
import glob
from pathlib import Path
from difflib import SequenceMatcher
from collections import defaultdict

def to_pure_alphanumeric_key(text):
    if not text:
        return ""
    no_payload = re.sub(r'[\x02].{1,4}[\x03]|[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
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

def clean_text(text):
    t = text.lower().replace("“", "\"").replace("”", "\"").replace("'", "").replace("`", "")
    t = t.replace("─", " ").replace("—", " ").replace("-", " ")
    t = re.sub(r'\s+', ' ', t).strip()
    return t

def get_words(text):
    """Tokenize and return words of length >= 4 to build index keys"""
    return set(re.findall(r'\b\w{4,}\b', text.lower()))

def generate_alignment():
    content_dir = Path("/home/chatja/fun/FFXIVMSQThai-Content/th")
    datamining_dir = Path("/home/chatja/fun/FFXIVMSQThai/ffxiv-datamining")

    if not content_dir.exists() or not datamining_dir.exists():
        print("Required folders not found!")
        return

    # 1. Load translations
    print("Loading translated dialogues...")
    json_files = glob.glob(os.path.join(content_dir, "**", "*.json"), recursive=True)
    translations = []
    for f_path in json_files:
        if "alignment.json" in f_path:
            continue
        try:
            with open(f_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for d in data.get("dialogues", []):
                    en = d.get("text_en", "").strip()
                    th = d.get("text", "").strip()
                    if en and th:
                        translations.append(en)
        except Exception:
            pass
    print(f"Loaded {len(translations)} unique translations.")

    # 2. Load game dialogues from CSVs
    print("Loading game dialogues from CSVs...")
    csv_pattern_cs = os.path.join(datamining_dir, "csv", "en", "cut_scene", "**", "*.csv")
    csv_pattern_q = os.path.join(datamining_dir, "csv", "en", "quest", "**", "*.csv")
    csv_files = glob.glob(csv_pattern_cs, recursive=True) + glob.glob(csv_pattern_q, recursive=True)
    
    game_lines = {}
    for file_path_str in csv_files:
        file_path = Path(file_path_str)
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                for row in reader:
                    if len(row) >= 3:
                        text = row[2]
                        if len(row) > 3:
                            text = ", ".join(row[2:])
                        game_lines[text] = True
        except Exception:
            pass
    print(f"Loaded {len(game_lines)} unique game lines.")

    # 3. Build Word Inverted Index for Game Lines (Search Blocking)
    print("Building word inverted index for game lines...")
    inverted_index = defaultdict(list)
    for line in game_lines.keys():
        words = get_words(line)
        for w in words:
            inverted_index[w].append(line)

    # Pre-filter exact match translations to isolate unmatched lines
    game_relaxed_db = {}
    for line in game_lines.keys():
        g_key = to_pure_alphanumeric_key(line)
        if g_key:
            game_relaxed_db[g_key] = line

    unmatched_trans = []
    for trans in translations:
        t_key = to_pure_alphanumeric_key(trans)
        if t_key not in game_relaxed_db:
            unmatched_trans.append(trans)
            
    print(f"Found {len(unmatched_trans)} translation lines without exact match. Running optimized search...")
    
    # 4. Perform search using Blocking
    alignment_map = {}
    count = 0
    
    for trans in unmatched_trans:
        clean_t = clean_text(trans)
        t_len = len(clean_t)
        if t_len < 15: # Skip very short sentences to avoid false positives
            continue
            
        t_key = to_pure_alphanumeric_key(trans)
        words = get_words(trans)
        if not words:
            continue
            
        # Collect candidate game lines sharing index words
        candidates = set()
        for w in words:
            if w in inverted_index:
                # Skip words that map to too many lines (>1000) to act as stop-word filter
                if len(inverted_index[w]) < 1000:
                    candidates.update(inverted_index[w])
                    
        # Filter candidates by length
        filtered_candidates = [c for c in candidates if abs(len(clean_text(c)) - t_len) <= 8]
        
        # Run similarity check on filtered candidates
        best_game_line = None
        best_ratio = 0
        
        for g_line in filtered_candidates:
            clean_g = clean_text(g_line)
            ratio = SequenceMatcher(None, clean_t, clean_g).ratio()
            if ratio > 0.90 and ratio < 1.0:
                if ratio > best_ratio:
                    best_ratio = ratio
                    best_game_line = g_line
                    
        if best_game_line:
            g_key = to_pure_alphanumeric_key(best_game_line)
            if g_key and t_key:
                alignment_map[g_key] = t_key
                count += 1
                if count % 100 == 0:
                    print(f"Mapped {count} phrasing mismatches...")

    # Write to content/alignment.json
    out_path = os.path.join(content_dir, "alignment.json")
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(alignment_map, f, ensure_ascii=False, indent=2)
        
    print(f"Successfully generated {len(alignment_map)} alignment pairs in {out_path}")

if __name__ == "__main__":
    generate_alignment()
