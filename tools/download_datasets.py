#!/usr/bin/env python3
r"""
================================================================================
download_datasets.py  —  NaijaStaples-30 Real Dataset Downloader
================================================================================
Downloads real public datasets needed to train the NaijaStaples-30 model.
Uses verified public sources (HuggingFace Hub, GitHub PlantDoc, Kaggle, Mendeley).

USAGE:
    # Option A — Download all automated datasets (Cassava, Rice, Maize, Tomato, Pepper):
    python tools/download_datasets.py --all

    # Option B — Download a single crop:
    python tools/download_datasets.py --crop cassava
    python tools/download_datasets.py --crop rice
    python tools/download_datasets.py --crop maize
    python tools/download_datasets.py --crop tomato
    python tools/download_datasets.py --crop pepper
    python tools/download_datasets.py --crop sorghum
    python tools/download_datasets.py --crop cowpea
    python tools/download_datasets.py --crop yam
================================================================================
"""

import os
import sys
import json
import shutil
import zipfile
import argparse
import random
import csv
from pathlib import Path

# Fix Windows console UTF-8 output if possible
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# ─── Config ──────────────────────────────────────────────────────────────────
TOOLS_DIR   = Path(__file__).parent.resolve()
DATASET_DIR = TOOLS_DIR / "datasets"
RAW_DIR     = TOOLS_DIR / "datasets_raw"
TRAIN_DIR   = DATASET_DIR / "train"
VAL_DIR     = DATASET_DIR / "val"
VAL_SPLIT   = 0.20
RANDOM_SEED = 42

# All 30 class folder names (must match classes.json order)
ALL_CLASSES = [
    "Cassava___Bacterial_Blight", "Cassava___Brown_Streak_Disease",
    "Cassava___Green_Mottle", "Cassava___Mosaic_Disease", "Cassava___Healthy",
    "Corn_(maize)___Common_Rust", "Corn_(maize)___Northern_Leaf_Blight",
    "Corn_(maize)___Fall_Armyworm", "Corn_(maize)___Healthy",
    "Yam___Anthracnose", "Yam___Mosaic_Virus", "Yam___Healthy",
    "Cowpea___Cercospora_Leaf_Spot", "Cowpea___Bacterial_Blight", "Cowpea___Healthy",
    "Rice___Bacterial_Blight", "Rice___Blast", "Rice___Brown_Spot", "Rice___Healthy",
    "Tomato___Bacterial_Spot", "Tomato___Early_Blight", "Tomato___Late_Blight",
    "Tomato___Yellow_Leaf_Curl_Virus", "Tomato___Leaf_Miner_Tuta", "Tomato___Healthy",
    "Pepper___Bacterial_Spot", "Pepper___Leaf_Curl", "Pepper___Healthy",
    "Sorghum___Anthracnose", "Sorghum___Healthy",
]

parser = argparse.ArgumentParser(description="Download NaijaStaples-30 datasets")
parser.add_argument("--all",       action="store_true", help="Download all automated crops")
parser.add_argument("--no-kaggle", action="store_true", help="Skip Kaggle downloads")
parser.add_argument("--crop",      type=str, default=None,
                    help="Download single crop: cassava|maize|rice|tomato|pepper|sorghum|cowpea|yam")
parser.add_argument("--dataset-dir", type=str, default=str(DATASET_DIR))
args = parser.parse_args()

DATASET_DIR = Path(args.dataset_dir)
TRAIN_DIR   = DATASET_DIR / "train"
VAL_DIR     = DATASET_DIR / "val"

# ─── Helpers ──────────────────────────────────────────────────────────────────
def ensure_dirs():
    for cls in ALL_CLASSES:
        (TRAIN_DIR / cls).mkdir(parents=True, exist_ok=True)
        (VAL_DIR   / cls).mkdir(parents=True, exist_ok=True)
    RAW_DIR.mkdir(parents=True, exist_ok=True)

def split_and_copy(src_dir: Path, dest_class_name: str, val_frac=VAL_SPLIT):
    """Copy images from src_dir into train/ and val/ class folders."""
    exts = {'.jpg', '.jpeg', '.png', '.JPG', '.JPEG', '.PNG'}
    images = [f for f in src_dir.iterdir() if f.is_file() and f.suffix in exts]
    if not images:
        print(f"  WARNING: No images found in {src_dir}")
        return 0
    random.seed(RANDOM_SEED)
    random.shuffle(images)
    split_idx = max(1, int(len(images) * (1 - val_frac)))
    train_imgs = images[:split_idx]
    val_imgs   = images[split_idx:]
    for img in train_imgs:
        dest = TRAIN_DIR / dest_class_name / img.name
        if not dest.exists():
            shutil.copy2(img, dest)
    for img in val_imgs:
        dest = VAL_DIR / dest_class_name / img.name
        if not dest.exists():
            shutil.copy2(img, dest)
    print(f"  -> {dest_class_name}: {len(train_imgs)} train / {len(val_imgs)} val")
    return len(images)

def try_kaggle_download(dataset_id: str, dest_dir: Path, is_competition=False):
    """Download from Kaggle using kagglehub or kaggle CLI."""
    try:
        import kagglehub
        if is_competition:
            print(f"  Downloading competition from Kaggle: {dataset_id} ...")
            path = kagglehub.competition_download(dataset_id)
        else:
            print(f"  Downloading dataset from Kaggle: {dataset_id} ...")
            path = kagglehub.dataset_download(dataset_id)
        print(f"  Downloaded to: {path}")
        return Path(path)
    except Exception as e:
        print(f"  kagglehub failed ({e}), trying CLI...")

    # Fallback to kaggle CLI
    if is_competition:
        cmd = f'kaggle competitions download -c {dataset_id} -p "{dest_dir}"'
    else:
        cmd = f'kaggle datasets download -d {dataset_id} -p "{dest_dir}" --unzip'
    ret = os.system(cmd)
    if ret != 0:
        print(f"  [INFO] Kaggle download skipped for {dataset_id} (requires kaggle.json)")
        return None
    return dest_dir


# ─── CASSAVA ──────────────────────────────────────────────────────────────────
def download_cassava():
    print("\n[1/8] CASSAVA - Makerere AI Lab 2021 Dataset")
    raw = RAW_DIR / "cassava"
    raw.mkdir(exist_ok=True)

    # Method 1: HuggingFace Hub snapshot download (no account needed)
    try:
        print("  Downloading Makerere Cassava images from HuggingFace (no login required)...")
        from huggingface_hub import snapshot_download, hf_hub_download

        # First download the metadata CSV
        hf_hub_download(
            repo_id="yt0609/cassava-leaf-disease-classification",
            repo_type="dataset",
            filename="train.csv",
            local_dir=str(raw),
        )

        # Download images from part_001 (~7,100 high-res real field photos)
        print("  Downloading images part_001 (~7,100 field photos)...")
        snapshot_download(
            repo_id="yt0609/cassava-leaf-disease-classification",
            repo_type="dataset",
            allow_patterns=["train_images/part_001/*"],
            local_dir=str(raw),
            max_workers=16,
        )

        csv_path = raw / "train.csv"
        part1_dir = raw / "train_images" / "part_001"
        if csv_path.exists() and part1_dir.exists():
            label_map = {
                "0": "Cassava___Bacterial_Blight",
                "1": "Cassava___Brown_Streak_Disease",
                "2": "Cassava___Green_Mottle",
                "3": "Cassava___Mosaic_Disease",
                "4": "Cassava___Healthy",
            }
            rows = []
            with open(csv_path, encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for r in reader:
                    img_file = part1_dir / r["image_id"]
                    if img_file.exists():
                        rows.append((img_file, r["label"]))

            print(f"  Found {len(rows)} images locally from part_001. Organizing into classes...")
            random.seed(RANDOM_SEED)
            random.shuffle(rows)
            split = int(len(rows) * 0.8)
            sets = {"train": rows[:split], "val": rows[split:]}
            counts = {c: 0 for c in label_map.values()}
            for set_name, subset in sets.items():
                dest_root = TRAIN_DIR if set_name == "train" else VAL_DIR
                for img_path, label_id in subset:
                    cls_name = label_map.get(str(label_id))
                    if cls_name:
                        dest = dest_root / cls_name / img_path.name
                        if not dest.exists():
                            shutil.copy2(img_path, dest)
                        counts[cls_name] += 1
            for c, cnt in counts.items():
                print(f"    {c}: {cnt} images organized")
            print("  [OK] Cassava downloaded and organized via HuggingFace")
            return
    except Exception as e:
        print(f"  HuggingFace direct download failed ({e}), checking Kaggle...")

    # Method 2: Kaggle
    if not args.no_kaggle:
        path = try_kaggle_download("cassava-leaf-disease-classification", raw, is_competition=True)
        if path:
            _organise_cassava_from_kaggle(path)


def _organise_cassava_from_kaggle(raw_path: Path):
    label_map = {
        "0": "Cassava___Bacterial_Blight",
        "1": "Cassava___Brown_Streak_Disease",
        "2": "Cassava___Green_Mottle",
        "3": "Cassava___Mosaic_Disease",
        "4": "Cassava___Healthy",
    }
    csv_path = next(raw_path.rglob("train.csv"), None)
    img_dir  = next(raw_path.rglob("train_images"), None)
    if not csv_path or not img_dir:
        print(f"  Could not find train.csv or train_images in {raw_path}")
        return

    rows = []
    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append((row["image_id"], row["label"]))

    random.seed(RANDOM_SEED)
    random.shuffle(rows)
    split = int(len(rows) * 0.8)
    sets  = {"train": rows[:split], "val": rows[split:]}

    for set_name, subset in sets.items():
        dest_root = TRAIN_DIR if set_name == "train" else VAL_DIR
        for img_id, label_id in subset:
            class_name = label_map.get(str(label_id))
            if not class_name:
                continue
            src = img_dir / img_id
            if src.exists():
                shutil.copy2(src, dest_root / class_name / src.name)
    print("  [OK] Cassava organized from Kaggle download")


# ─── MAIZE ────────────────────────────────────────────────────────────────────
def download_maize():
    print("\n[2/8] MAIZE - Corn Leaf Disease Dataset")
    raw = RAW_DIR / "maize"
    raw.mkdir(exist_ok=True)

    # Method 1: HuggingFace (Spitblaze/Corn_or_Maize_Leaf_Disease_Dataset)
    try:
        print("  Downloading Maize dataset from HuggingFace (no login required)...")
        from huggingface_hub import snapshot_download
        corn_dir = snapshot_download(
            repo_id="Spitblaze/Corn_or_Maize_Leaf_Disease_Dataset",
            repo_type="dataset",
            local_dir=str(raw / "corn_hf"),
            max_workers=16,
        )
        corn_path = Path(corn_dir)
        folder_map = {
            "Common_Rust": "Corn_(maize)___Common_Rust",
            "Blight":      "Corn_(maize)___Northern_Leaf_Blight",
            "Healthy":     "Corn_(maize)___Healthy",
        }
        for candidate in corn_path.rglob("*"):
            if candidate.is_dir():
                for key, dest in folder_map.items():
                    if key.lower() == candidate.name.lower():
                        split_and_copy(candidate, dest)
                        break
        print("  [OK] Maize (Common Rust, Northern Leaf Blight, Healthy) downloaded from HuggingFace")
        return
    except Exception as e:
        print(f"  HuggingFace maize download failed ({e}), checking Kaggle...")

    # Method 2: Kaggle
    if not args.no_kaggle:
        path = try_kaggle_download("smaranjitghose/corn-or-maize-leaf-disease-dataset", raw)
        if path:
            folder_map = {
                "Common_Rust":          "Corn_(maize)___Common_Rust",
                "Northern_Leaf_Blight": "Corn_(maize)___Northern_Leaf_Blight",
                "Healthy":              "Corn_(maize)___Healthy",
            }
            for src_folder, dest_class in folder_map.items():
                for candidate in path.rglob(f"*{src_folder}*"):
                    if candidate.is_dir():
                        split_and_copy(candidate, dest_class)
                        break


# ─── RICE ─────────────────────────────────────────────────────────────────────
def download_rice():
    print("\n[3/8] RICE - Rice Leaf Disease Dataset")
    raw = RAW_DIR / "rice"
    raw.mkdir(exist_ok=True)

    # Method 1: HuggingFace sharmin3/Rice-Leaf-Disease ZIP download
    try:
        print("  Downloading Rice dataset ZIP from HuggingFace (no login required)...")
        from huggingface_hub import hf_hub_download
        zip_file = hf_hub_download(
            repo_id="sharmin3/Rice-Leaf-Disease",
            repo_type="dataset",
            filename="Rice Leaf Disease-20241115T062818Z-001.zip",
        )
        print("  Extracting Rice images...")
        extracted_dir = raw / "extracted"
        with zipfile.ZipFile(zip_file, "r") as z:
            z.extractall(extracted_dir)

        folder_map = {
            "bacterialblight": "Rice___Bacterial_Blight",
            "blast":           "Rice___Blast",
            "brownspot":       "Rice___Brown_Spot",
            "healthy":         "Rice___Healthy",
        }
        for candidate in extracted_dir.rglob("*"):
            if candidate.is_dir():
                for key, dest in folder_map.items():
                    if key == candidate.name.lower():
                        split_and_copy(candidate, dest)
                        break
        print("  [OK] Rice (Bacterial Blight, Blast, Brown Spot, Healthy) downloaded from HuggingFace")
        return
    except Exception as e:
        print(f"  HuggingFace rice download failed ({e}), checking Kaggle...")

    # Method 2: Kaggle
    if not args.no_kaggle:
        path = try_kaggle_download("minhhuy2810/rice-diseases-image-dataset", raw)
        if path:
            folder_map = {
                "bacterialblight": "Rice___Bacterial_Blight",
                "blast":           "Rice___Blast",
                "brownspot":       "Rice___Brown_Spot",
                "healthy":         "Rice___Healthy",
            }
            for candidate in path.rglob("*"):
                if candidate.is_dir():
                    for key, dest in folder_map.items():
                        if key in candidate.name.lower().replace(" ", "").replace("_", ""):
                            split_and_copy(candidate, dest)
                            break


# ─── TOMATO ───────────────────────────────────────────────────────────────────
def download_tomato():
    print("\n[4/8] TOMATO - PlantDoc Real Field Images (GitHub)")
    raw = RAW_DIR / "tomato"
    raw.mkdir(exist_ok=True)

    # PlantDoc - Download direct ZIP or Git clone (no login needed)
    plantdoc_dir = raw / "PlantDoc-Dataset"
    if not plantdoc_dir.exists():
        zip_path = raw / "plantdoc.zip"
        try:
            print("  Downloading PlantDoc ZIP from GitHub...")
            import urllib.request
            urllib.request.urlretrieve(
                "https://github.com/pratikkayal/PlantDoc-Dataset/archive/refs/heads/master.zip",
                zip_path,
            )
            print("  Extracting PlantDoc ZIP...")
            with zipfile.ZipFile(zip_path, "r") as z:
                z.extractall(raw)
            extracted_master = raw / "PlantDoc-Dataset-master"
            if extracted_master.exists():
                extracted_master.rename(plantdoc_dir)
        except Exception as e:
            print(f"  Direct ZIP failed ({e}), trying git clone...")
            os.system(f'git clone --depth 1 https://github.com/pratikkayal/PlantDoc-Dataset "{plantdoc_dir}"')

    if plantdoc_dir.exists():
        tomato_folder_map = {
            "tomato bacterial spot":           "Tomato___Bacterial_Spot",
            "tomato early blight":             "Tomato___Early_Blight",
            "tomato late blight":              "Tomato___Late_Blight",
            "tomato yellow leaf curl virus":   "Tomato___Yellow_Leaf_Curl_Virus",
            "tomato leaf miner":               "Tomato___Leaf_Miner_Tuta",
            "tomato healthy":                  "Tomato___Healthy",
        }
        for base_split in ["train", "test"]:
            split_folder = plantdoc_dir / base_split
            if split_folder.exists():
                for folder in split_folder.iterdir():
                    if folder.is_dir():
                        for key, dest in tomato_folder_map.items():
                            if key in folder.name.lower():
                                split_and_copy(folder, dest)
                                break
        print("  [OK] Tomato field images organized from PlantDoc")


# ─── PEPPER ───────────────────────────────────────────────────────────────────
def download_pepper():
    print("\n[5/8] PEPPER - PlantDoc Field Images (GitHub)")
    raw = RAW_DIR / "pepper"
    raw.mkdir(exist_ok=True)

    plantdoc_dir = RAW_DIR / "tomato" / "PlantDoc-Dataset"
    if not plantdoc_dir.exists():
        plantdoc_dir = raw / "PlantDoc-Dataset"
        if not plantdoc_dir.exists():
            print("  Cloning PlantDoc from GitHub (no login needed)...")
            os.system(
                f'git clone --depth 1 https://github.com/pratikkayal/PlantDoc-Dataset "{plantdoc_dir}"'
            )

    if plantdoc_dir.exists():
        pepper_map = {
            "pepper bell bacterial spot": "Pepper___Bacterial_Spot",
            "pepper bell healthy":        "Pepper___Healthy",
        }
        for base_split in ["train", "test"]:
            split_folder = plantdoc_dir / base_split
            if split_folder.exists():
                for folder in split_folder.iterdir():
                    if folder.is_dir():
                        for key, dest in pepper_map.items():
                            if key in folder.name.lower():
                                split_and_copy(folder, dest)
                                break
        print("  [OK] Pepper field images organized from PlantDoc")


# ─── SORGHUM ──────────────────────────────────────────────────────────────────
def download_sorghum():
    print("\n[6/8] SORGHUM - Mendeley Data DOI:10.17632/fgb3cmfrg2.1")
    raw = RAW_DIR / "sorghum"
    raw.mkdir(exist_ok=True)
    zip_path = raw / "sorghum_disease.zip"
    print("  To download full Sorghum dataset (~1.2GB):")
    print("  1. Visit: https://data.mendeley.com/datasets/fgb3cmfrg2/1")
    print("  2. Click 'Download All'")
    print(f"  3. Place ZIP at: {zip_path}")
    print("  4. Re-run: python tools/download_datasets.py --crop sorghum")

    if zip_path.exists():
        print("  Extracting existing sorghum zip...")
        with zipfile.ZipFile(zip_path, "r") as z:
            z.extractall(raw / "extracted")
        sorghum_map = {
            "anthracnose": "Sorghum___Anthracnose",
            "healthy":     "Sorghum___Healthy",
        }
        for candidate in (raw / "extracted").rglob("*"):
            if candidate.is_dir():
                for key, dest in sorghum_map.items():
                    if key in candidate.name.lower():
                        split_and_copy(candidate, dest)
                        break


# ─── COWPEA ───────────────────────────────────────────────────────────────────
def download_cowpea():
    print("\n[7/8] COWPEA - Mendeley DOI:10.17632/ykvcrjffzd.1")
    raw = RAW_DIR / "cowpea"
    raw.mkdir(exist_ok=True)
    zip_path = raw / "cowpea_disease.zip"
    print("  To download Cowpea dataset:")
    print("  1. Visit: https://data.mendeley.com/datasets/ykvcrjffzd/1")
    print("  2. Click 'Download All'")
    print(f"  3. Place ZIP at: {zip_path}")
    print("  4. Re-run: python tools/download_datasets.py --crop cowpea")

    if zip_path.exists():
        print("  Extracting existing cowpea zip...")
        with zipfile.ZipFile(zip_path, "r") as z:
            z.extractall(raw / "extracted")
        cowpea_map = {
            "cercospora": "Cowpea___Cercospora_Leaf_Spot",
            "blight":     "Cowpea___Bacterial_Blight",
            "healthy":    "Cowpea___Healthy",
        }
        for candidate in (raw / "extracted").rglob("*"):
            if candidate.is_dir():
                for key, dest in cowpea_map.items():
                    if key in candidate.name.lower():
                        split_and_copy(candidate, dest)
                        break


# ─── YAM ──────────────────────────────────────────────────────────────────────
def download_yam():
    print("\n[8/8] YAM - Mendeley DOI:10.17632/fxy6jn3gm2.1")
    raw = RAW_DIR / "yam"
    raw.mkdir(exist_ok=True)
    zip_path = raw / "yam_disease.zip"
    print("  To download Yam dataset:")
    print("  1. Visit: https://data.mendeley.com/datasets/fxy6jn3gm2/1")
    print("  2. Click 'Download All'")
    print(f"  3. Place ZIP at: {zip_path}")
    print("  4. Re-run: python tools/download_datasets.py --crop yam")

    if zip_path.exists():
        print("  Extracting existing yam zip...")
        with zipfile.ZipFile(zip_path, "r") as z:
            z.extractall(raw / "extracted")
        yam_map = {
            "anthracnose": "Yam___Anthracnose",
            "mosaic":      "Yam___Mosaic_Virus",
            "healthy":     "Yam___Healthy",
        }
        for candidate in (raw / "extracted").rglob("*"):
            if candidate.is_dir():
                for key, dest in yam_map.items():
                    if key in candidate.name.lower():
                        split_and_copy(candidate, dest)
                        break


# ─── Report ───────────────────────────────────────────────────────────────────
def print_summary():
    print("\n" + "=" * 65)
    print("NAIJASTAPLES-30 DATASET INVENTORY")
    print("=" * 65)
    total_train = total_val = 0
    for cls in ALL_CLASSES:
        t = len(list((TRAIN_DIR / cls).glob("*.*"))) if (TRAIN_DIR / cls).exists() else 0
        v = len(list((VAL_DIR   / cls).glob("*.*"))) if (VAL_DIR   / cls).exists() else 0
        status = "[OK]  " if t >= 100 else "[WARN]" if t > 0 else "[EMPTY]"
        print(f"  {status} {cls:<42} train={t:>5}  val={v:>4}")
        total_train += t
        total_val   += v
    print("-" * 65)
    print(f"  TOTAL IMAGES ACROSS ALL CLASSES: {total_train} train / {total_val} val")
    print("=" * 65)


# ─── Entry ────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    ensure_dirs()
    random.seed(RANDOM_SEED)

    crop = args.crop.lower() if args.crop else None

    if crop == "rice" or args.all:
        download_rice()
    if crop == "maize" or args.all:
        download_maize()
    if crop == "tomato" or args.all:
        download_tomato()
    if crop == "pepper" or args.all:
        download_pepper()
    if crop == "cassava" or args.all:
        download_cassava()
    if crop == "sorghum":
        download_sorghum()
    if crop == "cowpea":
        download_cowpea()
    if crop == "yam":
        download_yam()

    if not crop and not args.all:
        print("No crop specified. Use --all or --crop <name>")
        print("Example: python tools/download_datasets.py --crop rice")

    print_summary()
