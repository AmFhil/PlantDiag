#!/usr/bin/env python3
# extract_plantdoc.py  --  Extract only Tomato & Pepper images from PlantDoc ZIP.
# Skips entries with Windows-invalid characters in their paths.
import os, sys, shutil, zipfile, random
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

TOOLS_DIR   = Path(__file__).parent.resolve()
ZIP_PATH    = TOOLS_DIR / "datasets_raw" / "tomato" / "plantdoc.zip"
EXTRACT_DIR = TOOLS_DIR / "datasets_raw" / "tomato" / "plantdoc_extracted"
TRAIN_DIR   = TOOLS_DIR / "datasets" / "train"
VAL_DIR     = TOOLS_DIR / "datasets" / "val"
VAL_SPLIT   = 0.20
RANDOM_SEED = 42

TOMATO_MAP = {
    # PlantDoc exact folder names (lowercased)
    "tomato leaf bacterial spot":            "Tomato___Bacterial_Spot",
    "tomato early blight leaf":              "Tomato___Early_Blight",
    "tomato leaf late blight":               "Tomato___Late_Blight",
    "tomato leaf yellow virus":              "Tomato___Yellow_Leaf_Curl_Virus",
    "tomato leaf mosaic virus":              "Tomato___Leaf_Miner_Tuta",   # closest proxy
    "tomato leaf":                           "Tomato___Healthy",
    "bell_pepper leaf spot":                 "Pepper___Bacterial_Spot",
    "bell_pepper leaf":                      "Pepper___Healthy",
}

# Display names for summary
DISPLAY_CLASSES = [
    "Tomato___Bacterial_Spot", "Tomato___Early_Blight", "Tomato___Late_Blight",
    "Tomato___Yellow_Leaf_Curl_Virus", "Tomato___Leaf_Miner_Tuta", "Tomato___Healthy",
    "Pepper___Bacterial_Spot", "Pepper___Healthy",
]

INVALID_CHARS = set('?*:|<>"')

def is_valid_windows_path(name):
    return not any(c in INVALID_CHARS for c in name)

def get_dest_class(folder_name):
    fn = folder_name.lower().strip()
    for key, cls in TOMATO_MAP.items():
        if key in fn:
            return cls
    return None

def split_and_copy(images, dest_class):
    random.seed(RANDOM_SEED)
    random.shuffle(images)
    split_idx = max(1, int(len(images) * (1 - VAL_SPLIT)))
    train_imgs = images[:split_idx]
    val_imgs   = images[split_idx:]
    (TRAIN_DIR / dest_class).mkdir(parents=True, exist_ok=True)
    (VAL_DIR   / dest_class).mkdir(parents=True, exist_ok=True)
    for p in train_imgs:
        dst = TRAIN_DIR / dest_class / p.name
        if not dst.exists():
            shutil.copy2(p, dst)
    for p in val_imgs:
        dst = VAL_DIR / dest_class / p.name
        if not dst.exists():
            shutil.copy2(p, dst)
    print(f"  -> {dest_class}: {len(train_imgs)} train / {len(val_imgs)} val")
    return len(images)

def main():
    if not ZIP_PATH.exists():
        print(f"ERROR: ZIP not found at {ZIP_PATH}")
        sys.exit(1)

    sz_mb = ZIP_PATH.stat().st_size // 1024 // 1024
    print(f"Opening PlantDoc ZIP: {ZIP_PATH} ({sz_mb} MB)")
    EXTRACT_DIR.mkdir(parents=True, exist_ok=True)

    skipped = 0
    extracted = 0

    import re
    with zipfile.ZipFile(ZIP_PATH, 'r') as z:
        members = z.namelist()
        print(f"  Total entries in ZIP: {len(members)}")

        relevant = []
        for m in members:
            parts = Path(m).parts
            if len(parts) < 4:
                continue
            folder_name = parts[2]
            filename    = parts[-1]
            ext = Path(filename).suffix.lower()
            if ext not in {'.jpg', '.jpeg', '.png'}:
                continue
            dest_class = get_dest_class(folder_name)
            if dest_class:
                # Sanitize filename for safe Windows storage
                clean_name = re.sub(r'[^a-zA-Z0-9._-]', '_', filename)
                relevant.append((m, dest_class, clean_name))

        print(f"  Relevant tomato/pepper entries: {len(relevant)}")

        class_files = {}
        for member, dest_class, filename in relevant:
            class_files.setdefault(dest_class, []).append((member, filename))

        for dest_class, file_list in class_files.items():
            class_extract_dir = EXTRACT_DIR / dest_class
            class_extract_dir.mkdir(parents=True, exist_ok=True)
            extracted_paths = []
            for member, filename in file_list:
                out_path = class_extract_dir / filename
                if not out_path.exists():
                    try:
                        data = z.read(member)
                        out_path.write_bytes(data)
                        extracted += 1
                    except Exception as e:
                        print(f"    WARN: could not extract {member}: {e}")
                        continue
                extracted_paths.append(out_path)
            split_and_copy(extracted_paths, dest_class)

    print(f"\n  Extracted {extracted} images, skipped {skipped} invalid-path entries.")

    print("\n=== TOMATO / PEPPER INVENTORY ===")
    for cls in DISPLAY_CLASSES:
        t = len(list((TRAIN_DIR / cls).glob("*.*"))) if (TRAIN_DIR / cls).exists() else 0
        v = len(list((VAL_DIR   / cls).glob("*.*"))) if (VAL_DIR   / cls).exists() else 0
        status = "[OK]" if t >= 50 else "[LOW]" if t > 0 else "[EMPTY]"
        print(f"  {status} {cls:<45} train={t:>4}  val={v:>4}")

if __name__ == "__main__":
    main()
