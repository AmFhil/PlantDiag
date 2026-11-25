#!/usr/bin/env python3
"""
PlantDiag Web App Server — Dual Model Inference (v1.7 & v2.0)
Built with Python standard library http.server + TensorFlow Lite.
"""

import os
import sys
import json
import base64
import io
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler
import numpy as np
from PIL import Image

# Working paths
APP_DIR = Path(__file__).resolve().parent
PUBLIC_DIR = APP_DIR / "public"
MODELS_DIR = APP_DIR / "models"

print("=====================================================")
print("  PlantDiag™ Web Server — Dual Model Edition")
print("  Built by Fhinovax™")
print("=====================================================")

# Import TFLite interpreter
try:
    import tensorflow as tf
    Interpreter = tf.lite.Interpreter
    print(f"Loaded TensorFlow {tf.__version__}")
except ImportError:
    try:
        from tflite_runtime.interpreter import Interpreter
        print("Loaded tflite_runtime")
    except ImportError:
        print("ERROR: TensorFlow or tflite_runtime is required. Please run inside tools/naija_train_env")
        sys.exit(1)

# 1. Load Model v1.7 (38-class ResNet NCHW ImageNet)
V1_DIR = MODELS_DIR / "v1_7"
v1_model_path = V1_DIR / "model.tflite"
v1_classes_path = V1_DIR / "classes.json"
v1_db_path = V1_DIR / "disease_db.json"

print(f"Loading v1.7 model from {v1_model_path}...")
v1_interp = Interpreter(model_path=str(v1_model_path))
v1_interp.allocate_tensors()
v1_in_det = v1_interp.get_input_details()[0]
v1_out_det = v1_interp.get_output_details()[0]

with open(v1_classes_path, "r", encoding="utf-8") as f:
    v1_classes = json.load(f)

with open(v1_db_path, "r", encoding="utf-8") as f:
    v1_db = json.load(f)

print(f"  -> v1.7 Ready: {len(v1_classes)} classes (Corn, Tomato, Pepper, Potato, Citrus, etc.)")

# 2. Load Model v2.0 (9-class MobileNetV3 NHWC [-1, 1])
V2_DIR = MODELS_DIR / "v2_0"
v2_model_path = V2_DIR / "model.tflite"
v2_classes_path = V2_DIR / "classes.json"
v2_db_path = V2_DIR / "disease_db.json"

print(f"Loading v2.0 model from {v2_model_path}...")
v2_interp = Interpreter(model_path=str(v2_model_path))
v2_interp.allocate_tensors()
v2_in_det = v2_interp.get_input_details()[0]
v2_out_det = v2_interp.get_output_details()[0]

with open(v2_classes_path, "r", encoding="utf-8") as f:
    v2_classes = json.load(f)

with open(v2_db_path, "r", encoding="utf-8") as f:
    v2_db = json.load(f)

print(f"  -> v2.0 Ready: {len(v2_classes)} fine-tuned classes (Cassava & Rice regional staples)")

IMAGENET_MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
IMAGENET_STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)

def run_inference(image_bytes, model_version="v2.0"):
    # Load and normalize PIL image
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB").resize((224, 224))
    arr = np.array(img, dtype=np.float32)

    if model_version == "v1.7":
        # v1.7: Float32 [1, 3, 224, 224] NCHW, ImageNet normalization
        arr = (arr / 255.0 - IMAGENET_MEAN) / IMAGENET_STD
        arr = np.transpose(arr, (2, 0, 1)) # NCHW
        inp = np.expand_dims(arr, 0).astype(np.float32)

        v1_interp.set_tensor(v1_in_det["index"], inp)
        v1_interp.invoke()
        logits = v1_interp.get_tensor(v1_out_det["index"])[0]

        # Softmax
        exp_logits = np.exp(logits - np.max(logits))
        probs = exp_logits / np.sum(exp_logits)
        classes = v1_classes
        db = v1_db
    else:
        # v2.0: Float32 [1, 224, 224, 3] NHWC, [-1.0, 1.0] normalization
        arr = (arr / 127.5) - 1.0
        inp = np.expand_dims(arr, 0).astype(np.float32)

        v2_interp.set_tensor(v2_in_det["index"], inp)
        v2_interp.invoke()
        raw_out = v2_interp.get_tensor(v2_out_det["index"])[0]

        # In v2.0 model ends in Softmax, so probabilities sum to 1.0
        probs = raw_out / np.sum(raw_out)
        classes = v2_classes
        db = v2_db

    # Normalized entropy
    num_c = len(classes)
    entropy_norm = -float(np.sum(probs * np.log(probs + 1e-10))) / float(np.log(num_c))

    # Top-3 ranking
    top_indices = np.argsort(probs)[::-1][:3]
    top_results = []
    for idx in top_indices:
        prob = float(probs[idx])
        class_name = classes[idx]
        
        # Split crop and disease
        if "___" in class_name:
            crop_raw, disease_raw = class_name.split("___", 1)
        else:
            crop_raw, disease_raw = class_name, "General"
        crop = crop_raw.replace("_", " ").replace("(maize)", "").strip()
        disease = disease_raw.replace("_", " ").strip()

        # Find in disease_db
        db_entries = db.get("diseases", [])
        matched = None
        for d in db_entries:
            if d.get("model_class_id") == int(idx):
                matched = d
                break

        top_results.append({
            "idx": int(idx),
            "class_name": class_name,
            "crop": crop,
            "disease": disease,
            "probability": prob,
            "percentage": round(prob * 100, 1),
            "is_healthy": (disease.lower() == "healthy" or (matched and matched.get("is_healthy", False))),
            "details": matched
        })

    top1 = top_results[0]
    return {
        "model_version": model_version,
        "entropy": round(entropy_norm, 3),
        "top": top1,
        "top3": top_results
    }


class PlantDiagHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(PUBLIC_DIR), **kwargs)

    def do_POST(self):
        if self.path.startswith("/api/diagnose"):
            content_length = int(self.headers.get("Content-Length", 0))
            post_data = self.rfile.read(content_length)

            try:
                data = json.loads(post_data.decode("utf-8"))
                img_data_str = data.get("image", "")
                model_ver = data.get("model", "v2.0")

                # Parse base64
                if "," in img_data_str:
                    img_data_str = img_data_str.split(",", 1)[1]
                image_bytes = base64.b64decode(img_data_str)

                result = run_inference(image_bytes, model_ver)

                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps(result).encode("utf-8"))

            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                err_resp = {"error": str(e)}
                self.wfile.write(json.dumps(err_resp).encode("utf-8"))
            return

        self.send_error(404, "Endpoint not found")

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()


def run_server(port=8000):
    server_address = ("", port)
    httpd = HTTPServer(server_address, PlantDiagHandler)
    print(f"\n=====================================================")
    print(f"  PlantDiag Web App is running at:")
    print(f"  >>> http://localhost:{port} <<<")
    print(f"=====================================================")
    print(f"Press Ctrl+C to stop the server.\n")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")


if __name__ == "__main__":
    port = 8000
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            pass
    run_server(port)
