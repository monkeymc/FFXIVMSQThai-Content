import os
import json
import re

def build_index():
    print("Building sentence index...")
    th_dir = "th"
    paths = []
    sentences = []
    
    # Walk through the th directory
    for root, dirs, files in os.walk(th_dir):
        # Sort files to ensure deterministic index order
        files.sort()
        dirs.sort()
        for file in files:
            if file.endswith(".json"):
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, th_dir)
                
                try:
                    with open(full_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    
                    dialogues = data.get("dialogues", [])
                    if not dialogues:
                        continue
                        
                    # Add path to paths list
                    paths.append(rel_path)
                    path_idx = len(paths) - 1
                    
                    for idx, diag in enumerate(dialogues):
                        text_en = diag.get("text_en", "").strip()
                        text_th = diag.get("text", "").strip()
                        key = diag.get("key", "").strip()
                        
                        if text_en or text_th:
                            # We store path_idx, text_en, text_th, and dialogue index
                            sentences.append([path_idx, text_en, text_th, idx])
                            
                except Exception as e:
                    print(f"Error reading {full_path}: {e}")
                    
    print(f"Indexed {len(paths)} files and {len(sentences)} sentences.")
    
    index_data = {
        "paths": paths,
        "sentences": sentences
    }
    
    # Save the index to a file
    os.makedirs("website/public", exist_ok=True)
    out_path = "website/public/sentences.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(index_data, f, ensure_ascii=False, separators=(',', ':'))
        
    print(f"Saved index to {out_path} (Size: {os.path.getsize(out_path) / (1024*1024):.2f} MB)")
    
    # Copy glossary.md to public folder
    import shutil
    shutil.copy("glossary.md", "website/public/glossary.md")
    print("Copied glossary.md to website/public/glossary.md")
    
    # Copy th folder to website/public/th
    dest_th = "website/public/th"
    if os.path.exists(dest_th):
        shutil.rmtree(dest_th)
    shutil.copytree("th", dest_th)
    print("Copied th folder to website/public/th")


if __name__ == "__main__":
    build_index()
