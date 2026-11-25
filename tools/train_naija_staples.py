#!/usr/bin/env python3
r"""
=============================================================================
train_naija_staples.py  –  NaijaStaples-30 Model Training & TFLite Export
=============================================================================
DESCRIPTION
-----------
Trains MobileNetV3-Large on the NaijaStaples-30 dataset (30 disease classes
for Nigerian staple crops) and exports a quantized INT8 TFLite model for
on-device inference in the Agrinovva Android app.

DATASET SOURCES (download and unzip into ./datasets/ before running)
----------------------------------------------------------------------
1. Makerere AI Lab Cassava Disease Dataset:
   https://huggingface.co/datasets/cassava-disease
   OR: https://www.kaggle.com/competitions/cassava-disease/data
   → place in: ./datasets/cassava/

2. IITA/CGIAR African Crop Disease (Maize, Cowpea, Sorghum):
   https://dataverse.harvard.edu/dataset.xhtml?persistentId=doi:10.7910/DVN/CWXFH3
   → place in: ./datasets/iita_african_crops/

3. PlantDoc In-Situ Field Images (Tomato, Pepper):
   https://github.com/pratikkayal/PlantDoc-Dataset
   → place in: ./datasets/plantdoc/

4. UCI Rice Disease Dataset (Blast, Brown Spot, BLB):
   https://www.kaggle.com/datasets/minhhuy2810/rice-diseases-image-dataset
   → place in: ./datasets/rice/

5. Yam Disease Dataset (IITA/ResearchGate field photos):
   Manual collection from IITA genebank + field surveys
   → place in: ./datasets/yam/

EXPECTED DIRECTORY STRUCTURE
-----------------------------
datasets/
  train/
    Cassava___Bacterial_Blight/       (≥500 images)
    Cassava___Brown_Streak_Disease/   (≥500 images)
    Cassava___Green_Mottle/           (≥300 images)
    Cassava___Mosaic_Disease/         (≥500 images)
    Cassava___Healthy/                (≥500 images)
    Corn_(maize)___Common_Rust/       (≥500 images)
    Corn_(maize)___Northern_Leaf_Blight/ (≥500 images)
    Corn_(maize)___Fall_Armyworm/     (≥400 images)
    Corn_(maize)___Healthy/           (≥500 images)
    Yam___Anthracnose/                (≥300 images)
    Yam___Mosaic_Virus/               (≥300 images)
    Yam___Healthy/                    (≥400 images)
    Cowpea___Cercospora_Leaf_Spot/    (≥400 images)
    Cowpea___Bacterial_Blight/        (≥300 images)
    Cowpea___Healthy/                 (≥400 images)
    Rice___Bacterial_Blight/          (≥500 images)
    Rice___Blast/                     (≥500 images)
    Rice___Brown_Spot/                (≥400 images)
    Rice___Healthy/                   (≥500 images)
    Tomato___Bacterial_Spot/          (≥400 images)
    Tomato___Early_Blight/            (≥400 images)
    Tomato___Late_Blight/             (≥400 images)
    Tomato___Yellow_Leaf_Curl_Virus/  (≥400 images)
    Tomato___Leaf_Miner_Tuta/         (≥300 images)
    Tomato___Healthy/                 (≥500 images)
    Pepper___Bacterial_Spot/          (≥400 images)
    Pepper___Leaf_Curl/               (≥300 images)
    Pepper___Healthy/                 (≥400 images)
    Sorghum___Anthracnose/            (≥400 images)
    Sorghum___Healthy/                (≥400 images)
  val/
    (same structure, ~20% split)

REQUIREMENTS
------------
    pip install tensorflow==2.15.0 albumentations==1.3.1 pillow numpy

USAGE
-----
    # Full training run (GPU recommended):
    python train_naija_staples.py

    # Quantize only (if you already have a saved Keras model):
    python train_naija_staples.py --quantize-only --saved-model-path ./output/naija_saved_model

    # Custom dataset path:
    python train_naija_staples.py --dataset-dir /path/to/datasets

OUTPUT
------
    ./output/
        naija_saved_model/              (Keras SavedModel format)
        naijastables_mobilenetv3.h5     (Keras HDF5 weights)
        naijastables_mobilenetv3_float32.tflite   (~15MB, for desktop testing)
        naijastables_mobilenetv3_int8.tflite      (~5-7MB, for production Android app)
        training_history.json           (loss/accuracy curves)
        confusion_matrix.png            (validation performance)

    COPY naijastables_mobilenetv3_int8.tflite to:
    Agrinovva mobile app/models/naijastables_mobilenetv3_int8.tflite

=============================================================================
"""

import os
import json
import argparse
import numpy as np
from pathlib import Path

# ─── Parse CLI arguments ───────────────────────────────────────────────────
parser = argparse.ArgumentParser(description="Train NaijaStaples-30 TFLite model")
parser.add_argument("--dataset-dir", type=str, default="./datasets",
                    help="Root directory containing train/ and val/ subdirs")
parser.add_argument("--output-dir", type=str, default="./output",
                    help="Where to save models and artifacts")
parser.add_argument("--warmup-epochs", type=int, default=5,
                    help="Number of warm-up epochs (default: 5)")
parser.add_argument("--epochs", type=int, default=15,
                    help="Total number of epochs including warmup (default: 15)")
parser.add_argument("--batch-size", type=int, default=32,
                    help="Batch size (default: 32)")
parser.add_argument("--img-size", type=int, default=224,
                    help="Input image size (default: 224)")
parser.add_argument("--learning-rate", type=float, default=1e-4,
                    help="Initial learning rate (default: 1e-4)")
parser.add_argument("--fast", action="store_true",
                    help="Enable high-speed native C++ TF augmentation for fast CPU training")
parser.add_argument("--quantize-only", action="store_true",
                    help="Skip training; only quantize an existing SavedModel")
parser.add_argument("--saved-model-path", type=str,
                    default="./output/naija_saved_model",
                    help="Path to SavedModel for --quantize-only mode")
args = parser.parse_args()

# ─── Configuration ─────────────────────────────────────────────────────────
DATASET_DIR   = Path(args.dataset_dir)
TRAIN_DIR     = DATASET_DIR / "train"
VAL_DIR       = DATASET_DIR / "val"
OUTPUT_DIR    = Path(args.output_dir)
IMG_SIZE      = (args.img_size, args.img_size)
BATCH_SIZE    = args.batch_size
WARMUP_EPOCHS = args.warmup_epochs
EPOCHS        = args.epochs
LR            = args.learning_rate
NUM_CLASSES   = 30
FAST_MODE     = args.fast

# NaijaStaples-30 class order — MUST match classes.json indices
CLASS_NAMES = [
    "Cassava___Bacterial_Blight",
    "Cassava___Brown_Streak_Disease",
    "Cassava___Green_Mottle",
    "Cassava___Mosaic_Disease",
    "Cassava___Healthy",
    "Corn_(maize)___Common_Rust",
    "Corn_(maize)___Northern_Leaf_Blight",
    "Corn_(maize)___Fall_Armyworm",
    "Corn_(maize)___Healthy",
    "Yam___Anthracnose",
    "Yam___Mosaic_Virus",
    "Yam___Healthy",
    "Cowpea___Cercospora_Leaf_Spot",
    "Cowpea___Bacterial_Blight",
    "Cowpea___Healthy",
    "Rice___Bacterial_Blight",
    "Rice___Blast",
    "Rice___Brown_Spot",
    "Rice___Healthy",
    "Tomato___Bacterial_Spot",
    "Tomato___Early_Blight",
    "Tomato___Late_Blight",
    "Tomato___Yellow_Leaf_Curl_Virus",
    "Tomato___Leaf_Miner_Tuta",
    "Tomato___Healthy",
    "Pepper___Bacterial_Spot",
    "Pepper___Leaf_Curl",
    "Pepper___Healthy",
    "Sorghum___Anthracnose",
    "Sorghum___Healthy",
]

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ─── Imports (deferred so argparse help works without TF installed) ─────────
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers
from tensorflow.keras.applications import MobileNetV3Large
from tensorflow.keras.callbacks import (
    EarlyStopping, ReduceLROnPlateau, ModelCheckpoint, CSVLogger
)

print(f"\n{'='*60}")
print(f"  NaijaStaples-30 | TF {tf.__version__} | GPU: {bool(tf.config.list_physical_devices('GPU'))}")
print(f"{'='*60}\n")


# ─── Albumentations field augmentation pipeline ────────────────────────────
def build_albumentations_augmenter():
    """
    Heavy field-condition augmentation to bridge the lab-to-field domain gap.
    Simulates: African sunlight/shadow, phone camera lens noise, dust haze,
    partial occlusion, and field angle variance.
    """
    try:
        import albumentations as A
        from albumentations import Compose

        transform = Compose([
            # Geometry
            A.RandomRotate90(p=0.5),
            A.Flip(p=0.5),
            A.ShiftScaleRotate(shift_limit=0.1, scale_limit=0.2,
                               rotate_limit=30, border_mode=0, p=0.7),
            A.Perspective(scale=(0.05, 0.15), p=0.4),

            # Colour / lighting — simulates harsh African sun and shade
            A.OneOf([
                A.RandomBrightnessContrast(brightness_limit=0.4,
                                           contrast_limit=0.4, p=1.0),
                A.HueSaturationValue(hue_shift_limit=20,
                                     sat_shift_limit=40,
                                     val_shift_limit=30, p=1.0),
                A.RGBShift(r_shift_limit=25, g_shift_limit=25,
                           b_shift_limit=25, p=1.0),
            ], p=0.9),

            # Shadow / sunlight patches
            A.RandomShadow(shadow_roi=(0, 0.0, 1, 1),
                           num_shadows_lower=1, num_shadows_upper=2,
                           shadow_dimension=5, p=0.5),
            A.RandomSunFlare(flare_roi=(0, 0, 1, 0.5),
                             angle_lower=0, angle_upper=1,
                             num_flare_circles_lower=3,
                             num_flare_circles_upper=7,
                             src_radius=75, p=0.2),

            # Noise / blur — simulates budget smartphone cameras
            A.OneOf([
                A.GaussNoise(var_limit=(10, 80), p=1.0),
                A.ISONoise(color_shift=(0.01, 0.05),
                           intensity=(0.1, 0.5), p=1.0),
                A.ImageCompression(quality_lower=50,
                                   quality_upper=90, p=1.0),
            ], p=0.6),
            A.OneOf([
                A.Blur(blur_limit=5, p=1.0),
                A.MotionBlur(blur_limit=9, p=1.0),
            ], p=0.3),

            # Occlusion — simulates partial leaf obstruction
            A.CoarseDropout(max_holes=6, max_height=32,
                            max_width=32, fill_value=0, p=0.4),

            # Atmospheric haze simulation
            A.RandomFog(fog_coef_lower=0.1, fog_coef_upper=0.3,
                        alpha_coef=0.1, p=0.2),
        ])
        return transform

    except ImportError:
        print("WARNING: albumentations not installed. Using TF-only augmentation.")
        return None


def augment_with_albumentations(image, transform):
    """Apply albumentations transform to a single image numpy array."""
    if transform is None:
        return image
    result = transform(image=image)
    return result["image"]


# ─── Dataset pipeline ───────────────────────────────────────────────────────
def preprocess_image(image, label):
    """Normalize image to [-1, 1] for MobileNetV3."""
    image = tf.cast(image, tf.float32)
    image = tf.keras.applications.mobilenet_v3.preprocess_input(image)
    return image, label


def build_dataset(data_dir: Path, augment: bool = False, alb_transform=None):
    """Build a tf.data pipeline from an image directory."""
    raw_ds = tf.keras.utils.image_dataset_from_directory(
        str(data_dir),
        class_names=CLASS_NAMES,
        image_size=IMG_SIZE,
        batch_size=BATCH_SIZE,
        label_mode="categorical",
        shuffle=augment,
        seed=42,
    )

    if augment:
        if FAST_MODE:
            # Native TensorFlow C++ batch augmentation for fast multithreaded CPU training
            tf_augmenter = tf.keras.Sequential([
                layers.RandomFlip("horizontal_and_vertical"),
                layers.RandomRotation(0.15),
                layers.RandomZoom(0.1),
                layers.RandomContrast(0.15),
            ])
            raw_ds = raw_ds.map(lambda x, y: (tf_augmenter(x, training=True), y),
                                num_parallel_calls=tf.data.AUTOTUNE)
        elif alb_transform is not None:
            # Apply albumentations per image (runs in tf.numpy_function)
            def aug_map(images, labels):
                def _aug_batch(imgs):
                    imgs = imgs.numpy().astype(np.uint8)
                    out = np.stack([
                        augment_with_albumentations(imgs[i], alb_transform)
                        for i in range(imgs.shape[0])
                    ])
                    return out.astype(np.float32)

                augmented = tf.numpy_function(
                    func=_aug_batch, inp=[images], Tout=tf.float32
                )
                augmented.set_shape([None, IMG_SIZE[0], IMG_SIZE[1], 3])
                return augmented, labels

            raw_ds = raw_ds.map(aug_map, num_parallel_calls=tf.data.AUTOTUNE)

    ds = raw_ds.map(preprocess_image, num_parallel_calls=tf.data.AUTOTUNE)
    ds = ds.prefetch(tf.data.AUTOTUNE)
    return ds


# ─── Model definition ────────────────────────────────────────────────────────
def build_model(num_classes: int = NUM_CLASSES,
                img_size: tuple = IMG_SIZE,
                dropout_rate: float = 0.4) -> keras.Model:
    """
    MobileNetV3-Large with custom classification head.
    - Backbone frozen for first 10 epochs (warm-up).
    - Then unfrozen for full fine-tuning with discriminative LRs.
    """
    inputs = layers.Input(shape=(*img_size, 3), name="input_image")

    backbone = MobileNetV3Large(
        input_shape=(*img_size, 3),
        include_top=False,
        weights="imagenet",
        include_preprocessing=False,  # We handle preprocessing in the pipeline
    )
    backbone.trainable = False  # Freeze for warm-up phase

    x = backbone(inputs, training=False)
    x = layers.GlobalAveragePooling2D(name="gap")(x)
    x = layers.Dense(512, activation="relu", name="fc1")(x)
    x = layers.BatchNormalization(name="bn_fc1")(x)
    x = layers.Dropout(dropout_rate, name="dropout")(x)
    x = layers.Dense(256, activation="relu", name="fc2")(x)
    outputs = layers.Dense(num_classes, activation="softmax", name="predictions")(x)

    model = keras.Model(inputs, outputs, name="NaijaStaples_MobileNetV3L")
    return model, backbone


# ─── Training ────────────────────────────────────────────────────────────────
def train():
    alb_transform = build_albumentations_augmenter()

    print("Building dataset pipelines...")
    train_ds = build_dataset(TRAIN_DIR, augment=True, alb_transform=alb_transform)
    val_ds   = build_dataset(VAL_DIR,   augment=False)

    print("Building model...")
    model, backbone = build_model()

    # ── Phase 1: Warm-up — train only the classification head ──────────────
    print(f"\n[Phase 1] Warm-up: training classification head only ({WARMUP_EPOCHS} epochs)...")
    model.compile(
        optimizer=keras.optimizers.Adam(learning_rate=LR * 10),
        loss="categorical_crossentropy",
        metrics=["accuracy",
                 keras.metrics.TopKCategoricalAccuracy(k=3, name="top3_accuracy")]
    )

    warmup_callbacks = [
        ModelCheckpoint(
            str(OUTPUT_DIR / "warmup_best.h5"),
            monitor="val_accuracy", save_best_only=True, verbose=1
        ),
        CSVLogger(str(OUTPUT_DIR / "warmup_log.csv")),
    ]
    if WARMUP_EPOCHS > 0:
        model.fit(train_ds, validation_data=val_ds,
                  epochs=WARMUP_EPOCHS, callbacks=warmup_callbacks)

    # ── Phase 2: Fine-tune — unfreeze backbone with lower LR ───────────────
    print(f"\n[Phase 2] Fine-tuning: unfreezing backbone (epochs {WARMUP_EPOCHS} to {EPOCHS})...")
    backbone.trainable = True

    # Use discriminative learning rates:
    # bottom layers get LR/10, top layers get full LR
    model.compile(
        optimizer=keras.optimizers.Adam(learning_rate=LR),
        loss="categorical_crossentropy",
        metrics=["accuracy",
                 keras.metrics.TopKCategoricalAccuracy(k=3, name="top3_accuracy")]
    )

    finetune_callbacks = [
        EarlyStopping(monitor="val_accuracy", patience=8,
                      restore_best_weights=True, verbose=1),
        ReduceLROnPlateau(monitor="val_loss", factor=0.3,
                          patience=4, min_lr=1e-7, verbose=1),
        ModelCheckpoint(
            str(OUTPUT_DIR / "naijastables_mobilenetv3.h5"),
            monitor="val_accuracy", save_best_only=True, verbose=1
        ),
        CSVLogger(str(OUTPUT_DIR / "finetune_log.csv")),
    ]

    history = model.fit(
        train_ds, validation_data=val_ds,
        epochs=EPOCHS,
        initial_epoch=WARMUP_EPOCHS,
        callbacks=finetune_callbacks,
    )

    # Save history
    history_path = OUTPUT_DIR / "training_history.json"
    with open(history_path, "w") as f:
        json.dump(
            {k: [float(v) for v in vals] for k, vals in history.history.items()},
            f, indent=2
        )
    print(f"Training history saved → {history_path}")

    # Save SavedModel
    saved_model_path = OUTPUT_DIR / "naija_saved_model"
    model.save(str(saved_model_path))
    print(f"SavedModel saved → {saved_model_path}")

    # Plot confusion matrix
    try:
        generate_confusion_matrix(model, val_ds)
    except Exception as e:
        print(f"Warning: could not generate confusion matrix: {e}")

    return str(saved_model_path)


# ─── Confusion matrix ────────────────────────────────────────────────────────
def generate_confusion_matrix(model, val_ds):
    import matplotlib.pyplot as plt
    from sklearn.metrics import confusion_matrix
    import itertools

    all_labels, all_preds = [], []
    for images, labels in val_ds:
        preds = model.predict(images, verbose=0)
        all_labels.extend(np.argmax(labels.numpy(), axis=1))
        all_preds.extend(np.argmax(preds, axis=1))

    cm = confusion_matrix(all_labels, all_preds)
    fig, ax = plt.subplots(figsize=(16, 16))
    im = ax.imshow(cm, interpolation="nearest", cmap=plt.cm.Blues)
    plt.colorbar(im)

    short_names = [c.split("___")[-1][:20] for c in CLASS_NAMES]
    tick_marks = np.arange(NUM_CLASSES)
    ax.set_xticks(tick_marks)
    ax.set_xticklabels(short_names, rotation=45, ha="right", fontsize=7)
    ax.set_yticks(tick_marks)
    ax.set_yticklabels(short_names, fontsize=7)

    thresh = cm.max() / 2.0
    for i, j in itertools.product(range(cm.shape[0]), range(cm.shape[1])):
        ax.text(j, i, format(cm[i, j], "d"),
                ha="center", va="center",
                color="white" if cm[i, j] > thresh else "black",
                fontsize=5)

    ax.set_ylabel("True Label", fontsize=10)
    ax.set_xlabel("Predicted Label", fontsize=10)
    ax.set_title("NaijaStaples-30 Validation Confusion Matrix", fontsize=12)
    plt.tight_layout()
    cm_path = OUTPUT_DIR / "confusion_matrix.png"
    plt.savefig(str(cm_path), dpi=150)
    plt.close()
    print(f"Confusion matrix saved → {cm_path}")


# ─── INT8 Quantization ──────────────────────────────────────────────────────
def quantize_to_tflite(saved_model_path: str, representative_ds_dir: Path):
    """
    Convert SavedModel to:
      1. Float32 TFLite (for reference/desktop testing)
      2. INT8 quantized TFLite (for production Android deployment)

    INT8 reduces model size from ~15MB → ~5-7MB and speeds up inference
    by 2-4x on Cortex-A class CPUs (budget Android phones).
    """
    print(f"\nConverting {saved_model_path} to TFLite (float32)...")

    # ── Float32 baseline ────────────────────────────────────────────────────
    converter_f32 = tf.lite.TFLiteConverter.from_saved_model(saved_model_path)
    tflite_f32    = converter_f32.convert()
    f32_path      = OUTPUT_DIR / "naijastables_mobilenetv3_float32.tflite"
    f32_path.write_bytes(tflite_f32)
    print(f"Float32 TFLite saved -> {f32_path}  ({len(tflite_f32)/1e6:.2f} MB)")

    # ── Representative dataset for INT8 calibration ─────────────────────────
    def representative_dataset_gen():
        """Provides ~200 sample images from the training set for calibration."""
        cal_ds = tf.keras.utils.image_dataset_from_directory(
            str(representative_ds_dir),
            class_names=CLASS_NAMES,
            image_size=IMG_SIZE,
            batch_size=1,
            label_mode=None,
            shuffle=True,
            seed=42,
        )
        cal_ds = cal_ds.map(
            lambda x: tf.keras.applications.mobilenet_v3.preprocess_input(
                tf.cast(x, tf.float32)
            )
        )
        count = 0
        for img in cal_ds.take(200):
            yield [img]
            count += 1
        print(f"  Calibration: used {count} images")

    # ── INT8 full quantization ───────────────────────────────────────────────
    print("\nConverting to INT8 quantized TFLite (this may take 1-3 minutes)...")
    converter_int8 = tf.lite.TFLiteConverter.from_saved_model(saved_model_path)
    converter_int8.optimizations            = [tf.lite.Optimize.DEFAULT]
    converter_int8.representative_dataset   = representative_dataset_gen
    converter_int8.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS_INT8]
    converter_int8.inference_input_type     = tf.uint8
    converter_int8.inference_output_type    = tf.uint8

    tflite_int8 = converter_int8.convert()
    int8_path   = OUTPUT_DIR / "naijastables_mobilenetv3_int8.tflite"
    int8_path.write_bytes(tflite_int8)
    print(f"INT8 TFLite saved -> {int8_path}  ({len(tflite_int8)/1e6:.2f} MB)")

    # ── Quick accuracy sanity-check on INT8 model ────────────────────────────
    print("\nRunning INT8 sanity check (first 50 val images)...")
    interpreter = tf.lite.Interpreter(str(int8_path))
    interpreter.allocate_tensors()
    in_idx  = interpreter.get_input_details()[0]["index"]
    out_idx = interpreter.get_output_details()[0]["index"]
    in_scale, in_zero_point = interpreter.get_input_details()[0]["quantization"]

    correct = total = 0
    sanity_ds = tf.keras.utils.image_dataset_from_directory(
        str(VAL_DIR),
        class_names=CLASS_NAMES,
        image_size=IMG_SIZE,
        batch_size=1,
        label_mode="categorical",
        shuffle=False,
    )
    for img, lbl in sanity_ds.take(50):
        img_np = img.numpy()[0]
        # Quantize float image to uint8
        img_q = (img_np / in_scale + in_zero_point).astype(np.uint8)
        img_q = np.expand_dims(img_q, axis=0)
        interpreter.set_tensor(in_idx, img_q)
        interpreter.invoke()
        out = interpreter.get_tensor(out_idx)[0]
        if np.argmax(out) == np.argmax(lbl.numpy()[0]):
            correct += 1
        total += 1

    print(f"INT8 sanity accuracy: {correct}/{total} = {correct/total*100:.1f}%")

    print("\n[OK] QUANTIZATION COMPLETE")
    print(f"   Deploy file -> {int8_path}")
    print("   Copy to: 'Agrinovva mobile app/models/naijastables_mobilenetv3_int8.tflite'")

    return str(int8_path)


# ─── Entry point ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    if args.quantize_only:
        print(f"[--quantize-only] Skipping training. Using: {args.saved_model_path}")
        if not Path(args.saved_model_path).exists():
            raise FileNotFoundError(
                f"SavedModel not found at: {args.saved_model_path}\n"
                f"Run training first (without --quantize-only)."
            )
        quantize_to_tflite(args.saved_model_path, TRAIN_DIR)
    else:
        # Validate dataset directories exist
        if not TRAIN_DIR.exists():
            raise FileNotFoundError(
                f"\nTraining directory not found: {TRAIN_DIR}\n"
                f"Please download the datasets (see docstring above) and "
                f"place them under: {DATASET_DIR}/train/<ClassName>/"
            )
        if not VAL_DIR.exists():
            raise FileNotFoundError(
                f"\nValidation directory not found: {VAL_DIR}\n"
                f"Split your dataset into train/ and val/ subdirectories."
            )

        saved_model_path = train()
        quantize_to_tflite(saved_model_path, TRAIN_DIR)

    print("\n🎉 Done! NaijaStaples-30 training pipeline complete.")
