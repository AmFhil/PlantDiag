import os
import sys
import shutil
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import tensorflow as tf

TOOLS_DIR = Path(__file__).parent.resolve()
OUTPUT_DIR = TOOLS_DIR / "output"
TRAIN_DIR = TOOLS_DIR / "datasets" / "train"

sys.path.insert(0, str(TOOLS_DIR))
from train_naija_staples import build_model, quantize_to_tflite, CLASS_NAMES

print("=" * 60)
print("  Exporting and Quantizing NaijaStaples-30 INT8 Model")
print("=" * 60)

h5_path = OUTPUT_DIR / "warmup_best.h5"
if not h5_path.exists():
    raise FileNotFoundError(f"Checkpoint not found: {h5_path}")

print(f"Loading weights from: {h5_path}")
model, backbone = build_model()
model.load_weights(str(h5_path))

saved_model_path = OUTPUT_DIR / "naija_saved_model"
print(f"Saving SavedModel to: {saved_model_path}")
model.save(str(saved_model_path))

print("\nStarting INT8 Calibration & Quantization...")
int8_path = quantize_to_tflite(str(saved_model_path), TRAIN_DIR)

# Copy to mobile app directories
app_models_dir = Path(r"c:\Users\user pc\Desktop\Agrinovva_App\Agrinovva mobile app\models")
android_assets_model = Path(r"c:\Users\user pc\Desktop\Agrinovva_App\Agrinovva mobile app\android\app\src\main\assets\model")
android_public_model = Path(r"c:\Users\user pc\Desktop\Agrinovva_App\Agrinovva mobile app\android\app\src\main\assets\public\assets\model")

android_assets_model.mkdir(parents=True, exist_ok=True)
android_public_model.mkdir(parents=True, exist_ok=True)

destinations = [
    app_models_dir / "naijastables_mobilenetv3_int8.tflite",
    android_assets_model / "naijastables_mobilenetv3_int8.tflite",
    android_public_model / "naijastables_mobilenetv3_int8.tflite",
]

for dest in destinations:
    shutil.copy2(int8_path, dest)
    print(f"Copied model -> {dest} ({os.path.getsize(dest)/1e6:.2f} MB)")

print("\nModel quantization and distribution complete!")
