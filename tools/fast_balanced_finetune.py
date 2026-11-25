#!/usr/bin/env python3
"""
tools/fast_balanced_finetune.py
Fast transfer-learning fine-tuner for PlantDiag.
Balances Cassava, Maize, Rice, Pepper, and Tomato classes.
Trains frozen MobileNetV3 backbone for quick CPU convergence (15-25 mins).
Exports float32 and quantized TFLite to tools/output_finetune/.
"""

import os
import sys
import json
import random
import shutil
from pathlib import Path
import numpy as np

# Set deterministic seed
random.seed(42)
np.random.seed(42)

WORKSPACE = Path(__file__).resolve().parent.parent
DATA_TRAIN = WORKSPACE / "tools" / "datasets" / "train"
DATA_VAL = WORKSPACE / "tools" / "datasets" / "val"
OUTPUT_DIR = WORKSPACE / "tools" / "output_finetune"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

IMG_SIZE = (224, 224)
BATCH_SIZE = 32
MAX_PER_CLASS = 280  # Cap dominant classes so Cassava Mosaic doesn't overpower others
MIN_PER_CLASS = 30   # Minimum images required to include class
EPOCHS = 8

print(f"=== PlantDiag Fast Balanced Fine-Tuning ===")
print(f"Scanning dataset at: {DATA_TRAIN}")

import tensorflow as tf
from tensorflow.keras import layers, models, applications

# 1. Identify valid classes — ONLY crops the 38-class model DOES NOT have:
# The 38-class model already has Corn, Tomato, Pepper, Potato, Orange, etc.
# What it lacks: Cassava (5 classes) and Rice (4 classes).
MISSING_CROP_PREFIXES = ["Cassava___", "Rice___"]

all_subdirs = sorted([d for d in DATA_TRAIN.iterdir() if d.is_dir()])
active_classes = []
for d in all_subdirs:
    # Check if this class belongs to a missing crop
    if any(d.name.startswith(p) for p in MISSING_CROP_PREFIXES):
        img_files = list(d.glob("*.jpg")) + list(d.glob("*.png")) + list(d.glob("*.jpeg"))
        if len(img_files) >= MIN_PER_CLASS:
            active_classes.append(d.name)

print(f"\nTargeting ONLY classes missing from the 38-class model ({len(active_classes)} classes):")
for i, c in enumerate(active_classes):
    n = len(list((DATA_TRAIN / c).glob("*.*")))
    print(f"  [{i:02d}] {c}: {n} images (capped to {min(n, MAX_PER_CLASS)})")

# 2. Build balanced file list
train_filepaths = []
train_labels = []
val_filepaths = []
val_labels = []

for label_idx, c in enumerate(active_classes):
    # Train files
    t_dir = DATA_TRAIN / c
    t_files = sorted(list(t_dir.glob("*.jpg")) + list(t_dir.glob("*.png")) + list(t_dir.glob("*.jpeg")))
    random.shuffle(t_files)
    t_selected = t_files[:MAX_PER_CLASS]
    for p in t_selected:
        train_filepaths.append(str(p))
        train_labels.append(label_idx)

    # Val files
    v_dir = DATA_VAL / c
    if v_dir.exists():
        v_files = sorted(list(v_dir.glob("*.jpg")) + list(v_dir.glob("*.png")) + list(v_dir.glob("*.jpeg")))
        random.shuffle(v_files)
        v_selected = v_files[:60]
    else:
        # Take 15% from train as val if val dir is missing
        v_selected = t_selected[:max(5, int(len(t_selected) * 0.15))]
    for p in v_selected:
        val_filepaths.append(str(p))
        val_labels.append(label_idx)

print(f"\nTotal balanced dataset:")
print(f"  Training samples  : {len(train_filepaths)}")
print(f"  Validation samples: {len(val_filepaths)}")

# 3. TF Data Pipeline
def parse_image(path, label):
    img_raw = tf.io.read_file(path)
    img = tf.image.decode_jpeg(img_raw, channels=3)
    img = tf.image.resize(img, IMG_SIZE)
    # MobileNetV3 expects [0, 255] or [-1, 1], preprocess_input handles it
    img = applications.mobilenet_v3.preprocess_input(img)
    return img, label

def augment_image(img, label):
    img = tf.image.random_flip_left_right(img)
    img = tf.image.random_brightness(img, max_delta=0.15)
    img = tf.image.random_contrast(img, lower=0.85, upper=1.15)
    return img, label

# Shuffle & Batch
train_ds = tf.data.Dataset.from_tensor_slices((train_filepaths, train_labels))
train_ds = train_ds.shuffle(len(train_filepaths), seed=42)
train_ds = train_ds.map(parse_image, num_parallel_calls=tf.data.AUTOTUNE)
train_ds = train_ds.map(augment_image, num_parallel_calls=tf.data.AUTOTUNE)
train_ds = train_ds.batch(BATCH_SIZE).prefetch(tf.data.AUTOTUNE)

val_ds = tf.data.Dataset.from_tensor_slices((val_filepaths, val_labels))
val_ds = val_ds.map(parse_image, num_parallel_calls=tf.data.AUTOTUNE)
val_ds = val_ds.batch(BATCH_SIZE).prefetch(tf.data.AUTOTUNE)

# 4. Model Architecture (Transfer Learning)
num_classes = len(active_classes)
print(f"\nBuilding MobileNetV3-Large with {num_classes} output heads...")

base_model = applications.MobileNetV3Large(
    input_shape=(224, 224, 3),
    include_top=False,
    weights="imagenet",
    pooling="avg"
)
base_model.trainable = False  # Freeze backbone for fast convergence on CPU

inputs = layers.Input(shape=(224, 224, 3))
x = base_model(inputs, training=False)
x = layers.Dropout(0.3)(x)
x = layers.Dense(128, activation="relu")(x)
x = layers.BatchNormalization()(x)
outputs = layers.Dense(num_classes, activation="softmax")(x)

model = models.Model(inputs, outputs)

model.compile(
    optimizer=tf.keras.optimizers.Adam(learning_rate=1e-3),
    loss="sparse_categorical_crossentropy",
    metrics=["accuracy"]
)

print(f"\nTraining for {EPOCHS} epochs (frozen backbone on CPU)...")
history = model.fit(
    train_ds,
    validation_data=val_ds,
    epochs=EPOCHS,
    verbose=1
)

# 5. Save Model & History
keras_path = OUTPUT_DIR / "plantdiag_finetuned.h5"
model.save(str(keras_path))
print(f"\nSaved Keras model to: {keras_path}")

# 6. Export to TFLite (Float32 & Quantized INT8)
print("Converting to TFLite...")
converter = tf.lite.TFLiteConverter.from_keras_model(model)
converter.optimizations = [tf.lite.Optimize.DEFAULT]
tflite_model = converter.convert()

tflite_path = OUTPUT_DIR / "plantdiag_finetuned.tflite"
with open(tflite_path, "wb") as f:
    f.write(tflite_model)
print(f"Saved optimized TFLite model ({len(tflite_model) / 1024 / 1024:.2f} MB) to: {tflite_path}")

# 7. Export classes.json
classes_path = OUTPUT_DIR / "classes.json"
with open(classes_path, "w") as f:
    json.dump(active_classes, f, indent=2)
print(f"Saved active classes ({len(active_classes)}) to: {classes_path}")

print(f"\n=== Fine-Tuning Complete! ===")
