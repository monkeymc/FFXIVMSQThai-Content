#!/usr/bin/env python3
import os
import csv
import json
import glob
from pathlib import Path

def extract_speaker(key):
    """
    Extracts the speaker name from the end of the voice key.
    E.g., "TEXT_VOICEMAN_02200_000010_THANCRED" -> "THANCRED"
    """
    parts = key.split('_')
    if len(parts) > 1:
        last_part = parts[-1]
        # If the last part is not numeric and not empty, it's likely the speaker name
        if not last_part.isdigit() and last_part:
            return last_part
    return ""

def collect_dialogues(base_dir, output_csv, output_json=None):
    csv_dir = Path(base_dir) / "csv"
    if not csv_dir.exists():
        print(f"Error: csv directory not found at {csv_dir.absolute()}")
        return

    records = []
    
    # Search for all cut_scene CSVs under any language folder
    # Path pattern: csv/{lang}/cut_scene/{patch_dir}/*.csv
    csv_pattern = os.path.join(csv_dir, "*", "cut_scene", "**", "*.csv")
    csv_files = glob.glob(csv_pattern, recursive=True)
    
    print(f"Found {len(csv_files)} CSV files in cut_scene directories.")
    
    for file_path_str in sorted(csv_files):
        file_path = Path(file_path_str)
        
        # Extract metadata from paths
        # Structure: .../csv/{lang}/cut_scene/{patch_dir}/{filename}.csv
        try:
            parts = file_path.parts
            # Find the index of "csv" in the path parts
            csv_idx = parts.index("csv")
            lang = parts[csv_idx + 1]
            patch_dir = parts[csv_idx + 3]
            file_name = file_path.name
        except (ValueError, IndexError):
            lang = "unknown"
            patch_dir = "unknown"
            file_name = file_path.name

        # Read the CSV file
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                for row_idx, row in enumerate(reader):
                    # Expecting at least 3 columns: Index, Key, Text
                    if len(row) >= 3:
                        idx = row[0]
                        key = row[1]
                        text = row[2]
                        
                        # Sometimes there are additional columns (though rare in voice csvs)
                        if len(row) > 3:
                            text = ", ".join(row[2:])
                            
                        speaker = extract_speaker(key)
                        
                        records.append({
                            'language': lang,
                            'patch': patch_dir,
                            'file': file_name,
                            'index': idx,
                            'key': key,
                            'speaker': speaker,
                            'dialogue': text
                        })
        except Exception as e:
            print(f"Error reading {file_path}: {e}")

    # Write to a consolidated CSV file
    try:
        with open(output_csv, 'w', encoding='utf-8', newline='') as f:
            fieldnames = ['language', 'patch', 'file', 'index', 'key', 'speaker', 'dialogue']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(records)
        print(f"Successfully compiled {len(records)} dialogue lines into CSV: {output_csv}")
    except Exception as e:
        print(f"Error writing CSV output: {e}")

    # Optionally write to JSON
    if output_json:
        try:
            with open(output_json, 'w', encoding='utf-8') as f:
                json.dump(records, f, ensure_ascii=False, indent=2)
            print(f"Successfully compiled dialogue lines into JSON: {output_json}")
        except Exception as e:
            print(f"Error writing JSON output: {e}")

if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    datamining_dir = os.path.join(current_dir, "ffxiv-datamining")
    
    out_csv = os.path.join(current_dir, "compiled_dialogues.csv")
    out_json = os.path.join(current_dir, "compiled_dialogues.json")
    
    collect_dialogues(datamining_dir, out_csv, out_json)
