import sys
import os

# Crucial Windows OpenMP & headless configurations
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"
os.environ["MPLBACKEND"] = "Agg"

results_path = os.path.join(os.path.dirname(__file__), "test_results.txt")

def log(msg):
    print(msg, flush=True)
    with open(results_path, "a") as f:
        f.write(msg + "\n")

with open(results_path, "w") as f:
    f.write("=== ML ENVIRONMENT TEST LOG ===\n")

log(f"Python: {sys.version}")
log(f"Executable: {sys.executable}")

try:
    log("Testing numpy...")
    import numpy as np
    log(f"NumPy: {np.__version__}")
except Exception as e:
    log(f"NumPy Error: {e}")

try:
    log("Testing Pillow...")
    import PIL
    log(f"Pillow: {PIL.__version__}")
except Exception as e:
    log(f"Pillow Error: {e}")

try:
    log("Testing scipy...")
    import scipy
    log(f"SciPy: {scipy.__version__}")
except Exception as e:
    log(f"SciPy Error: {e}")

try:
    log("Testing scikit-learn...")
    import sklearn
    log(f"Scikit-Learn: {sklearn.__version__}")
except Exception as e:
    log(f"Scikit-Learn Error: {e}")

try:
    log("Testing matplotlib...")
    import matplotlib
    log(f"Matplotlib: {matplotlib.__version__}")
except Exception as e:
    log(f"Matplotlib Error: {e}")

try:
    log("Testing huggingface_hub...")
    import huggingface_hub
    log(f"HuggingFace Hub: {huggingface_hub.__version__}")
except Exception as e:
    log(f"HuggingFace Hub Error: {e}")

try:
    log("Testing kagglehub...")
    import kagglehub
    log(f"KaggleHub: {kagglehub.__version__}")
except Exception as e:
    log(f"KaggleHub Error: {e}")

try:
    log("Testing tensorflow...")
    import tensorflow as tf
    log(f"TensorFlow: {tf.__version__}")
    log(f"Keras: {tf.keras.__version__}")
    gpus = tf.config.list_physical_devices("GPU")
    log(f"GPUs available: {len(gpus)}")
except Exception as e:
    log(f"TensorFlow Error: {e}")

log("=== ALL ENVIRONMENT CHECKS COMPLETED SUCCESSFULLY ===")
os._exit(0)
