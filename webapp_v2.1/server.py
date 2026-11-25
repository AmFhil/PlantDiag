#!/usr/bin/env python3
"""
PlantDiag Web App v2.1 Server — dual-model TFLite inference + static host.
Based on PlantDiag_Web_App/server.py (dual-model edition), adapted to:
  - serve the webapp_v2.1 folder directly (home.html / app.html / live.html)
  - load BOTH trained models bundled under assets/model/
      v1_7 : ResNet18 38-class (PlantVillage / new-plant-diseases dataset)
      naija: MobileNetV3 9-class (NaijaStaples Cassava & Rice)
  - route a farmer crop override to the model that actually knows that crop
  - when no override exists, run both models and return the more confident
    (lower-entropy) result, labelled with which model answered
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

APP_DIR = Path(__file__).resolve().parent
MODEL_DIR = APP_DIR / "assets" / "model"

print("=====================================================")
print("  PlantDiag(TM) Web Server - v2.1 (dual model)")
print("  Built by Fhinovax(TM)")
print("=====================================================")

try:
    import tensorflow as tf
    Interpreter = tf.lite.Interpreter
    print(f"Loaded TensorFlow {tf.__version__}")
except ImportError:
    try:
        from tflite_runtime.interpreter import Interpreter
        print("Loaded tflite_runtime")
    except ImportError:
        print("ERROR: TensorFlow or tflite_runtime is required. "
              "Please run inside tools/naija_train_env")
        sys.exit(1)


def class_crop_name(class_name):
    if "___" in class_name:
        crop_raw = class_name.split("___", 1)[0]
    else:
        crop_raw = class_name
    return crop_raw.replace("_", " ").strip()


def load_model_entry(version_label, model_file, classes_file, db_file):
    print(f"Loading {version_label} model from {model_file}...")
    interpreter = Interpreter(model_path=str(model_file))
    interpreter.allocate_tensors()
    with open(classes_file, "r", encoding="utf-8") as f:
        cls = json.load(f)
    with open(db_file, "r", encoding="utf-8") as f:
        db = json.load(f)
    print(f"  -> {version_label} Ready: {len(cls)} classes")
    return {
        "version": version_label,
        "interp": interpreter,
        "in_det": interpreter.get_input_details()[0],
        "out_det": interpreter.get_output_details()[0],
        "classes": cls,
        "db": db,
        "crop_set": {class_crop_name(c).lower() for c in cls},
    }


MODELS = {
    "v1.7": load_model_entry(
        "v1.7 (PlantVillage-38)",
        MODEL_DIR / "v1_7" / "model.tflite",
        MODEL_DIR / "v1_7" / "classes.json",
        MODEL_DIR / "v1_7" / "disease_db.json",
    ),
    "naija": load_model_entry(
        "NaijaStaples (9-class Cassava/Rice)",
        MODEL_DIR / "plant_disease_model.tflite",
        MODEL_DIR / "classes.json",
        MODEL_DIR / "disease_db.json",
    ),
}

IMAGENET_MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
IMAGENET_STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)


def preprocess(model_key, img):
    arr = np.array(img, dtype=np.float32)
    if model_key == "v1.7":
        arr = (arr / 255.0 - IMAGENET_MEAN) / IMAGENET_STD
        arr = np.transpose(arr, (2, 0, 1))
        return np.expand_dims(arr, 0).astype(np.float32)
    arr = (arr / 127.5) - 1.0
    return np.expand_dims(arr, 0).astype(np.float32)


def run_model(model_key, img, crop_override=None):
    model = MODELS[model_key]
    interp = model["interp"]
    inp = preprocess(model_key, img)

    interp.set_tensor(model["in_det"]["index"], inp)
    interp.invoke()
    raw_out = interp.get_tensor(model["out_det"]["index"])[0]

    if model_key == "v1.7":
        exp_logits = np.exp(raw_out - np.max(raw_out))
        probs = exp_logits / np.sum(exp_logits)
    else:
        probs = raw_out / np.sum(raw_out)

    classes = model["classes"]
    warning = None

    if crop_override:
        wanted = str(crop_override).strip().lower()
        mask = np.array(
            [class_crop_name(c).lower() == wanted for c in classes],
            dtype=bool,
        )
        if mask.any():
            masked = probs * mask
            total = float(np.sum(masked))
            if total > 1e-8:
                probs = masked / total
        else:
            warning = (f"Model {model_key} has no classes for crop "
                       f"'{crop_override}'; returning unfiltered ranking.")

    num_c = len(classes)
    entropy_norm = -float(np.sum(probs * np.log(probs + 1e-10))) / float(np.log(num_c))

    top_indices = np.argsort(probs)[::-1][:3]
    top_results = []
    for idx in top_indices:
        prob = float(probs[idx])
        class_name = classes[idx]

        if "___" in class_name:
            crop_raw, disease_raw = class_name.split("___", 1)
        else:
            crop_raw, disease_raw = class_name, "General"
        crop = crop_raw.replace("_", " ").strip()
        disease = disease_raw.replace("_", " ").strip()

        matched = None
        for d in model["db"].get("diseases", []):
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
            "is_healthy": (disease.lower() == "healthy"
                           or (matched and matched.get("is_healthy", False))),
            "details": matched,
        })

    result = {
        "model_version": model_key,
        "entropy": round(entropy_norm, 3),
        "top": top_results[0],
        "top3": top_results,
    }
    if warning:
        result["warning"] = warning
    return result


def pick_model_for_crop(crop_override):
    wanted = str(crop_override).strip().lower()
    if wanted in MODELS["naija"]["crop_set"]:
        return "naija"
    if wanted in MODELS["v1.7"]["crop_set"]:
        return "v1.7"
    return None


def diagnose_image(image_bytes, crop_override=None, model_hint=None):
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB").resize((224, 224))

    routed = model_hint if model_hint in MODELS else None
    if not routed and crop_override:
        routed = pick_model_for_crop(crop_override)

    if routed:
        result = run_model(routed, img, crop_override)
        result["crop_override"] = crop_override
        result["model_routing"] = "crop-routed" if crop_override else "explicit"
        return result

    results = {key: run_model(key, img, crop_override) for key in MODELS}
    best_key = min(results, key=lambda k: results[k]["entropy"])
    result = results[best_key]
    result["crop_override"] = crop_override
    result["model_routing"] = "auto-best-of-both"
    result["both_models"] = {
        key: {"entropy": r["entropy"],
              "top_crop": r["top"]["crop"],
              "top_disease": r["top"]["disease"],
              "top_probability": r["top"]["probability"]}
        for key, r in results.items()
    }
    return result


class PlantDiagV21Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(APP_DIR), **kwargs)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self.path = "/home.html"
        return super().do_GET()

    def do_POST(self):
        if self.path.startswith("/api/diagnose"):
            content_length = int(self.headers.get("Content-Length", 0))
            post_data = self.rfile.read(content_length)

            try:
                data = json.loads(post_data.decode("utf-8"))
                img_data_str = data.get("image", "")
                crop_override = data.get("crop") or None
                model_hint = data.get("model") or None

                if "," in img_data_str:
                    img_data_str = img_data_str.split(",", 1)[1]
                image_bytes = base64.b64decode(img_data_str)

                result = diagnose_image(image_bytes, crop_override, model_hint)

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

    def log_message(self, format, *args):
        sys.stdout.write("[v2.1] %s - %s\n" % (self.address_string(), format % args))


def run_server(port=8000):
    server_address = ("", port)
    httpd = HTTPServer(server_address, PlantDiagV21Handler)
    print(f"\n=====================================================")
    print(f"  PlantDiag Web App v2.1 is running at:")
    print(f"  >>> http://localhost:{port}/home.html <<<")
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
