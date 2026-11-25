import os
import glob
import numpy as np
from PIL import Image
import tensorflow as tf

model_path = r"Agrinovva mobile app/models/naijastables_mobilenetv3_int8.tflite"
interpreter = tf.lite.Interpreter(model_path=model_path)
interpreter.allocate_tensors()

in_details = interpreter.get_input_details()[0]
out_details = interpreter.get_output_details()[0]

val_images = glob.glob(r"tools/datasets/val/*/*.jpg") + glob.glob(r"tools/datasets/val/*/*.JPG")
if not val_images:
    val_images = glob.glob(r"tools/datasets/train/*/*.jpg")

print(f"Found {len(val_images)} sample images.")
if val_images:
    for img_path in val_images[:5]:
        img = Image.open(img_path).convert('RGB').resize((224, 224))
        # Raw uint8 input [1, 224, 224, 3]
        input_data = np.expand_dims(np.array(img, dtype=np.uint8), axis=0)
        
        interpreter.set_tensor(in_details['index'], input_data)
        interpreter.invoke()
        
        raw_out = interpreter.get_tensor(out_details['index'])[0]
        scale, zero_point = out_details['quantization']
        probs = (raw_out.astype(np.float32) - zero_point) * scale
        
        top_idx = np.argmax(probs)
        top_prob = probs[top_idx]
        
        # Calculate entropy
        p = probs[probs > 1e-10]
        entropy = -np.sum(p * np.log(p)) / np.log(30)
        
        # Softmax of probs (the bug!)
        exp_p = np.exp(probs - np.max(probs))
        double_softmax = exp_p / np.sum(exp_p)
        top_ds_prob = double_softmax[top_idx]
        ds_entropy = -np.sum(double_softmax * np.log(double_softmax)) / np.log(30)
        
        print(f"\nImage: {os.path.basename(os.path.dirname(img_path))}/{os.path.basename(img_path)}")
        print(f"  Raw output sum: {np.sum(probs):.4f}")
        print(f"  Top class idx: {top_idx}, Direct Prob: {top_prob*100:.1f}%, Entropy: {entropy:.3f}")
        print(f"  WITH DOUBLE SOFTMAX BUG: Top Prob: {top_ds_prob*100:.1f}%, Entropy: {ds_entropy:.3f}")
